"""Run one LLM arm over the frozen panel.

  python -m arms.run_arm --arm A3 --seed 1 --panel frozen/panel.csv --out runs/A3_s1

Refuses if frozen/ has uncommitted changes (R6). Checkpoints every gene to <out>/genes/<code>.json,
so a crashed run resumes where it stopped. Genes run in parallel; the per-gene call cap is enforced
by the shared LLM client.
"""
import argparse, csv, json, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import config
import scoring
from board.artifact import Artifact, ArtifactStore
from llm.client import LLMClient


def frozen_is_clean():
    out = subprocess.run(["git", "status", "--porcelain", "--", "frozen/"], cwd=config.ROOT,
                         capture_output=True, text=True, check=True).stdout
    return not out.strip()


def git_head():
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=config.ROOT,
                          capture_output=True, text=True, check=True).stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["A1", "A3"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--panel", default="frozen/panel.csv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None, help="first N genes only (smoke test)")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)

    if not frozen_is_clean():
        sys.exit("refusing to run: frozen/ has uncommitted changes (R6)")
    out = Path(args.out)
    genes_dir = out / "genes"
    genes_dir.mkdir(parents=True, exist_ok=True)
    with open(args.panel) as f:
        codes = [r["gene_code"] for r in csv.DictReader(f)][:args.limit]
    meta = {"arm": args.arm, "seed": args.seed, "model": config.LLM_MODEL, "backend": config.LLM_BACKEND,
            "temperature": config.TEMPERATURE, "reasoning_effort": config.LLM_REASONING_EFFORT,
            "max_calls_per_gene": config.MAX_LLM_CALLS_PER_GENE, "git_head": git_head(),
            "n_genes": len(codes)}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))

    client = LLMClient(f"{args.arm}_s{args.seed}", out, seed=args.seed)
    store = ArtifactStore(out / "board.partial.jsonl")
    if args.arm == "A3":
        from arms.collective import Collective
        runner = Collective(client, store)
    else:
        from arms.single_agent import SingleAgent
        runner = SingleAgent(client)

    todo = [c for c in codes if not (genes_dir / f"{c}.json").exists()]
    print(f"{args.arm} seed {args.seed}: {len(codes) - len(todo)} genes already done, {len(todo)} to run")

    def one(code):
        t0 = time.time()
        arts = runner.run(code)
        rec = {"gene_code": code, "score": scoring.score(arts),
               "calls": client.budget.used[(client.arm, code)], "seconds": round(time.time() - t0, 1),
               "artifacts": [asdict(a) for a in arts]}
        (genes_dir / f"{code}.json").write_text(json.dumps(rec, indent=1))   # checkpoint
        return rec

    failed = []
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(one, c): c for c in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            code = futs[fut]
            try:
                rec = fut.result()
                n_err = sum(a["artifact_type"] == "error" for a in rec["artifacts"])
                print(f"  [{i}/{len(todo)}] {code} score={rec['score']:+.3f} calls={rec['calls']} "
                      f"{rec['seconds']}s{' errors=' + str(n_err) if n_err else ''}", flush=True)
            except Exception as e:   # R10: loud, and the gene stays un-checkpointed for a rerun
                failed.append(code)
                print(f"  [{i}/{len(todo)}] {code} FAILED: {e}", flush=True)

    recs = [json.loads((genes_dir / f"{c}.json").read_text()) for c in codes if (genes_dir / f"{c}.json").exists()]
    with (out / "board.jsonl").open("w") as f:
        for r in sorted(recs, key=lambda r: r["gene_code"]):
            for a in r["artifacts"]:
                f.write(json.dumps(a, sort_keys=True) + "\n")
    with (out / "scores.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gene_code", "score", "calls"])
        for r in sorted(recs, key=lambda r: r["gene_code"]):
            w.writerow([r["gene_code"], r["score"], r["calls"]])
    print(f"wrote {out}/scores.csv ({len(recs)}/{len(codes)} genes)" + (f"; FAILED: {failed}" if failed else ""))
    sys.exit(1 if failed or len(recs) < len(codes) else 0)


if __name__ == "__main__":
    main()

"""T2: A2-constrained, a centralized arm that must choose. Post-freeze extension, 1 seed, not pre-registered.

  python -m exploratory.A2_constrained.run [--limit N]

Identical to exploratory/A2 except the planner must return EXACTLY 2 of the 4 specialists. It sees only the
gene code and one line per specialist, never evidence. The two chosen specialists run exactly as in A3 round 0
(same prompts, views, parser). No needs, no skeptic, no revisions. Unchanged scoring.py.
If the planner returns more than 2 valid names, the first 2 are used; fewer than 2 is recorded as an invalid
plan and only the valid names run. Both cases are flagged in plans.json.
Writes only under exploratory/A2_constrained/.
"""
import argparse, csv, json, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import config
import scoring
from agents import EVIDENCE_AGENT_CLASSES
from board.artifact import ArtifactStore
from exploratory.A2.run_a2 import SPECIALISTS
from llm.client import LLMClient
from llm.guards import BudgetExceeded

HERE = Path(__file__).resolve().parent
PROMPT = """You are the PLANNER of a drug-target evaluation team. You decide which specialists to consult for one
anonymised human gene. You never see any evidence yourself; each specialist reports a verdict from its own data.

Gene: {gene_code}

Specialists available:
{menu}

The question: would inhibiting this gene be a safe, effective therapy for cardiometabolic or liver disease?
You may consult EXACTLY 2 of these 4 specialists. Choose the 2 whose evidence you expect to matter most for this gene."""
SCHEMA = json.dumps({"specialists": ["exactly 2 names from the list above"], "reason": "one line, at most 200 characters"},
                    indent=1)


def plan(client, gene_code):
    menu = "\n".join(f"- {k}: {v}" for k, v in SPECIALISTS.items())
    parsed, err = client.complete_json(agent="planner", gene_code=gene_code,
                                       prompt=PROMPT.format(gene_code=gene_code, menu=menu), schema=SCHEMA,
                                       list_key="specialists")
    if parsed is None:
        return [], f"planner error: {err}", "error"
    valid = []
    for s in parsed.get("specialists") or []:
        s = str(s).strip().lower()
        if s in SPECIALISTS and s not in valid:
            valid.append(s)
    status = "ok" if len(valid) == 2 else ("truncated" if len(valid) > 2 else "invalid")
    return valid[:2], str(parsed.get("reason", ""))[:200], status


def run_gene(client, agents, gene_code):
    t0 = time.time()
    chosen, reason, status = plan(client, gene_code)
    store = ArtifactStore(HERE / "boards" / f"{gene_code}.jsonl")
    if store.path.exists():
        store.path.unlink()
    arts = []
    if chosen:
        def one(name):
            try:
                return agents[name].evidence(gene_code, 0)     # exactly A3 round 0
            except BudgetExceeded:
                return None
        with ThreadPoolExecutor(len(chosen)) as pool:
            for a in pool.map(one, chosen):
                if a is not None:
                    store.append(a)
                    arts.append(a)
    return {"gene_code": gene_code, "plan": chosen, "plan_status": status, "reason": reason,
            "score": scoring.score(arts), "calls": client.budget.used[(client.arm, gene_code)],
            "seconds": round(time.time() - t0, 1), "errors": sum(a.artifact_type == "error" for a in arts)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    config.LLM_BACKEND = "vertex"
    client = LLMClient("A2c_s1", HERE, seed=1)
    agents = {n: cls(client) for n, cls in EVIDENCE_AGENT_CLASSES.items()}
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        codes = [r["gene_code"] for r in csv.DictReader(f)][:args.limit]
    (HERE / "meta.json").write_text(json.dumps({
        "arm": "A2_constrained", "seed": 1, "model": f"google/{config.LLM_MODEL}", "backend": "vertex",
        "temperature": config.TEMPERATURE, "reasoning_effort": config.LLM_REASONING_EFFORT,
        "max_calls_per_gene": config.MAX_LLM_CALLS_PER_GENE, "specialists": list(SPECIALISTS), "pick": 2,
        "label": "post-freeze extension, 1 seed, not pre-registered"}, indent=1))
    recs = []
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(run_gene, client, agents, c): c for c in codes}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            recs.append(r)
            print(f"  [{i}/{len(codes)}] {r['gene_code']} plan={r['plan']} ({r['plan_status']}) "
                  f"score={r['score']:+.3f} calls={r['calls']}", flush=True)
    recs.sort(key=lambda r: r["gene_code"])
    (HERE / "plans.json").write_text(json.dumps(recs, indent=1))
    with (HERE / "scores.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gene_code", "score", "calls"])
        for r in recs:
            w.writerow([r["gene_code"], r["score"], r["calls"]])
    pairs = Counter(" + ".join(sorted(r["plan"])) for r in recs)
    print(f"wrote {HERE}/scores.csv; pairs: {dict(pairs)}; statuses: {dict(Counter(r['plan_status'] for r in recs))}")


if __name__ == "__main__":
    main()

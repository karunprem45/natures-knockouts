"""P1-1: A2, the centralized arm. Post-freeze extension, 1 seed, not pre-registered.

  python -m exploratory.A2.run_a2 [--limit N]

Everything is held constant except WHO DECIDES THE TRAJECTORY:
  - same model, same 10-call-per-gene cap, same LLM client and guards
  - same specialist prompts, views and parser: each chosen specialist runs exactly as in A3 round 0
  - same scoring.py, unchanged
A planner LLM sees only the gene code and a one-line description of each specialist (never any evidence)
and returns an ordered list of specialists to invoke. No needs index, no skeptic, no revisions.

The planner chooses among the four specialists that run in A3 round 0. The Variant agent is excluded because
it has no round-0 mode (it only answers needs), so it could not run "exactly as in A3 round 0".
Writes only under exploratory/A2/.
"""
import argparse, csv, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import config
import scoring
from agents import EVIDENCE_AGENT_CLASSES
from board.artifact import ArtifactStore
from llm.client import LLMClient
from llm.guards import BudgetExceeded

HERE = Path(__file__).resolve().parent
SPECIALISTS = {
    "burden": "rare-variant gene-burden results for in-scope cardiometabolic and liver traits",
    "gwas": "common-variant GWAS credible sets for in-scope traits",
    "tolerance": "population loss-of-function constraint (LOEUF, pLI) and cell-line essentiality",
    "safety": "associations with traits outside the therapeutic scope",
}
PLANNER_PROMPT = """You are the PLANNER of a drug-target evaluation team. You decide which specialists to consult for one
anonymised human gene. You never see any evidence yourself; each specialist reports a verdict from its own data.

Gene: {gene_code}

Specialists available:
{menu}

The question: would inhibiting this gene be a safe, effective therapy for cardiometabolic or liver disease?
Choose an ordered list of 1 to {n} specialists to consult, most important first. Consult only those you judge necessary."""
PLANNER_SCHEMA = json.dumps({"specialists": ["names from the list above, most important first"],
                             "rationale": "at most 200 characters"}, indent=1)


def plan(client, gene_code):
    menu = "\n".join(f"- {k}: {v}" for k, v in SPECIALISTS.items())
    parsed, err = client.complete_json(agent="planner", gene_code=gene_code,
                                       prompt=PLANNER_PROMPT.format(gene_code=gene_code, menu=menu, n=len(SPECIALISTS)),
                                       schema=PLANNER_SCHEMA, list_key="specialists")
    if parsed is None:
        return [], f"planner error: {err}"
    chosen = []
    for s in parsed.get("specialists") or []:
        s = str(s).strip().lower()
        if s in SPECIALISTS and s not in chosen:
            chosen.append(s)
    return chosen, str(parsed.get("rationale", ""))[:200]


def run_gene(client, agents, gene_code):
    t0 = time.time()
    chosen, why = plan(client, gene_code)
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
    return {"gene_code": gene_code, "plan": chosen, "planner_rationale": why, "score": scoring.score(arts),
            "calls": client.budget.used[(client.arm, gene_code)], "seconds": round(time.time() - t0, 1),
            "errors": sum(a.artifact_type == "error" for a in arts)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    config.LLM_BACKEND = "vertex"
    client = LLMClient("A2_s1", HERE, seed=1)
    agents = {n: cls(client) for n, cls in EVIDENCE_AGENT_CLASSES.items()}
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        codes = [r["gene_code"] for r in csv.DictReader(f)][:args.limit]
    (HERE / "meta.json").write_text(json.dumps({
        "arm": "A2", "seed": 1, "model": f"google/{config.LLM_MODEL}", "backend": "vertex",
        "temperature": config.TEMPERATURE, "reasoning_effort": config.LLM_REASONING_EFFORT,
        "max_calls_per_gene": config.MAX_LLM_CALLS_PER_GENE, "specialists": list(SPECIALISTS),
        "label": "post-freeze extension, 1 seed, not pre-registered"}, indent=1))
    recs = []
    with ThreadPoolExecutor(args.workers) as pool:
        futs = {pool.submit(run_gene, client, agents, c): c for c in codes}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            recs.append(r)
            print(f"  [{i}/{len(codes)}] {r['gene_code']} plan={r['plan']} score={r['score']:+.3f} "
                  f"calls={r['calls']}{' errors=' + str(r['errors']) if r['errors'] else ''}", flush=True)
    recs.sort(key=lambda r: r["gene_code"])
    (HERE / "plans.json").write_text(json.dumps(recs, indent=1))
    with (HERE / "scores.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["gene_code", "score", "calls"])
        for r in recs:
            w.writerow([r["gene_code"], r["score"], r["calls"]])
    print(f"wrote {HERE}/scores.csv ({len(recs)} genes, {sum(r['errors'] for r in recs)} error artifacts)")


if __name__ == "__main__":
    main()

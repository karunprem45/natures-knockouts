"""Phase 4 gate: 10 genes through the loop; a need fulfilled by a DIFFERENT agent; a challenge that
moves a score."""
import csv, json, shutil, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import config
import scoring
from agents import EVIDENCE_AGENT_CLASSES, SkepticAgent
from board.artifact import ArtifactStore
from board.loop import run_gene
from llm.client import LLMClient

N_GENES = 10


def main():
    out = config.RUNS_DIR / "phase4_gate"
    shutil.rmtree(out, ignore_errors=True)
    client = LLMClient("gate4", out, seed=1)
    store = ArtifactStore(out / "board.jsonl")
    agents = {n: cls(client) for n, cls in EVIDENCE_AGENT_CLASSES.items()}
    skeptic = SkepticAgent(client)
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        codes = [r["gene_code"] for r in csv.DictReader(f)][:N_GENES]
    with ThreadPoolExecutor(5) as pool:
        boards = dict(zip(codes, pool.map(lambda c: run_gene(c, agents, skeptic, client, store), codes)))

    cross, moved = 0, 0
    for code, arts in boards.items():
        by_id = {a.artifact_id: a for a in arts}
        fulfil = [a for a in arts if a.artifact_type == "fulfillment"]
        cross_here = [f"{by_id[f.parent_artifact_ids[0]].producer_agent}->{f.producer_agent}" for f in fulfil
                      if by_id[f.parent_artifact_ids[0]].producer_agent != f.producer_agent]
        cross += len(cross_here)
        full = scoring.score(arts)
        no_challenge = scoring.score([a for a in arts if a.artifact_type != "challenge"])
        round0 = scoring.score([a for a in arts if a.round == 0])
        moved += abs(full - no_challenge) > 1e-9
        kinds = Counter(a.artifact_type for a in arts)
        print(f"  {code}: {dict(kinds)} calls={client.budget.used[(client.arm, code)]} "
              f"score={full:+.3f} (no-skeptic {no_challenge:+.3f}, round0-only {round0:+.3f}) needs answered: {cross_here}")
    log = [json.loads(l) for l in (out / "llm_log.jsonl").read_text().splitlines()]
    calls = [l for l in log if "prompt_tokens" in l]
    errors = sum(1 for arts in boards.values() for a in arts if a.artifact_type == "error")
    print(f"\n{len(codes)} genes, {len(calls)} calls, {errors} error artifacts, cost ${sum(l['cost_usd'] for l in calls):.3f}, "
          f"max calls/gene {max(client.budget.used.values())}")
    print(f"cross-agent fulfilments: {cross}; genes where a challenge moved the score: {moved}")
    ok = cross >= 1 and moved >= 1 and max(client.budget.used.values()) <= config.MAX_LLM_CALLS_PER_GENE
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

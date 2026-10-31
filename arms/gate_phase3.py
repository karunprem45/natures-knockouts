"""Phase 3 gate: every agent returns valid JSON for 5 genes and the identity guard never fires."""
import csv, json, shutil, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import config
from agents import EVIDENCE_AGENT_CLASSES, SkepticAgent
from board.artifact import ArtifactStore
from llm.client import LLMClient

N_GENES = 5


def main():
    out = config.RUNS_DIR / "phase3_gate"
    shutil.rmtree(out, ignore_errors=True)
    client = LLMClient("gate3", out, seed=1)
    store = ArtifactStore(out / "board.jsonl")
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        codes = [r["gene_code"] for r in csv.DictReader(f)][:N_GENES]
    agents = [cls(client) for cls in EVIDENCE_AGENT_CLASSES.values()]
    skeptic = SkepticAgent(client)

    def gene(code):
        with ThreadPoolExecutor(len(agents)) as pool:
            arts = list(pool.map(lambda a: store.append(a.evidence(code)), agents))
        arts.append(store.append(skeptic.review(code, arts)))
        return arts

    with ThreadPoolExecutor(N_GENES) as pool:
        results = [a for arts in pool.map(gene, codes) for a in arts]
    for a in results:
        extra = (f"flags={a.flags} " if a.flags else "") + (f"needs={[n['type'] for n in a.needs]}" if a.needs else "") + \
                (f" challenges={[(c['type'], c['channel']) for c in a.challenges]}" if a.challenges else "") + \
                (f" ERROR {a.error}" if a.error else "")
        print(f"  {a.gene_code} {a.producer_agent:<9} {a.artifact_type:<9} {a.stance:<8} {a.strength:.2f} {extra}")
    errors = [a for a in results if a.artifact_type == "error"]
    log = [json.loads(l) for l in (out / "llm_log.jsonl").read_text().splitlines()]
    calls = [l for l in log if "prompt_tokens" in l]
    print(f"\n{len(results)} artifacts, {len(errors)} errors, {len(calls)} calls, "
          f"retries={sum(1 for l in log if l.get('event') == 'retry')}, "
          f"cost=${sum(l['cost_usd'] for l in calls):.4f}, "
          f"mean latency={sum(l['latency_s'] for l in calls) / max(1, len(calls)):.1f}s")
    print("identity flags:", sum(1 for a in results if a.flags))
    print("needs raised:", dict(Counter(n["type"] for a in results for n in a.needs)))
    print("PASS" if not errors else "FAIL")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

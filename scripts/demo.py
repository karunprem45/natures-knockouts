"""Two-minute demo: replay one gene's board round by round from the frozen A3 results.

  python -m scripts.demo                 # Gene_01, seed 1, paced for talking over
  python -m scripts.demo Gene_05 --fast  # no pauses
  python -m scripts.demo Gene_01 --live  # run the loop fresh (10 Gemini calls, about 40 s)

The replay makes no API calls, so it cannot fail on stage. The score at the end is recomputed
by scoring.py from the artifacts on screen.
"""
import argparse, json, sys, time
from pathlib import Path
import config
import scoring
from board.artifact import Artifact

BOARD = config.ROOT / "frozen_results" / "runs" / "A3_s1" / "board.jsonl"
C = {"burden": "\033[38;5;33m", "gwas": "\033[38;5;208m", "tolerance": "\033[38;5;36m",
     "safety": "\033[38;5;178m", "skeptic": "\033[38;5;169m"}
DIM, BOLD, END = "\033[2m", "\033[1m", "\033[0m"


def who(agent):
    return f"{C.get(agent, '')}{agent:<9}{END}"


def verdict(a):
    return f"{a.stance:<8} {a.strength:.2f}"


def load(gene, live):
    if not live:
        arts = [Artifact.from_dict(json.loads(l)) for l in BOARD.read_text().splitlines()]
        arts = [a for a in arts if a.gene_code == gene]
        if not arts:
            sys.exit(f"{gene} not on the frozen board")
        return arts
    from arms.collective import Collective
    from board.artifact import ArtifactStore
    from llm.client import LLMClient
    out = config.RUNS_DIR / "demo_live"
    client = LLMClient("demo", out)
    return Collective(client, ArtifactStore(out / "board.jsonl")).run(gene)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("gene", nargs="?", default="Gene_01")
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args(argv)
    pause = (lambda s: None) if args.fast else time.sleep
    arts = load(args.gene, args.live)
    by_id = {a.artifact_id: a for a in arts}

    print(f"\n{BOLD}{args.gene}{END}  identity hidden from every agent; each reads only its own view\n")
    pause(1.5)

    print(f"{BOLD}Round 0 · independent evidence{END}")
    for a in [a for a in arts if a.round == 0]:
        print(f"  {who(a.producer_agent)} {verdict(a)}  {DIM}{a.rationale}{END}")
        for n in a.needs:
            print(f"  {' ' * 9}   {DIM}↳ broadcasts need{END} {n['type']}: {n['query'][:90]}")
        pause(1.2)

    fulfil = [a for a in arts if a.artifact_type == "fulfillment"]
    print(f"\n{BOLD}Round 1 · agents pick up each other's needs (no planner){END}")
    for f in fulfil:
        asker = by_id[f.parent_artifact_ids[0]].producer_agent
        pressure = next((x.split(":")[1] for x in f.flags if x.startswith("pressure:")), "?")
        print(f"  {who(asker)} asked → {who(f.producer_agent)} answered  {DIM}pressure {pressure}{END}")
        print(f"  {' ' * 9}   {DIM}{f.rationale}{END}")
        pause(1.5)

    print(f"\n{BOLD}Round 2 · skeptic reviews every verdict{END}")
    for c in [a for a in arts if a.artifact_type == "challenge"]:
        for ch in c.challenges:
            print(f"  {who('skeptic')} {ch['type']:<19} on {who(ch['channel'])} {DIM}{ch['rationale']}{END}")
            pause(0.8)
    for r in [a for a in arts if a.artifact_type == "revision"]:
        old = by_id[r.parent_artifact_ids[0]]
        print(f"  {who(r.producer_agent)} revises  {verdict(old)} → {verdict(r)}  {DIM}{r.rationale}{END}")
        pause(1.2)

    total, parts = scoring.score(arts, return_breakdown=True)
    discounted = scoring.challenged_channels(arts)
    print(f"\n{BOLD}Score · pure Python, no LLM{END}")
    for ch, v in parts.items():
        if ch in config.ACTIVE_EVIDENCE_AGENTS:
            note = "  ×0.5 skeptic discount" if ch in discounted else ""
            print(f"  {who(ch)} {v:+.3f}{DIM}{note}{END}")
    print(f"  {BOLD}total     {total:+.3f}{END}   (round 0 alone: {scoring.score([a for a in arts if a.round == 0]):+.3f})")
    print(f"\n{DIM}{len(arts)} artifacts, each with a UUID, content hash and parent links: frozen_results/figures/3_provenance_dag.png{END}\n")


if __name__ == "__main__":
    main()

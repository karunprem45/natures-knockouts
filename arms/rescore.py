"""Ablations as re-scoring passes over a saved A3 board — ZERO extra LLM calls.

  A3_noskeptic   drop challenge artifacts
  A3_no<agent>   drop that agent's artifacts (and challenges naming its channel)
  A3_isolated    round-0 artifacts only (no needs, no skeptic, no revisions)
"""
import csv, json, sys
import config
import scoring
from board.artifact import Artifact


def load_boards(run_dir):
    boards = {}
    for p in sorted((run_dir / "genes").glob("Gene_*.json")):
        rec = json.loads(p.read_text())
        boards[rec["gene_code"]] = [Artifact.from_dict(a) for a in rec["artifacts"]]
    return boards


def drop_agent(arts, agent):
    keep = []
    for a in arts:
        if a.producer_agent == agent:
            continue
        if a.artifact_type == "challenge":
            a = Artifact.from_dict({**a.__dict__, "challenges": [c for c in a.challenges if c["channel"] != agent],
                                    "content_hash": ""})
        keep.append(a)
    return keep


ABLATIONS = {
    "noskeptic": lambda arts: [a for a in arts if a.artifact_type != "challenge"],
    "isolated": lambda arts: [a for a in arts if a.round == 0],
    **{f"no{ag}": (lambda ag: lambda arts: drop_agent(arts, ag))(ag) for ag in config.ACTIVE_EVIDENCE_AGENTS},
}


def main(argv):
    seeds = [int(s) for s in argv] or list(range(1, config.N_SEEDS + 1))
    for seed in seeds:
        src = config.RUNS_DIR / f"A3_s{seed}"
        boards = load_boards(src)
        if not boards:
            print(f"no A3 board for seed {seed}, skipped")
            continue
        for name, fn in ABLATIONS.items():
            out = config.RUNS_DIR / f"A3_{name}_s{seed}"
            out.mkdir(parents=True, exist_ok=True)
            with (out / "scores.csv").open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["gene_code", "score", "calls"])
                for code, arts in sorted(boards.items()):
                    w.writerow([code, scoring.score(fn(arts)), 0])
            print(f"  A3_{name}_s{seed}: {len(boards)} genes re-scored, 0 LLM calls")


if __name__ == "__main__":
    main(sys.argv[1:])

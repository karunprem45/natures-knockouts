"""P1-2: offline reproduction check. No API keys, no network, writes nothing.

  python -m exploratory.scripts.verify_frozen

1. Verifies every SHA-256 in frozen_results/SHA256SUMS.
2. Recomputes AUROC for every frozen arm from its score file and compares with frozen_results/arms_table.md.
3. Re-scores the A3 round-0 ablation from the frozen A3 boards with the unchanged scoring.py and compares
   with the frozen A3_isolated scores.
Labels come from data/labels/panel_labels.csv if present, else reproduce/panel_labels.csv (published after
results-final so a clean clone can recompute the table; blindness only mattered while arms ran).
"""
import hashlib, json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
import config
import scoring
from arms.rescore import ABLATIONS
from board.artifact import Artifact
from eval import metrics as m

ROOT = config.ROOT
FR = ROOT / "frozen_results"


def labels():
    for p in (config.LABELS_DIR / "panel_labels.csv", ROOT / "reproduce" / "panel_labels.csv"):
        if p.exists():
            return pd.read_csv(p).set_index("gene_code").sort_index(), p
    sys.exit("no labels: run `make data panel` or restore reproduce/panel_labels.csv")


def main():
    ok = True
    lines = (FR / "SHA256SUMS").read_text().splitlines()
    bad = [l.split("  ", 1)[1] for l in lines
           if hashlib.sha256((FR / l.split("  ", 1)[1]).read_bytes()).hexdigest() != l.split("  ", 1)[0]]
    print(f"1. SHA-256: {len(lines) - len(bad)}/{len(lines)} files match" + (f"; MISMATCH: {bad}" if bad else ""))
    ok &= not bad

    lab, src = labels()
    y = lab["label"].values
    table = (FR / "arms_table.md").read_text()
    frozen_auroc = {r.group(1): float(r.group(2)) for r in re.finditer(r"^\| (\S+) \| [^|]+ \| (\d\.\d{3}) ", table, re.M)}
    mismatches = []
    for arm, want in sorted(frozen_auroc.items()):
        dirs = [FR / "runs" / arm] if (FR / "runs" / arm).exists() else sorted((FR / "runs").glob(f"{arm}_s[0-9]"))
        sets = [pd.read_csv(d / "scores.csv").set_index("gene_code")["score"].reindex(lab.index).values for d in dirs]
        got = float(np.mean([m.auroc(y, s) for s in sets]))
        if abs(got - want) > 0.0005:
            mismatches.append(f"{arm}: frozen {want:.3f}, recomputed {got:.3f}")
    print(f"2. Arms table: {len(frozen_auroc) - len(mismatches)}/{len(frozen_auroc)} arms reproduce their AUROC "
          f"(labels from {src.relative_to(ROOT)})" + (f"; MISMATCH: {mismatches}" if mismatches else ""))
    ok &= not mismatches

    worst = 0.0
    for s in (1, 2):
        arts = [Artifact.from_dict(json.loads(l)) for l in (FR / "runs" / f"A3_s{s}" / "board.jsonl").read_text().splitlines()]
        boards = {}
        for a in arts:
            boards.setdefault(a.gene_code, []).append(a)
        mine = pd.Series({c: scoring.score(ABLATIONS["isolated"](b)) for c, b in boards.items()})
        frozen = pd.read_csv(FR / "runs" / f"A3_isolated_s{s}" / "scores.csv").set_index("gene_code")["score"]
        worst = max(worst, float((mine.reindex(frozen.index) - frozen).abs().max()))
    print(f"3. Re-scored A3 round 0 from frozen boards: max difference from frozen scores {worst:.2e}")
    ok &= worst < 1e-9
    print("ALL CHECKS PASS" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

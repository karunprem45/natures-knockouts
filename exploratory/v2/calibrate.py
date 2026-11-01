"""P2-1 step 1: fit per-challenge-type skeptic discounts on panel 1 (frozen A3 boards, both seeds).

  python -m exploratory.v2.calibrate     -> exploratory/v2/calibration.json

Rate = share of gene-runs on which a challenge type fired at least once, split by label.
One formula for every type, no hand-picking:
    multiplier_t = 1 - 0.5 * max(0, (rate_neg - rate_pos) / rate_neg)     (1.0 if rate_neg == 0)
A type that fires only on negatives keeps the original 0.5; one that fires equally on both is ignored (1.0);
one that fires more on positives is ignored. Panel 1 is already used, so fitting on it is safe; the
multipliers are evaluated only on panel 2.
"""
import json
from collections import defaultdict
import pandas as pd
import config

ROOT = config.ROOT
OUT = ROOT / "exploratory" / "v2" / "calibration.json"


def multiplier(rate_pos, rate_neg):
    return 1.0 if rate_neg == 0 else 1.0 - 0.5 * max(0.0, (rate_neg - rate_pos) / rate_neg)


def main():
    lab = pd.read_csv(config.LABELS_DIR / "panel_labels.csv").set_index("gene_code")["label"]
    fired, n = defaultdict(lambda: {"pos": 0, "neg": 0}), {"pos": 0, "neg": 0}
    for s in (1, 2):
        boards = defaultdict(list)
        for line in (ROOT / "frozen_results" / "runs" / f"A3_s{s}" / "board.jsonl").read_text().splitlines():
            a = json.loads(line)
            boards[a["gene_code"]].append(a)
        for g, arts in boards.items():
            k = "pos" if int(lab[g]) == 1 else "neg"
            n[k] += 1
            for t in {c["type"] for a in arts if a["artifact_type"] == "challenge" for c in a["challenges"]}:
                fired[t][k] += 1
    out = {"source": "frozen_results/runs/A3_s1, A3_s2 (panel 1)", "gene_runs": n,
           "formula": "multiplier_t = 1 - 0.5 * max(0, (rate_neg - rate_pos) / rate_neg); 1.0 if rate_neg == 0",
           "channel_rule": "a challenged channel takes the minimum multiplier over the types that name it",
           "types": {}}
    for t in sorted(set(config.SKEPTIC_CHALLENGES) | set(fired)):
        rp, rn = fired[t]["pos"] / n["pos"], fired[t]["neg"] / n["neg"]
        out["types"][t] = {"rate_pos": round(rp, 4), "rate_neg": round(rn, 4), "multiplier": round(multiplier(rp, rn), 4)}
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(out["types"], indent=1))


if __name__ == "__main__":
    main()

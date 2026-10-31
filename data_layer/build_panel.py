"""Phase 1d.4: sample the blind panel.

frozen/panel.csv          gene_code, ensembl_id, n_evidence_rows   (no label, no symbol)
data/labels/panel_labels.csv  gene_code, label, symbol
Pass --fallback for the 6:30 PM gate size (8 + 16).
"""
import csv, json, random, sys
import config
from data_layer.common import load_raw


def main(argv):
    n_pos, n_neg = ((config.N_POSITIVES_FALLBACK, config.N_NEGATIVES_FALLBACK) if "--fallback" in argv
                    else (config.N_POSITIVES, config.N_NEGATIVES))
    cand = json.loads((config.LABELS_DIR / "candidates.json").read_text())
    rng = random.Random(config.SEED)
    pos = cand["positives"][:n_pos]
    pool = sorted(cand["negatives_eligible"], key=lambda g: g["ensembl_id"])
    if len(pos) < n_pos or len(pool) < n_neg:
        sys.exit(f"not enough genes: {len(pos)}/{n_pos} positives, {len(pool)}/{n_neg} negatives")
    neg = rng.sample(pool, n_neg)
    genes = [dict(g, label=1) for g in pos] + [dict(g, label=0) for g in neg]
    rng.shuffle(genes)  # gene codes carry no information about the label

    config.FROZEN_DIR.mkdir(exist_ok=True)
    with (config.FROZEN_DIR / "panel.csv").open("w", newline="") as fp, \
         (config.LABELS_DIR / "panel_labels.csv").open("w", newline="") as fl:
        wp, wl = csv.writer(fp), csv.writer(fl)
        wp.writerow(["gene_code", "ensembl_id", "n_evidence_rows"])
        wl.writerow(["gene_code", "label", "symbol"])
        for i, g in enumerate(genes, 1):
            code = f"Gene_{i:02d}"
            raw = load_raw(g["ensembl_id"])
            wp.writerow([code, g["ensembl_id"], len(raw["burden"]) + len(raw["gwas"])])
            wl.writerow([code, g["label"], g["symbol"]])
    print(f"panel: {len(pos)} positives + {len(neg)} negatives -> frozen/panel.csv")


if __name__ == "__main__":
    main(sys.argv[1:])

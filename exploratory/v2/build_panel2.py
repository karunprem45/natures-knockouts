"""P2-1 step 3: build panel 2 by the rule in prereg_v2.md (after the prereg-v2 tag).

  python -m exploratory.v2.build_panel2

Same 12 positives; 28 negatives sampled with random.Random(20261101) from the eligible negatives (sorted by
Ensembl ID) excluding the 28 panel-1 negatives; the 40 shuffled with the same generator and coded
Gene_41..Gene_80. Views are built by the unchanged data_layer.build_views code into data/views_v2/.
Writes exploratory/v2/panel2.csv (no labels, no symbols) and data/labels/panel2_labels.csv.
"""
import csv, json, random, tempfile
from pathlib import Path
import config
from data_layer import build_views
from data_layer.common import load_raw

ROOT = config.ROOT
SEED2 = 20261101
PANEL2 = ROOT / "exploratory" / "v2" / "panel2.csv"
LABELS2 = config.LABELS_DIR / "panel2_labels.csv"
VIEWS2 = config.DATA_DIR / "views_v2"


def main():
    cand = json.loads((config.LABELS_DIR / "candidates.json").read_text())
    with (config.LABELS_DIR / "panel_labels.csv").open() as f:
        panel1_neg = {r["symbol"] for r in csv.DictReader(f) if r["label"] == "0"}
    rng = random.Random(SEED2)
    pos = cand["positives"]
    pool = sorted((g for g in cand["negatives_eligible"] if g["symbol"] not in panel1_neg), key=lambda g: g["ensembl_id"])
    neg = rng.sample(pool, 28)
    genes = [dict(g, label=1) for g in pos] + [dict(g, label=0) for g in neg]
    rng.shuffle(genes)
    with PANEL2.open("w", newline="") as fp, LABELS2.open("w", newline="") as fl:
        wp, wl = csv.writer(fp), csv.writer(fl)
        wp.writerow(["gene_code", "ensembl_id", "n_evidence_rows"])
        wl.writerow(["gene_code", "label", "symbol"])
        for i, g in enumerate(genes, 41):
            raw = load_raw(g["ensembl_id"])
            wp.writerow([f"Gene_{i:02d}", g["ensembl_id"], len(raw["burden"]) + len(raw["gwas"])])
            wl.writerow([f"Gene_{i:02d}", g["label"], g["symbol"]])
    print(f"panel 2: {len(pos)} positives + {len(neg)} fresh negatives (from {len(pool)} eligible, panel-1 negatives excluded)")
    overlap = panel1_neg & {g["symbol"] for g in neg}
    assert not overlap, overlap

    # build views with the unchanged panel-1 code, pointed at panel 2 and views_v2
    saved = (config.FROZEN_DIR, config.VIEWS_DIR, build_views.VIEW_LOG)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "panel.csv").write_text(PANEL2.read_text())
        config.FROZEN_DIR, config.VIEWS_DIR = Path(tmp), VIEWS2
        build_views.VIEW_LOG = VIEWS2 / "build_log.md"
        try:
            build_views.main()
        finally:
            config.FROZEN_DIR, config.VIEWS_DIR, build_views.VIEW_LOG = saved
    print(f"views -> {VIEWS2}")


if __name__ == "__main__":
    main()

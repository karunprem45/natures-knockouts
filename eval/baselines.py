"""Phase 2 gate: AUROC table for S1-S4 with bootstrap CIs. The only Phase 2 code that reads labels."""
import pandas as pd
import config
from eval import metrics as m

ARMS = ["S1", "S2", "S3", "S4"]


def load(arm, labels):
    s = pd.read_csv(config.RUNS_DIR / arm / "scores.csv").set_index("gene_code")["score"]
    return s.reindex(labels.index)


def main():
    labels = pd.read_csv(config.LABELS_DIR / "panel_labels.csv").set_index("gene_code").sort_index()["label"]
    y = labels.values
    lines = ["| Arm | AUROC (95% CI) | AUPRC (95% CI) | P@12 | perm p | Δ AUROC vs S4 (95% CI) |",
             "| --- | --- | --- | --- | --- | --- |"]
    s4 = load("S4", labels).values
    for arm in ARMS:
        s = load(arm, labels).values
        a, alo, ahi = m.bootstrap_ci(m.auroc, y, s)
        p, plo, phi = m.bootstrap_ci(m.auprc, y, s)
        _, perm_p = m.permutation_null(m.auroc, y, s)
        if arm == "S4":
            delta = "—"
        else:
            d, dlo, dhi = m.paired_delta(m.auroc, y, s, s4)
            delta = f"{d:+.3f} ({dlo:+.3f}, {dhi:+.3f})"
        lines.append(f"| {arm} | {a:.3f} ({alo:.3f}–{ahi:.3f}) | {p:.3f} ({plo:.3f}–{phi:.3f}) | "
                     f"{m.precision_at_k(y, s):.2f} | {perm_p:.3f} | {delta} |")
    table = "\n".join(lines)
    out = config.RUNS_DIR / "baselines_table.md"
    out.write_text(f"# Scripted baselines\n\n{len(y)} genes, {int(y.sum())} positives; "
                   f"chance AUPRC = {y.mean():.3f}\n\n{table}\n")
    print(table)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

"""Exploratory comparisons run AFTER results-final. Never part of the pre-registered headline.

  python -m eval.explore

For each exploratory run under runs/explore/<name>_s<seed>/, compares it with the frozen pre-registered
arm it extends (A3 + Variant vs A3; other-backend A1/A3 vs each other) on the same 40 genes, with the
same paired bootstrap. Writes frozen_results/exploratory/explore_table.md.
"""
import json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import config
from eval import metrics as m
from eval.report import labels, score_sets

EXPLORE = config.RUNS_DIR / "explore"
OUT = config.ROOT / "frozen_results" / "exploratory"


def run_sets(name, index):
    dirs = sorted(d for d in EXPLORE.glob(f"{name}_s*") if (d / "scores.csv").exists())
    sets = []
    for d in dirs:
        s = pd.read_csv(d / "scores.csv").set_index("gene_code")["score"].reindex(index)
        if s.isna().any():
            return [], dirs
        sets.append(s.values.astype(float))
    return sets, dirs


def variant_usage(dirs):
    asked, answered, pct, errors = 0, 0, [], 0
    for d in dirs:
        for f in (d / "genes").glob("Gene_*.json"):
            arts = json.loads(f.read_text())["artifacts"]
            asked += sum(n["type"] == "variant_check" for a in arts if a["round"] == 0 for n in a["needs"])
            for a in arts:
                if a["producer_agent"] == "variant" and a["artifact_type"] == "fulfillment":
                    answered += 1
                    errors += any(x == "evo2_error" for x in a["flags"])
                    pct += [float(x.split(":")[1]) for x in a["flags"] if x.startswith("evo2_percentile:")]
    return {"variant_checks_asked": asked, "variant_answers": answered, "evo2_errors": errors,
            "median_site_percentile": round(float(np.median(pct)), 1) if pct else None}


def fmt(t):
    return f"{t[0]:.3f} ({t[1]:.3f}–{t[2]:.3f})"


def fmtd(t):
    return f"{t[0]:+.3f} ({t[1]:+.3f}, {t[2]:+.3f})"


def main():
    lab = labels()
    y = lab["label"].values
    a3, _ = score_sets("A3", lab.index)
    a1, _ = score_sets("A1", lab.index)
    rows, notes = [], []

    var_sets, var_dirs = run_sets("A3_variant", lab.index)
    if var_sets:
        seeds = [int(d.name.rsplit("_s", 1)[1]) for d in var_dirs]
        base = [a3[s - 1] for s in seeds]        # same seeds as the variant runs: a paired comparison
        au = m.bootstrap_ci_seeds(m.auroc, y, var_sets)
        d_a3 = m.paired_delta_seeds(m.auroc, y, var_sets, base)
        d_a1 = m.paired_delta_seeds(m.auroc, y, var_sets, [a1[s - 1] for s in seeds])
        rows.append(f"| A3 + Variant (Evo 2) | Gemini 3 Flash + NVIDIA Evo 2 40B | {len(seeds)} | {fmt(au)} | "
                    f"{fmtd(d_a3)} vs A3 | {fmtd(d_a1)} vs A1 |")
        u = variant_usage(var_dirs)
        notes.append(f"Variant agent: {u['variant_checks_asked']} variant_check needs raised in round 0, "
                     f"{u['variant_answers']} answered with Evo 2, {u['evo2_errors']} Evo 2 errors; "
                     f"median site percentile of scored SNVs {u['median_site_percentile']}.")

    for backend in config.PROVIDERS:
        b1, d1 = run_sets(f"{backend}_A1", lab.index)
        b3, d3 = run_sets(f"{backend}_A3", lab.index)
        if b1 and b3 and len(b1) == len(b3):
            model = json.loads((d3[0] / "meta.json").read_text())["model"]
            au3, au1 = m.bootstrap_ci_seeds(m.auroc, y, b3), m.bootstrap_ci_seeds(m.auroc, y, b1)
            d = m.paired_delta_seeds(m.auroc, y, b3, b1)
            rows.append(f"| A3 on {backend} | {model} | {len(b3)} | {fmt(au3)} | {fmtd(d)} vs A1 on {backend} | "
                        f"A1: {fmt(au1)} |")
            import scoring
            from arms.rescore import ABLATIONS, load_boards
            for ab in ("isolated", "noskeptic"):
                abl = [pd.Series({c: scoring.score(ABLATIONS[ab](arts)) for c, arts in load_boards(dd).items()})
                       .reindex(lab.index).values.astype(float) for dd in d3]
                rows.append(f"| A3_{ab} on {backend} (re-scored, 0 calls) | {model} | {len(abl)} | "
                            f"{fmt(m.bootstrap_ci_seeds(m.auroc, y, abl))} | "
                            f"{fmtd(m.paired_delta_seeds(m.auroc, y, abl, b1))} vs A1 on {backend} | |")

    if not rows:
        print("no complete exploratory runs yet")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    text = "\n".join([
        "# Exploratory results (after `results-final`; not pre-registered)", "",
        "Same 40-gene panel, labels and paired bootstrap as the headline. These runs were designed and run "
        "after the pre-registered results were frozen, so they are hypotheses for the next panel, not claims.", "",
        "| Run | Model(s) | Seeds | AUROC (95% CI) | Paired Δ AUROC | Other |",
        "| --- | --- | --- | --- | --- | --- |", *rows, "", *[f"- {n}" for n in notes], "",
    ])
    (OUT / "explore_table.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()

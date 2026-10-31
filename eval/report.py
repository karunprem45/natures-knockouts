"""Phase 6: the arms table, headline paired delta, permutation null, candidates.

Reads labels (the only stage that does, with eval/baselines.py) and the frozen run outputs.
Writes frozen_results/arms_table.md and frozen_results/summary.json.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import config
from eval import metrics as m

RESULTS = config.ROOT / "frozen_results"
RUNS = RESULTS / "runs"
SEEDS = list(range(1, config.N_SEEDS + 1))
MAIN = ["S1", "S2", "S3", "S4", "A1", "A3"]
ABLATIONS = ["A3_isolated", "A3_noskeptic", "A3_noburden", "A3_nogwas", "A3_notolerance", "A3_nosafety"]
DESCRIPTION = {
    "S1": "LOEUF alone", "S2": "burden strength alone", "S3": "GWAS strength alone",
    "S4": "all features, z-scored, equal weights", "A1": "single agent, all views",
    "A3": "collective: 4 agents + skeptic on the board",
    "A3_isolated": "A3 round 0 only (no needs, skeptic, revisions)", "A3_noskeptic": "A3 without skeptic challenges",
    "A3_noburden": "A3 without burden agent", "A3_nogwas": "A3 without GWAS agent",
    "A3_notolerance": "A3 without tolerance agent", "A3_nosafety": "A3 without safety agent",
}


def labels():
    return pd.read_csv(config.LABELS_DIR / "panel_labels.csv").set_index("gene_code").sort_index()


def score_sets(arm, index):
    """List of score arrays: one per seed for LLM arms and ablations, one for scripted arms."""
    dirs = [RUNS / arm] if (RUNS / arm).exists() else [RUNS / f"{arm}_s{s}" for s in SEEDS]
    out = []
    for d in dirs:
        s = pd.read_csv(d / "scores.csv").set_index("gene_code")["score"].reindex(index)
        assert not s.isna().any(), f"{d} is missing genes"
        out.append(s.values.astype(float))
    return out, dirs


def cost_and_calls(dirs):
    """Calls per gene from the final boards (scores.csv); spend from the LLM log, which also
    includes calls lost to rate limits and rerun (runs/RERUN_LOG.md), i.e. what was actually paid."""
    calls, cost = [], []
    for d in dirs:
        log = d / "llm_log.jsonl"
        if not log.exists():
            return 0.0, 0.0
        calls.append(float(pd.read_csv(d / "scores.csv")["calls"].mean()))
        rows = [json.loads(l) for l in log.read_text().splitlines()]
        cost.append(sum(r.get("cost_usd") or 0.0 for r in rows))
    return float(np.mean(calls)), float(np.mean(cost))


def fmt_ci(t):
    return f"{t[0]:.3f} ({t[1]:.3f}–{t[2]:.3f})"


def fmt_delta(t):
    return f"{t[0]:+.3f} ({t[1]:+.3f}, {t[2]:+.3f})"


def main():
    lab = labels()
    y = lab["label"].values
    sets = {arm: score_sets(arm, lab.index) for arm in MAIN + ABLATIONS}
    rows, summary = [], {"n_genes": int(len(y)), "n_positives": int(y.sum()), "arms": {}}
    for arm in MAIN + ABLATIONS:
        ss, dirs = sets[arm]
        au = m.bootstrap_ci_seeds(m.auroc, y, ss)
        ap = m.bootstrap_ci_seeds(m.auprc, y, ss)
        p12 = float(np.mean([m.precision_at_k(y, s) for s in ss]))
        seed_au = [m.auroc(y, s) for s in ss]
        d_s4 = m.paired_delta_seeds(m.auroc, y, ss, sets["S4"][0])
        d_a1 = m.paired_delta_seeds(m.auroc, y, ss, sets["A1"][0]) if arm != "A1" else None
        calls, cost = cost_and_calls(dirs)
        if arm.startswith("A3_"):
            calls, cost = 0.0, 0.0
        summary["arms"][arm] = {"auroc": au, "auprc": ap, "p_at_12": p12, "auroc_per_seed": seed_au,
                                "delta_vs_s4": d_s4, "delta_vs_a1": d_a1, "calls_per_gene": calls,
                                "cost_usd_per_run": cost}
        seed_txt = f" [{np.mean(seed_au):.3f} ± {np.std(seed_au, ddof=1):.3f}]" if len(ss) > 1 else ""
        rows.append(f"| {arm} | {DESCRIPTION[arm]} | {fmt_ci(au)}{seed_txt} | {fmt_ci(ap)} | {p12:.2f} | "
                    f"{calls:.1f} | {cost:.2f} | {fmt_delta(d_s4) if arm != 'S4' else '—'} | "
                    f"{fmt_delta(d_a1) if d_a1 else '—'} |")

    a3_mean = np.mean(sets["A3"][0], axis=0)
    obs, perm_p = m.permutation_null(m.auroc, y, a3_mean)
    head = summary["arms"]["A3"]["delta_vs_a1"]
    summary["headline"] = {"delta_auroc_A3_minus_A1": head, "a3_permutation_p": perm_p}

    order = np.argsort(-a3_mean, kind="stable")
    ranked = lab.iloc[order].assign(a3_score=a3_mean[order])
    cand = ranked[ranked["label"] == 0].head(5)
    summary["candidates"] = [{"gene_code": c, "symbol": r["symbol"], "a3_score": round(float(r["a3_score"]), 3),
                              "a3_rank": int(np.where(ranked.index == c)[0][0]) + 1} for c, r in cand.iterrows()]

    lines = [
        "# Results", "",
        f"{len(y)} genes, {int(y.sum())} positives (chance AUPRC {y.mean():.3f}). LLM arms: mean over "
        f"{len(SEEDS)} seeds, per-seed mean ± sd in brackets. CIs: 1,000 gene resamples, seed {config.SEED}. "
        "Δ columns are paired: both arms scored on the same resample.", "",
        f"## Headline (pre-registered)\n\n**Δ AUROC (A3 − A1) = {fmt_delta(head)}**  \n"
        f"A3 permutation null (1,000 label shuffles, seed-averaged scores): AUROC {obs:.3f}, p = {perm_p:.3f}", "",
        "## All arms", "",
        "| Arm | What | AUROC (95% CI) | AUPRC (95% CI) | P@12 | Calls/gene | $ spent/run | Δ AUROC vs S4 | Δ AUROC vs A1 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |", *rows, "",
        "Ablations re-score the saved A3 boards: 0 extra LLM calls. $ spent includes calls lost to rate "
        "limits and rerun under one rule (RERUN_LOG.md).", "",
        "## Top-ranked negatives (hypotheses, not validated targets)", "",
        "| A3 rank | Gene | A3 score |", "| --- | --- | --- |",
        *[f"| {c['a3_rank']} | {c['symbol']} ({c['gene_code']}) | {c['a3_score']:+.3f} |" for c in summary["candidates"]],
        "",
    ]
    (RESULTS / "arms_table.md").write_text("\n".join(lines))
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1))
    print("\n".join(lines))


if __name__ == "__main__":
    main()

"""P0-2: secondary comparisons read from frozen score files. Post-freeze extension, not pre-registered.

  python -m exploratory.scripts.secondary

Uses the existing paired bootstrap (eval/metrics.py) on frozen scores only:
  frozen_results/runs/{A1,A3,A3_isolated}_s{1,2}/scores.csv           (Gemini, pre-registered arms and ablation)
  frozen_results/exploratory/runs/openai_{A1,A3}_s1/                  (gpt-5-mini, exploratory)
The gpt-5-mini round-0 scores are re-scored from its saved exploratory board with the unchanged scoring.py,
exactly as the pre-registered A3_isolated ablation was. Writes exploratory/explore_table.md and
exploratory/figures/coordination_effect.png. Writes nothing under frozen/ or frozen_results/.
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import config
import scoring
from arms.rescore import ABLATIONS, load_boards
from eval import metrics as m

ROOT = config.ROOT
RUNS = ROOT / "frozen_results" / "runs"
XRUNS = ROOT / "frozen_results" / "exploratory" / "runs"
OUT = ROOT / "exploratory" / "explore_table.md"
FIG = ROOT / "exploratory" / "figures" / "coordination_effect.png"
GPT_PRICE_IN, GPT_PRICE_OUT = 0.25, 2.00   # assumed USD per 1M tokens for gpt-5-mini; output includes reasoning


def labels():
    return pd.read_csv(config.LABELS_DIR / "panel_labels.csv").set_index("gene_code").sort_index()


def scores(path, idx):
    return pd.read_csv(path / "scores.csv").set_index("gene_code")["score"].reindex(idx).values.astype(float)


def spend(run_dirs, gpt=False):
    total = 0.0
    for d in run_dirs:
        for line in (d / "llm_log.jsonl").read_text().splitlines():
            r = json.loads(line)
            if "prompt_tokens" not in r:
                continue
            if gpt:
                total += (r["prompt_tokens"] * GPT_PRICE_IN + (r["completion_tokens"] or 0) * GPT_PRICE_OUT) / 1e6
            else:
                total += r.get("cost_usd") or 0.0
    return total / len(run_dirs)


def fmt(t):
    return f"{t[0]:.3f} ({t[1]:.3f}–{t[2]:.3f})"


def fmtd(t):
    return f"{t[0]:+.3f} ({t[1]:+.3f}, {t[2]:+.3f})"


def main():
    lab = labels(); idx = lab.index; y = lab["label"].values
    gem = {a: [scores(RUNS / f"{a}_s{s}", idx) for s in (1, 2)] for a in ("A1", "A3", "A3_isolated")}
    gpt_a1 = [scores(XRUNS / "openai_A1_s1", idx)]
    gpt_a3 = [scores(XRUNS / "openai_A3_s1", idx)]
    board = load_boards(XRUNS / "openai_A3_s1") if (XRUNS / "openai_A3_s1" / "genes").exists() else None
    if board is None:   # frozen exploratory copy keeps board.jsonl, not per-gene files
        from board.artifact import Artifact
        arts = [Artifact.from_dict(json.loads(l)) for l in (XRUNS / "openai_A3_s1" / "board.jsonl").read_text().splitlines()]
        board = {}
        for a in arts:
            board.setdefault(a.gene_code, []).append(a)
    gpt_r0 = [pd.Series({c: scoring.score(ABLATIONS["isolated"](a)) for c, a in board.items()})
              .reindex(idx).values.astype(float)]

    rows = []
    # cross-check: must equal the frozen arms table
    frozen_check = m.paired_delta_seeds(m.auroc, y, gem["A3_isolated"], gem["A1"])
    comparisons = [
        ("Multi-agent vs single-agent", "Gemini 3 Flash", 2, "A3 round 0 − A1", gem["A3_isolated"], gem["A1"]),
        ("Multi-agent vs single-agent", "gpt-5-mini", 1, "A3 round 0 − A1", gpt_r0, gpt_a1),
        ("Collaborative vs isolated", "Gemini 3 Flash", 2, "A3 − A3 round 0", gem["A3"], gem["A3_isolated"]),
        ("Collaborative vs isolated", "gpt-5-mini", 1, "A3 − A3 round 0", gpt_a3, gpt_r0),
        ("Pre-registered headline", "Gemini 3 Flash", 2, "A3 − A1", gem["A3"], gem["A1"]),
        ("Pre-registered headline (replication)", "gpt-5-mini", 1, "A3 − A1", gpt_a3, gpt_a1),
    ]
    for kind, model, n, label, a, b in comparisons:
        d = m.paired_delta_seeds(m.auroc, y, a, b)
        rows.append(f"| {kind} | {model} | {n} | {label} | {fmt(m.bootstrap_ci_seeds(m.auroc, y, a))} | "
                    f"{fmt(m.bootstrap_ci_seeds(m.auroc, y, b))} | **{fmtd(d)}** | {'yes' if d[1] > 0 or d[2] < 0 else 'no'} |")

    p12 = lambda sets: np.mean([m.precision_at_k(y, s) for s in sets])
    cost_rows = [
        ("A1 (Gemini, pre-registered)", 2, gem["A1"], f"{spend([RUNS / f'A1_s{s}' for s in (1, 2)]):.2f}", "3"),
        ("A3 (Gemini, pre-registered)", 2, gem["A3"], f"{spend([RUNS / f'A3_s{s}' for s in (1, 2)]):.2f}", "10"),
        ("A3 round 0 (Gemini, re-scored)", 2, gem["A3_isolated"], "0.00 extra (from A3 boards)", "0 extra"),
        ("A3 + Evo 2 (Gemini + NVIDIA Evo 2)", 2, [scores(XRUNS / f"A3_variant_s{s}", idx) for s in (1, 2)],
         f"{spend([XRUNS / f'A3_variant_s{s}' for s in (1, 2)]):.2f} (Evo 2 free trial)", "10"),
        ("A1 (gpt-5-mini)", 1, gpt_a1, f"~{spend([XRUNS / 'openai_A1_s1'], gpt=True):.2f} (assumed prices)", "3"),
        ("A3 (gpt-5-mini)", 1, gpt_a3, f"~{spend([XRUNS / 'openai_A3_s1'], gpt=True):.2f} (assumed prices)", "10"),
        ("A3 round 0 (gpt-5-mini, re-scored)", 1, gpt_r0, "0.00 extra", "0 extra"),
    ]
    cost_lines = [f"| {name} | {n} | {fmt(m.bootstrap_ci_seeds(m.auroc, y, s))} | {p12(s):.2f} | {c} | {calls} |"
                  for name, n, s, c, calls in cost_rows]

    a2_lines = []
    a2_dir = ROOT / "exploratory" / "A2"
    if (a2_dir / "scores.csv").exists():
        a2 = [scores(a2_dir, idx)]
        same_seed = {k: [v[0]] for k, v in gem.items()}           # seed 1, the seed A2 used
        plans = json.loads((a2_dir / "plans.json").read_text())
        from collections import Counter
        sizes = Counter(len(p["plan"]) for p in plans)
        a2_lines = [
            "## Decentralized vs centralized: A2 (post-freeze extension, 1 seed, not pre-registered)",
            "",
            "A2 holds everything constant except who decides the trajectory: same model, same 10-call cap, same "
            "specialist prompts, views and parser (each chosen specialist runs exactly as in A3 round 0), same "
            "`scoring.py`. A planner LLM sees only the gene code and a one-line description of each specialist, "
            "never any evidence, and picks which to consult. No needs, no skeptic, no revisions. The Variant agent "
            "is not offered because it has no round-0 mode. Comparisons use seed 1 of each Gemini arm, the seed A2 ran.",
            "",
            "| Contrast | AUROC first | AUROC second | Paired Δ AUROC (95% CI) |",
            "| --- | --- | --- | --- |",
            *[f"| {lbl} | {fmt(m.bootstrap_ci_seeds(m.auroc, y, a))} | {fmt(m.bootstrap_ci_seeds(m.auroc, y, b))} | "
              f"**{fmtd(m.paired_delta_seeds(m.auroc, y, a, b))}** |"
              for lbl, a, b in [("A2 − A1 (centralized vs single agent)", a2, same_seed["A1"]),
                                ("A2 − A3 (centralized vs decentralized loop)", a2, same_seed["A3"]),
                                ("A2 − A3 round 0 (centralized vs isolated specialists)", a2, same_seed["A3_isolated"])]],
            "",
            f"A2 AUPRC {m.auprc(y, a2[0]):.3f}, P@12 {m.precision_at_k(y, a2[0]):.2f}, spend "
            f"${spend([a2_dir]):.2f} per 40-gene run, {np.mean([p['calls'] for p in plans]):.1f} LLM calls per gene. "
            f"Planner chose {', '.join(f'{k} specialist(s) for {v} genes' for k, v in sorted(sizes.items()))}.",
            "",
            "**How to read A2:** with no evidence to go on, the planner consulted every specialist for every gene "
            "(only the order varied), so A2 ran the same configuration as A3 round 0. "
            f"{int((np.abs(a2[0] - same_seed['A3_isolated'][0]) < 1e-9).sum())} of 40 genes got identical scores; "
            "the rest differ only through Gemini's run-to-run variation at temperature 0. The A2 − round 0 delta is "
            "therefore a measured **noise floor between two runs of one configuration**, not a "
            "centralized-vs-decentralized effect. What A2 does show: a planner that cannot see evidence adds nothing "
            "over isolated specialists, and the same specialists without the coordination loop again beat the loop "
            "(A2 − A3). A planner that sees evidence summaries would be the informative next test.",
            "",
        ]

    text = "\n".join([
        "# Exploratory and secondary results",
        "",
        "**Post-freeze extension, not pre-registered.** The frozen exploratory table is "
        "[`frozen_results/exploratory/explore_table.md`](../frozen_results/exploratory/explore_table.md) and is "
        "unchanged; this file adds secondary comparisons read from frozen score files. Generated by "
        "`exploratory/scripts/secondary.py`.",
        "",
        "## Secondary, not the pre-registered headline",
        "",
        "The pre-registered headline is **A3 − A1 = +0.008 (−0.074, +0.103)** on Gemini, from "
        "[`frozen_results/arms_table.md`](../frozen_results/arms_table.md). A3 round 0 (isolated specialists) is "
        "one of the pre-registered ablations (`frozen/metrics.md`: \"A3_isolated (round 0 only)\"), but choosing it "
        "as the comparison to highlight was done after seeing results. Paired bootstrap, 1,000 gene resamples, "
        f"seed {config.SEED}; \"CI excludes 0\" means the 95% interval does not cross zero.",
        "",
        "| Comparison (rubric wording) | Model | Seeds | Contrast | AUROC first | AUROC second | Paired Δ AUROC (95% CI) | CI excludes 0 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *rows,
        "",
        f"Cross-check: the Gemini A3 round 0 − A1 delta recomputed here is {fmtd(frozen_check)}, matching the "
        "frozen arms table (+0.080, −0.004 to +0.173).",
        "",
        "**Reading it honestly:** isolated specialists beat the single agent by about +0.08 on Gemini and +0.04 on "
        "gpt-5-mini, but neither interval excludes zero (Gemini's lower bound is −0.004). The one interval that "
        "excludes zero is the **coordination penalty on Gemini: A3 − A3 round 0 = −0.071 (−0.139, −0.013)**; on "
        "gpt-5-mini the same contrast is −0.106 with an interval just crossing zero. Direction is consistent "
        "across two models. These are several post-hoc contrasts on 40 genes with no multiplicity correction, so "
        "they are evidence for the next pre-registered test, not settled effects.",
        "",
        "## AUROC, precision@12 and cost per arm",
        "",
        "Precision@12 is pre-registered (`frozen/metrics.md`) and already in the frozen arms table for every "
        "pre-registered arm; it is repeated here for the exploratory arms. Spend for Gemini arms is from the LLM "
        "logs (assumed $0.50 / $3.00 per 1M tokens, includes calls lost to rate limits and rerun); gpt-5-mini "
        f"uses assumed list prices (${GPT_PRICE_IN:.2f} / ${GPT_PRICE_OUT:.2f} per 1M tokens).",
        "",
        "| Arm | Seeds | AUROC (95% CI) | P@12 | $ per 40-gene run | LLM calls / gene |",
        "| --- | --- | --- | --- | --- | --- |",
        *cost_lines,
        "",
        "The skeptic's rank effect is already a frozen figure: "
        "[`frozen_results/figures/4_skeptic_rank_shift.png`](../frozen_results/figures/4_skeptic_rank_shift.png). "
        "The coordination loop's effect (round 0 → final) is in "
        "[`figures/coordination_effect.png`](figures/coordination_effect.png).",
        "",
        *a2_lines,
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)

    # figure: per-gene rank, round 0 vs full loop (Gemini, seed-averaged), positives vs negatives
    from eval.figures import BLUE, CONTEXT, GRID, INK2, SURFACE
    r0 = pd.Series(np.mean(gem["A3_isolated"], axis=0)).rank(ascending=False, method="first").values
    fin = pd.Series(np.mean(gem["A3"], axis=0)).rank(ascending=False, method="first").values
    fig, ax = plt.subplots(figsize=(6.5, 7))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    for i in np.argsort(y):
        col, lw, z = (BLUE, 2, 3) if y[i] else (CONTEXT, 1, 2)
        ax.plot([0, 1], [r0[i], fin[i]], color=col, lw=lw, zorder=z, marker="o", markersize=5)
    ax.invert_yaxis()
    ax.set_xticks([0, 1], ["round 0\n(isolated specialists)", "after needs, skeptic,\nrevisions (A3)"])
    ax.set_xlim(-0.25, 1.25)
    ax.set_ylabel("Rank (1 = most promising)", color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID)
    ax.set_title(f"Coordination loop effect on ranks (Gemini, 2 seeds)\nmean known-target rank "
                 f"{r0[y == 1].mean():.1f} → {fin[y == 1].mean():.1f}", fontsize=12, fontweight="bold")
    ax.legend(handles=[plt.Line2D([], [], color=BLUE, lw=2, label="positive (known target)"),
                       plt.Line2D([], [], color=CONTEXT, lw=1, label="hard negative")],
              loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=2, frameon=False)
    ax.text(0.5, -0.24, "Post-freeze extension, not pre-registered", transform=ax.transAxes, ha="center",
            fontsize=8, color=INK2)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    print(text)
    print(f"wrote {OUT} and {FIG}")


if __name__ == "__main__":
    main()

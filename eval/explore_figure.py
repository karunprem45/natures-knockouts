"""Exploratory figure: the same arms on two LLMs, plus the Evo 2 Variant agent (after results-final)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scoring
from arms.rescore import ABLATIONS, load_boards
from eval import metrics as m
from eval.figures import BLUE, CONTEXT, GRID, INK, INK2, ORANGE, SURFACE, YELLOW
from eval.report import RESULTS, labels, score_sets
import config

OUT = RESULTS / "figures" / "6_models_and_evo2.png"


def run_scores(d, idx):
    return pd.read_csv(d / "scores.csv").set_index("gene_code")["score"].reindex(idx).values.astype(float)


def main():
    lab = labels(); y = lab["label"].values; idx = lab.index
    ex = config.RUNS_DIR / "explore"
    gem = {"A1": score_sets("A1", idx)[0], "A3": score_sets("A3", idx)[0],
           "A3 round 0": score_sets("A3_isolated", idx)[0],
           "A3 + Evo 2": [run_scores(ex / f"A3_variant_s{s}", idx) for s in (1, 2)]}
    gpt_board = load_boards(ex / "openai_A3_s1")
    gpt = {"A1": [run_scores(ex / "openai_A1_s1", idx)], "A3": [run_scores(ex / "openai_A3_s1", idx)],
           "A3 round 0": [pd.Series({c: scoring.score(ABLATIONS["isolated"](a)) for c, a in gpt_board.items()})
                          .reindex(idx).values.astype(float)]}
    color = {"A1": ORANGE, "A3": BLUE, "A3 round 0": "#86b6ef", "A3 + Evo 2": YELLOW}
    rows = [("Gemini 3 Flash", k, v) for k, v in gem.items()] + [("gpt-5-mini", k, v) for k, v in gpt.items()]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ypos = np.arange(len(rows))[::-1]
    for yp, (model, arm, sets) in zip(ypos, rows):
        p, lo, hi = m.bootstrap_ci_seeds(m.auroc, y, sets)
        ax.errorbar(p, yp, xerr=[[p - lo], [hi - p]], fmt="o", color=color[arm], ecolor=color[arm], lw=2,
                    capsize=3, markersize=9, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(hi + 0.012, yp, f"{p:.3f}", va="center", fontsize=10, color=INK)
    ax.set_yticks(ypos, [f"{arm}" for _, arm, _ in rows])
    ax.axhline(2.5, color=GRID, lw=1)
    ax.text(0.405, 5.85, "Gemini 3 Flash (2 seeds)", fontsize=10, color=INK2)
    ax.text(0.405, 2.15, "gpt-5-mini (1 seed)", fontsize=10, color=INK2)
    ax.axvline(0.5, color=INK2, lw=1, ls=":")
    ax.set_xlim(0.4, 1.05)
    ax.set_xlabel("AUROC, point and 95% bootstrap CI (40 genes)")
    ax.set_title("Isolated specialists lead on both models; Evo 2 adds a little")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

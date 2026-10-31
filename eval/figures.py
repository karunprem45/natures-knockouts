"""Phase 6: five PNGs at 150 dpi -> frozen_results/figures/.

Colours: the dataviz skill's reference categorical palette in its validated order; identity is never
colour-alone (legend or direct label on every chart).
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve
import config
from board.artifact import Artifact
from eval.report import RESULTS, RUNS, labels, score_sets

OUT = RESULTS / "figures"
SURFACE, INK, INK2, GRID, CONTEXT = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
ARM_COLOR = {"A3": BLUE, "A1": ORANGE, "S4": AQUA, "A3_isolated": YELLOW}
AGENT_COLOR = {"burden": BLUE, "gwas": ORANGE, "tolerance": AQUA, "safety": YELLOW, "skeptic": MAGENTA}

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
                     "axes.titlesize": 13, "axes.titleweight": "bold", "legend.frameon": False})


def summary():
    return json.loads((RESULTS / "summary.json").read_text())


def mean_scores(arm, index):
    return np.mean(score_sets(arm, index)[0], axis=0)


def fig_curves(lab, y):
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.8))
    for arm in ["S4", "A1", "A3", "A3_isolated"]:
        s = mean_scores(arm, lab.index)
        fpr, tpr, _ = roc_curve(y, s)
        pr, rc, _ = precision_recall_curve(y, s)
        au = summary()["arms"][arm]["auroc"][0]
        ls = "--" if arm == "A3_isolated" else "-"
        a.plot(fpr, tpr, color=ARM_COLOR[arm], lw=2, ls=ls, label=f"{arm}  {au:.3f}")
        b.plot(rc, pr, color=ARM_COLOR[arm], lw=2, ls=ls, label=arm)
    a.plot([0, 1], [0, 1], color=CONTEXT, lw=1, ls=":")
    b.axhline(y.mean(), color=CONTEXT, lw=1, ls=":")
    b.text(0.99, y.mean() + 0.02, "chance", ha="right", color=INK2, fontsize=9)
    a.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC (seed-averaged scores)")
    b.set(xlabel="Recall", ylabel="Precision", title="Precision–recall", ylim=(0, 1.05))
    a.legend(title="Arm  AUROC", loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "1_roc_pr.png", dpi=150)
    plt.close(fig)


def fig_bars():
    s = summary()["arms"]
    arms = ["S1", "S2", "S3", "S4", "A1", "A3", "A3_isolated", "A3_noskeptic",
            "A3_noburden", "A3_nogwas", "A3_notolerance", "A3_nosafety"]
    color = {a: (ORANGE if a == "A1" else BLUE if a == "A3" else AQUA if a == "S4"
                 else "#86b6ef" if a.startswith("A3_") else CONTEXT) for a in arms}
    fig, ax = plt.subplots(figsize=(9, 6))
    ypos = np.arange(len(arms))[::-1]
    for yp, a in zip(ypos, arms):
        p, lo, hi = s[a]["auroc"]
        ax.errorbar(p, yp, xerr=[[p - lo], [hi - p]], fmt="o", color=color[a], ecolor=color[a], capsize=3,
                    lw=2, markersize=9, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(hi + 0.012, yp, f"{p:.3f}", va="center", fontsize=10, color=INK)
    ax.axvline(0.5, color=INK2, lw=1, ls=":")
    ax.text(0.505, -0.75, "chance", ha="left", color=INK2, fontsize=9)
    ax.axhspan(-0.5, 5.5, color=GRID, alpha=0.35, lw=0, zorder=0)
    ax.text(0.215, 2.5, "re-scored ablations\n(0 extra LLM calls)", ha="left", va="center", fontsize=9, color=INK2)
    ax.set_yticks(ypos, arms)
    ax.set_xlim(0.2, 1.05)
    ax.set_ylim(-1.1, len(arms) - 0.4)
    ax.set_xlabel("AUROC, point and 95% bootstrap CI (40 genes)")
    ax.set_title("Every arm on the same blind panel")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "2_arms_auroc.png", dpi=150)
    plt.close(fig)


def pick_demo_gene():
    """First gene (by code) whose seed-1 board shows every mechanism: a cross-agent fulfilment,
    a challenge and a revision. Chosen by structure only, never by label or score."""
    for p in sorted((RUNS / "A3_s1").glob("board.jsonl")):
        arts = [Artifact.from_dict(json.loads(l)) for l in p.read_text().splitlines()]
    by_gene = {}
    for a in arts:
        by_gene.setdefault(a.gene_code, []).append(a)
    for code in sorted(by_gene):
        kinds = {a.artifact_type for a in by_gene[code]}
        if {"fulfillment", "challenge", "revision"} <= kinds and sum(a.artifact_type == "fulfillment" for a in by_gene[code]) >= 2:
            return code, by_gene[code]
    raise RuntimeError("no gene shows all mechanisms")


def fig_dag():
    code, arts = pick_demo_gene()
    g = nx.DiGraph()
    ids = {a.artifact_id: a for a in arts}
    rows = {}
    for a in sorted(arts, key=lambda a: (a.round, a.artifact_type, a.producer_agent)):
        col = {"evidence": 0, "fulfillment": 1, "challenge": 2, "revision": 3}.get(a.artifact_type, 0)
        rows.setdefault(col, 0)
        g.add_node(a.artifact_id, pos=(col, -rows[col]), art=a)
        rows[col] += 1
    for a in arts:
        for p in a.parent_artifact_ids:
            if p in ids:
                g.add_edge(p, a.artifact_id, kind="challenge" if a.artifact_type == "challenge" else "parent")
    pos = nx.get_node_attributes(g, "pos")
    fig, ax = plt.subplots(figsize=(12, 6.5))
    for kind, style, col in [("parent", "-", INK2), ("challenge", "--", MAGENTA)]:
        edges = [(u, v) for u, v, d in g.edges(data=True) if d["kind"] == kind]
        nx.draw_networkx_edges(g, pos, edgelist=edges, style=style, edge_color=col, width=1.5, arrows=True,
                               arrowsize=14, node_size=2600, ax=ax, connectionstyle="arc3,rad=0.08")
    for n, d in g.nodes(data=True):
        a = d["art"]
        shape = "D" if a.artifact_type == "challenge" else "o"
        nx.draw_networkx_nodes(g, pos, nodelist=[n], node_color=AGENT_COLOR.get(a.producer_agent, CONTEXT),
                               node_shape=shape, node_size=2600, edgecolors=SURFACE, linewidths=2, ax=ax)
        if a.artifact_type == "challenge":
            label = f"skeptic\n{len(a.challenges)} challenges"
        else:
            label = f"{a.producer_agent}\n{a.stance} {a.strength:.2f}"
        x, yv = pos[n]
        ax.text(x, yv - 0.42, label, ha="center", va="top", fontsize=9, color=INK)
    for col, name in enumerate(["Round 0\nindependent evidence", "Round 1\nneeds answered",
                                "Round 2a\nskeptic", "Round 2b\nrevisions"]):
        ax.text(col, 0.75, name, ha="center", fontsize=11, color=INK2, fontweight="bold")
    ax.set_title(f"Provenance on the shared board, {code} (no planner assigned any of this work)")
    ax.axis("off")
    ax.set_ylim(min(p[1] for p in pos.values()) - 1.0, 1.2)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=10, label=k) for k, c in AGENT_COLOR.items()]
    handles += [plt.Line2D([], [], color=INK2, label="parent link"),
                plt.Line2D([], [], color=MAGENTA, ls="--", label="challenge")]
    ax.legend(handles=handles, loc="lower center", ncol=7, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    fig.savefig(OUT / "3_provenance_dag.png", dpi=150)
    plt.close(fig)
    return code


def fig_skeptic(lab, y):
    full = mean_scores("A3", lab.index)
    nosk = mean_scores("A3_noskeptic", lab.index)
    r_full = pd.Series(full).rank(ascending=False, method="first").values
    r_nosk = pd.Series(nosk).rank(ascending=False, method="first").values
    fig, ax = plt.subplots(figsize=(6.5, 7))
    for i in np.argsort(y):
        col, lw, z = (BLUE, 2, 3) if y[i] else (CONTEXT, 1, 2)
        ax.plot([0, 1], [r_nosk[i], r_full[i]], color=col, lw=lw, zorder=z, marker="o", markersize=5)
    ax.invert_yaxis()
    ax.set_xticks([0, 1], ["without skeptic", "with skeptic (A3)"])
    ax.set_xlim(-0.25, 1.25)
    ax.set_ylabel("Rank (1 = most promising)")
    mean_pos = (r_full[y == 1].mean(), r_nosk[y == 1].mean())
    ax.set_title(f"Skeptic effect on ranks\nmean positive rank {mean_pos[1]:.1f} → {mean_pos[0]:.1f}")
    ax.legend(handles=[plt.Line2D([], [], color=BLUE, lw=2, label="positive (known target)"),
                       plt.Line2D([], [], color=CONTEXT, lw=1, label="hard negative")], loc="lower center",
              bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "4_skeptic_rank_shift.png", dpi=150)
    plt.close(fig)


def fig_cost():
    s = summary()["arms"]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    pts = [("S4", AQUA), ("A1", ORANGE), ("A3", BLUE)]
    for arm, col in pts:
        cost = s[arm]["cost_usd_per_run"]
        p, lo, hi = s[arm]["auroc"]
        ax.errorbar(cost, p, yerr=[[p - lo], [hi - p]], fmt="o", color=col, markersize=10, capsize=4, lw=1.5,
                    markeredgecolor=SURFACE, markeredgewidth=2)
        left = arm == "A1"
        ax.annotate(f"{arm}  {p:.3f}\n{s[arm]['calls_per_gene']:.0f} calls/gene", (cost, p),
                    textcoords="offset points", xytext=(-12 if left else 12, -4), ha="right" if left else "left",
                    va="center", fontsize=10, color=INK)
    ax.set(xlabel="LLM spend per 40-gene run (USD)", ylabel="AUROC (95% CI)", title="Cost vs accuracy",
           xlim=(-0.15, 1.9), ylim=(0.5, 1.0))
    fig.tight_layout()
    fig.savefig(OUT / "5_cost_vs_auroc.png", dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = labels()
    y = lab["label"].values
    fig_curves(lab, y)
    fig_bars()
    code = fig_dag()
    fig_skeptic(lab, y)
    fig_cost()
    print(f"wrote 5 figures to {OUT} (DAG gene {code})")


if __name__ == "__main__":
    main()

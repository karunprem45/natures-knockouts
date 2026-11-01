"""Build site/index.html and site/keynote.html with every number computed from frozen or exploratory files.

  python -m site_build      (run from the repo root as:  .venv/bin/python site/build_site.py)

Nothing on either page is hand-typed: this script reads frozen_results/, exploratory/ and the panel labels,
computes each figure, and inlines the result as one JSON constant. Read-only on frozen/ and frozen_results/.
"""
import csv, json, re, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
import scoring  # noqa: E402
from arms.rescore import ABLATIONS  # noqa: E402
from board.artifact import Artifact  # noqa: E402
from eval import metrics as m  # noqa: E402

SITE = ROOT / "site"
FR = ROOT / "frozen_results"
EX = ROOT / "exploratory"
REPLAY = ["Gene_08", "Gene_21"]          # PCSK9 (positive), THBS1 (negative); chosen in the build notes
CHANNELS = ["burden", "gwas", "tolerance", "safety"]


def labels():
    return pd.read_csv(config.LABELS_DIR / "panel_labels.csv").set_index("gene_code").sort_index()


def board(path):
    out = defaultdict(list)
    for line in path.read_text().splitlines():
        a = Artifact.from_dict(json.loads(line))
        out[a.gene_code].append(a)
    return out


def scores(path, idx):
    return pd.read_csv(path / "scores.csv").set_index("gene_code")["score"].reindex(idx).values.astype(float)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def replay(code, lab, b1):
    arts = sorted(b1[code], key=lambda a: (a.round, a.artifact_type != "evidence", a.timestamp))
    short = {a.artifact_id: f"a{i}" for i, a in enumerate(arts)}
    full_total, full_parts = scoring.score(arts, return_breakdown=True)
    iso_total, iso_parts = scoring.score(ABLATIONS["isolated"](arts), return_breakdown=True)
    challenged = sorted(scoring.challenged_channels(arts))
    latest = scoring.latest_verdicts(arts)
    return {
        "code": code, "symbol": lab.loc[code, "symbol"], "label": int(lab.loc[code, "label"]),
        "artifacts": [{
            "id": short[a.artifact_id], "round": a.round, "type": a.artifact_type, "agent": a.producer_agent,
            "stance": a.stance, "strength": a.strength, "rationale": a.rationale,
            "parents": [short[p] for p in a.parent_artifact_ids if p in short],
            "needs": [{"type": n["type"], "query": n["query"]} for n in a.needs],
            "challenges": [{"type": c["type"], "channel": c["channel"],
                            "target": short.get(c.get("target_artifact_id"))} for c in a.challenges],
        } for a in arts],
        "final": {"total": round(full_total, 4), "parts": {k: round(v, 4) for k, v in full_parts.items() if k in CHANNELS},
                  "latest": {k: {"stance": v.stance, "strength": v.strength} for k, v in latest.items()}},
        "round0": {"total": round(iso_total, 4), "parts": {k: round(v, 4) for k, v in iso_parts.items() if k in CHANNELS}},
        "challenged": challenged,
    }


def main():
    lab = labels()
    y, idx = lab["label"].values, lab.index
    summary = json.loads((FR / "summary.json").read_text())
    arms = {k: {"auroc": [round(x, 3) for x in v["auroc"]], "auprc": [round(x, 3) for x in v["auprc"]],
                "calls": round(v["calls_per_gene"], 1), "cost": round(v["cost_usd_per_run"], 2)}
            for k, v in summary["arms"].items()}
    b1 = board(FR / "runs" / "A3_s1" / "board.jsonl")

    # replicate penalties (paired) and the unpaired floor
    from exploratory.noise_floor.analyze import RUNS, boards as rep_boards
    from scipy import stats
    pen, rep_au = {}, {}
    for s, run in RUNS.items():
        sc = scores(run, idx)
        iso = pd.Series({c: scoring.score(ABLATIONS["isolated"](a)) for c, a in rep_boards(run).items()}).reindex(idx).values
        rep_au[s] = m.auroc(y, sc)
        pen[s] = rep_au[s] - m.auroc(y, iso)
    d = np.array([pen[s] for s in sorted(pen)])
    se = d.std(ddof=1) / np.sqrt(len(d))
    tc = stats.t.ppf(0.975, len(d) - 1)
    t_stat, p_two = stats.ttest_1samp(d, 0.0)
    pair_diffs = [abs(rep_au[a] - rep_au[b]) for i, a in enumerate(sorted(rep_au)) for b in sorted(rep_au)[i + 1:]]
    floor = float(np.percentile(pair_diffs, 95))

    # mechanism: burden challenged by label (seed 1); rank shift round 0 -> A3 (seed-averaged)
    burden_hit = {0: 0, 1: 0}
    for g, arts in b1.items():
        if any(c["channel"] == "burden" for a in arts if a.artifact_type == "challenge" for c in a.challenges):
            burden_hit[int(lab.loc[g, "label"])] += 1
    a3m = np.mean([scores(FR / "runs" / f"A3_s{s}", idx) for s in (1, 2)], axis=0)
    r0m = np.mean([scores(FR / "runs" / f"A3_isolated_s{s}", idx) for s in (1, 2)], axis=0)
    rk = lambda v: pd.Series(v).rank(ascending=False, method="first").values
    rank_shift = [round(float(rk(r0m)[y == 1].mean()), 1), round(float(rk(a3m)[y == 1].mean()), 1)]
    n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())

    # ACVR1C
    acv = lab.index[lab.symbol == "ACVR1C"][0]
    neg_idx = lab.index[lab.label == 0]
    def rank_of(v, pool):
        s = pd.Series(v, index=idx)
        return int(1 + (s[pool] > s[acv]).sum())
    s1, s2 = scores(FR / "runs" / "A3_s1", idx), scores(FR / "runs" / "A3_s2", idx)
    acv_ranks = {"mean": [rank_of(a3m, idx), rank_of(a3m, neg_idx)], "seed1": [rank_of(s1, idx), rank_of(s1, neg_idx)],
                 "seed2": [rank_of(s2, idx), rank_of(s2, neg_idx)]}
    acv_latest = {k: {"stance": v.stance, "strength": v.strength} for k, v in scoring.latest_verdicts(b1[acv]).items()}
    case = (EX / "ACVR1C_CASE.md").read_text()
    hits = int(re.search(r"Identity or drug terms found: \*\*(\d+)\*\*", case).group(1))
    n_terms = int(re.search(r"for (\d+) identity terms", case).group(1))

    # Evo 2
    def pct_from_flags(run):
        out = []
        for line in (run / "board.jsonl").read_text().splitlines():
            a = json.loads(line)
            out += [float(f.split(":")[1]) for f in a["flags"] if f.startswith("evo2_percentile:")]
        return out
    lead_pct = pct_from_flags(FR / "exploratory" / "runs" / "A3_variant_s1") + pct_from_flags(FR / "exploratory" / "runs" / "A3_variant_s2")
    cod = pd.read_csv(EX / "evo2_coding" / "scores.csv")
    cod_pct = cod[cod.ok == 1].site_percentile.dropna()
    gsum = json.loads((EX / "evo2_coding" / "gene_summary.json").read_text())
    pos_codes = set(lab.index[lab.label == 1])
    gmed = lambda codes: round(float(np.median([gsum[c]["median_site_percentile"] for c in codes])), 1)
    a3s1 = scores(FR / "runs" / "A3_s1", idx)
    d_lead = m.paired_delta(m.auroc, y, scores(FR / "exploratory" / "runs" / "A3_variant_s1", idx), a3s1)
    d_cod = m.paired_delta(m.auroc, y, scores(EX / "evo2_coding" / "A3_variant_coding_s1", idx), a3s1)
    var2 = [scores(FR / "exploratory" / "runs" / f"A3_variant_s{s}", idx) for s in (1, 2)]
    a3both = [scores(FR / "runs" / f"A3_s{s}", idx) for s in (1, 2)]
    d_lead2 = m.paired_delta_seeds(m.auroc, y, var2, a3both)

    # planner
    plans = json.loads((EX / "A2_constrained" / "plans.json").read_text())
    per_spec = Counter(s for p in plans for s in p["plan"])
    a2c = scores(EX / "A2_constrained", idx)
    d_a2c = m.paired_delta(m.auroc, y, a2c, scores(FR / "runs" / "A3_isolated_s1", idx))

    # most common challenge type: fire rate by label (both seeds), from the panel-1 calibration file
    cal = json.loads((EX / "v2" / "calibration.json").read_text())
    bio = cal["types"]["biomarker_only"]
    challenge_rates = {"type": "biomarker_only", "pos": round(bio["rate_pos"], 3), "neg": round(bio["rate_neg"], 3),
                       "gene_runs": cal["gene_runs"]}
    cite = re.search(r"carriers of predicted damaging ACVR1C variants\s+had \*\*(\d+)% lower type 2 diabetes risk\*\* "
                     r"\(OR ([0-9.]+), 95% CI ([0-9.]+)–([0-9.]+)", case)
    assert cite, "ACVR1C carriers citation not found in ACVR1C_CASE.md"

    # isolation-check count
    n_checks = int(re.search(r"(\d+) tests? collected", subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pytest", "--collect-only", "-q", "tests/test_views_isolation.py"],
        cwd=ROOT, capture_output=True, text=True).stdout).group(1))

    data = {
        "built_from": git("rev-parse", "--short", "HEAD"),
        "tags": {t: git("rev-list", "-n1", "--abbrev-commit", "--abbrev=7", t) for t in
                 ["prereg", "results-raw", "results-final", "prereg-v2", "submission"]},
        "panel": {"n": len(y), "pos": n_pos, "neg": n_neg},
        "arms": arms,
        "headline": {"delta": [round(x, 3) for x in summary["headline"]["delta_auroc_A3_minus_A1"]],
                     "perm_p": round(summary["headline"]["a3_permutation_p"], 3)},
        "paired": {"penalties": [round(float(x), 4) for x in d], "mean": round(float(d.mean()), 4),
                   "sd": round(float(d.std(ddof=1)), 4), "se": round(float(se), 4),
                   "ci": [round(float(d.mean() - tc * se), 4), round(float(d.mean() + tc * se), 4)],
                   "t": round(float(t_stat), 2), "p": round(float(p_two), 4), "neg": int((d < 0).sum())},
        "floor": {"value": round(floor, 3), "replicates": [round(rep_au[s], 3) for s in sorted(rep_au)]},
        "mechanism": {"burden_pos": [burden_hit[1], n_pos], "burden_neg": [burden_hit[0], n_neg], "rank_shift": rank_shift,
                      "top_challenge": challenge_rates},
        "acvr1c": {"code": acv, "ranks": acv_ranks, "latest": acv_latest, "identity_hits": hits, "terms": n_terms, "views": 5,
                   "cite": {"pct_lower": int(cite.group(1)), "or": cite.group(2), "ci": [cite.group(3), cite.group(4)],
                            "ref": "Emdin et al., Diabetes 2019;68:226-234"}},
        "evo2": {"lead_median": round(float(np.median(lead_pct)), 1), "coding_median": round(float(cod_pct.median()), 1),
                 "n_coding": int((cod.ok == 1).sum()), "pos_median": gmed(pos_codes), "neg_median": gmed(set(idx) - pos_codes),
                 "d_lead_s1": [round(x, 3) for x in d_lead], "d_lead_2seed": [round(x, 3) for x in d_lead2],
                 "d_coding": [round(x, 3) for x in d_cod]},
        "planner": {"counts": {s: per_spec.get(s, 0) for s in CHANNELS}, "n": len(plans),
                    "auroc": round(m.auroc(y, a2c), 3), "d_round0": [round(x, 3) for x in d_a2c]},
        "isolation_checks": n_checks,
        "replays": [replay(c, lab, b1) for c in REPLAY],
    }
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    for name in ("index", "keynote"):
        tpl = (SITE / f"{name}.template.html").read_text()
        (SITE / f"{name}.html").write_text(tpl.replace("/*__DATA__*/null", blob))
    (SITE / "data.json").write_text(json.dumps(data, indent=1))
    print(f"built site from {data['built_from']}: {len(blob):,} bytes of data")


if __name__ == "__main__":
    main()

"""Phase 2: scripted baselines S1-S4. No LLM, no labels. Writes runs/S*/scores.csv.

S4 is the real competitor (BUILD.md §Phase 2): z-score every feature, flip sign where lower is
better, sum with equal weights. Missing values are imputed by the panel median and logged.
"""
import pandas as pd
import config

LOWER_IS_BETTER = {"pli", "depmap_dependency", "safety_risk_count"}
SINGLE = {"S1": "loeuf", "S2": "burden_prot_strength", "S3": "gwas_prot_strength"}


def impute(df, log):
    out = df.copy()
    for c in df.columns:
        n = int(df[c].isna().sum())
        if n == len(df):
            out = out.drop(columns=c)
            log.append(f"{c}: all {n} values missing -> column dropped")
        elif n:
            out[c] = df[c].fillna(df[c].median())
            log.append(f"{c}: {n} missing -> imputed panel median {df[c].median():.4g}")
    return out


def s4(feats):
    z = (feats - feats.mean()) / feats.std(ddof=0).replace(0, 1)
    for c in z.columns:
        if c in LOWER_IS_BETTER:
            z[c] = -z[c]
    return z.sum(axis=1)


def main():
    df = pd.read_csv(config.DATA_DIR / "features.csv").set_index("gene_code").sort_index()
    log = []
    feats = impute(df, log)
    scores = {arm: feats[col] for arm, col in SINGLE.items()}
    scores["S4"] = s4(feats)
    for arm, s in scores.items():
        d = config.RUNS_DIR / arm
        d.mkdir(parents=True, exist_ok=True)
        s.rename("score").to_csv(d / "scores.csv")
    (config.RUNS_DIR / "S4" / "imputation_log.md").write_text("\n".join(f"- {l}" for l in log) + "\n")
    print("\n".join(log))
    print(f"wrote scores for {', '.join(scores)}")


if __name__ == "__main__":
    main()

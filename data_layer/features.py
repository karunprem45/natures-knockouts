"""Phase 2: one row of numeric features per gene_code -> data/features.csv.

Built from the same identity-scrubbed rows the agents see, so baselines and agents get the
same information. Missing data is NaN, never 0 (a gene with burden rows but none protective
gets strength 0; a gene with no burden rows gets NaN).
"""
import csv, math, statistics
import config
from data_layer.build_views import Scrubber, p_of, row_text
from data_layer.common import load_raw, read_pool, symbol_map
from data_layer.scope import is_hard_endpoint

NAN = float("nan")
P_CAP = 30.0
SAFETY_MIN_NEG_LOG10_P = 6.0
MENDELIAN = set(config.SAFETY_EXTRA_DATASOURCES)
COLUMNS = ["gene_code", "burden_prot_strength", "burden_n_cohorts", "burden_hard_endpoint",
           "burden_n_traits", "gwas_prot_strength", "gwas_hard_endpoint", "loeuf", "pli",
           "depmap_dependency", "safety_risk_count", "evo2_delta"]


def is_prot_lof(r):
    return r.get("directionOnTarget") == "LoF" and r.get("directionOnTrait") == "protect"


def gwas_protective(r):
    """A GWAS credible set whose effect allele lowers the in-scope trait (beta < 0)."""
    beta = (r.get("credibleSet") or {}).get("beta")
    return beta is not None and beta < 0


def capped_max(values):
    vals = [v for v in values if v is not None]
    return min(P_CAP, max(vals)) if vals else 0.0


def features(raw, burden, gwas, other):
    prot = [r for r in burden if is_prot_lof(r)]
    gprot = [r for r in gwas if gwas_protective(r)]
    lof = {c["constraintType"]: c for c in raw["constraint"]}.get("lof", {})
    effects = [s["geneEffect"] for t in raw["essentiality"]["depmap"] for s in t["screens"] or []
               if s.get("geneEffect") is not None]
    risky = set()
    for r in other:
        risk_lof = r.get("directionOnTarget") == "LoF" and r.get("directionOnTrait") == "risk"
        if risk_lof and r["datasourceId"] in MENDELIAN:
            risky.add(r["disease"]["name"])
        elif risk_lof and r["datasourceId"] == config.DS_BURDEN and (p_of(r) or 0) >= SAFETY_MIN_NEG_LOG10_P:
            risky.add(r["disease"]["name"])
    return {
        "burden_prot_strength": capped_max(p_of(r) for r in prot) if burden else NAN,
        "burden_n_cohorts": len({r.get("cohortId") for r in prot}) if burden else NAN,
        "burden_hard_endpoint": float(any(is_hard_endpoint(r["disease"]["name"]) for r in prot)) if burden else NAN,
        "burden_n_traits": len({r["disease"]["name"] for r in prot}) if burden else NAN,
        "gwas_prot_strength": capped_max(p_of(r) for r in gprot) if gwas else NAN,
        "gwas_hard_endpoint": float(any(is_hard_endpoint(r["disease"]["name"]) for r in gprot)) if gwas else NAN,
        "loeuf": lof.get("oeUpper", NAN) if lof.get("oeUpper") is not None else NAN,
        "pli": lof.get("score") if lof.get("score") is not None else NAN,
        "depmap_dependency": -statistics.mean(effects) if effects else NAN,
        "safety_risk_count": float(len(risky) + len(raw["safety_liabilities"])),
        "evo2_delta": NAN,  # filled only if the Variant agent ran
    }


def main():
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        panel = list(csv.DictReader(f))
    syms = {s for s in set(symbol_map().values()) | {r["symbol"] for r in read_pool()}
            if not s.startswith("ENSG") and len(s) >= 3}
    scrub = Scrubber(syms)
    out = config.DATA_DIR / "features.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for g in panel:
            raw = load_raw(g["ensembl_id"])
            keep = lambda rows: [r for r in rows if scrub.ok(row_text(r), raw["identity"])]
            row = features(raw, keep(raw["burden"]), keep(raw["gwas"]), keep(raw["all_trait_evidence"]))
            w.writerow({"gene_code": g["gene_code"],
                        **{k: ("" if isinstance(v, float) and math.isnan(v) else round(v, 6)) for k, v in row.items()}})
    print(f"wrote {out} ({len(panel)} genes)")


if __name__ == "__main__":
    main()

"""Phase 1d.5: write data/views/<agent>/<Gene_NN>.json — the ONLY data any agent may read (R2).

Each view holds one evidence slice (BUILD.md §7). Stripped from every view: symbols, names,
synonyms, Ensembl IDs, literature, variant IDs, drug data. Any row whose text mentions a known
gene symbol, or the gene's own protein name, is dropped and logged.
"""
import csv, json, re, statistics
from collections import defaultdict
import config
from data_layer.common import load_raw, neg_log10_p, read_pool, symbol_map
from data_layer.scope import is_hard_endpoint

VIEW_LOG = config.VIEWS_DIR / "build_log.md"
CODING = ("missense", "stop_gained", "frameshift", "splice", "start_lost", "stop_lost", "inframe")
ROMAN = {"iii": "3", "ii": "2", "iv": "4", "i": "1"}


def norm(text):
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return "".join(ROMAN.get(w, w) for w in words)


class Scrubber:
    """Drops rows that could reveal any gene's identity."""

    def __init__(self, all_symbols):
        self.symbol_re = re.compile(r"\b(" + "|".join(sorted(map(re.escape, all_symbols), key=len,
                                                              reverse=True)) + r")\b")
        self.ensg_re = re.compile(r"ENSG\d{11}")
        self.dropped = 0

    def ok(self, row_text, identity):
        own = [identity["symbol"]] + [s for s in identity["synonyms"] if len(s) >= 3]
        own_norm = [norm(x) for x in own + [identity["name"] or ""] if len(norm(x)) >= 4]
        text_norm = norm(row_text)
        bad = (self.symbol_re.search(row_text) or self.ensg_re.search(row_text)
               or any(re.search(rf"\b{re.escape(s)}\b", row_text, re.IGNORECASE) for s in own)
               or any(n in text_norm for n in own_norm))
        if bad:
            self.dropped += 1
        return not bad


def row_text(r):
    cs = r.get("credibleSet") or {}
    return " ".join(str(x) for x in [r["disease"]["name"], r.get("cohortId"), r.get("projectId"),
                                       r.get("statisticalMethod"), (cs.get("study") or {}).get("traitFromSource")])


def p_of(r):
    cs = r.get("credibleSet") or {}
    return neg_log10_p(r.get("pValueMantissa") or cs.get("pValueMantissa"),
                       r.get("pValueExponent") if r.get("pValueExponent") is not None else cs.get("pValueExponent"))


def top(groups, key, n=config.MAX_VIEW_ROWS):
    rows = sorted(groups, key=lambda g: (-(g[key] or 0), g["trait"]))
    return rows[:n], max(0, len(rows) - n)


def burden_view(rows):
    by_trait = defaultdict(list)
    for r in rows:
        by_trait[r["disease"]["name"]].append(r)
    groups = []
    for trait, rs in sorted(by_trait.items()):
        best = max(rs, key=lambda r: p_of(r) or 0)
        groups.append({
            "trait": trait, "scope": best["scope"], "hard_endpoint": is_hard_endpoint(trait),
            "direction_on_trait": best.get("directionOnTrait"), "direction_on_target": best.get("directionOnTarget"),
            "beta": best.get("beta"), "odds_ratio": best.get("oddsRatio"), "neg_log10_p": p_of(best),
            "cohort": best.get("cohortId"), "project": best.get("projectId"), "ancestry": best.get("ancestry"),
            "sample_size": best.get("studySampleSize"), "n_cases": best.get("studyCases"),
            "carriers": best.get("studyCasesWithQualifyingVariants"), "method": best.get("statisticalMethod"),
            "n_rows_for_trait": len(rs),
            "n_cohorts_for_trait": len({r.get("cohortId") for r in rs}),
            "directions_for_trait": sorted({str(r.get("directionOnTrait")) for r in rs}),
        })
    kept, cut = top(groups, "neg_log10_p")
    for i, g in enumerate(kept, 1):
        g["ref"] = f"burden_{i}"
    return {"channel": "burden", "rows": kept, "summary": {
        "n_rows_total": len(rows), "n_traits": len(groups), "n_traits_not_shown": cut,
        "n_protective_lof_rows": sum(r.get("directionOnTarget") == "LoF" and r.get("directionOnTrait") == "protect" for r in rows),
        "n_risk_lof_rows": sum(r.get("directionOnTarget") == "LoF" and r.get("directionOnTrait") == "risk" for r in rows),
        "cohorts": sorted({str(r.get("cohortId")) for r in rows}),
        "projects": sorted({str(r.get("projectId")) for r in rows}),
        "ancestries": sorted({str(r.get("ancestry")) for r in rows}),
        "n_hard_endpoint_traits": sum(g["hard_endpoint"] for g in groups)}}


def gwas_view(rows):
    by_trait = defaultdict(list)
    for r in rows:
        by_trait[r["disease"]["name"]].append(r)
    groups = []
    for trait, rs in sorted(by_trait.items()):
        best = max(rs, key=lambda r: p_of(r) or 0)
        cs = best.get("credibleSet") or {}
        study = cs.get("study") or {}
        groups.append({
            "trait": trait, "scope": best["scope"], "hard_endpoint": is_hard_endpoint(trait),
            "beta": cs.get("beta"), "neg_log10_p": p_of(best),
            "lead_consequence": ((cs.get("variant") or {}).get("mostSevereConsequence") or {}).get("label"),
            "n_samples": study.get("nSamples"), "n_cases": study.get("nCases"),
            "ld_populations": sorted({p["ldPopulation"] for p in study.get("ldPopulationStructure") or []}),
            "finemapping": cs.get("finemappingMethod"), "l2g_score": best.get("score"),
            "n_credible_sets_for_trait": len(rs),
        })
    kept, cut = top(groups, "neg_log10_p")
    for i, g in enumerate(kept, 1):
        g["ref"] = f"gwas_{i}"
    return {"channel": "gwas", "rows": kept, "summary": {
        "n_rows_total": len(rows), "n_traits": len(groups), "n_traits_not_shown": cut,
        "n_hard_endpoint_traits": sum(g["hard_endpoint"] for g in groups),
        "ld_populations": sorted({p for g in groups for p in g["ld_populations"]})}}


def tolerance_view(raw):
    c = {x["constraintType"]: x for x in raw["constraint"]}
    effects = [s["geneEffect"] for t in raw["essentiality"]["depmap"] for s in t["screens"] or []
               if s.get("geneEffect") is not None]
    lof, mis = c.get("lof", {}), c.get("mis", {})
    return {"channel": "tolerance",
            "loeuf": lof.get("oeUpper"), "lof_oe": lof.get("oe"), "pli": lof.get("score"),
            "missense_oe": mis.get("oe"), "missense_z": mis.get("score"),
            "depmap_mean_gene_effect": round(statistics.mean(effects), 4) if effects else None,
            "depmap_frac_dependent": round(sum(e < -0.5 for e in effects) / len(effects), 4) if effects else None,
            "depmap_n_screens": len(effects), "is_core_essential": raw["essentiality"]["is_essential"],
            "subcellular_location": raw["annotation"]["subcellular"], "biotype": raw["annotation"]["biotype"]}


def safety_view(rows, liabilities):
    kind = {config.DS_BURDEN: "burden", config.DS_GWAS: "gwas"}
    by_trait = defaultdict(list)
    for r in rows:
        by_trait[r["disease"]["name"]].append(r)
    groups = []
    for trait, rs in sorted(by_trait.items()):
        best = max(rs, key=lambda r: (p_of(r) or 0, r.get("score") or 0))
        groups.append({
            "trait": trait, "evidence_types": sorted({kind.get(r["datasourceId"], "mendelian") for r in rs}),
            "direction_on_trait": best.get("directionOnTrait"), "direction_on_target": best.get("directionOnTarget"),
            "neg_log10_p": p_of(best), "evidence_score": best.get("score"), "n_rows_for_trait": len(rs)})
    groups.sort(key=lambda g: (-("mendelian" in g["evidence_types"]), -(g["neg_log10_p"] or 0),
                               -(g["evidence_score"] or 0), g["trait"]))
    kept, cut = groups[:config.MAX_VIEW_ROWS], max(0, len(groups) - config.MAX_VIEW_ROWS)
    for i, g in enumerate(kept, 1):
        g["ref"] = f"safety_{i}"
    events = sorted({(l.get("event") or "", tuple(sorted({str(e.get("direction")) for e in l.get("effects") or []})))
                     for l in liabilities})
    return {"channel": "safety", "rows": kept,
            "curated_safety_events": [{"event": e, "directions": list(d)} for e, d in events if e],
            "summary": {"n_out_of_scope_traits": len(groups), "n_traits_not_shown": cut,
                        "n_mendelian_traits": sum("mendelian" in g["evidence_types"] for g in groups)}}


def variant_view(gwas_rows):
    cands = []
    for r in gwas_rows:
        v = (r.get("credibleSet") or {}).get("variant") or {}
        if v.get("position") is None:
            continue
        cons = ((v.get("mostSevereConsequence") or {}).get("label") or "")
        cands.append((any(c in cons for c in CODING), p_of(r) or 0, v))
    if not cands:
        return {"channel": "variant", "available": False}
    coding, _, v = max(cands, key=lambda c: (c[0], c[1], c[2]["position"]))
    return {"channel": "variant", "available": True, "chrom": v["chromosome"], "pos": v["position"],
            "ref": v["referenceAllele"], "alt": v["alternateAllele"]}


def main():
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        panel = list(csv.DictReader(f))
    all_symbols = set(symbol_map().values()) | {r["symbol"] for r in read_pool()}
    all_symbols = {s for s in all_symbols if not s.startswith("ENSG") and len(s) >= 3}
    scrub = Scrubber(all_symbols)
    VIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = []
    for g in panel:
        raw, code = load_raw(g["ensembl_id"]), g["gene_code"]
        ident = raw["identity"]
        keep = lambda rows: [r for r in rows if scrub.ok(row_text(r), ident)]
        before = scrub.dropped
        burden, gwas, other = keep(raw["burden"]), keep(raw["gwas"]), keep(raw["all_trait_evidence"])
        liab = [l for l in raw["safety_liabilities"] if scrub.ok(l.get("event") or "", ident)]
        views = {"burden": burden_view(burden), "gwas": gwas_view(gwas), "tolerance": tolerance_view(raw),
                 "safety": safety_view(other, liab), "variant": variant_view(raw["gwas"])}
        for agent, view in views.items():
            d = config.VIEWS_DIR / agent
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{code}.json").write_text(json.dumps(dict(view, gene_code=code), indent=1, sort_keys=True))
        log.append(f"- {code}: dropped {scrub.dropped - before} identity-revealing rows; "
                   f"burden traits {views['burden']['summary']['n_traits']}, gwas traits {views['gwas']['summary']['n_traits']}")
    VIEW_LOG.write_text("# build_views log\n\n" + "\n".join(log) + "\n")
    print(f"wrote views for {len(panel)} genes x {len(views)} agents; {scrub.dropped} rows dropped by identity scrub")


if __name__ == "__main__":
    main()

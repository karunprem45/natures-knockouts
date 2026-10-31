"""Phase 1d.2: per-gene raw pull -> data/raw/{ensembl_id}.json; drug rows -> data/labels/chembl/.

Default gene set: positives + backups + every pool gene eligible as a negative, so build_labels
can check each one. Cached for RAW_CACHE_TTL_H hours.
"""
import csv, json, sys, time
from concurrent.futures import ThreadPoolExecutor
import config
from data_layer.ot_client import OTClient
from data_layer.schema_probe import select
from data_layer.scope import scope_group
from data_layer.fetch_pool import POOL_CSV

SYMBOL_Q = 'query($q:String!){search(queryString:$q,entityNames:["target"],page:{index:0,size:5}){hits{id entity object{... on Target{approvedSymbol}}}}}'
ASSOC_Q = """query($id:String!,$i:Int!){target(ensemblId:$id){associatedDiseases(includeMeasurements:true,
  page:{index:$i,size:500}){rows{disease{id name} datasourceScores{id}}}}}"""
CS_FIELDS = ("credibleSet{studyLocusId beta pValueMantissa pValueExponent finemappingMethod "
             "variant{id chromosome position referenceAllele alternateAllele mostSevereConsequence{label}} "
             "study{id traitFromSource nSamples nCases cohorts ldPopulationStructure{ldPopulation relativeSampleSize}}}")
EVIDENCE_WANTED = ["id", "datasourceId", "disease{id name}", "directionOnTrait", "directionOnTarget",
                   "beta", "oddsRatio", "pValueMantissa", "pValueExponent", "cohortId", "projectId",
                   "ancestry", "studySampleSize", "studyCases", "studyCasesWithQualifyingVariants",
                   "statisticalMethod", "score", "clinicalStage", CS_FIELDS]
TARGET_WANTED = ["id", "approvedSymbol", "approvedName", "symbolSynonyms{label}", "nameSynonyms{label}",
                 "biotype", "geneticConstraint{constraintType oe oeLower oeUpper score}",
                 "isEssential", "depMapEssentiality{tissueName screens{geneEffect}}",
                 "subcellularLocations{location}", "safetyLiabilities{event datasource effects{direction}}"]


def resolve_symbol(ot, symbol):
    for h in ot.query(SYMBOL_Q, {"q": symbol})["search"]["hits"]:
        if h["entity"] == "target" and (h.get("object") or {}).get("approvedSymbol") == symbol:
            return h["id"]
    return None


def associated_diseases(ot, ensembl_id):
    out, i = [], 0
    while True:
        rows = ot.query(ASSOC_Q, {"id": ensembl_id, "i": i})["target"]["associatedDiseases"]["rows"]
        out.extend(rows)
        if len(rows) < 500:
            return out
        i += 1


def fetch(ot, ensembl_id):
    path = config.RAW_DIR / f"{ensembl_id}.json"
    if path.exists() and time.time() - path.stat().st_mtime < config.RAW_CACHE_TTL_H * 3600:
        return json.loads(path.read_text())
    tfields = " ".join(select("Target", TARGET_WANTED))
    t = ot.query(f'query($id:String!){{target(ensemblId:$id){{{tfields}}}}}', {"id": ensembl_id})["target"]
    efields = " ".join(select("Evidence", EVIDENCE_WANTED))
    diseases = associated_diseases(ot, ensembl_id)

    def ids_for(sources):
        return [d["disease"]["id"] for d in diseases
                if any(s["id"] in sources for s in d["datasourceScores"])]

    def rows_for(sources):
        ids = ids_for(sources)
        return ot.target_evidences(ensembl_id, ids, sources, efields) if ids else []

    genetic = rows_for([config.DS_BURDEN, config.DS_GWAS] + config.SAFETY_EXTRA_DATASOURCES)
    drug = rows_for(config.LABEL_DATASOURCES)
    for r in genetic:
        r["scope"] = scope_group(r["disease"]["name"])
    in_scope = [r for r in genetic if r["scope"]]
    raw = {
        "ensembl_id": ensembl_id,
        "identity": {"symbol": t["approvedSymbol"], "name": t.get("approvedName"),
                     "synonyms": sorted({s["label"] for k in ("symbolSynonyms", "nameSynonyms")
                                         for s in (t.get(k) or [])})},
        "burden": [r for r in in_scope if r["datasourceId"] == config.DS_BURDEN],
        "gwas": [r for r in in_scope if r["datasourceId"] == config.DS_GWAS],
        "constraint": t.get("geneticConstraint") or [],
        "essentiality": {"is_essential": t.get("isEssential"),
                         "depmap": t.get("depMapEssentiality") or []},
        "annotation": {"biotype": t.get("biotype"),
                       "subcellular": sorted({l["location"] for l in t.get("subcellularLocations") or []})},
        "all_trait_evidence": [r for r in genetic if not r["scope"]],
        "safety_liabilities": t.get("safetyLiabilities") or [],
    }
    config.CHEMBL_DIR.mkdir(parents=True, exist_ok=True)
    (config.CHEMBL_DIR / f"{ensembl_id}.json").write_text(json.dumps(drug))
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw))
    return raw


def default_gene_set(ot):
    ids, unresolved = {}, []
    for s in config.POSITIVES + config.BACKUP_POSITIVES:
        eid = resolve_symbol(ot, s)
        (ids.__setitem__(eid, s) if eid else unresolved.append(s))
    with POOL_CSV.open() as f:
        for r in csv.DictReader(f):
            if r["has_drug_evidence_in_scope"] == "0":
                ids.setdefault(r["ensembl_id"], r["symbol"])
    if unresolved:
        print(f"  could not resolve symbols: {unresolved}")
    return ids


def main(argv):
    ot = OTClient()
    genes = {a: a for a in argv} if argv else default_gene_set(ot)
    (config.DATA_DIR / "symbol_map.json").write_text(json.dumps(genes, indent=1, sort_keys=True))
    print(f"fetching {len(genes)} genes")

    def one(eid):
        try:
            raw = fetch(ot, eid)
            return f"  {genes[eid]:<12} burden={len(raw['burden']):<4} gwas={len(raw['gwas']):<5} other={len(raw['all_trait_evidence'])}"
        except Exception as e:  # R10: fail loudly, never fabricate
            return f"  {genes[eid]:<12} ERROR {e}"

    failed = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for line in pool.map(one, sorted(genes)):
            print(line)
            failed += "ERROR" in line
    print(f"done, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])

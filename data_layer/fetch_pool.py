"""Phase 1d.1: candidate pool = targets with in-scope, loss-of-function, protective burden evidence.

Also flags targets with in-scope drug evidence (clinical_precedence, i.e. ChEMBL) so build_labels
can exclude them from the negatives. The flag lives only in data/pool.csv, which no agent reads.
"""
import csv
from collections import defaultdict
import config
from data_layer.ot_client import OTClient
from data_layer.scope import scope_group

POOL_CSV = config.DATA_DIR / "pool.csv"
ASSOC_Q = """query($efo:String!,$ds:String!,$i:Int!){disease(efoId:$efo){associatedTargets(
  datasources:[{id:$ds,weight:1,propagate:true,required:true}],enableIndirect:true,
  page:{index:$i,size:500}){count rows{target{id approvedSymbol}}}}}"""
EVID_Q = """query($efo:String!,$ids:[String!]!,$ds:[String!],$cur:String){disease(efoId:$efo){
  evidences(ensemblIds:$ids,enableIndirect:true,datasourceIds:$ds,size:1000,cursor:$cur){
  cursor rows{target{id} disease{name} directionOnTrait directionOnTarget pValueExponent}}}}"""


def associated_targets(ot, efo, ds):
    out, i = {}, 0
    while True:
        d = ot.query(ASSOC_Q, {"efo": efo, "ds": ds, "i": i})["disease"]["associatedTargets"]
        out.update({r["target"]["id"]: r["target"]["approvedSymbol"] for r in d["rows"]})
        if len(d["rows"]) < 500:
            return out
        i += 1


def disease_evidences(ot, efo, ids, ds):
    rows, cur = [], None
    while True:
        d = ot.query(EVID_Q, {"efo": efo, "ids": ids, "ds": ds, "cur": cur})["disease"]["evidences"]
        rows.extend(d["rows"])
        cur = d["cursor"]
        if not cur or not d["rows"]:
            return rows


def main():
    ot = OTClient()
    candidates = {}
    for efo in config.POOL_SEED_DISEASES:
        found = associated_targets(ot, efo, config.DS_BURDEN)
        print(f"  {efo}: {len(found)} targets with burden evidence")
        candidates.update(found)
    ids = sorted(candidates)
    print(f"{len(ids)} distinct candidate targets")

    prot = defaultdict(int)
    best_p = {}
    drug_in_scope = set()
    for efo in config.POOL_SEED_DISEASES:
        for i in range(0, len(ids), 50):
            batch = ids[i:i + 50]
            for r in disease_evidences(ot, efo, batch, [config.DS_BURDEN]):
                if not scope_group(r["disease"]["name"]):
                    continue
                if r["directionOnTarget"] == "LoF" and r["directionOnTrait"] == "protect":
                    t = r["target"]["id"]
                    prot[t] += 1
                    if r["pValueExponent"] is not None:
                        best_p[t] = min(best_p.get(t, 0), r["pValueExponent"])
            for r in disease_evidences(ot, efo, batch, config.LABEL_DATASOURCES):
                if scope_group(r["disease"]["name"]):
                    drug_in_scope.add(r["target"]["id"])
        print(f"  scanned {efo}")

    POOL_CSV.parent.mkdir(parents=True, exist_ok=True)
    with POOL_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ensembl_id", "symbol", "n_protective_lof_rows", "best_p_exponent",
                    "has_drug_evidence_in_scope"])
        for t in ids:
            if prot[t]:
                w.writerow([t, candidates[t], prot[t], best_p.get(t, ""), int(t in drug_in_scope)])
    n = sum(1 for t in ids if prot[t])
    n_clean = sum(1 for t in ids if prot[t] and t not in drug_in_scope)
    print(f"pool: {n} targets with protective LoF evidence in scope, {n_clean} without drug evidence")
    print(f"wrote {POOL_CSV}")


if __name__ == "__main__":
    main()

"""Phase 1a: introspect the live OT schema, write schema_snapshot.json, report missing fields.

Fetchers build their GraphQL selections through `select()`, so a field that does not exist in
this release is dropped and logged instead of crashing the pipeline.
"""
import json
from pathlib import Path
from data_layer.ot_client import OTClient

SNAPSHOT = Path(__file__).with_name("schema_snapshot.json")
TYPES = ["Target", "Evidence", "CredibleSet", "Study", "Variant", "Constraint",
         "DepMapEssentiality", "GeneEssentialityScreen", "SafetyLiability", "LocationAndSource"]
WANTED = {
    "Evidence": ["directionOnTrait", "directionOnTarget", "beta", "oddsRatio", "pValueMantissa",
                 "pValueExponent", "cohortId", "projectId", "ancestry", "studySampleSize",
                 "studyCases", "studyCasesWithQualifyingVariants", "statisticalMethod",
                 "clinicalStage", "score", "datasourceId", "credibleSet"],
    "Constraint": ["constraintType", "oe", "oeUpper", "score"],
    "Target": ["geneticConstraint", "depMapEssentiality", "isEssential", "subcellularLocations",
               "safetyLiabilities", "symbolSynonyms", "nameSynonyms", "approvedName"],
}


def load():
    if not SNAPSHOT.exists():
        main()
    return json.loads(SNAPSHOT.read_text())


def select(type_name, wanted, snapshot=None, log=print):
    """Keep only fields that exist on type_name in the live schema; log what was dropped."""
    snapshot = snapshot or load()
    have = set(snapshot.get(type_name, []))
    kept = [f for f in wanted if f.split("{")[0].strip() in have]
    for f in wanted:
        if f not in kept:
            log(f"  schema: {type_name}.{f.split('{')[0].strip()} missing in this release, dropped")
    return kept


def main():
    ot = OTClient()
    q = "query($n:String!){__type(name:$n){fields{name}}}"
    snap = {}
    for t in TYPES:
        d = ot.query(q, {"n": t}, cache=False)["__type"]
        snap[t] = sorted(f["name"] for f in d["fields"]) if d else []
    meta = ot.query("{meta{dataVersion{year month}}}", cache=False)["meta"]["dataVersion"]
    snap["_release"] = f"{meta['year']}.{meta['month']}"
    SNAPSHOT.write_text(json.dumps(snap, indent=1))
    print(f"OT release {snap['_release']}")
    for t in TYPES:
        print(f"  {t}: {len(snap[t])} fields")
    missing = [f"{t}.{f}" for t, fs in WANTED.items() for f in fs if f not in snap.get(t, [])]
    print("  missing wanted fields: " + (", ".join(missing) if missing else "none"))
    print(f"wrote {SNAPSHOT}")


if __name__ == "__main__":
    main()

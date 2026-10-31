"""Therapeutic-area categories for diseases, used to coarsen Mendelian disease names in the
Safety view (eponymous syndromes can identify a gene; see frozen/AMENDMENTS.md #2)."""
import json
import config
from data_layer.ot_client import OTClient

CACHE = config.DATA_DIR / "disease_areas.json"
QUERY = "query($ids:[String!]!){diseases(efoIds:$ids){id therapeuticAreas{name}}}"


def areas_for(disease_ids):
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    missing = sorted(set(disease_ids) - set(cache))
    ot = OTClient()
    for i in range(0, len(missing), 100):
        found = ot.query(QUERY, {"ids": missing[i:i + 100]})["diseases"]
        for d in found:
            cache[d["id"]] = sorted({t["name"] for t in d["therapeuticAreas"] or []}) or ["other"]
        for did in missing[i:i + 100]:
            cache.setdefault(did, ["other"])  # id unknown to this release
    if missing:
        CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    return {d: cache[d] for d in disease_ids}

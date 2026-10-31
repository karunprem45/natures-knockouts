"""Phase 0: Open Targets GraphQL answers a minimal query for PCSK9."""
import sys
import requests
import config

QUERY = "query($id:String!){ target(ensemblId:$id){ id approvedSymbol } }"
try:
    r = requests.post(config.OT_GRAPHQL_URL, timeout=30,
                      json={"query": QUERY, "variables": {"id": "ENSG00000169174"}})
    r.raise_for_status()
    t = r.json()["data"]["target"]
    assert t and t["id"] == "ENSG00000169174", f"unexpected payload {r.text[:200]}"
except Exception as e:
    print(f"FAIL {e}"); sys.exit(1)
print(f"PASS {t['id']} -> {t['approvedSymbol']}")

"""Open Targets GraphQL client: retry with backoff, on-disk cache, cursor pagination."""
import hashlib, json, random, time
import requests
import config

CACHE_DIR = config.DATA_DIR / "cache" / "ot"


class OTError(RuntimeError):
    pass


class OTClient:
    def __init__(self, max_attempts=5, timeout=120):
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.session = requests.Session()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def query(self, query, variables=None, cache=True):
        variables = variables or {}
        key = hashlib.sha256(json.dumps([query, variables], sort_keys=True).encode()).hexdigest()
        path = CACHE_DIR / f"{key}.json"
        if cache and path.exists():
            return json.loads(path.read_text())
        for attempt in range(1, self.max_attempts + 1):
            try:
                r = self.session.post(config.OT_GRAPHQL_URL, timeout=self.timeout,
                                      json={"query": query, "variables": variables})
                if r.status_code in (429, 500, 502, 503, 504):
                    raise OTError(f"HTTP {r.status_code}")
                r.raise_for_status()
                body = r.json()
                if body.get("errors"):
                    raise OTError(f"GraphQL errors: {json.dumps(body['errors'])[:500]}")
                data = body["data"]
                if cache:
                    path.write_text(json.dumps(data))
                return data
            except (requests.RequestException, OTError) as e:
                if attempt == self.max_attempts or (isinstance(e, OTError) and "GraphQL" in str(e)):
                    raise
                wait = min(30, 2 ** attempt) + random.random()
                print(f"  ot retry {attempt}/{self.max_attempts} in {wait:.1f}s: {e}")
                time.sleep(wait)

    def target_evidences(self, ensembl_id, efo_ids, datasources, fields, page_size=1000, chunk=200):
        """All evidence rows for one target over efo_ids, paging with the cursor."""
        q = ("query($id:String!,$efo:[String!]!,$ds:[String!],$size:Int,$cur:String){"
             "target(ensemblId:$id){evidences(efoIds:$efo,datasourceIds:$ds,size:$size,cursor:$cur)"
             "{count cursor rows{" + fields + "}}}}")
        rows = []
        efo_ids = sorted(set(efo_ids))
        for i in range(0, len(efo_ids), chunk):
            cur = None
            while True:
                d = self.query(q, {"id": ensembl_id, "efo": efo_ids[i:i + chunk], "ds": datasources,
                                   "size": page_size, "cur": cur})
                ev = d["target"]["evidences"]
                rows.extend(ev["rows"])
                cur = ev["cursor"]
                if not cur or not ev["rows"]:
                    break
        return rows

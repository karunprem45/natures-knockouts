"""Phase 0: Ensembl REST returns a reference DNA window. Retries transient 5xx/429."""
import re, sys, time
import requests
import config

url = f"{config.ENSEMBL_REST_URL}/sequence/region/human/1:55039974..55040974?content-type=text/plain"
err = None
for attempt in range(4):
    try:
        time.sleep(config.ENSEMBL_SLEEP_S + 2 ** attempt - 1)
        r = requests.get(url, timeout=30)
        if r.status_code in (429, 500, 502, 503, 504):
            err = f"HTTP {r.status_code} (attempt {attempt + 1})"
            continue
        r.raise_for_status()
        seq = r.text.strip()
        assert re.fullmatch(r"[ACGTN]+", seq), f"not DNA: {seq[:60]}"
        assert len(seq) == 1001, f"expected 1001 bp, got {len(seq)}"
        print(f"PASS {len(seq)} bp, starts {seq[:20]}")
        sys.exit(0)
    except (requests.RequestException, AssertionError) as e:
        err = str(e)
print(f"FAIL {err}"); sys.exit(1)

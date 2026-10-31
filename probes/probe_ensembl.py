"""Phase 0: Ensembl REST returns a reference DNA window."""
import re, sys, time
import requests
import config

url = f"{config.ENSEMBL_REST_URL}/sequence/region/human/1:55039974..55040974?content-type=text/plain"
try:
    time.sleep(config.ENSEMBL_SLEEP_S)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    seq = r.text.strip()
    assert re.fullmatch(r"[ACGTN]+", seq), f"not DNA: {seq[:60]}"
    assert len(seq) == 1001, f"expected 1001 bp, got {len(seq)}"
except Exception as e:
    print(f"FAIL {e}"); sys.exit(1)
print(f"PASS {len(seq)} bp, starts {seq[:20]}")

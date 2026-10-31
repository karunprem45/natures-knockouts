"""Reference DNA windows from Ensembl REST (GRCh38), cached on disk, with retry on 5xx/429."""
import hashlib, re, time
import requests
import config

CACHE = config.DATA_DIR / "cache" / "ensembl"


def region(chrom, start, end):
    """1-based inclusive, forward strand."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{chrom}:{start}-{end}".encode()).hexdigest()[:24]
    path = CACHE / f"{key}.txt"
    if path.exists():
        return path.read_text()
    url = f"{config.ENSEMBL_REST_URL}/sequence/region/human/{chrom}:{start}..{end}:1?content-type=text/plain"
    for attempt in range(5):
        time.sleep(config.ENSEMBL_SLEEP_S + (2 ** attempt - 1))
        r = requests.get(url, timeout=60)
        if r.status_code in (429, 500, 502, 503, 504):
            continue
        r.raise_for_status()
        seq = r.text.strip().upper()
        if not re.fullmatch(r"[ACGTN]+", seq) or len(seq) != end - start + 1:
            raise ValueError(f"bad Ensembl sequence for {chrom}:{start}-{end} (len {len(seq)})")
        path.write_text(seq)
        return seq
    raise RuntimeError(f"Ensembl kept failing for {chrom}:{start}-{end}")

"""Standalone Evo 2 variant scorer: python score_variant.py <chrom> <pos> <ref> <alt> [window_bp]

Needs NVIDIA_API_KEY (build.nvidia.com). GRCh38, 1-based position. Prints JSON.
"""
import base64, io, json, os, sys, time
import numpy as np
import requests

EVO2 = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/forward"
BASES = "ACGT"


def ensembl(chrom, start, end):
    url = f"https://rest.ensembl.org/sequence/region/human/{chrom}:{start}..{end}:1?content-type=text/plain"
    for attempt in range(5):
        r = requests.get(url, timeout=60)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.text.strip().upper()
    raise RuntimeError("Ensembl kept failing")


def logits(seq, key):
    r = requests.post(EVO2, headers={"Authorization": f"Bearer {key}"}, timeout=300,
                      json={"sequence": seq, "output_layers": ["unembed"]})
    r.raise_for_status()
    npz = np.load(io.BytesIO(base64.b64decode(r.json()["data"])))
    arr = np.asarray(npz[npz.files[0]], dtype=np.float32)
    arr = arr[0] if arr.ndim == 3 else arr
    if arr.shape[0] != len(seq):
        raise RuntimeError(f"Evo 2 returned {arr.shape[0]} positions for {len(seq)} bp; refusing to align")
    return arr


def log_softmax(x):
    x = x - x.max(axis=-1, keepdims=True)
    return x - np.log(np.exp(x).sum(axis=-1, keepdims=True))


def seq_ll(seq, lp):
    ids = np.frombuffer(seq.encode(), dtype=np.uint8).astype(int)
    return float(lp[np.arange(len(ids) - 1), ids[1:]].sum())


def main(chrom, pos, ref, alt, window=2048):
    key = os.environ.get("NVIDIA_API_KEY") or sys.exit("set NVIDIA_API_KEY")
    pos, window = int(pos), int(window)
    start = pos - window // 2
    seq = ensembl(chrom, start, start + window - 1)
    idx = pos - start
    if seq[idx:idx + len(ref)] != ref:
        sys.exit(f"reference mismatch: genome has {seq[idx:idx + len(ref)]!r}, variant says {ref!r}")
    alt_seq = seq[:idx] + alt + seq[idx + len(ref):]
    lp_ref, lp_alt = log_softmax(logits(seq, key)), log_softmax(logits(alt_seq, key))
    out = {"delta_ll": round(seq_ll(alt_seq, lp_alt) - seq_ll(seq, lp_ref), 4), "window_bp": window}
    if len(ref) == len(alt) == 1:
        site = [lp_ref[i - 1, ord(a)] - lp_ref[i - 1, ord(seq[i])]
                for i in range(1, len(seq)) if seq[i] in BASES for a in BASES if a != seq[i]]
        v = float(lp_ref[idx - 1, ord(alt)] - lp_ref[idx - 1, ord(ref)])
        out.update(site_score=round(v, 4), site_percentile=round(float((np.asarray(site) < v).mean() * 100), 2))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])

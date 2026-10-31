"""NVIDIA Evo 2 (hosted NIM) /forward: per-position log-probabilities for a DNA sequence.

Evo 2 is byte-level: a base's vocabulary index is ord(base). logits[t] predicts token t+1, so
position 0 is never scored and a length-N sequence yields N-1 scores. If the returned length does
not match the input, we refuse to compute (BUILD.md Phase 3) instead of guessing the alignment.
"""
import base64, hashlib, io, json, os
import numpy as np
import requests
import config

CACHE = config.DATA_DIR / "cache" / "evo2"
BASES = "ACGT"


class Evo2Error(RuntimeError):
    pass


def _winner():
    p = config.PROBE_RESULTS / "evo2.json"
    if not p.exists():
        raise Evo2Error("run `python -m probes.probe_evo2` first")
    return json.loads(p.read_text())


def _decode(body, layer):
    if "data" not in body:
        raise Evo2Error(f"unexpected Evo 2 response keys {sorted(body)}")
    npz = np.load(io.BytesIO(base64.b64decode(body["data"])))
    keys = [k for k in npz.files if layer in k] or npz.files
    arr = np.asarray(npz[keys[0]], dtype=np.float32)
    return arr[0] if arr.ndim == 3 else arr


def logits(sequence):
    """(N, vocab) logits for `sequence`, cached by sha256(sequence) so reruns cost nothing."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{hashlib.sha256(sequence.encode()).hexdigest()}.npy"
    if path.exists():
        return np.load(path)
    win = _winner()
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        raise Evo2Error("NVIDIA_API_KEY not set")
    r = requests.post(win["url"], headers={"Authorization": f"Bearer {key}"}, timeout=300,
                      json={"sequence": sequence, "output_layers": [win["layer"]]})
    if r.status_code != 200:
        raise Evo2Error(f"Evo 2 HTTP {r.status_code}: {r.text[:200]}")
    arr = _decode(r.json(), win["layer"])
    if arr.shape[0] != len(sequence):
        raise Evo2Error(f"Evo 2 returned {arr.shape[0]} positions for a {len(sequence)}-bp input; refusing to align")
    np.save(path, arr)
    return arr


def log_softmax(x):
    x = x - x.max(axis=-1, keepdims=True)
    return x - np.log(np.exp(x).sum(axis=-1, keepdims=True))


def sequence_ll(sequence, lp=None):
    lp = log_softmax(logits(sequence)) if lp is None else lp
    ids = np.frombuffer(sequence.encode(), dtype=np.uint8).astype(int)
    return float(lp[np.arange(len(ids) - 1), ids[1:]].sum())


def score_snv(ref_seq, idx, ref, alt):
    """Score a substitution at 0-based `idx` of `ref_seq` against every other possible SNV in the window.

    Returns delta_ll (full alt − ref sequence log-likelihood) and the variant's percentile among all
    single-base substitutions in the window by the single-site score log p(alt) − log p(ref) at that site.
    Lower percentile = more disfavoured by the genome model = more likely truly disruptive."""
    if ref_seq[idx:idx + len(ref)] != ref:
        raise Evo2Error(f"reference mismatch at window index {idx}: genome has {ref_seq[idx:idx + len(ref)]!r}, "
                        f"variant says {ref!r}; not guessing strand or assembly")
    lp_ref = log_softmax(logits(ref_seq))
    alt_seq = ref_seq[:idx] + alt + ref_seq[idx + len(ref):]
    delta = sequence_ll(alt_seq) - sequence_ll(ref_seq, lp_ref)
    site = []
    for i in range(1, len(ref_seq)):
        b = ref_seq[i]
        if b not in BASES:
            continue
        for a in BASES:
            if a != b:
                site.append(lp_ref[i - 1, ord(a)] - lp_ref[i - 1, ord(b)])
    site = np.asarray(site)
    out = {"delta_ll": round(delta, 4), "window_bp": len(ref_seq), "n_possible_snvs": int(len(site)),
           "variant_type": "snv" if len(ref) == len(alt) == 1 else "indel"}
    if out["variant_type"] == "snv" and idx >= 1:
        v = float(lp_ref[idx - 1, ord(alt)] - lp_ref[idx - 1, ord(ref)])
        out.update(site_score=round(v, 4), site_percentile=round(float((site < v).mean() * 100), 2),
                   window_site_score_median=round(float(np.median(site)), 4))
    return out

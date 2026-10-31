"""Phase 0: NVIDIA Evo 2 /forward. Tries 40b then 7b, and both layer names; caches the winner."""
import base64, io, json, os, sys
import numpy as np
import requests
from dotenv import load_dotenv
import config

load_dotenv()
key = os.environ.get("NVIDIA_API_KEY")
if not key:
    print("FAIL NVIDIA_API_KEY not set -> drop the Variant agent"); sys.exit(1)
SEQ = ("ACGT" * 50)  # 200 bp
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
errors = []

def decode(resp):
    body = resp.json()
    if "data" in body:  # base64-encoded npz
        npz = np.load(io.BytesIO(base64.b64decode(body["data"])))
        return {k: list(npz[k].shape) for k in npz.files}
    return {k: type(v).__name__ for k, v in body.items()}

for url in config.EVO2_URLS:
    for layer in config.EVO2_LAYER_NAMES:
        try:
            r = requests.post(url, headers=headers, timeout=120, allow_redirects=True,
                              json={"sequence": SEQ, "output_layers": [layer]})
            if r.status_code != 200:
                errors.append(f"{url.split('/')[-2]}/{layer}: {r.status_code} {r.text[:120]}")
                continue
            shapes = decode(r)
        except Exception as e:
            errors.append(f"{url.split('/')[-2]}/{layer}: {e}")
            continue
        win = {"url": url, "layer": layer, "shapes": shapes, "seq_len": len(SEQ)}
        config.PROBE_RESULTS.mkdir(parents=True, exist_ok=True)
        (config.PROBE_RESULTS / "evo2.json").write_text(json.dumps(win, indent=2))
        print(f"PASS {url.split('/')[-2]} layer={layer} shapes={shapes}")
        sys.exit(0)

print("FAIL all combinations -> drop the Variant agent\n  " + "\n  ".join(errors)); sys.exit(1)

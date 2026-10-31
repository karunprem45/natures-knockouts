"""Small helpers shared by the Phase 1 builders."""
import csv, json, math
import config

LABEL_LOG = config.LABELS_DIR / "label_log.md"


def load_raw(ensembl_id):
    path = config.RAW_DIR / f"{ensembl_id}.json"
    return json.loads(path.read_text()) if path.exists() else None


def load_chembl(ensembl_id):
    path = config.CHEMBL_DIR / f"{ensembl_id}.json"
    return json.loads(path.read_text()) if path.exists() else []


def symbol_map():
    return json.loads((config.DATA_DIR / "symbol_map.json").read_text())


def read_pool():
    with (config.DATA_DIR / "pool.csv").open() as f:
        return list(csv.DictReader(f))


def neg_log10_p(mantissa, exponent):
    if mantissa is None or exponent is None or mantissa <= 0:
        return None
    return round(-(math.log10(mantissa) + exponent), 3)


def log(msg, path=LABEL_LOG):
    print(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(f"- {msg}\n")

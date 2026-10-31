"""Guards on every outgoing prompt: identity (R4), labels (R3) and the per-gene call budget (R1)."""
import csv, json, re, threading
from collections import defaultdict
import config


class IdentityLeak(RuntimeError):
    pass


class LabelLeak(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


_ENSG = re.compile(r"ENSG\d{11}")
_symbol_re = None


def _symbols():
    syms = set()
    path = config.DATA_DIR / "symbol_map.json"
    if path.exists():
        syms |= set(json.loads(path.read_text()).values())
    pool = config.DATA_DIR / "pool.csv"
    if pool.exists():
        with pool.open() as f:
            syms |= {r["symbol"] for r in csv.DictReader(f)}
    syms |= set(config.POSITIVES + config.BACKUP_POSITIVES)
    return sorted({s for s in syms if len(s) >= 3 and not s.startswith("ENSG")}, key=len, reverse=True)


def _symbol_pattern():
    global _symbol_re
    if _symbol_re is None:
        _symbol_re = re.compile(r"\b(" + "|".join(map(re.escape, _symbols())) + r")\b")
    return _symbol_re


def redact_identity(text):
    """Replace gene symbols / Ensembl IDs an agent wrote in its OUTPUT. Returns (text, found)."""
    found = sorted(set(_symbol_pattern().findall(text or "")) | set(_ENSG.findall(text or "")))
    if found:
        text = _ENSG.sub("[gene]", _symbol_pattern().sub("[gene]", text))
    return text, found


def assert_no_identity(prompt):
    _symbol_re = _symbol_pattern()
    if m := _ENSG.search(prompt):
        raise IdentityLeak(f"Ensembl ID {m.group(0)} in prompt")
    if m := _symbol_re.search(prompt):
        raise IdentityLeak(f"gene symbol {m.group(0)!r} in prompt")


def assert_no_labels(prompt):
    low = prompt.lower()
    for word in ("chembl", "clinical_precedence", "panel_labels"):
        if word in low:
            raise LabelLeak(f"{word!r} in prompt")


class Budget:
    """Counts LLM calls per (arm, gene); the cap is identical for every arm."""

    def __init__(self, cap=config.MAX_LLM_CALLS_PER_GENE):
        self.cap = cap
        self.used = defaultdict(int)
        self._lock = threading.Lock()

    def take(self, arm, gene_code):
        with self._lock:
            if self.used[(arm, gene_code)] >= self.cap:
                raise BudgetExceeded(f"{arm}/{gene_code}: {self.cap} calls used")
            self.used[(arm, gene_code)] += 1
            return self.used[(arm, gene_code)]

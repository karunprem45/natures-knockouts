"""Phase 1d.3: decide positives and eligible negatives. Writes data/labels/candidates.json.

Positives: the fixed list in config, kept only if they have in-scope burden or GWAS evidence;
any that do not are replaced from BACKUP_POSITIVES, in order, and the swap is logged.
Negatives: pool genes with in-scope protective LoF burden evidence, no in-scope drug evidence,
not a positive or backup.
"""
import json
import config
from data_layer.common import LABEL_LOG, load_chembl, load_raw, log, read_pool, symbol_map
from data_layer.scope import scope_group


def has_in_scope_genetics(raw):
    return bool(raw and (raw["burden"] or raw["gwas"]))


def has_protective_lof(raw):
    return any(r.get("directionOnTarget") == "LoF" and r.get("directionOnTrait") == "protect"
               for r in raw["burden"])


def has_drug_in_scope(ensembl_id):
    return any(scope_group(r["disease"]["name"]) for r in load_chembl(ensembl_id))


def main():
    LABEL_LOG.unlink(missing_ok=True)
    by_symbol = {s: e for e, s in symbol_map().items()}
    positives, backups = [], list(config.BACKUP_POSITIVES)
    for s in config.POSITIVES:
        eid = by_symbol.get(s)
        if eid and has_in_scope_genetics(load_raw(eid)):
            positives.append((s, eid))
            continue
        while backups:
            b = backups.pop(0)
            beid = by_symbol.get(b)
            if beid and has_in_scope_genetics(load_raw(beid)):
                log(f"positive {s} has no in-scope burden/GWAS evidence -> replaced by {b}")
                positives.append((b, beid))
                break
        else:
            log(f"positive {s} has no in-scope evidence and no backup is left -> dropped")

    excluded = set(config.POSITIVES + config.BACKUP_POSITIVES)
    negatives = []
    for r in read_pool():
        eid, s = r["ensembl_id"], r["symbol"]
        if s in excluded or r["has_drug_evidence_in_scope"] != "0":
            continue
        raw = load_raw(eid)
        if raw is None:
            log(f"negative candidate {s} has no raw file -> skipped")
        elif not has_protective_lof(raw):
            log(f"negative candidate {s}: no protective LoF row in per-gene pull -> skipped")
        elif has_drug_in_scope(eid):
            log(f"negative candidate {s}: drug evidence in scope at gene level -> skipped")
        else:
            negatives.append((s, eid))

    out = {"positives": [{"symbol": s, "ensembl_id": e} for s, e in positives],
           "negatives_eligible": [{"symbol": s, "ensembl_id": e} for s, e in sorted(negatives)]}
    (config.LABELS_DIR / "candidates.json").write_text(json.dumps(out, indent=1))
    print(f"{len(positives)} positives, {len(negatives)} eligible negatives")


if __name__ == "__main__":
    main()

"""T3 step A: predicted loss-of-function variants per panel gene from Ensembl (GRCh38).

  python -m exploratory.evo2_coding.collect     -> exploratory/evo2_coding/variants.csv

Rule, identical for every gene: from /overlap/id/<gene>?feature=variation keep consequences stop_gained,
splice_acceptor_variant, splice_donor_variant, frameshift_variant. Rank single-nucleotide variants first,
then variants with any clinical-significance annotation, then by consequence (stop, splice, frameshift),
then by variant ID; keep 5. The alt allele is the first listed alternative (alleles are forward-strand).
"""
import csv, time
import requests
import config

HERE = config.ROOT / "exploratory" / "evo2_coding"
KEEP = ["stop_gained", "splice_acceptor_variant", "splice_donor_variant", "frameshift_variant"]
PER_GENE = 5


def fetch(gene):
    for attempt in range(5):
        r = requests.get(f"{config.ENSEMBL_REST_URL}/overlap/id/{gene}",
                         params={"feature": "variation", "content-type": "application/json"}, timeout=180)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Ensembl kept failing for {gene}")


def is_snv(a):
    return len(a) >= 2 and all(len(x) == 1 and x in "ACGT" for x in a[:2])


def main():
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        panel = list(csv.DictReader(f))
    rows, short = [], []
    for g in panel:
        time.sleep(config.ENSEMBL_SLEEP_S)
        lof = [v for v in fetch(g["ensembl_id"]) if v.get("consequence_type") in KEEP and len(v.get("alleles", [])) >= 2
               and v.get("strand", 1) == 1]
        lof.sort(key=lambda v: (not is_snv(v["alleles"]), not v.get("clinical_significance"),
                                KEEP.index(v["consequence_type"]), v["id"]))
        chosen = lof[:PER_GENE]
        if len(chosen) < PER_GENE:
            short.append(f"{g['gene_code']}: {len(chosen)}")
        for v in chosen:
            ref, alt = v["alleles"][0], v["alleles"][1]
            rows.append({"gene_code": g["gene_code"], "chrom": v["seq_region_name"], "pos": v["start"],
                         "ref": ref, "alt": alt, "consequence": v["consequence_type"], "variant_id": v["id"],
                         "snv": int(is_snv(v["alleles"])), "clinical": ";".join(v.get("clinical_significance") or []),
                         "source": f"Ensembl overlap ({v.get('source', '?')})", "n_lof_in_gene": len(lof)})
        print(f"  {g['gene_code']}: {len(lof)} LoF variants, kept {len(chosen)}", flush=True)
    with (HERE / "variants.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} variants for {len(panel)} genes; genes with fewer than {PER_GENE}: {short or 'none'}")


if __name__ == "__main__":
    main()

"""T3 step C: score the coding variants on NVIDIA's hosted Evo 2 40B.

  python -m exploratory.evo2_coding.score     -> scores.csv, gene_summary.json

4,096 bp window centred on each variant; the reference allele must match the genome or the variant gets an
error record and is skipped (tools/evo2.score_snv refuses); delta = ll(alt) - ll(ref); single-nucleotide
variants also get their percentile among every possible base change in the window. Windows are cached by
sha256 in data/cache/evo2, so reruns are free.
"""
import csv, json
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import config
from tools import ensembl, evo2

HERE = config.ROOT / "exploratory" / "evo2_coding"
WINDOW = 4096
PCT_THRESHOLD = 10.0


def score(v):
    pos = int(v["pos"])
    start = pos - WINDOW // 2
    try:
        seq = ensembl.region(v["chrom"], start, start + WINDOW - 1)
        out = evo2.score_snv(seq, pos - start, v["ref"], v["alt"])
        return dict(v, ok=1, error="", **out)
    except Exception as e:
        return dict(v, ok=0, error=str(e)[:200])


def main():
    with (HERE / "variants.csv").open() as f:
        variants = list(csv.DictReader(f))
    results = []
    with ThreadPoolExecutor(6) as pool:
        futs = [pool.submit(score, v) for v in variants]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            results.append(r)
            tag = f"pct {r.get('site_percentile')}" if r["ok"] else f"ERROR {r['error'][:60]}"
            print(f"  [{i}/{len(variants)}] {r['gene_code']} {r['variant_id']} {r['consequence']} {tag}", flush=True)
    results.sort(key=lambda r: (r["gene_code"], r["variant_id"]))
    cols = ["gene_code", "variant_id", "chrom", "pos", "ref", "alt", "consequence", "snv", "ok", "error",
            "delta_ll", "site_percentile", "site_score", "window_bp", "source"]
    with (HERE / "scores.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    summary = {}
    for code in sorted({r["gene_code"] for r in results}):
        ok = [r for r in results if r["gene_code"] == code and r["ok"]]
        pct = [r["site_percentile"] for r in ok if r.get("site_percentile") is not None]
        summary[code] = {
            "n_variants_scored": len(ok),
            "n_errors": sum(1 for r in results if r["gene_code"] == code and not r["ok"]),
            "strongest_delta_ll": round(min(r["delta_ll"] for r in ok), 4) if ok else None,
            "lowest_site_percentile": round(min(pct), 2) if pct else None,
            "median_site_percentile": round(float(np.median(pct)), 2) if pct else None,
            "share_below_10th_percentile": round(sum(p < PCT_THRESHOLD for p in pct) / len(pct), 3) if pct else None,
            "variant_types": sorted({r["consequence"] for r in ok}),
        }
    (HERE / "gene_summary.json").write_text(json.dumps(summary, indent=1))
    good = [r for r in results if r["ok"]]
    pcts = [r["site_percentile"] for r in good if r.get("site_percentile") is not None]
    print(f"scored {len(good)}/{len(results)}, errors {len(results) - len(good)}; median site percentile "
          f"{np.median(pcts):.1f} (lead GWAS variants were 59)")


if __name__ == "__main__":
    main()

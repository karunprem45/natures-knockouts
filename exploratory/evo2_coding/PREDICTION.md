# T3 prediction: Evo 2 on coding variants

**Post-freeze extension, not pre-registered in frozen/.** Committed before any coding variant was collected or scored.

## Prediction

> Given coding loss-of-function variants instead of non-coding lead tags, the Variant channel contributes more than +0.038.

## Why we expect it

With GWAS lead variants as input, the Variant agent added +0.038 AUROC over A3 (2 seeds, CI includes zero), and the variants it scored were mostly non-coding tags (median site percentile 59, i.e. ordinary for their window). Predicted loss-of-function variants (stop-gained, frameshift, splice donor/acceptor) are the kind of change a genome language model should flag as disruptive.

## How it will be tested

- **Variants:** for each of the 40 panel genes, up to 5 predicted loss-of-function variants from Ensembl (consequence `stop_gained`, `frameshift_variant`, `splice_acceptor_variant` or `splice_donor_variant`), single-nucleotide variants preferred; recorded in `variants.csv` with chrom, pos, ref, alt, consequence and source. The cached burden evidence is gene-level (no variant coordinates), so Ensembl is the source.
- **Scoring:** NVIDIA's hosted Evo 2 40B (`/forward`, `unembed` layer), 4,096 bp window centred on each variant; the reference base must match the genome or the variant is skipped with an error record; delta = log-likelihood(alt) − log-likelihood(ref); single-nucleotide variants also get their percentile among every possible base change in the window; every window cached by sha256.
- **Per-gene summary given to the Variant agent:** number scored, strongest (most negative) delta, lowest site percentile, and the share of single-nucleotide variants below the 10th percentile. Coordinates never reach a prompt.
- **Arm:** A3 + Variant, seed 1, everything else unchanged; the Variant agent reads the coding summary instead of the lead-variant numbers.
- **Comparison:** paired Δ AUROC of A3 + Variant (coding) against frozen A3 seed 1, set beside the same contrast for the existing lead-variant run (A3 + Variant seed 1 − A3 seed 1) and the earlier 2-seed +0.038.
- **Judged against the measured noise floor (0.062 AUROC, T1), not against zero.**

## What would count

The prediction holds if the coding-variant contrast exceeds +0.038. It is a real effect only if it also exceeds the 0.062 noise floor. Anything else is reported as not supported.

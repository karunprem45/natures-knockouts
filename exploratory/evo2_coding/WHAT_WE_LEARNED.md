# What we learned from Evo 2 on coding variants

**Post-freeze extension, not pre-registered in frozen/.** Full numbers in [`RESULTS.md`](RESULTS.md).

We wrote a prediction down before the data existed, tested it, and it failed. The way it failed tells us what a genome language model can and cannot contribute to this question.

## The prediction, as committed

Committed in [`PREDICTION.md`](PREDICTION.md) (commit `a87c90d`) before any variant was collected or scored:

> Given coding loss-of-function variants instead of non-coding lead tags, the Variant channel contributes more than +0.038.

**Verdict: not supported.** A3 + Variant with coding variants, against A3 on the same seed: **−0.006** (95% CI −0.165 to +0.132), 0.1× the measured noise floor of 0.062. The lead-tag run on the same seed gave +0.007.

## The input fix worked

The earlier diagnosis was that GWAS lead variants are mostly non-coding tags, so Evo 2 had little disruption to detect. We replaced them with 200 predicted loss-of-function variants from Ensembl (5 per gene; 188 stop-gained, 9 splice-site, 3 frameshift), scored on NVIDIA's hosted Evo 2 40B with a reference-base check. All 200 scored, 0 errors.

| Input | Median site percentile (0 = most disfavoured change in its window) |
| --- | --- |
| GWAS lead tags | 59 |
| Coding loss-of-function variants | **4.4** |

The coding variants were far more disruptive to Evo 2. The diagnosis was right at the DNA level.

## But disruption did not separate targets from negatives

| Gene group | Median of per-gene median percentiles |
| --- | --- |
| Known targets (12) | 3.4 |
| Hard negatives (28) | 5.2 |

Almost every gene's predicted loss-of-function variants look disruptive, in targets and negatives alike.

## Interpretation

Evo 2 reports that a variant **breaks a gene**. It does not report whether breaking that gene **benefits the carrier**, and that second question is the one that separates a drug target from a hard negative.

On this panel every gene is a loss-of-function gene of the protective kind: the 28 negatives were selected for in-scope protective loss-of-function burden evidence, and the 12 positives are established protective loss-of-function targets. So all of them carry real disruption, and a channel that measures disruption has nothing to rank on. Better variants were necessary but not sufficient.

## What would actually test the channel

A panel where loss of function is **harmful** for some genes and **protective** for others, for example adding genes whose loss-of-function variants cause disease. There, "this variant breaks the gene" combined with the other agents' evidence about consequences could separate genes, and the Variant channel would have something to contribute. On a panel built entirely from protective loss-of-function genes it cannot, and our result shows that.

Two design notes for that test: the Variant agent only answers needs in round 1 and reaches the score through other agents' revisions, so its influence is indirect by construction; and the comparison should be judged against the 0.062 floor, as here.

# Results

40 genes, 12 positives (chance AUPRC 0.300). LLM arms: mean over 2 seeds, per-seed mean ± sd in brackets. CIs: 1,000 gene resamples, seed 20261031. Δ columns are paired: both arms scored on the same resample.

## Headline (pre-registered)

**Δ AUROC (A3 − A1) = +0.008 (-0.074, +0.103)**  
A3 permutation null (1,000 label shuffles, seed-averaged scores): AUROC 0.784, p = 0.003

## All arms

| Arm | What | AUROC (95% CI) | AUPRC (95% CI) | P@12 | Calls/gene | $ spent/run | Δ AUROC vs S4 | Δ AUROC vs A1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | LOEUF alone | 0.720 (0.559–0.868) | 0.435 (0.277–0.732) | 0.42 | 0.0 | 0.00 | -0.030 (-0.241, +0.213) | -0.054 (-0.260, +0.146) |
| S2 | burden strength alone | 0.662 (0.487–0.827) | 0.396 (0.225–0.661) | 0.42 | 0.0 | 0.00 | -0.088 (-0.255, +0.069) | -0.112 (-0.309, +0.102) |
| S3 | GWAS strength alone | 0.440 (0.270–0.587) | 0.276 (0.146–0.446) | 0.08 | 0.0 | 0.00 | -0.310 (-0.446, -0.155) | -0.333 (-0.512, -0.152) |
| S4 | all features, z-scored, equal weights | 0.750 (0.542–0.910) | 0.697 (0.428–0.884) | 0.58 | 0.0 | 0.00 | — | -0.024 (-0.232, +0.169) |
| A1 | single agent, all views | 0.774 (0.616–0.903) [0.774 ± 0.023] | 0.653 (0.392–0.851) | 0.50 | 3.0 | 1.09 | +0.024 (-0.169, +0.232) | — |
| A3 | collective: 4 agents + skeptic on the board | 0.782 (0.641–0.895) [0.782 ± 0.012] | 0.630 (0.408–0.836) | 0.54 | 10.0 | 1.32 | +0.032 (-0.121, +0.210) | +0.008 (-0.074, +0.103) |
| A3_isolated | A3 round 0 only (no needs, skeptic, revisions) | 0.853 (0.729–0.948) [0.853 ± 0.016] | 0.736 (0.479–0.907) | 0.50 | 0.0 | 0.00 | +0.103 (-0.054, +0.284) | +0.080 (-0.004, +0.173) |
| A3_noskeptic | A3 without skeptic challenges | 0.844 (0.713–0.939) [0.844 ± 0.011] | 0.727 (0.475–0.901) | 0.58 | 0.0 | 0.00 | +0.094 (-0.043, +0.266) | +0.070 (-0.008, +0.166) |
| A3_noburden | A3 without burden agent | 0.732 (0.589–0.862) [0.732 ± 0.038] | 0.545 (0.329–0.777) | 0.46 | 0.0 | 0.00 | -0.018 (-0.186, +0.155) | -0.042 (-0.142, +0.067) |
| A3_nogwas | A3 without GWAS agent | 0.778 (0.628–0.905) [0.778 ± 0.017] | 0.606 (0.368–0.820) | 0.58 | 0.0 | 0.00 | +0.028 (-0.130, +0.230) | +0.004 (-0.077, +0.099) |
| A3_notolerance | A3 without tolerance agent | 0.760 (0.611–0.884) [0.760 ± 0.031] | 0.589 (0.374–0.809) | 0.54 | 0.0 | 0.00 | +0.010 (-0.146, +0.193) | -0.014 (-0.099, +0.089) |
| A3_nosafety | A3 without safety agent | 0.795 (0.652–0.907) [0.795 ± 0.027] | 0.614 (0.387–0.831) | 0.54 | 0.0 | 0.00 | +0.045 (-0.088, +0.207) | +0.021 (-0.100, +0.163) |

Ablations re-score the saved A3 boards: 0 extra LLM calls. $ spent includes calls lost to rate limits and rerun under one rule (RERUN_LOG.md).

## Top-ranked negatives (hypotheses, not validated targets)

| A3 rank | Gene | A3 score |
| --- | --- | --- |
| 6 | ACVR1C (Gene_06) | +2.513 |
| 7 | ZNF229 (Gene_20) | +2.475 |
| 8 | PKD1L3 (Gene_13) | +2.450 |
| 10 | GLTPD2 (Gene_05) | +2.300 |
| 11 | ZNF251 (Gene_32) | +2.275 |

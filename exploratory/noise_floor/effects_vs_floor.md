# Every reported effect against the measured noise floor

**Post-freeze extension, not pre-registered.** Floor = 0.062 AUROC, the 95th percentile of the 10 pairwise differences between 5 replicates of A3 (`RESULTS.md`).

| Effect | Size | × floor | Above floor? | Comparison type |
| --- | --- | --- | --- | --- |
| Coordination penalty (A3 − round 0), frozen seeds 1-2 | 0.071 | 1.1× | yes | paired, same boards |
| Coordination penalty, mean over all replicates | 0.053 | 0.9× | no | paired, same boards |
| Multi-agent vs single (round 0 − A1) | 0.080 | 1.3× | yes | different runs |
| Evo 2 Variant channel (A3 + Variant − A3) | 0.038 | 0.6× | no | different runs |
| Calibrated skeptic on panel 2 (calibrated − flat) | 0.004 | 0.1× | no | paired, same board |
| A2-constrained vs round 0 (seed 1) | 0.013 | 0.2× | no | different runs |
| Coordination penalty sign across replicates | 5/5 negative | — | sign test p = 0.031 | paired, each replicate |

**How to read the comparison type.** The floor is the spread between whole reruns of one arm, so it is the right yardstick for contrasts between different runs (round 0 − A1, the Evo 2 run). The coordination penalty and the calibrated-skeptic contrast re-score the same board two ways, so rerun variation is largely shared between the two sides; for the penalty, the per-replicate table in `RESULTS.md` is the more direct test of whether it is real.

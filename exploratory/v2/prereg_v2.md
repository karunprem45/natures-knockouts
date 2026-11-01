# Pre-registration v2: a calibrated skeptic, tested on a fresh panel

**Post-freeze extension.** Written, committed and tagged `prereg-v2` before panel 2 was built and before any panel-2 score was computed. Nothing below changes after the tag.

## Question

On panel 1, the skeptic's challenges were non-discriminative (for example `biomarker_only` fired on 83% of known targets and 84% of negatives), and a flat 0.5 discount on every challenged channel lowered AUROC (A3 − round 0 = −0.071, 95% CI −0.139 to −0.013). Does a discount calibrated to how discriminative each challenge type was recover that loss on genes the calibration never saw?

## The fix, fitted on panel 1 only

Source: frozen panel-1 A3 boards, both seeds (24 positive and 56 negative gene-runs). Rate = share of gene-runs on which a challenge type fired at least once.

```
multiplier_t = 1 - 0.5 * max(0, (rate_neg - rate_pos) / rate_neg)      (1.0 if rate_neg == 0)
```

One formula for every type. A challenged channel takes the minimum multiplier over the types that name it (the flat scorer applies 0.5 once, so this keeps the same "applied once" structure).

| Challenge type | Rate on positives | Rate on negatives | Multiplier |
| --- | --- | --- | --- |
| biomarker_only | 0.833 | 0.839 | 0.996 |
| direction_conflict | 0.000 | 0.286 | 0.500 |
| essential_gene | 0.000 | 0.214 | 0.500 |
| single_ancestry | 0.250 | 0.482 | 0.759 |
| single_cohort | 0.083 | 0.357 | 0.617 |
| underpowered | 0.042 | 0.089 | 0.733 |

Stored in `exploratory/v2/calibration.json`; applied by `exploratory/v2/scoring_v2.py`. `scoring.py` is unchanged.

## Panel 2 construction rule

- **Positives:** the same 12 as panel 1 (there is no second set of comparably established protective loss-of-function targets).
- **Negatives:** 28 sampled with `random.Random(20261101)` from the 89 eligible negatives in `data/labels/candidates.json`, sorted by Ensembl ID, **excluding all 28 panel-1 negatives**.
- **Codes:** the 40 genes shuffled with the same generator and coded `Gene_41` to `Gene_80`, so nothing collides with panel 1.
- **Views:** built with the same code as panel 1 (`data_layer/build_views.py` functions, same identity scrub, Mendelian diseases as categories), written to `data/views_v2/`. The isolation test is re-run on them and its check count reported.

## Run

- One A3 run on panel 2, seed 1: Gemini 3 Flash on Vertex AI, temperature 0, reasoning effort low, 10-call cap per gene, the unchanged agents, prompts, loop and skeptic.
- That one board is scored three ways, so the comparison is like-for-like:
  - `A3_v2_calibrated`: `exploratory/v2/scoring_v2.py` with the multipliers above
  - `A3_v2_flat`: `scoring.py`, flat 0.5 (the original)
  - `A3_v2_round0`: round-0 artifacts only, `scoring.py`

## Metric and contrasts

- Metric: AUROC, with AUPRC and precision@12 reported.
- **Primary contrast:** `A3_v2_calibrated − A3_v2_flat`, paired bootstrap over genes, 1,000 resamples, seed 20261031.
- Secondary: `A3_v2_calibrated − A3_v2_round0` and `A3_v2_flat − A3_v2_round0`.
- Reference: the panel-2 noise floor between two runs of one configuration is about 0.03 AUROC (measured by the A2 rerun of round 0 on panel 1).

## How each outcome will be described

| Outcome | Description |
| --- | --- |
| Calibrated > flat, approaching round 0 | The diagnosed failure was fixed by a pre-registered correction on genes it never saw |
| Calibrated > flat, still below round 0 | Calibration helps but does not close the gap; here a skeptic costs more than it returns |
| No improvement | The problem is not calibration; skeptic-style self-critique does not pay on this task |

## Disclosed in advance

Panel 2 shares the 12 positives; only the negatives are fresh. The multipliers were fitted on panel 1 and frozen here before panel 2 existed. One parameter set was fitted; no agent was trained. One seed.

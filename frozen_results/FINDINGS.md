# Findings

Panel frozen at `prereg` (`12b8c58`); raw outputs frozen at `results-raw` (`28a0e95`) before any A1/A3 metric was computed. Numbers below are from `arms_table.md`.

## 1. Headline: the collective ties the single agent

**Δ AUROC (A3 − A1) = +0.008, 95% CI −0.074 to +0.103** (pre-registered primary endpoint, paired bootstrap, mean over 2 seeds).

- A3 AUROC 0.782 (0.641–0.895); A1 0.774 (0.616–0.903); the strongest scripted baseline S4 0.750 (0.542–0.910).
- A3 clearly beats chance: permutation p = 0.003.
- A3 is the more stable arm across seeds (AUROC sd 0.012 vs 0.023).
- Same model and similar spend: A1 $1.09 per 40-gene run in 3 calls/gene, A3 $1.32 in 10 calls/gene.

Per BUILD.md §9 this is the "A3 ≈ S4 / tie" outcome: a dominant-signal regime where the value is provenance, error-catching and cost transparency, not a lift.

## 2. The decentralised views help; the coordination rounds did not

| Variant (re-scored from the same A3 boards) | AUROC | Δ vs A1 (paired) |
| --- | --- | --- |
| A3, round 0 only: isolated specialists, no needs, skeptic or revisions | **0.853** | +0.080 (−0.004, +0.173) |
| A3 without skeptic challenges | 0.844 | +0.070 (−0.008, +0.166) |
| A3, full loop | 0.782 | +0.008 (−0.074, +0.103) |

Four specialists that each see one slice of the evidence and never talk did better than one agent that sees everything. Rounds 1–2 then gave that advantage back. **These are secondary, post-hoc-interpretable ablations: the headline stays A3 vs A1 as pre-registered, and we did not re-tune anything after seeing them.**

Why the skeptic hurt:
- It challenged the burden channel on 7 of 12 positives and 21 of 28 negatives in seed 1 (8/12 and 23/28 in seed 2) — about the same rate whatever the label, so it carries little information.
- The most common challenge was `biomarker_only` on burden (46–47 per seed). Most in-scope burden evidence *is* biomarker-level, so the 0.5 discount mostly shrank the strongest channel for every gene.
- Mean rank of the 12 positives fell from 10.7 without the skeptic to 12.5 with it (`figures/4_skeptic_rank_shift.png`).
- Revisions barely moved verdicts (mean change in signed verdict +0.08 / −0.02 on positives, ≈0 on negatives).

This is the measured answer to "agents never add validation on their own": we added it, and an over-eager validator cost accuracy. A calibrated skeptic (challenges that must cite a row, or a discount scaled by evidence) is the obvious next experiment, run on a fresh panel.

## 3. Which evidence matters

Removing one agent's channel: burden is the most important (AUROC 0.732 without it), then tolerance (0.760), GWAS (0.778); removing safety *raised* AUROC slightly (0.795).

## 4. Discovery: top-ranked negatives (hypotheses, not validated targets)

| A3 rank | Gene |
| --- | --- |
| 6 | ACVR1C |
| 7 | ZNF229 |
| 8 | PKD1L3 |
| 10 | GLTPD2 |
| 11 | ZNF251 |

ACVR1C (ALK7) has protective loss-of-function evidence for fat distribution and type 2 diabetes; the others are weaker. None is claimed as a target.

## Limitations (stated by us, before a judge asks)

1. **Small panel.** 40 genes, 12 positives: every CI is wide. S4, A1 and A3 overlap.
2. **Study-intensity confound.** Famous positives carry far more evidence rows; every arm can partly score "how well studied".
3. **Anonymisation is partial.** Names, IDs and drug data are removed and Mendelian diseases coarsened to categories (amendment #2), but trait patterns remain: 2 of 320 A3 verdicts still named a gene (redacted and flagged).
4. **Direction labels.** Open Targets assigns "protect" for quantitative traits from the sign of beta, so lowering HDL reads as protective.
5. **Amendments after `prereg`**, all before any LLM arm ran: model `gemini-2.5-flash` → `gemini-3-flash-preview` on Vertex AI, and the Safety-view coarsening (`frozen/AMENDMENTS.md`). The S1–S4 feature definitions were committed after the tag but before any LLM arm.
6. **Reruns.** 16 gene-runs lost to rate limits were rerun under one rule for every arm (`RERUN_LOG.md`).
7. **No Variant agent.** No Evo 2 access, so the DNA-level channel was dropped at the Phase 0 gate.

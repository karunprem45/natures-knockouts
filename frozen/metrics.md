# Pre-registered analysis plan

Frozen at the `prereg` git tag, before any arm is run. Nothing below changes afterwards.

## Panel
`frozen/panel.csv`: 40 genes (12 positives + 28 hard negatives), sampled with `config.SEED`.
Labels live in `data/labels/panel_labels.csv` and are read only by `eval/`.

- **Positive**: a gene from `config.POSITIVES` with in-scope burden or GWAS evidence. All 12 qualified; no backups used.
- **Negative**: a gene with in-scope, loss-of-function, protective burden evidence in Open Targets 26.09 and **no** in-scope drug evidence (`clinical_precedence`), sampled from 89 eligible genes.

## Primary endpoint
**Δ AUROC = AUROC(A3) − AUROC(A1)**, the same model and call cap in both arms, mean over 2 seeds.
95% CI from a paired bootstrap over genes (1,000 resamples, `config.SEED`): both arms are scored on every resample.

## Secondary endpoints
- AUROC of A3 vs S4 (paired bootstrap, as above)
- AUPRC and precision@12 for every arm
- Permutation null for A3: 1,000 label shuffles, empirical one-sided p
- Ablations by re-scoring the saved board, with no new LLM calls: A3_noskeptic, A3_no<agent>, A3_isolated (round 0 only)

## Scoring
`frozen/weights.json`: equal channel weights, supports=+1 / neutral=0 / against=−1, × strength, × 0.5 for a channel named in a skeptic challenge. Each channel's latest artifact is used.

## Known limitations (stated before the result)
1. **Study-intensity confound**: positives are famous genes with many more evidence rows (e.g. ~1,000 burden rows vs tens). Row counts are visible in the views; S2 and every LLM arm can exploit them.
2. Anonymisation removes names, IDs and drug data; trait patterns remain and can let an LLM recognise a famous gene.
3. OT assigns `directionOnTrait` for quantitative traits from the sign of beta, so lowering HDL is labelled "protect" (see `data_layer/SUBSTITUTIONS.md`).
4. Top-ranked negatives are hypotheses, not validated targets.

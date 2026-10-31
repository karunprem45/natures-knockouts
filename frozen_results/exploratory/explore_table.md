# Exploratory results (after `results-final`; not pre-registered)

Same 40-gene panel, labels and paired bootstrap as the headline. These runs were designed and run after the pre-registered results were frozen, so they are hypotheses for the next panel, not claims.

| Run | Model(s) | Seeds | AUROC (95% CI) | Paired Δ AUROC | Other |
| --- | --- | --- | --- | --- | --- |
| A3 + Variant (Evo 2) | Gemini 3 Flash + NVIDIA Evo 2 40B | 2 | 0.820 (0.671–0.929) | +0.038 (-0.036, +0.124) vs A3 | +0.046 (-0.053, +0.147) vs A1 |

- Variant agent: 77 variant_check needs raised in round 0, 30 answered with Evo 2, 0 Evo 2 errors; median site percentile of scored SNVs 59.1.
## How to read this

- **Not pre-registered.** The Variant agent was added after `results-final`. The headline (A3 vs A1, +0.008) is unchanged.
- **Two things changed at once.** With the Variant agent enabled, every agent's round-0 prompt also mentions `variant_check`, and Evo 2 answers compete with other needs inside the same 10-call budget. Part of any difference may come from those changes, not from Evo 2's numbers.
- **What Evo 2 saw.** GWAS lead variants are mostly non-coding tags (median site percentile near 50, i.e. typical for their window), so there was little DNA-level disruption signal to add.
- **Next step.** Pre-register "A3 + Variant vs A3" on a fresh panel, with coding lead variants or burden-test variants as Evo 2's input.
- **Cost.** Evo 2 ran on NVIDIA's hosted trial endpoint (build.nvidia.com, `evo2-40b` `/forward`, `unembed` layer), so it was free. Gemini spend matched the A3 runs.

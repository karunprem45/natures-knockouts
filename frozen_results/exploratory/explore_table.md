# Exploratory results (after `results-final`; not pre-registered)

Same 40-gene panel, labels and paired bootstrap as the headline. These runs were designed and run after the pre-registered results were frozen, so they are hypotheses for the next panel, not claims.

| Run | Model(s) | Seeds | AUROC (95% CI) | Paired Δ AUROC | Other |
| --- | --- | --- | --- | --- | --- |
| A3 + Variant (Evo 2) | Gemini 3 Flash + NVIDIA Evo 2 40B | 2 | 0.820 (0.671–0.929) | +0.038 (-0.036, +0.124) vs A3 | +0.046 (-0.053, +0.147) vs A1 |
| A3 on openai | gpt-5-mini | 1 | 0.751 (0.574–0.902) | -0.068 (-0.188, +0.027) vs A1 on openai | A1: 0.820 (0.674–0.940) |
| A3_isolated on openai (re-scored, 0 calls) | gpt-5-mini | 1 | 0.857 (0.730–0.961) | +0.037 (-0.084, +0.158) vs A1 on openai | |
| A3_noskeptic on openai (re-scored, 0 calls) | gpt-5-mini | 1 | 0.763 (0.604–0.900) | -0.057 (-0.177, +0.046) vs A1 on openai | |

- Variant agent: 77 variant_check needs raised in round 0, 30 answered with Evo 2, 0 Evo 2 errors; median site percentile of scored SNVs 59.1.
## How to read this

- **Not pre-registered.** Both the Variant agent and the GPT runs were added after `results-final`. The headline (A3 vs A1 on Gemini, +0.008) is unchanged.
- **Variant run: two things changed at once.** With the Variant agent enabled, every agent's round-0 prompt also mentions `variant_check`, and Evo 2 answers compete with other needs inside the same 10-call budget. Part of any difference may come from those changes.
- **What Evo 2 saw.** GWAS lead variants are mostly non-coding tags (median site percentile near 50), so there was little DNA-level disruption signal to add. A fair test would feed Evo 2 coding or burden-test variants on a fresh, pre-registered panel.
- **GPT robustness run (1 seed, gpt-5-mini).** gpt-5-mini does not accept temperature 0, so it ran at its default temperature: less deterministic than the Gemini arms. Same panel, views, prompts, call cap and scoring.
- **What replicates across both models.** Isolated specialists (round 0 only) score about 0.85 on both Gemini (0.853) and GPT (0.857), at or above the single agent on each. The full coordination loop scores lower than round 0 on both. The single-agent-vs-collective comparison itself is a tie on Gemini and leans towards the single agent on GPT; neither interval excludes zero.
- **Cost.** Evo 2 ran free on NVIDIA's hosted trial endpoint. The GPT runs used about 2.6M input and 0.28M output tokens (reasoning included) from the hackathon's $50 OpenAI credit.

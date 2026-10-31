---
name: evo2-variant-score
description: Score whether a human genetic variant is disruptive using NVIDIA's hosted Evo 2 40B /forward endpoint, as a percentile among every possible base change in its window. Use when an agent or pipeline needs DNA-level evidence for a variant from a genome language model.
---

# Evo 2 variant score

`score_variant.py` in this folder is standalone (Python, `requests`, `numpy`). Given GRCh38 coordinates it fetches the reference window from Ensembl, runs **one** Evo 2 forward pass, and reports:

- `delta_ll`: log-likelihood of the sequence with the variant minus the reference (more negative = less natural to the genome model)
- `site_percentile` (SNVs): where the substitution ranks among every possible single-base change in the window, from the same pass (0 = most disfavoured; about 50 = typical)

## Run it

```bash
export NVIDIA_API_KEY=nvapi-...      # from build.nvidia.com, the Evo 2 model page
python skills/evo2-variant-score/score_variant.py 1 55063514 G A
```

## Hosted API facts (checked October 2026)

- Endpoint `https://health.api.nvidia.com/v1/biology/arc/evo2-40b/forward`, body `{"sequence": ..., "output_layers": ["unembed"]}`. `output_layer` can return 422 on the hosted API; `unembed` works.
- The response is base64 npz with key `unembed.output`, shape `(1, N, 512)`. Byte-level vocabulary: a base's index is `ord(base)`.
- `logits[t]` predicts token `t+1`, so position 0 is never scored.
- If the returned length differs from the input, refuse; never guess the alignment.

## Guards

- Check that the genome's base at the position equals the variant's reference allele before scoring. Never guess strand or assembly.
- Cache by sha256 of the sequence; reruns cost nothing.
- Keep coordinates out of LLM prompts if the gene must stay anonymous: pass only the numbers.

## Caveat from this project

GWAS lead variants are usually non-coding tags (median percentile around 50 here), so they carry little disruption signal. Coding or burden-test variants are the better input.

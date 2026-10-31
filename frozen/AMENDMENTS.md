# Amendments after the `prereg` tag

Every change to a pre-registered setting is listed here, with the reason and evidence that no arm had run yet.

## 1. LLM model and backend (before any LLM arm ran)

| | At `prereg` (`12b8c58`) | Now |
| --- | --- | --- |
| Model | `gemini-2.5-flash` | `gemini-3-flash-preview` |
| Backend | Gemini API with an API key | Vertex AI (`scienceclaw26bos-3027`, location `global`) with Application Default Credentials |

**Why:** the hackathon GCP organization disallows API keys, and on Vertex AI `gemini-2.5-flash` returns 404 for this project in both `global` and `us-central1`. `gemini-3-flash-preview` is the only Flash model that answered (`probes/results/llm.json`).

**Unchanged:** the model is still the same in every arm (R1), with the same per-gene call cap, `temperature = 0` and the same seeds. The panel, metrics and scoring weights are untouched. `frozen/weights.json` still names the old model and is kept as it was at the tag; `config.LLM_MODEL` is authoritative.

**No arm had run:** at the time of this change `runs/` held only the scripted baselines S1–S4, which use no LLM.

## 2. Safety view: Mendelian disease names replaced by disease categories (before any LLM arm ran)

**What changed:** in `data/views/safety/`, Mendelian / clinical-variant evidence (eva, genomics_england, orphanet, gene2phenotype, clingen, uniprot) is no longer listed by disease name. It appears only as counts per Open Targets therapeutic area (`mendelian_by_category`: number of diseases, number caused by loss of function, max evidence score). Out-of-scope burden and GWAS rows keep their trait names.

**Why:** in the Phase 3 checkpoint the Safety agent recognised a gene from eponymous syndromes in its view ("Norum disease", "Fish-eye disease") and wrote the gene's symbol in its rationale. Another named a single-gene syndrome. Redacting the output alone cannot stop the model's knowledge from shaping its verdict.

**Effect measured:** after the change, 1 of 160 agent verdicts (4 agents × 40 genes, a one-off sweep run only for this check) named a gene, down from 1 in 5 Safety verdicts in the checkpoint before. That name was redacted and the artifact flagged. Every arm (A1 and A3) reads the same views, so the comparison stays fair.

**Unchanged:** panel, labels, metrics, scoring weights and the S1–S4 features (`safety_risk_count` is computed from the raw rows, not the view). S1–S4 scores are identical.

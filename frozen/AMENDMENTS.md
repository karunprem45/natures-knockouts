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

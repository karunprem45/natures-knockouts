# Null Hypothesis

**Does a collective of AI agents, each seeing one slice of the evidence and coordinating with no planner, find drug targets better than one agent that sees everything?**

Some people are born with a broken copy of a gene and are healthier for it: loss of PCSK9 means lifelong low LDL cholesterol, far fewer heart attacks, and a drug (evolocumab). Finding the next such gene means combining evidence that lives in separate places. We built a decentralised collective of specialist agents for exactly that split, and tested it against a single agent and a strong scripted baseline on a blind, pre-registered panel of 40 genes.

Built at ScienceClaw, MIT Media Lab, by Karuniya Premnath, Karishma Premnath and Dheepak Karan.

## Results

| Arm | AUROC (95% CI) | What it is |
| --- | --- | --- |
| A3 | 0.782 (0.641–0.895) | Collective: four specialists + skeptic on a shared board |
| A1 | 0.774 (0.616–0.903) | One agent that sees every view |
| S4 | 0.750 (0.542–0.910) | Scripted baseline: all features, z-scored, equal weights |
| A3, round 0 only | 0.853 (0.729–0.948) | Same boards, before any coordination (re-scored, 0 extra calls) |

- **Pre-registered headline:** Δ AUROC (A3 − A1) = **+0.008** (−0.074 to +0.103). A tie. A3 beats chance (permutation p = 0.003).
- **Strongest finding:** isolated specialists that never talk score about 0.85 on both Gemini (0.853) and GPT-5 mini (0.857). The full coordination loop scores lower on both; an over-eager skeptic is the main reason.
- **Extensions (not pre-registered):** an NVIDIA Evo 2 40B Variant agent adds +0.038 AUROC (CI includes zero).

Full tables: [`frozen_results/arms_table.md`](frozen_results/arms_table.md), [`frozen_results/FINDINGS.md`](frozen_results/FINDINGS.md), [`frozen_results/exploratory/explore_table.md`](frozen_results/exploratory/explore_table.md).

## How it works

| Agent | Sees only | Question |
| --- | --- | --- |
| Burden | In-scope rare-variant burden rows | Do carriers get less disease? |
| GWAS | In-scope fine-mapped credible sets | Does a second study type agree? |
| Tolerance | LOEUF, pLI, DepMap | Can a human live without it? |
| Safety | Out-of-scope traits (Mendelian disease as categories) | Does breaking it harm elsewhere? |
| Skeptic | Only the other agents' verdicts | Is this evidence trustworthy? |
| Variant (extension) | Lead variant, scored by NVIDIA Evo 2 | Is the variant really disruptive? |

Round 0: independent verdicts. Round 1: each agent bids on the open need it can answer, ranked by `pressure = 2·novelty + centrality + 0.5·depth + 0.2·age`. Round 2: skeptic challenges, then revisions. A pure-Python scorer turns the latest verdicts into one number per gene. Nothing in the loop assigns work.

## Rigor

| Tag | Commit | What was fixed |
| --- | --- | --- |
| `prereg` | `12b8c58` | Panel, metrics and scoring weights, before any arm ran |
| `results-raw` | `28a0e95` | Every arm's scores and boards, hashed, before any metric |
| `results-final` | `4729a6b` | Arms table, figures, findings |

- `tests/test_views_isolation.py`: 203 checks that no agent's view holds another channel's data, a gene symbol, an Ensembl ID or drug data. A planted leak fails it.
- Amendments after `prereg`, both before any LLM arm ran: [`frozen/AMENDMENTS.md`](frozen/AMENDMENTS.md).
- Limitations, stated up front: [`frozen_results/FINDINGS.md`](frozen_results/FINDINGS.md).

## Reproduce

```bash
make setup                              # venv + dependencies
gcloud auth application-default login   # Vertex AI (Gemini) for all pre-registered arms
make probe                              # Gemini, Open Targets, Ensembl, Evo 2 checks
make data panel                         # Open Targets pull, blind panel, views, isolation tests
make baselines                          # S1–S4
make allarms ablations report           # A1, A3 x2 seeds, ablations, table, figures
make explore                            # exploratory: Evo 2 and other-model comparisons
make demo GENE=Gene_01                  # two-minute replay of one gene's board (no API calls)
make test
```

Keys go in `.env` (see `.env.example`); `.env` and `data/` are gitignored.

## Platforms

| Platform | Used for |
| --- | --- |
| Google Cloud, Vertex AI (Gemini 3 Flash) | Every agent in every pre-registered arm |
| NVIDIA build.nvidia.com (Evo 2 40B) | Variant agent (extension) |
| OpenAI (gpt-5-mini) | Robustness check on a second model (extension) |
| Open Targets, Ensembl | Genetics evidence and reference DNA |

## Repository map

`data_layer/` data pull and views · `llm/` the single LLM gateway and guards · `agents/` specialists, skeptic, prompts · `board/` artifacts, needs, loop · `scoring.py` · `arms/` scripted, A1, A3, ablations · `eval/` metrics, report, figures · `tools/` Ensembl and Evo 2 · `skills/` reusable skills · `slides/` the deck · `frozen/` pre-registration · `frozen_results/` hashed outputs.

Who did what: [`CONTRIBUTORS.md`](CONTRIBUTORS.md). Project report (PDF): [`docs/Null_Hypothesis_Project_Report.pdf`](docs/Null_Hypothesis_Project_Report.pdf). Original build plan: [`BUILD.md`](BUILD.md). Demo script: [`DEMO.md`](DEMO.md).

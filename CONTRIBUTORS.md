# Contributors

We worked as a mob on one machine, so every commit names a driver as author and the other two as co-authors (`scripts/commit.sh`, `.mob`). Ownership followed the roles in [BUILD.md](BUILD.md) §3.2.

| Person | GitHub | Role | Phases and pieces owned |
| --- | --- | --- | --- |
| Karuniya Premnath | [@karunprem45](https://github.com/karunprem45) | Data | Phase 1 Open Targets data layer, blind panel, per-agent views, isolation test · Phase 2 features and scripted baselines S1–S4 · slides and demo |
| Karishma Premnath | [@karishmapremnath4](https://github.com/karishmapremnath4) | Agents | Phase 3 LLM gateway, guards and agents · Phase 4 shared board, needs and pressure scoring, skeptic · reusable skills |
| Dheepak Karan | [@dheepakkaran](https://github.com/dheepakkaran) | Evaluation | Phase 5 arms, seeds and ablations · Phase 6 metrics, paired bootstrap, permutation null, figures, findings · extensions comparison · README |

## Final pull requests

| PR | Owner | What it adds |
| --- | --- | --- |
| [#1](https://github.com/karunprem45/natures-knockouts/pull/1) | Karuniya | Null Hypothesis deck, slide 6 with NVIDIA Evo 2 and GPT extensions |
| [#2](https://github.com/karunprem45/natures-knockouts/pull/2) | Karishma | Three reusable skills from the agent system |
| #3 | Dheepak | README, contributors, `make explore`, findings pointer to extensions |

Phase branches (`phase-0-probes` … `phase-7-slides`, `explore-platforms`, `explore-openai`) are kept on GitHub so the history shows each step.

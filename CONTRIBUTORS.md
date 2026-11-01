# Contributors

We worked as a mob on one machine, and every commit lists the other two as co-authors. Ownership is by area:

| Person | GitHub | Area | Branches |
| --- | --- | --- | --- |
| Karishma Premnath | [@karishmapremnath4](https://github.com/karishmapremnath4) | **Data**: panel, per-agent views, safety-view coarsening, panel 2 for `prereg-v2` | `data` |
| Karuniya Premnath | [@karunprem45](https://github.com/karunprem45) | **Agents**: LLM gateway and guards, the four specialists and the skeptic, the needs board, A1 and A3 arms, the Evo 2 Variant agent, the reusable skills | `agents` |
| Dheepak Karan | [@dheepakkaran](https://github.com/dheepakkaran) | **Evaluation**: baselines S1–S4, metrics and paired bootstrap, frozen results, the noise floor, paired reruns, the constrained planner, the Evo 2 coding test, the GPT-5 mini rerun | `eval` |

Shared work (report, deck, site, film) is on `main`, and its commits are spread across all three of us.

## Branch layout

| Branch | What it holds |
| --- | --- |
| `main` | The submitted project |
| `data` | Data work: probes, the blind panel and per-agent views, safety-view coarsening |
| `agents` | Agent work: LLM gateway, specialists and skeptic, needs board, Evo 2 Variant agent, skills |
| `eval` | Evaluation work: baselines, arms, paired bootstrap and figures, GPT-5 mini rerun |

`data`, `agents` and `eval` are all merged into `main`. Earlier histories are reachable through the tags below.

## Final pull requests

| PR | What it adds |
| --- | --- |
| [#1](https://github.com/karunprem45/null-hypothesis/pull/1) | Null Hypothesis deck, slide 6 with NVIDIA Evo 2 and GPT extensions |
| [#2](https://github.com/karunprem45/null-hypothesis/pull/2) | Three reusable skills from the agent system |
| [#3](https://github.com/karunprem45/null-hypothesis/pull/3) | README, contributors, `make explore`, findings pointer to extensions |

## Authorship reassignment (after the event)

During the hackathon every commit was made from one laptop. Afterwards we set each commit's author to the owner of its area (data, agents, evaluation). Only the author and committer fields changed:

- **File contents and commit messages are identical.** Every rewritten commit has the same tree as its original.
- **The pre-registration proof holds.** Commits up to and including `prereg` (`12b8c58`) were not rewritten, so `12b8c58` is still in `main`. The early data-layer phases (probes, blind panel) come before it and keep their recorded author for that reason.
- **Every cited hash still resolves.** The tags `prereg-v2` (`78df730`), `results-raw` (`28a0e95`), `results-final` (`4729a6b`) and `submission` (`2307265`) still point at their original commits. Those tags keep the earlier histories reachable.

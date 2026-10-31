# Reusable skills

Three portable skills packaged from this project. Each folder has a `SKILL.md` that an agent (Claude Code, ScienceClaw, or similar) can load.

| Skill | What it gives you |
| --- | --- |
| [`blind-agent-views`](blind-agent-views/SKILL.md) | Per-agent evidence folders with identity stripped, plus a test that proves agents can't see each other's data |
| [`needs-board-coordination`](needs-board-coordination/SKILL.md) | Artifact board with needs and pressure scoring, no planner, and free re-scoring ablations to measure coordination |
| [`evo2-variant-score`](evo2-variant-score/SKILL.md) | Standalone NVIDIA Evo 2 40B variant scorer: delta log-likelihood and percentile among every possible base change in the window |

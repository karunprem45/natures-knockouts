---
name: needs-board-coordination
description: Coordinate LLM agents through a shared artifact board with needs and pressure scoring instead of a central planner, then measure whether coordination helps with zero-cost ablations. Use when an agent system must show decentralised agency and a measured collective gain.
---

# Needs-board coordination

Agents post artifacts and broadcast needs to a shared board. Each agent decides for itself which open need to answer. Nothing assigns work.

## The artifact

Append-only JSONL. Every artifact carries `artifact_id` (UUID), `artifact_type` (evidence, fulfillment, challenge, revision, error), `producer_agent`, `round`, `stance`, `strength`, `rationale`, `data_refs`, `parent_artifact_ids`, `needs`, `content_hash` (sha256 of the content), and `flags`. Parent links give a provenance graph for free.

## Pressure scoring (organizers' formula)

```
pressure = 2.0*novelty + 1.0*centrality + 0.5*depth + 0.2*age
  novelty    = 1 / (1 + times this need type was already fulfilled)
  centrality = open needs of the same type with overlapping query tokens
  depth      = DAG depth of the parent artifact
  age        = rounds since the need was posted
```

An agent can't answer its own need, and a consumed need is never answered twice.

## The loop

1. **Round 0:** specialists post independent evidence in parallel; each may broadcast needs.
2. **Round 1:** every agent looks at the board and bids on the highest-pressure open need it can answer. The loop only enforces the shared call budget.
3. **Round 2:** a skeptic with no data reads every verdict and posts typed challenges; agents that received answers or challenges may post a revision whose parents are the original and the answers.
4. **Score in plain code,** never with the LLM: latest verdict per channel, revisions supersede parents, challenged channels discounted.

## Measure it, don't assume it

Save every board, then re-score with artifacts removed: no skeptic, round 0 only, without each agent. Zero extra LLM calls, so every ablation is free.

**What this repo found:** the round-0-only collective (isolated specialists) scored AUROC 0.853 on Gemini and 0.857 on GPT-5 mini, while the full loop scored 0.782 and 0.751. A skeptic that fires on most items regardless of truth costs accuracy. Calibrate it before trusting it.

## Code in this repo

`board/artifact.py`, `board/needs.py`, `board/loop.py`, `scoring.py`, `arms/rescore.py`, tests in `tests/test_board.py`.

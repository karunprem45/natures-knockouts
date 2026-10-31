# Null Hypothesis: two-minute demo

Run from the repo root, terminal font large, window wide:

```bash
make demo GENE=Gene_01
```

The replay reads the frozen A3 board, so it makes no API calls and cannot fail on stage. The final score is recomputed live by `scoring.py`.

## Script (about 2:00)

**0:00 Setup (15 s)**
"This is one gene from our blind panel. No agent knows which gene it is, and each one can open only its own folder of evidence. We can prove that: `pytest tests/test_views_isolation.py` runs 203 checks, including a planted leak that has to fail."

**0:15 Round 0 (30 s)** *(the four verdicts print)*
"Four specialists post independently. Burden sees loss-of-function carriers with lower HDL. Open Targets labels that 'protective', but the agent reads the trait and calls it unfavourable. Tolerance sees a gene humans lose without trouble. Each one also broadcasts what it can't see: Burden asks for GWAS and safety, GWAS asks for burden and tolerance."

**0:45 Round 1 (25 s)** *(the needs-answered lines print)*
"Nobody assigns these. Each agent looks at the board and bids on the open need it can answer, ranked by the organizers' pressure formula. Here GWAS asked and Burden answered; Burden asked and GWAS answered."

**1:10 Round 2 (25 s)** *(skeptic challenges and revisions print)*
"The skeptic has no data at all. It reads the verdicts and flags a direction conflict: a channel's stance doesn't match its own rationale. Burden and GWAS revise, and each revision points back to its parent."

**1:35 Score and result (25 s)** *(score breakdown prints)*
"Python, not the model, turns the latest verdicts into one number. Across all 40 genes the collective ties the single agent, +0.008 AUROC. But the four isolated specialists scored 0.853, ahead of the single agent, and the skeptic gave that back by firing on almost every gene. The panel was frozen at commit 12b8c58 before any arm ran."

## If asked

| Question | Answer, and where to show it |
| --- | --- |
| How do you know the agents are separate? | `pytest tests/test_views_isolation.py tests/test_guards.py -q`; `agents/base.py` refuses any path outside `data/views/<agent>/` |
| Did you tune to the result? | `git show prereg`, `git show results-raw`: panel frozen before any arm, raw scores frozen before any metric |
| Is A1 handicapped? | Same model, same cap, every view, the specialists' guidance text verbatim, same assess / self-review / revise steps; it spends about the same ($1.09 vs $1.32 per run) |
| Why did the skeptic hurt? | `frozen_results/FINDINGS.md` §2 and `figures/4_skeptic_rank_shift.png` |
| Show it live | `python -m scripts.demo Gene_01 --live` (10 Gemini calls, about 40 s; needs the Vertex sign-in) |

# Nature's Knockouts — BUILD.md

**This is the single source of truth. Read it fully before writing any code.**

|  |  |
| --- | --- |
| Event | ScienceClaw, MIT Media Lab |
| Deadline | **Sunday 1:00 PM** — hacking ends, final slides due |
| Start | Saturday \~4:30 PM |
| Team | 3 people, **one Mac, one Claude Code session** |
| Repo | one GitHub repo, branch per phase, all 3 emails on every commit |

---

# 0. The project in plain language

Some people are born with a **broken** copy of a gene and are **healthier** for it. Broken `PCSK9` → very low LDL cholesterol → far fewer heart attacks → the drug evolocumab exists because of that observation. Human genetics ran the trial for free.

Finding the next one is hard because the evidence is **scattered**: rare-variant burden studies, GWAS, population tolerance metrics, cross-phenotype safety signals, DNA models. No single source answers the question.

**We build a decentralized collective of specialist agents — each able to see only one slice of that evidence — that coordinate through a shared artifact board with no central planner, and we measure whether the collective beats a single agent and a strong scripted heuristic on a blind, pre-registered panel of genes.**

### The one number everything serves

> **Δ AUROC (collective − single agent)**, same LLM, same call budget, same panel, with a bootstrap confidence interval.

If any decision trades "more features" against "this number stays clean," choose the number.

---

# 1. Judging criteria → where we earn each one

| Criterion | Weight | What earns it | Where in this build |
| --- | --- | --- | --- |
| Problem significance | 20% | Hard, consequential, and genuinely needs a decentralized system | Drug-target discovery; evidence is physically split across five sources, so no single agent can see enough — **Phase 1 proves this on disk** |
| Scientific / technical impact | 25% | A real result, plus novel output | AUROC/AUPRC on a pre-registered panel + a **novel candidate list** (top-ranked negatives) |
| **Decentralized agency** | **20%** | Distinct information per agent; no planner prescribing the trajectory | Per-agent view directories (R2), needs-driven board with pressure scoring, **no orchestrator** — Phase 4 |
| **Collective capability** | **25%** | Measured gain vs single / isolated / centralized | Arms S1–S4, A1, A3, A3-isolated, ablations, permutation null — Phases 2, 5, 6 |
| Execution & validation | 10% | Working system, convincing evidence | Live one-gene demo + frozen results with CIs |
| Collaboration bonus | +10 | Capability other teams reuse | Three portable skills, published as early as time allows |

### Three things the organizers have said out loud that we are answering directly

1. NVIDIA's own hackathon material states the comparison judges want is **"one agent against a collective on the same testbed."** That is exactly our A1 vs A3.
2. NVIDIA's agent benchmark found **agents never add validation on their own and never question ill-posed tasks.** Our Skeptic agent is the fix, and we **measure** it (A3 vs A3-noskeptic).
3. The organizing lab publishes results where coordination **ties** with a simple baseline. So a tie is a respected outcome here, not a failure. We pre-register and report honestly.

---

# 2. Scope — already cut for the time we have

**Do not re-expand these without asking.**

| Decision | Value |
| --- | --- |
| Panel size | **40 genes**: 12 positives + 28 hard negatives |
| Arms with LLM | **A1 and A3 only**. A2 (centralized) is **cut** |
| Seeds | **2** per LLM arm |
| Ablations | **Re-scoring passes over the saved board — zero extra LLM calls** |
| Stage 2 binder design | **Cut** |
| Evo 2 / Variant agent | **Only if its probe passes inside 20 minutes.** Otherwise 4 agents + skeptic |
| Skills publishing | Only if we are ahead of schedule |

**Never cut:** the frozen panel, S4, A1, A3, the permutation null.

---

# 3. Git setup — 3 emails, branches, one machine

We share one Mac, so every commit records a **driver** as author and the other two as co-authors. This is the standard attribution pattern for mob programming and is accurate: all three of us are at the machine.

## 3.1 One-time setup

```bash
mkdir natures-knockouts && cd natures-knockouts
git init -b main
```

- `git init -b main` — create a repo whose first branch is named `main` (not `master`)

Create `.mob` with the three identities — Claude Code fills in the real values:

```bash
cat > .mob <<'EOF'
dk|Dheepak Karan|dheepak@example.edu
m2|Member Two|member2@example.edu
m3|Member Three|member3@example.edu
EOF
```

- `cat > file <<'EOF' … EOF` — write everything up to `EOF` into the file. Quoting `'EOF'` stops the shell from expanding anything inside

Create `scripts/commit.sh`:

```bash
#!/usr/bin/env bash
# usage: ./scripts/commit.sh <driver-initials> "<commit message>"
set -euo pipefail
DRIVER="$1"; shift
MSG="$*"
TRAILERS=""
AUTHOR=""
while IFS='|' read -r key name email; do
  [ -z "$key" ] && continue
  if [ "$key" = "$DRIVER" ]; then
    AUTHOR="$name <$email>"
  else
    TRAILERS="${TRAILERS}
Co-authored-by: $name <$email>"
  fi
done < .mob
[ -z "$AUTHOR" ] && { echo "unknown driver: $DRIVER"; exit 1; }
git add -A
git commit --author="$AUTHOR" -m "$MSG
${TRAILERS}"
```

- `set -euo pipefail` — stop on any error (`e`), on any undefined variable (`u`), and on a failure anywhere in a pipe (`pipefail`). Without this, a broken script keeps going and corrupts state
- `IFS='|' read -r key name email` — split each line on `|` into three variables. `-r` stops backslashes being treated specially
- `git commit --author=` — records who drove; the `Co-authored-by:` trailers are what GitHub reads to credit the other two

```bash
chmod +x scripts/commit.sh
```

- `chmod +x` — mark the file executable so `./scripts/commit.sh` runs

**From now on, every commit uses this script.** Rotate the driver to whoever actually did that piece.

## 3.2 Branch per phase

```bash
git checkout -b phase-0-probes
# … work …
./scripts/commit.sh dk "chore(probes): llm + open targets probes passing"
git checkout main
git merge --no-ff phase-0-probes -m "merge: phase 0 probes"
```

- `git checkout -b <name>` — create the branch and switch to it
- `git merge --no-ff` — **always record a merge commit**, even when a fast-forward is possible. This keeps each phase visible as its own bubble in the history graph. A judge glancing at the network graph sees structured work, not one big dump

Branches, in order:

| Branch | Owner (driver) |
| --- | --- |
| `phase-0-probes` | whoever has the keys |
| `phase-1-data` | **data person** |
| `phase-2-baselines` | data person |
| `phase-3-agents` | **agents person** |
| `phase-4-board` | agents person |
| `phase-5-arms` | **eval person** |
| `phase-6-eval` | eval person |

Merge to `main` only when the phase's acceptance criterion passes.

## 3.3 The pre-registration tag — this is a slide

After the panel is frozen (around 7 PM), do this and **write the hash on a sticky note**:

```bash
./scripts/commit.sh dk "freeze: pre-register panel, metrics and scorer weights"
git tag -a prereg -m "Panel, metrics and weights frozen before any arm was run"
git rev-parse --short prereg
```

- `git tag -a <name> -m` — an annotated tag: a permanent, dated, named pointer to this exact commit
- `git rev-parse --short prereg` — print the short hash

Slide 4 says: *"Panel and metrics frozen at commit `abc1234`, before any arm ran."* That single line answers "did you tune this to get the result?" before a judge can ask it.

## 3.4 Push early, push often

```bash
git remote add origin git@github.com:<org>/natures-knockouts.git
git push -u origin main --tags
```

⚠️ **The provided cloud accounts auto-delete Sunday night.** Push before judging, not after.

---

# 4. What we use, and why that thing

| Tool | Used for | Why this one |
| --- | --- | --- |
| **Gemini Flash** (AI Studio Tier-1 key) | The brain for **every** agent in **every** arm | Tier-1 gives 1,000–4,000 RPM and 2–4M TPM. A fair comparison needs the same model in every arm, and only Gemini has the headroom for thousands of calls in one night |
| **GCP VM / the Mac** | Runs all agents and the shared board | Coordination state is a shared local file, so every agent must be on one machine |
| **Open Targets** (GraphQL + BigQuery) | All genetics evidence | It already carries gene-burden results with **direction of effect** (risk vs protective), GWAS evidence, gnomAD constraint and DepMap essentiality behind one API. No multi-GB downloads |
| **Ensembl REST** | Reference DNA windows | Free, no key, needed to build the ref/alt sequences for Evo 2 |
| **NVIDIA Evo 2** (hosted NIM, or Brev) | The Variant agent | A DNA-level model. Every other channel is statistics; this one reads the sequence itself, so it is genuinely independent evidence |
| **Claude Code** ($100 Console credits) | **Builds the system** | Speed. Claude is not any agent's brain — that would break the fairness rule |
| **Git / GitHub** | Pre-registration, attribution, survival | The `prereg` tag is scientific evidence, not bookkeeping |

**Not used, deliberately:** ScienceClaw's `AutonomousOrchestrator` (it is an LLM planner that spawns agents and assigns tasks — a central planner, which would cost us the 20% Decentralized Agency). We mirror ScienceClaw's **artifact + needs** layer instead, which is the part the organizers' paper is actually about.

---

# 5. Ten rules that must hold in code

| # | Rule | How it is enforced |
| --- | --- | --- |
| R1 | Every arm uses the **same model** and **same per-gene call cap** | `MAX_LLM_CALLS_PER_GENE = 10` in `config.py`; `LLMClient` raises `BudgetExceeded` |
| R2 | **No agent reads another agent's data** | Each agent reads only `data/views/<agent>/`; enforced by a test |
| R3 | **No agent ever reads `data/labels/`** | Separate directory; a test asserts the string `chembl` appears in zero view files |
| R4 | **Gene identity hidden from every prompt** | Views keyed `Gene_01…Gene_40`; a regex guard scans outgoing prompts for symbols/Ensembl IDs and raises |
| R5 | **Python computes the final score, never an LLM** | `scoring.py` imports no LLM module |
| R6 | **Panel, metrics and weights frozen before any arm runs** | `make freeze` + the `prereg` tag; `run_arm.py` refuses if `frozen/` is dirty |
| R7 | **Results frozen once generated** | `make freeze-results` copies and hashes `runs/` |
| R8 | **Every LLM call logged** (arm, gene, agent, tokens, latency, cost) | `runs/<id>/llm_log.jsonl` |
| R9 | **Determinism**: `temperature=0`, fixed seeds, sorted iteration | `config.py` |
| R10 | **Fail loudly.** A failed tool writes an `error` artifact; never fabricate a value | — |

---

# 6. Repository layout

```
natures-knockouts/
├── BUILD.md                 ← this file
├── Makefile
├── requirements.txt
├── .env.example
├── .mob
├── config.py                # constants only, no logic
├── scripts/commit.sh
├── probes/
│   ├── probe_llm.py
│   ├── probe_opentargets.py
│   ├── probe_ensembl.py
│   └── probe_evo2.py
├── data_layer/
│   ├── ot_client.py         # GraphQL client: retry, cache, pagination
│   ├── schema_probe.py      # introspect and PRINT the real field names
│   ├── fetch_pool.py
│   ├── fetch_gene.py
│   ├── build_labels.py
│   ├── build_panel.py
│   ├── features.py
│   └── build_views.py
├── llm/
│   ├── client.py            # the single chokepoint for every LLM call
│   └── guards.py            # identity guard, label guard, budget
├── agents/
│   ├── base.py
│   ├── burden.py  gwas.py  tolerance.py  safety.py  variant.py  skeptic.py
│   └── prompts/*.txt
├── board/
│   ├── artifact.py          # dataclass + sha256 + JSONL store
│   ├── needs.py             # NeedItem + pressure scoring
│   └── loop.py              # the round loop
├── scoring.py
├── arms/
│   ├── scripted.py          # S1–S4
│   ├── single_agent.py      # A1
│   ├── collective.py        # A3
│   ├── rescore.py           # ablations — NO LLM
│   └── run_arm.py
├── eval/
│   ├── metrics.py  report.py  figures.py
├── skills/                  # only if ahead of schedule
├── data/                    # gitignored
│   ├── raw/  labels/  views/<agent>/
├── frozen/                  # panel.csv, weights.json, metrics.md — COMMITTED
├── runs/
└── tests/
```

---

# 7. The six agents

Five evidence channels plus one quality-control agent. Each answers a different necessary condition for "is this a drug target?"

| Agent | Sees | Condition it answers | Cannot see |
| --- | --- | --- | --- |
| **Burden** | In-scope rare-variant burden rows: trait, direction, effect, p-value, cohort, carrier count | Do carriers get **less** disease? | constraint, gwas, safety |
| **GWAS** | In-scope GWAS rows, with a hard-endpoint flag | Does a second, independent study type agree? | burden, constraint, safety |
| **Tolerance** | LOEUF, pLI, DepMap essentiality | Can a human **live** without this gene? | any trait association at all |
| **Safety** | Evidence for traits **outside** our scope | Does breaking it cause harm elsewhere? | in-scope evidence |
| **Variant** | Lead variant coordinates only → Evo 2 | Is the variant **actually** disruptive at the DNA level? | everything else |
| **Skeptic** | All artifacts for the gene. **No data tool at all** | Is this evidence trustworthy? | — |

Each agent returns strict JSON:

```json
{"stance": "supports|against|neutral",
 "strength": 0.0,
 "rationale": "<=200 chars",
 "data_refs": ["burden_1"],
 "needs": [{"type":"tolerance_check","query":"...","rationale":"..."}]}
```

**Every prompt must state the agent's limits explicitly** ("you can only see burden evidence; you cannot see constraint") **and instruct it to broadcast a need when the deciding information lies outside its view.** Those needs are what produce coordination, and coordination is 20% of the score.

### Skeptic challenge types

`underpowered`, `single_cohort`, `single_ancestry`, `biomarker_only`, `direction_conflict`, `essential_gene`.

Each names the channel it discounts; `scoring.py` halves that channel.

*(`single_ancestry` is deliberate: PCSK9's protective variants came out of African-ancestry data, and ancestry imbalance is a known failure mode in genetics. One judge works on AI policy at Hugging Face.)*

---

# 8. Phases, with time boxes

Times assume a 4:30 PM Saturday start. **Each phase has a gate. If the gate fails, take the fallback and move on — do not debug past the box.**

---

## Phase 0 — Probes · 4:30–5:00 PM · branch `phase-0-probes`

Four standalone scripts, each under 60 lines, each printing `PASS <detail>` or `FAIL <reason>` and exiting 0/1. `make probe` runs all four.

**`probe_llm.py`** — Gemini through the OpenAI-compatible endpoint:

```
base_url: https://generativelanguage.googleapis.com/v1beta/openai/
api_key:  $GEMINI_API_KEY
model:    gemini-2.5-flash
```

Check three things separately: (a) a chat completion returns text; (b) `response_format={"type":"json_object"}` returns valid JSON — if not, record that and we use prompt-only JSON with a tolerant parser; (c) token-usage fields are present (we need them for R8).

**`probe_opentargets.py`** — POST to `https://api.platform.opentargets.org/api/v4/graphql`, minimal query for `ENSG00000169174`, expect 200 with data.

**`probe_ensembl.py`** — `GET https://rest.ensembl.org/sequence/region/human/1:55039974..55040974?content-type=text/plain`, expect a DNA string. Sleep 0.1 s between calls (their limit is \~15/s).

**`probe_evo2.py`** — `POST https://health.api.nvidia.com/v1/biology/arc/evo2-40b/forward` with `{"sequence": "<~200bp>", "output_layers": ["output_layer"]}`. Known issues: the hosted 7B endpoint was marked **deprecated** in Aug 2026, and on the hosted API `output_layer` can return **422 "has no attribute"** — retry with `"unembed"` and cache which worked. Try 40b then 7b, and both layer names. Print the winning combination and the logits shape.

> **GATE 5:00 PM** — LLM and Open Targets must be PASS. Evo 2 may fail; if it does, **drop the Variant agent now** and move on. It is an ablation arm, not the core.

---

## Phase 1 — Data layer · 5:00–7:00 PM · branch `phase-1-data` · **highest risk**

### 1a. Introspect before querying

Run `schema_probe.py` **first**. Print the real field sets for `Target` and the evidence row type, write `data_layer/schema_snapshot.json`, and make every fetcher read field names from it. **If a field named in this doc does not exist, substitute the closest real one and log the substitution. Never crash, never silently drop a channel.**

### 1b. API behaviours to code around

| Behaviour | Consequence |
| --- | --- |
| Responses cap at \~10,000 rows | Query **per gene**, never in bulk |
| `directionOnTrait` **cannot be filtered server-side** | Fetch, then filter in Python |
| **ChEMBL evidence is always tagged protective** (it is drug data) | **The single biggest leak risk in this project.** ChEMBL goes to `data/labels/` and nowhere else |
| Burden sources include AstraZeneca PheWAS, Genebass, FinnGen, Regeneron | Record `projectId`/`cohortId` — the Skeptic's `single_cohort` challenge depends on it |

### 1c. Trait scope — set once in `config.py`, never change after freeze

```python
TRAIT_SCOPE = {
  "lipids":    ["LDL","HDL","triglyceride","cholesterol","lipoprotein"],
  "cardio":    ["coronary","myocardial","ischaemic heart","atherosclero"],
  "metabolic": ["type 2 diabetes","body mass index","obesity","waist","fat distribution"],
  "liver":     ["liver","hepatic","ALT","AST","steatosis","cirrhosis","NAFLD"],
}
HARD_ENDPOINT_TERMS = ["coronary","myocardial","diabetes","cirrhosis","ischaemic"]
```

The hard-endpoint flag matters: it is one of the few signals that genuinely separates our hard negatives, and it only becomes usable when an agent reasons about it in context.

### 1d. Pipeline

1. **`fetch_pool.py`** — for in-scope traits, pull `gene_burden` evidence with `enableIndirect: true`; keep rows that are loss-of-function **and** protective; collect distinct target IDs → `data/pool.csv`.
2. **`fetch_gene.py`** — per gene → `data/raw/{ensembl_id}.json` with keys `burden`, `gwas`, `constraint`, `essentiality`, `annotation`, `all_trait_evidence` (out-of-scope traits — the Safety agent's raw material). **ChEMBL rows go to `data/labels/chembl/`.** Cache: skip the network if the file exists and is under 24 h old.
3. **`build_labels.py`** — positives are the 12 below **that actually have in-scope burden or GWAS evidence**; replace any that do not, and log the replacement. Negatives are pool genes with protective LoF evidence in scope, **no ChEMBL evidence** in scope, and not in the positive list.

```python
POSITIVES = ["PCSK9","ANGPTL3","APOC3","ANGPTL4","NPC1L1","ASGR1",
             "SLC30A8","MAP3K15","HSD17B13","CIDEB","GPR75","INHBE"]
```

4. **`build_panel.py`** — 12 positives + 28 negatives sampled with `random.Random(SEED)`.
   - `frozen/panel.csv`: `gene_code, ensembl_id, n_evidence_rows` — **no label, no symbol**
   - `data/labels/panel_labels.csv`: `gene_code, label, symbol`
5. **`build_views.py`** — write `data/views/<agent>/<Gene_NN>.json` per the table in §7. Strip from every view: symbols, names, synonyms, descriptions, Ensembl IDs, literature/PMIDs, anything ChEMBL. Keep: trait names, directions, effect sizes, p-values, cohort names, LOEUF/pLI, DepMap, subcellular location.

### 1e. `tests/test_views_isolation.py` — write this, it is a slide

- every view file parses as JSON
- forbidden keys per view are absent
- no known gene symbol or Ensembl ID appears anywhere in any view file
- the string `chembl` appears in zero view files

We run this live if a judge asks how we know the agents are really separate.

> **GATE 6:30 PM** — if the panel is not built, **shrink to 24 genes (8 positives + 16 negatives)** and continue. Do not keep debugging.

**7:00 PM — `make freeze`, commit, `git tag -a prereg`, write the hash down.**

---

## Phase 2 — Features and scripted baselines · 7:00–8:00 PM · branch `phase-2-baselines`

`features.py` → `data/features.csv`, one row per `gene_code`:

`burden_prot_strength` (max `-log10(p)` over in-scope protective LoF rows, capped at 30), `burden_n_cohorts`, `burden_hard_endpoint`, `burden_n_traits`, `gwas_prot_strength`, `gwas_hard_endpoint`, `loeuf`, `pli`, `depmap_dependency`, `safety_risk_count`, `evo2_delta` (NaN unless the Variant agent ran).

Missing values are `NaN`, never `0`. Baselines impute by panel median and log that they did.

| Arm | Score |
| --- | --- |
| S1 | `loeuf` alone (higher = more LoF-tolerant = better candidate) |
| S2 | `burden_prot_strength` alone |
| S3 | `gwas_prot_strength` alone |
| **S4** | z-score every feature, flip sign where lower-is-better (`pli`, `depmap_dependency`, `safety_risk_count`), sum with equal weights |

**S4 is the real competitor. Make it genuinely strong — do not sandbag it.** NVIDIA's own material says a fixed heuristic script is what an agent system must beat. If S4 wins, that is a legitimate finding and we report it.

> **GATE 8:00 PM — we must have an AUROC table for S1–S4 with bootstrap CIs.** From this moment we always have something to present, whatever happens next. If this gate fails, stop building agents and fix the data layer.

---

## Phase 3 — LLM client and agents · 8:00–10:00 PM · branch `phase-3-agents`

**`llm/client.py`** — one class, the only place an LLM is called:

```python
def complete_json(self, *, agent, gene_code, prompt, schema) -> dict:
    # 1. guards.assert_no_identity(prompt)      # R4
    # 2. guards.assert_budget(arm, gene_code)   # R1
    # 3. call: temperature=0, json_object if the probe said it works
    # 4. parse; one retry with a "return only JSON" nudge;
    #    on second failure -> error artifact + neutral stance
    # 5. append to runs/<id>/llm_log.jsonl       # R8
```

Exponential backoff with jitter on 429/5xx, max 4 attempts, every retry logged. Thread-safe — Phase 5 calls this from a thread pool.

**`agents/base.py`** — load the view, render `prompts/<name>.txt`, call `complete_json`, return an `Artifact`.

**`agents/variant.py`** (only if Evo 2 passed):

1. read `chrom,pos,ref,alt`
2. fetch a 4,096 bp window from Ensembl centred on `pos`
3. **assert the base at `pos` equals `ref`** — if not, emit an error artifact; never guess strand or assembly
4. build the alt sequence
5. score both via `/forward` with the layer name the probe found
6. `delta = ll_alt − ll_ref`; strongly negative = the variant is disfavoured by the genome model = the loss of function is real
7. cache by `sha256(sequence)` — reruns across arms then cost nothing

Evo 2 is byte-level: a base's vocab index is `ord(base)`. Use `log_softmax(logits, -1)` then a causal shift (`logits[:, :-1]` vs `input_ids[:, 1:]`); position 0 does not score, so a length-N sequence yields N−1 scores. **If the returned `seq_len` does not match the input length, refuse to compute and return an error** — never guess the alignment.

> **GATE 10:00 PM** — each agent returns valid JSON for 5 genes and the identity guard never fires. If agents are not working, **skip Phase 4 and present S1–S4 + A1**. That is still a real result.

---

## Phase 4 — The board · 10:00 PM–12:00 AM · branch `phase-4-board`

**Artifact** (append-only JSONL at `runs/<id>/board.jsonl`):

```json
{"artifact_id":"<uuid4>","artifact_type":"evidence|fulfillment|challenge|revision|error",
 "producer_agent":"burden","gene_code":"Gene_17","round":0,
 "stance":"supports","strength":0.72,"rationale":"...","data_refs":["burden_1"],
 "parent_artifact_ids":[],"needs":[...],"content_hash":"<sha256>","timestamp":"..."}
```

Mirror the organizers' artifact layer deliberately — UUID, content hash, parent lineage, needs broadcast to a shared index. Same concepts, so the provenance story matches what they built.

**Pressure scoring** — use their published formula verbatim; it is a talking point:

```
pressure = 2.0*novelty + 1.0*centrality + 0.5*depth + 0.2*age
  novelty    = 1 / (1 + times_already_fulfilled)
  centrality = open needs of the same type with overlapping query tokens
  depth      = DAG depth of the parent artifact
  age        = round number
```

An agent **cannot fulfil its own need**. Fulfilled needs enter a `consumed` set so nothing is answered twice.

**The loop**, per gene:

```
round 0  burden, gwas, tolerance, safety run independently (parallel)
round 1  open needs ranked by pressure; whichever agent's capability matches
         picks one up and posts a fulfillment (variant/Evo 2 runs here if asked)
round 2  skeptic reads every artifact for the gene, posts challenges;
         a challenged agent may post a revision (parent = the old artifact)
score    scoring.py reads the artifacts, returns a float
```

**Nothing in this loop assigns work.** Put that in a code comment and say it in the demo — Decentralized Agency is 20%.

**`scoring.py`** — no LLM import:

```
score = Σ_channel  weight × stance × strength × discount
weights = 1.0 each (frozen) · supports=+1, neutral=0, against=−1
discount = 0.5 if a skeptic challenge names that channel
```

Use each channel's **latest** artifact; a revision supersedes its parent; a missing channel contributes 0.

> **GATE 12:00 AM** — the loop runs 10 genes, at least one need is fulfilled by a **different** agent, and at least one challenge changes a score. If not, run A1 only.

---

## Phase 5 — Arms · 12:00–12:30 AM launch, then sleep · branch `phase-5-arms`

```bash
python -m arms.run_arm --arm A3 --seed 1 --panel frozen/panel.csv --out runs/A3_s1
```

| Arm | LLM? | Implementation |
| --- | --- | --- |
| S1–S4 | no | `scripted.py` |
| **A1** | yes | **one** agent, **all five views concatenated**, same 10-call cap, one JSON verdict |
| **A3** | yes | the board loop |
| A3_noskeptic | **no** | `rescore.py`: drop challenge artifacts, re-score |
| A3_no\<agent> | **no** | drop that agent's artifacts, re-score |
| A3_isolated | **no** | keep round-0 artifacts only, re-score |
| Null | no | 1,000 label permutations on A3 scores |

**A1 is the arm judges will scrutinise. Make it genuinely strong**: every view, a good prompt, the full budget. A handicapped A1 makes the headline number worthless.

**Ablations are re-scoring passes over the saved board — zero extra LLM calls.** That is why six extra arms cost us two minutes instead of two hours.

Run A1 and A3 with **2 seeds** each. Parallelise with a `ThreadPoolExecutor` over genes (8–12 workers) behind a shared token-bucket limiter. Checkpoint after every gene so a crash resumes.

40 genes × \~10 calls × 4 LLM runs ≈ **1,600 calls ≈ 20–30 minutes**. Launch it and go to sleep.

---

## Phase 6 — Evaluation · 6:00–10:00 AM Sunday · branch `phase-6-eval`

**`metrics.py`**

- `auroc`, `auprc` (positives are 30% of a 40-gene panel, so AUPRC matters), `precision_at_k(k=12)`
- `bootstrap_ci(metric, n=1000, seed=SEED)` → point, lo, hi
- `permutation_null(scores, labels, n=1000, seed=SEED)` → empirical p
- **`paired_delta(a, b)`** — resample the panel, compute **both** arms on each resample, report the CI of the **difference**. This is the headline

**`report.py`** → `frozen_results/arms_table.md`

| Arm | AUROC (95% CI) | AUPRC | P@12 | Calls | $ | Δ vs S4 | Δ vs A1 |
| --- | --- | --- | --- | --- | --- | --- | --- |

Seeds as mean ± sd. Include A3's permutation p-value.

**`figures.py`** — five PNGs at 150 dpi:

1. ROC + PR curves, all arms
2. Arms bar chart with CI whiskers
3. **Provenance DAG for one gene** — nodes coloured by agent, edges = parent links, challenges marked ← the Decentralized Agency slide
4. Skeptic effect: genes whose rank moved
5. Cost vs AUROC scatter

**`make freeze-results`** immediately after. No tuning afterwards.

---

## Phase 7 — Slides and demo · 10:00 AM–1:00 PM

**Five slides**

1. **Problem** — the PCSK9 story → the evidence is scattered → why this needs a collective
2. **System** — the agent table, the board diagram, "no planner"
3. **Result** — the arms table with CIs, the Δ A3−A1 in large type, cost per arm
4. **Rigor** — the `prereg` commit hash, the blind panel, the null test, the limitations
5. **Discovery** — top-ranked negatives as novel candidates; skills if we published them

**Demo, 2 minutes** — pick one gene: artifacts appearing, a need raised by one agent and fulfilled by another, a skeptic challenge, the final score, the provenance graph.

**Push to GitHub with tags before judging.**

---

# 9. Whatever the result is, say it honestly

| Outcome | What we present |
| --- | --- |
| A3 > S4 and A1 | "Collective lift." Headline, with the paired-delta CI |
| A3 ≈ S4 | A dominant-signal regime. The value is provenance, trap-catching and cost transparency. **The organizers publish ties themselves** |
| A3 \< S4 | Report it. Use the ablations to explain why. NVIDIA's own material says losing to a fixed heuristic is still publishable |

**Never claim:** that top-ranked negatives are proven targets (they are hypotheses), or that anonymization removes all prior knowledge (it removes names and drug data; trait patterns remain). **Put those limitations on slide 4 ourselves**, before a judge raises them.

---

# 10. If time runs short

Cut in this order: extra seeds → per-agent ablations → skills → the Variant agent → the board loop (present A1 vs S4).

**Never cut:** the frozen panel, S4, A1, the permutation null, the `prereg` tag.

---

# 11. Makefile

```
make probe            # Phase 0
make data             # pool + per-gene pulls (cached)
make panel            # labels + panel + views + isolation tests
make freeze           # write frozen/, print git hash, refuse if dirty
make baselines        # S1–S4 table
make arm ARM=A3 SEED=1
make allarms          # A1 + A3 x2 seeds, parallel
make ablations        # re-scoring passes, no LLM
make freeze-results
make report           # arms table + figures
make test
```

---

# 12. Acceptance criteria

| Phase | Done when |
| --- | --- |
| 0 | LLM + Open Targets PASS. Evo 2 may fail (documented) |
| 1 | 40 view-sets exist; `test_views_isolation.py` passes; `prereg` tag exists |
| 2 | S1–S4 table with CIs printed |
| 3 | Every agent returns valid JSON for 5 genes; identity guard silent |
| 4 | 10 genes through the loop; a cross-agent fulfilment; a challenge that moves a score |
| 5 | A1 and A3 complete all 40 genes, 2 seeds |
| 6 | Arms table + 5 figures; results frozen |
| 7 | 5 slides, demo rehearsed, repo pushed |
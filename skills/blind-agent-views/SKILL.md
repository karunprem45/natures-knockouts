---
name: blind-agent-views
description: Split scattered evidence into per-agent folders so each agent sees one slice, nothing identifies the entity, and a test proves it. Use when building a multi-agent system whose claim depends on agents having distinct information.
---

# Blind agent views

A collective only shows decentralised capability if its agents genuinely see different things. This skill builds per-agent evidence folders and a test that fails loudly when they leak.

## When to use

- Several agents should each hold one evidence channel (assays, databases, modalities).
- The entity under study (gene, compound, patient) must stay anonymous to every prompt.
- A judge or reviewer will ask "how do you know the agents are really separate?"

## Steps

1. **Code the entities.** Map real IDs to neutral codes (`Gene_01…Gene_40`) with a seeded shuffle, so codes carry no label information. Keep the mapping and labels in a directory no agent code touches.
2. **Write one view per agent per entity**: `data/views/<agent>/<code>.json`. Each view holds only that agent's channel.
3. **Strip identity** from every view: symbols, names, synonyms, database IDs, literature IDs, coordinates. Drop whole rows whose free text mentions any known symbol or the entity's own protein name. Normalise Roman numerals ("C-III" → "c3") before matching.
4. **Coarsen eponyms.** Rare-disease names can identify an entity on their own ("Fish-eye disease" points to one gene). Replace them with category counts.
5. **Route label-like data elsewhere.** Anything that encodes the answer (here, drug-approval evidence) goes to the labels directory only.
6. **Enforce single-path reads.** Agents load views through one function that resolves the path and refuses anything outside `views/<self>/`.
7. **Test it** (see below), plant a leak once, and confirm the test fails.

## The isolation test

`tests/test_views_isolation.py` in this repo checks, for every view file:

- it parses as JSON, and its top-level keys are on that agent's allow-list
- no forbidden key appears anywhere (`symbol`, `ensembl_id`, `literature`, `drug`, …)
- no other channel's keys leak in (e.g. no `loeuf` in the burden view)
- no known symbol (word-boundary match) or ID pattern (`ENSG\d{11}`) appears
- the label source's name (`chembl`, `clinical_precedence`) appears nowhere

## Gotchas found the hard way

- **Open Targets 26.09 calls ChEMBL `clinical_precedence`.** Filtering only on "chembl" leaks drug data.
- **Short scope terms need word boundaries:** "AST" matches "waist".
- **Redact outputs too.** A model can recognise an entity from its trait pattern and name it; redact symbols in agent outputs before other agents read them, and count how often it happens.

## Code in this repo

`data_layer/build_views.py` (builder and `Scrubber`), `agents/base.py` (`load_view`), `llm/guards.py` (prompt guard and output redaction), `tests/test_views_isolation.py`.

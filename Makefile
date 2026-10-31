PY ?= .venv/bin/python
ARM ?= A3
SEED ?= 1

.PHONY: setup probe data panel freeze baselines arm allarms ablations freeze-results report test

setup:            ## create venv and install deps
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

probe:            ## Phase 0 — LLM + Open Targets must PASS; Evo 2 may fail
	@fail=0; \
	for p in llm opentargets ensembl evo2; do \
	  printf "%-12s " $$p; $(PY) -m probes.probe_$$p || { [ $$p = llm -o $$p = opentargets ] && fail=1; }; \
	done; exit $$fail

data:             ## Phase 1 — pool + per-gene pulls (cached)
	$(PY) -m data_layer.schema_probe
	$(PY) -m data_layer.fetch_pool
	$(PY) -m data_layer.fetch_gene

panel:            ## labels + panel + views + isolation tests
	$(PY) -m data_layer.build_labels
	$(PY) -m data_layer.build_panel
	$(PY) -m data_layer.build_views
	$(PY) -m pytest -q tests/test_views_isolation.py

freeze:           ## R6 — refuse if dirty, print hash
	@test -z "$$(git status --porcelain)" || { echo "refusing: working tree dirty"; exit 1; }
	@echo "frozen at $$(git rev-parse --short HEAD)"

baselines:        ## Phase 2 — S1–S4 table
	$(PY) -m data_layer.features
	$(PY) -m arms.scripted

arm:
	$(PY) -m arms.run_arm --arm $(ARM) --seed $(SEED) --panel frozen/panel.csv --out runs/$(ARM)_s$(SEED)

allarms:
	$(MAKE) arm ARM=A1 SEED=1 & $(MAKE) arm ARM=A1 SEED=2 & \
	$(MAKE) arm ARM=A3 SEED=1 & $(MAKE) arm ARM=A3 SEED=2 & wait

ablations:        ## re-scoring passes, no LLM
	$(PY) -m arms.rescore

freeze-results:   ## R7
	$(PY) -m eval.freeze_results

report:
	$(PY) -m eval.report
	$(PY) -m eval.figures

test:
	$(PY) -m pytest -q

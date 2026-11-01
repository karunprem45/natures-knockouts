"""Shared test helpers. Tests that read the local evidence views skip, with the reason, when data/ has not been
built (it is gitignored); build it with `make data panel` (Open Targets and Ensembl, no API key needed)."""
import pytest
import config

HAS_DATA = (config.VIEWS_DIR.exists() and (config.DATA_DIR / "symbol_map.json").exists()
            and (config.LABELS_DIR / "panel_labels.csv").exists())
requires_data = pytest.mark.skipif(not HAS_DATA, reason="needs local data/ (gitignored): run `make data panel`")

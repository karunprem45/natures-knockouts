"""Evo 2 scoring and the Variant agent, offline with fake logits (no NVIDIA or Ensembl calls)."""
import json
import numpy as np
import pytest
import config
from tools import evo2

SEQ = "ACGTACGTAC" * 6   # 60 bp


def fake_logits(seq):
    """A 'genome model' that strongly expects A after every position, so A->other substitutions
    at a site look disruptive and other->A look favourable."""
    out = np.zeros((len(seq), 512), dtype=np.float32)
    out[:, ord("A")] = 5.0
    return out


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(evo2, "logits", fake_logits)


def test_reference_mismatch_refuses():
    with pytest.raises(evo2.Evo2Error, match="reference mismatch"):
        evo2.score_snv(SEQ, 4, "C", "T")   # SEQ[4] is A


def test_disruptive_snv_ranks_low_and_delta_negative():
    out = evo2.score_snv(SEQ, 4, "A", "G")    # losing an expected A
    assert out["delta_ll"] < 0
    assert out["site_percentile"] < 10
    assert out["n_possible_snvs"] == 3 * (len(SEQ) - 1)


def test_favourable_snv_ranks_high():
    out = evo2.score_snv(SEQ, 5, "C", "A")    # gaining the expected A
    assert out["delta_ll"] > 0 and out["site_percentile"] > 50


def test_length_mismatch_from_api_refuses(monkeypatch, tmp_path):
    monkeypatch.undo()
    monkeypatch.setattr(evo2, "CACHE", tmp_path)
    monkeypatch.setattr(evo2, "_winner", lambda: {"url": "x", "layer": "unembed"})
    monkeypatch.setenv("NVIDIA_API_KEY", "test")

    class R:
        status_code = 200
        def json(self): return {"data": ""}
    monkeypatch.setattr(evo2.requests, "post", lambda *a, **k: R())
    monkeypatch.setattr(evo2, "_decode", lambda body, layer: np.zeros((len(SEQ) - 1, 512)))
    with pytest.raises(evo2.Evo2Error, match="refusing to align"):
        evo2.logits(SEQ)


def test_variant_prompt_never_contains_coordinates(monkeypatch):
    from agents.variant import VariantAgent
    from tools import ensembl
    seen = {}

    class Client:
        def complete_json(self, **kw):
            seen["prompt"] = kw["prompt"]
            return {"stance": "supports", "strength": 0.7, "rationale": "disruptive", "data_refs": []}, None

    agent = VariantAgent(Client())
    view = {"available": True, "chrom": "1", "pos": 55063514, "ref": "A", "alt": "G"}
    monkeypatch.setattr(agent, "load_view", lambda code: view)
    window = "C" * (config.EVO2_WINDOW_BP // 2) + "A" + "C" * (config.EVO2_WINDOW_BP // 2 - 1)
    monkeypatch.setattr(ensembl, "region", lambda c, s, e: window)
    from board.artifact import Artifact
    parent = Artifact("evidence", "burden", "Gene_01", 0)
    art = agent.fulfil("Gene_01", {"query": "is the lead variant disruptive?", "rationale": ""}, parent)
    assert art.artifact_type == "fulfillment" and art.producer_agent == "variant"
    assert "55063514" not in seen["prompt"] and "chrom" not in seen["prompt"]
    assert any(f.startswith("evo2_percentile:") for f in art.flags)


def test_variant_agent_skips_round0(tmp_path):
    from agents.variant import VariantAgent
    assert VariantAgent.posts_round0 is False

"""R1 budget, R2 view access, R3 no label access, R4 identity guard — all offline, no LLM calls."""
import csv, json
from pathlib import Path
import pytest
import config
from agents import EVIDENCE_AGENT_CLASSES
from agents.base import ViewAccessError
from agents.skeptic import SkepticAgent
from board.artifact import Artifact
from llm import guards
from tests.conftest import requires_data

ROOT = Path(__file__).resolve().parents[1]


class NoCallClient:
    def complete_json(self, **kw):
        raise AssertionError("tests must not call the LLM")


def panel_codes():
    with (config.FROZEN_DIR / "panel.csv").open() as f:
        return [r["gene_code"] for r in csv.DictReader(f)]


def test_identity_guard_catches_symbol_and_ensembl_id():
    with pytest.raises(guards.IdentityLeak):
        guards.assert_no_identity("the gene PCSK9 lowers LDL")
    with pytest.raises(guards.IdentityLeak):
        guards.assert_no_identity("target ENSG00000169174")
    guards.assert_no_identity("low density lipoprotein cholesterol measurement")


def test_label_guard():
    with pytest.raises(guards.LabelLeak):
        guards.assert_no_labels("ChEMBL says approved")


def test_budget_cap_is_enforced_per_arm_and_gene():
    b = guards.Budget(cap=config.MAX_LLM_CALLS_PER_GENE)
    for _ in range(config.MAX_LLM_CALLS_PER_GENE):
        b.take("A3", "Gene_01")
    with pytest.raises(guards.BudgetExceeded):
        b.take("A3", "Gene_01")
    b.take("A3", "Gene_02")
    b.take("A1", "Gene_01")


@requires_data
@pytest.mark.parametrize("name", sorted(EVIDENCE_AGENT_CLASSES))
def test_every_rendered_prompt_passes_guards(name):
    agent = EVIDENCE_AGENT_CLASSES[name](NoCallClient())
    for code in panel_codes():
        prompt = agent.render(code, task="TASK")
        guards.assert_no_identity(prompt)
        guards.assert_no_labels(prompt)


@pytest.mark.parametrize("name", sorted(EVIDENCE_AGENT_CLASSES))
def test_agent_cannot_read_another_view(name):
    agent = EVIDENCE_AGENT_CLASSES[name](NoCallClient())
    other = next(a for a in EVIDENCE_AGENT_CLASSES if a != name)
    with pytest.raises(ViewAccessError):
        agent.load_view(f"../{other}/Gene_01")
    with pytest.raises(ViewAccessError):
        agent.load_view("../../labels/panel_labels")


def test_skeptic_has_no_data_tool():
    s = SkepticAgent(NoCallClient())
    assert not hasattr(s, "load_view") and not hasattr(s, "render")


def test_agent_code_never_touches_labels():
    for d in ("agents", "llm", "board"):
        for f in (ROOT / d).rglob("*.py"):
            text = f.read_text()
            assert "LABELS_DIR" not in text and "data/labels" not in text, f


def test_artifact_hash_is_content_based():
    a = Artifact("evidence", "burden", "Gene_01", 0, stance="supports", strength=0.5)
    b = Artifact("evidence", "burden", "Gene_01", 0, stance="supports", strength=0.5)
    assert a.content_hash == b.content_hash and a.artifact_id != b.artifact_id


def test_agent_output_naming_a_gene_is_redacted_and_flagged():
    from agents.base import redact_output
    text, needs, flags = redact_output("Looks like APOC3 deficiency",
                                       [{"type": "tolerance_check", "query": "is PCSK9 tolerated", "rationale": ""}])
    assert "APOC3" not in text and "PCSK9" not in needs[0]["query"]
    assert flags == ["identity_named:2"]

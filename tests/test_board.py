"""Board, needs, loop and scoring — offline, with scripted fake agents."""
import pytest
import config
import scoring
from board.artifact import Artifact, ArtifactStore
from board.loop import run_gene
from board.needs import NeedIndex
from llm.guards import Budget, BudgetExceeded


def ev(agent, stance="supports", strength=0.8, needs=(), round_=0):
    return Artifact("evidence", agent, "Gene_01", round_, stance=stance, strength=strength, needs=list(needs))


# ---------- scoring (R5) ----------

def test_scoring_imports_no_llm():
    src = open(scoring.__file__).read()
    assert "from llm" not in src and "import llm" not in src and "openai" not in src


def test_score_sums_channels_and_missing_is_zero():
    arts = [ev("burden", "supports", 0.8), ev("tolerance", "against", 0.5)]
    total, parts = scoring.score(arts, return_breakdown=True)
    assert total == pytest.approx(0.3) and parts["gwas"] == 0.0


def test_revision_supersedes_parent_and_challenge_halves_channel():
    e = ev("burden", "supports", 0.8)
    r = Artifact("revision", "burden", "Gene_01", 2, stance="supports", strength=0.4, parent_artifact_ids=[e.artifact_id])
    c = Artifact("challenge", "skeptic", "Gene_01", 2, challenges=[{"type": "single_cohort", "channel": "burden",
                                                                  "target_artifact_id": e.artifact_id, "rationale": ""}])
    assert scoring.score([e]) == pytest.approx(0.8)
    assert scoring.score([e, r]) == pytest.approx(0.4)
    assert scoring.score([e, r, c]) == pytest.approx(0.2)


def test_error_and_fulfilment_artifacts_are_not_scored():
    e = Artifact("error", "gwas", "Gene_01", 0, error="x")
    f = Artifact("fulfillment", "tolerance", "Gene_01", 1, stance="supports", strength=1.0)
    assert scoring.score([e, f]) == 0.0


# ---------- needs ----------

def test_pressure_formula_and_no_self_fulfilment():
    a = ev("burden", needs=[{"type": "tolerance_check", "query": "is loss of function tolerated", "rationale": ""}])
    b = ev("gwas", needs=[{"type": "tolerance_check", "query": "loss of function tolerated in humans", "rationale": ""}])
    idx = NeedIndex()
    idx.post_from(a, depth=0)
    idx.post_from(b, depth=0)
    need, p = idx.best_for("tolerance", current_round=1)
    # novelty 1 (x2.0) + centrality 1 (overlapping tokens) + depth 0 + age 1 (x0.2)
    assert p == pytest.approx(2.0 + 1.0 + 0.0 + 0.2)
    assert idx.best_for("burden", 1)[0] is None
    idx.consume(need)
    need2, p2 = idx.best_for("tolerance", 1)
    assert need2.need_id != need.need_id and p2 == pytest.approx(2.0 * 0.5 + 0 + 0 + 0.2)


# ---------- loop with fake agents ----------

class FakeClient:
    arm = "test"

    def __init__(self):
        self.budget = Budget()


class FakeAgent:
    def __init__(self, name, client, stance, needs):
        self.name, self.client, self.stance, self.needs = name, client, stance, needs

    def _take(self, gene):
        self.client.budget.take(self.client.arm, gene)

    def evidence(self, gene, round_=0):
        self._take(gene)
        return Artifact("evidence", self.name, gene, round_, stance=self.stance, strength=0.8, needs=self.needs)

    def fulfil(self, gene, need, parent, round_=1):
        self._take(gene)
        return Artifact("fulfillment", self.name, gene, round_, stance="against", strength=0.9,
                        parent_artifact_ids=[parent.artifact_id])

    def revise(self, gene, parent, challenges=(), answers=(), round_=2):
        self._take(gene)
        return Artifact("revision", self.name, gene, round_, stance=parent.stance, strength=0.3,
                        parent_artifact_ids=[parent.artifact_id] + [a.artifact_id for a in answers])


class FakeSkeptic:
    def __init__(self, client):
        self.client = client

    def review(self, gene, arts, round_=2):
        self.client.budget.take(self.client.arm, gene)
        return Artifact("challenge", "skeptic", gene, round_,
                        challenges=[{"type": "single_cohort", "channel": "burden", "target_artifact_id": None,
                                     "rationale": ""}])


def make(tmp_path):
    client = FakeClient()
    tol_need = [{"type": "tolerance_check", "query": "is it tolerated", "rationale": ""}]
    agents = {"burden": FakeAgent("burden", client, "supports", tol_need),
              "gwas": FakeAgent("gwas", client, "supports", [{"type": "burden_check", "query": "burden?", "rationale": ""}]),
              "tolerance": FakeAgent("tolerance", client, "supports", []),
              "safety": FakeAgent("safety", client, "neutral", tol_need)}
    return client, agents, FakeSkeptic(client), ArtifactStore(tmp_path / "board.jsonl")


def test_loop_cross_agent_fulfilment_challenge_and_budget(tmp_path):
    client, agents, skeptic, store = make(tmp_path)
    arts = run_gene("Gene_01", agents, skeptic, client, store)
    fulfil = [a for a in arts if a.artifact_type == "fulfillment"]
    assert fulfil, "no need was fulfilled"
    by_id = {a.artifact_id: a for a in arts}
    assert all(by_id[f.parent_artifact_ids[0]].producer_agent != f.producer_agent for f in fulfil)
    assert any(a.artifact_type == "challenge" for a in arts)
    assert any(a.artifact_type == "revision" for a in arts)
    assert client.budget.used[("test", "Gene_01")] <= config.MAX_LLM_CALLS_PER_GENE
    assert len(store.all("Gene_01")) == len(arts)


def test_loop_without_skeptic_posts_no_challenge(tmp_path):
    client, agents, skeptic, store = make(tmp_path)
    arts = run_gene("Gene_01", agents, skeptic, client, store, use_skeptic=False)
    assert not any(a.artifact_type == "challenge" for a in arts)


def test_loop_source_says_no_assignment():
    import board.loop as loop
    assert "NOTHING IN THIS LOOP ASSIGNS WORK" in open(loop.__file__).read()

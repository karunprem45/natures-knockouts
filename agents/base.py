"""Agent base: load ONLY this agent's view (R2), render its prompt, call the LLM, return an Artifact."""
import json
from pathlib import Path
import config
from board.artifact import Artifact
from llm.guards import redact_identity

PROMPTS = Path(__file__).with_name("prompts")
STANCES = {"supports", "against", "neutral"}

EVIDENCE_SCHEMA = json.dumps({
    "stance": "supports | against | neutral",
    "strength": "number 0.0-1.0, how strongly your evidence backs the stance",
    "rationale": "string, at most 200 characters",
    "data_refs": ["refs of the rows you relied on, e.g. burden_1"],
    "needs": [{"type": "one of " + ", ".join(sorted(config.NEED_TYPES)),
               "query": "what you need checked, in plain words",
               "rationale": "why it would change your verdict"}],
}, indent=1)


class ViewAccessError(RuntimeError):
    pass


def clean_needs(raw_needs, own_agent):
    out = []
    for n in raw_needs or []:
        if not isinstance(n, dict) or n.get("type") not in config.NEED_TYPES:
            continue
        if config.NEED_TYPES[n["type"]] == own_agent:   # cannot ask yourself
            continue
        if config.NEED_TYPES[n["type"]] not in config.ACTIVE_EVIDENCE_AGENTS:
            continue
        out.append({"type": n["type"], "query": str(n.get("query", ""))[:300],
                    "rationale": str(n.get("rationale", ""))[:300]})
    return out


def redact_output(rationale, needs):
    """An agent may recognise a gene from its trait pattern and name it. The name is redacted
    before anyone else reads it, and the artifact is flagged so leaks are counted, not hidden."""
    rationale, found = redact_identity(rationale)
    for n in needs:
        n["query"], f1 = redact_identity(n["query"])
        n["rationale"], f2 = redact_identity(n["rationale"])
        found += f1 + f2
    return rationale, needs, ([f"identity_named:{len(set(found))}"] if found else [])


def coerce_verdict(d):
    stance = d.get("stance") if d.get("stance") in STANCES else "neutral"
    try:
        strength = min(1.0, max(0.0, float(d.get("strength", 0.0))))
    except (TypeError, ValueError):
        strength = 0.0
    refs = [str(r) for r in d.get("data_refs") or [] if isinstance(r, (str, int))]
    return stance, strength, str(d.get("rationale", ""))[:200], refs


class Agent:
    name = None            # also the view directory name
    capability = None      # need type this agent can fulfil

    def __init__(self, client):
        self.client = client
        self.template = (PROMPTS / f"{self.name}.txt").read_text()

    def load_view(self, gene_code):
        """The only file read an agent makes. Anything outside data/views/<self.name>/ is refused."""
        root = (config.VIEWS_DIR / self.name).resolve()
        path = (root / f"{gene_code}.json").resolve()
        if root not in path.parents:
            raise ViewAccessError(f"{self.name} may not read {path}")
        return json.loads(path.read_text())

    def render(self, gene_code, **extra):
        view = self.load_view(gene_code)
        view.pop("gene_code", None)
        return self.template.format(view=json.dumps(view, indent=1, sort_keys=True), **extra)

    def _ask(self, gene_code, prompt, round_, artifact_type, parents=()):
        parsed, err = self.client.complete_json(agent=self.name, gene_code=gene_code,
                                                prompt=prompt, schema=EVIDENCE_SCHEMA)
        if parsed is None:  # R10: error artifact + neutral stance, never a fabricated value
            return Artifact("error", self.name, gene_code, round_, error=err,
                            parent_artifact_ids=list(parents))
        stance, strength, rationale, refs = coerce_verdict(parsed)
        rationale, needs, flags = redact_output(rationale, clean_needs(parsed.get("needs"), self.name))
        return Artifact(artifact_type, self.name, gene_code, round_, stance=stance, strength=strength,
                        rationale=rationale, data_refs=refs, parent_artifact_ids=list(parents),
                        needs=needs, flags=flags)

    def evidence(self, gene_code, round_=0):
        prompt = self.render(gene_code, task=(PROMPTS / "_task_evidence.txt").read_text())
        return self._ask(gene_code, prompt, round_, "evidence")

    def fulfil(self, gene_code, need, parent, round_=1):
        """Answer another agent's broadcast need using only this agent's own view."""
        task = (PROMPTS / "_task_fulfil.txt").read_text().format(
            requester=parent.producer_agent, query=need["query"], why=need["rationale"])
        return self._ask(gene_code, self.render(gene_code, task=task), round_, "fulfillment", [parent.artifact_id])

    def revise(self, gene_code, challenge, parent, round_=2):
        """Reconsider an earlier artifact in light of a skeptic challenge."""
        task = (PROMPTS / "_task_revise.txt").read_text().format(
            ctype=challenge["type"], why=challenge["rationale"], stance=parent.stance,
            strength=parent.strength, rationale=parent.rationale)
        return self._ask(gene_code, self.render(gene_code, task=task), round_, "revision", [parent.artifact_id])

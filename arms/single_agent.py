"""A1: ONE agent sees all four views, with the same per-gene call cap and the same scoring.

Kept genuinely strong (BUILD.md Phase 5): every view, the specialists' own guidance text verbatim,
and the same three steps the collective gets in round 0 and round 2 — assess every channel,
review itself with the skeptic's challenge types, revise. What A1 lacks is only the decentralised
structure: separate views, needs broadcast between agents, an independent skeptic.
scoring.py computes the score from A1's per-channel verdicts exactly as for A3 (R5).
"""
import json, re
import config
from agents import EVIDENCE_AGENT_CLASSES
from agents.base import PROMPTS, coerce_verdict, redact_output
from board.artifact import Artifact
from llm.guards import BudgetExceeded

CHANNELS = sorted(EVIDENCE_AGENT_CLASSES)
VERDICT = {"stance": "supports | against | neutral", "strength": "0.0-1.0",
           "rationale": "at most 200 characters", "data_refs": ["row refs"]}
ASSESS_SCHEMA = json.dumps({"channels": {c: VERDICT for c in CHANNELS}}, indent=1)
CRITIQUE_SCHEMA = json.dumps({"challenges": [{"type": "one of " + ", ".join(config.SKEPTIC_CHALLENGES),
                                              "channel": " | ".join(CHANNELS),
                                              "rationale": "at most 200 characters"}]}, indent=1)


def guidance():
    """The 'YOU SEE ... how to read it' section of each specialist prompt, verbatim."""
    parts = []
    for c in CHANNELS:
        text = (PROMPTS / f"{c}.txt").read_text()
        body = text[text.index("YOU SEE"):text.index("Typical needs")].strip()
        body = re.sub(r"YOU CANNOT SEE:.*?\n\n", "", body, flags=re.S)  # A1 sees everything
        parts.append(f"=== {c.upper()} CHANNEL ===\n{body}")
    return "\n\n".join(parts)


class SingleAgent:
    name = "single"

    def __init__(self, client):
        self.client = client
        self.viewers = {c: EVIDENCE_AGENT_CLASSES[c](client) for c in CHANNELS}  # same R2 read path
        self.template = (PROMPTS / "single_agent.txt").read_text()
        self.guidance = guidance()

    def _prompt(self, gene_code, task):
        views = []
        for c in CHANNELS:
            v = self.viewers[c].load_view(gene_code)
            v.pop("gene_code", None)
            views.append(f"--- {c} ---\n{json.dumps(v, indent=1, sort_keys=True)}")
        return self.template.format(guidance=self.guidance, task=task, views="\n\n".join(views))

    def _ask(self, gene_code, task, schema, list_key=None):
        try:
            return self.client.complete_json(agent=self.name, gene_code=gene_code,
                                             prompt=self._prompt(gene_code, task), schema=schema,
                                             list_key=list_key)
        except BudgetExceeded as e:
            return None, str(e)

    def _verdicts(self, gene_code, parsed, round_, kind, parents=None):
        arts = []
        chans = (parsed or {}).get("channels") or {}
        for c in CHANNELS:
            d = chans.get(c) if isinstance(chans.get(c), dict) else {}
            stance, strength, rationale, refs = coerce_verdict(d)
            rationale, _, flags = redact_output(rationale, [])
            arts.append(Artifact(kind, c, gene_code, round_, stance=stance, strength=strength,
                                 rationale=rationale, data_refs=refs, flags=["single_agent"] + flags,
                                 parent_artifact_ids=[parents[c].artifact_id] if parents else []))
        return arts

    @staticmethod
    def _fmt(arts):
        return json.dumps({a.producer_agent: {"stance": a.stance, "strength": a.strength,
                                              "rationale": a.rationale} for a in arts}, indent=1)

    def run(self, gene_code):
        task = (PROMPTS / "_task_single_assess.txt").read_text()
        parsed, err = self._ask(gene_code, task, ASSESS_SCHEMA)
        if parsed is None:
            return [Artifact("error", self.name, gene_code, 0, error=err)]
        first = self._verdicts(gene_code, parsed, 0, "evidence")
        arts = list(first)

        task = (PROMPTS / "_task_single_critique.txt").read_text().format(verdicts=self._fmt(first))
        parsed, err = self._ask(gene_code, task, CRITIQUE_SCHEMA, list_key="challenges")
        if parsed is None:
            return arts + [Artifact("error", self.name, gene_code, 2, error=err)]
        by_c = {a.producer_agent: a for a in first}
        challenges = []
        for c in parsed.get("challenges") or []:
            if isinstance(c, dict) and c.get("type") in config.SKEPTIC_CHALLENGES and c.get("channel") in CHANNELS:
                challenges.append({"type": c["type"], "channel": c["channel"],
                                   "target_artifact_id": by_c[c["channel"]].artifact_id,
                                   "rationale": redact_output(str(c.get("rationale", ""))[:200], [])[0]})
        arts.append(Artifact("challenge", self.name, gene_code, 2, challenges=challenges,
                             parent_artifact_ids=sorted({c["target_artifact_id"] for c in challenges}),
                             rationale=f"{len(challenges)} self-challenge(s)", flags=["single_agent"]))
        if not challenges:
            return arts

        task = (PROMPTS / "_task_single_revise.txt").read_text().format(
            verdicts=self._fmt(first), challenges=json.dumps(challenges, indent=1))
        parsed, err = self._ask(gene_code, task, ASSESS_SCHEMA)
        if parsed is None:
            return arts + [Artifact("error", self.name, gene_code, 2, error=err)]
        return arts + self._verdicts(gene_code, parsed, 2, "revision", parents=by_c)

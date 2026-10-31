"""The Skeptic: no data tool at all. Reads every artifact for a gene and posts challenges."""
import json
import config
from agents.base import PROMPTS
from board.artifact import Artifact
from llm.guards import redact_identity

SCHEMA = json.dumps({"challenges": [{
    "type": "one of " + ", ".join(config.SKEPTIC_CHALLENGES),
    "channel": "the channel discounted: burden | gwas | tolerance | safety",
    "target": "the artifact ref you challenge, e.g. A1",
    "rationale": "at most 200 characters"}]}, indent=1)


class SkepticAgent:
    name = "skeptic"

    def __init__(self, client):
        self.client = client
        self.template = (PROMPTS / "skeptic.txt").read_text()

    def review(self, gene_code, artifacts, round_=2):
        shown = [a for a in artifacts if a.artifact_type in ("evidence", "fulfillment", "revision")]
        refs = {f"A{i}": a for i, a in enumerate(shown, 1)}
        listing = json.dumps([{"ref": r, "agent": a.producer_agent, "type": a.artifact_type,
                               "stance": a.stance, "strength": a.strength, "rationale": a.rationale,
                               "data_refs": a.data_refs} for r, a in refs.items()], indent=1)
        parsed, err = self.client.complete_json(agent=self.name, gene_code=gene_code,
                                                prompt=self.template.format(artifacts=listing), schema=SCHEMA,
                                                list_key="challenges")
        if parsed is None:
            return Artifact("error", self.name, gene_code, round_, error=err)
        challenges, found = [], []
        for c in parsed.get("challenges") or []:
            if not isinstance(c, dict) or c.get("type") not in config.SKEPTIC_CHALLENGES:
                continue
            if c.get("channel") not in config.ACTIVE_EVIDENCE_AGENTS:
                continue
            target = refs.get(str(c.get("target")))
            why, f = redact_identity(str(c.get("rationale", ""))[:200])
            found += f
            challenges.append({"type": c["type"], "channel": c["channel"],
                               "target_artifact_id": target.artifact_id if target else None,
                               "rationale": why})
        parents = sorted({c["target_artifact_id"] for c in challenges if c["target_artifact_id"]})
        return Artifact("challenge", self.name, gene_code, round_, challenges=challenges,
                        parent_artifact_ids=parents, rationale=f"{len(challenges)} challenge(s)",
                        flags=[f"identity_named:{len(set(found))}"] if found else [])

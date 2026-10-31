"""Needs broadcast to a shared index, ranked by the organizers' pressure formula (verbatim):

    pressure = 2.0*novelty + 1.0*centrality + 0.5*depth + 0.2*age
      novelty    = 1 / (1 + times_already_fulfilled)
      centrality = open needs of the same type with overlapping query tokens
      depth      = DAG depth of the parent artifact
      age        = round number
"""
import re
from dataclasses import dataclass
import config

STOP = {"the", "a", "an", "of", "is", "are", "to", "in", "for", "and", "or", "this", "gene", "does", "do",
        "with", "on", "be", "it", "its", "any", "there", "what", "whether", "if", "can", "would"}


def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP and len(t) > 2}


@dataclass
class NeedItem:
    need_id: str
    type: str
    query: str
    rationale: str
    requester: str
    parent_artifact_id: str
    round_posted: int
    depth: int

    @property
    def capability(self):
        return config.NEED_TYPES[self.type]


class NeedIndex:
    """Shared, per-gene index of open needs. It ranks; it never assigns."""

    def __init__(self):
        self.items = []
        self.consumed = set()
        self.fulfilled_by_type = {}

    def post_from(self, artifact, depth):
        for i, n in enumerate(artifact.needs):
            self.items.append(NeedItem(f"{artifact.artifact_id}:{i}", n["type"], n["query"], n["rationale"],
                                       artifact.producer_agent, artifact.artifact_id, artifact.round, depth))

    def open(self):
        return [n for n in self.items if n.need_id not in self.consumed]

    def pressure(self, need, current_round):
        novelty = 1.0 / (1 + self.fulfilled_by_type.get(need.type, 0))
        mine = tokens(need.query)
        centrality = sum(1 for o in self.open()
                         if o.need_id != need.need_id and o.type == need.type and mine & tokens(o.query))
        age = current_round - need.round_posted
        return (config.PRESSURE_W_NOVELTY * novelty + config.PRESSURE_W_CENTRALITY * centrality
                + config.PRESSURE_W_DEPTH * need.depth + config.PRESSURE_W_AGE * age)

    def best_for(self, agent_name, current_round):
        """What an agent sees when IT looks at the board: the highest-pressure open need it is able to
        answer and did not raise itself. Ties break on need_id so runs are deterministic."""
        mine = [n for n in self.open() if n.capability == agent_name and n.requester != agent_name]
        if not mine:
            return None, 0.0
        scored = sorted(((self.pressure(n, current_round), n) for n in mine), key=lambda x: (-x[0], x[1].need_id))
        return scored[0][1], scored[0][0]

    def consume(self, need):
        self.consumed.add(need.need_id)
        self.fulfilled_by_type[need.type] = self.fulfilled_by_type.get(need.type, 0) + 1

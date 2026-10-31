"""A3: the decentralised collective — four evidence agents + skeptic on the shared board."""
from agents import EVIDENCE_AGENT_CLASSES, SkepticAgent
from board.loop import run_gene


class Collective:
    def __init__(self, client, store):
        self.client, self.store = client, store
        self.agents = {n: cls(client) for n, cls in EVIDENCE_AGENT_CLASSES.items()}
        self.skeptic = SkepticAgent(client)

    def run(self, gene_code):
        return run_gene(gene_code, self.agents, self.skeptic, self.client, self.store)

"""Variant agent (NVIDIA Evo 2). Answers `variant_check` needs only; it posts nothing in round 0.

Reads data/views/variant/<gene>.json (lead variant chrom/pos/ref/alt), scores it with Evo 2, and asks
the LLM to interpret ONLY the resulting numbers: coordinates never reach a prompt (R4).
"""
import json
import config
from agents.base import PROMPTS, Agent
from board.artifact import Artifact
from tools import ensembl, evo2


class VariantAgent(Agent):
    name = "variant"
    capability = "variant_check"
    posts_round0 = False

    def evo2_numbers(self, gene_code):
        v = self.load_view(gene_code)
        if not v.get("available"):
            return {"error": "no lead variant with coordinates for this gene"}
        half = config.EVO2_WINDOW_BP // 2
        start = int(v["pos"]) - half
        try:
            seq = ensembl.region(v["chrom"], start, start + config.EVO2_WINDOW_BP - 1)
            return evo2.score_snv(seq, int(v["pos"]) - start, v["ref"], v["alt"])
        except Exception as e:  # R10: report the failure, never fabricate a score
            return {"error": str(e)[:200]}

    def render(self, gene_code, numbers=None, **extra):
        numbers = self.evo2_numbers(gene_code) if numbers is None else numbers
        return self.template.format(evo2=json.dumps(numbers, indent=1, sort_keys=True), **extra)

    def evidence(self, gene_code, round_=0):
        raise RuntimeError("the Variant agent only answers variant_check needs")

    def fulfil(self, gene_code, need, parent, round_=1):
        """Numbers are computed per call and passed through: no shared state, because genes run
        in parallel threads on one agent instance."""
        numbers = self.evo2_numbers(gene_code)
        task = (PROMPTS / "_task_fulfil.txt").read_text().format(
            requester=parent.producer_agent, query=need["query"], why=need["rationale"])
        art = self._ask(gene_code, self.render(gene_code, numbers=numbers, task=task), round_,
                        "fulfillment", [parent.artifact_id])
        if "error" in numbers:
            return art.add_flag("evo2_error")
        if "site_percentile" in numbers:
            return art.add_flag(f"evo2_percentile:{numbers['site_percentile']}")
        return art.add_flag(f"evo2_delta_ll:{numbers['delta_ll']}")

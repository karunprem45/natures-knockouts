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

    def render(self, gene_code, **extra):
        numbers = self.evo2_numbers(gene_code)
        self._last_numbers = numbers
        return self.template.format(evo2=json.dumps(numbers, indent=1, sort_keys=True), **extra)

    def evidence(self, gene_code, round_=0):
        raise RuntimeError("the Variant agent only answers variant_check needs")

    def fulfil(self, gene_code, need, parent, round_=1):
        art = super().fulfil(gene_code, need, parent, round_)
        nums = getattr(self, "_last_numbers", {})
        if "error" in nums:
            art = art.add_flag("evo2_error")
        elif "site_percentile" in nums:
            art = art.add_flag(f"evo2_percentile:{nums['site_percentile']}")
        return art

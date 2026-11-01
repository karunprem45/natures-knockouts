"""T3 step D: A3 + Variant (seed 1) with the coding-variant Evo 2 summary as the Variant agent's input.

  python -m exploratory.evo2_coding.run_arm_coding      -> exploratory/evo2_coding/A3_variant_coding_s1

Everything else is the existing A3 + Variant run: same loop, agents, budget, scoring. The Variant agent's
evo2_numbers() returns this gene's precomputed coding summary (gene_summary.json) instead of scoring its GWAS
lead variant, and its prompt describes that summary. Coordinates never reach a prompt.
"""
import json
from pathlib import Path
import agents.variant as variant_module
from agents.variant import VariantAgent
from arms import run_arm

HERE = Path(__file__).resolve().parent
SUMMARY = json.loads((HERE / "gene_summary.json").read_text())


class CodingVariantAgent(VariantAgent):
    def __init__(self, client):
        super().__init__(client)
        self.template = (HERE / "variant_coding.txt").read_text()

    def evo2_numbers(self, gene_code):
        s = SUMMARY.get(gene_code)
        if not s or not s["n_variants_scored"]:
            return {"error": "no predicted loss-of-function variant could be scored for this gene"}
        out = {k: v for k, v in s.items() if k != "n_errors"}
        out["delta_ll"] = s["strongest_delta_ll"]            # keys the base class uses for its flags
        if s["lowest_site_percentile"] is not None:
            out["site_percentile"] = s["lowest_site_percentile"]
        return out


def main():
    variant_module.VariantAgent = CodingVariantAgent       # Collective imports it from this module at run time
    run_arm.main(["--arm", "A3", "--seed", "1", "--variant", "--out",
                  str(HERE / "A3_variant_coding_s1"), "--workers", "5"])


if __name__ == "__main__":
    main()

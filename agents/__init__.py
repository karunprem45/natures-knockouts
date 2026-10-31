from agents.burden import BurdenAgent
from agents.gwas import GwasAgent
from agents.safety import SafetyAgent
from agents.skeptic import SkepticAgent
from agents.tolerance import ToleranceAgent

EVIDENCE_AGENT_CLASSES = {"burden": BurdenAgent, "gwas": GwasAgent,
                          "tolerance": ToleranceAgent, "safety": SafetyAgent}

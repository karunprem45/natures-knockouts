"""Calibrated scorer for P2-1. Identical to scoring.py except the skeptic discount: instead of a flat 0.5 for any
challenged channel, a channel takes the minimum calibrated multiplier over the challenge types naming it
(exploratory/v2/calibration.json). scoring.py itself is unchanged. Imports no LLM code."""
import json
from pathlib import Path
import config
from scoring import latest_verdicts

CAL = json.loads((Path(__file__).with_name("calibration.json")).read_text())["types"]


def channel_multipliers(artifacts):
    mult = {}
    for a in artifacts:
        if a.artifact_type == "challenge":
            for c in a.challenges:
                m = CAL.get(c["type"], {"multiplier": config.SKEPTIC_DISCOUNT})["multiplier"]
                mult[c["channel"]] = min(mult.get(c["channel"], 1.0), m)
    return mult


def score(artifacts):
    latest = latest_verdicts(artifacts)
    mult = channel_multipliers(artifacts)
    total = 0.0
    for channel, weight in sorted(config.CHANNEL_WEIGHTS.items()):
        a = latest.get(channel)
        if a is not None:
            total += weight * config.STANCE_VALUE[a.stance] * a.strength * mult.get(channel, 1.0)
    return total

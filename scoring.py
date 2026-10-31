"""R5: Python computes the final score. This module imports no LLM code.

score = sum over channels of weight x stance x strength x discount
  weights from frozen/weights.json-equivalent constants in config (1.0 each)
  supports = +1, neutral = 0, against = -1
  discount = 0.5 if any skeptic challenge names that channel
Each channel uses its LATEST verdict: a revision supersedes its parent. Fulfilments are answers to
other agents' needs and are not scored directly. Missing or errored channels contribute 0.
"""
import config

SCORED_TYPES = ("evidence", "revision")


def latest_verdicts(artifacts):
    by_id = {a.artifact_id: a for a in artifacts}
    superseded = {p for a in artifacts if a.artifact_type == "revision" for p in a.parent_artifact_ids
                  if p in by_id and by_id[p].artifact_type in SCORED_TYPES}
    latest = {}
    for a in sorted(artifacts, key=lambda a: (a.round, a.timestamp)):
        if a.artifact_type in SCORED_TYPES and a.artifact_id not in superseded:
            latest[a.producer_agent] = a
    return latest


def challenged_channels(artifacts):
    return {c["channel"] for a in artifacts if a.artifact_type == "challenge" for c in a.challenges}


def score(artifacts, return_breakdown=False):
    latest = latest_verdicts(artifacts)
    discounted = challenged_channels(artifacts)
    total, parts = 0.0, {}
    for channel, weight in sorted(config.CHANNEL_WEIGHTS.items()):
        a = latest.get(channel)
        if a is None:
            parts[channel] = 0.0
            continue
        discount = config.SKEPTIC_DISCOUNT if channel in discounted else 1.0
        parts[channel] = weight * config.STANCE_VALUE[a.stance] * a.strength * discount
        total += parts[channel]
    return (total, parts) if return_breakdown else total

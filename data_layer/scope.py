"""Trait-scope matching shared by every builder, so scope is defined exactly once."""
import re
import config


def _match(term, text):
    if len(term) <= config.SHORT_TERM_MAX_LEN:
        return re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE) is not None
    return term.lower() in text.lower()


def scope_group(trait_name):
    """Return the scope group ('lipids', ...) a trait belongs to, or None if out of scope."""
    for group in sorted(config.TRAIT_SCOPE):
        if any(_match(t, trait_name or "") for t in config.TRAIT_SCOPE[group]):
            return group
    return None


def is_hard_endpoint(trait_name):
    name = (trait_name or "").lower()
    return "measurement" not in name and any(t in name for t in config.HARD_ENDPOINT_TERMS)

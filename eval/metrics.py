"""Metrics, bootstrap CIs, permutation null and the paired delta (the headline number)."""
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
import config


def auroc(y, s):
    return float(roc_auc_score(y, s))


def auprc(y, s):
    return float(average_precision_score(y, s))


def precision_at_k(y, s, k=config.PRECISION_AT_K):
    y, s = np.asarray(y), np.asarray(s)
    order = np.lexsort((np.arange(len(s)), -s))  # ties broken by panel order, deterministically
    return float(y[order[:k]].mean())


def _resamples(y, n, seed):
    """Yield bootstrap index arrays that contain both classes."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    done = 0
    while done < n:
        idx = rng.integers(0, len(y), len(y))
        if 0 < y[idx].sum() < len(idx):
            done += 1
            yield idx


def bootstrap_ci(metric, y, s, n=config.N_BOOTSTRAP, seed=config.SEED):
    y, s = np.asarray(y), np.asarray(s)
    vals = [metric(y[i], s[i]) for i in _resamples(y, n, seed)]
    return metric(y, s), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def paired_delta(metric, y, s_a, s_b, n=config.N_BOOTSTRAP, seed=config.SEED):
    """metric(a) - metric(b), with both arms scored on the SAME resample each time."""
    y, a, b = np.asarray(y), np.asarray(s_a), np.asarray(s_b)
    vals = [metric(y[i], a[i]) - metric(y[i], b[i]) for i in _resamples(y, n, seed)]
    point = metric(y, a) - metric(y, b)
    return point, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def permutation_null(metric, y, s, n=config.N_PERMUTATIONS, seed=config.SEED):
    """One-sided empirical p: share of label shuffles scoring >= the observed metric."""
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s)
    obs = metric(y, s)
    hits = sum(metric(rng.permutation(y), s) >= obs for _ in range(n))
    return obs, (hits + 1) / (n + 1)

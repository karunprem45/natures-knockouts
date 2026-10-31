import numpy as np
from eval import metrics as m

Y = np.array([1, 1, 1, 0, 0, 0, 0, 0])
PERFECT = np.array([8, 7, 6, 5, 4, 3, 2, 1.0])


def test_perfect_ranking():
    assert m.auroc(Y, PERFECT) == 1.0
    assert m.auprc(Y, PERFECT) == 1.0
    assert m.precision_at_k(Y, PERFECT, k=3) == 1.0


def test_bootstrap_is_deterministic_and_brackets_point():
    s = np.array([5, 3, 6, 4, 2, 7, 1, 0.0])
    a = m.bootstrap_ci(m.auroc, Y, s, n=200)
    assert a == m.bootstrap_ci(m.auroc, Y, s, n=200)
    assert a[1] <= a[0] <= a[2]


def test_paired_delta_of_identical_arms_is_zero():
    assert m.paired_delta(m.auroc, Y, PERFECT, PERFECT, n=100) == (0.0, 0.0, 0.0)


def test_permutation_null_small_p_for_perfect():
    _, p = m.permutation_null(m.auroc, Y, PERFECT, n=500)
    assert p < 0.05


def test_seed_paired_delta_matches_single_seed_case():
    s = np.array([5, 3, 6, 4, 2, 7, 1, 0.0])
    assert m.paired_delta_seeds(m.auroc, Y, [PERFECT], [s], n=100) == m.paired_delta(m.auroc, Y, PERFECT, s, n=100)

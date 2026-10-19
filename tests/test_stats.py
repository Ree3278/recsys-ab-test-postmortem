import numpy as np
from scipy import stats

from ab_rec_eval import stats as S


def test_srm_balanced_ok_and_skewed_alerts():
    assert not S.srm_test(50_100, 49_900).alert
    assert S.srm_test(50_000, 48_500).alert


def test_welch_matches_scipy():
    rng = np.random.default_rng(0)
    a, b = rng.normal(10, 3, 500), rng.normal(10.5, 5, 700)
    r = S.welch_test(a, b)
    assert np.isclose(r.p_value, stats.ttest_ind(b, a, equal_var=False).pvalue)
    assert r.ci_diff[0] < r.diff < r.ci_diff[1]


def test_cuped_variance_reduction_matches_rho_squared():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 200_000)
    y = 0.7 * x + rng.normal(0, 1, 200_000)
    rho2 = np.corrcoef(x, y)[0, 1] ** 2
    _, _, vr = S.cuped_adjust(y, x)
    assert abs(vr - rho2) < 0.01


def test_power_roundtrip():
    n = S.n_per_arm(mde_abs=1.0, sd=10)
    assert S.mde_abs(n, sd=10) <= 1.0 + 1e-6


def test_gini_extremes():
    assert S.gini(np.ones(1000)) < 1e-9
    assert S.gini(np.r_[np.zeros(999), 1.0]) > 0.99


def test_bh_adjusted_not_smaller():
    p = np.array([0.001, 0.02, 0.04, 0.5])
    assert (S.adjust_pvalues(p) >= p).all()

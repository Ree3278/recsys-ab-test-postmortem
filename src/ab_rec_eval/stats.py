"""Core experiment statistics. Pure functions, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests


@dataclass(frozen=True)
class SRMResult:
    n_control: int
    n_treatment: int
    chi2: float
    p_value: float
    alert: bool


def srm_test(n_control: int, n_treatment: int, p_treat: float = 0.5,
             alpha: float = 0.001) -> SRMResult:
    """Chi-square goodness-of-fit against the intended split.
    alpha=0.001 is the common SRM alert threshold."""
    total = n_control + n_treatment
    exp = np.array([total * (1 - p_treat), total * p_treat])
    chi2, p = stats.chisquare([n_control, n_treatment], exp)
    return SRMResult(n_control, n_treatment, float(chi2), float(p), bool(p < alpha))


@dataclass(frozen=True)
class EffectResult:
    mean_control: float
    mean_treatment: float
    diff: float
    ci_diff: tuple[float, float]
    rel_lift: float
    ci_rel_lift: tuple[float, float]
    p_value: float


def welch_test(y_control, y_treatment, alpha: float = 0.05) -> EffectResult:
    """Two-sided Welch t-test; abs diff CI via Welch df, relative-lift CI via delta method."""
    c, t = np.asarray(y_control, float), np.asarray(y_treatment, float)
    mc, mt = c.mean(), t.mean()
    vc, vt = c.var(ddof=1) / len(c), t.var(ddof=1) / len(t)
    se = np.sqrt(vc + vt)
    df = (vc + vt) ** 2 / (vc**2 / (len(c) - 1) + vt**2 / (len(t) - 1))
    tcrit = stats.t.ppf(1 - alpha / 2, df)
    diff = mt - mc
    p = 2 * stats.t.sf(abs(diff / se), df)
    # delta method for ratio mt/mc (independent samples)
    ratio = mt / mc
    se_ratio = np.sqrt(vt / mc**2 + (mt**2) * vc / mc**4)
    return EffectResult(
        mc, mt, diff, (diff - tcrit * se, diff + tcrit * se),
        ratio - 1, (ratio - 1 - tcrit * se_ratio, ratio - 1 + tcrit * se_ratio), float(p))


def cuped_adjust(y, x, arm=None):
    """CUPED: y_adj = y - theta * (x - mean(x)), theta = cov(x, y) / var(x).
    theta is estimated on pooled data. Returns (y_adj, theta, variance_reduction)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    if x.var(ddof=1) == 0:  # covariate carries no information (e.g. new users)
        return y.copy(), 0.0, 0.0
    theta = np.cov(x, y, ddof=1)[0, 1] / x.var(ddof=1)
    y_adj = y - theta * (x - x.mean())
    return y_adj, float(theta), float(1 - y_adj.var(ddof=1) / y.var(ddof=1))


def n_per_arm(mde_abs: float, sd: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Sample size per arm for a two-sided two-sample test of means."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return int(np.ceil(2 * (z * sd / mde_abs) ** 2))


def mde_abs(n: int, sd: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable absolute effect given n per arm."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return float(z * sd * np.sqrt(2 / n))


def lorenz(values):
    """Lorenz curve points (x = cumulative share of items, y = cumulative share of total)."""
    v = np.sort(np.asarray(values, float))
    cum = np.cumsum(v) / v.sum()
    return np.r_[0, np.arange(1, len(v) + 1) / len(v)], np.r_[0, cum]


def gini(values) -> float:
    x, y = lorenz(values)
    return float(1 - 2 * np.trapezoid(y, x))


def adjust_pvalues(pvals, method: str = "fdr_bh"):
    """Multiple-comparison correction. method: 'fdr_bh' (Benjamini-Hochberg) or 'bonferroni'."""
    return multipletests(pvals, method=method)[1]

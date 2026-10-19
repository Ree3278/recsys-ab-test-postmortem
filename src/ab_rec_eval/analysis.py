"""Turn raw simulated tables into the numbers behind the 4 charts.

All results are for SIMULATED data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import stats as S
from .simulate import SimConfig, generate

N_DAYS = 14


def user_level(users: pd.DataFrame, daily: pd.DataFrame, day_from: int = 1,
               day_to: int = N_DAYS) -> pd.DataFrame:
    """One row per user with y = GMV summed over [day_from, day_to]."""
    d = daily[(daily.day >= day_from) & (daily.day <= day_to)]
    y = d.groupby("user_id").gmv.sum().rename("y")
    return users.join(y, on="user_id").fillna({"y": 0.0})


def estimate(df: pd.DataFrame, cuped: bool = True, alpha: float = 0.05) -> dict:
    """Welch estimate of the treatment effect on y, optionally CUPED-adjusted."""
    y = df.y.to_numpy()
    vr = 0.0
    if cuped:
        y, _, vr = S.cuped_adjust(y, df.pre_gmv.to_numpy())
    arm = df.arm.to_numpy()
    r = S.welch_test(y[arm == 0], y[arm == 1], alpha)
    return {
        "n_control": int((arm == 0).sum()), "n_treatment": int((arm == 1).sum()),
        "mean_control": float(r.mean_control), "mean_treatment": float(r.mean_treatment),
        "diff": float(r.diff), "ci_diff": [float(v) for v in r.ci_diff],
        "rel_lift": float(r.rel_lift), "ci_rel_lift": [float(v) for v in r.ci_rel_lift],
        "p_value": float(r.p_value), "variance_reduction": float(vr),
    }


def srm_report(users: pd.DataFrame, p_treat: float = 0.5) -> dict:
    n0, n1 = int((users.arm == 0).sum()), int((users.arm == 1).sum())
    overall = S.srm_test(n0, n1, p_treat)
    by_device = []
    for dev, g in users.groupby("device"):
        r = S.srm_test(int((g.arm == 0).sum()), int((g.arm == 1).sum()), p_treat)
        by_device.append({"device": dev, "n_control": r.n_control, "n_treatment": r.n_treatment,
                          "chi2": r.chi2, "p_value": r.p_value, "alert": r.alert})
    return {"overall": {"n_control": n0, "n_treatment": n1, "chi2": overall.chi2,
                        "p_value": overall.p_value, "alert": overall.alert},
            "by_device": by_device}


def cumulative(users, daily, cuped=True) -> list[dict]:
    """Lift using days 1..k for k=1..14. Diagnostic only: repeated looks inflate false positives."""
    return [{"day": k, **estimate(user_level(users, daily, 1, k), cuped)}
            for k in range(1, N_DAYS + 1)]


def daily_lift(users, daily, cuped=True) -> list[dict]:
    """Lift on each single day: shows novelty decay without cumulative smoothing."""
    return [{"day": k, **estimate(user_level(users, daily, k, k), cuped)}
            for k in range(1, N_DAYS + 1)]


def subgroups(df: pd.DataFrame, dims=("user_type", "segment", "device"), cuped=True) -> list[dict]:
    rows = []
    for dim in dims:
        for level, g in df.groupby(dim):
            rows.append({"dimension": dim, "level": level, **estimate(g, cuped)})
    p = np.array([r["p_value"] for r in rows])
    p_bh = S.adjust_pvalues(p, "fdr_bh")
    for r, a in zip(rows, p_bh):
        r["p_adj_bh"] = float(a)
        r["significant_bh"] = bool(a < 0.05)
    return rows


def long_tail(skus: pd.DataFrame, points: int = 101) -> dict:
    out = {}
    for arm, name in ((0, "control"), (1, "treatment")):
        imp = skus[skus.arm == arm].sort_values("sku_id").impressions.to_numpy()
        x, y = S.lorenz(imp)
        idx = np.linspace(0, len(x) - 1, points).astype(int)
        top = np.sort(imp)[::-1]
        out[name] = {"gini": S.gini(imp), "lorenz_x": x[idx].tolist(), "lorenz_y": y[idx].tolist(),
                     "top1pct_share": float(top[: max(1, len(top) // 100)].sum() / top.sum()),
                     "zero_impression_skus": int((imp == 0).sum())}
    out["gini_delta"] = out["treatment"]["gini"] - out["control"]["gini"]
    return out


def sizing(df: pd.DataFrame, cuped_vr: float) -> dict:
    """Pre-experiment planning numbers from baseline (control) variance, not post-hoc power."""
    base = df[df.arm == 0].y
    mean, sd = float(base.mean()), float(base.std(ddof=1))
    sd_c = sd * np.sqrt(1 - cuped_vr)
    table = []
    for rel in (0.01, 0.02, 0.03, 0.05, 0.10):
        table.append({"mde_rel": rel,
                      "n_per_arm_raw": S.n_per_arm(rel * mean, sd),
                      "n_per_arm_cuped": S.n_per_arm(rel * mean, sd_c)})
    return {"baseline_mean": mean, "baseline_sd": sd, "cuped_variance_reduction": cuped_vr,
            "alpha": 0.05, "power": 0.8, "table": table}


def run_all(raw_dir="data/raw", out_path="reports/results.json",
            cfg: SimConfig | None = None) -> dict:
    cfg = cfg or SimConfig()
    raw = Path(raw_dir)
    users = pd.read_parquet(raw / "users.parquet")
    daily = pd.read_parquet(raw / "daily.parquet")
    skus = pd.read_parquet(raw / "skus.parquet")
    df = user_level(users, daily)

    overall_cuped = estimate(df, cuped=True)
    # SRM scenario: same experiment but with a logging loss on one device in treatment
    bad = generate(SimConfig(**{**cfg.__dict__, "srm_drop_frac": 0.08}))["users"]

    res = {
        "meta": {"simulated": True, "n_users": len(users), "n_days": N_DAYS,
                 "seed": cfg.seed, "planted_long_run_lift": cfg.long_run_lift,
                 "planted_novelty_peak": cfg.novelty_peak,
                 "planted_novelty_tau_days": cfg.novelty_tau_days},
        "srm": {"clean": srm_report(users), "injected": srm_report(bad),
                "injected_note": f"{cfg.srm_drop_device} treatment users dropped (8%)"},
        "overall": {"raw": estimate(df, cuped=False), "cuped": overall_cuped},
        "cumulative": cumulative(users, daily),
        "daily": daily_lift(users, daily),
        "windows": {
            "early_d1_3": estimate(user_level(users, daily, 1, 3)),
            "late_d8_14": estimate(user_level(users, daily, 8, 14)),
        },
        "subgroups": subgroups(df),
        "long_tail": long_tail(skus),
        "sizing": sizing(df, overall_cuped["variance_reduction"]),
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    r = run_all()
    o = r["overall"]
    print(f"overall lift raw {o['raw']['rel_lift']:+.3f} | cuped {o['cuped']['rel_lift']:+.3f}"
          f" (var reduction {o['cuped']['variance_reduction']:.1%})")

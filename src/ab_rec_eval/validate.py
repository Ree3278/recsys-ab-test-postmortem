"""Pipeline validation by repeated simulation (all synthetic).

1. A/A: with no planted effect, false-positive rate should be ~5% (and SRM alerts ~0.1%).
2. Coverage: 95% CIs should cover the *known* planted 14-day relative lift ~95% of the time.
   The planted lift is exact because treatment multiplies purchase probability by (1+lift_d).
3. Precision: CUPED CI width relative to raw CI width.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

from . import analysis as A
from . import stats as S
from .simulate import SimConfig, generate


def true_lift(cfg: SimConfig, segment: str | None = None) -> float:
    days = np.arange(1, cfg.n_days + 1)
    nov = cfg.novelty_peak * np.exp(-(days - 1) / cfg.novelty_tau_days)
    if segment is not None:
        return float(np.mean(cfg.long_run_lift[segment] + nov))
    # overall: ratio of expected GMV, weighted by segment contribution to control GMV
    w = np.array([cfg.segment_share[s] * cfg.segment_scale[s] for s in cfg.segment_share])
    lifts = np.array([np.mean(cfg.long_run_lift[s] + nov) for s in cfg.segment_share])
    return float((w * lifts).sum() / w.sum())


def run(n_reps: int = 100, n_users: int = 30_000, seed0: int = 1000) -> dict:
    base = SimConfig(n_users=n_users, n_skus=200, n_impressions=50_000)
    aa = replace(base, long_run_lift={k: 0.0 for k in base.long_run_lift}, novelty_peak=0.0)
    out = {"n_reps": n_reps, "n_users": n_users}

    fp_raw = fp_cup = srm_alerts = 0
    for i in range(n_reps):
        d = generate(replace(aa, seed=seed0 + i))
        df = A.user_level(d["users"], d["daily"])
        fp_raw += A.estimate(df, cuped=False)["p_value"] < 0.05
        fp_cup += A.estimate(df, cuped=True)["p_value"] < 0.05
        srm_alerts += S.srm_test((d["users"].arm == 0).sum(), (d["users"].arm == 1).sum()).alert
    out["aa"] = {"fpr_raw": fp_raw / n_reps, "fpr_cuped": fp_cup / n_reps,
                 "srm_alert_rate": srm_alerts / n_reps}

    targets = {"overall": None, "ret_high": "ret_high", "new": "new"}
    cover = {k: {"raw": 0, "cuped": 0} for k in targets}
    width = {k: [] for k in targets}
    for i in range(n_reps):
        d = generate(replace(base, seed=seed0 + 10_000 + i))
        df = A.user_level(d["users"], d["daily"])
        for name, seg in targets.items():
            sub = df if seg is None else df[df.segment == seg]
            t = true_lift(base, seg)
            r, c = A.estimate(sub, cuped=False), A.estimate(sub, cuped=True)
            cover[name]["raw"] += r["ci_rel_lift"][0] <= t <= r["ci_rel_lift"][1]
            cover[name]["cuped"] += c["ci_rel_lift"][0] <= t <= c["ci_rel_lift"][1]
            width[name].append((c["ci_rel_lift"][1] - c["ci_rel_lift"][0]) /
                               (r["ci_rel_lift"][1] - r["ci_rel_lift"][0]))
    out["coverage"] = {k: {"true_lift": true_lift(base, targets[k]),
                           "raw": v["raw"] / n_reps, "cuped": v["cuped"] / n_reps,
                           "cuped_ci_width_ratio": float(np.mean(width[k]))}
                       for k, v in cover.items()}
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    res = run(n)
    Path("reports").mkdir(exist_ok=True)
    Path("reports/validation.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))

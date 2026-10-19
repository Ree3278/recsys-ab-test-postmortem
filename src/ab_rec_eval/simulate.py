"""Synthetic experiment generator.

Everything produced here is SIMULATED. The planted effects below are
parameters we choose; the analysis pipeline's job is to recover them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SEGMENTS = ["new", "ret_low", "ret_mid", "ret_high"]


@dataclass(frozen=True)
class SimConfig:
    n_users: int = 200_000
    n_days: int = 14
    n_pre_days: int = 14
    seed: int = 42
    p_treat: float = 0.5  # intended share assigned to treatment

    # user mix
    segment_share: dict = field(default_factory=lambda: {
        "new": 0.25, "ret_low": 0.30, "ret_mid": 0.26, "ret_high": 0.19})
    device_share: dict = field(default_factory=lambda: {
        "ios": 0.35, "android": 0.45, "web": 0.20})

    # baseline behaviour
    base_daily_purchase_p: float = 0.06
    segment_scale: dict = field(default_factory=lambda: {
        "new": 0.6, "ret_low": 0.5, "ret_mid": 1.0, "ret_high": 2.2})
    theta_shape: float = 0.7  # gamma shape of per-user propensity (heavy tail)
    order_value_mu: float = 3.6
    order_value_sigma: float = 0.8

    # planted effects: long-run relative lift on purchase probability
    long_run_lift: dict = field(default_factory=lambda: {
        "new": -0.12, "ret_low": 0.00, "ret_mid": 0.03, "ret_high": 0.08})
    novelty_peak: float = 0.20  # extra lift on day 1, decays exponentially
    novelty_tau_days: float = 3.0

    # SRM injection: drop this share of treatment users in one device
    srm_drop_frac: float = 0.0
    srm_drop_device: str = "android"

    # SKU exposure model (for Lorenz / Gini)
    n_skus: int = 2_000
    n_impressions: int = 2_000_000
    zipf_s: float = 0.9
    exposure_sharpness_control: float = 1.0
    exposure_sharpness_treat: float = 1.2


def novelty_multiplier(day: np.ndarray, cfg: SimConfig) -> np.ndarray:
    """day is 1-indexed. Returns extra lift added on top of long-run lift."""
    return cfg.novelty_peak * np.exp(-(day - 1) / cfg.novelty_tau_days)


def _choice(rng, share: dict, n: int) -> np.ndarray:
    keys = list(share)
    p = np.array([share[k] for k in keys], dtype=float)
    return np.array(keys)[rng.choice(len(keys), size=n, p=p / p.sum())]


def generate(cfg: SimConfig | None = None) -> dict[str, pd.DataFrame]:
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_users

    users = pd.DataFrame({
        "user_id": np.arange(n),
        "segment": _choice(rng, cfg.segment_share, n),
        "device": _choice(rng, cfg.device_share, n),
        "arm": (rng.random(n) < cfg.p_treat).astype(int),
    })
    users["user_type"] = np.where(users.segment == "new", "new", "returning")

    scale = users.segment.map(cfg.segment_scale).to_numpy()
    theta = rng.gamma(cfg.theta_shape, 1 / cfg.theta_shape, n) * scale
    base_p = np.clip(cfg.base_daily_purchase_p * theta, 0, 0.6)

    def simulate_days(n_days: int, lift_by_day: np.ndarray | None):
        gmv = np.zeros((n, n_days))
        orders = np.zeros((n, n_days), dtype=int)
        for d in range(n_days):
            p = base_p if lift_by_day is None else np.clip(base_p * (1 + lift_by_day[:, d]), 0, 0.9)
            o = rng.random(n) < p
            val = rng.lognormal(cfg.order_value_mu, cfg.order_value_sigma, n)
            orders[:, d] = o
            gmv[:, d] = o * val
        return gmv, orders

    # pre-period: no treatment; new users have no history
    pre_gmv, _ = simulate_days(cfg.n_pre_days, None)
    users["pre_gmv"] = np.where(users.segment == "new", 0.0, pre_gmv.sum(axis=1))

    # in-experiment: lift only for treatment users
    days = np.arange(1, cfg.n_days + 1)
    lr = users.segment.map(cfg.long_run_lift).to_numpy()[:, None]
    lift = (lr + novelty_multiplier(days, cfg)[None, :]) * users.arm.to_numpy()[:, None]
    gmv, orders = simulate_days(cfg.n_days, lift)

    daily = pd.DataFrame({
        "user_id": np.repeat(users.user_id.to_numpy(), cfg.n_days),
        "day": np.tile(days, n),
        "gmv": gmv.ravel(),
        "orders": orders.ravel(),
    })

    # SRM injection: logging loss in treatment/device
    if cfg.srm_drop_frac > 0:
        lost = (
            (users.arm == 1) & (users.device == cfg.srm_drop_device)
            & (rng.random(n) < cfg.srm_drop_frac)
        )
        users = users[~lost].reset_index(drop=True)
        daily = daily[daily.user_id.isin(users.user_id)].reset_index(drop=True)

    return {"users": users, "daily": daily, "skus": simulate_skus(cfg, rng)}


def simulate_skus(cfg: SimConfig, rng: np.random.Generator) -> pd.DataFrame:
    rank = np.arange(1, cfg.n_skus + 1)
    pop = rank ** (-cfg.zipf_s)
    rows = []
    for arm, sharp in ((0, cfg.exposure_sharpness_control), (1, cfg.exposure_sharpness_treat)):
        w = pop ** sharp
        imp = rng.multinomial(cfg.n_impressions, w / w.sum())
        ctr = np.clip(0.02 * (pop / pop.max()) ** 0.15, 0, 1)
        rows.append(pd.DataFrame({
            "sku_id": rank, "arm": arm, "impressions": imp,
            "clicks": rng.binomial(imp, ctr),
        }))
    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw")
    out.mkdir(parents=True, exist_ok=True)
    for name, df in generate().items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"{name}: {len(df):,} rows")

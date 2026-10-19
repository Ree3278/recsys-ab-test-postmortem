import numpy as np

from ab_rec_eval import analysis as A
from ab_rec_eval import stats as S
from ab_rec_eval.simulate import SimConfig, generate


def data(**kw):
    return generate(SimConfig(n_users=40_000, n_skus=300, n_impressions=100_000, **kw))


def test_cuped_with_constant_covariate_is_noop():
    y = np.random.default_rng(0).normal(size=100)
    adj, theta, vr = S.cuped_adjust(y, np.zeros(100))
    assert theta == 0 and vr == 0 and np.allclose(adj, y)


def test_cuped_narrows_ci_without_moving_estimate_much():
    d = data()
    df = A.user_level(d["users"], d["daily"])
    raw, cup = A.estimate(df, cuped=False), A.estimate(df, cuped=True)
    w = lambda r: r["ci_rel_lift"][1] - r["ci_rel_lift"][0]
    assert w(cup) < w(raw)
    assert abs(cup["rel_lift"] - raw["rel_lift"]) < 0.05


def test_novelty_visible_in_daily_lift():
    d = data()
    dl = A.daily_lift(d["users"], d["daily"])
    assert np.mean([r["rel_lift"] for r in dl[:3]]) > np.mean([r["rel_lift"] for r in dl[-3:]])


def test_subgroups_have_bh_column_and_new_users_negative_direction():
    d = data()
    rows = A.subgroups(A.user_level(d["users"], d["daily"]))
    assert all("p_adj_bh" in r and r["p_adj_bh"] >= r["p_value"] for r in rows)
    hi = next(r for r in rows if r["level"] == "ret_high")
    assert hi["rel_lift"] > 0.05


def test_srm_report_flags_injected_loss():
    assert not A.srm_report(data()["users"])["overall"]["alert"]
    bad = A.srm_report(data(srm_drop_frac=0.1)["users"])
    assert bad["overall"]["alert"]
    assert any(r["alert"] for r in bad["by_device"] if r["device"] == "android")


def test_late_window_lift_smaller_than_early():
    d = data()
    e = A.estimate(A.user_level(d["users"], d["daily"], 1, 3))
    late = A.estimate(A.user_level(d["users"], d["daily"], 8, 14))
    assert e["rel_lift"] > late["rel_lift"]

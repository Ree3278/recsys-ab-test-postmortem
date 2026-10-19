
from ab_rec_eval import stats as S
from ab_rec_eval.simulate import SimConfig, generate


def small(**kw):
    return generate(SimConfig(n_users=40_000, n_skus=500, n_impressions=300_000, **kw))


def test_reproducible():
    a, b = small(), small()
    assert a["users"].equals(b["users"])


def test_no_srm_by_default_and_srm_when_injected():
    u = small()["users"]
    assert not S.srm_test((u.arm == 0).sum(), (u.arm == 1).sum()).alert
    u2 = small(srm_drop_frac=0.2)["users"]
    assert S.srm_test((u2.arm == 0).sum(), (u2.arm == 1).sum()).alert


def test_new_users_have_no_pre_period():
    u = small()["users"]
    assert (u.loc[u.segment == "new", "pre_gmv"] == 0).all()


def test_treatment_concentrates_exposure():
    s = small()["skus"]
    g = {a: S.gini(d.impressions) for a, d in s.groupby("arm")}
    assert g[1] > g[0]

from ab_rec_eval import analysis as A
from ab_rec_eval import charts
from ab_rec_eval.simulate import SimConfig, generate


def test_build_all_charts(tmp_path):
    cfg = SimConfig(n_users=30_000, n_skus=300, n_impressions=100_000)
    raw = tmp_path / "raw"
    raw.mkdir()
    for name, df in generate(cfg).items():
        df.to_parquet(raw / f"{name}.parquet")
    A.run_all(raw, tmp_path / "results.json", cfg)
    paths = charts.build(tmp_path / "results.json", tmp_path / "site")
    assert len(paths) == 4
    for p in paths:
        text = p.read_text()
        assert "SIMULATED DATA" in text and "Plotly.newPlot" in text and "<table>" in text
    assert (tmp_path / "site/assets/plotly.min.js").stat().st_size > 1_000_000


def test_index_build(tmp_path):
    from ab_rec_eval import site
    cfg = SimConfig(n_users=30_000, n_skus=300, n_impressions=100_000)
    raw = tmp_path / "raw"
    raw.mkdir()
    for name, df in generate(cfg).items():
        df.to_parquet(raw / f"{name}.parquet")
    A.run_all(raw, tmp_path / "results.json", cfg)
    paths = site.build(tmp_path / "results.json", tmp_path / "none.json", tmp_path / "site")
    idx = (tmp_path / "site/index.html").read_text()
    assert paths[-1].name == "index.html" and "%%" not in idx and "All data on this page is synthetic" in idx
    assert (tmp_path / "site/.nojekyll").exists()

"""Build the full static site: 4 chart pages + narrative index.html (all SIMULATED data)."""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from . import charts

REPO_URL = "https://github.com/Ree3278/recsys-ab-test-postmortem"  # set to your GitHub repo URL to show a source link

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recommender A/B Test Post-mortem (Simulated)</title>
<meta name="description" content="Simulated A/B test of a recommendation engine: novelty effect, heterogeneity, long-tail concentration and SRM diagnostics.">
<style>
  :root { color-scheme: light; --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --rule:#e1e0d9; --accent:#2a78d6; }
  @media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) {
    color-scheme: dark; --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --rule:#2c2c2a; --accent:#3987e5; } }
  :root[data-theme="dark"] { color-scheme: dark; --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --rule:#2c2c2a; --accent:#3987e5; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--page); color:var(--ink); font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif; }
  main { max-width: 980px; margin: 0 auto; padding: 0 16px 64px; }
  header.top { display:flex; justify-content:space-between; align-items:center; padding:16px 0; font-size:13px; color:var(--ink2); }
  button { font:inherit; font-size:13px; color:var(--ink2); background:var(--surface); border:1px solid var(--rule); border-radius:999px; padding:4px 12px; cursor:pointer; }
  button:focus-visible, a:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
  h1 { font-size: clamp(26px, 5vw, 38px); line-height:1.15; margin: 24px 0 12px; font-weight:650; letter-spacing:-.01em; max-width: 22ch; }
  h2 { font-size: 22px; margin: 56px 0 4px; font-weight:600; }
  h2 .n { color: var(--muted); font-weight:500; margin-right:8px; }
  p { max-width: 68ch; margin: 8px 0; }
  .lead { font-size: 18px; color: var(--ink2); max-width: 60ch; }
  .banner { border:1px solid var(--rule); background:var(--surface); border-radius:10px; padding:12px 16px; margin:20px 0; font-size:14px; color:var(--ink2); }
  .banner b { color: var(--ink); }
  .tiles { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin: 24px 0; }
  .tile { background:var(--surface); border:1px solid var(--rule); border-radius:12px; padding:16px; }
  .tile .k { font-size:13px; color:var(--ink2); }
  .tile .v { font-size: 30px; font-weight:600; line-height:1.2; margin:4px 0; }
  .tile .d { font-size:13px; color:var(--muted); }
  iframe { width:100%; border:0; height:600px; display:block; margin-top:12px; background:transparent; color-scheme: normal; }
  .why { color:var(--ink2); }
  table { border-collapse: collapse; width:100%; font-size:14px; margin:12px 0; font-variant-numeric: tabular-nums; }
  th, td { text-align:right; padding:6px 10px; border-bottom:1px solid var(--rule); }
  th:first-child, td:first-child { text-align:left; }
  .tw { overflow-x:auto; }
  ul { max-width: 68ch; padding-left: 20px; }
  li { margin: 6px 0; }
  a { color: var(--accent); }
  footer { margin-top: 56px; padding-top: 16px; border-top:1px solid var(--rule); color:var(--muted); font-size:13px; }
</style></head>
<body><main>
<header class="top"><span>Recommender A/B test · simulated</span><button id="theme" type="button" aria-label="Change color theme">Theme: auto</button></header>

<h1>Did the new recommender really win?</h1>
<p class="lead">%%LEAD%%</p>
<div class="banner"><b>All data on this page is synthetic.</b> Effect sizes (novelty decay, subgroup lifts, exposure concentration) are parameters I set in a simulator.
The point is the analysis pipeline: it should recover the planted effects and raise the planted warnings. No claim is made about any real product.</div>

<div class="tiles">
  <div class="tile"><div class="k">Headline: 14-day GMV per user</div><div class="v">%%HEAD%%</div><div class="d">95% CI %%HEADCI%%, CUPED-adjusted</div></div>
  <div class="tile"><div class="k">Days 8–14 only</div><div class="v">%%LATE%%</div><div class="d">95% CI %%LATECI%%; days 1–3 were %%EARLY%%</div></div>
  <div class="tile"><div class="k">Impression Gini</div><div class="v">%%G0%% → %%G1%%</div><div class="d">Top 1% of SKUs: %%T0%% → %%T1%% of impressions</div></div>
</div>

<h2><span class="n">1</span>Is the lift real, or novelty?</h2>
<p class="why">%%S1%%</p>
<iframe src="charts/novelty.html" title="Novelty effect chart" loading="lazy"></iframe>

<h2><span class="n">2</span>Who is helped and who is hurt?</h2>
<p class="why">%%S2%%</p>
<iframe src="charts/heterogeneity.html" title="Heterogeneity forest plot" loading="lazy"></iframe>

<h2><span class="n">3</span>What happens to the long tail?</h2>
<p class="why">%%S3%%</p>
<iframe src="charts/long_tail.html" title="Lorenz curve chart" loading="lazy"></iframe>

<h2><span class="n">4</span>Can the experiment be trusted at all?</h2>
<p class="why">%%S4%%</p>
<iframe src="charts/srm.html" title="Sample ratio mismatch chart" loading="lazy"></iframe>

<h2>Method</h2>
<ul>
  <li><b>Estimand.</b> Relative lift in 14-day GMV per user, treatment vs control, on the pre-registered 14-day window. Daily and cumulative views are diagnostics only: repeated looks inflate false positives.</li>
  <li><b>Test.</b> Two-sided Welch t-test; relative-lift CI by the delta method.</li>
  <li><b>CUPED.</b> Pre-period GMV as covariate; variance reduced by %%VR%% overall. New users have no history, so it does nothing for them.</li>
  <li><b>SRM.</b> Chi-square goodness of fit to the intended 50/50 split, alert at p &lt; 0.001, then sliced by device.</li>
  <li><b>Subgroups.</b> Exploratory; Benjamini–Hochberg adjusted across %%NSUB%% tests.</li>
  <li><b>Power.</b> Planned before the experiment from baseline variance (below), not computed after the fact.</li>
</ul>
<p>Sample size per arm to detect a relative GMV lift (80% power, α = 0.05, baseline mean %%BM%%, SD %%BSD%%):</p>
<div class="tw">%%SIZING%%</div>

<h2>Does the pipeline work?</h2>
%%VALID%%

<h2>Limitations</h2>
<ul>
  <li>Simulated users are independent; there is no interference between users, which real marketplaces violate (the cannibalization concern from the brief).</li>
  <li>The recommender is not built: a click model stands in for it, so no claim is made about LLM or vector retrieval quality.</li>
  <li>Planted effects are my assumptions. Recovering them shows the method works, not that real recommenders behave this way.</li>
  <li>The SRM scenario is localized by device only; no funnel-stage decomposition.</li>
</ul>

<footer>Python · pandas · SciPy · statsmodels · Plotly. %%REPO%%Built with uv.</footer>
</main>
<script>
(function () {
  var modes = ["auto", "light", "dark"], i = 0, btn = document.getElementById("theme");
  var frames = Array.prototype.slice.call(document.querySelectorAll("iframe"));
  try { var s = localStorage.getItem("ab-theme"); if (s && modes.indexOf(s) >= 0) i = modes.indexOf(s); } catch (e) {}
  function push() {
    var m = modes[i];
    if (m === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", m);
    btn.textContent = "Theme: " + m;
    frames.forEach(function (f) { try { f.contentWindow.postMessage({abTheme: m}, "*"); } catch (e) {} });
  }
  btn.addEventListener("click", function () {
    i = (i + 1) % 3;
    try { localStorage.setItem("ab-theme", modes[i]); } catch (e) {}
    push();
  });
  frames.forEach(function (f) { f.addEventListener("load", push); });
  window.addEventListener("message", function (e) {
    if (!e.data || !e.data.abHeight) return;
    frames.forEach(function (f) { if (f.contentWindow === e.source) f.style.height = (e.data.abHeight + 4) + "px"; });
  });
  push();
})();
</script>
</body></html>
"""


def _p(x): return f"{x * 100:+.1f}%"
def _ci(c): return f"[{c[0] * 100:+.1f}%, {c[1] * 100:+.1f}%]"


def build_index(res: dict, val: dict | None, out_dir: Path) -> Path:
    ov, win = res["overall"]["cuped"], res["windows"]
    lt, sg = res["long_tail"], {(r["dimension"], r["level"]): r for r in res["subgroups"]}
    new, hi = sg[("user_type", "new")], sg[("segment", "ret_high")]
    inj = res["srm"]["injected"]
    bad = [d["device"] for d in inj["by_device"] if d["alert"]]

    sizing = res["sizing"]
    srows = "".join(
        f"<tr><td>{r['mde_rel']:.0%}</td><td>{r['n_per_arm_raw']:,}</td><td>{r['n_per_arm_cuped']:,}</td></tr>"
        for r in sizing["table"])
    sizing_html = ("<table><thead><tr><th>Target lift</th><th>Per arm, raw</th><th>Per arm, with CUPED</th></tr></thead>"
                   f"<tbody>{srows}</tbody></table>")

    if val:
        aa, cov = val["aa"], val["coverage"]
        crow = "".join(
            f"<tr><td>{k.replace('_', ' ')}</td><td>{v['true_lift'] * 100:+.1f}%</td><td>{v['raw']:.1%}</td>"
            f"<td>{v['cuped']:.1%}</td><td>{v['cuped_ci_width_ratio']:.2f}</td></tr>" for k, v in cov.items())
        valid = (f"<p>Repeated simulation ({val['n_reps']} runs of {val['n_users']:,} users). With no planted effect, the false-positive rate is "
                 f"{aa['fpr_raw']:.1%} (raw) and {aa['fpr_cuped']:.1%} (CUPED), and SRM alerts fire in {aa['srm_alert_rate']:.1%} of runs. "
                 "With planted effects, 95% intervals cover the known true lift about 95% of the time:</p>"
                 "<div class='tw'><table><thead><tr><th>Group</th><th>True lift</th><th>Coverage, raw</th>"
                 "<th>Coverage, CUPED</th><th>CUPED CI width vs raw</th></tr></thead>"
                 f"<tbody>{crow}</tbody></table></div>")
    else:
        valid = "<p>Run <code>uv run python -m ab_rec_eval.validate</code> to generate validation results.</p>"

    s1 = (f"The 14-day average is {_p(ov['rel_lift'])}, but the first three days run at {_p(win['early_d1_3']['rel_lift'])} while days 8–14 run at "
          f"{_p(win['late_d8_14']['rel_lift'])}. A user-level cumulative view keeps early days in the average, so it looks healthy long after the effect has faded.")
    s2 = (f"The overall number is an average of opposing effects: new users {_p(new['rel_lift'])} (BH-adjusted p = {new['p_adj_bh']:.2g}) "
          f"versus high-activity returning users {_p(hi['rel_lift'])}. Subgroup results are exploratory and corrected for multiple comparisons.")
    s3 = (f"Treatment concentrates impressions on already-popular items: Gini {lt['control']['gini']:.2f} → {lt['treatment']['gini']:.2f}. "
          "Short-term click metrics would not show this; a guardrail metric does.")
    s4 = (f"Before reading any result, check the split. Here an injected logging loss (p = {inj['overall']['p_value']:.1e}) is flagged and traced to "
          f"{', '.join(bad) if bad else 'no single device'}; the clean run passes (p = {res['srm']['clean']['overall']['p_value']:.2f}).")
    lead = ("A simulated A/B test of a new recommendation engine. The headline metric improves, but the story changes once you separate "
            "novelty from steady state, split by user group, and look at what happens to long-tail items.")

    page = INDEX
    for k, v in {
        "LEAD": lead, "HEAD": _p(ov["rel_lift"]), "HEADCI": _ci(ov["ci_rel_lift"]),
        "LATE": _p(win["late_d8_14"]["rel_lift"]), "LATECI": _ci(win["late_d8_14"]["ci_rel_lift"]),
        "EARLY": _p(win["early_d1_3"]["rel_lift"]),
        "G0": f"{lt['control']['gini']:.2f}", "G1": f"{lt['treatment']['gini']:.2f}",
        "T0": f"{lt['control']['top1pct_share']:.0%}", "T1": f"{lt['treatment']['top1pct_share']:.0%}",
        "S1": s1, "S2": s2, "S3": s3, "S4": s4,
        "VR": f"{ov['variance_reduction']:.0%}", "NSUB": str(len(res["subgroups"])),
        "BM": f"{sizing['baseline_mean']:.2f}", "BSD": f"{sizing['baseline_sd']:.2f}",
        "SIZING": sizing_html, "VALID": valid,
        "REPO": f'<a href="{html.escape(REPO_URL)}">Source on GitHub</a>. ' if REPO_URL else "",
    }.items():
        page = page.replace(f"%%{k}%%", v)
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("")
    return path


def build(results="reports/results.json", validation="reports/validation.json", out_dir="site") -> list[Path]:
    out = Path(out_dir)
    paths = charts.build(results, out)
    res = json.loads(Path(results).read_text())
    vp = Path(validation)
    paths.append(build_index(res, json.loads(vp.read_text()) if vp.exists() else None, out))
    return paths


if __name__ == "__main__":
    for p in build(*sys.argv[1:4]):
        print("wrote", p)

"""Build the 4 interactive charts as standalone pages (Plotly, light/dark aware).

Reads reports/results.json (SIMULATED data) and writes site/charts/*.html.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.subplots import make_subplots

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
GOOD, CRITICAL = "#0ca30c", "#d03b3b"          # status colors: fixed, always with icon + label
Z_SRM = 3.2905                                 # two-sided z for p = 0.001
SIM = "SIMULATED DATA"

# --------------------------------------------------------------------------- theme JS
THEME_JS = r"""
(function () {
  var INK = {
    light: {primary:"#0b0b0b", secondary:"#52514e", muted:"#898781", grid:"#e1e0d9", axis:"#c3c2b7", surface:"#fcfcfb"},
    dark:  {primary:"#f0efec", secondary:"#c3c2b7", muted:"#898781", grid:"#2c2c2a", axis:"#383835", surface:"#1a1a19"}
  };
  var SLOTS = {
    blue:["#2a78d6","#3987e5"], orange:["#eb6834","#d95926"], red:["#e34948","#e66767"],
    gray:["#898781","#898781"], ink:["#0b0b0b","#f0efec"]
  };
  function mode() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t === "dark" || t === "light") return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function rgba(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  function apply(gd) {
    var m = mode(), k = m === "dark" ? 1 : 0, c = INK[m], L = {};
    gd.data.forEach(function (tr, i) {
      var mt = tr.meta; if (!mt || !mt.slot) return;
      var col = SLOTS[mt.slot][k], u = {};
      if (mt.line) u["line.color"] = col;
      if (mt.marker) u["marker.color"] = col;
      if (mt.fill != null) u["fillcolor"] = rgba(col, mt.fill);
      if (mt.err) u["error_" + mt.err + ".color"] = rgba(col, mt.erralpha || 1);
      if (mt.ring) u["marker.line.color"] = c.surface;
      Plotly.restyle(gd, u, [i]);
    });
    L["font.color"] = c.secondary;
    L["legend.font.color"] = c.secondary;
    L["hoverlabel.bgcolor"] = c.surface;
    L["hoverlabel.bordercolor"] = c.axis;
    L["hoverlabel.font.color"] = c.primary;
    Object.keys(gd.layout).filter(function (x) { return /^[xy]axis\d*$/.test(x); }).forEach(function (a) {
      L[a + ".gridcolor"] = c.grid; L[a + ".linecolor"] = c.axis; L[a + ".zerolinecolor"] = c.axis;
      L[a + ".tickfont.color"] = c.muted; L[a + ".title.font.color"] = c.secondary;
    });
    (gd.layout.annotations || []).forEach(function (a, i) {
      L["annotations[" + i + "].font.color"] = a.name === "muted" ? c.muted : c.secondary;
    });
    (gd.layout.shapes || []).forEach(function (s, i) {
      if (s.name === "ref") L["shapes[" + i + "].line.color"] = c.axis;
      if (s.name === "win") L["shapes[" + i + "].fillcolor"] = rgba(c.muted, 0.12);
    });
    Plotly.relayout(gd, L);
  }
  window.addEventListener("message", function (e) {
    var d = e.data;
    if (d && d.abTheme) {
      if (d.abTheme === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", d.abTheme);
    }
  });
  function postHeight() {
    if (window.parent !== window) window.parent.postMessage({abHeight: document.documentElement.scrollHeight}, "*");
  }
  if (window.ResizeObserver) new ResizeObserver(postHeight).observe(document.documentElement);
  window.addEventListener("load", postHeight);
  function compact(gd) {
    var narrow = gd.clientWidth < 560;
    if (!gd._orig) {
      var m = gd.layout.margin || {};
      gd._orig = {l: m.l, r: m.r, fs: (gd.layout.font || {}).size || 13,
                  xd: gd.layout.xaxis && gd.layout.xaxis.dtick};
    }
    var o = gd._orig, L = {};
    L["margin.l"] = narrow ? (o.l > 150 ? 122 : 62) : o.l;
    L["margin.r"] = narrow ? 10 : o.r;
    L["font.size"] = narrow ? 11 : o.fs;
    if (o.xd === 1) {
      Object.keys(gd.layout).filter(function (x) { return /^xaxis\d*$/.test(x); })
        .forEach(function (a) { L[a + ".dtick"] = narrow ? 2 : 1; });
    }
    Plotly.relayout(gd, L);
  }
  window.ABTheme = {
    mount: function (gd) {
      compact(gd);
      window.addEventListener("resize", function () { compact(gd); });
      apply(gd);
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () { apply(gd); });
      new MutationObserver(function () { apply(gd); })
        .observe(document.documentElement, {attributes: true, attributeFilter: ["data-theme"]});
    }
  };
})();
"""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%%TITLE%%</title>
<style>
  :root { color-scheme: light; --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --rule:#e1e0d9; }
  @media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) {
    color-scheme: dark; --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --rule:#2c2c2a; } }
  :root[data-theme="dark"] { color-scheme: dark; --page:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --rule:#2c2c2a; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--page); color:var(--ink); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }
  main { max-width: 960px; margin: 0 auto; padding: 24px 16px 40px; }
  .card { background:var(--surface); border:1px solid var(--rule); border-radius:12px; padding:20px 16px 8px; }
  h1 { font-size: 20px; font-weight: 600; margin: 0 0 4px; }
  .sub { color: var(--ink2); margin: 0 0 12px; max-width: 70ch; }
  .tag { display:inline-block; font-size:11px; letter-spacing:.06em; color:var(--ink2); border:1px solid var(--rule); border-radius:999px; padding:1px 8px; margin-bottom:8px; }
  #chart { width:100%; max-width:%%MAXW%%; margin:0 auto; }
  details { margin-top: 12px; border-top:1px solid var(--rule); padding: 8px 0; color: var(--ink2); }
  summary { cursor:pointer; }
  table { border-collapse: collapse; width:100%; font-size:13px; margin-top:8px; font-variant-numeric: tabular-nums; }
  th, td { text-align:right; padding:4px 8px; border-bottom:1px solid var(--rule); }
  th:first-child, td:first-child { text-align:left; }
  .note { color: var(--muted); font-size: 13px; margin: 12px 0 0; max-width: 75ch; }
  .tablewrap { overflow-x:auto; }
</style></head>
<body><main>
  <div class="card">
    <span class="tag">%%SIM%%</span>
    <h1>%%HEADING%%</h1>
    <p class="sub">%%SUBTITLE%%</p>
    <div id="chart" role="img" aria-label="%%ALT%%"></div>
    <details><summary>Show data table</summary><div class="tablewrap">%%TABLE%%</div></details>
  </div>
  <p class="note">%%NOTE%%</p>
</main>
<script src="../assets/plotly.min.js"></script>
<script src="../assets/chart-theme.js"></script>
<script>
  var fig = %%FIG%%;
  var gd = document.getElementById("chart");
  Plotly.newPlot(gd, fig.data, fig.layout, {responsive:true, displaylogo:false,
    modeBarButtonsToRemove:["lasso2d","select2d","autoScale2d"]}).then(function () { ABTheme.mount(gd); });
</script></body></html>
"""


def _table(headers: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def _page(fig, slug, out_dir, heading, subtitle, alt, table, note, max_width="100%"):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13), margin=dict(l=70, r=24, t=48, b=56),
        hoverlabel=dict(font=dict(family=FONT)),
    )
    page = (PAGE.replace("%%TITLE%%", html.escape(heading)).replace("%%SIM%%", SIM)
            .replace("%%HEADING%%", html.escape(heading)).replace("%%SUBTITLE%%", html.escape(subtitle))
            .replace("%%ALT%%", html.escape(alt, quote=True)).replace("%%TABLE%%", table)
            .replace("%%NOTE%%", html.escape(note)).replace("%%MAXW%%", max_width).replace("%%FIG%%", fig.to_json()))
    path = out_dir / "charts" / f"{slug}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return path


def _axes(fig, **kw):
    fig.update_xaxes(showline=True, linewidth=1, ticks="", zeroline=False, **kw)
    fig.update_yaxes(showline=False, ticks="", zeroline=False, gridwidth=1)


def _pct(x):
    return f"{x * 100:+.1f}%"


def _ci(ci):
    return f"[{ci[0] * 100:+.1f}, {ci[1] * 100:+.1f}]"


# --------------------------------------------------------------------------- 1. novelty
def chart_novelty(res, out_dir):
    cum, day, win = res["cumulative"], res["daily"], res["windows"]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("Cumulative (days 1 to k)", "Single day"))
    for a in fig.layout.annotations[:2]:
        a.font.size = 12
    for col, series, name in ((1, cum, "Cumulative"), (2, day, "Single day")):
        x = [r["day"] for r in series]
        lo = [r["ci_rel_lift"][0] * 100 for r in series]
        hi = [r["ci_rel_lift"][1] * 100 for r in series]
        y = [r["rel_lift"] * 100 for r in series]
        meta_band = dict(slot="blue", fill=0.12)
        fig.add_trace(go.Scatter(x=x, y=hi, mode="lines", line=dict(width=0), hoverinfo="skip",
                                 showlegend=False, meta=meta_band), row=1, col=col)
        fig.add_trace(go.Scatter(x=x, y=lo, mode="lines", line=dict(width=0), fill="tonexty",
                                 hoverinfo="skip", showlegend=False, meta=meta_band), row=1, col=col)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers", name=name, showlegend=False,
            line=dict(width=2, shape="linear"), marker=dict(size=8, line=dict(width=2)),
            meta=dict(slot="blue", line=True, marker=True, ring=True),
            customdata=list(zip(lo, hi)),
            hovertemplate=f"Day %{{x}}<br>{name} lift %{{y:+.1f}}%<br>95% CI [%{{customdata[0]:+.1f}}, %{{customdata[1]:+.1f}}]<extra></extra>",
        ), row=1, col=col)
    ymax = max(r["ci_rel_lift"][1] for r in cum + day) * 100 + 10
    ymin = min(-6, min(r["ci_rel_lift"][0] for r in cum + day) * 100 - 2)
    fig.add_hline(y=0, line_width=1, line_color="#c3c2b7", name="ref")
    fig.layout.shapes[-1].update(name="ref")
    for (x0, x1, key, label) in ((0.5, 3.5, "early_d1_3", "Days 1–3"), (7.5, 14.5, "late_d8_14", "Days 8–14")):
        fig.add_shape(type="rect", xref="x2", yref="paper", x0=x0, x1=x1, y0=0, y1=1,
                      line_width=0, fillcolor="rgba(137,135,129,0.12)", name="win", layer="below")
        fig.add_annotation(xref="x2", yref="paper", x=(x0 + x1) / 2, y=0.99, yanchor="top", showarrow=False,
                           text=f"{label}<br><b>{_pct(win[key]['rel_lift'])}</b>",
                           font=dict(size=12), align="center")
    fig.update_yaxes(range=[ymin, ymax], ticksuffix="%", title_text="Lift in GMV per user vs control", row=1, col=1)
    fig.update_xaxes(title_text="Experiment day", dtick=1, range=[0.5, 14.5])
    _axes(fig)
    fig.update_layout(height=470, hovermode="closest", margin=dict(l=80, r=24, t=52, b=56))
    e, l_ = win["early_d1_3"], win["late_d8_14"]
    sub = (f"Average lift is {_pct(e['rel_lift'])} over days 1–3 but {_pct(l_['rel_lift'])} over days 8–14. "
           "The cumulative line stays high because early days remain in the average, so it hides the decay.")
    rows = [[c["day"], _pct(c["rel_lift"]), _ci(c["ci_rel_lift"]), _pct(d["rel_lift"]), _ci(d["ci_rel_lift"])]
            for c, d in zip(cum, day)]
    return _page(fig, "novelty", out_dir, "Novelty effect: the lift decays", sub,
                 "Two line charts of treatment lift by experiment day with 95% confidence bands",
                 _table(["Day", "Cumulative lift", "95% CI (%)", "Single-day lift", "95% CI (%)"], rows),
                 "CUPED-adjusted Welch estimates. The cumulative panel is a diagnostic: checking it every day "
                 "inflates false positives. The decision uses only the pre-registered 14-day window.")


# --------------------------------------------------------------------------- 2. forest
def chart_forest(res, out_dir):
    sg = {(r["dimension"], r["level"]): r for r in res["subgroups"]}
    layout = [
        ("All users", None), ("Customer type", None),
        ("New users", ("user_type", "new")), ("Returning users", ("user_type", "returning")),
        ("Activity (returning)", None),
        ("Low", ("segment", "ret_low")), ("Mid", ("segment", "ret_mid")), ("High", ("segment", "ret_high")),
        ("Device", None),
        ("iOS", ("device", "ios")), ("Android", ("device", "android")), ("Web", ("device", "web")),
    ]
    ov = res["overall"]["cuped"]
    n = len(layout)
    tickvals, ticktext, pts = [], [], []
    for i, (label, key) in enumerate(layout):
        y = n - i
        tickvals.append(y)
        if label == "All users":
            ticktext.append("<b>All users</b>"); pts.append(("all", y, label, ov, None))
        elif key is None:
            ticktext.append(f"<b>{label}</b>")
        else:
            ticktext.append("   " + label); pts.append(("sub", y, label, sg[key], sg[key]["p_adj_bh"]))

    def trace(name, sel, slot, symbol, size=9):
        sel = [p for p in pts if sel(p)]
        if not sel:
            return None
        meta = dict(slot=slot, marker=True, err="x", erralpha=1.0, ring=symbol != "circle-open")
        return go.Scatter(
            x=[p[3]["rel_lift"] * 100 for p in sel], y=[p[1] for p in sel], mode="markers", name=name,
            marker=dict(symbol=symbol, size=size, line=dict(width=2, color="#fcfcfb")), meta=meta,
            error_x=dict(type="data", symmetric=False, thickness=2, width=0,
                         array=[(p[3]["ci_rel_lift"][1] - p[3]["rel_lift"]) * 100 for p in sel],
                         arrayminus=[(p[3]["rel_lift"] - p[3]["ci_rel_lift"][0]) * 100 for p in sel]),
            customdata=[[p[2], p[3]["ci_rel_lift"][0] * 100, p[3]["ci_rel_lift"][1] * 100,
                         p[3]["n_control"] + p[3]["n_treatment"],
                         "n/a (primary result)" if p[4] is None else f"{p[4]:.3g}"] for p in sel],
            hovertemplate="<b>%{customdata[0]}</b><br>Lift %{x:+.1f}%<br>95% CI [%{customdata[1]:+.1f}, %{customdata[2]:+.1f}]"
                          "<br>Users %{customdata[3]:,}<br>BH-adjusted p: %{customdata[4]}<extra></extra>")

    sig = lambda p: p[4] is not None and p[4] < 0.05
    traces = [
        trace("All users (primary result)", lambda p: p[0] == "all", "ink", "diamond", 11),
        trace("Significant, positive (BH-adjusted)", lambda p: p[0] == "sub" and sig(p) and p[3]["rel_lift"] > 0, "blue", "circle"),
        trace("Significant, negative (BH-adjusted)", lambda p: p[0] == "sub" and sig(p) and p[3]["rel_lift"] < 0, "red", "square"),
        trace("Not significant after correction", lambda p: p[0] == "sub" and not sig(p), "gray", "circle-open"),
    ]
    fig = go.Figure([t for t in traces if t is not None])
    lo = min(p[3]["ci_rel_lift"][0] for p in pts) * 100
    hi = max(p[3]["ci_rel_lift"][1] for p in pts) * 100
    fig.add_vline(x=0, line_width=1, line_color="#c3c2b7")
    fig.layout.shapes[-1].update(name="ref")
    fig.update_xaxes(range=[lo - 3, hi + 3], ticksuffix="%", title_text="Lift vs control, 95% CI")
    fig.update_yaxes(tickvals=tickvals, ticktext=ticktext, range=[0.4, n + 0.6], showgrid=False)
    _axes(fig)
    fig.update_xaxes(showgrid=True, gridwidth=1)
    fig.update_layout(height=520, margin=dict(l=170, r=24, t=16, b=130),
                      legend=dict(orientation="h", y=-0.2, x=0, yanchor="top"), hovermode="closest")
    new, hi_ = sg[("user_type", "new")], sg[("segment", "ret_high")]
    sub = (f"New users: {_pct(new['rel_lift'])}. High-activity returning users: {_pct(hi_['rel_lift'])}. "
           "These are 14-day lifts in GMV per user; a modest overall effect hides opposite effects in different groups.")
    rows = [[lab, _pct(d["rel_lift"]), _ci(d["ci_rel_lift"]), f"{d['n_control'] + d['n_treatment']:,}",
             f"{d['p_value']:.3g}", f"{d['p_adj_bh']:.3g}"]
            for lab, d in ((l, sg[k]) for l, k in layout if k)]
    rows.insert(0, ["All users", _pct(ov["rel_lift"]), _ci(ov["ci_rel_lift"]), f"{ov['n_control'] + ov['n_treatment']:,}", f"{ov['p_value']:.3g}", "n/a"])
    return _page(fig, "heterogeneity", out_dir, "Who wins, who loses", sub,
                 "Forest plot of treatment lift by user group with confidence intervals",
                 _table(["Group", "Lift", "95% CI (%)", "Users", "p-value", "BH-adjusted p"], rows),
                 "Subgroup effects are exploratory. p-values are Benjamini–Hochberg adjusted across the 9 subgroup tests "
                 "(customer type, activity segment, device); the overall result is the primary test and is not in that family.")


# --------------------------------------------------------------------------- 3. Lorenz
def chart_lorenz(res, out_dir):
    lt = res["long_tail"]
    c, t = lt["control"], lt["treatment"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect equality",
                             line=dict(width=1, dash="dot"), meta=dict(slot="gray", line=True), hoverinfo="skip"))
    for d, name, slot in ((c, "Control", "blue"), (t, "Treatment", "orange")):
        fig.add_trace(go.Scatter(
            x=d["lorenz_x"], y=d["lorenz_y"], mode="lines", line=dict(width=2),
            name=f"{name} (Gini {d['gini']:.2f})", meta=dict(slot=slot, line=True),
            hovertemplate=f"{name}<br>Bottom %{{x:.0%}} of SKUs get %{{y:.1%}} of impressions<extra></extra>"))
    _axes(fig)
    fig.update_xaxes(range=[0, 1], tickformat=".0%", title_text="Share of SKUs, least to most exposed", showgrid=True)
    fig.update_yaxes(range=[0, 1.02], tickformat=".0%", title_text="Cumulative share of impressions", showgrid=True)
    fig.update_layout(height=600, hovermode="x unified", margin=dict(l=80, r=24, t=16, b=130),
                      legend=dict(orientation="h", y=-0.2, x=0, yanchor="top"))
    sub = (f"Gini rises from {c['gini']:.2f} to {t['gini']:.2f}. The top 1% of SKUs take "
           f"{t['top1pct_share']:.0%} of impressions instead of {c['top1pct_share']:.0%}: "
           "the new model concentrates exposure on already-popular items.")
    rows = [["Control", f"{c['gini']:.3f}", f"{c['top1pct_share']:.1%}", c["zero_impression_skus"]],
            ["Treatment", f"{t['gini']:.3f}", f"{t['top1pct_share']:.1%}", t["zero_impression_skus"]]]
    return _page(fig, "long_tail", out_dir, "Long tail: exposure concentrates on hits", sub,
                 "Lorenz curves of SKU impressions for control and treatment",
                 _table(["Arm", "Gini", "Top-1% SKU share of impressions", "SKUs with zero impressions"], rows),
                 "Impressions come from a simple exposure model where treatment sharpens popularity ranking; "
                 "the Gini values are a property of that assumption, shown here to demonstrate the measurement.",
                 max_width="680px")


# --------------------------------------------------------------------------- 4. SRM
def chart_srm(res, out_dir):
    scen = [("clean", "Clean"), ("injected", "Logging loss")]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
                        subplot_titles=[s[1] for s in scen])
    rows = []
    alert_legend_done = False
    for ci_, (key, title) in enumerate(scen, start=1):
        s = res["srm"][key]
        items = [("All devices", s["overall"])] + [(d["device"], d) for d in s["by_device"]]
        names = {"ios": "iOS", "android": "Android", "web": "Web", "All devices": "All"}
        xs, share, band, alert, hov = [], [], [], [], []
        for nm, d in items:
            n = d["n_control"] + d["n_treatment"]
            sh = d["n_treatment"] / n * 100
            xs.append(names[nm]); share.append(sh); band.append(Z_SRM * (0.25 / n) ** 0.5 * 100)
            alert.append(bool(d["alert"]))
            hov.append([d["n_control"], d["n_treatment"], d["p_value"]])
            rows.append([title, names[nm], f"{d['n_control']:,}", f"{d['n_treatment']:,}", f"{sh:.2f}%", f"{d['p_value']:.3g}",
                         "ALERT" if d["alert"] else "ok"])
        fig.add_trace(go.Scatter(
            x=xs, y=[50] * len(xs), mode="markers", name="Expected 50% ± range (alert at p < 0.001)",
            legendgroup="exp", showlegend=ci_ == 1, hoverinfo="skip",
            marker=dict(symbol="line-ew", size=14, line=dict(width=2)),
            error_y=dict(type="data", array=band, thickness=14, width=0), meta=dict(slot="gray", marker=True, err="y", erralpha=0.3)),
            row=1, col=ci_)
        for flag, nm, color, sym in ((False, "Observed treatment share, within range", "blue", "circle"),
                                     (True, "Observed treatment share, SRM alert", "red", "diamond")):
            idx = [i for i, a in enumerate(alert) if a is flag]
            fig.add_trace(go.Scatter(
                x=[xs[i] for i in idx], y=[share[i] for i in idx], mode="markers", name=nm, legendgroup=nm,
                showlegend=(not flag and ci_ == 1) or (flag and bool(idx) and not alert_legend_done),
                marker=dict(symbol=sym, size=11, line=dict(width=2)),
                meta=dict(slot=color, marker=True, ring=True), customdata=[hov[i] for i in idx],
                hovertemplate="<b>%{x}</b><br>Treatment share %{y:.2f}%<br>Control %{customdata[0]:,} · Treatment %{customdata[1]:,}"
                              "<br>χ² p-value %{customdata[2]:.3g}<extra></extra>"), row=1, col=ci_)
        alert_legend_done = alert_legend_done or any(alert)
        ok = not s["overall"]["alert"]
        badge = (f'<span style="color:{GOOD}">✓</span> No SRM' if ok else f'<span style="color:{CRITICAL}">▲</span> SRM detected')
        fig.layout.annotations[ci_ - 1].update(font=dict(size=12), text=f"<b>{title}</b><br>{badge}<br>χ² p = {s['overall']['p_value']:.2g}")
    fig.update_yaxes(range=[40, 60], ticksuffix="%", title_text="Share of users assigned to treatment", row=1, col=1)
    _axes(fig)
    fig.update_yaxes(showgrid=True)
    fig.update_xaxes(showgrid=False)
    fig.update_layout(height=540, margin=dict(l=80, r=24, t=92, b=140),
                      legend=dict(orientation="h", y=-0.12, x=0, yanchor="top"), hovermode="closest")
    inj = res["srm"]["injected"]
    bad = [d["device"] for d in inj["by_device"] if d["alert"]]
    sub = (f"A silent logging loss in the treatment arm is flagged by the chi-square test (p = {inj['overall']['p_value']:.1e}) "
           f"and localizes to: {', '.join(bad) if bad else 'no single device'}. Results from a flagged experiment are not trustworthy.")
    return _page(fig, "srm", out_dir, "Sample ratio mismatch check", sub,
                 "Dot plot of treatment share by device against the expected 50 percent range, for clean and flagged scenarios",
                 _table(["Scenario", "Slice", "Control", "Treatment", "Treatment share", "χ² p-value", "Status"], rows),
                 f"Injected fault: {res['srm'].get('injected_note', 'logging loss')}. Grey bars show the range expected under a true 50/50 split; a dot outside it "
                 "triggers the alert (p < 0.001, the common SRM threshold).")


# --------------------------------------------------------------------------- build
def build(results_path="reports/results.json", out_dir="site") -> list[Path]:
    res = json.loads(Path(results_path).read_text())
    out = Path(out_dir)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "assets" / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    (out / "assets" / "chart-theme.js").write_text(THEME_JS, encoding="utf-8")
    return [f(res, out) for f in (chart_novelty, chart_forest, chart_lorenz, chart_srm)]


if __name__ == "__main__":
    for p in build(*sys.argv[1:3]):
        print("wrote", p)

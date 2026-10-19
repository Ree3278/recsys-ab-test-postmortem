
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

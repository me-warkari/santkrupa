/* santkrupa reader controls — optional. Text renders fully with JS off.
   Preferences are stored only in this browser (localStorage). */
(function () {
  var root = document.documentElement;
  function get(k, d) {
    try { return localStorage.getItem("santkrupa-" + k) || d; } catch (e) { return d; }
  }
  function set(k, v) {
    try { localStorage.setItem("santkrupa-" + k, v); } catch (e) { /* ignore */ }
  }
  function apply() {
    var theme = get("theme", "");
    if (theme) root.setAttribute("data-theme", theme);
    root.setAttribute("data-size", get("size", "1"));
    root.setAttribute("data-spacing", get("spacing", "normal"));
    root.setAttribute("data-font", get("font", "serif"));
    var t = document.getElementById("theme");
    if (t) t.textContent = theme === "dark" ? "☀ प्रकाश" : "☾ अंधारी";
    var s = document.getElementById("spacing");
    if (s) s.setAttribute("aria-pressed", get("spacing", "normal") === "roomy" ? "true" : "false");
    var f = document.getElementById("fontface");
    if (f) f.setAttribute("aria-pressed", get("font", "serif") === "sans" ? "true" : "false");
  }
  function bind(id, fn) {
    var el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  }
  bind("theme", function () {
    set("theme", get("theme", "") === "dark" ? "light" : "dark");
    apply();
  });
  bind("font-plus", function () {
    var s = Math.min(3, parseInt(get("size", "1"), 10) + 1);
    set("size", String(s)); apply();
  });
  bind("font-minus", function () {
    var s = Math.max(0, parseInt(get("size", "1"), 10) - 1);
    set("size", String(s)); apply();
  });
  bind("spacing", function () {
    set("spacing", get("spacing", "normal") === "roomy" ? "normal" : "roomy");
    apply();
  });
  bind("fontface", function () {
    set("font", get("font", "serif") === "sans" ? "serif" : "sans");
    apply();
  });
  document.querySelectorAll("button.copy").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy") || "";
      function done() { btn.textContent = "✓ नक्कल झाले"; setTimeout(function () { btn.textContent = "नक्कल"; }, 1500); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallback(); });
      } else { fallback(); }
      function fallback() {
        var ta = document.createElement("textarea");
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ }
        document.body.removeChild(ta);
      }
    });
  });
  apply();
})();

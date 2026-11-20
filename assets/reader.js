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
  /* --- daily reading rotation (home page only) ---
     #today-data holds one candidate per Haripath section; pick by the
     visitor's day-of-year so the verse changes daily without a rebuild.
     No JS: the server-picked verse stays. */
  var todayData = document.getElementById("today-data");
  var todayBox = document.getElementById("today");
  if (todayData && todayBox) {
    try {
      var cands = JSON.parse(todayData.textContent);
      if (cands.length) {
        var now = new Date();
        var start = new Date(now.getFullYear(), 0, 0);
        var doy = Math.floor((now - start) / 86400000);
        var c = cands[(doy - 1) % cands.length];
        var escHtml = function (s) {
          return s.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        };
        var linesHtml = c.lines.map(escHtml).join("<br>\n");
        var copyText = c.lines.map(escHtml).join("\n");
        todayBox.innerHTML =
          '<article class="verse" id="v-' + c.number + '">\n' +
          '  <p class="vlines">' + linesHtml + '</p>\n' +
          '  <div class="vmeta"><span class="vnum">' + escHtml(c.marker) + '</span>\n' +
          '  <a class="vlink" href="#v-' + c.number + '" title="या अभंगाची जोडणी">¶</a>\n' +
          '  <button class="copy" type="button" data-copy="' + copyText + '" title="हा अभंग नक्कल करा">नक्कल</button></div>\n' +
          '</article>';
        var cap = document.getElementById("today-cap");
        if (cap) {
          var sec = c.section;
          cap.textContent = (sec === "ध्यान" || sec === "समापन भजन" || sec === "भजन")
            ? "हरिपाठ — " + sec + "."
            : "हरिपाठ — भाग " + sec + ".";
        }
      }
    } catch (e) { /* keep the server-rendered verse */ }
  }

  /* --- jump to a verse by its printed number --- */
  var jumpInput = document.getElementById("jump-n");
  var jumpGo = document.getElementById("jump-go");
  function devToInt(s) {
    var map = { "०": 0, "१": 1, "२": 2, "३": 3, "४": 4, "५": 5, "६": 6, "७": 7, "८": 8, "९": 9 };
    var n = 0, found = false;
    for (var i = 0; i < s.length; i++) {
      if (s[i] in map) { n = n * 10 + map[s[i]]; found = true; }
    }
    return found ? n : null;
  }
  function jumpToVerse() {
    if (!jumpInput) return;
    var want = parseInt(jumpInput.value, 10);
    if (!want) return;
    /* First verse whose printed marker matches. In chapters that mix
       ovis and Gita slokas both can carry the same small number; the
       first match in reading order wins. */
    var marks = document.querySelectorAll(".verse .vnum");
    for (var i = 0; i < marks.length; i++) {
      if (devToInt(marks[i].textContent) === want) {
        var art = marks[i].closest("article");
        if (art) art.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }
  }
  if (jumpGo) jumpGo.addEventListener("click", jumpToVerse);
  if (jumpInput) jumpInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); jumpToVerse(); }
  });

  /* --- thin reading-progress bar (reading pages only) --- */
  var prog = document.getElementById("read-progress");
  function updateProgress() {
    if (!prog) return;
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    prog.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + "%";
  }
  if (prog) {
    window.addEventListener("scroll", function () { requestAnimationFrame(updateProgress); }, { passive: true });
    updateProgress();
  }

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
  document.querySelectorAll("button.share-native").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var title = btn.getAttribute("data-share-title") || "";
      var text = btn.getAttribute("data-share-text") || "";
      var url = btn.getAttribute("data-share-url") || location.href;
      var original = btn.innerHTML;
      function copied() {
        btn.innerHTML = "✓ दुवा नक्कल केला";
        setTimeout(function () { btn.innerHTML = original; }, 1800);
      }
      function fallbackCopy() {
        var ta = document.createElement("textarea");
        ta.value = url; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); copied(); } catch (e) { /* ignore */ }
        document.body.removeChild(ta);
      }
      if (navigator.share) {
        navigator.share({ title: title, text: text, url: url }).catch(function () { /* dismissed */ });
      } else if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(copied, fallbackCopy);
      } else { fallbackCopy(); }
    });
  });
  apply();
})();

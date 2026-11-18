/* santkrupa search — client-side only. Fetches the build-time index
   (search-index.json, one level up from /shodh/) and filters locally.
   Nothing is sent to any server. */
(function () {
  var input = document.getElementById("q");
  var out = document.getElementById("results");
  if (!input || !out) return;
  var index = null;
  fetch("../search-index.json")
    .then(function (r) { return r.json(); })
    .then(function (data) { index = data; })
    .catch(function () { out.innerHTML = "<p>शोध सूची लोड झाली नाही. ग्रंथसूचीतून वाचा.</p>"; });
  function devDigits(s) {
    return s.replace(/[०-९]/g, function (d) { return "०१२३४५६७८९".indexOf(d); });
  }
  input.addEventListener("input", function () {
    var q = input.value.trim();
    if (!index) { out.innerHTML = "<p>शोध सूची लोड होत आहे…</p>"; return; }
    if (q.length < 2) { out.innerHTML = "<p>शोध सुरू करण्यासाठी किमान दोन अक्षरे लिहा.</p>"; return; }
    var qn = devDigits(q);
    var hits = index.filter(function (e) {
      return e.text.indexOf(q) !== -1 || e.title.indexOf(q) !== -1 ||
        String(e.n) === qn || devDigits(e.text).indexOf(qn) !== -1;
    }).slice(0, 50);
    if (!hits.length) { out.innerHTML = "<p>काही सापडले नाही — दुसरा शब्द वापरून पहा.</p>"; return; }
    var html = "<p>" + hits.length + " निकाल.</p>";
    hits.forEach(function (e) {
      var snippet = e.text.length > 140 ? e.text.slice(0, 140) + "…" : e.text;
      html += '<div class="result"><a href="../' + e.url + '">' + e.title +
        " — " + e.n + '</a><p>' + snippet.replace(/</g, "&lt;") + "</p></div>";
    });
    out.innerHTML = html;
  });
})();

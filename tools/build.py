#!/usr/bin/env python3
"""santkrupa site builder — Apache License 2.0.

Reads the Devanagari text files in content/<work>/<work>.md (+ SOURCE.md)
and generates a plain-HTML static site in this directory (site/).

Usage:  python3 build.py
Output: index.html, nitya/*, granth/*, vishayi/, shodh/, assets/

No framework, no JavaScript required to read. The generated pages are the
source of truth for nothing — content/ is. Re-run after adding a work.
"""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote as urlquote

ROOT = Path(__file__).resolve().parent          # site/
CONTENT = ROOT.parent / "content"               # content/
REPO = "https://github.com/me-warkari/santkrupa"
ISSUES = REPO + "/issues/new"
SITE_URL = "https://me-warkari.github.io/santkrupa/"
# Cloudflare Web Analytics beacon token (cookieless, anonymous pageviews).
# Empty until the Web Analytics site is created; then fill in the token.
CF_BEACON_TOKEN = ""

DEV_DIGITS = "०१२३४५६७८९"


def dev_num(n: int) -> str:
    """Arabic int -> Devanagari numeral string."""
    return "".join(DEV_DIGITS[int(d)] for d in str(n))


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- parsing

HEADING_WORD = re.compile(r"^॥\s*([^०-९॥|]{1,20})\s*॥\s*$")
SECTION_MD = re.compile(r"^##\s*(.+?)\s*$")
CLOSE_NUMBER = re.compile(r"[०-९]+\s*[॥|।]+\s*$")          # line ends with a number + danda(s)
CLOSE_HARIPATH = re.compile(r"॥\s*[४६]\s*॥\s*$|॥\s*।\s*$")  # haripath abhang closes on ४, ६, or ॥।


def parse_work(slug: str, text: str):
    """Split a work's text into a list of items.

    Item: {"kind": "heading"|"verse", "text": [...lines...] or str,
           "number": int|None, "section": str|None}
    Verse numbers are sequential per work; the trailing marker in the
    source is kept as the displayed number where the source gives one.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    items = []
    section = None
    cur = []          # lines of the verse being accumulated
    seq = 0

    def flush():
        nonlocal cur, seq
        if not cur:
            return
        seq += 1
        items.append({"kind": "verse", "lines": list(cur),
                      "number": seq, "section": section})
        cur = []

    first_content = True
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("वर्ग:"):
            continue                      # Wikisource category junk at file end
        m = SECTION_MD.match(s)
        if m:
            flush()
            section = m.group(1).strip()
            items.append({"kind": "heading", "text": section, "section": section})
            continue
        m = HEADING_WORD.match(s)
        if m and slug == "haripath":
            flush()
            section = m.group(1).strip()
            items.append({"kind": "heading", "text": section, "section": section})
            continue
        if m and s in ("॥ जय जय रघुवीर समर्थ ॥",):
            flush()
            items.append({"kind": "heading", "text": "॥ जय जय रघुवीर समर्थ ॥",
                          "section": section})
            continue
        if s in ("ध्यान", "समापन भजन", "भजन") and slug == "haripath":
            flush()
            section = s
            items.append({"kind": "heading", "text": s, "section": s})
            continue
        if first_content:
            first_content = False
            if slug == "haripath" and s.startswith("श्री ज्ञानदेव हरिपाठ"):
                continue                  # work title line, not a verse
        cur.append(s)
        if slug == "haripath":
            if CLOSE_HARIPATH.search(s):
                flush()
        else:
            if CLOSE_NUMBER.search(s):
                flush()
    flush()
    return items


def verse_marker(lines):
    """Trailing number marker of a verse, e.g. '॥ ६५ ॥' or '||९||'."""
    last = lines[-1]
    m = re.search(r"([॥|]+\s*[०-९]+\s*[॥|।]*)", last)
    if m:
        return m.group(1).strip()
    m = re.search(r"([०-९]+\s*॥)", last)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- works

WORKS = [
    {"slug": "haripath", "title": "श्री ज्ञानदेव हरिपाठ", "short": "हरिपाठ",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "nitya", "path": "nitya/haripath",
     "unit": "अभंग", "licence": "Public Domain",
     "blurb": "रोजच्या पाठासाठी — या आवृत्तीत ३० भाग."},
    {"slug": "pasaydan", "title": "पसायदान", "short": "पसायदान",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "nitya", "path": "nitya/pasaydan",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीच्या शेवटीची ९ ओव्यांची प्रार्थना."},
    {"slug": "changdev-pasashti", "title": "चांगदेव पासष्टी", "short": "चांगदेव पासष्टी",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/changdev-pasashti",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "चांगदेवांना उद्देशून ६५ ओव्या."},
    {"slug": "manache-shlok", "title": "मनाचे श्लोक", "short": "मनाचे श्लोक",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/manache-shlok",
     "unit": "श्लोक", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "मनाला उद्देशून २०५ श्लोक."},
    {"slug": "dnyaneshwari-adhyay-1", "title": "ज्ञानेश्वरी — अध्याय पहिला", "short": "अध्याय पहिला",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-1",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा पहिला अध्याय — २७५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-2", "title": "ज्ञानेश्वरी — अध्याय दुसरा", "short": "अध्याय दुसरा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-2",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा दुसरा अध्याय — ३७५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-3", "title": "ज्ञानेश्वरी — अध्याय तिसरा", "short": "अध्याय तिसरा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-3",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा तिसरा अध्याय — २७६ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-4", "title": "ज्ञानेश्वरी — अध्याय चौथा", "short": "अध्याय चौथा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-4",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा चौथा अध्याय — २२५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-5", "title": "ज्ञानेश्वरी — अध्याय पाचवा", "short": "अध्याय पाचवा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-5",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा पाचवा अध्याय — १८० ओव्या."},
    {"slug": "dasbodh-dashak-1", "title": "दासबोध — दशक पहिला", "short": "दशक पहिला",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-1",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा पहिला दशक — स्तवननाम, १० समास, ३२६ ओव्या."},
    {"slug": "dasbodh-dashak-2", "title": "दासबोध — दशक दुसरा", "short": "दशक दुसरा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-2",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा दुसरा दशक — मूर्खलक्षणनाम, १० समास, ४६९ ओव्या."},
]

# Block counts = ovis + Gita slokas + 1 trailing block (chapter-end line).
# They rose in Nov 2026 when the ''' wikitext wrappers were stripped:
# wrapped sloka lines previously failed CLOSE_NUMBER, so slokas were
# not counted at all. A1 275+47+1, A2 375+72+1, A3 276+43+1,
# A4 225+42+1, A5 180+29+1. Dasbodh Dashak 1: 326 ovis + 2 header blocks
# + 10 samas-end blocks + 1 closing block − 2 merges (S2 ovi 5 and
# S5 ovi 9 have no number markers in the OCR, so each merges into the
# following verse block). Dasbodh Dashak 2: 469 ovis + 2 header blocks
# + 10 samas-end blocks + 1 closing block − 2 merges (S1 ovi 64 and
# S2 ovi 34 have no number markers in the OCR).
EXPECTED = {"haripath": None, "pasaydan": 9, "changdev-pasashti": 65,
            "manache-shlok": 205,
            "dnyaneshwari-adhyay-1": 323, "dnyaneshwari-adhyay-2": 448,
            "dnyaneshwari-adhyay-3": 320, "dnyaneshwari-adhyay-4": 268,
            "dnyaneshwari-adhyay-5": 210, "dasbodh-dashak-1": 337,
            "dasbodh-dashak-2": 480}


def load_source_md(slug: str) -> str:
    """SOURCE.md rendered as simple HTML (headings, lists, paragraphs, links)."""
    path = CONTENT / slug / "SOURCE.md"
    if not path.exists():
        return "<p>स्रोत माहिती उपलब्ध नाही.</p>"
    out, in_list = [], False
    url_re = re.compile(r"(https?://[^\s\)]+)")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{esc(line[2:].strip())}</h3>")
            continue
        line = esc(line)
        line = url_re.sub(lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', line)
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def load_work(work):
    text = (CONTENT / work["slug"] / f'{work["slug"]}.md').read_text(encoding="utf-8")
    items = parse_work(work["slug"], text)
    verses = [i for i in items if i["kind"] == "verse"]
    return items, verses

# ---------------------------------------------------------------- template

BASE = """<!DOCTYPE html>
<html lang="mr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — संतकृपा</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="संतकृपा">
<meta property="og:title" content="{title} — संतकृपा">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
{beacon}
<link rel="stylesheet" href="{prefix}assets/style.css">
<script src="{prefix}assets/reader.js" defer></script>
</head>
<body>
<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{prefix}index.html">॥ संतकृपा ॥</a>
    <nav aria-label="मुख्य">
      <a href="{prefix}index.html">मुख्य</a>
      <a href="{prefix}nitya/haripath/index.html">नित्यपाठ</a>
      <a href="{prefix}granth/index.html">ग्रंथ</a>
      <a href="{prefix}shodh/index.html">शोध</a>
      <a href="{prefix}vishayi/index.html">विषयी</a>
    </nav>
  </div>
</header>
<div class="toolbar" role="group" aria-label="वाचन सोयी">
  <div class="wrap">
    <button id="font-minus" type="button" title="अक्षर लहान">अ−</button>
    <button id="font-plus" type="button" title="अक्षर मोठे">अ+</button>
    <button id="spacing" type="button" title="ओळींमधील अंतर">अंतर</button>
    <button id="fontface" type="button" title="अक्षरशैली बदला">अक्षर</button>
    <button id="theme" type="button" title="प्रकाश / अंधारी पद्धत">☾ अंधारी</button>
  </div>
</div>
<main class="wrap">
{body}
</main>
<footer class="site-foot">
  <div class="wrap">
    <p>संतकृपा — मराठी संतसाहित्य, मूळ ग्रंथ, मोफत. संकेतस्थळाचा कोड Apache 2.0;
    ग्रंथांचे परवाने प्रत्येक कृतीच्या स्रोत पानावर दिलेले आहेत.</p>
    <p><a href="{prefix}vishayi/index.html">विषयी व स्रोत</a> ·
    <a href="{repo}">GitHub</a></p>
  </div>
</footer>
</body>
</html>
"""


def beacon() -> str:
    """Cloudflare Web Analytics beacon (cookieless, anonymous). Empty until configured."""
    if not CF_BEACON_TOKEN:
        return ""
    return ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
            'data-cf-beacon=\'{"token": "' + CF_BEACON_TOKEN + '"}\'></script>')


# WhatsApp brand glyph (Simple Icons, CC0) — inline so every page is self-contained.
# The svg carries explicit width/height and the link carries inline pill styling,
# so the button renders correctly even if the visitor's browser still holds a
# cached copy of style.css (new HTML + old CSS otherwise blows the icon up).
WA_ICON = ('<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" '
           'd="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>')
SHARE_STYLE = ("display:inline-flex;align-items:center;gap:.5em;background:#25D366;"
               "color:#fff;text-decoration:none;font-weight:700;padding:.55em 1em;border-radius:999px")
# Native share icon (Feather "share-2": three dots joined by lines) — drawn from
# primitives so it needs no memorised path data.
SHARE_ICON = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
              '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>')
SHARE_NATIVE_STYLE = ("display:inline-flex;align-items:center;gap:.5em;background:transparent;"
                      "color:inherit;border:1px solid var(--rule);font:inherit;font-weight:700;"
                      "padding:.55em 1em;border-radius:999px;cursor:pointer")


def share_link(title: str, url: str) -> str:
    """WhatsApp button + native share button (opens the phone's share sheet)."""
    text = urlquote(f"{title} — संतकृपा {url}")
    return (
        '<p class="share" style="display:flex;gap:.6em;flex-wrap:wrap">'
        f'<a href="https://api.whatsapp.com/send?text={text}" style="{SHARE_STYLE}">'
        f"{WA_ICON}WhatsApp वर पाठवा</a>"
        f'<button type="button" class="share-native" style="{SHARE_NATIVE_STYLE}" '
        f'data-share-title="{esc(title)}" data-share-text="{esc(title + " — संतकृपा")}" data-share-url="{esc(url)}">'
        f"{SHARE_ICON}सामायिक करा</button></p>")


def page(prefix: str, title: str, desc: str, body: str, url: str = "") -> str:
    full = SITE_URL + url
    return BASE.format(prefix=prefix, title=esc(title), desc=esc(desc),
                       body=body, repo=REPO, url=full, beacon=beacon())


def breadcrumb(prefix: str, crumbs):
    parts = ['<nav class="crumbs" aria-label="मार्ग">']
    parts.append(f'<a href="{prefix}index.html">मुख्य</a>')
    for label, href in crumbs:
        parts.append(" › ")
        parts.append(f'<a href="{href}">{esc(label)}</a>' if href else esc(label))
    parts.append("</nav>")
    return "".join(parts)


def report_link(prefix: str, work, verse_no=None):
    title = f"चूक नोंदवा: {work['title']}"
    if verse_no:
        title += f" ({work['unit']} {dev_num(verse_no)})"
    body = (f"कृती: {work['title']}%0A"
            f"स्रोत: {REPO}/blob/main/content/{work['slug']}/{work['slug']}.md")
    return (f"{ISSUES}?title={html.escape(title, quote=True)}"
            f"&amp;body={body}")


def verse_html(work, item, prefix: str) -> str:
    lines = "<br>\n".join(esc(ln) for ln in item["lines"])
    marker = verse_marker(item["lines"])
    num = marker or f"॥ {dev_num(item['number'])} ॥"
    copy_text = "\n".join(item["lines"])
    anchor = f"v-{item['number']}"
    return (
        f'<article class="verse" id="{anchor}">\n'
        f'  <p class="vlines">{lines}</p>\n'
        f'  <div class="vmeta"><span class="vnum">{esc(num)}</span>\n'
        f'  <a class="vlink" href="#{anchor}" title="या {work["unit"]}ची जोडणी">¶</a>\n'
        f'  <button class="copy" type="button" data-copy="{esc(copy_text)}" '
        f'title="हा {work["unit"]} नक्कल करा">नक्कल</button></div>\n'
        f'</article>'
    )


def proofing_needed(slug: str) -> bool:
    """True when the work's SOURCE.md marks proofing as NEEDED."""
    path = CONTENT / slug / "SOURCE.md"
    return path.exists() and "Proofing: NEEDED" in path.read_text(encoding="utf-8")


def reading_page(work, items, verses, prev_work, next_work, prefix: str) -> str:
    count = len(verses)
    head = [breadcrumb(prefix, [("नित्यपाठ" if work["kind"] == "nitya" else "ग्रंथ",
                                 f"{prefix}{'nitya' if work['kind'] == 'nitya' else 'granth'}/index.html"),
                                (work["title"], None)]),
            f"<h1>{esc(work['title'])}</h1>",
            f"<p class=\"byline\">{esc(work['author'])} · {dev_num(count)} {work['unit']} · "
            f"मूळ ग्रंथ</p>",
            "<p class=\"source-line\">स्रोत, परवाना व तपासणीची स्थिती — "
            f"खाली स्रोत विभाग पहा. या पानावरील मजकूर तपासणीच्या प्रतीक्षेत आहे; "
            "चूक आढळल्यास कृपया नोंदवा.</p>",
            share_link(work["title"], SITE_URL + work["path"] + "/")]
    if proofing_needed(work["slug"]):
        head.append('<p class="notice">ही आवृत्ती तपासणी बाकी आहे — मजकुरात चुका असू शकतात. '
                    'चूक आढळल्यास “चूक नोंदवा” वापरा.</p>')
    nav = []
    if prev_work:
        nav.append(f'<a class="prev" href="{prefix}{prev_work["path"]}/index.html">← {esc(prev_work["short"])}</a>')
    if next_work:
        nav.append(f'<a class="next" href="{prefix}{next_work["path"]}/index.html">{esc(next_work["short"])} →</a>')
    if nav:
        head.append(f'<nav class="prevnext" aria-label="मागील / पुढील कृती">{" ".join(nav)}</nav>')
    body = ["\n".join(head)]
    for item in items:
        if item["kind"] == "heading":
            body.append(f'<h2 class="vsection">{esc(item["text"])}</h2>')
        else:
            body.append(verse_html(work, item, prefix))
    if nav:
        body.append(f'<nav class="prevnext" aria-label="मागील / पुढील कृती">{" ".join(nav)}</nav>')
    body.append('<section class="sourcebox" aria-label="स्रोत">'
                '<h2>स्रोत</h2>' + load_source_md(work["slug"]) +
                f'<p><a href="{report_link(prefix, work)}">चूक नोंदवा ↗</a> — '
                'GitHub वर issue उघडेल; कृती व ओवी/श्लोक क्रमांक आधीच भरलेला असेल.</p>'
                '</section>')
    return page(prefix, work["title"],
                f"{work['title']} — {work['author']}, {dev_num(count)} {work['unit']}. मूळ ग्रंथ, मराठी.",
                "\n".join(body), url=f"{work['path']}/index.html")


def work_card(prefix: str, work, count: int) -> str:
    return (
        f'<article class="card">\n'
        f'  <h3><a href="{prefix}{work["path"]}/index.html">{esc(work["title"])}</a></h3>\n'
        f'  <p>{esc(work["author"])} · {dev_num(count)} {work["unit"]}</p>\n'
        f'  <p>{esc(work["blurb"])}</p>\n'
        f'  <p class="lic">{esc(work["licence"])} · तपासणी बाकी</p>\n'
        f'</article>'
    )


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- main

def main() -> int:
    loaded = {}
    for work in WORKS:
        items, verses = load_work(work)
        loaded[work["slug"]] = (items, verses)
        expected = EXPECTED[work["slug"]]
        flag = ""
        if expected is not None and len(verses) != expected:
            flag = f"  <-- EXPECTED {expected}, MISMATCH!"
        print(f"{work['slug']}: {len(verses)} {work['unit']}{flag}")

    # ---- reading pages (with prev/next in WORKS order)
    for i, work in enumerate(WORKS):
        items, verses = loaded[work["slug"]]
        prev_w = WORKS[i - 1] if i > 0 else None
        next_w = WORKS[i + 1] if i + 1 < len(WORKS) else None
        depth = len(work["path"].split("/"))
        prefix = "../" * depth
        write(ROOT / work["path"] / "index.html",
              reading_page(work, items, verses, prev_w, next_w, prefix))

    # ---- granth index
    granth = [w for w in WORKS if w["kind"] == "granth"]
    nitya = [w for w in WORKS if w["kind"] == "nitya"]
    cards = "\n".join(work_card("../", w, len(loaded[w["slug"]][1])) for w in granth)
    write(ROOT / "granth" / "index.html", page(
        "../", "ग्रंथ", "संतकृपा ग्रंथसूची — मूळ ग्रंथ.",
        breadcrumb("../", [("ग्रंथ", None)])
        + "<h1>ग्रंथ</h1>"
        + "<p>मूळ ग्रंथच — भाष्य, अर्थ किंवा भाषांतर नाही. प्रत्येक ग्रंथाच्या पानावर स्रोत, परवाना व तपासणीची स्थिती दिली आहे.</p>"
        + f'<div class="cards">{cards}</div>'
        + "<p>येत्या कृती: ज्ञानेश्वरी अध्याय ६–१८, दासबोध दशक ३–२०, तुकाराम गाथा, नामदेव गाथा, एकनाथी भागवत — मजकूर तयार होताच येथे येतील. रिकामी पाने प्रसिद्ध केली जात नाहीत.</p>",
        url="granth/index.html"))

    # ---- nitya index
    cards = "\n".join(work_card("../", w, len(loaded[w["slug"]][1])) for w in nitya)
    write(ROOT / "nitya" / "index.html", page(
        "../", "नित्यपाठ", "रोजच्या पाठासाठी — हरिपाठ, पसायदान.",
        breadcrumb("../", [("नित्यपाठ", None)])
        + "<h1>नित्यपाठ</h1>"
        + "<p>रोज वाचण्यासाठी — हरिपाठ व पसायदान. एका बैठकीत वाचता येण्याइतके लहान.</p>"
        + f'<div class="cards">{cards}</div>',
        url="nitya/index.html"))

    # ---- home
    hp_items, hp_verses = loaded["haripath"]
    today = hp_verses[1] if len(hp_verses) > 1 else hp_verses[0]  # first abhang of section एक
    today_html = verse_html(WORKS[0], today, "")
    all_cards = "\n".join(work_card("", w, len(loaded[w["slug"]][1])) for w in WORKS)
    home_body = (
        '<section class="hero">'
        '<h1>॥ संतकृपा ॥</h1>'
        '<p class="tagline">मराठी संतसाहित्य — मूळ ग्रंथ, मोफत, स्रोतासह.</p>'
        '<div class="actions">'
        '<a class="big" href="nitya/haripath/index.html">आजचा हरिपाठ वाचा →</a>'
        '<a class="big ghost" href="granth/index.html">ग्रंथ शोधा</a>'
        '</div></section>'
        '<section><h2>आजचे वाचन</h2>'
        '<p>हरिपाठ — भाग एक, पहिला अभंग. पूर्ण हरिपाठ '
        '<a href="nitya/haripath/index.html">येथे वाचा</a>.</p>'
        f'{today_html}</section>'
        '<section><h2>या वेळच्या कृती</h2>'
        f'<div class="cards">{all_cards}</div></section>'
        '<section><h2>हे संकेतस्थळ कसे आहे</h2>'
        '<p>संतकृपा ही मराठी संतांच्या मूळ ग्रंथांची मुक्त वाचनालय आहे. '
        'प्रत्येक कृतीचा मजकूर युनिकोड देवनागरीत, स्रोत व परवान्यासह दिला आहे. '
        'भाष्य, अर्थ, भाषांतर किंवा कृत्रिम अर्थ येथे नाहीत. मजकूर तपासणीच्या प्रतीक्षेत आहे — '
        'चूक आढळल्यास प्रत्येक पानावरची “चूक नोंदवा” जोडणी वापरा.</p>'
        '<p>जाहिराती नाहीत, खाते लागत नाही. भेटींची मोजणी कुकीशिवाय व निनावी — फक्त आमच्या माहितीसाठी.</p></section>')
    write(ROOT / "index.html", page("", "मुख्य", "संतकृपा — मराठी संतसाहित्य, मूळ ग्रंथ, मोफत.", home_body, url=""))

    # ---- about / vishayi
    write(ROOT / "vishayi" / "index.html", page(
        "../", "विषयी", "संतकृपा कशासाठी, स्रोत व परवाने.",
        breadcrumb("../", [("विषयी", None)])
        + "<h1>विषयी</h1>"
        + "<h2>संतकृपा कशासाठी</h2>"
        "<p>मराठी संतांचे मूळ ग्रंथ — हरिपाठ, पसायदान, ग्रंथ — देवनागरीत, मोफत वाचता यावेत, "
        "हे या संकेतस्थळाचे काम आहे. मजकूर हा संकेतस्थळाचा गाभा आहे; वाचनासाठी लागणारी "
        "सोय — मोठी अक्षरे, अंधारी पद्धत, छपाई — त्याभोवती बांधली आहे.</p>"
        "<h2>स्रोत</h2>"
        "<p>मजकूर दोनच प्रकारच्या स्रोतांतून येतो: मराठी विकिस्रोतावरील टंकलिखित मजकूर, "
        "आणि archive.org / डिजिटल लायब्ररी ऑफ इंडिया यांवरील सार्वजनिक क्षेत्रातील छापील "
        "पुस्तकांचे स्कॅन (Tesseract ने देवनागरी OCR करून, मग तपासून). प्रत्येक कृतीच्या "
        "स्रोत विभागात लेखक, आवृत्ती, स्रोताची जोडणी, परवाना व तपासणीची स्थिती दिलेली आहे.</p>"
        "<h2>परवाने</h2>"
        "<ul><li>संकेतस्थळाचा कोड (हा जनरेटर व संशोधन एजंट): Apache License 2.0.</li>"
        "<li>मूळ ग्रंथ: सार्वजनिक क्षेत्र (Public Domain) — मध्ययुगीन संत किंवा १९३० पूर्वीच्या आवृत्त्या.</li>"
        "<li>विकिस्रोतावरील टंकलेखन: CC BY-SA 4.0, विकिस्रोताचा उल्लेखासह — मूळ कृती "
        "सार्वजनिक क्षेत्रात असली तरी टंकलेखनावर विकिमीडियाचा परवाना लागू होतो.</li></ul>"
        "<h2>येथे काय नाही — आणि का</h2>"
        "<ul>"
        "<li><b>परवानगी नसलेल्या स्रोतांतील मजकूर नाही.</b> ज्या स्रोतांकडून पुनर्प्रकाशनाची "
        "परवानगी नाही, त्यांचा मजकूर येथे घेतलेला नाही. संतकृपा फक्त सार्वजनिक क्षेत्रातील "
        "स्रोतांतूनच बांधली आहे.</li>"
        "<li><b>आधुनिक अर्थ, भाष्य व भाषांतरे नाहीत.</b> ती बहुधा अजूनही हक्काधीन असतात; फक्त मूळ ग्रंथ येथे आहेत.</li>"
        "<li><b>कृत्रिम अर्थ नाहीत.</b> यंत्राने लिहिलेले अर्थ किंवा भाष्य येथे कधीही येणार नाही.</li>"
        "<li><b>तुकडोजी महाराजांचे साहित्य नाही</b> — ते १ जानेवारी २०२९ पर्यंत सार्वजनिक क्षेत्रात येत नाही.</li>"
        "<li><b>मोडी लिपीतील किंवा हस्तलिखित स्कॅन नाहीत.</b> त्यांचे देवनागरी OCR होत नाही; ते हाताने "
        "टंकलिखित केल्याशिवाय येणार नाहीत.</li>"
        "</ul>"
        "<h2>तपासणी</h2>"
        "<p>सध्या सर्व कृती “तपासणी बाकी” आहेत. OCR मधील चुका व विकिस्रोतावरील “तपासणी करायचे” "
        "खुणा यांची पडताळणी सार्वजनिक क्षेत्रातील आवृत्तीशी करूनच पूर्ण होईल. चूक आढळल्यास "
        "प्रत्येक वाचन पानावरची “चूक नोंदवा” जोडणी वापरा.</p>"
        "<h2>हे कसे बांधले आहे</h2>"
        "<p>मजकूर <code>content/</code> मधील साध्या मजकूर फाइल्समध्ये आहे. "
        "<code>tools/build.py</code> ही साधी Python स्क्रिप्ट त्यांतून साधी HTML पाने तयार करते — "
        "कोणतेही फ्रेमवर्क नाही, वाचण्यासाठी JavaScript लागत नाही, अक्षरे संकेतस्थळावरच "
        "ठेवलेली आहेत (Tiro Devanagari Marathi व Mukta, SIL Open Font License).</p>",
        url="vishayi/index.html"))

    # ---- search index + search page
    index = []
    for work in WORKS:
        for item in loaded[work["slug"]][1]:
            index.append({"work": work["slug"], "title": work["title"],
                          "n": item["number"],
                          "text": " ".join(item["lines"]),
                          "url": f"{work['path']}/index.html#v-{item['number']}"})
    write(ROOT / "search-index.json", json.dumps(index, ensure_ascii=False))
    write(ROOT / "shodh" / "index.html", page(
        "../", "शोध", "संतकृपा मजकुरात शोधा.",
        breadcrumb("../", [("शोध", None)])
        + "<h1>शोध</h1>"
        + "<p>कृती, संत किंवा मजकुरातील शब्द शोधा. शोध तुमच्या ब्राउझरमध्येच चालतो; "
        "काहीही सर्व्हरला पाठवले जात नाही. (शोधासाठी JavaScript लागते; ते बंद असेल तरी "
        "ग्रंथसूचीतील जोडण्यांनी वाचता येते.)</p>"
        + '<p><label>शोधा: <input id="q" type="search" placeholder="उदा. हरि, राम, मना" size="30"></label></p>'
        + '<div id="results"><p>शोध सुरू करण्यासाठी वर शब्द लिहा.</p></div>'
        + '<script src="../assets/search.js" defer></script>',
        url="shodh/index.html"))
    # ---- sitemap + robots (reach: let search engines find every page)
    urls = []
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).as_posix()
        if rel == "index.html":
            loc = SITE_URL
        elif rel.endswith("/index.html"):
            loc = SITE_URL + rel[:-len("index.html")]
        else:
            loc = SITE_URL + rel
        urls.append(loc)
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
               + "</urlset>\n")
    write(ROOT / "sitemap.xml", sitemap)
    write(ROOT / "robots.txt",
          f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    print(f"sitemap: {len(urls)} urls")
    print(f"search index: {len(index)} verses")
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
from datetime import date
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
    {"slug": "kanhopatra-aga-vaikunthichya-raya", "title": "अगा वैकुंठीच्या राया", "short": "अगा वैकुंठीच्या राया",
     "author": "संत कान्होपात्रा", "author_en": "Sant Kanhopatra",
     "kind": "abhang", "path": "granth/kanhopatra-aga-vaikunthichya-raya",
     "unit": "अभंग", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "कान्होपात्रेचा अभंग — वैकुंठीच्या रायाला आर्त हाक."},
    {"slug": "kanhopatra-nako-devraya-anta-ata-pahu", "title": "नको देवराया, अंत आता पाहू", "short": "नको देवराया, अंत आता पाहू",
     "author": "संत कान्होपात्रा", "author_en": "Sant Kanhopatra",
     "kind": "abhang", "path": "granth/kanhopatra-nako-devraya-anta-ata-pahu",
     "unit": "अभंग", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "कान्होपात्रेचा अभंग — अंत न पाहण्याची विनवणी."},
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
    {"slug": "dnyaneshwari-adhyay-6", "title": "ज्ञानेश्वरी — अध्याय सहावा", "short": "अध्याय सहावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-6",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा सहावा अध्याय — ४९६ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-8", "title": "ज्ञानेश्वरी — अध्याय आठवा", "short": "अध्याय आठवा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-8",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा आठवा अध्याय — २७१ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-9", "title": "ज्ञानेश्वरी — अध्याय नववा", "short": "अध्याय नववा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-9",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा नववा अध्याय — ५३५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-10", "title": "ज्ञानेश्वरी — अध्याय दहावा", "short": "अध्याय दहावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-10",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा दहावा अध्याय — ३३५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-11", "title": "ज्ञानेश्वरी — अध्याय अकरावा", "short": "अध्याय अकरावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-11",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा अकरावा अध्याय — ७०८ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-12", "title": "ज्ञानेश्वरी — अध्याय बारावा", "short": "अध्याय बारावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-12",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा बारावा अध्याय — २४७ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-14", "title": "ज्ञानेश्वरी — अध्याय चौदावा", "short": "अध्याय चौदावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-14",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा चौदावा अध्याय — ४१५ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-15", "title": "ज्ञानेश्वरी — अध्याय पंधरावा", "short": "अध्याय पंधरावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-15",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा पंधरावा अध्याय — ५९९ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-16", "title": "ज्ञानेश्वरी — अध्याय सोळावा", "short": "अध्याय सोळावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-16",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा सोळावा अध्याय — ४७३ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-17", "title": "ज्ञानेश्वरी — अध्याय सतरावा", "short": "अध्याय सतरावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-17",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा सतरावा अध्याय — ४३३ ओव्या."},
    {"slug": "dnyaneshwari-adhyay-18", "title": "ज्ञानेश्वरी — अध्याय अठरावा", "short": "अध्याय अठरावा",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/dnyaneshwari-adhyay-18",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ज्ञानेश्वरीचा अठरावा अध्याय — १८११ ओव्या."},
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
    {"slug": "dasbodh-dashak-3", "title": "दासबोध — दशक तिसरा", "short": "दशक तिसरा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-3",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा तिसरा दशक — स्वगुणपरीक्षानाम, १० समास, ५८१ ओव्या."},
    {"slug": "dasbodh-dashak-4", "title": "दासबोध — दशक चवथा", "short": "दशक चवथा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-4",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा चवथा दशक — नवविधा भक्तिनाम, १० समास, २९५ ओव्या."},
    {"slug": "dasbodh-dashak-5", "title": "दासबोध — दशक पांचवा", "short": "दशक पांचवा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-5",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा पांचवा दशक — मंत्रांचा, १० समास, ५७३ ओव्या."},
    {"slug": "dasbodh-dashak-6", "title": "दासबोध — दशक सहावा", "short": "दशक सहावा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-6",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा सहावा दशक — देवशोधननाम, १० समास, ४१३ ओव्या."},
    {"slug": "dasbodh-dashak-7", "title": "दासबोध — दशक सातवा", "short": "दशक सातवा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-7",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा सातवा दशक — चौदा ब्रह्मांचा, १० समास, ५६४ ओव्या."},
    {"slug": "dasbodh-dashak-8", "title": "दासबोध — दशक आठवा", "short": "दशक आठवा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-8",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा आठवा दशक — मायोद्भव अथवा ज्ञानदशक, १० समास, ६४४ ओव्या."},
    {"slug": "dasbodh-dashak-9", "title": "दासबोध — दशक नववा", "short": "दशक नववा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-9",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा नववा दशक — गुणरूप, १० समास, ४२७ ओव्या."},
    {"slug": "dasbodh-dashak-10", "title": "दासबोध — दशक दहावा", "short": "दशक दहावा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-10",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा दहावा दशक — जगज्ज्योतीनाम, १० समास, ३५४ ओव्या."},
    {"slug": "dasbodh-dashak-11", "title": "दासबोध — दशक अकरावा", "short": "दशक अकरावा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-11",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा अकरावा दशक — भीमदशक, १० समास, २८७ ओव्या."},
    {"slug": "dasbodh-dashak-12", "title": "दासबोध — दशक बारावा", "short": "दशक बारावा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-12",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा बारावा दशक — विवेकवैराग्य, १० समास, २९४ ओव्या."},
    {"slug": "dasbodh-dashak-13", "title": "दासबोध — दशक तेरावा", "short": "दशक तेरावा",
     "author": "समर्थ रामदास", "author_en": "Samarth Ramdas",
     "kind": "granth", "path": "granth/dasbodh-dashak-13",
     "unit": "ओवी", "licence": "Public Domain",
     "blurb": "दासबोधाचा तेरावा दशक — नामरूप, १० समास, ३०० ओव्या."},
    {"slug": "bhavarth-ramayan-adhyay-1", "title": "भावार्थ रामायण — अध्याय पहिला", "short": "अध्याय पहिला",
     "author": "संत एकनाथ", "author_en": "Sant Eknath",
     "kind": "granth", "path": "granth/bhavarth-ramayan-adhyay-1",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "भावार्थ रामायणाचा पहिला अध्याय (बालकाण्ड) — ११९ ओव्या."},
    {"slug": "amritanubhav-ch-1", "title": "अमृतानुभव — अध्याय १", "short": "अध्याय १",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/amritanubhav-ch-1",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "अमृतानुभवाचे पहिले प्रकरण (शिवशक्तिसमावेशन) — ६४ ओव्या."},
    {"slug": "amritanubhav-ch-3", "title": "अमृतानुभव — अध्याय ३", "short": "अध्याय ३",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/amritanubhav-ch-3",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "अमृतानुभवाचे तिसरे प्रकरण (वाचाऋण परिहार) — ३३ ओव्या."},
    {"slug": "amritanubhav-ch-4", "title": "अमृतानुभव — अध्याय ४", "short": "अध्याय ४",
     "author": "संत ज्ञानेश्वर", "author_en": "Sant Dnyaneshwar",
     "kind": "granth", "path": "granth/amritanubhav-ch-4",
     "unit": "ओवी", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "अमृतानुभवाचे चवथे प्रकरण (ज्ञानाज्ञानभेदकथन) — ४३ ओव्या."},
    {"slug": "namdev-abhanggatha", "title": "नामदेव अभंगगाथा (निवड)", "short": "अभंगगाथा (निवड)",
     "author": "संत नामदेव", "author_en": "Sant Namdev",
     "kind": "granth", "path": "granth/namdev-abhanggatha",
     "unit": "अभंग", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "नामदेवांच्या १०० अभंगांची निवड — मुख्यतः बाळकृष्ण लीला."},
    {"slug": "gondavalekar-pravachane-january", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — जानेवारी", "short": "जानेवारी",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-january",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "जानेवारी महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-february", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — फेब्रुवारी", "short": "फेब्रुवारी",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-february",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "फेब्रुवारी महिन्यातील २९ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-march", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — मार्च", "short": "मार्च",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-march",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "मार्च महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-april", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — एप्रिल", "short": "एप्रिल",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-april",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "एप्रिल महिन्यातील ३० दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-may", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — मे", "short": "मे",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-may",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "मे महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-june", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — जून", "short": "जून",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-june",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "जून महिन्यातील ३० दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-july", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — जुलै", "short": "जुलै",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-july",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "जुलै महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-august", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — ऑगस्ट", "short": "ऑगस्ट",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-august",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ऑगस्ट महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-september", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — सप्टेंबर", "short": "सप्टेंबर",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-september",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "सप्टेंबर महिन्यातील ३० दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-october", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — ऑक्टोबर", "short": "ऑक्टोबर",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-october",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "ऑक्टोबर महिन्यातील ३१ दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-november", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — नोव्हेंबर", "short": "नोव्हेंबर",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-november",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "नोव्हेंबर महिन्यातील ३० दिवसांची प्रवचने."},
    {"slug": "gondavalekar-pravachane-december", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने — डिसेंबर", "short": "डिसेंबर",
     "author": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज)", "author_en": "Shri Brahmachaitanya Maharaj (Gondavalekar Maharaj)",
     "kind": "granth", "path": "granth/gondavalekar-pravachane-december",
     "unit": "दिवस", "licence": "CC BY-SA 4.0 · Wikisource",
     "blurb": "डिसेंबर महिन्यातील ३१ दिवसांची प्रवचने."},
]

# Series: parent works that group related parts, so a reader finds the
# neighbouring chapters of the same granth together. A work's series is
# derived from its slug prefix, so new chapters group automatically:
# dnyaneshwari-*, dasbodh-*, amritanubhav-*, bhavarth-*, namdev-*,
# gondavalekar-pravachane-*; haripath/pasaydan are nitya; anything else
# is a standalone granth.
# "index" is the series page (None while nothing in the series is published
# yet — empty pages are never published); "upcoming" is plain text, no link.
SERIES = [
    {"key": "nitya", "title": "नित्यपाठ",
     "blurb": "रोजच्या पाठासाठी — हरिपाठ व पसायदान.",
     "index": "nitya/index.html", "upcoming": "",
     "progress": "", "plan": ""},
    {"key": "dnyaneshwari", "title": "ज्ञानेश्वरी",
     "blurb": "संत ज्ञानेश्वरांची गीतेवरील ओवीबद्ध टीका — १८ अध्याय.",
     "index": "granth/dnyaneshwari/index.html",
     "upcoming": "अध्याय ७ व १३ येत आहेत.",
     "progress": "१७ / १८ अध्याय",
     "plan": "रोज एक अध्याय — १८ दिवसांत पूर्ण."},
    {"key": "dasbodh", "title": "दासबोध",
     "blurb": "समर्थ रामदासांचा उपदेशपर ग्रंथ — २० दशक.",
     "index": "granth/dasbodh/index.html",
     "upcoming": "दशक १४–२० येत आहेत.",
     "progress": "१३ / २० दशक",
     "plan": "रोज एक दशक — २० दिवसांत पूर्ण."},
    {"key": "amritanubhav", "title": "अमृतानुभव",
     "blurb": "संत ज्ञानेश्वरांचे अद्वैतपर प्रकरण.",
     "index": "granth/amritanubhav/index.html",
     "upcoming": "अध्याय २, ५–१० विकिस्रोतवर उपलब्ध नाहीत.",
     "progress": "३ / १० अध्याय",
     "plan": "रोज एक अध्याय — १० दिवसांत पूर्ण."},
    {"key": "bhavarth-ramayan", "title": "भावार्थ रामायण",
     "blurb": "संत एकनाथांची रामायणावरील ओवीबद्ध टीका.",
     "index": "granth/bhavarth-ramayan/index.html", "upcoming": "",
     "progress": "अध्याय १ उपलब्ध", "plan": ""},
    {"key": "namdev", "title": "नामदेव गाथा",
     "blurb": "संत नामदेवांचे अभंग.",
     "index": "granth/namdev/index.html",
     "upcoming": "नामदेव गाथा — पहिले १०० अभंग OCR मधून येत आहेत.",
     "progress": "१०० अभंगांची निवड उपलब्ध", "plan": ""},
    {"key": "tukaram", "title": "तुकाराम गाथा",
     "blurb": "संत तुकारामांचे अभंग — ४,५८३ अभंग.",
     "index": None,
     "upcoming": "गाथा १–४५८३ तयारीत आहे.",
     "progress": "", "plan": ""},
    {"key": "eknathi-bhagavat", "title": "एकनाथी भागवत",
     "blurb": "संत एकनाथांची भागवतावरील ओवीबद्ध टीका.",
     "index": None,
     "upcoming": "अध्याय १ OCR मधून येत आहे.",
     "progress": "", "plan": ""},
    {"key": "gondavalekar-pravachane", "title": "श्रीब्रह्मचैतन्य महाराजांची प्रवचने",
     "blurb": "श्रीब्रह्मचैतन्य महाराज (गोंदवलेकर महाराज) यांची रोजची प्रवचने — वर्षातील ३६६ दिवस.",
     "index": "granth/gondavalekar-pravachane/index.html",
     "upcoming": "",
     "progress": "१२ / १२ महिने · ३६६ दिवस",
     "plan": "रोज एक दिवस — वर्षभराची वाचन योजना."},
    {"key": "other", "title": "इतर ग्रंथ",
     "blurb": "एकेक ग्रंथ — चांगदेव पासष्टी, मनाचे श्लोक, कान्होपात्रा अभंग.",
     "index": "granth/other/index.html", "upcoming": "",
     "progress": "४ ग्रंथ उपलब्ध", "plan": ""},
]
SERIES_BY_KEY = {s["key"]: s for s in SERIES}


def series_key(slug: str) -> str:
    if slug in ("haripath", "pasaydan"):
        return "nitya"
    for prefix, key in (("dnyaneshwari-", "dnyaneshwari"),
                        ("dasbodh-", "dasbodh"),
                        ("amritanubhav-", "amritanubhav"),
                        ("bhavarth-", "bhavarth-ramayan"),
                        ("namdev-", "namdev"),
                        ("gondavalekar-pravachane-", "gondavalekar-pravachane")):
        if slug.startswith(prefix):
            return key
    return "other"


def series_works(key: str):
    return [w for w in WORKS if series_key(w["slug"]) == key]


def series_card(prefix: str, series, loaded):
    """Compact card for a series (home + granth index): title, one line on
    what it is, how much is published, and what is coming. The full chapter
    list lives on the series page, not here."""
    if series["index"]:
        title = f'<h3><a href="{prefix}{series["index"]}">{esc(series["title"])}</a></h3>'
    else:
        title = f'<h3>{esc(series["title"])}</h3>'
    parts = [f'<article class="card series-card">{title}',
             f'<p>{esc(series["blurb"])}</p>']
    if series.get("progress"):
        parts.append(f'<p class="progress">{esc(series["progress"])}</p>')
    if series["upcoming"]:
        parts.append(f'<p class="upcoming">येत आहे — {esc(series["upcoming"])}</p>')
    parts.append("</article>")
    return "\n".join(parts)


def toc_list(prefix: str, works, loaded):
    """Numbered table of contents for a series page: chapter, verse count."""
    rows = []
    for w in works:
        count = len(loaded[w["slug"]][1])
        rows.append(f'<li><a href="{prefix}{w["path"]}/index.html">{esc(w["short"])}</a>'
                    f' <span class="tcount">{dev_num(count)} {w["unit"]}</span></li>')
    return '<ol class="toc">\n' + "\n".join(rows) + "\n</ol>"


def daily_candidates(items):
    """First verse block of each Haripath section, in order — the pool for
    the daily reading rotation (one per day, by day-of-year). A Haripath
    block is usually the whole section (4 abhangs), so one day = one भाग."""
    cands, seen = [], set()
    for it in items:
        if it["kind"] == "verse" and it.get("section") and it["section"] not in seen:
            seen.add(it["section"])
            cands.append(it)
    return cands


def today_caption(section: str) -> str:
    """'हरिपाठ — भाग एक.' (ध्यान / समापन भजन are not भाग)."""
    if section in ("ध्यान", "समापन भजन", "भजन"):
        return f"हरिपाठ — {section}."
    return f"हरिपाठ — भाग {section}."


# Block counts = ovis + Gita slokas + 1 trailing block (chapter-end line).
# They rose in Nov 2026 when the ''' wikitext wrappers were stripped:
# wrapped sloka lines previously failed CLOSE_NUMBER, so slokas were
# not counted at all. A1 275+47+1, A2 375+72+1, A3 276+43+1,
# A4 225+42+1, A5 180+29+1, A6 496+47+1 (Wikisource skips ovi 328; standard
# count 497), A8 271+28+1 (271 ovis ॥१॥–॥२७१॥, 28 Gita slokas, 1 trailing
# chapter-end line; standard count 271). A9 535+32+1, A10 335+43+1,
# A11 708+56+1, A12 247+21+1, A14 415+28+1, A15 599+21+1,
# A16 473+25+1, A17 433+29+1, A18 1811+84+1 (1811th ovi is the colophon;
# audio count 1810 excludes it). A13 HELD: Wikisource has 1151 ovis, 17 missing
# (10–26); needs OCR from a PD printed edition. Dasbodh Dashak 1: 326 ovis + 2 header blocks
# + 10 samas-end blocks + 1 closing block − 2 merges (S2 ovi 5 and
# S5 ovi 9 have no number markers in the OCR, so each merges into the
# following verse block). Dasbodh Dashak 2: 469 ovis + 2 header blocks
# + 10 samas-end blocks + 1 closing block − 2 merges (S1 ovi 64 and
# S2 ovi 34 have no number markers in the OCR). Bhavarth Adhyay 1: 119 ovis
# + 2 opening slokas + 1 colophon block + 1 closing count line = 123.
# Amritanubhav ch.3: 33 ovis + 1 closing line (title lines merge into
# ovi 1) = 34. Namdev Abhanggatha: 100 abhangs − 1 merge (abhang 82 ends
# mid-verse on the Wikisource page itself, no closing marker, so it merges
# into abhang 83's block) = 99. Gondavalekar Pravachane: each day is one
# ## section = 1 block, so the count is the days in the month (Feb 29 —
# the leap day is included); no mid-day CLOSE_NUMBER splits were found.
EXPECTED = {"haripath": None, "pasaydan": 9, "changdev-pasashti": 65,
            "manache-shlok": 205,
            "dnyaneshwari-adhyay-1": 323, "dnyaneshwari-adhyay-2": 448,
            "dnyaneshwari-adhyay-3": 320, "dnyaneshwari-adhyay-4": 268,
            "dnyaneshwari-adhyay-5": 210, "dnyaneshwari-adhyay-6": 544,
            "dnyaneshwari-adhyay-8": 300, "dnyaneshwari-adhyay-9": 568,
            "dnyaneshwari-adhyay-10": 379, "dnyaneshwari-adhyay-11": 765,
            "dnyaneshwari-adhyay-12": 269, "dnyaneshwari-adhyay-14": 444,
            "dnyaneshwari-adhyay-15": 621, "dnyaneshwari-adhyay-16": 499,
            "dnyaneshwari-adhyay-17": 463, "dnyaneshwari-adhyay-18": 1896,
            "dasbodh-dashak-1": 337,
            "dasbodh-dashak-2": 480, "dasbodh-dashak-3": 597, "dasbodh-dashak-4": 308, "dasbodh-dashak-5": 585, "dasbodh-dashak-6": 428, "dasbodh-dashak-7": 583, "dasbodh-dashak-8": 656, "dasbodh-dashak-9": 439, "dasbodh-dashak-10": 367, "dasbodh-dashak-11": 299, "dasbodh-dashak-12": 306, "dasbodh-dashak-13": 312, "bhavarth-ramayan-adhyay-1": 123,
            "amritanubhav-ch-1": 70, "amritanubhav-ch-3": 34,
            "amritanubhav-ch-4": 44, "namdev-abhanggatha": 99,
            "kanhopatra-aga-vaikunthichya-raya": 4,
            "kanhopatra-nako-devraya-anta-ata-pahu": 4,
            "gondavalekar-pravachane-january": 31,
            "gondavalekar-pravachane-february": 29,
            "gondavalekar-pravachane-march": 31,
            "gondavalekar-pravachane-april": 30,
            "gondavalekar-pravachane-may": 31,
            "gondavalekar-pravachane-june": 30,
            "gondavalekar-pravachane-july": 31,
            "gondavalekar-pravachane-august": 31,
            "gondavalekar-pravachane-september": 30,
            "gondavalekar-pravachane-october": 31,
            "gondavalekar-pravachane-november": 30,
            "gondavalekar-pravachane-december": 31}


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
<!-- ?v=2 cache-busts the assets on each deploy: without it a reader's
     browser can keep the previous reader.js/style.css after a push and
     new controls (e.g. jump-to-verse) silently do nothing. Bump the
     number whenever either file changes. -->
<link rel="stylesheet" href="{prefix}assets/style.css?v=2">
<script src="{prefix}assets/reader.js?v=2" defer></script>
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


def reading_page(work, items, verses, prev_work, next_work, prefix: str, siblings=None) -> str:
    count = len(verses)
    series = SERIES_BY_KEY[series_key(work["slug"])]
    crumbs = [("नित्यपाठ" if work["kind"] == "nitya" else "ग्रंथ",
               f"{prefix}{'nitya' if work['kind'] == 'nitya' else 'granth'}/index.html")]
    if work["kind"] == "granth" and series["index"]:
        crumbs.append((series["title"], f"{prefix}{series['index']}"))
    crumbs.append((work["title"], None))
    head = [breadcrumb(prefix, crumbs),
            f"<h1>{esc(work['title'])}</h1>",
            f"<p class=\"byline\">{esc(work['author'])} · {dev_num(count)} {work['unit']} · "
            f"मूळ ग्रंथ</p>",
            "<p class=\"source-line\">स्रोत, परवाना व तपासणीची स्थिती — "
            f"खाली स्रोत विभाग पहा. या पानावरील मजकूर तपासणीच्या प्रतीक्षेत आहे; "
            "चूक आढळल्यास कृपया नोंदवा.</p>"]
    if siblings and len(siblings) > 1:
        links = []
        for sib in siblings:
            if sib["slug"] == work["slug"]:
                links.append(f'<span class="cur">{esc(sib["short"])}</span>')
            else:
                links.append(f'<a href="{prefix}{sib["path"]}/index.html">{esc(sib["short"])}</a>')
        head.append('<nav class="siblings" aria-label="या ग्रंथातील भाग">'
                    '<span class="sib-label">या ग्रंथातील भाग:</span> ' + " ".join(links) + "</nav>")
    # Jump to a verse by its displayed number (॥N॥ as printed on the page).
    # Works with JS off? No — without JS it is inert, reading still works.
    head.append(f'<p class="jump"><label for="jump-n">{work["unit"]} क्रमांकावर जा:</label> '
                f'<input id="jump-n" type="number" min="1" max="{count}" inputmode="numeric"> '
                f'<button id="jump-go" type="button">जा</button></p>')
    head.append(share_link(work["title"], SITE_URL + work["path"] + "/"))
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
    body = ['<div class="read-progress" id="read-progress"></div>',
            "\n".join(head)]
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

    # ---- reading pages (prev/next within the same series, so an adhyay
    # leads to the next adhyay of the same granth, not to another granth)
    for work in WORKS:
        items, verses = loaded[work["slug"]]
        sibs = series_works(series_key(work["slug"]))
        j = sibs.index(work)
        prev_w = sibs[j - 1] if j > 0 else None
        next_w = sibs[j + 1] if j + 1 < len(sibs) else None
        depth = len(work["path"].split("/"))
        prefix = "../" * depth
        write(ROOT / work["path"] / "index.html",
              reading_page(work, items, verses, prev_w, next_w, prefix, sibs))

    # ---- series pages (one per parent work with published parts)
    for series in SERIES:
        if series["key"] == "nitya" or not series["index"]:
            continue
        works = series_works(series["key"])
        if not works:
            continue
        depth = len(Path(series["index"]).parts) - 1
        prefix = "../" * depth
        body = (breadcrumb(prefix, [("ग्रंथ", f"{prefix}granth/index.html"),
                                     (series["title"], None)])
                + f"<h1>{esc(series['title'])}</h1>"
                + f"<p>{esc(series['blurb'])}</p>")
        if series.get("plan"):
            body += f'<p class="plan">वाचन योजना — {esc(series["plan"])}</p>'
        body += toc_list(prefix, works, loaded)
        if series["upcoming"]:
            body += f'<p class="upcoming">येत आहे — {esc(series["upcoming"])}</p>'
        write(ROOT / series["index"], page(
            prefix, series["title"], f"{series['title']} — {series['blurb']}",
            body, url=series["index"]))

    # ---- granth index (series cards; chapter lists live on series pages)
    nitya = [w for w in WORKS if w["kind"] == "nitya"]
    granth_cards = "\n".join(
        series_card("../", s, loaded)
        for s in SERIES if s["key"] != "nitya")
    write(ROOT / "granth" / "index.html", page(
        "../", "ग्रंथ", "संतकृपा ग्रंथसूची — मूळ ग्रंथ.",
        breadcrumb("../", [("ग्रंथ", None)])
        + "<h1>ग्रंथ</h1>"
        + "<p>मूळ ग्रंथच — भाष्य, अर्थ किंवा भाषांतर नाही. प्रत्येक ग्रंथाचे अध्याय "
        "त्याच्या स्वतःच्या पानावर आहेत; स्रोत, परवाना व तपासणीची स्थिती प्रत्येक "
        "कृतीच्या पानावर दिली आहे. रिकामी पाने प्रसिद्ध केली जात नाहीत.</p>"
        + f'<div class="cards">{granth_cards}</div>',
        url="granth/index.html"))

    # ---- nitya index (same TOC form as the series pages)
    write(ROOT / "nitya" / "index.html", page(
        "../", "नित्यपाठ", "रोजच्या पाठासाठी — हरिपाठ, पसायदान.",
        breadcrumb("../", [("नित्यपाठ", None)])
        + "<h1>नित्यपाठ</h1>"
        + "<p>रोज वाचण्यासाठी — हरिपाठ व पसायदान. एका बैठकीत वाचता येण्याइतके लहान.</p>"
        + toc_list("../", nitya, loaded),
        url="nitya/index.html"))

    # ---- home (doorway, not catalogue: today's reading, start-here,
    # compact series cards; chapter lists live on the series pages)
    hp_items, hp_verses = loaded["haripath"]
    cands = daily_candidates(hp_items)
    doy = date.today().timetuple().tm_yday
    today = cands[(doy - 1) % len(cands)]
    today_html = verse_html(WORKS[0], today, "")
    # Same pool as JSON so reader.js can rotate by the visitor's own date;
    # without JS the server-picked verse (build day) stays.
    today_json = json.dumps(
        [{"section": c["section"], "number": c["number"],
          "marker": verse_marker(c["lines"]), "lines": c["lines"]} for c in cands],
        ensure_ascii=False)
    home_cards = "\n".join(
        series_card("", s, loaded)
        for s in SERIES if series_works(s["key"]))
    home_body = (
        '<section class="hero">'
        '<h1>॥ संतकृपा ॥</h1>'
        '<p class="tagline">मराठी संतसाहित्य — मूळ ग्रंथ, मोफत, स्रोतासह.</p>'
        '<div class="actions">'
        '<a class="big" href="nitya/haripath/index.html">आजचा हरिपाठ वाचा →</a>'
        '<a class="big ghost" href="granth/index.html">ग्रंथ शोधा</a>'
        '</div></section>'
        '<section><h2>आजचे वाचन</h2>'
        f'<p><span id="today-cap">{esc(today_caption(today["section"]))}</span> पूर्ण हरिपाठ '
        '<a href="nitya/haripath/index.html">येथे वाचा</a>.</p>'
        f'<div id="today">{today_html}</div>'
        f'<script type="application/json" id="today-data">{today_json}</script></section>'
        '<section><h2>सुरुवात कोठून करावी?</h2>'
        '<div class="cards">'
        '<article class="card"><h3><a href="nitya/haripath/index.html">रोजचा पाठ</a></h3>'
        '<p>दररोज सकाळी — हरिपाठ व पसायदान.</p></article>'
        '<article class="card"><h3><a href="granth/manache-shlok/index.html">पहिला ग्रंथ</a></h3>'
        '<p>लहान व सोपा — मनाचे २०५ श्लोक.</p></article>'
        '<article class="card"><h3><a href="granth/dnyaneshwari-adhyay-1/index.html">खोलवर जा</a></h3>'
        '<p>ज्ञानेश्वरी — अध्याय पहिला.</p></article>'
        '</div></section>'
        '<section><h2><a href="granth/index.html">ग्रंथ</a></h2>'
        f'<div class="cards">{home_cards}</div></section>'
        + '<section><h2>हे संकेतस्थळ कसे आहे</h2>'
        '<p>संतकृपा ही मराठी संतांच्या मूळ ग्रंथांचे मुक्त वाचनालय आहे. '
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

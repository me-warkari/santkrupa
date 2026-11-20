# दासबोध — दशक दुसरा — SOURCE

- Work: दासबोध, दशक दुसरा (मूर्खलक्षणनाम), १० समास, ४६९ ओव्या
- Author: समर्थ रामदास (Samarth Ramdas, 1608–1682) — public domain
- Source: archive.org item dasbodh-samarth-ramdas, scan (calibre-made PDF, 533 pages); Dashak 2 = PDF pages 34–64
  - https://archive.org/details/dasbodh-samarth-ramdas
- OCR class: (c) scan OCR — Tesseract mar+san+eng at 300 DPI, run on tempsystem 2026-11-20; Devanagari ratio 78–84% per page (mostly 79–81%). The PDF's embedded text layer is garbled (conjuncts dropped) and was not used.
- Proofing: NEEDED — published with a proofing disclaimer; no human proofreader has checked this text yet. The text may contain errors.
- Licence for this text in santkrupa: Public Domain (author died 1682)
- Do NOT use: text from any source that does not permit reuse; modern commentary.

- Mechanical cleanup 2026-11-20 (tempsystem, clean_dasbodh.py v2): 444 ASCII pipe characters normalized (|→।, ||→॥); 4 isolated ovi-number misreads corrected only where the sequence resumes immediately (S1 ॥२९॥→॥२१॥; S2 ॥३९॥→॥३१॥; S4 ॥१९॥→॥११॥; S9 ॥६॥→॥४॥); page markers, stray "_" lines and blank lines dropped.
- Manual fix (same rule, regex miss): S9 ovi 15 read ॥९५॥ with trailing junk "४1 वग" — the cleaner's trailing-marker regex missed it because junk followed the marker. Sequence 14, [15], 16 and the १→९ misread pattern prove 15; corrected to ॥१५॥ and the trailing junk stripped. Applied identically to the tempsystem cleaned file and this file.
- Samas-end suffixes: the cleaner's SAMAS_END regex expects a "१." prefix (Dashak 1), so Dashak 2's "२. N" suffixes (e.g. "समास पहिला ॥१॥२. १") were not stripped and the build counted 479. Stripped all 10 suffixes (same treatment as Dashak 1), identically on tempsystem and here; final file sha256 552e59fb…; build count 480, no mismatch.
- Known issues awaiting proofing: 2 ovi-number markers are missing in the OCR (S1 ovi 64 — the line reads "तो येक मूर्ख esl" with no number; S2 ovi 34 — the line reads "चुकुरपणें 113811" with no number — each merges into the following verse block in the built page); the Sanskrit slokas in S3 and S5 have no numbers and merge into the following ovi blocks (S3 sloka → ovi 4, S5 sloka → ovi 3); 32 lines contain Latin-letter OCR junk left exactly as read (e.g. S1 ovi 3 "AKER", S1 ovi 10 "PAA", S9 ovi 25 "Geant", S10 ovi 11 "var वग", S10 ovi 20 "var तुक्य") — these are OCR errors, not text; the two "var …" lines in S10 are stray junk lines inside their ovis (their markers ॥११॥ and ॥२०॥ are present on the following lines); other unflagged misreads remain. Proof against a printed edition before treating any line as final.
- Builder: 480 verse blocks (469 ovis + 2 header blocks + 10 समास-end blocks + 1 closing block − 2 merges from the missing markers).
- Disclaimer on the reading page: "ही आवृत्ती तपासणी बाकी आहे — मजकुरात चुका असू शकतात. चूक आढळल्यास “चूक नोंदवा” वापरा."

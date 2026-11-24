# Changelog

## 0.9.1 — 2026-11-24

- `head.sane` rule card: a wrong magic number is a trace of a hand edit, not a common fault; it is refused by OTS but registered by macOS CoreText (tested), so the card no longer says that systems refuse it. Example with a checksum written at the wrong offset.

## 0.9.0 — 2026-11-24

- New preset **Installs in the operating system** (Engineer level): only what decides whether a file is accepted and named — the container, required tables, outline type, glyph counts, cmap, checksums, embedding bits, OTS and the name records. Not menu order, rendering or conflicts with installed fonts.
- 8 new checks (category A, 64 in all): `sfnt.header` (version tag, sorted directory, tables inside the file, alignment, overlaps), `sfnt.required_tables`, `sfnt.outline_match` (version tag, maxp and outline table agree; CFF matrix), `head.sane`, `maxp.counts` (hmtx, loca, CharStrings and post agree with numGlyphs), `cmap.usable` (a Windows Unicode subtable, existing glyphs, a space), `sfnt.checksums`, `os2.fstype`.
- A file the font library cannot open used to disappear from the report (every check was "not applicable"). Checks that read only the file's bytes (`raw`) now run on it: `sfnt.header`, `sfnt.required_tables`, `sfnt.checksums`.
- A damaged `hmtx` no longer stops the run while outline keys are computed.

## 0.8.1 — 2026-11-24

- Fixed `glyphs.mark_widths`: spacing accents (breve, caron, circumflex, grave, macron, tilde, ring… U+02D8, U+02C7, U+0060…) were reported as combining marks only because GDEF lists them as marks. A GDEF mark that an ordinary character maps to is no longer reported. A glyph shared by a spacing and a combining character is still reported, now with the combining code point (e.g. `grave (U+0300) 216`).

## 0.8.0 — 2026-11-18

Speed. Measured with `tests/perf.py` in headless Chromium (CDNs are the real ones).

- One file instead of 68: the engine (`core/`, rules, data) is served as `core.bundle.json`, hashed; own requests at start went from 94 to 4. `./serve.sh` builds it on the fly.
- Nothing is installed from PyPI at check time: openpyxl and munkres are wheels on the site (`wheels.json`), installed with `micropip` without dependency lookup; PyPI requests during checks went from 9 to 0. The workbook is built when you ask for `report.xlsx`, not at every check.
- Offline: a service worker keeps the site and the Pyodide/HarfBuzz files (CDN cache-first, own files network-first). After the first visit the page starts without a network. Not registered on localhost (set `localStorage.fontqa:sw = "1"` to try it).
- Progress: the engine reports its stage (reading, inspecting, attachments, report) and the page shows an estimate of the time left and the percentage in the tab title.
- Attachment pages (glyph grids, GSUB, proofs, menus) are built when you open them, not at every check: a check of two fonts with attachments went from about 20 s to 0.4 s.
- Cold start 6.6 → 4.6 s, first Designer check 4.4 → 1.7 s, 60 small files 2.0 → 1.2 s.

## 0.7.0 — 2026-11-18

- Coverage section: tabs **Character sets** and **Languages**, the same list of bars with filters, what to add and copy buttons.
- Character sets: 29 instead of 7 — ASCII, ISO 8859-1, Windows code pages 1250–1258, Adobe Latin 1–5 and the Google Fonts glyphsets (Latin Kernel / Core / Plus / African / Vietnamese, Cyrillic Core / Plus / Pro, Greek Core / Plus / Pro, Arabic Core / Plus). Filters: complete / with missing / under 10 % short; script; source; sort by coverage, size or name. The copy buttons above the list give the union for the sets shown.
- Data: `core/data/charsets.json` is now a compact range format with metadata, built by `scripts/build_charsets.py`; the Google Fonts sets are Apache-2.0 (`LICENSE-GLYPHSETS.txt`). `core/charsets.py` reads it and computes coverage.
- `issues.json`: `charsets` (groups of styles, `have` per set, `missing` as ranges) replaces `coverage`. The xlsx Coverage sheet is one row per style group and set, with the share and the code points to add.
- The detail tables are written compactly (40 rows each, the buttons copy all): a Squishy Blob report went from 512 to 326 KB.
- Row data carries only the characters and the AGL names; code points and `uniXXXX` names are derived in the page.

## 0.6.0 — 2026-11-17

- Languages in the report are a list of bars: every language the font supports, and every language of which it has at least 40 % of the letters, each with its share and count (e.g. Hungarian 80,6 % — 29/36), after Font Analyzer's Languages tab.
- Filters: supported / with missing letters / under 10 % short; script; where the language is spoken (continent, from CLDR: a territory with 100 000 speakers or more); sort by coverage, speakers or name.
- A language with missing letters opens a table of what to add — code point, Unicode name, glyph name (AGL, else uniXXXX) — with buttons to copy the glyph names (for Glyphs' Add Glyphs), the Unicode values or the characters. The same buttons above the list copy the union for the languages the filters leave visible: the letters that open the most languages.
- `issues.json`: `languages.groups[*].partial` (with `need`, `have`, `total`) replaces `almost`; names carry `regions` and `letters`. The xlsx Languages sheet has the share and the code points to add.
- The report frame may write to the clipboard (`allow="clipboard-write"`); where it cannot, the copy falls back to a selection copy.

## 0.5.0 — 2026-11-17

- Languages: the report has a Languages section (and an xlsx sheet) listing the languages each style supports — all everyday letters, upper and lower case — and those one to three letters short, with the letters to add. Data: Unicode CLDR 49 exemplar characters and territory population, 248 languages and scripts, built by `scripts/build_languages.py` into `core/data/languages.json` (104 KB). `issues.json` has `languages`.
- New check `charset.languages_almost` (Designer, Harmless): languages with a million speakers or more that are one to three letters short. 56 checks, 21 at the Designer level.
- A letter without its own glyph counts when its base and combining accent are there and the font has a `mark` feature.
- Fixed: a check with only a harmless finding was listed under Passed and Flagged at once.

## 0.4.0 — 2026-11-16

- Summary table: **Flagged** (checks that gave findings, with links to them) and **Passed** next to each other; checks not performed or not applicable are listed under the table. `summary.by_category[*].passed` and `.flagged` are new; `confirmed` stays one version as an alias of `passed`.
- Presets: `--preset differences|names|tables|metrics|glyphs|outlines|layout|variable|lineage|release|validators`, `./check.sh rules --presets`, and a selector with a list of individual checks on the page. A partial run is marked in the report header, a note, the xlsx and the file name (`…-partial-…`); `issues.json` has `scope`.
- Page: the level and the checks are chosen before the fonts; Probes and Compare with terminal moved under Developer; reference fonts are optional and said so; the run is automatic for up to 40 files once a level has been chosen (never Font Bakery).
- The report is a tab as tall as its content (no inner scroll), with Inventory and Test page as the other tabs, "Open in new tab", the page's theme, and links inside it that scroll the page.
- Fixed: a partial run reported menu symptoms of checks that did not run.
- Fixed: the order of checks depended on which module was imported first, so the terminal and the browser listed them differently; checks are sorted by category and id.

## 0.3.0 — 2026-11-16

- Tests: every check has a font broken for it and must fire on it; a clean set (TrueType, CFF, features, a variable font) must stay silent. Fonts are generated by code, none are stored.
- Fixed: a variable font whose default master had the same outlines as a static font was skipped by the outline checks for variable fonts (master compatibility).
- The browser cache of font facts is keyed by a fingerprint of the code that reads fonts, so it can no longer go stale after an update.
- Weight and width words written apart are recognised (Extra Light, Semi Condensed).
- Two levels decide what is checked: Designer (20 drawing checks) and Engineer (all 55).
- A rule card for every check; the Rules page; reports quote the cards.

## 0.2.0 — 2026-10-28

- Inspection with HTML, xlsx and JSON reports; variable-font and lineage checks; menu simulation and checklist.

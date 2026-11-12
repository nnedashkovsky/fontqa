# Font QA

Inspection of built fonts in the browser. Drop fonts or a whole delivery folder on the page: it lists what you got, runs 55 checks and writes a report in HTML, xlsx and JSON.

**Fonts never leave your machine.** The checks are Python (fontTools) running inside the browser through Pyodide; nothing is uploaded.

## Use it

Open the page, drop OTF / TTF / WOFF / WOFF2 files or a folder, press **Run inspection**, download the report.

The first visit takes 10–40 s while the browser loads Python, fontTools and HarfBuzz from a CDN; after that they come from the cache.

A dropped folder keeps its structure, so App / Desktop / Web lines of the same family are recognised by folder names.

## What you get

- `report.html` — findings with filters and search, light and dark themes, prints to PDF.
- `report.xlsx` — the same findings as a worksheet; Status and Comment columns are for your notes.
- `issues.json` — the source of both reports; two runs can be compared.
- Attachments, without judgements:
  - `glyphs-<style>.html` — every glyph next to your reference fonts; glyphs that differ in weight or width more than usual are marked;
  - `gsub.html` — every GSUB substitution, before and after, plus a GPOS summary;
  - `proofs.html` — waterfall, spacing and kerning strings;
  - `menus.html` — how the fonts will appear in Windows (GDI, WWS) and macOS / Font Book menus, predicted from the tables, and a checklist for checking it on a real system.

### Levels of detail

The report and the Rules page have a switch: **Beginner** (what is wrong, why it matters, what to do), **Designer** (the default: plus measured and expected values, files, glyphs and the summary tables) and **Engineer** (plus how each check measures, check ids, the fonts table and the inputs). `report.html?level=beginner` opens a report at a given level.

### Rules

Every check is explained in a card in `rules/<check id>.md`: what it checks, why it matters, how it is checked, when it does not apply, how to fix it, an example and sources. The Rules page (`/rules/`) is built from these cards, and the report quotes them. `./check.sh rules` checks that the cards agree with the code.

### How to read a finding

Every finding has three marks:
- **action** — Fix, Confirm (is this intended?) or Harmless;
- **severity** — High, Medium or Low, by the harm to the user;
- **result** — × does not match, △ needs confirmation, ○ matches, — not applicable.

The same finding in ten files is one row with the file list. Each row says what was measured and what was expected, the basis, the glyphs, the direction of the fix and, where known, the symptom a user will see.

**Categories:** A environment and installation · C character set and glyphs · D OpenType layout · E external validators · F table values, names and consistency between lines · G variable fonts · R release readiness.

## What is checked

- **Names:** the GDI name length (31), RIBBI and style bits, WWS names, localized records, unique names (ID 25 and PostScript names of instances too), required records, version, Mac records, family consistency, the `meta` table.
- **Table values:** weight and width classes against style names, vertical metrics across the family, clipping by win metrics, line spacing on Mac and Windows, USE_TYPO_METRICS, x-height and cap height against the drawn glyphs, Unicode and code page bits, slant and caret, hinting.
- **Character set:** the same set in every style, the Western European store minimum, `.notdef`, empty mapped glyphs, space widths, zero-width marks, tabular figures, widths that differ by 1–2 units between styles.
- **Outlines:** zero-length segments, nodes on extremes, fractional coordinates in CFF.
- **OpenType:** scripts registered in GSUB/GPOS, unreachable glyphs, kerning pairs hidden behind an earlier subtable, a legacy `kern` table for Word, `aalt` coverage, `mark`.
- **Validators:** OTS (the browser itself) and, optionally, Font Bakery (universal profile).
- **Release:** formats, file name = PostScript name, copyright and license, version.
- **Variable fonts:** the default instance name, unique instance names, STAT, HVAR, master compatibility, and every named instance against the static font of the same style (widths, bounds, kerning shaped by HarfBuzz).
- **Font lines:** copies of one style in App / Desktop / Web, TTF / WOFF / WOFF2 share the glyph set, cmap, widths, outlines, metrics and layout behaviour.

Each check lives in `core/checks/` with its category, basis and fix next to the code.

## Run locally

Needs Python 3.11+.

```bash
pip install -r requirements.txt
./serve.sh                # page on http://127.0.0.1:8765/web/
```

Optional:

```bash
./serve.sh --mount name=~/Downloads/Delivery   # then open /web/?load=mnt/name
FONTQA_REFS=~/RefFonts ./serve.sh                # built-in reference fonts for the glyph grid
```

The same inspection in the terminal:

```bash
./check.sh inspect <folder or files…> --out reports/<name>
```

Flags: `--fontbakery`, `--ref <font>` (repeatable), `--checks vf.,lineage.` (only these prefixes), `--no-attachments`, `--json-only`.

Compare two runs (or the browser against the terminal):

```bash
./check.sh compare old/issues.json new/issues.json
```

## Layout

- `core/` — the Python core, the same for terminal and browser: font facts, checks, inspection, reports, menu simulation.
- `web/` — the page and the worker that runs Pyodide and HarfBuzz off the main thread.
- `serve.py` — local server; `check.sh` — terminal entry; `build_site.py` — static build for GitHub Pages.

`core/data/charsets.json` includes Adobe Latin 1–5 from adobe-type-tools (MIT).

The tool only reads fonts and never writes to them.

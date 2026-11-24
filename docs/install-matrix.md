# Where a fault breaks the font

Nine generated fonts, one fault each (`python scripts/make_install_tests.py` writes them). The results below are what was
observed, not what the spec says; an empty cell means not tested. Update the table when a system is tested again.

| File | Fault | macOS: installed | Windows: installed | macOS: CoreText registers | Chrome (OTS) loads | Font QA |
|---|---|---|---|---|---|---|
| `00-good.ttf` | none | | | yes | yes | silent |
| `01-bad-magic.ttf` | `head.magicNumber` is 0 | yes | yes | yes | **no** | `head.sane` · Harmless |
| `02-no-name-table.ttf` | no `name` table | **no** | **no** | yes | **no** | `sfnt.required_tables`, `names.required` · Fix |
| `03-no-cmap-table.ttf` | no `cmap` table | **no** | **no** | yes | **no** | `sfnt.required_tables`, `sfnt.header` · Fix |
| `04-numglyphs-wrong.ttf` | `maxp.numGlyphs` 999, tables hold 220 | **no** | **no** | yes | **no** | `maxp.counts` · Fix |
| `05-truncated.ttf` | file cut off in its last table | **no** | **no** | yes | **no** | `sfnt.header` · Fix |
| `06-bad-version-tag.ttf` | unknown version tag `XXXX` | **no** | **no** | **no** | **no** | `sfnt.header` · Fix |
| `07-bad-checksum.ttf` | a table edited, checksums not recomputed | yes | yes | yes | **no** | `sfnt.checksums` · Harmless |
| `08-glyf-with-OTTO-tag.otf` | version tag `OTTO` over TrueType outlines | **no** | **no** | **no** | yes | `sfnt.outline_match` · Fix |

**How to read it.**

- *macOS: installed* and *Windows: installed* are what a person saw when installing the file (2026-11-24).
- *CoreText registers* is the API `CTFontManagerRegisterFontsForURL` with process scope, run by a script; it installs nothing. It is far more tolerant than an installation: it accepted every file except the two with a wrong version tag.
- *Chrome (OTS)* is a headless Chromium loading the file as a web font. It refused `07` too; why was not investigated (the test overwrote the first byte of the `name` table, so the table itself is damaged, not only its checksum).
- The two "installed" columns tell whether a fault blocks installation. `01` and `07` install on both systems, which is why `head.sane` (wrong magic number) and `sfnt.checksums` are Harmless and the other faults are Fix.

**Open.** `00-good.ttf` was not reported; it is the control and is assumed to install.

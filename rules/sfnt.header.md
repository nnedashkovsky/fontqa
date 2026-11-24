---
id: sfnt.header
title: The sfnt header and table directory are well formed
summary: The file opens, its version tag is known, and its table directory is sorted, inside the file, aligned and without overlaps.
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files, including files the font library cannot open.
related: sfnt.required_tables, sfnt.checksums, external.ots
sources:
  - OpenType spec, font file organization | https://learn.microsoft.com/en-us/typography/opentype/spec/otff
  - OpenType Sanitizer | https://github.com/khaledhosny/ots
---

## What it checks

A TTF or OTF file starts with a 12-byte header (the version tag, the number of tables and three search fields), followed by a directory with one 16-byte record per table: its tag, checksum, offset and length. The system finds every table through this directory.

## Why it matters

If the directory is wrong, the system either refuses the file or reads one table's bytes as another's. The font then does not install, is listed as damaged, or draws nothing. Such errors almost always come from editing the file by hand or from a damaged copy, a cut-off download or a sync tool; a font compiler does not produce them.

## How it is checked

The directory is read from the file itself, not through a font library, so a file that cannot be opened is still examined. These are reported:

1. An unknown version tag (known: `00010000` for TrueType, `OTTO` for CFF, `true`).
2. A directory shorter than the number of tables.
3. Search fields that do not match the number of tables (medium).
4. The same tag twice.
5. Tags not in ascending order (medium).
6. A table that reaches past the end of the file.
7. Overlapping tables (medium).
8. A table that does not start on a 4-byte boundary (low).
9. A file the font library cannot open although the directory looks fine.

## When it does not apply

- Web fonts (WOFF, WOFF2) have their own container and are not checked here.

## How to fix

Do not edit the file. Export the font again from the source, or re-save it with the font compiler (fontTools, fontmake, Glyphs), which writes a correct directory. If the file came from a download or a sync folder, copy it again from the original.

## Example

| Finding | Meaning |
|---|---|
| Tables reach past the end of the file: post | The file was cut off; the last table is incomplete. |
| Table tags are not in ascending order | The directory was edited or built by a tool that does not sort it. |

---
id: sfnt.checksums
title: Table checksums are correct
summary: Every table matches the checksum in the directory, and head.checkSumAdjustment matches the whole file.
category: A
level: engineer
severity: low
action: ok
applies: TTF and OTF files, including files the font library cannot open.
related: sfnt.header, external.ots
sources:
  - OpenType spec, calculating checksums | https://learn.microsoft.com/en-us/typography/opentype/spec/otff#calculating-checksums
---

## What it checks

Each table in the directory has a checksum: the sum of its bytes read as 32-bit numbers. The `head` table also stores `checkSumAdjustment`, a value that makes the sum of the whole file equal `0xB1B0AFBA`.

## Why it matters

A checksum that no longer matches means the table was changed after the font was saved: by a hand edit, a script that patched a table without re-saving the font, or a damaged copy. Font validators report it.

It does **not** stop the font from installing: a font with a wrong table checksum was installed on both macOS and Windows when tested, so this is reported as **Harmless**. What it tells you is that the file was edited outside the compiler, and that the edit itself deserves a look.

## How it is checked

The file is read and each table's checksum is computed (with `checkSumAdjustment` set to zero for `head`) and compared with the directory. Then the sum of the entire file is compared with `checkSumAdjustment`. The tables with a mismatch are listed.

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Re-save the font with the compiler (fontTools, fontmake, Glyphs export): it recomputes every checksum and the adjustment. Never patch a table inside a finished file.

## Example

| Finding | Meaning |
|---|---|
| Checksum does not match for name | The name table was edited after the font was saved. |

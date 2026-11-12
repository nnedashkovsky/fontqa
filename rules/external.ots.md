---
id: external.ots
title: Browsers accept the font (OTS)
summary: The OpenType Sanitizer — the check every browser runs on web fonts — accepts the file.
category: E
level: engineer
severity: high
action: fix
applies: All fonts, when OTS runs (in the browser: always; in the terminal: with the ots module).
related: external.fontbakery
sources:
  - OpenType Sanitizer (OTS) | https://github.com/khaledhosny/ots
---

## What it checks

Chrome and Firefox pass every web font through the **OpenType Sanitizer** before using it. OTS checks the tables of the font for errors and inconsistencies and rejects fonts it does not trust. The check runs the font through OTS and reports a rejection, with OTS's message.

## Why it matters

A rejected font is **not loaded** by the browser at all: the page silently shows the fallback font. The site looks wrong only for some visitors and only in some browsers, and nothing in the page code points at the font.

Desktop fonts are not sanitised, but a font OTS rejects usually has a real table error that can cause trouble elsewhere too.

## How it is checked

- **In the browser**, the page loads every font through the browser itself (the FontFace API). If the browser refuses it, that is OTS's verdict, and the browser's error is reported.
- **In the terminal**, the `ots` Python module runs the same sanitiser. Very large WOFF2 files are checked decompressed, because the command-line tool has a size limit that browsers do not.

## When it does not apply

Never skipped when OTS is available; in the terminal without the `ots` module, the check is listed as "not performed".

## How to fix

Fix the table that OTS names. Most rejections come from post-processing tools that left a table malformed or inconsistent (wrong lengths, offsets, glyph counts), or from rare tables that OTS does not accept. Re-export from the editor, then re-apply post-processing step by step to find the one that breaks it.

## Example

| File | OTS | |
|---|---|---|
| AcmeSans-Regular.woff2 | accepted | good |
| AcmeSans-Bold.woff2 | "GPOS: Failed to parse lookup 12" | bad: the browser shows the fallback font |

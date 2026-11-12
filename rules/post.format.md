---
id: post.format
title: Web fonts without glyph names
summary: TrueType web fonts can drop glyph names (post table format 3) — browsers never read them.
category: F
level: engineer
severity: low
action: ok
applies: TrueType-outline fonts in a Web folder.
related: release.formats
sources:
  - OpenType spec, post table | https://learn.microsoft.com/en-us/typography/opentype/spec/post
---

## What it checks

A TrueType font can store a name for every glyph (`post` table format 2), or no names (format 3). For web fonts the check notes when the names are kept.

## Why it matters

Browsers never use glyph names, so they only add bytes to every page load — a few kilobytes per font, more for large character sets. It does no harm in use, which is why the result is **Harmless**: it is an optimisation, not a defect.

Desktop fonts should keep their names: apps use them for copying text from PDFs and for glyph palettes.

## How it is checked

For TrueType fonts in a Web folder, the format of the `post` table is read; format 2 (with names) is reported.

## When it does not apply

- Desktop and App fonts.
- CFF-outline fonts (glyph names are stored in CFF).

## How to fix

Export the web build without glyph names (post format 3), for example by post-processing the web files with fontTools (set the post table's format to 3).

## Example

| File | post | |
|---|---|---|
| Web/AcmeSans-Regular.woff2 | 3.0 | good |
| Web/AcmeSans-Regular.woff2 | 2.0 | harmless: a few KB more |

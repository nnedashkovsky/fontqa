---
id: release.font_json
title: Promo facts (font.json) describe this build
summary: Optional. If you keep the facts for banners and store texts in a font.json file, its glyph and character counts and features match the fonts.
category: R
level: engineer
severity: medium
action: fix
applies: Only when a font.json is given (dropped on the page, or `--font-json` in the terminal).
related: release.formats
---

## What it checks

Some teams keep the numbers used in promotion — "1,200 glyphs", "supports 220 languages", "40 OpenType features" — in a `font.json` file next to the project, so that banners and store texts all take them from one place. This check compares that file with the fonts that are actually delivered.

For every style the file lists (by PostScript name), the build must have:

- a font with that PostScript name;
- the same number of glyphs;
- the same number of characters;
- the same OpenType features (GSUB), if the file lists them.

## Why it matters

The numbers on banners and in store descriptions are promises to customers. When the font grows or shrinks between versions and the promo facts are not updated, the store page says one thing and the font does another.

## How it is checked

The file is read as `{"facts": {"styles": [{"postscript", "glyphs", "unicodes", "features"}, …]}}`. Each style is matched with a delivered font by PostScript name and compared as listed above. Styles the build lacks, and every difference, are reported.

## When it does not apply

Without a font.json — which is the usual case. The check is listed as "not performed".

## How to fix

Regenerate font.json from the new build, then update the promo materials that use it.

## Example

| Style | font.json | Build | |
|---|---|---|---|
| AcmeSans-Bold | 1,204 glyphs | 1,204 | good |
| AcmeSans-Bold | 1,180 glyphs | 1,204 | bad: banners say 1,180 |

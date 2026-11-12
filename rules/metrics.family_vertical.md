---
id: metrics.family_vertical
title: Vertical metrics are the same across the family
summary: Every style of a family has the same UPM, line metrics (hhea, typo, win), USE_TYPO_METRICS setting and underline.
category: F
level: designer
severity: medium
action: fix
applies: Each family, per line (App, Desktop, Web), static and variable fonts separately; families of two styles or more.
related: metrics.win_clipping, charset.family_same
sources:
  - OpenType spec, OS/2 vertical metrics | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#sTypoAscender
  - OpenType spec, hhea | https://learn.microsoft.com/en-us/typography/opentype/spec/hhea
---

## What it checks

All styles of a family share one set of vertical metrics:

- units per em (UPM);
- `hhea` ascender, descender and line gap (used by macOS);
- `OS/2` typo ascender, descender and line gap (used by Windows apps and browsers that honour USE_TYPO_METRICS);
- `OS/2` win ascent and descent (used by Windows for clipping and in older apps for line spacing);
- the USE_TYPO_METRICS flag;
- underline position and thickness.

## Why it matters

Line spacing is calculated from these numbers. If Bold has a different ascender than Regular, then a paragraph where one word is bold gets a **taller line** around that word: lines jump. The same happens when a heading in one style and text in another must share a baseline grid.

Different underline values make the underline jump up and down between styles in one line (severity **low**).

## How it is checked

1. Fonts are grouped into families: the same family name, the same line (App, Desktop, Web), static and variable apart.
2. For each set of values above, the values of all styles are compared.
3. If they differ, the most common value is taken as expected, and the styles with other values are listed.

## When it does not apply

Families of one style.

## How to fix

Use one set of vertical metrics for the whole family. In Glyphs, give every master the same values (Font Info → Masters → custom parameters such as typoAscender, hheaAscender, winAscent…), or override them with the same values in every instance.

## Example

| Style | typo ascender / descender / gap | |
|---|---|---|
| Regular | 800 / −200 / 200 | |
| Bold | 800 / −200 / 200 | good |
| Black | 850 / −220 / 200 | bad: lines with a Black word are taller |

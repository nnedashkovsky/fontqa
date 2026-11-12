---
id: names.wws
title: WWS names for styles with extra words
summary: When the style name has words other than weight, width and slope (Display, Text, Dark…), IDs 21/22 are present and the WWS bit is off.
category: A
severity: low
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.ribbi
sources:
  - OpenType spec, name IDs 21 and 22 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
  - OpenType spec, OS/2.fsSelection bit 8 (WWS) | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fsselection
---

## What it checks

Some apps (the Windows font dialog of Notepad, apps built on DirectWrite) arrange a family on three axes only: **W**eight, **W**idth and **S**lope (WWS). A style name such as "Display Bold" or "Dark Condensed" contains a word that is none of those. For such styles the font must say how to split the name:

- ID 21 — the family including the extra words ("Acme Sans Display");
- ID 22 — the style with weight, width and slope only ("Bold");
- the WWS bit in `OS/2.fsSelection` is **off**, because the font is not WWS-clean on its own.

## Why it matters

Without IDs 21/22 the app guesses where the family ends. It either mixes Display and Text styles in one list, where two "Bold" entries appear, or it splits the family into extra rows with odd names.

The WWS bit claims "IDs 16/17 already follow the weight-width-slope model". If it is set on a style with extra words, apps trust it and skip their own grouping; the mistake then shows in every app that reads the bit.

## How it is checked

1. The style is ID 17 (or ID 2). It is split into words at spaces, hyphens and underscores.
2. Words known as weight (Thin … Black and abbreviations like Bd, Md, XBd), width (Condensed, Narrow, Expanded, Wide…) or slope (Italic, Oblique, Upright, Roman) are removed.
3. If anything is left — "Display", "Dark", "Text", "Rounded" — the font needs IDs 21 and 22. Missing IDs → **low**.
4. If, in addition, the WWS bit is set → **medium**: the font actively claims something false.

## When it does not apply

- Styles made only of weight, width and slope words ("Bold Condensed Italic").
- Web fonts.

## How to fix

1. Add ID 21 = family with the extra words, ID 22 = the weight/width/slope part of the style.
2. Clear fsSelection bit 8 (WWS) for these styles.
3. In Glyphs: add the WWS names via the instance custom parameters for name IDs 21 and 22 (or the Name Table Entry parameter), and make sure the WWS bit is not forced on.

## Example

| Style (ID 17) | Extra words | ID 21 | ID 22 | WWS bit |
|---|---|---|---|---|
| Bold Italic | — | not needed | not needed | may be on |
| Display Bold | Display | Acme Sans Display | Bold | off |
| Dark Condensed | Dark | Acme Sans Dark | Condensed | off |

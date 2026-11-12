---
id: glyphs.empty_mapped
title: Encoded characters have outlines
summary: Every character with a Unicode value has an outline, except spaces and invisible control characters.
category: C
level: designer
severity: high
action: fix
applies: All fonts.
related: glyphs.notdef, charset.family_same
sources:
  - Unicode, general categories (Zs, Cc, Cf) | https://www.unicode.org/reports/tr44/#General_Category_Values
---

## What it checks

A glyph that has a Unicode value but no outline: the font says "I have this character" and then draws nothing.

## Why it matters

When a font lacks a character, the system shows it from another font, so the text stays readable. When the font **claims** the character but the glyph is empty, the system trusts the font: the character disappears from the text and from print, with no fallback. The user sees a gap and usually does not understand why.

This happens with placeholder glyphs that were created and never drawn, or with outlines lost at export.

## How it is checked

- Every encoded glyph is checked once (a glyph used for several characters counts once).
- Characters that are expected to be empty are skipped: spaces, line and paragraph separators, control and format characters (Unicode categories Zs, Zl, Zp, Cc, Cf).
- A glyph with no outline and no components is reported.

## When it does not apply

- Spaces and invisible characters, as above.

## How to fix

Draw the glyph, or remove its Unicode value so that the system falls back to another font. The finding lists the empty glyphs by name and code.

## Example

| Glyph | Unicode | Outline | |
|---|---|---|---|
| Eng | U+014A | yes | good |
| rupeeIndian | U+20B9 | none | bad: ₹ prints nothing |

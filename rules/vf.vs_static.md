---
id: vf.vs_static
title: Named instances match the static fonts
summary: Each named instance of a variable font is the same as the static font of that style — widths, outlines and spacing of every pair.
category: G
level: designer
severity: medium
action: fix
applies: Deliveries that contain both a variable font and static fonts of the same styles in the same line.
related: vf.interpolation, layout.kern_shadowed
sources:
  - HarfBuzz, text shaping | https://harfbuzz.github.io/
---

## What it checks

When a family is delivered both as a variable font and as static fonts, the variable font's named instance "Bold" must set text exactly like the static "Bold". The check compares them:

- **advance widths** of every glyph, in every named instance;
- **outlines** (their bounding boxes) in the first, middle and last instance, and in every instance where a width differs;
- **spacing of pairs**: text is set with both fonts — every ASCII pair, plus every pair either font kerns — and the positions are compared.

## Why it matters

Users switch between the variable and the static fonts of a family: a designer uses the statics, the website uses the variable font; an app replaces one with the other. If they differ, **text reflows**: line breaks move, a headline that fitted no longer fits, a kerned pair in print is unkerned on the web.

Differences usually mean that the two were exported from different states of the source, or that kerning got lost in one of them (see hidden kerning pairs).

## How it is checked

1. Variable and static fonts are matched by style name within one line (App, Desktop, Web).
2. For each named instance, the instance is read directly from the variable font at its axis position and compared with the static font:
   - widths of every glyph must be equal;
   - outline bounding boxes may differ by up to **2 units** (rounding of components);
   - text is shaped with HarfBuzz, kerning on and ligatures off, and every glyph position must match.
3. Glyph substitutions that the variable font applies at certain axis positions (bracket layers in Glyphs) are taken into account.
4. For fonts with Chinese, Japanese or Korean glyphs, a sample is compared and the finding says how many.

## When it does not apply

- Deliveries without both kinds of font.
- A static font of another sub-family that only shares the style name.

## How to fix

Export the static and the variable fonts from the same source state, at the same time. If only kerning differs, look at how the variable font's kerning is split into subtables — pairs hidden behind an earlier subtable are the most common cause.

## Example

| Style | Glyph or pair | Static | Variable | |
|---|---|---|---|---|
| Bold | A width | 690 | 690 | good |
| Bold | f width | 402 | 404 | bad: text reflows |
| Bold | `&` + `Д` | −30 | 0 | bad: kerning lost in the variable font |

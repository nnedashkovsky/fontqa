---
id: glyphs.spaces
title: Space widths
summary: The no-break space is as wide as the space; zero-width characters have width 0; the figure space is as wide as a tabular figure.
category: C
level: designer
severity: medium
action: fix
applies: All fonts that have these characters.
related: glyphs.tabular
sources:
  - Unicode, U+00A0 NO-BREAK SPACE and the space characters | https://www.unicode.org/charts/PDF/U2000.pdf
---

## What it checks

Three kinds of space must have the widths Unicode gives them:

- **No-break space** (U+00A0) — the same width as the normal space (U+0020). It only differs in that a line cannot break at it.
- **Zero-width** characters (U+200B zero-width space, U+200C ZWNJ, U+200D ZWJ, U+2060 word joiner, U+FEFF) — width 0.
- **Figure space** (U+2007) — the width of a tabular digit.

## Why it matters

- Word processors insert no-break spaces automatically: in French before "?" and "!", between a number and its unit, after short words. If it is wider or narrower than the space, the text gets uneven gaps exactly in those places.
- Zero-width characters are inserted by keyboards and apps to control joining and line breaks. With a width, they leave visible gaps in the middle of words.
- The figure space is used to align numbers in columns; at the wrong width, columns go out of line.

## How it is checked

1. If both exist, the widths of U+0020 and U+00A0 are compared → **medium** if they differ.
2. Each of U+200B, U+200C, U+200D, U+2060, U+FEFF that exists must have width 0 → **low** otherwise.
3. If U+2007 and the digit 0 exist, the figure space is compared with the zero — the zero as the `tnum` feature produces it, if the font has one → **low** if they differ.

## When it does not apply

When the font does not have these characters.

## How to fix

Set the widths in the source. The simplest way for the no-break space: build `nbspace` from `space` as a component, so the two never drift apart.

## Example

| Character | Width | |
|---|---|---|
| space | 230 | |
| nbspace | 230 | good |
| nbspace | 460 | bad: double gaps in French text |
| zero-width joiner | 0 | good |
| figure space | 560 = tabular zero | good |

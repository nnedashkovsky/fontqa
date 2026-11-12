---
id: glyphs.notdef
title: .notdef is first and visible
summary: Glyph 0 is .notdef and has a visible outline.
category: C
level: designer
severity: medium
action: fix
applies: All fonts.
related: glyphs.empty_mapped
sources:
  - OpenType spec, recommendations for .notdef | https://learn.microsoft.com/en-us/typography/opentype/spec/recom#glyph-0-the-notdef-glyph
---

## What it checks

The first glyph of the font (glyph 0) must be `.notdef`, and it must be drawn — usually as an empty rectangle.

## Why it matters

Glyph 0 is what apps show when the text asks for a character the font does not have and no fallback happens. A visible box tells the user "this character is missing". If glyph 0 is something else, apps show that glyph instead — a letter in the wrong place. If `.notdef` is empty, missing characters vanish without a trace.

## How it is checked

1. The first name in the glyph order must be `.notdef`. Otherwise → **medium**.
2. If it is, it must have an outline. An empty `.notdef` → **low**.

## When it does not apply

Always applies.

## How to fix

Keep `.notdef` as the first glyph and draw a box in it — a rectangle about the size of a capital letter, often with a cross or a question mark inside.

## Example

| Glyph 0 | Outline | |
|---|---|---|
| .notdef | rectangle | good |
| .notdef | none | bad: missing characters disappear |
| space | — | bad: missing characters show as spaces |

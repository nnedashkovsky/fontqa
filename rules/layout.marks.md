---
id: layout.marks
title: Combining marks are positioned
summary: A font that has combining accents has a mark feature that places them on their letters.
category: D
level: designer
severity: medium
action: fix
applies: Fonts that encode combining marks (U+0300–U+036F).
related: glyphs.mark_widths
sources:
  - OpenType feature registry, mark | https://learn.microsoft.com/en-us/typography/opentype/spec/features_ko#tag-mark
---

## What it checks

If the font has combining accents (the characters U+0300–U+036F: combining acute, grave, dieresis…), it must also have the OpenType `mark` feature, which attaches each accent to the right place on its letter.

## Why it matters

Many texts write accented letters as two characters: a base letter followed by a combining accent. Vietnamese is typed this way; text from databases, macOS file names and some web content is stored this way (Unicode decomposed form). Without `mark`, the accent is not attached: it sits wherever its own outline puts it — usually floating at a fixed height, off-centre on narrow letters, colliding with capitals.

## How it is checked

The font's characters are searched for combining marks in the range U+0300–U+036F. If there is at least one and GPOS has no `mark` feature, the font is reported.

## When it does not apply

Fonts without combining marks in that range.

## How to fix

Add anchors to the base letters and the marks (`top`, `bottom`, and `_top`, `_bottom` on the marks) so that the export builds `mark` (and `mkmk` for stacked accents). In Glyphs, anchors can be added automatically with Glyph → Set Anchors; check them in every master.

## Example

| Text | With mark | Without mark |
|---|---|---|
| e + ◌́ | é, accent centred over e | accent at its own position, often off-centre |
| A + ◌̈ | Ä, dieresis above the capital | dieresis collides with the A |

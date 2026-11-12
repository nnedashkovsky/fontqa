---
id: glyphs.mark_widths
title: Combining marks have zero width
summary: Combining marks — Unicode nonspacing marks and glyphs marked as marks in GDEF — have advance width 0.
category: C
level: designer
severity: medium
action: fix
applies: All fonts.
related: layout.marks
sources:
  - Unicode, nonspacing marks (category Mn) | https://www.unicode.org/reports/tr44/#General_Category_Values
  - OpenType spec, GDEF glyph classes | https://learn.microsoft.com/en-us/typography/opentype/spec/gdef
---

## What it checks

Combining accents — the acute, grave, dieresis and others that are typed after a letter (U+0301, U+0308…) — must not take up horizontal space: their width is 0.

## Why it matters

Text in Vietnamese, Lithuanian, transliteration and many web sources writes accented letters as two characters: the base letter and a combining mark. The mark is positioned over the letter by the `mark` feature, but its **width** is still added to the line. With a non-zero width, every such letter is followed by a gap: "é" looks like "é ".

## How it is checked

1. Marks are collected from two places: characters whose Unicode category is Mn (nonspacing mark), and glyphs that GDEF classifies as marks (class 3).
2. Every mark with a width other than 0 is reported, with its width.

## When it does not apply

Fonts without combining marks.

## How to fix

Set the width of combining marks to 0. In Glyphs, these are the `*comb` glyphs (`acutecomb`, `dieresiscomb`…); their category should be Mark, Nonspacing. If one of them has a width, check its category and whether a width was set by hand or by a metrics key.

## Example

| Glyph | Width | |
|---|---|---|
| acutecomb | 0 | good |
| dieresiscomb | 220 | bad: a gap after every ü typed as u + ◌̈ |

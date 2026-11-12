---
id: glyphs.tabular
title: Tabular figures are tabular
summary: When the font has a tnum feature, the figures it produces all have the same width.
category: C
level: designer
severity: medium
action: fix
applies: Fonts with a tnum feature.
related: glyphs.spaces, widths.near_equal
sources:
  - OpenType feature registry, tnum | https://learn.microsoft.com/en-us/typography/opentype/spec/features_pt#tag-tnum
---

## What it checks

The `tnum` feature promises tabular figures: digits of one width, so that numbers line up in columns. The check makes sure the figures it produces really share one width.

## Why it matters

Tables, price lists, timetables and financial reports rely on tabular figures. If one digit is a few units wider — often "1" or a digit that was redrawn later — the columns drift apart, and the user has no way to fix it in the layout.

## How it is checked

1. Only fonts with a `tnum` feature are checked.
2. For each digit 0–9, the glyph that `tnum` substitutes is taken (or the digit itself, if `tnum` leaves it unchanged).
3. The widths of these ten glyphs must be equal. The finding lists each glyph with its width.

## When it does not apply

Fonts without a `tnum` feature. Fonts whose default figures are tabular without a feature are not checked here.

## How to fix

Give all tabular figures the same width — usually the width of the zero. In Glyphs, select the `.tf` figures and set one width for all; check also the tabular variants of other figure sets (old-style tabular, `.tosf`).

## Example

| Glyph | Width | |
|---|---|---|
| zero.tf … nine.tf | 560 | good |
| one.tf | 540 | bad: columns drift by 20 units |

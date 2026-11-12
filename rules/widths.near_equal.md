---
id: widths.near_equal
title: Widths that should match across styles differ by a unit or two
summary: A glyph that has the same width in most styles is not 1–2 units off in a few of them.
category: C
level: designer
severity: medium
action: fix
applies: Static fonts of a family with three styles or more; upright and italic styles are compared separately.
related: glyphs.tabular, charset.family_same
---

## What it checks

Some glyphs are meant to have exactly the same width in every weight: tabular figures, arrows, geometric symbols, monospaced punctuation. The check finds glyphs whose width is the same in most styles but off by **1 or 2 units** in a few.

## Why it matters

Such a small difference is almost never a design decision — it is a rounding error from scaling, interpolation or a nudged node. But it breaks what the equal width was for: tabular figures stop aligning when the weight changes, symbol fonts used in layouts shift by a unit, and a family that should behave consistently does not.

Bigger differences are left alone: a letter that is 20 units wider in Bold is design.

## How it is checked

1. Static styles of one family and line are compared, uprights and italics apart. At least three styles are needed to see what is "usual".
2. For every glyph present in all of them, the widths are compared. If the spread is more than 2 units, the glyph is skipped as designed.
3. The expected width is the most common one; on a tie, the rounder number (1000 rather than 1001). It must appear in at least 40% of the styles.
4. The styles where the width differs are listed per glyph.

## When it does not apply

- Variable fonts (their widths come from one design space).
- Families of fewer than three styles in a group.

## How to fix

Set the odd widths to the common value in the source. In Glyphs, check whether the glyph's width is controlled by a metrics key or is interpolated: a metrics key such as `=zero` keeps tabular figures and symbols at one width in every master.

## Example

| Glyph | Light | Regular | Bold | Black | |
|---|---|---|---|---|---|
| zero.tf | 560 | 560 | 560 | 560 | good |
| blackDiamond | 1000 | 1001 | 1000 | 1001 | bad: 1 unit off in two styles |
| A | 640 | 660 | 690 | 720 | not checked: designed difference |

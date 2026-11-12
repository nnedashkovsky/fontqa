---
id: layout.kern_shadowed
title: No kerning pairs hidden behind earlier subtables
summary: Every kerning pair the font defines can actually apply — none is hidden behind an earlier class-kerning subtable.
category: D
level: designer
severity: medium
action: fix
applies: All fonts with GPOS kerning.
related: vf.vs_static
sources:
  - OpenType spec, GPOS pair adjustment (formats 1 and 2) | https://learn.microsoft.com/en-us/typography/opentype/spec/gpos#lookup-type-2-pair-adjustment-positioning-subtable
---

## What it checks

Kerning in a font is stored in a lookup made of one or more **subtables**. A shaping engine looks at the subtables in order and stops at the first one whose list of first glyphs (its *coverage*) contains the current glyph. The check finds kerning pairs that sit in a later subtable although an earlier **class-kerning** subtable already covers their first glyph — those pairs are never reached.

## Why it matters

The pairs are in the font, the designer kerned them, but **no app applies them**: the text shows the unkerned spacing. Typical victims are exceptions and pairs with rare glyphs — `&` followed by Cyrillic or Greek, accented letters after punctuation.

It also explains a confusing symptom: a variable font and its statics, built from the same kerning, space the same text differently, because the subtables were split differently at export.

## How it is checked

1. Kerning lookups (GPOS type 2) are read subtable by subtable.
2. For each class-kerning subtable (format 2), its first glyphs are remembered. A glyph-pair subtable (format 1) does not hide anything: when a pair is not in it, the engine moves on.
3. Any later pair whose first glyph is already covered by an earlier class subtable, and which has a non-zero value, is counted as hidden.
4. The finding shows the number of hidden pairs and their first glyphs.

## When it does not apply

Fonts without GPOS kerning.

## How to fix

The cause is in how the export splits kerning into subtables, usually when the kerning is large or has many exceptions.

- Make sure kerning groups do not overlap and every first glyph belongs to one group.
- Re-export with the current version of the editor; if pairs are still hidden, move exceptions into the subtable that covers their first glyph, or reduce the number of exceptions.

## Example

| Subtable | Type | Covers | |
|---|---|---|---|
| 1 | class kerning | A, V, W, ampersand… | |
| 2 | class kerning | ampersand + Cyrillic | bad: never reached, `&Д` is not kerned |

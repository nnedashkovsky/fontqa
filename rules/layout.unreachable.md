---
id: layout.unreachable
title: Every glyph can be reached
summary: Every glyph in the font can be typed — through a character, an OpenType feature or as a component of another glyph.
category: D
level: designer
severity: medium
action: fix
applies: All fonts; each distinct outline table once.
related: layout.aalt
sources:
  - OpenType feature registry | https://learn.microsoft.com/en-us/typography/opentype/spec/featurelist
---

## What it checks

A glyph is reachable if the user can get it on screen: it has a Unicode value, or some OpenType feature produces it (small caps, stylistic sets, alternates…), or another glyph uses it as a component. The check lists glyphs that none of these paths reaches.

## Why it matters

An unreachable glyph is drawn, exported, paid for — and nobody can use it. Almost always it is a forgotten feature: small caps drawn but no `smcp`, a stylistic alternate with no `ss01`, tabular figures with no `tnum`. Customers buy the font for its alternates and do not find them.

## How it is checked

1. Starting from every character of the font, the check follows every OpenType substitution of every feature, and every component, and collects all glyphs it can reach.
2. Glyphs left over are reported, except technical ones (`.notdef`, `.null`, `CR`…).
3. For each leftover glyph, the name suffix suggests the missing feature: `.sc` → smcp/c2sc, `.tf` → tnum, `.osf` → onum, `.ss01` → ssXX, `.alt` → salt/aalt, and so on.

## When it does not apply

Fonts without glyphs beyond their character set.

## How to fix

Add the glyph to the feature its suffix suggests, or remove it from the export if it is a leftover. In Glyphs, features are generated from suffixes automatically — check the glyph's name (a typo in the suffix breaks it), that the feature is set to automatic, and that the glyph exports.

## Example

| Glyph | Suggested feature | |
|---|---|---|
| a.ss01 | ssXX | bad: no ss01 feature uses it |
| one.tf | tnum | bad: the font has no tnum |
| a.sc | smcp/c2sc | good once smcp exists |

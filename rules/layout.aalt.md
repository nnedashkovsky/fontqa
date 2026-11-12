---
id: layout.aalt
title: aalt offers every alternate
summary: The Access All Alternates feature (aalt) lists every single substitution and alternate that the other features offer.
category: D
level: designer
severity: low
action: confirm
applies: Fonts that have an aalt feature.
related: layout.unreachable
sources:
  - OpenType feature registry, aalt | https://learn.microsoft.com/en-us/typography/opentype/spec/features_ae#tag-aalt
---

## What it checks

`aalt` (Access All Alternates) collects every alternate form of a glyph in one place. The check makes sure that every one-to-one substitution of the other features — small caps, stylistic sets, figure styles, swashes, single alternates — is also offered by `aalt`.

## Why it matters

Design apps show alternates from `aalt`: InDesign's Glyphs panel and the alternates pop-up on a selected letter offer only what `aalt` lists. An alternate missing from `aalt` can still be reached through its own feature, but designers who look for it in the panel will not find it.

The result is **Confirm**: leaving something out of `aalt` can be intended.

## How it is checked

1. All single (type 1) and alternate (type 3) substitutions of `aalt` are collected as pairs "glyph → alternate".
2. The same is done for the other features, except those that never belong in `aalt`: contextual and required features (`ccmp`, `locl`, `calt`, `rlig`, `rvrn`…), ligatures, fractions and positional forms.
3. Pairs offered by other features but not by `aalt` are listed.

## When it does not apply

Fonts without an `aalt` feature.

## How to fix

Let the export rebuild `aalt` from all features with alternates. In Glyphs, `aalt` is generated automatically if it is not set to manual; after adding a new feature or alternate, regenerate the features (Font Info → Features → Update).

## Example

| Substitution | In ss01 | In aalt | |
|---|---|---|---|
| a → a.ss01 | yes | yes | good |
| g → g.ss02 | yes | no | bad: not in InDesign's alternates |

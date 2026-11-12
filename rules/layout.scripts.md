---
id: layout.scripts
title: Scripts of the character set are registered
summary: Every script the font really covers (10 letters or more) has its own record in the OpenType layout tables GSUB and GPOS.
category: D
level: engineer
severity: medium
action: confirm
applies: All fonts with GSUB or GPOS.
related: layout.marks, tables.meta
sources:
  - OpenType spec, script list table | https://learn.microsoft.com/en-us/typography/opentype/spec/chapter2#script-list-table-and-script-record
  - OpenType script tags | https://learn.microsoft.com/en-us/typography/opentype/spec/scripttags
---

## What it checks

OpenType features are organised by script: the layout tables list Latin (`latn`), Cyrillic (`cyrl`), Greek (`grek`)… and, for each, the features and languages. The check makes sure every script that the font covers with at least 10 letters has its own record in GSUB and in GPOS.

## Why it matters

A shaping engine first decides the script of the text, then looks up that script's features. If the script has no record, the engine falls back to the default (`DFLT`) — which usually works for plain kerning, but loses everything **language-specific**: localised forms for Bulgarian, Serbian or Romanian (`locl`), language-specific features in Chinese or Japanese text, and sometimes all features in apps that do not use the fallback.

The result is **Confirm**: a font may deliberately treat a small set of letters through DFLT.

## How it is checked

1. The font's letters are counted by script.
2. For every script with **10 letters or more**, the OpenType script tag is looked up (Latin → `latn`, Cyrillic → `cyrl`…).
3. If GSUB or GPOS exists but does not list that tag, it is reported, with the table that lacks it.

## When it does not apply

Fonts without GSUB and GPOS; scripts with fewer than 10 letters in the font.

## How to fix

Let the export register the scripts. Editors add a script record when a feature has lookups for that script or when the feature code names the script explicitly (`script cyrl;`). In Glyphs, features are generated per script automatically when the glyphs carry the right script; check the script of glyphs added by hand.

## Example

| Script | Letters | GSUB | GPOS | |
|---|---|---|---|---|
| Latin | 240 | latn | latn | good |
| Cyrillic | 66 | — | cyrl | Confirm: Bulgarian forms will not switch on |

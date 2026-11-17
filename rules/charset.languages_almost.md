---
id: charset.languages_almost
title: Languages one step away
summary: No language with a million speakers or more is short of just one to three letters.
category: C
level: designer
severity: low
action: ok
applies: All fonts.
related: charset.store_minimum, charset.family_same
sources:
  - Unicode CLDR, exemplar characters | https://cldr.unicode.org/
---

## What it checks

For each language, Unicode CLDR lists the letters its everyday writing needs — the "main" exemplar characters. The check compares them with the characters of the font, upper and lower case. A font that has all of a language's letters supports it. A font that lacks **one to three letters** (and has at least 70% of the rest) is one step away.

## Why it matters

This is the cheapest way to gain customers. A Western European font without ő and ű cannot set Hungarian, with 14 million speakers; a font without ş cannot set Kurdish in Latin. The font looks complete, and the gap is found by the first buyer.

It is a hint, not a defect, so it is **Harmless**: nothing is broken in the font. The list tells you which letters to draw to reach more languages — and which languages not to promise.

## How it is checked

1. The language data (`core/data/languages.json`) is built from CLDR: 248 languages and scripts with at least 100,000 speakers, each with its main letters and an estimate of its speakers.
2. For each language, every letter must be in the font in lower case and in upper case (if it has one). A letter without its own glyph counts when its base and its combining accent are both there **and** the font has a `mark` feature that positions them.
3. No missing letters: the language is **supported** (listed in the report's Languages section).
4. One to three letters missing, and at least 70% of its letters present: the language is **one step away**.
5. Only languages with at least **1,000,000 speakers** become findings; the Languages section of the report shows all of them. Speakers are estimated by summing territory population times the share of each language that CLDR gives.

## When it does not apply

Fonts that are not meant for general text (symbol, icon and ornament fonts) get hints for languages they will never need — leave those as Harmless.

## How to fix

Draw the letters named in the finding if the language matters for your customers. In Glyphs, add the glyphs by name (Glyph → Add Glyphs) and compose them from existing letters and accents.

## Example

| Font | Missing | Result |
|---|---|---|
| Western European (Windows-1252) | ő Ő ű Ű | Hungarian is one step away |
| Western European + Central European | — | Hungarian supported |

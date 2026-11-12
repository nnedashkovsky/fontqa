---
id: charset.store_minimum
title: Western European minimum for stores
summary: The font has every printable Windows-1252 character, including the currency signs $ € £ ¥ ¢.
category: C
level: designer
severity: medium
action: fix
applies: All fonts.
related: charset.family_same
sources:
  - Microsoft, Windows-1252 code page | https://learn.microsoft.com/en-us/globalization/encoding/sbcs
---

## What it checks

The font covers the basic Western European set: the 218 printable characters of the Windows-1252 code page — Latin letters with the accents of French, German, Spanish, Scandinavian languages and others, punctuation, and the currency signs $ € £ ¥ ¢.

## Why it matters

This is the set customers silently expect from a Latin font. Stores check it when you submit a font: MyFonts asks for a Western European minimum with all five currency signs. A missing "€" or "ß" shows up as a gap or a fallback character in the first real text.

## How it is checked

The font's characters are compared with the 218 printable characters of Windows-1252. Every missing character is listed. Missing currency signs are named in the summary, because they are the most common gap.

## When it does not apply

Always applies. A font that is not meant for Western European languages (a Cyrillic-only or display set) still gets the finding — confirm it as intended.

## How to fix

Add the missing characters before submitting the font to stores. Most of them are accented letters that can be built from components; in Glyphs, add them by name (Glyph → Add Glyphs) and they are composed automatically.

## Example

| Font | Missing | |
|---|---|---|
| Acme Sans | — | good |
| Acme Display | 6: € ¥ ¢ Ÿ Œ œ | bad |

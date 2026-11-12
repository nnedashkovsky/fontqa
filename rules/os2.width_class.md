---
id: os2.width_class
title: usWidthClass matches the style name
summary: The numeric width stored in the font (OS/2 usWidthClass) is 5 (normal) unless the style name has a width word such as Condensed or Expanded.
category: F
level: engineer
severity: medium
action: confirm
applies: Static installable fonts (OTF, TTF outside a Web folder).
related: os2.weight_class, names.wws
sources:
  - OpenType spec, OS/2.usWidthClass | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#uswidthclass
---

## What it checks

Every font stores its width as a class from 1 (Ultra-condensed) to 9 (Ultra-expanded); 5 is normal. The check compares it with the width word in the style name.

## Why it matters

Windows and DirectWrite group a family by width using this class. A style that is not wider but has, for example, width class 6 is shown with "Semi-Expanded" in Windows font dialogs and may be split into a separate row. CSS `font-stretch` also matches fonts by it.

The result is **Confirm**: some families use the class for designs that the name does not spell out.

## How it is checked

1. The style name is taken from ID 17 (or ID 2) and split into words.
2. Known width words give the expected class: UltraCondensed 1, ExtraCondensed and Compressed 2, Condensed and Narrow 3, SemiCondensed 4, SemiExpanded 6, Expanded, Extended and Wide 7, ExtraExpanded 8, UltraExpanded 9. Compound words count whether written together or apart: SemiCondensed and Semi Condensed both give 4.
3. No width word means 5.

## When it does not apply

- Variable fonts.
- Web fonts.

## How to fix

Set `usWidthClass` to 5 for styles that are not width variants, and to the matching class for those that are. In Glyphs, Font Info → Exports → each instance → Width Class.

## Example

| Style | usWidthClass | |
|---|---|---|
| Bold | 5 | good |
| Condensed Bold | 3 | good |
| Display Bold | 6 | Confirm: Windows shows "Semi-Expanded" |

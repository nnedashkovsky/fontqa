---
id: os2.weight_class
title: usWeightClass matches the style name
summary: The numeric weight stored in the font (OS/2 usWeightClass) is the one its style name implies — Light 300, Regular 400, Bold 700 and so on.
category: F
level: engineer
severity: medium
action: fix
applies: Static installable fonts (OTF, TTF outside a Web folder).
related: os2.width_class, names.ribbi
sources:
  - OpenType spec, OS/2.usWeightClass | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#usweightclass
---

## What it checks

Every font stores its weight as a number from 1 to 1000 (`OS/2.usWeightClass`). The check compares it with the weight word in the style name.

## Why it matters

Apps order and group styles by this number, not by name:

- font menus sort the family by it, so a wrong number puts "Light" after "Bold";
- CSS `font-weight` and Windows match styles by it, so `font-weight: 600` may pick the wrong font;
- Windows uses it to link a regular to its bold.

## How it is checked

1. The style name is taken from ID 17 (or ID 2) and split into words.
2. Known weight words give the expected value: Thin/Hairline 100, ExtraLight/UltraLight/XLight 200, Light/Lt 300, Book/Regular/Normal/Rg 400, Medium/Md 500, SemiBold/DemiBold/SBd 600, Bold/Bd 700, ExtraBold/UltraBold/XBold 800, Black/Heavy 900, ExtraBlack/UltraBlack 950. Compound words are recognised when written as one word (ExtraLight, not Extra Light). If several appear, the last one counts.
3. No weight word means 400.
4. A different `usWeightClass` is reported. If the name has no weight word, the result is **Confirm**: the name may simply not say the weight.

## When it does not apply

- Variable fonts (their weight comes from the axis).
- Web fonts.

## How to fix

Set the weight class per style in the source. In Glyphs, Font Info → Exports → each instance → Weight Class.

## Example

| Style | usWeightClass | |
|---|---|---|
| Light | 300 | good |
| SemiBold | 600 | good |
| SemiBold | 500 | bad: sorts with Medium, CSS 600 picks something else |
| Display | 700 | Confirm: the name has no weight word |

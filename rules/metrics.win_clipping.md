---
id: metrics.win_clipping
title: Nothing is clipped on Windows
summary: The Windows ascent and descent (usWinAscent, usWinDescent) cover the highest and lowest points of every glyph.
category: F
level: designer
severity: medium
action: fix
applies: All fonts with an OS/2 table.
related: metrics.family_vertical, metrics.x_cap_height
sources:
  - OpenType spec, OS/2 usWinAscent and usWinDescent | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#uswinascent
---

## What it checks

Windows draws text only inside a box from `usWinAscent` above the baseline to `usWinDescent` below it. The check makes sure that box contains every glyph of the font: the highest point (often an accented capital such as Ǻ or a stacked Vietnamese accent) and the lowest (a descender, a cedilla, a bracket).

## Why it matters

Anything outside that box is **cut off** on Windows: the tops of accented capitals, the bottoms of descenders or brackets. It happens in many Windows apps and in some browsers on Windows, while the same text looks fine on a Mac — so it is often found only by a customer.

## How it is checked

The font's bounding box is compared with the win metrics:

- `usWinAscent` must be at least the highest point (`head.yMax`);
- `usWinDescent` must be at least the depth of the lowest point (−`head.yMin`).

The finding shows both values.

## When it does not apply

Fonts without an OS/2 table.

## How to fix

Raise `usWinAscent` / `usWinDescent` to the font's extremes. In Glyphs, set the custom parameters winAscent and winDescent with the same values in every master, or leave them unset so that Glyphs calculates them from the bounding box at export. Raising them does not change line spacing on macOS or in apps that use the typo metrics.

## Example

| | Win metric | Glyph extreme | |
|---|---|---|---|
| Ascent | 1000 | Ǻ at 980 | good |
| Ascent | 900 | Ǻ at 980 | bad: the ring is cut off |
| Descent | 300 | ţ at −260 | good |

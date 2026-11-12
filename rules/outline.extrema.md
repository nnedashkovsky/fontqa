---
id: outline.extrema
title: Nodes on extremes
summary: Every curve has nodes at its horizontal and vertical extremes — no curve bulges past its end nodes.
category: C
level: designer
severity: low
action: confirm
applies: All fonts; each distinct outline table once (App, Desktop and Web copies of a style share the result).
related: outline.zero_length, outline.fractional
---

## What it checks

Where a curve reaches its leftmost, rightmost, highest or lowest point, there should be a node. The check finds curves that bulge beyond their end nodes — the extreme lies **inside** the curve, between two nodes.

## Why it matters

- **Hinting and rendering** place the font's alignment zones and stems by the nodes at extremes. Without them, the top of an "o" may not snap to the x-height at small sizes, and round letters look uneven on screen.
- **Bounding boxes** are calculated faster and more exactly from nodes; some tools compute them from nodes only and then clip or misplace the glyph.
- **Overlap removal and offsetting** (bold, outline effects in apps and at export) are more reliable with nodes at extremes.

It is a convention, not a law: ornaments and some designs skip extremes on purpose, which is why the result is **Confirm**.

## How it is checked

1. Each glyph's own contours are read (components are checked in the component glyph).
2. For every curve, the check computes how far the curve goes beyond the range of its two end nodes, horizontally and vertically.
3. A bulge of more than **0.5 unit** (CFF, cubic curves) or **1 unit** (TrueType, quadratic curves — converted curves bulge by a fraction of a unit between implied points) counts.
4. The finding lists glyphs with the number of such curves and the largest bulge. If any glyph bulges by **10 units or more**, the severity rises to **medium**: that is a clearly missing node, not rounding.
5. In italics, the check also tries the curve with the slant removed. Glyphs whose nodes sit on the **slanted** extremes (a style some foundries use) are marked "nodes on slanted extremes".

## When it does not apply

Fonts without outlines. Glyphs drawn only from straight lines have nothing to check.

## How to fix

Add nodes at the extremes in the source. In Glyphs: Path → Add Extremes, in every master. Check the result visually — added nodes change nothing in the shape, but very short curves near corners are worth a look.

## Example

| Glyph | Bulge | |
|---|---|---|
| o | 0 | good: nodes at top, bottom, left, right |
| S | 0.4 | good: within 0.5 unit |
| at | 14.2 | bad: a node is missing at the top of the inner bowl |

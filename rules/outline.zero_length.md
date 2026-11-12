---
id: outline.zero_length
title: No zero-length segments or contours
summary: No segment ends where it starts, and no contour collapses into a point or a line.
category: C
level: designer
severity: low
action: fix
applies: All fonts; each distinct outline table once.
related: outline.extrema
---

## What it checks

Degenerate outline pieces:

- a **segment of zero length** — two nodes on the same spot, so the line or curve between them has no length;
- a **collapsed contour** — a contour that has no area: all its points on one spot or on one straight line;
- in TrueType fonts, a **point repeated** on its contour.

## Why it matters

Such pieces are invisible, but rasterizers, hinting tools and overlap removal may handle them badly: a stray pixel at small sizes, a hinting instruction that fails, a contour that flips direction when an app makes the glyph bold. Usually nothing visible happens, which is why the severity is low — but it is easy to clean up.

They come from double-clicking a node twice, merging paths, cutting shapes, or from interpolation where two nodes meet in one master.

## How it is checked

Each glyph's own contours are read. Zero-length segments and degenerate contours are counted per glyph; the finding lists the glyphs with their count.

## When it does not apply

Fonts without outlines.

## How to fix

Delete the duplicate nodes in the source. In Glyphs, Path → Tidy Up Paths removes many of them; check the masters too, because interpolation can create a zero-length segment in an instance if two nodes coincide in one master.

## Example

| Glyph | Problem | |
|---|---|---|
| a | none | good |
| g | 2 nodes at (312, −120) | bad: a zero-length segment |
| period | a contour of 3 points on one line | bad: a collapsed contour |

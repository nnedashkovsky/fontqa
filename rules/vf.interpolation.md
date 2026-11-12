---
id: vf.interpolation
title: Masters interpolate cleanly
summary: The masters stored in a variable font are compatible in a way that keeps shapes intact between them — no wrong contour order, start points, weight jumps or kinks.
category: G
level: designer
severity: low
action: confirm
applies: Variable fonts; each distinct outline table once.
related: vf.vs_static, outline.extrema
sources:
  - fontTools, varLib.interpolatable | https://github.com/fonttools/fonttools/blob/main/Lib/fontTools/varLib/interpolatable.py
---

## What it checks

A variable font contains the drawing of each master and interpolates between them. Even when the masters are technically compatible (same number of points), a few kinds of mismatch make shapes go wrong **between** masters. The check runs fontTools' `interpolatable` on the masters stored in the font and reports what it finds:

- **contour order** — contours are listed in a different order, so one contour morphs into another;
- **wrong start point** — a contour starts at a different node, so the shape twists in between;
- **weight** — a contour gets thinner or thicker in the middle than at either end;
- **kink** — a smooth curve breaks into a corner at intermediate positions;
- and similar problems the tool detects.

## Why it matters

The masters themselves look fine, so these problems are invisible in the editor and in the named instances that sit on masters. They show up at **intermediate positions** of the axes — exactly where users drag sliders or where CSS sets weight 450. A twisting "o" or a thinning stem in a web page is hard to trace back to the font.

The result is **Confirm**: the tool also flags differences that are harmless or intended, so look at the glyphs before changing anything.

## How it is checked

1. fontTools `interpolatable` compares every pair of neighbouring masters for every glyph.
2. Findings are grouped by kind; the report lists the glyphs per kind (up to 12 named, with the total).
3. For fonts with more than **800 glyphs**, a sample is checked: every glyph below U+3000 and an even spread of the rest. The finding says how many glyphs were checked.

## When it does not apply

Static fonts.

## How to fix

Look at the listed glyphs at intermediate positions (in Glyphs, preview an instance between the masters), and fix contour order and start points in the source so that every contour corresponds to the same contour in every master.

## Example

| Glyph | Problem | Seen at |
|---|---|---|
| o | none | |
| ae | contour order | weight 450: the e-part morphs into the a-part |
| S | wrong start point | weight 600: the spine twists |

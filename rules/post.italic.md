---
id: post.italic
title: Italic angle, caret and italic bit agree
summary: Italic fonts have a non-zero italic angle, upright fonts an angle of 0, and the text cursor slants with the angle.
category: F
level: engineer
severity: low
action: fix
applies: All fonts.
related: names.ribbi
sources:
  - OpenType spec, post.italicAngle | https://learn.microsoft.com/en-us/typography/opentype/spec/post
  - OpenType spec, hhea caretSlopeRise and caretSlopeRun | https://learn.microsoft.com/en-us/typography/opentype/spec/hhea
---

## What it checks

Three things describe how slanted a font is, and they must agree:

- the **italic bit** (`fsSelection` ITALIC, `macStyle` Italic) — "this is an italic";
- the **italic angle** (`post.italicAngle`) — how many degrees it leans;
- the **caret slope** (`hhea.caretSlopeRise`, `caretSlopeRun`) — how the text cursor and the selection lean.

## Why it matters

- Apps slant the cursor and the text selection by the caret slope. In an italic with an upright caret, the cursor cuts through letters and the selection looks broken.
- Apps add synthetic slant or adjust spacing when they think a font is upright; an angle on an upright font, or no angle on an italic, misleads them.
- Some apps place underlines and inline objects using the italic angle.

## How it is checked

1. An italic font with italic angle 0 → **Confirm** (some italics are upright by design).
2. A font with an italic angle but no italic bit (and no oblique bit) → **medium, Confirm**.
3. The caret angle computed from rise and run must match the italic angle within **1°**.

## When it does not apply

Always applies; an upright font with angle 0 and an upright caret passes.

## How to fix

Set the italic angle in the source masters; the export derives the caret from it. In Glyphs, Font Info → Masters → Italic Angle.

## Example

| Style | Italic bit | Angle | Caret | |
|---|---|---|---|---|
| Italic | on | −12 | 12° | good |
| Italic | on | 0 | upright | Confirm |
| Italic | on | −12 | upright | bad: the cursor does not slant |

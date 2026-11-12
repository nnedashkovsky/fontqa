---
id: tables.hinting
title: TrueType hinting tables are present
summary: TrueType fonts carry hinting tables (fpgm, prep, cvt).
category: F
level: engineer
severity: low
action: ok
applies: Fonts with TrueType outlines.
related: outline.extrema
sources:
  - OpenType spec, TrueType instructions (fpgm, prep, cvt) | https://learn.microsoft.com/en-us/typography/opentype/spec/ttinst
  - ttfautohint | https://freetype.org/ttfautohint/
---

## What it checks

TrueType fonts can carry hinting: small programs that adjust outlines to the pixel grid at small sizes. They live in three tables — `fpgm` (function definitions), `prep` (control values and settings, including dropout control) and `cvt ` (control values). The check notes fonts that lack any of them.

## Why it matters

Modern macOS, iOS and most browsers ignore hinting. **Windows** with the classic renderer (GDI — Word, older apps, some printers) uses it: unhinted fonts render small text unevenly, with stems of different widths and blurred horizontals. Without dropout control in `prep`, thin strokes can disappear at low resolutions.

For display typefaces that are used large, this hardly matters — which is why the result is **Harmless**.

## How it is checked

For fonts with TrueType outlines, the presence of `fpgm`, `prep` and `cvt ` is checked; missing tables are listed. The check does not judge the quality of the hinting.

## When it does not apply

CFF (OTF) fonts — they use a different, much simpler hinting system.

## How to fix

Autohint the TrueType build, for example with ttfautohint (Glyphs' Autohint export option uses it for TrueType). At minimum, add a `prep` program that turns on dropout control.

## Example

| File | fpgm | prep | cvt | |
|---|---|---|---|---|
| AcmeSans-Regular.ttf | yes | yes | yes | good |
| AcmeDisplay-Regular.ttf | — | — | — | harmless for display use |

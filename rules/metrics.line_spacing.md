---
id: metrics.line_spacing
title: Line spacing agrees between macOS and Windows
summary: The default line height on macOS (hhea) equals the one Windows uses (typo metrics with USE_TYPO_METRICS, otherwise win metrics), within 1% of the em.
category: F
level: engineer
severity: low
action: confirm
applies: All fonts with OS/2 typo metrics.
related: metrics.use_typo, metrics.family_vertical, metrics.win_clipping
sources:
  - OpenType spec, OS/2 vertical metrics | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#sTypoAscender
---

## What it checks

A font stores its default line height three times, and different systems read different ones:

- **macOS** (and many cross-platform apps) use `hhea`: ascender − descender + line gap;
- **Windows** uses the `OS/2` typo metrics if USE_TYPO_METRICS is on, otherwise the `OS/2` win metrics (win ascent + win descent).

The check compares the macOS line height with the one Windows uses.

## Why it matters

If they differ, the same document has different default leading on Mac and Windows: text runs longer on one platform, pages break differently, and a layout made on a Mac does not fit on a Windows machine. In browsers, the line height of `line-height: normal` changes between platforms.

The result is **Confirm**: some fonts set them differently on purpose (for example, to keep tight win metrics for legacy apps).

## How it is checked

1. The macOS line height is `hhea` ascender − descender + line gap.
2. The Windows line height is typo ascender − descender + line gap if USE_TYPO_METRICS is on, otherwise win ascent + win descent.
3. A difference of more than **1% of the em** (10 units at 1000 UPM) is reported.

## When it does not apply

Fonts without typo metrics in OS/2.

## How to fix

Make the `hhea` line height equal to the one Windows uses. The common setup: USE_TYPO_METRICS on, typo metrics as the intended line spacing, `hhea` with the same values, and win metrics large enough to avoid clipping.

## Example

| | Ascender | Descender | Gap | Line |
|---|---|---|---|---|
| hhea | 950 | −250 | 0 | 1200 |
| typo (USE_TYPO_METRICS on) | 800 | −200 | 200 | 1200 — good |
| win (bit off) | 1050 | 350 | | 1400 — bad: looser on Windows |

---
id: metrics.use_typo
title: USE_TYPO_METRICS is set
summary: The font sets the USE_TYPO_METRICS flag (OS/2 fsSelection bit 7), so Windows takes line spacing from the typo metrics.
category: F
level: engineer
severity: low
action: confirm
applies: All fonts.
related: metrics.line_spacing, metrics.win_clipping
sources:
  - OpenType spec, OS/2.fsSelection bit 7 | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fsselection
---

## What it checks

Bit 7 of `OS/2.fsSelection`, USE_TYPO_METRICS, tells Windows apps and browsers to use the typo ascender, descender and line gap for line spacing. The check reports fonts where the bit is off.

## Why it matters

Without the bit, Windows uses the **win** metrics for line spacing. But the win metrics also decide clipping, so they must cover the tallest accent and the deepest descender — and as line spacing they are often too loose. With the bit on, the two jobs are separated: win metrics prevent clipping, typo metrics set the leading. The OpenType specification recommends the bit for new fonts.

The result is **Confirm**: older families sometimes keep the bit off so that their line spacing does not change between versions.

## How it is checked

Reads the bit; reports it when it is off.

## When it does not apply

Always applies.

## How to fix

Turn the bit on and keep the typo metrics as the intended line spacing. In Glyphs, the custom parameter Use Typo Metrics in Font Info → Font. Then check line spacing on Windows: it may change for existing users.

## Example

| USE_TYPO_METRICS | Windows line spacing from | |
|---|---|---|
| on | typo: 800 − (−200) + 200 = 1200 | good |
| off | win: 1050 + 350 = 1400 | Confirm: looser than intended |

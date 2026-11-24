---
id: cmap.usable
title: The cmap can be used by the system
summary: The font has a Windows Unicode cmap subtable, maps only glyphs that exist, and maps the space.
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files.
related: glyphs.spaces, glyphs.empty_mapped, charset.store_minimum
sources:
  - OpenType spec, cmap table | https://learn.microsoft.com/en-us/typography/opentype/spec/cmap
  - Microsoft, recommendations for OpenType fonts | https://learn.microsoft.com/en-us/typography/opentype/spec/recom
---

## What it checks

The `cmap` table turns characters into glyphs. A font is a *Windows Unicode* font when it has a subtable with platform 3 and encoding 1 (characters up to U+FFFF) and, for characters beyond that, encoding 10. Symbol fonts use (3,0) instead.

## Why it matters

Windows looks for the (3,1) subtable. Without it, text typed in the font shows as boxes or in a fallback font, and some applications refuse to list the font. A cmap entry that points at a glyph that does not exist draws `.notdef` or breaks the shaper, and a font without a space leaves Word and browsers to invent its width.

## How it is checked

- The cmap has at least one subtable.
- Unless it is a symbol font, a (3,1) or (3,10) subtable exists.
- If a character beyond U+FFFF is mapped, a (3,10) subtable exists (medium).
- Every glyph the cmap names is in the font.
- U+0020 is mapped (medium).

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Export the font with the Windows Unicode cmap (every compiler does this by default; check any "legacy" or "Mac only" export option). Map every encoded character to a glyph, and add a space.

## Example

| Subtables | Verdict |
|---|---|
| (0,3), (3,1) | good |
| (0,3) only | bad: Windows has no subtable to read |

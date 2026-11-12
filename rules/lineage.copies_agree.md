---
id: lineage.copies_agree
title: Copies of one style agree across lines and formats
summary: The App, Desktop and Web copies of a style, in every format (TTF, OTF, WOFF, WOFF2), have the same design data — glyphs, widths, outlines, layout and vertical metrics.
category: F
level: engineer
severity: medium
action: fix
applies: Deliveries with more than one copy of a style (lines App, Desktop, Web, or several formats).
related: vf.vs_static, metrics.family_vertical
---

## What it checks

A delivery often has the same style several times: for apps, for desktop, for the web; as TTF, OTF, WOFF, WOFF2. Names, embedding settings, hinting, the legacy kern table and glyph names may differ between them by design. The **design data** must not:

- the glyph set and the character map;
- advance widths;
- outlines;
- the layout tables GSUB, GPOS, GDEF;
- vertical metrics.

## Why it matters

The same text must set the same way in the app, on the desktop and on the web. If the web copy has a different width for one glyph or loses a kerning pair, a headline that fits in the design file breaks into two lines on the site. A difference usually means one line was exported from an older state of the source.

## How it is checked

1. Copies are matched by file name without the line marker: `AcmeSans_A_Bd`, `AcmeSans_W_Bd` and `AcmeSans_Bd` are one style (markers A, W, D, App, Web, Desktop); static and variable apart.
2. A Desktop copy is the reference when there is one.
3. Each aspect above is compared with the reference. Differences are listed per aspect, with examples (which glyphs changed width, which counts differ).
4. If the layout tables differ byte by byte, the check shapes text with each copy — by default and with every feature switched on — and reports the copies only if the **result** differs. Tables compiled differently but behaving the same pass.

## When it does not apply

Styles that exist once in the delivery.

## How to fix

Build every line from one export of the source, and apply only the per-line differences the brief asks for (names, hinting, kern table, subsetting for the web).

## Example

| Copy | Glyphs | Widths | Layout | |
|---|---|---|---|---|
| Desktop/AcmeSans_Bd.otf | 412 | reference | reference | |
| App/AcmeSans_A_Bd.ttf | 412 | same | same behaviour | good |
| Web/AcmeSans_W_Bd.woff2 | 412 | f 402→404 | same behaviour | bad: text reflows on the web |

---
id: names.ribbi
title: Style linking (RIBBI) and style bits
summary: Name ID 2 is one of Regular, Italic, Bold, Bold Italic; other styles carry IDs 16/17; the style bits agree with ID 2.
category: A
severity: medium
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.gdi_length, names.wws, names.localized
sources:
  - OpenType spec, name table, IDs 1, 2, 16, 17 | https://learn.microsoft.com/en-us/typography/opentype/spec/name
  - OpenType spec, OS/2.fsSelection | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fsselection
  - OpenType spec, head.macStyle | https://learn.microsoft.com/en-us/typography/opentype/spec/head
---

## What it checks

Classic Windows apps know only four styles per family: **R**egular, **I**talic, **B**old, **B**old **I**talic (RIBBI). The check makes sure every font describes itself in those terms consistently:

- name ID 2 is one of the four RIBBI names;
- a style outside the four (Light, Black, Condensed Medium…) also has IDs 16 and 17 with its real name;
- the style bits in `OS/2.fsSelection` and `head.macStyle` say the same as ID 2.

## Why it matters

Windows groups fonts into menu items by ID 1 and links them with ID 2 and the style bits. The B and I buttons in Word jump between the linked styles.

- If ID 2 is "Light" or "Black", Windows does not know where the style belongs: it shows up oddly in menus, and B / I can apply a fake bold or slant instead of the real style.
- If ID 2 says "Bold" but the BOLD bit is off, or ID 2 says "Regular" while the ITALIC bit is on, apps disagree about what the font is. The same document looks different in different programs.
- Without IDs 16 and 17, a non-RIBBI style has no full name. Modern apps show it as "Acme Sans Light / Regular" instead of "Acme Sans / Light".

## How it is checked

1. ID 2 must be exactly `Regular`, `Italic`, `Bold` or `Bold Italic`.
2. The style is taken from ID 17 (or ID 2). If it is not one of the four, both ID 16 and ID 17 must exist.
3. When ID 2 is RIBBI, the bits must match it (table below).

| ID 2 | fsSelection REGULAR | fsSelection BOLD | fsSelection ITALIC | macStyle Bold | macStyle Italic |
|---|---|---|---|---|---|
| Regular | on | off | off | off | off |
| Italic | off | off | on | off | on |
| Bold | off | on | off | on | off |
| Bold Italic | off | on | on | on | on |

Each kind of mismatch is reported separately, with the bits that disagree.

## When it does not apply

- Web fonts (WOFF, WOFF2, or anything in a Web folder).

## How to fix

1. Give each style a style-linking role: Regular, Bold, Italic or Bold Italic of some four-style group. A family of eight weights becomes four groups of up to four styles each.
2. In Glyphs, set it per instance under Style Linking: *Is Bold*, *Is Italic*, and *Linked to* (the upright partner of an italic).
3. Glyphs writes IDs 16/17 and the style bits from those settings; check the custom parameters do not override them.

## Example

| Style | ID 1 | ID 2 | ID 16 | ID 17 | |
|---|---|---|---|---|---|
| Light | Acme Sans Light | Regular | Acme Sans | Light | good |
| Light Italic | Acme Sans Light | Italic | Acme Sans | Light Italic | good |
| Light | Acme Sans | Light | — | — | bad: ID 2 not RIBBI, no 16/17 |
| Bold | Acme Sans | Bold | — | — | good, but bad if fsSelection BOLD is off |

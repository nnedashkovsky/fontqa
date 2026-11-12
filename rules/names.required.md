---
id: names.required
title: Required name records are present
summary: Name IDs 1 to 6 exist in the Windows English records.
category: F
severity: high
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.postscript, names.version
sources:
  - OpenType spec, name table, IDs 1–6 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
---

## What it checks

Six name records identify a font everywhere, and each must be present (Windows platform, English):

| ID | Meaning |
|---|---|
| 1 | Family name (for Windows menus) |
| 2 | Style name (Regular, Italic, Bold, Bold Italic) |
| 3 | Unique font identifier |
| 4 | Full name ("Acme Sans Bold") |
| 5 | Version string |
| 6 | PostScript name |

## Why it matters

Without these, a font may refuse to install, appear without a name or with a garbage name in menus, or fail in PDF export and printing (which need the PostScript name). Font managers and installers use IDs 3 and 5 to tell versions apart.

## How it is checked

Each of IDs 1–6 must exist and must not be empty. Missing ones are listed in one finding per font.

## When it does not apply

- Web fonts: browsers do not need them, and web builds often strip names on purpose.

## How to fix

Fill the missing names in the source and export again. Font editors write all six by default, so a missing ID usually means a custom parameter or a post-processing script removed it.

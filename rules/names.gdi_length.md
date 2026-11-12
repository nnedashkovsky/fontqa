---
id: names.gdi_length
title: Family name fits the Windows GDI limit
summary: The Windows family name (name ID 1) is 30 characters or fewer — for variable fonts, family plus instance name too.
category: A
severity: high
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.ribbi, names.unique
sources:
  - Microsoft, LOGFONTW structure (LF_FACESIZE = 32) | https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-logfontw
  - OpenType spec, name table, IDs 1 and 16 | https://learn.microsoft.com/en-us/typography/opentype/spec/name
---

## What it checks

The family name that old Windows apps see — name ID 1 — must be 30 characters or shorter.

## Why it matters

Word, PowerPoint, Notepad and every other app that uses the classic Windows font API (GDI) store the family name in a 32-character field. One place goes to the terminating zero, so 31 characters fit exactly and anything longer is cut off. The check asks for 30 to keep one character of margin. When the name is too long, two things go wrong:

- **Styles merge.** "Acme Sans Display Condensed Extra Light" and "Acme Sans Display Condensed Extra Bold" are both cut to the same 31 characters. The menu shows one item, and only one of the styles can be chosen.
- **Text falls back.** Word saves the cut name in the document. When the document is opened again, Word looks for a font with that name, does not find it, and sets the text — or the characters outside Latin — in a system font.

## How it is checked

- Reads name ID 1 (Windows, English).
- Flags it when it is **31 characters or longer**.
- For a **variable font**, Windows builds a GDI name for every named instance: the family (ID 16, or ID 1 if there is no 16) plus the words of the instance name except Regular, Bold and Italic. Each such name is checked the same way, and the finding lists up to 12 that are too long.

## When it does not apply

- Web fonts (WOFF, WOFF2, or anything in a Web folder): browsers take the family name from CSS, not from the font.
- A long typographic family (ID 16) is fine. Only ID 1 is limited.

## How to fix

Shorten name ID 1 and keep the full names in IDs 16 and 17, which modern apps show instead:

1. Abbreviate the style words that end up in ID 1: "Dark Display XBold" → "Dk Dis XBd".
2. Keep ID 16 = "Acme Sans", ID 17 = "Dark Display XBold" unchanged.
3. In Glyphs, set the shortened family per instance with the Style Map Family Names property, then export again.

## Example

| | Name ID 1 | Length | Windows shows |
|---|---|---|---|
| Bad | `Acme Sans Display Condensed Extra Light` | 39 | `Acme Sans Display Condensed Ext` |
| Bad | `Acme Sans Display Condensed Extra Bold` | 38 | `Acme Sans Display Condensed Ext` — the same item |
| Good | `Acme Sans Dis Cd XLt` | 20 | `Acme Sans Dis Cd XLt`; ID 16/17 keep the full name |

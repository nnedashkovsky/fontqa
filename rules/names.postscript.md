---
id: names.postscript
title: PostScript name is valid
summary: Name ID 6 is at most 63 printable ASCII characters, without spaces or the characters [ ] ( ) { } < > / %.
category: F
level: engineer
severity: high
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.unique, names.required
sources:
  - OpenType spec, name ID 6 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
  - Adobe Technical Note #5902, PostScript name generation | https://adobe-type-tools.github.io/font-tech-notes/pdfs/5902.AdobePSNameGeneration.pdf
---

## What it checks

The PostScript name (ID 6) is the font's machine name: `AcmeSans-BoldItalic`. It must be:

- at most **63 characters**;
- printable ASCII only — codes 33 to 126, so **no spaces** and no letters outside basic Latin;
- free of `[ ] ( ) { } < > / %`, which have a special meaning in PostScript.

## Why it matters

PDF files, print drivers, Adobe apps and design tools refer to fonts by PostScript name. An invalid name can:

- break PDF export or embed the font under a mangled name;
- make the font missing when the document is opened elsewhere;
- stop the font from installing in some environments.

## How it is checked

ID 6 is read, every character outside codes 33–126 or in the forbidden set is collected, and the length is counted. The finding shows the name, the offending characters and the length.

## When it does not apply

- Web fonts.

## How to fix

Write ID 6 as `FamilyName-StyleName` with spaces removed: "Acme Sans Bold Italic" → `AcmeSans-BoldItalic`. Replace letters outside ASCII ("Á" → "A"). If the name is too long, abbreviate the style part.

Glyphs generates this name from the family and instance names; set the instance's PostScript name explicitly if the generated one breaks the rules.

## Example

| ID 6 | |
|---|---|
| `AcmeSans-BoldItalic` | good |
| `Acme Sans-Bold Italic` | bad: spaces |
| `AcmeSans-Bold(Alt)` | bad: parentheses |
| `AcméSans-Bold` | bad: é is not ASCII |

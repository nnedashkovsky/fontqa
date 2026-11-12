---
id: release.file_names
title: File name matches the PostScript name
summary: Each font file is named after its PostScript name — AcmeSans-Bold.otf for AcmeSans-Bold.
category: R
level: engineer
severity: low
action: confirm
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.postscript, release.formats
---

## What it checks

The file name without its extension equals the font's PostScript name (name ID 6).

## Why it matters

`FamilyName-Style` is the convention customers, stores and font managers recognise. When files are named differently — "Acme Bold final2.otf", "AS_Bd.otf" — customers cannot tell which file is which style, stores ask why family, styles and files do not name the same thing, and support has to guess which version a customer has.

The result is **Confirm**: some clients ask for their own file naming.

## How it is checked

For each installable font, the file name without extension is compared with name ID 6.

## When it does not apply

Web fonts — their file names are often chosen for the website.

## How to fix

Name the files after the PostScript name. Editors do this at export by default; renaming afterwards is the usual cause of a mismatch.

## Example

| File | PostScript name | |
|---|---|---|
| AcmeSans-Bold.otf | AcmeSans-Bold | good |
| Acme Sans Bold.otf | AcmeSans-Bold | Confirm |

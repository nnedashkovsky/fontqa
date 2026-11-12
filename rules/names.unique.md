---
id: names.unique
title: Names are unique across the delivery
summary: No two installable fonts of the same format share a family + style, full name, PostScript name or unique ID.
category: A
severity: high
action: fix
applies: All installable fonts of the delivery together, OTF and TTF separately.
related: names.gdi_length, names.postscript
sources:
  - OpenType spec, name IDs 3, 4, 6, 25 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
---

## What it checks

Operating systems identify an installed font by its names. Within one format (all OTF, or all TTF) of the delivery, these must not repeat:

- ID 1 + ID 2 (the Windows family and style);
- ID 16 + ID 17 (the typographic family and style);
- ID 4 (full name);
- ID 6 (PostScript name);
- ID 3 (unique font identifier);
- for variable fonts: ID 25 (the prefix for instance PostScript names) and the PostScript names of the named instances.

## Why it matters

When two fonts have the same name, the system treats them as one font:

- installing the second one **silently replaces** the first;
- or both stay installed and only one of them can be chosen in menus;
- PDF and print workflows embed and look up fonts by PostScript name, so a duplicate can bring the wrong font into a document.

This happens most often when a family is delivered in several lines (App, Desktop), or when a variable font and the static fonts produce the same instance names.

## How it is checked

- The fonts are split by format. OTF and TTF of the same style are expected to share names, because a user installs one or the other.
- Every name in the list above is compared across the fonts of a format. Each repeated value is one finding, with the files that share it.
- A repeated **ID 3** is rated **medium**: it rarely breaks installation but confuses font managers.
- For variable fonts, the instance PostScript names are compared across all variable fonts of that format.

## When it does not apply

- Web fonts: they are loaded by CSS under any name.
- The same style in OTF and TTF.

## How to fix

Make the names distinct. When two lines of a family must be installed side by side, add the line to every name the other line also uses — family, full name, PostScript name, unique ID: "Acme Sans App Bold", `AcmeSansApp-Bold`.

## Example

| File | ID 1 | ID 2 | ID 6 | |
|---|---|---|---|---|
| Desktop/AcmeSans-Bold.otf | Acme Sans | Bold | AcmeSans-Bold | |
| App/AcmeSansApp-Bold.otf | Acme Sans | Bold | AcmeSans-Bold | bad: same names |
| App/AcmeSansApp-Bold.otf | Acme Sans App | Bold | AcmeSansApp-Bold | good |

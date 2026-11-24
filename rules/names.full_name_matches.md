---
id: names.full_name_matches
title: Full name is the family and style names put together
summary: Name ID 4 equals ID 16 + ID 17, or ID 1 + ID 2 when the font has no typographic names; "Regular" may be left out.
category: F
level: engineer
severity: medium
action: confirm
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.full_name, names.required, names.ribbi
sources:
  - OpenType spec, name IDs 1, 2, 4, 16, 17 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
---

## What it checks

The full font name (ID 4) is the family name and the style name written together. The spec defines it as generally a combination of IDs 1 and 2, or of IDs 16 and 17, "or a similar human-readable variant", so the check asks for confirmation, not for a fix.

## Why it matters

Font managers, PDF export and some applications list a font by its full name. A full name that does not match the family and style names makes two styles look alike, or one style look like a different family, in those lists.

## How it is checked

```text
If the font has ID 16 and ID 17:
ID 16 (Typographic Family): Font Sans
ID 17 (Typographic Subfamily): Light Italic
ID16 + " " + ID17 = Font Sans Light Italic
ID 4 (Full name): Font Sans Light Italic ✔

If it has no ID 16 and ID 17, ID 1 and ID 2 are used:
ID 1 (Family): Font Sans
ID 2 (Subfamily): Bold
ID1 + " " + ID2 = Font Sans Bold
ID 4 (Full name): Font Sans Bold ✔
```

If only one of ID 16 and ID 17 exists, the missing one is replaced as the spec says: ID 16 by ID 1, ID 17 by ID 2.

**When ID 16/17 exist, ID 1 + ID 2 are not compared with ID 4.** They are for the Windows style-linking groups and may differ on purpose: Minion Pro Semibold has ID 1 "Minion Pro SmBd" and ID 2 "Regular", and its full name is "Minion Pro Semibold" (ID 16 + ID 17).

**Regular.** The spec says that for a non-regular font whose ID 2 is Regular, "Regular" is generally left out of ID 4 (Arial Black has ID 4 "Arial Black"). It is silent about an ordinary Regular font, so both are accepted. The word is left out of longer styles too: ID 17 "Dark Regular" gives the full name "Font Sans Dark".

```text
ID 1: Font Sans    ID 2: Regular
ID 4 = Font Sans Regular   ✔ exact match
ID 4 = Font Sans           Harmless: "Regular" left out
```

The result:

- exact match: passes silently;
- the same words in another case or spacing, or "Regular" left out: **Harmless**;
- other words, another order of the words, or a missing family name: **Confirm**.

## When it does not apply

- Web fonts, whose names are set by CSS.
- Fonts without ID 4, or without a family or style name: *Required name records are present* reports them.

## How to fix

Write ID 4 as "Family Style" using the same words as ID 16 and 17 (or ID 1 and 2). If the difference is intended, for example a marketing name, confirm it.

## Example

| ID 16 | ID 17 | ID 4 | Verdict |
|---|---|---|---|
| Font Sans | Light Italic | Font Sans Light Italic | good |
| Font Sans | Light Italic | Font Sans Italic Light | confirm: another order |
| Font Sans | Regular | Font Sans | harmless: "Regular" left out |

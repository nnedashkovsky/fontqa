---
id: vf.default_instance
title: The default instance owns name ID 2/17
summary: In a variable font, the named instance at the default position carries the font's own style name (ID 17 or ID 2), and no other instance does.
category: G
level: engineer
severity: medium
action: fix
applies: Installable variable fonts (outside a Web folder).
related: vf.instance_names, vf.stat
sources:
  - OpenType spec, fvar instance records | https://learn.microsoft.com/en-us/typography/opentype/spec/fvar#instancerecord
---

## What it checks

A variable font has a **default position** on its axes — the design stored directly in the outlines — and a list of **named instances** (Light, Regular, Bold…). The font's own style name (ID 17, or ID 2) describes the default. The check makes sure that:

- there is a named instance at the default position;
- that instance has the same name as ID 17 / ID 2;
- no other instance uses name ID 2 or 17.

## Why it matters

Apps show the default design under the font's own style name. If the default is Light but ID 2 says "Regular", macOS Font Book and TextEdit list two "Regular" entries — one of them actually Light — and the real default style is missing from the list. Users pick the wrong weight without knowing.

## How it is checked

1. The default position is read from `fvar`.
2. If no named instance sits there → **low, Confirm**.
3. The name of the instance at the default is compared with ID 17 (or ID 2); if they differ → medium.
4. Other instances that point to name ID 2 or 17 are listed.

## When it does not apply

- Static fonts.
- Variable web fonts (browsers use CSS names).

## How to fix

Either move the default position to the instance that ID 2/17 names (usually Regular), or give the default instance the font's own style name and move the other instance to a new name ID. In Glyphs, the default is the origin master (custom parameter Variable Font Origin); make it the master the family is named after.

## Example

| Default | Instance at default | ID 2 / 17 | |
|---|---|---|---|
| wght 400 | Regular | Regular | good |
| wght 300 | Light | Regular | bad: two "Regular" in Font Book, Light missing |

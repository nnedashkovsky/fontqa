---
id: vf.instance_names
title: Named instances have unique names
summary: No two named instances of a variable font share a style name or a PostScript name.
category: G
level: engineer
severity: medium
action: fix
applies: Installable variable fonts (outside a Web folder).
related: vf.default_instance, names.unique
sources:
  - OpenType spec, fvar instance records | https://learn.microsoft.com/en-us/typography/opentype/spec/fvar#instancerecord
---

## What it checks

Every named instance of a variable font has a style name and, optionally, a PostScript name. Within one font, both must be unique.

## Why it matters

Font menus list instances by name: a duplicate appears twice, and only one of the two can be told apart by trying. Documents store the instance by name, so a document set in one "Bold" may open in the other. Duplicate PostScript names confuse PDF export and print.

## How it is checked

The style names of all named instances are counted, and so are their PostScript names (where given). Any name used more than once is reported, separately for style names and PostScript names.

## When it does not apply

- Static fonts.
- Variable web fonts.

## How to fix

Rename the duplicate instances in the source. In Glyphs, Font Info → Exports: check instance names, and that each has its own PostScript name if set by hand.

## Example

| Instance | Coordinates | Name | |
|---|---|---|---|
| 1 | wght 700, wdth 100 | Bold | |
| 2 | wght 700, wdth 75 | Bold | bad: should be "Condensed Bold" |

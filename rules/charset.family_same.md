---
id: charset.family_same
title: Every style has the same character set
summary: Within a family, every style contains the same characters.
category: C
level: designer
severity: medium
action: confirm
applies: Each family, per line (App, Desktop, Web), static and variable fonts separately; families of two styles or more.
related: charset.store_minimum, glyphs.empty_mapped
---

## What it checks

All styles of a family — Light, Regular, Bold, their italics — have the same characters. If Bold has "ŋ" and Light does not, that is a gap.

## Why it matters

People switch styles in the middle of a text: a bold word, an italic quote. If a character exists in Regular but not in Bold, the bold word shows it in a different font, picked by the system. It looks like a mistake in the typesetting, and the user cannot fix it.

Stores such as MyFonts also expect one character set across a family.

## How it is checked

1. Fonts are grouped into families: the same family name, the same line (App, Desktop, Web), static and variable apart.
2. All characters of all styles are put together.
3. For each style, the characters it lacks from that union are listed. Styles that lack the same characters are reported together, with up to 60 of the missing characters.

The result is **Confirm**: a smaller set in some styles can be a decision, for example a Display sub-family.

## When it does not apply

- A family of one style.
- Styles of different lines (App vs Desktop) are not compared with each other.

## How to fix

- Draw the missing glyphs in the styles that lack them. In Glyphs, missing glyphs show as empty in the master where they were not drawn; for separate source files, compare glyph lists in Font Info or with a filter.
- If the difference is intended, say so in the release notes and the store description.

## Example

| Style | Characters | |
|---|---|---|
| Regular | 412 | |
| Bold | 412 | |
| Black | 398 | lacks 14: Ŋ ŋ ẞ ₹ … |

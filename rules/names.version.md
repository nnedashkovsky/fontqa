---
id: names.version
title: Version string matches the font revision
summary: Name ID 5 starts with "Version X.YYY", and that number equals head.fontRevision.
category: F
level: engineer
severity: low
action: fix
applies: All fonts, web fonts included.
related: names.family_consistent
sources:
  - OpenType spec, name ID 5 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
  - OpenType spec, head.fontRevision | https://learn.microsoft.com/en-us/typography/opentype/spec/head
---

## What it checks

A font stores its version twice:

- `head.fontRevision` — a number, read by installers and font managers;
- name ID 5 — text, read by people ("Version 1.200; build 0412").

The check makes sure ID 5 has the standard form **"Version X.YYY"** at the start and that the number is the same as in `head`.

## Why it matters

Installers and font managers decide "newer or older" by `head.fontRevision`, while users and support compare what they see in ID 5. If the two disagree, an update may not replace the old font, and nobody can tell which build a customer has.

## How it is checked

1. ID 5 must start with `Version`, a space, and a number with a dot: `Version 1.200`. Anything after it (a semicolon, build info) is ignored.
2. The number is compared with `head.fontRevision`. A difference of up to 0.0005 is allowed, because `head` stores the revision as a fixed-point number that cannot hold every decimal exactly.

## When it does not apply

Always applies, web fonts included.

## How to fix

Set the version once in the source and let the editor write both fields. In Glyphs: Font Info → Font → Version (major / minor). Avoid a versionString custom parameter that drops the "Version" prefix or uses a different number.

## Example

| ID 5 | head.fontRevision | |
|---|---|---|
| `Version 1.200; build 0412` | 1.2 | good |
| `Version 1.200` | 1.1 | bad: numbers differ |
| `1.200` | 1.2 | bad: no "Version" prefix |

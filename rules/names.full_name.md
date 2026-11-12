---
id: names.full_name
title: Full name is not too long
summary: Name ID 4 is at most 63 characters.
category: F
severity: low
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.gdi_length
sources:
  - OpenType spec, name ID 4 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
---

## What it checks

The full name (ID 4, "Acme Sans Display Bold Italic") is no longer than 63 characters.

## Why it matters

Older Mac and Office code keeps the full name in a 64-byte field and cuts longer names. Two long styles can then end up with the same cut name in lists of installed fonts. Modern systems are not affected, so the risk is low.

## How it is checked

Counts the characters of ID 4 and flags more than 63.

## When it does not apply

- Web fonts.

## How to fix

Shorten ID 4, usually by abbreviating the style part the same way as in ID 1.

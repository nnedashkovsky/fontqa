---
id: names.family_consistent
title: Family-wide name fields agree
summary: Within one family and line, the family name, version, vendor, copyright, trademark, manufacturer, designer, license and URLs are the same in every style.
category: F
severity: medium
action: fix
applies: Each family, per line (App, Desktop, Web) and separately for static and variable fonts.
related: names.version, names.unique
sources:
  - OpenType spec, name IDs 0–14, 16 | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
  - OpenType spec, OS/2.achVendID | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#achvendid
---

## What it checks

Some fields describe the family, not the style, and must be identical in every style of the family:

| Field | Where |
|---|---|
| Family | ID 16 (or ID 1) |
| Version | ID 5, up to the first `;` |
| Vendor | OS/2.achVendID |
| Copyright | ID 0 |
| Trademark | ID 7 |
| Manufacturer | ID 8 |
| Designer | ID 9 |
| Vendor URL, designer URL | IDs 11, 12 |
| License, license URL | IDs 13, 14 |

## Why it matters

A difference here almost always means that one style was exported from an older or different source: a forgotten fix, an old version number, an outdated license text. The style may then also differ in places the eye cannot see — metrics, kerning, features.

Users notice it as a font manager that shows two versions of one family, or a license text that differs between styles of one purchase.

## How it is checked

1. Fonts are grouped into families: the same family name, the same line (App, Desktop, Web), static and variable separately.
2. For each field, the values of all styles in the group are collected.
3. If there is more than one value, the most common one is taken as the expected value, and the styles with other values are listed.

## When it does not apply

- Families of one style.
- Fields that differ between lines (App vs Desktop) are not compared here — lines are grouped separately.

## How to fix

Export every style from the same state of the source. If the styles live in separate source files, copy the family-wide fields (Font Info → Font in Glyphs) from one master file into all of them before export.

## Example

| Style | ID 5 | |
|---|---|---|
| Regular | Version 1.200 | |
| Bold | Version 1.200 | |
| Black | Version 1.100 | bad: exported from an older source |

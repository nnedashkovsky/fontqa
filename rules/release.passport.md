---
id: release.passport
title: Copyright, license and credits are filled
summary: The font carries its copyright, manufacturer, designer, URLs and license text (name IDs 0, 8, 9, 11, 12, 13, 14).
category: R
level: engineer
severity: low
action: confirm
applies: Each family; installable fonts.
related: names.family_consistent, names.required
sources:
  - OpenType spec, name IDs | https://learn.microsoft.com/en-us/typography/opentype/spec/name#name-ids
---

## What it checks

The "passport" of the font — the fields that say who made it and under what terms:

| ID | Field |
|---|---|
| 0 | Copyright notice |
| 8 | Manufacturer |
| 9 | Designer |
| 11 | Vendor URL |
| 12 | Designer URL |
| 13 | License description |
| 14 | License URL |

## Why it matters

Customers and stores read these fields: font managers and design apps show them, stores check them at upload, and lawyers look at them when a font is used without a licence. A font without copyright and licence text is rejected by some stores and is harder to defend.

## How it is checked

1. An empty copyright (ID 0) → **medium, Fix**.
2. The other fields: styles with the same set of empty fields are reported together, with the list of what is empty (**low, Confirm** — a designer URL, for example, may not exist).

## When it does not apply

Web fonts — their names are often reduced on purpose.

## How to fix

Fill these fields in the source. In Glyphs, Font Info → Font: Copyright, Designer, Manufacturer and their URLs, and the License and License URL properties.

## Example

| Field | Value | |
|---|---|---|
| 0 Copyright | © 2026 Acme Type | good |
| 13 License | — | Confirm: empty |

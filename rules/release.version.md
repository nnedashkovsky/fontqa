---
id: release.version
title: Release version
summary: The font version is 1.000 or higher.
category: R
level: engineer
severity: low
action: confirm
applies: Each family.
related: names.version
sources:
  - OpenType spec, head.fontRevision | https://learn.microsoft.com/en-us/typography/opentype/spec/head
---

## What it checks

The font revision (`head.fontRevision`) is at least 1.000.

## Why it matters

Customers, stores and font managers read versions below 1.0 as beta or work in progress. A release with version 0.900 raises questions about whether the font is finished, and later updates start from a confusing number.

The result is **Confirm**: a public beta may be intended.

## How it is checked

For every font of the family, `head.fontRevision` is compared with 1.0; the fonts below it are listed.

## When it does not apply

Always applies.

## How to fix

Set the release version in the source. In Glyphs, Font Info → Font → Version.

## Example

| Version | |
|---|---|
| 1.000 | good |
| 0.950 | Confirm: reads as beta |

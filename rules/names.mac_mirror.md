---
id: names.mac_mirror
title: Macintosh name records match the Windows ones
summary: Where the font has Mac platform name records, IDs 1, 2, 4, 6, 16 and 17 equal the Windows English ones.
category: F
severity: low
action: confirm
applies: Installable fonts that carry Mac (platform 1) name records.
related: names.required
sources:
  - OpenType spec, name table, platform IDs | https://learn.microsoft.com/en-us/typography/opentype/spec/name#platform-ids
---

## What it checks

A name table can hold two sets of records: Windows (platform 3) and the old Macintosh set (platform 1, Roman encoding, English). Modern fonts usually need only Windows records. If Mac records are present, they must say the same as the Windows ones for IDs 1, 2, 4, 6, 16 and 17.

## Why it matters

Some older Mac apps and some font tools still read the Mac records first. When the two sets differ, the same font has one name in those apps and another everywhere else — and documents made in one app may not find the font in another.

The result is **Confirm**: different Mac names are almost always left over from an older export, but a few workflows set them on purpose.

## How it is checked

For each of IDs 1, 2, 4, 6, 16, 17 that exists in the Mac set, the value is compared with the Windows English value. The finding lists each pair that differs.

## When it does not apply

- Fonts without Mac records (the usual case today).
- Web fonts.

## How to fix

Either regenerate the Mac records from the Windows ones, or remove the Mac records altogether. Most current editors no longer write them unless asked.

## Example

| ID | Windows | Mac | |
|---|---|---|---|
| 1 | Acme Sans Light | Acme Sans Light | good |
| 4 | Acme Sans Light | Acme Sans Lt | bad: differ |

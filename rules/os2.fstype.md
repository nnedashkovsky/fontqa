---
id: os2.fstype
title: Embedding permissions are valid and intended
summary: OS/2 fsType has no reserved bits, no contradictory permissions, and does not forbid embedding unintentionally.
category: F
level: engineer
severity: low
action: confirm
applies: TTF and OTF files.
related: release.passport
sources:
  - OpenType spec, OS/2 fsType | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype
---

## What it checks

`fsType` in `OS/2` tells applications whether the font may be embedded in a document (a PDF, a Word file, a presentation):

| Value | Meaning |
|---|---|
| 0 | installable embedding: no restrictions |
| 2 | restricted license: must not be embedded |
| 4 | preview and print only |
| 8 | editable embedding |
| +0x100 / +0x200 | no subsetting / bitmap embedding only |

Only one of 2, 4 and 8 may be set, and the other bits are reserved.

## Why it matters

A font marked restricted cannot be embedded: PDF export, Office and some web services refuse it or replace it with another font. That is right for a license that forbids embedding, and a mistake for a font that was meant to be used freely. A value with reserved or contradictory bits is read differently by different applications.

## How it is checked

- Reserved bits set, or more than one of 2, 4 and 8: reported as a fault (low).
- Restricted license (2): reported for confirmation, since only the license can say whether it is intended.
- 0, 4, 8 and the 0x100/0x200 flags pass.

## When it does not apply

Never for TTF and OTF files; the check passes silently when the value is 0.

## How to fix

Set `fsType` to 0 (installable embedding) unless the license restricts embedding; in Glyphs it is the *Embedding* option in Font Info, Masters or Exports.

## Example

| fsType | Verdict |
|---|---|
| 0 | good |
| 2 | confirm: no embedding in PDF or Office |
| 6 | bad: restricted and preview-only at once |

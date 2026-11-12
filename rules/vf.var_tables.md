---
id: vf.var_tables
title: Variation tables for metrics
summary: A variable font has an HVAR table for its horizontal metrics (and VVAR if it has vertical metrics); missing side-bearing maps are noted.
category: G
level: engineer
severity: low
action: ok
applies: All variable fonts.
related: vf.vs_static
sources:
  - OpenType spec, HVAR | https://learn.microsoft.com/en-us/typography/opentype/spec/hvar
  - OpenType spec, VVAR | https://learn.microsoft.com/en-us/typography/opentype/spec/vvar
---

## What it checks

In a variable font, widths and side bearings change along the axes. The `HVAR` table stores these changes directly, so apps can get a glyph's width at any position without computing its outline. The check notes:

- a TrueType variable font without `HVAR` → **medium, Confirm**;
- `HVAR` with advance widths only, without left/right side-bearing maps → **Harmless**;
- vertical metrics (`vmtx`) without `VVAR` → **Harmless**.

## Why it matters

Without `HVAR`, every app that needs a width at a non-default position — that is, for every line of text — has to interpolate the outline first. Text layout becomes slower, and some apps compute widths differently from others, so lines can break differently. `HVAR` is recommended by the specification for every variable font.

The side-bearing maps and `VVAR` are recommended too, but their absence rarely shows — hence **Harmless**.

## How it is checked

Reads which of `gvar`, `HVAR`, `vmtx`, `VVAR` the font has, and whether `HVAR` contains side-bearing maps.

## When it does not apply

Static fonts.

## How to fix

Let the export build `HVAR` (and `VVAR` for fonts with vertical metrics). Current versions of the common editors do this by default; a missing `HVAR` usually means an old export pipeline or a post-processing step that dropped it.

## Example

| Font | HVAR | LSB/RSB maps | |
|---|---|---|---|
| AcmeSansVF.ttf | yes | yes | good |
| AcmeSansVF.ttf | yes | no | harmless |
| AcmeSansVF.ttf | no | — | Confirm: widths come from outlines only |

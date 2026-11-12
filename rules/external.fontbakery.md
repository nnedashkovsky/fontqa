---
id: external.fontbakery
title: Font Bakery (universal profile)
summary: Font Bakery's universal profile — an open set of several hundred checks — is run on the fonts, and its failures and warnings are listed.
category: E
level: engineer
severity: medium
action: confirm
applies: All fonts, when Font Bakery is switched on for the run.
related: external.ots
sources:
  - Font Bakery | https://github.com/fonttools/fontbakery
---

## What it checks

Font Bakery is the open-source font QA tool used by Google Fonts and many foundries. Its **universal** profile includes the general OpenType checks and many good-practice rules. When switched on, the run includes it and every failing or warning Font Bakery check becomes a finding here, with Font Bakery's own message.

## Why it matters

It covers ground this tool does not: hundreds of specific rules collected by the community, from glyph names to table versions. It is also what many clients and stores run, so its findings are worth knowing before they do.

Font Bakery's rules are written for its own goals (Google Fonts), and some do not fit a commercial release — which is why every finding is **Confirm**.

## How it is checked

1. Font Bakery 0.12.7 runs the universal profile on the OTF/TTF files.
2. **FAIL** results become medium findings, **WARN** results low ones; all are Confirm. PASS, INFO and SKIP are not listed.
3. A few Font Bakery checks are left out because they are covered elsewhere or cannot run in the browser: the OTS check (see the OTS rule), the FreeType rasterizer, the TTX round-trip, the Font Bakery version and the single-directory rule.

## When it does not apply

Runs only at the Engineer level and only when "Include Font Bakery" is switched on (in the terminal: `--fontbakery`). It is slow — about 10 seconds per font.

## How to fix

Read Font Bakery's rationale for each check (its id is in the finding) and decide whether it applies to the release. Fix the ones that do; note the others as intended.

## Example

| Font Bakery check | Status | |
|---|---|---|
| com.google.fonts/check/family/underline_thickness | FAIL | medium, Confirm |
| com.google.fonts/check/varfont/regular_wght_coord | WARN | low, Confirm |

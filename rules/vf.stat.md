---
id: vf.stat
title: STAT describes the axes and the instances
summary: A variable font has a STAT table that lists every axis, names the default for elision, and has a value for every axis position a named instance uses.
category: G
level: engineer
severity: medium
action: fix
applies: All variable fonts.
related: vf.default_instance, vf.instance_names
sources:
  - OpenType spec, STAT table | https://learn.microsoft.com/en-us/typography/opentype/spec/stat
---

## What it checks

The `STAT` (style attributes) table describes the design space in words: which axes there are, what each position on an axis is called ("Bold" at weight 700, "Condensed" at width 75), and which word to drop when it is the default ("Regular"). The check makes sure that:

- `STAT` exists;
- it lists every axis of the variable font;
- its **elided fallback name** (the name for the all-default style) points to a name that exists;
- every axis position that a named instance uses has an axis value.

## Why it matters

Windows, Office and newer apps build style names from `STAT` — for named instances and for any position the user picks with sliders. Without it, or with gaps, names come out wrong ("Bold Regular", an empty name, a number instead of a word), styles are grouped wrongly, and font menus differ between apps. CSS and some browsers also read it.

## How it is checked

1. Missing `STAT` → reported, and nothing else is checked.
2. Axes in `fvar` but not in `STAT` are listed.
3. A missing or broken ElidedFallbackNameID → **low**.
4. For each named instance, each of its axis coordinates must fall on an axis value (single value, range, or a combined value). Coordinates not covered are listed per axis.

## When it does not apply

Static fonts.

## How to fix

Add the missing axis values. In Glyphs, set Axis Location for masters and instances and, where needed, the STAT-related custom parameters (axis values, elidable names) so that every instance position has a name; then export again and check the instance names in an app that uses `STAT`.

## Example

| Axis | Instance positions | STAT values | |
|---|---|---|---|
| wght | 300, 400, 700 | Light 300, Regular 400 (elidable), Bold 700 | good |
| wdth | 75, 100 | Normal 100 | bad: no value for 75 (Condensed) |

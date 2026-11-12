---
id: release.formats
title: Formats for desktop and web
summary: Every family in the delivery ships a desktop font (OTF or TTF) and a web font (WOFF2).
category: R
level: engineer
severity: low
action: confirm
applies: The whole delivery; families are taken from the static desktop and app fonts.
related: release.file_names, post.format
sources:
  - W3C, WOFF 2.0 | https://www.w3.org/TR/WOFF2/
---

## What it checks

Each family of the delivery has at least one OTF or TTF (for desktop use and stores) and a WOFF2 (for the web).

## Why it matters

Stores accept OTF or TTF uploads, and customers install them on their computers. Web licences need WOFF2 — the compressed format every current browser supports. A family without one of them cannot be sold or used in that way, and a missing format is easy to overlook in a large delivery.

The result is **Confirm**: a delivery can be desktop-only or web-only by agreement.

## How it is checked

1. Families are collected from the static fonts outside a Web folder, by typographic family name (ID 16, or ID 1).
2. Each family must have an OTF or TTF.
3. Each family must have a WOFF2 with the same family name. Web fonts with hidden (obfuscated) names cannot be matched to a family; if there are any, they count for every family.

## When it does not apply

Always applies to a delivery.

## How to fix

Export the missing formats.

## Example

| Family | Desktop | Web | |
|---|---|---|---|
| Acme Sans | OTF | WOFF2 | good |
| Acme Display | OTF | — | Confirm: no WOFF2 |

"""The file as an operating system receives it (category A): container, required tables, counts, cmap.

Windows and macOS decide at install time whether a file is a font at all, and then read the same few
tables to name it. These checks read the bytes of the table directory themselves, so they can say
*what* is wrong where OTS only says "rejected": a sorted directory, a table inside the file, the right
outline table for the version tag, glyph counts that agree between tables, a cmap the system can use.
"""

import math
import os
import struct
import sys
from array import array

from . import Hit, check


def file_sfnt(v):
    return v.is_sfnt


def file_sfnt_raw(v):
    """TTF and OTF, including a file whose facts could not be read (they have no format then)."""
    return v.is_sfnt or v.rel.lower().endswith((".ttf", ".otf"))


VERSIONS = {b"\x00\x01\x00\x00": "TrueType", b"OTTO": "CFF", b"true": "TrueType (Apple)"}
REQUIRED = ("cmap", "head", "hhea", "hmtx", "maxp", "name", "OS/2", "post")
BITMAP_ONLY = ("CBDT", "EBDT", "sbix", "SVG ")


def directory(v):
    """The sfnt header and table directory as written in the file, or None when it cannot be read."""
    def compute():
        with open(v.path, "rb") as fh:
            head = fh.read(12)
            if len(head) < 12:
                return None
            version, n, search, selector, shift = struct.unpack(">4sHHHH", head)
            body = fh.read(16 * n)
        entries = [(t.decode("latin-1"), s, o, ln) for t, s, o, ln in
                   (struct.unpack(">4sIII", body[i * 16:i * 16 + 16]) for i in range(len(body) // 16))]
        return {"version": version, "n": n, "search": search, "selector": selector, "shift": shift,
                "entries": entries, "size": os.path.getsize(v.path)}
    return v._memo("sfnt_directory", compute)


def tags_of(v):
    d = directory(v)
    return {e[0] for e in d["entries"]} if d else set()


# ------------------------------------------------------------------ container

@check(id="sfnt.header", category="A", scope="file", applies=file_sfnt_raw, raw=True,
       title="The sfnt header and table directory are well formed",
       classification="Container / sfnt / Header and table directory",
       what="the file opens, the version tag is known, tables are sorted, inside the file, aligned and do not overlap",
       basis="The system finds every table through this directory; a wrong one makes the file unreadable or the tables misread.",
       fix="Rebuild the font with the font compiler instead of editing the file; do not patch tables by hand.", severity="high",
       symptoms=("Windows, macOS: the font does not install or is shown as damaged",))
def header(v):
    found = False
    for hit in _header(v):
        found = True
        yield hit
    if not v.ok and not found:  # the directory looks fine, yet the font library cannot open the file
        yield Hit(key="file cannot be read", measured=str(v.facts.get("error") or "unreadable")[:120], expected="a readable font",
                  summary="the file cannot be read as a font: " + (str(v.facts.get("error") or "a table is damaged")[:100]))


def _header(v):
    d = directory(v)
    if d is None:
        yield Hit(key="file shorter than the sfnt header", measured="under 12 bytes", expected="a header", summary="the file is too short to be a font")
        return
    n, entries, size = d["n"], d["entries"], d["size"]
    if d["version"] not in VERSIONS:
        yield Hit(key="unknown sfnt version", measured=repr(d["version"]), expected="00010000, OTTO or true",
                  summary=f"unknown sfnt version {d['version']!r}")
    if len(entries) < n:
        yield Hit(key="directory cut short", measured=f"{len(entries)} of {n} entries", expected=f"{n} entries",
                  summary=f"the table directory has {len(entries)} of {n} entries")
    power = 1 << (n.bit_length() - 1) if n else 0
    expected = (power * 16, int(math.log2(power)) if power else 0, n * 16 - power * 16)
    if (d["search"], d["selector"], d["shift"]) != expected:
        yield Hit(key="search fields wrong", measured=f"{d['search']}, {d['selector']}, {d['shift']}",
                  expected=", ".join(map(str, expected)), severity="medium",
                  summary="searchRange, entrySelector and rangeShift do not match the number of tables")
    tags = [e[0] for e in entries]
    dup = sorted({t for t in tags if tags.count(t) > 1})
    if dup:
        yield Hit(key="duplicate table tags", measured=", ".join(dup), expected="each tag once",
                  summary="duplicate tables: " + ", ".join(dup))
    if tags != sorted(tags, key=lambda t: t.encode("latin-1")):
        yield Hit(key="directory not sorted", measured="out of order", expected="ascending by tag", severity="medium",
                  summary="table tags are not in ascending order")
    outside = [e[0] for e in entries if e[2] + e[3] > size]
    if outside:
        yield Hit(key="table beyond the end of the file", measured=", ".join(outside), expected="inside the file",
                  summary="tables reach past the end of the file: " + ", ".join(outside))
    ordered = sorted(entries, key=lambda e: e[2])
    over = [b[0] for a, b in zip(ordered, ordered[1:]) if b[2] < a[2] + a[3]]
    if over:
        yield Hit(key="tables overlap", measured=", ".join(over), expected="separate data", severity="medium",
                  summary="tables overlap: " + ", ".join(over))
    loose = [e[0] for e in entries if e[2] % 4]
    if loose:
        yield Hit(key="tables not aligned", measured=", ".join(loose), expected="offsets divisible by 4", severity="low",
                  summary="tables do not start on a 4-byte boundary: " + ", ".join(loose))


@check(id="sfnt.required_tables", category="A", scope="file", applies=file_sfnt_raw, raw=True,
       title="The tables every font needs are present",
       classification="Container / sfnt / Required tables",
       what="cmap, head, hhea, hmtx, maxp, name, OS/2, post, and outlines (glyf with loca, or CFF/CFF2)",
       basis="OpenType spec: these tables are required; the installer and the text engines read them directly.",
       fix="Add the missing tables in the source and export again.", severity="high",
       symptoms=("Windows, macOS: the font does not install or does not appear in application menus",))
def required_tables(v):
    tags = tags_of(v)
    missing = [t for t in REQUIRED if t not in tags]
    has_glyf, has_loca = "glyf" in tags, "loca" in tags
    cff = "CFF " in tags or "CFF2" in tags
    if not (has_glyf and has_loca) and not cff and not any(t in tags for t in BITMAP_ONLY):
        missing.append("outlines (glyf + loca, or CFF)")
    elif has_glyf != has_loca:
        missing.append("loca" if has_glyf else "glyf")
    if missing:
        yield Hit(key="missing: " + ", ".join(missing), measured="missing " + ", ".join(missing), expected="all required tables",
                  summary="required tables missing: " + ", ".join(missing))


@check(id="sfnt.outline_match", category="A", scope="file", applies=file_sfnt,
       title="Outline tables match the font's declared type",
       classification="Container / sfnt / Outline format",
       what="the version tag, maxp version and outline table agree: TrueType with glyf, or CFF with OTTO; CFF matrix equals 1/unitsPerEm",
       basis="A text engine picks its rasterizer by the version tag; a mismatch makes it read outlines as the wrong format.",
       fix="Rebuild the font so the container, maxp and outline table are of one kind.", severity="high",
       symptoms=("Windows, macOS: the font does not install or draws no glyphs",))
def outline_match(v):
    d = directory(v)
    tags = tags_of(v)
    version = d["version"] if d else None
    glyf, cff = "glyf" in tags, "CFF " in tags or "CFF2" in tags
    if glyf and cff:
        yield Hit(key="glyf and CFF together", measured="both outline tables", expected="one", summary="the font has both glyf and CFF outlines")
    elif version == b"OTTO" and glyf:
        yield Hit(key="OTTO with glyf", measured="OTTO, glyf", expected="OTTO with CFF", summary="version OTTO, but the outlines are TrueType (glyf)")
    elif version in (b"\x00\x01\x00\x00", b"true") and cff:
        yield Hit(key="TrueType version with CFF", measured="00010000, CFF", expected="OTTO with CFF",
                  summary="TrueType version tag, but the outlines are CFF")
    if "maxp" in tags and (glyf or cff):
        raw = v.font.reader["maxp"][:4]
        want = b"\x00\x00\x50\x00" if cff and not glyf else b"\x00\x01\x00\x00"
        if raw != want:
            yield Hit(key="maxp version", measured=raw.hex(), expected=want.hex(),
                      summary=f"maxp version {raw.hex()} does not suit {'CFF' if cff and not glyf else 'TrueType'} outlines")
    if "CFF " in tags and "head" in tags:
        top = v.font["CFF "].cff.topDictIndex[0]
        matrix = getattr(top, "FontMatrix", None)
        upm = v.font["head"].unitsPerEm
        if matrix and abs(matrix[0] * upm - 1) > 1e-3:
            yield Hit(key="CFF FontMatrix", measured=f"{matrix[0]:g}", expected=f"1/{upm}", severity="medium",
                      summary=f"CFF FontMatrix {matrix[0]:g} is not 1/unitsPerEm (1/{upm})")


# ------------------------------------------------------------------ tables

@check(id="head.sane", category="A", scope="file", applies=file_sfnt,
       title="The head table has valid values",
       classification="Tables / head / Magic number, units per em, loca format",
       what="magicNumber is 0x5F0F3CF5, unitsPerEm is 16–16384, indexToLocFormat is 0 or 1",
       basis="OpenType spec, head: parsers refuse a file whose magic number or scale is out of range.",
       fix="Export again; set unitsPerEm to 1000 or 2048.", severity="high",
       symptoms=("Windows, macOS: the font does not install",))
def head_sane(v):
    if "head" not in tags_of(v):
        return
    head = v.font["head"]
    if head.magicNumber != 0x5F0F3CF5:
        yield Hit(key="magic number", measured=hex(head.magicNumber), expected="0x5f0f3cf5", summary=f"head magicNumber is {hex(head.magicNumber)}")
    if not 16 <= head.unitsPerEm <= 16384:
        yield Hit(key="units per em", measured=str(head.unitsPerEm), expected="16–16384", summary=f"unitsPerEm {head.unitsPerEm} is out of range")
    if head.indexToLocFormat not in (0, 1):
        yield Hit(key="loca format", measured=str(head.indexToLocFormat), expected="0 or 1", summary=f"indexToLocFormat {head.indexToLocFormat} is not 0 or 1")


@check(id="maxp.counts", category="A", scope="file", applies=file_sfnt,
       title="Glyph counts agree between tables",
       classification="Tables / maxp / Glyph count",
       what="maxp.numGlyphs matches hmtx, loca (or CharStrings in CFF) and post",
       basis="Tables are read by glyph index; a different count in one of them shifts or truncates what follows.",
       fix="Export again from the source; do not edit table counts by hand.", severity="high",
       symptoms=("Windows, macOS: the font does not install, or glyphs are missing or shifted",))
def counts(v):
    tags = tags_of(v)
    if "maxp" not in tags:
        return
    font = v.font
    n = font["maxp"].numGlyphs
    reader = font.reader
    if "hhea" in tags and "hmtx" in tags:
        nh = font["hhea"].numberOfHMetrics
        if not 1 <= nh <= n:
            yield Hit(key="numberOfHMetrics", measured=str(nh), expected=f"1–{n}", summary=f"hhea numberOfHMetrics {nh} is outside 1–{n}")
        else:
            need = 4 * nh + 2 * (n - nh)
            if len(reader["hmtx"]) < need:
                yield Hit(key="hmtx too short", measured=f"{len(reader['hmtx'])} bytes", expected=f"{need} bytes for {n} glyphs",
                          summary=f"hmtx holds {len(reader['hmtx'])} bytes; {n} glyphs need {need}")
    if "loca" in tags and "head" in tags:
        size = 4 if font["head"].indexToLocFormat else 2
        entries, rest = divmod(len(reader["loca"]), size)
        if entries != n + 1 or rest:
            yield Hit(key="loca entries", measured=f"{entries} entries", expected=f"{n + 1} for {n} glyphs",
                      summary=f"loca has {entries} entries; {n} glyphs need {n + 1} (check indexToLocFormat)")
    for tag in ("CFF ", "CFF2"):
        if tag in tags:
            have = len(font[tag].cff.topDictIndex[0].CharStrings)
            if have != n:
                yield Hit(key="CharStrings", measured=f"{have} charstrings", expected=f"{n}", summary=f"{tag.strip()} has {have} glyphs; maxp says {n}")
    if "post" in tags:
        raw = reader["post"]
        if len(raw) >= 34 and raw[:4] == b"\x00\x02\x00\x00":
            have = struct.unpack(">H", raw[32:34])[0]
            if have != n:
                yield Hit(key="post glyph names", measured=f"{have} names", expected=f"{n}", severity="medium",
                          summary=f"post lists {have} glyph names; maxp says {n}")


@check(id="cmap.usable", category="A", scope="file", applies=file_sfnt,
       title="The cmap can be used by the system",
       classification="Tables / cmap / Subtables",
       what="a Windows Unicode subtable (3,1 or 3,10), glyphs that exist, and a space",
       basis="Windows reads the (3,1) subtable (and (3,10) beyond U+FFFF) to turn text into glyphs; without it text shows as .notdef.",
       fix="Export the cmap with a Windows Unicode subtable; map every code point to a glyph that exists, and map U+0020.", severity="high",
       symptoms=("Windows: text typed in the font shows boxes or fallback characters",))
def cmap_usable(v):
    if "cmap" not in tags_of(v):
        return
    subtables = v.font["cmap"].tables
    ids = {(t.platformID, t.platEncID) for t in subtables}
    if not subtables:
        yield Hit(key="no subtables", measured="empty cmap", expected="a Unicode subtable", summary="the cmap has no subtables")
        return
    symbol = (3, 0) in ids
    if not symbol and not ({(3, 1), (3, 10)} & ids):
        yield Hit(key="no Windows Unicode subtable", measured=", ".join(f"({p},{e})" for p, e in sorted(ids)),
                  expected="(3,1) or (3,10)", summary="no Windows Unicode cmap subtable (3,1 or 3,10)")
    cmap = v.cmap
    if cmap and max(cmap) > 0xFFFF and (3, 10) not in ids and not symbol:
        yield Hit(key="no (3,10) for characters beyond the BMP", measured=f"U+{max(cmap):04X}", expected="(3,10) subtable", severity="medium",
                  summary=f"U+{max(cmap):04X} is mapped, but there is no (3,10) subtable")
    order = set(v.glyph_order)
    ghosts = sorted({g for g in cmap.values() if g not in order})
    if ghosts:
        yield Hit(key="maps to glyphs that do not exist", measured=f"{len(ghosts)} glyphs", expected="existing glyphs", glyphs=ghosts[:40],
                  summary=f"cmap points at {len(ghosts)} glyphs that do not exist")
    if not symbol and 0x20 not in cmap:
        yield Hit(key="no space", measured="U+0020 missing", expected="U+0020 mapped", severity="medium",
                  summary="U+0020 is not in the cmap")


def checksum(data):
    data = data + b"\0" * (-len(data) % 4)
    words = array("I", data)
    if words.itemsize != 4:
        words = array("L", data)
    if sys.byteorder == "little":
        words.byteswap()
    return sum(words) & 0xFFFFFFFF


@check(id="sfnt.checksums", category="A", scope="file", applies=file_sfnt_raw, raw=True,
       title="Table checksums are correct",
       classification="Container / sfnt / Checksums",
       what="every table matches the checksum in the directory, and head.checkSumAdjustment matches the whole file",
       basis="macOS Font Book and font validators verify checksums; a table edited after export fails them.",
       fix="Re-save the font with the compiler, which recomputes the checksums.", severity="medium")
def checksums(v):
    d = directory(v)
    if not d:
        return
    with open(v.path, "rb") as fh:
        data = fh.read()
    bad, head_at = [], None
    for tag, expected, offset, length in d["entries"]:
        if offset + length > len(data):
            continue
        chunk = data[offset:offset + length]
        if tag == "head" and length >= 12:
            head_at = offset
            chunk = chunk[:8] + b"\0\0\0\0" + chunk[12:]
        if checksum(chunk) != expected:
            bad.append(tag)
    if bad:
        yield Hit(key="table checksums", measured=", ".join(bad), expected="matching checksums",
                  summary="checksum does not match for " + ", ".join(bad))
    if head_at is not None and head_at + 12 <= len(data):
        stored = struct.unpack(">I", data[head_at + 8:head_at + 12])[0]
        whole = checksum(data[:head_at + 8] + b"\0\0\0\0" + data[head_at + 12:])
        if (0xB1B0AFBA - whole) & 0xFFFFFFFF != stored:
            yield Hit(key="head checkSumAdjustment", measured=hex(stored), expected=hex((0xB1B0AFBA - whole) & 0xFFFFFFFF),
                      summary="head.checkSumAdjustment does not match the file")


@check(id="os2.fstype", category="F", scope="file", applies=file_sfnt,
       title="Embedding permissions are valid and intended",
       classification="Tables / OS/2 / fsType",
       what="fsType has no reserved bits, no contradictory permissions, and does not forbid embedding unintentionally",
       basis="OpenType spec, OS/2 fsType: applications read it to decide whether the font may be embedded in documents.",
       fix="Set fsType to 0 (installable embedding) unless the license restricts it.", severity="low", action="confirm")
def fstype(v):
    if "OS/2" not in tags_of(v):
        return
    fs = v.font["OS/2"].fsType
    levels = [b for b in (0x2, 0x4, 0x8) if fs & b]
    if fs & 0xFCF1 or len(levels) > 1:
        yield Hit(key="invalid fsType", measured=f"fsType {fs} (0x{fs:04X})", expected="one of 0, 2, 4, 8, plus 0x100/0x200", action="fix",
                  summary=f"fsType {fs} has reserved bits or contradictory permissions")
    elif fs & 0x2:
        yield Hit(key="embedding restricted", measured="restricted license embedding", expected="0 unless the license forbids it",
                  summary="fsType forbids embedding in documents")

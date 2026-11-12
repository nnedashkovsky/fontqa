"""External validators (category E): OTS and Font Bakery.

Their results are computed before the checks run and passed in through the
context: OTS by the browser's own font loader (FontFace) or, in the terminal,
by the `ots` module; Font Bakery by probes.run_fontbakery. Font Bakery is
filtered: checks that only make sense for Google Fonts, or that our own checks
cover better, are dropped so the report is not padded with them (RT separated
"Latin-prerequisite and delivery-service policy" results the same way).
"""

from . import Hit, check

# Font Bakery checks not reported as issues, and why
FB_IGNORE = {
    "com.google.fonts/check/family/single_directory": "files of one family in several folders is how deliveries are organized",
    "com.google.fonts/check/fontbakery_version": "about the tool, not the font",
    "com.google.fonts/check/freetype_rasterizer": "needs FreeType, unavailable in the browser",
    "com.google.fonts/check/ttx_roundtrip": "needs a subprocess, unavailable in the browser",
    "com.google.fonts/check/ots": "covered by check E ots (browser or ots module)",
}
FB_LEVEL = {"FAIL": ("confirm", "medium"), "WARN": ("confirm", "low")}


@check(id="external.ots", category="E", scope="file",
       title="Browsers accept the font (OTS)",
       classification="Tool inspection / OTS / Rejected by browsers",
       what="the OpenType Sanitizer accepts the file",
       basis="Chrome and Firefox run every web font through OTS and drop the ones it rejects.",
       fix="Fix the table OTS names; usually a malformed or inconsistent table from post-processing.",
       severity="high", requires=("ots",),
       symptoms=("Chrome, Firefox: the web font is not loaded; the fallback font is shown",))
def ots(v):
    if v.ctx_ots not in (None, "ok"):
        yield Hit(key="rejected by OTS", measured=str(v.ctx_ots)[:200], expected="accepted",
                  summary="rejected: " + str(v.ctx_ots)[:120])


@check(id="external.fontbakery", category="E", scope="package",
       title="Font Bakery (universal profile)",
       classification="Tool inspection / Font Bakery / Universal profile",
       what="Font Bakery's universal profile, without checks listed in FB_IGNORE",
       basis="Font Bakery 0.12.7, profile universal (includes opentype).",
       fix="See the Font Bakery rationale for each check.", severity="medium", action="confirm",
       requires=("fontbakery",))
def fontbakery(views, ctx=None):
    fb = (ctx or {}).get("fontbakery")
    if not fb:
        return
    by = {}
    for r in fb["results"]:
        if r["check"] in FB_IGNORE or r["status"] not in FB_LEVEL:
            continue
        by.setdefault((r["check"], r["status"]), []).append(r)
    for (cid, status), rows in sorted(by.items()):
        action, severity = FB_LEVEL[status]
        files = sorted({r["target"] for r in rows if r["target"] != "(family)"})
        msg = next((r.get("message") for r in rows if r.get("message")), None)
        yield Hit(key=f"{cid} {status}", files=files or None, measured=status, expected="PASS",
                  summary=f"Font Bakery {cid.split('/')[-1]}: {status}" + (f" — {msg[:120]}" if msg else ""),
                  action=action, severity=severity)

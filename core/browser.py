"""Browser-only setup: install what Pyodide lacks, stub what it cannot have.

Font Bakery and Hyperglot are pure Python but import native modules. The
loop below imports the entry point, and on every ModuleNotFoundError either
installs the missing package with micropip (pure-Python wheels from PyPI) or,
when no browser build exists, replaces it with a stub. The log it returns is
part of the probe result: it says which packages came from PyPI and which
native ones were faked, so the report can tell which checks are trustworthy
in the browser.
"""

import importlib
import importlib.util
import sys

from . import hbshim
from .probes import STUBBED, stub_modules

# import name -> PyPI name, where they differ
PIP_NAMES = {
    "yaml": "pyyaml", "google": "protobuf", "dateutil": "python-dateutil",
    "PIL": "pillow", "bs4": "beautifulsoup4", "pip_api": "pip-api",
    "ots": "opentype-sanitizer", "freetype": "freetype-py", "fontTools": "fonttools",
}
# native extensions with no Pyodide build: stub at once instead of trying PyPI
NATIVE = {"freetype", "cmarkgfm", "ots", "pathops", "shaperglot", "unicodedata2",
          "lxml_html_clean", "skia", "pip_api"}

PINS = {"fontbakery": "fontbakery==0.12.7", "hyperglot": "hyperglot==0.8.1"}


class Log(list):
    """Setup log that also streams each line to the page while it happens."""

    def __init__(self, report=None):
        super().__init__()
        self.report = report

    def append(self, line):
        super().append(line)
        if self.report:
            self.report(line)


async def _install(name, log, deps=False):
    import micropip
    try:
        await micropip.install(name, deps=deps)
        log.append(f"installed {name}")
        return True
    except Exception as exc:
        log.append(f"cannot install {name}: {str(exc).splitlines()[0][:160]}")
        return False


async def _resolve(entry, log, tries=60):
    """Import `entry` (callable doing the imports), fixing missing modules as we go."""
    seen = set()
    for _ in range(tries):
        try:
            entry()
            return True
        except ModuleNotFoundError as exc:
            root = (exc.name or "").split(".")[0]
            if not root or root in seen:
                log.append(f"giving up on {exc.name}: {exc}")
                return False
            seen.add(root)
            _forget(root)
            if root in NATIVE or not await _install(PIP_NAMES.get(root, root), log):
                stub_modules(root)
                log.append(f"stubbed {root}")
            _forget_partial()
        except Exception as exc:
            log.append(f"import failed: {type(exc).__name__}: {str(exc)[:200]}")
            return False
    return False


def _forget(root):
    for name in [n for n in sys.modules if n == root or n.startswith(root + ".")]:
        del sys.modules[name]


def _forget_partial():
    """Drop half-imported fontbakery/hyperglot modules so the next try starts clean."""
    for name in [n for n in sys.modules if n.split(".")[0] in ("fontbakery", "hyperglot")]:
        del sys.modules[name]
    importlib.invalidate_caches()


async def prepare(tool, report=None):
    """Get `fontbakery` or `hyperglot` importable; returns the setup log.

    Hyperglot's language database is 788 YAML files. Pyodide's PyYAML has no C
    loader, so the first parse takes minutes; Hyperglot pickles each parsed
    language into .hyperglot-cache in the working directory as the run goes,
    and the worker keeps that file in IndexedDB after the run, so only the very
    first run in a browser pays for it.
    """
    log = Log(report)
    hbshim.install()
    log.append(f"uharfbuzz -> harfbuzzjs shim ({hbshim.version_string()})")
    if importlib.util.find_spec(tool) is None:
        await _install(PINS[tool], log, deps=False)

    if tool == "fontbakery":
        def entry():
            # Font Bakery's own loader swallows ImportError and later fails with
            # "check not found"; importing the check modules here lets the
            # resolver see which dependency is missing.
            import pkgutil
            import fontbakery.checks as pkg
            for _, name, _ in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
                importlib.import_module(name)
            # everything probes.run_fontbakery imports, so the run itself cannot miss a module
            import fontbakery.checkrunner, fontbakery.configuration, fontbakery.reporters  # noqa: E401,F401
            from fontbakery.fonts_profile import get_module, profile_factory
            profile_factory(get_module("fontbakery.profiles.universal"))
    else:
        def entry():
            import os
            import tempfile
            from hyperglot.checker import FontChecker  # noqa: F401
            from hyperglot.languages import Languages
            here = os.getcwd()
            os.chdir(tempfile.gettempdir())  # where run_hyperglot looks for the cache
            try:
                cached = os.path.exists(".hyperglot-cache")
                log.append("language database: " + ("from cache" if cached else
                           "not cached yet; the first run parses 788 YAML files (a few minutes)"))
                Languages()
            finally:
                os.chdir(here)

    ok = await _resolve(entry, log)
    log.append(("ready" if ok else "NOT ready") + f"; stubbed: {sorted(STUBBED) or 'none'}")
    return {"ok": ok, "log": list(log)}

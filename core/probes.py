"""Probes: do Font Bakery and Hyperglot give the same answers in the browser?

Phase 0 does not judge fonts with these tools yet; it asks whether they can run
at all under Pyodide, and if so whether the same call returns the same result
as in the terminal. Both environments call the functions below. In the browser
`browser.prepare_*` first installs the pure-Python packages and replaces native
ones (freetype, cmarkgfm, ots…) with stubs; any check that touches a stub fails
with MissingNative, and the comparison names exactly those checks.
"""

import importlib.abc
import importlib.machinery
import sys
import types

STUBBED = set()


class MissingNative(RuntimeError):
    """Raised when code reaches a native module that is only a stub here."""


class _StubObject:
    def __init__(self, name):
        self._name = name

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        return _StubObject(f"{self._name}.{attr}")

    def __call__(self, *args, **kwargs):
        raise MissingNative(f"{self._name} needs a native module that the browser does not have")

    def __mro_entries__(self, bases):
        return (object,)


class _StubModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []  # a package, so `import x.y` also resolves to stubs

    def __getattr__(self, attr):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        return _StubObject(f"{self.__name__}.{attr}")


class _StubLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return _StubModule(spec.name)

    def exec_module(self, module):
        pass


class _StubFinder(importlib.abc.MetaPathFinder):
    def __init__(self, roots):
        self.roots = set(roots)

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.roots:
            STUBBED.add(name.split(".")[0])
            return importlib.machinery.ModuleSpec(name, _StubLoader(), is_package=True)
        return None


_FINDER = _StubFinder(())


def stub_modules(*roots):
    """Make `import root` (and submodules) yield stubs from now on."""
    if _FINDER not in sys.meta_path:
        sys.meta_path.insert(0, _FINDER)
    _FINDER.roots.update(roots)


# ---------------------------------------------------------------- Font Bakery

def run_fontbakery(paths, profile="universal"):
    """Run a Font Bakery profile on (abs, rel) paths; one row per check × font."""
    from fontbakery.checkrunner import CheckRunner
    from fontbakery.configuration import Configuration
    from fontbakery.fonts_profile import get_module, profile_factory, setup_context
    from fontbakery.reporters import FontbakeryReporter
    from fontbakery.status import DEBUG

    rel = {p: r for p, r in paths}
    rows = []

    class Collect(FontbakeryReporter):
        def receive_result(self, result):
            super().receive_result(result)
            ident = result.identity
            where = []
            for name, index in ident.iterargs:
                try:
                    testable = runner.context.testables_by_type[name][index]
                    where.append(rel.get(testable.file, testable.file))
                except Exception:
                    where.append(f"{name}{index}")
            worst = result.summary_status
            first = next((s for s in result.results if s.status == worst), None)
            rows.append({
                "check": ident.check.id if ident.check else None,
                "target": ", ".join(where) or "(family)",
                "status": worst.name,
                "message": (str(first.message)[:300] if first and worst.name in ("ERROR", "FATAL", "FAIL", "WARN") else None),
            })

    prof = profile_factory(get_module(f"fontbakery.profiles.{profile}"))
    context = setup_context([p for p, _ in paths])
    runner = CheckRunner(prof, context=context, config=Configuration())
    reporter = Collect(runner=runner, loglevels=[DEBUG])
    runner.run([reporter])
    rows.sort(key=lambda r: (r["check"] or "", r["target"]))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    import fontbakery
    return {
        "profile": profile,
        "fontbakery": getattr(fontbakery, "__version__", None) or _dist_version("fontbakery"),
        "stubbed": sorted(STUBBED),
        "counts": dict(sorted(counts.items())),
        "results": rows,
    }


# ---------------------------------------------------------------- Hyperglot

def run_hyperglot(paths, marks=False):
    """Languages each font supports by Hyperglot's default criteria.

    With marks=True Hyperglot also shapes base+mark sequences through HarfBuzz,
    which in the browser goes through the harfbuzzjs shim.
    """
    import os
    import tempfile

    from hyperglot.checker import FontChecker

    files = []
    here = os.getcwd()
    os.chdir(tempfile.gettempdir())  # Hyperglot drops .hyperglot-cache into the cwd
    try:
        for p, r in paths:
            try:
                res = FontChecker(os.path.join(here, p)).get_supported_languages(marks=marks)
                langs = {script: sorted(isos) for script, isos in sorted(res.items())}
                files.append({"path": r, "languages": langs,
                              "count": sum(len(v) for v in langs.values())})
            except Exception as exc:
                files.append({"path": r, "error": f"{type(exc).__name__}: {exc}"[:300]})
    finally:
        os.chdir(here)
    return {"hyperglot": _dist_version("hyperglot"), "marks": marks,
            "stubbed": sorted(STUBBED), "files": files}


def _dist_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None

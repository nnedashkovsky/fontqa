"""Font QA core: font facts, inventory and probes.

The same Python package runs in two places: in the terminal (CPython with the
studio's installed fontTools) and in the browser (Pyodide inside a web worker).
Nothing in here may depend on where it runs, except the two modules that say so
in their names: `hbshim` (browser stand-in for uharfbuzz) and `browser`
(micropip installs). That is what lets the terminal run serve as the reference
the browser output is compared against.
"""

VERSION = "0.2.0"

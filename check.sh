#!/bin/sh
# Terminal run of the same Python core the page uses (the reference for the browser).
#   ./check.sh inventory <folder or files…> -o inventory.json
#   ./check.sh shape | fontbakery | hyperglot | compare …
PYTHONPATH="$(cd "$(dirname "$0")" && pwd)${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m core "$@"

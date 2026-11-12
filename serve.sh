#!/bin/sh
# Start the Font QA page on http://127.0.0.1:8765/web/ (local only).
# Extra folders: ./serve.sh --mount name=~/Downloads/Delivery  ·  references: FONTQA_REFS=/path/to/fonts
cd "$(dirname "$0")" && exec python3 serve.py "$@"

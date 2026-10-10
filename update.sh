#!/usr/bin/env bash
# Pull new/edited pages from Wikisource, rebuild index, commit + push only if the data changed.
set -euo pipefail
cd "$(dirname "$0")"
python3 wikisource.py
python3 build_index.py
python3 export_divan.py
git add export poets
# export/*.jsonl and the poems (also the Persian works from Ganjoor, ganjoor.py) are the change signal; divan.db bytes change every run
if git diff --cached --quiet -- export poets; then echo "no changes"; exit 0; fi
git add -A
git commit -q -m "data: Wikisource sync $(date -u +%F)"
git push -q origin HEAD
echo "pushed"

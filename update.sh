#!/usr/bin/env bash
# Pull new/edited pages from Wikisource, rebuild index, commit + push only if the data changed.
set -euo pipefail
cd "$(dirname "$0")"
python3 wikisource.py
python3 build_index.py
python3 export_divan.py
git add export
if git diff --cached --quiet -- export; then echo "no changes"; exit 0; fi  # export/*.jsonl is the change signal; divan.db bytes change every run
git add -A
git commit -q -m "data: Wikisource sync $(date -u +%F)"
git push -q origin HEAD
echo "pushed"

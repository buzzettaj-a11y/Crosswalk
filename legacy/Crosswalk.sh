#!/usr/bin/env bash
# Crosswalk. Run this file to start the tool.
cd "$(dirname "$0")" || exit 1
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done
if [ -z "$PY" ]; then
  echo "Crosswalk needs Python. Install it from python.org and try again."
  exit 1
fi
exec "$PY" launch.py

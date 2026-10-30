#!/usr/bin/env bash
# Crosswalk. Double-click this file to start the tool.
cd "$(dirname "$0")" || exit 1

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
done

if [ -z "$PY" ]; then
  osascript -e 'display dialog "Crosswalk needs Python, and it is not installed on this computer.

Install it once from python.org/downloads, then double-click Crosswalk again." with title "Crosswalk cannot start" buttons {"OK"} default button 1' >/dev/null 2>&1
  exit 1
fi

"$PY" launch.py

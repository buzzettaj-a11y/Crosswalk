#!/usr/bin/env bash
# Stop Crosswalk if it is still running after the browser was closed.
cd "$(dirname "$0")" || exit 1
curl -s -X POST http://127.0.0.1:8765/api/quit >/dev/null 2>&1
if [ -f crosswalk.pid ]; then
  kill "$(cat crosswalk.pid)" 2>/dev/null
  rm -f crosswalk.pid
fi
# only a Python running this folder's launch.py, never anything else
pkill -f "python[0-9.]* .*$(pwd)/launch.py" 2>/dev/null
echo "Crosswalk has been stopped. This folder can now be moved, replaced or deleted."

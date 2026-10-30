#!/usr/bin/env bash
# Install dependencies (first run) and launch the tool bound to this machine only.
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py --server.address=127.0.0.1

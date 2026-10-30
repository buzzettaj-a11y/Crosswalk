@echo off
REM Install dependencies (first run) and launch the tool bound to this machine only.
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address=127.0.0.1

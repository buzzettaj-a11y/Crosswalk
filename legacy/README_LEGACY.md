# The old build, for reference only

This folder is the old Crosswalk build, version string 2026.09.17, as Joe sent it on 2026-10-30. The screenshots and the Word and PowerPoint documents were left out to keep the repo small.

- Don't import from it, copy code from it, or ship any of it.
- Read it to learn what a rule did. Then build the rule from `SPEC.md`, which wins wherever the two differ.
- `docs/audit/` lists 101 places where this build is wrong, with the file and line for each.
- Its tests pass (1,233 checks), but they mostly check that screens answer, not that answers are right.
- Its network paths are all removed in the rewrite. They are `launch.py` (first-launch `pip install`, port probing, `webbrowser`), `run.bat` and `run.sh` (Streamlit), and `crosswalk_server.py` (a FastAPI server on 127.0.0.1).

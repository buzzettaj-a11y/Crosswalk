# Same target names on every platform (CLAUDE.md). Run inside the activated .venv.
PYTHON ?= python

.PHONY: test offline copy screens run bundle lock installer sign release docs docs-check

# Exported by make rather than written before the command, so it works in cmd.exe as well as sh.
test: export QT_QPA_PLATFORM = offscreen
test:
	$(PYTHON) -m pytest -q

offline:
	$(PYTHON) -m pytest -q tests/offline

copy:
	$(PYTHON) -m pytest -q tests/copy

run:
	$(PYTHON) -m wholecount

screens: export QT_QPA_PLATFORM = offscreen
screens:
	$(PYTHON) -m tools.screens

# M15: the user guide is generated from the copy registry. docs-check fails when the committed guide is out of date
# or a doc names a file, command or function that isn't there (A-25).
docs: export QT_QPA_PLATFORM = offscreen
docs: screens
	$(PYTHON) tools/make_docs.py

docs-check:
	$(PYTHON) tools/make_docs.py --check
	$(PYTHON) tools/check_doc_refs.py

bundle:
	$(PYTHON) tools/make_version_info.py
	$(PYTHON) tools/make_icon.py
	$(PYTHON) tools/collect_licenses.py
	$(PYTHON) -m PyInstaller --noconfirm --clean --distpath dist --workpath build build/wholecount.spec
	$(PYTHON) tools/check_bundle.py dist/Wholecount build/wholecount

# Windows only. Elsewhere they say so and fail, so a stub never looks green.
installer sign release:
	@echo "Windows only"; exit 1
	@exit 1

# Recompiles both lockfiles. pip-tools is not in either lock, so it runs from a throwaway venv on Python 3.12:
#   python3.12 -m venv /tmp/piptools && /tmp/piptools/bin/pip install pip-tools
#   make lock PIP_COMPILE=/tmp/piptools/bin/pip-compile
PIP_COMPILE ?= pip-compile
LOCK_FLAGS = --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url
lock:
	$(PIP_COMPILE) $(LOCK_FLAGS) -o requirements.lock requirements.in
	$(PIP_COMPILE) $(LOCK_FLAGS) -o requirements-dev.lock requirements-dev.in
	$(PIP_COMPILE) $(LOCK_FLAGS) -o requirements-build.lock requirements-build.in

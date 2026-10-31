# Same target names on every platform (CLAUDE.md). Run inside the activated .venv.
PYTHON ?= python

.PHONY: test offline copy screens run bundle lock

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

bundle:
	@echo "make bundle arrives in M14"
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

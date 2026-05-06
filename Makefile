.PHONY: compile smoke test test-core test-full verify

PYTHON ?= python3

compile:
	$(PYTHON) -m compileall core controller cli risnet app config utils

smoke:
	$(PYTHON) -m pytest tests/test_smoke.py

test-core:
	$(PYTHON) -m pytest tests/test_smoke.py tests/test_fixes.py tests/test_physics_fixes.py

test:
	$(PYTHON) -m pytest

test-full: test

verify: compile test

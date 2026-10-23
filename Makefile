.PHONY: help setup doctor doctor-json doctor-check lint contracts unit media golden

UV ?= uv
PYTHON ?= python3

help:
	@echo "ARO Studio — Makefile Targets"
	@echo "  setup         - Install worker package and dependencies with uv"
	@echo "  doctor        - Run human-readable aro doctor environment diagnosis"
	@echo "  doctor-json   - Run aro doctor and output machine-readable JSON"
	@echo "  doctor-check  - Run aro doctor assertion check (fails if environment is broken)"
	@echo "  lint          - Run lint checks on worker package"
	@echo "  contracts     - Run contract & schema tests (Scheduled for A02)"
	@echo "  unit          - Run unit test suite (Scheduled for A02+)"
	@echo "  media         - Run media pipeline tests (Scheduled for A06)"
	@echo "  golden        - Run G1 Golden acceptance test (Scheduled for A18)"

setup:
	@echo "==> Setting up worker environment using uv..."
	cd worker && $(UV) sync

doctor:
	@cd worker && $(UV) run aro doctor

doctor-json:
	@cd worker && $(UV) run aro doctor --json

doctor-check:
	@cd worker && $(UV) run aro doctor --check

lint:
	@echo "==> Running lint checks..."
	@cd worker && $(UV) run python -m py_compile src/aro_worker/*.py src/aro_worker/core/*.py
	@echo "Lint check PASSED."

contracts:
	@echo "ERROR: Target 'contracts' is not implemented in A01. Blocked until A02 (Contracts and shared fixtures)." >&2
	@exit 1

unit:
	@echo "ERROR: Target 'unit' is not implemented in A01. Blocked until unit test suites are introduced." >&2
	@exit 1

media:
	@echo "ERROR: Target 'media' is not implemented in A01. Blocked until A06 (FFmpeg wrapper, probe và audio extract)." >&2
	@exit 1

golden:
	@echo "ERROR: Target 'golden' is not implemented in A01. Blocked until A18 (G1 video donghua thật và restart)." >&2
	@exit 1

.PHONY: help setup doctor doctor-json doctor-check test test-cli test-unit lint contracts unit media golden

UV ?= uv
PYTHON ?= python3

help:
	@echo "ARO Studio — Makefile Targets"
	@echo "  setup         - Install worker dependencies with frozen lockfile"
	@echo "  doctor        - Run human-readable aro doctor environment diagnosis"
	@echo "  doctor-json   - Run aro doctor and output machine-readable JSON"
	@echo "  doctor-check  - Run aro doctor assertion check (fails if environment is broken)"
	@echo "  test          - Run all A01 validation tests (CLI and unit tests)"
	@echo "  test-cli      - Test aro --version command"
	@echo "  test-unit     - Run unit test suite (CLI, doctor, missing FFmpeg, capabilities)"
	@echo "  lint          - Run lint / bytecode compilation checks on worker package"
	@echo "  contracts     - Run contract & schema tests (Scheduled for A02)"
	@echo "  unit          - Alias for test-unit"
	@echo "  media         - Run media pipeline tests (Scheduled for A06)"
	@echo "  golden        - Run G1 Golden acceptance test (Scheduled for A18)"

setup:
	@echo "==> Setting up worker environment with frozen lockfile..."
	cd worker && $(UV) sync --frozen

doctor:
	@cd worker && $(UV) run aro doctor

doctor-json:
	@cd worker && $(UV) run aro doctor --json

doctor-check:
	@cd worker && $(UV) run aro doctor --check

test-cli:
	@echo "==> Testing aro --version..."
	@cd worker && $(UV) run aro --version

test-unit:
	@echo "==> Running unit test suite..."
	@cd worker && $(UV) run python -m unittest discover -s tests -v

test: test-cli test-unit

unit: test-unit

lint:
	@echo "==> Running lint / syntax checks..."
	@cd worker && $(UV) run python -m py_compile src/aro_worker/*.py src/aro_worker/core/*.py tests/*.py
	@echo "Lint check PASSED."

contracts:
	@echo "ERROR: Target 'contracts' is not implemented in A01. Blocked until A02 (Contracts and shared fixtures)." >&2
	@exit 1

media:
	@echo "ERROR: Target 'media' is not implemented in A01. Blocked until A06 (FFmpeg wrapper, probe và audio extract)." >&2
	@exit 1

golden:
	@echo "ERROR: Target 'golden' is not implemented in A01. Blocked until A18 (G1 video donghua thật và restart)." >&2
	@exit 1

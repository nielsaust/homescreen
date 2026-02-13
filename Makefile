PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: install baseline doctor smoke test-local test-device run

install:
	bash tools/bootstrap.sh

doctor:
	$(PYTHON) tools/doctor.py

baseline:
	$(PYTHON) tools/smoke.py --compile-only

smoke:
	$(PYTHON) tools/smoke.py

test-local: doctor smoke

test-device:
	bash tools/device_smoke.sh

run:
	$(PYTHON) main.py

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: install baseline doctor smoke test-local test-device run net-down net-up net-status settings-check settings-update-example settings-update-local

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

net-down:
	$(PYTHON) tools/network_sim.py down

net-up:
	$(PYTHON) tools/network_sim.py up

net-status:
	$(PYTHON) tools/network_sim.py status

settings-check:
	$(PYTHON) tools/settings_sync.py check

settings-update-example:
	$(PYTHON) tools/settings_sync.py update-example

settings-update-local:
	$(PYTHON) tools/settings_sync.py update-local

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: install configuration mqtt-topics locale-setup migrate-local-config menu-migrate-actions service-setup baseline doctor smoke test-unit perf-check menu-contract-check menu-item-scaffold menu-item-new-toggle menu-item-verify-toggle py39-guard localization-check check-local test-local test-device run net-down net-up net-status net-recover settings-check settings-update-example settings-update-local settings-prune-local-preview settings-prune-local deploy-dry-run precommit-install precommit-run security-scan

install:
	bash tools/bootstrap.sh

configuration:
	$(PYTHON) tools/configuration_wizard.py

mqtt-topics:
	$(PYTHON) tools/mqtt_topics_wizard.py

locale-setup:
	$(PYTHON) tools/locale_setup.py wizard

migrate-local-config:
	$(PYTHON) tools/migrate_local_config.py --apply

menu-migrate-actions:
	$(PYTHON) tools/migrate_menu_actions.py --apply

service-setup:
	$(PYTHON) tools/service_setup.py wizard

doctor:
	$(PYTHON) tools/doctor.py

baseline:
	$(PYTHON) tools/smoke.py --compile-only

smoke:
	$(PYTHON) tools/smoke.py

test-unit:
	$(PYTHON) tools/test_unit.py

perf-check:
	$(PYTHON) tools/perf_check.py

menu-contract-check:
	$(PYTHON) tools/menu_contract_check.py

py39-guard:
	$(PYTHON) tools/py39_guard.py

localization-check:
	$(PYTHON) tools/localization_check.py

menu-item-scaffold:
	$(PYTHON) tools/menu_item_scaffold.py wizard

menu-item-new-toggle:
	@echo "Deprecated target. Use: make menu-item-scaffold"
	$(PYTHON) tools/menu_item_scaffold.py wizard

menu-item-verify-toggle:
	$(PYTHON) tools/menu_item_scaffold.py verify

check-local: settings-check menu-contract-check py39-guard localization-check

test-local: doctor smoke test-unit menu-contract-check py39-guard localization-check

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

net-recover:
	bash tools/network_recover.sh

settings-check:
	$(PYTHON) tools/settings_sync.py check

settings-update-example:
	$(PYTHON) tools/settings_sync.py update-example

settings-update-local:
	$(PYTHON) tools/settings_sync.py update-local

settings-prune-local-preview:
	$(PYTHON) tools/settings_sync.py prune-local

settings-prune-local:
	$(PYTHON) tools/settings_sync.py prune-local --apply

deploy-dry-run:
	bash tools/deploy_on_pi.sh "$(PWD)" "main" ""

precommit-install:
	@command -v pre-commit >/dev/null 2>&1 || (echo "pre-commit not installed. Install with: brew install pre-commit" && exit 1)
	pre-commit install

precommit-run:
	@command -v pre-commit >/dev/null 2>&1 || (echo "pre-commit not installed. Install with: brew install pre-commit" && exit 1)
	pre-commit run --all-files

security-scan:
	@command -v gitleaks >/dev/null 2>&1 || (echo "gitleaks not installed. Install with: brew install gitleaks" && exit 1)
	@mkdir -p logs/security
	@gitleaks detect --no-banner --redact --source . --report-format json --report-path logs/security/gitleaks.json; \
	status=$$?; \
	echo "gitleaks report: logs/security/gitleaks.json"; \
	exit $$status

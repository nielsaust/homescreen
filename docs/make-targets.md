# Make Targets

Complete overview of available `make` commands.

## Task Navigator

- `make wizard`  
  Interactive menu to browse targets by category.
  - shows short explanations per option
  - selected target runs immediately
  - supports back (`0`) and quit (`q`)

## Onboarding & Setup

- `make install`  
  Bootstrap `.venv`, install Python deps, prepare local runtime defaults.
- `make configuration`  
  Interactive feature setup wizard.
- `make migrate-local-config`  
  One-time migration for older local config layouts.
- `make service-setup`  
  Linux/Pi systemd setup wizard (includes deploy polling interval: every X minutes/hours/days).
- `make locale-setup`  
  Linux locale helper (for date/time locale rendering).
- `make mqtt-topics`  
  Interactive MQTT topics wizard.

## Run & Device

- `make run`  
  Run app locally (`main.py`).
- `make test-device`  
  Device-oriented smoke checks for Pi.
- `make deploy-dry-run`  
  Dry-run deploy script invocation.

## Validation & Tests

- `make test-local`  
  Full local quality gate: doctor + smoke + unit + contracts + guards.
- `make check-local`  
  Config/contract/guard checks (without full smoke+unit flow).
- `make doctor`  
  Environment/runtime prerequisites check.
- `make baseline`  
  Syntax/compile-only smoke check.
- `make smoke`  
  Import/runtime smoke checks.
- `make test-unit`  
  Unit tests.
- `make perf-check`  
  Performance guard checks.
- `make menu-contract-check`  
  Menu/action/state contract validation.
- `make py39-guard`  
  Blocks unsupported `|` annotation usage for Python 3.9 runtime compatibility.
- `make localization-check`  
  Localization consistency check:
  - missing translation keys
  - cross-locale key mismatches
  - unused keys

## Menu Tooling

- `make menu-item-scaffold`  
  Interactive create/edit/remove/verify for menu items.
- `make menu-item-new-toggle`  
  Deprecated alias; forwards to scaffold wizard.
- `make menu-item-verify-toggle`  
  Verify one existing menu item wiring.
- `make menu-migrate-actions`  
  Migrate menu action metadata to current format.

## Settings Sync

- `make settings-check`  
  Compare local settings vs example keys/types.
- `make settings-update-example`  
  Add missing keys from local into `settings.json.example`.
- `make settings-update-local`  
  Add missing keys from example into local settings.
- `make settings-prune-local-preview`  
  Preview removable local-only keys.
- `make settings-prune-local`  
  Apply prune for removable local-only keys.

## Network Simulation & Recovery

- `make net-down`  
  Simulate network outage.
- `make net-up`  
  End simulated outage.
- `make net-status`  
  Show simulation status.
- `make net-recover`  
  Run network recovery script.

## Security & Hooks

- `make precommit-install`  
  Install pre-commit git hooks.
- `make precommit-run`  
  Run pre-commit hooks over all files.
- `make security-scan`  
  Run gitleaks scan and write report to `logs/security/gitleaks.json`.

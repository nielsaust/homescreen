# Deploy Plan (CI/CD to Raspberry Pi)

## Goal

On every push to `main`, deploy the latest code to the Raspberry Pi and restart the app service.

## Recommended setup

Use GitHub Actions as the trigger and SSH into the Pi.

Why this setup:
- simple and reliable
- no inbound webhook listener needed on your home network
- easy to audit in GitHub Actions logs

## Added in this repo

- Workflow: `.github/workflows/deploy-main-to-pi.yml`
- Pi deploy script: `tools/deploy_on_pi.sh`

The script does:
1. `git fetch` + `git pull --ff-only` on `main`
2. installs/updates Python deps in `.venv`
3. runs `make baseline`
4. restarts `systemd` service (for example `homescreen.service`)

## What to prepare in GitHub (Repository Secrets)

1. `PI_HOST`: IP or hostname of the Pi
2. `PI_USER`: SSH user on the Pi
3. `PI_SSH_KEY`: private key (recommended: dedicated deploy key)
4. `PI_APP_DIR`: absolute path of this repo on the Pi
5. `PI_SERVICE_NAME`: systemd service name, for example `homescreen.service`

## What to prepare on the Pi

1. Repo cloned at `PI_APP_DIR`
2. SSH public key from GitHub added to `~/.ssh/authorized_keys` for `PI_USER`
3. `sudo` rights for restarting the service, for example:
   - allow `systemctl restart <service>` without password for deploy user
4. A working `systemd` unit for the app

## First dry run

Run on Pi directly:

```bash
bash tools/deploy_on_pi.sh "/absolute/path/to/homescreen" "main" "homescreen.service"
```

When this works, push to `main` and verify workflow run in GitHub Actions.

## Rollback strategy

Minimal rollback:
1. SSH into Pi
2. `cd $PI_APP_DIR`
3. `git log --oneline -n 5`
4. `git checkout <previous-commit>`
5. `sudo systemctl restart $PI_SERVICE_NAME`

For safer production rollback later, we can move to release tags and pin deploys to tags.

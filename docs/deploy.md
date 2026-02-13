# Deploy Plan (CI/CD to Raspberry Pi)

## Goal

On updates to `main`, pull latest code on the Pi and restart the app safely.
When there is no new commit, deploy exits early and does not restart the app.

## Files in this repo

- Workflow (GitHub -> Pi over SSH): `.github/workflows/deploy-main-to-pi.yml`
- Deploy script (runs on Pi): `tools/deploy_on_pi.sh`
- `systemd` templates:
  - `deploy/systemd/homescreen.service.example`
  - `deploy/systemd/homescreen-deploy.service.example`
  - `deploy/systemd/homescreen-deploy.timer.example`

## Option A: Pi listens (recommended for home networks)

This mode does not require inbound SSH from GitHub to your Pi.
The Pi checks `main` every 2 minutes and deploys itself.

### 1) Install app service on Pi

```bash
cd /home/pi/homescreen
sudo cp deploy/systemd/homescreen.service.example /etc/systemd/system/homescreen.service
sudo sed -i 's|^User=.*|User=<YOUR_PI_USER>|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/home/<YOUR_PI_USER>/homescreen|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^ExecStart=.*|ExecStart=/home/<YOUR_PI_USER>/homescreen/.venv/bin/python /home/<YOUR_PI_USER>/homescreen/main.py|' /etc/systemd/system/homescreen.service
sudo sed -i '/^Environment=PYTHONUNBUFFERED=1/a Environment=DISPLAY=:0\nEnvironment=XAUTHORITY=/home/<YOUR_PI_USER>/.Xauthority' /etc/systemd/system/homescreen.service
sudo systemctl daemon-reload
sudo systemctl enable --now homescreen.service
```

### 2) Install deploy timer on Pi

```bash
cd /home/pi/homescreen
sudo cp deploy/systemd/homescreen-deploy.service.example /etc/systemd/system/homescreen-deploy.service
sudo cp deploy/systemd/homescreen-deploy.timer.example /etc/systemd/system/homescreen-deploy.timer
sudo sed -i 's|^User=.*|User=<YOUR_PI_USER>|' /etc/systemd/system/homescreen-deploy.service
sudo sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/home/<YOUR_PI_USER>/homescreen|' /etc/systemd/system/homescreen-deploy.service
sudo sed -i 's|^ExecStart=.*|ExecStart=/usr/bin/bash /home/<YOUR_PI_USER>/homescreen/tools/deploy_on_pi.sh /home/<YOUR_PI_USER>/homescreen main homescreen.service|' /etc/systemd/system/homescreen-deploy.service

# Allow deploy service user to restart/status homescreen.service without password.
echo '<YOUR_PI_USER> ALL=(root) NOPASSWD: /usr/bin/systemctl restart homescreen.service, /usr/bin/systemctl --no-pager --full status homescreen.service -n 20' | sudo tee /etc/sudoers.d/homescreen-deploy
sudo chmod 440 /etc/sudoers.d/homescreen-deploy

sudo systemctl daemon-reload
sudo systemctl enable --now homescreen-deploy.timer
```

### 3) Verify

```bash
systemctl status homescreen.service --no-pager
systemctl status homescreen-deploy.timer --no-pager
systemctl list-timers --all | grep homescreen-deploy
```

Notes:
- `homescreen-deploy.service` is `Type=oneshot`, so `inactive (dead)` after success is expected.
- `list-timers` may show `n/a` columns on some systemd versions; check `status` + `journalctl` for truth.
- If you previously had user-level units, disable/remove old `~/.config/systemd/user/homescreen.service`.

### 4) Dry run deploy

```bash
cd /home/pi/homescreen
bash tools/deploy_on_pi.sh "/home/pi/homescreen" "main" "homescreen.service"
```

### 5) Required runtime files (first install)

```bash
cd /home/<YOUR_PI_USER>/homescreen
cp -n settings.json.example settings.json
mkdir -p logs
```

Without these:
- missing `settings.json` -> app exits at startup
- missing `logs/` -> logger may fail creating date-based log file

## Option B: GitHub Actions pushes deploy over SSH

Use this only if your Pi is reachable from GitHub runners (public endpoint, VPN tunnel, or similar).

Prepare repository secrets:
1. `PI_HOST`
2. `PI_USER`
3. `PI_SSH_KEY`
4. `PI_APP_DIR`
5. `PI_SERVICE_NAME`

Then push to `main`; workflow `.github/workflows/deploy-main-to-pi.yml` runs:
1. SSH to Pi
2. Execute `tools/deploy_on_pi.sh`

## Rollback

```bash
cd /home/pi/homescreen
git log --oneline -n 5
git checkout <previous-commit>
sudo systemctl restart homescreen.service
```

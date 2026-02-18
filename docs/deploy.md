# Deploy (Raspberry Pi)

This document reflects the current working setup:

- `homescreen.service` runs the app.
- `homescreen-deploy.timer` polls `main` and runs `tools/deploy_on_pi.sh`.

## 1) Clone + Python env

```bash
cd /home/<USER>
git clone git@github.com:nielsaust/homescreen.git
cd homescreen

make install
make configuration
make locale-setup
```

If Pillow build fails on Pi:

```bash
sudo apt update
sudo apt install -y libjpeg-dev zlib1g-dev libfreetype6-dev libopenjp2-7-dev libtiff5-dev
.venv/bin/pip install -r requirements.txt
```

## 2) Required runtime files

`make install` now creates/updates:
- `local_config/settings.json` (from example when missing)
- `local_config/mqtt_topics.json` (from example when missing)
- `local_config/mqtt_routes.json` (from example when missing)
- `local_config/device_state_mapping.json` (from example when missing)
- `local_config/startup_actions.json` (from example when missing)
- `local_config/menu.json` (from example when missing; can prompt to overwrite when it exists)
- `logs/`
- `.sim/`

## 3) Install systemd units

Option A (recommended): run helper

```bash
make service-setup
```

Option B: manual setup (below)

```bash
sudo cp deploy/systemd/homescreen.service.example /etc/systemd/system/homescreen.service
sudo cp deploy/systemd/homescreen-deploy.service.example /etc/systemd/system/homescreen-deploy.service
sudo cp deploy/systemd/homescreen-deploy.timer.example /etc/systemd/system/homescreen-deploy.timer
```

Adjust paths/user:

```bash
sudo sed -i 's|^User=.*|User=<USER>|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/home/<USER>/homescreen|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^ExecStart=.*|ExecStart=/home/<USER>/homescreen/.venv/bin/python /home/<USER>/homescreen/main.py|' /etc/systemd/system/homescreen.service

sudo sed -i 's|^User=.*|User=<USER>|' /etc/systemd/system/homescreen-deploy.service
sudo sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/home/<USER>/homescreen|' /etc/systemd/system/homescreen-deploy.service
sudo sed -i 's|^ExecStart=.*|ExecStart=/usr/bin/bash /home/<USER>/homescreen/tools/deploy_on_pi.sh /home/<USER>/homescreen main homescreen.service|' /etc/systemd/system/homescreen-deploy.service
```

GUI environment for Tk:

```bash
sudo sed -i 's|^Environment=XAUTHORITY=.*|Environment=XAUTHORITY=/home/<USER>/.Xauthority|' /etc/systemd/system/homescreen.service
```

The shipped service file already includes:
- `After=network-online.target display-manager.service`
- `Environment=DISPLAY=:0`
- `Environment=XAUTHORITY=/home/<USER>/.Xauthority`
- `ExecStartPre` wait loop for `/tmp/.X11-unix/X0` (prevents early-start race on boot)
- `WantedBy=graphical.target`

## 4) Allow deploy service restart without password

```bash
echo '<USER> ALL=(root) NOPASSWD: /usr/bin/systemctl restart homescreen.service, /usr/bin/systemctl --no-pager --full status homescreen.service -n 20' | sudo tee /etc/sudoers.d/homescreen-deploy
sudo chmod 440 /etc/sudoers.d/homescreen-deploy
```

## 5) Git safety for timer service

If deploy service runs as root and repo is owned by `<USER>`, configure safe directory:

```bash
sudo git config --global --add safe.directory /home/<USER>/homescreen
```

## 6) Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl reenable homescreen.service
sudo systemctl start homescreen.service
sudo systemctl enable --now homescreen-deploy.timer
```

## 7) Verify

```bash
systemctl status homescreen.service --no-pager
systemctl status homescreen-deploy.timer --no-pager
systemctl status homescreen-deploy.service --no-pager
systemctl list-timers --all | grep homescreen-deploy || true
```

Notes:
- `homescreen-deploy.service` is oneshot, so `inactive (dead)` after success is normal.
- `list-timers` can show `n/a`; use `status` + journal output as source of truth.
- Deploy timer only restarts app when remote `main` actually changed.
  - If commit SHA is unchanged, logs show: `already up to date ... no changes; skipping ...`.

## 8) Logs and troubleshooting

```bash
journalctl -u homescreen.service -n 100 --no-pager
journalctl -u homescreen-deploy.service -n 100 --no-pager
```

Common startup failures:
- `no $DISPLAY` -> add `DISPLAY=:0` and `XAUTHORITY`.
- `local_config/settings.json not found` -> copy from example.
- `logs/<date>.log not found` -> create `logs/`.
- `RPi.GPIO import` error -> install/update GPIO deps on Pi.
- Service starts manually but not after reboot:
  - run `sudo systemctl reenable homescreen.service`
  - verify `systemctl get-default` is `graphical.target`
  - verify unit install target is `WantedBy=graphical.target`

If service file drifted during older setup attempts, reset it to the example:

```bash
sudo cp deploy/systemd/homescreen.service.example /etc/systemd/system/homescreen.service
sudo sed -i 's|^User=.*|User=<USER>|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^WorkingDirectory=.*|WorkingDirectory=/home/<USER>/homescreen|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^ExecStart=.*|ExecStart=/home/<USER>/homescreen/.venv/bin/python /home/<USER>/homescreen/main.py|' /etc/systemd/system/homescreen.service
sudo sed -i 's|^Environment=XAUTHORITY=.*|Environment=XAUTHORITY=/home/<USER>/.Xauthority|' /etc/systemd/system/homescreen.service
sudo systemctl daemon-reload
sudo systemctl reenable homescreen.service
sudo systemctl restart homescreen.service
```

## 9) Test deploy manually

```bash
cd /home/<USER>/homescreen
bash tools/deploy_on_pi.sh "/home/<USER>/homescreen" "main" "homescreen.service"
```

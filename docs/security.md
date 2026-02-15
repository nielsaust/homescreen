# Security Workflow

Use this workflow before making the repository public and keep it active afterwards.

## 1) Local guardrails (pre-commit)

Install tools:

```bash
brew install pre-commit gitleaks
```

Enable local git hook:

```bash
make precommit-install
```

Run manually on current tree:

```bash
make precommit-run
make security-scan
```

## 2) GitHub guardrails

In GitHub repository settings:

1. Open `Settings`.
2. Open `Security & analysis`.
3. Enable:
- Secret scanning
- Push protection (if available on your plan)

## 3) One-time history rewrite before public launch

If historical commits still contain sensitive values, rewrite history from a mirror clone.

Create mirror clone:

```bash
git clone --mirror git@github.com:nielsaust/homescreen.git /tmp/homescreen-cleanup.git
cd /tmp/homescreen-cleanup.git
```

### Remove legacy files from all commits

```bash
git filter-repo --invert-paths \
  --path tests/settings.py \
  --path tests/ask_reboot.py \
  --path tests/async-test.py \
  --path tests/async.py \
  --path tests/asyncio_test.py \
  --path tests/circular.py \
  --path tests/colors.py \
  --path tests/demaster.py \
  --path tests/doorbell.py \
  --path tests/homecalendar.py \
  --path tests/import-json.py \
  --path tests/loading.gif \
  --path tests/loading.py \
  --path tests/mqtt_controller-async.py \
  --path tests/rounded.py \
  --path tests/slider.py \
  --path tests/slideshow.py \
  --force
```

### Replace known leaked strings across all commits

Create `replacements.txt`:

```txt
regex:REDACTED_OPENWEATHER_KEY==>REDACTED_OPENWEATHER_KEY
regex:REDACTED_MQTT_PASSWORD==>REDACTED_MQTT_PASSWORD
regex:REDACTED_DOORBELL_PASSWORD==>REDACTED_DOORBELL_PASSWORD
regex:doornena\.duckdns\.org==>REDACTED_HOSTNAME
```

Run replacement:

```bash
git filter-repo --replace-text replacements.txt --force
```

Verify:

```bash
git grep -I -n "REDACTED_OPENWEATHER_KEY" $(git rev-list --all)
git grep -I -n "REDACTED_MQTT_PASSWORD" $(git rev-list --all)
git grep -I -n "REDACTED_DOORBELL_PASSWORD" $(git rev-list --all)
git grep -I -n "127.0.0.1" $(git rev-list --all)
```

Push rewritten history:

```bash
git remote add origin git@github.com:nielsaust/homescreen.git  # only if missing
git push --force --all origin
git push --force --tags origin
```

## 4) Note about mirror push errors for PR refs

When pushing from a mirror clone, GitHub may reject hidden PR refs (for example `refs/pull/*`).
This is expected and does not mean branch/tag rewrites failed.

Validate rewritten branch heads explicitly:

```bash
git ls-remote --heads origin
git ls-remote --tags origin
```

## 5) After rewrite

1. Rotate previously leaked credentials.
2. Inform collaborators to re-clone or hard reset.
3. Keep pre-commit and GitHub scanning enabled.

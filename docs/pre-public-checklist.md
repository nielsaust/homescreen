# Pre-Public Checklist

Use this as the release gate before making the repository public.

## 0. Release Gate

- [ ] Fresh clone on macOS: `make install`, `make configuration`, `make run`.
- [ ] Fresh clone on Raspberry Pi: install, service setup, reboot validation.
- [ ] Local checks pass: `make test-local`, `make settings-check`, `make menu-contract-check`.
- [ ] Final docs pass completed (install, config, MQTT/HA, deploy, troubleshooting).

## 1. Security And History

- [x] Manually inspect commit #2 and #3 in full history for sensitive data.
  - Commit #2: `e76acbc49ec948228e1e69b665be65d9fc6a1406`
  - Commit #3: `d8a5b8e7912cbeba9b095cdd3e050868e1d017f9`
  - Result: no live secrets found; placeholders only (`CHANGE_ME`, empty DSN).
  - Verification commands:
    - `git rev-list --first-parent --reverse main | nl -ba | head -n 8`
    - `git show --no-patch --pretty=fuller <commit>`
    - `git show <commit>:settings.json.example`
- [ ] Run full tree secret scan (`gitleaks detect --no-banner --redact --source .`).
- [ ] Verify removed private paths are absent from reachable history (`git rev-list --objects --all | grep ...`).
- [ ] Re-run history purge if needed, then force-push and hard-sync worktrees.

## 2. Menu Baseline And Profiles

- [ ] Define minimal default menu for public users.
- [ ] Define items that should only appear when feature is configured/enabled.
- [ ] Decide profile strategy for dev vs prod menu visibility.
- [ ] Ensure scaffold tooling supports this baseline/profile model.

## 3. Startup UX And Missing Artifact Feedback

- [ ] Detect missing `make install` artifacts at startup (`local_config/*`, `logs/`, `.venv` assumptions).
- [ ] Show actionable guidance in the setup-required screen (same UX path as `make configuration` guidance).
- [ ] Keep app usable with clear fallback (no crash/blank state when artifacts are missing).

## 4. Music UX

- [ ] Add toggle to show/hide album name.
- [ ] Add action/state wiring in menu schema.
- [ ] Update rendering logic + tests + docs.

## 5. Pi Runtime Stability

- [ ] Keep fullscreen fallback button in options (`Force fullscreen`) available in default template.
- [ ] Validate kiosk persistence after reboot and after desktop notifications.
- [ ] Confirm service unit remains clean (single `DISPLAY`/`XAUTHORITY` entries).

## 6. SSH Warning Investigation

- [ ] Investigate SSH message:
  - `channel N: open failed: connect failed: open failed`
- [ ] Check local SSH config for stale `LocalForward`/`RemoteForward`/`DynamicForward` entries.
- [ ] Check IDE/remote tooling that may auto-open forwarded channels.
- [ ] Document root cause + clean fix steps.

## 7. Documentation Finalization

- [ ] Remove user-specific absolute paths and personal references everywhere.
- [ ] Ensure docs match current config model (`local_config/*.json`, routes/topics/menu sources).
- [ ] Add/update Home Assistant automation examples (music refresh/state push).
- [ ] Final terminology consistency pass (NL/EN usage, command naming, menu wording).

# Local Config

This directory contains machine-local config that should not be committed.

## Menu config

1. Copy `menu.json.example` to `menu.json`.
2. Keep personal button layout/actions in `menu.json` (gitignored).
3. Use `make menu-item-scaffold` to create/edit/remove items; it writes to `menu.json`.

## QR items

1. Copy `qr_items.json.example` to `qr_items.json`.
2. Fill in your local values.
3. Reference item ids from menu actions using action kind `show_qr`.

Supported types:
- `url`: fields `url`
- `wifi`: fields `ssid`, `password`, optional `auth` (`WPA`, `WEP`, `nopass`), optional `hidden` (`true`/`false`)

# Local Config

This directory contains machine-local config that should not be committed.

## QR items

1. Copy `qr_items.example.json` to `qr_items.json`.
2. Fill in your local values.
3. Reference item ids from menu actions using action kind `show_qr`.

Supported types:
- `url`: fields `url`
- `wifi`: fields `ssid`, `password`, optional `auth` (`WPA`, `WEP`, `nopass`), optional `hidden` (`true`/`false`)

# homescreen

Touch-first Tkinter homescreen for Raspberry Pi + HyperPixel, built around Home Assistant and MQTT.

## Project Origin

This project is inspired by:
- [Sonos Album Art on Raspberry Pi Screen](https://www.hackster.io/mark-hank/sonos-album-art-on-raspberry-pi-screen-5b0012)

The original idea was a clean media display, but this implementation is a full rewrite with a different architecture:
- Home Assistant + MQTT based (no direct Sonos API dependency)
- weather on idle
- media + smart-home controls
- modular and easy to extend

A fun turning point: I accidentally bought the **touch** version of the HyperPixel display (which the inspiration project didn't require). That changed the direction completely. Once touch interaction was available, the possibilities became much broader, and it evolved into a practical daily interface for both information and control.

Today it's a pleasant way to glance at what matters and interact quickly, for example:
- household event alerts (e.g. laundry done, doorbell pressed)
- camera feed popups
- QR code display for Wi-Fi access
- media actions and smart-home actions from the same screen

## Feature Snapshot

- Idle dashboard view (typically weather)
- MQTT-driven updates and actions
- Touch menu with configurable actions/states
- Overlays for alerts, camera, calendar, print status, and more
- Runtime-friendly configuration and simulation tooling
- Optional modules (`enable_mqtt`, `enable_music`, `enable_weather`)

## Hardware Reference Build

- Display: [HyperPixel 4.0 Square Touch](https://shop.pimoroni.com/products/hyperpixel-4-square?variant=30138251444307)
- SBC: [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)
- Case: [HyperPixel/Pi Zero enclosure](https://cults3d.com/en/3d-model/gadget/case-for-hyperpixel-4-0-rectangle-touch-pi-zero)

## Quick Start (Local)

```bash
make install
make configuration
make test-local
make run
```

## Quick Start (Pi)

1. Flash Raspberry Pi OS (headless optional):  
   [https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)
2. Optional headless + SSH guide:  
   [https://www.tomshardware.com/reviews/raspberry-pi-headless-setup-how-to,6028.html](https://www.tomshardware.com/reviews/raspberry-pi-headless-setup-how-to,6028.html)
3. Clone this repository and follow setup/deploy docs below.

For systemd/deploy details: `docs/deploy.md`

## Common Commands

- Command navigator (interactive): `make wizard`
- Install/update environment: `make install`
- Interactive configuration: `make configuration`
- Configure MQTT topics: `make mqtt-topics`
- Run app: `make run`
- Local quality gate: `make test-local`
- Device checks (Pi): `make test-device`
- Simulate outage locally: `make net-down`, `make net-status`, `make net-up`
- Full command reference: `docs/make-targets.md`

## Documentation Map

- Architecture and runtime flow: `docs/architecture.md`
- Folder structure and boundaries: `docs/structure.md`
- Interactive setup/configuration: `docs/configuration.md`
- Testing and simulation commands: `docs/testing.md`
- Deploy to Raspberry Pi: `docs/deploy.md`
- Logging and Sentry: `docs/observability.md`
- Settings sync workflow: `docs/settings.md`
- Menu schema/actions/state system: `docs/menu-system.md`
- Localization (NL/EN system texts): `docs/localization.md`
- Music integration payload contract: `docs/music-integration.md`
- Home Assistant blueprint file: `homeassistant/media_player_to_mqtt_music_blueprint.yaml`
- Home Assistant blueprint usage and import links: `docs/home-assistant-blueprints.md`
- Security and history rewrite workflow: `docs/security.md`

# exynos-eub

**Open-source Exynos EUB (Exynos USB Booting) boot repair & flashing — a free rescue path for dead Samsung phones.**

When a Samsung phone can't boot and can't enter Download Mode, the last
conversation a technician can have with it happens at the chip level: the
Exynos **BootROM**, reachable via a **test point** on the mainboard.
Commercial tools can use this interface. This project is an open-source,
cross-platform (macOS/Linux) toolchain for the rescue half of the job:

> **test point in → EUB out → Download Mode → flash stock firmware → alive.**

## Status: pre-alpha research

| Milestone | What | State |
| --- | --- | --- |
| M0 | Test point → EUB → phone appears on USB | monitor tool ready (`tools/eub-detect.py`) |
| M1 | BootROM USB protocol + BL stage layout research | in progress |
| M2 | Host driver: talk to the BootROM (pyusb) | not started |
| M3 | End-to-end: EUB → Download Mode → flash | not started |
| M4 | Support beyond the first target + docs | not started |

**First target:** Galaxy A35 5G (**SM-A356E**, Exynos 1380) — then generalize
to other EUB-capable Exynos SoCs.

## Scope & principles

- **Rescue only.** This project implements *boot repair* (EUB → Download Mode)
  and *flashing*. Nothing else.
- **Not a ChimeraTool clone.** We only provide the *flash/rescue* option —
  we do not reimplement commercial tools' paid features (FRP removal, IMEI
  repair, carrier unlocks, MDM, ...). Those aren't needed to save a bricked
  phone, and mature professional tools do them better.
  [ChimeraTool](https://chimeratool.com) is a great product and their public
  research is part of how the community understands EUB today — if you
  service phones professionally, buy their tools.
- **Your own devices only.** Tinkering, learning, repair — not for bypassing
  other people's locks.

### ⚠️ Read this before heating any back cover

Samsung's April 2025 Exynos security update **permanently disables EUB** on
many devices by burning an eFuse — after which the BootROM *never* enumerates
on USB, and **no tool, paid or free, can use it** (documented by ChimeraTool's
public research, Oct 2025; re-confirmed Sep 2026). The reliable check is the
test point + PC test — that's what `tools/eub-detect.py` is for.
Pre-update firmware / unaffected models are still repairable.

## Known-good building blocks (from public research)

- EUB exposes itself as USB device **`04e8:1234`** (Samsung VID + BootROM PID).
- The BootROM download speaks a DNW-style protocol: 8-byte header
  (`1B 44 4E 57` + little-endian payload size), payload, 2-byte checksum,
  transferred over bulk endpoints (OUT `0x02` / IN `0x81`).
- Uploads use **Samsung-signed bootloader stages taken from the device's own
  stock firmware** — nothing needs to be forged.

(Verified from public reverse engineering — see `docs/prior-art.md`.)

## Quick start

```bash
brew install libusb            # macOS (Linux: apt install libusb-1.0-0)
python3 -m pip install pyusb

python3 tools/eub-detect.py --watch
# -> now: open the phone, short the model-specific test point, plug USB in.
#    If a 04e8:1234 device appears: EUB is alive on your unit.
```

## Roadmap details

See [`docs/PLAN.md`](docs/PLAN.md).

## Prior art & credits

- **[hubble](https://github.com/halal-beef/hubble)** — "I don't want people
  to be paying to unbrick their devices." Same mission, older SoCs;
  architectural blueprint for this project.
- **[exynos-usbdl](https://github.com/frederic/exynos-usbdl)** + forks
  ([VDavid003](https://code.chipmunk.land/max/exynos-usbdl),
  [sNegative](https://github.com/sNegative/exynos-usbdl_V2)) — BootROM USB
  protocol reverse engineering and code loading.
- **[OpenExyBootchain](https://github.com/VDavid003/OpenExyBootchain)** —
  open bootchain research.

## License

GPL-3.0-or-later (see `LICENSE`). Prior-art projects retain their own
licenses (GPL-2.0 / GPL-3.0).

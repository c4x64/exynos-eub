#!/usr/bin/env python3
"""
eub-detect.py — first-contact USB monitor for Exynos EUB (Exynos USB Booting).

Part of the exynos-eub project.

What it does
------------
Lists USB devices. With --watch it keeps polling and reports devices as they
appear — meant for the test-point session: if a `04e8:1234` device shows up
when you force EUB, the BootROM is enumerating and the phone is reachable at
the lowest level.

The descriptor strings matter: on an Exynos BootROM the
  product   string reports the SoC name (e.g. "Exynos9830"),
  serial    string carries the SoC ID + Chip ID,
  interface string carries the "USB Booting Version".
Capture all of these during the M0 session.

Requires
--------
- Python 3.8+
- pyusb:   python3 -m pip install pyusb
- libusb:  macOS: brew install libusb | Linux: apt install libusb-1.0-0

Usage
-----
    python3 eub-detect.py             # one-shot list
    python3 eub-detect.py --watch     # live monitor (for the TP session)
"""

from __future__ import annotations

import argparse
import sys
import time

try:
    import usb.core
    import usb.util
except ImportError:
    sys.exit(
        "pyusb is not installed. Install it with:\n"
        "  python3 -m pip install pyusb\n"
        "and make sure libusb is present (macOS: brew install libusb)."
    )

# Samsung's vendor ID; 0x1234 is the product ID the Exynos BootROM exposes in
# USB download (EUB) mode — the target of this whole project.
SAMSUNG_VID = 0x04E8
EUB_PID = 0x1234


def describe(dev) -> str:
    vid, pid = dev.idVendor, dev.idProduct
    tag = ""
    if vid == SAMSUNG_VID and pid == EUB_PID:
        tag = "  ** EXYNOS EUB / BOOTROM (DNW mode) **"
    elif vid == SAMSUNG_VID:
        tag = "  (Samsung VID)"

    parts = [f"{vid:#06x}:{pid:#06x}  bus {dev.bus} addr {dev.address}{tag}"]

    for attr, label in (
        ("iManufacturer", "manufacturer"),
        ("iProduct", "product"),
        ("iSerialNumber", "serial"),
    ):
        idx = getattr(dev, attr, 0)
        if idx:
            try:
                parts.append(f"{label}={usb.util.get_string(dev, idx)!r}")
            except Exception:
                pass

    try:
        # On the Exynos BootROM this string is the "USB Booting Version".
        cfg = dev.get_active_configuration()
        iface_idx = cfg[(0, 0)].iInterface
        if iface_idx:
            parts.append(f"interface={usb.util.get_string(dev, iface_idx)!r}")
    except Exception:
        pass

    try:
        parts.append(f"bcdUSB={dev.bcdUSB:#06x} bcdDevice={dev.bcdDevice:#06x}")
    except Exception:
        pass

    return "  ".join(parts)


def all_devices():
    try:
        return list(usb.core.find(find_all=True))
    except usb.core.NoBackendError:
        sys.exit("No libusb backend found. macOS: brew install libusb")
    except usb.core.USBError as exc:
        print(f"[!] USB error while enumerating: {exc}", file=sys.stderr)
        return []


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--watch", action="store_true",
        help="keep polling and report devices as they appear",
    )
    ap.add_argument(
        "--interval", type=float, default=1.0,
        help="poll interval in seconds for --watch (default: 1.0)",
    )
    args = ap.parse_args()

    if not args.watch:
        devs = all_devices()
        if not devs:
            print("No USB devices found (or no permission to enumerate them).")
        for d in devs:
            print(describe(d))
        return

    print("Watching for USB devices — press Ctrl+C to stop.")
    print("For the EUB test: short the test point, then plug the phone in.")
    print("Success looks like a new 04e8:1234 device below.\n")

    seen = set()
    try:
        while True:
            for d in all_devices():
                key = (d.bus, d.address, d.idVendor, d.idProduct)
                if key not in seen:
                    seen.add(key)
                    print(f"[+] {time.strftime('%H:%M:%S')}  {describe(d)}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

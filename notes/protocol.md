# Exynos EUB / BootROM USB protocol — public knowledge baseline

Source: hubble (halal-beef, GPL-2.0) source read 2026-10-19, plus the
exynos-usbdl lineage. This describes the SoC families hubble supports
(7580 … 9830). **Unverified for Exynos 1380** — that is exactly what M0/M2
on the bench will confirm.

## Enumeration

The BootROM exposes a single USB device:

- VID:PID = `04e8:1234`
- `iProduct` = **SoC name** (e.g. `Exynos9830`; ancient chips report
  `SEC S5PC210 Test B/D`)
- `iSerialNumber` = **SoC ID (15 chars) + Chip ID (16 chars)**, ASCII
- interface 0 `iInterface` = **USB booting version** string (hubble reads
  characters 12:16)

`tools/eub-detect.py` prints all of these during the M0 session.

## Download frame ("DNW 4.0")

Each upload is one bulk transfer containing a single self-describing frame:

```
offset 0:   1B 44 4E 57     magic = "\x1bDNW"
offset 4:   u32 LE          total frame length = 8 + payload + 2
offset 8:   payload         (e.g. one slice of sboot.bin)
end-2:      FF FF           checksum field — fixed 0xFFFF (not validated)
```

- Bulk OUT endpoint `0x02` (hubble uses a 50 s write timeout).
- One frame per part; "chunking" is done by splitting the source file into
  named slices, not by cutting frames.

## Responses / BootROM crash dumps

- Bulk IN endpoint `0x81`; read 512-byte chunks until empty.
- A response containing `UUUUUUUU` = **BootROM crash/exception dump**; the
  ASCII dump is parsed as 8-character records:
  chunk[1] version, chunk[2] SoC ID, chunk[3..4] chip IDs, chunk[9] reset
  status, chunk[11] OM status, chunk[13] key bank address, chunk[26] boot
  device info, chunk[27..28] status registers.
- hubble enables response reads only when the SoC's JSON has
  `response_support: true`.

## Upload sequence (how Download Mode is reached)

hubble uploads, from the device's own stock BL tar (Samsung-signed images):

1. `sboot.bin`, split into named parts (9830: fwbl1 / epbl / bl2 / lk /
   el3_mon) and sent strictly in the order of the SoC's split table.
2. Extra files listed in `files_to_send` (9830: `ldfw.img`, `tzsw.img`).
3. BootROM chains the stages → the device lands in **Download Mode**.
   The bootloader is left wiped: stock firmware must be flashed immediately
   after.

Per-SoC tables are `ExynosData/<SoC>.json` in hubble:

```json
{
  "response_support": true,
  "files_to_send": ["ldfw.img", "tzsw.img"],
  "bootloader_splits": {
    "fwbl1.bin":   {"start": 0,       "length": 12288},
    "epbl.bin":    {"start": 12288,   "length": 77824},
    "bl2.bin":     {"start": 90112,   "length": 442368},
    "lk.bin":      {"start": 897024,  "length": 2621440},
    "el3_mon.bin": {"start": 3518464, "length": 262144}
  }
}
```

## 1380 TODO list (derived from the above)

1. **M0:** capture `iProduct` / `iSerialNumber` / interface strings of the
   real device with `tools/eub-detect.py --watch`.
2. **M1:** from the stock BL tar, locate the 1380 stage images (still
   `sboot.bin`, or a new layout?) and derive the split table — names,
   offsets, lengths, order.
3. **M2:** confirm `response_support` behaviour on the bench device
   (read-only), then implement the DNW sender in Python/pyusb.

## Host-side notes

- Linux: detach the kernel driver and claim interface 0 before transfers
  (libusb); macOS usually needs no detach.
- Windows requires a libusb-based driver bound to `04e8:1234`.

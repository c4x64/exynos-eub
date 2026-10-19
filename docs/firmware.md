# Stock firmware: acquisition & handling

## Why

Boot repair always needs the **device's own stock firmware**:

- the BootROM upload uses Samsung-signed bootloader stages from `BL_*.tar.md5`
- after the phone reaches Download Mode, the full stock package is flashed

Rules of the game:

- model must match exactly (SM-A356E).
- the binary revision ("bit") being flashed must be **>= the bit on the
  device** — downgrades are refused by the bootloader (SW REV check).
- prefer the newest package available for your region.

## Downloading (macOS/Linux): samloader-rs

We use [topjohnwu/samloader-rs](https://github.com/topjohnwu/samloader-rs)
(Apache-2.0; prebuilt macOS/Linux/Windows binaries; parallel FUS download with
on-the-fly decryption, md5 verification, and a heimdall-derived flasher).

```bash
# what's current? (region = CSC code: INS, BTU, XAA, ...)
samloader check-update --model SM-A356E --region INS
# -> A356EXXSBDZH1/A356EODMBDZH1/A356EXXSBDZH1/A356EXXSBDZH1

# download the latest package (≈9.6 GB zip; decrypted while downloading)
samloader download --model SM-A356E --region INS -d firmware/
```

The zip contains the familiar Odin tars: `BL_*.tar.md5`, `AP_*.tar.md5`,
`CP_*.tar.md5`, `CSC_*.tar.md5`, `HOME_CSC_*.tar.md5`.

## Working with the packages: `tools/odin-fw.py`

```bash
python3 tools/odin-fw.py list BL_*.tar.md5                          # members + md5
python3 tools/odin-fw.py extract AP_*.tar.md5 boot.img.lz4 --decompress -o stock/
python3 tools/odin-fw.py replace AP_custom.tar.md5 --set boot.img.lz4=stock/boot.img.lz4
python3 tools/odin-fw.py pack -o boot-only.tar.md5 boot.img.lz4=stock/boot.img.lz4
```

## Flashing (once the phone is in Download Mode)

In order of preference on macOS/Linux:

1. `samloader flash` — same tool as above; verifies md5, heimdall-derived
2. `odin4` — Linux; Thor-protocol based
3. heimdall — legacy; weak on modern Exynos boards, last resort

> Boot repair leaves the bootloader wiped: **flash the full stock package
> immediately after the phone lands in Download Mode.**

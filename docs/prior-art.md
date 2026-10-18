# Prior art notes

## hubble (halal-beef) — GPL-2.0

- Python. Recovers Exynos devices that fall back to USB download (`usbdl`),
  using the device's own stock **BL tar**.
- Supported/tested SoCs: 9830 (S20 series), 9820 (S10), 9810 (S9, Note 10
  Lite), 9610 (A51), 7885 (A8 2018), 7580 (A5 2016). **Nothing newer.**
- Key protocol facts (read from its source):
  - BootROM USB ID: **`04e8:1234`**
  - Download header: magic `1B 44 4E 57` ("DNW") + u32 LE size; payload;
    2-byte checksum (set to `0xFFFF`).
  - Bulk OUT endpoint `0x02`; bulk IN `0x81` used for optional device
    responses (per-SoC `response_support` flag in `ExynosData`).
  - The BootROM can report "crash info" (SoC ID, reset status, key bank,
    boot device info, ...) — useful bring-up diagnostics.

## exynos-usbdl (frederic) — GPL-3.0

- C. "Unsigned code loader for Exynos BootROM" exploiting a bootROM USB-stack
  bug on 8890/8895. Its docs also describe the *normal* path: sending a
  **signed** bootloader over USB (which is what factory/service tooling does).
- Forks:
  - `sNegative/exynos-usbdl_V2` — packaging/variants.
  - `VDavid003` (code.chipmunk.land/max/exynos-usbdl) — adds a "new exploit"
    (missing length checks on some USB control requests, swapped read/write
    semantics) and targets 7870/7885/9610/9810/9830/3830.
    README caveat: Samsung's April 2025 Exynos updates **fuse off EUB**
    entirely on newer SoCs.

## OpenExyBootchain (VDavid003) — GPL-2.0

- Early-stage open bootchain replacement (BL1 only; 7870/7885). Research
  reference, not a dependency.

## EUB fuse timeline (community reporting)

- **April 2025:** Samsung Exynos updates begin permanently disabling EUB via
  eFuse on affected devices. A fused device forced to EUB stays silent on USB.
  (ChimeraTool public research, 2025-10-21; re-confirmed in their Sep 2026
  A-series test-point article.)
- KG-locked (KnoxGuard) devices already lacked EUB before that.
- Practical check = test point + PC test → `tools/eub-detect.py`.

## Related reading

- XDA "eub" tag — e.g. S20 boot-repair threads (Feb 2025), Tab A T585 test
  point thread (Jul 2026: device enumerates, "no free program detects it").
- fredericb.info — BootROM dumping / USB stack reverse-engineering posts.

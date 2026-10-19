# The EUB-disable fuse — findings in the stock bootloader

Status: mechanism located; version bracketing experiment in progress (2026-10-19).

## Background
ChimeraTool's Oct 2025 research reported that an April-2025-and-later Exynos
firmware update permanently disables EUB (the bootROM's USB booting mode) on
"most" devices, by burning an eFuse — seemingly in the block that gates USB
enumeration. The exact OTP field was not publicly named.

## Findings in A356EXXSBDZH1 (SM-A356E, Aug 2026 build)
`sboot.bin` (the LK/download-mode bootloader) contains an eFuse (OTP) write
path with a dedicated field:

- `[EFUSE] Set usb_disable_se1!`  ← strongest candidate for the EUB-killing fuse
- `[EFUSE] USB boot! Skip efuse write`  ← the write path is skipped when the
  current boot is a USB boot (an EUB session does not burn the fuse itself;
  a fuse already burned still blocks EUB with no software recovery)
- gating strings: `[EFUSE] it's not commercial, skip...`,
  `[EFUSE] commercial bit is not set. skip checking..`
- the same code table also programs: `enable_antirbk`, `model_id`, `jtag_lock`,
  `warranty bit`, `etc_market`, `otp_tune`, `USE_ROM_SEC_BOOT`, RB counters.

The `usb_disable` string appears only in `sboot.bin` — not in ldfw/tzsw/tzar/
fld/keystorage (checked).

Open question: was the field added by the April-2025 update, or did it exist
earlier and the April update changed the condition that writes it?

## Version bracketing experiment
FUS version list (SM-A356E / INS, `samloader check-update --all`) shows a
clean break: all builds up to **A356EXXS4AYB2 (Feb 2025)** are "class A";
**A356EXXU4BYDC (Apr 2025)** is the first "class B" build — matching the
reported April-2025 update. Comparison downloads:

| Build | Date | Purpose |
| --- | --- | --- |
| A356EXXS4AYB2 | Feb 2025 | last pre-April build |
| A356EXXU4BYDC | Apr 2025 | first April-2025 build |

Then: extract both `sboot.bin`, compare `usb_disable_se1` presence and the
surrounding code region.

## Implication for our unit
The phone ran the latest patch (class B, 2026) → it booted builds whose
bootloaders carry the fuse-write path. If a single normal boot executed it,
the fuse is burned and EUB will not enumerate. The test-point enumeration
test (M0) remains the only definitive check for this unit.

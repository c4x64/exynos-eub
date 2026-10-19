# The EUB-disable fuse — findings in the stock bootloader

Status: mechanism located and disassembled; bracketing — `usb_disable_se1`
absent in the May-2025 bootloader, present in the Aug-2026 one
(Feb-2025 download pending) (2026-10-19).

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

## Version bracketing — results

FUS version list (SM-A356E / INS) shows a clean break: all builds up to
**A356EXXS4AYB2 (Feb 2025)** are "class A"; **A356EXXU4BYDC (Apr 2025)** is
the first "class B" build. Comparison of the extracted `sboot.bin` images
(all exactly 8 MiB, LZ4-packed in the BL tar):

| Build | Date | `usb_disable_se1` in sboot.bin |
| --- | --- | --- |
| A356EXXS4AYB2 | Feb 2025 | *(download in progress)* |
| A356EXXU4BYDC | Apr/May 2025 | **absent** — 0 hits |
| A356EXXSBDZH1 | Aug 2026 | **present** — 1 hit |

Every other piece of the fusing machinery (`fuse history`, `otp_tune`,
`Update RP`, `etc_market`, `This is a device for Market`, `forced fusing`,
the USB-boot skip, `SE1_RECOVERY_DISABLE` aside) is **already present** in
the May-2025 bootloader. Only the SE1 USB-disable field is new in the
8.5-era build.

## Write-site (Aug-2026 image, disassembled with tools/arm64-xref.py)

- `0x17baec` — `[EFUSE] Set usb_disable_se1!` log sits directly in front of
  the OTP write call (`0x10bf30`). Written only when the preceding check
  (`0x17c9d8`) returns 0 **and** context field `+0xd0 != 1`.
- `0x17bb0c` — `[EFUSE] Set otp_tune!` → write call `0x10c094`, guarded by
  field `+0xc8 != 0x200`.
- `0x17b744` — `[EFUSE] USB boot! Skip efuse write`: on a USB boot (EUB
  session) the whole fusing block is skipped (jumps to `0x17b94c`).
- `0x17b9f8` — `[EFUSE] it's not commercial, skip...`: the fusing/RP path is
  gated on the commercial bit; `[EFUSE] forced fusing operation 0200`
  (`0x17bb70`) is the market-fusing path (`This is a device for Market` →
  `Set etc_market!`).

Open question (partially answered): the SE1 field did not exist in the
May-2025 bootloader → it was added somewhere between May 2025 and Aug 2026,
i.e. in the One UI 8.5 era (the same era as the D2 gate). The Feb-2025
check will confirm the "class A" side.

## Implication for our unit
The phone ran the latest patch (class B, 2026) → it booted builds whose
bootloaders carry the fuse-write path. If a single normal boot executed it,
the fuse is burned and EUB will not enumerate. The test-point enumeration
test (M0) remains the only definitive check for this unit.

## Who runs the policy (disassembly)

The fusing engine has two entry points (`0x17b050`, `0x17b31c`) into one
body. Its call sites in the image:

- `0x1134c0` — inside the boot-time **"Init ddi/efuse"** sequence
  (`'Init ddi/efuse'` log right before the call). The instruction right
  after it tests `0xf2f28` — the same USB-boot detector used by
  `[EFUSE] USB boot! Skip efuse write`.
- `0x175df8` — a key/OTP-write flow.
- `0x17e13c` — a bootloader-integrity flow (strings `'usr'`,
  `'BOOTLOADER'`, `'LDFW'`, `'VBMETA'` nearby).

Inside the engine the SE1 write is gated by:

- the USB-boot skip (`0xf2f28`),
- a state check at `0x17c9d8` (reads context fields `+0x68` / `+0x70`,
  the market / `etc_market` fusing state; nonzero result skips the write),
- context field `+0xd0 == 1` also skips it,
- the surrounding block only runs for commercial devices
  (`it's not commercial, skip...`).

Takeaway: the burn is **state-conditional policy run from normal-boot
init**, not a simple "firmware version ≥ X" switch. A device that never
executed a qualifying normal boot (e.g. bricked early, or failing the
state checks) can keep a live EUB even on an 8.5-era build. Per-device
ground truth remains the enumeration test.

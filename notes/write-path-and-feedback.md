# Write paths & on-device feedback — design notes

Requirements added 2026-10-19:

1. **Download Mode may not be exposed** after the EUB stage upload (e.g. gate
   screens like D2, or bootloader states that never open Loke USB). The tool
   must still be able to patch/replace partition images **directly from the
   EUB session**.
2. **Chimera-style on-screen image** so the operator can see the device is
   connected and the payload is running.

## 1. Write-path decision tree (M2/M3)

### P1 — Download Mode exposed (preferred)
Upload the stock boot chain (hubble-style). If the phone lands in Loke /
Thor Download Mode:
- flash **targeted** packages instead of full firmware where possible:
  boot-only, BL-only, or full stock (`tools/odin-fw.py` builds these);
- flasher: `samloader flash` (heimdall-derived) or `odin4`.

### P2 — Download Mode NOT exposed (direct from EUB)
Evidence vendor tools do this routinely in EUB mode:
- ChimeraTool EUB procedures that run without DM: FRP/MDM/KnoxGuard/
  warning-logo patches, CSC change, factory reset, backup/restore, Read Codes.
- Sigma Plus docs: "Now you are free to run different service operations,
  like Remove FRP or **Read/Write operations**" — in EUB mode.

Free-community route for us: the **exynos-usbdl** family — exploit the
BootROM USB-stack bug(s) to run **unsigned AArch64 payloads**:

| Payload class (VDavid003 fork) | What it gives |
| --- | --- |
| `*_dump_bootrom` | read BootROM memory (recon) |
| `*_boot_nonsecure` | bypass secure-boot checks → load unsigned stages |
| `*_boot_custom_key` | boot with a custom security key (7870/7885/9610) |
| `*_set_pshold` | power/reset control |

Existing payload targets: 7870, 7885, 850, 8890, 8895, 9610, 9810, 990.
**Exynos 1380: unknown** — whether a comparable BootROM bug exists has to be
determined on the bench (controlled experiment, after M0).

If we get code execution on 1380, this unlocks:
- a storage-write payload → direct partition replace (boot/recovery/vbmeta,
  and credential/Knox-state partitions behind gate screens);
- eventually payload-driven display init (Phase C below).

## 2. On-device feedback (M4)

### Phase A — available now (no extra code on device)
- When the uploaded stock chain runs, the screen shows the Samsung boot logo
  → then either the **D2 gate screen**, the **Download Mode screen**, or off.
- **Any lit screen = payload is alive.** Document expected progression.
- Host side: watch for USB re-enumeration (new VID:PID) after the chain
  boots — automatic "connected" confirmation in the tool output.

### Phase B — once writes work (persistent splash)
- Store our own splash image into the boot-logo partition
  (`up_param` / `param` family — model-specific) → custom image on every
  boot, Chimera-style.
- Reachable via P1 (flash the logo partition in DM) or P2 (direct write).

### Phase C — stretch (live framebuffer)
- Display init + bitmap blit from a running payload. Requires reversing the
  1380 display controller/panel init path. Only if A and B land first.

## Status / dependencies

- Everything here depends on **M0**: if the unit's EUB is eFuse-disabled
  (April 2025+ update), it never enumerates and none of this applies.
- M0 also captures the baseline (descriptor strings) needed before any P2
  experiments.

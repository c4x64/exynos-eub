# USB data-R/W mode sweep — SM-A356E / Exynos 1380 (S5E8835) / A356EXXSBDZH1 (One UI 8.5)

Goal: enumerate every firmware-supported way to talk to the device over USB with **real
data read/write** (memory / block / partition level), for rescuing a bricked unit without
a service center. Everything below is from the Aug-2026 BL (A356EXXSBDZH1) unless noted,
cross-checked against the Feb-2025 and May-2025 builds, plus the AP/CP/CSC of the same
package (super.img stream-scanned, recovery/vendor_boot ramdisks unpacked).

Host-side cleanliness: all analysis is offline firmware RE; nothing was sent to the phone.

## TL;DR — mode inventory

| # | Mode | USB identity | Capability | Enter / gates | Status on this unit |
|---|------|--------------|-----------|----------------|---------------------|
| 1 | **EUB / EDL ("USB boot", DNW)** | `04e8:1234` | **Full R/W** — RAM code upload, memory read/write, unbrick any BL stage | SoC-side: missing/invalid BL, USB-boot request register + WDT/reset, test point. **Killed by OTP fuse `usb_disable_se1` / `SE1_RECOVERY_DISABLE` (only in 8.5-era BL)** | **Dead** (fused) |
| 2 | **Download Mode (ODIN MODE)** | `04e8:685d` | **Partition R/W** (flash everything, read PIT; service tools read/erase too) | Vol-Dn + cable. Gates: FMM/D2 screen, CC mode, MDM, Auto Blocker, KG, installment | **Unknown — decisive physical test; the SC/OTP fuse does not affect it** |
| 3 | **Upload / RDX (RAM dump)** | (USB serial + bulk) | **Read-only** — RAM/core dumps to PC ("Save to PC"), save to device | Crash / WDT / key combos | Not storage R/W |
| 4 | **Userspace `fastbootd` (recovery)** | `18d1:4ee0` | Flash logical partitions (fastboot protocol) | Recovery menu → BCB `boot-fastboot` (**BL support absent**, see §5) + `ro.boot.fastbootd` prop + token; recovery itself FMM-gated | **Not reachable here** |
| 5 | **Android-side gadget modes** | `04e8:685b/685e` (mass storage ±adb), `04e8:685d` (dm+acm) | UMS LUN expose (PC R/W to the backed file), Samsung DM serial function | `sys.usb.config=...` from booted One UI / factory framework | Post-revival only |
| 6 | **AT/ENG factory handshake** | CDC-ACM | `AT+ENGMODES=1,3,1` only; no storage commands found | Factory rigs | — |
| 7 | **Chip-off / ISP / JTAG** | — | Full R/W | Physical work, sockets, skill | Last resort |

Only **#1** and **#2** give the host actual storage access over USB. On a fused unit #1 is
gone; #2 is the only remaining candidate and its gates are unknown until tested.

## 1. EUB / EDL path (dead — fuse)

- `fld.bin` (4 MiB BL member) is the **EUB first-loader**: strings `Ready to rx EPBL`,
  `EPBL rx done`, `EPBL Header Pass/Fail`, plus device identity (`SM-A356E`,
  `A356EXXSBDZH1`, `SignerVer03`). EUB flow = ROM enumerates `04e8:1234`, host uploads
  the first loader, which receives subsequent stages ("EPBL") over USB.
- sboot logs for the same path: `[Bootloader] USB Loading Done` (per stage),
  `to enter USB booting after WDT reset`, `[EFUSE] USB boot! Skip efuse write`.
- Fuse fields (`usb_disable_se1`, `SE1_RECOVERY_DISABLE`) exist **only** in the Aug-2026
  BL; Feb/May-2025 builds have neither (see `eub-fuse-mechanism.md` for the table,
  write-site, call sites). Nothing else about this path changed across the three builds.
- Boot-mode dispatcher (file offsets ~`0x113340`–`0x1135xx`) contains the
  **`sbl_check_edl` / "EDL Download Start.."** flow, prints `T32 Fuse Start.. Clear SBOOT..`,
  `Init ddi/efuse`, writes a USB-boot request magic `0x12345601` to `0x1186080c`, and is
  gated twice by the USB-boot predicate `0xf2f28` (reads `0x11860810`: bit3 via `0xf2b34`
  plus mode nibbles). `0xf2f28` is also the predicate the fuse engine consults before
  burning `usb_disable_se1` (the "skip efuse write" exception).
- Consequence unchanged from earlier analysis: on a fused 8.5 unit the SoC will not enter
  EUB; the request-register dance by LK cannot revive it.

## 2. Download Mode (ODIN MODE) — the only remaining USB R/W channel

- DM entry chain (offsets for future reference): FMM gate fn `0x186de8` → FMM state getter
  `0x171bec`; then DM entry `0x154090` (CC-mode block check `0x17a424`; UI loop). Strings:
  `FMM Lock is On, Download mode is not Allowed!...`, `DOWNLOAD IS BLOCKED BY CC MODE`,
  `MDM MODE. CAN'T DOWNLOAD.`, `AUTO BLOCKER IS ON. CAN'T DOWNLOAD (%s)`,
  `All binaries are not allowed to be flashed due to KG locked.(%s)`, `... remaining
  installment balance`.
- Mode selector `0x1547ac` (called only from dispatcher `0x113588`): queries bootparam ids
  `0`/`3`/`4`/`0x11`; `0x11==5` → the `MID` print path, `0xd` → another; magic `0xabcf`
  in bootparam 3 supplies a 16-bit value stored at `0x2bdee0`; the USB-boot predicate
  `0xf2f28` decides between `w20=9` and the `0x11f91c` path (`w20=2`).
- Bootparam accessor `0x150424` (getter) / `0x1503a0` (pointer getter): arrays rooted at
  `0x5666b4` — 64 words, 20 × 2 KiB records (`0x40..0x53`), 10 × 10 KiB records (`0x54..0x5d`).
- `FASTBOOT MODE` (string `0x2550a8`) sits next to `ODIN MODE` in the DM screen string
  block, but **sboot contains no fastboot-protocol strings** (`getvar`, `download:`,
  `flash:`, `erase:` absent) → not a protocol implementation; treat as a title/state
  string, not a channel.
- The DM/Odin path is **not** killed by the SE1 fuse. It is gated by the lock stack above
  and by the D2 credential flow (`notes`/community: hidden OTP screen, 8-digit code, RSA
  public key only — no DIY code derivation). Physical cable test is the only way to learn
  this unit's gate state, and it is free.

## 3. Upload / RDX mode — read-only

- Strings: `DS:start dumpsink`, `DS:finish dumpsink`, `dumpsink_bootdev`,
  `usb:rdx_probe_info`, `1. Get RAMDUMP with RDX, then reboot`, `[Save to PC] connect a
  usb cable`, `[Save to Device] POWER_KEY for 7s`, `[Reconnect USB] VOL_UP+POWER_KEY for
  3s`, `[Reboot Device] VOL_DN+POWER_KEY for 3s` (menu printer at `0x19de90`).
- Host side receives RAM dumps; no block/partition read/write exposed.

## 4. Recovery ramdisk contents (userspace fastbootd present)

Unpacked `recovery.img` ramdisk (LZ4 legacy, 86.2 MB decompressed, 753 cpio entries):

- `system/bin/fastbootd` (1,575,392 B; Samsung `sec_fastbootd.cpp` strings), 
  `android.hardware.fastboot@1.0/1.1.so`, `res/images/fastbootd.png`,
  `libfusesideload.so`, `libengmode2lite_recovery.so` (EM token engine),
  `usb_f_dm.ko` / `usb_f_dm1.ko` (Samsung ttyGS "Samsung Android DM"/"DM1" gadget
  functions), `dwc3-exynos-usb.ko`, `usb_notify_layer.ko`, etc.
- Recovery `system/etc/init/hw/init.rc`: configfs gadget `g1`, `ffs.fastboot`, and
  `on property:sys.usb.config=fastboot` → `idProduct 0x4EE0` + `start fastbootd`.
- Gates found in the recovery binary: `ro.boot.fastbootd` → `allowFastbootd = %s`,
  `no property, so don't allow fastbootd`; plus `the device has / does not have a
  fastbootd token, so allow / don't allow fastbootd` (string sits in libsnapshot code
  area; token source not identified — likely bootloader/service-provided).
- AOSP chain would be: recovery menu "Enter fastboot" (label exists in
  `librecovery_ui.so`) → BCB `boot-fastboot` → BL boots fastbootd. **But sboot has zero
  hits for `boot-fastboot` (and for `boot-recovery` / `boot-bootloader`) in all three
  builds — byte-level grep.** Only `boot-skiprecovery` (1×) exists. So this platform's BL
  does not implement the fastbootd BCB hop; fastbootd is not reachable from a dead unit,
  and its prop/token gate makes it non-obvious even post-revival.

## 5. Android-side gadget modes (need a booted OS)

From the streamed super image, `init.rc` gadget configs:

- `sys.usb.config=mass_storage` → `idProduct 0x685B`, `mass_storage.0` LUN with
  `removable 1 cdrom 1 ro 0` (+ `ss_mon`), adb variant `0x685E` (`mass_storage + ffs.adb`).
  This is the literal "USB with data R/W" userspace mode (UMS) — the LUN is a file/blockdev
  chosen by the framework (`/config/usb_gadget/g1/functions/mass_storage.0/lun.0/file` is
  `chown system` + `chmod 0660` at boot; `sys.usb.config = mass_storage` is set by
  UsbDeviceManager).
- `sys.usb.config=dm,acm` (+adb) → `idProduct 0x685D` with `dm.gs7` (Samsung `usb_f_dm`)
  and `acm.gs6` — a **userspace download-mode-identity serial function** used by Samsung
  service/emergency tooling.
- Framework vestiges: `usb_mass_storage_enabled` / `def_usb_mass_storage_enabled` settings,
  `usb_mass_storage_restrict` notification string.
- All of this requires running One UI (or factory framework): irrelevant to a dead phone,
  relevant after a successful revive.

## 6. AT / ENG / connector

- Only `AT+ENGMODES`, `AT+ENGMODES=`, `AT+ENGMODES=1,3,1`, `+ENGMODES:` found; handler
  region prints `ENG MODE : DEV DEVICE`. No memory/flash AT commands.
- EDL flow also touches MUIC/connector: `ifconn_init`, `ifconn_usb_en`,
  `ifconn_com_to_uart`, `muic standalone mode`, `CC UART`.

## 7. Cross-version identity (why 8.5 adds no new doors)

- The 3,392-byte DT **overlay** embedded in sboot at `0xed000` (sha1 `eb99c26ea282`) is
  **byte-identical** in Feb-2025, May-2025 and Aug-2026. It contains `no-dboot;`,
  `feature/dump-mode { enabled=1, fastboot-support=1 }`, security flags
  (`seh_enable`, `seclog_enable`, `sdm_enable`, …), `policy/exception` pre-log bits.
  (Interpretation of `no-dboot` / `fastboot-support` deliberately left open — the values
  predate the EUB fuse and are not device-specific.)
- Every unlock/access mechanism inventoried earlier (FMM/D2, CC/MDM/AutoBlocker/KG,
  unlock-key machinery, jig/upload, AT+ENGMODES, fastboot-screen strings) exists
  identically in all three builds. The **only** delta in 8.5-era firmware remains the
  `usb_disable_se1` / `SE1_RECOVERY_DISABLE` fuse machinery (see `eub-fuse-mechanism.md`).

## Tooling used (committed with this note)

- `tools/arm64-dis.py` — arbitrary-range ARM64 disassembly with string annotations.
- `tools/arm64-callers.py` — "who calls this offset" across a flat sboot image
  (requires capstone `detail=True`).
- `tools/arm64-xref.py` — ADRP/ADR string-reference finder.
- `tools/fw-scan.py` — streaming tar.md5 + LZ4 member pattern scanner (no extraction;
  used for the 11.2 GB decompressed super.img scan).

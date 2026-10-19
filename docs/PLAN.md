# Project plan

Goal: free, open, cross-platform boot repair for EUB-capable Exynos devices.
Primary test target: **SM-A356E** (Galaxy A35 5G, Exynos 1380).

## Milestones

### M0 — First contact (bench)
- Open the phone per its model guide; short the EUB test point; plug USB.
- Run `tools/eub-detect.py --watch`.
- **Success:** a new USB device `04e8:1234` appears (+ descriptor dump captured).
- **Failure:** nothing enumerates → suspect eFuse-disabled EUB (April 2025+
  firmware). Re-check cable/contact/fuse facts before concluding.
- Artifacts: `notes/m0-capture.md`, raw descriptor dump.

### M1 — Desk research
- Study hubble's protocol (DNW header, EP 0x02 / 0x81, per-SoC `ExynosData`).
- Study exynos-usbdl (control requests, signed vs exploit loading paths).
- Acquire SM-A356E stock firmware (bootloader package) — legitimate sources only.
- Map the Exynos 1380 boot chain: which parts exist, where the stage splits are.
- Artifacts: `notes/protocol.md`, `notes/bl-layout.md`.

### M2 — Host driver + write-path decision tree
- Python + pyusb: detect → handshake → stage upload → execute.
- Read-only probing first; **no storage writes** until the protocol notes exist.
- Validate on the bench device; use BootROM crash-info responses as diagnostics.
- **Never assume Download Mode appears.** Decide the write path dynamically:
  1. Loke/Thor Download Mode (preferred, if exposed after stage upload)
  2. direct payload-mediated partition writes from the uploaded EUB state
     (research; needs a 1380-compatible unsigned-payload path)

### M3 — End-to-end rescue (with or without Download Mode)
- Path A — Download Mode exposed: flash **targeted** packages (boot-only,
  BL-only, or full stock) via `samloader flash` / `odin4`. Rescue without
  ever needing a working OS or a normal-bootable device.
- Path B — Download Mode not exposed: replace the needed partitions directly
  from the EUB session (payload write service; R&D as above). Likely targets:
  boot/recovery/vbmeta plus credential/Knox-state partitions behind gate
  screens (e.g. D2).
- Validate the full loop: bricked → stock boot.

### M4 — Feedback & reach
- **On-device screen feedback** (Chimera-style "is it connected?")
  - Phase A (available now): built-in screens as status — boot logo / D2 /
    Download Mode screen — plus host-side detection of USB re-enumeration.
  - Phase B (once writes work): store our own splash into the boot-logo
    partition (`param` / logo family) → custom image on boot.
  - Phase C (stretch): live framebuffer from a payload — needs display RE.
- SoC data for more Exynos chips (1330/2400 relatives; help wanted).
- Upstream 1380 support to hubble (if it fits there) and/or cross-link.
- Docs: per-model test-point notes (with permission), macOS guide.

## Unknowns (honest list)

1. Is EUB even enabled on the bench unit (eFuse)? → answered at M0.
2. BootROM USB protocol generation on 1380 — same DNW-style flow? → M0/M2.
3. BL package layout and split points for 1380 — no public work exists today.
4. Download-mode flash protocol version for 1380 (Loke vX / Thor) for M3.

## Bench safety rules

- Only devices you own.
- No writes/probing attempts until M1 protocol notes exist; M0 is passive.
- Test point work: model-specific diagram only, light contact, ESD care.
- Never blindly repeat an action the device answered with a crash dump.

## Environment

- macOS (Apple Silicon) or Linux host.
- `brew install libusb`, `python3 -m pip install pyusb`.
- Reference repos kept locally under `opensource/` (hubble, exynos-usbdl +
  forks, OpenExyBootchain) — see `docs/prior-art.md`.

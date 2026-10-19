# SM-A356E BL package layout (A356EXXSBDZH1)

## BL tar members (decompressed sizes)
| member | size | notes |
| --- | --- | --- |
| fld.bin | 4,194,304 | purpose unknown (4 MiB) |
| sboot.bin | 8,388,608 | the bootloader chain (8 MiB) |
| up_param.bin | 3,062,544 | boot logo / param UI partition |
| ldfw.img | 8,388,608 | MCU load-firmware (8 MiB) |
| tzsw.img | 2,097,152 | TrustZone software |
| tzar.img | 5,767,952 | TZ agent loader (?) |
| harx.bin | 3,145,728 | unknown |
| dtp.bin | 2,097,152 | unknown |
| keystorage.bin | 524,288 | keystore blob |
| vbmeta.img | 10,128 | verified boot metadata |
| uh.bin | 294,312 | unknown |
| ssp.img | 770,048 | SSP (secure/sensor payload) |

md5 trailer: factory (FUS) zips use an `md5sum`-style text line
(`<32-hex>  <name>\n`); classic single-file tars use the raw 16-byte trailer.
`tools/odin-fw.py` verifies both.

## sboot.bin
- Header at 0: `98 00 00 00 | ff ca 3d 40 | "head" (as bytes daeh) | ...`
  (0x98 = 152 — likely header length of the stage format).
- SoC id confirmed: `v2.6(release):HEC1-240827-Android13-5.15-PT72590-s5e8835-...`
  → **S5E8835 = Exynos 1380**.
- Stage names referenced in the chain: EPBL, BL2 (variants BL2_LP4 / BL2_LP5),
  EL3_MON (EL3 monitor), LDFW, TZSW, DP, ICM, "ONE_OF_LDFW_SP_SSP".
  USB loading protocol prints `[<STAGE>] USB Loading Done` per part.
- Name table ~0x58E0-0x5AB0: `bl2`, `bootload`, `el3_mon`, `ldfw`, `tzsw`,
  `dp`, `bl2_lp4`, `bl2_lp5`, `dt`.
- Coarse region map (zero-run segmentation):
  - [0x0 .. ~0xC500] EPBL stage (messages, loader logic, name table)
  - [~0xF000 .. ~0x31000] code
  - [~0x230000 .. ~0x2DA734] LK region (download mode): `odin`, `keystorage`,
    `vbmeta`, `up_param`, EFUSE write path
  - [~0x31C000 .. ~0x4F0DF0] large zero run (~1.9 MiB)
  - [~0x59AFB0 .. ~0x5D2818] final region (contains the "sboot.bin" string)
  - zero padding to 0x7FFFC0
- Exact stage boundaries NOT yet derived. hubble-style blind slices need
  per-SoC RE; the 1380 chain may instead be device-driven (named part
  requests). Derive/confirm at bench (M2) before any upload.

## Next steps
1. Bracket the EUB fuse build — see `notes/eub-fuse-mechanism.md`.
2. M0 test-point session → decide EUB alive vs fused for the unit.
3. M2: protocol confirmation with the bench device before any writes.

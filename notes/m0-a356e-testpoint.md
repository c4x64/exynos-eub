# M0 — SM-A356E (Galaxy A35 5G): opening + test point

Prep done 2026-10-19. Bench session: not yet run (pending phone opening).

## Opening the phone (back cover only)

The A35 has a glued glass back. You only need the back cover off to reach the
mainboard — no screen or battery removal for the EUB test point.

Tools: hair dryer / heat mat (≈50–60 °C along the edges), suction cup, thin
plastic pick, Phillips #000, 91 %+ IPA, ESD care (discharge yourself; avoid
metal tools near pads).

Guides:
- Text + photos + video (full): https://vrm24.com/instructions/how-to-disassemble-samsung-galaxy-a35-5g-sm-a356
- Video — back panel only (quickest): https://www.youtube.com/watch?v=j569dTL8-_E
- Video — full teardown: https://www.youtube.com/watch?v=0Q_P2hw8a7I
- LML logic-board access guide: https://www.lmlrepair.com/guides/phone/samsung/galaxy-a/Galaxy-A35-5G-(A356-2024)/logic-board-repair

Notes:
- Heat in ~2-3 min passes, keep the heat moving; glass can crack if rushed.
- A35 back glass has no fingerprint ribbon (safer than older models).
- Keep screws organised; mid-frame hides the battery connector.

## Test point (EUB)

Community (non-vendor) sources — verify the exact pads against your board
revision/frame before touching anything:
- "Samsung A35 SM-A356E Testpoint EUB Mode FRP Bypass": https://www.youtube.com/watch?v=LFFzfgiThVs
  (frame-checked 2026-10-19; annotated still at ~20–58 s)
- "Samsung A35 A356E FRP Unlock Chimera Tool (Test Point) (EUB Method)": https://www.youtube.com/watch?v=yiJPs8S_dMA
  (YouTube blocked the download attempt — watch in browser)
- HalabTech A35 EUB folder (login needed; fallback if videos unclear): https://support.halabtech.com/index.php?a=downloads&b=folder&id=185410

Location seen in video #1 (verify on the real board before touching):
- On the mainboard, **directly below the rear camera module**, near the left
  board edge in the video's orientation (camera upper-left, shield cans right).
- Inside the marked circle: a **small exposed pad** on the blue PCB (dark dot),
  possible second gold pad at the circle's lower-left edge. At 720p the exact
  pad layout is at the limit of what the video shows — scrub the clip at
  0.25x speed to confirm pad count and technique on your unit.
- General technique (vendor docs, same idea): keep the point shorted while you
  plug the USB-C cable in, release after the device is seen on USB.

Session procedure (strictly passive for M0):
1. Phone OFF, unplugged; back cover off; board exposed.
2. Start the monitor first: `python3 tools/eub-detect.py --watch`.
3. Short the test point per the video frame — keep it shorted.
4. Plug the USB-C cable into the Mac (while still shorted).
5. Watch for enumeration: expect VID:PID **04e8:1234**
   (= Exynos BootROM / DNW mode = EUB alive).
6. Release the short after the device is seen.
7. Retry a few times with clean contact if needed.
8. If it never enumerates after several careful attempts → suspect
   eFuse-disabled EUB (see README warning). Stop there; no writes, nothing to
   gain by more poking.

Hard rules:
- M0 = read-only. No writes, no commands sent to the device, no flashing.
- Never bridge neighbouring pads; use a fine probe/insulated tweezers.
- If the device answers anything unexpected (crash dump, disconnect loop),
  note it and repeat exactly: do not improvise.

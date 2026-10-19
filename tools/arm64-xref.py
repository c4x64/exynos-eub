#!/usr/bin/env python3
"""Find code references to string literals in a raw ARM64 image.

Bootloader images extracted from Samsung firmware are flat, headerless
binaries, so ordinary disassembly tooling cannot resolve references from
code to string literals. Strings are usually materialized with the
position-independent pattern:

    ADRP Xd, page            ; ADD Xd, Xd, #offset
    ADR  Xd, #offset

Both are PC-relative, so the distance between an instruction and the
address it computes does not depend on the load address of the image.
Treating file offsets as addresses therefore yields, for every ADRP+ADD
pair, the file offset of the literal it references.

Usage:
    arm64-xref.py IMAGE "literal" ["literal" ...] [--disasm N] [--near N]

Options:
    --disasm N   after locating a reference, disassemble ~N instructions of
                 context around it (requires capstone) and annotate the
                 literals it references.
    --near N     also report references whose computed target is within N
                 bytes of the literal (use if the image region is not
                 4 KiB-aligned relative to its load address).
"""

import argparse
import re
import struct

MASK_ADR = 0x9F000000
VAL_ADRP = 0x90000000
VAL_ADR = 0x10000000


def sign_extend(v, bits):
    if v & (1 << (bits - 1)):
        return v - (1 << bits)
    return v


def decode_adrp(w, at):
    imm = (((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 0x3)
    return (at & ~0xFFF) + (sign_extend(imm, 21) << 12)


def decode_adr(w, at):
    imm = (((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 0x3)
    return at + sign_extend(imm, 21)


def collect_refs(data):
    """Scan the image, return {target_offset: [(insn_off, kind), ...]}."""
    refs = {}
    unpack_from = struct.unpack_from
    n = len(data)
    prev = None
    for f in range(0, n - 3, 4):
        (w,) = unpack_from("<I", data, f)
        top = w & MASK_ADR
        if top == VAL_ADRP:
            page = decode_adrp(w, f)
            refs.setdefault(page, []).append((f, "adrp"))
            prev = (f, w & 0x1F, page)
            continue
        if top == VAL_ADR:
            refs.setdefault(decode_adr(w, f), []).append((f, "adr"))
            prev = None
            continue
        if prev is not None and prev[0] == f - 4 and (w & 0xFF000000) == 0x91000000:
            sh = (w >> 22) & 0x3
            if sh in (0, 1) and (w >> 5) & 0x1F == prev[1] and (w & 0x1F) == prev[1]:
                imm12 = (w >> 10) & 0xFFF
                t = prev[2] + (imm12 << (12 if sh == 1 else 0))
                refs.setdefault(t, []).append((prev[0], "adrp+add"))
        prev = None
    return refs


def printable_at(data, off, minlen=4, maxlen=48):
    if off < 0 or off >= len(data):
        return None
    buf = []
    for c in data[off:off + maxlen]:
        if 0x20 <= c < 0x7F:
            buf.append(chr(c))
        else:
            break
    if len(buf) >= minlen:
        return "".join(buf)
    return None


def disasm_window(data, center, n_insn):
    try:
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    except ImportError:
        print("  [!] capstone not installed; skipping disassembly")
        return
    start = max(0, center - 4 * (n_insn // 2)) & ~3
    end = min(len(data), center + 4 * (n_insn // 2) + 8)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    print(f"  --- disassembly around 0x{center:x} ---")
    regs = {}
    for insn in md.disasm(data[start:end], start):
        w = int.from_bytes(data[insn.address:insn.address + 4], "little")
        top = w & MASK_ADR
        note = ""
        if top == VAL_ADRP:
            page = decode_adrp(w, insn.address)
            m = re.match(r"(x\d+),", insn.op_str)
            if m:
                regs[m.group(1)] = page
            note = f"  ; page 0x{page:x}"
        elif top == VAL_ADR:
            t = decode_adr(w, insn.address)
            m = re.match(r"(x\d+),", insn.op_str)
            if m:
                regs[m.group(1)] = t
            s = printable_at(data, t)
            note = f"  ; -> 0x{t:x}" + (f" {s!r}" if s else "")
        elif (w & 0xFF000000) == 0x91000000:
            m = re.match(r"(x\d+), (x\d+), #(0x[0-9a-f]+)", insn.op_str)
            if m and m.group(2) in regs:
                val = regs[m.group(2)] + int(m.group(3), 16)
                regs[m.group(1)] = val
                s = printable_at(data, val)
                note = f"  ; -> 0x{val:x}" + (f" {s!r}" if s else "")
        elif insn.mnemonic.startswith("ldr") or insn.mnemonic.startswith("ldrb") or insn.mnemonic.startswith("ldrh"):
            m = re.match(r"(x\d+), \[(x\d+)(?:, #(0x[0-9a-f]+))?\]", insn.op_str)
            if m and m.group(2) in regs:
                off = int(m.group(3), 16) if m.group(3) else 0
                val = regs[m.group(2)] + off
                s = printable_at(data, val)
                note = f"  ; -> 0x{val:x}" + (f" {s!r}" if s else "")
        elif insn.mnemonic in ("bl", "b") and insn.op_str.startswith("#"):
            pass
        print(f"    {insn.address:08x}: {insn.mnemonic:<8} {insn.op_str}{note}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("strings", nargs="+")
    ap.add_argument("--disasm", type=int, default=0, metavar="N")
    ap.add_argument("--near", type=int, default=0, metavar="N")
    args = ap.parse_args()

    data = open(args.image, "rb").read()
    print(f"scanning {args.image} ({len(data):,} bytes) ...")
    refs = collect_refs(data)
    print(f"collected {sum(len(v) for v in refs.values()):,} ADRP/ADR-derived references")

    for s in args.strings:
        needle = s.encode()
        occ = []
        i = data.find(needle)
        while i != -1:
            occ.append(i)
            i = data.find(needle, i + 1)
        print(f"\nliteral {s!r}: {len(occ)} occurrence(s)")
        cands = []
        for o in occ:
            rs = o
            while rs > 0 and 0x20 <= data[rs - 1] < 0x7F:
                rs -= 1
            for c in (o, rs):
                if c not in cands:
                    cands.append(c)
        for o in cands:
            hits = list(refs.get(o, []))
            if not hits and args.near:
                for t, lst in refs.items():
                    if abs(t - o) <= args.near:
                        hits.extend((at, kind + f"+near({t - o:+d})") for at, kind in lst)
            if not hits:
                print(f"  @0x{o:x}: no direct ADRP/ADR reference found")
                continue
            by_kind = {}
            for at, kind in hits:
                by_kind.setdefault(kind, []).append(at)
            for kind, ats in by_kind.items():
                ats = sorted(set(ats))
                print(f"  @0x{o:x}: {len(ats)} ref(s) via {kind}: " + ", ".join(f"0x{a:x}" for a in ats))
            if args.disasm:
                seen = set()
                for at, kind in sorted(hits):
                    if at in seen or "adrp" == kind:
                        continue
                    seen.add(at)
                    disasm_window(data, at, args.disasm)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Disassemble arbitrary byte ranges of a raw ARM64 image, annotating
PC-relative string references (ADRP+ADD, ADR, literal-pool loads).

Bootloader images from Samsung firmware are flat, headerless binaries;
--disasm of arm64-xref.py only works around discovered string references.
This tool dumps any range, which is useful when hunting a function whose
address is known from a nearby string reference.

Usage:
    arm64-dis.py IMAGE --at 0xOFFSET [--at 0xOFFSET ...] [--len N] [--max N]

    IMAGE       raw flat ARM64 binary (e.g. sboot.bin)
    --at        file offset to start disassembling at (repeatable)
    --len       bytes to disassemble per --at (default 256, hex or dec)
    --max       cap total printed instructions (default 1200)
"""
import argparse
import sys

try:
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_MEM, ARM64_OP_REG
except ImportError:
    sys.exit("[!] needs capstone:  python3 -m pip install capstone")


def getstr(data, off, maxlen=72):
    if not (0 <= off < len(data)):
        return None
    end = data.find(b"\0", off, off + maxlen)
    if end == -1:
        end = off + maxlen
    chunk = data[off:end]
    if len(chunk) < 3:
        return None
    printable = sum(1 for b in chunk if 32 <= b < 127)
    if printable / len(chunk) < 0.9:
        return None
    return chunk.decode("ascii", "replace")


def pool_str(data, addr):
    """Try to interpret a literal-pool value at addr as a string pointer
    or as a raw string start."""
    s = getstr(data, addr)
    if s:
        return s
    for size in (8, 4):
        if 0 <= addr <= len(data) - size:
            val = int.from_bytes(data[addr:addr + size], "little")
            s = getstr(data, val)
            if s:
                return f"{s}  (ptr {val:#x})"
    return None


def dis_range(md, data, start, length, budget):
    pages = {}
    end = min(len(data), start + length)
    n = 0
    for ins in md.disasm(data[start:end], start):
        if n >= budget:
            print("        ... (budget reached)")
            break
        n += 1
        line = f"  {ins.address:08x}: {ins.mnemonic:<8} {ins.op_str}"
        ann = ""
        try:
            if ins.mnemonic == "adrp" and len(ins.operands) == 2:
                dst, imm = ins.operands
                if dst.type == ARM64_OP_REG and imm.type == ARM64_OP_IMM:
                    pages[dst.reg] = imm.imm
            elif ins.mnemonic == "add" and len(ins.operands) == 3:
                dst, src, imm = ins.operands
                if (dst.type == ARM64_OP_REG and src.type == ARM64_OP_REG
                        and imm.type == ARM64_OP_IMM and src.reg in pages):
                    pages[dst.reg] = pages[src.reg] + imm.imm
                    s = getstr(data, pages[dst.reg])
                    if s:
                        ann = f"   ; -> '{s}'"
            elif ins.mnemonic == "adr" and len(ins.operands) == 2:
                dst, imm = ins.operands
                if dst.type == ARM64_OP_REG and imm.type == ARM64_OP_IMM:
                    pages[dst.reg] = imm.imm
                    s = getstr(data, imm.imm)
                    if s:
                        ann = f"   ; -> '{s}'"
            elif ins.mnemonic in ("ldr", "ldrsw", "ldrsw") and len(ins.operands) == 2:
                src = ins.operands[1]
                if src.type == ARM64_OP_MEM:
                    base = src.mem.base
                    if base == 0:  # PC-relative literal load
                        disp = src.mem.disp
                        for cand in (disp, ins.address + disp):
                            s = pool_str(data, cand)
                            if s:
                                ann = f"   ; pool -> '{s}'"
                                break
        except Exception:
            pass
        print(line + ann)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--at", action="append", required=True,
                    help="offset to disassemble (hex with 0x, or decimal)")
    ap.add_argument("--len", default="256",
                    help="bytes per --at (hex with 0x, or decimal; default 256)")
    ap.add_argument("--max", type=int, default=1200,
                    help="max instructions printed in total (default 1200)")
    args = ap.parse_args()

    data = open(args.image, "rb").read()
    length = int(args.len, 0)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True

    budget = args.max
    for spec in args.at:
        start = int(spec, 0)
        print(f"=== disassembly @ {start:#x} ({length} bytes) ===")
        used = dis_range(md, data, start, length, budget)
        budget -= used
        if budget <= 0:
            break


if __name__ == "__main__":
    main()

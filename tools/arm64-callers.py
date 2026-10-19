#!/usr/bin/env python3
"""Find BL/B (branch-with-link / branch) call sites to target addresses in a
raw flat ARM64 image (e.g. Samsung sboot.bin).

Usage:
    arm64-callers.py IMAGE TARGET [TARGET ...] [--max N]

    TARGETs are file offsets (== virtual addresses for these flat images),
    hex with 0x or decimal. 'bl' sites are calls; 'b' sites are usually
    tail calls or local branches - both are reported, tagged.
"""
import argparse
import sys

try:
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
    from capstone.arm64 import ARM64_OP_IMM
except ImportError:
    sys.exit("[!] needs capstone:  python3 -m pip install capstone")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--max", type=int, default=40, help="max sites per target")
    ap.add_argument("--chunk", type=int, default=1 << 20)
    args = ap.parse_args()

    targets = [int(t, 0) for t in args.targets]
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    md.detail = True  # required: operand info is only available with detail on
    data = open(args.image, "rb").read()

    hits = {t: [] for t in targets}
    seen = set()
    for start in range(0, len(data), args.chunk):
        end = min(len(data), start + args.chunk + 16)
        for ins in md.disasm(data[start:end], start):
            if ins.mnemonic not in ("bl", "b"):
                continue
            try:
                ops = ins.operands
            except Exception:
                continue
            if not ops or ops[0].type != ARM64_OP_IMM:
                continue
            tgt = ops[0].imm
            if tgt not in hits:
                continue
            key = (ins.address, ins.mnemonic)
            if key in seen:
                continue
            seen.add(key)
            hits[tgt].append((ins.address, ins.mnemonic))

    for t in targets:
        sites = hits[t]
        print(f"target {t:#x}: {len(sites)} site(s)")
        for addr, mn in sorted(sites)[:args.max]:
            print(f"  {addr:#010x}  {mn}")
        if len(sites) > args.max:
            print(f"  ... {len(sites) - args.max} more")


if __name__ == "__main__":
    main()

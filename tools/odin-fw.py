#!/usr/bin/env python3
"""
odin-fw.py — inspect and modify Odin firmware packages (tar / tar.md5).

Part of the exynos-eub project.

Samsung firmware distributed for Odin (AP_*.tar.md5, BL_*.tar.md5, ...) is a
POSIX tar; when the file name ends in .md5, the raw 16-byte MD5 of the tar is
appended to it. Images inside are usually LZ4-compressed (e.g. "boot.img.lz4").

Subcommands
-----------
  list     show members + sizes (and verify the .md5 when present)
  extract  pull one member out (e.g. the original stock boot.img.lz4)
  replace  swap member(s) inside a copy of the package (e.g. restore the
           original boot.img.lz4 into a modified AP), regenerating the md5
  pack     build a minimal package from member=file pairs
           (e.g. a boot-only tar for a quick restore flash)

Requires: Python 3.8+ (standard library only).
          LZ4 compression/decompression needs: pip install lz4

Examples
--------
  ./odin-fw.py list AP_A356E.tar.md5
  ./odin-fw.py extract AP_A356E.tar.md5 boot.img.lz4 -o stock/
  ./odin-fw.py extract AP_A356E.tar.md5 boot.img.lz4 --decompress -o stock/
  ./odin-fw.py replace AP_modified.tar.md5 --set boot.img.lz4=stock/boot.img.lz4
  ./odin-fw.py pack -o boot-only.tar.md5 boot.img.lz4=stock/boot.img.lz4

Only use devices and firmware you are entitled to modify/flash.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import os
import sys
import tarfile

CHUNK = 1 << 20  # 1 MiB
INTERESTING = ("boot", "recovery", "vbmeta", "init_boot", "dtbo", "super")


def _lz4frame():
    try:
        import lz4.frame as frame
        return frame
    except ImportError:
        sys.exit(
            "LZ4 operation requested but the 'lz4' package is not installed.\n"
            "Install it with:  python3 -m pip install lz4"
        )


def is_md5(path: str) -> bool:
    return path.lower().endswith(".md5")


def default_out(path: str) -> str:
    md5 = is_md5(path)
    base = path[:-4] if md5 else path
    if base.lower().endswith(".tar"):
        base = base[:-4]
    return f"{base}.new.tar" + (".md5" if md5 else "")


def verify_md5(path: str) -> None:
    size = os.path.getsize(path)
    if size <= 16:
        print("  [!] file too small for a .md5 trailer")
        return
    h = hashlib.md5()
    with open(path, "rb") as f:
        remaining = size - 16
        while remaining:
            block = f.read(min(CHUNK, remaining))
            if not block:
                break
            h.update(block)
            remaining -= len(block)
        trailer = f.read(16)
    if h.digest() == trailer:
        print("  md5 OK")
    else:
        print("  [!!] md5 MISMATCH - file is incomplete/corrupt or was modified")


def append_md5(path: str) -> None:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    with open(path, "ab") as f:
        f.write(h.digest())
    print(f"  md5 trailer appended ({h.hexdigest()})")


def prepare_data(member: str, src_path: str) -> bytes:
    """Read src_path, converting between raw and .lz4 as the member needs."""
    with open(src_path, "rb") as f:
        data = f.read()
    if member.endswith(".lz4") and not src_path.endswith(".lz4"):
        print(f"    compressing {src_path} -> lz4 for {member}")
        data = _lz4frame().compress(data)
    elif src_path.endswith(".lz4") and not member.endswith(".lz4"):
        print(f"    decompressing {src_path} for {member}")
        data = _lz4frame().decompress(data)
    return data


def cmd_list(args) -> None:
    path = args.package
    print(path)
    if is_md5(path) and not args.no_verify:
        print("  verifying md5 (this can take a moment on multi-GB files)...")
        verify_md5(path)
    with tarfile.open(path, "r:") as tf:
        for ti in tf:
            kind = "dir " if ti.isdir() else "file" if ti.isreg() else "othr"
            mark = " *" if any(k in ti.name.lower() for k in INTERESTING) else ""
            mib = ti.size / (1 << 20)
            print(f"  {kind}  {ti.size:>12,}  {mib:9.1f} MiB  {ti.name}{mark}")
    print("  (* = boot-critical member)")


def cmd_extract(args) -> None:
    with tarfile.open(args.package, "r:") as tf:
        try:
            ti = tf.getmember(args.member)
        except KeyError:
            names = ", ".join(sorted(m.name for m in tf.getmembers()))
            sys.exit(f"[!] '{args.member}' not found. Members:\n  {names}")
        if not ti.isreg():
            sys.exit(f"[!] '{args.member}' is not a regular file")
        f = tf.extractfile(ti)
        if f is None:
            sys.exit(f"[!] cannot read '{args.member}'")

        out_dir = args.output or "."
        out_name = os.path.basename(ti.name)
        if args.decompress:
            if not out_name.endswith(".lz4"):
                sys.exit("[!] --decompress requires an .lz4 member")
            out_name = out_name[:-4]
        out_path = os.path.join(out_dir, out_name)
        os.makedirs(out_dir, exist_ok=True)

        if args.decompress:
            frame = _lz4frame()
            with open(out_path, "wb") as out:
                out.write(frame.decompress(f.read()))
        else:
            with open(out_path, "wb") as out:
                while True:
                    block = f.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
    print(f"extracted {ti.name} -> {out_path} ({os.path.getsize(out_path):,} bytes)")


def cmd_replace(args) -> None:
    sets = {}
    for pair in args.set:
        if "=" not in pair:
            sys.exit("[!] --set expects MEMBER=FILE")
        member, file = pair.split("=", 1)
        if not os.path.isfile(file):
            sys.exit(f"[!] replacement file not found: {file}")
        sets[member] = file

    with tarfile.open(args.package, "r:") as tf:
        names = {ti.name for ti in tf}
    missing = set(sets) - names
    if missing:
        sys.exit("[!] member(s) not in package: " + ", ".join(sorted(missing)))

    out_path = args.output or default_out(args.package)
    if os.path.abspath(out_path) == os.path.abspath(args.package):
        sys.exit("[!] refusing to overwrite the input package")

    replaced = set()
    with tarfile.open(args.package, "r:") as src_tf, \
            tarfile.open(out_path, "w:", format=tarfile.GNU_FORMAT) as dst_tf:
        for ti in src_tf:
            if ti.isreg() and ti.name in sets:
                data = prepare_data(ti.name, sets[ti.name])
                new_ti = copy.copy(ti)
                new_ti.size = len(data)
                dst_tf.addfile(new_ti, io.BytesIO(data))
                replaced.add(ti.name)
                print(f"  replaced {ti.name} ({len(data):,} bytes)")
            else:
                fileobj = src_tf.extractfile(ti) if ti.isreg() else None
                dst_tf.addfile(ti, fileobj)
                print(f"  copied   {ti.name} ({ti.size / (1 << 20):.1f} MiB)")

    if args.no_md5:
        if is_md5(out_path):
            os.remove(out_path)
            sys.exit("[!] --no-md5 conflicts with an .md5 output name; pick a .tar name")
    elif is_md5(out_path):
        append_md5(out_path)
    print(f"wrote {out_path}")
    assert replaced == set(sets)


def cmd_pack(args) -> None:
    with tarfile.open(args.output, "w:", format=tarfile.GNU_FORMAT) as dst:
        for pair in args.pairs:
            if "=" not in pair:
                sys.exit("[!] arguments must be MEMBER=FILE")
            member, file = pair.split("=", 1)
            if not os.path.isfile(file):
                sys.exit(f"[!] file not found: {file}")
            data = prepare_data(member, file)
            ti = tarfile.TarInfo(member)
            ti.size = len(data)
            ti.mode = 0o644
            ti.mtime = int(os.path.getmtime(file))
            dst.addfile(ti, io.BytesIO(data))
            print(f"  added {member} ({len(data):,} bytes) from {file}")
    if is_md5(args.output) and not args.no_md5:
        append_md5(args.output)
    print(f"wrote {args.output}")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="odin-fw.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="show members (verifies md5)")
    p.add_argument("package")
    p.add_argument("--no-verify", action="store_true", help="skip md5 verification")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("extract", help="extract one member")
    p.add_argument("package")
    p.add_argument("member")
    p.add_argument("-o", "--output", help="output directory (default: .)")
    p.add_argument("--decompress", action="store_true",
                   help="decompress an .lz4 member to raw")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("replace", help="swap member(s) inside a copy of the package")
    p.add_argument("package")
    p.add_argument("--set", action="append", required=True, metavar="MEMBER=FILE",
                   help="replace MEMBER with the contents of FILE (repeatable)")
    p.add_argument("-o", "--output",
                   help="output package (default: <name>.new.tar[.md5])")
    p.add_argument("--no-md5", action="store_true", help="do not append an md5 trailer")
    p.set_defaults(func=cmd_replace)

    p = sub.add_parser("pack", help="build a new package from MEMBER=FILE pairs")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--no-md5", action="store_true", help="do not append an md5 trailer")
    p.add_argument("pairs", nargs="+", metavar="MEMBER=FILE")
    p.set_defaults(func=cmd_pack)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

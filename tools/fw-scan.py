#!/usr/bin/env python3
"""Stream-scan a member of a Samsung firmware tar.md5 (or any raw/LZ4 file)
for byte patterns, without extracting anything to disk.

The big AP members (super.img.lz4 etc.) are multi-GB; extracting them just
to grep is wasteful. This walks the LZ4 stream in chunks and reports hits
with decompressed stream offsets plus text context.

Usage:
    fw-scan.py FILE --patterns "pat1,pat2,..." [--member NAME]
                    [--max-hits N] [--chunk MiB]

    FILE        a .tar.md5 / .tar archive, or a raw file (optionally .lz4)
    --member    exact member name inside the tar (required for archives);
                a .lz4 member is decompressed while scanning
    --patterns  comma-separated byte patterns (ASCII, case-sensitive)
    --max-hits  max printed hits per pattern (counting continues; default 25)
    --chunk     read chunk size in MiB (default 8)
"""
import argparse
import fnmatch
import sys
import tarfile

try:
    import lz4.frame as lz4f
except ImportError:
    sys.exit("[!] needs lz4:  python3 -m pip install lz4")


def open_stream(path, member):
    if path.endswith((".tar", ".md5")):
        tf = tarfile.open(path, "r:")
        if member is None:
            sys.exit("[!] --member is required for tar archives")
        match = None
        for m in tf.getmembers():
            if m.name == member or fnmatch.fnmatch(m.name, member):
                match = m
                break
        if match is None:
            names = [m.name for m in tf.getmembers() if m.isfile()]
            sys.exit(f"[!] member {member!r} not found. Members: {names}")
        print(f"[i] member {match.name} ({match.size:,} bytes compressed/raw)")
        fh = tf.extractfile(match)
        return fh, match.name
    fh = open(path, "rb")
    return fh, path


def scan(stream, name, patterns, max_hits, chunk_mib):
    if name.endswith(".lz4"):
        stream = lz4f.LZ4FrameFile(stream, "rb")
    pats = [p.encode() for p in patterns]
    counts = {p: 0 for p in pats}
    shown = {p: 0 for p in pats}
    overlap = max(len(p) for p in pats) - 1
    chunk = chunk_mib * 1024 * 1024
    tail = b""
    base = 0
    total = 0
    while True:
        block = stream.read(chunk)
        if not block:
            break
        window = tail + block
        wbase = base - len(tail)
        for p in pats:
            idx = 0
            while True:
                idx = window.find(p, idx)
                if idx == -1:
                    break
                pos = wbase + idx
                counts[p] += 1
                if shown[p] < max_hits:
                    lo = max(0, idx - 64)
                    hi = min(len(window), idx + len(p) + 96)
                    ctx = window[lo:hi].decode("ascii", "replace")
                    ctx = " ".join(ctx.split())
                    print(f"  {p.decode():24} @0x{pos:012x}  ...{ctx}...")
                shown[p] += 1
                idx += 1
        total += len(block)
        base += len(block)
        tail = window[-overlap:] if overlap else b""
    print(f"[i] scanned {total:,} decompressed bytes")
    for p in pats:
        print(f"  {p.decode():24} total hits: {counts[p]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--member", default=None)
    ap.add_argument("--patterns", required=True)
    ap.add_argument("--max-hits", type=int, default=25)
    ap.add_argument("--chunk", type=int, default=8)
    args = ap.parse_args()

    patterns = [p for p in args.patterns.split(",") if p]
    stream, name = open_stream(args.file, args.member)
    try:
        scan(stream, name, patterns, args.max_hits, args.chunk)
    finally:
        stream.close()


if __name__ == "__main__":
    main()

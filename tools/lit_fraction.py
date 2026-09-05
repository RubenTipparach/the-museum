#!/usr/bin/env python3
# What fraction of a PNG's pixels are lit, in pure stdlib.
#
# scripts/render-proof.sh uses this to fail a render that produced a black
# frame, which is what a renderer that starts and draws nothing looks like.
# It decodes the PNG itself rather than importing Pillow, because the proof
# behind requirement 0 must run wherever the engine runs: a guard with an
# undeclared dependency turned a green render into a red job on a GitHub
# runner, which had every other tool and not that one.
#
# Handles what Godot's Image.SavePng writes: 8 bits per channel, RGB or RGBA,
# non interlaced. Anything else fails loudly rather than guessing.
#
# Checked against Pillow rather than assumed: on the committed proof frame this
# decoder returns byte identical RGB, and the luma below is Pillow's own Rec.
# 601 rule, rounded and compared with >=, which reproduces its 0.091 exactly. A
# truncating divide and a > read the same frame as 0.081, which is the kind of
# quiet disagreement that makes a guard's number mean nothing.
#
# Usage: python3 tools/lit_fraction.py <png> [threshold] [minimum]
#   threshold  luma above which a pixel counts as lit, 0 to 255 (default 40)
#   minimum    fraction that must be lit for exit 0 (default 0.02)

import struct
import sys
import zlib


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def read_png(path):
    """Returns (width, height, channels, raw bytes), one byte per channel."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("%s: not a PNG" % path)

    pos, idat, hdr = 8, bytearray(), None
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + length

    if hdr is None:
        raise SystemExit("%s: no IHDR" % path)
    width, height, depth, color, comp, filt, interlace = hdr
    if depth != 8 or color not in (2, 6) or interlace != 0:
        raise SystemExit(
            "%s: expected 8 bit RGB or RGBA, non interlaced; got depth %d, "
            "colour type %d, interlace %d" % (path, depth, color, interlace))

    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    out = bytearray(height * stride)

    # Undo the per scanline filter. Each row is prefixed by its filter type,
    # and every filter refers to the byte `channels` back and the row above.
    for y in range(height):
        ftype = raw[y * (stride + 1)]
        line = raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
        base, prev = y * stride, (y - 1) * stride
        for x in range(stride):
            value = line[x]
            a = out[base + x - channels] if x >= channels else 0
            b = out[prev + x] if y > 0 else 0
            c = out[prev + x - channels] if (y > 0 and x >= channels) else 0
            if ftype == 1:
                value += a
            elif ftype == 2:
                value += b
            elif ftype == 3:
                value += (a + b) // 2
            elif ftype == 4:
                value += paeth(a, b, c)
            elif ftype != 0:
                raise SystemExit("%s: unknown filter %d on row %d"
                                 % (path, ftype, y))
            out[base + x] = value & 0xFF
    return width, height, channels, out


def main(argv):
    path = argv[1]
    threshold = int(argv[2]) if len(argv) > 2 else 40
    minimum = float(argv[3]) if len(argv) > 3 else 0.02

    width, height, channels, px = read_png(path)
    lit = 0
    # Rec. 601 luma, in integers so this needs no float per pixel. The + 500
    # rounds rather than truncates, which is what Pillow's L conversion does.
    for i in range(0, len(px), channels):
        luma = (299 * px[i] + 587 * px[i + 1] + 114 * px[i + 2] + 500) // 1000
        if luma >= threshold:
            lit += 1
    fraction = lit / float(width * height)
    print("lit pixel fraction %.3f of %dx%d (needs > %.3f)"
          % (fraction, width, height, minimum))
    return 0 if fraction > minimum else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

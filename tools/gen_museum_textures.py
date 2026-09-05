#!/usr/bin/env python3
# The exhibit's textures, one PNG set per material role, generated from this
# script. This is the declared stopgap for Material Maker (CLAUDE.md 5,
# docs/BLENDER.md 5): Material Maker 1.4 segfaults while loading its own
# interface under this sandbox's software GL, so until a build of it runs
# here the textures are made by code, held to the same contract: a static
# committed file, a committed source, `--check` to catch drift, every
# dimension a power of two, and albedo, normal and roughness where the
# surface needs them. Replace this with .ptex graphs the day it runs.
#
# Deterministic: seeded, so a rerun writes identical bytes.
#
# Usage: python3 tools/gen_museum_textures.py [--check]

import hashlib
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "assets", "textures")
SIZE = 1024                                   # a 4 m tile at 256 px per metre


def noise(size, seed, octaves=4, base=8):
    """Value noise, tileable, as an L image: a coarse random grid resampled
    up, per octave, with the grid tiled first so the edges wrap."""
    rnd = np.random.RandomState(seed)
    acc = np.zeros((size, size), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = base * (2 ** o)
        small = Image.fromarray(rnd.randint(0, 256, (n, n)).astype(np.uint8))
        big = Image.new("L", (n * 2, n * 2))
        for dx in (0, n):
            for dy in (0, n):
                big.paste(small, (dx, dy))
        big = big.resize((size * 2, size * 2), Image.BICUBIC).crop((size // 2, size // 2, size // 2 + size, size // 2 + size))
        acc += np.asarray(big, dtype=np.float32) * amp
        total += amp
        amp *= 0.5
    return Image.fromarray((acc / total).astype(np.uint8))


def tint(gray, rgb, lo=0.6, hi=1.0):
    """An L image as a coloured albedo between lo and hi of rgb."""
    r = gray.point(lambda v: int(rgb[0] * (lo + (hi - lo) * v / 255)))
    g = gray.point(lambda v: int(rgb[1] * (lo + (hi - lo) * v / 255)))
    b = gray.point(lambda v: int(rgb[2] * (lo + (hi - lo) * v / 255)))
    return Image.merge("RGB", (r, g, b))


def normal_from_height(h, strength=2.0):
    """A tangent space normal map from an L height image, tileable."""
    a = np.asarray(h, dtype=np.float32) / 255.0
    dx = (np.roll(a, -1, axis=1) - np.roll(a, 1, axis=1)) * strength
    dy = (np.roll(a, -1, axis=0) - np.roll(a, 1, axis=0)) * strength
    nx, ny, nz = -dx, dy, np.ones_like(a)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    out = np.stack([nx / length, ny / length, nz / length], axis=-1) * 0.5 + 0.5
    return Image.fromarray((out * 255).astype(np.uint8), "RGB")


def carpet():
    """Loop pile: a fine grid of tufts with a slow colour drift."""
    s = SIZE
    tuft = Image.new("L", (8, 8), 0)
    d = ImageDraw.Draw(tuft); d.ellipse([1, 1, 6, 6], fill=255)
    grid = Image.new("L", (s, s))
    rnd = random.Random(3)
    for y in range(0, s, 8):
        for x in range(0, s, 8):
            grid.paste(tuft.point(lambda v, k=rnd.randint(150, 255): v * k // 255), (x, y))
    drift = noise(s, 4, 3, 4)
    height = ImageChops.blend(grid, drift, 0.35)
    albedo = tint(height, (92, 66, 74), 0.55, 1.0)
    return {"albedo": albedo, "normal": normal_from_height(height, 1.6), "rough": Image.new("L", (s, s), 235)}


def paint(rgb, seed):
    """Matte emulsion on plaster: a faint roller stipple, nearly flat."""
    s = SIZE
    stipple = noise(s, seed, 5, 16)
    albedo = tint(stipple, rgb, 0.9, 1.0)
    return {"albedo": albedo, "normal": normal_from_height(stipple, 0.5), "rough": stipple.point(lambda v: 200 + v // 6)}


def relief_floral():
    """The temple decor wall: rosettes in a grid, joined by scrolling vines,
    carved into sandstone. Drawn as a height map; the normal comes from it."""
    s = SIZE
    h = Image.new("L", (s, s), 128)
    d = ImageDraw.Draw(h)
    cell = s // 4
    for gy in range(4):
        for gx in range(4):
            cx, cy = gx * cell + cell // 2, gy * cell + cell // 2
            # a twelve petal rosette, petals as ellipses turned about the centre
            for k in range(12):
                a = k * math.pi / 6
                px, py = cx + math.cos(a) * cell * 0.22, cy + math.sin(a) * cell * 0.22
                petal = Image.new("L", (cell, cell), 0)
                pd = ImageDraw.Draw(petal)
                pd.ellipse([cell * 0.5 - cell * 0.06, cell * 0.5 - cell * 0.19, cell * 0.5 + cell * 0.06, cell * 0.5 + cell * 0.19], fill=255)
                petal = petal.rotate(math.degrees(a) + 90, resample=Image.BICUBIC)
                mask = petal.point(lambda v: 255 if v > 128 else 0)
                h.paste(200, (int(px - cell * 0.5), int(py - cell * 0.5)), mask)
            d.ellipse([cx - cell * 0.09, cy - cell * 0.09, cx + cell * 0.09, cy + cell * 0.09], fill=220)
            d.ellipse([cx - cell * 0.04, cy - cell * 0.04, cx + cell * 0.04, cy + cell * 0.04], fill=110)
            # the scroll to the next rosette: an s curve of raised stem
            for i in range(0, 100):
                t = i / 100
                x = cx + cell * 0.30 + t * cell * 0.4
                y = cy + math.sin(t * math.pi * 2) * cell * 0.12
                d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=185)
                y2 = cy + cell * 0.30 + t * cell * 0.4
                x2 = cx + math.sin(t * math.pi * 2) * cell * 0.12
                d.ellipse([x2 - 4, y2 - 4, x2 + 4, y2 + 4], fill=185)
    # leaves on the scrolls
    rnd = random.Random(11)
    for _ in range(160):
        x, y = rnd.randrange(s), rnd.randrange(s)
        if h.getpixel((x, y)) == 185:
            d.polygon([(x, y), (x + rnd.randint(-14, 14), y - 18), (x + rnd.randint(-14, 14), y - 30)], fill=175)
    # border bands at the top and bottom of the tile
    d.rectangle([0, 0, s, s * 0.03], fill=190); d.rectangle([0, s * 0.97, s, s], fill=190)
    h = h.filter(ImageFilter.GaussianBlur(2.2))
    grain = noise(s, 12, 4, 8)
    height = ImageChops.blend(h, grain, 0.18)
    albedo = tint(ImageChops.blend(height, grain, 0.5), (168, 146, 112), 0.62, 1.0)
    return {"albedo": albedo, "normal": normal_from_height(height, 3.0), "rough": grain.point(lambda v: 170 + v // 4)}


def blocks(rgb, seed, courses=6, mortar=6):
    """Cut stone in running bond: paving and the arch."""
    s = SIZE
    h = Image.new("L", (s, s), 210)
    d = ImageDraw.Draw(h)
    ch = s // courses
    rnd = random.Random(seed)
    for c in range(courses):
        y0 = c * ch
        off = (c % 2) * ch
        x = -off
        while x < s:
            w = int(ch * (1.4 + rnd.random() * 1.2))
            d.rectangle([x, y0, x + mortar, y0 + ch], fill=60)
            x += w
        d.rectangle([0, y0, s, y0 + mortar], fill=60)
    h = h.filter(ImageFilter.GaussianBlur(1.2))
    grain = noise(s, seed + 1, 5, 8)
    height = ImageChops.blend(h, grain, 0.25)
    albedo = tint(ImageChops.blend(height, grain, 0.6), rgb, 0.55, 1.0)
    return {"albedo": albedo, "normal": normal_from_height(height, 2.5), "rough": grain.point(lambda v: 190 + v // 5)}


def metal_black():
    s = SIZE
    g = noise(s, 21, 4, 32)
    albedo = tint(g, (22, 22, 24), 0.7, 1.0)
    return {"albedo": albedo, "normal": normal_from_height(g, 0.3), "rough": g.point(lambda v: 110 + v // 4)}


def door_paint(rgb, seed):
    """A painted door with two recessed panels."""
    s = SIZE
    h = Image.new("L", (s, s), 150)
    d = ImageDraw.Draw(h)
    for y0, y1 in ((0.08, 0.46), (0.54, 0.92)):
        d.rectangle([s * 0.12, s * y0, s * 0.88, s * y1], fill=120)
        d.rectangle([s * 0.15, s * y0 + s * 0.03, s * 0.85, s * y1 - s * 0.03], fill=150)
    h = h.filter(ImageFilter.GaussianBlur(3))
    g = noise(s, seed, 5, 16)
    height = ImageChops.blend(h, g, 0.1)
    return {"albedo": tint(ImageChops.blend(height, g, 0.5), rgb, 0.85, 1.0), "normal": normal_from_height(height, 2.0), "rough": g.point(lambda v: 150 + v // 5)}


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sign(text, fg, bg, w=512, h=256, pad=0.18):
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    f = font(int(h * 0.55))
    tw = d.textlength(text, font=f)
    while tw > w * (1 - pad) and f.size > 8:
        f = font(f.size - 2); tw = d.textlength(text, font=f)
    d.text(((w - tw) / 2, h * 0.18), text, fill=fg, font=f)
    return {"albedo": im}


def leaf():
    """An alpha cut leaf for the vines: shape, midrib, veins."""
    s = 256
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(s * 0.5, s * 0.02)]
    for i in range(1, 30):
        t = i / 30
        wobble = math.sin(t * math.pi) * s * 0.34
        pts.append((s * 0.5 + wobble, s * (0.02 + t * 0.9)))
    for i in range(29, 0, -1):
        t = i / 30
        wobble = math.sin(t * math.pi) * s * 0.34
        pts.append((s * 0.5 - wobble, s * (0.02 + t * 0.9)))
    d.polygon(pts, fill=(58, 92, 46, 255))
    d.line([(s * 0.5, s * 0.05), (s * 0.5, s * 0.92)], fill=(38, 64, 30, 255), width=4)
    for i in range(6):
        y = s * (0.2 + i * 0.12)
        d.line([(s * 0.5, y), (s * 0.5 + s * 0.28, y + s * 0.1)], fill=(44, 72, 34, 255), width=2)
        d.line([(s * 0.5, y), (s * 0.5 - s * 0.28, y + s * 0.1)], fill=(44, 72, 34, 255), width=2)
    return {"albedo": im}


SET = {
    "mat_carpet": carpet,
    "mat_paint_green": lambda: paint((40, 66, 54), 5),
    "mat_paint_plum": lambda: paint((84, 48, 62), 6),
    "mat_relief_floral": relief_floral,
    "mat_stone_paving": lambda: blocks((96, 92, 84), 31, 8, 8),
    "mat_stone_arch": lambda: blocks((150, 138, 112), 41, 6, 10),
    "mat_metal_black": metal_black,
    "mat_door_stone": lambda: blocks((110, 102, 90), 51, 5, 8),
    "mat_door_staff": lambda: door_paint((112, 108, 104), 61),
    "mat_vine": lambda: {"albedo": tint(noise(256, 71, 4, 8), (74, 58, 38), 0.6, 1.0)},
    "mat_sign_exit": lambda: sign("EXIT", (245, 255, 245), (18, 120, 52)),
    "mat_sign_staff": lambda: sign("STAFF ONLY", (30, 30, 30), (225, 220, 205), 512, 128),
    "mat_leaf": leaf,
}


def main(check=False):
    os.makedirs(OUT, exist_ok=True)
    drift = []
    for role, make in SET.items():
        maps = make()
        for kind, im in maps.items():
            path = os.path.join(OUT, "%s_%s.png" % (role, kind))
            w, h = im.size
            assert (w & (w - 1)) == 0 and (h & (h - 1)) == 0, "%s is %dx%d, not a power of two" % (path, w, h)
            if check:
                buf = os.path.join(OUT, ".check.png"); im.save(buf, optimize=True)
                new = hashlib.sha256(open(buf, "rb").read()).hexdigest(); os.remove(buf)
                old = hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.exists(path) else None
                if new != old:
                    drift.append(os.path.relpath(path, ROOT))
            else:
                im.save(path, optimize=True)
                print("wrote %s %dx%d" % (os.path.relpath(path, ROOT), w, h))
    if check:
        if drift:
            print("DRIFT: " + ", ".join(drift)); sys.exit(1)
        print("textures match their generator")


if __name__ == "__main__":
    main("--check" in sys.argv)

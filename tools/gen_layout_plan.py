#!/usr/bin/env python3
# Draw the plan of an exhibit from its layout file: walls, door openings, the
# path a visitor walks, and every fixture where the file puts it. The picture
# is a build product of data/layout/<exhibit>.json; edit the file, not the
# picture. Needs Pillow (a developer tool, not part of the build).
#
# Usage: python3 tools/gen_layout_plan.py elmorian

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..")


def main(name):
    with open(os.path.join(ROOT, "data", "layout", name + ".json")) as f:
        L = json.load(f)
    S = 44                                   # pixels per metre
    xs = [w["a"][0] for w in L["walls"]] + [w["b"][0] for w in L["walls"]]
    zs = [w["a"][1] for w in L["walls"]] + [w["b"][1] for w in L["walls"]]
    x0, x1, z0, z1 = min(xs) - 1.5, max(xs) + 1.5, min(zs) - 1.5, max(zs) + 3.5
    W, H = int((x1 - x0) * S), int((z1 - z0) * S)
    im = Image.new("RGB", (W, H), (27, 33, 30))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except OSError:
        font = small = ImageFont.load_default()

    def P(x, z):                             # world to pixel: north is up
        return ((x - x0) * S, (z1 - z) * S)

    fills = {"mat_carpet": (58, 46, 52), "mat_stone_paving": (60, 58, 52)}
    for r in L["rooms"]:
        b = r["bounds"]
        d.rectangle([P(b[0], b[3]), P(b[2], b[1])], fill=fills.get(r["floor"], (50, 50, 50)))
        cx, cz = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        d.text((P(cx, cz)[0] - 30, P(cx, cz)[1] - 8), "%d  %s" % (r["id"], r["key"]), fill=(216, 211, 197), font=font)

    dw = L["door"]["w"]
    for w in L["walls"]:
        ax, az = w["a"]; bx, bz = w["b"]
        length = ((bx - ax) ** 2 + (bz - az) ** 2) ** 0.5
        ux, uz = (bx - ax) / length, (bz - az) / length
        segs = [(0, length)]
        if "door" in w:
            a = w["door"] - dw / 2
            segs = [(0, a), (a + dw, length)]
        col = (140, 120, 90) if "brick" in w["material"] else (150, 150, 140)
        for s0, s1 in segs:
            if s1 > s0:
                d.line([P(ax + ux * s0, az + uz * s0), P(ax + ux * s1, az + uz * s1)], fill=col, width=int(L["wallThickness"] * S))

    cs = {r["id"]: ((r["bounds"][0] + r["bounds"][2]) / 2, (r["bounds"][1] + r["bounds"][3]) / 2) for r in L["rooms"]}
    for dd in L["doors"]:
        a, b = dd["rooms"]
        pts = [P(*cs[a]), P(dd["at"][0], dd["at"][1]), P(*cs[b])]
        d.line(pts, fill=(217, 167, 90), width=2)
        d.ellipse([pts[1][0] - 4, pts[1][1] - 4, pts[1][0] + 4, pts[1][1] + 4], fill=(217, 167, 90))

    F = L["fixtures"]
    def dot(x, z, col, label):
        px, pz = P(x, z)
        d.rectangle([px - 5, pz - 5, px + 5, pz + 5], fill=col)
        d.text((px + 7, pz - 6), label, fill=col, font=small)
    for e in F["exitSigns"]:
        dot(e["pos"][0], e["pos"][2], (120, 220, 120), "EXIT")
    for e in F["extinguishers"]:
        dot(e["pos"][0], e["pos"][2], (230, 80, 70), "ext")
    sd = F["staffDoor"]
    dot(sd["pos"][0], sd["pos"][2], (200, 200, 90), "STAFF")
    t = F["truss"]
    for rid in t["rooms"]:
        b = [r for r in L["rooms"] if r["id"] == rid][0]["bounds"]
        x = b[0] + t["grid"] / 2
        while x < b[2]:
            d.line([P(x, b[1]), P(x, b[3])], fill=(70, 70, 70), width=1); x += t["grid"]
        z = b[1] + t["grid"] / 2
        while z < b[3]:
            d.line([P(b[0], z), P(b[2], z)], fill=(70, 70, 70), width=1); z += t["grid"]
    for h in F["trackHeads"]:
        px, pz = P(h["pos"][0], h["pos"][2]); ax, az = P(h["aim"][0], h["aim"][2])
        d.line([(px, pz), (ax, az)], fill=(255, 230, 170), width=1)
        d.ellipse([px - 3, pz - 3, px + 3, pz + 3], outline=(255, 230, 170))
    for k, st in L["stations"].items():
        px, pz = P(st["point"][0], st["point"][2])
        d.ellipse([px - 6, pz - 6, px + 6, pz + 6], outline=(125, 191, 208), width=2)
        d.text((px + 8, pz + 2), k, fill=(125, 191, 208), font=small)
    for p in L["plaques"]:
        px, pz = P(p["pos"][0], p["pos"][2])
        d.rectangle([px - 3, pz - 3, px + 3, pz + 3], outline=(216, 211, 197))

    y = 10
    for col, txt in [((217, 167, 90), "visitor path, door"), ((125, 191, 208), "puzzle station"), ((216, 211, 197), "plaque"),
                     ((120, 220, 120), "exit sign"), ((230, 80, 70), "extinguisher"), ((200, 200, 90), "staff door"),
                     ((255, 230, 170), "track head and aim"), ((70, 70, 70), "truss grid"), ((140, 120, 90), "brick wall"), ((150, 150, 140), "painted wall")]:
        d.rectangle([10, y, 20, y + 10], fill=col); d.text((26, y - 2), txt, fill=(216, 211, 197), font=small); y += 15
    d.text((10, H - 20), "north is up. %s, %d px per metre" % (name, S), fill=(146, 156, 149), font=small)

    out = os.path.join(ROOT, "docs", "reference", name + "_plan.png")
    im.save(out, optimize=True)
    print("wrote", os.path.relpath(out, ROOT), im.size)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "elmorian")

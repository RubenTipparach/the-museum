#!/usr/bin/env python3
# Build a mockup's single self contained index.html from its sources: the
# template, the vendored library, and the game's own scripts, inlined in
# order. One file, no network, the way CLAUDE.md 3 wants a prototype, and a
# build product of committed sources the way CLAUDE.md 5 wants an asset.
#
# Usage: python3 tools/build_mockup.py elmorian-exhibit

import base64
import io
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")


def textures_json(d):
    """The generated texture set, downscaled to 512 and JPEG encoded as data
    URIs, keyed by role and map. A build product of the PNGs; the PNGs are
    the assets. Alpha maps stay PNG."""
    from PIL import Image
    tex_dir = os.path.join(ROOT, "assets", "textures")
    out = {}
    for name in sorted(os.listdir(tex_dir)):
        if not name.endswith(".png"):
            continue
        role, kind = name[:-4].rsplit("_", 1)
        im = Image.open(os.path.join(tex_dir, name))
        im.thumbnail((512, 512))
        buf = io.BytesIO()
        if im.mode == "RGBA":
            im.save(buf, "PNG", optimize=True); mime = "image/png"
        else:
            im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True); mime = "image/jpeg"
        out.setdefault(role, {})[kind] = "data:%s;base64,%s" % (mime, base64.b64encode(buf.getvalue()).decode())
    return json.dumps(out)


def build(slug):
    d = os.path.join(ROOT, "mockups", slug)
    parts = {
        "THREE": os.path.join(d, "vendor", "three.min.js"),
        "PUZZLES": os.path.join(d, "puzzles.js"),
        "ART": os.path.join(d, "art.js"),
        "LORE": os.path.join(d, "lore.js"),
        "GAME": os.path.join(d, "game.js"),
    }
    with open(os.path.join(d, "index.template.html")) as f:
        page = f.read()
    for key, path in parts.items():
        with open(path) as f:
            src = f.read()
        if key == "LORE":
            with open(os.path.join(ROOT, "data", "lore", "elmorian.json")) as lf:
                src = src.replace("{{LORE_JSON}}", json.dumps(json.load(lf)))
        # A closing script tag inside a script would end the block early.
        src = src.replace("</script>", "<\\/script>")
        page = page.replace("{{%s}}" % key, src)
    # The shell, the layout and the textures: build products of assets/ and
    # data/. The shell is TEXT, converted from the committed .glb by
    # tools/glb_to_json.py: a page that embeds a binary model is a page the
    # artifact share review cannot review. See that script's header.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import glb_to_json
    shell = glb_to_json.convert(os.path.join(ROOT, "assets", "exhibit", "elmorian.glb"))
    page = page.replace("{{SHELL}}", json.dumps(shell, separators=(",", ":")))
    with open(os.path.join(ROOT, "data", "layout", "elmorian.json")) as f:
        page = page.replace("{{LAYOUT}}", json.dumps(json.load(f)))
    with open(os.path.join(ROOT, "data", "tuning.json")) as f:
        page = page.replace("{{TUNING}}", json.dumps(json.load(f)))
    with open(os.path.join(ROOT, "data", "materials.json")) as f:
        page = page.replace("{{MATERIALS}}", json.dumps(json.load(f)))
    page = page.replace("{{TEXTURES}}", textures_json(d))
    out = os.path.join(d, "index.html")
    with open(out, "w") as f:
        f.write(page)
    print("wrote %s (%d bytes)" % (os.path.relpath(out, ROOT), os.path.getsize(out)))

    # The artifact host wraps a page in its own doctype, html, head and body,
    # so it gets the same page with those stripped: title and style first,
    # then the body's content. One source, two shells.
    head = page.split("<head>")[1].split("</head>")[0]
    body = page.split("<body>")[1].split("</body>")[0]
    head = "\n".join(l for l in head.splitlines() if not l.strip().startswith("<meta"))
    art = os.path.join(d, "artifact.html")
    with open(art, "w") as f:
        f.write(head.strip() + "\n" + body.strip() + "\n")
    print("wrote %s (%d bytes)" % (os.path.relpath(art, ROOT), os.path.getsize(art)))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "elmorian-exhibit")

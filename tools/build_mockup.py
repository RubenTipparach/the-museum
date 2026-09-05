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


def module_to_script(src, exports_to):
    """An ES module from three's examples as a plain script: its imports from
    'three' read the global, its import of BufferGeometryUtils reads the
    global that file was turned into, and its exports land on `exports_to`."""
    src = re.sub(r"import\s*\{([^}]*)\}\s*from\s*'three';", lambda m: "const {%s} = THREE;" % m.group(1), src)
    src = re.sub(r"import\s*\{([^}]*)\}\s*from\s*'\.\./utils/BufferGeometryUtils\.js';", lambda m: "const {%s} = window.BufferGeometryUtils;" % m.group(1), src)
    src = re.sub(r"^export function ", "function ", src, flags=re.M)
    src = re.sub(r"export\s*\{([^}]*)\};", lambda m: "window.%s = {%s};" % (exports_to, m.group(1)), src)
    assert "import " not in src and "export " not in src, "a module boundary survived the transform"
    # Its own scope: two scripts declaring the same names from THREE at top
    # level share one global lexical scope and the second one throws.
    return "(function () {\n'use strict';\n" + src + "\n})();"


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
        # A closing script tag inside a script would end the block early.
        src = src.replace("</script>", "<\\/script>")
        page = page.replace("{{%s}}" % key, src)
    with open(os.path.join(d, "vendor", "BufferGeometryUtils.js")) as f:
        page = page.replace("{{BGU}}", module_to_script(f.read(), "BufferGeometryUtils"))
    with open(os.path.join(d, "vendor", "GLTFLoader.js")) as f:
        page = page.replace("{{GLTF}}", module_to_script(f.read(), "GLTFLoaderModule"))
    # The shell, the layout and the textures: build products of assets/ and data/.
    with open(os.path.join(ROOT, "assets", "exhibit", "elmorian.glb"), "rb") as f:
        page = page.replace("{{GLB}}", base64.b64encode(f.read()).decode())
    with open(os.path.join(ROOT, "data", "layout", "elmorian.json")) as f:
        page = page.replace("{{LAYOUT}}", json.dumps(json.load(f)))
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

#!/usr/bin/env python3
# Build a mockup's single self contained index.html from its sources: the
# template, the vendored library, and the game's own scripts, inlined in
# order. One file, no network, the way CLAUDE.md 3 wants a prototype, and a
# build product of committed sources the way CLAUDE.md 5 wants an asset.
#
# Usage: python3 tools/build_mockup.py elmorian-exhibit

import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")


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

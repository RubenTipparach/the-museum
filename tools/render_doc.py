#!/usr/bin/env python3
# Render docs/ARCHITECTURE.md to docs/ARCHITECTURE.html: one self contained page,
# images embedded as data URIs, no network but Google Fonts, the version the owner
# reviews as a published artifact.
#
# The Markdown is the source and this page is a build product (CLAUDE.md 5):
# regenerate it after editing the document, never edit the HTML by hand.
#
# Usage: python3 tools/render_doc.py
# Needs: pip install markdown pillow

import base64
import html
import io
import os
import re

import markdown
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "docs", "ARCHITECTURE.md")
OUT = os.path.join(ROOT, "docs", "ARCHITECTURE.html")
PHOTOS = os.path.join(ROOT, "docs", "reference", "photos")


def data_uri(path, max_px):
    """A JPEG data URI no wider or taller than max_px. The proof frame keeps its
    PNG so the lit pixels are the renderer's own and not a codec's."""
    im = Image.open(path)
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    if path.endswith(".png"):
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=78, optimize=True)
        mime = "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(buf.getvalue()).decode())


def embed_images(body):
    def repl(m):
        src = m.group(1)
        path = os.path.normpath(os.path.join(ROOT, "docs", src))
        return '<img src="%s" alt="">' % data_uri(path, 960)
    return re.sub(r'<img alt="" src="([^"]+)"\s*/?>', repl, body)


def nav_from(md_text):
    """One rail entry per H2, in document order. ADRs are numbered rooms; the
    plain sections keep their numbers too, which the document already carries."""
    items = []
    for line in md_text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            m = re.match(r"(ADR-\d+|\d+)[.:]?\s*(.*)", title)
            tag, rest = (m.group(1), m.group(2)) if m else ("", title)
            short = re.split(r"[.:]", rest, 1)[0].strip()
            items.append((tag, short, title))
    return items


def slug(title):
    """Match python-markdown's toc slugify for the anchors it writes."""
    s = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[\s]+", "-", s)


with open(SRC) as f:
    md_text = f.read()

body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc"],
    extension_configs={"toc": {"toc_depth": "2-3"}},
)
body = embed_images(body)

# Relative links resolve beside the Markdown, not from a published page. Point
# them at the same files on the branch instead.
REPO = "https://github.com/RubenTipparach/the-museum/blob/claude/museum-game-architecture-bqevws/"
body = body.replace('href="../', 'href="' + REPO).replace('href="reference/', 'href="' + REPO + "docs/reference/")
body = body.replace("<table>", '<div class="scroll"><table>').replace("</table>", "</table></div>")

# The title block is the H1; lift it out so the header can set it.
body = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", body, count=1, flags=re.S)

nav = "".join(
    '<a href="#%s"><span class="tag">%s</span><span>%s</span></a>'
    % (slug(full), html.escape(tag), html.escape(short))
    for tag, short, full in nav_from(md_text)
)

photos = ""
for name in sorted(os.listdir(PHOTOS)):
    if name.endswith(".jpg"):
        cap = re.sub(r"^\d+-", "", name[:-4]).replace("-", " ")
        photos += '<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>' % (
            data_uri(os.path.join(PHOTOS, name), 560), html.escape(cap), html.escape(cap))

page = open(os.path.join(os.path.dirname(__file__), "render_doc_template.html")).read()
page = page.replace("{{NAV}}", nav).replace("{{BODY}}", body).replace("{{PHOTOS}}", photos)
with open(OUT, "w") as f:
    f.write(page)
print("wrote %s (%d bytes)" % (os.path.relpath(OUT, ROOT), os.path.getsize(OUT)))

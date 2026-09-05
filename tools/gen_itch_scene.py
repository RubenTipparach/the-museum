#!/usr/bin/env python3
"""Write itch/scenes/exhibit.tscn from data/layout/elmorian.json.

The scene is structure (CLAUDE.md 9): every prop is an instance of a committed
glb from assets/props, placed where the layout says, with an authored collision
body that names what a tap on it means. Nothing here is built at runtime; the
scene is a build product of the layout, regenerated rather than edited, like
the shell is (CLAUDE.md 5).

  python3 tools/gen_itch_scene.py            # writes the scene and the links
  python3 tools/gen_itch_scene.py --check    # exits 1 if the scene has drifted
"""
import json
import math
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "itch", "scenes", "exhibit.tscn")
LAYOUT = os.path.join(ROOT, "data", "layout", "elmorian.json")
PROPS = ["eye_disc_0", "eye_disc_1", "eye_disc_2", "plinth", "peg", "ring_0", "ring_1", "ring_2", "ring_3",
         "pad", "stone", "plate", "door_lamp", "ancestor"]


def num(v):
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def tf(at, yaw=0.0, tilt=0.0, scale=1.0):
    """A Transform3D literal: rotation about y by yaw, then about x by tilt
    (applied first), then a uniform scale. Rows of the basis, as the .tscn
    parser reads them."""
    cy, sy, ct, st = math.cos(yaw), math.sin(yaw), math.cos(tilt), math.sin(tilt)
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rx = [[1, 0, 0], [0, ct, -st], [0, st, ct]]
    m = [[sum(ry[i][k] * rx[k][j] for k in range(3)) * scale for j in range(3)] for i in range(3)]
    nums = [m[i][j] for i in range(3) for j in range(3)] + list(at)
    return "Transform3D(" + ", ".join(num(v) for v in nums) + ")"


def facing(n):
    return math.atan2(n[0], n[2])


class Scene:
    def __init__(self):
        self.ext, self.sub, self.nodes = [], [], []
        self.ext_ids = {}

    def prop(self, name):
        if name not in self.ext_ids:
            self.ext_ids[name] = "p_%s" % name
            self.ext.append('[ext_resource type="PackedScene" path="res://assets/props/%s.glb" id="p_%s"]' % (name, name))
        return self.ext_ids[name]

    def box(self, size):
        sid = "box_%d" % len(self.sub)
        self.sub.append('[sub_resource type="BoxShape3D" id="%s"]\nsize = Vector3(%s, %s, %s)' % ((sid,) + tuple(num(v) for v in size)))
        return sid

    def node(self, name, parent, type_=None, instance=None, transform=None, meta=None, extra=()):
        head = '[node name="%s"' % name
        if type_:
            head += ' type="%s"' % type_
        head += ' parent="%s"' % parent
        if instance:
            head += ' instance=ExtResource("%s")' % instance
        head += "]"
        lines = [head]
        if transform:
            lines.append("transform = " + transform)
        lines += list(extra)
        for k, v in (meta or {}).items():
            lines.append("metadata/%s = %s" % (k, json.dumps(v) if isinstance(v, str) else num(v)))
        self.nodes.append("\n".join(lines))

    def body(self, name, parent, kind, meta, size, at=(0, 0, 0), yaw=0.0):
        m = {"kind": kind}
        m.update(meta)
        self.node(name, parent, "StaticBody3D", transform=tf(at, yaw), meta=m)
        self.node("shape", parent + "/" + name, "CollisionShape3D", extra=['shape = SubResource("%s")' % self.box(size)])

    def text(self):
        steps = len(self.ext) + len(self.sub) + 1
        parts = ["[gd_scene load_steps=%d format=3]" % steps, "", "\n".join(self.ext), ""]
        if self.sub:
            parts += ["\n\n".join(self.sub), ""]
        parts += ["\n\n".join(self.nodes), ""]
        return "\n".join(parts)


def build(L):
    P, D, DW, DH = L["props"], L["doors"], L["door"]["w"], L["door"]["h"]
    S = Scene()
    S.ext.append('[ext_resource type="Script" path="res://src/exhibit_view.gd" id="script"]')
    S.node("Exhibit", None, "Node3D", extra=['script = ExtResource("script")'])
    S.nodes[-1] = S.nodes[-1].replace(' parent="None"', "")

    # room 1: the eye discs, turned about their own axis by the state
    S.node("Eyes", ".", "Node3D")
    for e in P["eyes"]:
        n = "eye_%d" % e["i"]
        S.node(n, "Eyes", instance=S.prop("eye_disc_%d" % e["i"]), transform=tf(e["at"]))
        S.body("body", "Eyes/" + n, "eye", {"i": e["i"]}, (e["r"] * 2, e["r"] * 2, 0.16))

    # room 2: plinth, pegs with their tap panes, the four rings, the two glyphs
    st = P["stack"]
    S.node("Stack", ".", "Node3D")
    ps = st["plinthSize"]
    S.node("plinth", "Stack", instance=S.prop("plinth"), transform=tf((st["pegX"], 0, st["pegZ"][1])))
    S.body("body", "Stack/plinth", "stack", {"peg": -1}, ps, at=(0, ps[1] / 2, 0))
    for i, z in enumerate(st["pegZ"]):
        n = "peg_%d" % i
        S.node(n, "Stack", instance=S.prop("peg"), transform=tf((st["pegX"], st["plinthTop"], z)))
        S.body("body", "Stack/" + n, "stack", {"peg": i}, st["pane"], at=(0, st["pane"][1] / 2, 0))
    for sz in range(4):
        y = st["plinthTop"] + st["ringLift"] + (3 - sz) * st["ringStep"]
        S.node("ring_%d" % sz, "Stack", instance=S.prop("ring_%d" % sz), transform=tf((st["pegX"], y, st["pegZ"][0])))
    for k, g in enumerate(st["glyphs"]):
        S.node("glyph_%d" % k, "Stack", instance=S.prop("plate"), meta={"art": g["art"]},
               transform=tf((st["glyphX"], st["glyphY"], st["pegZ"][g["peg"]]), facing([1, 0, 0]), scale=st["glyphSize"]))

    # room 3: six pads on the west wall, two rows of three
    pd = P["pads"]
    S.node("Pads", ".", "Node3D")
    for i in range(6):
        n = "pad_%d" % i
        at = (pd["x"], pd["rows"][i // 3], pd["z"] + (1 - i % 3) * pd["step"])
        S.node(n, "Pads", instance=S.prop("pad"), transform=tf(at, facing(pd["normal"])))
        S.body("body", "Pads/" + n, "pad", {"i": i}, (pd["size"], pd["size"], 0.12))

    # room 4: three seeing stones, each with the little relief that shows a room
    sn = P["stones"]
    S.node("Stones", ".", "Node3D")
    yaw = facing(sn["normal"])
    R = sn["r"] * 2
    for i, z in enumerate(sn["z"]):
        n = "stone_%d" % i
        at = (sn["x"], sn["y"], z)
        S.node(n, "Stones", instance=S.prop("stone"), transform=tf(at, yaw))
        S.body("body", "Stones/" + n, "stone", {"i": i}, (R, R, 0.05))
        dn = "diagram_%d" % i
        S.node(dn, "Stones", "Node3D", transform=tf(at, yaw))
        parent = "Stones/" + dn
        if i == 0:      # three eyes and their counts
            for k in range(3):
                S.node("eye_%d" % k, parent, instance=S.prop("eye_disc_%d" % k), transform=tf(((0.25 + 0.25 * k - 0.5) * R, 0.08 * R, 0.04), scale=0.2))
                S.node("numeral_%d" % k, parent, instance=S.prop("plate"), transform=tf(((0.25 + 0.25 * k - 0.5) * R, -0.2 * R, 0.03), scale=0.12 * R))
        elif i == 1:    # three pegs, the four rings, the night eye above
            base = -0.22 * R
            for k in range(3):
                S.node("peg_%d" % k, parent, instance=S.prop("peg"), transform=tf(((0.28 + 0.22 * k - 0.5) * R, base, 0.03), scale=0.3))
            for sz in range(4):
                S.node("ring_%d" % sz, parent, instance=S.prop("ring_%d" % sz), transform=tf((0, base, 0.06), tilt=math.radians(70), scale=0.14))
            S.node("word", parent, instance=S.prop("plate"), meta={"art": "word_2"}, transform=tf((0, 0.28 * R, 0.03), scale=0.16 * R))
        else:           # the last phrase, two columns of two, read from the top right
            for k in range(4):
                S.node("word_%d" % k, parent, instance=S.prop("plate"),
                       transform=tf(((0.62 - 0.3 * (k // 2) - 0.5) * R, (0.5 - 0.34 - 0.32 * (k % 2)) * R, 0.03), scale=0.2 * R))

    # the doors: a pane in each opening that a tap can choose, a lamp each side
    S.node("Doors", ".", "Node3D")
    dl = P["doorLamps"]
    for d in D:
        out = (0, 0, 1) if d["axis"] == "x" else (1, 0, 0)
        pyaw = 0.0 if d["axis"] == "x" else math.pi / 2
        S.body("pane_%d" % d["i"], "Doors", "doorway", {"i": d["i"]}, (DW, DH, 0.06), at=(d["at"][0], DH / 2, d["at"][1]), yaw=pyaw)
        for s, side in ((0, 1), (1, -1)):
            o = (out[0] * side, 0, out[2] * side)
            at = (d["at"][0] + o[0] * dl["out"], DH + dl["up"], d["at"][1] + o[2] * dl["out"])
            S.node("lamp_%d_%d" % (d["i"], s), "Doors", instance=S.prop("door_lamp"), transform=tf(at, facing(o)))

    # the alcove: the ancestor
    S.node("Ancestor", ".", instance=S.prop("ancestor"), transform=tf(P["ancestor"]["at"]))
    return S.text()


def main(argv):
    L = json.load(open(LAYOUT))
    text = build(L)
    links = os.path.join(ROOT, "itch", "assets", "props")
    if "--check" in argv:
        have = open(OUT).read() if os.path.exists(OUT) else ""
        missing = [p for p in PROPS if not os.path.islink(os.path.join(links, p + ".glb"))]
        if have != text or missing:
            print("DRIFT: itch/scenes/exhibit.tscn is not what the layout describes" if have != text else "missing links: %s" % missing)
            return 1
        print("ok    itch/scenes/exhibit.tscn matches the layout")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(text)
    os.makedirs(links, exist_ok=True)
    for p in PROPS:
        dst = os.path.join(links, p + ".glb")
        if not os.path.islink(dst):
            os.symlink(os.path.join("..", "..", "..", "assets", "props", p + ".glb"), dst)
    print("wrote %s (%d nodes) and %d links" % (os.path.relpath(OUT, ROOT), text.count("[node "), len(PROPS)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

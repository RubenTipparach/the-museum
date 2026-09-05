# Build an exhibit's shell from its layout file, in Blender, headless:
#
#   blender -b --python tools/build_exhibit.py -- elmorian
#
# Reads data/layout/<name>.json and makes the walls (slabs, doors cut out by
# boolean, a carved frieze cut into each feature wall), floors, the ceiling
# void, the black truss with hangers, one track head per plaque and station,
# stanchions before each station, vines on the feature walls, an exit sign
# over every leaving door, an extinguisher beside it, the staff door, the
# arch, the door slabs and the plaque planes; materials named for roles, UVs
# at world scale. Writes assets/exhibit/<name>.glb and .blend and renders the
# proof to docs/reference/. docs/BLENDER.md says why; tools/blenderlib.py how.
#
# Axes: the layout is y up with z toward the visitor (the engine's frame).
# Blender is z up. A layout point (x, y, z) is Blender (x, -z, y), and the
# glTF exporter's y up conversion turns it back.

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import blenderlib as B  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = argv[0] if argv else "elmorian"
with open(os.path.join(B.ROOT, "data", "layout", NAME + ".json")) as f:
    L = json.load(f)
TILE = 1024.0 / L["texelDensity"]          # metres one texture tile covers
H, T = L["wallHeight"], L["wallThickness"]
DW, DH = L["door"]["w"], L["door"]["h"]
FX = L["fixtures"]


def bl(p):
    """Layout (x, y, z) to Blender (x, -z, y)."""
    return (p[0], -p[2], p[1])


def bl2(x, z, y=0.0):
    return (x, -z, y)


def room_at(x, z):
    for r in L["rooms"]:
        b = r["bounds"]
        if b[0] <= x <= b[2] and b[1] <= z <= b[3]:
            return r
    return None


def facing(normal):
    """Rotation about z that turns a slab's +y face toward a layout normal."""
    n = Vector(bl2(normal[0], normal[2]))
    return math.atan2(n.y, n.x) - math.pi / 2


SIDE_NORMAL = {"north": (0, 1), "south": (0, -1), "east": (-1, 0), "west": (1, 0)}   # layout normal INTO the room

B.reset_scene()
exported, log = [], []

# ---- walls -----------------------------------------------------------------------
feature_faces = []     # (room, wall object, layout normal into the room), for the frieze and the vines
for w in L["walls"]:
    ax, az = w["a"]; bx, bz = w["b"]
    length = math.hypot(bx - ax, bz - az)
    ux, uz = (bx - ax) / length, (bz - az) / length
    mid = ((ax + bx) / 2, (az + bz) / 2)
    ang = math.atan2(-(bz - az), bx - ax)
    wall = B.slab("wall_" + w["name"], (length, T, H), bl2(mid[0], mid[1]), ang)
    if "door" in w:
        px, pz = ax + ux * w["door"], az + uz * w["door"]
        B.boolean(wall, B.cutter("cut_door_" + w["name"], (DW, T, DH), bl2(px, pz), ang))
    # a feature wall gets a carved frieze: a row of rosettes and two grooves,
    # cut 15 mm into the face that looks into the room
    for r in L["rooms"]:
        ft = r.get("feature")
        if not ft:
            continue
        want = SIDE_NORMAL[ft["wall"]]
        # is this wall that room's feature wall? its run is perpendicular to `want` and it bounds the room on that side
        b = r["bounds"]
        edge = {"north": (b[1] - T / 2, "z"), "south": (b[3] + T / 2, "z"), "east": (b[2] + T / 2, "x"), "west": (b[0] - T / 2, "x")}[ft["wall"]]
        coord = mid[1] if edge[1] == "z" else mid[0]
        if abs(coord - edge[0]) > 0.05:
            continue
        # ... and it has to be THIS room's wall. Two rooms share a line: the
        # north walls of the gaze and the stack both run along z = -9.2, so
        # matching on the perpendicular coordinate alone made every feature
        # wall match twice and built every vine twice, one set exactly on top
        # of the other. The wall's midpoint must lie across the room as well.
        across = mid[0] if edge[1] == "z" else mid[1]
        lo_a, hi_a = (b[0], b[2]) if edge[1] == "z" else (b[1], b[3])
        if not (lo_a <= across <= hi_a):
            continue
        # the run of the face inside the room
        lo, hi = (b[0], b[2]) if edge[1] == "z" else (b[1], b[3])
        n = (want[0], want[1])
        face_c = (edge[0] + n[0] * T / 2, ) if edge[1] == "x" else (edge[0] + n[1] * T / 2,)
        span = hi - lo
        cnt = int(span / 0.6)
        # the rosette row, arrayed along the run
        bpy.ops.mesh.primitive_cylinder_add(radius=0.11, depth=0.05, vertices=12)
        ros = bpy.context.active_object; ros.name = "cut_frieze_" + r["key"]
        first = lo + (span - (cnt - 1) * 0.6) / 2
        if edge[1] == "z":
            ros.location = bl2(first, edge[0] + n[1] * T / 2 - n[1] * 0.01, 3.25); ros.rotation_euler = (math.pi / 2, 0, 0)
            step = Vector((0.6, 0, 0))
        else:
            ros.location = bl2(edge[0] + n[0] * T / 2 - n[0] * 0.01, first, 3.25); ros.rotation_euler = (0, math.pi / 2, 0)
            step = Vector((0, -0.6, 0))
        B.apply_all(ros); B.link(ros, "cutters"); ros.hide_render = True; ros.display_type = "WIRE"
        B.array(ros, cnt, step)
        B.boolean(wall, ros)
        for gz in (2.95, 3.55):
            if edge[1] == "z":
                g = B.cutter("cut_groove_" + r["key"] + str(gz), (span - 0.2, 0.03, 0.04), bl2((lo + hi) / 2, edge[0] + n[1] * T / 2 - n[1] * 0.0, gz - 0.02), 0)
            else:
                g = B.cutter("cut_groove_" + r["key"] + str(gz), (0.03, span - 0.2, 0.04), bl2(edge[0] + n[0] * T / 2 - n[0] * 0.0, (lo + hi) / 2, gz - 0.02), 0)
            B.boolean(wall, g)
        feature_faces.append((r, wall, n, lo, hi, edge))
    dv, df = B.clean(wall)
    B.bevel(wall, 0.01, 2)
    B.assign(wall, w["material"])
    for r in L["rooms"]:
        def looks_into(fn, c, r=r):
            return room_at(c.x + fn.x * 0.3, -c.y - fn.y * 0.3) is r
        B.assign(wall, r["walls"], looks_into)
        if r.get("feature"):
            want = SIDE_NORMAL[r["feature"]["wall"]]
            B.assign(wall, r["feature"]["material"], lambda fn, c, r=r, want=want: looks_into(fn, c, r) and fn.x * want[0] + (-fn.y) * want[1] > 0.9)
    B.cube_project(wall, TILE)
    exported.append((wall, 6000, False))
    log.append("%s: %d faces" % (wall.name, len(wall.data.polygons)))

# ---- vines on the feature walls ------------------------------------------------------------
for r, wall, n, lo, hi, edge in feature_faces:
    if not r["feature"].get("vines"):
        continue
    if edge[1] == "z":
        origin = bl2(lo + 0.3, edge[0] + n[1] * T / 2, 0); right = (1, 0, 0)
    else:
        origin = bl2(edge[0] + n[0] * T / 2, lo + 0.3, 0); right = (0, -1, 0)
    normal = Vector(bl2(n[0], n[1]))
    # the station on this wall, as a keep out box the vines turn away from:
    # `along` is metres from the wall's left foot, on whichever axis it runs
    avoid = []
    for k, st in L["stations"].items():
        if st["room"] != r["id"]:
            continue
        coord = st["point"][0] if edge[1] == "z" else st["point"][2]
        along = coord - (lo + 0.3)
        avoid.append((along - st["w"] / 2 - 0.3, along + st["w"] / 2 + 0.3, st["point"][1] - st["h"] / 2 - 0.3, st["point"][1] + st["h"] / 2 + 0.3))
    stems, leaves = B.vines("vines_" + r["key"], origin, right, normal, (hi - lo) - 0.6, H - 0.3, seed=100 + r["id"], count=4, avoid=avoid)
    exported.append((stems, 12000, False)); exported.append((leaves, 2000, False, True))

# ---- floors and the void ------------------------------------------------------------------
for r in L["rooms"]:
    b = r["bounds"]
    inset = 0.0 if r["id"] == 0 else -T / 2
    fl = B.slab("floor_" + r["key"], (b[2] - b[0] - 2 * inset, b[3] - b[1] - 2 * inset, 0.02), bl2((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, -0.02))
    B.assign(fl, r["floor"]); B.cube_project(fl, TILE); exported.append((fl, 100, True))
    if r["id"] != 0:
        ce = B.slab("void_" + r["key"], (b[2] - b[0] + T, b[3] - b[1] + T, 0.02), bl2((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, H))
        B.assign(ce, "mat_void_black"); B.cube_project(ce, TILE); exported.append((ce, 100, True))

# ---- the truss: rails, posts, hangers, on the grid ---------------------------------------
tr = FX["truss"]
RAIL, DROP, POST = 0.06, 0.24, 0.5
for rid in tr["rooms"]:
    r = [q for q in L["rooms"] if q["id"] == rid][0]
    b = r["bounds"]
    parts = []
    def ladder(name, x0, z0, x1, z1):
        length = math.hypot(x1 - x0, z1 - z0)
        ang = math.atan2(-(z1 - z0), x1 - x0)
        mid = ((x0 + x1) / 2, (z0 + z1) / 2)
        parts.append(B.slab(name + "_top", (length, RAIL, RAIL), bl2(mid[0], mid[1], tr["y"] - RAIL / 2), ang, "fixtures"))
        parts.append(B.slab(name + "_bot", (length, RAIL, RAIL), bl2(mid[0], mid[1], tr["y"] - DROP - RAIL / 2), ang, "fixtures"))
        cnt = max(2, int(length / POST) + 1); step = length / (cnt - 1)
        post = B.slab(name + "_post", (0.03, 0.03, DROP), bl2(x0, z0, tr["y"] - DROP), ang, "fixtures")
        B.array(post, cnt, Vector(((x1 - x0) / length * step, -(z1 - z0) / length * step, 0)))
        parts.append(post)
    x = b[0] + tr["grid"] / 2
    while x < b[2] - 0.1:
        ladder("truss_r%d_x%d" % (rid, int(x * 10)), x, b[1] + T / 2, x, b[3] - T / 2); x += tr["grid"]
    z = b[1] + tr["grid"] / 2
    while z < b[3] - 0.1:
        ladder("truss_r%d_z%d" % (rid, int(-z * 10)), b[0] + T / 2, z, b[2] - T / 2, z); z += tr["grid"]
    x = b[0] + tr["grid"] / 2
    while x < b[2] - 0.1:
        z = b[1] + tr["grid"] / 2
        while z < b[3] - 0.1:
            parts.append(B.slab("hanger", (0.04, 0.04, H - tr["y"]), bl2(x, z, tr["y"]), 0, "fixtures")); z += tr["grid"]
        x += tr["grid"]
    truss = B.join(parts, "truss_r%d" % rid)
    B.clean(truss); B.assign(truss, "mat_metal_black"); B.cube_project(truss, TILE)
    exported.append((truss, 20000, False))

# ---- one track head per plaque and per station, aimed ---------------------------------------------
heads = [(p["pos"], p["normal"], "plaque_" + p["id"]) for p in L["plaques"]] + [(s["point"], s["normal"], "station_" + k) for k, s in L["stations"].items()]
so = FX["lighting"]["standoff"]
for i, (aim_l, n, what) in enumerate(heads):
    pos_l = [aim_l[0] + n[0] * so, tr["y"] - DROP - 0.15, aim_l[2] + n[2] * so]
    pos, aim = Vector(bl(pos_l)), Vector(bl(aim_l))
    d = (aim - pos).normalized()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.2, vertices=16)
    barrel = bpy.context.active_object; barrel.name = "head_%d_barrel" % i
    barrel.location = pos + d * 0.1; barrel.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    B.apply_all(barrel); B.link(barrel, "fixtures")
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.01, vertices=16)
    lens = bpy.context.active_object; lens.name = "lens_%s" % what
    lens.location = pos + d * 0.205; lens.rotation_euler = barrel.rotation_euler
    B.apply_all(lens); B.link(lens, "fixtures")
    stem = B.slab("head_%d_stem" % i, (0.03, 0.03, 0.15), (pos.x, pos.y, pos.z), 0, "fixtures")
    yoke = B.slab("head_%d_yoke" % i, (0.16, 0.03, 0.03), (pos.x, pos.y, pos.z - 0.015), 0, "fixtures")
    head = B.join([barrel, stem, yoke], "trackhead_%s" % what)
    B.clean(head); B.assign(head, "mat_metal_black"); B.smart_project(head, TILE)
    B.assign(lens, "mat_lamp"); B.smart_project(lens, TILE)
    exported.append((head, 1200, False)); exported.append((lens, 200, False))

# ---- stanchions before each station ----------------------------------------------------------------
sp = FX["stanchions"]
for k, st in L["stations"].items():
    n = st["normal"]; nn = math.hypot(n[0], n[2])
    c = bl2(st["point"][0] + n[0] / nn * sp["standoff"], st["point"][2] + n[2] / nn * sp["standoff"], 0)
    posts, belt = B.stanchions("stanchion_" + k, c, Vector(bl2(n[0] / nn, n[2] / nn)), sp["halfSpan"], sp["postHeight"], sp["beltHeight"])
    exported.append((posts, 3000, False)); exported.append((belt, 100, True))

# ---- exit signs ----------------------------------------------------------------------------------
for i, e in enumerate(FX["exitSigns"]):
    n = e["normal"]
    sign = B.slab("exit_%d" % i, (0.36, 0.08, 0.16), bl2(e["pos"][0] + n[0] * 0.04, e["pos"][2] + n[2] * 0.04, e["pos"][1] - 0.08), facing(n), "fixtures")
    B.assign(sign, "mat_metal_black")
    nb = Vector(bl2(n[0], n[2]))
    B.assign(sign, "mat_sign_exit", lambda fn, c, nb=nb: fn.dot(nb) > 0.9)
    B.cube_project(sign, TILE); B.decal_uv(sign, lambda fn, c, nb=nb: fn.dot(nb) > 0.9)
    exported.append((sign, 100, True))

# ---- extinguishers: body with a label band cut in, neck, handle, bracket -------------------------------
for i, e in enumerate(FX["extinguishers"]):
    n = e["normal"]
    cx, cy, cz = e["pos"][0] + n[0] * 0.14, e["pos"][1], e["pos"][2] + n[2] * 0.14
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.5, vertices=20)
    body = bpy.context.active_object; body.name = "ext_%d_body" % i
    body.location = bl2(cx, cz, cy); B.apply_all(body); B.link(body, "fixtures")
    band = B.cutter("cut_ext_%d_band" % i, (0.3, 0.3, 0.12), bl2(cx, cz, cy - 0.06))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.077, depth=0.3, vertices=20)
    keep = bpy.context.active_object; keep.name = "cut_ext_%d_keep" % i
    keep.location = bl2(cx, cz, cy); B.apply_all(keep); B.link(keep, "cutters"); keep.hide_render = True
    B.boolean(band, keep)                       # the band becomes a ring 3 mm deep
    B.boolean(body, band)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.08, vertices=12)
    neck = bpy.context.active_object; neck.name = "ext_%d_neck" % i
    neck.location = bl2(cx, cz, cy + 0.29); B.apply_all(neck); B.link(neck, "fixtures")
    handle = B.slab("ext_%d_handle" % i, (0.14, 0.025, 0.02), bl2(cx, cz, cy + 0.33), facing(n), "fixtures")
    bracket = B.slab("ext_%d_bracket" % i, (0.08, 0.06, 0.12), bl2(e["pos"][0] + n[0] * 0.05, e["pos"][2] + n[2] * 0.05, cy - 0.06), facing(n), "fixtures")
    ext = B.join([body, neck, handle, bracket], "extinguisher_%d" % i)
    B.clean(ext); B.assign(ext, "mat_metal_black"); B.assign(ext, "mat_extinguisher", lambda fn, c, cy=cy: cy - 0.26 < c.z < cy + 0.26 and abs(fn.z) < 0.9)
    B.smart_project(ext, TILE)
    exported.append((ext, 1500, False))

# ---- the staff door: a recess cut into its wall, a slab, a plate, a handle -----------------------------
sd = FX["staffDoor"]
n = sd["normal"]
def nearest_wall(x, z):
    best = None
    for w in L["walls"]:
        ax, az = w["a"]; bx, bz = w["b"]
        t = max(0, min(1, ((x - ax) * (bx - ax) + (z - az) * (bz - az)) / ((bx - ax) ** 2 + (bz - az) ** 2)))
        dist = math.hypot(ax + (bx - ax) * t - x, az + (bz - az) * t - z)
        if best is None or dist < best[0]:
            best = (dist, bpy.data.objects["wall_" + w["name"]])
    return best[1]
wall = nearest_wall(sd["pos"][0], sd["pos"][2])
B.boolean(wall, B.cutter("cut_staff_recess", (sd["w"] + 0.1, 0.06, sd["h"] + 0.05), bl2(sd["pos"][0] - n[0] * 0.03, sd["pos"][2] - n[2] * 0.03), facing(n)))
B.clean(wall); B.cube_project(wall, TILE)
door = B.slab("staff_door", (sd["w"], 0.04, sd["h"]), bl2(sd["pos"][0] - n[0] * 0.04, sd["pos"][2] - n[2] * 0.04), facing(n), "fixtures")
B.assign(door, "mat_door_staff"); B.cube_project(door, TILE)
nb = Vector(bl2(n[0], n[2]))
B.decal_uv(door, lambda fn, c, nb=nb: fn.dot(nb) > 0.9); exported.append((door, 100, True))
plate = B.slab("staff_plate", (0.3, 0.01, 0.08), bl2(sd["pos"][0] - n[0] * 0.015, sd["pos"][2] - n[2] * 0.015, 1.6), facing(n), "fixtures")
B.assign(plate, "mat_sign_staff"); B.cube_project(plate, TILE); B.decal_uv(plate, lambda fn, c, nb=nb: fn.dot(nb) > 0.9); exported.append((plate, 100, True))
bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.1, vertices=10)
knob = bpy.context.active_object; knob.name = "staff_handle"
knob.location = bl2(sd["pos"][0] + n[0] * 0.03 + nb.y * 0.35, sd["pos"][2] + n[2] * 0.03 - nb.x * 0.35, 1.05)
knob.rotation_euler = nb.to_track_quat("Z", "Y").to_euler()
B.apply_all(knob); B.link(knob, "fixtures"); B.assign(knob, "mat_metal_black"); B.smart_project(knob, TILE); exported.append((knob, 200, False))

# ---- the doors of the exhibit: slabs the engine slides ---------------------------------------------------
for d in L["doors"]:
    if not d["slab"]:
        continue
    slab = B.slab("door_%d_slab" % d["i"], (DW, 0.24, DH), bl2(d["at"][0], d["at"][1]), 0.0 if d["axis"] == "x" else math.pi / 2, "doors")
    B.bevel(slab, 0.01, 2); B.assign(slab, "mat_door_stone"); B.cube_project(slab, TILE)
    exported.append((slab, 300, True))

# ---- the arch: two pillars, a half torus cut by a boolean, a keystone, the hall sign --------------------
for sx in (-1.45, 1.45):
    p = B.slab("arch_pillar_%s" % ("w" if sx < 0 else "e"), (0.5, 0.5, 2.7), bl2(sx, 0.1), 0, "arch")
    B.bevel(p, 0.01, 2); B.assign(p, "mat_stone_arch"); B.cube_project(p, TILE); exported.append((p, 300, True))
bpy.ops.mesh.primitive_torus_add(major_radius=1.45, minor_radius=0.26, major_segments=28, minor_segments=10)
tor = bpy.context.active_object; tor.name = "arch_top"
tor.rotation_euler = (math.pi / 2, 0, 0); tor.location = bl2(0, 0.1, 2.7); B.apply_all(tor); B.link(tor, "arch")
B.boolean(tor, B.cutter("cut_arch_lower", (4.0, 1.0, 2.0), bl2(0, 0.1, 0.7)))
B.clean(tor); B.assign(tor, "mat_stone_arch"); B.smart_project(tor, TILE); exported.append((tor, 1200, False))
key = B.slab("arch_keystone", (0.5, 0.6, 0.5), bl2(0, 0.1, 3.9), 0, "arch")
key.rotation_euler = (0, math.pi / 4, 0); B.apply_all(key); B.assign(key, "mat_stone_arch"); B.smart_project(key, TILE); exported.append((key, 100, True))
sign = B.slab("sign_hall", (1.7, 0.02, 0.66), bl2(0, -0.59, 3.25 - 0.33), 0, "arch")
B.assign(sign, "mat_sign_hall"); B.cube_project(sign, TILE); B.decal_uv(sign, lambda fn, c: fn.y < -0.9); exported.append((sign, 100, True))

# ---- plaque planes: the engine paints them -------------------------------------------------------
for p in L["plaques"]:
    n = p["normal"]
    pl = B.slab("plaque_" + p["id"], (1.4, 0.02, 1.0), bl2(p["pos"][0] + n[0] * 0.01, p["pos"][2] + n[2] * 0.01, p["pos"][1] - 0.5), facing(n), "plaques")
    B.assign(pl, "mat_plaque"); B.cube_project(pl, TILE)
    nb = Vector(bl2(n[0], n[2]))
    B.decal_uv(pl, lambda fn, c, nb=nb: fn.dot(nb) > 0.9); exported.append((pl, 100, True))

# ---- the gate, the files, the proof -------------------------------------------------------------------
tris = 0
for entry in exported:
    obj, budget, closed = entry[0], entry[1], entry[2]
    tris += B.check(obj, TILE, budget, closed, decal=len(entry) > 3 and entry[3]) or 0
cols = [bpy.data.collections[c] for c in ("shell", "fixtures", "doors", "arch", "plaques")]
out = os.path.join(B.ROOT, "assets", "exhibit", NAME)
size = B.export_glb(out + ".glb", cols)
B.save_blend(out + ".blend")
voids = [o for o in bpy.data.objects if o.name.startswith("void_")]
B.render(os.path.join(B.ROOT, "docs", "reference", NAME + "_shell_overview.png"), (24, -16, 28), (-4, 11, 0), (1280, 900), hide=voids, fov=50)
B.render(os.path.join(B.ROOT, "docs", "reference", NAME + "_shell_room1.png"), (0.0, 2.0, 1.7), (0.0, 9.0, 2.0), (960, 720), fov=78)
B.render(os.path.join(B.ROOT, "docs", "reference", NAME + "_shell_room3.png"), (-6.0, 13.4, 1.7), (-12.4, 13.4, 1.8), (960, 720), fov=78)
print("\n".join(log[:3]) + "\n...")
print("BUILT %s: %d objects, %d triangles, %d bytes glb" % (NAME, len(exported), tris, size))

# Build the exhibit's props in Blender, headless, one glb each, at the origin:
#
#   blender -b --python tools/build_props.py
#
# The three eye discs, the stack's plinth, peg and four rings, a speech pad, a
# seeing stone, a decal plate, a door lamp and the ancestor. Every one comes
# through tools/blenderlib.py like the shell does (CLAUDE.md 5, docs/BLENDER.md):
# materials named for roles in data/materials.json, UVs at world scale, the
# gate, a render as the proof. Writes assets/props/<name>.glb, one .blend
# holding all of them laid out for a person, and docs/reference/elmorian_props.png.
#
# Frame: a prop's front faces Blender -Y, which the glTF exporter's y up
# conversion turns into +Z, the direction the prototype's props face before
# the scene turns them to their wall. Heights are along Blender Z (engine Y).

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import blenderlib as B  # noqa: E402

with open(os.path.join(B.ROOT, "data", "layout", "elmorian.json")) as f:
    TILE = 1024.0 / json.load(f)["texelDensity"]
OUT = os.path.join(B.ROOT, "assets", "props")
FRONT = lambda n, c: n.y < -0.9          # the face toward the visitor  # noqa: E731

B.reset_scene()
built = []      # (collection name, [objects], glb budget, closed)


def bake(obj):
    """Location into the vertices too, so a prop's origin is the point the
    scene places: the centre of a pad, the base of a plinth."""
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def primitive(name, col, op, **kw):
    op(**kw)
    o = bpy.context.active_object
    o.name = name
    return B.link(o, col)


def cylinder_y(name, col, radius, depth, vertices=40, at=(0, 0, 0), r2=None):
    """A cylinder (or a cone frustum with r2) whose axis is Blender Y, so
    its flat face looks at the visitor."""
    if r2 is None:
        o = primitive(name, col, bpy.ops.mesh.primitive_cylinder_add, radius=radius, depth=depth, vertices=vertices)
    else:
        o = primitive(name, col, bpy.ops.mesh.primitive_cone_add, radius1=radius, radius2=r2, depth=depth, vertices=vertices)
    o.rotation_euler = (math.pi / 2, 0, 0)
    o.location = at
    return bake(o)


def finish(objs, col, budget, closed=False, decal=False, smooth=True):
    """Clean, then smooth: a turned or rounded prop is shaded smooth across
    its curves and hard across its edges (35 degrees is the line), because
    an eye or a ring with every facet showing reads as a model, not a thing."""
    for o in objs:
        B.clean(o)
        if smooth:
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o], selected_editable_objects=[o]):
                bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    built.append((col, objs, budget, closed, decal))


# ---- room 1: three eye discs, face toward the visitor, turned about their axis ----
for i, r in enumerate((0.62, 0.44, 0.3)):
    col = "eye_disc_%d" % i
    d = cylinder_y(col, col, r, 0.16)
    B.assign(d, "mat_stone_prop"); B.smart_project(d, TILE)
    B.assign(d, "mat_decal", FRONT); B.decal_uv(d, FRONT)
    finish([d], col, 400, closed=True)

# ---- room 2: plinth, peg, four rings ------------------------------------------
pl = B.slab("plinth", (1.1, 3.3, 0.9), (0, 0, 0), 0, "plinth")
B.bevel(pl, 0.01, 2); B.assign(pl, "mat_stone_plinth"); B.cube_project(pl, TILE)
finish([pl], "plinth", 300, closed=True, smooth=False)
pg = B.slab("peg", (0.16, 0.16, 1.0), (0, 0, 0), 0, "peg")
B.assign(pg, "mat_stone_peg"); B.cube_project(pg, TILE)
finish([pg], "peg", 100, closed=True, smooth=False)
for sz in range(4):
    col = "ring_%d" % sz
    ring = primitive(col, col, bpy.ops.mesh.primitive_torus_add, major_radius=0.17 + sz * 0.09, minor_radius=0.075, major_segments=36, minor_segments=12)
    bake(ring)
    B.assign(ring, "mat_ring_%d" % sz); B.smart_project(ring, TILE)
    finish([ring], col, 1000, closed=True)

# ---- room 3: a speech pad, its front a decal the scene chooses ----------------
pad = B.slab("pad", (0.62, 0.12, 0.62), (0, 0, -0.31), 0, "pad")
B.bevel(pad, 0.006, 2); B.assign(pad, "mat_stone_peg"); B.cube_project(pad, TILE)
B.assign(pad, "mat_decal", FRONT); B.decal_uv(pad, FRONT)
finish([pad], "pad", 300, closed=True, smooth=False)

# ---- room 4: a seeing stone, dark glass in a stone rim ----------------------------
st = cylinder_y("stone", "stone", 0.55, 0.05)
B.assign(st, "mat_stone_base"); B.smart_project(st, TILE)
B.assign(st, "mat_stone_face", FRONT)
finish([st], "stone", 400, closed=True)

# ---- a plate: one picture from assets/art on a unit square, scaled by the scene ---
plate = primitive("plate", "plate", bpy.ops.mesh.primitive_plane_add, size=1.0)
plate.rotation_euler = (math.pi / 2, 0, 0); bake(plate)
B.assign(plate, "mat_decal"); B.cube_project(plate, TILE); B.decal_uv(plate, FRONT)
finish([plate], "plate", 2, decal=True, smooth=False)

# ---- a door lamp: a small disc that a scene lights green, red or not at all -----
lamp = cylinder_y("door_lamp", "door_lamp", 0.06, 0.01, vertices=20)
B.assign(lamp, "mat_door_lamp"); B.smart_project(lamp, TILE)
finish([lamp], "door_lamp", 200, closed=True)

# ---- the ancestor: a figure gone to stone, facing the door ---------------------------
col = "ancestor"
parts = []
parts.append(primitive("body", col, bpy.ops.mesh.primitive_cone_add, vertices=24, radius1=0.5, radius2=0.34, depth=1.5))
parts[-1].location = (0, 0, 0.75)
parts.append(primitive("neck", col, bpy.ops.mesh.primitive_cone_add, vertices=16, radius1=0.22, radius2=0.16, depth=0.3))
parts[-1].location = (0, 0, 1.6)
head = primitive("head", col, bpy.ops.mesh.primitive_uv_sphere_add, segments=28, ring_count=20, radius=0.36)
head.scale = (1.0, 0.95, 1.3); head.location = (0, 0, 2.15); parts.append(head)
# the sil, a single tentacle from the crown, as a bevelled curve made mesh
curve = bpy.data.curves.new("sil_curve", "CURVE")
curve.dimensions = "3D"; curve.bevel_depth = 0.09; curve.bevel_resolution = 4; curve.resolution_u = 8
spline = curve.splines.new("NURBS")
pts = [(0, 0.05, 2.55), (0.12, 0.3, 2.95), (0.5, 0.6, 2.8), (0.62, 0.5, 2.1), (0.55, 0.25, 1.5)]
spline.points.add(len(pts) - 1)
for p, xyz in zip(spline.points, pts):
    p.co = (xyz[0], xyz[1], xyz[2], 1.0)
spline.use_endpoint_u = True; spline.order_u = 3
sil = bpy.data.objects.new("sil", curve); B.collection(col).objects.link(sil)
sil = B.to_mesh(sil); parts.append(sil)
tip = primitive("tip", col, bpy.ops.mesh.primitive_uv_sphere_add, segments=12, ring_count=8, radius=0.09)
tip.location = pts[-1]; parts.append(tip)
for o in parts:
    bake(o)
body = B.join(parts, "ancestor_body")
B.assign(body, "mat_stone_ancestor"); B.smart_project(body, TILE)
eyes = []
for (x, y, r), role in zip(((-0.14, 2.08, 0.14), (0.16, 2.1, 0.1), (0.0, 2.4, 0.06)), ("mat_eye_white", "mat_eye_white", "mat_eye_glow")):
    e = primitive("eye", col, bpy.ops.mesh.primitive_uv_sphere_add, segments=18, ring_count=12, radius=r)
    e.location = (x, -0.3, y); bake(e); B.assign(e, role); eyes.append(e)
    p = primitive("pupil", col, bpy.ops.mesh.primitive_uv_sphere_add, segments=12, ring_count=8, radius=r * 0.45)
    p.location = (x, -(0.3 + r * 0.75), y); bake(p); B.assign(p, "mat_eye_pupil"); eyes.append(p)
eyes = B.join(eyes, "ancestor_eyes"); B.smart_project(eyes, TILE)
base = primitive("ancestor_base", col, bpy.ops.mesh.primitive_cone_add, vertices=24, radius1=0.8, radius2=0.7, depth=0.2)
base.location = (0, 0, 0.1); bake(base); B.assign(base, "mat_stone_base"); B.smart_project(base, TILE)
finish([body, eyes, base], col, 9000)

# ---- the gate, the files, the proof ---------------------------------------------------
os.makedirs(OUT, exist_ok=True)
total = 0
for col, objs, budget, closed, decal in built:
    tris = sum(B.check(o, TILE, None, closed, decal=decal) or 0 for o in objs)
    if tris > budget:
        raise RuntimeError("%s: %d triangles over the budget of %d" % (col, tris, budget))
    total += tris
    size = B.export_glb(os.path.join(OUT, col + ".glb"), [bpy.data.collections[col]])
    print("  %-12s %5d tris %7d bytes" % (col, tris, size))

# Laid out in a row for the person opening the .blend and for the render; the
# glbs above were exported before anything moved.
x = 0.0
for col, objs, _, _, _ in built:
    for o in objs:
        o.location.x += x
    x += 1.6
B.save_blend(os.path.join(OUT, "props.blend"))
B.render(os.path.join(B.ROOT, "docs", "reference", "elmorian_props.png"), (x / 2, -9.0, 3.2), (x / 2, 0.0, 1.0), (1600, 600), fov=62)
print("BUILT props: %d glbs, %d triangles" % (len(built), total))

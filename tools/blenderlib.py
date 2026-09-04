# The one implementation of what every Blender build in this repository does:
# make a slab, cut it, clean it, unwrap it at world scale, check it, export
# it, render the proof. Per docs/BLENDER.md, and per CLAUDE.md 4.1: a second
# copy of any of these in a generator script is the defect the rule names.
#
# Runs inside Blender only: `blender -b --python tools/<script>.py`.

import math
import os

import bmesh
import bpy
from mathutils import Vector

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ---- scene ---------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def link(obj, col_name):
    col = collection(col_name)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


# ---- materials are roles ---------------------------------------------------------------
# The engine binds textures by these names. The colours here are only so a
# Workbench render tells the roles apart.
ROLE_COLORS = {
    "mat_paint_green": (0.10, 0.19, 0.15), "mat_paint_plum": (0.28, 0.15, 0.20),
    "mat_carpet": (0.33, 0.24, 0.21), "mat_brick_temple": (0.52, 0.42, 0.30),
    "mat_metal_black": (0.04, 0.04, 0.045), "mat_stone_arch": (0.58, 0.53, 0.43),
    "mat_stone_paving": (0.30, 0.29, 0.26), "mat_void_black": (0.015, 0.015, 0.015),
    "mat_sign_exit": (0.10, 0.85, 0.30), "mat_sign_staff": (0.85, 0.82, 0.70),
    "mat_lamp": (1.0, 0.92, 0.72), "mat_extinguisher": (0.72, 0.07, 0.05),
    "mat_door_staff": (0.42, 0.40, 0.38), "mat_door_stone": (0.36, 0.34, 0.30),
    "mat_sign_hall": (0.62, 0.58, 0.50), "mat_plaque": (0.55, 0.52, 0.44),
    "mat_relief_floral": (0.60, 0.52, 0.40), "mat_vine": (0.28, 0.22, 0.14), "mat_leaf": (0.22, 0.36, 0.18),
    "mat_belt": (0.45, 0.08, 0.10),
}


def material(role):
    if not role.startswith("mat_"):
        raise ValueError("a material is named for a role, mat_<role>: %r" % role)
    m = bpy.data.materials.get(role)
    if m is None:
        m = bpy.data.materials.new(role)
        m.use_nodes = True
        rgb = ROLE_COLORS.get(role, (0.5, 0.5, 0.5))
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85 if "metal" not in role else 0.5
        if "metal" in role:
            bsdf.inputs["Metallic"].default_value = 0.9
        if role in ("mat_sign_exit", "mat_lamp"):
            bsdf.inputs["Emission Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
            bsdf.inputs["Emission Strength"].default_value = 3.0
        m.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return m


def assign(obj, role, faces=None):
    """Give obj the role material; with `faces` (a bmesh face predicate on
    a face's world normal and centre) only those faces take it."""
    m = material(role)
    if m.name not in [s.material.name for s in obj.material_slots if s.material]:
        obj.data.materials.append(m)
    idx = [s.material.name for s in obj.material_slots].index(m.name)
    if faces is None:
        for p in obj.data.polygons:
            p.material_index = idx
    else:
        mw = obj.matrix_world
        for p in obj.data.polygons:
            n = (mw.to_3x3() @ p.normal).normalized()
            c = mw @ p.center
            if faces(n, c):
                p.material_index = idx
    return idx


# ---- solids ------------------------------------------------------------------------
def slab(name, size, at, rot_z=0.0, col="shell"):
    """A box of `size` (x, y, z) with its origin at the centre of its base."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    o.location = (at[0], at[1], at[2] + size[2] / 2)
    o.rotation_euler = (0, 0, rot_z)
    apply_all(o)
    return link(o, col)


def cutter(name, size, at, rot_z=0.0):
    """A boolean tool: overshoots by 0.02 so it never shares a face with what
    it cuts (docs/BLENDER.md 3). Lives in `cutters`, hidden from render."""
    o = slab(name, (size[0] + 0.02, size[1] + 0.02, size[2] + 0.02), (at[0], at[1], at[2] - 0.01), rot_z, "cutters")
    o.hide_render = True
    o.display_type = "WIRE"
    return o


def boolean(obj, tool, op="DIFFERENCE"):
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = tool
    apply_modifier(obj, mod.name)
    return obj


def bevel(obj, width=0.01, segments=2):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.harden_normals = True
    apply_modifier(obj, mod.name)
    return obj


def array(obj, count, offset):
    mod = obj.modifiers.new("array", "ARRAY")
    mod.count = count
    mod.use_relative_offset = False
    mod.use_constant_offset = True
    mod.constant_offset_displace = offset
    apply_modifier(obj, mod.name)
    return obj


def apply_modifier(obj, name):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier=name)


def apply_all(obj):
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def clean(obj, merge=0.0005):
    """Merge by distance, drop degenerate faces, normals outside. Returns what
    it removed, so a build can say so."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = (len(bm.verts), len(bm.faces))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.dissolve_degenerate(bm, dist=merge, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return before[0] - len(obj.data.vertices), before[1] - len(obj.data.polygons)


def join(objs, name):
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, selected_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


# ---- UVs at world scale ------------------------------------------------------------------
def cube_project(obj, tile):
    """Every face takes the two world coordinates across its dominant axis,
    divided by `tile` (the metres one texture covers). A texel is then the
    same size on every wall and every wall continues into the next; no view,
    no operator, no stretch on an axis aligned face."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    mw = obj.matrix_world
    for p in mesh.polygons:
        n = (mw.to_3x3() @ p.normal).normalized()
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            w = mw @ mesh.vertices[mesh.loops[li].vertex_index].co
            if ax == 0:
                u, v = (w.y, w.z) if n.x > 0 else (-w.y, w.z)
            elif ax == 1:
                u, v = (-w.x, w.z) if n.y > 0 else (w.x, w.z)
            else:
                u, v = (w.x, w.y) if n.z > 0 else (w.x, -w.y)
            uv[li].uv = (u / tile, v / tile)


def decal_uv(obj, pred):
    """The faces `pred` picks get their own 0..1 island, so a decal (a sign
    face, a plaque) lands on exactly that face. Everything else keeps its
    world scale UVs."""
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    mw = obj.matrix_world
    made = list(mesh.get("decal_faces", []))
    for p in mesh.polygons:
        n = (mw.to_3x3() @ p.normal).normalized()
        if not pred(n, mw @ p.center):
            continue
        made.append(p.index)
        pts = [mw @ mesh.vertices[mesh.loops[li].vertex_index].co for li in p.loop_indices]
        up = Vector((0, 0, 1))
        right = up.cross(n).normalized() if abs(n.z) < 0.9 else Vector((1, 0, 0))
        vup = n.cross(right).normalized()
        us = [q.dot(right) for q in pts]; vs = [q.dot(vup) for q in pts]
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        for li, u, v in zip(p.loop_indices, us, vs):
            uv[li].uv = ((u - u0) / max(1e-6, u1 - u0), (v - v0) / max(1e-6, v1 - v0))
    mesh["decal_faces"] = made          # the stretch report leaves these alone


def planar_project(obj, tile):
    """Every face onto its own plane, at world scale: zero stretch on any
    face by construction, and a seam at every edge, which is the right trade
    for a prop that wears a near uniform finish (black steel, a painted
    cylinder). Architecture is cube projected instead, for continuity."""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="UVMap")
    uv = mesh.uv_layers.active.data
    mw = obj.matrix_world
    up = Vector((0, 0, 1))
    for p in mesh.polygons:
        n = (mw.to_3x3() @ p.normal).normalized()
        right = up.cross(n).normalized() if abs(n.z) < 0.95 else Vector((1, 0, 0))
        vup = n.cross(right).normalized()
        for li in p.loop_indices:
            w = mw @ mesh.vertices[mesh.loops[li].vertex_index].co
            uv[li].uv = (w.dot(right) / tile, w.dot(vup) / tile)


def smart_project(obj, tile, margin=0.02):
    """Props are projected per face. Blender's smart projection was tried
    first and refused by the gate: it groups faces within its angle limit
    onto one island's plane, so a sixteen sided barrel's steep faces come
    out stretched by the cosine of that angle, 39 percent across the mesh.
    Per face is zero stretch by construction; the seams it leaves fall on
    finishes where they cannot show."""
    planar_project(obj, tile)


def _areas(obj, tile):
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    mw = obj.matrix_world
    wa = ua = 0.0
    for p in mesh.polygons:
        pts = [mw @ mesh.vertices[mesh.loops[li].vertex_index].co for li in p.loop_indices]
        uvs = [Vector(uv[li].uv) for li in p.loop_indices]
        wa += _poly_area(pts)
        ua += _poly_area2(uvs)
    return wa, ua


def _poly_area(pts):
    a = Vector((0, 0, 0))
    for i in range(1, len(pts) - 1):
        a += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
    return a.length / 2


def _poly_area2(pts):
    a = 0.0
    for i in range(1, len(pts) - 1):
        a += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
    return abs(a) / 2


def uv_stretch_report(obj, tile, band=0.08, face_band=0.25):
    """Per face, world area against UV area times the tile's area. Refuses a
    mesh whose faces vary by more than `band` about their median or any one
    face off by more than `face_band`. Returns (median ratio, worst face)."""
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    mw = obj.matrix_world
    ratios = []
    decals = set(mesh.get("decal_faces", []))
    for p in mesh.polygons:
        if p.index in decals:
            continue
        pts = [mw @ mesh.vertices[mesh.loops[li].vertex_index].co for li in p.loop_indices]
        uvs = [Vector(uv[li].uv) for li in p.loop_indices]
        wa, ua = _poly_area(pts), _poly_area2(uvs) * tile * tile
        if wa < 1e-6:
            continue
        # A strip narrower than about a centimetre (a bevel) holds no texel
        # to stretch; area over perimeter is half its width, whatever its length.
        perim = sum((pts[i] - pts[i - 1]).length for i in range(len(pts)))
        if perim > 0 and wa / perim < 0.006:
            continue
        ratios.append((ua / wa, p.index))
    if not ratios:
        if len(mesh.polygons):
            return None, None            # nothing but strips: a tube, a rail; nothing to stretch
        raise RuntimeError("%s: no faces" % obj.name)
    ratios.sort()
    med = ratios[len(ratios) // 2][0]
    worst = max(ratios, key=lambda r: abs(r[0] - med))
    spread = abs(worst[0] - med) / med
    if spread > face_band:
        raise RuntimeError("%s: face %d has UV stretch %.0f%% off the mesh's median (limit %.0f%%)"
                           % (obj.name, worst[1], spread * 100, face_band * 100))
    lo, hi = ratios[int(len(ratios) * 0.1)][0], ratios[int(len(ratios) * 0.9) - 1][0]
    if (hi - lo) / med > band * 2 and len(ratios) > 8:
        raise RuntimeError("%s: UV density varies %.0f%% across the mesh (limit %.0f%%)"
                           % (obj.name, (hi - lo) / med * 100, band * 200))
    return med, worst


# ---- the gate --------------------------------------------------------------------------------
def check(obj, tile, tri_budget=None, closed=False, decal=False):
    """What docs/BLENDER.md 8 refuses. Raises with the mesh, the face and the
    number. `decal` is a mesh whose every face is its own 0..1 island (leaf
    cards, a label): its density is the card's own and the tiling band does
    not apply."""
    if obj.type != "MESH":
        return
    if any(abs(s - 1.0) > 1e-6 for s in obj.scale):
        raise RuntimeError("%s: scale not applied %r" % (obj.name, tuple(obj.scale)))
    if not obj.data.uv_layers:
        raise RuntimeError("%s: no UV layer" % obj.name)
    for s in obj.material_slots:
        if s.material is None or not s.material.name.startswith("mat_"):
            raise RuntimeError("%s: material %r is not named for a role" % (obj.name, s.material and s.material.name))
    if not obj.material_slots:
        raise RuntimeError("%s: no material" % obj.name)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tri_budget and tris > tri_budget:
        raise RuntimeError("%s: %d triangles over the budget of %d" % (obj.name, tris, tri_budget))
    if closed:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        open_edges = [e for e in bm.edges if len(e.link_faces) != 2]
        bm.free()
        if open_edges:
            raise RuntimeError("%s: %d non manifold edges on a closed solid" % (obj.name, len(open_edges)))
    if not decal:
        uv_stretch_report(obj, tile)
    return tris


# ---- export and proof -------------------------------------------------------------------
def export_glb(path, collections):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in bpy.context.scene.objects:
        o.select_set(any(o.name in c.objects for c in collections))
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_materials="EXPORT", export_image_format="NONE",
                              export_normals=True, export_texcoords=True, export_tangents=False)
    return os.path.getsize(path)


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)


def render(path, cam_from, cam_to, size=(1280, 800), hide=(), fov=60.0):
    """A Workbench render from one camera: the proof that the model is right
    and not only exported."""
    sc = bpy.context.scene
    cam_data = bpy.data.cameras.new("proof_cam")
    cam_data.angle = math.radians(fov)
    cam = bpy.data.objects.new("proof_cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = Vector(cam_from)
    d = (Vector(cam_to) - Vector(cam_from)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    was = [(o, o.hide_render) for o in hide]
    for o in hide:
        o.hide_render = True
    bpy.ops.render.render(write_still=True)
    for o, h in was:
        o.hide_render = h
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cam_data)
    return path


# ---- props the layout derives ----------------------------------------------------------
def stanchions(name, centre, normal, half_span, post_h, belt_h, col="fixtures"):
    """Two posts and a belt across the front of a station. `centre` and
    `normal` are Blender vectors on the floor; the posts stand either side
    along the wall's run."""
    n = Vector(normal).normalized()
    t = Vector((-n.y, n.x, 0))
    parts = []
    for side in (-1, 1):
        at = Vector(centre) + t * (side * half_span)
        for r, d, z in ((0.18, 0.02, 0.0), (0.02, post_h, 0.02), (0.035, 0.03, post_h)):
            bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, vertices=20)
            o = bpy.context.active_object
            o.location = (at.x, at.y, at.z + z + d / 2)
            apply_all(o); link(o, col); parts.append(o)
    posts = join(parts, name + "_posts")
    clean(posts); assign(posts, "mat_metal_black"); smart_project(posts, 4.0)
    belt = slab(name + "_belt", (half_span * 2 - 0.05, 0.004, 0.05), (centre[0], centre[1], belt_h - 0.025), math.atan2(t.y, t.x), col)
    assign(belt, "mat_belt"); cube_project(belt, 4.0)
    return posts, belt


def to_mesh(obj):
    """A curve (with its bevel) as a mesh object of the same name, through
    the depsgraph rather than the convert operator, which will not run in a
    background context. The curve object is removed."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    new = bpy.data.objects.new(obj.name, me)
    new.matrix_world = obj.matrix_world
    cols = list(obj.users_collection)
    for c in cols:
        c.objects.link(new)
    name = obj.name
    bpy.data.objects.remove(obj)
    new.name = name
    return new


def vines(name, origin, right, normal, width, height, seed, count=5, col="fixtures", avoid=()):
    # `avoid`: (along0, along1, up0, up1) rectangles on the face, in metres
    # from the wall's left foot, that a vine turns away from: the puzzle
    # stands there.
    """A vine generator, and the one listed use of procedural generation in
    this build (docs/ARCHITECTURE.md ADR-7): vines climb a wall from its
    foot by a seeded random walk, branch once in a while, and carry leaf
    cards. The output is committed with the model; a rerun with the same
    seed writes the same vines. `origin` is the wall foot's left end on the
    face, `right` runs along it, `normal` points into the room."""
    import random
    rnd = random.Random(seed)
    right, normal = Vector(right).normalized(), Vector(normal).normalized()
    up = Vector((0, 0, 1))
    stems, leaves = [], []
    starts = [(rnd.uniform(0.15, 0.85), 0.05, rnd.uniform(1.8, min(height - 0.6, 3.4))) for _ in range(count)]
    branches = []
    for sx, sz, length in starts:
        pos = Vector(origin) + right * (sx * width) + up * sz + normal * 0.03
        pts, radii = [pos.copy()], [1.0]
        heading = Vector((rnd.uniform(-0.3, 0.3), 0, 1)).normalized()
        travelled = 0.0
        while travelled < length:
            heading = (heading + Vector((rnd.uniform(-0.55, 0.55), 0, rnd.uniform(0.2, 0.6)))).normalized()
            step = 0.15
            nxt = pos + (right * heading.x + up * heading.z) * step + normal * rnd.uniform(-0.01, 0.01)
            along, upv = (nxt - Vector(origin)).dot(right), (nxt - Vector(origin)).dot(up)
            blocked = along < 0.1 or along > width - 0.1
            for a0, a1, u0, u1 in avoid:
                if a0 < along < a1 and u0 < upv < u1:
                    blocked = True
            if blocked:
                # turn away: lean the other way and step along the wall instead of into the box
                heading.x = -heading.x if abs(heading.x) > 0.2 else (1.0 if along < width / 2 else -1.0)
                nxt = pos + right * (heading.x * step)
                a2 = (nxt - Vector(origin)).dot(right)
                if a2 < 0.1 or a2 > width - 0.1:
                    nxt = pos + up * step
            pos = nxt
            pts.append(pos.copy()); radii.append(max(0.25, 1.0 - travelled / length))
            travelled += step
            if rnd.random() < 0.06 and length - travelled > 0.6:
                branches.append((pos.copy(), (length - travelled) * 0.6))
        stems.append((pts, radii))
    for start, length in branches:
        pos = start.copy(); pts, radii = [pos.copy()], [0.6]
        heading = Vector((rnd.uniform(-0.8, 0.8), 0, 0.6)).normalized(); travelled = 0.0
        while travelled < length:
            heading = (heading + Vector((rnd.uniform(-0.5, 0.5), 0, rnd.uniform(0.1, 0.5)))).normalized()
            pos = pos + (right * heading.x + up * heading.z) * 0.15
            pts.append(pos.copy()); radii.append(max(0.2, 0.6 - travelled / length * 0.5)); travelled += 0.15
        stems.append((pts, radii))
    # the stems: one curve, bevelled to tubes, converted to a mesh
    cu = bpy.data.curves.new(name + "_curve", "CURVE")
    cu.dimensions = "3D"; cu.bevel_depth = 0.012; cu.bevel_resolution = 2; cu.resolution_u = 3
    for pts, radii in stems:
        sp = cu.splines.new("NURBS"); sp.points.add(len(pts) - 1)
        for i, (p, r) in enumerate(zip(pts, radii)):
            sp.points[i].co = (p.x, p.y, p.z, 1.0); sp.points[i].radius = r
        sp.use_endpoint_u = True; sp.order_u = 3
    vine = bpy.data.objects.new(name + "_stems", cu)
    bpy.context.scene.collection.objects.link(vine); link(vine, col)
    vine = to_mesh(vine); clean(vine); assign(vine, "mat_vine"); smart_project(vine, 4.0)
    # the leaves: a card every other point, turned a little each, its own 0..1 UVs
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for pts, radii in stems:
        for i in range(1, len(pts), 2):
            p = pts[i]
            ang = rnd.uniform(-0.8, 0.8); tilt = rnd.uniform(0.15, 0.6); sz = rnd.uniform(0.09, 0.15)
            a = right * math.cos(ang) + up * math.sin(ang)
            b = up * math.cos(ang) - right * math.sin(ang)
            b = (b * math.cos(tilt) + normal * math.sin(tilt)).normalized()
            base = p + normal * 0.02
            vs = [bm.verts.new(base + a * (-sz * 0.4)), bm.verts.new(base + a * (sz * 0.4)),
                  bm.verts.new(base + a * (sz * 0.4) + b * sz * 1.3), bm.verts.new(base + a * (-sz * 0.4) + b * sz * 1.3)]
            f = bm.faces.new(vs)
            for lp, uvc in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))):
                lp[uv_layer].uv = uvc
    me = bpy.data.meshes.new(name + "_leaves"); bm.to_mesh(me); bm.free()
    lv = bpy.data.objects.new(name + "_leaves", me)
    bpy.context.scene.collection.objects.link(lv); link(lv, col); assign(lv, "mat_leaf")
    return vine, lv

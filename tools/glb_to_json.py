#!/usr/bin/env python3
# Convert a committed .glb into the compact TEXT payload the prototype page
# embeds.
#
# Why this exists: a mockup page is one self contained file (CLAUDE.md 3), so
# the shell has to travel inside it, and a 3.8 MB binary glTF embedded as
# base64 is a binary file in a web page. The artifact share review refuses to
# pass a page that embeds a file type it cannot review, which is exactly what
# a model/gltf-binary blob is. So the .glb stays the committed asset that
# Blender writes, and this makes a build product from it: quantized integers
# in JSON, no base64, no file magic, nothing to sniff.
#
# It is also smaller. Positions and texture coordinates are 16 bit fixed
# point, and normals are left out entirely because the exporter already
# splits vertices at every hard edge, so the page's computeVertexNormals
# reproduces them.
#
# Usage: python3 tools/glb_to_json.py assets/exhibit/elmorian.glb [out.json]

import json
import math
import os
import struct
import sys


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        raise SystemExit("%s is not a binary glTF" % path)
    pos, js, bin_chunk = 12, None, b""
    while pos < len(data):
        ln, kind = struct.unpack("<I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if kind == b"JSON":
            js = json.loads(body)
        elif kind == b"BIN\x00":
            bin_chunk = body
        pos += 8 + ln
    return js, bin_chunk


COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
COUNT = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def accessor(g, blob, index):
    """One accessor as a flat list of numbers, honouring its stride."""
    a = g["accessors"][index]
    fmt, size = COMPONENT[a["componentType"]]
    n = COUNT[a["type"]]
    view = g["bufferViews"][a["bufferView"]]
    start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = view.get("byteStride") or n * size
    out = []
    for i in range(a["count"]):
        off = start + i * stride
        out.extend(struct.unpack_from("<" + fmt * n, blob, off))
    return out


def mat_mul(a, b):
    return [sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4)) for r in range(4) for c in range(4)]


def node_matrix(node):
    if "matrix" in node:                       # glTF stores column major
        m = node["matrix"]
        return [m[0], m[4], m[8], m[12], m[1], m[5], m[9], m[13],
                m[2], m[6], m[10], m[14], m[3], m[7], m[11], m[15]]
    t = node.get("translation", [0, 0, 0])
    q = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = q
    rot = [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0,
           2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0,
           2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0,
           0, 0, 0, 1]
    for c in range(3):
        for r in range(3):
            rot[r * 4 + c] *= s[c]
    rot[3], rot[7], rot[11] = t[0], t[1], t[2]
    return rot


def apply(m, x, y, z):
    return (m[0] * x + m[1] * y + m[2] * z + m[3],
            m[4] * x + m[5] * y + m[6] * z + m[7],
            m[8] * x + m[9] * y + m[10] * z + m[11])


def convert(path):
    g, blob = read_glb(path)
    parts = []
    IDENT = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

    def walk(index, parent):
        node = g["nodes"][index]
        world = mat_mul(parent, node_matrix(node))
        if "mesh" in node:
            mesh = g["meshes"][node["mesh"]]
            for pi, prim in enumerate(mesh["primitives"]):
                pos = accessor(g, blob, prim["attributes"]["POSITION"])
                uv = accessor(g, blob, prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in prim["attributes"] else None
                idx = accessor(g, blob, prim["indices"]) if "indices" in prim else list(range(len(pos) // 3))
                world_pos = []
                for i in range(0, len(pos), 3):
                    world_pos.extend(apply(world, pos[i], pos[i + 1], pos[i + 2]))
                name = node.get("name", mesh.get("name", "part"))
                parts.append({
                    "n": name if pi == 0 else "%s#%d" % (name, pi),
                    "m": g["materials"][prim["material"]]["name"] if "material" in prim else "",
                    "pos": world_pos, "uv": uv, "idx": idx,
                })
        for child in node.get("children", []):
            walk(child, world)

    for scene_node in g["scenes"][g.get("scene", 0)]["nodes"]:
        walk(scene_node, IDENT)

    # One quantization box for every position, so the page decodes with one
    # scale. The museum is about 25 m across, so 16 bits is under half a
    # millimetre and nothing shifts.
    allx = [v for p in parts for v in p["pos"][0::3]]
    ally = [v for p in parts for v in p["pos"][1::3]]
    allz = [v for p in parts for v in p["pos"][2::3]]
    lo = [min(allx), min(ally), min(allz)]
    hi = [max(allx), max(ally), max(allz)]
    span = [max(1e-6, hi[i] - lo[i]) for i in range(3)]

    out = {"pb": [round(v, 5) for v in lo + span], "parts": []}
    for p in parts:
        q = []
        for i, v in enumerate(p["pos"]):
            a = i % 3
            q.append(max(0, min(65535, int(round((v - lo[a]) / span[a] * 65535)))))
        entry = {"n": p["n"], "m": p["m"], "p": q, "i": p["idx"]}
        if p["uv"]:
            u0, u1 = min(p["uv"][0::2]), max(p["uv"][0::2])
            v0, v1 = min(p["uv"][1::2]), max(p["uv"][1::2])
            du, dv = max(1e-6, u1 - u0), max(1e-6, v1 - v0)
            entry["ub"] = [round(u0, 5), round(v0, 5), round(du, 5), round(dv, 5)]
            entry["t"] = [max(0, min(65535, int(round(((v - (u0 if i % 2 == 0 else v0)) / (du if i % 2 == 0 else dv)) * 65535))))
                          for i, v in enumerate(p["uv"])]
        out["parts"].append(entry)
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "assets/exhibit/elmorian.glb"
    data = convert(src)
    text = json.dumps(data, separators=(",", ":"))
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            f.write(text)
        print("wrote %s (%d bytes)" % (sys.argv[2], len(text)))
    else:
        tris = sum(len(p["i"]) for p in data["parts"]) // 3
        print("%d parts, %d triangles, %d bytes of JSON (%.2f MB)"
              % (len(data["parts"]), tris, len(text), len(text) / 1e6))

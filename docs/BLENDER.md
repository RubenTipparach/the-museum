# Modelling in Blender, headless, for this game

**Status: adopted, September 2026, on the owner's instruction to build the exhibit
in Blender with boolean modelling and to write the practice down.** These are the
rules every model in `assets/` is built to, and `tools/blenderlib.py` is where the
ones that can be checked are checked. A model that breaks one does not export.

Blender runs here (ADR-0 applies to tools as much as to the engine): the pinned build
is downloaded by `scripts/install-blender.sh` and every generator is run as
`blender -b --python tools/<script>.py`. Nothing is done in the interface that the
script cannot do again.

---

## 1. The scene is the layout, and the layout is a file

`data/layout/<exhibit>.json` is the one description of an exhibit: rooms, walls, door
openings, stations, plaques, fixtures. The Blender build reads it, the prototype reads
it, and the plan drawing in `docs/` is drawn from it. Nothing about where a wall stands
is typed into a script. A wall moved in the file moves everywhere; a wall moved by hand
in a `.blend` is a wall the next build puts back.

## 2. Units, scale, origins, names

- **Metres, scale 1.** `scene.unit_settings.system = 'METRIC'`, `scale_length = 1`.
  A door is 1.8 wide and 2.7 high in the file and 1.8 by 2.7 in the engine.
- **Apply every transform before export.** A mesh with an unapplied scale has UVs,
  normals and booleans that lie. `blenderlib.apply_all()` runs on everything.
- **Origins where the thing is held.** Architecture at the world origin, so the file's
  coordinates are the mesh's. A prop at the base of its own bounding box, on the floor
  line, so placing it is one position. A hanging fixture at its mount point.
- **Names say what and where.** `wall_r1_north`, `door_1_slab`, `fixture_exit_r2`,
  `prop_extinguisher`. Collections per room and one `cutters` collection for every
  boolean tool object, excluded from render and export.

## 3. Boolean modelling, and how it stays clean

Openings are cut, not modelled around. A wall is a slab; a door is a cutter the size
of the opening, and the boolean takes it out. That keeps the wall one object, gives
the opening real reveals, and means a moved door is a moved cutter.

- **Exact solver**, always. Fast is fast and leaves faces behind.
- **Cutters overshoot.** A cutter the exact thickness of the wall shares faces with it
  and the solver cannot decide who wins. Every cutter is 0.02 larger than the slab on
  every axis it passes through.
- **Apply booleans before UVs**, because a projected UV on the modifier stack is a UV
  on the slab, not on the cut.
- **Then clean.** Merge by distance at 0.0005, dissolve degenerate faces, recalculate
  normals outside. `blenderlib.clean()` does this and reports what it removed.
- **Bevel after the boolean**, small and few: 0.01 at two segments on architecture,
  with harden normals. It is what makes an edge catch light, and it is the difference
  between a box and a wall.
- **Modifier order** where more than one is used: Mirror, Array, Boolean, Bevel,
  Weighted Normal. Apply in that order.

## 4. UVs: uniform density, no stretch

The owner's brief, from the reference photograph: uniform unwrapping, no UV stretch.
Two rules make that mechanical rather than a matter of care:

- **Architecture is cube projected at world scale.** `uv.cube_project` with
  `cube_size` equal to the metres one texture tile covers and `scale_to_bounds`
  off, so a texel is the same size on every wall, every wall's texture is continuous
  with its neighbour's, and a 4 metre wall shows exactly as much brick as a 4 metre
  wall should. The texel density is written once, in `data/layout/<exhibit>.json`
  as `texelDensity` (pixels per metre), and every material's tile size follows it.
- **Props are projected per face, at the same density.** Every face onto its own
  plane, world coordinates divided by the tile: zero stretch on any face by
  construction, and a seam at every edge, which is the right trade for a prop that
  wears a near uniform finish (black steel, a painted cylinder). Blender's smart
  projection was tried first and the gate refused it: it groups faces within its angle
  limit onto one plane, and a sixteen sided barrel's steep faces came out 39 percent
  off. A prop that needs a continuous pattern across a curve is unwrapped by hand
  with seams, in the `.blend`, and that is the exception to write down when it comes.
- **It is checked, per face.** `blenderlib.uv_stretch_report` compares each face's
  world area to its UV area times the texture's area, and fails the export if the
  ratio across a mesh varies by more than 8 percent or any face is off by more than
  25 percent. Stretch is a number; nobody has to look for it. Bevel strips are exempt:
  a face a centimetre wide holds no texel to stretch, and the first run of the gate
  refused the facade for one at 27 percent, which was the check being right about
  the wrong thing.
- **No two parts share a UV area unless they tile.** A plaque, a sign face, an
  extinguisher label: their own island, no overlap, so a decal lands on one thing.

## 5. Materials are roles; textures come from one tool

- A material is named for a **role**: `mat_paint_green`, `mat_paint_plum`,
  `mat_carpet`, `mat_brick_temple`, `mat_metal_black`, `mat_stone_arch`,
  `mat_sign_exit`. The engine binds textures by that name. A mesh never carries a
  colour of its own.
- **Textures come from Material Maker** (CLAUDE.md 5), the `.ptex` committed beside
  the PNG set, every dimension a power of two, exported headless by
  `scripts/gen-textures.sh`. Until that runs here, `tools/gen_museum_textures.py`
  is the declared stopgap and is held to the same contract: a static file, a
  committed source, `--check` for drift.
- **One material per surface kind, not per object.** Every draw call is a material,
  and a room with twelve materials is twelve draws for what could be four.

## 6. Fixtures are props, placed by the layout

The things a real hall has and a game forgets: an exit sign over every door on the
way out, an extinguisher on the wall beside it at 1.1 metres, a staff door on a wall
nothing else needs, a black truss ceiling with track heads aimed at what is lit. Each
is one modelled prop in `assets/props/`, and `data/layout/<exhibit>.json` says where
each instance stands and which way it faces. The Blender build instances them; so
does the engine. A fixture added by hand to one room is a fixture the other rooms do
not have.

## 6a. The vines, and where generation is allowed to reach

The one generator in the build (`blenderlib.vines`, listed in ADR-7) climbs a feature
wall from its foot by a seeded random walk. It is given the puzzle's own extent on
that wall as a keep out box and turns away from it, because the first build grew a
vine straight across the middle eye: a generator that can reach the puzzle is a
generator that will, and the layout, not the seed, is what says where the puzzle is.

## 7. Export, and the proof

- **glTF binary**, `export_apply=True`, Y up, tangents on, materials exported by
  name, images NOT embedded (`export_image_format='NONE'`): the engine binds the
  role's textures itself, so the file stays small and one texture serves every
  mesh that wears it.
- The `.blend` the build writes is committed beside the `.glb` (CLAUDE.md 5), so the
  model can be opened and edited by a person, and the script can regenerate it.
- **A render is the proof.** Every build also renders the model from a fixed camera
  with Workbench, headless, to `docs/reference/`, because a mesh that exported is
  not a mesh that is right. Requirement 0, applied to a tool.

## 8. What the checks refuse

`tools/blenderlib.py` refuses to export a mesh with: no UV layer; an unapplied
transform; a non manifold edge on a closed solid; a face with UV stretch outside the
bands in section 4; a material not named for a role; a triangle count over the
budget the layout file gives that kind of object. The refusal names the mesh, the
face and the number, so the fix is a fix and not a hunt.

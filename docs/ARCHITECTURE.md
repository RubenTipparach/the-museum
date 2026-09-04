# The Museum: Architecture Decision Document

**Status: Proposed, September 2026.** This is the first document in the repository and
it is written to be reviewed before a line of engine code exists. Each ADR records a
decision and why; the engine survey in ADR-1 was checked against vendor releases in
early September 2026 (Godot 4.7.1, Bevy 0.19, godot-rust 0.5), and the version numbers
are the part that will go stale first. The structural conclusions are the durable part.

The project rules that every change is held to are in [`../CLAUDE.md`](../CLAUDE.md).
The photographs the puzzles are seeded from are in
[`reference/README.md`](reference/README.md). Section 11 is the list of questions the
owner needs to answer before Phase 0, and it is the section to read first.

---

## 1. The game, in one paragraph

You are locked inside an alien recreation of a human museum. The halls are the halls
of a natural history museum (a Pacific hall of carved figures and masks, a hall of
gems, a dinosaur, a table of trilobites, a Chinese altar, a diorama of a plantation),
and they are almost right. The lighting is low, the corridors are a little too long,
the labels explain the wrong things, and the artifacts have properties the originals
never had. It is played in first person. Walking up to an artifact and pressing it
moves the camera onto the object, in the manner of *The Room*, and the object becomes
the puzzle: turned, opened, arranged, listened to. The puzzles are in the tradition of
*Myst* and *Riven*: designed, self consistent, and solved by attention rather than by
inventory arithmetic. The aesthetic is liminal space: a familiar public building with
nobody in it, lit as if after hours.

## 2. Requirements (from the owner)

0. **The engine must run in the Claude Code online sandbox, headless.** Not
   negotiable, and it ranks above every other requirement. "Run" means install,
   test, build AND RENDER: in previous projects Claude rendered scenes in engine to
   troubleshoot and to prove visual work, and that is how this one is verified too.
   An engine that cannot draw a frame here is an engine whose visual claims nobody
   can check. ADR-0 is the proof that the chosen engine does.
1. **Lots of high quality lights.** A museum is hundreds of small lights: case lights,
   spots on artifacts, backlit tables, floor washes, emergency signs. That is the
   picture, and the engine has to carry it.
2. **First person**, with the camera transitioning into a focused puzzle view.
3. **Puzzles in the Myst / Riven vein**, seeded from real museum displays (section 9).
4. **Liminal, low light, uncanny.** Fog, bounce light, long sightlines, glass.
5. **Materials from Material Maker; models from Blender driven by Python**; open
   source procedural tools allowed for foliage and the like, offline.
6. **Write once and reuse, SOLID, clean code.** Not negotiable.
7. **Every major UI or gameplay change is approved on an interactive JavaScript
   prototype** (a Claude artifact or an HTML page) before it is built.
8. **Static assets.** Procedural generation only when authoring is genuinely
   impractical, and then as a build step whose output is committed.
9. Open to experimental choices, including Rust, or Godot with C#.

Two things about this game shape everything below, the way "small-N and kinematic"
shaped the space game:

- **It is an authored space.** Every room is placed by hand: the walls, the cases, the
  artifacts, and above all the lights. That makes an EDITOR the most valuable tool the
  engine can offer, ahead of raw renderer features. A renderer that needs lights placed
  by typing coordinates is a renderer that will have far fewer lights.
- **It is static.** Nothing in the architecture moves. Almost all of the light is
  therefore bakeable, and baked light is both the cheapest and, for soft bounce in dark
  rooms, the best looking light there is. "Lots of high quality lights" is mostly a
  baking problem, not a runtime one, and the runtime budget goes to the few lights that
  actually change: the player's torch, a flicker, a puzzle that turns something on.

---

## ADR-0: The engine runs and renders in the sandbox, and this is the measurement

**Decision:** Godot 4.7.1 (mono) on the Forward+ renderer over Mesa's software
Vulkan driver (lavapipe) under Xvfb is the proven path, and `scripts/render-proof.sh`
is the check. It is the first thing to run in a fresh session and the last thing to
break.

**Measured on 2026-09-04, in this sandbox** (Ubuntu 24.04, no GPU, no display,
outbound HTTPS through the agent proxy):

| Step | Result |
|---|---|
| Download the editor from `downloads.godotengine.org` through the proxy | 105.9 MB, first try |
| `apt-get install mesa-vulkan-drivers vulkan-tools dotnet-sdk-8.0` | succeeded; lavapipe registered as `lvp_icd.json`, Vulkan 1.4.318, .NET SDK 8.0.130 |
| `godot --headless --import` on a C# project | succeeded |
| `dotnet build` of the C# script | 8.8 s, 0 warnings, 0 errors |
| `xvfb-run godot --rendering-driver vulkan --rendering-method forward_plus` | started: "Vulkan 1.4.318 - Forward+ - llvmpipe (LLVM 20.1.2)" |
| A 960x540 frame with 12 shadow casting spotlights, volumetric fog, SSAO, glow and AgX tone mapping | drawn and written to PNG, 680 ms per frame cold and 227 ms with the shader cache warm, in software |
| The frame itself | `reference/forward_plus_lavapipe_proof.png`: twelve lit cones in fog over shadowed pedestals, 9.1 percent of pixels above black |

![](reference/forward_plus_lavapipe_proof.png)

**What that establishes.** Every renderer feature ADR-3 relies on (clustered lights,
shadows, volumetric fog, the post stack) draws here, in the same code path a player's
GPU runs, only slowly. A few hundred milliseconds a frame is a screenshot every second, which is what
troubleshooting needs; it is not a frame rate, and nothing performance related is
measured on this machine (ADR-9 needs the Q3 reference GPU for that). `the-federation`
ran Godot here too, but on the Compatibility renderer over OpenGL, which has none of
the lighting features; the difference is one apt package and two flags, and the
script carries both.

**Why it decides ADR-1.** The Rust options would have to be proven the same way and
none has been: Bevy on wgpu can in principle target lavapipe, but a Bevy debug build in
this sandbox is minutes of compile before the first frame and there is no editor to
bake a lightmap in; a custom renderer would be proven only once written. Godot was
proven in twenty minutes with a script anybody can rerun. Requirement 0 is the
non-negotiable, so the engine that meets it today wins.

**The costs, so nobody rediscovers them:**

- The sandbox is ephemeral: the editor, lavapipe and the SDK are reinstalled per
  session, about two minutes. A session start hook can pay that once, and
  `scripts/install-sandbox-deps.sh` and `scripts/install-godot.sh` are idempotent so
  the hook is one line.
- Godot writes audio driver errors on a machine with no sound card. They are noise.
- The screenshot is taken from the viewport texture on frame twelve, after shaders
  compile; a frame taken earlier is black and reads as a broken renderer.
- Lightmap bakes in software will be slow. Q14 asks whether bakes are committed or
  made in CI, and this is the reason to commit them.

---

## ADR-1: Engine. Godot 4 (Forward+) with C#, and the alternatives recorded honestly

**Decision:** Build on **Godot 4.7.x, Forward+ renderer, C# (.NET)** for desktop, with
the game's rules in an engine free C# library (ADR-2). Do not build on Bevy, do not
build a custom Rust renderer, and do not use Godot's Rust bindings for the core, for
the reasons below. Any of the three is reopenable if the answers to the section 11
questions change the brief, and the ADR-2 split is what makes reopening cheap.

### What "lots of high quality lights" actually needs

Three renderer capabilities, in the order they matter for this game:

1. **A lightmapper with bounce**, so hundreds of static lights cost nothing per frame
   and dark rooms get the soft indirect light that makes them read as rooms rather than
   as black with spots in it.
2. **Clustered (or deferred) direct lighting**, so the dynamic lights that remain are
   not capped per object at a number a museum case blows through instantly.
3. **Volumetric fog that the lights participate in**, because the liminal look is
   light in air: a spot on a mask that is also a cone of haze.

After those: screen space reflections and reflection probes for glass, ambient
occlusion, a real tone mapper, and depth of field for the inspect camera.

### The survey

| Option | Lights | Editor | Language | Runs here (req 0) | Verdict |
|---|---|---|---|---|---|
| **Godot 4.7 Forward+, C#** | Clustered forward (lights, decals and probes are binned per cluster, default cap 512 elements per cluster, thousands in a scene); GPU lightmapper with bounce (`LightmapGI`); `VoxelGI` and `SDFGI` for dynamic GI; volumetric fog with per light contribution; SSR, SSAO, SSIL, glow, DOF, AgX tone mapping | Full scene editor, light placement, lightmap baking in editor | C#, with a real test runner outside the engine | **Proven, ADR-0** | **Chosen.** Everything in the list above exists today and is documented. Web export is not possible with C# (verified by `the-federation` against 4.7.1 and still true in 4.7), which is acceptable only if the answer to Q1 is "desktop". |
| Godot 4.7 Forward+, GDScript | Same renderer | Same editor | GDScript: hot reload, web export works, no test runner outside the engine | Same path as ADR-0, minus the SDK | The fallback if web matters. `the-federation` took it for exactly that reason. Costs: tests need a headless Godot boot, weaker typing, and a language the owner did not ask for. |
| Godot 4.7 + godot-rust (gdext 0.5) | Same renderer | Same editor | Rust core as a GDExtension | Same renderer path; the Rust toolchain is present here (rustc 1.94) | Viable and stable on desktop (0.5 supports the 4.6 API level and is preparing 4.7). Rejected for this game because a single player puzzle game has none of the problems Rust solves here: no determinism contract across machines, no lockstep, no hot loop. What it adds is a second language at every boundary. Keep in reserve for a tool that needs to be fast (a lightmap or scatter pre pass) rather than for the game. |
| **Bevy 0.19** (Rust) | Clustered forward PBR, volumetric fog, SSAO, SSR, contact shadows, lightmap SAMPLING (no baker: bake in Blender and export), and `bevy_solari`, real time ray traced direct light and GI, explicitly experimental and not for production | No shipped editor. Scenes are authored in code or in Blender via glTF exporters | Rust | Unproven. wgpu can target lavapipe in principle; a debug build here is minutes of compile per change | The "experimental Rust" option, and the most interesting renderer on the list because Solari is the only open source answer to Lumen. Rejected: no editor for a game that is all placed lights, no lightmapper, the owner's recorded dislike of Bevy compile times (`redux-tribes` ADR-1 addendum), and a breaking release every four to five months. Right choice for a rendering research project; wrong for shipping an authored museum. |
| Custom Rust renderer (wgpu, deferred or clustered) | Whatever is written | None | Rust | Proven only once written | "Many lights" is the one thing a deferred renderer does well, and it would still be twelve to twenty four months of engine before the first room. Rejected on the same grounds `redux-tribes` rejected it. |
| Fyrox 1.x (Rust) | Deferred renderer, many lights, lightmapper | Shipped editor (FyroxEd) | Rust | Unproven; OpenGL, so Mesa's llvmpipe would carry it | The one Rust engine with an editor and a deferred pipeline; genuinely a fit for the lighting brief. Rejected on bus factor: near solo maintenance on donations, thin ecosystem. |
| Unreal Engine 5 (Lumen, MegaLights) | The reference point: dynamic GI in dark rooms and hundreds of shadowed lights are exactly what Lumen and MegaLights were built for | Best in class | C++ and Blueprint | No. The toolchain does not install or run in this sandbox | Recorded so the comparison is honest. Not open source, a very large toolchain that does not suit headless CI or script driven authoring, and its material and mesh pipeline would sideline Material Maker and the Blender scripts the owner already has. If the lighting bar ever proves unreachable in Godot, this is the honest fallback, and the ADR-2 core would port. |

### Why Godot wins for this game specifically

- **It is the engine that runs here** (ADR-0), which is requirement 0 and ends the
  argument on its own. The rest is why it is also the right choice.
- **The editor is the level tool.** Rooms, cases and lights are placed and lit
  interactively, and the lightmap is baked in the same window. Every Rust option pays
  for this with either a Blender round trip per adjustment or no bake at all.
- **The lighting features are all present and shipped**, not experimental: the
  lightmapper, two dynamic GI methods, volumetric fog, clustered lights. The renderer is
  Vulkan (and D3D12 on Windows), which is the class of API the brief needs.
- **C# gives the core library a test runner that does not need the engine.** The
  federation's GDScript simulation has to boot a headless Godot to run its 91 checks;
  a C# class library runs `dotnet test` in a second and CI runs it without an export
  template. That is what makes ADR-2 cheap rather than aspirational.
- **The pipeline already exists in `the-federation`:** pinned Godot from a
  `build.config`, thin CI over scripts, itch.io deploy, a headless boot that proves the
  export runs. It transfers with the flavor flipped from `standard` to `mono`.

### Accepted costs

- **No web build.** Q1 has to say desktop. If it does not, the language is GDScript
  and everything else in this document stands.
- **C# has no hot reload in Godot 4;** a script change means the editor rebuilds the
  assembly. Tolerable because the tight loops (a puzzle's logic, a tuning value) live
  in the core library and its tests, not in the editor.
- **A .NET runtime ships in the build,** tens of megabytes. Irrelevant for a desktop
  download.
- **Vulkan on old hardware.** Forward+ needs a Vulkan 1.0 class GPU; the Compatibility
  renderer exists for everything older and has none of the lighting features. The
  quality ladder (ADR-3) decides how far down the game stands features down, and Q3
  decides the floor.

---

## ADR-2: The load bearing split. An engine free core, and Godot as the front end

**Decision:** The rules of the game never touch the engine.

```
src/
  Museum.Core/        C# class library, NO Godot reference. Puzzle graph and its
                      node types, the interaction contract, inventory, the
                      observed / unobserved rule, room and puzzle definitions loaded
                      from data/, the event log that is the save file, and a
                      seeded RNG for the one or two places chance is wanted.
  Museum.Core.Tests/  xunit. Runs with `dotnet test`, no editor, no export template.
  Museum.Godot/       The Godot project: scenes, materials, the camera rig, input,
                      audio, HUD, lightmaps. Mirrors core state; decides nothing.
data/                 Puzzle definitions, room manifests, tuning, light budgets. JSON.
assets/               Committed meshes, textures, audio, with their sources beside them.
tools/                Python: Blender exporters, Material Maker exports, scatter and
                      foliage generators, model doc regeneration, asset verification.
mockups/              One self contained HTML file per approved prototype.
scripts/              Build, test, style check, install pinned tools, deploy. CI runs
                      these; it holds no logic of its own.
```

**Why this matters here, since there is no multiplayer to force it:**

1. **Puzzles are testable as puzzles.** "Placing the censer in slot three after both
   candlesticks unlocks the lid" is a unit test on a state machine. Without the split it
   is a test that boots the engine, loads a scene, and drives a fake mouse.
2. **The interactive prototypes stay in step with the game** (CLAUDE.md 3). A puzzle
   prototyped in JavaScript is a graph of states and transitions; the core library is
   the same graph in C#, and the data file is what both read. The prototype is not
   thrown away, it becomes the specification the tests check.
3. **The engine stays a front end.** ADR-1 records three alternatives and one of them is
   Unreal. If the lighting bar forces a move, the puzzles, the rooms' definitions, the
   save format and the tools move unchanged.
4. **It is the rule the other two repos converged on** from opposite directions
   (`sim_core` in Rust, `src/sim/` in GDScript) and both record the bug it prevented:
   two implementations of one rule, drifting.

**The boundary rule:** if a second front end computed this differently, would the
player's game be different? If yes, it is core. Framing, easing, what a raycast hit,
how a hint is worded on screen: front end. Whether the hint is due, whether the lock
opened, what the room did while unobserved: core.

**Saves are the event log.** A game is its starting room plus every interaction since,
and resuming replays them through the core. Small, survives an asset change, and it is
the debugging tool: a bug report is a save file. Snapshots would be larger and
invalidated by every format change.

---

## ADR-3: Lighting. Bake what never changes, budget what does, fog over everything

**Decision:** Three tiers, and every light in the game is authored into exactly one.

| Tier | What | How | Cost per frame |
|---|---|---|---|
| **Baked** | The architecture, the cases, the hundreds of case and track lights, the emergency signs, everything that never changes state | `LightmapGI`, bake mode Static, with bounce. Baked in the editor, the lightmap committed as a build product with its bake settings in data | None beyond a texture fetch |
| **Dynamic, budgeted** | The player's torch, flickers, anything a puzzle switches, anything that moves | Real time lights, bake mode Dynamic. A written budget: at most 8 shadow casting and 32 unshadowed on screen, and a shadow atlas the budget is sized against | The whole runtime light budget |
| **Volumetric** | The haze every light sits in | Forward+ volumetric fog, per room density, per light fog energy. The player's torch gets the highest, because a cone in dust is the game's signature image | One pass, resolution scaled by the ladder |

**Rooms whose lighting changes as a puzzle are the interesting case,** and Q5 asks how
many there are. A lightmap holds one state. The options, in order of preference:

1. Make the lights that change Dynamic and keep everything else in the bake. Right
   when a puzzle turns on one or two lights.
2. Give that room `VoxelGI`, which is built for bounded interiors, keeps its geometry
   bake and reacts to dynamic lights in real time. Right when a puzzle relights a whole
   room.
3. `SDFGI` for very large connected halls. Last, because it leaks through thin walls
   and a museum is made of thin display walls.

One GI method per room, chosen by whether its lighting changes, written in the room's
manifest, checked by a test that reads the scene.

**Glass is the defining surface** and is the hardest one: every photograph in
`reference/` is taken through a case. Reflection probes per case, screen space
reflections on top, refraction in the material, and the sorting trap written down
before it bites: transparent objects sort per object, so a case inside a case, or a
label behind two panes, draws in the wrong order unless the panes are authored as
separate meshes with explicit render priority. The first prototype room is a case with
an artifact in it, seen from the outside and then from the inspect camera, precisely
because that shot is the game and it is where the renderer will fail first.

**The quality ladder**, in the spirit of `redux-tribes` ADR-13: the game measures its
own frame time and steps down a fixed ladder (volumetric fog resolution, shadow atlas
size, dynamic shadow count, SSR, then SSIL) rather than offering one setting. Slow to
fire, permanent for the session, and it says why. Q3 decides the floor the bottom rung
has to run on.

**Post:** AgX tone mapping (without one, a torch, a bulb and a lit wall all clip to the
same white and glow has nothing to threshold), glow, SSAO, SSIL where the ladder
allows, depth of field only in inspect mode, and a film grain and vignette that are
ours, dithered so dark gradients do not band. `redux-tribes` measured that a slow dark
gradient through an eight bit output bands into forty pixel contours; this game is
nothing but slow dark gradients.

---

## ADR-4: One camera rig, three modes, and one interaction contract

**Decision:** There is one camera and it has a mode. There is one way to be
interactable and one raycast that finds it.

**Modes:** `Walk` (first person, mouse look, no sliders, no camera buttons), `Inspect`
(the camera eases onto an authored anchor on the object; drag rotates the object or
orbits it, per the anchor's kind; hotspots on the object are the puzzle's controls;
Escape or a step back returns to Walk), `Cinematic` (authored, non interactive, for the
supernatural beats). The mode machine lives in core so a test can assert that a puzzle
cannot be interacted with from Walk and that Inspect cannot be entered on a non
inspectable. The Godot side owns the easing: a goal and a drawn value, eased with
`1 - exp(-k * dt)` so the transition takes the same wall time at any frame rate, and
distance eased in log space because zoom is multiplicative. Both numbers come from
`data/tuning.json` and the mockup reads the same file.

**Inspect anchors are authored on the object,** in Blender, as named empties exported
in the glTF: the camera position, the pivot, the allowed orbit range and which
hotspots are visible from it. The Room's trick is that every object has a "right"
distance and the camera always finds it; that is an authoring decision per object, not
a formula.

**The interaction contract** is one interface in core (`IInteractable`: what am I, can
I be used now, what happens if I am) and one resolver in the front end (a raycast from
the camera through the crosshair, returning the nearest interactable). The HUD prompt,
the inspect transition, and the puzzle hotspot all consume that one answer. The rule
from `redux-tribes` applies verbatim: a press on an object is about that object. It
never does something else because of what is behind it.

**Touch and gamepad** are a Q6 question. If either is in, the Inspect mode's drag is
the gesture that has to be designed for it first, since it is the mode the game spends
its time in.

---

## ADR-5: Puzzles are data on one evaluator, and the museum changes when unobserved

**Decision:** A puzzle is a **graph** in `data/puzzles/<id>.json`: nodes with typed
state, edges that are conditions, and a solved node. One evaluator in core walks every
puzzle. Puzzle KINDS are node types, added by adding a type, never by adding a branch:

| Kind | State | Solved when | Seeded by |
|---|---|---|---|
| Arrangement | N objects, M slots | each slot holds the right object | the altar set, the memorial figures |
| Sequence | ordered inputs | the last K inputs match the key | the debating stool, the trilobite ring |
| Alignment | rotations on one or more axes | every axis within tolerance | the masks, the eagle finial |
| Combination | K dials or numbered positions | the reading matches | the trilobite table, the emerald carats |
| Resonance | a sounding object with pitch and rate | the pitch matches the target | the whirling slats |
| Illumination | a light source, targets in its beam | every target lit at once | the emerald crystal, the skull's eye |
| Observation | a room with a hidden state | the player looks at the right thing from the right place | the diorama, the memorial house |

Each kind is a small class with a state, a `TryApply(input)` and an `IsSolved`. A
puzzle that needs a kind that does not exist gets a new kind, and a new kind gets a
test that solves it, fails it, and solves it after failing it.

**The observed / unobserved rule** is the supernatural mechanic, and it is ONE system.
A room registers what may change while the player is not looking at it (an object
moves a slot, a figure turns, a label rewrites, a corridor lengthens) and the system
decides when, from the player's view frustum and a seeded RNG, so a replayed save does
the same thing. Every "the museum is wrong" beat goes through it. Two rooms with their
own copy would drift on what "looking" means, and the player would learn two rules.

**Hints** are a tier on the same graph: a puzzle declares what it may reveal after how
long, and the hint system reads it. Not a bespoke timer per puzzle.

---

## ADR-6: The asset pipeline. Blender and Material Maker, driven headlessly, sources committed

**Decision:** Adopt `the-federation`'s pipeline shape and `redux-tribes`'s asset rules
wholesale, with one change: this game is PBR rather than pixel art, so there is no
palette gate. The gates that replace it are below.

**Models: Blender, headless, via Python.** Every artifact, case, and room piece is a
`.blend` with a committed `tools/export_*.py` that writes the `.glb`. The script also
writes the inspect anchors (ADR-4) from named empties, the collision shape from a
named collection, and a line in the model doc with extents measured from the file.
Deliverable formats per CLAUDE.md 5: `.glb` when there are materials, hierarchy or
animation; `.obj` for plain static geometry.

**Textures: Material Maker, headless under Xvfb**, `.ptex` beside every PNG set, power
of two dimensions, the full PBR set exported from one graph. `redux-tribes` could not
install it from its sandbox and hand rolled a stopgap; this repo's first tooling task
is to prove the headless export runs here, because every texture after that depends on
it.

**Foliage and scatter** (the plantation diorama, a potted plant in a corridor) come from
Blender's own tools (the bundled tree generator, geometry nodes for scatter) run by a
committed script, exported as static meshes plus a committed placement file that the
Godot side instances with `MultiMeshInstance3D`. Generated once, committed, per ADR-7.

**Gates a script enforces before an asset is written**, in `tools/assetlib.py` (one
implementation, every generator calls it):

- every texture dimension is a power of two;
- every mesh has a source file beside it and a script that regenerates it;
- every interactable mesh carries its inspect anchors;
- triangle winding agrees with normals (the federation lost an afternoon to a frigate
  that shaded black);
- triangle and texture memory per asset within the written budget (ADR-9).

**Audio** is a Q9 question; the rule is the same (a committed source beside the render)
whatever the tool.

---

## ADR-7: Procedural generation is a build step, and each use is listed here

**Decision:** Procedural tools run offline, by a committed script, output committed as
a static asset, and only where authoring is impractical. Never at runtime. Never for a
room's layout. Never for a puzzle. GUIDELINES 6 of `redux-tribes` says it for
encounters: "Scenarios are authored and committed as data. Procedural generation is
for backdrops and flavour, never for the encounter the player is asked to solve." A
puzzle room is the encounter.

Listed uses, with the reason authoring was impractical:

- None yet. The expected first entries are the diorama's few hundred coffee shrubs
  and the trees in the plantation backdrop.

Anything not listed is not an exception.

---

## ADR-8: Prototype first, on an interactive page, then build

**Decision:** CLAUDE.md 3 is the rule; this ADR records what the prototypes are FOR
and the order they come in, since the owner has said the design doc is reviewed first
and then systems are prototyped here.

The first prototypes, each an interactive page with the game's own numbers:

1. **The inspect transition.** Walk to a case, press, the camera eases onto the
   artifact, drag to turn it, step back. This decides the game's feel and it is the
   thing every other screen sits inside. Approved by dragging it.
2. **One puzzle of each kind** in ADR-5, on the graph the core will run, so approving
   the puzzle approves the data format.
3. **The observed / unobserved rule** as a top down toy: a room, a view cone, things
   that move when outside it. Approved by being fooled by it.
4. **The HUD**, which should be nearly nothing: a crosshair that changes on an
   interactable, and the museum's own labels as the text device.

Every approved page lives at `mockups/<slug>/index.html` and is kept in step with the
game per CLAUDE.md 3.

---

## ADR-9: Budgets, and measuring before blaming

**Decision:** Written budgets, checked by a script, quoted in commit messages as
measured numbers.

| Budget | Value | Measured by |
|---|---|---|
| Frame time at the ladder's top rung | 16.6 ms at 1080p on the Q3 reference GPU | the debug overlay, and a headless bench in CI where it can |
| Dynamic shadow casting lights on screen | 8 | a scene walker that counts them |
| Dynamic unshadowed lights on screen | 32 | same |
| Shadow atlas | 4096, sized against the shadow budget | project setting, read by the test |
| Triangles per artifact / per room | to be set after the first room is measured | `tools/assetlib.py` |
| Texture memory per room | same | same |
| Lightmap texel density | same, per room manifest | same |

The rules from `redux-tribes` carry over verbatim: measure before you blame; do
expensive work once per frame, not once per event; cache on a key that describes the
input; numbers in the commit message; and attribute growth to the change that caused
it, on the same toolchain either side of the commit.

---

## 10. Tests, and the suites that grow with the code

Every suite that exists must pass before a push (CLAUDE.md 9). Today:

```sh
./scripts/check-style.sh           # no em or en dashes, anywhere
./scripts/render-proof.sh          # the engine installs, compiles C#, and draws a lit
                                   # Forward+ frame here (ADR-0); about two minutes cold
```

As code lands, in this order:

```sh
dotnet test src/Museum.Core.Tests   # puzzles, interaction, observed rule, saves
./scripts/run-tests.sh              # headless Godot: scenes instantiate, panels keep
                                    # their size, every room manifest names one GI
                                    # method and its lights are in a tier
python3 tools/verify_assets.py      # every asset has a source, a script, and is
                                    # within budget
./scripts/build.sh && ./scripts/verify-build.sh   # the export boots headless
```

And the one that plays the game: a scripted walkthrough that starts a new game,
solves the first room through the real input path, and exits non zero if it cannot,
because no suite above can say the GAME is playable. `redux-tribes` shipped two
defects every unit suite was blind to and wrote that harness afterwards; this repo
writes it with the first room.

---

## 11. Questions for the owner, before Phase 0

Answers to these change the document. Numbered so they can be answered by number.

1. **Platform.** Desktop only (Windows, Linux, macOS as downloads on itch.io or
   Steam)? A web build cannot exist with C# on Godot 4, so "web matters" means
   GDScript and "desktop" means C#. **Recommended: desktop.** A first person game with
   this lighting bar is not a browser game anyway.
2. **Language, given 1.** C# (recommended, for the engine free test loop), GDScript
   (if web), or Rust via godot-rust (only if you want Rust for its own sake; ADR-1
   says it buys nothing here).
3. **Hardware floor.** What must the bottom rung of the ladder run on? Steam Deck and
   a GTX 1060 class desktop at 1080p is the sensible floor for Forward+. A Raspberry Pi
   5, which `redux-tribes` targets, would take away nearly every lighting feature this
   game is about, so it should not be the floor here.
4. **Scope.** How many halls, how many puzzles, and roughly how long a playthrough?
   One contiguous museum or a hub with wings that unlock? This sizes everything from
   the lightmap budget to the save format.
5. **Lighting that changes.** How many puzzles switch a room's light state (turn the
   case lights on, put the hall into emergency lighting)? One or two dynamic lights per
   room is free; relighting whole rooms decides between `VoxelGI` and a second bake.
6. **Input.** Mouse and keyboard only, or gamepad and touch too? Inspect mode's drag is
   designed around the answer.
7. **Player abilities.** A torch? An inventory that carries artifacts between rooms, or
   self contained puzzles like The Room? Can the player pick up and hold objects, or only
   inspect them in place?
8. **Threat.** Pure atmosphere, or is there something in the museum with the player?
   An entity means AI, a fail state, and a very different save design.
9. **Sound.** Is audio in scope for the first milestone, and with what tool? The rule
   (source beside render) holds whatever the answer, but the resonance puzzle kind
   needs a synthesis path.
10. **Story delivery.** The museum's own labels, mistranslated by the aliens, are the
    obvious device and cost no new UI. Audio logs, notes, or a narrator would each add
    a system.
11. **The reference museum and cultural material.** The photographs are of real
    displays, several of them of ancestral and memorial carvings from living
    cultures. The proposal is that everything in the game is an ORIGINAL
    reinterpretation, which the alien recreation premise makes natural (they are
    copies, and they are wrong), and that no real object, label text or donor is
    reproduced. Agreed? And may the reference museum be named in the docs?
12. **Licence.** `the-federation` is GPL-3.0 because of a vendored shader; this repo
    has nothing vendored yet. MIT, GPL, or all rights reserved? It decides what may be
    vendored later (a foliage tool, a shader).
13. **Where the prototypes live.** Published Claude artifacts, files under `mockups/`,
    or both (as `redux-tribes` does)? Both is the proposal, so a link exists to open and
    a file exists to diff.
14. **Lightmap bakes in CI or committed.** Bakes are minutes on a GPU and CI has none.
    The proposal is that bakes are committed build products with their settings in the
    room manifest, and a check fails if the settings changed and the bake did not.
15. **The game's name.** The repository is `the-museum`; is that the title?
16. **Session start.** Should the sandbox install (lavapipe, the SDK, the pinned
    editor: about two minutes) run automatically as a session start hook, so every
    session can render from its first turn, or on demand?

# The Museum

Project rules for Claude Code working in this repository. They are binding. When a rule
here conflicts with a general habit or with a suggestion in the design docs, this file
wins.

The architecture, the engine decision and the open questions live in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Read it before touching anything. The
photographs the puzzles are seeded from, and what each one suggests, are in
[docs/reference/README.md](docs/reference/README.md), and the invented world they become
is in [docs/WORLD.md](docs/WORLD.md).

These rules are adopted from `RubenTipparach/redux-tribes` (`GUIDELINES.md`, `CLAUDE.md`)
and `RubenTipparach/the-federation` (`CLAUDE.md`). Where those repos are stricter for
reasons that do not apply here (a wasm size budget, a lockstep hash, a pixel palette) the
rule stays there. What is kept is what holds regardless of game.

---

## 1. No em dashes or en dashes, anywhere

Straight ASCII hyphens only: in code, comments, docs, commit messages, PR bodies, in
game text and chat. U+2014 and U+2013 are banned by codepoint.
`scripts/check-style.sh` greps for them by codepoint, so this file stays clean ASCII
and does not report itself.

**This is a rule about how the repository is written, so it belongs to whoever is
writing: run the check before pushing.** It is deliberately not a CI job. A build that
goes red over a punctuation mark spends a runner and a cycle of somebody's attention on
something the author could have seen in a second, and it teaches people to read a red
build as noise.

| Instead of a dash | Use |
|---|---|
| introducing a definition | a colon |
| an aside | commas or parentheses |
| a break between two clauses | a period, and two sentences |
| a range | a plain hyphen, as in `10-25 minutes` |

## 2. Only this repository is ever modified

`the-museum` is the only thing to change. `redux-tribes` and `the-federation` are
REFERENCES, checked out to be read and copied from, never worked on, whatever turns up
while reading them. A pasted log or error from another project is not a request to go
and fix that project.

## 3. Major UI and gameplay changes are approved on an interactive prototype first

**Every new screen, camera behaviour, interaction model, puzzle mechanic or restructure
of an approved one is prototyped in JavaScript, as an interactive Claude artifact or a
self contained HTML page, and approved before any engine code is written.** This is the
owner's stated process: the design doc is reviewed first, then game systems are
prototyped here, then they are built.

- **One self contained HTML file per mockup**, at `mockups/<slug>/index.html`, and
  published as an artifact so it can be opened. No network: no CDN scripts, no remote
  fonts, no fetch. Vendor and inline everything.
- **Nothing binary is embedded, only text and images.** A prototype that carries a
  model, an archive or any other binary file inside it is a prototype the artifact
  share review refuses, so it cannot be sent to anyone: it fails with "the latest
  version embeds a file type that can't be reviewed for public sharing". Assets travel
  as text (`tools/glb_to_json.py` is how the exhibit shell does it) or as images, which
  are reviewable. The committed asset stays binary; the page gets a build product.
- **A prototype is interactive, not a picture.** A camera transition is approved by
  dragging it; a puzzle is approved by solving it. A description, a number or a
  static frame is not something anybody can judge feel from.
- **Take the numbers from the real project.** When the game holds a value (a field of
  view, a transition time, a light count) the mockup reads the same value, so it answers
  the question the game will actually ask.
- **Show every state that matters:** unsolved, partly solved, solved, wrong, and the
  supernatural variant where the room has changed behind the player.
- **Asking for approval means linking the thing to be approved.** Never ask "is this
  approved?" without the artifact link in the same message, and say what specifically is
  being decided.
- **The prototype and the game are one description, kept in step.** Change the game,
  update the page in the same commit. An approved prototype left unimplemented turns the
  set into a wish list nobody can tell from the spec.

Does not need a prototype: retitling a label, fixing a margin, recolouring a state, a
bug fix, a tuning change inside an approved range. Make the change and say what you
picked. When unsure, ask; asking is cheaper than the wrong screen.

## 4. Reuse, SOLID and clean code are not negotiable

### 4.1 Divergent paths for like functionality are a defect

If two places need the same behaviour, they call the same code. No copies, no near
copies, no "this one is slightly different so I forked it". When a second caller needs a
variation, parameterize the one implementation. Before writing anything new, search for
the thing that already does most of the job and extend it; if nothing fits, say so
before building. If you find duplication while working, say so and do not add a third
copy.

Each of these exists exactly once, and every caller goes through it (the list grows in
`docs/ARCHITECTURE.md` as systems are added):

- **Interaction.** One interactable contract and one raycast that resolves what the
  player is looking at. The HUD prompt, the inspect camera and the puzzle hotspots all
  read the same answer.
- **Camera.** One rig with modes (walk, inspect, cinematic). Not one camera per screen.
- **Puzzle evaluation.** One graph evaluator that every puzzle kind runs on. A puzzle is
  data plus a small typed node, never a bespoke script with its own win check.
- **Persistence.** One save format, which is the event log, and one writer.
- **The observed / unobserved rule.** One system decides what the museum may change
  while the player is not looking. Rooms register with it; they do not roll their own.
- **Asset loading.** One place spells every asset path.
- **The world.** One numeral table, one script, one lexicon, one bestiary. The labels,
  the glyph atlas and the puzzle evaluator all read them rather than holding a copy.

### 4.2 SOLID

Single responsibility (one class, one reason to change; split anything that has grown
two jobs). Open / closed (extend by adding a type or a data row, never by growing a
`switch` in the middle of existing logic). Liskov (a subtype is usable anywhere its base
is, with no special casing at the call site). Interface segregation (small, focused
interfaces; callers do not depend on methods they never use). Dependency inversion
(depend on interfaces, inject dependencies, so every system is testable in isolation).
Practical consequence: no globals shared between systems. Data flows through the object
that owns it.

### 4.3 The core simulates, the engine draws

Puzzle state, the interaction graph, inventory, the observed / unobserved rule, the
save format and every rule that decides an outcome live in an engine free class library
that runs and is tested without opening the editor. The Godot project draws it, plays
its sounds, collects input and tweens its cameras. Nothing in a scene decides what
happens. See `docs/ARCHITECTURE.md` ADR-2.

### 4.4 Data belongs in data files

Tuning values, puzzle definitions, room manifests, light budgets and anything a designer
will want to change live in committed, human readable, diffable files under `data/`,
never inline in gameplay code and never in inspector fields. Scenes are structure; code
is behaviour; data is what the code reads.

## 5. Every asset is a static file with an editable source

- **Static, not procedural at runtime.** Meshes, textures, audio and level geometry are
  files on disk, committed.
- **The editable source is committed beside the product:** the `.blend` beside the
  `.glb`, the `.ptex` beside the `.png`, the project file beside the render. A product
  with no source is the failure this rule exists to prevent.
- **Generated assets are generated by a committed script**, never by hand once, and the
  build product never drifts from its source: regenerate, do not patch.
- **Never overwrite art a person made.** Add a variant.
- **3D: Blender, headless, via Python**, to the practice in `docs/BLENDER.md`:
  booleans for every opening, UVs at world scale, materials named for roles, a gate
  that refuses what is wrong, a render as the proof. Deliverables are `.glb` (`.gltf`)
  for anything with materials or hierarchy and `.obj` for plain static geometry. The
  Godot import is a build product.
- **Textures: [Material Maker](https://www.materialmaker.org/)**, headless under Xvfb,
  exporting the full PBR set (albedo, normal, roughness, metallic, ambient occlusion,
  emission, height) from one graph. Every texture dimension is a power of two.
- **Materials are authored, not painted at runtime.** No two parts share a UV area on one
  texture unless they are meant to tile.
- **Model docs are regenerated whenever a model changes**, with extents measured out of
  the file rather than estimated.

## 6. The world is invented, and it is authored once

The museum holds our own civilizations, history, writing, numbers, animals and
ecosystem, eerily close to Earth's and not quite them. No real culture, object, label
text or donor is reproduced. `docs/WORLD.md` is the world; `docs/ARCHITECTURE.md` ADR-10
is how it is kept honest.

- **The world is data**, in `data/world/`: the numerals, the script, the lexicon, the
  bestiary, the cultures. One file per system, and every reader asks it.
- **Labels are generated from that data, never typed.** A hand written label is how the
  museum contradicts itself in a game about noticing contradictions.
- **The numerals are a mechanic, not a font.** The Combination puzzle kind reads the
  same table the labels are set from.
- **One count everywhere, one difference per thing.** Section 1 of `docs/WORLD.md` is
  the rule, and `tools/verify_world.py` fails the build when something breaks it.

## 7. Audio is made by the tool the sound calls for

Adopted from `RubenTipparach/tom-lander` (ADR-12) and subject to section 5 like every
other asset. **Two pipelines, one per kind, and never a third.** `docs/AUDIO.md` is the
whole of it: the two pipelines, the world's scale and motifs, the instrument set,
the method for making a new effect, the gate, and the post mortem of the two
versions that shipped wrong.

- **A score is instruments playing notes**, so it is a `.mid` rendered headless by
  fluidsynth against the General MIDI soundfont. It opens in LMMS, Ardour or MuseScore.
- **An effect is an object making a noise**, so it is a Csound `.csd` scored against
  `assets/audio/sfx/museum.orc` and rendered headless by csound: modal resonator banks
  for a struck body, friction inside a band for stone across stone. It opens in any text
  editor, and `csound door_open.csd` renders it.
- Both are mastered by **sox**, in one chain, and the source is committed beside the
  product in every case.

- **A sound is an object, not an instrument.** A wood block through a soundfont sounds
  like a wood block being PLAYED, which is not what a fingertip on a label sounds like.
  No noise beds: noise appears only where a real object makes it, band limited and under
  a tonal body.
- **Everything must survive a phone speaker**, so an effect carries a knock in the mids
  as well as its weight underneath, and a pitched effect is not written an octave below
  the phrase it belongs to.
- **A render must repeat.** The orchestra is seeded and sox is told not to dither, so
  `./scripts/render-audio.sh --check` can tell a changed sound from a re-rendered one.
- **`tools/check_audio.py` is the gate** and CI runs it: spectral flatness (how much
  like static it is), register, level, and every note against `data/world/music.json`.

## 8. Procedural generation is a build step, and it is the exception

Procedural tools are allowed **offline, at build time, by a committed script, with the
output committed as a static asset**, and only where authoring by hand is genuinely
impractical: scattering a few hundred coffee shrubs across a diorama, growing a tree, a
seamless texture. Never at runtime, never for level layout, and **never for a puzzle**:
puzzles and rooms are designed, in the tradition of Myst and Riven, and a generated room
is a room nobody designed. Each use is listed in `docs/ARCHITECTURE.md` ADR-7 with the
reason it could not be authored. Nothing may be treated as an exception until it is
listed there.

## 9. Scenes are structure, code is behaviour

- A `.tscn` defines what exists and how it is arranged. It does not define what things
  do. Scripts on nodes are thin: they wire the node to a system in the core library.
- Small, single purpose scenes that compose, usable and testable on their own.
- No node trees built in code as the normal way of constructing things. Instantiate and
  configure prebuilt scenes.
- UI panels are a fixed, authored size; content that does not fit scrolls, it never
  pushes. Menus name things, they do not explain them.

## 10. The engine runs here, and visual work is proven with a frame

**The engine must stay runnable in the Claude Code online sandbox, headless: install,
test, build and render.** This ranks above every other technical preference. It is
requirement 0 in `docs/ARCHITECTURE.md` and ADR-0 is the measurement behind it.

- `./scripts/render-proof.sh` is the check. Run it in a fresh session before making a
  visual claim, and after touching `build.config` or the renderer settings.
- **A visual change is proven by rendering it in the engine here** and attaching the
  frame, the way earlier projects did to troubleshoot and to prove work. "It should
  look right" is not a result; a PNG drawn by the real renderer is.
- Anything that breaks the headless path (a plugin that needs a GPU, a setting the
  software driver cannot run, a build step that needs a display) is a defect, whatever
  else it improves.
- Software rendering is slow (about 700 ms a frame). It proves what is drawn, never how
  fast. Performance numbers come from the reference hardware in ADR-9.

## 11. Budget everything, and measure before you blame

Frame time, light count, shadow atlas occupancy, draw calls and texture memory each have
a written budget (ADR-3, ADR-9) and the numbers in a commit message are measured, not
felt. "Faster" is not a result; 16 ms to 4 ms is. Keep a quality ladder rather than one
setting, and make the game stand a feature down when it measures itself over budget.

## 12. Tests before a push

The suites are listed in `docs/ARCHITECTURE.md` section 13 and grow with the code:
the style check and the render proof, which CI runs; the puzzle tests, the texture
drift check and the Blender build; and the playthrough, which plays the exhibit to its
end at phone size and is run by hand after touching the prototype. A web session can
verify that something renders, that inputs route and that numbers agree. It cannot verify that
something feels right: feel gets a human and a link.

## 13. No self scheduled check-ins

Do not schedule recurring check-ins, polling loops or re-arming reminders on a pull
request, a CI run or anything else here, unless the owner asks for one. Watching a pull
request is server side already; end the turn and let the events arrive. When a check-in
fires, do the work it names, report once, and stop.

## 14. After every push, hand over the links

A push is finished when the owner can look at it: the pull request link and, once a
deploy exists, the run for the pushed commit and the place the build can be played.

## 15. Documented exceptions

Exceptions to the rules above live here, with the reason. Nothing may be treated as an
exception until it is listed and agreed.

- **`tools/lightproof/Shoot.cs` builds its scene in code.** Section 9 forbids that
  for game scenes. This one file is not a game scene: it is the renderer proof behind
  ADR-0, it has to exist before any authored scene does, and it is retired the day the
  first authored room can be rendered by `scripts/render-proof.sh` instead. Agreed with
  the owner's requirement that the engine be runnable here (2026-09-04).
- **The shell's collision is made from its meshes at import.** Section 9 wants
  structure authored in scenes. The shell has 107 parts, and a collision body hand
  placed beside each would be a second description of the same wall. So
  `itch/src/import/shell_post_import.gd` runs when `assets/exhibit/elmorian.glb` is
  imported and gives every solid part a body shaped by its own mesh, naming the door
  slabs and plaques on those bodies. It is derived once, at import, from the authored
  model, never at runtime, and the props keep authored bodies. Agreed with the itch
  track (ADR-14, 2026-09-05).
- **`itch/scenes/exhibit.tscn` is written by a script.** Section 9 says scenes are
  structure and section 5 says a generated thing is generated by a committed script.
  This scene is both: `tools/gen_itch_scene.py` writes it from the `props` block of
  the layout, the way the shell is built from the layout, and
  `scripts/check-config.sh` fails when it has drifted. Edit the layout, not the
  scene. Agreed with the itch track (ADR-14, 2026-09-05).
- **`itch/data` and `itch/assets/*` are symbolic links.** Section 4.1 wants one copy
  of everything and a Godot project can only read inside its own folder; the links
  are how both hold. ADR-14 says what was rejected instead.
- **The plaque art is 1024 by 732.** Section 5 wants every texture dimension a power
  of two, for textures that tile. A plaque's picture is a decal on one face at the
  face's own aspect, rendered from the prototype's `art.js` by `tools/render_art.mjs`,
  and padding it to a square would put the label's paper off the plaque. Agreed with
  the itch track (ADR-14, 2026-09-05).

# The itch track

The Elmorian exhibit as a Godot 4.7 GDScript project, exported to the Web and
played at https://ruben-tipparach.itch.io/the-museum. This is one of the two
tracks docs/ARCHITECTURE.md ADR-14 describes; the desktop track (C#, Forward+)
is deferred and will sit beside it.

## What is where

```
itch/
  project.godot        GL Compatibility, 390 unit short side, importer defaults
  export_presets.cfg   the Web preset scripts/build.sh exports
  data -> ../data      the layout, the lore, the tuning, the material roles
  assets/              links to ../assets: the shell, the props, textures, art, audio
  scenes/main.tscn     the world: shell, props, lights, camera rig, audio, HUD
  scenes/exhibit.tscn  every prop, placed; WRITTEN by tools/gen_itch_scene.py
  scenes/hud.tscn      the HUD, fixed panels, the card's text scrolls
  src/sim/puzzles.gd   the four puzzles, no scene, no renderer
  src/*.gd             the rig, the raycast, the lights, the view, the HUD, the save
  src/import/          the post import script that gives the shell its collision
  tests/run_tests.gd   the puzzles solved headless (21 checks)
  tests/scene_test.gd  every room and station rendered under xvfb, frames to docs/reference
  tests/web_boot.mjs   the exported build booted in headless Chromium
  tests/playthrough.mjs the exported build played to its end through real taps
```

`data/` and `assets/` are symbolic links to the repository's own folders, so
this project reads the same layout, lore, textures and art the prototype and
the Blender build read, and nothing is copied. The `.import` sidecars Godot
writes beside them are committed: they are import settings, and a fresh
checkout imports every texture as Basis Universal and every sound as QOA
because they say so. On Windows, clone with symbolic links enabled
(`git clone -c core.symlinks=true`, with Developer Mode on) or the links
arrive as text files.

## Run it

```sh
./scripts/install-godot.sh standard   # the editor and the web templates, into .tools/
./scripts/run-tests.sh                # puzzles headless, then every room rendered
./scripts/build.sh                    # builds/web
./scripts/verify-build.sh             # boots it in headless Chromium
node itch/tests/playthrough.mjs       # plays it to the end, 390x844
node itch/tests/playthrough.mjs --touch      # the same through touch events
node itch/tests/playthrough.mjs --landscape  # 844x390
./scripts/deploy-itch.sh              # butler push, needs BUTLER_API_KEY
```

CI (`.github/workflows/deploy-itch.yml`) runs the same scripts and deploys on
main. The page's own configuration on itch.io is embed, 390 wide, with the
fullscreen button and mobile friendly on.

## Regenerate, do not edit

- `scenes/exhibit.tscn` comes from `data/layout/elmorian.json` through
  `tools/gen_itch_scene.py`. Move a prop in the layout and rerun it.
- `assets/props/*.glb` come from `tools/build_props.py` (Blender, headless).
- `assets/audio/sfx/*.wav` come from the `.csd` beside each, scored against
  `museum.orc` and rendered by csound; `assets/audio/music/*.ogg` comes from its
  `.mid` through fluidsynth. `./scripts/render-audio.sh` does both and gates the
  result (docs/AUDIO.md). Edit a `.csd` in any text editor, the `.mid` in LMMS or
  MuseScore, or the generator that writes them.
- `assets/art/*.png` come from the prototype's `art.js` through `tools/render_art.mjs`.

`scripts/check-config.sh` fails when the scene or the sound effects have
drifted from their sources.

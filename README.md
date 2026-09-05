# The Museum

A first person puzzle game about being locked inside an alien recreation of a human
museum. The halls are almost right. The artifacts are not. Puzzles in the tradition of
*Myst* and *Riven*, inspected the way *The Room* inspects an object, lit like a public
building after hours.

Two tracks (docs/ARCHITECTURE.md ADR-14). The itch track, built first, is Godot 4.7
GDScript exported to the Web and played in a browser or on a phone at
https://ruben-tipparach.itch.io/the-museum. The desktop track, Godot 4.7 Forward+ with
C#, keyboard and mouse and a gamepad, is deferred. The civilizations in it are our
own: their history, their writing, their way of counting, their animals.

| Doc | Contents |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Project rules. Binding. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Engine decision, the engine free core, lighting, camera, puzzles, pipeline, budgets, and the questions to answer before Phase 0 |
| [docs/WORLD.md](docs/WORLD.md) | The invented civilizations, numbers, writing, animals and ecosystem, in the manner of Riven. A proposal, awaiting approval |
| [docs/reference/README.md](docs/reference/README.md) | The photographs the puzzles are seeded from, what each suggests, and the invented hall it becomes |

## Status

Pre-production, with the first hall playable twice over. The architecture and the world
are approved; the Elmorian exhibit was approved as a point and click prototype in
three.js at `mockups/elmorian-exhibit/` that plays on a phone, and is now built in
Godot at `itch/` (see `itch/README.md`), its shell and props built in Blender from
`data/layout/elmorian.json` (docs/BLENDER.md), its sounds and its score from the
ADR-12 pipeline. Game systems are prototyped as interactive pages and approved
before they are built (CLAUDE.md section 3).

```sh
./scripts/check-style.sh                       # no em or en dashes
./scripts/render-proof.sh                      # the engine installs, compiles C#, and draws a lit frame here
./scripts/build-exhibit.sh elmorian            # Blender builds the exhibit shell from the layout, headless
python3 tools/build_mockup.py elmorian-exhibit # one self contained page from the sources
./scripts/run-tests.sh                         # the itch track: puzzles headless, every room rendered
./scripts/build.sh && ./scripts/verify-build.sh   # the Web export, booted in headless Chromium
node itch/tests/playthrough.mjs                # and played to its end at phone size
node mockups/elmorian-exhibit/playthrough.mjs  # plays it to the end at phone size
python3 tools/render_doc.py                    # regenerate docs/ARCHITECTURE.html from the Markdown
```

`docs/ARCHITECTURE.html` is the review copy of the architecture document and the world
bible, published as
an artifact at https://claude.ai/code/artifact/7b5d842a-a958-4a48-90a4-29934fa41da1. It
is a build product of the Markdown: regenerate it, never edit it.

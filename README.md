# The Museum

A first person puzzle game about being locked inside an alien recreation of a human
museum. The halls are almost right. The artifacts are not. Puzzles in the tradition of
*Myst* and *Riven*, inspected the way *The Room* inspects an object, lit like a public
building after hours.

| Doc | Contents |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Project rules. Binding. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Engine decision, the engine free core, lighting, camera, puzzles, pipeline, budgets, and the questions to answer before Phase 0 |
| [docs/reference/README.md](docs/reference/README.md) | The photographs the puzzles are seeded from, and what each suggests |

## Status

Pre-production. The architecture document is under review; no engine code exists yet.
Game systems are prototyped as interactive pages and approved before they are built
(CLAUDE.md section 3).

```sh
./scripts/check-style.sh     # no em or en dashes
./scripts/render-proof.sh    # the engine installs, compiles C#, and draws a lit frame here
python3 tools/render_doc.py  # regenerate docs/ARCHITECTURE.html from the Markdown
```

`docs/ARCHITECTURE.html` is the review copy of the architecture document, published as
an artifact at https://claude.ai/code/artifact/7b5d842a-a958-4a48-90a4-29934fa41da1. It
is a build product of the Markdown: regenerate it, never edit it.

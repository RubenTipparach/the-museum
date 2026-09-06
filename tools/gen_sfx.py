#!/usr/bin/env python3
"""The exhibit's sound effects: Csound sources, rendered headless.

Each effect is a .csd committed in assets/audio/sfx, holding a score against
the instrument set in museum.orc beside it. Open one and type
`csound door_open.csd` and you get the sound; change a number and it changes.
That is the editable source CLAUDE.md 5 asks for, and for foley it is a
better one than a .mid, because it describes the OBJECT rather than a note.

An effect is not an instrument. The version before this played General MIDI
through a soundfont, and a wood block sounded like a wood block being played
rather than a fingertip on a label; the version before THAT was filtered
noise and shipped as static. Both are recorded in docs/AUDIO.md section 5.

Pitched effects take their pitch from data/world/music.json, so the six
speech pads are the six notes of the lexicon and pressing a phrase plays it.

  python3 tools/gen_sfx.py            writes assets/audio/sfx/*.csd and *.wav
  python3 tools/gen_sfx.py --check    exits 1 if a committed wav has drifted
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_render as A   # noqa: E402

ROOT = A.ROOT
OUT = os.path.join(ROOT, "assets", "audio", "sfx")
WORLD = os.path.join(ROOT, "data", "world", "music.json")

STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def hz(name):
    """"bb4" to a frequency, A4 = 440."""
    letter, rest = name[0], name[1:]
    semi = STEP[letter]
    while rest and rest[0] in "b#":
        semi += -1 if rest[0] == "b" else 1
        rest = rest[1:]
    return 440.0 * 2 ** (((int(rest) + 1) * 12 + semi - 69) / 12.0)


def note(instr, start, dur, amp, freq=None, decay=None):
    row = 'i "%s" %-6s %-6s %-5s' % (instr, _n(start), _n(dur), _n(amp))
    if freq is not None:
        row += " %-8s" % _n(freq)
    if decay is not None:
        row += " %s" % _n(decay)
    return row.rstrip()


def _n(v):
    s = ("%.4f" % float(v)).rstrip("0").rstrip(".")
    return s or "0"


# ---- one entry per effect --------------------------------------------------------------
# Each is a score against museum.orc, plus how it is mastered: the peak it is
# authored to sit at, and how long its tail is faded. Levels are set HERE, so
# the game never balances a sound at runtime: a plaque tick is a small sound
# and a door is a big one because they are rendered that way.
def effects(world):
    words = world["words"]
    motifs = world["motifs"]
    out = {}

    def add(name, why, lines, end, peak=-2.0, tail=0.1, loop=None, trim=True):
        out[name] = {"why": why, "score": lines, "end": end, "peak": peak,
                     "tail": tail, "loop": loop, "trim": trim}

    add("ui_click", "A fingertip on a label: a nail across card over board.",
        [note("label", 0, 0.22, 0.8)], 0.4, peak=-12.0, tail=0.05)

    # the three discs are three sizes, so they are three pitches, the big day
    # eye lowest. A notch is grit and then a knock.
    for i, (f, why) in enumerate(((300.0, "The day eye, the largest disc and the lowest."),
                                  (372.0, "The far eye, the middle disc."),
                                  (455.0, "The small eye, which sees what stands behind."))):
        add("eye_tick_%d" % i, "A stone disc turning one notch of six. " + why,
            [note("label", 0, 0.05, 0.35),
             note("stone", 0.012, 0.7, 0.9, f, 0.16)], 0.8, peak=-5.0)

    add("thud", "A refusal: something heavy that does not move, and the knock on top of it.",
        [note("stone", 0, 0.9, 0.30, 92.0, 0.3),
         note("stone", 0, 0.55, 1.0, 330.0, 0.12),
         note("stone", 0, 0.35, 0.55, 690.0, 0.06),
         note("label", 0, 0.07, 0.7)], 1.0, peak=-2.0, tail=0.15)

    add("lift", "A ring lifted off its peg: stone leaving stone.",
        [note("stone", 0, 0.5, 0.7, 260.0, 0.1),
         note("label", 0.005, 0.09, 0.45)], 0.6, peak=-6.0)

    add("drop", "A ring set down on stone, and its one small bounce.",
        [note("stone", 0, 0.6, 1.0, 247.0, 0.22),
         note("stone", 0.085, 0.4, 0.34, 247.0, 0.12),
         note("label", 0, 0.05, 0.28)], 0.8, peak=-3.0)

    # the six speech pads: a stone cut to sing, at the six notes of the lexicon
    for i in range(6):
        w = words[str(i)]
        add("pad_%d" % i, "The %s pad: a stone cut to sing at %s." % (w["word"], w["note"].upper()),
            [note("singing", 0, 2.2, 0.9, hz(w["note"]), 1.5)], 2.4, peak=-4.0, tail=0.3)

    add("chime", "A phrase understood: the greeting's first three notes, on bronze.",
        [note("bronze", k * 0.26, 2.0, 0.75, hz(n), 1.6)
         for k, n in enumerate(motifs["the_greeting"]["notes"][:3])], 2.8, peak=-4.0, tail=0.4)

    add("door_chime", "A door deciding to open: the house theme's own first four notes.",
        [note("bronze", k * 0.32, 2.6, 0.8, hz(n), 2.2)
         for k, n in enumerate(motifs["hall_six"]["notes"][:4])], 3.6, peak=-3.0, tail=0.5)

    add("door_open", "A stone slab going down into the floor: it catches, it slips, it seats.",
        [note("slab", 0, 2.3, 0.95), note("seat", 2.18, 1.4, 0.9)], 3.6, peak=-1.5, tail=0.4)

    add("step", "A shoe on museum carpet: almost nothing, and what there is, is low.",
        [note("carpet", 0, 0.4, 0.8)], 0.5, peak=-12.0, tail=0.08)

    add("room_tone", "The hall at night: the air plant, and the room answering it.",
        [note("air", 0, 14.0, 0.9)], 14.0, peak=-16.0, tail=0.0, loop=1.5, trim=False)
    return out


def csd(name, spec):
    return "\n".join([
        "; %s" % spec["why"],
        "; Written by tools/gen_sfx.py from data/world/music.json. The bodies",
        "; are museum.orc beside this file; render it with `csound %s.csd`." % name,
        "<CsoundSynthesizer>",
        "<CsOptions>",
        "-o %s.wav -W -f -d -m0" % name,
        "</CsOptions>",
        "<CsInstruments>",
        '#include "museum.orc"',
        "</CsInstruments>",
        "<CsScore>",
        "; instr    start  dur    amp   pitch    decay",
    ] + spec["score"] + [
        "e %s" % _n(spec["end"]),
        "</CsScore>",
        "</CsoundSynthesizer>",
        "",
    ])


def build():
    world = json.load(open(WORLD))
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for name, spec in effects(world).items():
        path = os.path.join(OUT, name + ".csd")
        with open(path, "w") as f:
            f.write(csd(name, spec))
        raw = A.render_csound(path)
        try:
            a = A.master(raw, peak_db=spec["peak"], tail=spec["tail"], trim=spec["trim"])
        finally:
            os.remove(raw)
        if spec["loop"]:
            a = A.loop_seam(a, spec["loop"])
        made[name] = a
    return made


def main(argv):
    missing = A.have_tools()
    if missing:
        print("cannot render: missing %s. Run ./scripts/install-audio-tools.sh" % ", ".join(missing))
        return 1
    made = build()
    bad = 0
    for name in sorted(made):
        path = os.path.join(OUT, name + ".wav")
        if "--check" in argv:
            before = open(path, "rb").read() if os.path.exists(path) else None
            A.write(path + ".tmp", made[name])
            after = open(path + ".tmp", "rb").read()
            os.remove(path + ".tmp")
            if before != after:
                print("DRIFT " + path)
                bad += 1
            else:
                print("ok    " + path)
        else:
            A.write(path, made[name])
            print("wrote %-34s %5.2f s" % (os.path.relpath(path, ROOT), len(made[name]) / A.SR))
    if "--check" in argv:
        print("all %d effects match their sources" % len(made) if not bad else "%d files drift" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

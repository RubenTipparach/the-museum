#!/usr/bin/env python3
"""The exhibit's sound effects: MIDI sources, rendered by fluidsynth.

Every effect is written as a .mid (tools/midi.py), played by a real
instrument out of the General MIDI soundfont, and mastered by
tools/audio_render.py. The .mid beside each .wav is the editable source
CLAUDE.md 5 asks for: open it in LMMS, Ardour or MuseScore and change the
notes. Nothing here computes a waveform.

The instruments are chosen as OBJECTS rather than as music: a museum is
struck wood, stone and bronze, a taiko for anything heavy, and the six
speech pads are tubular bells cut to the six notes of the lexicon
(data/world/music.json), so pressing a phrase plays it.

  python3 tools/gen_sfx.py            writes assets/audio/sfx/*.mid and *.wav
  python3 tools/gen_sfx.py --check    exits 1 if a committed wav has drifted
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_render as A   # noqa: E402
import midi                # noqa: E402

ROOT = A.ROOT
OUT = os.path.join(ROOT, "assets", "audio", "sfx")
WORLD = os.path.join(ROOT, "data", "world", "music.json")

# General MIDI programs, named for the object rather than the instrument.
WOODBLOCK, MARIMBA, BELLS, KALIMBA, TAIKO, TIMPANI, PAD_BOWED, PAD_WARM = 115, 12, 14, 108, 116, 47, 92, 89

STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def key(name):
    """"bb4" to a MIDI key number."""
    letter, rest = name[0], name[1:]
    semi = STEP[letter]
    while rest and rest[0] in "b#":
        semi += -1 if rest[0] == "b" else 1
        rest = rest[1:]
    return (int(rest) + 1) * 12 + semi


# ---- one entry per effect ---------------------------------------------------------------
# score(track_factory) writes the notes; the rest is how it is heard.
def effects(world):
    words = world["words"]
    motifs = world["motifs"]
    out = {}

    def add(name, tracks, bpm=60, room=0.7, level=0.5, gain=0.6, peak=0.7, fade_tail=0.12, loop=None):
        out[name] = {"tracks": tracks, "bpm": bpm, "room": room, "level": level,
                     "gain": gain, "peak": peak, "tail": fade_tail, "loop": loop}

    def track(name, program, channel=0):
        return midi.Track(name, program, channel)

    # a fingertip on a label: one wood block, quiet and dry
    t = track("tick", WOODBLOCK)
    t.note(0, key("a6"), 0.1, 52)
    add("ui_click", [t], room=0.35, level=0.25, peak=0.30, fade_tail=0.05)

    # a stone disc turning one notch of six. Three discs, three sizes, so
    # three pitches: the big day eye lowest.
    for i, note in enumerate(("d4", "g4", "c5")):
        t = track("notch", WOODBLOCK)
        t.note(0, key(note), 0.15, 70)
        m = track("body", MARIMBA)
        m.note(0, key(note) - 12, 0.5, 42)
        add("eye_tick_%d" % i, [t, m], room=0.6, level=0.45, peak=0.55, fade_tail=0.1)

    # a refusal: something heavy that does not move. The weight is a taiko
    # low down and the KNOCK is a block on top of it, because 73 Hz alone is
    # a sound a phone speaker cannot make at all.
    t = track("thud", TAIKO)
    t.note(0, key("d3"), 0.6, 88)
    t.note(0, key("d2"), 0.7, 70)
    k = track("knock", WOODBLOCK)
    k.note(0, key("d4"), 0.2, 64)
    add("thud", [t, k], room=0.55, level=0.4, peak=0.72, fade_tail=0.15)

    # a ring lifted off its peg, and set down again
    t = track("lift", MARIMBA)
    t.note(0, key("g4"), 0.3, 58)
    t.note(0.12, key("d5"), 0.3, 44)
    add("lift", [t], room=0.6, level=0.45, peak=0.5)
    t = track("drop", MARIMBA)
    t.note(0, key("d4"), 0.5, 74)
    b = track("weight", TAIKO)
    b.note(0, key("d3"), 0.4, 46)
    add("drop", [t, b], room=0.6, level=0.45, peak=0.68)

    # the six speech pads: tubular bells cut to the six notes of the lexicon,
    # so the greeting and the farewell are melodies rather than beeps
    for i in range(6):
        t = track("pad", BELLS)
        t.note(0, key(words[str(i)]["note"]), 1.6, 76)
        add("pad_%d" % i, [t], room=0.85, level=0.6, peak=0.62, fade_tail=0.25)

    # a phrase understood, and a door deciding to open: the greeting's own
    # notes, then the house theme's, on bronze
    t = track("chime", BELLS)
    for k, n in enumerate(motifs["the_greeting"]["notes"][:3]):
        t.note(k * 0.28, key(n), 1.5, 70)
    add("chime", [t], room=0.9, level=0.65, peak=0.58, fade_tail=0.3)
    t = track("door", BELLS)
    for k, n in enumerate(motifs["hall_six"]["notes"][:4]):
        t.note(k * 0.34, key(n), 1.8, 74)
    u = track("under", PAD_BOWED)
    u.note(0, key("d3"), 2.4, 40)
    add("door_chime", [t, u], room=0.92, level=0.7, peak=0.62, fade_tail=0.4)

    # a stone slab going down into the floor: a timpani roll for the grind,
    # the hall answering it, and the seat at the end
    t = track("grind", TIMPANI)
    g = track("stone", WOODBLOCK)
    beat = 0.0
    while beat < 2.2:
        t.note(beat, key("d3") + (0 if int(beat * 8) % 2 else 2), 0.14, 38 + int(24 * min(1.0, beat / 1.4)))
        # the stone itself, catching and slipping across the floor: the part
        # that is actually audible on a phone
        g.note(beat + 0.05, key("g4") + (int(beat * 13) % 5), 0.1, 30 + int(18 * min(1.0, beat / 1.6)))
        beat += 0.11
    s = track("seat", TAIKO)
    s.note(2.35, key("d3"), 0.7, 100)
    s.note(2.35, key("d2"), 0.8, 78)
    r = track("room", PAD_WARM)
    r.note(0, key("d3"), 2.9, 30)
    add("door_open", [t, g, s, r], bpm=60, room=0.95, level=0.6, peak=0.82, fade_tail=0.5)

    # a shoe on museum carpet: almost nothing
    t = track("step", TAIKO)
    t.note(0, key("g3"), 0.25, 34)
    t.note(0, key("g2"), 0.3, 26)
    add("step", [t], room=0.5, level=0.35, peak=0.3, fade_tail=0.08)

    # the hall at night: an open fifth on a bowed pad, far away, and one bell
    # struck once so the loop has something to breathe around
    t = track("air", PAD_BOWED)
    for k, n in enumerate(("d2", "a2", "d3")):
        t.note(0, key(n), 24, 28 - k * 4)
    b = track("far", BELLS)
    b.note(9.0, key("d4"), 6, 22)
    add("room_tone", [t, b], bpm=60, room=0.98, level=0.85, gain=0.5, peak=0.24,
        fade_tail=0.0, loop=1.6)
    return out


def build():
    world = json.load(open(WORLD))
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for name, spec in effects(world).items():
        mid = os.path.join(OUT, name + ".mid")
        midi.write(mid, spec["tracks"], bpm=spec["bpm"])
        a = A.render(mid, room=spec["room"], level=spec["level"], gain=spec["gain"])
        a = A.dc_block(A.trim(a))
        if spec["loop"]:
            a = A.loop_seam(a, spec["loop"])
            a = A.peak_to(a, spec["peak"])
        else:
            a = A.peak_to(A.fade(a, 0.005, spec["tail"]), spec["peak"])
        made[name] = a
    return made


def main(argv):
    check = "--check" in argv
    missing = A.have_tools()
    if missing:
        print("cannot render: missing %s. Run ./scripts/install-audio-tools.sh" % ", ".join(missing))
        return 1
    made = build()
    bad = 0
    for name in sorted(made):
        path = os.path.join(OUT, name + ".wav")
        if check:
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
            print("wrote %-28s %5.2f s" % (os.path.relpath(path, ROOT), len(made[name]) / A.SR))
    if check:
        print("all %d effects match their sources" % len(made) if not bad else "%d files drift" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

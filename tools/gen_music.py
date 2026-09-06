#!/usr/bin/env python3
""""Hall Six": the exhibit's score, composed from the world's own motifs.

The arrangement is written as a multitrack .mid (the editable source: open it
in LMMS, Ardour or MuseScore), rendered by fluidsynth against the General
MIDI soundfont, and encoded to ogg. docs/AUDIO.md is the reasoning; the
motifs, the scale and the six word pitches are data/world/music.json and
nothing here invents a note that is not in them.

The shape, in the manner of Riven rather than in imitation of it: a slow
modal piece with more silence than sound, one theme stated plainly and then
answered in other registers, and a close that refuses to resolve. Every bar
is six beats long because the Elmorians count in sixes.

  python3 tools/gen_music.py           writes the .mid, the .ogg and a .wav
  python3 tools/gen_music.py --check   exits 1 if the committed ogg drifted
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_render as A   # noqa: E402
import midi                # noqa: E402

ROOT = A.ROOT
OUT = os.path.join(ROOT, "assets", "audio", "music")
WORLD = os.path.join(ROOT, "data", "world", "music.json")

BPM = 48
BAR = 6.0                    # beats, because they count in sixes
BELLS, PAD_BOWED, PAD_WARM, KALIMBA, CHOIR, TIMPANI = 14, 92, 89, 108, 52, 47

STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def key(name, octave_shift=0):
    letter, rest = name[0], name[1:]
    semi = STEP[letter]
    while rest and rest[0] in "b#":
        semi += -1 if rest[0] == "b" else 1
        rest = rest[1:]
    return (int(rest) + 1) * 12 + semi + 12 * octave_shift


def compose(world):
    m = {k: v["notes"] for k, v in world["motifs"].items() if k != "_"}
    bells = midi.Track("bells", BELLS, 0)
    drone = midi.Track("drone", PAD_BOWED, 1)
    pad = midi.Track("pad", PAD_WARM, 2)
    kalimba = midi.Track("kalimba", KALIMBA, 3)
    choir = midi.Track("choir", CHOIR, 4)
    drum = midi.Track("drum", TIMPANI, 5)

    def bar(n):
        return n * BAR

    # ---- the drone: an open fifth on the root, under everything, breathing
    # in eight bar spans so it never restates on a bar line. It sits at D3
    # rather than D2 on purpose: below 80 Hz a phone makes no sound at all,
    # so a drone down there is budget spent where nobody can hear it, and
    # the first cut of this piece put 41 percent of its energy exactly
    # there (docs/AUDIO.md).
    for start, length, notes, vel in (
        (0, 8, ("d3", "a3"), 34), (8, 8, ("d3", "a3", "d4"), 32),
        (16, 8, ("d3", "bb3"), 30), (24, 6, ("d3", "a3"), 26),
    ):
        for k, n in enumerate(notes):
            drone.note(bar(start), key(n), bar(length) - 0.4, vel - k * 4)

    # ---- the far drum: three strikes in the whole piece, and the last is
    # the quietest, because something is walking away
    for b, vel in ((3, 44), (13, 38), (25, 26)):
        drum.note(bar(b) + 2, key("d3"), 2.0, vel)

    # ---- bars 4 to 8: the house theme, stated once, plainly, and then left
    # alone. Six notes, one to a beat with a rest between each pair, so the
    # hall has time to answer it.
    for k, n in enumerate(m["hall_six"]):
        bells.note(bar(4) + k * 1.5, key(n), 3.0, 72 - k * 3)

    # ---- bars 9 to 13: the gaze, three voices at three registers, near,
    # far and behind, each entering a bar after the last
    for voice, (shift, vel, delay) in enumerate(((0, 60, 0.0), (1, 48, 1.0), (-1, 40, 2.0))):
        for k, n in enumerate(m["the_gaze"]):
            kalimba.note(bar(9) + delay * BAR / 3 + k * 1.0, key(n, shift), 1.4, vel - k * 4)

    # ---- bars 13 to 18: the greeting, and the farewell answering it. The
    # two phrases the speech room is made of; they begin differently and end
    # in different places, which is the whole point of them.
    for k, n in enumerate(m["the_greeting"]):
        bells.note(bar(13) + k * 1.5, key(n), 3.0, 66)
    for k, n in enumerate(m["the_farewell"]):
        choir.note(bar(16) + k * 1.5, key(n), 2.6, 52)

    # ---- bars 19 to 24: going to stone. The descent, and the sixth degree
    # returning at the end to be held rather than resolved: the piece stops
    # on the one semitone in the scale and never comes home.
    for k, n in enumerate(m["going_to_stone"][:-1]):
        choir.note(bar(19) + k * 1.5, key(n), 2.8, 50 - k * 2)
        if k % 2 == 0:
            bells.note(bar(19) + k * 1.5, key(n), 3.5, 42)
    held = m["going_to_stone"][-1]
    choir.note(bar(23), key(held), BAR * 2.0, 44)
    bells.note(bar(23), key(held), BAR * 1.6, 46)

    # ---- the pads: three slow chords out of the six notes, changing only
    # where the melody has already moved, so nothing is ever announced
    for start, notes in ((0, ("d3", "f3", "a3")), (9, ("bb3", "d4", "f4")),
                         (16, ("g3", "bb3", "d4")), (23, ("d3", "f3", "a3"))):
        for k, n in enumerate(notes):
            pad.note(bar(start) + 0.5, key(n), bar(7) if start < 23 else bar(6), 26 - k * 3)

    # ---- and the last bell, on the root, alone, after everything else has
    # gone: the only note in the piece that is allowed to be simple
    bells.note(bar(27), key("d4"), BAR, 40)
    return [drone, pad, bells, kalimba, choir, drum]


def build():
    world = json.load(open(WORLD))
    os.makedirs(OUT, exist_ok=True)
    mid = os.path.join(OUT, "hall_six.mid")
    midi.write(mid, compose(world), bpm=BPM)
    raw = A.render_midi(mid, room=0.95, level=0.72, gain=0.7)
    try:
        # The score keeps its own long fades rather than the effects' short
        # ones: it opens out of silence and it loops.
        a = A.master(raw, peak_db=-1.7, tail=2.5, trim=True)
    finally:
        os.remove(raw)
    return mid, a


def main(argv):
    missing = A.have_tools()
    if missing:
        print("cannot render: missing %s. Run ./scripts/install-audio-tools.sh" % ", ".join(missing))
        return 1
    mid, a = build()
    wav = os.path.join(OUT, "hall_six.wav")
    ogg = os.path.join(OUT, "hall_six.ogg")
    A.write(wav, a)
    if "--check" in argv:
        before = os.path.exists(ogg) and open(ogg, "rb").read()
        A.encode_ogg(wav, ogg + ".tmp")
        after = open(ogg + ".tmp", "rb").read()
        os.remove(ogg + ".tmp")
        os.remove(wav)
        if before != after:
            print("DRIFT " + ogg)
            return 1
        print("ok    " + ogg)
        return 0
    A.encode_ogg(wav, ogg)
    os.remove(wav)
    print("wrote %s (%.1f s) and %s (%.2f MB)" % (
        os.path.relpath(mid, ROOT), len(a) / A.SR, os.path.relpath(ogg, ROOT), os.path.getsize(ogg) / 1048576))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

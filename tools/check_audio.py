#!/usr/bin/env python3
"""Refuse audio that is noise, inaudible, or out of the world's scale.

The defect this exists for shipped: every effect was built from filtered
white noise and the score sat under 320 Hz, and the whole thing reached the
owner as static under a rumble. Nothing measured it, so nothing caught it.

Three measurements, all pure stdlib so this runs wherever the build does:

  flatness  the spectral flatness measure, the geometric mean of the power
            spectrum over its arithmetic mean. White noise is 1, a struck
            body is near 0. This is literally "how much like static is it".
  balance   the share of energy a phone speaker can reproduce (above 200 Hz)
            and the share wasted below 80 Hz, where no phone and few laptops
            make any sound at all.
  level     peak and RMS, so a sound is neither inaudible nor shouting.

And for a score, every note is checked against data/world/music.json: a
pitch outside the six is a pitch the Elmorians do not have.

  python3 tools/check_audio.py            everything in assets/audio
  python3 tools/check_audio.py <file>...  named files
"""
import cmath
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORLD = os.path.join(ROOT, "data", "world", "music.json")

# Per sound: the most static it may be, the least of it that may be audible
# on a phone, and the peak window. A slab grinding across a floor is allowed
# to be noisier than a struck stone, because friction IS noise; a room tone
# is allowed to be quiet, and required to be.
#            flatness  min share    peak range
#              max     above 200Hz
# A sound a phone cannot reproduce is a sound nobody hears, so even the
# heavy ones must carry a knock in the mids: the share above 200 Hz is the
# check for that, and it is what caught a thud sitting entirely at 73 Hz.
LIMITS = {
    "door_open": (0.35, 0.20, (0.5, 0.95)),   # friction IS noise, within reason
    "step":      (0.20, 0.15, (0.15, 0.5)),   # deliberately small
    "room_tone": (0.14, 0.30, (0.1, 0.35)),   # a bed: quiet, and never static
    "thud":      (0.14, 0.20, (0.4, 0.95)),
    "_default":  (0.12, 0.35, (0.2, 0.95)),
}
MUSIC = {"flatness": 0.10, "above200": 0.45, "melody": 0.12, "sub80": 0.20}


# ---- a radix 2 FFT, so this needs nothing installed --------------------------------
def fft(a):
    n = len(a)
    if n == 1:
        return a
    ev, od = fft(a[0::2]), fft(a[1::2])
    out = [0j] * n
    for k in range(n // 2):
        t = cmath.exp(-2j * math.pi * k / n) * od[k]
        out[k] = ev[k] + t
        out[k + n // 2] = ev[k] - t
    return out


def read_wav(path):
    with wave.open(path, "rb") as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    import struct
    a = list(struct.unpack("<%dh" % (len(raw) // 2), raw))
    if ch == 2:
        a = [(a[i] + a[i + 1]) / 2.0 for i in range(0, len(a), 2)]
    return [s / 32768.0 for s in a], sr


def read_any(path):
    """A wav directly; an ogg through oggdec, which is what the render step
    already needs."""
    if path.endswith(".wav"):
        return read_wav(path)
    tmp = tempfile.mktemp(suffix=".wav")
    subprocess.run(["oggdec", "-Q", "-o", tmp, path], check=True)
    try:
        return read_wav(tmp)
    finally:
        os.path.exists(tmp) and os.remove(tmp)


def spectra(a, sr, frame=2048):
    """Power spectra of the loudest frames, so silence and tails do not
    dominate the answer."""
    hop = frame // 2
    win = [0.5 - 0.5 * math.cos(2 * math.pi * i / frame) for i in range(frame)]
    frames = []
    for start in range(0, max(1, len(a) - frame), hop):
        seg = a[start:start + frame]
        if len(seg) < frame:
            break
        e = sum(s * s for s in seg)
        if e <= 1e-12:
            continue
        frames.append((e, [abs(v) ** 2 for v in fft([complex(s * w) for s, w in zip(seg, win)])[:frame // 2]]))
    if not frames:
        return [], 0.0
    frames.sort(key=lambda f: -f[0])
    keep = frames[:max(1, len(frames) // 2)]
    return [f[1] for f in keep], sr / frame


def flatness(S):
    """Geometric mean over arithmetic mean, per frame, then the median."""
    out = []
    for s in S:
        band = [v for v in s[2:] if v > 0]
        if len(band) < 16:
            continue
        lg = sum(math.log(v) for v in band) / len(band)
        out.append(math.exp(lg) / (sum(band) / len(band)))
    out.sort()
    return out[len(out) // 2] if out else 0.0


def shares(S, df):
    """What fraction of the energy sits above 200 Hz, below 80, and in the
    melody band."""
    tot = above = sub = mel = 0.0
    for s in S:
        for k, v in enumerate(s):
            f = k * df
            tot += v
            if f >= 200:
                above += v
            if f < 80:
                sub += v
            if 250 <= f <= 950:
                mel += v
    tot = tot or 1.0
    return above / tot, sub / tot, mel / tot


def measure(path):
    a, sr = read_any(path)
    S, df = spectra(a, sr)
    peak = max(abs(s) for s in a) if a else 0.0
    rms = math.sqrt(sum(s * s for s in a) / len(a)) if a else 0.0
    above, sub, mel = shares(S, df)
    return {"seconds": len(a) / sr, "peak": peak, "rms": rms, "flat": flatness(S),
            "above200": above, "sub80": sub, "melody": mel}


# ---- the world's own notes -------------------------------------------------------------
STEP = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def pitch_class(name):
    letter, rest = name[0], name[1:]
    semi = STEP[letter]
    while rest and rest[0] in "b#":
        semi += -1 if rest[0] == "b" else 1
        rest = rest[1:]
    return semi % 12


def check_scale(path, world):
    """Every note named in a .strudel source must be in the six."""
    allowed = {(pitch_class(world["scale"]["root"]) + s) % 12 for s in world["scale"]["semitones"]}
    text = open(path).read()
    text = "\n".join(l for l in text.splitlines() if not l.strip().startswith("//"))
    bad = set()
    for note in re.findall(r'\b([a-g](?:[b#])?[0-8])\b', text):
        if pitch_class(note) not in allowed:
            bad.add(note)
    return sorted(bad)


def main(argv):
    world = json.load(open(WORLD))
    targets = [a for a in argv if not a.startswith("-")]
    if not targets:
        base = os.path.join(ROOT, "assets", "audio")
        targets = sorted(os.path.join(base, "sfx", f) for f in os.listdir(os.path.join(base, "sfx")) if f.endswith(".wav"))
        targets += sorted(os.path.join(base, "music", f) for f in os.listdir(os.path.join(base, "music")) if f.endswith(".ogg"))
    bad = 0
    print("%-16s %6s %6s %6s %7s %7s %7s" % ("", "sec", "peak", "flat", ">200Hz", "<80Hz", "melody"))
    for path in targets:
        name = os.path.basename(path).rsplit(".", 1)[0]
        m = measure(path)
        music = path.endswith(".ogg")
        fails = []
        if music:
            if m["flat"] > MUSIC["flatness"]:
                fails.append("noisy: flatness %.3f over %.2f" % (m["flat"], MUSIC["flatness"]))
            if m["above200"] < MUSIC["above200"]:
                fails.append("no phone will play it: only %.0f%% above 200 Hz, wants %.0f%%" % (100 * m["above200"], 100 * MUSIC["above200"]))
            if m["melody"] < MUSIC["melody"]:
                fails.append("no tune in it: %.0f%% in the melody band, wants %.0f%%" % (100 * m["melody"], 100 * MUSIC["melody"]))
            if m["sub80"] > MUSIC["sub80"]:
                fails.append("%.0f%% wasted below 80 Hz, over %.0f%%" % (100 * m["sub80"], 100 * MUSIC["sub80"]))
            src = path[:-4] + ".strudel"
            if os.path.exists(src):
                out = check_scale(src, world)
                if out:
                    fails.append("notes outside the six: " + ", ".join(out))
        else:
            flat_max, above_min, (pk_lo, pk_hi) = LIMITS.get(name, LIMITS["_default"])
            if m["flat"] > flat_max:
                fails.append("static: flatness %.3f over %.2f" % (m["flat"], flat_max))
            if m["above200"] < above_min:
                fails.append("inaudible on a phone: %.0f%% above 200 Hz, wants %.0f%%" % (100 * m["above200"], 100 * above_min))
            if not (pk_lo <= m["peak"] <= pk_hi):
                fails.append("peak %.2f outside %.2f to %.2f" % (m["peak"], pk_lo, pk_hi))
        mark = "ok  " if not fails else "FAIL"
        print("%s %-16s %6.2f %6.2f %6.3f %6.0f%% %6.0f%% %6.0f%%" % (
            mark, name, m["seconds"], m["peak"], m["flat"], 100 * m["above200"], 100 * m["sub80"], 100 * m["melody"]))
        for f in fails:
            print("       %s" % f)
            bad += 1
    print("\n%s" % ("all audio passes" if not bad else "%d problem(s): see FAIL above" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

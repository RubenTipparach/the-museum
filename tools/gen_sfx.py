#!/usr/bin/env python3
"""Sound effects for the Elmorian exhibit, from the standard library alone.

Seeded, so a rerun is byte identical (CLAUDE.md 7, ADR-12: the tom-lander
shape, tools/generate_weapon_sfx.py there is the model). A museum after hours
is nearly silent, so these are small sounds: stone on stone, a click, a chime
when a door decides to open, and one long rocky slide for the door itself.

  python3 tools/gen_sfx.py           writes assets/audio/sfx/*.wav
  python3 tools/gen_sfx.py --check   exits 1 if any committed file differs
"""
import io
import math
import os
import random
import struct
import sys
import wave

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "assets", "audio", "sfx")
SR = 44100
PAD_HZ = [220.0, 261.6, 293.7, 349.2, 392.0, 440.0]   # the six pads, the prototype's tones


# ---- building blocks ----------------------------------------------------------------
def n_of(seconds):
    return int(SR * seconds)


def tone(freq, dur, wave_kind="sine", vol=0.2, attack=0.004, f_end=None):
    """One voice with the prototype's envelope: a 4 ms rise, then an
    exponential fall to nothing at `dur`. `f_end` sweeps the pitch."""
    out = []
    n = n_of(dur)
    for i in range(n):
        t = i / SR
        f = freq if f_end is None else freq * (f_end / freq) ** (t / dur)
        ph = 2 * math.pi * f * t
        if wave_kind == "sine":
            x = math.sin(ph)
        elif wave_kind == "triangle":
            x = 2 / math.pi * math.asin(math.sin(ph))
        else:
            x = 1.0 if math.sin(ph) >= 0 else -1.0
        env = min(1.0, t / attack) * (0.0001 ** (t / dur))
        out.append(x * env * vol)
    return out


def noise(dur, rng, lp=0.3, hp=0.0, vol=1.0):
    """White noise through a one pole low pass (and an optional one pole high
    pass): the body of every scrape and knock."""
    out, prev, hprev, hx = [], 0.0, 0.0, 0.0
    for _ in range(n_of(dur)):
        w = rng.uniform(-1.0, 1.0)
        prev += lp * (w - prev)
        y = prev
        if hp > 0:
            hprev += hp * (y - hprev)
            y = y - hprev
        out.append(y * vol)
    return out


def shape(samples, env):
    """Multiply by an envelope function of t in seconds."""
    return [s * env(i / SR) for i, s in enumerate(samples)]


def decay(dur, floor=0.0001):
    return lambda t: floor ** (t / dur)


def swell(rise, dur):
    return lambda t: min(1.0, t / rise) * max(0.0, 1.0 - max(0.0, t - (dur - rise)) / rise)


def mix(*layers):
    """Sum of (samples, start_seconds) pairs."""
    n = max(int(at * SR) + len(s) for s, at in layers)
    out = [0.0] * n
    for s, at in layers:
        o = int(at * SR)
        for i, v in enumerate(s):
            out[o + i] += v
    return out


def normalize(samples, peak=0.8):
    m = max(1e-9, max(abs(s) for s in samples))
    return [s * peak / m for s in samples]


def loop_seam(samples, seconds=0.5):
    """Cross fade the tail into the head so the bed repeats without a click."""
    n = n_of(seconds)
    out = samples[:-n]
    for i in range(n):
        k = i / n
        out[i] = out[i] * k + samples[len(samples) - n + i] * (1 - k)
    return out


def wav_bytes(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))
    return buf.getvalue()


# ---- the sounds ----------------------------------------------------------------------------
def ui_click(rng):
    # a dry chit: a grain of noise and the prototype's 900 Hz blip under it
    return normalize(mix((tone(900, 0.05, "square", 0.05), 0), (shape(noise(0.02, rng, 0.6), decay(0.02)), 0)), 0.5)


def eye_tick(i, rng):
    # a stone disc turning one notch: four ratchet clicks over a ringing tone
    clicks = [(shape(noise(0.012, rng, 0.5, vol=0.9), decay(0.012)), k * 0.034) for k in range(4)]
    return normalize(mix((tone(500 + i * 120, 0.09, "triangle", 0.25), 0.0), *clicks), 0.7)


def thud(rng):
    # a refusal: a knuckle on a slab that will not move
    return normalize(mix((tone(90, 0.18, "sine", 0.6, f_end=55), 0), (shape(noise(0.08, rng, 0.08), decay(0.08)), 0)), 0.8)


def lift(rng):
    # a ring lifted off its peg: a short scrape rising, and a note
    scrape = shape(noise(0.16, rng, 0.35, hp=0.02), lambda t: min(1.0, t / 0.05) * (0.001 ** (t / 0.16)))
    return normalize(mix((tone(330, 0.12, "triangle", 0.25), 0.02), (scrape, 0)), 0.6)


def drop(rng):
    # a ring set down: a low note and a stone rattle that settles
    rattle = [(shape(noise(0.01, rng, 0.45, vol=0.6), decay(0.01)), 0.04 + k * 0.03) for k in range(3)]
    return normalize(mix((tone(180, 0.16, "sine", 0.5), 0), (shape(noise(0.03, rng, 0.2), decay(0.03)), 0), *rattle), 0.8)


def pad(i, rng):
    f = PAD_HZ[i]
    press = shape(noise(0.015, rng, 0.4), decay(0.015))
    return normalize(mix((press, 0), (tone(f, 0.55, "sine", 0.45), 0.005), (tone(f * 2, 0.28, "triangle", 0.1), 0.005)), 0.75)


def chime():
    return normalize(mix(*((tone(f, 0.55, "sine", 0.3), d) for f, d in ((523, 0.0), (659, 0.12), (784, 0.24)))), 0.7)


def door_chime():
    return normalize(mix(*((tone(f, 0.75, "triangle", 0.25), d) for f, d in ((392, 0.0), (523, 0.15), (659, 0.3), (1047, 0.45)))), 0.7)


def door_open(rng):
    # a stone slab sliding into the floor: 2.4 s of rumble and grit, then it
    # seats with a thud. Brown-ish noise for the rumble (integrated white,
    # heavily low passed), a grinding band on top whose level wanders.
    dur = 2.4
    rumble = shape(noise(dur, rng, 0.02, vol=6.0), swell(0.35, dur))
    grit = noise(dur, rng, 0.3, hp=0.08, vol=0.5)
    level, walk = 0.5, []
    for i in range(len(grit)):
        if i % 441 == 0:
            level = min(1.0, max(0.15, level + rng.uniform(-0.25, 0.25)))
        walk.append(level)
    grit = [g * w for g, w in zip(grit, walk)]
    grit = shape(grit, swell(0.4, dur))
    seat = mix((tone(60, 0.35, "sine", 0.9, f_end=40), 0), (shape(noise(0.12, rng, 0.06, vol=2.0), decay(0.12)), 0))
    return normalize(mix((rumble, 0), (grit, 0), (seat, dur - 0.25)), 0.85)


def step(rng):
    return normalize(mix((tone(140, 0.1, "sine", 0.3), 0), (shape(noise(0.08, rng, 0.2), decay(0.08)), 0)), 0.45)


def room_tone(rng):
    # eight seconds of the hall at night: the hum of the case lights and air
    # moving, made to loop. Quiet on purpose; it sits under everything.
    dur = 8.5
    hum = [0.0] * n_of(dur)
    for f, v in ((55.0, 0.05), (110.0, 0.03), (165.0, 0.012), (220.0, 0.006)):
        for i in range(len(hum)):
            hum[i] += math.sin(2 * math.pi * f * i / SR) * v * (1 + 0.15 * math.sin(2 * math.pi * 0.11 * i / SR))
    air = noise(dur, rng, 0.05, vol=1.2)
    air = [a * (0.7 + 0.3 * math.sin(2 * math.pi * 0.07 * i / SR)) for i, a in enumerate(air)]
    return loop_seam(normalize(mix((hum, 0), (air, 0)), 0.3))


def build():
    rng = random.Random(6)     # the Elmorians count in sixes
    files = {
        "ui_click": ui_click(rng), "thud": thud(rng), "lift": lift(rng), "drop": drop(rng),
        "chime": chime(), "door_chime": door_chime(), "door_open": door_open(rng), "step": step(rng),
        "room_tone": room_tone(rng),
    }
    for i in range(3):
        files["eye_tick_%d" % i] = eye_tick(i, rng)
    for i in range(6):
        files["pad_%d" % i] = pad(i, rng)
    return {k: wav_bytes(v) for k, v in files.items()}


def main(argv):
    check = "--check" in argv
    made = build()
    bad = 0
    os.makedirs(OUT, exist_ok=True)
    for name in sorted(made):
        path = os.path.join(OUT, name + ".wav")
        if check:
            have = open(path, "rb").read() if os.path.exists(path) else None
            if have != made[name]:
                print("DRIFT " + path); bad += 1
            else:
                print("ok    " + path)
        else:
            with open(path, "wb") as f:
                f.write(made[name])
            print("wrote %s (%.2f s)" % (path, (len(made[name]) - 44) / 2 / SR))
    if check:
        print("all %d effects match their generator" % len(made) if not bad else "%d files drift" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

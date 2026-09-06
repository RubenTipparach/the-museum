"""Render a MIDI file to a wav with fluidsynth, and master it.

The one place a sound is rendered (CLAUDE.md 4.1). tools/gen_sfx.py and
tools/gen_music.py both write .mid files and both come through here, so the
soundfont, the reverb and the level policy are set once.

Why a soundfont and not synthesis in Python: CLAUDE.md 5 wants a real tool
driven headless, the way Blender makes the models. An earlier cut of the
effects hand rolled every waveform out of filtered noise and shipped as
static. A .mid opens in LMMS, Ardour or MuseScore, so the source is editable
by a person, which is the other half of that rule.
"""
import math
import os
import struct
import subprocess
import tempfile
import wave

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100


def have_tools():
    missing = [t for t in ("fluidsynth",) if subprocess.run(["which", t], capture_output=True).returncode]
    if not os.path.exists(SOUNDFONT):
        missing.append(SOUNDFONT)
    return missing


def render(mid, room=0.7, level=0.55, gain=0.6, chorus=False):
    """MIDI to samples, through fluidsynth's own reverb. `room` is the size of
    the space the sound is heard in: a museum hall is large."""
    out = tempfile.mktemp(suffix=".wav")
    cmd = ["fluidsynth", "-a", "file", "-F", out, "-r", str(SR), "-g", str(gain), "-q",
           "-o", "synth.reverb.active=yes",
           "-o", "synth.reverb.room-size=%.2f" % room,
           "-o", "synth.reverb.level=%.2f" % level,
           "-o", "synth.reverb.damp=0.4",
           "-o", "synth.reverb.width=0.8",
           "-o", "synth.chorus.active=%s" % ("yes" if chorus else "no"),
           SOUNDFONT, mid]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError("fluidsynth failed on %s: %s" % (mid, r.stderr.decode()[:400]))
    try:
        return read(out)
    finally:
        os.remove(out)


def read(path):
    with wave.open(path, "rb") as w:
        ch, n = w.getnchannels(), w.getnframes()
        raw = w.readframes(n)
    a = struct.unpack("<%dh" % (len(raw) // 2), raw)
    if ch == 2:
        a = [(a[i] + a[i + 1]) / 65536.0 for i in range(0, len(a), 2)]
    else:
        a = [s / 32768.0 for s in a]
    return list(a)


# ---- mastering: what a person would do after the render ------------------------------
def dc_block(a, corner=20.0):
    """Take the DC offset out. Several FluidR3 samples carry one, and the
    score came off the renderer sitting at +0.028: that is headroom spent on
    a constant, a thump when a sound starts or stops, and, measured as a
    spectrum, nearly half the energy in a band nothing can reproduce. One
    pole high pass at 20 Hz, which is under everything the museum plays."""
    r = math.exp(-2 * math.pi * corner / SR)
    out = [0.0] * len(a)
    x1 = y1 = 0.0
    for i, x in enumerate(a):
        y1 = x - x1 + r * y1
        x1 = x
        out[i] = y1
    return out



def trim(a, floor=0.0015, keep_tail=0.12):
    """Drop the silence fluidsynth leaves at each end, keeping a little of the
    tail so a reverb is not cut off."""
    lo = 0
    while lo < len(a) and abs(a[lo]) < floor:
        lo += 1
    hi = len(a)
    while hi > lo and abs(a[hi - 1]) < floor:
        hi -= 1
    return a[lo:min(len(a), hi + int(keep_tail * SR))]


def fade(a, seconds=0.05, tail=None):
    n = max(1, int(seconds * SR))
    m = max(1, int((tail if tail is not None else seconds) * SR))
    out = list(a)
    for i in range(min(n, len(out))):
        out[i] *= i / n
    for i in range(min(m, len(out))):
        out[-1 - i] *= i / m
    return out


def peak_to(a, peak):
    m = max(1e-9, max(abs(s) for s in a))
    return [s * peak / m for s in a]


def loop_seam(a, seconds=1.0):
    """Cross fade the tail into the head so a bed repeats without a click."""
    n = int(seconds * SR)
    if n * 2 >= len(a):
        return a
    out = a[:-n]
    for i in range(n):
        k = i / n
        out[i] = out[i] * k + a[len(a) - n + i] * (1 - k)
    return out


def write(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in a))
    return path


def encode_ogg(wav_path, ogg_path, quality=4, serial=6):
    """A fixed stream serial, so the same audio encodes to the same bytes.
    Ogg puts a RANDOM serial in every stream header by default, which made a
    byte comparison of a re-render report drift on a file that had not
    changed. Six, because they count in sixes."""
    subprocess.run(["oggenc", "-Q", "-q", str(quality), "--serial", str(serial),
                    "-o", ogg_path, wav_path], check=True)
    return ogg_path

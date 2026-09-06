"""Render a sound from its source, and master it.

The one place a sound is rendered and the one place it is mastered
(CLAUDE.md 4.1). Two renderers, because there are two kinds of sound and a
soundfont is right for exactly one of them (docs/AUDIO.md):

  render_midi   a .mid through fluidsynth and the General MIDI soundfont.
                For a SCORE, where the point is instruments playing notes.
  render_csound a .csd through csound. For an EFFECT, where the point is an
                object making a noise: modal resonator banks for a struck
                body, friction inside a band for stone across stone. A wood
                block instrument sounds like a wood block being PLAYED, which
                is not what a fingertip on a label sounds like.

Both write 32 bit float and are mastered by sox, which does the trimming,
the DC block, the fades and the normalisation. Csound's modal banks have
enormous gain at high Q, so a float intermediate is what keeps the render
from clipping before the level is set.
"""
import math
import os
import struct
import subprocess
import tempfile
import wave

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
ORCHESTRA = "museum.orc"     # beside the .csd files it is included by
SR = 44100


def have_tools():
    missing = [t for t in ("fluidsynth", "csound", "sox", "oggenc")
               if subprocess.run(["which", t], capture_output=True).returncode]
    if not os.path.exists(SOUNDFONT):
        missing.append(SOUNDFONT)
    return missing


def render_midi(mid, room=0.7, level=0.55, gain=0.6, chorus=False):
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
    return out


def render_csound(csd):
    """A .csd to a float wav. Run from the file's own directory so its
    #include of the orchestra resolves the way it does for a person who
    opens the folder and types `csound door_open.csd`."""
    out = tempfile.mktemp(suffix=".wav")
    r = subprocess.run(["csound", "-o", out, "-W", "-f", "-d", "-m0", os.path.basename(csd)],
                       cwd=os.path.dirname(os.path.abspath(csd)), capture_output=True, text=True)
    errors = [l for l in r.stderr.splitlines()
              if ("error" in l.lower() or "cannot" in l.lower()) and not l.startswith("0 errors")]
    if errors or not os.path.exists(out):
        raise RuntimeError("csound failed on %s:\n%s" % (csd, "\n".join(errors[:6]) or r.stderr[-400:]))
    return out


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


# ---- mastering: sox, which is what a person would reach for ------------------
# One chain, so a plaque tick and a door are levelled the same way:
#   highpass 20   the DC block. Several FluidR3 samples carry an offset and the
#                 score came off the renderer at +0.028: headroom spent on a
#                 constant, a thump at every start, and, measured as a
#                 spectrum, nearly half the energy where nothing reproduces it.
#   silence       trim the lead in and, reversed, the tail, so a file is the
#                 sound and not the renderer's padding.
#   fade          a 5 ms rise and an authored tail, so nothing clicks.
#   gain -n       normalise to the level this sound is meant to sit at.
def master(src, peak_db=-1.5, tail=0.12, trim=True):
    """Master a rendered wav to a mono 16 bit wav, and return its samples."""
    out = tempfile.mktemp(suffix=".wav")
    # Normalise FIRST, then trim. csound writes float at whatever level the
    # instrument happens to make, and a trim threshold is a share of full
    # scale: judging a signal peaking at 0.01 against 0.05% of full scale
    # trimmed the quietest effects away to nothing.
    # -D: no dither. sox adds dither automatically when it narrows float to
    # 16 bits, and dither is random, so two renders of an unchanged source
    # came out different files and --check reported drift on all eighteen.
    # At 16 bits the quantisation it would hide sits at -96 dBFS, which is
    # under the room tone, and a reproducible build is worth more than that.
    chain = ["sox", "-D", src, "-b", "16", "-c", "1", "-r", str(SR), out, "highpass", "20", "gain", "-n", "-0.5"]
    if trim:
        chain += ["silence", "1", "0.005", "0.03%",
                  "reverse", "silence", "1", "0.02", "0.008%", "reverse"]
    # The fade out is a fade IN on the reversed signal. sox cannot fade out
    # from the end of a stream whose length it no longer knows, which is what
    # the trim above leaves it with, and the reverse trick needs no length.
    chain += ["fade", "t", "0.005"]
    if tail > 0:
        chain += ["reverse", "fade", "t", str(tail), "reverse"]
    chain += ["gain", "-n", str(peak_db)]
    r = subprocess.run(chain, capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError("sox failed: %s" % r.stderr[-400:])
    try:
        return read(out)
    finally:
        os.remove(out)


def read_and_clean(path):
    return read(path)


def peak_to(a, peak):
    m = max(1e-9, max(abs(s) for s in a))
    return [s * peak / m for s in a]


def loop_seam(a, seconds=1.0):
    """Cross fade the tail into the head so a bed repeats without a click.
    The one piece of mastering sox makes awkward, because it is a file
    against itself."""
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

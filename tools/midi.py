"""A small standard MIDI file writer, pure stdlib.

The editable source of every sound in this repository is a .mid: it opens in
LMMS, Ardour, MuseScore or any DAW, which is what CLAUDE.md 5 asks of an
asset's source. tools/gen_music.py and tools/gen_sfx.py write them and
fluidsynth renders them; nothing here makes a waveform.
"""
import struct


def _vlq(n):
    """MIDI's variable length quantity."""
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


class Track:
    """One instrument. Times are in beats, floats allowed."""

    def __init__(self, name, program, channel, ticks=480):
        self.name, self.program, self.channel, self.ticks = name, program, channel, ticks
        self.events = []          # (tick, order, bytes)

    def _at(self, beat, order, data):
        self.events.append((int(round(beat * self.ticks)), order, data))

    def note(self, beat, pitch, beats, velocity=80):
        pitch = int(pitch)
        self._at(beat, 1, bytes([0x90 | self.channel, pitch & 0x7F, max(1, min(127, int(velocity)))]))
        self._at(beat + beats, 0, bytes([0x80 | self.channel, pitch & 0x7F, 0]))

    def control(self, beat, cc, value):
        self._at(beat, 2, bytes([0xB0 | self.channel, cc & 0x7F, max(0, min(127, int(value)))]))

    def pitch_bend(self, beat, semitones, rng=2.0):
        """A slide. The renderer's default bend range is two semitones."""
        v = int(8192 + 8191 * max(-1.0, min(1.0, semitones / rng)))
        self._at(beat, 2, bytes([0xE0 | self.channel, v & 0x7F, (v >> 7) & 0x7F]))

    def chunk(self):
        head = [(0, 3, bytes([0xFF, 0x03, len(self.name)]) + self.name.encode())]
        if self.channel != 9:
            head.append((0, 3, bytes([0xC0 | self.channel, self.program & 0x7F])))
        evs = sorted(head + self.events, key=lambda e: (e[0], e[1]))
        data, last = bytearray(), 0
        for tick, _order, payload in evs:
            data += _vlq(tick - last) + payload
            last = tick
        data += _vlq(0) + b"\xFF\x2F\x00"
        return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def write(path, tracks, bpm=60, ticks=480):
    for t in tracks:
        t.ticks = ticks
    tempo = int(60_000_000 / bpm)
    meta = Track("tempo", 0, 0, ticks)
    meta.events.append((0, 0, bytes([0xFF, 0x51, 0x03]) + struct.pack(">I", tempo)[1:]))
    head = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks) + 1, ticks)
    with open(path, "wb") as f:
        f.write(head + meta.chunk() + b"".join(t.chunk() for t in tracks))
    return path

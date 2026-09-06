; The hall at night: the air plant, and the room answering it.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound room_tone.csd`.
<CsoundSynthesizer>
<CsOptions>
-o room_tone.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "air" 0      14     0.9
e 14
</CsScore>
</CsoundSynthesizer>

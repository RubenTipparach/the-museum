; A stone slab going down into the floor: it catches, it slips, it seats.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound door_open.csd`.
<CsoundSynthesizer>
<CsOptions>
-o door_open.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "slab" 0      2.3    0.95
i "seat" 2.18   1.4    0.9
e 3.6
</CsScore>
</CsoundSynthesizer>

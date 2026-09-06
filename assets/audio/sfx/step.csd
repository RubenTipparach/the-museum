; A shoe on museum carpet: almost nothing, and what there is, is low.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound step.csd`.
<CsoundSynthesizer>
<CsOptions>
-o step.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "carpet" 0      0.4    0.8
e 0.5
</CsScore>
</CsoundSynthesizer>

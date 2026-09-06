; A stone disc turning one notch of six. The day eye, the largest disc and the lowest.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound eye_tick_0.csd`.
<CsoundSynthesizer>
<CsOptions>
-o eye_tick_0.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "label" 0      0.05   0.35
i "stone" 0.012  0.7    0.9   300      0.16
e 0.8
</CsScore>
</CsoundSynthesizer>

; The eye pad: a stone cut to sing at C5.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound pad_2.csd`.
<CsoundSynthesizer>
<CsOptions>
-o pad_2.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "singing" 0      2.2    0.9   523.2511 1.5
e 2.4
</CsScore>
</CsoundSynthesizer>

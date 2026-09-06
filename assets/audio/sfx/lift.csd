; A ring lifted off its peg: stone leaving stone.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound lift.csd`.
<CsoundSynthesizer>
<CsOptions>
-o lift.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "stone" 0      0.5    0.7   260      0.1
i "label" 0.005  0.09   0.45
e 0.6
</CsScore>
</CsoundSynthesizer>

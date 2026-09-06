; A ring set down on stone, and its one small bounce.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound drop.csd`.
<CsoundSynthesizer>
<CsOptions>
-o drop.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "stone" 0      0.6    1     247      0.22
i "stone" 0.085  0.4    0.34  247      0.12
i "label" 0      0.05   0.28
e 0.8
</CsScore>
</CsoundSynthesizer>

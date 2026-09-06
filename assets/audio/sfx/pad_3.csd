; The touch pad: a stone cut to sing at G4.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound pad_3.csd`.
<CsoundSynthesizer>
<CsOptions>
-o pad_3.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "singing" 0      2.2    0.9   391.9954 1.5
e 2.4
</CsScore>
</CsoundSynthesizer>

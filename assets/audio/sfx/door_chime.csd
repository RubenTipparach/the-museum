; A door deciding to open: the house theme's own first four notes.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound door_chime.csd`.
<CsoundSynthesizer>
<CsOptions>
-o door_chime.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "bronze" 0      2.6    0.8   440      2.2
i "bronze" 0.32   2.6    0.8   523.2511 2.2
i "bronze" 0.64   2.6    0.8   440      2.2
i "bronze" 0.96   2.6    0.8   391.9954 2.2
e 3.6
</CsScore>
</CsoundSynthesizer>

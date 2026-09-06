; A phrase understood: the greeting's first three notes, on bronze.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound chime.csd`.
<CsoundSynthesizer>
<CsOptions>
-o chime.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "bronze" 0      2      0.75  440      1.6
i "bronze" 0.26   2      0.75  523.2511 1.6
i "bronze" 0.52   2      0.75  391.9954 1.6
e 2.8
</CsScore>
</CsoundSynthesizer>

; A refusal: something heavy that does not move, and the knock on top of it.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound thud.csd`.
<CsoundSynthesizer>
<CsOptions>
-o thud.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "stone" 0      0.9    0.3   92       0.3
i "stone" 0      0.55   1     330      0.12
i "stone" 0      0.35   0.55  690      0.06
i "label" 0      0.07   0.7
e 1
</CsScore>
</CsoundSynthesizer>

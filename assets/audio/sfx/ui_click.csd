; A fingertip on a label: a nail across card over board.
; Written by tools/gen_sfx.py from data/world/music.json. The bodies
; are museum.orc beside this file; render it with `csound ui_click.csd`.
<CsoundSynthesizer>
<CsOptions>
-o ui_click.wav -W -f -d -m0
</CsOptions>
<CsInstruments>
#include "museum.orc"
</CsInstruments>
<CsScore>
; instr    start  dur    amp   pitch    decay
i "label" 0      0.22   0.8
e 0.4
</CsScore>
</CsoundSynthesizer>

; The museum's instrument set: the bodies every sound effect is struck out of.
;
; Csound, rendered headless (docs/AUDIO.md). This file is the source: change a
; body here and every sound made of it changes. Each .csd beside it holds only
; a score, and includes this.
;
; The idea throughout is MODAL synthesis. A struck object rings at a set of
; frequencies with a set of decay times, and what tells stone from wood from
; bronze is the RATIOS between them and how fast the high ones die. Nothing
; here is a sample and nothing is broadband noise: noise appears only as
; friction and as the grit an impact presses out, always inside a band.
;
; Decay is written as seconds and turned into the resonator's Q, because a
; time is a thing a person can reason about and a Q is not: for a mode at f
; ringing for t seconds, Q is pi * f * t.

sr = 44100
ksmps = 32
nchnls = 1
0dbfs = 1

; A fixed seed, so a re-render is byte identical and --check can tell a
; changed sound from a re-rendered one. Csound seeds its noise from the clock
; otherwise, and every one of these effects has friction or grit in it. Six,
; because they count in sixes.
seed 6

opcode Qof, i, ii
  ifreq, itime xin
  xout        3.14159265 * ifreq * itime
endop

; ---- cut stone: dense, inharmonic, and dead within a breath -------------------
; p4 amp, p5 pitch, p6 decay seconds
instr stone
  iq1   Qof    p5 * 1.00, p6
  iq2   Qof    p5 * 1.47, p6 * 0.62
  iq3   Qof    p5 * 2.09, p6 * 0.40
  iq4   Qof    p5 * 2.71, p6 * 0.28
  iq5   Qof    p5 * 3.36, p6 * 0.18
  aexc  mpulse 1, 0
  anz   noise  0.35, 0
  aeg   expseg 1, 0.0012, 0.03, 0.006, 0.0001
  aexc  =      aexc + anz * aeg
  a1    mode   aexc, p5 * 1.00, iq1
  a2    mode   aexc, p5 * 1.47, iq2
  a3    mode   aexc, p5 * 2.09, iq3
  a4    mode   aexc, p5 * 2.71, iq4
  a5    mode   aexc, p5 * 3.36, iq5
        out    (a1 + a2 * 0.45 + a3 * 0.26 + a4 * 0.14 + a5 * 0.07) * p4 * 0.02
endin

; ---- a stone cut to sing: the speech pads ------------------------------------
; Fewer modes and nearly harmonic, so it holds a pitch a phrase can be heard
; in, but struck rather than blown. p4 amp, p5 pitch, p6 decay seconds
instr singing
  iq1   Qof    p5 * 1.00, p6
  iq2   Qof    p5 * 2.01, p6 * 0.55
  iq3   Qof    p5 * 3.02, p6 * 0.33
  iq4   Qof    p5 * 4.18, p6 * 0.18
  aexc  mpulse 1, 0
  anz   noise  0.18, 0
  aeg   expseg 1, 0.002, 0.04, 0.008, 0.0001
  aexc  =      aexc + anz * aeg
  ahit  butterbp anz * aeg, p5 * 6, p5 * 4
  a1    mode   aexc, p5 * 1.00, iq1
  a2    mode   aexc, p5 * 2.01, iq2
  a3    mode   aexc, p5 * 3.02, iq3
  a4    mode   aexc, p5 * 4.18, iq4
        out    ((a1 + a2 * 0.5 + a3 * 0.3 + a4 * 0.15) * 0.012 + ahit * 0.10) * p4
endin

; ---- bronze: a bell's own ratios, and it rings a long time -------------------
instr bronze
  iq1   Qof    p5 * 1.00, p6
  iq2   Qof    p5 * 2.76, p6 * 0.7
  iq3   Qof    p5 * 5.40, p6 * 0.45
  iq4   Qof    p5 * 8.93, p6 * 0.25
  aexc  mpulse 1, 0
  a1    mode   aexc, p5 * 1.00, iq1
  a2    mode   aexc, p5 * 2.76, iq2
  a3    mode   aexc, p5 * 5.40, iq3
  a4    mode   aexc, p5 * 8.93, iq4
  ; the strike itself, before the bell answers
  anz   noise  1, 0
  aeg   expseg 1, 0.004, 0.05, 0.02, 0.0001
  ahit  butterbp anz * aeg, p5 * 4, p5 * 3
        out    ((a1 + a2 * 0.5 + a3 * 0.26 + a4 * 0.11) * 0.012 + ahit * 0.25) * p4
endin

; ---- a fingertip on a label: a nail across card over board ------------------
instr label
  anz   noise  1, 0
  aeg   expseg 1, 0.004, 0.15, 0.02, 0.0001
  abr   butterbp anz * aeg, 2600, 1800
  a1    mode   abr, 1900, 60
  a2    mode   abr, 3100, 45
        out    (abr * 0.6 + (a1 + a2 * 0.6) * 0.02) * p4
endin

; ---- stone across stone ------------------------------------------------------
; Friction whose band wanders, catching and slipping, over the slab's own body.
; The body sits at 95 and 150 Hz rather than down at 40: below 80 a phone makes
; no sound at all, so weight there is weight nobody hears. p4 amp.
instr slab
  idur   =      p3
  kj     randi  380, 11, 0.3
  kc     line   520, idur, 900
  anz    noise  1, 0
  asc    butterbp anz, kc + kj, 300
  kg     randi  0.5, 7, 0.7
  kswell linseg 0, 0.35, 1, idur - 0.75, 1, 0.4, 0.25
  asc    =      asc * (0.55 + kg) * kswell
  arum   noise  1, 0
  arum   butterlp arum, 220
  iqa    Qof    95, 0.09
  iqb    Qof    150, 0.07
  a1     mode   arum, 95, iqa
  a2     mode   arum, 150, iqb
         out    (asc * 1.5 + (a1 + a2 * 0.6) * 0.012 * kswell) * p4
endin

; ---- a heavy stone landing, and the grit it presses out ---------------------
instr seat
  iq1   Qof    88, 0.34
  iq2   Qof    143, 0.24
  iq3   Qof    232, 0.16
  aexc  mpulse 1, 0
  a1    mode   aexc, 88, iq1
  a2    mode   aexc, 143, iq2
  a3    mode   aexc, 232, iq3
  anz   noise  1, 0
  aeg   expseg 1, 0.006, 0.08, 0.05, 0.0001
  agr   butterbp anz * aeg, 700, 600
        out    ((a1 + a2 * 0.5 + a3 * 0.4) * 0.010 + agr * 0.75) * p4
endin

; ---- a shoe on museum carpet: a soft low thump and a brush of pile ----------
instr carpet
  iq1   Qof    150, 0.06
  iq2   Qof    240, 0.04
  aexc  mpulse 1, 0
  a1    mode   aexc, 150, iq1
  a2    mode   aexc, 240, iq2
  anz   noise  1, 0
  aeg   expseg 1, 0.006, 0.12, 0.03, 0.0001
  abr   butterbp anz * aeg, 1100, 900
        out    ((a1 + a2 * 0.5) * 0.015 + abr * 0.55) * p4
endin

; ---- the hall at night -------------------------------------------------------
; Not a noise bed. An empty building is a few narrow resonances, the air plant
; and the room answering it, and the ear reads the quiet between them as space.
; Very low noise through very narrow bands, each drifting against the others.
instr air
  anz    noise  1, 0
  alow   butterlp anz, 260
  kd1    randi  1.5, 0.07, 0.11
  kd2    randi  2.2, 0.05, 0.31
  kd3    randi  3.0, 0.04, 0.53
  a1     reson  alow, 57 + kd1, 2.2, 1
  a2     reson  alow, 86 + kd2, 3.0, 1
  a3     reson  alow, 114 + kd3, 3.6, 1
  a4     reson  alow, 171, 6.0, 1
  ; one long room resonance, at the edge of hearing
  iq     Qof    220, 6.0
  afar   mode   alow * 0.02, 220, iq
         out    (a1 * 0.5 + a2 * 0.33 + a3 * 0.2 + a4 * 0.09 + afar * 0.004) * p4
endin

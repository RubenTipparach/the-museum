// Offline renderer for Strudel patterns (no browser needed). Vendored from
// RubenTipparach/tom-lander tools/strudel with the owner's permission (ADR-12);
// the one change is that a plain .strudel source file is accepted (below).
// Evaluates the pattern with strudel's own engine (@strudel/core + mini +
// transpiler), queries the event stream, and synthesizes audio with a small
// Node DSP that covers the features these tracks use: saw/tri/sine/square
// oscillators (polyBLEP), ADSR, biquad lowpass, waveshaper distortion,
// vibrato, synthesized bd/sd/hh/oh drums, stereo feedback delay and a
// Schroeder reverb, equal-power pan.
//
// Usage: node render_offline.mjs <url-file> <out.wav> <cycles> [tailSeconds]
import fs from 'fs';
import { evalScope, noteToMidi } from '@strudel/core';

const SR = 44100;

const urlFile = process.argv[2];
const outWav = process.argv[3];
const CYCLES = parseFloat(process.argv[4]);
const TAIL = parseFloat(process.argv[5] || '3.5');

// ---- the pattern: a plain .strudel source, or a strudel.cc share URL --------
// (the-museum keeps the source itself beside the render, CLAUDE.md 7; the URL
// form is kept so a pattern pasted from strudel.cc still renders)
const text = fs.readFileSync(urlFile, 'utf8').trim();
const code = /^https?:\/\//.test(text)
  ? Buffer.from(decodeURIComponent(text.split('#')[1]), 'base64').toString('utf8')
  : text;
console.log('code:', code.split('\n').slice(0, 3).join(' | ').slice(0, 120));

// ---- evaluate the pattern ----------------------------------------------------
let CPS = 0.5;
await evalScope(
  import('@strudel/core'),
  import('@strudel/mini'),
  { setcps: (x) => { CPS = x; }, setCps: (x) => { CPS = x; } },
);
const { evaluate } = await import('@strudel/transpiler');
const { pattern } = await evaluate(code);
console.log('cps =', CPS, ' cycles =', CYCLES, ' length =', (CYCLES / CPS).toFixed(2), 's');

const haps = pattern.queryArc(0, CYCLES).filter(h => h.hasOnset());
console.log('events:', haps.length);

// ---- output + buses ------------------------------------------------------------
const totalSec = CYCLES / CPS + TAIL;
const N = Math.ceil(totalSec * SR);
const L = new Float64Array(N), R = new Float64Array(N);          // dry master
const dL = new Float64Array(N), dR = new Float64Array(N);        // delay send
const vL = new Float64Array(N), vR = new Float64Array(N);        // reverb send

let delayTime = 0.25, roomSize = 2;

// ---- tiny DSP helpers ------------------------------------------------------------
function biquadLP(freq, q = 1) {
  const w = 2 * Math.PI * Math.min(freq, SR * 0.45) / SR;
  const alpha = Math.sin(w) / (2 * q);
  const cosw = Math.cos(w);
  const b0 = (1 - cosw) / 2, b1 = 1 - cosw, b2 = (1 - cosw) / 2;
  const a0 = 1 + alpha, a1 = -2 * cosw, a2 = 1 - alpha;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  return (x) => {
    const y = (b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    return y;
  };
}

function polyblep(t, dt) {
  if (t < dt) { t /= dt; return t + t - t * t - 1; }
  if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
  return 0;
}

function shaperCurve(amount) {
  const k = (2 * amount) / (1 - Math.min(amount, 0.99));
  return (x) => ((1 + k) * x) / (1 + k * Math.abs(x));
}

// superdough-ish envelope defaults
function adsr(attack, decay, sustain, release, susSec) {
  const a = Math.max(attack, 0.0005), d = Math.max(decay, 0.001), r = Math.max(release, 0.005);
  const total = Math.max(susSec, a + d * 0.5) + r;
  return {
    total,
    at: (t) => {
      if (t < a) return t / a;
      if (t < a + d) return 1 + (sustain - 1) * ((t - a) / d);
      if (t < susSec) return sustain;
      const rt = (t - Math.max(susSec, a + d)) / r;
      return rt >= 1 ? 0 : sustain * (1 - rt);
    },
  };
}

function noise() { return Math.random() * 2 - 1; }

// ---- voice rendering -----------------------------------------------------------
function addVoice(startSec, samples, pan, gain, delaySend, roomSend) {
  const start = Math.floor(startSec * SR);
  const pl = Math.cos((pan ?? 0.5) * Math.PI / 2);
  const pr = Math.sin((pan ?? 0.5) * Math.PI / 2);
  for (let i = 0; i < samples.length; i++) {
    const idx = start + i;
    if (idx >= N) break;
    const x = samples[i] * gain;
    L[idx] += x * pl; R[idx] += x * pr;
    if (delaySend > 0) { dL[idx] += x * pl * delaySend; dR[idx] += x * pr * delaySend; }
    if (roomSend > 0) { vL[idx] += x * pl * roomSend; vR[idx] += x * pr * roomSend; }
  }
}

function renderSynth(v, durSec) {
  const midi = typeof v.note === 'number' ? v.note : noteToMidi(v.note);
  const f0 = 440 * Math.pow(2, (midi - 69) / 12);
  const env = adsr(v.attack ?? 0.001, v.decay ?? 0.05, v.sustain ?? 0.6,
                   v.release ?? 0.01, durSec);
  const n = Math.ceil(env.total * SR);
  const out = new Float64Array(n);
  const lp = v.lpf ? biquadLP(v.lpf, v.resonance ?? 1) : null;
  const shape = v.shape ? shaperCurve(v.shape) : null;
  const vibHz = v.vib ?? 0, vibSemis = v.vibmod ?? 0.5;
  let phase = Math.random();
  const wave = v.s;
  for (let i = 0; i < n; i++) {
    const t = i / SR;
    let f = f0;
    if (vibHz > 0) f = f0 * Math.pow(2, (vibSemis * Math.sin(2 * Math.PI * vibHz * t)) / 12);
    const dt = f / SR;
    phase += dt;
    if (phase >= 1) phase -= 1;
    let x;
    if (wave === 'sine') x = Math.sin(2 * Math.PI * phase);
    else if (wave === 'triangle') x = 1 - 4 * Math.abs(Math.round(phase) - phase);
    else if (wave === 'square') {
      x = phase < 0.5 ? 1 : -1;
      x += polyblep(phase, dt);
      x -= polyblep((phase + 0.5) % 1, dt);
    } else { // sawtooth
      x = 2 * phase - 1;
      x -= polyblep(phase, dt);
    }
    if (shape) x = shape(x);
    if (lp) x = lp(x);
    out[i] = x * env.at(t) * 0.28;
  }
  return out;
}

function renderDrum(v) {
  const kind = v.s;
  let n, gen;
  if (kind === 'bd') {
    n = Math.ceil(0.28 * SR);
    let ph = 0;
    gen = (i) => {
      const t = i / SR;
      const f = 42 + 90 * Math.exp(-t * 30);
      ph += f / SR;
      const body = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 14);
      const click = t < 0.004 ? noise() * 0.5 * (1 - t / 0.004) : 0;
      return (body * 1.25 + click) * 0.9;
    };
  } else if (kind === 'sd') {
    n = Math.ceil(0.22 * SR);
    let ph = 0;
    gen = (i) => {
      const t = i / SR;
      ph += 185 / SR;
      const tone = Math.sin(2 * Math.PI * ph) * Math.exp(-t * 24) * 0.5;
      const snap = noise() * Math.exp(-t * 20) * 0.7;
      return (tone + snap) * 0.8;
    };
  } else if (kind === 'oh') {
    n = Math.ceil(0.3 * SR);
    let hp = 0;
    gen = (i) => {
      const t = i / SR;
      const x = noise();
      const y = x - hp; hp = hp + (x - hp) * 0.35;   // crude highpass
      return y * Math.exp(-t * 11) * 0.5;
    };
  } else { // hh
    n = Math.ceil(0.07 * SR);
    let hp = 0;
    gen = (i) => {
      const t = i / SR;
      const x = noise();
      const y = x - hp; hp = hp + (x - hp) * 0.45;
      return y * Math.exp(-t * 55) * 0.5;
    };
  }
  const out = new Float64Array(n);
  const lp = v.lpf ? biquadLP(v.lpf, v.resonance ?? 1) : null;
  for (let i = 0; i < n; i++) {
    let x = gen(i);
    if (lp) x = lp(x);
    out[i] = x;
  }
  return out;
}

// ---- render every event -----------------------------------------------------------
const DRUMS = new Set(['bd', 'sd', 'hh', 'oh']);
let skipped = 0;
for (const hap of haps) {
  const v = hap.value ?? {};
  const t0 = hap.whole.begin.valueOf() / CPS;
  const dur = (hap.whole.end.valueOf() - hap.whole.begin.valueOf()) / CPS;
  const gain = v.gain ?? 0.8;
  if (v.delaytime) delayTime = v.delaytime;
  if (v.roomsize) roomSize = Math.max(roomSize, v.roomsize);
  const delaySend = v.delay ?? 0;
  const roomSend = v.room ?? 0;
  try {
    let samples;
    if (DRUMS.has(v.s)) samples = renderDrum(v);
    else if (v.note !== undefined) samples = renderSynth(v, dur);
    else { skipped++; continue; }
    addVoice(t0, samples, v.pan, gain, delaySend, roomSend);
  } catch (e) { skipped++; }
}
if (skipped) console.log('skipped events:', skipped);

// ---- delay bus: stereo feedback with slight ping-pong -------------------------------
{
  const dn = Math.max(1, Math.round(delayTime * SR));
  const fb = 0.45;
  const bufL = new Float64Array(dn), bufR = new Float64Array(dn);
  let w = 0;
  for (let i = 0; i < N; i++) {
    const rl = bufL[w], rr = bufR[w];
    L[i] += rl; R[i] += rr;
    bufL[w] = dR[i] + rr * fb;      // cross-feed = ping-pong
    bufR[w] = dL[i] + rl * fb;
    w = (w + 1) % dn;
  }
}

// ---- reverb bus: 4 combs + 2 allpass per channel -------------------------------------
function reverbChannel(inp, out, seed) {
  const scale = 0.4 + roomSize * 0.18;
  const combs = [0.0297, 0.0311, 0.0371, 0.0414].map((t, k) => {
    const dn = Math.round((t * (1 + 0.13 * k * seed)) * scale * SR) || 1;
    return { buf: new Float64Array(dn), w: 0, g: 0.72 + Math.min(roomSize, 6) * 0.032 };
  });
  const aps = [0.005, 0.0017].map(t => {
    const dn = Math.round(t * SR) || 1;
    return { buf: new Float64Array(dn), w: 0, g: 0.7 };
  });
  for (let i = 0; i < N; i++) {
    let acc = 0;
    for (const c of combs) {
      const y = c.buf[c.w];
      c.buf[c.w] = inp[i] + y * c.g;
      c.w = (c.w + 1) % c.buf.length;
      acc += y;
    }
    let x = acc * 0.25;
    for (const a of aps) {
      const y = a.buf[a.w];
      const z = x + y * a.g;
      a.buf[a.w] = z;
      a.w = (a.w + 1) % a.buf.length;
      x = y - z * a.g;
    }
    out[i] += x * 0.8;
  }
}
reverbChannel(vL, L, 1.0);
reverbChannel(vR, R, 1.31);

// ---- normalize + fade tail + write WAV ------------------------------------------------
let peak = 0;
for (let i = 0; i < N; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
const norm = peak > 0 ? 0.89 / peak : 1;
const fadeStart = N - Math.floor(1.2 * SR);
const buf = Buffer.alloc(44 + N * 4);
buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 4, 4); buf.write('WAVE', 8);
buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20);
buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28);
buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34);
buf.write('data', 36); buf.writeUInt32LE(N * 4, 40);
for (let i = 0; i < N; i++) {
  const fade = i > fadeStart ? Math.max(0, 1 - (i - fadeStart) / (N - fadeStart)) : 1;
  buf.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(L[i] * norm * fade * 32767))), 44 + i * 4);
  buf.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(R[i] * norm * fade * 32767))), 46 + i * 4);
}
fs.writeFileSync(outWav, buf);
console.log('wrote', outWav, (N / SR).toFixed(1) + 's, peak', peak.toFixed(3));

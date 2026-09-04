// The four puzzles of the Elmorian exhibit, as plain state machines with no
// renderer and no DOM, so `node test.mjs` can solve them without a browser.
// This is the ADR-2 split in miniature: game.js draws these and asks them; it
// never decides an outcome itself.
//
// Numbers here are the world's: six positions on a gaze dial, six pads, and
// the six word glyphs, because the Elmorians count in sixes (WORLD.md 2).

(function (root) {
  'use strict';

  var WORDS = ['light', 'stone', 'eye', 'touch', 'door', 'dark'];

  // Room 1: three eye discs, each with six positions. The door opens when all
  // three look at the door mark (3). The final puzzle wants them on the sun,
  // the far eye and the door respectively.
  function makeGaze() {
    return { pos: [0, 5, 1], door: [3, 3, 3], final: [2, 4, 0] };
  }
  function gazeTap(g, i) { g.pos[i] = (g.pos[i] + 1) % 6; }
  function gazeMatches(g, target) {
    return g.pos[0] === target[0] && g.pos[1] === target[1] && g.pos[2] === target[2];
  }

  // Room 2: four rings on three pegs, Tower of Hanoi rules. Ring size 3 is the
  // largest. The door opens with the stack under the sun (peg 2); the final
  // puzzle wants it under the night eye (peg 1).
  function makeStack() {
    return { pegs: [[3, 2, 1, 0], [], []], held: null, from: null, doorPeg: 2, finalPeg: 1 };
  }
  // Returns 'lift', 'drop', 'return' (dropped back where it came from),
  // 'refuse' (illegal, ring stays held) or 'empty' (nothing to lift).
  function stackTap(s, peg) {
    var p = s.pegs[peg];
    if (s.held === null) {
      if (!p.length) return 'empty';
      s.held = p.pop();
      s.from = peg;
      return 'lift';
    }
    if (peg === s.from) { p.push(s.held); s.held = null; s.from = null; return 'return'; }
    if (p.length && p[p.length - 1] < s.held) return 'refuse';
    p.push(s.held); s.held = null; s.from = null;
    return 'drop';
  }
  function stackOn(s, peg) { return s.held === null && s.pegs[peg].length === 4; }

  // Room 3: six pads, one word each. A phrase is four pads in order. The
  // greeting opens the door; the farewell is what the final puzzle wants.
  // The two phrases begin differently, so a wrong first pad is known at once.
  function makeSpeech() {
    return {
      pads: [0, 1, 2, 3, 4, 5],
      greeting: [0, 2, 3, 4],   // light, eye, touch, door
      farewell: [1, 5, 3, 2],   // stone, dark, touch, eye
      input: [], last: null
    };
  }
  function isPrefix(input, phrase) {
    for (var i = 0; i < input.length; i++) if (input[i] !== phrase[i]) return false;
    return true;
  }
  // Returns 'ok', 'greeting', 'farewell' or 'wrong'.
  function speechTap(sp, pad) {
    sp.input.push(pad);
    var g = isPrefix(sp.input, sp.greeting), f = isPrefix(sp.input, sp.farewell);
    if (!g && !f) { sp.input = []; return 'wrong'; }
    if (g && sp.input.length === sp.greeting.length) { sp.input = []; sp.last = 'greeting'; return 'greeting'; }
    if (f && sp.input.length === sp.farewell.length) { sp.input = []; sp.last = 'farewell'; return 'farewell'; }
    return 'ok';
  }

  // Room 4: nothing of its own to touch. It reads the three rooms behind it and
  // opens when they hold the configuration its diagram shows.
  function finalMatches(g, s, sp) {
    return gazeMatches(g, g.final) && stackOn(s, s.finalPeg) && sp.last === 'farewell';
  }

  // The exhibit: which doors have opened. A door that has opened stays open,
  // so a solved room can be re-entered and re-set for the final puzzle.
  function makeExhibit() {
    return { gaze: makeGaze(), stack: makeStack(), speech: makeSpeech(),
             open: [true, false, false, false, false] };
  }
  function refreshDoors(x) {
    if (gazeMatches(x.gaze, x.gaze.door)) x.open[1] = true;
    if (stackOn(x.stack, x.stack.doorPeg)) x.open[2] = true;
    if (x.speech.last !== null) x.open[3] = true;
    if (finalMatches(x.gaze, x.stack, x.speech)) x.open[4] = true;
  }

  var api = { WORDS: WORDS, makeGaze: makeGaze, gazeTap: gazeTap, gazeMatches: gazeMatches,
              makeStack: makeStack, stackTap: stackTap, stackOn: stackOn,
              makeSpeech: makeSpeech, speechTap: speechTap, finalMatches: finalMatches,
              makeExhibit: makeExhibit, refreshDoors: refreshDoors };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Puzzles = api;
})(typeof window !== 'undefined' ? window : globalThis);

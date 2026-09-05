// Solves every puzzle without a browser. `node mockups/elmorian-exhibit/test.mjs`
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const P = require('./puzzles.js');

let n = 0;
function ok(cond, msg) { assert.ok(cond, msg); n++; }

// Room 1: taps advance one of six positions and the door needs all on 3.
const x = P.makeExhibit();
ok(!P.gazeMatches(x.gaze, x.gaze.door), 'gaze starts unsolved');
for (let i = 0; i < 3; i++) while (x.gaze.pos[i] !== 3) P.gazeTap(x.gaze, i);
P.refreshDoors(x);
ok(x.open[1] && !x.open[2], 'gaze on the door opens door 1 only');
for (let i = 0; i < 6; i++) P.gazeTap(x.gaze, 0);
ok(x.gaze.pos[0] === 3, 'six taps is a full turn');
ok(x.open[1], 'a door that opened stays open when the dials move');

// Room 2: Hanoi rules, four rings, refused moves keep the ring held.
const s = x.stack;
ok(P.stackTap(s, 1) === 'empty', 'nothing to lift from an empty peg');
ok(P.stackTap(s, 0) === 'lift' && s.held === 0, 'lift the smallest');
ok(P.stackTap(s, 0) === 'return' && s.held === null, 'tapping the same peg puts it back');
P.stackTap(s, 0); P.stackTap(s, 2);           // 0 -> peg 2
P.stackTap(s, 0);                             // hold ring 1
ok(P.stackTap(s, 2) === 'refuse' && s.held === 1, 'a larger ring is refused and stays held');
ok(P.stackTap(s, 1) === 'drop', 'and goes on an empty peg');
function hanoi(k, from, to, via) {
  if (k === 0) return;
  hanoi(k - 1, from, via, to);
  assert.equal(P.stackTap(s, from), 'lift'); assert.equal(P.stackTap(s, to), 'drop');
  hanoi(k - 1, via, to, from);
}
// Put everything back on peg 0 (ring 1 first, or ring 0 blocks it), then
// solve to peg 2 by the book.
P.stackTap(s, 1); P.stackTap(s, 0); P.stackTap(s, 2); P.stackTap(s, 0);
ok(s.pegs[0].length === 4, 'reset to the start');
hanoi(4, 0, 2, 1);
P.refreshDoors(x);
ok(P.stackOn(s, 2) && x.open[2], 'four rings under the sun opens door 2');

// Room 3: a wrong pad clears the phrase, the greeting opens the door.
const sp = x.speech;
ok(P.speechTap(sp, 0) === 'ok' && P.speechTap(sp, 5) === 'wrong' && sp.input.length === 0, 'a wrong pad resets');
ok(P.speechTap(sp, 3) === 'wrong', 'the third word cannot start either phrase');
[0, 2, 3].forEach(p => assert.equal(P.speechTap(sp, p), 'ok'));
ok(P.speechTap(sp, 4) === 'greeting' && sp.last === 'greeting', 'the greeting completes');
P.refreshDoors(x);
ok(x.open[3] && !x.open[4], 'door 3 opens, the final door does not');

// Room 4: the three rooms re-set to the final configuration.
x.gaze.pos = [3, 3, 3];
for (let i = 0; i < 3; i++) while (x.gaze.pos[i] !== x.gaze.final[i]) P.gazeTap(x.gaze, i);
P.refreshDoors(x);
ok(!x.open[4], 'the eyes alone are not enough');
hanoi(4, 2, 1, 0);
P.refreshDoors(x);
ok(!x.open[4], 'the stack under the night eye is not enough either');
[1, 5, 3].forEach(p => assert.equal(P.speechTap(sp, p), 'ok'));
ok(P.speechTap(sp, 2) === 'farewell', 'the farewell completes');
P.refreshDoors(x);
ok(x.open[4], 'all three together open the final door');
ok(x.open.every(Boolean), 'every door in the exhibit is open');

console.log(`ALL ${n} CHECKS PASSED`);

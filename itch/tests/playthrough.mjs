// Plays the exported web build to its end, through real taps at phone size,
// and exits non zero if it cannot get there. The same walk as the prototype's
// mockups/elmorian-exhibit/playthrough.mjs: ftDebug is read to OBSERVE (where
// a thing is on screen, what the state is) and never to make progress.
//
//   node itch/tests/playthrough.mjs [builds/web]            # 390x844, mouse
//   node itch/tests/playthrough.mjs --touch                 # the same with touch events
//   node itch/tests/playthrough.mjs --landscape             # 844x390
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { open, waitFor } from './web_lib.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const args = process.argv.slice(2);
const dir = path.resolve(args.find(a => !a.startsWith('--')) || path.join(root, 'builds', 'web'));
const touch = args.includes('--touch');
const landscape = args.includes('--landscape');
const size = landscape ? { width: 844, height: 390 } : { width: 390, height: 844 };
const tag = landscape ? 'landscape' : (touch ? 'touch' : 'portrait');

let n = 0;
function ok(cond, msg) { assert.ok(cond, msg); n++; console.log('  ok  ' + msg); }

const g = await open(dir, { ...size, touch });
const { page, q } = g;
const state = () => q({ op: 'state' });
const settle = async () => {
  ok(await waitFor(async () => (await state()).arrived, 30000), 'the camera arrives');
  await new Promise(r => setTimeout(r, 150));
};
// A finger is down for a moment; a press and release in the same instant is
// not a tap anybody makes, and the page does not treat it as one either.
async function tap(x, y) {
  if (touch) {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
    await new Promise(r => setTimeout(r, 70));
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await cdp.detach();
  } else {
    await page.mouse.move(x, y);
    await page.mouse.down();
    await new Promise(r => setTimeout(r, 70));
    await page.mouse.up();
  }
  await new Promise(r => setTimeout(r, 120));
}
async function tapThing(kind, i, id) {
  const p = await q({ op: 'screenOf', kind, i: i ?? null, id: id ?? '' });
  assert.ok(p && !p.behind, `${kind} ${i ?? id} is on screen`);
  assert.ok(p.x >= 0 && p.x <= size.width && p.y >= 0 && p.y <= size.height, `${kind} ${i ?? id} is inside the viewport (${p.x.toFixed(0)}, ${p.y.toFixed(0)})`);
  await tap(p.x, p.y);
}
// A drag is a real gesture: down, a few moves, up. Turns the room camera.
async function drag(dx) {
  const x0 = size.width / 2, y0 = size.height * 0.45;
  if (touch) {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x0, y: y0 }] });
    for (let k = 1; k <= 6; k++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x0 + dx * k / 6, y: y0 }] });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await cdp.detach();
  } else {
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    for (let k = 1; k <= 6; k++) { await page.mouse.move(x0 + dx * k / 6, y0); await new Promise(r => setTimeout(r, 16)); }
    await page.mouse.up();
  }
  await settle();
}
// Turn until a thing is on screen, the way a player looks round for a door.
// Steps of about 24 degrees: a portrait phone sees 31, so a larger step can
// turn straight past the thing being looked for.
async function findOnScreen(kind, i) {
  for (let n = 0; n < 24; n++) {
    const p = await q({ op: 'screenOf', kind, i, id: '' });
    if (p && !p.behind && p.x > 30 && p.x < size.width - 30 && p.y > 80 && p.y < size.height - 110) return p;
    await drag(-80);
  }
  throw new Error(`could not bring ${kind} ${i} on screen by turning`);
}
async function walk(door) { await findOnScreen('doorway', door); await tapThing('doorway', door); await settle(); }
async function tapHud(name) {
  const h = await q({ op: 'hud' });
  const r = h[name];
  assert.ok(r && r.visible, `HUD control ${name} is visible`);
  await tap(r.x + r.w / 2, r.y + r.h / 2);
}
async function shot(name) { await page.screenshot({ path: path.join(root, 'docs', 'reference', `itch_web_${name}_${tag}.png`) }); }

try {
  await settle();
  ok((await state()).room === 0, 'starts in the forecourt');
  await tap(size.width / 2, size.height * 0.55);   // the first touch wakes the page, on the floor
  ok((await state()).room === 0 && !(await state()).card, 'a tap on nothing does nothing');
  await shot('forecourt');

  // through the arch
  await tapThing('doorway', 0); await settle();
  ok((await state()).room === 1, 'the arch leads into room 1');
  await shot('room1');

  // room 1: the eyes to the door mark, 3
  await tapThing('eye', 0); await settle();
  ok((await state()).station === 'gaze', 'a tap on a disc goes to the station');
  const s1 = await state();
  for (let i = 0; i < 3; i++) for (let k = (3 - s1.gaze[i] + 6) % 6; k > 0; k--) await tapThing('eye', i);
  await new Promise(r => setTimeout(r, 300));
  ok(JSON.stringify((await state()).gaze) === '[3,3,3]', 'the three eyes read 3, 3, 3');
  ok((await state()).open[1] === true, 'door 1 opens');
  await shot('gaze_solved');
  await tapHud('back'); await settle();
  ok((await state()).mode === 'room', 'Back leaves the station');
  await walk(1);
  ok((await state()).room === 2, 'the door of the gaze leads into room 2');

  // room 2: Hanoi, four rings, peg 0 to peg 2
  await tapThing('stack', 0); await settle();
  ok((await state()).station === 'stack', 'a tap on the stack goes to the station');
  const moves = [];
  (function hanoi(k, from, to, via) { if (!k) return; hanoi(k - 1, from, via, to); moves.push([from, to]); hanoi(k - 1, via, to, from); })(4, 0, 2, 1);
  for (const [from, to] of moves) { await tapThing('stack', from); await tapThing('stack', to); }
  await new Promise(r => setTimeout(r, 600));
  ok((await state()).pegs[2].length === 4, 'four rings stand under the sun');
  ok((await state()).open[2] === true, 'door 2 opens');
  await shot('stack_solved');
  await tapHud('back'); await settle();
  await walk(2);
  ok((await state()).room === 3, 'the door of the stack leads into room 3');

  // room 3: the greeting
  await tapThing('pad', 0); await settle();
  ok((await state()).station === 'speech', 'a tap on a pad goes to the station');
  for (const p of [0, 2, 3, 4]) await tapThing('pad', p);
  await new Promise(r => setTimeout(r, 300));
  ok((await state()).last === 'greeting' && (await state()).open[3] === true, 'the greeting opens door 3');
  await shot('speech_solved');
  await tapHud('back'); await settle();
  await walk(3);
  ok((await state()).room === 4, 'the door of the speech leads into room 4');

  // room 4: the stones, then back through the chips to re-set the three rooms
  await tapThing('stone', 0); await settle();
  ok((await state()).station === 'final' && (await state()).card, 'a seeing stone shows its label at the final station');
  await shot('final_stones');
  await tapHud('close');
  ok(!(await state()).card, 'Close keeps the camera on the stones');
  await tapHud('back'); await settle();

  await tapHud('chip_1'); await settle();
  ok((await state()).room === 1, 'the chip row jumps back to room 1');
  await tapThing('eye', 0); await settle();
  const s2 = await state();
  const final = [2, 4, 0];
  for (let i = 0; i < 3; i++) for (let k = (final[i] - s2.gaze[i] + 6) % 6; k > 0; k--) await tapThing('eye', i);
  await new Promise(r => setTimeout(r, 300));
  ok(JSON.stringify((await state()).gaze) === '[2,4,0]', 'the eyes are re-set for the ancestors');
  await tapHud('back'); await settle();

  await tapHud('chip_2'); await settle();
  await tapThing('stack', 1); await settle();
  moves.length = 0;
  (function hanoi(k, from, to, via) { if (!k) return; hanoi(k - 1, from, via, to); moves.push([from, to]); hanoi(k - 1, via, to, from); })(4, 2, 1, 0);
  for (const [from, to] of moves) { await tapThing('stack', from); await tapThing('stack', to); }
  await new Promise(r => setTimeout(r, 600));
  ok((await state()).pegs[1].length === 4, 'the stack stands under the night eye');
  await tapHud('back'); await settle();

  await tapHud('chip_3'); await settle();
  await tapThing('pad', 1); await settle();
  for (const p of [1, 5, 3, 2]) await tapThing('pad', p);
  await new Promise(r => setTimeout(r, 300));
  ok((await state()).last === 'farewell' && (await state()).open[4] === true, 'the farewell opens the ancestor door');
  await tapHud('back'); await settle();

  await tapHud('chip_4'); await settle();
  await shot('final_arranged');
  await walk(4);
  ok((await state()).room === 5, 'the door of the ancestor leads into the alcove');
  ok(await waitFor(async () => (await state()).card, 5000), 'the end card appears');
  await shot('end');

  // the save: the page reloaded comes back to the exhibit as it stands
  await page.reload();
  await page.waitForFunction(() => window.ftDebug && typeof window.ftDebug.query === 'function', null, { timeout: 240000 });
  await waitFor(async () => { const s = await state(); return s && s.arrived; }, 60000);
  const s3 = await state();
  ok(s3.open.every(Boolean) && s3.last === 'farewell' && s3.room === 4, 'a reload restores the exhibit, every door open, in room 4');

  const lit = await q({ op: 'lit' });
  ok(lit > 0.05, `the last frame is drawn (${(lit * 100).toFixed(0)}% lit)`);
  console.log(`ALL ${n} PLAYTHROUGH CHECKS PASSED (${tag})`);
} catch (e) {
  await shot('failed');
  console.error('FAILED after ' + n + ' checks: ' + e.message);
  console.error(g.log.slice(-15).join('\n'));
  process.exitCode = 1;
} finally {
  await g.close();
}

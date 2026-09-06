// Plays the exhibit to its end through the real input path, at phone size:
// taps where a player would tap, drags to turn, presses the same buttons.
// It reads window.ftDebug to OBSERVE (where is the door on screen, what does
// the puzzle hold) and never to make progress. Exits non zero if the ancestor
// door cannot be reached.
//
//   node mockups/elmorian-exhibit/playthrough.mjs [--landscape]
// Needs playwright (npm i playwright) and a Chromium; the sandbox has both.

import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const landscape = process.argv.includes('--landscape');
const W = landscape ? 844 : 390, H = landscape ? 390 : 844;
const exe = process.env.CHROMIUM || '/opt/pw-browsers/chromium';

const browser = await chromium.launch({ executablePath: exe, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, hasTouch: true, isMobile: true });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
await page.goto('file://' + path.join(here, 'index.html'));
// Wait on PROGRESS, not on a deadline. The shell is built synchronously from
// the text payload, so how long the page takes to be ready depends on the
// machine and on what else is running on it; a fixed pause passed on a quiet
// box and failed on a busy one, which reads as a broken game and is not one.
await page.waitForFunction(() => window.ftDebug && window.ftDebug.rig, null, { timeout: 120000 });
await page.waitForTimeout(400);

let checks = 0;
const ok = (c, m) => { assert.ok(c, m); checks++; console.log('  ok  ' + m); };
const state = () => page.evaluate(() => ({ open: ftDebug.exhibit.open.slice(), gaze: ftDebug.exhibit.gaze.pos.slice(), pegs: JSON.parse(JSON.stringify(ftDebug.exhibit.stack.pegs)), last: ftDebug.exhibit.speech.last, room: ftDebug.rig.room, mode: ftDebug.rig.mode, station: ftDebug.rig.station }));
const where = (kind, i) => page.evaluate(([k, i]) => ftDebug.screenOf(k, i), [kind, i]);
// Wait as a player does: until the camera has arrived, not for a fixed time.
const settle = async () => {
  await page.waitForTimeout(250);
  for (let i = 0; i < 24; i++) {
    const there = await page.evaluate(() => ftDebug.rig.queue.length === 0 && ftDebug.rig.target.distanceTo(ftDebug.rig.goal.target) < 0.03 && Math.abs(ftDebug.rig.yaw - ftDebug.rig.goal.yaw) < 0.01);
    if (there) return;
    await page.waitForTimeout(250);
  }
};
async function tapAt(x, y) { await page.touchscreen.tap(x, y); await settle(); }
async function tapThing(kind, i) {
  const p = await where(kind, i);
  assert.ok(p && p.z < 1 && p.x > 0 && p.x < W && p.y > 0 && p.y < H, `${kind} ${i} is on screen`);
  await tapAt(p.x, p.y);
}
async function drag(dx) {
  const x0 = W / 2, y0 = H * 0.45;
  // A drag has to be a real touch gesture, so it goes through CDP.
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x0, y: y0 }] });
  for (let k = 1; k <= 6; k++) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x0 + dx * k / 6, y: y0 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await cdp.detach();
  await settle();
}
// Turn until a thing is on screen, the way a player looks around for a door.
async function findOnScreen(kind, i) {
  // Steps of about 24 degrees: a portrait phone sees 31, so a larger step
  // can turn straight past the thing being looked for.
  for (let n = 0; n < 24; n++) {
    const p = await where(kind, i);
    if (p && p.z < 1 && p.x > 30 && p.x < W - 30 && p.y > 80 && p.y < H - 110) return p;
    await drag(-80);
  }
  throw new Error(`could not bring ${kind} ${i} on screen by turning`);
}
async function walk(door) { await findOnScreen('doorway', door); await tapThing('doorway', door); await page.waitForTimeout(1600); }
async function back() { await page.click('#back'); await settle(); }

// The forecourt, through the arch.
let s = await state(); ok(s.room === 0, 'starts in the forecourt');
await walk(0); s = await state(); ok(s.room === 1, 'the arch leads to room 1');

// Room 1: turn every eye to the door.
await findOnScreen('eye', 0); await tapThing('eye', 0);
s = await state(); ok(s.station === 'gaze', 'tapping an eye goes to the gaze station');
for (let i = 0; i < 3; i++) { while ((await state()).gaze[i] !== 3) await tapThing('eye', i); }
s = await state(); ok(s.open[1], 'three eyes on the door opens door 1');
await back(); await walk(1); s = await state(); ok(s.room === 2, 'door 1 leads to room 2');

// Room 2: the light stack under the sun, by the book.
await findOnScreen('stack', 0); await tapThing('stack', 0);
s = await state(); ok(s.station === 'stack', 'tapping a peg goes to the stack station');
async function hanoi(k, from, to, via) {
  if (!k) return;
  await hanoi(k - 1, from, via, to);
  await tapThing('stack', from); await tapThing('stack', to);
  await hanoi(k - 1, via, to, from);
}
await hanoi(4, 0, 2, 1);
s = await state(); ok(s.pegs[2].length === 4 && s.open[2], 'four rings under the sun opens door 2');
await back(); await walk(2); s = await state(); ok(s.room === 3, 'door 2 leads to room 3');

// Room 3: the greeting.
await findOnScreen('pad', 0); await tapThing('pad', 0);
s = await state(); ok(s.station === 'speech', 'tapping a pad goes to the speech station');
for (const p of [5]) await tapThing('pad', p);              // a wrong word first
s = await state(); ok(s.last === null, 'a wrong word does nothing');
for (const p of [0, 2, 3, 4]) await tapThing('pad', p);
s = await state(); ok(s.last === 'greeting' && s.open[3], 'the greeting opens door 3');
await back(); await walk(3); s = await state(); ok(s.room === 4, 'door 3 leads to room 4');

// Room 4: read the stones, find the ancestor door shut.
await findOnScreen('stone', 1); await tapThing('stone', 1);
s = await state(); ok(s.station === 'final', 'the seeing stones are a station');
ok(!(await page.isVisible('#card')) && await page.isVisible('#read'),
   'a tap on an exhibit item offers its label rather than opening it');
const readBox = await page.locator('#read').boundingBox();
const backBox = await page.locator('#back').boundingBox();
ok(readBox.y + readBox.height > H - 60, 'Read sits along the bottom edge, not over the item');
ok(Math.abs(readBox.x + readBox.width / 2 - W / 2) < 12, 'and centred across the screen');
ok(readBox.x > backBox.x + backBox.width, 'clear of Back beside it');
await page.click('#read'); await settle();
ok(await page.isVisible('#card'), 'and Read description opens it');
await page.click('#cardClose'); await settle();
await back(); await findOnScreen('door', 4); await tapThing('door', 4);
s = await state(); ok(s.room === 4 && !s.open[4], 'the ancestor door is shut');
ok(await page.isVisible('#card'), 'and says so');
await page.click('#cardClose'); await settle();

// Back through the house, setting it as the diagram asks.
await walk(3); s = await state(); ok(s.room === 3, 'door 3 leads back to room 3');
await findOnScreen('pad', 1); await tapThing('pad', 1);   // enters the station, says nothing
for (const p of [1, 5, 3, 2]) await tapThing('pad', p);
s = await state(); ok(s.last === 'farewell', 'the farewell is said');
await back(); await walk(2);
await findOnScreen('stack', 2); await tapThing('stack', 2);
await hanoi(4, 2, 1, 0);
s = await state(); ok(s.pegs[1].length === 4, 'the stack stands under the night eye');
await back(); await walk(1);
await findOnScreen('eye', 0); await tapThing('eye', 0);
for (let i = 0; i < 3; i++) { while ((await state()).gaze[i] !== [2, 4, 0][i]) await tapThing('eye', i); }
s = await state(); ok(s.open[4], 'the three rooms together open the ancestor door');
await back();

// To the ancestor, by the room chips this time, which are the other way in.
await page.click('#chips button:nth-child(5)'); await page.waitForTimeout(1600);
s = await state(); ok(s.room === 4, 'the chip for room 4 goes there');
await walk(4); await page.waitForTimeout(1800);
s = await state(); ok(s.room === 5, 'the open ancestor door leads to the alcove');
ok(await page.isVisible('#card') && (await page.textContent('#cardTitle')).includes('Ancestor'), 'the exhibit ends');
await page.screenshot({ path: path.join(here, '..', '..', 'docs', 'reference', `elmorian_end_${landscape ? 'landscape' : 'portrait'}.png`) });

ok(errors.length === 0, 'no page errors: ' + (errors.join(' | ') || 'none'));
console.log(`PLAYTHROUGH COMPLETE, ${checks} checks, ${W}x${H}`);
await browser.close();

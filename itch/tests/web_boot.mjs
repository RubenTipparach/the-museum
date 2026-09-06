// Boots an exported web build (scripts/verify-build.sh runs this): serves the
// directory given, opens it in headless Chromium, waits for the smoke marker,
// asks the game for its state and a lit fraction, and writes a frame to
// docs/reference/itch_web_boot.png. Exits non zero if any of that fails.
//
//   node itch/tests/web_boot.mjs builds/web
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { open, waitFor } from './web_lib.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const dir = path.resolve(process.argv[2] || path.join(root, 'builds', 'web'));
const t0 = Date.now();
const g = await open(dir);
try {
  const s = await g.q({ op: 'state' });
  if (!s || typeof s.room !== 'number') throw new Error('state query failed: ' + JSON.stringify(s));
  await waitFor(async () => (await g.q({ op: 'state' })).arrived, 20000);
  const lit = await g.q({ op: 'lit' });
  if (!(lit > 0.05)) throw new Error('the first frame is black: lit fraction ' + lit);
  await g.page.screenshot({ path: path.join(root, 'docs', 'reference', 'itch_web_boot.png') });
  const errors = g.log.filter(l => /error|PAGEERROR/i.test(l) && !/AudioContext|autoplay|ALSA/i.test(l));
  if (errors.length) throw new Error('errors in the console:\n' + errors.join('\n'));
  console.log(`web build boots: room ${s.room}, ${(lit * 100).toFixed(0)}% of the frame lit, ${((Date.now() - t0) / 1000).toFixed(1)} s to the first frame`);
} finally {
  await g.close();
}

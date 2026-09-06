// What both web harnesses need, once: a static server for an exported build,
// a headless Chromium that can run WebGL2 on a machine with no GPU, and the
// bridge to the game's ftDebug (src/debug_bridge.gd), which is observed and
// never driven. Nothing here advances the game; a harness taps where a
// player taps.
import { createServer } from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.wasm': 'application/wasm',
               '.pck': 'application/octet-stream', '.png': 'image/png', '.json': 'application/json' };

// CHROMIUM names the browser; else the one the Claude Code sandbox
// pre-installs (its Playwright browsers directory holds a plain chromium and
// none of the per version shells a bare launch looks for); else Playwright's
// own, which CI installs with `npx playwright install chromium`.
function chromiumPath() {
  if (process.env.CHROMIUM) return process.env.CHROMIUM;
  const sandbox = '/opt/pw-browsers/chromium';
  return fs.existsSync(sandbox) ? sandbox : undefined;
}

export function serve(dir) {
  const server = createServer((req, res) => {
    const file = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/\/$/, '/index.html'));
    if (!file.startsWith(dir) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve({ server, url: `http://127.0.0.1:${server.address().port}/` })));
}

export async function open(dir, { width = 390, height = 844, touch = false, dpr = 1 } = {}) {
  const { server, url } = await serve(dir);
  const browser = await chromium.launch({
    executablePath: chromiumPath(),
    args: ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
  });
  const context = await browser.newContext({ viewport: { width, height }, hasTouch: touch, isMobile: touch, deviceScaleFactor: dpr });
  const page = await context.newPage();
  const log = [];
  page.on('console', m => log.push(m.text()));
  page.on('pageerror', e => log.push('PAGEERROR ' + e.message));
  await page.goto(url);
  // Wait on PROGRESS, never on a stopwatch: the marker is printed at the end
  // of main.gd's _ready, which is the moment the game exists.
  await page.waitForFunction(() => window.ftDebug && typeof window.ftDebug.query === 'function', null, { timeout: 240000 });
  const ok = await waitFor(() => log.some(l => l.includes('MUSEUM_SMOKE_OK')), 30000);
  if (!ok) throw new Error('no smoke marker; console was:\n' + log.slice(-20).join('\n'));
  const q = (query) => page.evaluate(qq => { window.ftDebug.query(JSON.stringify(qq)); return window.ftDebugResult; }, query);
  return { browser, context, page, log, q, close: async () => { await browser.close(); server.close(); } };
}

export async function waitFor(fn, ms = 20000, every = 100) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await fn()) return true;
    await new Promise(r => setTimeout(r, every));
  }
  return false;
}

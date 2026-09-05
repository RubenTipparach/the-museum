// Pre-render the exhibit's drawn art to PNGs for the itch build.
//
// art.js draws every plaque, diagram, eye disc, pad and glyph on a canvas, and
// is the ONE implementation of that art (CLAUDE.md 4.1). The web prototype
// draws it at load; a Godot build needs files. This runs the same code in a
// headless browser and writes what it draws, so the two builds show the same
// pictures and nothing is drawn twice. Output is committed (CLAUDE.md 5).
//
//   node tools/render_art.mjs      -> assets/art/*.png

import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'assets', 'art');
fs.mkdirSync(out, { recursive: true });
const src = ['puzzles.js', 'art.js'].map(f => fs.readFileSync(path.join(root, 'mockups/elmorian-exhibit', f), 'utf8')).join('\n');
const lore = JSON.parse(fs.readFileSync(path.join(root, 'data/lore/elmorian.json'), 'utf8'));

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' });
const page = await browser.newPage();
await page.setContent('<html><body></body></html>');
await page.addScriptTag({ content: src });

// Each entry: name, and a function body run in the page returning a canvas.
const jobs = [];
for (const [id, def] of Object.entries(lore.plaques)) {
  jobs.push([`plaque_${id}`, `
    var def = ${JSON.stringify(def)};
    return Art.plaque(1024, 732, function (g) {
      if (def.art === 'diagramSpeech') Art.diagramSpeech(g, 1024, 732, Puzzles.makeSpeech().greeting);
      else if (def.art === 'diagramFinal') { var gz = Puzzles.makeGaze(); Art.diagramFinal(g, 1024, 732, gz.final, Puzzles.makeSpeech().farewell); }
      else Art[def.art](g, 1024, 732);
    }, '#8c8470', ${id.length * 7});`]);
}
jobs.push(['eye_disc', 'return Art.eyeDisc(512);']);
for (let i = 0; i < 6; i++) {
  jobs.push([`pad_${i}`, `return Art.pad(256, ${i}, false);`]);
  jobs.push([`pad_${i}_lit`, `return Art.pad(256, ${i}, true);`]);
  jobs.push([`word_${i}`, `var c = Art.canvas(128, 128), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = '#d8d3c5'; g.lineWidth = 5; g.lineCap = 'round'; Art.word(g, 64, 64, 100, ${i}); return c;`]);
  jobs.push([`numeral_${i}`, `var c = Art.canvas(128, 128), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = '#d8d3c5'; g.lineWidth = 5; g.lineCap = 'round'; Art.numeral(g, 64, 64, 90, ${i}); return c;`]);
}
jobs.push(['sign_hall', `return Art.sign(1024, 400, ${JSON.stringify([lore.hall, 'The Elmorians'])});`]);
jobs.push(['glyph_sun', `var c = Art.canvas(128, 128), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = 'rgba(28,22,12,0.85)'; g.lineWidth = 5; Art.word(g, 64, 64, 110, 0); return c;`]);
jobs.push(['glyph_eye', `var c = Art.canvas(128, 128), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = 'rgba(28,22,12,0.85)'; g.lineWidth = 5; Art.word(g, 64, 64, 110, 2); return c;`]);

for (const [name, body] of jobs) {
  const dataUrl = await page.evaluate(new Function(body + '\n').toString().replace(/^function anonymous\(\n\) \{/, '(function () {').replace(/\}$/, '})().toDataURL("image/png")'));
  fs.writeFileSync(path.join(out, name + '.png'), Buffer.from(dataUrl.split(',')[1], 'base64'));
}
await browser.close();
console.log(`wrote ${jobs.length} PNGs to assets/art/`);

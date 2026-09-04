// Every picture in the exhibit is drawn here, on a 2D canvas, at load. This is
// a PROTOTYPE: the game's assets are authored files (CLAUDE.md 5), and what
// is settled here (the figure, the glyphs, the diagrams) becomes those files.
// Nothing here is random noise dressed as art: every diagram is a composition
// that says something the puzzle needs said.

(function (root) {
  'use strict';

  // ---- seeded speckle, for stone -------------------------------------------
  function rng(seed) {
    var s = seed >>> 0 || 1;
    return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  }
  function canvas(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

  // A slab of stone: base colour, two grains of speckle, a faint block pattern.
  function stone(size, base, seed, blocks) {
    var c = canvas(size, size), g = c.getContext('2d'), r = rng(seed || 7);
    g.fillStyle = base; g.fillRect(0, 0, size, size);
    for (var i = 0; i < size * 14; i++) {
      var v = (r() - 0.5) * 0.22;
      g.fillStyle = 'rgba(' + (v > 0 ? '255,250,235,' : '0,0,0,') + Math.abs(v).toFixed(3) + ')';
      var w = 1 + r() * 3;
      g.fillRect(r() * size, r() * size, w, w * (0.5 + r()));
    }
    if (blocks) {
      g.strokeStyle = 'rgba(0,0,0,0.28)'; g.lineWidth = Math.max(1, size / 128);
      var rows = 6, bh = size / rows;
      for (var y = 0; y < rows; y++) {
        var yy = y * bh + (r() - 0.5) * 2;
        g.beginPath(); g.moveTo(0, yy); g.lineTo(size, yy); g.stroke();
        var off = (y % 2) * bh * 0.9, x = -off;
        while (x < size) { x += bh * (1.4 + r() * 1.2); g.beginPath(); g.moveTo(x, yy); g.lineTo(x + (r() - 0.5) * 3, yy + bh); g.stroke(); }
      }
    }
    return c;
  }

  // ---- the engraved style ----------------------------------------------------
  // Everything carved into a plaque is drawn twice: a pale line offset down and
  // right (the lit edge of a cut), then the dark cut itself. On stone it reads
  // as relief rather than as ink, and it costs nothing.
  function engrave(g, fn, scale) {
    g.save(); g.translate(scale * 0.35, scale * 0.35); g.strokeStyle = 'rgba(255,245,220,0.35)'; g.fillStyle = 'rgba(255,245,220,0.35)'; fn(g); g.restore();
    g.save(); g.strokeStyle = 'rgba(28,22,12,0.85)'; g.fillStyle = 'rgba(28,22,12,0.85)'; fn(g); g.restore();
  }

  // A plaque: stone with a border and an engraved drawing.
  function plaque(w, h, draw, base, seed) {
    var c = canvas(w, h), g = c.getContext('2d');
    g.drawImage(stone(Math.max(w, h), base || '#8f8672', seed || 11), 0, 0, w, h);
    engrave(g, function (q) {
      q.lineWidth = 3; q.strokeRect(w * 0.04, h * 0.04, w * 0.92, h * 0.92);
    }, 2);
    engrave(g, function (q) { q.lineWidth = 2.2; q.lineCap = 'round'; q.lineJoin = 'round'; draw(q); }, 2);
    return c;
  }

  // ---- the Elmorian ------------------------------------------------------------
  // Green, three eyes of three sizes, one tentacle from the crown, no nose and
  // no mouth. Size s is the head height. Pose 'front' faces the viewer,
  // 'side' shows the tentacle's full curve, 'gaze' turns all three eyes to a
  // direction (angle in radians, for the room 1 diagram).
  function elmorian(g, cx, cy, s, opt) {
    opt = opt || {};
    var fill = opt.fill !== false;
    g.save(); g.translate(cx, cy);
    // tentacle: from the crown, back and down, tapering
    g.lineWidth = s * 0.16; g.lineCap = 'round';
    g.beginPath(); g.moveTo(s * 0.05, -s * 0.48);
    g.bezierCurveTo(s * 0.5, -s * 0.9, s * 0.95, -s * 0.4, s * 0.75, s * 0.35);
    g.stroke();
    g.lineWidth = s * 0.09;
    g.beginPath(); g.moveTo(s * 0.75, s * 0.35); g.bezierCurveTo(s * 0.7, s * 0.6, s * 0.55, s * 0.7, s * 0.62, s * 0.9); g.stroke();
    // head: tall rounded, a little wider at the brow
    g.beginPath();
    g.moveTo(0, -s * 0.5);
    g.bezierCurveTo(s * 0.42, -s * 0.5, s * 0.42, s * 0.1, s * 0.28, s * 0.42);
    g.bezierCurveTo(s * 0.18, s * 0.58, -s * 0.18, s * 0.58, -s * 0.28, s * 0.42);
    g.bezierCurveTo(-s * 0.42, s * 0.1, -s * 0.42, -s * 0.5, 0, -s * 0.5);
    g.closePath();
    if (fill) { g.save(); g.fillStyle = opt.skin || '#5f8c4a'; g.fill(); g.restore(); }
    g.lineWidth = s * 0.05; g.stroke();
    // shoulders and robe
    g.lineWidth = s * 0.05;
    g.beginPath(); g.moveTo(-s * 0.22, s * 0.55); g.lineTo(-s * 0.55, s * 0.75); g.lineTo(-s * 0.62, s * 1.4);
    g.moveTo(s * 0.22, s * 0.55); g.lineTo(s * 0.55, s * 0.75); g.lineTo(s * 0.62, s * 1.4); g.stroke();
    // the three eyes: large low left, medium low right, small high centre.
    var eyes = [[-s * 0.16, s * 0.05, s * 0.15], [s * 0.17, s * 0.07, s * 0.10], [s * 0.0, -s * 0.24, s * 0.06]];
    var a = opt.gaze;
    for (var i = 0; i < 3; i++) {
      var e = eyes[i];
      g.beginPath(); g.ellipse(e[0], e[1], e[2], e[2] * 0.82, 0, 0, Math.PI * 2);
      if (fill) { g.save(); g.fillStyle = '#e9e3b8'; g.fill(); g.restore(); }
      g.lineWidth = s * 0.035; g.stroke();
      var px = e[0], py = e[1];
      if (a !== undefined) { px += Math.cos(a) * e[2] * 0.45; py -= Math.sin(a) * e[2] * 0.45; }
      g.beginPath(); g.arc(px, py, e[2] * 0.42, 0, Math.PI * 2); g.fill();
    }
    g.restore();
  }

  // ---- numerals: marks on a stem, base six (WORLD.md 2) -------------------------
  // n from 0 to 35. A stem carries 0 to 5 marks; a second stem to the right is
  // the sixes place, and it is drawn only when needed.
  function numeral(g, x, y, h, n) {
    var units = n % 6, sixes = Math.floor(n / 6);
    var stems = sixes ? 2 : 1, gap = h * 0.55, x0 = x - (stems - 1) * gap / 2;
    g.lineWidth = Math.max(2, h * 0.09); g.lineCap = 'round';
    function stem(sx, marks) {
      g.beginPath(); g.moveTo(sx, y - h / 2); g.lineTo(sx, y + h / 2); g.stroke();
      for (var i = 0; i < marks; i++) {
        var my = y + h / 2 - h * 0.16 - i * h * 0.17;
        g.beginPath(); g.arc(sx + h * 0.17, my, h * 0.06, 0, Math.PI * 2); g.fill();
      }
    }
    if (sixes) { stem(x0 + gap, sixes); }
    stem(x0, units);
  }

  // ---- the six word glyphs: what the pads say ------------------------------------
  // light, stone, eye, touch, door, dark. Each is a mark a tentacle can read.
  function word(g, x, y, s, id) {
    g.save(); g.translate(x, y); g.lineWidth = Math.max(2, s * 0.09); g.lineCap = 'round'; g.lineJoin = 'round';
    switch (id) {
      case 0: // light: a point and six rays
        g.beginPath(); g.arc(0, 0, s * 0.12, 0, Math.PI * 2); g.fill();
        for (var i = 0; i < 6; i++) { var a = i * Math.PI / 3; g.beginPath(); g.moveTo(Math.cos(a) * s * 0.22, Math.sin(a) * s * 0.22); g.lineTo(Math.cos(a) * s * 0.45, Math.sin(a) * s * 0.45); g.stroke(); }
        break;
      case 1: // stone: a block with a grain line
        g.strokeRect(-s * 0.36, -s * 0.26, s * 0.72, s * 0.52);
        g.beginPath(); g.moveTo(-s * 0.36, 0); g.lineTo(s * 0.36, 0); g.stroke();
        break;
      case 2: // eye: the almond with the pupil
        g.beginPath(); g.moveTo(-s * 0.42, 0); g.quadraticCurveTo(0, -s * 0.42, s * 0.42, 0); g.quadraticCurveTo(0, s * 0.42, -s * 0.42, 0); g.stroke();
        g.beginPath(); g.arc(0, 0, s * 0.12, 0, Math.PI * 2); g.fill();
        break;
      case 3: // touch: two tentacle tips meeting
        g.beginPath(); g.moveTo(-s * 0.45, -s * 0.35); g.quadraticCurveTo(-s * 0.05, -s * 0.35, -s * 0.03, 0); g.stroke();
        g.beginPath(); g.moveTo(s * 0.45, s * 0.35); g.quadraticCurveTo(s * 0.05, s * 0.35, s * 0.03, 0); g.stroke();
        g.beginPath(); g.arc(0, 0, s * 0.07, 0, Math.PI * 2); g.fill();
        break;
      case 4: // door: an arch
        g.beginPath(); g.moveTo(-s * 0.3, s * 0.4); g.lineTo(-s * 0.3, -s * 0.05); g.arc(0, -s * 0.05, s * 0.3, Math.PI, 0); g.lineTo(s * 0.3, s * 0.4); g.stroke();
        break;
      case 5: // dark: a filled circle with nothing around it
        g.beginPath(); g.arc(0, 0, s * 0.3, 0, Math.PI * 2); g.fill();
        break;
    }
    g.restore();
  }

  // Six positions round a ring, the way room 1 counts them: 0 to the right and
  // then anticlockwise, as an eye turning.
  function posAngle(k) { return k * Math.PI / 3; }

  // ---- the diagrams ---------------------------------------------------------------
  // Room 1. An Elmorian turns all three eyes to a door. Round it, the six
  // marks of a dial, with the door glyph at mark 3. Says: turn each eye to
  // three. Does not say which disc is which: the sizes say that.
  function diagramGaze(g, w, h) {
    var cx = w * 0.36, cy = h * 0.5, R = h * 0.4;
    g.lineWidth = 2;
    g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.stroke();
    for (var k = 0; k < 6; k++) {
      var a = posAngle(k), tx = cx + Math.cos(a) * (R + h * 0.1), ty = cy - Math.sin(a) * (R + h * 0.1);
      numeral(g, tx, ty, h * 0.11, k);
      g.beginPath(); g.moveTo(cx + Math.cos(a) * R * 0.92, cy - Math.sin(a) * R * 0.92); g.lineTo(cx + Math.cos(a) * R, cy - Math.sin(a) * R); g.stroke();
    }
    elmorian(g, cx, cy - h * 0.02, h * 0.34, { gaze: posAngle(3), fill: false });
    // the door glyph beyond mark 3, and a long arrow from the eyes to it
    word(g, cx - R - h * 0.3, cy, h * 0.26, 4);
    g.setLineDash([h * 0.02, h * 0.03]); g.beginPath(); g.moveTo(cx - h * 0.12, cy); g.lineTo(cx - R - h * 0.16, cy); g.stroke(); g.setLineDash([]);
    // right column: the three disc sizes with the same mark beside each
    var xr = w * 0.8;
    [0.13, 0.09, 0.06].forEach(function (r, i) {
      var y = h * (0.26 + i * 0.24);
      g.beginPath(); g.arc(xr, y, h * r, 0, Math.PI * 2); g.stroke();
      g.beginPath(); g.arc(xr - h * r * 0.5, y, h * r * 0.3, 0, Math.PI * 2); g.fill();
      numeral(g, xr + h * 0.24, y, h * 0.1, 3);
    });
  }

  // Room 2. Three pegs; the sun over the right one, the night eye over the
  // middle. Rings on the right peg in size order, and a crossed image of a
  // small ring under a large one. Says: everything under the sun, small on
  // large, never the other way.
  function diagramStack(g, w, h) {
    var base = h * 0.78, pegX = [w * 0.2, w * 0.5, w * 0.8];
    g.lineWidth = 3;
    g.beginPath(); g.moveTo(w * 0.08, base); g.lineTo(w * 0.92, base); g.stroke();
    pegX.forEach(function (x) { g.beginPath(); g.moveTo(x, base); g.lineTo(x, base - h * 0.34); g.stroke(); });
    word(g, pegX[2], h * 0.18, h * 0.22, 0);            // sun over the right peg
    word(g, pegX[1], h * 0.18, h * 0.18, 2);            // the eye over the middle
    [4, 3, 2, 1].forEach(function (k, i) {             // the stack, large at the bottom
      var y = base - h * 0.05 - i * h * 0.07, hw = w * 0.03 * k + w * 0.02;
      g.beginPath(); g.ellipse(pegX[2], y, hw, h * 0.03, 0, 0, Math.PI * 2); g.stroke();
    });
    // the forbidden move, crossed out, under the left peg
    var fx = pegX[0], fy = base - h * 0.12;
    g.beginPath(); g.ellipse(fx, fy + h * 0.05, w * 0.04, h * 0.025, 0, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.ellipse(fx, fy - h * 0.03, w * 0.11, h * 0.03, 0, 0, Math.PI * 2); g.stroke();
    g.lineWidth = 3.5; g.beginPath(); g.moveTo(fx - w * 0.13, fy - h * 0.14); g.lineTo(fx + w * 0.13, fy + h * 0.12); g.stroke();
    g.beginPath(); g.moveTo(fx + w * 0.13, fy - h * 0.14); g.lineTo(fx - w * 0.13, fy + h * 0.12); g.stroke();
  }

  // Room 3. The greeting, written the way the world writes: columns read top
  // to bottom, right to left. Four glyphs in two columns of two, numbered by
  // the marks beside them so the order can be checked against room 1's dial.
  function diagramSpeech(g, w, h, phrase) {
    var cols = 2, rows = 2, gx = w * 0.26, gy = h * 0.36, x0 = w * 0.66, y0 = h * 0.3;
    for (var i = 0; i < phrase.length; i++) {
      var c = Math.floor(i / rows), r = i % rows, x = x0 - c * gx, y = y0 + r * gy;
      word(g, x, y, h * 0.26, phrase[i]);
      numeral(g, x + w * 0.1, y, h * 0.1, i);
    }
    // the two tentacle tips meeting, framing the phrase: this is speech
    g.lineWidth = 3;
    g.beginPath(); g.moveTo(w * 0.06, h * 0.9); g.quadraticCurveTo(w * 0.2, h * 0.55, w * 0.18, h * 0.12); g.stroke();
    g.beginPath(); g.moveTo(w * 0.94, h * 0.9); g.quadraticCurveTo(w * 0.8, h * 0.55, w * 0.82, h * 0.12); g.stroke();
    g.lineWidth = 2; g.setLineDash([4, 6]); g.beginPath(); g.moveTo(w * 0.18, h * 0.12); g.lineTo(w * 0.82, h * 0.12); g.stroke(); g.setLineDash([]);
  }

  // Room 4. The sixfold gaze: two Elmorians meet, tentacles touching, and
  // between them the three settings the rooms behind must hold. Eyes at the
  // marks 2, 4, 0; the stack under the night eye; the farewell phrase.
  function diagramFinal(g, w, h, gaze, farewell) {
    elmorian(g, w * 0.12, h * 0.42, h * 0.3, { fill: false });
    g.save(); g.translate(w, 0); g.scale(-1, 1); elmorian(g, w * 0.12, h * 0.42, h * 0.3, { fill: false }); g.restore();
    g.lineWidth = 2;
    // the three eye discs and their marks
    var xs = [w * 0.34, w * 0.5, w * 0.66], rs = [0.09, 0.065, 0.045];
    for (var i = 0; i < 3; i++) {
      g.beginPath(); g.arc(xs[i], h * 0.26, h * rs[i], 0, Math.PI * 2); g.stroke();
      var a = posAngle(gaze[i]);
      g.beginPath(); g.arc(xs[i] + Math.cos(a) * h * rs[i] * 0.5, h * 0.26 - Math.sin(a) * h * rs[i] * 0.5, h * rs[i] * 0.3, 0, Math.PI * 2); g.fill();
      numeral(g, xs[i], h * 0.47, h * 0.1, gaze[i]);
    }
    // the stack under the night eye, three pegs shown so the middle is clear
    var base = h * 0.8, px = [w * 0.36, w * 0.5, w * 0.64];
    g.beginPath(); g.moveTo(w * 0.3, base); g.lineTo(w * 0.7, base); g.stroke();
    px.forEach(function (x) { g.beginPath(); g.moveTo(x, base); g.lineTo(x, base - h * 0.2); g.stroke(); });
    word(g, px[1], base - h * 0.28, h * 0.12, 2);
    [4, 3, 2, 1].forEach(function (k, j) { g.beginPath(); g.ellipse(px[1], base - h * 0.03 - j * h * 0.04, w * 0.012 * k + w * 0.01, h * 0.018, 0, 0, Math.PI * 2); g.stroke(); });
    // the farewell, written in columns, in the lower corners
    for (var k = 0; k < farewell.length; k++) {
      var c = Math.floor(k / 2), r = k % 2;
      var x = c === 0 ? w * 0.9 : w * 0.1, y = h * 0.62 + r * h * 0.2;
      word(g, x, y, h * 0.14, farewell[k]);
      numeral(g, x + (c === 0 ? -w * 0.06 : w * 0.06), y, h * 0.07, k);
    }
  }

  // ---- illustrations for the lore plaques ------------------------------------------
  function illusPortrait(g, w, h) { elmorian(g, w * 0.5, h * 0.42, h * 0.42, {}); }
  function illusCliff(g, w, h) {
    // a cliff face with cut houses, and light stacks on its ledges
    g.lineWidth = 3; g.beginPath(); g.moveTo(w * 0.1, h * 0.9); g.lineTo(w * 0.22, h * 0.3); g.lineTo(w * 0.4, h * 0.2); g.lineTo(w * 0.55, h * 0.45); g.lineTo(w * 0.7, h * 0.35); g.lineTo(w * 0.9, h * 0.9); g.stroke();
    [[0.28, 0.62], [0.45, 0.5], [0.6, 0.66], [0.72, 0.55]].forEach(function (p) {
      var x = w * p[0], y = h * p[1];
      g.beginPath(); g.moveTo(x - w * 0.04, y); g.lineTo(x - w * 0.04, y - h * 0.08); g.arc(x, y - h * 0.08, w * 0.04, Math.PI, 0); g.lineTo(x + w * 0.04, y); g.stroke();
    });
    [[0.2, 0.9], [0.5, 0.9], [0.82, 0.9]].forEach(function (p) {
      for (var i = 0; i < 4; i++) g.beginPath(), g.ellipse(w * p[0], h * p[1] - i * h * 0.05, w * 0.05 - i * w * 0.009, h * 0.02, 0, 0, Math.PI * 2), g.stroke();
    });
    word(g, w * 0.85, h * 0.18, h * 0.2, 0);
  }
  function illusTouch(g, w, h) {
    elmorian(g, w * 0.28, h * 0.45, h * 0.36, { fill: false });
    g.save(); g.translate(w, 0); g.scale(-1, 1); elmorian(g, w * 0.28, h * 0.45, h * 0.36, { fill: false }); g.restore();
    g.lineWidth = 2; g.setLineDash([3, 6]);
    g.beginPath(); g.moveTo(w * 0.4, h * 0.45); g.lineTo(w * 0.6, h * 0.45); g.stroke(); g.setLineDash([]);
    numeral(g, w * 0.5, h * 0.85, h * 0.14, 6);
  }
  function illusAncestors(g, w, h) {
    // three figures, the last of them gone to stone: drawn as a block
    elmorian(g, w * 0.2, h * 0.45, h * 0.3, { fill: false });
    elmorian(g, w * 0.5, h * 0.45, h * 0.3, { fill: false, skin: '#777' });
    g.lineWidth = 3; g.strokeRect(w * 0.7, h * 0.22, w * 0.2, h * 0.62);
    g.beginPath(); g.arc(w * 0.8, h * 0.45, h * 0.03, 0, Math.PI * 2); g.fill();
    word(g, w * 0.8, h * 0.12, h * 0.14, 5);
  }
  function illusDrink(g, w, h) {
    word(g, w * 0.5, h * 0.16, h * 0.28, 0);
    elmorian(g, w * 0.5, h * 0.58, h * 0.32, { fill: false });
    g.lineWidth = 2;
    for (var i = -2; i <= 2; i++) { g.beginPath(); g.moveTo(w * 0.5 + i * w * 0.05, h * 0.3); g.lineTo(w * 0.5 + i * w * 0.08, h * 0.45); g.stroke(); }
  }

  // ---- textures for the puzzle parts ----------------------------------------------------
  // An eye disc: pale sclera, a green iris, and the pupil off centre to the
  // right, so turning the disc turns where it looks.
  function eyeDisc(size) {
    var c = canvas(size, size), g = c.getContext('2d'), r = size / 2;
    g.fillStyle = '#e6e0b6'; g.beginPath(); g.arc(r, r, r, 0, Math.PI * 2); g.fill();
    g.drawImage(stone(size, 'rgba(0,0,0,0)', 5), 0, 0);
    g.fillStyle = '#4d7a3c'; g.beginPath(); g.arc(r, r, r * 0.66, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#2b4a22'; g.beginPath(); g.arc(r, r, r * 0.66, 0, Math.PI * 2); g.lineWidth = size * 0.02; g.strokeStyle = '#1e2d18'; g.stroke();
    g.fillStyle = '#0d120b'; g.beginPath(); g.arc(r + r * 0.34, r, r * 0.24, 0, Math.PI * 2); g.fill();
    g.fillStyle = 'rgba(255,255,240,0.5)'; g.beginPath(); g.arc(r + r * 0.28, r - r * 0.08, r * 0.06, 0, Math.PI * 2); g.fill();
    return c;
  }
  // A pad: a rounded stone with a word glyph cut into it.
  function pad(size, id, lit) {
    var c = canvas(size, size), g = c.getContext('2d');
    g.drawImage(stone(size, lit ? '#b8b07c' : '#6f6a58', 20 + id), 0, 0);
    engrave(g, function (q) { q.lineWidth = size * 0.04; word(q, size / 2, size / 2, size * 0.7, id); }, 2);
    return c;
  }
  // A seeing stone in room 4: a round face reporting one room's state.
  function seeingStone(size, draw) {
    var c = canvas(size, size), g = c.getContext('2d');
    g.fillStyle = '#26302a'; g.beginPath(); g.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2); g.fill();
    g.strokeStyle = '#9fb59a'; g.lineWidth = size * 0.03; g.beginPath(); g.arc(size / 2, size / 2, size * 0.45, 0, Math.PI * 2); g.stroke();
    g.strokeStyle = '#cfe2c2'; g.fillStyle = '#cfe2c2'; g.lineWidth = size * 0.025; g.lineCap = 'round';
    draw(g, size);
    return c;
  }
  // A label: the museum's own typeface over stone, for the arch and the doors.
  function sign(w, h, lines, base) {
    var c = canvas(w, h), g = c.getContext('2d');
    g.drawImage(stone(Math.max(w, h), base || '#6c6559', 31), 0, 0, w, h);
    engrave(g, function (q) {
      q.textAlign = 'center'; q.textBaseline = 'middle';
      lines.forEach(function (l, i) { q.font = (i ? '500 ' : '600 ') + Math.round(h * (i ? 0.22 : 0.34)) + 'px Georgia, serif'; q.fillText(l, w / 2, h * (lines.length === 1 ? 0.5 : 0.36 + i * 0.36)); });
    }, 2);
    return c;
  }

  root.Art = { stone: stone, plaque: plaque, elmorian: elmorian, numeral: numeral, word: word, posAngle: posAngle,
               diagramGaze: diagramGaze, diagramStack: diagramStack, diagramSpeech: diagramSpeech, diagramFinal: diagramFinal,
               illusPortrait: illusPortrait, illusCliff: illusCliff, illusTouch: illusTouch, illusAncestors: illusAncestors, illusDrink: illusDrink,
               eyeDisc: eyeDisc, pad: pad, seeingStone: seeingStone, sign: sign, canvas: canvas };
})(window);

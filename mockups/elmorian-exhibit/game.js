// The Elmorian exhibit: a point and click walk through four rooms, on a phone.
// Drag to look, pinch to zoom, tap to touch. Every rule lives in puzzles.js;
// this file draws, eases, and asks.

(function () {
  'use strict';

  // ---- tuning: the numbers the game will hold in data/tuning.json --------------
  var T = {
    fov: 62, near: 0.05, far: 60,
    easeK: 5.5,               // camera ease, 1 - exp(-k dt)
    orbitSens: 0.0052, pitchMin: -0.35, pitchMax: 0.62,
    distMin: 2.0, distMax: 3.4,
    inspectNudge: 0.22,       // radians of drag allowed at an anchor
    tapMs: 450, tapPx: 9,
    wallH: 4, wallT: 0.4, doorW: 1.8, doorH: 2.7,
    ringHover: 2.05
  };

  var P = window.Puzzles, A = window.Art, L = window.LORE;
  var V3 = function (x, y, z) { return new THREE.Vector3(x, y, z); };
  var PI = Math.PI;

  // ---- renderer, scene, camera -------------------------------------------------
  var canvasEl = document.getElementById('view');
  var renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;

  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x04060a);
  scene.fog = new THREE.FogExp2(0x05070a, 0.055);
  var camera = new THREE.PerspectiveCamera(T.fov, 1, T.near, T.far);

  // A fixed pool of lights that follows the room the player is in, so the
  // shader never recompiles for a new light count and a phone never pays for
  // lights it cannot see: one room light, and a track head on every plaque
  // and station, which is what the owner asked for and what a museum does.
  var hemi = new THREE.HemisphereLight(0x243228, 0x0a0805, 0.22); scene.add(hemi);
  var lampA = new THREE.PointLight(0xffd7a3, 10, 11, 2); scene.add(lampA);
  var SPOTS = 5, spots = [];
  for (var si = 0; si < SPOTS; si++) { var sp = new THREE.SpotLight(0xfff0d0, 0, 12, 0.5, 0.6, 1.4); scene.add(sp); scene.add(sp.target); spots.push(sp); }
  // Two more for the door lamps: a room has at most two doors, and a small
  // coloured wash on the jamb is what makes the state read from across it.
  var doorLights = [new THREE.PointLight(0x000000, 0, 1.9, 2), new THREE.PointLight(0x000000, 0, 1.9, 2)];
  doorLights.forEach(function (l) { scene.add(l); });
  var LAY = window.LAYOUT, TEX = window.TEXTURES;

  // ---- textures and materials ------------------------------------------------------
  function tex(c, repeat) {
    var t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
    t.anisotropy = 4; return t;
  }
  var stoneWall = A.stone(256, '#5e5a50', 3, true), stoneFloor = A.stone(256, '#36332d', 9, false), stoneDark = A.stone(256, '#3d3a34', 17, false);
  function stoneMat(c, rx, ry, extra) {
    var m = new THREE.MeshStandardMaterial({ map: tex(c, [rx, ry]), roughness: 0.92, metalness: 0.02 });
    if (extra) Object.assign(m, extra); return m;
  }
  var plaqueMats = {};
  var roleMats = {};
  function roleMat(name) {
    if (roleMats[name]) return roleMats[name];
    var t = TEX[name] || {}, m = new THREE.MeshStandardMaterial({ roughness: 0.9, metalness: name.indexOf('metal') >= 0 ? 0.6 : 0.0 });
    // flipY off: these go on the shell, whose glTF UVs are already flipped.
    function load(uri, srgb) { var im = new Image(); var tx = new THREE.Texture(im); tx.flipY = false; im.onload = function () { tx.needsUpdate = true; }; im.src = uri; tx.wrapS = tx.wrapT = THREE.RepeatWrapping; if (srgb) tx.colorSpace = THREE.SRGBColorSpace; tx.anisotropy = 4; return tx; }
    if (t.albedo) m.map = load(t.albedo, true); else m.color.setHex({ mat_void_black: 0x030303, mat_lamp: 0xfff2d0, mat_plaque: 0x8c8470, mat_sign_hall: 0x8c8470, mat_belt: 0x6a1418, mat_extinguisher: 0xb01008 }[name] || 0x777777);
    if (t.normal) { m.normalMap = load(t.normal, false); m.normalScale.set(0.8, 0.8); }
    if (t.rough) m.roughnessMap = load(t.rough, false);
    if (name === 'mat_leaf') { m.transparent = false; m.alphaTest = 0.5; m.side = THREE.DoubleSide; }
    if (name === 'mat_lamp') { m.emissive.setHex(0xffe0a0); m.emissiveIntensity = 2.5; }
    if (name === 'mat_sign_exit') { m.emissive.setHex(0x20c050); m.emissiveIntensity = 0.7; if (m.map) m.emissiveMap = m.map; }
    if (name === 'mat_extinguisher') { m.color.setHex(0xb01008); m.roughness = 0.45; }
    roleMats[name] = m; return m;
  }

  // ---- the shell: assets/exhibit/elmorian.glb, built by Blender from the layout ----
  var solids = [];    // what a tap ray can stop on
  var shellByName = {};
  var plaqueMeshes = {};
  (function loadShell() {
    var bytes = Uint8Array.from(atob(window.SHELL_GLB), function (c) { return c.charCodeAt(0); });
    var loader = new window.GLTFLoaderModule.GLTFLoader();
    loader.parse(bytes.buffer, '', function (gltf) {
      gltf.scene.traverse(function (o) {
        if (!o.isMesh) return;
        var role = o.material && o.material.name;
        o.material = roleMat(role || 'mat_stone_paving');
        shellByName[o.name] = o;
        if (/^door_\d+_slab$/.test(o.name)) { var i = +o.name.split('_')[1]; DOORS[i].mesh = o; DOORS[i].closedY = o.position.y; DOORS[i].openY = o.position.y - T.doorH - 0.1; mark(o, { kind: 'door', i: i }); }
        else if (o.name.indexOf('plaque_') === 0) { plaqueMeshes[o.name.slice(7)] = o; }
        else if (o.name === 'sign_hall') { o.material = signMat; }
        else if (o.name.indexOf('vines_') < 0) solids.push(o);
      });
      scene.add(gltf.scene);
      DOORS.forEach(function (d, i) { if (d.mesh && X.open[i]) d.mesh.position.y = d.openY; });
      Object.keys(plaqueMeshes).forEach(function (id) { var m = plaqueMeshes[id]; m.material = plaqueMat(id); mark(m, { kind: 'plaque', id: id, normal: plaqueNormal(id) }); });
    }, function (err) { console.error('shell failed to load', err); });
  })();
  var signTex = tex(A.sign(512, 200, [L.hall, 'The Elmorians'])); signTex.flipY = false; signTex.needsUpdate = true;
  var signMat = new THREE.MeshStandardMaterial({ map: signTex, roughness: 0.8 });
  var cache = {};
  function plaqueMat(id) {
    if (cache[id]) return cache[id];
    var def = L.plaques[id], c = A.plaque(512, 366, function (g) {
      if (def.art === 'diagramSpeech') A.diagramSpeech(g, 512, 366, P.makeSpeech().greeting);
      else if (def.art === 'diagramFinal') { var gz = P.makeGaze(); A.diagramFinal(g, 512, 366, gz.final, P.makeSpeech().farewell); }
      else A[def.art](g, 512, 366);
    }, '#8c8470', id.length * 7);
    var t = tex(c); t.flipY = false; t.needsUpdate = true;
    cache[id] = new THREE.MeshStandardMaterial({ map: t, roughness: 0.85 }); return cache[id];
  }
  function plaqueNormal(id) { var p = LAY.plaques.filter(function (q) { return q.id === id; })[0]; return V3(p.normal[0], 0, p.normal[2]); }
  function plaqueDef(id) { return LAY.plaques.filter(function (q) { return q.id === id; })[0]; }

  // ---- the rooms and the camera's places in them ---------------------------------------------
  var ROOMS = [
    { center: V3(0, 1.8, -0.4), yaw: 0, pitch: 0.02, dist: 4.4, lamps: [[0, 3.4, 3.2], [0, 2.6, 1.2]], spot: [[0, 4.6, 3.6], [0, 2.2, -0.4]] },
    { center: V3(0, 1.5, -4.8), yaw: 0, pitch: 0.05, dist: 3.0, lamps: [[0, 3.6, -5], [0, 3.0, -8]], spot: [[0, 3.8, -6.3], [0, 2.0, -9.0]] },
    { center: V3(-8.0, 1.5, -5), yaw: PI / 2, pitch: 0.05, dist: 3.0, lamps: [[-8.4, 3.6, -5], [-10.6, 3.0, -5]], spot: [[-9.4, 3.8, -5], [-11.3, 1.0, -5]] },
    { center: V3(-8.0, 1.5, -13.4), yaw: PI / 2, pitch: 0.05, dist: 3.0, lamps: [[-8.4, 3.6, -13.4], [-10.6, 3.0, -13.4]], spot: [[-9.4, 3.8, -13.4], [-12.4, 1.6, -13.4]] },
    { center: V3(0, 1.5, -13.4), yaw: -PI / 2, pitch: 0.05, dist: 3.0, lamps: [[0, 3.6, -13.4], [2.2, 3.0, -13.4]], spot: [[1.4, 3.8, -13.4], [4.0, 2.0, -13.4]] },
    { center: V3(0, 1.3, -19.9), yaw: 0, pitch: 0.08, dist: 2.0, lamps: [[0, 3.5, -19.8], [0, 3.2, -18.4]], spot: [[0, 3.9, -18.6], [0, 1.4, -19.8]] }
  ];
  var DOORS = LAY.doors.map(function (d) { return { pos: V3(d.at[0], 0, d.at[1]), axis: d.axis, rooms: d.rooms, slab: d.slab }; });

  var interact = [];   // everything a tap may land on
  function mark(mesh, data) { Object.assign(mesh.userData, data); interact.push(mesh); return mesh; }

  // An invisible pane in each opening so an open door can be tapped to walk
  // through. The slabs themselves come from the shell.
  DOORS.forEach(function (d, i) {
    var ry = d.axis === 'x' ? 0 : PI / 2;
    var pane = new THREE.Mesh(new THREE.PlaneGeometry(T.doorW, T.doorH), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    pane.position.set(d.pos.x, T.doorH / 2, d.pos.z); pane.rotation.y = ry; pane.material.side = THREE.DoubleSide; scene.add(pane);
    d.pane = mark(pane, { kind: 'doorway', i: i });
  });

  // ---- plaques -------------------------------------------------------------------------
  // A plaque faces the room: `n` is its wall's normal into the room.
  function plaque(id, x, y, z, n) {
    var def = L.plaques[id], c = A.plaque(512, 366, function (g) {
      if (def.art === 'diagramSpeech') A.diagramSpeech(g, 512, 366, P.makeSpeech().greeting);
      else if (def.art === 'diagramFinal') { var gz = P.makeGaze(); A.diagramFinal(g, 512, 366, gz.final, P.makeSpeech().farewell); }
      else A[def.art](g, 512, 366);
    }, '#8c8470', id.length * 7);
    var m = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.0), new THREE.MeshStandardMaterial({ map: tex(c), roughness: 0.85 }));
    m.position.set(x + n[0] * 0.02, y, z + n[2] * 0.02); m.rotation.y = Math.atan2(n[0], n[2]);
    m.userData.normal = V3(n[0], 0, n[2]); scene.add(m);
    return mark(m, { kind: 'plaque', id: id, normal: V3(n[0], 0, n[2]), dist: 1.5 });
  }
  plaque('portrait', 4.0, 2.0, -7.0, [-1, 0, 0]); plaque('gaze', 4.0, 2.0, -5.0, [-1, 0, 0]); plaque('count', 4.0, 2.0, -3.0, [-1, 0, 0]);
  plaque('cliff', -10.6, 2.0, -1.0, [0, 0, -1]); plaque('stack', -8.4, 2.0, -1.0, [0, 0, -1]); plaque('drink', -6.2, 2.0, -1.0, [0, 0, -1]);
  plaque('touch', -9.5, 2.0, -17.4, [0, 0, 1]); plaque('greet', -7.3, 2.0, -17.4, [0, 0, 1]);
  plaque('ancestors', -2.4, 2.0, -9.4, [0, 0, -1]); plaque('six', 0, 2.0, -9.4, [0, 0, -1]); plaque('farewell', 2.4, 2.0, -9.4, [0, 0, -1]);

  // ---- door lamps: green on the way on, red on the way back --------------------
  // Green means this door has opened and leads deeper; red means it goes back
  // the way you came; dark means it is still shut. One disc on each side of the
  // opening, because a door is a fact in both rooms.
  var LAMP = { green: 0x2fe06a, red: 0xe0392f, off: 0x1a1c18 };
  var lampMats = {};
  function lampMat(kind) {
    if (!lampMats[kind]) lampMats[kind] = new THREE.MeshStandardMaterial({ color: 0x101210, emissive: LAMP[kind], emissiveIntensity: kind === 'off' ? 0.04 : 0.75, roughness: 0.4 });
    return lampMats[kind];
  }
  DOORS.forEach(function (d) {
    d.lamps = [1, -1].map(function (side) {
      var m = new THREE.Mesh(new THREE.CircleGeometry(0.06, 20), lampMat('off'));
      var out = d.axis === 'x' ? V3(0, 0, side) : V3(side, 0, 0);
      m.position.set(d.pos.x + out.x * 0.21, T.doorH + 0.16, d.pos.z + out.z * 0.21);
      m.lookAt(m.position.clone().add(out));
      scene.add(m); return m;
    });
  });
  function refreshDoorLamps() {
    var lit = [];
    DOORS.forEach(function (d, i) {
      // rooms[0] is always the nearer room, so from rooms[0] this door leads on.
      var kind = d.rooms.indexOf(rig.room) < 0 ? 'off'
               : d.rooms[1] === rig.room ? 'red'
               : X.open[i] ? 'green' : 'off';
      d.lamps.forEach(function (m) { m.material = lampMat(kind); });
      if (kind !== 'off' && lit.length < doorLights.length) lit.push([d, kind]);
    });
    doorLights.forEach(function (l, k) {
      if (!lit[k]) { l.intensity = 0; return; }
      var d = lit[k][0], out = d.axis === 'x' ? V3(0, 0, 1) : V3(1, 0, 0);
      var toward = ROOMS[rig.room].center.clone().sub(d.pos); toward.y = 0;
      var sgn = toward.dot(out) >= 0 ? 1 : -1;
      l.position.set(d.pos.x + out.x * sgn * 0.45, T.doorH + 0.05, d.pos.z + out.z * sgn * 0.45);
      l.color.setHex(LAMP[lit[k][1]]); l.intensity = 0.85;
    });
  }

  function box(w, h, d, mat, x, y, z, ry) {
    var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); if (ry) m.rotation.y = ry;
    scene.add(m); return m;
  }

  // ---- room 1: the eye discs -------------------------------------------------------------
  var X = P.makeExhibit();
  var eyeDiscs = [];
  [[-1.25, 0.62], [0.25, 0.44], [1.35, 0.3]].forEach(function (e, i) {
    var grp = new THREE.Group(); grp.position.set(e[0], 2.0, -8.92);
    var side = new THREE.Mesh(new THREE.CylinderGeometry(e[1], e[1], 0.16, 40, 1, false), stoneMat(A.stone(128, '#8a8267', 60 + i), 4, 1));
    side.rotation.x = PI / 2; grp.add(side);
    var face = new THREE.Mesh(new THREE.CircleGeometry(e[1] * 0.98, 40), new THREE.MeshStandardMaterial({ map: tex(A.eyeDisc(256)), roughness: 0.55 }));
    face.position.z = 0.081; grp.add(face);
    scene.add(grp); mark(side, { kind: 'eye', i: i }); mark(face, { kind: 'eye', i: i });
    grp.userData.angle = A.posAngle(X.gaze.pos[i]); grp.rotation.z = grp.userData.angle;
    eyeDiscs.push(grp);
  });

  // ---- room 2: the light stack --------------------------------------------------------------
  var plinthTop = 0.9, pegZ = [-3.8, -5.0, -6.2], pegX = -11.3;
  var plinth = box(1.1, plinthTop, 3.3, stoneMat(A.stone(256, '#6a6357', 70, false), 2, 6), pegX, plinthTop / 2, -5);
  mark(plinth, { kind: 'stack', peg: -1 });
  pegZ.forEach(function (z, i) {
    var peg = box(0.16, 1.0, 0.16, stoneMat(A.stone(64, '#4e483f', 71 + i), 1, 4), pegX, plinthTop + 0.5, z);
    mark(peg, { kind: 'stack', peg: i });
    var pane = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.2, 1.0), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    pane.position.set(pegX, plinthTop + 0.6, z); scene.add(pane); mark(pane, { kind: 'stack', peg: i });
  });
  // the sun over the right peg (as seen from the room) and the eye over the middle
  [[2, 0], [1, 2]].forEach(function (s) {
    var c = A.canvas(128, 128), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = 'rgba(28,22,12,0.85)'; A.word(g, 64, 64, 110, s[1]);
    var m = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.5), new THREE.MeshStandardMaterial({ map: tex(c), transparent: true, roughness: 0.9 }));
    m.position.set(-12.37, 2.6, pegZ[s[0]]); m.rotation.y = PI / 2; scene.add(m);
  });
  var rings = [];
  function ringHome(size, peg, index) { return V3(pegX, plinthTop + 0.1 + index * 0.17, pegZ[peg]); }
  for (var sz = 0; sz < 4; sz++) {
    var r = new THREE.Mesh(new THREE.TorusGeometry(0.17 + sz * 0.09, 0.075, 12, 36), stoneMat(A.stone(64, ['#a89a72', '#8f8a6a', '#7f7a68', '#6d6a60'][sz], 80 + sz), 6, 1));
    r.rotation.x = PI / 2; scene.add(r); r.userData.queue = [];
    rings.push(r);
  }
  function layoutRings(instant) {
    X.stack.pegs.forEach(function (p, peg) { p.forEach(function (size, idx) { var h = ringHome(size, peg, idx); if (instant) rings[size].position.copy(h); else rings[size].userData.queue = [h]; }); });
  }
  layoutRings(true);

  // ---- room 3: the pads ---------------------------------------------------------------------
  var pads = [];
  for (var pi = 0; pi < 6; pi++) {
    var pm = new THREE.MeshStandardMaterial({ map: tex(A.pad(128, pi, false)), roughness: 0.8, emissive: new THREE.Color(0x000000) });
    var pad = box(0.62, 0.62, 0.12, pm, -12.36, pi < 3 ? 2.05 : 1.25, -13.4 + (1 - (pi % 3)) * 1.0, PI / 2);
    pad.userData.lit = tex(A.pad(128, pi, true)); pad.userData.dim = pm.map; pad.userData.glow = 0;
    mark(pad, { kind: 'pad', i: pi }); pads.push(pad);
  }

  // ---- room 4: the seeing stones ---------------------------------------------------------------
  var stones = [];
  var stoneDraw = [
    function (g, s) { for (var i = 0; i < 3; i++) { var r = [0.11, 0.08, 0.055][i] * s, x = s * (0.25 + i * 0.25), y = s * 0.42, a = A.posAngle(X.gaze.pos[i]);
      g.beginPath(); g.arc(x, y, r, 0, PI * 2); g.stroke(); g.beginPath(); g.arc(x + Math.cos(a) * r * 0.5, y - Math.sin(a) * r * 0.5, r * 0.3, 0, PI * 2); g.fill(); A.numeral(g, x, s * 0.7, s * 0.12, X.gaze.pos[i]); } },
    function (g, s) { var base = s * 0.72; g.beginPath(); g.moveTo(s * 0.15, base); g.lineTo(s * 0.85, base); g.stroke();
      X.stack.pegs.forEach(function (p, i) { var x = s * (0.28 + i * 0.22); g.beginPath(); g.moveTo(x, base); g.lineTo(x, base - s * 0.3); g.stroke();
        p.forEach(function (size, j) { g.beginPath(); g.ellipse(x, base - s * 0.03 - j * s * 0.055, s * 0.03 + size * s * 0.02, s * 0.02, 0, 0, PI * 2); g.stroke(); }); });
      A.word(g, s * 0.5, s * 0.22, s * 0.16, 2); },
    function (g, s) { var ph = X.speech.last ? X.speech[X.speech.last] : null;
      if (!ph) { g.beginPath(); g.arc(s * 0.5, s * 0.5, s * 0.06, 0, PI * 2); g.stroke(); return; }
      ph.forEach(function (w, i) { A.word(g, s * (0.62 - Math.floor(i / 2) * 0.3), s * (0.34 + (i % 2) * 0.32), s * 0.2, w); }); }
  ];
  [-15.0, -13.4, -11.8].forEach(function (z, i) {
    var c = A.seeingStone(256, stoneDraw[i]);
    var m = new THREE.Mesh(new THREE.CircleGeometry(0.55, 40), new THREE.MeshStandardMaterial({ map: tex(c), roughness: 0.5, emissive: new THREE.Color(0x1a2a20), emissiveIntensity: 0.6 }));
    m.position.set(3.975, 2.1, z); m.rotation.y = -PI / 2; scene.add(m); m.userData.canvas = c;
    mark(m, { kind: 'stone', i: i, normal: V3(-1, 0, 0), dist: 1.6 }); stones.push(m);
  });
  function refreshStones() { stones.forEach(function (m, i) { var c = m.userData.canvas; var nc = A.seeingStone(256, stoneDraw[i]); c.getContext('2d').drawImage(nc, 0, 0); m.material.map.needsUpdate = true; }); }

  // ---- the alcove: the ancestor -------------------------------------------------------------
  (function () {
    var mat = new THREE.MeshStandardMaterial({ map: tex(A.stone(256, '#5a7052', 90, false)), roughness: 0.7 });
    var g = new THREE.Group(); g.position.set(0, 0, -19.8);
    var body = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.5, 1.5, 24), mat); body.position.y = 0.75; g.add(body);
    var neck = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.22, 0.3, 16), mat); neck.position.y = 1.6; g.add(neck);
    var head = new THREE.Mesh(new THREE.SphereGeometry(0.36, 28, 20), mat); head.scale.set(1, 1.3, 0.95); head.position.y = 2.15; g.add(head);
    var eyeMat = new THREE.MeshStandardMaterial({ color: 0xe6e0b6, roughness: 0.4 }), pupil = new THREE.MeshStandardMaterial({ color: 0x0b0f0a, roughness: 0.3 });
    [[-0.14, 2.08, 0.14], [0.16, 2.1, 0.1], [0.0, 2.4, 0.06]].forEach(function (e, i) {
      var eye = new THREE.Mesh(new THREE.SphereGeometry(e[2], 18, 12), i === 2 ? new THREE.MeshStandardMaterial({ color: 0xe6e0b6, emissive: 0x88a060, emissiveIntensity: 0.9 }) : eyeMat);
      eye.position.set(e[0], e[1], 0.3); g.add(eye);
      var pp = new THREE.Mesh(new THREE.SphereGeometry(e[2] * 0.45, 12, 8), pupil); pp.position.set(e[0], e[1], 0.3 + e[2] * 0.75); g.add(pp);
    });
    var curve = new THREE.CatmullRomCurve3([V3(0, 2.55, -0.05), V3(0.12, 2.95, -0.3), V3(0.5, 2.8, -0.6), V3(0.62, 2.1, -0.5), V3(0.55, 1.5, -0.25)]);
    var sil = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.09, 10, false), mat); g.add(sil);
    var tip = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 8), mat); tip.position.copy(curve.getPoint(1)); g.add(tip);
    var base = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.8, 0.2, 24), stoneMat(stoneDark, 2, 1)); base.position.y = 0.1; g.add(base);
    scene.add(g);
  })();

  // ---- the camera rig ------------------------------------------------------------------------
  var rig = { target: ROOMS[0].center.clone(), yaw: 0, pitch: 0.02, dist: 4.4,
              goal: { target: ROOMS[0].center.clone(), yaw: 0, pitch: 0.02, dist: 4.4 },
              queue: [], mode: 'room', room: 0, station: null, anchorYaw: 0, anchorPitch: 0 };
  function nearAngle(a, ref) { while (a - ref > PI) a -= 2 * PI; while (a - ref < -PI) a += 2 * PI; return a; }
  function setGoal(target, yaw, pitch, dist) { rig.goal.target.copy(target); rig.goal.yaw = nearAngle(yaw, rig.yaw); rig.goal.pitch = pitch; rig.goal.dist = dist; }
  function placeLights(r) {
    var R = ROOMS[r];
    lampA.position.set(R.lamps[0][0], R.lamps[0][1], R.lamps[0][2]);
    // every plaque in this room, then its station: the track heads the shell carries
    var so = LAY.fixtures.lighting.standoff, y = LAY.fixtures.truss.y - 0.4;
    var aims = LAY.plaques.filter(function (p) { return roomOf(p.pos) === r; }).map(function (p) { return [p.pos, p.normal, 26, 0.52]; });
    Object.keys(LAY.stations).forEach(function (k) { var st = LAY.stations[k]; if (st.room === r) aims.push([st.point, st.normal, 70, 0.8]); });
    if (r === 0) aims.push([[0, 3.25, -0.6], [0, 0, 1], 30, 0.5], [[0, 1.6, -0.6], [0, 0, 1], 24, 0.7]);
    if (r === 5) aims.push([[0, 1.4, -19.9], [0, 0.6, 1], 50, 0.7]);
    spots.forEach(function (sp, i) {
      var a = aims[i];
      if (!a) { sp.intensity = 0; return; }
      var n = a[1], len = Math.hypot(n[0], n[2]) || 1;
      sp.position.set(a[0][0] + n[0] / len * so, y, a[0][2] + n[2] / len * so);
      sp.target.position.set(a[0][0], a[0][1], a[0][2]); sp.intensity = a[2]; sp.angle = a[3];
    });
  }
  function roomOf(p) { for (var i = 0; i < LAY.rooms.length; i++) { var b = LAY.rooms[i].bounds; if (p[0] >= b[0] && p[0] <= b[2] && p[2] >= b[1] && p[2] <= b[3]) return LAY.rooms[i].id; } return -1; }
  function goRoom(r, instant) {
    var R = ROOMS[r], from = rig.room;
    rig.mode = 'room'; rig.station = null; rig.room = r; hideCard(); backBtn.hidden = true;
    // Through the doorway first, then to the room's own place, so the camera
    // never cuts through a wall on the way.
    var door = DOORS.filter(function (d) { return (d.rooms[0] === from && d.rooms[1] === r) || (d.rooms[1] === from && d.rooms[0] === r); })[0];
    rig.queue = [];
    if (door && !instant) {
      var dp = door.pos.clone(); dp.y = 1.5;
      var dir = R.center.clone().sub(dp); dir.y = 0; dir.normalize();
      var look = Math.atan2(-dir.x, -dir.z);
      rig.queue.push({ target: dp.clone().add(dir.clone().multiplyScalar(0.9)), yaw: look, pitch: 0.02, dist: 0.9 });
    }
    rig.queue.push({ target: R.center, yaw: R.yaw, pitch: R.pitch, dist: roomDist(R) });
    var g = rig.queue.shift(); setGoal(g.target, g.yaw, g.pitch, g.dist);
    if (instant) { rig.target.copy(rig.goal.target); rig.yaw = rig.goal.yaw; rig.pitch = rig.goal.pitch; rig.dist = rig.goal.dist; }
    placeLights(r); refreshDoorLamps(); updateHud(); save();
    if (r === 5) setTimeout(function () { if (rig.room === 5) showCard(L.end.title, L.end.text); }, 1400);
  }
  function inspect(point, normal, dist, station) {
    var off = normal.clone().normalize();
    rig.mode = 'inspect'; rig.station = station || null; rig.queue = [];
    var yaw = Math.atan2(off.x, off.z), pitch = Math.asin(Math.max(-1, Math.min(1, off.y)));
    rig.anchorYaw = nearAngle(yaw, rig.yaw); rig.anchorPitch = pitch;
    setGoal(point, yaw, pitch, dist);
    backBtn.hidden = false;
  }
  function leaveInspect() { var R = ROOMS[rig.room]; rig.mode = 'room'; rig.station = null; rig.queue = []; setGoal(R.center, R.yaw, R.pitch, roomDist(R)); hideCard(); backBtn.hidden = true; }
  // The distance that fits a w by h extent in the current view, capped so the
  // camera stays inside the room.
  function fitDist(w, h, cap) {
    var vf = camera.fov * PI / 360, hf = Math.atan(Math.tan(vf) * camera.aspect);
    var d = Math.max(w * 0.5 / Math.tan(hf), h * 0.5 / Math.tan(vf)) * 1.12 + 0.3;
    return Math.min(cap, Math.max(1.2, d));
  }
  var STATIONS = {
    gaze: { point: V3(0, 2.0, -9.0), normal: V3(0, 0, 1), w: 3.7, h: 1.6, cap: 6.6, room: 1 },
    stack: { point: V3(-11.3, 1.15, -5), normal: V3(1, 0.32, 0), w: 3.4, h: 1.7, cap: 6.4, room: 2 },
    speech: { point: V3(-12.4, 1.65, -13.4), normal: V3(1, 0, 0), w: 2.9, h: 1.7, cap: 6.4, room: 3 },
    final: { point: V3(4.0, 2.0, -13.4), normal: V3(-1, 0, 0), w: 4.4, h: 1.5, cap: 6.8, room: 4 }
  };
  function goStation(name) { var s = STATIONS[name]; inspect(s.point, s.normal, fitDist(s.w, s.h, s.cap), name); }
  function roomDist(R) { return camera.aspect < 1 ? R.dist + 0.3 : R.dist; }

  // ---- input ---------------------------------------------------------------------------------------
  var pointers = {}, drag = null, pinchD = 0;
  canvasEl.addEventListener('pointerdown', function (e) {
    canvasEl.setPointerCapture(e.pointerId);
    pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
    var n = Object.keys(pointers).length;
    if (n === 1) drag = { x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, t: performance.now(), moved: false };
    if (n === 2) { var ps = Object.values(pointers); pinchD = Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y); drag = null; }
    audio.wake();
  });
  canvasEl.addEventListener('pointermove', function (e) {
    if (!pointers[e.pointerId]) return;
    pointers[e.pointerId].x = e.clientX; pointers[e.pointerId].y = e.clientY;
    var ps = Object.values(pointers);
    if (ps.length >= 2) {
      var d = Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y);
      if (pinchD > 0) rig.goal.dist = Math.max(T.distMin * 0.6, Math.min(T.distMax, rig.goal.dist * pinchD / d));
      pinchD = d; return;
    }
    if (!drag) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
    if (Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy) > T.tapPx) drag.moved = true;
    if (!drag.moved) return;
    if (rig.mode === 'room') {
      rig.goal.yaw -= dx * T.orbitSens; rig.goal.pitch = Math.max(T.pitchMin, Math.min(T.pitchMax, rig.goal.pitch + dy * T.orbitSens));
    } else {
      rig.goal.yaw = Math.max(rig.anchorYaw - T.inspectNudge, Math.min(rig.anchorYaw + T.inspectNudge, rig.goal.yaw - dx * T.orbitSens * 0.6));
      rig.goal.pitch = Math.max(rig.anchorPitch - T.inspectNudge, Math.min(rig.anchorPitch + T.inspectNudge, rig.goal.pitch + dy * T.orbitSens * 0.6));
    }
  });
  function endPointer(e) {
    var was = pointers[e.pointerId]; delete pointers[e.pointerId];
    if (drag && was && !drag.moved && performance.now() - drag.t < T.tapMs) tap(e.clientX, e.clientY);
    if (!Object.keys(pointers).length) { drag = null; pinchD = 0; }
  }
  canvasEl.addEventListener('pointerup', endPointer); canvasEl.addEventListener('pointercancel', endPointer);
  canvasEl.addEventListener('wheel', function (e) { rig.goal.dist = Math.max(T.distMin * 0.6, Math.min(T.distMax, rig.goal.dist * (e.deltaY > 0 ? 1.08 : 0.92))); }, { passive: true });

  var ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  function tap(x, y) {
    hint.classList.add('gone');
    ndc.set((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    // A hit closer than half a metre is something the camera stands in. A
    // doorway closer than a metre and a bit is one the camera is passing
    // through, not one being chosen: tapping it would walk straight back out.
    var hits = ray.intersectObjects(interact.concat(solids), false).filter(function (h) { return h.distance > (h.object.userData.kind === 'doorway' ? 1.2 : 0.5); });
    if (!hits.length) { if (rig.mode === 'inspect') leaveInspect(); return; }
    var h = hits[0], u = h.object.userData;
    if (!u.kind) { if (rig.mode === 'inspect') leaveInspect(); return; }
    switch (u.kind) {
      case 'door': case 'doorway': {
        var d = DOORS[u.i];
        if (!X.open[u.i]) { showCard(L.doors[u.i].title, L.doors[u.i].text); shake(d.mesh); audio.thud(); return; }
        var to = d.rooms[0] === rig.room ? d.rooms[1] : d.rooms[0]; goRoom(to); audio.step(); break;
      }
      case 'plaque': showCard(L.plaques[u.id].title, L.plaques[u.id].text); inspect(h.object.position, u.normal, fitDist(1.5, 1.1, 4), 'plaque'); audio.click(); break;
      case 'stone': showCard('Seeing stone', 'It shows a room behind you as that room stands now.'); goStation('final'); audio.click(); break;
      case 'eye':
        if (rig.station !== 'gaze') { goStation('gaze'); audio.click(); break; }
        P.gazeTap(X.gaze, u.i); eyeDiscs[u.i].userData.angle += PI / 3; audio.tick(u.i); afterChange(); break;
      case 'stack':
        if (rig.station !== 'stack') { goStation('stack'); audio.click(); break; }
        if (u.peg < 0) break;
        stackTap(u.peg); break;
      case 'pad':
        if (rig.station !== 'speech') { goStation('speech'); audio.click(); break; }
        padTap(u.i); break;
    }
  }

  function stackTap(peg) {
    var heldBefore = X.stack.held, from = X.stack.from, r = P.stackTap(X.stack, peg);
    if (r === 'empty') { audio.thud(); return; }
    if (r === 'lift') { var ring = rings[X.stack.held]; ring.userData.queue = [V3(pegX, T.ringHover, pegZ[peg])]; audio.lift(); return; }
    if (r === 'refuse') { shake(rings[heldBefore]); audio.thud(); return; }
    var size = X.stack.pegs[peg][X.stack.pegs[peg].length - 1], m = rings[size];
    var home = ringHome(size, peg, X.stack.pegs[peg].length - 1);
    m.userData.queue = r === 'return' ? [home] : [V3(pegX, T.ringHover, pegZ[peg]), home];
    audio.drop(); afterChange();
  }
  function padTap(i) {
    var r = P.speechTap(X.speech, i);
    pads[i].userData.glow = 1; audio.pad(i);
    if (r === 'wrong') { setTimeout(function () { pads.forEach(function (p) { p.userData.glow = 0; }); audio.thud(); }, 260); litPads(null); return; }
    if (r === 'ok') { litPads(X.speech.input); return; }
    litPads(X.speech[r]); audio.chime(); afterChange();
  }
  function litPads(list) { pads.forEach(function (p, i) { var on = !!(list && list.indexOf(i) >= 0); p.material.map = on ? p.userData.lit : p.userData.dim; p.material.needsUpdate = true; p.userData.on = on; }); }
  litPads(X.speech.last ? X.speech[X.speech.last] : null);

  var wasOpen = X.open.slice();
  function afterChange() {
    P.refreshDoors(X); refreshStones(); refreshDoorLamps(); save();
    X.open.forEach(function (o, i) { if (o && !wasOpen[i]) { audio.doorChime(); toast(i === 4 ? 'The ancestor door opens' : 'A door opens'); } });
    wasOpen = X.open.slice(); updateHud();
  }
  var shakes = [];
  function shake(mesh) { if (mesh) shakes.push({ m: mesh, t: 0, x: mesh.position.x }); }

  // ---- HUD ------------------------------------------------------------------------------------------
  var card = document.getElementById('card'), cardTitle = document.getElementById('cardTitle'), cardText = document.getElementById('cardText');
  var backBtn = document.getElementById('back'), hint = document.getElementById('hint'), chips = document.getElementById('chips'), toastEl = document.getElementById('toast');
  function showCard(title, text) { cardTitle.textContent = title; cardText.innerHTML = text.split('\n\n').map(function (p) { return '<p>' + p + '</p>'; }).join(''); cardText.scrollTop = 0; card.hidden = false; }
  function hideCard() { card.hidden = true; }
  document.getElementById('cardClose').addEventListener('click', function () { hideCard(); if (rig.station === 'plaque') leaveInspect(); });
  backBtn.addEventListener('click', leaveInspect);
  var toastT = 0; function toast(s) { toastEl.textContent = s; toastEl.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 2200); }
  function chip(i) {
    var c = A.canvas(64, 64), g = c.getContext('2d'); g.strokeStyle = g.fillStyle = '#d8d3c5'; g.lineWidth = 4; g.lineCap = 'round';
    if (i === 0) A.word(g, 32, 32, 50, 4); else if (i === 5) A.word(g, 32, 32, 44, 5); else A.numeral(g, 32, 32, 40, i);
    var b = document.createElement('button'); b.setAttribute('aria-label', L.rooms[i].name); b.innerHTML = '<img alt="" src="' + c.toDataURL() + '">';
    b.addEventListener('click', function () { if (canReach(i)) { goRoom(i); audio.step(); } else audio.thud(); });
    chips.appendChild(b); return b;
  }
  var chipEls = [0, 1, 2, 3, 4, 5].map(chip);
  function canReach(i) { for (var k = 1; k <= i && k <= 4; k++) if (!X.open[k]) return false; return true; }
  function updateHud() {
    document.getElementById('roomSub').textContent = L.rooms[rig.room].sub; document.getElementById('roomName').textContent = L.rooms[rig.room].name;
    chipEls.forEach(function (b, i) { b.classList.toggle('here', i === rig.room); b.classList.toggle('locked', !canReach(i)); });
  }
  var resetBtn = document.getElementById('reset'), resetArmed = false;
  resetBtn.addEventListener('click', function () {
    if (!resetArmed) { resetArmed = true; resetBtn.textContent = 'tap again to restart'; setTimeout(function () { resetArmed = false; resetBtn.textContent = 'restart'; }, 2500); return; }
    try { localStorage.removeItem(SAVE); } catch (e) {} location.reload();
  });
  document.getElementById('archInfo').addEventListener('click', function () { showCard(L.arch.title, L.arch.text); });

  // ---- save: the state, not the scene ---------------------------------------------------------------------
  var SAVE = 'elmorian-exhibit-v1';
  function save() { try { localStorage.setItem(SAVE, JSON.stringify({ gaze: X.gaze.pos, pegs: X.stack.pegs, last: X.speech.last, open: X.open, room: rig.room })); } catch (e) {} }
  function load() {
    try {
      var s = JSON.parse(localStorage.getItem(SAVE) || 'null'); if (!s) return false;
      X.gaze.pos = s.gaze; X.stack.pegs = s.pegs; X.speech.last = s.last; X.open = s.open;
      eyeDiscs.forEach(function (g, i) { g.userData.angle = A.posAngle(X.gaze.pos[i]); g.rotation.z = g.userData.angle; });
      layoutRings(true); litPads(X.speech.last ? X.speech[X.speech.last] : null); refreshStones(); wasOpen = X.open.slice();
      DOORS.forEach(function (d, i) { if (d.mesh && X.open[i]) d.mesh.position.y = d.openY; });
      goRoom(Math.min(s.room, 4), true); hint.classList.add('gone'); return true;
    } catch (e) { return false; }
  }

  // ---- audio: a handful of tones, nothing loaded --------------------------------------------------------
  var audio = (function () {
    var ctx = null;
    function wake() { if (!ctx) { try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {} } if (ctx && ctx.state === 'suspended') ctx.resume(); }
    function tone(f, dur, type, vol, when) {
      if (!ctx) return; var o = ctx.createOscillator(), g = ctx.createGain(); var t0 = ctx.currentTime + (when || 0);
      o.type = type || 'sine'; o.frequency.value = f; g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(vol || 0.15, t0 + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      o.connect(g); g.connect(ctx.destination); o.start(t0); o.stop(t0 + dur + 0.05);
    }
    var padF = [220, 261.6, 293.7, 349.2, 392, 440];
    return { wake: wake, click: function () { tone(900, 0.05, 'square', 0.04); }, tick: function (i) { tone(500 + i * 120, 0.08, 'triangle', 0.08); },
             thud: function () { tone(90, 0.18, 'sine', 0.2); }, lift: function () { tone(330, 0.12, 'triangle', 0.08); }, drop: function () { tone(180, 0.14, 'sine', 0.14); },
             pad: function (i) { tone(padF[i], 0.5, 'sine', 0.16); tone(padF[i] * 2, 0.25, 'triangle', 0.04); },
             chime: function () { [0, 0.12, 0.24].forEach(function (d, i) { tone([523, 659, 784][i], 0.5, 'sine', 0.1, d); }); },
             doorChime: function () { [0, 0.15, 0.3, 0.45].forEach(function (d, i) { tone([392, 523, 659, 1047][i], 0.7, 'triangle', 0.08, d); }); },
             step: function () { tone(140, 0.1, 'sine', 0.06); } };
  })();

  // ---- the loop --------------------------------------------------------------------------------------------
  function resize() {
    var w = window.innerWidth, h = window.innerHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    if (rig.mode === 'inspect' && rig.station && STATIONS[rig.station]) { var st = STATIONS[rig.station]; rig.goal.dist = fitDist(st.w, st.h, st.cap); }
    else if (rig.mode === 'room' && !rig.queue.length) rig.goal.dist = roomDist(ROOMS[rig.room]);
  }
  window.addEventListener('resize', resize); resize();
  function ease(a, b, k) { return a + (b - a) * k; }
  var last = performance.now(), offset = new THREE.Vector3();
  function frame(now) {
    var dt = Math.min(0.05, (now - last) / 1000); last = now;
    var k = 1 - Math.exp(-T.easeK * dt);
    // camera
    rig.target.lerp(rig.goal.target, k); rig.yaw = ease(rig.yaw, rig.goal.yaw, k); rig.pitch = ease(rig.pitch, rig.goal.pitch, k);
    rig.dist = Math.exp(ease(Math.log(rig.dist), Math.log(rig.goal.dist), k));
    if (rig.queue.length && rig.target.distanceTo(rig.goal.target) < 0.25) { var g = rig.queue.shift(); setGoal(g.target, g.yaw, g.pitch, g.dist); }
    offset.set(Math.sin(rig.yaw) * Math.cos(rig.pitch), Math.sin(rig.pitch), Math.cos(rig.yaw) * Math.cos(rig.pitch)).multiplyScalar(rig.dist);
    camera.position.copy(rig.target).add(offset); camera.lookAt(rig.target);
    // doors
    DOORS.forEach(function (d, i) { if (d.mesh) d.mesh.position.y = ease(d.mesh.position.y, X.open[i] ? d.openY : d.closedY, k * 0.6); });
    // eyes
    eyeDiscs.forEach(function (e) { e.rotation.z = ease(e.rotation.z, e.userData.angle, k * 1.4); });
    // rings
    rings.forEach(function (r) { var q = r.userData.queue; if (!q.length) return; r.position.lerp(q[0], k * 1.6); if (r.position.distanceTo(q[0]) < 0.02) { r.position.copy(q[0]); q.shift(); } });
    // pads
    pads.forEach(function (p) { p.userData.glow = ease(p.userData.glow, p.userData.on ? 0.55 : 0, k); p.material.emissive.setRGB(0.9 * p.userData.glow, 0.7 * p.userData.glow, 0.25 * p.userData.glow); });
    // shakes
    for (var i = shakes.length - 1; i >= 0; i--) { var s = shakes[i]; s.t += dt; s.m.position.x = s.x + Math.sin(s.t * 60) * 0.03 * Math.max(0, 0.3 - s.t); if (s.t > 0.3) { s.m.position.x = s.x; shakes.splice(i, 1); } }
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  if (!load()) goRoom(0, true);
  requestAnimationFrame(frame);

  // Observed, never driven: the playthrough reads this and the tests will too.
  function screenOf(kind, i) {
    var m = interact.filter(function (o) { return o.userData.kind === kind && (i === undefined || o.userData.i === i || o.userData.peg === i || o.userData.id === i); })[0];
    if (!m) return null;
    var v = new THREE.Vector3(); m.getWorldPosition(v); v.project(camera);
    return { x: (v.x + 1) / 2 * window.innerWidth, y: (1 - v.y) / 2 * window.innerHeight, z: v.z };
  }
  // What a tap at (x, y) would land on, nearest first: names, kinds, distances.
  function hitAt(x, y) {
    ndc.set((x / window.innerWidth) * 2 - 1, -(y / window.innerHeight) * 2 + 1); ray.setFromCamera(ndc, camera);
    return ray.intersectObjects(interact.concat(solids), false).slice(0, 4).map(function (h) { return { name: h.object.name, kind: h.object.userData.kind, d: +h.distance.toFixed(2) }; });
  }
  window.ftDebug = { exhibit: X, rig: rig, rooms: ROOMS, screenOf: screenOf, hitAt: hitAt, pads: pads, rings: rings, eyes: eyeDiscs, stones: stones, doors: DOORS, renderer: renderer,
                     // navigation only, for taking pictures; a playthrough taps
                     goRoom: goRoom, goStation: goStation };
})();

/* Mundo Renda - terreno contínuo desenhado em blocos (chunks) com cache em várias resoluções.
   Cada bloco junta: tinta de profundidade da água, espuma do litoral, chão texturizado com bordas orgânicas,
   variação de cor em grande escala, tufos e flores, estradas com cantos arredondados e sombras dos objetos. */
'use strict';

var Terrain = (function () {
  var C = 8, P = 4;
  var w = World.w, T = DATA.T, I = DATA.BY_ID;
  var NC = Math.ceil(w.W / C);
  var ver = new Uint32Array(NC * NC);
  var entries = [];               // por bloco: { nivel: entrada }
  var pixels = 0, frameNo = 0;
  var LEVELS = [0.25, 0.35, 0.5, 0.71, 1, 1.41, 2, 2.83];
  var depth = new Uint8Array(w.N), terCopy = new Uint8Array(w.N), depthDirty = true;
  var ORDER = [T.AREIA, T.TERRA, T.PEDRA, T.SECA, T.GRAMA, T.CAMPO];   // prioridade (quem "derrama" sobre quem)
  var PRI = []; ORDER.forEach(function (t, n) { PRI[t] = n; });
  var TEXN = ['grama', 'campo', 'seca', 'areia', 'terra', 'pedra'];
  var geoms = [];
  var tmpShadow = null, smallCv = null;
  var stats = { rendered: 0, ms: 0 };
  var EDGES = [
    [[-0.5, -0.5], [0.5, -0.5], [0, -1], [-0.7071, -0.7071]],
    [[0.5, -0.5], [0.5, 0.5], [1, 0], [0.7071, -0.7071]],
    [[0.5, 0.5], [-0.5, 0.5], [0, 1], [0.7071, 0.7071]],
    [[-0.5, 0.5], [-0.5, -0.5], [-1, 0], [-0.7071, 0.7071]]
  ];

  for (var cj = 0; cj < NC; cj++) for (var ci = 0; ci < NC; ci++) { geoms.push(geom(ci, cj)); entries.push({}); }

  function geom(ci, cj) {
    var i0 = ci * C, j0 = cj * C, i1 = Math.min(w.W, i0 + C) - 1, j1 = Math.min(w.H, j0 + C) - 1;
    var top = [(i0 - j0) * 32, (i0 + j0) * 16 - 16], right = [(i1 - j0) * 32 + 32, (i1 + j0) * 16];
    var bottom = [(i1 - j1) * 32, (i1 + j1) * 16 + 16], left = [(i0 - j1) * 32 - 32, (i0 + j1) * 16];
    return { ci: ci, cj: cj, i0: i0, j0: j0, i1: i1, j1: j1, top: top, right: right, bottom: bottom, left: left,
      ox: left[0] - P, oy: top[1] - P, wpx: right[0] - left[0] + 2 * P, hpx: bottom[1] - top[1] + 2 * P };
  }

  /* ---------------- Invalidação ---------------- */
  function invalidate(k) {
    if (k < 0) {
      for (var c = 0; c < ver.length; c++) { ver[c]++; dropChunk(c); }
      terCopy.set(w.ter); depthDirty = true;
      return;
    }
    var i = World.iOf(k), j = World.jOf(k), r = 3;
    if (w.ter[k] !== terCopy[k]) {
      if ((w.ter[k] === T.AGUA) !== (terCopy[k] === T.AGUA)) { depthDirty = true; r = 7; }
      terCopy[k] = w.ter[k];
    }
    var a0 = Math.max(0, Math.floor((i - r) / C)), a1 = Math.min(NC - 1, Math.floor((i + r) / C));
    var b0 = Math.max(0, Math.floor((j - r) / C)), b1 = Math.min(NC - 1, Math.floor((j + r) / C));
    for (var b = b0; b <= b1; b++) for (var a = a0; a <= a1; a++) ver[b * NC + a]++;
  }
  function dropChunk(c) {
    var es = entries[c];
    for (var l in es) { pixels -= es[l].cv.width * es[l].cv.height; es[l].cv.width = es[l].cv.height = 0; }
    entries[c] = {};
  }

  function computeDepth() {
    var N = w.N, W = w.W, H = w.H, q = new Int32Array(N), head = 0, tail = 0, k;
    for (k = 0; k < N; k++) {
      if (w.ter[k] !== T.AGUA) { depth[k] = 0; q[tail++] = k; } else depth[k] = 255;
    }
    while (head < tail) {
      k = q[head++];
      var d = depth[k];
      if (d >= 6) continue;
      var i = k % W, j = (k / W) | 0;
      for (var dj = -1; dj <= 1; dj++) for (var di = -1; di <= 1; di++) {
        var ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= W || jj >= H) continue;
        var kk = jj * W + ii;
        if (depth[kk] === 255) { depth[kk] = d + 1; q[tail++] = kk; }
      }
    }
    for (k = 0; k < N; k++) if (depth[k] === 255) depth[k] = 6;
  }

  /* ---------------- Formas ---------------- */
  // contorno orgânico de um ladrilho (sempre cobre o losango inteiro e avança um pouco sobre os vizinhos)
  function blob(path, i, j, E, cuts) {
    var X = (i - j) * 32, Y = (i + j) * 16, pts = [];
    for (var e = 0; e < 4; e++) {
      var a = EDGES[e][0], b = EDGES[e][1], nrm = EDGES[e][2], cn = EDGES[e][3];
      for (var s = 0; s < 4; s++) {
        var t = s / 4, u = a[0] + (b[0] - a[0]) * t, v = a[1] + (b[1] - a[1]) * t;
        var n = s === 0 ? cn : nrm;
        var wx = X + (u - v) * 32, wy = Y + (u + v) * 16;
        var nz = U.noise(wx * 0.075, wy * 0.075, 31);
        var amt = E * (0.35 + 0.65 * nz);
        if (cuts) {
          if (s === 0 && cuts[e]) amt = -(0.3 + 0.1 * nz);          // canto convexo exposto: arredonda para dentro
          else if ((s === 1 && cuts[e]) || (s === 3 && cuts[(e + 1) % 4])) amt *= 0.15;
        }
        var uu = u + n[0] * amt, vv = v + n[1] * amt;
        pts.push(X + (uu - vv) * 32, Y + (uu + vv) * 16);
      }
    }
    var L = pts.length, lx = pts[L - 2], ly = pts[L - 1];
    path.moveTo((lx + pts[0]) / 2, (ly + pts[1]) / 2);
    for (var p = 0; p < L; p += 2) {
      var nx = pts[(p + 2) % L], ny = pts[(p + 3) % L];
      path.quadraticCurveTo(pts[p], pts[p + 1], (pts[p] + nx) / 2, (pts[p + 1] + ny) / 2);
    }
    path.closePath();
  }

  function nearWater(i, j) {
    for (var dj = -1; dj <= 1; dj++) for (var di = -1; di <= 1; di++) {
      var ii = i + di, jj = j + dj;
      if (ii >= 0 && jj >= 0 && ii < w.W && jj < w.H && w.ter[jj * w.W + ii] === T.AGUA) return true;
    }
    return false;
  }

  /* ---------------- Camadas do bloco ---------------- */
  // imagem pequena no espaço dos ladrilhos (sub amostras por ladrilho), desenhada esticada e desfocada
  function gridImage(ra, rb, rA, rB, sub, colorFn) {
    var nw = (rA - ra + 1) * sub, nh = (rB - rb + 1) * sub;
    if (!smallCv) smallCv = document.createElement('canvas');
    if (smallCv.width !== nw || smallCv.height !== nh) { smallCv.width = nw; smallCv.height = nh; }
    var sg = smallCv.getContext('2d'), img = sg.createImageData(nw, nh), d = img.data, any = false;
    var off = 0.5 / sub - 0.5;
    for (var b = 0; b < nh; b++) for (var a = 0; a < nw; a++) {
      var c = colorFn(ra + off + a / sub, rb + off + b / sub);
      var o = (b * nw + a) * 4;
      if (c) { d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2]; d[o + 3] = c[3]; if (c[3]) any = true; }
    }
    if (!any) return false;
    sg.putImageData(img, 0, 0);
    return true;
  }
  function drawGrid(g, R, G, ra, rb, sub, blur) {
    var X0 = (ra - rb) * 32, Y0 = (ra + rb - 1) * 16, k = 1 / sub;
    g.save();
    g.setTransform(R * 32 * k, R * 16 * k, -R * 32 * k, R * 16 * k, R * (X0 - G.ox), R * (Y0 - G.oy));
    g.imageSmoothingEnabled = true;
    try { g.imageSmoothingQuality = 'high'; } catch (e) { /* opcional */ }
    if (blur && 'filter' in g) g.filter = 'blur(' + (blur * R).toFixed(1) + 'px)';
    g.drawImage(smallCv, 0, 0);
    g.restore();
  }

  var WATER_TINT = [[120, 225, 225, 150], [105, 212, 224, 112], [60, 168, 208, 40], [22, 82, 142, 40], [14, 58, 112, 78], [9, 42, 92, 104], [6, 32, 78, 124]];
  function waterTint(g, R, G, ra, rb, rA, rB) {
    if (gridImage(ra, rb, rA, rB, 1, function (i, j) { return WATER_TINT[depth[Math.round(j) * w.W + Math.round(i)]]; })) drawGrid(g, R, G, ra, rb, 1, 7);
  }

  // cantos côncavos: quando os dois vizinhos de um canto são do mesmo tipo "mais forte",
  // um gomo arredondado preenche o canto e as diagonais deixam de parecer escadinha
  var CORNERS = [
    { c: [-0.5, -0.5], A: [0, -1], dA: [1, 0], B: [-1, 0], dB: [0, 1] },
    { c: [0.5, -0.5], A: [0, -1], dA: [-1, 0], B: [1, 0], dB: [0, 1] },
    { c: [0.5, 0.5], A: [1, 0], dA: [0, -1], B: [0, 1], dB: [-1, 0] },
    { c: [-0.5, 0.5], A: [0, 1], dA: [1, 0], B: [-1, 0], dB: [0, -1] }
  ];
  function terAt(i, j) { return (i < 0 || j < 0 || i >= w.W || j >= w.H) ? -1 : w.ter[j * w.W + i]; }
  function pri(t) { return t === T.AGUA ? -1 : PRI[t]; }
  function wedge(path, i, j, cn) {
    var X = (i - j) * 32, Y = (i + j) * 16, a = 0.56, c = cn.c, dA = cn.dA, dB = cn.dB;
    // mantém a mesma orientação dos contornos (senão a regra "nonzero" abre buracos)
    if (dA[0] * dB[1] - dA[1] * dB[0] < 0) { var tmp = dA; dA = dB; dB = tmp; }
    var pts = [];
    function P(u, v) { pts.push(X + (u - v) * 32, Y + (u + v) * 16); }
    P(c[0] - 0.06 * (dA[0] + dB[0]), c[1] - 0.06 * (dA[1] + dB[1]));
    P(c[0] + a * dA[0] - 0.05 * dB[0], c[1] + a * dA[1] - 0.05 * dB[1]);
    var ax = c[0] + a * dA[0], ay = c[1] + a * dA[1], bx = c[0] + a * dB[0], by = c[1] + a * dB[1];
    var inx = (dA[0] + dB[0]) * 0.7071, iny = (dA[1] + dB[1]) * 0.7071;
    for (var s = 1; s <= 4; s++) {
      var t = s / 5, u = ax + (bx - ax) * t, v = ay + (by - ay) * t;
      var wx = X + (u - v) * 32, wy = Y + (u + v) * 16;
      var d = 0.09 * (U.noise(wx * 0.08, wy * 0.08, 47) - 0.45);
      P(u + inx * d, v + iny * d);
    }
    P(c[0] + a * dB[0] - 0.05 * dA[0], c[1] + a * dB[1] - 0.05 * dA[1]);
    path.moveTo(pts[0], pts[1]);
    path.lineTo(pts[2], pts[3]);
    for (var p = 4; p < pts.length - 2; p += 2) path.quadraticCurveTo(pts[p], pts[p + 1], (pts[p] + pts[p + 2]) / 2, (pts[p + 1] + pts[p + 3]) / 2);
    path.lineTo(pts[pts.length - 2], pts[pts.length - 1]);
    path.closePath();
  }

  function land(g, ra, rb, rA, rB) {
    var paths = [], foam = null, i, j, cuts = [false, false, false, false];
    function P(px) { return paths[px] || (paths[px] = new Path2D()); }
    for (j = rb; j <= rB; j++) for (i = ra; i <= rA; i++) {
      var t = w.ter[j * w.W + i], pt = pri(t), anyCut = false;
      for (var q = 0; q < 4; q++) {
        var cn = CORNERS[q];
        var ta = terAt(i + cn.A[0], j + cn.A[1]), tb = terAt(i + cn.B[0], j + cn.B[1]);
        cuts[q] = false;
        if (ta < 0 || tb < 0) continue;
        var pa = pri(ta), pb = pri(tb);
        if (pa > pt && pb > pt) {
          // canto côncavo: o tipo vizinho (mais forte) preenche o canto
          var x = pa <= pb ? ta : tb;
          wedge(P(PRI[x]), i, j, cn);
          if (t === T.AGUA) { if (!foam) foam = new Path2D(); wedge(foam, i, j, cn); }
        } else if (pa < pt && pb < pt && t !== T.AGUA) {
          // canto convexo: este ladrilho recua e o vizinho (mais fraco) ocupa o canto
          cuts[q] = true; anyCut = true;
          var y = pa >= pb ? ta : tb;
          if (y === T.AGUA) y = pa >= pb ? tb : ta;
          if (y !== T.AGUA) wedge(P(PRI[y]), i, j, cn);
        }
      }
      if (t === T.AGUA) continue;
      var c = anyCut ? cuts : null;
      if (nearWater(i, j)) {
        blob(P(PRI[t]), i, j, 0.22, c);
        if (!foam) foam = new Path2D();
        blob(foam, i, j, 0.22, c);
      } else blob(P(PRI[t]), i, j, 0.2, c);
    }
    return { paths: paths, foam: foam };
  }
  function drawFoam(g, L) {
    if (!L.foam) return;
    g.lineJoin = 'round';
    g.strokeStyle = 'rgba(255,255,255,0.16)'; g.lineWidth = 8; g.stroke(L.foam);
    g.strokeStyle = 'rgba(235,250,255,0.55)'; g.lineWidth = 3; g.stroke(L.foam);
  }
  function drawLand(g, L) {
    for (var n = 0; n < ORDER.length; n++) {
      if (!L.paths[n]) continue;
      g.fillStyle = Tex.pattern(TEXN[ORDER[n]]);
      g.fill(L.paths[n]);
    }
  }

  function variation(g, R, G, ra, rb, rA, rB) {
    var ok = gridImage(ra, rb, rA, rB, 2, function (fi, fj) {
      var ti = U.clamp(Math.round(fi), 0, w.W - 1), tj = U.clamp(Math.round(fj), 0, w.H - 1);
      var t = w.ter[tj * w.W + ti];
      if (t > T.SECA && t !== T.TERRA) return null;
      var n = (U.fbm(fi * 0.1, fj * 0.1, 5, 3) - 0.5) * 2.0;
      var m = (U.fbm(fi * 0.27 + 40, fj * 0.27, 9, 2) - 0.5) * 0.8;
      var v = U.clamp(n + m, -1, 1);
      if (t === T.TERRA) v *= 0.5;
      return v > 0 ? [255, 236, 140, Math.round(v * 60)] : [22, 66, 24, Math.round(-v * 75)];
    });
    if (!ok) return;
    g.save();
    g.globalCompositeOperation = 'source-atop';
    drawGrid(g, R, G, ra, rb, 2, 10);
    g.restore();
  }

  var DET = {};
  DET[T.GRAMA] = { n: 3.2, list: [['tufo', 0.66], ['flor', 0.22], ['pedrinha', 0.07], ['cogumelo', 0.05]] };
  DET[T.CAMPO] = { n: 5, list: [['tufoEscuro', 0.6], ['tufo', 0.2], ['flor', 0.17], ['cogumelo', 0.03]] };
  DET[T.SECA] = { n: 3, list: [['tufoSeco', 0.65], ['pedrinha', 0.2], ['graveto', 0.15]] };
  DET[T.AREIA] = { n: 1.4, list: [['concha', 0.35], ['pedrinha', 0.25], ['tufoSeco', 0.4]] };
  DET[T.TERRA] = { n: 2, list: [['pedrinha', 0.45], ['graveto', 0.2], ['tufo', 0.35]] };
  DET[T.PEDRA] = { n: 2.5, list: [['pedrinha', 0.55], ['tufo', 0.3], ['tufoSeco', 0.15]] };
  var FLOWERS = ['florBranca', 'florAmarela', 'florRoxa', 'florRosa'];

  function groundDetails(g, ra, rb, rA, rB) {
    var dets = Tex.details;
    for (var j = rb; j <= rB; j++) for (var i = ra; i <= rA; i++) {
      var k = j * w.W + i, t = w.ter[k], spec = DET[t];
      if (!spec) continue;
      var o = w.obj[k];
      if (o) { var kd = I[o.id].kind; if (kd !== 'natural') continue; }
      var h = U.hash2(i, j, 555), cnt = Math.floor(h * spec.n + 0.3);
      var flower = FLOWERS[Math.floor(U.hash2(i, j, 91) * 4)];
      for (var n = 0; n < cnt; n++) {
        var r1 = U.hash2(i * 7 + n, j * 13 - n, 77), r2 = U.hash2(i * 3 - n, j * 5 + n * 11, 78), r3 = U.hash2(i + n * 17, j - n * 3, 79);
        var name = spec.list[spec.list.length - 1][0], acc = 0;
        for (var q = 0; q < spec.list.length; q++) { acc += spec.list[q][1]; if (r3 < acc) { name = spec.list[q][0]; break; } }
        if (name === 'flor') name = flower;
        var d = dets[name];
        if (!d) continue;
        var u = (r1 - 0.5) * 0.76, v = (r2 - 0.5) * 0.76;
        var wx = (i - j + u - v) * 32, wy = (i + j + u + v) * 16;
        g.drawImage(d.c, wx - d.ox, wy - d.oy, d.w, d.h);
      }
    }
  }

  function isRoadAt(i, j) {
    if (i < 0 || j < 0 || i >= w.W || j >= w.H) return false;
    var o = w.obj[j * w.W + i];
    return !!(o && I[o.id].kind === 'road');
  }
  var DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  function roads(g, R, G, ra, rb, rA, rB) {
    var lists = { estrada: [], rua: [] }, any = false, i, j;
    for (j = rb; j <= rB; j++) for (i = ra; i <= rA; i++) {
      var o = w.obj[j * w.W + i];
      if (o && (o.id === 'estrada' || o.id === 'rua')) { lists[o.id].push([i, j]); any = true; }
    }
    if (!any) return;
    g.save();
    g.setTransform(R * 32, R * 16, -R * 32, R * 16, -R * G.ox, -R * G.oy);
    g.lineCap = 'round'; g.lineJoin = 'round';
    function segs(list, off) {
      var p = new Path2D();
      list.forEach(function (t) {
        var c = 0;
        DIRS.forEach(function (d) {
          if (!isRoadAt(t[0] + d[0], t[1] + d[1])) return;
          c++;
          var ox = d[1] !== 0 ? off : 0, oy = d[0] !== 0 ? off : 0;
          p.moveTo(t[0] + ox, t[1] + oy); p.lineTo(t[0] + d[0] * 0.52 + ox, t[1] + d[1] * 0.52 + oy);
        });
        if (!c && !off) { p.moveTo(t[0] - 0.12, t[1] - 0.12); p.lineTo(t[0] + 0.12, t[1] + 0.12); }
      });
      return p;
    }
    if (lists.estrada.length) {
      var pe = segs(lists.estrada, 0);
      g.strokeStyle = '#9c8452'; g.lineWidth = 0.74; g.stroke(pe);
      g.strokeStyle = '#8f6c45'; g.lineWidth = 0.64; g.stroke(pe);
      g.strokeStyle = Tex.pattern('estrada', 1 / 36); g.lineWidth = 0.56; g.stroke(pe);
      g.strokeStyle = 'rgba(110,80,45,0.22)'; g.lineWidth = 0.05;
      g.stroke(segs(lists.estrada, 0.13)); g.stroke(segs(lists.estrada, -0.13));
      g.strokeStyle = 'rgba(255,240,210,0.12)'; g.lineWidth = 0.12; g.stroke(pe);
    }
    if (lists.rua.length) {
      var pr = segs(lists.rua, 0);
      g.strokeStyle = '#6f7a5e'; g.lineWidth = 0.8; g.stroke(pr);
      g.strokeStyle = '#d8d2c6'; g.lineWidth = 0.74; g.stroke(pr);
      g.strokeStyle = '#8a857d'; g.lineWidth = 0.64; g.stroke(pr);
      g.strokeStyle = Tex.pattern('cobble'); g.lineWidth = 0.6; g.stroke(pr);
    }
    g.restore();
  }

  function shadows(g, R, G, cwPx, chPx) {
    if (!Sprites.shadowShapes) return;
    var a0 = Math.max(0, G.i0 - 3), b0 = Math.max(0, G.j0 - 3), a1 = Math.min(w.W - 1, G.i1 + 1), b1 = Math.min(w.H - 1, G.j1 + 1);
    var Rs = Math.max(0.25, R * 0.5);
    var sw = Math.ceil(G.wpx * Rs), sh = Math.ceil(G.hpx * Rs);
    if (!tmpShadow) tmpShadow = document.createElement('canvas');
    if (tmpShadow.width < sw || tmpShadow.height < sh) { tmpShadow.width = Math.max(sw, tmpShadow.width); tmpShadow.height = Math.max(sh, tmpShadow.height); }
    var tg = tmpShadow.getContext('2d');
    tg.setTransform(1, 0, 0, 1, 0, 0);
    tg.clearRect(0, 0, sw + 2, sh + 2);
    tg.setTransform(Rs, 0, 0, Rs, -G.ox * Rs, -G.oy * Rs);
    tg.fillStyle = '#000';
    var any = false;
    for (var j = b0; j <= b1; j++) for (var i = a0; i <= a1; i++) {
      var k = j * w.W + i, o = w.obj[k];
      if (!o) continue;
      var shapes = Sprites.shadowShapes(o.id, o.lv, Sprites.varFor(k, o.id));
      if (!shapes || !shapes.length) continue;
      var X = (i - j) * 32, Y = (i + j) * 16;
      tg.beginPath();
      for (var s = 0; s < shapes.length; s++) {
        var sp = shapes[s];
        if (sp.e) { tg.moveTo(X + sp.x + sp.rx, Y + sp.y); tg.ellipse(X + sp.x, Y + sp.y, sp.rx, sp.ry, 0, 0, Math.PI * 2); }
        else {
          tg.moveTo(X + sp.p[0], Y + sp.p[1]);
          for (var q = 2; q < sp.p.length; q += 2) tg.lineTo(X + sp.p[q], Y + sp.p[q + 1]);
          tg.closePath();
        }
      }
      tg.fill('nonzero');
      any = true;
    }
    if (!any) return;
    g.save();
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.globalAlpha = 0.3;
    if ('filter' in g) g.filter = 'blur(' + Math.max(0.6, 1.8 * R).toFixed(1) + 'px)';
    g.drawImage(tmpShadow, 0, 0, sw, sh, 0, 0, sw * R / Rs, sh * R / Rs);
    g.restore();
    void cwPx; void chPx;
  }

  function clipDiamond(g, G, ex) {
    g.beginPath();
    g.moveTo(G.top[0], G.top[1] - ex); g.lineTo(G.right[0] + ex * 2, G.right[1]);
    g.lineTo(G.bottom[0], G.bottom[1] + ex); g.lineTo(G.left[0] - ex * 2, G.left[1]); g.closePath();
    g.clip();
  }

  /* ---------------- Renderização de um bloco ---------------- */
  function render(c, lvl) {
    var t0 = performance.now();
    var G = geoms[c], R = LEVELS[lvl];
    var cw = Math.ceil(G.wpx * R), chh = Math.ceil(G.hpx * R);
    var old = entries[c][lvl], cvs;
    if (old) { cvs = old.cv; pixels -= cvs.width * cvs.height; }
    else cvs = document.createElement('canvas');
    if (cvs.width !== cw || cvs.height !== chh) { cvs.width = cw; cvs.height = chh; }
    var g = cvs.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, cw, chh);
    g.setTransform(R, 0, 0, R, -G.ox * R, -G.oy * R);
    var ra = Math.max(0, G.i0 - 2), rb = Math.max(0, G.j0 - 2), rA = Math.min(w.W - 1, G.i1 + 2), rB = Math.min(w.H - 1, G.j1 + 2);
    var water = false;
    for (var j = rb; j <= rB && !water; j++) for (var i = ra; i <= rA; i++) if (w.ter[j * w.W + i] === T.AGUA) { water = true; break; }
    var L = land(g, ra, rb, rA, rB);
    // camadas semitransparentes: recorte exato do losango (sem sobreposição entre blocos)
    g.save(); clipDiamond(g, G, 0);
    if (water) waterTint(g, R, G, ra, rb, rA, rB);
    drawFoam(g, L);
    g.restore();
    // camadas opacas: recorte um pouco maior para não deixar fresta entre blocos
    g.save(); clipDiamond(g, G, 1.6);
    drawLand(g, L);
    variation(g, R, G, ra, rb, rA, rB);
    if (R >= 0.5) groundDetails(g, ra, rb, rA, rB);
    roads(g, R, G, ra, rb, rA, rB);
    shadows(g, R, G, cw, chh);
    g.restore();
    var e = { cv: cvs, lvl: lvl, ver: ver[c], used: frameNo, ox: G.ox, oy: G.oy, wpx: cw / R, hpx: chh / R };
    entries[c][lvl] = e;
    pixels += cw * chh;
    stats.rendered++;
    stats.ms += performance.now() - t0;
    return e;
  }

  function best(c, want) {
    var es = entries[c], b = null, bs = -1e9;
    for (var l in es) {
      var e = es[l], li = e.lvl;
      var sc = (e.ver === ver[c] ? 100 : 0) - Math.abs(li - want) * 2 + (li > want ? 0.5 : 0);
      if (sc > bs) { bs = sc; b = e; }
    }
    return b;
  }

  function levelFor(r, maxL) {
    for (var n = 0; n < LEVELS.length; n++) if (LEVELS[n] >= r * 0.92) return Math.min(n, maxL);
    return Math.min(LEVELS.length - 1, maxL);
  }

  // desenha o terreno visível; view = retângulo do mundo; budget = ms por quadro para refinar blocos
  function draw(ctx, view, scale, maxL, budgetMs, budgetPx) {
    frameNo++;
    if (depthDirty) { computeDepth(); depthDirty = false; }
    var want = levelFor(scale, maxL);
    var vis = [];
    var cx = (view.x0 + view.x1) / 2, cy = (view.y0 + view.y1) / 2;
    for (var c = 0; c < geoms.length; c++) {
      var G = geoms[c];
      if (G.ox > view.x1 || G.ox + G.wpx < view.x0 || G.oy > view.y1 || G.oy + G.hpx < view.y0) continue;
      var dx = G.ox + G.wpx / 2 - cx, dy = G.oy + G.hpx / 2 - cy;
      vis.push([c, dx * dx + dy * dy]);
    }
    vis.sort(function (a, b) { return a[1] - b[1]; });
    var t0 = performance.now(), done = 0, quick = Math.min(want, 2), quickLeft = 3;
    for (var n = 0; n < vis.length; n++) {
      var cc = vis[n][0], e = entries[cc][want];
      if (e && e.ver === ver[cc]) { e.used = frameNo; continue; }
      var b = best(cc, want);
      if (!b) {
        // sem nada em cache: no máximo algumas versões rápidas por quadro (o resto usa o rascunho)
        if (quickLeft <= 0 || (done > 0 && performance.now() - t0 > budgetMs * 2)) continue;
        render(cc, quick); quickLeft--; done++;
        if (quick === want) continue;
      }
      if (done === 0 || performance.now() - t0 < budgetMs) { render(cc, want); done++; }
    }
    for (n = 0; n < vis.length; n++) {
      var bb = best(vis[n][0], want);
      if (!bb) { drawDraft(ctx, vis[n][0]); continue; }
      bb.used = frameNo;
      ctx.drawImage(bb.cv, bb.ox, bb.oy, bb.wpx, bb.hpx);
    }
    evict(budgetPx);
  }

  // cor média de cada textura do chão (para o rascunho combinar com o bloco final)
  function draftColors() {
    var sc = document.createElement('canvas'); sc.width = 32; sc.height = 16;
    var sg = sc.getContext('2d');
    return DATA.TERRAIN.map(function (t, n) {
      var tx = Tex.tex[TEXN[n]];
      if (tx) {
        try {
          sg.clearRect(0, 0, 32, 16); sg.drawImage(tx, 0, 0, 32, 16);
          var d = sg.getImageData(0, 0, 32, 16).data, r = 0, g = 0, b = 0, m = d.length / 4;
          for (var q = 0; q < d.length; q += 4) { r += d[q]; g += d[q + 1]; b += d[q + 2]; }
          return [r / m, g / m, b / m];
        } catch (e) { /* cai para a cor da tabela */ }
      }
      var h = t.color.replace('#', '');
      return [parseInt(h.substr(0, 2), 16) * 0.86, parseInt(h.substr(2, 2), 16) * 0.86, parseInt(h.substr(4, 2), 16) * 0.86];
    });
  }

  // rascunho de um bloco ainda não desenhado: um pixel por ladrilho (água transparente), esticado no losango
  var drafts = [], DRAFT = null;
  function drawDraft(ctx, c) {
    var d = drafts[c], G = geoms[c];
    if (!d || d.ver !== ver[c]) {
      if (!DRAFT) DRAFT = draftColors();
      var cv = d ? d.cv : document.createElement('canvas'), nw = G.i1 - G.i0 + 1, nh = G.j1 - G.j0 + 1;
      cv.width = nw; cv.height = nh;
      var g = cv.getContext('2d'), img = g.createImageData(nw, nh), px = img.data;
      for (var b = 0; b < nh; b++) for (var a = 0; a < nw; a++) {
        var k = (G.j0 + b) * w.W + G.i0 + a, t = w.ter[k], q = (b * nw + a) * 4, col = DRAFT[t];
        px[q] = col[0]; px[q + 1] = col[1]; px[q + 2] = col[2]; px[q + 3] = t === T.AGUA ? 0 : 255;
      }
      g.putImageData(img, 0, 0);
      d = drafts[c] = { cv: cv, ver: ver[c] };
    }
    ctx.save();
    ctx.transform(32, 16, -32, 16, 32 * (G.i0 - G.j0), 16 * (G.i0 + G.j0) - 16);
    ctx.drawImage(d.cv, 0, 0);
    ctx.restore();
  }

  function evict(budgetPx) {
    if (pixels <= budgetPx) return;
    var all = [];
    for (var c = 0; c < entries.length; c++) for (var l in entries[c]) { var e = entries[c][l]; if (e.used < frameNo) all.push([c, l, e]); }
    all.sort(function (a, b) { return a[2].used - b[2].used; });
    for (var n = 0; n < all.length && pixels > budgetPx; n++) {
      var x = all[n];
      pixels -= x[2].cv.width * x[2].cv.height;
      x[2].cv.width = x[2].cv.height = 0;
      delete entries[x[0]][x[1]];
    }
  }

  function depthAt(k) { return depth[k]; }

  return { invalidate: invalidate, draw: draw, depthAt: depthAt, stats: stats, LEVELS: LEVELS,
    memory: function () { return pixels; }, clear: function () { invalidate(-1); } };
})();

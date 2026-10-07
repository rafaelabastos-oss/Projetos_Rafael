/* Mundo Renda - renderização: câmera, água animada, terreno em blocos, objetos por profundidade,
   camadas de efeitos, luz, interface sobre o mapa e minimapa */
'use strict';

var Render = (function () {
  var TW = 64, TH = 32;
  var w = World.w, I = DATA.BY_ID, T = DATA.T;
  var canvas, ctx, cw = 0, ch = 0, dpr = 1;
  var cam = { x: 0, y: 1536, z: 1 };
  var ZMIN = 0.38, ZMAX = 2.6;
  var roadTiles = [], roadVersion = -1;
  var walkers = [], floats = [];
  var time = 0;
  var mini = null, miniCtx = null, miniOff = null, miniVersion = -1;
  var hero = null, scaleCap = 2;
  var water = null, islandShadow = null;

  function init(cv) {
    canvas = cv; ctx = canvas.getContext('2d');
    Tex.init();
    water = { a: Tex.freshPattern('water'), b: Tex.freshPattern('water'), blobs: Tex.freshPattern('waterBlobs') };
    World.onChange(function (k, prev, obj) {
      Terrain.invalidate(k);
      if (typeof Fx !== 'undefined') Fx.onTile(k, prev, obj);
    });
    buildIslandShadow();
    resize();
  }

  function quality() { return (Game.settings && Game.settings.quality) || 'alta'; }
  function high() { return quality() !== 'baixa'; }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, high() ? scaleCap : 1);
    oceanGrad = null;
    cw = window.innerWidth; ch = window.innerHeight;
    canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    canvas.style.width = cw + 'px'; canvas.style.height = ch + 'px';
    Sprites.setScale(Math.min(2.5, Math.max(1.25, dpr * 1.25)));
    if (typeof Light !== 'undefined') Light.resize(cw, ch, dpr);
    clampCam();
  }

  /* ---------------- Câmera e coordenadas ---------------- */
  function tileCenter(i, j) { return { x: (i - j) * TW / 2, y: (i + j) * TH / 2 }; }
  function screenToWorld(sx, sy) { return { x: (sx - cw / 2) / cam.z + cam.x, y: (sy - ch / 2) / cam.z + cam.y }; }
  function worldToScreen(x, y) { return { x: (x - cam.x) * cam.z + cw / 2, y: (y - cam.y) * cam.z + ch / 2 }; }
  function worldToTileF(x, y) { var a = x / (TW / 2), b = y / (TH / 2); return { i: (a + b) / 2, j: (b - a) / 2 }; }
  function screenToTile(sx, sy) {
    var p = screenToWorld(sx, sy), t = worldToTileF(p.x, p.y);
    var i = Math.round(t.i), j = Math.round(t.j);
    if (!World.inside(i, j)) return -1;
    return World.idx(i, j);
  }
  function clampCam() {
    var maxX = w.W * TW / 2, maxY = (w.W + w.H) * TH / 2;
    cam.x = U.clamp(cam.x, -maxX, maxX);
    cam.y = U.clamp(cam.y, 0, maxY);
    cam.z = U.clamp(cam.z, ZMIN, ZMAX);
  }
  function centerOn(i, j, z) { var p = tileCenter(i, j); cam.x = p.x; cam.y = p.y; if (z) cam.z = z; clampCam(); }
  function pan(dx, dy) { cam.x -= dx / cam.z; cam.y -= dy / cam.z; clampCam(); }
  function zoomAt(f, sx, sy) {
    var before = screenToWorld(sx, sy);
    cam.z = U.clamp(cam.z * f, ZMIN, ZMAX);
    var after = screenToWorld(sx, sy);
    cam.x += before.x - after.x; cam.y += before.y - after.y;
    clampCam();
  }
  function worldTransform() {
    var z = cam.z * dpr;
    ctx.setTransform(z, 0, 0, z, (cw / 2 - cam.x * cam.z) * dpr, (ch / 2 - cam.y * cam.z) * dpr);
  }

  function visibleRange(margin) {
    var vw = cw / cam.z, vh = ch / cam.z;
    var x0 = cam.x - vw / 2 - TW, x1 = cam.x + vw / 2 + TW, y0 = cam.y - vh / 2 - TH, y1 = cam.y + vh / 2 + (margin || TH);
    var imin = Math.floor((x0 / 32 + y0 / 16) / 2) - 1, imax = Math.ceil((x1 / 32 + y1 / 16) / 2) + 1;
    var jmin = Math.floor((y0 / 16 - x1 / 32) / 2) - 1, jmax = Math.ceil((y1 / 16 - x0 / 32) / 2) + 1;
    return { x0: x0, x1: x1, y0: y0, y1: y1, imin: Math.max(0, imin), imax: Math.min(w.W - 1, imax), jmin: Math.max(0, jmin), jmax: Math.min(w.H - 1, jmax) };
  }

  /* ---------------- Ilha e água ---------------- */
  function mapDiamond(c, grow) {
    var g = grow || 0;
    c.beginPath();
    c.moveTo(0, -16 - g);
    c.lineTo(w.W * 32 + g * 2, (w.W - 1) * 16);
    c.lineTo(0, (w.W + w.H - 2) * 16 + 16 + g);
    c.lineTo(-w.H * 32 - g * 2, (w.H - 1) * 16);
    c.closePath();
  }
  function blurDiamond(col, blur) {
    var c = document.createElement('canvas'); c.width = 300; c.height = 170;
    var g = c.getContext('2d');
    if ('filter' in g) g.filter = 'blur(' + blur + 'px)';
    g.fillStyle = col;
    g.beginPath(); g.moveTo(150, 20); g.lineTo(280, 85); g.lineTo(150, 150); g.lineTo(20, 85); g.closePath(); g.fill();
    return c;
  }
  function buildIslandShadow() {
    islandShadow = blurDiamond('rgba(0,0,0,0.85)', 9);
    shallow = blurDiamond('rgba(120,214,214,0.9)', 7);
  }
  var EDGE = 54, shallow = null, oceanGrad = null;
  // a vista inteira está sobre a ilha? (então o mar e as encostas nem aparecem)
  function insideMap(x, y) { var t = worldToTileF(x, y); return t.i > -0.5 && t.j > -0.5 && t.i < w.W - 0.5 && t.j < w.H - 0.5; }
  function allLand(v) { return insideMap(v.x0, v.y0) && insideMap(v.x1, v.y0) && insideMap(v.x0, v.y1 + EDGE) && insideMap(v.x1, v.y1 + EDGE); }
  function drawOcean(v) {
    var mw = (w.W + w.H) * 32, cy = (w.W + w.H - 2) * 8 + EDGE;
    if (!oceanGrad) {
      // gradiente elíptico (achatado 2:1 como o mapa): azul-turquesa perto da ilha, azul profundo longe
      oceanGrad = ctx.createRadialGradient(0, cy * 2, mw * 0.3, 0, cy * 2, mw * 1.25);
      oceanGrad.addColorStop(0, '#2b93c6'); oceanGrad.addColorStop(0.35, '#1f78ad'); oceanGrad.addColorStop(1, '#0c3a63');
    }
    ctx.save(); ctx.scale(1, 0.5);
    ctx.fillStyle = oceanGrad; ctx.fillRect(v.x0, v.y0 * 2, v.x1 - v.x0, (v.y1 - v.y0) * 2);
    ctx.restore();
    if (window.DOMMatrix && water.a.setTransform) {
      var t = time;
      water.blobs.setTransform(new DOMMatrix([1.6, 0, 0, 1.6, (t * 1.5) % 410, (t * 0.8) % 205]));
      ctx.globalAlpha = 0.5; ctx.fillStyle = water.blobs; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
      water.a.setTransform(new DOMMatrix([1.4, 0, 0, 1.4, (t * 4) % 358, (t * 1.5) % 179]));
      ctx.globalAlpha = high() ? 0.55 : 0.4; ctx.fillStyle = water.a; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
      ctx.globalAlpha = 1;
    }
    // faixa de água rasa em volta da base da ilha
    var mh = (w.W + w.H) * 16;
    ctx.globalAlpha = 0.55;
    ctx.drawImage(shallow, -w.H * 32 - mw * 0.16, -16 + EDGE - mh * 0.2, mw * 1.32, mh * 1.4);
    ctx.globalAlpha = 1;
    drawOceanSparkles(v);
  }
  function drawOceanSparkles(v) {
    if (!high() || cam.z < 0.55) return;
    ctx.fillStyle = '#ffffff';
    var gx0 = Math.floor(v.x0 / 80), gx1 = Math.ceil(v.x1 / 80), gy0 = Math.floor(v.y0 / 40), gy1 = Math.ceil(v.y1 / 40);
    for (var gy = gy0; gy <= gy1; gy++) for (var gx = gx0; gx <= gx1; gx++) {
      var h = U.hash2(gx + 5000, gy + 5000, 11), ph = (time * 0.3 + h * 13) % 1;
      if (ph > 0.1) continue;
      var x = (gx + U.hash2(gx, gy, 12)) * 80, y = (gy + U.hash2(gx, gy, 13)) * 40;
      if (insideMap(x, y - EDGE)) continue;
      var a = Math.sin(ph / 0.1 * Math.PI), s = 1.4 + a * 2;
      ctx.globalAlpha = a * 0.8;
      ctx.beginPath(); ctx.moveTo(x - s * 1.8, y); ctx.lineTo(x, y - s * 0.35); ctx.lineTo(x + s * 1.8, y); ctx.lineTo(x, y + s * 0.35); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  function drawIslandBase(v) {
    if (allLand(v)) return false;
    drawOcean(v);
    var mw = (w.W + w.H) * 32, mh = (w.W + w.H) * 16;
    ctx.globalAlpha = 0.4;
    ctx.drawImage(islandShadow, -w.H * 32 - mw * 0.086 + 18, -16 + EDGE + 10 - mh * 0.12, mw * 1.172, mh * 1.21);
    ctx.globalAlpha = 1;
    drawEdges(v);
    return true;
  }
  function drawWater(v) {
    ctx.save();
    mapDiamond(ctx, 0);
    ctx.clip();
    ctx.fillStyle = '#2b8ccc';
    ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
    if (window.DOMMatrix && water.a.setTransform) {
      var t = time;
      water.blobs.setTransform(new DOMMatrix([1, 0, 0, 1, (t * 2.5) % 256, (t * 1.2) % 128]));
      ctx.fillStyle = water.blobs; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
      if (high()) {
        water.a.setTransform(new DOMMatrix([1, 0, 0, 1, (t * 6) % 256, (t * 2) % 128]));
        ctx.fillStyle = water.a; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
        water.b.setTransform(new DOMMatrix([-1.3, 0, 0, 1.3, (-t * 4.5) % 333, (t * 3.2) % 166]));
        ctx.globalAlpha = 0.55; ctx.fillStyle = water.b; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0); ctx.globalAlpha = 1;
      } else {
        ctx.fillStyle = water.a; ctx.fillRect(v.x0, v.y0, v.x1 - v.x0, v.y1 - v.y0);
      }
    }
    ctx.restore();
  }

  function drawSparkles(v) {
    if (!high() || cam.z < 0.75) return;
    ctx.fillStyle = '#ffffff';
    for (var j = v.jmin; j <= v.jmax; j++) for (var i = v.imin; i <= v.imax; i++) {
      var k = j * w.W + i;
      if (w.ter[k] !== T.AGUA || w.obj[k]) continue;
      var h = U.hash2(i, j, 3), ph = (time * 0.35 + h * 17) % 1;
      if (ph > 0.12) continue;
      var a = Math.sin(ph / 0.12 * Math.PI);
      var u = (U.hash2(i, j, 4) - 0.5) * 0.7, vv = (U.hash2(i, j, 5) - 0.5) * 0.7;
      var x = (i - j + u - vv) * 32, y = (i + j + u + vv) * 16, s = 1.2 + a * 1.8;
      ctx.globalAlpha = a * 0.9;
      ctx.beginPath(); ctx.moveTo(x - s * 1.8, y); ctx.lineTo(x, y - s * 0.35); ctx.lineTo(x + s * 1.8, y); ctx.lineTo(x, y + s * 0.35); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x, y - s); ctx.lineTo(x + s * 0.3, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s * 0.3, y); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // laterais da ilha (falésia com camadas de terra), degradê úmido perto do mar, espuma e cachoeiras
  var strataL = null, strataR = null, edgeGrad = {};
  function drawEdges(v) {
    if (!strataL) {
      strataL = Tex.freshPattern('strata'); strataR = Tex.freshPattern('strata');
      // cisalhamento acompanhando a borda + deslocamento para a grama ficar exatamente no topo
      if (strataL.setTransform && window.DOMMatrix) {
        strataL.setTransform(new DOMMatrix([1, 0.5, 0, 1, 0, 32 * (w.H - 1) + 16]));
        strataR.setTransform(new DOMMatrix([1, -0.5, 0, 1, 0, 32 * (w.W - 1) + 16]));
      }
    }
    if (v.imax === w.W - 1) edgeSide(1, Math.max(0, v.jmin), Math.min(w.H - 1, v.jmax));
    if (v.jmax === w.H - 1) edgeSide(-1, Math.max(0, v.imin), Math.min(w.W - 1, v.imax));
  }
  function edgeSide(sd, a0, a1) {
    if (a1 < a0) return;
    var D = EDGE, xa, ya, xb, yb, top;
    if (sd > 0) { var i = w.W - 1; xa = (i - a0) * 32 + 32; ya = (i + a0) * 16; xb = (i - a1) * 32; yb = (i + a1) * 16 + 16; top = 32 * i + 16; }
    else { var j = w.H - 1; xa = (a0 - j) * 32 - 32; ya = (a0 + j) * 16; xb = (a1 - j) * 32; yb = (a1 + j) * 16 + 16; top = 32 * j + 16; }
    ctx.beginPath(); ctx.moveTo(xa, ya - 0.5); ctx.lineTo(xb, yb - 0.5); ctx.lineTo(xb, yb + D); ctx.lineTo(xa, ya + D); ctx.closePath();
    ctx.fillStyle = sd > 0 ? strataR : strataL; ctx.fill();
    // degradê vertical medido a partir da borda de cima (inclinada): transformação de cisalhamento deixa a borda reta
    ctx.save(); ctx.clip();
    ctx.transform(1, sd > 0 ? -0.5 : 0.5, 0, 1, 0, 0);
    var key = sd + '_' + top;
    if (!edgeGrad[key]) {
      var gr = ctx.createLinearGradient(0, top, 0, top + D);
      var sh = sd > 0 ? 0.26 : 0.06;
      gr.addColorStop(0, 'rgba(255,236,190,0.18)'); gr.addColorStop(0.06, 'rgba(0,0,0,' + sh + ')');
      gr.addColorStop(0.62, 'rgba(10,20,25,' + (sh + 0.12) + ')'); gr.addColorStop(0.86, 'rgba(15,45,60,' + (sh + 0.3) + ')'); gr.addColorStop(1, 'rgba(10,50,70,' + (sh + 0.45) + ')');
      edgeGrad[key] = gr;
    }
    ctx.fillStyle = edgeGrad[key];
    ctx.fillRect(Math.min(xa, xb) - 4, top - 4, Math.abs(xb - xa) + 8, D + 8);
    ctx.restore();
    // cachoeiras onde rio/lago encontra a borda
    var fallT = time * 60, n, k, wx, wy;
    for (n = a0; n <= a1; n++) {
      k = sd > 0 ? n * w.W + (w.W - 1) : (w.H - 1) * w.W + n;
      if (w.ter[k] !== T.AGUA) continue;
      var ii = sd > 0 ? w.W - 1 : n, jj = sd > 0 ? n : w.H - 1;
      wx = (ii - jj) * 32; wy = (ii + jj) * 16;
      ctx.beginPath();
      if (sd > 0) { ctx.moveTo(wx + 32.5, wy); ctx.lineTo(wx - 0.5, wy + 16.3); ctx.lineTo(wx - 0.5, wy + 16 + D); ctx.lineTo(wx + 32.5, wy + D); }
      else { ctx.moveTo(wx - 32.5, wy); ctx.lineTo(wx + 0.5, wy + 16.3); ctx.lineTo(wx + 0.5, wy + 16 + D); ctx.lineTo(wx - 32.5, wy + D); }
      ctx.closePath();
      waterfall(wx, wy, sd, D, fallT);
    }
    // espuma batendo na base da falésia
    var len = Math.abs(xb - xa), steps = Math.max(2, Math.ceil(len / 10)), dx = (xb - xa) / steps, dy = (yb - ya) / steps;
    for (var layer = 0; layer < 2; layer++) {
      ctx.beginPath();
      for (n = 0; n <= steps; n++) {
        var x = xa + dx * n, y = ya + dy * n + D + (layer ? 3.5 : 1);
        var wv = Math.sin(time * 1.6 + x * 0.045 + layer * 2) * 1.3 + Math.sin(time * 0.9 - x * 0.021) * 0.9;
        if (n) ctx.lineTo(x, y + wv); else ctx.moveTo(x, y + wv);
      }
      ctx.strokeStyle = layer ? 'rgba(255,255,255,' + (0.16 + 0.08 * Math.sin(time * 1.3)).toFixed(3) + ')' : 'rgba(255,255,255,0.62)';
      ctx.lineWidth = layer ? 6 : 2.2;
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.stroke();
    }
  }
  function waterfall(wx, wy, side, depth, ft) {
    var g = ctx;
    g.save(); g.clip();
    g.fillStyle = side > 0 ? '#2a7bb3' : '#3389c2'; g.fillRect(wx - 34, wy - 2, 68, depth + 22);
    g.strokeStyle = 'rgba(255,255,255,0.55)'; g.lineWidth = 1.2;
    for (var n = 0; n < 9; n++) {
      var x = wx + side * (n * 3.6 + 1);
      var off = (ft + n * 13) % 30;
      for (var y = -30 + off; y < depth + 20; y += 30) {
        var yy = wy + (side > 0 ? (32 - (x - wx)) * 0.5 : (x - wx + 32) * 0.5) + y;
        g.beginPath(); g.moveTo(x, yy); g.lineTo(x, yy + 12); g.stroke();
      }
    }
    g.restore();
    g.fillStyle = 'rgba(255,255,255,0.4)';
    g.beginPath(); g.ellipse(wx + side * 16, wy + 8 + depth, 20, 5, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = 'rgba(255,255,255,0.25)';
    g.beginPath(); g.ellipse(wx + side * 16, wy + 9 + depth, 28 + Math.sin(time * 5) * 2, 7, 0, 0, Math.PI * 2); g.fill();
  }

  /* ---------------- Moradores (provisório até o módulo de pessoas) ---------------- */
  var SHIRTS = ['#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#1abc9c', '#e67e22', '#ecf0f1', '#ff6fa5', '#2ecc71'];
  function updateRoads() {
    if (roadVersion === w.mapVersion) return;
    roadVersion = w.mapVersion;
    World.recompute();
    roadTiles = [];
    for (var k = 0; k < w.N; k++) if (w.roadConn[k]) roadTiles.push(k);
  }
  function updateWalkers(dt, s) {
    var rep = Sim.report();
    var dark = s ? darkness(s.t) : 0;
    var want = 0;
    if (roadTiles.length > 1 && rep && s) {
      want = Math.min(high() ? 60 : 20, Math.floor(rep.employed * 0.7 + rep.c.houses * 0.8 + 2));
      want = Math.floor(want * (1 - dark * 0.7));
    } else if (roadTiles.length > 1 && !s) want = 25;
    while (walkers.length < want) {
      var k = roadTiles[Math.floor(Math.random() * roadTiles.length)];
      walkers.push({ i: World.iOf(k), j: World.jOf(k), ti: World.iOf(k), tj: World.jOf(k), pk: -1, di: 0, dj: 1,
        sp: 0.8 + Math.random() * 0.6, shirt: SHIRTS[Math.floor(Math.random() * SHIRTS.length)], ph: Math.random() * 6, say: null, sayT: 0 });
    }
    if (walkers.length > want) walkers.length = want;
    for (var n = 0; n < walkers.length; n++) {
      var a = walkers[n];
      var tk = World.idx(a.ti, a.tj);
      if (!World.isRoad(w.obj[tk])) { var nk = roadTiles[Math.floor(Math.random() * roadTiles.length)]; a.i = a.ti = World.iOf(nk); a.j = a.tj = World.jOf(nk); continue; }
      var di = a.ti - a.i, dj = a.tj - a.j, dist = Math.sqrt(di * di + dj * dj), step = a.sp * dt;
      a.ph += dt * 10;
      if (a.sayT > 0) a.sayT -= dt;
      if (dist <= step) {
        a.i = a.ti; a.j = a.tj;
        var opts = [], ck = World.idx(a.ti, a.tj);
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (d) {
          var ii = a.ti + d[0], jj = a.tj + d[1];
          if (World.inside(ii, jj) && World.isRoad(w.obj[World.idx(ii, jj)])) opts.push(World.idx(ii, jj));
        });
        if (opts.length > 1 && a.pk >= 0) opts = opts.filter(function (x) { return x !== a.pk; });
        if (opts.length) {
          var nx = opts[Math.floor(Math.random() * opts.length)]; a.pk = ck;
          a.ti = World.iOf(nx); a.tj = World.jOf(nx);
        }
      } else { a.i += di / dist * step; a.j += dj / dist * step; }
    }
  }

  function addFloat(k, text, color) {
    if (floats.length > 40) return;
    var p = tileCenter(World.iOf(k), World.jOf(k));
    floats.push({ x: p.x, y: p.y - 30, text: text, color: color || '#fff', t: 0 });
  }
  function dayFloats(report) {
    var vis = visibleRange(40);
    var count = 0;
    report.outputs.forEach(function (b) {
      if (count > 14) return;
      var i = World.iOf(b.k), j = World.jOf(b.k), p = tileCenter(i, j);
      if (p.x < vis.x0 || p.x > vis.x1 || p.y < vis.y0 || p.y > vis.y1) return;
      var info = report.st[b.k];
      if (!info) return;
      var txt = '';
      for (var g in info.out) { if (info.out[g] >= 1) { txt = '+' + Math.round(info.out[g]) + ' ' + DATA.GOODS[g].icon; break; } }
      if (!txt && info.inc >= 1) txt = '+' + U.shortMoney(info.inc);
      if (txt) { addFloat(b.k, txt, '#fff'); count++; }
    });
    if (w.hq >= 0 && report) {
      var pr = report.profit;
      addFloat(w.hq, (pr >= 0 ? '+' : '') + U.shortMoney(pr), pr >= 0 ? '#7dffa1' : '#ff8a8a');
    }
    if (typeof Fx !== 'undefined') Fx.dayEnd(report, vis);
  }

  /* ---------------- Dia e noite ---------------- */
  function darkness(t) {
    var h = t * 24;
    if (h >= 6.5 && h < 18) return 0;
    if (h >= 18 && h < 20) return (h - 18) / 2;
    if (h >= 20 || h < 4.5) return 1;
    return 1 - (h - 4.5) / 2;
  }

  /* ---------------- Desenho principal ---------------- */
  function draw(dt) {
    time += dt;
    var s = Game.s, ui = Game.ui;
    updateRoads();
    var simDt = dt * (s ? (s.speed > 0 ? Math.min(2, s.speed) : 0) : 1);
    if (typeof People !== 'undefined') People.update(simDt, s, roadTiles, time);
    else updateWalkers(simDt, s);
    if (typeof Fx !== 'undefined') Fx.update(dt, s, time);

    worldTransform();
    ctx.imageSmoothingEnabled = true;
    var v = visibleRange(TH);
    drawIslandBase(v);
    drawWater(v);
    Terrain.draw(ctx, v, cam.z * dpr, high() ? 7 : 5, high() ? 7 : 4, high() ? 12e6 : 6e6);
    drawSparkles(v);
    if (ui && s) drawGroundOverlays(v, ui);

    // objetos e pessoas em ordem de profundidade
    var vo = visibleRange(130);
    var dmin = vo.imin + vo.jmin, dmax = vo.imax + vo.jmax;
    var buckets = {};
    var movers = typeof People !== 'undefined' ? People.list() : walkers;
    for (var n = 0; n < movers.length; n++) {
      var a = movers[n], dk = Math.round(a.i) + Math.round(a.j);
      (buckets[dk] || (buckets[dk] = [])).push(a);
    }
    var dark = s && Game.settings.daynight ? darkness(s.t) : 0;
    var lights = [], ems = [];
    var fx = typeof Fx !== 'undefined' ? Fx : null;
    for (var d = dmin; d <= dmax; d++) {
      var ia = Math.max(vo.imin, d - vo.jmax), ib = Math.min(vo.imax, d - vo.jmin);
      for (var i = ia; i <= ib; i++) {
        var j = d - i, k = j * w.W + i, o = w.obj[k];
        if (!o || o.id === 'estrada' || o.id === 'rua') continue;
        var wx = (i - j) * 32, wy = (i + j) * 16;
        if (wx < vo.x0 || wx > vo.x1 || wy < vo.y0 || wy > vo.y1) continue;
        var spr = o.id === 'ponte' ? Sprites.road('ponte', bridgeMask(i, j)) : Sprites.object(o.id, o.lv, Sprites.varFor(k, o.id), time, k);
        if (ui && ui.moving === k) ctx.globalAlpha = 0.35;
        if (!(fx && fx.drawGrow(ctx, k, spr, wx, wy))) ctx.drawImage(spr.c, wx - spr.ox, wy - spr.oy, spr.w, spr.h);
        ctx.globalAlpha = 1;
        if (spr.anim && Sprites.drawAnim) Sprites.drawAnim(ctx, spr, wx, wy, time, k);
        if (fx && spr.emit && spr.emit.length && s) fx.smoke(k, spr, wx, wy);
        if (dark > 0.02) {
          if (spr.wins && spr.wins.length) ems.push([spr, wx, wy]);
          if (spr.lights) for (var q = 0; q < spr.lights.length; q++) { var L = spr.lights[q]; lights.push([wx + L[0], wy + L[1], L[2], spr, wx, wy, L[3] || null]); }
          else {
            var it = I[o.id];
            if (it.light) lights.push([wx + 6, wy - 24, 1.3]);
            else if (it.kind === 'house' || it.kind === 'hq' || it.kind === 'service' || it.kind === 'shop' || it.kind === 'processor') lights.push([wx, wy - 10, 0.8]);
          }
        }
      }
      var bk = buckets[d];
      if (bk) for (n = 0; n < bk.length; n++) {
        if (typeof People !== 'undefined') People.draw(ctx, bk[n], time);
        else drawPerson(bk[n]);
      }
    }
    if (hero) drawHero();
    if (fx) fx.drawWorld(ctx, vo, cam.z);

    if (typeof Light !== 'undefined' && s && Game.settings.daynight) {
      if (dark > 0.02 && typeof People !== 'undefined' && People.lights) People.lights(lights);
      if (fx) fx.drawSky(ctx, vo, cam.z, time);
      Light.apply(ctx, s.t, lights, ems, cam, dpr, time, high());
      worldTransform();
    } else {
      if (fx) fx.drawSky(ctx, vo, cam.z, time);
      if (dark > 0) simpleNight(dark, lights);
    }

    if (ui && s) drawTopOverlays(vo, ui);
    if (typeof People !== 'undefined') People.drawSpeech(ctx);
    drawFloats(dt);

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (fx) fx.drawScreen(ctx, cw, ch, dpr, time);
    if (typeof Light !== 'undefined' && high()) Light.vignette(ctx, canvas.width, canvas.height);
    drawMini();
  }

  function bridgeMask(i, j) {
    var m = 0;
    if (j > 0 && World.isRoad(w.obj[(j - 1) * w.W + i])) m |= 1;
    if (i < w.W - 1 && World.isRoad(w.obj[j * w.W + i + 1])) m |= 2;
    if (j < w.H - 1 && World.isRoad(w.obj[(j + 1) * w.W + i])) m |= 4;
    if (i > 0 && World.isRoad(w.obj[j * w.W + i - 1])) m |= 8;
    return m;
  }

  var glow = null;
  function simpleNight(dark, lights) {
    if (!glow) {
      glow = document.createElement('canvas'); glow.width = glow.height = 64;
      var g = glow.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, 'rgba(255,214,140,1)'); gr.addColorStop(0.4, 'rgba(255,190,100,0.45)'); gr.addColorStop(1, 'rgba(255,170,80,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = 'rgba(10,16,48,' + (dark * 0.5).toFixed(3) + ')';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    worldTransform();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = dark * 0.55;
    for (var n = 0; n < lights.length; n++) { var L = lights[n], r = 26 * L[2]; ctx.drawImage(glow, L[0] - r, L[1] - r, r * 2, r * 2); }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }

  function drawFloats(dt) {
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = 'bold 12px sans-serif';
    for (var n = floats.length - 1; n >= 0; n--) {
      var f = floats[n];
      f.t += dt;
      if (f.t > 1.8) { floats.splice(n, 1); continue; }
      ctx.globalAlpha = f.t < 1.2 ? 1 : 1 - (f.t - 1.2) / 0.6;
      ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 4; ctx.shadowOffsetY = 1;
      ctx.fillStyle = f.color; ctx.fillText(f.text, f.x, f.y - f.t * 18);
    }
    ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.globalAlpha = 1;
  }

  function tileDiamond(k, fill, stroke, lw) {
    var p = tileCenter(World.iOf(k), World.jOf(k));
    Sprites.diamondPath(ctx, p.x, p.y, 0.96);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1.5; ctx.stroke(); }
  }

  function radiusDiamond(k, r, color) {
    var i = World.iOf(k), j = World.jOf(k);
    var top = tileCenter(i - r, j - r), right = tileCenter(i + r, j - r), bot = tileCenter(i + r, j + r), left = tileCenter(i - r, j + r);
    ctx.beginPath();
    ctx.moveTo(top.x, top.y - 16); ctx.lineTo(right.x + 32, right.y); ctx.lineTo(bot.x, bot.y + 16); ctx.lineTo(left.x - 32, left.y); ctx.closePath();
    ctx.fillStyle = color || 'rgba(255,255,255,0.12)'; ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]); ctx.stroke(); ctx.setLineDash([]);
  }

  function drawGroundOverlays(v, ui) {
    var tool = ui.tool;
    if (tool && tool !== 'info' && Game.settings.grid) {
      ctx.strokeStyle = 'rgba(255,255,255,0.13)'; ctx.lineWidth = 1 / cam.z;
      ctx.beginPath();
      for (var i = v.imin; i <= v.imax + 1; i++) { var a = tileCenter(i - 0.5, v.jmin - 0.5), b = tileCenter(i - 0.5, v.jmax + 0.5); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); }
      for (var j = v.jmin; j <= v.jmax + 1; j++) { var c = tileCenter(v.imin - 0.5, j - 0.5), d = tileCenter(v.imax + 0.5, j - 0.5); ctx.moveTo(c.x, c.y); ctx.lineTo(d.x, d.y); }
      ctx.stroke();
    }
    if (ui.linePath && ui.linePath.length) {
      ui.linePath.forEach(function (e) { tileDiamond(e.k, e.ok ? 'rgba(80,255,140,0.35)' : 'rgba(255,80,80,0.35)', e.ok ? 'rgba(80,255,140,0.9)' : 'rgba(255,80,80,0.9)', 1); });
    }
    if (ui.selected >= 0 && ui.selected !== undefined) {
      var pulse = 0.5 + Math.sin(time * 5) * 0.3;
      tileDiamond(ui.selected, 'rgba(255,220,80,' + (pulse * 0.35).toFixed(2) + ')', 'rgba(255,220,80,0.95)', 2);
      var so = w.obj[ui.selected];
      if (so) { var sit = I[so.id]; var rr = (sit.eff && sit.eff.r) || (sit.beauty && sit.br) || 0; if (rr) radiusDiamond(ui.selected, rr, 'rgba(255,230,120,0.10)'); }
    }
    if (ui.hover >= 0 && tool && tool !== 'info' && !(ui.linePath && ui.linePath.length)) {
      var it = I[ui.moving >= 0 ? w.obj[ui.moving] && w.obj[ui.moving].id : tool];
      var ok = ui.hoverOk;
      if (it && it.kind !== 'road' && it.kind !== 'terrain' && it.kind !== 'clear') {
        var rad = (it.eff && it.eff.r) || (it.beauty && it.br) || (it.houses ? 5 : 0);
        if (rad) radiusDiamond(ui.hover, rad, 'rgba(255,255,255,0.10)');
      }
      tileDiamond(ui.hover, ok ? 'rgba(80,255,140,0.30)' : 'rgba(255,80,80,0.35)', ok ? 'rgba(80,255,140,0.95)' : 'rgba(255,80,80,0.95)', 1.5);
    }
  }

  function drawTopOverlays(v, ui) {
    var tool = ui.tool;
    if (ui.hover >= 0 && tool && (ui.moving >= 0 || (I[tool] && I[tool].draw))) {
      var id = ui.moving >= 0 ? (w.obj[ui.moving] && w.obj[ui.moving].id) : tool;
      var lv = ui.moving >= 0 && w.obj[ui.moving] ? w.obj[ui.moving].lv : 1;
      if (id) {
        var p = tileCenter(World.iOf(ui.hover), World.jOf(ui.hover));
        var spr = Sprites.object(id, lv, 1, time, ui.hover);
        ctx.globalAlpha = 0.72;
        ctx.drawImage(spr.c, p.x - spr.ox, p.y - spr.oy, spr.w, spr.h);
        ctx.globalAlpha = 1;
      }
    }
    if (Sprites.drawBadges) Sprites.drawBadges(ctx, v, cam.z, time);
    if (Game.settings.alerts && cam.z > 0.6) {
      var blink = Math.sin(time * 4) > -0.3;
      if (blink) for (var j = v.jmin; j <= v.jmax; j++) for (var i = v.imin; i <= v.imax; i++) {
        var k = j * w.W + i, o = w.obj[k];
        if (!o || !World.isBuilding(o)) continue;
        var st = Sim.status(k);
        if (!st || (st.alert !== 'road' && st.alert !== 'input')) continue;
        var c = tileCenter(i, j);
        if (c.x < v.x0 || c.x > v.x1 || c.y < v.y0 || c.y > v.y1) continue;
        var spr2 = Sprites.object(o.id, o.lv, Sprites.varFor(k, o.id), time, k);
        var icon = st.alert === 'road' ? '🛣️' : '📦';
        var y = c.y - (spr2.top || 50) - 26;
        ctx.fillStyle = st.alert === 'road' ? 'rgba(220,60,60,0.92)' : 'rgba(240,160,30,0.92)';
        roundRect(c.x - 10, y - 9, 20, 18, 6); ctx.fill();
        ctx.beginPath(); ctx.moveTo(c.x - 4, y + 8); ctx.lineTo(c.x + 4, y + 8); ctx.lineTo(c.x, y + 13); ctx.fill();
        ctx.font = '11px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff'; ctx.fillText(icon, c.x, y + 1);
      }
    }
  }

  function roundRect(x, y, wd, ht, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + wd - r, y); ctx.quadraticCurveTo(x + wd, y, x + wd, y + r);
    ctx.lineTo(x + wd, y + ht - r); ctx.quadraticCurveTo(x + wd, y + ht, x + wd - r, y + ht);
    ctx.lineTo(x + r, y + ht); ctx.quadraticCurveTo(x, y + ht, x, y + ht - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }

  function speech(x, y, text) {
    ctx.font = 'bold 7px sans-serif';
    var tw = ctx.measureText(text).width + 9, bx = x - tw / 2, by = y - 30;
    ctx.fillStyle = 'rgba(0,0,0,0.22)';
    roundRect(bx + 0.8, by + 1.2, tw, 13, 6.5); ctx.fill();
    ctx.fillStyle = '#fffdf6';
    roundRect(bx, by, tw, 13, 6.5); ctx.fill();
    ctx.beginPath(); ctx.moveTo(x - 3, by + 12.5); ctx.lineTo(x + 2, by + 12.5); ctx.lineTo(x - 1, by + 17); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#1d2b25'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(text, x, by + 6.8);
  }

  function drawPerson(a) {
    var p = tileCenter(a.i, a.j);
    var bob = Math.abs(Math.sin(a.ph)) * 1.2;
    var off = ((a.sp * 37) % 1 - 0.5) * 10;
    var x = p.x + off, y = p.y - bob + off * 0.3;
    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    ctx.beginPath(); ctx.ellipse(x, p.y + 0.5 + off * 0.3, 3, 1.3, 0, 0, Math.PI * 2); ctx.fill();
    Sprites.person(ctx, x, y, a.shirt);
    if (a.say && a.sayT > 0) speech(x, y, a.say);
  }
  function drawHero() {
    var hp = tileCenter(hero.i, hero.j);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(hp.x, hp.y + 1, 9, 4.5, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = hero.shirt; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.ellipse(hp.x, hp.y + 1, 11.5, 5.8, 0, 0, Math.PI * 2); ctx.stroke();
    if (typeof People !== 'undefined') People.drawHero(ctx, hero, time);
    else {
      var bob = Math.abs(Math.sin(hero.ph)) * 1.2;
      ctx.save(); ctx.translate(hp.x, hp.y - bob); ctx.scale(1.5, 1.5);
      Sprites.person(ctx, 0, 0, hero.shirt);
      ctx.fillStyle = hero.cap; ctx.fillRect(-2, -10.2, 4, 1.6);
      ctx.restore();
    }
  }

  /* ---------------- Minimapa ---------------- */
  function setMini(cv) { mini = cv; miniCtx = cv.getContext('2d'); }
  function drawMini() {
    if (!mini || mini.offsetParent === null) return;
    var mw = mini.clientWidth, mh = mini.clientHeight;
    if (!mw) return;
    var md = Math.min(window.devicePixelRatio || 1, 2);
    if (mini.width !== Math.round(mw * md)) { mini.width = Math.round(mw * md); mini.height = Math.round(mh * md); miniVersion = -1; }
    if (!miniOff) { miniOff = document.createElement('canvas'); miniOff.width = w.W; miniOff.height = w.H; }
    if (miniVersion !== w.mapVersion) {
      miniVersion = w.mapVersion;
      var oc = miniOff.getContext('2d'), img = oc.createImageData(w.W, w.H), dta = img.data;
      var cols = DATA.TERRAIN.map(function (t) { var c = t.color.replace('#', ''); return [parseInt(c.substr(0, 2), 16), parseInt(c.substr(2, 2), 16), parseInt(c.substr(4, 2), 16)]; });
      var br = Game.s ? Game.s.project.color : '#2e86de', bc = [parseInt(br.substr(1, 2), 16), parseInt(br.substr(3, 2), 16), parseInt(br.substr(5, 2), 16)];
      for (var k = 0; k < w.N; k++) {
        var c = cols[w.ter[k]], o = w.obj[k];
        if (w.ter[k] === T.AGUA) { var dd = Terrain.depthAt(k); c = [Math.max(10, 70 - dd * 9), Math.max(60, 170 - dd * 16), Math.max(110, 225 - dd * 14)]; }
        if (o) {
          var kd = I[o.id].kind;
          if (kd === 'road') c = [214, 190, 140];
          else if (kd === 'natural' || kd === 'decor') c = o.id === 'n_pedra' ? [120, 120, 120] : [40, 110, 50];
          else if (kd === 'house') c = [245, 230, 200];
          else c = bc;
          if (o.id === 'hq') c = [255, 230, 80];
        }
        dta[k * 4] = c[0]; dta[k * 4 + 1] = c[1]; dta[k * 4 + 2] = c[2]; dta[k * 4 + 3] = 255;
      }
      oc.putImageData(img, 0, 0);
    }
    var g = miniCtx;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, mini.width, mini.height);
    var sx = mini.width / (2 * w.W), sy = mini.height / (2 * w.H);
    g.setTransform(sx, sy, -sx, sy, mini.width / 2, 0);
    g.imageSmoothingEnabled = false;
    g.drawImage(miniOff, 0, 0);
    g.setTransform(1, 0, 0, 1, 0, 0);
    var vw = cw / cam.z, vh = ch / cam.z;
    var x0 = (cam.x - vw / 2) * sx / 32 + mini.width / 2, y0 = (cam.y - vh / 2) * sy / 16;
    g.strokeStyle = '#fff'; g.lineWidth = 1.5 * md;
    g.strokeRect(x0, y0, vw * sx / 32, vh * sy / 16);
  }
  function miniToWorld(mx, my) {
    var sx = mini.clientWidth / (2 * w.W), sy = mini.clientHeight / (2 * w.H);
    return { x: (mx - mini.clientWidth / 2) * 32 / sx, y: my * 16 / sy };
  }

  function setHero(h) { hero = h; }

  function downscale() {
    var cur = Math.min(window.devicePixelRatio || 1, scaleCap);
    if (!high() || cur <= 1) return false;
    scaleCap = Math.max(1, cur - 0.25);
    resize();
    return true;
  }

  return {
    init: init, resize: resize, draw: draw, cam: cam, screenToTile: screenToTile, screenToWorld: screenToWorld,
    worldToScreen: worldToScreen, worldToTileF: worldToTileF, tileCenter: tileCenter, centerOn: centerOn, pan: pan,
    zoomAt: zoomAt, clampCam: clampCam, addFloat: addFloat, dayFloats: dayFloats, setMini: setMini, miniToWorld: miniToWorld,
    walkers: function () { return typeof People !== 'undefined' ? People.list() : walkers; }, setHero: setHero, darkness: darkness,
    downscale: downscale, resetScale: function () { scaleCap = 2; resize(); }, speech: speech, roundRect: roundRect,
    size: function () { return { w: cw, h: ch }; }, high: high, time: function () { return time; },
    visibleRange: visibleRange,
    resetWalkers: function () { walkers = []; floats = []; roadVersion = -1; miniVersion = -1; if (typeof People !== 'undefined') People.reset(); if (typeof Fx !== 'undefined') Fx.reset(); }
  };
})();

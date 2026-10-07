/* Mundo Renda - renderização isométrica, câmera, moradores andando, dia e noite, minimapa */
'use strict';

var Render = (function () {
  var TW = 64, TH = 32;
  var w = World.w, I = DATA.BY_ID, T = DATA.T;
  var canvas, ctx, cw = 0, ch = 0, dpr = 1;
  var cam = { x: 0, y: 1536, z: 1 };
  var ZMIN = 0.45, ZMAX = 2.6;
  var variant = new Uint8Array(w.N);
  var wmask = new Uint8Array(w.N), rmask = new Uint8Array(w.N);
  var maskVersion = -1, roadTiles = [];
  var walkers = [], floats = [];
  var glow = null, time = 0;
  var mini = null, miniCtx = null, miniOff = null, miniVersion = -1;
  var hero = null, scaleCap = 2, bgGrad = null;

  function init(cv) {
    canvas = cv; ctx = canvas.getContext('2d');
    for (var k = 0; k < w.N; k++) variant[k] = Math.floor(U.hash2(World.iOf(k), World.jOf(k), 77) * 4);
    glow = document.createElement('canvas'); glow.width = glow.height = 64;
    var g = glow.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,214,140,1)'); gr.addColorStop(0.4, 'rgba(255,190,100,0.45)'); gr.addColorStop(1, 'rgba(255,170,80,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    resize();
  }

  function quality() { return (Game.settings && Game.settings.quality) || 'alta'; }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, quality() === 'baixa' ? 1 : scaleCap);
    bgGrad = null;
    cw = window.innerWidth; ch = window.innerHeight;
    canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    canvas.style.width = cw + 'px'; canvas.style.height = ch + 'px';
    Sprites.setScale(Math.min(2.5, Math.max(1.25, dpr * 1.25)));
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

  /* ---------------- Máscaras (água e estradas) ---------------- */
  function updateMasks() {
    if (maskVersion === w.mapVersion) return;
    maskVersion = w.mapVersion;
    var W = w.W, H = w.H, k, i, j;
    roadTiles = [];
    for (j = 0; j < H; j++) for (i = 0; i < W; i++) {
      k = j * W + i;
      var m = 0;
      if (w.ter[k] === T.AGUA) {
        if (j > 0 && w.ter[k - W] !== T.AGUA) m |= 1;
        if (i < W - 1 && w.ter[k + 1] !== T.AGUA) m |= 2;
        if (j < H - 1 && w.ter[k + W] !== T.AGUA) m |= 4;
        if (i > 0 && w.ter[k - 1] !== T.AGUA) m |= 8;
      }
      wmask[k] = m;
      var o = w.obj[k];
      if (o && I[o.id].kind === 'road') {
        var r = 0;
        if (j > 0 && World.isRoad(w.obj[k - W])) r |= 1;
        if (i < W - 1 && World.isRoad(w.obj[k + 1])) r |= 2;
        if (j < H - 1 && World.isRoad(w.obj[k + W])) r |= 4;
        if (i > 0 && World.isRoad(w.obj[k - 1])) r |= 8;
        rmask[k] = r;
      }
    }
    World.recompute();
    for (k = 0; k < w.N; k++) if (w.roadConn[k]) roadTiles.push(k);
  }

  /* ---------------- Moradores ---------------- */
  var SHIRTS = ['#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#1abc9c', '#e67e22', '#ecf0f1', '#ff6fa5', '#2ecc71'];
  function updateWalkers(dt, s) {
    var rep = Sim.report();
    var dark = darkness(s ? s.t : 0.5);
    var want = 0;
    if (roadTiles.length > 1 && rep) {
      want = Math.min(quality() === 'baixa' ? 20 : 60, Math.floor(rep.employed * 0.7 + rep.c.houses * 0.8 + 2));
      want = Math.floor(want * (1 - dark * 0.7));
    } else if (roadTiles.length > 1 && !s) want = 25;
    while (walkers.length < want) {
      var k = roadTiles[Math.floor(Math.random() * roadTiles.length)];
      walkers.push({ i: World.iOf(k), j: World.jOf(k), ti: World.iOf(k), tj: World.jOf(k), pk: -1,
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
        if (opts.length) { var nx = opts[Math.floor(Math.random() * opts.length)]; a.pk = ck; a.ti = World.iOf(nx); a.tj = World.jOf(nx); }
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
  }

  /* ---------------- Dia e noite ---------------- */
  function darkness(t) {
    var h = t * 24;
    if (h >= 6.5 && h < 18) return 0;
    if (h >= 18 && h < 20) return (h - 18) / 2;
    if (h >= 20 || h < 4.5) return 1;
    return 1 - (h - 4.5) / 2;
  }

  function visibleRange(margin) {
    var vw = cw / cam.z, vh = ch / cam.z;
    var x0 = cam.x - vw / 2 - TW, x1 = cam.x + vw / 2 + TW, y0 = cam.y - vh / 2 - TH, y1 = cam.y + vh / 2 + (margin || TH);
    var imin = Math.floor((x0 / 32 + y0 / 16) / 2) - 1, imax = Math.ceil((x1 / 32 + y1 / 16) / 2) + 1;
    var jmin = Math.floor((y0 / 16 - x1 / 32) / 2) - 1, jmax = Math.ceil((y1 / 16 - x0 / 32) / 2) + 1;
    return { x0: x0, x1: x1, y0: y0, y1: y1, imin: Math.max(0, imin), imax: Math.min(w.W - 1, imax), jmin: Math.max(0, jmin), jmax: Math.min(w.H - 1, jmax) };
  }

  /* ---------------- Desenho principal ---------------- */
  function draw(dt) {
    time += dt;
    var s = Game.s, ui = Game.ui;
    updateMasks();
    updateWalkers(dt * (s ? (s.speed > 0 ? Math.min(2, s.speed) : 0) : 1), s);

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (!bgGrad) {
      bgGrad = ctx.createLinearGradient(0, 0, 0, canvas.height);
      bgGrad.addColorStop(0, '#16352b'); bgGrad.addColorStop(1, '#0d221b');
    }
    ctx.fillStyle = bgGrad; ctx.fillRect(0, 0, canvas.width, canvas.height);

    var z = cam.z * dpr;
    ctx.setTransform(z, 0, 0, z, (cw / 2 - cam.x * cam.z) * dpr, (ch / 2 - cam.y * cam.z) * dpr);
    ctx.imageSmoothingEnabled = true;

    var v = visibleRange(TH), i, j, k, wx, wy, spr, o;
    var frame = quality() === 'baixa' ? 0 : Math.floor(time * 1.6) % 3;

    // borda do "tabuleiro"
    drawEdges(v);

    // terreno + estradas
    for (j = v.jmin; j <= v.jmax; j++) for (i = v.imin; i <= v.imax; i++) {
      wx = (i - j) * 32; wy = (i + j) * 16;
      if (wx < v.x0 || wx > v.x1 || wy < v.y0 || wy > v.y1) continue;
      k = j * w.W + i;
      var t = w.ter[k];
      spr = t === T.AGUA ? Sprites.water(wmask[k], (frame + variant[k]) % 3) : Sprites.terrain(t, variant[k]);
      ctx.drawImage(spr.c, wx - spr.ox, wy - spr.oy, spr.w, spr.h);
      o = w.obj[k];
      if (o && (o.id === 'estrada' || o.id === 'rua')) {
        spr = Sprites.road(o.id, rmask[k]);
        ctx.drawImage(spr.c, wx - spr.ox, wy - spr.oy, spr.w, spr.h);
      }
    }

    if (ui && s) drawGroundOverlays(v, ui);

    // objetos e moradores em ordem de profundidade
    var vo = visibleRange(110);
    var dmin = vo.imin + vo.jmin, dmax = vo.imax + vo.jmax;
    var buckets = {};
    for (var n = 0; n < walkers.length; n++) {
      var a = walkers[n], dk = Math.round(a.i) + Math.round(a.j);
      (buckets[dk] || (buckets[dk] = [])).push(a);
    }
    var lights = [];
    var dark = s && Game.settings.daynight ? darkness(s.t) : (s ? 0 : 0.0);
    for (var d = dmin; d <= dmax; d++) {
      var ia = Math.max(vo.imin, d - vo.jmax), ib = Math.min(vo.imax, d - vo.jmin);
      for (i = ia; i <= ib; i++) {
        j = d - i; k = j * w.W + i;
        o = w.obj[k];
        if (!o || o.id === 'estrada' || o.id === 'rua') continue;
        wx = (i - j) * 32; wy = (i + j) * 16;
        if (wx < vo.x0 || wx > vo.x1 || wy < vo.y0 || wy > vo.y1) continue;
        if (o.id === 'ponte') spr = Sprites.road('ponte', rmask[k]);
        else spr = Sprites.object(o.id, o.lv, I[o.id].kind === 'house' ? variant[k] + (k % 7) : variant[k]);
        if (ui && ui.moving === k) ctx.globalAlpha = 0.35;
        ctx.drawImage(spr.c, wx - spr.ox, wy - spr.oy, spr.w, spr.h);
        ctx.globalAlpha = 1;
        if (dark > 0.05) {
          var it = I[o.id];
          if (it.light) lights.push([wx + 6, wy - 24, 1.3]);
          else if (it.kind === 'house' || it.kind === 'hq' || it.kind === 'service' || it.kind === 'shop' || it.kind === 'processor' || (it.draw && it.draw.p === 'box')) lights.push([wx, wy - 10, 0.8]);
        }
      }
      var bk = buckets[d];
      if (bk) for (n = 0; n < bk.length; n++) drawPerson(bk[n]);
    }

    if (hero) {
      var hp = tileCenter(hero.i, hero.j);
      ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.ellipse(hp.x, hp.y + 1, 9, 4.5, 0, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = hero.shirt; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.ellipse(hp.x, hp.y + 1, 11.5, 5.8, 0, 0, Math.PI * 2); ctx.stroke();
      drawPerson(hero);
    }
    if (ui && s) drawTopOverlays(vo, ui);

    // textos flutuantes
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = 'bold 12px sans-serif';
    for (n = floats.length - 1; n >= 0; n--) {
      var f = floats[n];
      f.t += dt;
      if (f.t > 1.8) { floats.splice(n, 1); continue; }
      ctx.globalAlpha = f.t < 1.2 ? 1 : 1 - (f.t - 1.2) / 0.6;
      ctx.shadowColor = 'rgba(0,0,0,0.85)'; ctx.shadowBlur = 4; ctx.shadowOffsetY = 1;
      ctx.fillStyle = f.color; ctx.fillText(f.text, f.x, f.y - f.t * 18);
    }
    ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.globalAlpha = 1;

    // noite
    if (dark > 0) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = 'rgba(10,16,48,' + (dark * 0.5).toFixed(3) + ')';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(z, 0, 0, z, (cw / 2 - cam.x * cam.z) * dpr, (ch / 2 - cam.y * cam.z) * dpr);
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = dark * 0.55;
      for (n = 0; n < lights.length; n++) { var L = lights[n], r = 26 * L[2]; ctx.drawImage(glow, L[0] - r, L[1] - r, r * 2, r * 2); }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }
    if (s && Game.settings.daynight) {
      var h = s.t * 24, warm = 0;
      if (h > 16.5 && h < 19.5) warm = 1 - Math.abs(h - 18) / 1.5;
      if (h > 4.5 && h < 7) warm = Math.max(warm, (1 - Math.abs(h - 5.8) / 1.2) * 0.7);
      if (warm > 0) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = 'rgba(255,130,50,' + (warm * 0.13).toFixed(3) + ')';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    }
    drawMini();
  }

  function drawEdges(v) {
    var depth = 22;
    var i, j, wx, wy, k;
    if (v.imax === w.W - 1) {
      i = w.W - 1;
      for (j = v.jmin; j <= v.jmax; j++) {
        wx = (i - j) * 32; wy = (i + j) * 16; k = j * w.W + i;
        ctx.beginPath(); ctx.moveTo(wx + 32, wy); ctx.lineTo(wx, wy + 16); ctx.lineTo(wx, wy + 16 + depth); ctx.lineTo(wx + 32, wy + depth); ctx.closePath();
        ctx.fillStyle = w.ter[k] === T.AGUA ? '#2a6f9e' : '#6b4b2f'; ctx.fill();
      }
    }
    if (v.jmax === w.H - 1) {
      j = w.H - 1;
      for (i = v.imin; i <= v.imax; i++) {
        wx = (i - j) * 32; wy = (i + j) * 16; k = j * w.W + i;
        ctx.beginPath(); ctx.moveTo(wx - 32, wy); ctx.lineTo(wx, wy + 16); ctx.lineTo(wx, wy + 16 + depth); ctx.lineTo(wx - 32, wy + depth); ctx.closePath();
        ctx.fillStyle = w.ter[k] === T.AGUA ? '#3683b8' : '#86603d'; ctx.fill();
      }
    }
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
    // grade de construção
    if (tool && tool !== 'info' && Game.settings.grid) {
      ctx.strokeStyle = 'rgba(255,255,255,0.10)'; ctx.lineWidth = 1 / cam.z;
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
    // pré-visualização da construção
    if (ui.hover >= 0 && tool && (ui.moving >= 0 || (I[tool] && I[tool].draw))) {
      var id = ui.moving >= 0 ? (w.obj[ui.moving] && w.obj[ui.moving].id) : tool;
      var lv = ui.moving >= 0 && w.obj[ui.moving] ? w.obj[ui.moving].lv : 1;
      if (id) {
        var p = tileCenter(World.iOf(ui.hover), World.jOf(ui.hover));
        var spr = Sprites.object(id, lv, 1);
        ctx.globalAlpha = 0.7;
        ctx.drawImage(spr.c, p.x - spr.ox, p.y - spr.oy, spr.w, spr.h);
        ctx.globalAlpha = 1;
      }
    }
    // alertas
    if (Game.settings.alerts && cam.z > 0.6) {
      var blink = Math.sin(time * 4) > -0.3;
      if (blink) for (var j = v.jmin; j <= v.jmax; j++) for (var i = v.imin; i <= v.imax; i++) {
        var k = j * w.W + i, o = w.obj[k];
        if (!o || !World.isBuilding(o)) continue;
        var st = Sim.status(k);
        if (!st || (st.alert !== 'road' && st.alert !== 'input')) continue;
        var c = tileCenter(i, j);
        if (c.x < v.x0 || c.x > v.x1 || c.y < v.y0 || c.y > v.y1) continue;
        var icon = st.alert === 'road' ? '🛣️' : st.alert === 'input' ? '📦' : '👷';
        var y = c.y - 58;
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

  function drawPerson(a) {
    var p = tileCenter(a.i, a.j);
    var bob = Math.abs(Math.sin(a.ph)) * 1.2;
    var off = a.hero ? 0 : ((a.sp * 37) % 1 - 0.5) * 10;
    var x = p.x + off, y = p.y - bob + off * 0.3;
    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    ctx.beginPath(); ctx.ellipse(x, p.y + 0.5 + off * 0.3, 3, 1.3, 0, 0, Math.PI * 2); ctx.fill();
    if (a.hero) {
      ctx.save(); ctx.translate(x, y); ctx.scale(1.5, 1.5);
      Sprites.person(ctx, 0, 0, a.shirt);
      ctx.fillStyle = a.cap; ctx.fillRect(-2, -10.2, 4, 1.6);
      ctx.restore();
    } else Sprites.person(ctx, x, y, a.shirt);
    if (a.say && a.sayT > 0) {
      ctx.font = '9px sans-serif';
      var tw = ctx.measureText(a.say).width + 10;
      ctx.fillStyle = 'rgba(255,255,255,0.95)';
      roundRect(x - tw / 2, y - 30, tw, 15, 6); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x - 3, y - 15.5); ctx.lineTo(x + 3, y - 15.5); ctx.lineTo(x, y - 11); ctx.fill();
      ctx.fillStyle = '#1d2b25'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(a.say, x, y - 22.5);
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

  // resolução dinâmica: se o aparelho estiver lento, reduz a resolução do canvas
  function downscale() {
    var cur = Math.min(window.devicePixelRatio || 1, scaleCap);
    if (quality() === 'baixa' || cur <= 1) return false;
    scaleCap = Math.max(1, cur - 0.25);
    resize();
    return true;
  }

  return {
    init: init, resize: resize, draw: draw, cam: cam, screenToTile: screenToTile, screenToWorld: screenToWorld,
    worldToScreen: worldToScreen, worldToTileF: worldToTileF, tileCenter: tileCenter, centerOn: centerOn, pan: pan,
    zoomAt: zoomAt, clampCam: clampCam, addFloat: addFloat, dayFloats: dayFloats, setMini: setMini, miniToWorld: miniToWorld,
    walkers: function () { return walkers; }, setHero: setHero, darkness: darkness, downscale: downscale,
    resetScale: function () { scaleCap = 2; resize(); },
    size: function () { return { w: cw, h: ch }; }, resetWalkers: function () { walkers = []; floats = []; maskVersion = -1; miniVersion = -1; }
  };
})();

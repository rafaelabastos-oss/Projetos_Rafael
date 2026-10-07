/* Mundo Renda - moradores animados (ciclo de caminhada, frente/costas, roupas variadas) e veículos nas ruas */
'use strict';

var People = (function () {
  var w = World.w;
  var list = [], frames = {}, looks = [], vframes = {}, SS = 4;
  var SKIN = ['#f3cfa3', '#e0ac69', '#c68642', '#9a6235', '#6b4226'];
  var HAIR = ['#2b1d0e', '#4a2f1b', '#141414', '#8a5a2b', '#d8b25a', '#b5482f', '#6b6b6b'];
  var SHIRT = ['#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#1abc9c', '#e67e22', '#ecf0f1', '#ff6fa5', '#2ecc71', '#34495e', '#d35400'];
  var PANTS = ['#34405e', '#2d2d36', '#5b4a3a', '#2f5f8a', '#6f6f6f', '#3f5f3f'];
  var NLOOK = 18;

  function initLooks() {
    if (looks.length) return;
    for (var n = 0; n < NLOOK; n++) {
      var r = U.rng(n * 131 + 7);
      looks.push({ skin: SKIN[Math.floor(r() * SKIN.length)], hair: HAIR[Math.floor(r() * HAIR.length)], hs: Math.floor(r() * 4),
        shirt: SHIRT[Math.floor(r() * SHIRT.length)], pants: PANTS[Math.floor(r() * PANTS.length)], dress: r() < 0.25, hat: r() < 0.15,
        bag: r() < 0.25, bagc: SHIRT[Math.floor(r() * SHIRT.length)] });
    }
  }

  function sh(c, a) { return Sprites && U.shade ? (c[0] === '#' ? U.shade(c, a) : c) : c; }

  // um quadro de pessoa: view 0 = de frente, 1 = de costas; f = 0..3; m = espelhado
  function personFrame(look, view, f, m) {
    var key = look.id + '_' + view + '_' + f + '_' + m;
    if (frames[key]) return frames[key];
    var Wd = 14, Hd = 22, c = document.createElement('canvas');
    c.width = Wd * SS; c.height = Hd * SS;
    var g = c.getContext('2d');
    g.scale(SS, SS); g.translate(Wd / 2, Hd - 2);
    if (m) g.scale(-1, 1);
    g.lineCap = 'round'; g.lineJoin = 'round';
    var ph = f / 4 * Math.PI * 2, sw = Math.sin(ph), L = look;
    // sombra
    g.fillStyle = 'rgba(0,0,0,0.25)'; g.beginPath(); g.ellipse(0, 0.2, 3, 1.1, 0, 0, Math.PI * 2); g.fill();
    // pernas
    var lA = sw * 1.4, lB = -sw * 1.4;
    g.strokeStyle = L.dress ? L.skin : L.pants; g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(-0.9, -5.5); g.lineTo(-0.9 + lA * 0.6, -0.6 - Math.max(0, sw) * 0.9); g.stroke();
    g.beginPath(); g.moveTo(0.9, -5.5); g.lineTo(0.9 + lB * 0.6, -0.6 - Math.max(0, -sw) * 0.9); g.stroke();
    g.fillStyle = '#2a2a2a';
    g.beginPath(); g.ellipse(-0.9 + lA * 0.6 + 0.3, -0.4 - Math.max(0, sw) * 0.9, 1, 0.6, 0, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.ellipse(0.9 + lB * 0.6 + 0.3, -0.4 - Math.max(0, -sw) * 0.9, 1, 0.6, 0, 0, Math.PI * 2); g.fill();
    // braço de trás
    g.strokeStyle = sh(L.shirt, -0.25); g.lineWidth = 1.2;
    g.beginPath(); g.moveTo(2.2, -10); g.lineTo(2.4 - sw * 1.2, -6.6); g.stroke();
    // tronco / vestido
    if (L.dress) {
      g.fillStyle = L.shirt;
      g.beginPath(); g.moveTo(-2.1, -11); g.lineTo(2.1, -11); g.lineTo(3, -4.5); g.lineTo(-3, -4.5); g.closePath(); g.fill();
      g.fillStyle = 'rgba(0,0,0,0.15)'; g.beginPath(); g.moveTo(0.8, -11); g.lineTo(2.1, -11); g.lineTo(3, -4.5); g.lineTo(1.2, -4.5); g.closePath(); g.fill();
    } else {
      g.fillStyle = L.shirt;
      g.beginPath(); g.moveTo(-2.2, -11.2); g.lineTo(2.2, -11.2); g.lineTo(2.3, -5.6); g.lineTo(-2.3, -5.6); g.closePath(); g.fill();
      g.fillStyle = 'rgba(0,0,0,0.15)'; g.fillRect(0.8, -11.2, 1.5, 5.6);
      g.fillStyle = L.pants; g.fillRect(-2.3, -6.2, 4.6, 1);
    }
    if (L.bag && view === 0) { g.fillStyle = L.bagc; g.fillRect(-3.6, -7.8, 2, 2.6); g.strokeStyle = sh(L.bagc, -0.3); g.lineWidth = 0.4; g.beginPath(); g.moveTo(-2.6, -7.8); g.lineTo(1.6, -11); g.stroke(); }
    if (L.bag && view === 1) { g.fillStyle = L.bagc; g.fillRect(-1.8, -10.6, 3.6, 3.8); }
    // braço da frente
    g.strokeStyle = L.shirt; g.lineWidth = 1.3;
    g.beginPath(); g.moveTo(-2.2, -10); g.lineTo(-2.4 + sw * 1.2, -6.6); g.stroke();
    g.fillStyle = L.skin; g.beginPath(); g.arc(-2.4 + sw * 1.2, -6.3, 0.6, 0, Math.PI * 2); g.fill();
    // pescoço e cabeça
    g.fillStyle = L.skin; g.fillRect(-0.6, -12.4, 1.2, 1.4);
    g.beginPath(); g.arc(0, -14, 2.3, 0, Math.PI * 2); g.fill();
    g.fillStyle = L.hair;
    if (view === 1) {
      g.beginPath(); g.arc(0, -14.2, 2.45, 0, Math.PI * 2); g.fill();
      if (L.hs === 1) { g.fillRect(-2.2, -14, 4.4, 4); }
      if (L.hs === 2) { g.beginPath(); g.arc(0, -16.4, 1.2, 0, Math.PI * 2); g.fill(); }
    } else {
      g.beginPath(); g.arc(0, -14.6, 2.4, Math.PI * 1.02, Math.PI * 1.98); g.fill();
      if (L.hs === 1) { g.fillRect(-2.4, -15, 1, 3.6); g.fillRect(1.4, -15, 1, 3.6); }
      if (L.hs === 2) { g.beginPath(); g.arc(0, -16.6, 1.2, 0, Math.PI * 2); g.fill(); }
      if (L.hs === 3) { for (var q = -2; q <= 2; q++) { g.beginPath(); g.arc(q * 0.9, -16, 0.9, 0, Math.PI * 2); g.fill(); } }
      g.fillStyle = '#1a1a1a'; g.fillRect(-1.1, -14.1, 0.5, 0.6); g.fillRect(0.6, -14.1, 0.5, 0.6);
      g.fillStyle = 'rgba(220,90,80,0.35)'; g.beginPath(); g.arc(-1.4, -13.2, 0.5, 0, Math.PI * 2); g.arc(1.4, -13.2, 0.5, 0, Math.PI * 2); g.fill();
    }
    if (L.hat) {
      g.fillStyle = L.hatc || '#e9d8a6';
      g.beginPath(); g.ellipse(0, -15.6, 3.4, 1, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.arc(0, -16, 1.9, Math.PI, 0); g.fill();
    }
    frames[key] = { c: c, w: Wd, h: Hd, ox: Wd / 2, oy: Hd - 2 };
    return frames[key];
  }

  /* ---------------- Veículos ---------------- */
  function iso(u, v, z) { return [(u - v) * 32, (u + v) * 16 - (z || 0)]; }
  function vframe(type, dir, col) {
    // dir: 0 = +u (baixo-direita), 1 = -u (cima-esquerda), 2 = +v (baixo-esquerda), 3 = -v (cima-direita)
    var key = type + dir + col;
    if (vframes[key]) return vframes[key];
    var Wd = 40, Hd = 32, c = document.createElement('canvas');
    c.width = Wd * SS; c.height = Hd * SS;
    var g = c.getContext('2d');
    g.scale(SS, SS); g.translate(Wd / 2, Hd - 9);
    g.lineJoin = 'round'; g.lineCap = 'round';
    var au = dir < 2, sgn = dir === 0 || dir === 2 ? 1 : -1;
    function P(a, b, z) { return au ? iso(a * sgn, b, z) : iso(b, a * sgn, z); }   // a = ao longo do movimento, b = lateral
    function poly(pts, fill) { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (var n = 1; n < pts.length; n++) g.lineTo(pts[n][0], pts[n][1]); g.closePath(); g.fillStyle = fill; g.fill(); }
    function boxv(a0, a1, b0, b1, z0, z1, colr, top) {
      var faces = [];
      // faces visíveis: lateral +b (se ela aponta para a tela) e frente/trás conforme a direção
      var fr = [[a0, b1], [a1, b1]], ends = sgn > 0 ? a1 : a0;
      faces.push([[P(fr[0][0], fr[0][1], z0), P(fr[1][0], fr[1][1], z0), P(fr[1][0], fr[1][1], z1), P(fr[0][0], fr[0][1], z1)], au ? U.shade(colr, -0.05) : U.shade(colr, -0.2)]);
      faces.push([[P(ends, b0, z0), P(ends, b1, z0), P(ends, b1, z1), P(ends, b0, z1)], au ? U.shade(colr, -0.22) : U.shade(colr, -0.08)]);
      var bb = [[a0, b0], [a1, b0]];
      faces.unshift([[P(bb[0][0], bb[0][1], z0), P(bb[1][0], bb[1][1], z0), P(bb[1][0], bb[1][1], z1), P(bb[0][0], bb[0][1], z1)], U.shade(colr, -0.3)]);
      faces.forEach(function (f) { poly(f[0], f[1]); });
      poly([P(a0, b0, z1), P(a1, b0, z1), P(a1, b1, z1), P(a0, b1, z1)], top || U.shade(colr, 0.15));
    }
    function wheel(a, b) { var p = P(a, b, 1.3); g.fillStyle = '#1e1e1e'; g.beginPath(); g.ellipse(p[0], p[1], 1.8, 1.4, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = '#9a9a9a'; g.beginPath(); g.ellipse(p[0], p[1], 0.7, 0.55, 0, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = 'rgba(0,0,0,0.25)';
    var sc = P(0, 0, 0);
    g.beginPath(); g.ellipse(sc[0], sc[1] + 0.5, type === 'van' ? 11 : 6, type === 'van' ? 5 : 2.6, 0, 0, Math.PI * 2); g.fill();
    if (type === 'van') {
      wheel(-0.1, -0.08); wheel(0.1, -0.08);
      boxv(-0.17, 0.05, -0.085, 0.085, 1.5, 9, col);
      boxv(0.05, 0.17, -0.085, 0.085, 1.5, 7, '#f2f2ee', '#dcdcd6');
      var wi = sgn > 0 ? 0.17 : 0.05;
      poly([P(wi, -0.07, 4.2), P(wi, 0.07, 4.2), P(wi, 0.07, 6.6), P(wi, -0.07, 6.6)], '#7fb2d9');
      poly([P(0.06, 0.086, 4.2), P(0.15, 0.086, 4.2), P(0.15, 0.086, 6.4), P(0.06, 0.086, 6.4)], '#7fb2d9');
      wheel(-0.1, 0.08); wheel(0.1, 0.08);
      var hl = P(sgn > 0 ? 0.172 : -0.172, 0.06, 3); g.fillStyle = sgn > 0 ? '#fff4c2' : '#ff4040'; g.fillRect(hl[0] - 0.6, hl[1] - 0.6, 1.2, 1.2);
    } else {
      wheel(-0.07, 0); wheel(0.07, 0);
      var a = P(-0.07, 0, 1.4), b = P(0.07, 0, 1.4), seat = P(-0.01, 0, 5), bar = P(0.05, 0, 6.5);
      g.strokeStyle = type === 'moto' ? '#333' : col; g.lineWidth = type === 'moto' ? 1.6 : 0.8;
      g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(seat[0], seat[1]); g.lineTo(b[0], b[1]); g.moveTo(seat[0], seat[1]); g.lineTo(bar[0], bar[1]); g.stroke();
      if (type === 'moto') {
        var bx = P(-0.06, 0, 6);
        boxv(-0.1, -0.02, -0.035, 0.035, 5, 9, Sprites.brand ? Sprites.brand() : '#e74c3c');
        void bx;
      }
      // ciclista
      var hip = P(0, 0, 6.2), sh2 = P(0.02, 0, 11), head = P(0.03, 0, 13.4);
      g.strokeStyle = '#34405e'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(hip[0], hip[1]); g.lineTo(P(0.04, 0, 2.8)[0], P(0.04, 0, 2.8)[1]); g.stroke();
      g.strokeStyle = type === 'moto' ? '#c0392b' : col; g.lineWidth = 2.6; g.beginPath(); g.moveTo(hip[0], hip[1]); g.lineTo(sh2[0], sh2[1]); g.stroke();
      g.strokeStyle = '#f0c27d'; g.lineWidth = 1; g.beginPath(); g.moveTo(sh2[0], sh2[1] + 0.5); g.lineTo(bar[0], bar[1]); g.stroke();
      g.fillStyle = type === 'moto' ? '#ffffff' : '#c68642'; g.beginPath(); g.arc(head[0], head[1], 2, 0, Math.PI * 2); g.fill();
      if (type === 'moto') { g.fillStyle = '#2c3e50'; g.beginPath(); g.arc(head[0], head[1] - 0.3, 2.1, Math.PI * 0.9, Math.PI * 2.1); g.fill(); }
    }
    vframes[key] = { c: c, w: Wd, h: Hd, ox: Wd / 2, oy: Hd - 9 };
    return vframes[key];
  }

  /* ---------------- Simulação dos que andam ---------------- */
  var DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  function isRoad(i, j) { return World.inside(i, j) && World.isRoad(w.obj[World.idx(i, j)]); }

  function spawn(roadTiles, veh) {
    var k = roadTiles[Math.floor(Math.random() * roadTiles.length)];
    var i = World.iOf(k), j = World.jOf(k), types = ['bike', 'moto', 'van', 'van'];
    var cols = ['#e74c3c', '#2e86de', '#f1c40f', '#ecf0f1', '#27ae60', '#8e44ad'];
    var a = { i: i, j: j, ti: i, tj: j, pk: -1, di: 1, dj: 0, sp: veh ? 1.6 + Math.random() * 0.6 : 0.65 + Math.random() * 0.5,
      ph: Math.random() * 4, say: null, sayT: 0, side: Math.random() < 0.5 ? -1 : 1, veh: veh,
      look: Math.floor(Math.random() * NLOOK), type: veh ? types[Math.floor(Math.random() * types.length)] : null,
      col: cols[Math.floor(Math.random() * cols.length)], off: 0.16 + Math.random() * 0.12 };
    if (veh && a.type === 'van') a.sp *= 0.85;
    return a;
  }

  function update(dt, s, roadTiles, time) {
    initLooks();
    var rep = Sim.report(), dark = s && Game.settings.daynight ? Render.darkness(s.t) : 0;
    var high = Render.high();
    var wantP = 0, wantV = 0;
    if (roadTiles.length > 1) {
      if (s && rep) {
        wantP = Math.min(high ? 70 : 24, Math.floor(rep.employed * 0.7 + rep.c.houses * 0.9 + 3));
        wantV = Math.min(high ? 12 : 4, Math.floor(rep.c.shops * 1.5 + rep.c.processors + (World.w.counts.entrega || 0) * 3));
        if (roadTiles.length < 8) wantV = 0;
      } else if (!s) { wantP = 28; wantV = 5; }
      wantP = Math.floor(wantP * (1 - dark * 0.7));
      wantV = Math.floor(wantV * (1 - dark * 0.5));
    }
    var np = 0, nv = 0, n;
    for (n = 0; n < list.length; n++) { if (list[n].veh) nv++; else np++; }
    while (np < wantP) { list.push(spawn(roadTiles, false)); np++; }
    while (nv < wantV) { list.push(spawn(roadTiles, true)); nv++; }
    for (n = list.length - 1; n >= 0 && (np > wantP || nv > wantV); n--) {
      if (list[n].veh && nv > wantV) { list.splice(n, 1); nv--; }
      else if (!list[n].veh && np > wantP) { list.splice(n, 1); np--; }
    }
    for (n = 0; n < list.length; n++) step(list[n], dt, roadTiles);
    void time;
  }

  function step(a, dt, roadTiles) {
    if (!isRoad(a.ti, a.tj)) {
      var nk = roadTiles[Math.floor(Math.random() * roadTiles.length)];
      a.i = a.ti = World.iOf(nk); a.j = a.tj = World.jOf(nk); return;
    }
    var di = a.ti - a.i, dj = a.tj - a.j, dist = Math.sqrt(di * di + dj * dj), stp = a.sp * dt;
    a.ph += dt * (a.veh ? 0 : 6.5 * a.sp);
    if (a.sayT > 0) a.sayT -= dt;
    if (dist <= stp) {
      a.i = a.ti; a.j = a.tj;
      var opts = [], ck = World.idx(a.ti, a.tj);
      for (var n = 0; n < 4; n++) { var ii = a.ti + DIRS[n][0], jj = a.tj + DIRS[n][1]; if (isRoad(ii, jj)) opts.push([ii, jj]); }
      if (opts.length > 1 && a.pk >= 0) opts = opts.filter(function (x) { return World.idx(x[0], x[1]) !== a.pk; });
      if (opts.length) {
        var nx = opts[Math.floor(Math.random() * opts.length)];
        a.pk = ck; a.di = nx[0] - a.ti; a.dj = nx[1] - a.tj; a.ti = nx[0]; a.tj = nx[1];
      }
    } else { a.i += di / dist * stp; a.j += dj / dist * stp; }
  }

  function pos(a) {
    // desloca para a calçada (pessoas) ou para a mão direita (veículos)
    var off = a.veh ? 0.15 : a.off * a.side;
    var pi = a.i - a.dj * off, pj = a.j + a.di * off;
    return { x: (pi - pj) * 32, y: (pi + pj) * 16 };
  }
  function viewOf(a) {
    // de frente quando desce na tela (+i ou +j); espelhado quando vai para a esquerda (+j ou -i)
    var front = a.di > 0 || a.dj > 0, mirror = a.dj > 0 || a.di < 0;
    return [front ? 0 : 1, mirror ? 1 : 0];
  }

  function draw(ctx, a, time) {
    var p = pos(a);
    if (a.veh) {
      var dir = a.di > 0 ? 0 : a.di < 0 ? 1 : a.dj > 0 ? 2 : 3;
      var f = vframe(a.type, dir, a.col);
      var bob = a.type === 'van' ? 0 : Math.sin(time * 14 + a.ph) * 0.2;
      ctx.drawImage(f.c, p.x - f.ox, p.y - f.oy + bob, f.w, f.h);
      return;
    }
    var vw = viewOf(a), L = looks[a.look]; L.id = a.look;
    var fr = personFrame(L, vw[0], Math.floor(a.ph) % 4, vw[1]);
    ctx.drawImage(fr.c, p.x - fr.ox, p.y - fr.oy, fr.w, fr.h);
    if (a.say && a.sayT > 0) talk.push([p.x, p.y - 4, a.say, Math.min(1, a.sayT * 2)]);
  }
  var talk = [];
  function drawSpeech(ctx) {
    for (var n = 0; n < talk.length; n++) { ctx.globalAlpha = talk[n][3]; Render.speech(talk[n][0], talk[n][1], talk[n][2]); }
    ctx.globalAlpha = 1;
    talk.length = 0;
  }

  var heroLook = null;
  function drawHero(ctx, hero, time) {
    initLooks();
    if (!heroLook) heroLook = { id: 'hero', skin: '#c68642', hair: '#2b1d0e', hs: 0, shirt: hero.shirt, pants: '#2f3e5e', hat: true, hatc: hero.shirt, bag: true, bagc: '#f1c40f' };
    heroLook.shirt = hero.shirt; heroLook.hatc = '#ffffff';
    var moving = hero.ph !== hero._lph; hero._lph = hero.ph;
    var dir = hero.dir || [1, 0];
    var front = dir[0] > 0 || dir[1] > 0, mirror = dir[1] > 0 || dir[0] < 0;
    var f = moving ? Math.floor(hero.ph * 0.6) % 4 : 0;
    var key = 'hero' + hero.shirt; heroLook.id = key;
    var fr = personFrame(heroLook, front ? 0 : 1, f, mirror ? 1 : 0);
    var x = (hero.i - hero.j) * 32, y = (hero.i + hero.j) * 16;
    ctx.save(); ctx.translate(x, y); ctx.scale(1.45, 1.45);
    ctx.drawImage(fr.c, -fr.ox, -fr.oy, fr.w, fr.h);
    ctx.restore();
    void time;
  }

  function lights(arr) {
    for (var n = 0; n < list.length; n++) {
      var a = list[n];
      if (!a.veh || a.type !== 'van') continue;
      var p = pos(a);
      arr.push([p.x + (a.di - a.dj) * 9, p.y + (a.di + a.dj) * 4.5 - 4, 0.6, null, 0, 0, '#fff1c4']);
    }
  }

  return { update: update, draw: draw, drawHero: drawHero, drawSpeech: drawSpeech, list: function () { return list; }, reset: function () { list = []; }, lights: lights };
})();

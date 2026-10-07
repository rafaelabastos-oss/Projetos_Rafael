/* Mundo Renda - efeitos: construir "crescendo", poeira, fumaça das chaminés, moedas, pássaros,
   nuvens e suas sombras, chuva/estiagem dos eventos e confete de conquistas */
'use strict';

var Fx = (function () {
  var w = World.w, I = DATA.BY_ID;
  var parts = [], screen = [], grows = {}, smokeT = {}, birds = [], clouds = [];
  var now = 0, birdTimer = 8, spr = {}, inited = false, rainT = 0;
  var MAXP = 260;

  function soft(col, r) {
    var c = document.createElement('canvas'); c.width = c.height = 32;
    var g = c.getContext('2d'), gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
    gr.addColorStop(0, col); gr.addColorStop(0.6, col.replace(/[\d.]+\)$/, '0.35)')); gr.addColorStop(1, col.replace(/[\d.]+\)$/, '0)'));
    g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
    void r;
    return c;
  }
  function init() {
    if (inited) return;
    inited = true;
    spr.smoke = soft('rgba(214,216,220,0.95)');
    spr.dust = soft('rgba(196,160,110,0.9)');
    spr.leaf = soft('rgba(120,200,90,0.9)');
    // moeda
    var c = document.createElement('canvas'); c.width = c.height = 24;
    var g = c.getContext('2d');
    g.fillStyle = '#c98a0c'; g.beginPath(); g.arc(12, 12, 10, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#ffcf3a'; g.beginPath(); g.arc(12, 11, 8.5, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#a86f00'; g.font = 'bold 10px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('$', 12, 11.5);
    spr.coin = c;
    // nuvens
    spr.clouds = [];
    for (var n = 0; n < 4; n++) {
      var cc = document.createElement('canvas'); cc.width = 260; cc.height = 130;
      var cg = cc.getContext('2d'), r = U.rng(n * 17 + 3), blobs = [];
      for (var b = 0; b < 9; b++) blobs.push([60 + r() * 140, 60 + (r() - 0.5) * 30, 22 + r() * 26]);
      blobs.forEach(function (p) { cg.fillStyle = 'rgba(190,205,225,0.9)'; cg.beginPath(); cg.arc(p[0] + 4, p[1] + 8, p[2], 0, Math.PI * 2); cg.fill(); });
      blobs.forEach(function (p) { cg.fillStyle = '#ffffff'; cg.beginPath(); cg.arc(p[0], p[1], p[2], 0, Math.PI * 2); cg.fill(); });
      blobs.forEach(function (p) { cg.fillStyle = 'rgba(255,255,255,0.9)'; cg.beginPath(); cg.arc(p[0] - p[2] * 0.3, p[1] - p[2] * 0.35, p[2] * 0.5, 0, Math.PI * 2); cg.fill(); });
      spr.clouds.push(cc);
    }
    spr.cshadow = soft('rgba(10,30,20,0.9)');
    var mapW = (w.W + w.H) * 32;
    for (n = 0; n < 7; n++) clouds.push({ x: (Math.random() - 0.5) * mapW, y: Math.random() * (w.W + w.H) * 16, s: 0.8 + Math.random() * 0.9, k: n % 4, sp: 6 + Math.random() * 6 });
  }

  function add(p) { if (parts.length < MAXP) parts.push(p); }

  /* ---------------- Ganchos do mundo ---------------- */
  function onTile(k, prev, obj) {
    init();
    if (k < 0) { grows = {}; parts = []; return; }
    var X = (World.iOf(k) - World.jOf(k)) * 32, Y = (World.iOf(k) + World.jOf(k)) * 16;
    if (obj && (!prev || prev.id !== obj.id || prev.lv !== obj.lv)) {
      var kd = I[obj.id].kind;
      if (kd !== 'natural') {
        if (kd !== 'road') grows[k] = now;
        var big = kd !== 'road' && kd !== 'decor';
        dust(X, Y, big ? 14 : 5, big ? 1 : 0.6);
      }
    } else if (prev && !obj) {
      dust(X, Y, 18, 1.2);
      for (var n = 0; n < 6; n++) add({ t: 'debris', x: X + (Math.random() - 0.5) * 20, y: Y - 8, z: 6 + Math.random() * 6, vx: (Math.random() - 0.5) * 30, vy: (Math.random() - 0.5) * 15, vz: 20 + Math.random() * 20, life: 0, max: 1.1, s: 1.2 + Math.random(), col: Math.random() < 0.5 ? '#9c7a55' : '#8a8f93' });
    }
  }
  function dust(X, Y, n, s) {
    for (var m = 0; m < n; m++) {
      var a = Math.random() * Math.PI * 2, sp = 10 + Math.random() * 22;
      add({ t: 'dust', x: X + Math.cos(a) * 10, y: Y + Math.sin(a) * 5, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp * 0.5 - 4, life: 0, max: 0.7 + Math.random() * 0.5, s: (3 + Math.random() * 4) * s });
    }
  }

  function ease(t) { var c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); }
  function drawGrow(ctx, k, s, wx, wy) {
    var t0 = grows[k];
    if (t0 === undefined) return false;
    var t = (now - t0) / 0.55;
    if (t >= 1) { delete grows[k]; return false; }
    var e = ease(Math.max(0, t));
    ctx.save();
    ctx.translate(wx, wy);
    ctx.scale(1 + (1 - e) * 0.18, Math.max(0.02, e));
    ctx.drawImage(s.c, -s.ox, -s.oy, s.w, s.h);
    ctx.restore();
    return true;
  }

  // fumaça das chaminés quando a construção está funcionando
  function smoke(k, s, wx, wy) {
    var st = Sim.status(k);
    if (!st || st.alert === 'road' || st.alert === 'staff0') return;
    var t = smokeT[k] || 0;
    if (now < t) return;
    smokeT[k] = now + 0.3 + Math.random() * 0.25;
    for (var n = 0; n < s.emit.length; n++) {
      var e = s.emit[n];
      add({ t: 'smoke', x: wx + e[0] + (Math.random() - 0.5) * 1.5, y: wy + e[1], vx: 3 + Math.random() * 3, vy: -10 - Math.random() * 5, life: 0, max: 2.8, s: 2.2 + Math.random() });
    }
  }

  function dayEnd(report, vis) {
    init();
    var n = 0;
    report.list.forEach(function (b) {
      if (n > 10) return;
      var st = report.st[b.k];
      if (!st || !st.sold || st.sold < 1) return;
      var i = World.iOf(b.k), j = World.jOf(b.k), X = (i - j) * 32, Y = (i + j) * 16;
      if (X < vis.x0 || X > vis.x1 || Y < vis.y0 || Y > vis.y1) return;
      n++;
      for (var m = 0; m < 5; m++) add({ t: 'coin', x: X + (Math.random() - 0.5) * 16, y: Y - 20, vx: (Math.random() - 0.5) * 12, vy: -30 - Math.random() * 18, life: -m * 0.08, max: 1.2, s: 4.5 });
    });
  }

  function confetti() {
    init();
    var cols = ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6', '#ff6fa5', '#ffffff'];
    for (var n = 0; n < 90; n++) screen.push({ t: 'conf', x: Math.random(), y: -Math.random() * 0.3, vx: (Math.random() - 0.5) * 0.15, vy: 0.25 + Math.random() * 0.3, r: Math.random() * 6, vr: (Math.random() - 0.5) * 10, col: cols[n % cols.length], life: 0, max: 3.2 });
  }

  /* ---------------- Atualização ---------------- */
  function update(dt, s, time) {
    init();
    now = time;
    for (var n = parts.length - 1; n >= 0; n--) {
      var p = parts[n];
      p.life += dt;
      if (p.life > p.max) { parts.splice(n, 1); continue; }
      if (p.life < 0) continue;
      if (p.t === 'debris') { p.vz -= 70 * dt; p.z += p.vz * dt; if (p.z < 0) { p.z = 0; p.vz *= -0.3; p.vx *= 0.6; p.vy *= 0.6; } }
      if (p.t === 'coin') p.vy += 40 * dt;
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.t === 'dust') { p.vx *= 0.92; p.vy *= 0.92; }
      if (p.t === 'smoke') { p.vx += 4 * dt; p.vy *= 0.985; }
    }
    for (n = screen.length - 1; n >= 0; n--) {
      var q = screen[n];
      q.life += dt;
      if (q.life > q.max) { screen.splice(n, 1); continue; }
      q.x += q.vx * dt; q.y += q.vy * dt; q.r += q.vr * dt;
    }
    // nuvens
    var mapW = (w.W + w.H) * 32;
    clouds.forEach(function (c) { c.x += c.sp * dt; if (c.x > mapW * 0.6) c.x = -mapW * 0.6; });
    // pássaros
    birdTimer -= dt;
    var wx = Game.settings.weather !== false;
    if (birdTimer <= 0 && Render.high() && wx) {
      birdTimer = 18 + Math.random() * 25;
      var cam = Render.cam, sz = Render.size(), dir = Math.random() < 0.5 ? 1 : -1;
      var bx = cam.x - dir * (sz.w / cam.z / 2 + 60), by = cam.y + (Math.random() - 0.5) * sz.h / cam.z * 0.6, nb = 3 + Math.floor(Math.random() * 4);
      for (var b = 0; b < nb; b++) birds.push({ x: bx - dir * b * 12, y: by + (b % 2 ? 1 : -1) * b * 6, z: 70 + Math.random() * 10, vx: dir * (38 + Math.random() * 4), vy: 4, ph: Math.random() * 6, life: 0 });
    }
    for (n = birds.length - 1; n >= 0; n--) {
      var bd = birds[n];
      bd.life += dt; bd.x += bd.vx * dt; bd.y += bd.vy * dt; bd.ph += dt * 9;
      if (bd.life > 40) birds.splice(n, 1);
    }
    // chuva dos eventos
    var rain = s && s.events && s.events.some(function (e) { return e.id === 'chuva'; });
    if (rain && Render.high() && wx) {
      rainT += dt;
      while (rainT > 0.012) { rainT -= 0.012; screen.push({ t: 'rain', x: Math.random() * 1.2 - 0.1, y: -0.05, vx: -0.18, vy: 1.6 + Math.random() * 0.5, life: 0, max: 0.8, r: 0, vr: 0 }); }
      if (screen.length > 400) screen.splice(0, screen.length - 400);
    }
  }

  /* ---------------- Desenho ---------------- */
  function drawWorld(ctx, v, zoom) {
    // sombras das nuvens (bem suaves)
    if (Render.high() && Game.settings.weather !== false) {
      ctx.globalAlpha = 0.09;
      clouds.forEach(function (c) {
        var rw = 300 * c.s, rh = 150 * c.s;
        if (c.x + rw < v.x0 || c.x - rw > v.x1 || c.y + rh < v.y0 || c.y - rh > v.y1) return;
        ctx.drawImage(spr.cshadow, c.x - rw, c.y - rh, rw * 2, rh * 2);
      });
      ctx.globalAlpha = 1;
    }
    for (var n = 0; n < parts.length; n++) {
      var p = parts[n];
      if (p.life < 0) continue;
      var t = p.life / p.max;
      if (p.t === 'smoke') {
        ctx.globalAlpha = Math.min(1, t * 6) * (1 - t) * 0.9;
        var ss = p.s + t * 9;
        ctx.drawImage(spr.smoke, p.x - ss, p.y - ss, ss * 2, ss * 2);
      } else if (p.t === 'dust') {
        ctx.globalAlpha = (1 - t) * 0.7;
        var ds = p.s * (1 + t);
        ctx.drawImage(spr.dust, p.x - ds, p.y - ds, ds * 2, ds * 2);
      } else if (p.t === 'debris') {
        ctx.globalAlpha = 1 - t * t;
        ctx.fillStyle = p.col;
        ctx.fillRect(p.x - p.s / 2, p.y - p.z - p.s / 2, p.s, p.s);
      } else if (p.t === 'coin') {
        ctx.globalAlpha = t < 0.7 ? 1 : 1 - (t - 0.7) / 0.3;
        var cs = p.s * (0.6 + 0.4 * Math.abs(Math.cos(p.life * 8)));
        ctx.drawImage(spr.coin, p.x - cs, p.y - p.s, cs * 2, p.s * 2);
      }
    }
    ctx.globalAlpha = 1;
    // sombras dos pássaros
    ctx.fillStyle = 'rgba(0,0,0,0.18)';
    birds.forEach(function (b) { ctx.beginPath(); ctx.ellipse(b.x + b.z * 0.6, b.y + b.z * 0.45, 2.4, 1, 0, 0, Math.PI * 2); ctx.fill(); });
    void zoom;
  }

  function drawSky(ctx, v, zoom, time) {
    ctx.strokeStyle = '#2b2b2b'; ctx.lineWidth = 1.1; ctx.lineCap = 'round';
    birds.forEach(function (b) {
      var x = b.x, y = b.y - b.z, f = Math.sin(b.ph) * 2.6;
      ctx.beginPath(); ctx.moveTo(x - 4, y - f); ctx.quadraticCurveTo(x - 2, y - 2 - f * 0.4, x, y); ctx.quadraticCurveTo(x + 2, y - 2 - f * 0.4, x + 4, y - f); ctx.stroke();
    });
    // nuvens aparecem quando a câmera está longe
    var a = U.clamp((0.95 - zoom) / 0.45, 0, 0.75);
    if (a > 0.01 && Render.high() && Game.settings.weather !== false) {
      ctx.globalAlpha = a;
      clouds.forEach(function (c) {
        var cw = 260 * c.s * 1.4, ch = 130 * c.s * 1.4, x = c.x - cw / 2, y = c.y - 220 - ch / 2;
        if (x > v.x1 || x + cw < v.x0 || y > v.y1 || y + ch < v.y0 - 200) return;
        ctx.drawImage(spr.clouds[c.k], x, y, cw, ch);
      });
      ctx.globalAlpha = 1;
    }
    void time;
  }

  function drawScreen(ctx, cw, ch, dpr, time) {
    var s = Game.s, W = cw * dpr, H = ch * dpr;
    if (s && s.events) {
      var rain = s.events.some(function (e) { return e.id === 'chuva'; });
      var dry = s.events.some(function (e) { return e.id === 'seca'; });
      if (rain) { ctx.fillStyle = 'rgba(30,45,70,0.18)'; ctx.fillRect(0, 0, W, H); }
      if (dry) { ctx.fillStyle = 'rgba(255,170,60,0.08)'; ctx.fillRect(0, 0, W, H); }
    }
    for (var n = 0; n < screen.length; n++) {
      var q = screen[n];
      if (q.t === 'rain') {
        ctx.strokeStyle = 'rgba(200,220,255,0.45)'; ctx.lineWidth = 1 * dpr;
        ctx.beginPath(); ctx.moveTo(q.x * W, q.y * H); ctx.lineTo((q.x - 0.012) * W, (q.y + 0.03) * H); ctx.stroke();
      } else if (q.t === 'conf') {
        ctx.save();
        ctx.globalAlpha = q.life > q.max - 0.6 ? (q.max - q.life) / 0.6 : 1;
        ctx.translate(q.x * W, q.y * H); ctx.rotate(q.r);
        ctx.fillStyle = q.col; ctx.fillRect(-3 * dpr, -1.5 * dpr, 6 * dpr, 3 * dpr);
        ctx.restore();
      }
    }
    void time;
  }

  function reset() { parts = []; screen = []; grows = {}; smokeT = {}; birds = []; }

  return { onTile: onTile, drawGrow: drawGrow, smoke: smoke, dayEnd: dayEnd, confetti: confetti, update: update,
    drawWorld: drawWorld, drawSky: drawSky, drawScreen: drawScreen, reset: reset };
})();

/* Mundo Renda - arte procedural isométrica (sem imagens externas). Tudo é desenhado em canvas e guardado em cache. */
'use strict';

var Sprites = (function () {
  var TW = 64, TH = 32, SS = 2;
  var cache = {};
  var brand = '#2e86de';

  function setScale(s) { if (s !== SS) { SS = s; cache = {}; } }
  function setBrand(c) { if (c !== brand) { brand = c; cache = {}; } }
  function clearCache() { cache = {}; }

  function iso(u, v, z) { return [(u - v) * TW / 2, (u + v) * TH / 2 - (z || 0)]; }

  function make(w, h, ox, oy, fn) {
    var c = document.createElement('canvas');
    c.width = Math.ceil(w * SS); c.height = Math.ceil(h * SS);
    var g = c.getContext('2d');
    g.scale(SS, SS); g.translate(ox, oy);
    g.lineJoin = 'round'; g.lineCap = 'round';
    fn(g);
    return { c: c, ox: ox, oy: oy, w: w, h: h };
  }

  function poly(g, pts, fill, stroke, lw) {
    g.beginPath();
    g.moveTo(pts[0][0], pts[0][1]);
    for (var n = 1; n < pts.length; n++) g.lineTo(pts[n][0], pts[n][1]);
    g.closePath();
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 1; g.stroke(); }
  }
  function quad(g, u0, v0, u1, v1, z, fill, stroke) {
    poly(g, [iso(u0, v0, z), iso(u1, v0, z), iso(u1, v1, z), iso(u0, v1, z)], fill, stroke);
  }
  function circle(g, x, y, r, fill, stroke) {
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = 1; g.stroke(); }
  }
  function ellipse(g, x, y, rx, ry, fill) {
    g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); g.fillStyle = fill; g.fill();
  }
  function shadow(g, f, a) {
    var p = iso(0.06, 0.06, 0);
    g.save(); g.globalAlpha = a || 0.18;
    poly(g, [[p[0], p[1] - f * 32], [p[0] + f * 64, p[1]], [p[0], p[1] + f * 32], [p[0] - f * 64, p[1]]], '#13301c');
    g.restore();
  }

  /* ---------------- Terreno ---------------- */
  function terrain(t, variant) {
    var key = 't' + t + '_' + variant;
    if (cache[key]) return cache[key];
    var base = DATA.TERRAIN[t].color;
    var r = U.rng(t * 977 + variant * 131 + 7);
    var col = U.shade(base, (variant - 1.5) * 0.025);
    cache[key] = make(TW + 2, TH + 2, TW / 2 + 1, TH / 2 + 1, function (g) {
      poly(g, [[0, -TH / 2 - 0.7], [TW / 2 + 1.2, 0], [0, TH / 2 + 0.7], [-TW / 2 - 1.2, 0]], col);
      for (var n = 0; n < 16; n++) {
        var u = r() - 0.5, v = r() - 0.5;
        if (Math.abs(u) + Math.abs(v) > 0.45) continue;
        var p = iso(u * 0.95, v * 0.95, 0);
        var dark = r() < 0.5;
        if (t <= 2) {
          g.strokeStyle = U.shade(base, dark ? -0.18 : 0.18); g.lineWidth = 0.8;
          g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[0] + (r() - 0.5) * 1.5, p[1] - 2 - r() * 1.5); g.stroke();
        } else if (t === 5) {
          ellipse(g, p[0], p[1], 1.6 + r() * 1.4, 0.9 + r() * 0.6, U.shade(base, dark ? -0.2 : 0.2));
        } else {
          circle(g, p[0], p[1], 0.5 + r() * 0.6, U.shade(base, dark ? -0.15 : 0.15));
        }
      }
    });
    return cache[key];
  }

  // água: máscara de margens (1=NE, 2=SE, 4=SO, 8=NO) e quadro de animação
  function water(mask, frame) {
    var key = 'w' + mask + '_' + frame;
    if (cache[key]) return cache[key];
    cache[key] = make(TW + 2, TH + 2, TW / 2 + 1, TH / 2 + 1, function (g) {
      var top = [0, -TH / 2], right = [TW / 2, 0], bot = [0, TH / 2], left = [-TW / 2, 0];
      poly(g, [[0, -TH / 2 - 0.7], [TW / 2 + 1.2, 0], [0, TH / 2 + 0.7], [-TW / 2 - 1.2, 0]], U.shade('#3f9fd8', frame * 0.02 - 0.02));
      var r = U.rng(frame * 31 + 5);
      g.strokeStyle = 'rgba(255,255,255,0.35)'; g.lineWidth = 0.9;
      for (var n = 0; n < 3; n++) {
        var u = r() * 0.6 - 0.3, v = r() * 0.6 - 0.3, p = iso(u, v, 0);
        g.beginPath(); g.moveTo(p[0] - 4, p[1]); g.quadraticCurveTo(p[0], p[1] - 1.5, p[0] + 4, p[1]); g.stroke();
      }
      var edges = [[1, top, right], [2, right, bot], [4, bot, left], [8, left, top]];
      edges.forEach(function (e) {
        if (!(mask & e[0])) return;
        var a = e[1], b = e[2];
        var cx = 0, cy = 0, k = 0.12;
        var a2 = [a[0] + (cx - a[0]) * k, a[1] + (cy - a[1]) * k], b2 = [b[0] + (cx - b[0]) * k, b[1] + (cy - b[1]) * k];
        g.strokeStyle = 'rgba(255,255,255,0.75)'; g.lineWidth = 1.6;
        g.beginPath(); g.moveTo(a2[0], a2[1]); g.lineTo(b2[0], b2[1]); g.stroke();
        g.strokeStyle = 'rgba(40,110,160,0.5)'; g.lineWidth = 2.5;
        var k2 = 0.25;
        var a3 = [a[0] + (cx - a[0]) * k2, a[1] + (cy - a[1]) * k2], b3 = [b[0] + (cx - b[0]) * k2, b[1] + (cy - b[1]) * k2];
        g.beginPath(); g.moveTo(a3[0], a3[1]); g.lineTo(b3[0], b3[1]); g.stroke();
      });
    });
    return cache[key];
  }

  /* ---------------- Estradas (máscara de conexões 1=NE 2=SE 4=SO 8=NO) ---------------- */
  function road(id, mask) {
    var key = 'r' + id + mask;
    if (cache[key]) return cache[key];
    var colors = id === 'rua' ? ['#7d7a76', '#bdb7ab'] : id === 'ponte' ? ['#6b4a2b', '#a9753f'] : ['#a37a4b', '#cfa877'];
    cache[key] = make(TW + 2, TH + 12, TW / 2 + 1, TH / 2 + 8, function (g) {
      function shape(r, ext) {
        var rects = [[-r, -r, r, r]];
        if (mask & 1) rects.push([-r, -0.5 - ext, r, -r]);
        if (mask & 2) rects.push([r, -r, 0.5 + ext, r]);
        if (mask & 4) rects.push([-r, r, r, 0.5 + ext]);
        if (mask & 8) rects.push([-0.5 - ext, -r, -r, r]);
        return rects;
      }
      var R = mask ? 0.26 : 0.3;
      if (id === 'ponte') {
        shape(R + 0.02, 0.02).forEach(function (q) { quad(g, q[0], q[1], q[2], q[3], 0, 'rgba(0,0,0,0.25)'); });
        shape(R, 0.02).forEach(function (q) { quad(g, q[0], q[1], q[2], q[3], 2, colors[1]); });
        g.strokeStyle = colors[0]; g.lineWidth = 0.7;
        for (var n = -5; n <= 5; n++) {
          var t = n / 10;
          if (mask & 5) { var a = iso(-R, t, 2), b = iso(R, t, 2); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke(); }
          if (mask & 10 || !mask) { var c = iso(t, -R, 2), d = iso(t, R, 2); g.beginPath(); g.moveTo(c[0], c[1]); g.lineTo(d[0], d[1]); g.stroke(); }
        }
        g.strokeStyle = '#5a3b20'; g.lineWidth = 1.2;
        var rails = (mask & 5) && !(mask & 10) ? [[-R, -0.52, -R, 0.52], [R, -0.52, R, 0.52]] :
          (mask & 10) && !(mask & 5) ? [[-0.52, -R, 0.52, -R], [-0.52, R, 0.52, R]] : [];
        rails.forEach(function (l) {
          var p1 = iso(l[0], l[1], 6), p2 = iso(l[2], l[3], 6);
          g.beginPath(); g.moveTo(p1[0], p1[1]); g.lineTo(p2[0], p2[1]); g.stroke();
          for (var m = 0; m <= 2; m++) {
            var f = m / 2, uu = l[0] + (l[2] - l[0]) * f, vv = l[1] + (l[3] - l[1]) * f;
            var q1 = iso(uu, vv, 2), q2 = iso(uu, vv, 6);
            g.beginPath(); g.moveTo(q1[0], q1[1]); g.lineTo(q2[0], q2[1]); g.stroke();
          }
        });
        return;
      }
      shape(R + 0.04, 0.02).forEach(function (q) { quad(g, q[0], q[1], q[2], q[3], 0, colors[0]); });
      shape(R - 0.01, 0.02).forEach(function (q) { quad(g, q[0], q[1], q[2], q[3], 0, colors[1]); });
      var r = U.rng(mask * 7 + (id === 'rua' ? 3 : 1));
      if (id === 'rua') {
        g.strokeStyle = 'rgba(90,85,80,0.35)'; g.lineWidth = 0.5;
        for (var n2 = 0; n2 < 18; n2++) {
          var u = r() - 0.5, v = r() - 0.5, p = iso(u * 0.9, v * 0.9, 0);
          if (inShape(u * 0.9, v * 0.9, shape(R - 0.03, 0))) { g.strokeRect(p[0] - 1.5, p[1] - 0.8, 3, 1.6); }
        }
      } else {
        for (var n3 = 0; n3 < 10; n3++) {
          var u2 = r() - 0.5, v2 = r() - 0.5;
          if (inShape(u2, v2, shape(R - 0.03, 0))) { var p2 = iso(u2, v2, 0); circle(g, p2[0], p2[1], 0.6, 'rgba(110,80,45,0.5)'); }
        }
      }
    });
    return cache[key];
  }
  function inShape(u, v, rects) {
    for (var n = 0; n < rects.length; n++) { var q = rects[n]; if (u >= q[0] && u <= q[2] && v >= q[1] && v <= q[3]) return true; }
    return false;
  }

  /* ---------------- Primitivas de construção ---------------- */
  function box(g, fu, fv, h, wall, opts) {
    opts = opts || {};
    var z0 = opts.z0 || 0, cu = opts.cu || 0, cv = opts.cv || 0;
    var L = U.shade(wall, -0.04), R = U.shade(wall, -0.22);
    poly(g, [iso(cu - fu, cv + fv, z0), iso(cu + fu, cv + fv, z0), iso(cu + fu, cv + fv, z0 + h), iso(cu - fu, cv + fv, z0 + h)], L);
    poly(g, [iso(cu + fu, cv + fv, z0), iso(cu + fu, cv - fv, z0), iso(cu + fu, cv - fv, z0 + h), iso(cu + fu, cv + fv, z0 + h)], R);
    if (opts.top !== false) poly(g, [iso(cu - fu, cv - fv, z0 + h), iso(cu + fu, cv - fv, z0 + h), iso(cu + fu, cv + fv, z0 + h), iso(cu - fu, cv + fv, z0 + h)], opts.top || U.shade(wall, 0.12));
    g.strokeStyle = 'rgba(0,0,0,0.12)'; g.lineWidth = 0.5;
    var a = iso(cu + fu, cv + fv, z0), b = iso(cu + fu, cv + fv, z0 + h);
    g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke();
  }
  function windowL(g, u0, u1, v, z0, z1, col) {
    poly(g, [iso(u0, v, z0), iso(u1, v, z0), iso(u1, v, z1), iso(u0, v, z1)], col || '#5a86ad');
    poly(g, [iso(u0, v, z1 - (z1 - z0) * 0.35), iso(u1, v, z1 - (z1 - z0) * 0.35), iso(u1, v, z1), iso(u0, v, z1)], 'rgba(255,255,255,0.25)');
  }
  function windowR(g, u, v0, v1, z0, z1, col) {
    poly(g, [iso(u, v0, z0), iso(u, v1, z0), iso(u, v1, z1), iso(u, v0, z1)], col || '#4b7395');
  }
  function gable(g, fu, fv, h, rh, roof, wall) {
    var o = 0.05;
    poly(g, [iso(-fu - o, -fv - o, h), iso(fu + o, -fv - o, h), iso(fu + o, 0, h + rh), iso(-fu - o, 0, h + rh)], U.shade(roof, 0.1));
    poly(g, [iso(fu, -fv, h), iso(fu, fv, h), iso(fu, 0, h + rh)], U.shade(wall, -0.22));
    poly(g, [iso(-fu - o, fv + o, h), iso(fu + o, fv + o, h), iso(fu + o, 0, h + rh), iso(-fu - o, 0, h + rh)], U.shade(roof, -0.06));
    g.strokeStyle = U.shade(roof, -0.25); g.lineWidth = 0.6;
    for (var n = 1; n <= 3; n++) {
      var t = n / 4, a = iso(-fu - o, (fv + o) * (1 - t), h + rh * t), b = iso(fu + o, (fv + o) * (1 - t), h + rh * t);
      g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke();
    }
    var r1 = iso(-fu - o, 0, h + rh), r2 = iso(fu + o, 0, h + rh);
    g.strokeStyle = U.shade(roof, -0.35); g.lineWidth = 1;
    g.beginPath(); g.moveTo(r1[0], r1[1]); g.lineTo(r2[0], r2[1]); g.stroke();
  }
  function pyramid(g, fu, fv, h, rh, roof) {
    var o = 0.04, A = iso(0, 0, h + rh);
    var N = iso(-fu - o, -fv - o, h), E = iso(fu + o, -fv - o, h), S = iso(fu + o, fv + o, h), Wp = iso(-fu - o, fv + o, h);
    poly(g, [N, E, A], U.shade(roof, 0.15));
    poly(g, [Wp, N, A], U.shade(roof, 0.05));
    poly(g, [Wp, S, A], U.shade(roof, -0.05));
    poly(g, [S, E, A], U.shade(roof, -0.25));
  }
  function flatRoof(g, fu, fv, h, roof) {
    quad(g, -fu, -fv, fu, fv, h, U.shade(roof, 0.05));
    quad(g, -fu + 0.05, -fv + 0.05, fu - 0.05, fv - 0.05, h, U.shade(roof, -0.12));
    quad(g, -fu + 0.08, -fv + 0.08, fu - 0.08, fv - 0.08, h, U.shade(roof, 0.0));
  }
  function badge(g, icon, y, lv) {
    circle(g, 0, y, 7.5, 'rgba(255,255,255,0.95)');
    g.lineWidth = 1.4; g.strokeStyle = brand; g.beginPath(); g.arc(0, y, 7.5, 0, Math.PI * 2); g.stroke();
    g.font = '9px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(icon, 0, y + 0.5);
    if (lv > 1) {
      g.font = 'bold 6px sans-serif'; g.fillStyle = '#f5b400'; g.strokeStyle = '#6b4d00'; g.lineWidth = 1.2;
      var s = lv === 2 ? '★★' : '★★★';
      g.strokeText(s, 0, y + 10); g.fillText(s, 0, y + 10);
    }
  }
  function tree(g, u, v, s, variant, fruit) {
    var p = iso(u, v, 0);
    ellipse(g, p[0] + 2, p[1] + 1, 7 * s, 3.5 * s, 'rgba(0,0,0,0.18)');
    g.fillStyle = '#7a5434'; g.fillRect(p[0] - 1.2 * s, p[1] - 9 * s, 2.4 * s, 9 * s);
    var greens = [['#2f8f3a', '#45ad48', '#7dd36a'], ['#2b7d45', '#3f9c55', '#6cc47a'], ['#4d8f2a', '#69ad38', '#9bd35c'], ['#24704a', '#2f8f5c', '#58b884']][variant % 4];
    circle(g, p[0] - 3 * s, p[1] - 12 * s, 5.5 * s, greens[0]);
    circle(g, p[0] + 3.5 * s, p[1] - 12.5 * s, 5.5 * s, greens[0]);
    circle(g, p[0], p[1] - 16 * s, 6.5 * s, greens[1]);
    circle(g, p[0] - 1.5 * s, p[1] - 18 * s, 3.2 * s, greens[2]);
    if (fruit) for (var n = 0; n < 5; n++) circle(g, p[0] + Math.cos(n * 1.7) * 5 * s, p[1] - 14 * s + Math.sin(n * 2.3) * 4 * s, 1.1 * s, fruit);
  }
  function pine(g, u, v, s) {
    var p = iso(u, v, 0);
    ellipse(g, p[0] + 2, p[1] + 1, 6 * s, 3 * s, 'rgba(0,0,0,0.18)');
    g.fillStyle = '#6b4a2e'; g.fillRect(p[0] - 1.2 * s, p[1] - 6 * s, 2.4 * s, 6 * s);
    var cols = ['#1f6b3d', '#28804a', '#35955a'];
    for (var n = 0; n < 3; n++) {
      var y = p[1] - (5 + n * 6) * s, wdt = (8 - n * 2) * s;
      poly(g, [[p[0], y - 9 * s], [p[0] + wdt, y], [p[0] - wdt, y]], cols[n]);
      poly(g, [[p[0], y - 9 * s], [p[0] + wdt, y], [p[0], y]], 'rgba(0,0,0,0.12)');
    }
  }
  function palm(g, u, v, s) {
    var p = iso(u, v, 0);
    ellipse(g, p[0] + 2, p[1] + 1, 6 * s, 3 * s, 'rgba(0,0,0,0.15)');
    g.strokeStyle = '#8a6a42'; g.lineWidth = 2.2 * s;
    g.beginPath(); g.moveTo(p[0], p[1]); g.quadraticCurveTo(p[0] + 4 * s, p[1] - 12 * s, p[0] + 2 * s, p[1] - 22 * s); g.stroke();
    var tx = p[0] + 2 * s, ty = p[1] - 22 * s;
    g.strokeStyle = '#2f9a45'; g.lineWidth = 2 * s;
    for (var n = 0; n < 6; n++) {
      var a = n / 6 * Math.PI * 2;
      g.beginPath(); g.moveTo(tx, ty);
      g.quadraticCurveTo(tx + Math.cos(a) * 7 * s, ty - 4 * s, tx + Math.cos(a) * 11 * s, ty + Math.sin(a) * 4 * s + 4 * s); g.stroke();
    }
    circle(g, tx, ty + 1, 1.8 * s, '#6b4a2e');
  }
  function bush(g, u, v, s) {
    var p = iso(u, v, 0);
    ellipse(g, p[0] + 1, p[1] + 1, 6 * s, 2.5 * s, 'rgba(0,0,0,0.15)');
    circle(g, p[0] - 3 * s, p[1] - 3 * s, 3.5 * s, '#3b8f3c');
    circle(g, p[0] + 3 * s, p[1] - 3 * s, 3.5 * s, '#3b8f3c');
    circle(g, p[0], p[1] - 5 * s, 4 * s, '#52a84c');
  }
  function person(g, x, y, shirt) {
    g.fillStyle = shirt; g.fillRect(x - 1.5, y - 6, 3, 4);
    g.fillStyle = '#3a3a55'; g.fillRect(x - 1.4, y - 2, 1.2, 2); g.fillRect(x + 0.2, y - 2, 1.2, 2);
    circle(g, x, y - 7.5, 1.6, '#c98d5a');
  }

  /* ---------------- Objetos ---------------- */
  var HOUSE_WALLS = ['#f7e1b5', '#f2c9a0', '#eef1f2', '#cde8d6', '#f5d0d0', '#d9e4f5', '#fff2c2'];
  var HOUSE_ROOFS = ['#c0563b', '#a8432f', '#7a5236', '#4f6d8f', '#3d7a5a', '#b8643a'];

  function object(id, lv, variant) {
    var key = 'o' + id + '_' + lv + '_' + variant;
    if (cache[key]) return cache[key];
    var it = DATA.BY_ID[id], d = it.draw || {}, maxH = it.kind === 'natural' ? 50 : it.kind === 'decor' ? 64 : 96;
    cache[key] = make(TW + 16, TH + maxH, TW / 2 + 8, maxH + TH / 2 - 4, function (g) {
      var p = d.p, r = U.rng(variant * 71 + it.num * 13 + 1);
      var roofC = d.roofC === 'brand' ? brand : d.roofC;
      if (p === 'box' || p === 'hq' || p === 'house' || p === 'sobrado') {
        var fu, fv, h, wall, roof, rh = 10, top = 0;
        if (p === 'hq') { fu = 0.4; fv = 0.4; h = 22 + 8 * (lv - 1); wall = '#f4ead2'; roof = brand; }
        else if (p === 'house') { fu = 0.3; fv = 0.28; h = 12 + 9 * (lv - 1); wall = HOUSE_WALLS[variant % HOUSE_WALLS.length]; roof = HOUSE_ROOFS[(variant >> 1) % HOUSE_ROOFS.length]; }
        else if (p === 'sobrado') { fu = 0.36; fv = 0.34; h = 24 + 9 * (lv - 1); wall = HOUSE_WALLS[(variant + 2) % HOUSE_WALLS.length]; roof = HOUSE_ROOFS[variant % HOUSE_ROOFS.length]; }
        else { fu = d.wide ? 0.42 : 0.36; fv = d.wide ? 0.34 : 0.36; h = d.h * (1 + 0.35 * (lv - 1)); wall = d.wall; roof = roofC; }
        shadow(g, Math.max(fu, fv) + 0.05, 0.2);
        box(g, fu, fv, h, wall, { top: d.roof === 'flat' ? false : undefined });
        // janelas e porta
        var floors = Math.max(1, Math.floor(h / 11));
        var nwin = p === 'house' ? 1 : p === 'sobrado' ? 2 : (d.win || 0);
        for (var fl = 0; fl < floors; fl++) {
          var z0 = 3.5 + fl * 10, z1 = z0 + (d.glass ? 7.5 : 5.5);
          if (z1 > h - 1.5) break;
          for (var n = 0; n < nwin; n++) {
            var span = (2 * fu) / nwin, u0 = -fu + span * n + span * 0.25, u1 = u0 + span * 0.5;
            windowL(g, u0, u1, fv, z0, z1, d.glass ? '#7fb2d9' : null);
          }
          if (fl > 0 || p !== 'house') windowR(g, fu, -fv * 0.6, -fv * 0.15, z0, z1);
        }
        poly(g, [iso(fu, fv * 0.15, 0), iso(fu, fv * 0.6, 0), iso(fu, fv * 0.6, 8), iso(fu, fv * 0.15, 8)], '#7a4f2e');
        if (d.awning) {
          var stripes = 6;
          for (var s2 = 0; s2 < stripes; s2++) {
            var a0 = -fu + (2 * fu) * s2 / stripes, a1 = a0 + (2 * fu) / stripes;
            poly(g, [iso(a0, fv, 11), iso(a1, fv, 11), iso(a1, fv + 0.14, 7), iso(a0, fv + 0.14, 7)], s2 % 2 ? '#ffffff' : brand);
          }
        }
        if (p === 'hq') {
          pyramid(g, fu, fv, h, 14, roof);
          var fp = iso(0, 0, h + 14);
          g.strokeStyle = '#555'; g.lineWidth = 1; g.beginPath(); g.moveTo(fp[0], fp[1]); g.lineTo(fp[0], fp[1] - 14); g.stroke();
          poly(g, [[fp[0], fp[1] - 14], [fp[0] + 9, fp[1] - 11], [fp[0], fp[1] - 8]], brand);
          badge(g, (Game.s && Game.s.project.emoji) || '🏛️', fp[1] - 24, lv);
          return;
        }
        if (d.roof === 'flat') {
          flatRoof(g, fu, fv, h, roof);
          if (d.glass) { var tp = iso(-0.1, -0.1, h); g.fillStyle = '#9aa6ad'; g.fillRect(tp[0] - 3, tp[1] - 4, 6, 4); }
          top = h;
        } else if (d.roof === 'pyramid') { pyramid(g, fu, fv, h, 12, roof); top = h + 12; }
        else {
          gable(g, fu, fv, h, rh, roof, wall); top = h + rh;
          if (d.chimney || (p === 'house' && variant % 3 === 0)) {
            box(g, 0.05, 0.05, 7, '#9b5a3c', { z0: h + rh * 0.5, cu: -fu * 0.5, cv: -fv * 0.45 });
            if (d.chimney) { var cp = iso(-fu * 0.5, -fv * 0.45, h + rh * 0.5 + 9); circle(g, cp[0], cp[1] - 2, 2, 'rgba(230,230,230,0.6)'); circle(g, cp[0] + 2, cp[1] - 5, 2.5, 'rgba(230,230,230,0.45)'); }
          }
        }
        if (p === 'box') badge(g, it.icon, iso(0, 0, top)[1] - 12, lv);
        else if (lv > 1 && p !== 'house' && p !== 'sobrado') badge(g, it.icon, iso(0, 0, top)[1] - 12, lv);
        return;
      }
      switch (p) {
        case 'horta': {
          quad(g, -0.44, -0.44, 0.44, 0.44, 0, '#7b5434');
          quad(g, -0.4, -0.4, 0.4, 0.4, 0, '#8c6240');
          for (var row = 0; row < 4; row++) {
            var vv = -0.3 + row * 0.2;
            for (var c = 0; c < 5; c++) {
              var uu = -0.32 + c * 0.16, q = iso(uu, vv, 0);
              circle(g, q[0], q[1] - 2, 2.6, row % 2 ? '#3f9e45' : '#5fbf4a');
              circle(g, q[0] - 0.8, q[1] - 3, 1.3, '#8be070');
              if ((row + c) % 3 === 0 && row % 2) circle(g, q[0] + 1.5, q[1] - 1.5, 0.9, '#e2412b');
            }
          }
          if (lv > 1) { var sc = iso(0.38, -0.38, 0); g.strokeStyle = '#6b4a2e'; g.lineWidth = 1; g.beginPath(); g.moveTo(sc[0], sc[1]); g.lineTo(sc[0], sc[1] - 12); g.moveTo(sc[0] - 4, sc[1] - 8); g.lineTo(sc[0] + 4, sc[1] - 8); g.stroke(); circle(g, sc[0], sc[1] - 13, 2, '#e8c35a'); }
          badge(g, it.icon, -22, lv);
          break;
        }
        case 'galinheiro': {
          quad(g, -0.44, -0.44, 0.44, 0.44, 0, '#c9b07a');
          shadow(g, 0.25, 0.15);
          box(g, 0.18, 0.16, 9, '#d9a066', { cu: -0.18, cv: -0.18 });
          g.save(); g.translate(iso(-0.18, -0.18, 0)[0], iso(-0.18, -0.18, 0)[1]); gable(g, 0.18, 0.16, 9, 7, '#b2452f', '#d9a066'); g.restore();
          g.strokeStyle = '#8a6a42'; g.lineWidth = 0.8;
          [[-0.44, 0.44, 0.44, 0.44], [0.44, -0.44, 0.44, 0.44]].forEach(function (l) {
            for (var m = 0; m <= 6; m++) { var f = m / 6, pp = iso(l[0] + (l[2] - l[0]) * f, l[1] + (l[3] - l[1]) * f, 0); g.beginPath(); g.moveTo(pp[0], pp[1]); g.lineTo(pp[0], pp[1] - 4); g.stroke(); }
            var a = iso(l[0], l[1], 3), b = iso(l[2], l[3], 3); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke();
          });
          for (var ch = 0; ch < 4 + lv; ch++) {
            var cq = iso(r() * 0.5 - 0.05, r() * 0.5 - 0.05, 0);
            ellipse(g, cq[0], cq[1] - 1.5, 2.2, 1.6, ch % 3 ? '#ffffff' : '#c47a3a');
            circle(g, cq[0] + 1.6, cq[1] - 2.8, 1, '#ffffff'); circle(g, cq[0] + 1.8, cq[1] - 3.6, 0.5, '#e33');
          }
          badge(g, it.icon, -32, lv);
          break;
        }
        case 'pomar': {
          quad(g, -0.45, -0.45, 0.45, 0.45, 0, '#6cbf55');
          [[-0.22, -0.22], [0.22, -0.22], [-0.22, 0.22], [0.22, 0.22]].forEach(function (t2, n2) { tree(g, t2[0], t2[1], 0.62 + 0.08 * lv, n2 + variant, n2 % 2 ? '#f2b705' : '#e0352b'); });
          badge(g, it.icon, -34, lv);
          break;
        }
        case 'viveiro': {
          quad(g, -0.44, -0.44, 0.44, 0.44, 0, '#8c6a46');
          for (var pr = 0; pr < 4; pr++) for (var pc = 0; pc < 4; pc++) {
            var pq = iso(-0.3 + pc * 0.2, -0.3 + pr * 0.2, 0);
            g.fillStyle = '#a0522d'; g.fillRect(pq[0] - 2, pq[1] - 3, 4, 3);
            circle(g, pq[0], pq[1] - 4.5, 2, pr % 2 ? '#4fb34a' : '#7ad35d');
          }
          g.strokeStyle = '#6b6b6b'; g.lineWidth = 0.8;
          [[-0.42, -0.42], [0.42, -0.42], [0.42, 0.42], [-0.42, 0.42]].forEach(function (c2) { var a = iso(c2[0], c2[1], 0), b = iso(c2[0], c2[1], 14); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke(); });
          g.save(); g.globalAlpha = 0.55; quad(g, -0.44, -0.44, 0.44, 0.44, 14, '#1e5a33'); g.restore();
          badge(g, it.icon, -30, lv);
          break;
        }
        case 'apiario': {
          quad(g, -0.45, -0.45, 0.45, 0.45, 0, '#79c55c');
          for (var fl2 = 0; fl2 < 14; fl2++) { var fq = iso(r() - 0.5, r() - 0.5, 0); circle(g, fq[0] * 0.85, fq[1] * 0.85 - 1, 1.2, ['#ff6fa5', '#ffd23f', '#ffffff', '#b57bff'][fl2 % 4]); }
          [[-0.18, -0.15], [0.15, -0.18], [0.0, 0.18]].forEach(function (b2) {
            box(g, 0.08, 0.08, 4, '#f4c542', { cu: b2[0], cv: b2[1] });
            box(g, 0.08, 0.08, 4, '#f7dc7a', { cu: b2[0], cv: b2[1], z0: 4 });
            box(g, 0.1, 0.1, 1.5, '#ffffff', { cu: b2[0], cv: b2[1], z0: 8 });
          });
          badge(g, it.icon, -24, lv);
          break;
        }
        case 'estufa': {
          shadow(g, 0.45, 0.15);
          quad(g, -0.42, -0.4, 0.42, 0.4, 0, '#7b5434');
          for (var er = 0; er < 3; er++) for (var ec = 0; ec < 4; ec++) { var eq = iso(-0.3 + ec * 0.2, -0.25 + er * 0.25, 0); circle(g, eq[0], eq[1] - 2, 2.4, '#4fb34a'); }
          g.save(); g.globalAlpha = 0.5;
          box(g, 0.42, 0.4, 14 + 4 * (lv - 1), '#d8f1ff', { top: false });
          gable(g, 0.42, 0.4, 14 + 4 * (lv - 1), 9, '#e8f7ff', '#d8f1ff');
          g.restore();
          g.strokeStyle = 'rgba(255,255,255,0.9)'; g.lineWidth = 0.7;
          for (var em = 0; em <= 4; em++) { var eu = -0.42 + em * 0.21, a2 = iso(eu, 0.4, 0), b3 = iso(eu, 0.4, 14 + 4 * (lv - 1)); g.beginPath(); g.moveTo(a2[0], a2[1]); g.lineTo(b3[0], b3[1]); g.stroke(); }
          badge(g, it.icon, -46 - 4 * (lv - 1), lv);
          break;
        }
        case 'coleta': {
          quad(g, -0.44, -0.44, 0.44, 0.44, 0, '#b8b8b0');
          shadow(g, 0.25, 0.15);
          box(g, 0.2, 0.3, 12, '#9fb3a0', { cu: -0.18, cv: -0.05 });
          g.save(); var cpt = iso(-0.18, -0.05, 0); g.translate(cpt[0], cpt[1]); flatRoof(g, 0.2, 0.3, 12, brand); g.restore();
          [['#2e86de', 0.2, -0.25], ['#e74c3c', 0.22, -0.02], ['#27ae60', 0.0, 0.32], ['#f1c40f', 0.24, 0.21]].forEach(function (bn) { box(g, 0.07, 0.07, 7, bn[0], { cu: bn[1], cv: bn[2] }); });
          badge(g, it.icon, -32, lv);
          break;
        }
        case 'feira': {
          quad(g, -0.45, -0.45, 0.45, 0.45, 0, '#d8c9a6');
          var tents = lv === 1 ? [[-0.2, -0.2], [0.2, 0.15]] : [[-0.2, -0.2], [-0.15, 0.25], [0.2, 0.15]];
          tents.sort(function (a, b) { return (a[0] + a[1]) - (b[0] + b[1]); });
          tents.forEach(function (tp2, n3) {
            var cu = tp2[0], cv = tp2[1];
            g.strokeStyle = '#6b4a2e'; g.lineWidth = 0.8;
            [[-0.14, -0.14], [0.14, -0.14], [0.14, 0.14], [-0.14, 0.14]].forEach(function (c3) { var a = iso(cu + c3[0], cv + c3[1], 0), b = iso(cu + c3[0], cv + c3[1], 9); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke(); });
            box(g, 0.14, 0.12, 3, '#a8743f', { cu: cu, cv: cv });
            for (var pd = 0; pd < 5; pd++) { var pp2 = iso(cu - 0.1 + pd * 0.05, cv, 3); circle(g, pp2[0], pp2[1] - 1, 1.3, ['#e0352b', '#f2b705', '#4fb34a', '#ff8c1a', '#9b59b6'][(pd + n3) % 5]); }
            g.save(); g.translate(iso(cu, cv, 0)[0], iso(cu, cv, 0)[1]); pyramid(g, 0.17, 0.17, 9, 7, n3 % 2 ? '#ffffff' : brand); g.restore();
          });
          badge(g, it.icon, -30, lv);
          break;
        }
        case 'solar': {
          quad(g, -0.44, -0.44, 0.44, 0.44, 0, '#c9c9c0');
          for (var sr = 0; sr < 2; sr++) {
            var sv = -0.2 + sr * 0.38;
            poly(g, [iso(-0.38, sv - 0.12, 3), iso(0.38, sv - 0.12, 3), iso(0.38, sv + 0.12, 9), iso(-0.38, sv + 0.12, 9)], '#1f3b73', '#9db4e0', 0.6);
            g.strokeStyle = 'rgba(160,190,240,0.6)'; g.lineWidth = 0.4;
            for (var sl = 1; sl < 5; sl++) { var su = -0.38 + sl * 0.152, a3 = iso(su, sv - 0.12, 3), b4 = iso(su, sv + 0.12, 9); g.beginPath(); g.moveTo(a3[0], a3[1]); g.lineTo(b4[0], b4[1]); g.stroke(); }
          }
          badge(g, it.icon, -24, lv);
          break;
        }
        case 'poco': {
          shadow(g, 0.25, 0.15);
          var pc0 = iso(0, 0, 0);
          ellipse(g, pc0[0], pc0[1], 12, 6, '#8e8e8e');
          g.fillStyle = '#9d9d9d'; g.fillRect(pc0[0] - 12, pc0[1] - 6, 24, 6);
          ellipse(g, pc0[0], pc0[1] - 6, 12, 6, '#b5b5b5');
          ellipse(g, pc0[0], pc0[1] - 6, 9, 4.5, '#2a6fa8');
          g.strokeStyle = '#6b4a2e'; g.lineWidth = 1.5;
          g.beginPath(); g.moveTo(pc0[0] - 11, pc0[1] - 6); g.lineTo(pc0[0] - 11, pc0[1] - 22); g.moveTo(pc0[0] + 11, pc0[1] - 6); g.lineTo(pc0[0] + 11, pc0[1] - 22); g.stroke();
          poly(g, [[pc0[0] - 15, pc0[1] - 20], [pc0[0], pc0[1] - 30], [pc0[0] + 15, pc0[1] - 20]], '#a8432f');
          badge(g, it.icon, -40, lv);
          break;
        }
        case 'fonte': {
          shadow(g, 0.3, 0.12);
          var fc = iso(0, 0, 0);
          ellipse(g, fc[0], fc[1], 22, 11, '#a7a39a');
          g.fillStyle = '#b9b4a8'; g.fillRect(fc[0] - 22, fc[1] - 4, 44, 4);
          ellipse(g, fc[0], fc[1] - 4, 22, 11, '#cfcabe');
          ellipse(g, fc[0], fc[1] - 4, 18, 9, '#4aa8e0');
          g.fillStyle = '#cfcabe'; g.fillRect(fc[0] - 2, fc[1] - 18, 4, 14);
          ellipse(g, fc[0], fc[1] - 18, 6, 3, '#d9d4c8');
          for (var dr = 0; dr < 10; dr++) { var a4 = dr / 10 * Math.PI * 2; circle(g, fc[0] + Math.cos(a4) * 8, fc[1] - 14 + Math.sin(a4) * 3, 1, 'rgba(255,255,255,0.85)'); }
          circle(g, fc[0], fc[1] - 24, 2, 'rgba(255,255,255,0.9)');
          break;
        }
        case 'praca': {
          quad(g, -0.5, -0.5, 0.5, 0.5, 0, '#d9d2c1');
          quad(g, -0.42, -0.42, 0.42, 0.42, 0, '#e6dfcf');
          [[-0.34, -0.34], [0.34, -0.34], [0.34, 0.34], [-0.34, 0.34]].forEach(function (c4) { var q4 = iso(c4[0], c4[1], 0); ellipse(g, q4[0], q4[1], 5, 2.5, '#5aa845'); circle(g, q4[0], q4[1] - 1.5, 1, '#ff6fa5'); });
          box(g, 0.12, 0.04, 2.5, '#9b6b3e', { cu: 0.0, cv: 0.3 });
          box(g, 0.04, 0.12, 2.5, '#9b6b3e', { cu: 0.3, cv: 0.0 });
          tree(g, 0, 0, 0.85, variant, null);
          break;
        }
        case 'parquinho': {
          quad(g, -0.45, -0.45, 0.45, 0.45, 0, '#ecd9a0');
          var s0 = iso(-0.2, 0.1, 0), s1 = iso(0.2, 0.1, 0);
          g.strokeStyle = '#e74c3c'; g.lineWidth = 1.5;
          g.beginPath(); g.moveTo(s0[0], s0[1]); g.lineTo(s0[0] + 3, s0[1] - 16); g.lineTo(s0[0] + 6, s0[1]); g.stroke();
          g.beginPath(); g.moveTo(s1[0], s1[1]); g.lineTo(s1[0] - 3, s1[1] - 16); g.lineTo(s1[0] - 6, s1[1]); g.stroke();
          g.strokeStyle = '#2e86de'; g.beginPath(); g.moveTo(s0[0] + 3, s0[1] - 16); g.lineTo(s1[0] - 3, s1[1] - 16); g.stroke();
          g.strokeStyle = '#555'; g.lineWidth = 0.6;
          var sw = iso(0, 0.1, 0); g.beginPath(); g.moveTo(sw[0] - 3, sw[1] - 16); g.lineTo(sw[0] - 3, sw[1] - 5); g.moveTo(sw[0] + 3, sw[1] - 16); g.lineTo(sw[0] + 3, sw[1] - 5); g.stroke();
          g.fillStyle = '#f1c40f'; g.fillRect(sw[0] - 4, sw[1] - 5, 8, 1.5);
          var sl0 = iso(-0.15, -0.25, 0);
          poly(g, [[sl0[0], sl0[1] - 12], [sl0[0] + 16, sl0[1]], [sl0[0] + 13, sl0[1] + 1], [sl0[0] - 3, sl0[1] - 11]], '#27ae60');
          g.strokeStyle = '#7f8c8d'; g.lineWidth = 1; g.beginPath(); g.moveTo(sl0[0], sl0[1] - 12); g.lineTo(sl0[0] - 2, sl0[1]); g.stroke();
          break;
        }
        case 'mural': {
          shadow(g, 0.4, 0.12);
          box(g, 0.42, 0.06, 18, '#efe6d6');
          var cols = ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6', '#e67e22'];
          for (var mm = 0; mm < 7; mm++) {
            var mu = -0.38 + r() * 0.7, mz = 3 + r() * 11;
            var m1 = iso(mu, 0.06, mz);
            circle(g, m1[0], m1[1], 2 + r() * 3, cols[mm % cols.length]);
          }
          var mp = iso(-0.3, 0.06, 6), mq = iso(0.35, 0.06, 12);
          g.strokeStyle = '#2c3e50'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(mp[0], mp[1]); g.quadraticCurveTo((mp[0] + mq[0]) / 2, mp[1] - 10, mq[0], mq[1]); g.stroke();
          break;
        }
        case 'estatua': {
          shadow(g, 0.3, 0.15);
          box(g, 0.22, 0.22, 4, '#b8b2a5');
          box(g, 0.14, 0.14, 12, '#cbc5b8', { z0: 4 });
          var st0 = iso(0, 0, 16);
          g.fillStyle = '#6d5a3a'; g.fillRect(st0[0] - 3, st0[1] - 12, 6, 12);
          circle(g, st0[0], st0[1] - 15, 3, '#6d5a3a');
          g.strokeStyle = '#6d5a3a'; g.lineWidth = 2; g.beginPath(); g.moveTo(st0[0] + 3, st0[1] - 10); g.lineTo(st0[0] + 7, st0[1] - 20); g.stroke();
          circle(g, st0[0] + 7, st0[1] - 22, 2.2, '#f5b400');
          break;
        }
        case 'tree': tree(g, 0, 0, 0.85 + (variant % 3) * 0.12, variant, null); break;
        case 'pine': pine(g, 0, 0, 0.8 + (variant % 3) * 0.12); break;
        case 'palm': palm(g, 0, 0, 0.9 + (variant % 2) * 0.12); break;
        case 'bush': bush(g, (variant % 3 - 1) * 0.1, 0, 0.9 + (variant % 2) * 0.2); break;
        case 'rock': {
          var rp = iso((variant % 3 - 1) * 0.1, 0, 0), sz = 0.8 + (variant % 3) * 0.25;
          ellipse(g, rp[0] + 2, rp[1] + 1, 9 * sz, 4 * sz, 'rgba(0,0,0,0.18)');
          poly(g, [[rp[0] - 9 * sz, rp[1]], [rp[0] - 6 * sz, rp[1] - 7 * sz], [rp[0] + 1 * sz, rp[1] - 10 * sz], [rp[0] + 8 * sz, rp[1] - 5 * sz], [rp[0] + 9 * sz, rp[1]], [rp[0], rp[1] + 3 * sz]], '#8a8f93');
          poly(g, [[rp[0] - 6 * sz, rp[1] - 7 * sz], [rp[0] + 1 * sz, rp[1] - 10 * sz], [rp[0] + 8 * sz, rp[1] - 5 * sz], [rp[0], rp[1] - 3 * sz]], '#aab0b4');
          break;
        }
        case 'flowers': {
          quad(g, -0.32, -0.32, 0.32, 0.32, 0, '#8c6240');
          quad(g, -0.32, -0.32, 0.32, 0.32, 1.5, '#9b6e48');
          var fcol = ['#ff4d6d', '#ffd23f', '#ffffff', '#b57bff', '#ff8c1a'][variant % 5];
          for (var fw = 0; fw < 16; fw++) { var fq2 = iso(r() * 0.56 - 0.28, r() * 0.56 - 0.28, 1.5); circle(g, fq2[0], fq2[1] - 2, 1.6, '#3f9e45'); circle(g, fq2[0], fq2[1] - 3, 1.3, fw % 3 ? fcol : '#ffd23f'); }
          break;
        }
        case 'wildflowers': {
          for (var wf = 0; wf < 9; wf++) { var wq = iso(r() * 0.7 - 0.35, r() * 0.7 - 0.35, 0); g.strokeStyle = '#3f9e45'; g.lineWidth = 0.6; g.beginPath(); g.moveTo(wq[0], wq[1]); g.lineTo(wq[0], wq[1] - 3); g.stroke(); circle(g, wq[0], wq[1] - 3.5, 1.2, ['#ffd23f', '#ffffff', '#ff8fb1', '#c39bff'][(wf + variant) % 4]); }
          break;
        }
        case 'hedge': {
          box(g, 0.42, 0.42, 5, '#3f8f3f', { top: '#58b04f' });
          for (var hd = 0; hd < 10; hd++) { var hq = iso(r() * 0.8 - 0.4, r() * 0.8 - 0.4, 5); circle(g, hq[0], hq[1], 1.5, '#6cc35d'); }
          break;
        }
        case 'bench': {
          shadow(g, 0.2, 0.12);
          box(g, 0.24, 0.07, 3, '#9b6b3e');
          box(g, 0.24, 0.02, 4, '#8a5c33', { cv: -0.06, z0: 3 });
          var lp = iso(0.32, 0.25, 0); g.strokeStyle = '#444'; g.lineWidth = 1; g.beginPath(); g.moveTo(lp[0], lp[1]); g.lineTo(lp[0], lp[1] - 5); g.stroke();
          g.fillStyle = '#3d7a5a'; g.fillRect(lp[0] - 2, lp[1] - 7, 4, 2.5);
          break;
        }
        case 'lamp': {
          var lb = iso(0, 0, 0);
          ellipse(g, lb[0] + 1, lb[1] + 1, 4, 2, 'rgba(0,0,0,0.2)');
          g.strokeStyle = '#3c4148'; g.lineWidth = 1.6; g.beginPath(); g.moveTo(lb[0], lb[1]); g.lineTo(lb[0], lb[1] - 24); g.lineTo(lb[0] + 5, lb[1] - 26); g.stroke();
          ellipse(g, lb[0] + 6, lb[1] - 25, 3, 1.6, '#3c4148');
          circle(g, lb[0] + 6, lb[1] - 24, 1.6, '#ffe9a0');
          break;
        }
        default: {
          box(g, 0.3, 0.3, 12, '#ddd');
        }
      }
    });
    return cache[key];
  }

  // preto e branco/realce de seleção
  function diamondPath(ctx, x, y, s) {
    s = s || 1;
    ctx.beginPath();
    ctx.moveTo(x, y - TH / 2 * s); ctx.lineTo(x + TW / 2 * s, y); ctx.lineTo(x, y + TH / 2 * s); ctx.lineTo(x - TW / 2 * s, y); ctx.closePath();
  }

  return {
    TW: TW, TH: TH, setScale: setScale, setBrand: setBrand, clearCache: clearCache, terrain: terrain, water: water,
    road: road, object: object, diamondPath: diamondPath, person: person, iso: iso,
    scale: function () { return SS; }
  };
})();

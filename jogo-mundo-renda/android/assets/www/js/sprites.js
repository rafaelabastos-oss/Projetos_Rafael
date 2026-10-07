/* Mundo Renda - arte isométrica procedural (nenhuma imagem externa).
   Cada objeto é desenhado uma vez em canvas e guardado em cache, junto com metadados:
   sombra projetada (para o terreno), janelas (para acender à noite), luzes, chaminés e partes animadas. */
'use strict';

var Sprites = (function () {
  var TW = 64, TH = 32, SS = 2;
  var cache = {}, badgeCache = {}, thumbs = {};
  var brand = '#2e86de';
  var LU = 0.021, LV = 0.005;          // direção do sol para as sombras (ladrilhos por pixel de altura)
  var g = null, B = null;               // contexto e metadados do sprite em construção

  function setScale(s) { if (s !== SS) { SS = s; cache = {}; badgeCache = {}; } }
  function setBrand(c) { if (c !== brand) { brand = c; cache = {}; badgeCache = {}; thumbs = {}; } }
  function clearCache() { cache = {}; badgeCache = {}; thumbs = {}; }

  /* ---------------- Cores ---------------- */
  var colCache = {};
  function rgb(c) {
    if (colCache[c]) return colCache[c];
    var r;
    if (c[0] === '#') {
      var h = c.slice(1);
      if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
      r = [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)];
    } else { var m = c.match(/[\d.]+/g); r = [+m[0], +m[1], +m[2]]; }
    colCache[c] = r;
    return r;
  }
  function sh(c, a) {
    var p = rgb(c), r = p[0], gg = p[1], b = p[2];
    if (a >= 0) { r += (255 - r) * a; gg += (255 - gg) * a; b += (255 - b) * a; }
    else { r *= 1 + a; gg *= 1 + a; b *= 1 + a; }
    return 'rgb(' + Math.round(r) + ',' + Math.round(gg) + ',' + Math.round(b) + ')';
  }
  function al(c, a) { var p = rgb(c); return 'rgba(' + p[0] + ',' + p[1] + ',' + p[2] + ',' + a + ')'; }

  /* ---------------- Primitivas ---------------- */
  function iso(u, v, z) { return [(u - v) * 32, (u + v) * 16 - (z || 0)]; }
  function track(y) { if (B && y < B.minY) B.minY = y; }
  function path(pts) {
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (var n = 1; n < pts.length; n++) g.lineTo(pts[n][0], pts[n][1]);
    g.closePath();
    for (n = 0; n < pts.length; n++) track(pts[n][1]);
  }
  function poly(pts, fill, stroke, lw) {
    path(pts);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 0.6; g.stroke(); }
  }
  function circ(x, y, r, fill, stroke, lw) {
    g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); track(y - r);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 0.5; g.stroke(); }
  }
  function ell(x, y, rx, ry, fill, stroke) {
    g.beginPath(); g.ellipse(x, y, Math.max(0.01, rx), Math.max(0.01, ry), 0, 0, Math.PI * 2); track(y - ry);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = 0.5; g.stroke(); }
  }
  function line(a, b, col, lw) {
    g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]);
    g.strokeStyle = col; g.lineWidth = lw || 0.5; g.stroke(); track(Math.min(a[1], b[1]));
  }
  function vgrad(y0, y1, stops) {
    var gr = g.createLinearGradient(0, y0, 0, y1);
    for (var n = 0; n < stops.length; n++) gr.addColorStop(stops[n][0], stops[n][1]);
    return gr;
  }
  function clipTo(pts, fn) { g.save(); path(pts); g.clip(); fn(); g.restore(); }
  function q(u0, v0, u1, v1, z) { return [iso(u0, v0, z), iso(u1, v0, z), iso(u1, v1, z), iso(u0, v1, z)]; }
  function quad(u0, v0, u1, v1, z, fill, stroke) { poly(q(u0, v0, u1, v1, z), fill, stroke); }

  /* ---------------- Caixas (paredes) ---------------- */
  // o: {cu, cv, fu, fv, z0, h, wall, wallR, top, tex, mortar, vol, ao}
  function box(o) {
    var cu = o.cu || 0, cv = o.cv || 0, fu = o.fu, fv = o.fv, z0 = o.z0 || 0, h = o.h;
    var wall = o.wall, wallR = o.wallR || sh(wall, -0.2);
    var b = {
      cu: cu, cv: cv, fu: fu, fv: fv, z0: z0, h: h, wall: wall,
      L: function (a, z) { return iso(cu + a, cv + fv, z0 + z); },
      R: function (a, z) { return iso(cu + fu, cv + a, z0 + z); }
    };
    var Lp = [b.L(-fu, 0), b.L(fu, 0), b.L(fu, h), b.L(-fu, h)];
    var Rp = [b.R(fv, 0), b.R(-fv, 0), b.R(-fv, h), b.R(fv, h)];
    var yb = iso(cu + fu, cv + fv, z0)[1], yt = yb - h;
    var gl = h > 3 && o.ao !== false ? vgrad(yb + 6, yt, [[0, sh(wall, -0.16)], [0.22, wall], [1, sh(wall, 0.06)]]) : wall;
    var gr = h > 3 && o.ao !== false ? vgrad(yb + 6, yt, [[0, sh(wallR, -0.16)], [0.22, wallR], [1, sh(wallR, 0.05)]]) : wallR;
    poly(Lp, gl);
    poly(Rp, gr);
    if (o.tex) {
      clipTo(Lp, function () { texture(o.tex, b.L, -fu, fu, h, wall, o); });
      clipTo(Rp, function () { texture(o.tex, b.R, fv, -fv, h, wallR, o); });
    }
    if (o.top !== false) poly([iso(cu - fu, cv - fv, z0 + h), iso(cu + fu, cv - fv, z0 + h), iso(cu + fu, cv + fv, z0 + h), iso(cu - fu, cv + fv, z0 + h)], o.top || sh(wall, 0.16));
    line(b.L(fu, 0.3), b.L(fu, h - 0.2), al('#ffffff', 0.18), 0.5);
    if (o.vol !== false) B.vols.push({ t: 'box', cu: cu, cv: cv, fu: fu, fv: fv, z0: o.float ? z0 : 0, h: o.float ? h : z0 + h });
    return b;
  }

  // texturas aplicadas na face (F mapeia posição ao longo da face e altura para a tela)
  function texture(kind, F, a0, a1, h, base, o) {
    var n, z, a, dir = a1 > a0 ? 1 : -1, len = Math.abs(a1 - a0);
    if (kind === 'brick') {
      var mort = o.mortar || al('#f3e6d3', 0.5), row = 2.1, bl = 0.12;
      for (z = row; z < h; z += row) line(F(a0, z), F(a1, z), mort, 0.32);
      for (n = 0, z = 0; z < h; z += row, n++) {
        for (a = (n % 2) * bl / 2; a < len; a += bl) line(F(a0 + a * dir, z), F(a0 + a * dir, Math.min(h, z + row)), mort, 0.3);
      }
      var r = U.rng(7);
      for (n = 0; n < 26; n++) {
        var rz = Math.floor(r() * h / row) * row, ra = r() * len;
        poly([F(a0 + ra * dir, rz), F(a0 + Math.min(len, ra + bl) * dir, rz), F(a0 + Math.min(len, ra + bl) * dir, rz + row), F(a0 + ra * dir, rz + row)], r() < 0.5 ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.07)');
      }
    } else if (kind === 'wood') {
      for (z = 1.8; z < h; z += 1.8) line(F(a0, z), F(a1, z), al('#3d2412', 0.28), 0.35);
    } else if (kind === 'woodv') {
      for (a = 0.06; a < len; a += 0.07) line(F(a0 + a * dir, 0), F(a0 + a * dir, h), al('#3d2412', 0.3), 0.35);
    } else if (kind === 'metal') {
      for (a = 0.02, n = 0; a < len; a += 0.034, n++) line(F(a0 + a * dir, 0), F(a0 + a * dir, h), n % 2 ? al('#ffffff', 0.22) : al('#000000', 0.16), 0.45);
    } else if (kind === 'stone') {
      var rs = U.rng(11);
      for (z = 0; z < h; z += 2.6) {
        line(F(a0, z), F(a1, z), al('#000000', 0.18), 0.35);
        for (a = rs() * 0.1; a < len; a += 0.11 + rs() * 0.08) line(F(a0 + a * dir, z), F(a0 + a * dir, Math.min(h, z + 2.6)), al('#000000', 0.15), 0.3);
      }
    } else if (kind === 'plaster') {
      var rp = U.rng(5);
      for (n = 0; n < 40; n++) {
        var p = F(a0 + rp() * len * dir, rp() * h);
        circ(p[0], p[1], 0.25 + rp() * 0.35, rp() < 0.5 ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.08)');
      }
      poly([F(a0, 0), F(a1, 0), F(a1, 1.4), F(a0, 1.4)], 'rgba(60,40,20,0.12)');
    } else if (kind === 'glass') {
      var fl = o.floorH || 7;
      poly([F(a0, 0), F(a1, 0), F(a1, h), F(a0, h)], vgrad(F(a0, h)[1], F(a0, 0)[1], [[0, '#bfe3f7'], [0.5, '#6fb1dc'], [1, '#3f7fb0']]));
      for (z = fl; z < h; z += fl) line(F(a0, z), F(a1, z), al('#e8f4fb', 0.85), 0.6);
      for (a = 0.1; a < len; a += 0.12) line(F(a0 + a * dir, 0), F(a0 + a * dir, h), al('#e8f4fb', 0.6), 0.4);
      poly([F(a0 + len * 0.15 * dir, 0), F(a0 + len * 0.35 * dir, 0), F(a0 + len * 0.6 * dir, h), F(a0 + len * 0.4 * dir, h)], 'rgba(255,255,255,0.18)');
    }
    void base;
  }

  /* ---------------- Janelas e portas ---------------- */
  // st: {frame, shutters, cross, sill, glass, noLight}
  function win(F, a0, a1, z0, z1, st) {
    st = st || {};
    var fr = st.frame || '#f6f1e7', fo = 0.018, fz = 0.55;
    var outer = [F(a0 - fo, z0 - fz), F(a1 + fo, z0 - fz), F(a1 + fo, z1 + fz), F(a0 - fo, z1 + fz)];
    if (st.shutters) {
      var sw = (a1 - a0) * 0.55;
      [[a0 - fo - sw, a0 - fo], [a1 + fo, a1 + fo + sw]].forEach(function (s) {
        poly([F(s[0], z0 - fz), F(s[1], z0 - fz), F(s[1], z1 + fz), F(s[0], z1 + fz)], st.shutters);
        for (var zz = z0 + 0.6; zz < z1; zz += 1.1) line(F(s[0], zz), F(s[1], zz), al('#000000', 0.2), 0.3);
      });
    }
    poly(outer, fr);
    var gl = [F(a0, z0), F(a1, z0), F(a1, z1), F(a0, z1)];
    poly(gl, vgrad(gl[2][1], gl[0][1], [[0, st.glass || '#a9d3ee'], [0.55, '#5f8fb5'], [1, '#3e6a8f']]));
    poly([F(a0 + (a1 - a0) * 0.1, z0 + (z1 - z0) * 0.25), F(a0 + (a1 - a0) * 0.35, z0 + (z1 - z0) * 0.25), F(a0 + (a1 - a0) * 0.7, z1 - 0.3), F(a0 + (a1 - a0) * 0.45, z1 - 0.3)], 'rgba(255,255,255,0.28)');
    if (st.cross !== false) {
      var am = (a0 + a1) / 2, zm = (z0 + z1) / 2;
      line(F(am, z0), F(am, z1), fr, 0.45);
      if (z1 - z0 > 3) line(F(a0, zm), F(a1, zm), fr, 0.45);
    }
    if (st.sill !== false) poly([F(a0 - fo * 2, z0 - fz), F(a1 + fo * 2, z0 - fz), F(a1 + fo * 2, z0 - fz - 0.7), F(a0 - fo * 2, z0 - fz - 0.7)], sh(fr, -0.12));
    if (!st.noLight) B.wins.push(gl);
  }
  function door(F, a0, a1, h, col, st) {
    st = st || {};
    var fr = st.frame || sh(col, -0.35);
    poly([F(a0 - 0.02, 0), F(a1 + 0.02, 0), F(a1 + 0.02, h + 0.6), F(a0 - 0.02, h + 0.6)], fr);
    poly([F(a0, 0), F(a1, 0), F(a1, h), F(a0, h)], vgrad(F(a0, h)[1], F(a0, 0)[1], [[0, sh(col, 0.12)], [1, sh(col, -0.1)]]));
    if (st.glass) {
      var gp = [F(a0 + (a1 - a0) * 0.15, h * 0.3), F(a1 - (a1 - a0) * 0.15, h * 0.3), F(a1 - (a1 - a0) * 0.15, h * 0.92), F(a0 + (a1 - a0) * 0.15, h * 0.92)];
      poly(gp, '#86b8d8'); B.wins.push(gp);
    } else if (st.roll) {
      for (var z = 0.8; z < h; z += 0.9) line(F(a0, z), F(a1, z), al('#000000', 0.22), 0.35);
    } else {
      var am = (a0 + a1) / 2;
      line(F(am, 0.4), F(am, h - 0.4), al('#000000', 0.22), 0.35);
      poly([F(a0 + (a1 - a0) * 0.15, h * 0.55), F(am - 0.01, h * 0.55), F(am - 0.01, h * 0.9), F(a0 + (a1 - a0) * 0.15, h * 0.9)], al('#ffffff', 0.12));
      var kp = F(a1 - (a1 - a0) * 0.2, h * 0.45); circ(kp[0], kp[1], 0.35, '#e8c75a');
    }
  }
  function awning(F, a0, a1, z, depth, c1, c2, outwardFn) {
    var n = Math.max(3, Math.round((a1 - a0) / 0.07)), s;
    for (s = 0; s < n; s++) {
      var x0 = a0 + (a1 - a0) * s / n, x1 = a0 + (a1 - a0) * (s + 1) / n;
      poly([F(x0, z), F(x1, z), outwardFn(x1, z - 3.2, depth), outwardFn(x0, z - 3.2, depth)], s % 2 ? c2 : c1);
    }
    for (s = 0; s < n; s++) {
      var x2 = a0 + (a1 - a0) * (s + 0.5) / n, p = outwardFn(x2, z - 3.2, depth);
      ell(p[0], p[1] + 0.4, 1.6, 0.8, s % 2 ? sh(c2, -0.1) : sh(c1, -0.1));
    }
  }
  function sign(F, a0, a1, z0, z1, col, icon) {
    poly([F(a0, z0), F(a1, z0), F(a1, z1), F(a0, z1)], col, sh(col, -0.35), 0.4);
    if (icon) {
      var c = F((a0 + a1) / 2, (z0 + z1) / 2);
      g.font = ((z1 - z0) * 0.95).toFixed(1) + 'px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(icon, c[0], c[1] + 0.3);
    }
  }

  /* ---------------- Telhados ---------------- */
  // telha colonial num plano: e0->e1 é a beira, r0->r1 a cumeeira
  function tiledPlane(e0, e1, r1, r0, col, rows, cols) {
    var pts = [e0, e1, r1, r0];
    poly(pts, col);
    clipTo(pts, function () {
      var n, t;
      for (n = 0; n <= cols; n++) {
        t = n / cols;
        var a = [e0[0] + (e1[0] - e0[0]) * t, e0[1] + (e1[1] - e0[1]) * t], b = [r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t];
        line(a, b, al('#000000', 0.16), 0.9);
        line([a[0] + 0.7, a[1]], [b[0] + 0.7, b[1]], al('#ffffff', 0.12), 0.5);
      }
      for (n = 1; n < rows; n++) {
        t = n / rows;
        var c = [e0[0] + (r0[0] - e0[0]) * t, e0[1] + (r0[1] - e0[1]) * t], d = [e1[0] + (r1[0] - e1[0]) * t, e1[1] + (r1[1] - e1[1]) * t];
        line(c, d, al('#000000', 0.12), 0.45);
      }
    });
    line(e0, e1, al('#000000', 0.25), 0.7);
  }
  function eaveShadow(b, hz) {
    poly([b.L(-b.fu, hz), b.L(b.fu, hz), b.L(b.fu, hz - 2.2), b.L(-b.fu, hz - 2.2)], 'rgba(0,0,0,0.14)');
    poly([b.R(b.fv, hz), b.R(-b.fv, hz), b.R(-b.fv, hz - 2.2), b.R(b.fv, hz - 2.2)], 'rgba(0,0,0,0.16)');
  }
  // duas águas: axis 'u' = cumeeira paralela a u (oitão na face direita); 'v' = paralela a v (oitão na face esquerda)
  function gable(b, axis, rh, col, o) {
    o = o === undefined ? 0.05 : o;
    var cu = b.cu, cv = b.cv, fu = b.fu, fv = b.fv, z = b.z0 + b.h, wallR = sh(b.wall, -0.2);
    eaveShadow(b, b.h);
    if (axis === 'u') {
      var bl = iso(cu - fu - o, cv - fv - o, z), br = iso(cu + fu + o, cv - fv - o, z), fl = iso(cu - fu - o, cv + fv + o, z), fr = iso(cu + fu + o, cv + fv + o, z);
      var r0 = iso(cu - fu - o, cv, z + rh), r1 = iso(cu + fu + o, cv, z + rh);
      tiledPlane(bl, br, r1, r0, sh(col, 0.12), 4, 9);
      poly([iso(cu + fu, cv - fv, z), iso(cu + fu, cv + fv, z), iso(cu + fu, cv, z + rh)], wallR);
      tiledPlane(fl, fr, r1, r0, sh(col, -0.04), 4, 9);
      line(r0, r1, sh(col, -0.4), 1.4);
      line([r0[0], r0[1] - 0.5], [r1[0], r1[1] - 0.5], al('#ffffff', 0.25), 0.5);
      B.vols.push({ t: 'pts', pts: [[cu - fu - o, cv - fv - o, z], [cu + fu + o, cv - fv - o, z], [cu + fu + o, cv + fv + o, z], [cu - fu - o, cv + fv + o, z], [cu - fu - o, cv, z + rh], [cu + fu + o, cv, z + rh]] });
    } else {
      var bl2 = iso(cu - fu - o, cv - fv - o, z), bf = iso(cu - fu - o, cv + fv + o, z), rb = iso(cu + fu + o, cv - fv - o, z), rf = iso(cu + fu + o, cv + fv + o, z);
      var q0 = iso(cu, cv - fv - o, z + rh), q1 = iso(cu, cv + fv + o, z + rh);
      tiledPlane(bl2, bf, q1, q0, sh(col, 0.14), 4, 9);
      poly([iso(cu - fu, cv + fv, z), iso(cu + fu, cv + fv, z), iso(cu, cv + fv, z + rh)], sh(b.wall, 0.02));
      tiledPlane(rf, rb, q0, q1, sh(col, -0.2), 4, 9);
      line(q0, q1, sh(col, -0.45), 1.4);
      B.vols.push({ t: 'pts', pts: [[cu - fu - o, cv - fv - o, z], [cu + fu + o, cv - fv - o, z], [cu + fu + o, cv + fv + o, z], [cu - fu - o, cv + fv + o, z], [cu, cv - fv - o, z + rh], [cu, cv + fv + o, z + rh]] });
    }
    B.roofTop = z + rh;
  }
  function hip(b, rh, col, o) {
    o = o === undefined ? 0.05 : o;
    var cu = b.cu, cv = b.cv, fu = b.fu + o, fv = b.fv + o, z = b.z0 + b.h;
    eaveShadow(b, b.h);
    var along = fu >= fv, k = Math.min(fu, fv) * 0.9;
    var r0 = along ? iso(cu - fu + k, cv, z + rh) : iso(cu, cv - fv + k, z + rh);
    var r1 = along ? iso(cu + fu - k, cv, z + rh) : iso(cu, cv + fv - k, z + rh);
    var N = iso(cu - fu, cv - fv, z), E = iso(cu + fu, cv - fv, z), S = iso(cu + fu, cv + fv, z), W = iso(cu - fu, cv + fv, z);
    if (along) {
      tiledPlane(N, E, r1, r0, sh(col, 0.14), 4, 8);
      poly([W, N, r0], sh(col, 0.06));
      tiledPlane(W, S, r1, r0, sh(col, -0.03), 4, 8);
      poly([S, E, r1], sh(col, -0.24));
    } else {
      poly([N, E, r0], sh(col, 0.14));
      tiledPlane(N, W, r1, r0, sh(col, 0.06), 4, 8);
      poly([W, S, r1], sh(col, -0.02));
      tiledPlane(E, S, r1, r0, sh(col, -0.24), 4, 8);
    }
    line(r0, r1, sh(col, -0.4), 1.2);
    [[N, r0], [W, along ? r0 : r1], [S, r1], [E, along ? r1 : r0]].forEach(function (p) { line(p[0], p[1], sh(col, -0.3), 0.6); });
    B.vols.push({ t: 'pts', pts: [[cu - fu, cv - fv, z], [cu + fu, cv - fv, z], [cu + fu, cv + fv, z], [cu - fu, cv + fv, z], along ? [cu - fu + k, cv, z + rh] : [cu, cv - fv + k, z + rh], along ? [cu + fu - k, cv, z + rh] : [cu, cv + fv - k, z + rh]] });
    B.roofTop = z + rh;
  }
  function pyramid(b, rh, col, o) {
    o = o === undefined ? 0.05 : o;
    var cu = b.cu, cv = b.cv, fu = b.fu + o, fv = b.fv + o, z = b.z0 + b.h, A = iso(cu, cv, z + rh);
    eaveShadow(b, b.h);
    var N = iso(cu - fu, cv - fv, z), E = iso(cu + fu, cv - fv, z), S = iso(cu + fu, cv + fv, z), W = iso(cu - fu, cv + fv, z);
    poly([N, E, A], sh(col, 0.15)); poly([W, N, A], sh(col, 0.06));
    tiledPlane(W, S, A, A, sh(col, -0.04), 4, 8);
    tiledPlane(S, E, A, A, sh(col, -0.25), 4, 8);
    B.vols.push({ t: 'pts', pts: [[cu - fu, cv - fv, z], [cu + fu, cv - fv, z], [cu + fu, cv + fv, z], [cu - fu, cv + fv, z], [cu, cv, z + rh]] });
    B.roofTop = z + rh;
  }
  // laje com platibanda; devolve a altura do piso da laje
  function flat(b, col, par) {
    var cu = b.cu, cv = b.cv, fu = b.fu, fv = b.fv, z = b.z0 + b.h, p = par === undefined ? 1.6 : par, i = 0.045;
    poly([b.L(-fu, b.h), b.L(fu, b.h), b.L(fu, b.h + p), b.L(-fu, b.h + p)], sh(b.wall, 0.04));
    poly([b.R(fv, b.h), b.R(-fv, b.h), b.R(-fv, b.h + p), b.R(fv, b.h + p)], sh(b.wall, -0.16));
    poly(q(cu - fu, cv - fv, cu + fu, cv + fv, z + p), sh(b.wall, 0.18));
    poly(q(cu - fu + i, cv - fv + i, cu + fu - i, cv + fv - i, z + p * 0.25), col || '#9c9a93');
    poly([iso(cu - fu + i, cv - fv + i, z + p), iso(cu + fu - i, cv - fv + i, z + p), iso(cu + fu - i, cv - fv + i, z + p * 0.25), iso(cu - fu + i, cv - fv + i, z + p * 0.25)], sh(b.wall, -0.1));
    poly([iso(cu - fu + i, cv - fv + i, z + p), iso(cu - fu + i, cv + fv - i, z + p), iso(cu - fu + i, cv + fv - i, z + p * 0.25), iso(cu - fu + i, cv - fv + i, z + p * 0.25)], sh(b.wall, -0.02));
    line(b.L(-fu, b.h + p), b.L(fu, b.h + p), al('#ffffff', 0.35), 0.5);
    B.vols.push({ t: 'box', cu: cu, cv: cv, fu: fu, fv: fv, z0: b.z0, h: b.h + p });
    B.roofTop = z + p;
    return z + p * 0.25;
  }
  // telhado em arco (galpões e estufas), cumeeira ao longo de u
  function arch(b, rh, col, alpha) {
    var cu = b.cu, cv = b.cv, fu = b.fu + 0.03, fv = b.fv + 0.03, z = b.z0 + b.h, N = 7, pts = [], n;
    for (n = 0; n <= N; n++) { var a = Math.PI * n / N; pts.push([cv - Math.cos(a) * fv, z + Math.sin(a) * rh]); }
    g.globalAlpha = alpha || 1;
    for (n = 0; n < N; n++) {
      var v0 = pts[n][0], z0 = pts[n][1], v1 = pts[n + 1][0], z1 = pts[n + 1][1];
      poly([iso(cu - fu, v0, z0), iso(cu + fu, v0, z0), iso(cu + fu, v1, z1), iso(cu - fu, v1, z1)], sh(col, 0.22 - n / N * 0.36));
      line(iso(cu - fu, v1, z1), iso(cu + fu, v1, z1), al('#ffffff', 0.25), 0.4);
    }
    var endPts = pts.map(function (p) { return iso(cu + fu, p[0], p[1]); });
    poly(endPts, sh(col, -0.15));
    g.globalAlpha = 1;
    for (var r = 0; r <= 4; r++) {
      var uu = cu - fu + 2 * fu * r / 4;
      g.beginPath();
      pts.forEach(function (p, m) { var s = iso(uu, p[0], p[1]); if (m) g.lineTo(s[0], s[1]); else g.moveTo(s[0], s[1]); });
      g.strokeStyle = al('#ffffff', 0.7); g.lineWidth = 0.5; g.stroke();
    }
    track(iso(cu, cv, z + rh)[1]);
    B.vols.push({ t: 'pts', pts: [[cu - fu, cv - fv, z], [cu + fu, cv - fv, z], [cu + fu, cv + fv, z], [cu - fu, cv + fv, z], [cu - fu, cv, z + rh], [cu + fu, cv, z + rh]] });
    B.roofTop = z + rh;
  }

  /* ---------------- Acessórios ---------------- */
  function tank(u, v, z, s) {
    s = s || 1;
    var c = iso(u, v, z);
    poly([[c[0] - 5 * s, c[1]], [c[0] + 5 * s, c[1]], [c[0] + 5 * s, c[1] - 5 * s], [c[0] - 5 * s, c[1] - 5 * s]], vgrad(c[1] - 5 * s, c[1], [[0, '#3f8fd6'], [1, '#2266a8']]));
    ell(c[0], c[1], 5 * s, 2.5 * s, '#2266a8');
    ell(c[0], c[1] - 5 * s, 5 * s, 2.5 * s, '#5aa8ea');
    ell(c[0], c[1] - 5.6 * s, 3.4 * s, 1.6 * s, '#7bbcf0');
    line([c[0] - 4 * s, c[1] - 2.5 * s], [c[0] + 4 * s, c[1] - 2.5 * s], al('#ffffff', 0.25), 0.4);
    B.vols.push({ t: 'ell', u: u, v: v, z: z + 3 * s, r: 5 * s });
  }
  function ac(F, a, z) {
    poly([F(a - 0.05, z), F(a + 0.05, z), F(a + 0.05, z + 2.4), F(a - 0.05, z + 2.4)], '#e3e6e6', '#9aa0a0', 0.3);
    var c = F(a, z + 1.2); circ(c[0], c[1], 0.8, '#8c9494');
  }
  function chimney(u, v, z0, h, col) {
    box({ cu: u, cv: v, fu: 0.045, fv: 0.045, z0: z0, h: h, wall: col || '#a35a3e', tex: 'brick', mortar: al('#e6d2c0', 0.4) });
    box({ cu: u, cv: v, fu: 0.06, fv: 0.06, z0: z0 + h, h: 0.9, wall: '#6f6a64', vol: false });
    B.emit.push(iso(u, v, z0 + h + 1.5));
  }
  function antenna(u, v, z, h) {
    var a = iso(u, v, z), b2 = iso(u, v, z + h);
    line(a, b2, '#6a6f73', 0.7);
    line([b2[0] - 3, b2[1] + 2], [b2[0] + 3, b2[1] + 2], '#6a6f73', 0.5);
    line([b2[0] - 2, b2[1] + 4], [b2[0] + 2, b2[1] + 4], '#6a6f73', 0.5);
    circ(b2[0], b2[1], 0.8, '#ff4d4d');
    B.lights.push([b2[0], b2[1], 0.35, '#ff5050']);
    B.vols.push({ t: 'pole', u: u, v: v, h: z + h });
  }
  function dish(u, v, z) {
    var c = iso(u, v, z);
    line(c, [c[0], c[1] - 3], '#777', 0.8);
    ell(c[0] + 1, c[1] - 5, 3.2, 2.4, '#e9eef0', '#9aa');
    circ(c[0] + 2.4, c[1] - 5.4, 0.5, '#666');
  }
  function pad(fu, fv, col, edge) {
    quad(-fu, -fv, fu, fv, 0, col);
    if (edge) poly(q(-fu, -fv, fu, fv, 0), null, edge, 0.5);
  }
  function grassPad(fu, fv) {
    quad(-fu, -fv, fu, fv, 0, '#6db84f');
    var r = U.rng(3);
    for (var n = 0; n < 40; n++) {
      var p = iso((r() - 0.5) * fu * 2, (r() - 0.5) * fv * 2, 0);
      line(p, [p[0] + (r() - 0.5), p[1] - 1.6], r() < 0.5 ? '#4f9a3a' : '#8fd46a', 0.5);
    }
  }
  function fence(u0, v0, u1, v1, col, h, posts) {
    h = h || 3; col = col || '#f2ede2';
    var n = posts || Math.max(2, Math.round(Math.sqrt((u1 - u0) * (u1 - u0) + (v1 - v0) * (v1 - v0)) / 0.1));
    for (var s = 0; s <= n; s++) {
      var t = s / n, u = u0 + (u1 - u0) * t, v = v0 + (v1 - v0) * t;
      line(iso(u, v, 0), iso(u, v, h + 0.6), sh(col, -0.15), 0.8);
    }
    line(iso(u0, v0, h * 0.45), iso(u1, v1, h * 0.45), col, 0.6);
    line(iso(u0, v0, h), iso(u1, v1, h), col, 0.6);
  }
  function shrub(u, v, s, col) {
    col = col || '#3f9442';
    var c = iso(u, v, 0);
    ell(c[0] + 1, c[1] + 0.5, 4 * s, 1.8 * s, 'rgba(0,0,0,0.18)');
    circ(c[0] - 2 * s, c[1] - 2 * s, 2.6 * s, sh(col, -0.15));
    circ(c[0] + 2 * s, c[1] - 2 * s, 2.6 * s, sh(col, -0.08));
    circ(c[0], c[1] - 3.4 * s, 3 * s, col);
    circ(c[0] - 0.8 * s, c[1] - 4.4 * s, 1.4 * s, sh(col, 0.25));
    B.vols.push({ t: 'ell', u: u, v: v, z: 2.5 * s, r: 3.6 * s });
  }
  function pot(u, v, col) {
    var c = iso(u, v, 0);
    poly([[c[0] - 1.6, c[1] - 2.6], [c[0] + 1.6, c[1] - 2.6], [c[0] + 1.1, c[1]], [c[0] - 1.1, c[1]]], '#b5643c');
    circ(c[0], c[1] - 3.8, 2.2, col || '#4da64a');
    circ(c[0] + 0.8, c[1] - 4.6, 0.7, '#ff7aa8');
  }
  function crate(u, v, s, col) {
    box({ cu: u, cv: v, fu: 0.06 * s, fv: 0.06 * s, h: 4 * s, wall: col || '#c49a5c', tex: 'wood' });
  }
  function bench(u, v, along) {
    if (along === 'v') {
      box({ cu: u, cv: v, fu: 0.035, fv: 0.13, z0: 1.4, h: 0.8, wall: '#a8733f', vol: false });
      box({ cu: u - 0.04, cv: v, fu: 0.012, fv: 0.13, z0: 2.2, h: 2.2, wall: '#9a6534', vol: false });
    } else {
      box({ cu: u, cv: v, fu: 0.13, fv: 0.035, z0: 1.4, h: 0.8, wall: '#a8733f', vol: false });
      box({ cu: u, cv: v - 0.04, fu: 0.13, fv: 0.012, z0: 2.2, h: 2.2, wall: '#9a6534', vol: false });
    }
  }
  function lamp(u, v, h) {
    h = h || 20;
    var b0 = iso(u, v, 0), top = iso(u, v, h);
    ell(b0[0], b0[1], 2, 1, '#3a3f44');
    line(b0, top, '#2f3438', 1.3);
    line([b0[0] - 0.4, b0[1]], [top[0] - 0.4, top[1]], al('#ffffff', 0.18), 0.4);
    var glass = [[top[0] - 2.2, top[1] - 0.5], [top[0] + 2.2, top[1] - 0.5], [top[0] + 1.6, top[1] - 4.5], [top[0] - 1.6, top[1] - 4.5]];
    poly(glass, '#ffe7a6', '#2f3438', 0.6);
    poly([[top[0] - 2.6, top[1] - 4.5], [top[0] + 2.6, top[1] - 4.5], [top[0], top[1] - 6.6]], '#2f3438');
    B.wins.push(glass);
    B.lights.push([top[0], top[1] - 2.5, 1.6]);
    B.vols.push({ t: 'pole', u: u, v: v, h: h });
  }

  /* ---------------- Vegetação ---------------- */
  var GREENS = [['#2f7f35', '#3f9a43', '#5cb84f', '#8fd870'], ['#2a7346', '#368f55', '#4fae6a', '#80d39a'],
    ['#4b8a2a', '#5fa335', '#7fbf45', '#addf70'], ['#246b45', '#2f8556', '#47a36f', '#7cc99a']];
  function broadleaf(u, v, s, variant, sway, fruit) {
    var c = iso(u, v, 0), gr = GREENS[variant % 4], sx = (sway || 0) * 1.1 * s, n;
    var r = U.rng(variant * 31 + 7);
    ell(c[0], c[1] + 0.5, 3 * s, 1.2 * s, 'rgba(0,0,0,0.2)');
    poly([[c[0] - 1.3 * s, c[1]], [c[0] + 1.3 * s, c[1]], [c[0] + 0.9 * s + sx * 0.3, c[1] - 11 * s], [c[0] - 0.9 * s + sx * 0.3, c[1] - 11 * s]], vgrad(c[1] - 11 * s, c[1], [[0, '#6b4a2e'], [1, '#86603d']]));
    line([c[0] + sx * 0.2, c[1] - 7 * s], [c[0] + 3.5 * s + sx * 0.4, c[1] - 11 * s], '#6b4a2e', 0.9 * s);
    var cx = c[0] + sx, cy = c[1] - 16 * s, blobs = [];
    for (n = 0; n < 9; n++) {
      var a = r() * Math.PI * 2, d = r() * 5.5 * s;
      blobs.push([cx + Math.cos(a) * d * 1.15, cy + Math.sin(a) * d * 0.8, (3.6 + r() * 2.2) * s]);
    }
    blobs.sort(function (p, p2) { return p[1] - p2[1]; });
    blobs.forEach(function (bb) { circ(bb[0] + 0.6 * s, bb[1] + 1.2 * s, bb[2], gr[0]); });
    blobs.forEach(function (bb) { circ(bb[0], bb[1], bb[2] * 0.92, gr[1]); });
    blobs.forEach(function (bb) { circ(bb[0] - bb[2] * 0.25, bb[1] - bb[2] * 0.28, bb[2] * 0.55, gr[2]); });
    blobs.forEach(function (bb, m) { if (m % 2) circ(bb[0] - bb[2] * 0.4, bb[1] - bb[2] * 0.45, bb[2] * 0.22, gr[3]); });
    if (fruit) for (n = 0; n < 7; n++) circ(cx + (r() - 0.5) * 11 * s, cy + (r() - 0.3) * 7 * s, 0.9 * s, fruit);
    B.vols.push({ t: 'ell', u: u, v: v, z: 15 * s, r: 7.5 * s });
    B.vols.push({ t: 'pole', u: u, v: v, h: 10 * s, w: 1.2 * s });
  }
  // araucária (pinheiro-do-paraná): tronco alto e copa em "candelabro"
  function araucaria(u, v, s, variant, sway) {
    var c = iso(u, v, 0), sx = (sway || 0) * 1.2 * s, H = (26 + (variant % 3) * 3) * s;
    ell(c[0], c[1] + 0.5, 2.6 * s, 1 * s, 'rgba(0,0,0,0.2)');
    poly([[c[0] - 1 * s, c[1]], [c[0] + 1 * s, c[1]], [c[0] + 0.6 * s + sx * 0.5, c[1] - H], [c[0] - 0.6 * s + sx * 0.5, c[1] - H]], vgrad(c[1] - H, c[1], [[0, '#5a3f2a'], [1, '#7a5636']]));
    var tiers = [[H - 1 * s, 9.5 * s], [H + 2.5 * s, 7.5 * s], [H + 5.5 * s, 5 * s]];
    tiers.forEach(function (t, n) {
      var y = c[1] - t[0], w = t[1], x = c[0] + sx * (0.6 + n * 0.2);
      line([x, y + 2 * s], [x - w * 0.8, y - 0.5 * s], '#4a3424', 0.6 * s);
      line([x, y + 2 * s], [x + w * 0.8, y - 0.5 * s], '#4a3424', 0.6 * s);
      ell(x, y + 0.8 * s, w, 2.2 * s, '#1f5a34');
      ell(x, y - 0.2 * s, w * 0.92, 1.8 * s, '#2b7342');
      ell(x - w * 0.15, y - 0.8 * s, w * 0.6, 1.1 * s, '#3f8f55');
      for (var m = -3; m <= 3; m++) circ(x + m * w * 0.28, y + 1.2 * s, 0.9 * s, '#235f38');
    });
    B.vols.push({ t: 'ell', u: u, v: v, z: H + 2 * s, r: 8 * s });
    B.vols.push({ t: 'pole', u: u, v: v, h: H, w: 1 * s });
  }
  function coqueiro(u, v, s, variant, sway) {
    var c = iso(u, v, 0), sx = (sway || 0) * 1.4 * s, H = (22 + (variant % 2) * 4) * s, lean = (variant % 2 ? -1 : 1) * 4 * s, n;
    ell(c[0], c[1] + 0.5, 2.5 * s, 1 * s, 'rgba(0,0,0,0.2)');
    var tx = c[0] + lean + sx, ty = c[1] - H, mxT = c[0] + lean * 0.1, myT = c[1] - H * 0.6;
    g.lineCap = 'round';
    g.strokeStyle = '#8a6a42'; g.lineWidth = 2.2 * s;
    g.beginPath(); g.moveTo(c[0], c[1]); g.quadraticCurveTo(mxT, myT, tx, ty); g.stroke(); track(ty);
    for (n = 1; n < 9; n++) {
      var t = n / 9, px = (1 - t) * (1 - t) * c[0] + 2 * (1 - t) * t * mxT + t * t * tx, py = (1 - t) * (1 - t) * c[1] + 2 * (1 - t) * t * myT + t * t * ty;
      line([px - 1.1 * s, py], [px + 1.1 * s, py], '#6b5233', 0.4 * s);
    }
    var fr = ['#2f8f3a', '#3fa548', '#2a7a33'];
    for (n = 0; n < 8; n++) {
      var a = n / 8 * Math.PI * 2 + 0.3, ex = tx + Math.cos(a) * 11 * s, ey = ty + Math.sin(a) * 4 * s + 4 * s;
      var mx = tx + Math.cos(a) * 6 * s, my = ty - 3 * s + Math.sin(a) * 2 * s;
      g.strokeStyle = fr[n % 3]; g.lineWidth = 1.6 * s;
      g.beginPath(); g.moveTo(tx, ty); g.quadraticCurveTo(mx, my, ex, ey); g.stroke(); track(my);
      for (var m = 1; m < 5; m++) {
        var t2 = m / 5, lx = (1 - t2) * (1 - t2) * tx + 2 * (1 - t2) * t2 * mx + t2 * t2 * ex, ly = (1 - t2) * (1 - t2) * ty + 2 * (1 - t2) * t2 * my + t2 * t2 * ey;
        line([lx, ly], [lx + Math.cos(a + 1.2) * 2.4 * s, ly + 2 * s], fr[(n + 1) % 3], 0.6 * s);
      }
    }
    circ(tx - 1 * s, ty + 1 * s, 1.4 * s, '#6b4a2e'); circ(tx + 1.2 * s, ty + 1.3 * s, 1.4 * s, '#7a5634');
    B.vols.push({ t: 'ell', u: u + lean / 64, v: v, z: H, r: 8 * s });
    B.vols.push({ t: 'pole', u: u, v: v, h: H, w: 1.1 * s });
  }
  function ipe(u, v, s, variant, sway) {
    var c = iso(u, v, 0), sx = (sway || 0) * 1.1 * s, n;
    var cols = [['#f2b705', '#ffd84a', '#ffe98f'], ['#d1478f', '#ef6fb0', '#ffa3d0'], ['#8e5bd6', '#ae82ee', '#d3b9ff'], ['#ecece4', '#ffffff', '#fff7d6']][variant % 4];
    var r = U.rng(variant * 13 + 5);
    ell(c[0], c[1] + 0.5, 3 * s, 1.2 * s, 'rgba(0,0,0,0.2)');
    g.lineCap = 'round';
    g.strokeStyle = '#5e4330'; g.lineWidth = 1.8 * s;
    g.beginPath(); g.moveTo(c[0], c[1]); g.quadraticCurveTo(c[0] - 2 * s, c[1] - 7 * s, c[0] + sx * 0.4, c[1] - 12 * s); g.stroke();
    g.lineWidth = 0.9 * s;
    g.beginPath(); g.moveTo(c[0] - 0.5 * s, c[1] - 7 * s); g.lineTo(c[0] - 5 * s + sx * 0.3, c[1] - 13 * s); g.moveTo(c[0] + 0.3 * s, c[1] - 9 * s); g.lineTo(c[0] + 5 * s + sx * 0.4, c[1] - 14 * s); g.stroke();
    var cx = c[0] + sx, cy = c[1] - 17 * s;
    for (n = 0; n < 36; n++) {
      var a = r() * Math.PI * 2, d = Math.sqrt(r()) * 7 * s;
      circ(cx + Math.cos(a) * d * 1.2, cy + Math.sin(a) * d * 0.75, (1.6 + r() * 1.4) * s, cols[n % 3]);
    }
    for (n = 0; n < 6; n++) circ(cx + (r() - 0.5) * 12 * s, cy + (r() - 0.5) * 8 * s, 1.1 * s, '#4f8f3a');
    B.vols.push({ t: 'ell', u: u, v: v, z: 16 * s, r: 8 * s });
    B.vols.push({ t: 'pole', u: u, v: v, h: 11 * s, w: 1.1 * s });
  }
  function rock(u, v, s, variant) {
    var c = iso(u, v, 0), r = U.rng(variant * 7 + 3), pts = [], N = 7;
    for (var n = 0; n < N; n++) { var a = n / N * Math.PI * 2; pts.push([c[0] + Math.cos(a) * (7 + r() * 3) * s, c[1] + Math.sin(a) * (3.4 + r() * 1.4) * s - 2 * s]); }
    ell(c[0] + 1.5 * s, c[1] + 0.5 * s, 8 * s, 3 * s, 'rgba(0,0,0,0.2)');
    var top = pts.map(function (p) { return [p[0] * 0.85 + c[0] * 0.15, p[1] - 4.5 * s]; });
    poly(pts, '#7c8285');
    poly(top, '#a3a9ab');
    poly([top[0], top[1], top[2], [c[0], c[1] - 6 * s]], '#b9bfc0');
    if (variant % 2) ell(top[4][0], top[4][1] + 0.5, 3 * s, 1.2 * s, 'rgba(90,150,60,0.75)');
    B.vols.push({ t: 'ell', u: u, v: v, z: 3 * s, r: 7 * s });
  }

  /* ---------------- Pintores de cada objeto ---------------- */
  var WALLS = ['#f6dcb0', '#f2c7a2', '#eef1f2', '#cfe8d5', '#f6cfcf', '#d6e2f5', '#fff0bd', '#f1d3e9', '#e5f0c4', '#ffd9b3'];
  var ROOFS = ['#c45a3b', '#b2472f', '#d06a43', '#a5502f', '#8a4a33', '#c2603d'];

  function houseP(lv, variant) {
    var style = variant % 4, wall = WALLS[variant % WALLS.length], roof = ROOFS[(variant >> 1) % ROOFS.length];
    var fu = 0.28 + (lv === 3 ? 0.06 : 0), fv = 0.26 + (lv === 3 ? 0.04 : 0), floors = lv === 1 ? 1 : 2, fh = 11;
    var h = floors * fh + 1;
    grassPad(0.44, 0.44);
    quad(fu - 0.02, -0.07, 0.46, 0.07, 0, '#cbbfa8');
    shrub(-0.34, 0.36, 0.55, '#3f9442');
    if (variant % 3 === 0) pot(0.38, 0.22, '#4da64a');
    var b = box({ fu: fu, fv: fv, h: h, wall: style === 3 ? '#b8613f' : wall, tex: style === 3 ? 'brick' : 'plaster', mortar: al('#f0dccb', 0.45) });
    for (var f = 0; f < floors; f++) {
      var z0 = f * fh + 4, z1 = z0 + 5;
      win(b.L, -fu * 0.62, -fu * 0.12, z0, z1, { shutters: style === 0 ? sh(roof, -0.1) : null });
      win(b.L, fu * 0.22, fu * 0.7, z0, z1, { shutters: style === 0 ? sh(roof, -0.1) : null });
      if (f > 0) win(b.R, fv * 0.55, fv * 0.05, z0, z1, {});
      win(b.R, -fv * 0.25, -fv * 0.7, z0, z1, {});
    }
    door(b.R, fv * 0.62, fv * 0.15, 7.5, ['#7a4f2e', '#2f6f8f', '#5f7a3a', '#8f3f3f'][variant % 4]);
    box({ cu: fu + 0.035, cv: fv * 0.38, fu: 0.035, fv: 0.13, h: 0.9, wall: '#c9c2b5', vol: false });
    if (style === 0) { gable(b, 'u', 10, roof); if (variant % 5 === 0) chimney(-fu * 0.45, -0.06, h + 4, 5); }
    else if (style === 1) { var zt = flat(b, '#a7a49c'); tank(-fu * 0.35, -fv * 0.3, zt, 0.9); ac(b.L, fu * 0.7, h - 3.5); }
    else if (style === 2) {
      hip(b, 9, roof);
      var pz = 7.5;
      poly([iso(-fu, fv, pz), iso(fu, fv, pz), iso(fu, fv + 0.16, pz - 1.6), iso(-fu, fv + 0.16, pz - 1.6)], sh(roof, -0.05));
      [-fu + 0.03, 0, fu - 0.03].forEach(function (uu) { line(iso(uu, fv + 0.14, 0), iso(uu, fv + 0.14, pz - 1.6), '#f4efe6', 1); });
    } else { var zt2 = flat(b, '#9c9890'); tank(fu * 0.2, -fv * 0.35, zt2, 0.9); }
    if (lv === 3 && style !== 2) {
      var bz = fh + 3.2;
      poly([b.L(-fu * 0.7, bz), b.L(fu * 0.1, bz), iso(fu * 0.1, fv + 0.12, bz), iso(-fu * 0.7, fv + 0.12, bz)], '#d8d2c6');
      for (var a = -fu * 0.7; a <= fu * 0.1 + 0.001; a += 0.05) line(iso(a, fv + 0.12, bz), iso(a, fv + 0.12, bz + 3), '#4a4a4a', 0.4);
      line(iso(-fu * 0.7, fv + 0.12, bz + 3), iso(fu * 0.1, fv + 0.12, bz + 3), '#4a4a4a', 0.6);
    }
    B.lights.push(iso(0.1, 0.1, 6).concat([0.75]));
  }

  function sobradoP(lv, variant) {
    var wall = WALLS[(variant + 3) % WALLS.length], roof = ROOFS[variant % ROOFS.length];
    var fu = 0.38, fv = 0.32, floors = 1 + lv, fh = 10.5, h = floors * fh + 1;
    pad(0.46, 0.46, '#d7cdbb');
    shrub(-0.38, 0.38, 0.55);
    shrub(0.4, -0.36, 0.5, '#4a9f3f');
    var b = box({ fu: fu, fv: fv, h: h, wall: wall, tex: 'plaster' });
    for (var f = 0; f < floors; f++) {
      var z0 = f * fh + 3.8, z1 = z0 + 5.2;
      for (var n = 0; n < 3; n++) { var a0 = -fu + 0.06 + n * 0.25; win(b.L, a0, a0 + 0.13, z0, z1, { shutters: variant % 2 ? '#3f7f5f' : null }); }
      win(b.R, -fv * 0.2, -fv * 0.75, z0, z1, {});
      if (f > 0) win(b.R, fv * 0.75, fv * 0.25, z0, z1, {});
      if (f > 0) {
        var bz = f * fh + 1.4;
        poly([b.L(-fu, bz), b.L(fu, bz), iso(fu, fv + 0.1, bz), iso(-fu, fv + 0.1, bz)], '#e2dccf');
        for (var a = -fu; a <= fu + 0.001; a += 0.045) line(iso(a, fv + 0.1, bz), iso(a, fv + 0.1, bz + 2.8), '#3c3c3c', 0.35);
        line(iso(-fu, fv + 0.1, bz + 2.8), iso(fu, fv + 0.1, bz + 2.8), '#3c3c3c', 0.6);
      }
    }
    door(b.R, fv * 0.7, fv * 0.25, 7.5, '#6b4a2e');
    if (variant % 2) gable(b, 'v', 10, roof); else hip(b, 9, roof);
    B.lights.push(iso(0.1, 0.1, 8).concat([1]));
  }

  function hqP(lv) {
    var fu = 0.38, fv = 0.34, h = 18 + 7 * (lv - 1), wall = '#f4eee2';
    pad(0.48, 0.48, '#d9d1c1', al('#000000', 0.15));
    [[-0.4, 0.4], [0.42, -0.38]].forEach(function (p) { quad(p[0] - 0.06, p[1] - 0.06, p[0] + 0.06, p[1] + 0.06, 0, '#7a5434'); var c = iso(p[0], p[1], 0); circ(c[0], c[1] - 1.5, 2.2, '#ff6f91'); });
    var b = box({ cu: -0.04, fu: fu, fv: fv, h: h, wall: wall, tex: 'stone' });
    var floors = Math.floor(h / 9);
    for (var f = 0; f < floors; f++) {
      var z0 = 3.5 + f * 8.5;
      for (var n = 0; n < 3; n++) { var a0 = -fu + 0.07 + n * 0.25; win(b.L, a0, a0 + 0.13, z0, z0 + 5.5, { frame: '#ffffff' }); }
    }
    var pu = b.cu + fu, ph = Math.min(h - 1, 15);
    box({ cu: pu + 0.08, cv: 0, fu: 0.08, fv: 0.24, h: 1.4, wall: '#cfc7b8', vol: false });
    box({ cu: pu + 0.13, cv: 0, fu: 0.03, fv: 0.28, h: 0.8, wall: '#c2b9a8', vol: false });
    door(b.R, 0.12, -0.12, 9, '#6b4a2e', {});
    poly([iso(pu, -0.26, ph), iso(pu + 0.14, -0.26, ph), iso(pu + 0.14, 0.26, ph), iso(pu, 0.26, ph)], '#ece5d8');
    [-0.2, -0.07, 0.07, 0.2].forEach(function (vv) {
      var bb = iso(pu + 0.12, vv, 1.4), tt = iso(pu + 0.12, vv, ph);
      poly([[bb[0] - 1.1, bb[1]], [bb[0] + 1.1, bb[1]], [tt[0] + 1.1, tt[1]], [tt[0] - 1.1, tt[1]]], vgrad(tt[1], bb[1], [[0, '#ffffff'], [1, '#d8d0c2']]));
      line([bb[0] - 0.3, bb[1]], [tt[0] - 0.3, tt[1]], al('#000000', 0.12), 0.4);
    });
    var p0 = iso(pu + 0.14, 0.27, ph), p1 = iso(pu + 0.14, -0.27, ph), pt = iso(pu + 0.14, 0, ph + 7);
    poly([p0, p1, pt], sh(brand, -0.05), '#ffffff', 0.8);
    var cc = iso(pu + 0.14, 0, ph + 2.6); circ(cc[0], cc[1], 2, '#ffffff'); circ(cc[0], cc[1], 1.4, sh(brand, 0.3));
    line(cc, [cc[0], cc[1] - 1], '#333', 0.3); line(cc, [cc[0] + 0.8, cc[1]], '#333', 0.3);
    hip(b, 12, brand);
    var fb = iso(-0.04, 0, B.roofTop - 1), ft = iso(-0.04, 0, B.roofTop + 16);
    line(fb, ft, '#555b60', 0.9);
    circ(ft[0], ft[1], 0.8, '#e8c75a');
    B.anim = { type: 'flag', x: ft[0], y: ft[1] + 1, color: brand };
    B.vols.push({ t: 'pole', u: -0.04, v: 0, h: B.roofTop + 16 });
    B.lights.push(iso(0.3, 0, 6).concat([1.3]));
  }

  function civicP(id, lv) {
    var spec = {
      creche: { fu: 0.36, fv: 0.34, fh: 10, floors: 1, wall: '#ffe7a3', roof: 'gable', rc: '#f07d52', tex: 'plaster', stripe: true },
      escola: { fu: 0.42, fv: 0.32, fh: 9, floors: 2, wall: '#f6ecd2', roof: 'flat', tex: 'plaster', band: '#5b7bd5' },
      saude: { fu: 0.38, fv: 0.34, fh: 9.5, floors: 2, wall: '#fbfbf8', roof: 'flat', tex: 'plaster', band: '#3daa6f' },
      banco: { fu: 0.36, fv: 0.34, fh: 11, floors: 2, wall: '#eee5d0', roof: 'hip', rc: '#3d8f6e', tex: 'stone' }
    }[id];
    var floors = spec.floors + (lv - 1), h = floors * spec.fh + 1, f, n, s;
    pad(0.47, 0.47, '#d4ccbb', al('#000000', 0.12));
    var b = box({ fu: spec.fu, fv: spec.fv, h: h, wall: spec.wall, tex: spec.tex });
    if (spec.band) {
      for (f = 0; f < floors; f++) {
        var zb = f * spec.fh + 1.2;
        poly([b.L(-spec.fu, zb), b.L(spec.fu, zb), b.L(spec.fu, zb + 1.1), b.L(-spec.fu, zb + 1.1)], spec.band);
        poly([b.R(spec.fv, zb), b.R(-spec.fv, zb), b.R(-spec.fv, zb + 1.1), b.R(spec.fv, zb + 1.1)], sh(spec.band, -0.2));
      }
    }
    if (spec.stripe) {
      var cols = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6'];
      for (s = 0; s < 6; s++) {
        var sa0 = -spec.fu + 2 * spec.fu * s / 6, sa1 = sa0 + 2 * spec.fu / 6;
        poly([b.L(sa0, 1.2), b.L(sa1, 1.2), b.L(sa1, 2.6), b.L(sa0, 2.6)], cols[s]);
      }
    }
    var per = id === 'escola' ? 4 : 3;
    for (f = 0; f < floors; f++) {
      var z0 = f * spec.fh + 3.6, z1 = z0 + (id === 'banco' ? 6 : 5);
      for (n = 0; n < per; n++) {
        var span = 2 * spec.fu / per, a = -spec.fu + span * n + span * 0.22;
        if (id === 'creche') {
          var cp = b.L(a + span * 0.28, (z0 + z1) / 2);
          circ(cp[0], cp[1], 2.4, '#ffffff'); circ(cp[0], cp[1], 1.8, '#7fb8e0');
          B.wins.push([[cp[0] - 1.4, cp[1] - 1.4], [cp[0] + 1.4, cp[1] - 1.4], [cp[0] + 1.4, cp[1] + 1.4], [cp[0] - 1.4, cp[1] + 1.4]]);
        } else win(b.L, a, a + span * 0.56, z0, z1, { frame: id === 'banco' ? '#f2ead8' : '#ffffff' });
      }
      if (f > 0 || id !== 'banco') win(b.R, -spec.fv * 0.25, -spec.fv * 0.75, z0, z1, {});
    }
    if (id === 'banco') {
      var pu = spec.fu, ph = Math.min(h, 16);
      box({ cu: pu + 0.06, cv: 0.05, fu: 0.06, fv: 0.22, h: 1.2, wall: '#d0c7b5', vol: false });
      door(b.R, 0.15, -0.05, 9, '#4a3a2a', {});
      [-0.12, 0.02, 0.16].forEach(function (vv) { var bb = iso(pu + 0.1, vv + 0.05, 1.2), tt = iso(pu + 0.1, vv + 0.05, ph); poly([[bb[0] - 1, bb[1]], [bb[0] + 1, bb[1]], [tt[0] + 1, tt[1]], [tt[0] - 1, tt[1]]], '#f7f2e8'); });
      poly([iso(pu + 0.12, 0.29, ph), iso(pu + 0.12, -0.19, ph), iso(pu + 0.12, 0.05, ph + 5)], '#efe8da', '#b9ae98', 0.5);
    } else door(b.R, spec.fv * 0.75, spec.fv * 0.2, 8, id === 'saude' ? '#dfe9f0' : '#6b4a2e', { glass: id === 'saude' });
    if (id === 'saude') {
      var cx = b.R(-spec.fv * 0.05, h - 3.5);
      poly([[cx[0] - 3.2, cx[1] - 1.1], [cx[0] + 3.2, cx[1] + 0.5], [cx[0] + 3.2, cx[1] + 2.7], [cx[0] - 3.2, cx[1] + 1.1]], '#e23b3b');
      poly([[cx[0] - 1, cx[1] - 2.6], [cx[0] + 1, cx[1] - 2.1], [cx[0] + 1, cx[1] + 4.2], [cx[0] - 1, cx[1] + 3.7]], '#e23b3b');
    }
    if (id === 'creche') {
      gable(b, 'u', 10, spec.rc);
      fence(-0.46, 0.46, 0.2, 0.46, '#ffd24a', 2.6);
      var bl = iso(-0.2, 0.4, 0); circ(bl[0], bl[1] - 1.5, 1.5, '#e74c3c'); circ(bl[0] - 0.4, bl[1] - 1.9, 0.5, '#ffffff');
    } else if (spec.roof === 'flat') {
      var zt = flat(b, '#a4a29a');
      if (id === 'escola') {
        var tb = box({ cu: spec.fu * 0.5, cv: 0, fu: 0.09, fv: 0.09, z0: zt, h: 7, wall: spec.wall });
        pyramid(tb, 5, '#c45a3b', 0.03);
        var ck = iso(spec.fu * 0.5 + 0.09, 0, zt + 4.5); circ(ck[0], ck[1], 1.6, '#ffffff', '#333', 0.3);
        line(ck, [ck[0], ck[1] - 1.1], '#333', 0.3);
        var fb = iso(-spec.fu * 0.6, 0, zt), ft = iso(-spec.fu * 0.6, 0, zt + 14);
        line(fb, ft, '#666', 0.7);
        B.anim = { type: 'flag', x: ft[0], y: ft[1] + 1, color: '#2e9e4f', small: true };
        B.vols.push({ t: 'pole', u: -spec.fu * 0.6, v: 0, h: zt + 14 });
      } else ac(b.L, spec.fu * 0.6, h - 4);
      if (id === 'saude') tank(-spec.fu * 0.4, -spec.fv * 0.3, zt, 1);
    } else hip(b, 10, spec.rc);
    B.lights.push(iso(0.1, 0.1, 7).concat([1.1]));
  }

  function shopP(id, lv) {
    var S = {
      padaria: { wall: '#f8dcae', roof: 'gable', axis: 'u', tex: 'plaster', awn: true, chim: true, icon: '🍞', disp: ['#d99a4e', '#c27a35', '#f0c27a'] },
      cozinha: { wall: '#fff3db', roof: 'gable', axis: 'v', tex: 'plaster', chim: true, steel: true, icon: '🍲', tables: true },
      doceria: { wall: '#ffd6e2', roof: 'gable', axis: 'u', tex: 'plaster', awn: true, icon: '🍓', disp: ['#e23b5a', '#ff8fb0', '#a8325a'] },
      artesanato: { wall: '#e3b98f', roof: 'gable', axis: 'v', tex: 'plaster', rustic: true, icon: '🏺', pots: true },
      costura: { wall: '#e9e0f6', roof: 'flat', tex: 'plaster', floors2: true, icon: '🧵', fabric: true },
      loja: { wall: '#fff4e0', roof: 'flat', tex: 'plaster', awn: true, icon: '🏪', disp: ['#3498db', '#e67e22', '#2ecc71', '#9b59b6'], big: true },
      entrega: { wall: '#ffe9a8', roof: 'flat', tex: 'plaster', garage: true, icon: '🛵', bikes: true }
    }[id];
    var fu = 0.36, fv = 0.33, floors = (S.floors2 ? 2 : 1) + (lv - 1), fh = 10, h = floors * fh + 1, f, n;
    pad(0.47, 0.47, '#d8cfbe', al('#000000', 0.12));
    var b = box({ fu: fu, fv: fv, h: h, wall: S.wall, tex: S.tex });
    if (S.rustic) {
      for (var a = -fu + 0.06; a < fu; a += 0.17) line(b.L(a, 0), b.L(a, h), '#7a5434', 1.1);
      line(b.L(-fu, h - 1), b.L(fu, h - 1), '#7a5434', 1.2);
    }
    if (S.disp || S.fabric) {
      var w0 = -fu * 0.85, w1 = fu * (S.big ? 0.85 : 0.45);
      win(b.L, w0, w1, 2.2, 7.2, { frame: '#ffffff', cross: false, glass: '#cfe6f3' });
      var cols = S.disp || ['#e74c3c', '#3498db', '#f1c40f', '#9b59b6', '#2ecc71'];
      for (n = 0; n < 7; n++) {
        var t = (n + 0.5) / 7, p = b.L(w0 + (w1 - w0) * t, 3.4);
        if (S.fabric) poly([[p[0] - 1, p[1]], [p[0] + 1, p[1] + 0.5], [p[0] + 1, p[1] - 3.2], [p[0] - 1, p[1] - 3.7]], cols[n % cols.length]);
        else ell(p[0], p[1], 1.4, 0.9, cols[n % cols.length]);
      }
      if (!S.big) win(b.L, fu * 0.58, fu * 0.88, 3, 7, {});
    } else {
      win(b.L, -fu * 0.7, -fu * 0.2, 3, 7.5, {});
      win(b.L, fu * 0.15, fu * 0.65, 3, 7.5, {});
    }
    for (f = 1; f < floors; f++) for (var m = 0; m < 3; m++) { var a2 = -fu + 0.06 + m * 0.25; win(b.L, a2, a2 + 0.13, f * fh + 3.4, f * fh + 8.4, {}); }
    if (S.garage) {
      door(b.R, fv * 0.85, fv * 0.15, 7.5, '#b9bdc0', { roll: true });
      door(b.R, -fv * 0.1, -fv * 0.8, 7.5, '#b9bdc0', { roll: true });
    } else {
      door(b.R, fv * 0.7, fv * 0.2, 7.5, S.steel ? '#9aa3a8' : '#6b4a2e', { glass: !S.steel });
      win(b.R, -fv * 0.2, -fv * 0.75, 3, 7.5, {});
    }
    for (f = 1; f < floors; f++) win(b.R, fv * 0.6, -fv * 0.6, f * fh + 3.4, f * fh + 8.4, {});
    if (S.awn) awning(b.L, -fu * 0.9, S.big ? fu * 0.9 : fu * 0.5, 9.2, 0.14, brand, '#ffffff', function (a3, z, d) { return iso(a3, fv + d, z); });
    sign(b.L, -fu * 0.55, fu * 0.25, h - 3.6, h - 0.8, '#ffffff', S.icon);
    if (S.roof === 'gable') gable(b, S.axis, 9, brand);
    else { var zt = flat(b, '#a6a39b'); if (id === 'loja') ac(b.R, -fv * 0.6, h - 4); if (id === 'costura') tank(-fu * 0.3, -fv * 0.3, zt, 0.85); }
    if (S.chim) {
      if (S.steel) {
        var cb = iso(-fu * 0.4, -fv * 0.4, B.roofTop - 4), ctop = iso(-fu * 0.4, -fv * 0.4, B.roofTop + 6);
        poly([[cb[0] - 1.6, cb[1]], [cb[0] + 1.6, cb[1]], [ctop[0] + 1.6, ctop[1]], [ctop[0] - 1.6, ctop[1]]], vgrad(ctop[1], cb[1], [[0, '#d7dde0'], [1, '#8f989d']]));
        ell(ctop[0], ctop[1], 2.2, 1, '#6f777b');
        B.emit.push([ctop[0], ctop[1] - 1]);
      } else chimney(-fu * 0.45, -fv * 0.35, B.roofTop - 6, 7);
    }
    if (S.tables) {
      [[0.42, -0.25], [0.42, 0.2]].forEach(function (p2) {
        var c = iso(p2[0], p2[1], 0);
        line(c, [c[0], c[1] - 6], '#777', 0.6);
        poly([[c[0] - 5, c[1] - 6], [c[0], c[1] - 9], [c[0] + 5, c[1] - 6], [c[0], c[1] - 4]], brand);
        ell(c[0], c[1] - 2.4, 2.6, 1.2, '#f2ede2');
      });
    }
    if (S.pots) {
      [[0.42, -0.3], [0.44, -0.12], [0.41, 0.08]].forEach(function (p2, k) {
        var c = iso(p2[0], p2[1], 0), hh = 4 + k;
        g.fillStyle = ['#b5643c', '#c9884d', '#9f4e2e'][k];
        g.beginPath(); g.moveTo(c[0] - 1.2, c[1]); g.quadraticCurveTo(c[0] - 3, c[1] - hh * 0.6, c[0] - 1, c[1] - hh); g.lineTo(c[0] + 1, c[1] - hh); g.quadraticCurveTo(c[0] + 3, c[1] - hh * 0.6, c[0] + 1.2, c[1]); g.closePath(); g.fill(); track(c[1] - hh);
        line([c[0] - 2, c[1] - hh * 0.5], [c[0] + 2, c[1] - hh * 0.5], al('#ffffff', 0.4), 0.4);
      });
    }
    if (S.bikes) {
      [[0.43, -0.2], [0.44, 0.15]].forEach(function (p2) {
        var c = iso(p2[0], p2[1], 0);
        circ(c[0] - 2.5, c[1] - 1.5, 1.4, null, '#222', 0.6); circ(c[0] + 2.5, c[1] - 0.2, 1.4, null, '#222', 0.6);
        line([c[0] - 2.5, c[1] - 1.5], [c[0] + 2.5, c[1] - 0.2], '#c0392b', 0.8);
        box({ cu: p2[0] - 0.02, cv: p2[1] - 0.02, fu: 0.045, fv: 0.045, z0: 3, h: 3.5, wall: brand, vol: false });
      });
    }
    B.lights.push(iso(0.2, 0.15, 5).concat([1]));
  }

  function industrialP(id, lv) {
    var S = {
      triagem: { wall: '#c9d4c4', tex: 'metal', roofC: brand, bales: true },
      armazem: { wall: '#d6bf98', tex: 'woodv', roofC: '#8a6d4c', crates: true },
      marcenaria: { wall: '#c89b6d', tex: 'wood', roofC: brand, logs: true }
    }[id];
    var fu = 0.42, fv = 0.3, h = 14 + 4 * (lv - 1), n;
    pad(0.48, 0.48, '#cfc6b4', al('#000000', 0.12));
    var b = box({ cu: -0.02, cv: -0.05, fu: fu, fv: fv, h: h, wall: S.wall, tex: S.tex });
    door(b.R, fv * 0.7, -fv * 0.6, h * 0.7, S.tex === 'metal' ? '#a9b3b0' : '#8a6438', { roll: S.tex === 'metal' });
    for (n = 0; n < 4; n++) { var a = -fu + 0.08 + n * 0.21; win(b.L, a, a + 0.1, h - 5.5, h - 2.5, { cross: false }); }
    if (S.tex === 'metal') arch(b, 6, S.roofC); else gable(b, 'u', 8, S.roofC);
    if (S.bales) {
      var cols = ['#4e7fbf', '#5aa04a', '#a77b4c', '#d3cfc3', '#c9584a'];
      [[0.06, 0.4], [0.2, 0.4], [0.34, 0.4], [0.13, 0.4, 4], [0.27, 0.4, 4]].forEach(function (p, m) {
        box({ cu: p[0], cv: p[1], fu: 0.06, fv: 0.05, z0: p[2] || 0, h: 4, wall: cols[m % cols.length], vol: m < 3 });
      });
    }
    if (S.crates) { crate(0.1, 0.4, 1.1); crate(0.25, 0.41, 1); crate(0.17, 0.4, 0.9); box({ cu: 0.36, cv: 0.4, fu: 0.07, fv: 0.06, h: 0.8, wall: '#b08a55', vol: false }); }
    if (S.logs) {
      for (var r = 0; r < 3; r++) for (var c = 0; c < 4 - r; c++) {
        var p = iso(0.05 + c * 0.09 + r * 0.045, 0.42, 1.5 + r * 2.6);
        circ(p[0], p[1], 1.5, '#9b6b3e'); circ(p[0], p[1], 1, '#d9b07a'); circ(p[0], p[1], 0.4, '#b88a55');
      }
      B.vols.push({ t: 'box', cu: 0.18, cv: 0.42, fu: 0.18, fv: 0.05, z0: 0, h: 7 });
    }
    B.lights.push(iso(0.2, 0, 5).concat([0.9]));
  }

  function techP(lv) {
    var fu = 0.34, fv = 0.32, floors = 3 + lv, fh = 7, h = floors * fh;
    pad(0.47, 0.47, '#c9cdd0', al('#000000', 0.15));
    shrub(-0.4, 0.4, 0.5); shrub(0.4, -0.38, 0.5);
    var b = box({ fu: fu, fv: fv, h: h, wall: '#dbe7f0', wallR: '#9fb5c6', tex: 'glass', floorH: fh });
    for (var f = 0; f < floors; f++) {
      var z0 = f * fh + 1, z1 = z0 + fh - 2;
      if (f % 2 === 0 || f === floors - 1) B.wins.push([b.L(-fu, z0), b.L(fu, z0), b.L(fu, z1), b.L(-fu, z1)]);
      if (f % 2 === 1) B.wins.push([b.R(fv, z0), b.R(-fv, z0), b.R(-fv, z1), b.R(fv, z1)]);
    }
    poly([b.L(-fu, h - 1.4), b.L(fu, h - 1.4), b.L(fu, h), b.L(-fu, h)], brand);
    poly([b.R(fv, h - 1.4), b.R(-fv, h - 1.4), b.R(-fv, h), b.R(fv, h)], sh(brand, -0.2));
    door(b.R, 0.14, -0.1, 5.6, '#cfe3ee', { glass: true });
    poly([iso(fu, 0.2, 6), iso(fu + 0.12, 0.2, 6), iso(fu + 0.12, -0.15, 6), iso(fu, -0.15, 6)], brand);
    var zt = flat(b, '#8f9496', 1.2);
    antenna(-fu * 0.4, -fv * 0.3, zt, 12);
    dish(fu * 0.3, -fv * 0.2, zt);
    for (var n = 0; n < 2; n++) poly([iso(-0.1 + n * 0.16, 0.1, zt + 1), iso(0.03 + n * 0.16, 0.1, zt + 1), iso(0.03 + n * 0.16, 0.22, zt + 2.8), iso(-0.1 + n * 0.16, 0.22, zt + 2.8)], '#203c6e', '#9cb6e3', 0.3);
    B.lights.push(iso(0.2, 0.1, 6).concat([1.4]));
  }

  function pousadaP(lv) {
    var floors = 2 + (lv > 2 ? 1 : 0), fh = 10, h = floors * fh + 1;
    grassPad(0.47, 0.47);
    if (lv >= 2) {
      quad(-0.44, 0.1, -0.12, 0.44, 0, '#e8e2d4');
      quad(-0.4, 0.14, -0.16, 0.4, 0.2, '#57c4e8');
      quad(-0.38, 0.16, -0.18, 0.38, 0.25, al('#ffffff', 0.25));
    }
    shrub(0.4, -0.38, 0.55, '#3f9442'); pot(0.42, 0.3, '#4da64a');
    var b = box({ cu: lv >= 2 ? 0.05 : 0, cv: lv >= 2 ? -0.06 : 0, fu: lv >= 2 ? 0.33 : 0.38, fv: lv >= 2 ? 0.28 : 0.32, h: h, wall: '#f3e2c4', tex: 'plaster' });
    for (var f = 0; f < floors; f++) {
      var z0 = f * fh + 3.6, z1 = z0 + 5.2;
      win(b.L, -b.fu * 0.7, -b.fu * 0.2, z0, z1, { shutters: '#2f7f5f', frame: '#ffffff' });
      win(b.L, b.fu * 0.2, b.fu * 0.7, z0, z1, { shutters: '#2f7f5f', frame: '#ffffff' });
      win(b.R, -b.fv * 0.2, -b.fv * 0.75, z0, z1, { shutters: '#2f7f5f' });
      if (f > 0) {
        var bz = f * fh + 1.2;
        poly([b.L(-b.fu, bz), b.L(b.fu, bz), iso(b.cu + b.fu, b.cv + b.fv + 0.12, bz), iso(b.cu - b.fu, b.cv + b.fv + 0.12, bz)], '#a8733f');
        for (var a = -b.fu; a <= b.fu + 0.001; a += 0.06) line(iso(b.cu + a, b.cv + b.fv + 0.12, bz), iso(b.cu + a, b.cv + b.fv + 0.12, bz + 3), '#7a4f2e', 0.5);
        line(iso(b.cu - b.fu, b.cv + b.fv + 0.12, bz + 3), iso(b.cu + b.fu, b.cv + b.fv + 0.12, bz + 3), '#7a4f2e', 0.8);
        for (var p = 0; p < 3; p++) { var pp = iso(b.cu - b.fu + 0.12 + p * 0.22, b.cv + b.fv + 0.12, bz + 3.2); circ(pp[0], pp[1] - 1, 1.4, '#4da64a'); circ(pp[0] + 0.6, pp[1] - 1.6, 0.6, '#ff6f91'); }
      }
    }
    door(b.R, b.fv * 0.75, b.fv * 0.25, 7.5, '#7a4f2e');
    hip(b, 10, '#c45a3b');
    B.lights.push(iso(0.1, 0.1, 7).concat([1.2]));
  }

  function hortaP(lv) {
    quad(-0.46, -0.46, 0.46, 0.46, 0, '#8a6a46');
    var beds = lv === 1 ? 3 : 4, crops = ['alface', 'tomate', 'cenoura', 'couve'];
    for (var n = 0; n < beds; n++) {
      var v0 = -0.4 + n * (0.8 / beds) + 0.02, v1 = v0 + 0.8 / beds - 0.06;
      box({ cu: 0, cv: (v0 + v1) / 2, fu: 0.4, fv: (v1 - v0) / 2, h: 1.6, wall: '#a8733f', top: '#6b4a2e', tex: 'wood', vol: false });
      var crop = crops[n % crops.length];
      for (var m = 0; m < 7; m++) {
        var u = -0.34 + m * 0.113, c = iso(u, (v0 + v1) / 2, 1.6);
        if (crop === 'alface') { circ(c[0], c[1] - 1.4, 2.2, '#5fbf4a'); circ(c[0] - 0.5, c[1] - 2, 1.2, '#9be27a'); }
        else if (crop === 'tomate') { line(c, [c[0], c[1] - 6], '#8a6a42', 0.4); circ(c[0], c[1] - 3.5, 1.9, '#3f9e45'); circ(c[0] + 0.8, c[1] - 2.6, 0.75, '#e2412b'); circ(c[0] - 0.7, c[1] - 4.2, 0.65, '#ff5a3a'); }
        else if (crop === 'cenoura') { for (var k = -1; k <= 1; k++) line([c[0], c[1] - 0.5], [c[0] + k * 1.4, c[1] - 3.6], '#58b84a', 0.6); circ(c[0], c[1] - 0.3, 0.6, '#ff8c1a'); }
        else { circ(c[0], c[1] - 1.6, 2.3, '#3f8f4a'); circ(c[0] + 0.6, c[1] - 2.2, 1.1, '#6fc070'); }
      }
    }
    if (lv >= 2) { var wc = iso(0.4, 0.42, 0); poly([[wc[0] - 2, wc[1] - 3], [wc[0] + 2, wc[1] - 3], [wc[0] + 1.6, wc[1]], [wc[0] - 1.6, wc[1]]], '#4f8fc0'); line([wc[0] + 2, wc[1] - 2.6], [wc[0] + 4, wc[1] - 4.2], '#4f8fc0', 0.7); }
    if (lv >= 3) {
      var sc = iso(-0.42, -0.42, 0);
      line(sc, [sc[0], sc[1] - 14], '#6b4a2e', 0.9); line([sc[0] - 5, sc[1] - 10], [sc[0] + 5, sc[1] - 10], '#6b4a2e', 0.8);
      poly([[sc[0] - 2.5, sc[1] - 11], [sc[0] + 2.5, sc[1] - 11], [sc[0] + 2, sc[1] - 6], [sc[0] - 2, sc[1] - 6]], '#3a73b8');
      circ(sc[0], sc[1] - 13, 2, '#f2d38a'); poly([[sc[0] - 3.4, sc[1] - 14], [sc[0] + 3.4, sc[1] - 14], [sc[0], sc[1] - 17]], '#d9a441');
      B.vols.push({ t: 'pole', u: -0.42, v: -0.42, h: 16 });
    }
    fence(-0.46, 0.46, 0.46, 0.46, '#f2ede2', 2.4);
    fence(0.46, -0.46, 0.46, 0.46, '#f2ede2', 2.4);
  }

  function galinheiroP(lv) {
    quad(-0.46, -0.46, 0.46, 0.46, 0, '#c8b27f');
    var r = U.rng(5), n;
    for (n = 0; n < 30; n++) { var p = iso(r() - 0.5, r() - 0.5, 0); circ(p[0] * 0.9, p[1] * 0.9, 0.4, 'rgba(120,95,50,0.5)'); }
    function coop(cu, cv) {
      [[-0.14, -0.12], [0.14, -0.12], [0.14, 0.12], [-0.14, 0.12]].forEach(function (d) { line(iso(cu + d[0], cv + d[1], 0), iso(cu + d[0], cv + d[1], 3), '#6b4a2e', 0.8); });
      var b = box({ cu: cu, cv: cv, fu: 0.16, fv: 0.14, z0: 3, h: 8, wall: '#c0392b', tex: 'woodv' });
      door(b.R, 0.05, -0.06, 4, '#5a2a1f');
      poly([iso(cu + 0.16, cv - 0.01, 3), iso(cu + 0.16, cv + 0.06, 3), iso(cu + 0.34, cv + 0.06, 0), iso(cu + 0.34, cv - 0.01, 0)], '#a8733f');
      gable(b, 'u', 6, '#7a4f2e', 0.04);
      line(b.L(-0.16, 0), b.L(0.16, 0), '#f4f1e8', 0.8);
    }
    coop(-0.18, -0.2);
    if (lv >= 2) coop(-0.2, 0.18);
    var chickens = 4 + lv * 2;
    for (n = 0; n < chickens; n++) {
      var c = iso(0.05 + r() * 0.35, -0.3 + r() * 0.7, 0), white = n % 3 !== 0, col = white ? '#ffffff' : '#c47a3a', dir = r() < 0.5 ? -1 : 1;
      ell(c[0], c[1] + 0.3, 2, 0.7, 'rgba(0,0,0,0.15)');
      ell(c[0], c[1] - 1.6, 2.2, 1.6, col);
      circ(c[0] + 1.6 * dir, c[1] - 3, 1.1, col);
      poly([[c[0] + 2.5 * dir, c[1] - 3.1], [c[0] + 3.5 * dir, c[1] - 2.8], [c[0] + 2.5 * dir, c[1] - 2.5]], '#f2a20c');
      circ(c[0] + 1.5 * dir, c[1] - 4, 0.5, '#e33');
      poly([[c[0] - 2 * dir, c[1] - 2.2], [c[0] - 3 * dir, c[1] - 3.6], [c[0] - 1.4 * dir, c[1] - 2.8]], sh(col, -0.12));
    }
    box({ cu: 0.32, cv: -0.36, fu: 0.08, fv: 0.03, h: 1.4, wall: '#8a8f93', vol: false });
    fence(-0.46, 0.46, 0.46, 0.46, '#d9cfb5', 3.4, 14);
    fence(0.46, -0.46, 0.46, 0.46, '#d9cfb5', 3.4, 14);
  }

  function pomarP(lv, variant) {
    grassPad(0.46, 0.46);
    var pos = lv === 1 ? [[-0.22, -0.22], [0.22, -0.22], [-0.22, 0.22], [0.22, 0.22]] :
      [[-0.28, -0.28], [0.05, -0.3], [0.32, -0.28], [-0.3, 0.05], [0.3, 0.05], [-0.28, 0.32], [0.05, 0.3], [0.32, 0.32]];
    pos.forEach(function (p, n) { broadleaf(p[0], p[1], lv === 1 ? 0.62 : 0.5, (variant + n) % 4, 0, n % 2 ? '#f2a20c' : '#e0352b'); });
    var bk = iso(0.42, 0.06, 0);
    poly([[bk[0] - 2.5, bk[1] - 2.4], [bk[0] + 2.5, bk[1] - 2.4], [bk[0] + 2, bk[1]], [bk[0] - 2, bk[1]]], '#c9884d');
    circ(bk[0] - 1, bk[1] - 2.8, 0.9, '#e0352b'); circ(bk[0] + 0.8, bk[1] - 2.9, 0.9, '#f2a20c');
  }

  function viveiroP(lv) {
    quad(-0.46, -0.46, 0.46, 0.46, 0, '#8f6e4b');
    for (var r = 0; r < 4; r++) {
      var v = -0.33 + r * 0.22;
      quad(-0.36, v - 0.07, 0.36, v + 0.07, 0, '#5a3f28');
      for (var c = 0; c < 8; c++) { var p = iso(-0.31 + c * 0.088, v, 0); circ(p[0], p[1] - 1.2, 1.2, c % 2 ? '#5fbf4a' : '#7ed35d'); line([p[0], p[1]], [p[0], p[1] - 1], '#3f8f3a', 0.4); }
    }
    var H = 13 + lv * 2;
    [[-0.44, -0.44], [0.44, -0.44], [0.44, 0.44], [-0.44, 0.44], [0, -0.44], [0, 0.44]].forEach(function (d) { line(iso(d[0], d[1], 0), iso(d[0], d[1], H), '#5d6266', 0.8); });
    g.globalAlpha = 0.36;
    poly(q(-0.46, -0.46, 0.46, 0.46, H), '#173d24');
    g.globalAlpha = 1;
    for (var n = -0.4; n <= 0.41; n += 0.1) line(iso(n, -0.46, H), iso(n, 0.46, H), al('#000000', 0.2), 0.3);
    poly([iso(-0.46, 0.46, H), iso(0.46, 0.46, H), iso(0.46, 0.46, H - 2.5), iso(-0.46, 0.46, H - 2.5)], al('#173d24', 0.55));
    poly([iso(0.46, 0.46, H), iso(0.46, -0.46, H), iso(0.46, -0.46, H - 2.5), iso(0.46, 0.46, H - 2.5)], al('#102c19', 0.6));
    B.vols.push({ t: 'box', cu: 0, cv: 0, fu: 0.46, fv: 0.46, z0: H - 1, h: 1 });
    pot(0.5, 0.2, '#4da64a');
  }

  function apiarioP(lv) {
    grassPad(0.46, 0.46);
    var r = U.rng(8), cols = ['#b57bff', '#ffd23f', '#ffffff', '#ff6fa5', '#9f7aea'], n;
    for (n = 0; n < 34; n++) { var p = iso((r() - 0.5) * 0.88, (r() - 0.5) * 0.88, 0); line(p, [p[0], p[1] - 2.2], '#3f8f3a', 0.4); circ(p[0], p[1] - 2.6, 0.9, cols[n % cols.length]); }
    var hives = [[-0.2, -0.16], [0.14, -0.2], [-0.02, 0.18]];
    if (lv >= 2) hives.push([0.3, 0.16]);
    if (lv >= 3) hives.push([-0.32, 0.22]);
    hives.sort(function (a, b) { return (a[0] + a[1]) - (b[0] + b[1]); });
    hives.forEach(function (hp) {
      box({ cu: hp[0], cv: hp[1], fu: 0.07, fv: 0.07, h: 1.4, wall: '#7a5434', vol: false });
      box({ cu: hp[0], cv: hp[1], fu: 0.065, fv: 0.065, z0: 1.4, h: 3, wall: '#f6f1e2' });
      box({ cu: hp[0], cv: hp[1], fu: 0.065, fv: 0.065, z0: 4.4, h: 3, wall: '#f4c542' });
      box({ cu: hp[0], cv: hp[1], fu: 0.08, fv: 0.08, z0: 7.4, h: 1, wall: '#e9e4d6' });
      var e = iso(hp[0] + 0.065, hp[1], 2); line([e[0] - 0.8, e[1]], [e[0] + 0.8, e[1] + 0.4], '#333', 0.5);
    });
    for (n = 0; n < 8; n++) { var bp = iso((r() - 0.5) * 0.8, (r() - 0.5) * 0.8, 8 + r() * 6); circ(bp[0], bp[1], 0.55, '#f2c200'); circ(bp[0] + 0.5, bp[1] - 0.3, 0.35, 'rgba(255,255,255,0.8)'); }
  }

  function estufaP(lv) {
    quad(-0.46, -0.46, 0.46, 0.46, 0, '#c9c4b5');
    var fu = 0.44, fv = lv >= 2 ? 0.4 : 0.34, h = 6 + lv;
    quad(-fu + 0.03, -fv + 0.03, fu - 0.03, fv - 0.03, 0, '#7b5434');
    for (var r = 0; r < 3; r++) for (var c = 0; c < 8; c++) { var p = iso(-0.36 + c * 0.1, -fv + 0.12 + r * (fv * 2 - 0.24) / 2, 0); circ(p[0], p[1] - 2, 2.1, r % 2 ? '#4fb34a' : '#6fcf55'); circ(p[0] + 0.6, p[1] - 1.5, 0.5, '#ff5a3a'); }
    g.globalAlpha = 0.42;
    var b = box({ fu: fu, fv: fv, h: h, wall: '#dff3ff', wallR: '#bfe0f0', top: false, ao: false });
    g.globalAlpha = 1;
    arch(b, 7, '#e6f6ff', 0.5);
    for (var n = 0; n <= 6; n++) { var a = -fu + n * fu / 3; line(b.L(a, 0), b.L(a, h), al('#ffffff', 0.9), 0.5); }
    line(b.L(-fu, h), b.L(fu, h), al('#ffffff', 0.9), 0.6);
    door(b.R, 0.08, -0.08, h - 0.5, '#e0f0f8', { glass: true });
  }

  function coletaP(lv) {
    pad(0.47, 0.47, '#bdbab2', al('#000000', 0.12));
    var H = 12, n;
    [[-0.38, -0.36], [0.2, -0.36], [-0.38, 0.1], [0.2, 0.1]].forEach(function (p) { line(iso(p[0], p[1], 0), iso(p[0], p[1], H), '#5f666b', 0.9); });
    ['#2e86de', '#e74c3c', '#27ae60', '#f1c40f'].forEach(function (col, k) {
      var u = -0.3 + k * 0.15;
      box({ cu: u, cv: -0.12, fu: 0.06, fv: 0.08, h: 6, wall: col });
      box({ cu: u, cv: -0.12, fu: 0.065, fv: 0.085, z0: 6, h: 0.8, wall: sh(col, -0.2), vol: false });
    });
    poly([iso(-0.42, -0.4, H), iso(0.24, -0.4, H), iso(0.24, 0.14, H - 2), iso(-0.42, 0.14, H - 2)], sh(brand, 0.05), sh(brand, -0.3), 0.5);
    for (var a = -0.38; a < 0.24; a += 0.06) line(iso(a, -0.4, H), iso(a, 0.14, H - 2), al('#000000', 0.15), 0.4);
    B.vols.push({ t: 'box', cu: -0.09, cv: -0.13, fu: 0.33, fv: 0.27, z0: H - 1.5, h: 1.5 });
    var bags = lv >= 2 ? 3 : 2;
    for (n = 0; n < bags; n++) {
      var bp = iso(0.34, -0.3 + n * 0.25, 0);
      poly([[bp[0] - 4, bp[1] - 1], [bp[0] + 4, bp[1] + 1], [bp[0] + 4, bp[1] - 6], [bp[0] - 4, bp[1] - 8]], '#f2f0ea', '#c8c4ba', 0.4);
      poly([[bp[0] - 4, bp[1] - 8], [bp[0] + 4, bp[1] - 6], [bp[0] + 3, bp[1] - 8], [bp[0] - 3, bp[1] - 9.5]], '#e2ded4');
      B.vols.push({ t: 'box', cu: 0.34, cv: -0.3 + n * 0.25, fu: 0.08, fv: 0.08, z0: 0, h: 7 });
    }
    var sp = iso(-0.44, 0.38, 0); line(sp, [sp[0], sp[1] - 10], '#666', 0.7);
    poly([[sp[0] - 4, sp[1] - 15], [sp[0] + 4, sp[1] - 13], [sp[0] + 4, sp[1] - 9], [sp[0] - 4, sp[1] - 11]], '#2f9e4f');
    g.font = '4px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('♻️', sp[0], sp[1] - 12);
  }

  function feiraP(lv) {
    pad(0.47, 0.47, '#d9ccab');
    var stalls = lv === 1 ? [[-0.2, -0.2], [0.2, 0.15]] : lv === 2 ? [[-0.22, -0.22], [0.22, -0.18], [-0.12, 0.24]] : [[-0.24, -0.24], [0.2, -0.22], [-0.22, 0.2], [0.22, 0.22]];
    var canopies = [brand, '#e74c3c', '#f1c40f', '#27ae60'];
    function L2(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
    stalls.sort(function (a, b) { return (a[0] + a[1]) - (b[0] + b[1]); });
    stalls.forEach(function (p, n) {
      var cu = p[0], cv = p[1], H = 9, s, m;
      [[-0.13, -0.11], [0.13, -0.11], [0.13, 0.11], [-0.13, 0.11]].forEach(function (d) { line(iso(cu + d[0], cv + d[1], 0), iso(cu + d[0], cv + d[1], H), '#7a5434', 0.7); });
      box({ cu: cu, cv: cv + 0.04, fu: 0.13, fv: 0.06, h: 3.2, wall: '#a8733f', tex: 'wood', top: '#c49a5c' });
      var cols = [['#e0352b', '#f2a20c', '#4fb34a'], ['#ff8c1a', '#9b59b6', '#e0352b'], ['#5fbf4a', '#f1c40f', '#c0392b']][n % 3];
      for (m = 0; m < 6; m++) { var pp = iso(cu - 0.1 + m * 0.04, cv + 0.04, 3.2); circ(pp[0], pp[1] - 0.8, 1.2, cols[m % 3]); circ(pp[0] + 0.7, pp[1] - 1.3, 1, cols[(m + 1) % 3]); }
      box({ cu: cu + 0.16, cv: cv + 0.1, fu: 0.035, fv: 0.035, h: 2.2, wall: '#c49a5c', vol: false });
      var c1 = canopies[n % canopies.length];
      var N0 = iso(cu - 0.16, cv - 0.15, H), E0 = iso(cu + 0.16, cv - 0.15, H), S0 = iso(cu + 0.16, cv + 0.15, H), W0 = iso(cu - 0.16, cv + 0.15, H);
      var R0 = iso(cu - 0.16, cv, H + 4), R1 = iso(cu + 0.16, cv, H + 4);
      for (s = 0; s < 6; s++) {
        var t0 = s / 6, t1 = (s + 1) / 6;
        poly([L2(N0, E0, t0), L2(N0, E0, t1), L2(R0, R1, t1), L2(R0, R1, t0)], s % 2 ? '#ffffff' : sh(c1, 0.1));
        poly([L2(W0, S0, t0), L2(W0, S0, t1), L2(R0, R1, t1), L2(R0, R1, t0)], s % 2 ? '#f0f0f0' : c1);
      }
      for (s = 0; s < 6; s++) { var sc = L2(W0, S0, (s + 0.5) / 6); ell(sc[0], sc[1] + 0.4, 1.4, 0.7, s % 2 ? '#e6e6e6' : sh(c1, -0.1)); }
      B.vols.push({ t: 'pts', pts: [[cu - 0.16, cv - 0.15, H], [cu + 0.16, cv - 0.15, H], [cu + 0.16, cv + 0.15, H], [cu - 0.16, cv + 0.15, H], [cu - 0.16, cv, H + 4], [cu + 0.16, cv, H + 4]] });
    });
  }

  function solarP(lv) {
    pad(0.47, 0.47, '#c4c0b6');
    var rows = lv === 1 ? 2 : 3;
    for (var r = 0; r < rows; r++) {
      var u = 0.28 - r * (0.56 / Math.max(1, rows - 1));
      [[u + 0.1, -0.34], [u + 0.1, 0.34]].forEach(function (p) { line(iso(p[0], p[1], 0), iso(p[0], p[1], 3), '#7d868b', 0.8); });
      [[u - 0.08, -0.34], [u - 0.08, 0.34]].forEach(function (p) { line(iso(p[0], p[1], 0), iso(p[0], p[1], 8), '#7d868b', 0.8); });
      var pts = [iso(u + 0.12, -0.38, 3), iso(u + 0.12, 0.38, 3), iso(u - 0.1, 0.38, 8.5), iso(u - 0.1, -0.38, 8.5)];
      poly(pts, vgrad(pts[3][1], pts[0][1], [[0, '#5a8ad6'], [0.45, '#23468a'], [1, '#162c60']]), '#dfe6f0', 0.6);
      (function (uu, pp) {
        clipTo(pp, function () {
          for (var n = 1; n < 8; n++) { var v = -0.38 + n * 0.095; line(iso(uu + 0.12, v, 3), iso(uu - 0.1, v, 8.5), al('#b9d0f5', 0.55), 0.35); }
          line(iso(uu + 0.01, -0.38, 5.75), iso(uu + 0.01, 0.38, 5.75), al('#b9d0f5', 0.55), 0.35);
          poly([iso(uu + 0.12, -0.15, 3), iso(uu + 0.12, 0.0, 3), iso(uu - 0.1, 0.18, 8.5), iso(uu - 0.1, 0.03, 8.5)], 'rgba(255,255,255,0.2)');
        });
      })(u, pts);
      B.vols.push({ t: 'pts', pts: [[u + 0.12, -0.38, 3], [u + 0.12, 0.38, 3], [u - 0.1, 0.38, 8.5], [u - 0.1, -0.38, 8.5], [u + 0.12, -0.38, 0], [u + 0.12, 0.38, 0]] });
    }
    box({ cu: 0.4, cv: 0.4, fu: 0.05, fv: 0.04, h: 5, wall: '#e6e6e0' });
  }

  function pocoP() {
    grassPad(0.3, 0.3);
    var c = iso(0, 0, 0), R = 8;
    ell(c[0] + 2, c[1] + 1, R + 2, (R + 2) / 2, 'rgba(0,0,0,0.18)');
    poly([[c[0] - R, c[1]], [c[0] + R, c[1]], [c[0] + R, c[1] - 6], [c[0] - R, c[1] - 6]], vgrad(c[1] - 6, c[1] + 4, [[0, '#b9b4ab'], [1, '#8a857c']]));
    ell(c[0], c[1], R, R / 2, '#8f8a80');
    for (var n = 0; n < 7; n++) { var a = Math.PI * n / 7; var p0 = [c[0] - Math.cos(a) * R, c[1] + Math.sin(a) * R / 2]; line(p0, [p0[0], p0[1] - 6], al('#000000', 0.15), 0.4); }
    ell(c[0], c[1] - 6, R, R / 2, '#c9c4ba');
    ell(c[0], c[1] - 6, R - 1.6, (R - 1.6) / 2, '#1f5f96');
    ell(c[0] - 1.5, c[1] - 6.5, 2.5, 1, al('#9fd8ff', 0.6));
    line([c[0] - R + 0.8, c[1] - 6], [c[0] - R + 0.8, c[1] - 22], '#6b4a2e', 1.4);
    line([c[0] + R - 0.8, c[1] - 6], [c[0] + R - 0.8, c[1] - 22], '#6b4a2e', 1.4);
    line([c[0] - R, c[1] - 18], [c[0] + R, c[1] - 18], '#7a5434', 1);
    poly([[c[0] - R - 3, c[1] - 20], [c[0], c[1] - 28], [c[0], c[1] - 24], [c[0] - R - 3, c[1] - 17]], '#b2472f');
    poly([[c[0] + R + 3, c[1] - 20], [c[0], c[1] - 28], [c[0], c[1] - 24], [c[0] + R + 3, c[1] - 17]], '#8f3a26');
    line([c[0] + 1, c[1] - 18], [c[0] + 1, c[1] - 11], '#5a4a3a', 0.4);
    poly([[c[0] - 0.8, c[1] - 11], [c[0] + 2.8, c[1] - 11], [c[0] + 2.4, c[1] - 8], [c[0] - 0.4, c[1] - 8]], '#9a7a50');
    B.vols.push({ t: 'box', cu: 0, cv: 0, fu: 0.14, fv: 0.14, z0: 0, h: 6 });
    B.vols.push({ t: 'pts', pts: [[-0.2, 0, 17], [0.2, 0, 17], [0, -0.2, 17], [0, 0.2, 17], [0, 0, 28]] });
  }

  function pracaP(variant) {
    quad(-0.5, -0.5, 0.5, 0.5, 0, '#ece6d8');
    clipTo(q(-0.48, -0.48, 0.48, 0.48, 0), function () {
      for (var n = -6; n <= 6; n++) {
        g.beginPath();
        for (var s = 0; s <= 24; s++) {
          var u = -0.5 + s / 24, v = n * 0.09 + Math.sin(u * 14) * 0.03;
          var p = iso(u, v, 0); if (s) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]);
        }
        g.strokeStyle = n % 2 ? '#5d5a55' : '#ece6d8'; g.lineWidth = 1.5; g.stroke();
      }
    });
    poly(q(-0.48, -0.48, 0.48, 0.48, 0), null, '#bdb5a3', 0.6);
    var c0 = iso(0, 0, 0);
    ell(c0[0], c0[1], 9, 4.5, '#a7a094'); ell(c0[0], c0[1] - 1.2, 8, 4, '#7a5434');
    broadleaf(0, 0, 0.82, variant, 0);
    bench(0.3, -0.05, 'v'); bench(-0.05, 0.3, 'u');
    lamp(0.36, 0.36, 18);
    [[-0.36, -0.36], [0.36, -0.36], [-0.36, 0.36]].forEach(function (p) { var c = iso(p[0], p[1], 0); ell(c[0], c[1] - 0.6, 4, 2, '#5aa845'); circ(c[0] - 1, c[1] - 1.5, 0.9, '#ff6f91'); circ(c[0] + 1.2, c[1] - 1.2, 0.9, '#ffd23f'); });
  }

  function fonteP() {
    quad(-0.48, -0.48, 0.48, 0.48, 0, '#e2dccd');
    poly(q(-0.48, -0.48, 0.48, 0.48, 0), null, '#c2b9a5', 0.6);
    var c = iso(0, 0, 0);
    ell(c[0] + 2, c[1] + 1.5, 24, 12, 'rgba(0,0,0,0.15)');
    poly([[c[0] - 22, c[1]], [c[0] + 22, c[1]], [c[0] + 22, c[1] - 4], [c[0] - 22, c[1] - 4]], vgrad(c[1] - 4, c[1] + 11, [[0, '#cfc8ba'], [1, '#9f988b']]));
    ell(c[0], c[1], 22, 11, '#a39c8f');
    ell(c[0], c[1] - 4, 22, 11, '#ddd6c8');
    ell(c[0], c[1] - 4, 18.5, 9.2, '#3f9fd8');
    ell(c[0] - 3, c[1] - 5, 9, 3.5, al('#bfe8ff', 0.5));
    poly([[c[0] - 2.4, c[1] - 4], [c[0] + 2.4, c[1] - 4], [c[0] + 1.8, c[1] - 14], [c[0] - 1.8, c[1] - 14]], '#d6cfc1');
    ell(c[0], c[1] - 14, 7, 3.5, '#cfc8ba'); ell(c[0], c[1] - 14.8, 6, 3, '#3f9fd8');
    poly([[c[0] - 1.2, c[1] - 15], [c[0] + 1.2, c[1] - 15], [c[0] + 0.8, c[1] - 20], [c[0] - 0.8, c[1] - 20]], '#d6cfc1');
    B.anim = { type: 'fountain', x: c[0], y: c[1] - 20, r1: 18, by: c[1] - 4 };
    B.vols.push({ t: 'ell', u: 0, v: 0, z: 2, r: 20 });
    B.vols.push({ t: 'pole', u: 0, v: 0, h: 20, w: 2 });
  }

  function parquinhoP() {
    quad(-0.47, -0.47, 0.47, 0.47, 0, '#ead7a0');
    poly(q(-0.47, -0.47, 0.47, 0.47, 0), null, '#c9b27a', 0.6);
    [[-0.28, -0.3], [-0.12, -0.3], [-0.12, -0.14], [-0.28, -0.14]].forEach(function (d) { line(iso(d[0], d[1], 0), iso(d[0], d[1], 12), '#e74c3c', 1); });
    poly(q(-0.29, -0.31, -0.11, -0.13, 12), '#f1c40f');
    poly([iso(-0.11, -0.28, 12), iso(-0.11, -0.16, 12), iso(0.22, -0.16, 0.5), iso(0.22, -0.28, 0.5)], '#2e86de', '#1f5f9e', 0.4);
    for (var n = 0; n < 4; n++) line(iso(-0.3, -0.29, 2 + n * 2.6), iso(-0.3, -0.15, 2 + n * 2.6), '#e74c3c', 0.6);
    B.vols.push({ t: 'box', cu: -0.2, cv: -0.22, fu: 0.09, fv: 0.09, z0: 0, h: 12 });
    var a0 = iso(0.05, 0.25, 0), a1 = iso(0.35, 0.25, 0);
    [a0, a1].forEach(function (a) { line([a[0] - 3, a[1] + 1.5], [a[0], a[1] - 15], '#27ae60', 1); line([a[0] + 3, a[1] - 1.5], [a[0], a[1] - 15], '#27ae60', 1); });
    line([a0[0], a0[1] - 15], [a1[0], a1[1] - 15], '#1e8449', 1.2);
    [0.13, 0.27].forEach(function (u) { var p = iso(u, 0.25, 15), s2 = iso(u, 0.25, 4); line(p, s2, '#555', 0.4); line([p[0] + 2, p[1] - 1], [s2[0] + 2, s2[1] - 1], '#555', 0.4); poly([[s2[0] - 1, s2[1]], [s2[0] + 3, s2[1] - 2], [s2[0] + 3, s2[1] - 1], [s2[0] - 1, s2[1] + 1]], '#e67e22'); });
    B.vols.push({ t: 'pts', pts: [[0.05, 0.25, 15], [0.35, 0.25, 15], [0.05, 0.25, 0], [0.35, 0.25, 0]] });
    var sw = iso(0.25, -0.2, 0);
    poly([[sw[0] - 1.5, sw[1]], [sw[0] + 1.5, sw[1]], [sw[0], sw[1] - 3]], '#7f8c8d');
    line([sw[0] - 9, sw[1] - 1], [sw[0] + 9, sw[1] - 5], '#9b59b6', 1.6);
  }

  function muralP(variant) {
    quad(-0.45, -0.1, 0.45, 0.16, 0, '#d9d2c4');
    var b = box({ cu: 0, cv: 0, fu: 0.44, fv: 0.06, h: 18, wall: '#f0e8d8', tex: 'plaster' });
    var cols = ['#e74c3c', '#f39c12', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6', '#e84393'];
    var face = [b.L(-0.44, 0), b.L(0.44, 0), b.L(0.44, 18), b.L(-0.44, 18)];
    clipTo(face, function () {
      poly(face, vgrad(b.L(0, 18)[1], b.L(0, 0)[1], [[0, '#7fd3f0'], [1, '#f9e79f']]));
      var sun = b.L(0.25, 13); circ(sun[0], sun[1], 4, '#ffcf3a');
      for (var n = 0; n < 5; n++) { var p = b.L(-0.4 + n * 0.2, 0); g.beginPath(); g.moveTo(p[0] - 8, p[1]); g.quadraticCurveTo(p[0], p[1] - 10 - n % 2 * 4, p[0] + 8, p[1] + 4); g.fillStyle = cols[(n + variant) % cols.length]; g.fill(); }
      var hp = b.L(-0.15, 7); circ(hp[0], hp[1] - 4, 2, '#8d5a3b'); poly([[hp[0] - 3, hp[1] + 4], [hp[0] + 3, hp[1] + 5], [hp[0] + 2, hp[1] - 2], [hp[0] - 2, hp[1] - 3]], '#e84393');
      var hp2 = b.L(0.05, 6.5); circ(hp2[0], hp2[1] - 4, 2, '#f1c27d'); poly([[hp2[0] - 3, hp2[1] + 4], [hp2[0] + 3, hp2[1] + 5], [hp2[0] + 2, hp2[1] - 2], [hp2[0] - 2, hp2[1] - 3]], '#3498db');
      line([hp[0] + 2, hp[1] - 1], [hp2[0] - 2, hp2[1] - 1], '#333', 0.6);
    });
  }

  function estatuaP() {
    quad(-0.4, -0.4, 0.4, 0.4, 0, '#d7d0c0');
    box({ fu: 0.24, fv: 0.24, h: 2.4, wall: '#b8b2a5', tex: 'stone' });
    box({ fu: 0.16, fv: 0.16, z0: 2.4, h: 11, wall: '#d0cabd', tex: 'stone' });
    box({ fu: 0.2, fv: 0.2, z0: 13.4, h: 1.2, wall: '#c2bcaf' });
    var p = iso(0, 0, 14.6);
    var bronze = vgrad(p[1] - 18, p[1], [[0, '#a07c4c'], [1, '#5c4428']]);
    poly([[p[0] - 3.2, p[1]], [p[0] + 3.2, p[1]], [p[0] + 2.6, p[1] - 11], [p[0] - 2.6, p[1] - 11]], bronze);
    circ(p[0], p[1] - 13.4, 2.6, '#8a6a40');
    line([p[0] + 2.4, p[1] - 9.5], [p[0] + 6, p[1] - 18], '#7a5c36', 1.6);
    circ(p[0] + 6.2, p[1] - 19.5, 2.4, '#f5b400');
    poly([[p[0] + 5, p[1] - 20.6], [p[0] + 6.2, p[1] - 24], [p[0] + 7.4, p[1] - 20.6]], '#ff7a1a');
    line([p[0] - 2.4, p[1] - 9.5], [p[0] - 4.5, p[1] - 4], '#7a5c36', 1.4);
    B.vols.push({ t: 'box', cu: 0, cv: 0, fu: 0.16, fv: 0.16, z0: 0, h: 14 });
    B.vols.push({ t: 'pole', u: 0, v: 0, h: 38, w: 2.5 });
    B.lights.push([p[0] + 6.2, p[1] - 19.5, 0.5, '#ffb347']);
  }

  function coretoP() {
    quad(-0.48, -0.48, 0.48, 0.48, 0, '#e5dfd0');
    var c = iso(0, 0, 0), R = 18, N = 8, H = 3, top = 15;
    ell(c[0], c[1], R + 2, (R + 2) / 2, '#c9c2b2');
    poly([[c[0] - R, c[1]], [c[0] + R, c[1]], [c[0] + R, c[1] - H], [c[0] - R, c[1] - H]], '#d8d1c2');
    ell(c[0], c[1], R, R / 2, '#bdb6a6');
    ell(c[0], c[1] - H, R, R / 2, '#efe9dc');
    var posts = [];
    for (var n = 0; n < N; n++) { var a = n / N * Math.PI * 2; posts.push([c[0] + Math.cos(a) * (R - 2), c[1] - H + Math.sin(a) * (R - 2) / 2, Math.sin(a)]); }
    posts.filter(function (p) { return p[2] < 0; }).forEach(function (p) { line([p[0], p[1]], [p[0], p[1] - top], '#ffffff', 1.2); });
    g.beginPath(); g.ellipse(c[0], c[1] - H - 3, R - 2, (R - 2) / 2, 0, 0, Math.PI); g.strokeStyle = '#ffffff'; g.lineWidth = 0.6; g.stroke();
    posts.filter(function (p) { return p[2] >= 0; }).forEach(function (p) { line([p[0], p[1]], [p[0], p[1] - top], '#ffffff', 1.2); line([p[0] - 0.4, p[1]], [p[0] - 0.4, p[1] - top], al('#000000', 0.15), 0.4); });
    var ty = c[1] - H - top;
    ell(c[0], ty, R + 1, (R + 1) / 2, '#b8402b');
    poly([[c[0] - R - 1, ty], [c[0] + R + 1, ty], [c[0], ty - 11]], '#c9553a');
    poly([[c[0], ty - 11], [c[0] + R + 1, ty], [c[0], ty + (R + 1) / 2]], '#a63a26');
    poly([[c[0], ty - 11], [c[0] - R - 1, ty], [c[0], ty + (R + 1) / 2]], '#d46a4a');
    circ(c[0], ty - 11.5, 1.2, '#e8c75a');
    B.vols.push({ t: 'ell', u: 0, v: 0, z: H + top + 4, r: R });
    B.lights.push([c[0], c[1] - H - 8, 1.2]);
  }

  function windmillP() {
    grassPad(0.3, 0.3);
    var b0 = iso(0, 0, 0), H = 30;
    [[-5, 0], [5, 0], [0, -2.5], [0, 2.5]].forEach(function (d) { line([b0[0] + d[0], b0[1] + d[1]], [b0[0], b0[1] - H], '#8d9499', 0.8); });
    for (var y = 6; y < H; y += 6) { var k = 1 - y / H; line([b0[0] - 5 * k, b0[1] - y], [b0[0] + 5 * k, b0[1] - y], '#8d9499', 0.5); }
    var hub = [b0[0], b0[1] - H];
    poly([[hub[0] + 1, hub[1] - 1], [hub[0] + 9, hub[1] - 2], [hub[0] + 9, hub[1] + 1], [hub[0] + 1, hub[1] + 1]], '#c0392b');
    circ(hub[0], hub[1], 1.4, '#555');
    track(hub[1] - 12);
    var tk = iso(0.2, 0.2, 0);
    poly([[tk[0] - 4, tk[1]], [tk[0] + 4, tk[1]], [tk[0] + 4, tk[1] - 5], [tk[0] - 4, tk[1] - 5]], '#9aa3a8');
    ell(tk[0], tk[1] - 5, 4, 2, '#b9c1c6');
    B.anim = { type: 'windmill', x: hub[0], y: hub[1], r: 12 };
    B.vols.push({ t: 'pole', u: 0, v: 0, h: H, w: 3 });
    B.vols.push({ t: 'ell', u: 0, v: 0, z: H, r: 11 });
  }

  function bridgeP(mask) {
    var alongU = (mask & 10) && !(mask & 5), alongV = (mask & 5) && !(mask & 10);
    if (!alongU && !alongV) alongU = !(mask & 5);
    var z = 3.5, W = 0.27;
    var piers = alongU ? [[-0.32, -W], [-0.32, W], [0.32, -W], [0.32, W]] : [[-W, -0.32], [W, -0.32], [-W, 0.32], [W, 0.32]];
    piers.forEach(function (p) {
      var a = iso(p[0], p[1], -3), b2 = iso(p[0], p[1], z);
      poly([[a[0] - 1.2, a[1]], [a[0] + 1.2, a[1]], [b2[0] + 1.2, b2[1]], [b2[0] - 1.2, b2[1]]], '#5a3d22');
      ell(a[0], a[1] + 0.5, 3, 1.2, al('#ffffff', 0.45));
    });
    var deck = alongU ? q(-0.52, -W, 0.52, W, z) : q(-W, -0.52, W, 0.52, z);
    poly(alongU ? [iso(-0.52, W, z), iso(0.52, W, z), iso(0.52, W, z - 1.8), iso(-0.52, W, z - 1.8)] : [iso(W, 0.52, z), iso(W, -0.52, z), iso(W, -0.52, z - 1.8), iso(W, 0.52, z - 1.8)], '#6b4a2b');
    poly(deck, '#b07d48');
    clipTo(deck, function () {
      for (var n = -12; n <= 12; n++) {
        var t = n / 24;
        if (alongU) line(iso(t, -W, z), iso(t, W, z), al('#5a3d22', 0.55), 0.6);
        else line(iso(-W, t, z), iso(W, t, z), al('#5a3d22', 0.55), 0.6);
      }
    });
    var rails = alongU ? [[-0.52, -W, 0.52, -W], [-0.52, W, 0.52, W]] : [[-W, -0.52, -W, 0.52], [W, -0.52, W, 0.52]];
    rails.forEach(function (l) {
      for (var m = 0; m <= 3; m++) { var t2 = m / 3, u = l[0] + (l[2] - l[0]) * t2, v = l[1] + (l[3] - l[1]) * t2; line(iso(u, v, z), iso(u, v, z + 4.5), '#5a3d22', 1); }
      line(iso(l[0], l[1], z + 4.5), iso(l[2], l[3], z + 4.5), '#7a5434', 1.1);
      line(iso(l[0], l[1], z + 2.4), iso(l[2], l[3], z + 2.4), '#7a5434', 0.7);
    });
    B.vols.push(alongU ? { t: 'box', cu: 0, cv: 0, fu: 0.5, fv: W, z0: z - 1, h: 1 } : { t: 'box', cu: 0, cv: 0, fu: W, fv: 0.5, z0: z - 1, h: 1 });
  }

  function flowersP(variant) {
    quad(-0.34, -0.34, 0.34, 0.34, 0, '#8c6240');
    box({ fu: 0.34, fv: 0.34, h: 1.6, wall: '#c9c1b0', top: '#7a5434', vol: false });
    var cols = [['#ff4d6d', '#ffd23f'], ['#b57bff', '#ffffff'], ['#ff8c1a', '#ff4d6d'], ['#ffd23f', '#ff6fa5'], ['#ffffff', '#5aa0ff']][variant % 5];
    var r = U.rng(variant * 3 + 1);
    for (var n = 0; n < 22; n++) {
      var p = iso((r() - 0.5) * 0.58, (r() - 0.5) * 0.58, 1.6);
      circ(p[0], p[1] - 1.6, 1.6, '#3f9e45');
      circ(p[0], p[1] - 2.8, 1.2, cols[n % 2]);
      circ(p[0], p[1] - 2.8, 0.4, '#fff3a0');
    }
  }

  function hedgeP() {
    box({ fu: 0.42, fv: 0.42, h: 6, wall: '#3f8f3f', wallR: '#2f7531', top: '#5cb04f', ao: false });
    var r = U.rng(4), n;
    for (n = 0; n < 26; n++) { var p = iso((r() - 0.5) * 0.8, (r() - 0.5) * 0.8, 6); circ(p[0], p[1], 1.4, r() < 0.5 ? '#6fc35d' : '#4fa143'); }
    for (n = 0; n < 16; n++) { var a = (r() - 0.5) * 0.8, z = r() * 6; var pl = iso(a, 0.42, z); circ(pl[0], pl[1], 1, r() < 0.5 ? '#4f9f45' : '#2f7a32'); var pr = iso(0.42, a, z); circ(pr[0], pr[1], 1, r() < 0.5 ? '#3a8a3a' : '#2a6a2c'); }
  }

  function benchP() {
    quad(-0.2, -0.12, 0.2, 0.12, 0, '#cfc6b4');
    bench(0, 0, 'u');
    var c = iso(0.28, 0.2, 0);
    poly([[c[0] - 1.6, c[1] - 4], [c[0] + 1.6, c[1] - 4], [c[0] + 1.2, c[1]], [c[0] - 1.2, c[1]]], '#4a5a52');
    B.vols.push({ t: 'box', cu: 0, cv: 0, fu: 0.13, fv: 0.04, z0: 0, h: 4.4 });
  }

  function wildflowersP(variant) {
    var r = U.rng(variant * 5 + 2), cols = ['#ffd23f', '#ffffff', '#ff8fb1', '#c39bff', '#ff9a3c'];
    for (var n = 0; n < 14; n++) {
      var p = iso((r() - 0.5) * 0.7, (r() - 0.5) * 0.7, 0);
      line(p, [p[0] + (r() - 0.5), p[1] - 3.5], '#3f8f3a', 0.5);
      circ(p[0], p[1] - 3.8, 1.1, cols[(n + variant) % cols.length]);
      circ(p[0], p[1] - 3.8, 0.35, '#fff3a0');
    }
  }

  /* ---------------- Construção e cache ---------------- */
  function make(key, w, h, ox, oy, fn, opts) {
    var c = document.createElement('canvas');
    c.width = Math.ceil(w * SS); c.height = Math.ceil(h * SS);
    g = c.getContext('2d');
    g.scale(SS, SS); g.translate(ox, oy);
    g.lineJoin = 'round'; g.lineCap = 'round';
    B = { vols: [], lights: [], wins: [], emit: [], anim: null, minY: 0, roofTop: 0 };
    fn();
    var meta = B; B = null;
    var spr = { c: (opts && opts.outline === false) ? c : outline(c, opts && opts.outlineAlpha), ox: ox, oy: oy, w: w, h: h,
      top: meta.minY, shadow: shadowFrom(meta.vols), lights: meta.lights.length ? meta.lights : null,
      wins: meta.wins, emit: meta.emit, anim: meta.anim };
    cache[key] = spr;
    return spr;
  }

  // contorno escuro suave (destaca o objeto sobre o chão texturizado)
  function outline(c, a) {
    var o = Math.max(1, Math.round(SS * 0.55));
    var t = document.createElement('canvas'); t.width = c.width; t.height = c.height;
    var tg = t.getContext('2d');
    tg.drawImage(c, 0, 0);
    tg.globalCompositeOperation = 'source-in';
    tg.fillStyle = 'rgba(28,36,30,' + (a || 0.5) + ')';
    tg.fillRect(0, 0, t.width, t.height);
    var out = document.createElement('canvas'); out.width = c.width; out.height = c.height;
    var og = out.getContext('2d');
    og.drawImage(t, o, 0); og.drawImage(t, -o, 0); og.drawImage(t, 0, o); og.drawImage(t, 0, -o);
    og.drawImage(c, 0, 0);
    return out;
  }

  // projeta os volumes no chão (direção do sol); devolve polígonos/elipses em pixels locais
  function proj(u, v, z) { return iso(u + z * LU, v + z * LV, 0); }
  function hull(pts) {
    pts.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    function cross(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
    var lower = [], upper = [], n;
    for (n = 0; n < pts.length; n++) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], pts[n]) <= 0) lower.pop(); lower.push(pts[n]); }
    for (n = pts.length - 1; n >= 0; n--) { while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], pts[n]) <= 0) upper.pop(); upper.push(pts[n]); }
    upper.pop(); lower.pop();
    return lower.concat(upper);
  }
  function shadowFrom(vols) {
    var out = [];
    vols.forEach(function (vl) {
      var pts = [];
      if (vl.t === 'box') {
        [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(function (s) {
          pts.push(proj(vl.cu + s[0] * vl.fu, vl.cv + s[1] * vl.fv, vl.z0));
          pts.push(proj(vl.cu + s[0] * vl.fu, vl.cv + s[1] * vl.fv, vl.z0 + vl.h));
        });
      } else if (vl.t === 'pts') {
        vl.pts.forEach(function (p) { pts.push(proj(p[0], p[1], p[2])); });
      } else if (vl.t === 'ell') {
        var c = proj(vl.u, vl.v, vl.z);
        out.push({ e: 1, x: c[0], y: c[1], rx: vl.r * 1.05, ry: vl.r * 0.6 });
        return;
      } else if (vl.t === 'pole') {
        var a = iso(vl.u, vl.v, 0), b = proj(vl.u, vl.v, vl.h), w = (vl.w || 0.8) * 0.6;
        out.push({ p: [a[0] - w, a[1], a[0] + w, a[1], b[0] + w, b[1], b[0] - w, b[1]] });
        return;
      }
      var hl = hull(pts), flatp = [];
      hl.forEach(function (p) { flatp.push(p[0], p[1]); });
      if (flatp.length >= 6) out.push({ p: flatp });
    });
    return out;
  }

  var TREES = { tree: 1, pine: 1, palm: 1, ipe: 1 };
  function swayFrame(k, time) {
    if (!time || typeof Render === 'undefined' || !Render.high || !Render.high()) return 0;
    var f = Math.floor(time * 1.4 + U.hash2(k % 96, (k / 96) | 0, 9) * 4) % 4;
    return f === 1 ? 1 : f === 3 ? -1 : 0;
  }

  function object(id, lv, variant, time, k) {
    var it = DATA.BY_ID[id], d = it.draw || {}, p = d.p;
    var sway = TREES[p] && k !== undefined ? swayFrame(k, time) : 0;
    var key = 'o' + id + '_' + lv + '_' + variant + '_' + sway;
    if (cache[key]) return cache[key];
    var kind = it.kind;
    var maxH = kind === 'natural' ? 74 : kind === 'decor' ? 80 : 130;
    var W = TW + 40, H = maxH + TH + 8, ox = W / 2, oy = maxH + TH / 2 + 2;
    var opts = { outlineAlpha: kind === 'natural' || kind === 'decor' ? 0.42 : 0.5 };
    return make(key, W, H, ox, oy, function () {
      switch (p) {
        case 'house': houseP(lv, variant); break;
        case 'sobrado': sobradoP(lv, variant); break;
        case 'hq': hqP(lv); break;
        case 'tree': broadleaf((variant % 3 - 1) * 0.05, 0, 1.22 + (variant % 3) * 0.12, variant, sway); break;
        case 'pine': araucaria(0, 0, 1.0 + (variant % 3) * 0.08, variant, sway); break;
        case 'palm': coqueiro(0, 0, 1.12 + (variant % 2) * 0.1, variant, sway); break;
        case 'ipe': ipe(0, 0, 1.22 + (variant % 2) * 0.1, variant, sway); break;
        case 'bush':
          shrub((variant % 3 - 1) * 0.1, 0, 1.3 + (variant % 2) * 0.3, variant % 2 ? '#3f9442' : '#4a9f3f');
          if (variant % 3 === 0) { var bc = iso((variant % 3 - 1) * 0.1, 0, 0); circ(bc[0] - 1.5, bc[1] - 4, 0.8, '#e2412b'); circ(bc[0] + 1.8, bc[1] - 3, 0.8, '#e2412b'); }
          break;
        case 'rock': rock((variant % 3 - 1) * 0.08, 0, 0.95 + (variant % 3) * 0.22, variant); break;
        case 'wildflowers': wildflowersP(variant); break;
        case 'flowers': flowersP(variant); break;
        case 'hedge': hedgeP(); break;
        case 'bench': benchP(); break;
        case 'lamp': lamp(0, 0, 22); break;
        case 'praca': pracaP(variant); break;
        case 'fonte': fonteP(); break;
        case 'parquinho': parquinhoP(); break;
        case 'mural': muralP(variant); break;
        case 'estatua': estatuaP(); break;
        case 'coreto': coretoP(); break;
        case 'windmill': windmillP(); break;
        case 'horta': hortaP(lv); break;
        case 'galinheiro': galinheiroP(lv); break;
        case 'pomar': pomarP(lv, variant); break;
        case 'viveiro': viveiroP(lv); break;
        case 'apiario': apiarioP(lv); break;
        case 'estufa': estufaP(lv); break;
        case 'coleta': coletaP(lv); break;
        case 'feira': feiraP(lv); break;
        case 'solar': solarP(lv); break;
        case 'poco': pocoP(lv); break;
        case 'box':
          if (id === 'creche' || id === 'escola' || id === 'saude' || id === 'banco') civicP(id, lv);
          else if (id === 'triagem' || id === 'armazem' || id === 'marcenaria') industrialP(id, lv);
          else if (id === 'tecnologia') techP(lv);
          else if (id === 'pousada') pousadaP(lv);
          else shopP(id, lv);
          break;
        default: box({ fu: 0.3, fv: 0.3, h: 12, wall: '#dddddd' });
      }
    }, opts);
  }

  function road(id, mask) {
    var key = 'b' + mask;
    if (cache[key]) return cache[key];
    return make(key, TW + 20, TH + 40, (TW + 20) / 2, 30, function () { bridgeP(mask); }, { outlineAlpha: 0.35 });
  }

  function shadowShapes(id, lv, variant) {
    if (id === 'estrada' || id === 'rua') return null;
    if (id === 'ponte') return road('ponte', 10).shadow;
    return object(id, lv, variant).shadow;
  }

  /* ---------------- Partes animadas ---------------- */
  function drawAnim(ctx, spr, wx, wy, t, k) {
    var a = spr.anim, x = wx + a.x, y = wy + a.y, s, n;
    if (a.type === 'flag') {
      var L = a.small ? 7 : 10, H = a.small ? 4 : 6;
      n = 6;
      ctx.beginPath();
      ctx.moveTo(x, y);
      for (s = 1; s <= n; s++) ctx.lineTo(x + L * s / n, y + Math.sin(t * 6 + s * 0.9 + k) * 1.1 * s / n);
      for (s = n; s >= 0; s--) ctx.lineTo(x + L * s / n, y + H + Math.sin(t * 6 + s * 0.9 + k) * 1.1 * s / n);
      ctx.closePath();
      ctx.fillStyle = a.color; ctx.fill();
      ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.lineWidth = 0.4; ctx.stroke();
      if (!a.small && Game.s) {
        ctx.font = '4px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(Game.s.project.emoji, x + L * 0.5, y + H * 0.5 + Math.sin(t * 6 + 2.7 + k) * 0.5);
      }
    } else if (a.type === 'fountain') {
      ctx.fillStyle = 'rgba(225,246,255,0.9)';
      for (var m = 0; m < 16; m++) {
        var ph = (t * 0.8 + m / 16) % 1, ang = m / 16 * Math.PI * 2;
        var dx = Math.cos(ang) * a.r1 * 0.55 * ph, dy = Math.sin(ang) * a.r1 * 0.28 * ph;
        var hy = -Math.sin(ph * Math.PI) * 9;
        ctx.globalAlpha = 1 - ph * 0.6;
        ctx.beginPath(); ctx.arc(x + dx, y + 4 + dy + hy + ph * (a.by - a.y - 4), 0.8, 0, Math.PI * 2); ctx.fill();
      }
      ctx.globalAlpha = 0.6;
      ctx.beginPath(); ctx.ellipse(x, wy + a.by + 1, 6 + Math.sin(t * 4) * 1.5, 2.5, 0, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 0.6; ctx.stroke();
      ctx.globalAlpha = 1;
    } else if (a.type === 'windmill') {
      var ang0 = t * 2.4 + k;
      ctx.fillStyle = '#f2f2ee'; ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 0.4;
      for (var b = 0; b < 6; b++) {
        var an = ang0 + b * Math.PI / 3, cs = Math.cos(an), sn = Math.sin(an);
        ctx.beginPath();
        ctx.moveTo(x + cs * 1.5, y + sn * 1.5);
        ctx.lineTo(x + cs * a.r - sn * 1.6, y + sn * a.r + cs * 1.6);
        ctx.lineTo(x + cs * a.r + sn * 0.6, y + sn * a.r - cs * 0.6);
        ctx.closePath(); ctx.fill(); ctx.stroke();
      }
      ctx.beginPath(); ctx.arc(x, y, 1.6, 0, Math.PI * 2); ctx.fillStyle = '#c0392b'; ctx.fill();
    }
  }

  /* ---------------- Placas sobre as construções ---------------- */
  function badgeCanvas(icon, lv) {
    var key = icon + lv + brand;
    if (badgeCache[key]) return badgeCache[key];
    var S = 3, c = document.createElement('canvas'); c.width = 28 * S; c.height = 34 * S;
    var bg = c.getContext('2d'); bg.scale(S, S);
    bg.fillStyle = 'rgba(0,0,0,0.25)'; bg.beginPath(); bg.ellipse(14, 26, 6, 1.6, 0, 0, Math.PI * 2); bg.fill();
    bg.beginPath(); bg.moveTo(11, 21); bg.lineTo(17, 21); bg.lineTo(14, 25.5); bg.closePath(); bg.fillStyle = brand; bg.fill();
    bg.beginPath(); bg.arc(14, 12, 10, 0, Math.PI * 2); bg.fillStyle = brand; bg.fill();
    bg.beginPath(); bg.arc(14, 12, 8.4, 0, Math.PI * 2); bg.fillStyle = '#ffffff'; bg.fill();
    bg.font = '11px sans-serif'; bg.textAlign = 'center'; bg.textBaseline = 'middle'; bg.fillText(icon, 14, 12.6);
    if (lv > 1) {
      bg.font = 'bold 6px sans-serif'; bg.fillStyle = '#ffcf3a'; bg.strokeStyle = '#6b4d00'; bg.lineWidth = 1.4;
      var st = lv === 2 ? '★★' : '★★★';
      bg.strokeText(st, 14, 30); bg.fillText(st, 14, 30);
    }
    badgeCache[key] = c;
    return c;
  }
  var NOBADGE = { house: 1, decor: 1, natural: 1, road: 1, terrain: 1 };
  function drawBadges(ctx, v, zoom, time) {
    if (!Game.settings || Game.settings.badges === false || zoom < 0.5) return;
    var a = U.clamp((zoom - 0.5) / 0.2, 0, 1), w = World.w, I = DATA.BY_ID;
    var s = U.clamp(1 / zoom, 0.55, 1.6);
    ctx.globalAlpha = a;
    for (var j = v.jmin; j <= v.jmax; j++) for (var i = v.imin; i <= v.imax; i++) {
      var k = j * w.W + i, o = w.obj[k];
      if (!o) continue;
      var it = I[o.id];
      if (NOBADGE[it.kind]) continue;
      var wx = (i - j) * 32, wy = (i + j) * 16;
      if (wx < v.x0 || wx > v.x1 || wy < v.y0 || wy > v.y1) continue;
      var spr = object(o.id, o.lv, varFor(k, o.id), time, k);
      var icon = o.id === 'hq' && Game.s ? Game.s.project.emoji : it.icon;
      var bc = badgeCanvas(icon, o.lv);
      var bw = 28 * s * 0.8, bh = 34 * s * 0.8;
      var by = wy + spr.top - bh - 2 + Math.sin(time * 2 + k) * 0.8;
      ctx.drawImage(bc, wx - bw / 2, by, bw, bh);
    }
    ctx.globalAlpha = 1;
  }

  /* ---------------- Janelas acesas (noite) ---------------- */
  function emissive(spr) {
    if (spr.em !== undefined) return spr.em;
    if (!spr.wins || !spr.wins.length) { spr.em = null; return null; }
    var c = document.createElement('canvas'); c.width = spr.c.width; c.height = spr.c.height;
    var e = c.getContext('2d');
    e.scale(SS, SS); e.translate(spr.ox, spr.oy);
    e.shadowColor = 'rgba(255,200,110,0.9)'; e.shadowBlur = 3 * SS;
    spr.wins.forEach(function (p, n) {
      e.beginPath(); e.moveTo(p[0][0], p[0][1]);
      for (var m = 1; m < p.length; m++) e.lineTo(p[m][0], p[m][1]);
      e.closePath();
      e.fillStyle = n % 5 === 3 ? 'rgba(255,236,190,0.55)' : 'rgba(255,214,130,0.95)';
      e.fill();
    });
    spr.em = c;
    return c;
  }

  /* ---------------- Miniaturas para a interface ---------------- */
  // miniatura para a interface (paleta e cartão), com a peça de chão e a sombra
  function thumb(id, lv) {
    var key = id + '_' + (lv || 1);
    if (thumbs[key] !== undefined) return thumbs[key];
    var it = DATA.BY_ID[id];
    if (!it || it.kind === 'clear') { thumbs[key] = null; return null; }
    if (it.kind === 'terrain' || it.kind === 'road') return (thumbs[key] = groundThumb(it));
    if (!it.draw) { thumbs[key] = null; return null; }
    var c = document.createElement('canvas'), S = 112;
    c.width = S; c.height = S;
    var tg = c.getContext('2d');
    var spr = object(id, lv || 1, 2);
    var top = -spr.top + 18, scale = Math.min(S * 0.92 / 76, S * 0.9 / (top + 6));
    tg.translate(S / 2, S - 16 * scale - 4);
    tg.scale(scale, scale);
    thumbBlock(tg, typeof Tex !== 'undefined' && Tex.pattern ? Tex.pattern('grama') : '#7cc65a', '#5e9a3f', '#6fae4a');
    if (spr.shadow) {
      tg.fillStyle = 'rgba(0,0,0,0.22)';
      spr.shadow.forEach(function (sp) {
        tg.beginPath();
        if (sp.e) tg.ellipse(sp.x, sp.y, sp.rx, sp.ry, 0, 0, Math.PI * 2);
        else { tg.moveTo(sp.p[0], sp.p[1]); for (var n = 2; n < sp.p.length; n += 2) tg.lineTo(sp.p[n], sp.p[n + 1]); tg.closePath(); }
        tg.fill();
      });
    }
    tg.drawImage(spr.c, -spr.ox, -spr.oy, spr.w, spr.h);
    try { thumbs[key] = c.toDataURL('image/png'); } catch (e) { thumbs[key] = null; }
    return thumbs[key];
  }
  // bloco de chão isométrico (topo + laterais com estratos)
  function thumbBlock(tg, top, sideR, sideL, path) {
    tg.fillStyle = sideL; tg.beginPath(); tg.moveTo(-32, 0); tg.lineTo(0, 16); tg.lineTo(0, 24); tg.lineTo(-32, 8); tg.closePath(); tg.fill();
    tg.fillStyle = sideR; tg.beginPath(); tg.moveTo(32, 0); tg.lineTo(0, 16); tg.lineTo(0, 24); tg.lineTo(32, 8); tg.closePath(); tg.fill();
    tg.fillStyle = 'rgba(90,60,30,0.55)';
    tg.beginPath(); tg.moveTo(-32, 3); tg.lineTo(0, 19); tg.lineTo(32, 3); tg.lineTo(32, 8); tg.lineTo(0, 24); tg.lineTo(-32, 8); tg.closePath(); tg.fill();
    tg.beginPath(); tg.moveTo(0, -16); tg.lineTo(32, 0); tg.lineTo(0, 16); tg.lineTo(-32, 0); tg.closePath();
    tg.fillStyle = top; tg.fill();
    if (path) path();
    tg.strokeStyle = 'rgba(255,255,255,0.18)'; tg.lineWidth = 0.6;
    tg.beginPath(); tg.moveTo(-32, 0); tg.lineTo(0, -16); tg.lineTo(32, 0); tg.stroke();
  }
  function groundThumb(it) {
    if (typeof Tex === 'undefined' || !Tex.pattern) return null;
    var c = document.createElement('canvas'), S = 112;
    c.width = S; c.height = S;
    var tg = c.getContext('2d'), sc = 1.55;
    tg.translate(S / 2, S / 2 - 4);
    tg.scale(sc, sc);
    var names = ['grama', 'campo', 'seca', 'areia', 'terra', 'pedra'];
    if (it.kind === 'road') {
      thumbBlock(tg, Tex.pattern('grama'), '#5e9a3f', '#6fae4a', function () {
        tg.save(); tg.clip();
        tg.transform(32, 16, -32, 16, 0, 0);     // espaço do ladrilho, centro em (0,0)
        tg.lineCap = 'butt';
        function st(c, wd) { tg.strokeStyle = c; tg.lineWidth = wd; tg.beginPath(); tg.moveTo(-0.7, 0); tg.lineTo(0.7, 0); tg.stroke(); }
        if (it.id === 'rua') { st('#6f7a5e', 0.8); st('#d8d2c6', 0.74); st('#8a857d', 0.64); st(Tex.pattern('cobble'), 0.6); }
        else {
          st('#9c8452', 0.74); st('#8f6c45', 0.64); st(Tex.pattern('estrada', 1 / 36), 0.56);
          tg.strokeStyle = 'rgba(110,80,45,0.3)'; tg.lineWidth = 0.05;
          tg.beginPath(); tg.moveTo(-0.7, 0.13); tg.lineTo(0.7, 0.13); tg.moveTo(-0.7, -0.13); tg.lineTo(0.7, -0.13); tg.stroke();
        }
        tg.restore();
      });
    } else if (it.terrain === 6 && !it.fill) {
      thumbBlock(tg, '#2b8ccc', '#8a6b48', '#a07c55', function () {
        tg.save(); tg.clip();
        tg.fillStyle = Tex.pattern('waterBlobs'); tg.fillRect(-40, -30, 80, 60);
        tg.fillStyle = Tex.pattern('water'); tg.fillRect(-40, -30, 80, 60);
        tg.strokeStyle = 'rgba(234,215,154,0.9)'; tg.lineWidth = 3;
        tg.beginPath(); tg.moveTo(-32, 0); tg.lineTo(0, -16); tg.lineTo(32, 0); tg.lineTo(0, 16); tg.closePath(); tg.stroke();
        tg.restore();
      });
    } else {
      var nm = names[it.terrain] || 'grama';
      var sides = { grama: ['#5e9a3f', '#6fae4a'], campo: ['#4f8f3b', '#5ea247'], seca: ['#8f9a48', '#a3ad55'], areia: ['#c9b47a', '#dcc68a'], terra: ['#8a6440', '#9c7449'], pedra: ['#7c8285', '#8d9396'] }[nm];
      thumbBlock(tg, Tex.pattern(nm), sides[0], sides[1], it.fill ? function () {
        tg.save(); tg.clip();
        tg.fillStyle = 'rgba(43,140,204,0.9)'; tg.beginPath(); tg.moveTo(-32, 0); tg.lineTo(-10, -11); tg.lineTo(6, 3); tg.lineTo(-14, 9); tg.closePath(); tg.fill();
        tg.restore();
      } : null);
    }
    try { return c.toDataURL('image/png'); } catch (e) { return null; }
  }

  /* ---------------- Utilidades ---------------- */
  function diamondPath(ctx, x, y, s) {
    s = s || 1;
    ctx.beginPath();
    ctx.moveTo(x, y - TH / 2 * s); ctx.lineTo(x + TW / 2 * s, y); ctx.lineTo(x, y + TH / 2 * s); ctx.lineTo(x - TW / 2 * s, y); ctx.closePath();
  }
  function person(ctx, x, y, shirt) {
    ctx.fillStyle = shirt; ctx.fillRect(x - 1.5, y - 6, 3, 4);
    ctx.fillStyle = '#3a3a55'; ctx.fillRect(x - 1.4, y - 2, 1.2, 2); ctx.fillRect(x + 0.2, y - 2, 1.2, 2);
    ctx.beginPath(); ctx.arc(x, y - 7.5, 1.6, 0, Math.PI * 2); ctx.fillStyle = '#c98d5a'; ctx.fill();
  }

  var VAR = null;
  function varFor(k, id) {
    if (!VAR) { VAR = new Uint8Array(World.w.N); for (var n = 0; n < VAR.length; n++) VAR[n] = Math.floor(U.hash2(n % World.w.W, (n / World.w.W) | 0, 77) * 4); }
    var it = DATA.BY_ID[id];
    return it && it.kind === 'house' ? (VAR[k] + (k % 7)) % 10 : VAR[k];
  }

  return {
    TW: TW, TH: TH, setScale: setScale, setBrand: setBrand, clearCache: clearCache, object: object, road: road,
    shadowShapes: shadowShapes, drawAnim: drawAnim, drawBadges: drawBadges, emissive: emissive, thumb: thumb,
    diamondPath: diamondPath, person: person, iso: iso, varFor: varFor,
    scale: function () { return SS; }, brand: function () { return brand; }
  };
})();

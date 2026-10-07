/* Mundo Renda - texturas procedurais sem emenda (chão, estradas, água, encostas) e pequenos detalhes do terreno */
'use strict';

var Tex = (function () {
  var TR = 2;                 // texels por pixel do mundo
  var TW = 256, TH = 128;     // tamanho das texturas do chão em pixels do mundo (proporção isométrica 2:1)
  var tex = {}, pats = {}, details = {};
  var scratch = null;

  function cv(w, h) { var c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h); return c; }
  function ctx2(c) { return c.getContext('2d'); }

  // desenha algo repetindo nas bordas para a textura não ter emenda
  function wrap(w, h, x, y, r, fn) {
    var xs = [x], ys = [y];
    if (x < r) xs.push(x + w); if (x > w - r) xs.push(x - w);
    if (y < r) ys.push(y + h); if (y > h - r) ys.push(y - h);
    for (var a = 0; a < xs.length; a++) for (var b = 0; b < ys.length; b++) fn(xs[a], ys[b]);
  }

  function rgba(hex, a) {
    var c = hex.replace('#', '');
    return 'rgba(' + parseInt(c.substr(0, 2), 16) + ',' + parseInt(c.substr(2, 2), 16) + ',' + parseInt(c.substr(4, 2), 16) + ',' + a + ')';
  }

  function blob(g, x, y, r, color, a) {
    var gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, rgba(color, a)); gr.addColorStop(1, rgba(color, 0));
    g.fillStyle = gr;
    g.beginPath(); g.ellipse(x, y, r, r * 0.6, 0, 0, Math.PI * 2); g.fill();
  }

  /* ---------------- Texturas do chão ---------------- */
  function ground(name, base, spec) {
    var w = TW * TR, h = TH * TR;
    var c = cv(w, h), g = ctx2(c), r = U.rng(spec.seed || 1);
    g.fillStyle = base; g.fillRect(0, 0, w, h);
    var n;
    // manchas grandes e suaves
    for (n = 0; n < (spec.mottle || 0); n++) {
      var mx = r() * w, my = r() * h, mr = (10 + r() * 26) * TR, col = r() < 0.5 ? spec.light : spec.dark, ma = 0.18 + r() * 0.18;
      wrap(w, h, mx, my, mr, function (x, y) { blob(g, x, y, mr, col, ma); });
    }
    // pedrinhas/torrões achatados
    for (n = 0; n < (spec.stones || 0); n++) {
      var sx = r() * w, sy = r() * h, sr = (1.2 + r() * spec.stoneSize) * TR;
      var sc = spec.stoneColors[Math.floor(r() * spec.stoneColors.length)];
      wrap(w, h, sx, sy, sr * 2, function (x, y) {
        g.fillStyle = 'rgba(0,0,0,0.18)';
        g.beginPath(); g.ellipse(x + sr * 0.25, y + sr * 0.3, sr, sr * 0.55, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = sc;
        g.beginPath(); g.ellipse(x, y, sr, sr * 0.55, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = 'rgba(255,255,255,0.28)';
        g.beginPath(); g.ellipse(x - sr * 0.25, y - sr * 0.18, sr * 0.5, sr * 0.25, 0, 0, Math.PI * 2); g.fill();
      });
    }
    // capim: risquinhos verticais
    g.lineCap = 'round';
    for (n = 0; n < (spec.blades || 0); n++) {
      var bx = r() * w, by = r() * h, bl = (1.4 + r() * spec.bladeLen) * TR, tilt = (r() - 0.5) * 1.6 * TR;
      var bc = spec.bladeColors[Math.floor(r() * spec.bladeColors.length)];
      g.strokeStyle = bc; g.lineWidth = (0.45 + r() * 0.35) * TR;
      wrap(w, h, bx, by, bl + 4, function (x, y) { g.beginPath(); g.moveTo(x, y); g.lineTo(x + tilt, y - bl); g.stroke(); });
    }
    // pontinhos
    for (n = 0; n < (spec.dots || 0); n++) {
      var dx = r() * w, dy = r() * h, dr = (0.35 + r() * 0.6) * TR;
      g.fillStyle = spec.dotColors[Math.floor(r() * spec.dotColors.length)];
      g.beginPath(); g.ellipse(dx, dy, dr, dr * 0.6, 0, 0, Math.PI * 2); g.fill();
      if (dx < 4 || dy < 4 || dx > w - 4 || dy > h - 4) { /* pequenos, emenda imperceptível */ }
    }
    // ondulações (areia)
    for (n = 0; n < (spec.ripples || 0); n++) {
      var rx = r() * w, ry = r() * h, rl = (8 + r() * 14) * TR;
      wrap(w, h, rx, ry, rl, function (x, y) {
        g.lineWidth = 0.7 * TR;
        g.strokeStyle = 'rgba(255,255,240,0.35)';
        g.beginPath(); g.moveTo(x - rl, y); g.quadraticCurveTo(x, y - 2.2 * TR, x + rl, y); g.stroke();
        g.strokeStyle = 'rgba(150,120,60,0.18)';
        g.beginPath(); g.moveTo(x - rl, y + 1.1 * TR); g.quadraticCurveTo(x, y - 1.1 * TR, x + rl, y + 1.1 * TR); g.stroke();
      });
    }
    // trevos/florzinhas minúsculas
    for (n = 0; n < (spec.clover || 0); n++) {
      var cx = r() * w, cy = r() * h, cc = spec.cloverColors[Math.floor(r() * spec.cloverColors.length)];
      wrap(w, h, cx, cy, 6, function (x, y) {
        g.fillStyle = cc;
        for (var q = 0; q < 3; q++) { var a = q * 2.1; g.beginPath(); g.arc(x + Math.cos(a) * 0.7 * TR, y + Math.sin(a) * 0.4 * TR, 0.55 * TR, 0, Math.PI * 2); g.fill(); }
      });
    }
    // rachaduras (terra)
    for (n = 0; n < (spec.cracks || 0); n++) {
      var kx = r() * w, ky = r() * h;
      g.strokeStyle = 'rgba(70,45,25,0.25)'; g.lineWidth = 0.5 * TR;
      var steps = [];
      for (var s2 = 0; s2 < 4; s2++) steps.push([(r() - 0.3) * 8 * TR, (r() - 0.5) * 3 * TR]);
      wrap(w, h, kx, ky, 30 * TR, function (x, y) {
        g.beginPath(); g.moveTo(x, y);
        var px = x, py = y;
        for (var s = 0; s < steps.length; s++) { px += steps[s][0]; py += steps[s][1]; g.lineTo(px, py); }
        g.stroke();
      });
    }
    tex[name] = c;
    return c;
  }

  function buildGround() {
    ground('grama', '#76c255', { seed: 11, mottle: 34, light: '#9adb72', dark: '#5ea944', blades: 2600, bladeLen: 2.2,
      bladeColors: ['rgba(70,140,50,0.8)', 'rgba(95,170,65,0.8)', 'rgba(150,220,110,0.75)', 'rgba(185,236,140,0.6)', 'rgba(60,125,45,0.7)'],
      dots: 260, dotColors: ['rgba(60,120,40,0.5)', 'rgba(200,240,150,0.5)'], clover: 26, cloverColors: ['rgba(255,255,255,0.75)', 'rgba(255,230,90,0.8)'] });
    ground('campo', '#5aa645', { seed: 12, mottle: 34, light: '#79c25b', dark: '#447f33', blades: 3200, bladeLen: 2.8,
      bladeColors: ['rgba(50,110,40,0.85)', 'rgba(70,140,52,0.8)', 'rgba(120,190,90,0.7)', 'rgba(40,95,35,0.8)'],
      dots: 200, dotColors: ['rgba(40,90,30,0.5)'], clover: 50, cloverColors: ['rgba(120,190,90,0.9)', 'rgba(255,255,255,0.6)', 'rgba(210,160,255,0.7)'] });
    ground('seca', '#b9bf62', { seed: 13, mottle: 30, light: '#d6d27a', dark: '#9aa04c', blades: 1500, bladeLen: 2.6,
      bladeColors: ['rgba(150,140,60,0.8)', 'rgba(205,190,100,0.8)', 'rgba(120,130,55,0.7)', 'rgba(228,214,140,0.6)'],
      dots: 500, dotColors: ['rgba(160,130,80,0.6)', 'rgba(120,100,60,0.5)'] });
    ground('areia', '#e8d49a', { seed: 14, mottle: 22, light: '#f6e8bd', dark: '#d4bd80', dots: 4200,
      dotColors: ['rgba(200,175,120,0.55)', 'rgba(255,250,230,0.7)', 'rgba(170,145,95,0.45)'], ripples: 46,
      stones: 14, stoneSize: 1.4, stoneColors: ['#f3ecdf', '#d9cdb7', '#e8b9a5'] });
    ground('terra', '#b48555', { seed: 15, mottle: 30, light: '#c99b69', dark: '#946a42', dots: 1500,
      dotColors: ['rgba(110,75,45,0.55)', 'rgba(215,180,135,0.5)'], stones: 70, stoneSize: 1.6,
      stoneColors: ['#a08a74', '#8e7a66', '#c2ad94'], cracks: 18, blades: 120, bladeLen: 1.6, bladeColors: ['rgba(110,150,60,0.6)'] });
    ground('pedra', '#9a9f9e', { seed: 16, mottle: 26, light: '#b7bcb9', dark: '#7f8584', stones: 150, stoneSize: 3.4,
      stoneColors: ['#a9aeab', '#8f9593', '#b9bdb8', '#9a9286'], dots: 900, dotColors: ['rgba(90,95,95,0.5)', 'rgba(220,225,220,0.5)'],
      blades: 220, bladeLen: 1.6, bladeColors: ['rgba(100,140,70,0.6)', 'rgba(130,160,90,0.5)'] });
    // estrada de terra batida
    ground('estrada', '#cfa673', { seed: 17, mottle: 18, light: '#dcb98a', dark: '#b58d5c', dots: 1800,
      dotColors: ['rgba(150,110,70,0.5)', 'rgba(240,215,175,0.5)'], stones: 40, stoneSize: 1.0, stoneColors: ['#bfa98e', '#a8916f'] });
  }

  // calçamento de pedra no espaço do ladrilho (vai ser desenhado com transformação isométrica)
  function buildCobble() {
    var S = 192, c = cv(S, S), g = ctx2(c), r = U.rng(99);
    g.fillStyle = '#7d7871'; g.fillRect(0, 0, S, S);
    var n = 6, cell = S / n;
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      var off = (y % 2) * cell / 2;
      var px = x * cell + off, py = y * cell;
      var shade = 0.82 + r() * 0.3;
      var col = 'rgb(' + Math.round(190 * shade) + ',' + Math.round(184 * shade) + ',' + Math.round(172 * shade) + ')';
      for (var dx = -S; dx <= S; dx += S) {
        var qx = px + dx;
        if (qx > S || qx + cell < 0) continue;
        g.fillStyle = col;
        rr(g, qx + 2.5, py + 2.5, cell - 5, cell - 5, 7); g.fill();
        g.fillStyle = 'rgba(255,255,255,0.18)';
        rr(g, qx + 4, py + 3.5, cell - 10, (cell - 8) * 0.4, 5); g.fill();
      }
    }
    tex.cobble = c;
  }
  function rr(g, x, y, w, h, r) {
    g.beginPath(); g.moveTo(x + r, y); g.lineTo(x + w - r, y); g.quadraticCurveTo(x + w, y, x + w, y + r);
    g.lineTo(x + w, y + h - r); g.quadraticCurveTo(x + w, y + h, x + w - r, y + h); g.lineTo(x + r, y + h);
    g.quadraticCurveTo(x, y + h, x, y + h - r); g.lineTo(x, y + r); g.quadraticCurveTo(x, y, x + r, y); g.closePath();
  }

  // ondas da água (camada animada por cima da cor de fundo)
  function buildWater() {
    var W = 256, H = 128, c = cv(W, H), g = ctx2(c), r = U.rng(5);
    g.lineCap = 'round';
    for (var n = 0; n < 90; n++) {
      var x = r() * W, y = r() * H, l = 5 + r() * 12, lw = 0.7 + r() * 0.9;
      var light = r() < 0.6, la = (0.18 + r() * 0.22).toFixed(2);
      wrap(W, H, x, y, l + 2, function (px, py) {
        g.strokeStyle = light ? 'rgba(255,255,255,' + la + ')' : 'rgba(10,60,110,0.22)';
        g.lineWidth = lw;
        g.beginPath(); g.moveTo(px - l, py); g.quadraticCurveTo(px, py - 1.6, px + l, py); g.stroke();
      });
    }
    tex.water = c;
    var c2 = cv(W, H), g2 = ctx2(c2), r2 = U.rng(8);
    for (var m = 0; m < 26; m++) {
      var bx = r2() * W, by = r2() * H, br = 10 + r2() * 26, bc = r2() < 0.5 ? '#9fe6ff' : '#0b3f73';
      wrap(W, H, bx, by, br, function (px, py) { blob(g2, px, py, br, bc, 0.18); });
    }
    tex.waterBlobs = c2;
  }

  // camadas de terra das bordas da ilha (faixa vertical, 64 px de altura, repete na horizontal)
  function buildStrata() {
    var W = 128, H = 64, c = cv(W, H), g = ctx2(c), r = U.rng(3), x, n;
    var P = Math.PI * 2 / W;
    // limites ondulados (periódicos em W para não ter emenda)
    function edge(y0, amp, k, ph) { return function (xx) { return y0 + Math.sin(xx * P * k + ph) * amp + Math.sin(xx * P * (k + 2) + ph * 1.7) * amp * 0.5; }; }
    var bands = [
      [edge(5.5, 0.6, 3, 0.4), '#8a5f3a'], [edge(15, 1.4, 2, 1.1), '#7a5434'], [edge(25, 1.8, 1, 2.3), '#6d4d33'],
      [edge(34, 1.6, 2, 0.2), '#6b5a4a'], [edge(46, 2.2, 1, 1.4), '#5d544b'], [function () { return H; }, '#4f4842']
    ];
    var prev = function () { return 0; };
    g.fillStyle = '#8a5f3a'; g.fillRect(0, 0, W, H);
    bands.forEach(function (b, i) {
      var top = i ? bands[i - 1][0] : prev;
      g.fillStyle = b[1];
      g.beginPath(); g.moveTo(0, top(0));
      for (x = 0; x <= W; x += 2) g.lineTo(x, top(x));
      for (x = W; x >= 0; x -= 2) g.lineTo(x, b[0](x));
      g.closePath(); g.fill();
      // linha clara no topo de cada camada
      if (i) { g.strokeStyle = 'rgba(255,230,190,0.12)'; g.lineWidth = 0.8; g.beginPath(); for (x = 0; x <= W; x += 2) { if (x) g.lineTo(x, top(x) + 0.6); else g.moveTo(x, top(x) + 0.6); } g.stroke(); }
    });
    // pedras e cascalho
    for (n = 0; n < 130; n++) {
      x = r() * W; var y = 7 + r() * 56, sz = 0.5 + r() * (y > 34 ? 2.8 : 1.6);
      var deep = y > 33, col = deep ? (r() < 0.5 ? '#80766a' : '#463f39') : (r() < 0.5 ? '#9b7048' : '#5f4127');
      wrap(W, H, x, y, sz * 2, function (px, py) {
        g.fillStyle = col; g.beginPath(); g.ellipse(px, py, sz * 1.4, sz, 0, 0, Math.PI * 2); g.fill();
        if (deep && sz > 1.4) { g.fillStyle = 'rgba(255,255,255,0.14)'; g.beginPath(); g.ellipse(px - sz * 0.3, py - sz * 0.35, sz * 0.7, sz * 0.4, 0, 0, Math.PI * 2); g.fill(); }
      });
    }
    // raízes
    g.strokeStyle = 'rgba(60,40,20,0.55)'; g.lineWidth = 0.6;
    for (n = 0; n < 16; n++) { var rx = r() * W, len = 5 + r() * 9; g.beginPath(); g.moveTo(rx, 4); g.quadraticCurveTo(rx + (r() - 0.5) * 6, 4 + len * 0.5, rx + (r() - 0.5) * 8, 4 + len); g.stroke(); }
    // grama da borda com pontas caindo
    g.fillStyle = '#4b8f3a'; g.fillRect(0, 0, W, 3.6);
    g.fillStyle = '#5aa645'; g.fillRect(0, 0, W, 2.2);
    g.fillStyle = '#4b8f3a';
    for (n = 0; n < 40; n++) { x = r() * W; var d = 1.5 + r() * 3.5; g.beginPath(); g.moveTo(x - 1.2, 3); g.lineTo(x + 1.2, 3); g.lineTo(x + 0.2, 3 + d); g.closePath(); g.fill(); }
    tex.strata = c;
  }

  /* ---------------- Detalhes do chão (tufos, flores, pedrinhas) ---------------- */
  function detail(name, w, h, ox, oy, fn) {
    var S = 3, c = cv(w * S, h * S), g = ctx2(c);
    g.scale(S, S); g.translate(ox, oy); g.lineCap = 'round';
    fn(g);
    details[name] = { c: c, w: w, h: h, ox: ox, oy: oy };
  }
  function buildDetails() {
    function tuft(cols) {
      return function (g) {
        g.fillStyle = 'rgba(0,0,0,0.12)'; g.beginPath(); g.ellipse(0.5, 0.3, 3.2, 1.1, 0, 0, Math.PI * 2); g.fill();
        for (var n = 0; n < 7; n++) {
          var a = -1.15 + n * 0.38, l = 3.2 + (n % 3) * 0.9;
          g.strokeStyle = cols[n % cols.length]; g.lineWidth = 0.7;
          g.beginPath(); g.moveTo(0, 0); g.quadraticCurveTo(Math.sin(a) * l * 0.4, -l * 0.6, Math.sin(a) * l, -l); g.stroke();
        }
      };
    }
    detail('tufo', 10, 8, 5, 6, tuft(['#4f9a3a', '#6cbf4c', '#3d8a30', '#8fd46a']));
    detail('tufoEscuro', 10, 8, 5, 6, tuft(['#3a7f2e', '#4f9a3a', '#2f6e28']));
    detail('tufoSeco', 10, 8, 5, 6, tuft(['#a99a52', '#c9b46a', '#8c8a45']));
    function flowers(col) {
      return function (g) {
        for (var n = 0; n < 4; n++) {
          var x = (n - 1.5) * 1.6, y = (n % 2) * 0.8;
          g.strokeStyle = '#3f8f3a'; g.lineWidth = 0.5; g.beginPath(); g.moveTo(x, y); g.lineTo(x, y - 2.2); g.stroke();
          g.fillStyle = col; g.beginPath(); g.arc(x, y - 2.6, 0.85, 0, Math.PI * 2); g.fill();
          g.fillStyle = 'rgba(255,240,120,0.9)'; g.beginPath(); g.arc(x, y - 2.6, 0.32, 0, Math.PI * 2); g.fill();
        }
      };
    }
    detail('florBranca', 9, 6, 4.5, 4.5, flowers('#ffffff'));
    detail('florAmarela', 9, 6, 4.5, 4.5, flowers('#ffd93b'));
    detail('florRoxa', 9, 6, 4.5, 4.5, flowers('#b98cff'));
    detail('florRosa', 9, 6, 4.5, 4.5, flowers('#ff8fb8'));
    detail('pedrinha', 8, 5, 4, 3, function (g) {
      g.fillStyle = 'rgba(0,0,0,0.18)'; g.beginPath(); g.ellipse(0.6, 0.6, 2.6, 1.1, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#9a9a92'; g.beginPath(); g.ellipse(0, 0, 2.4, 1.4, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#c4c4bb'; g.beginPath(); g.ellipse(-0.5, -0.4, 1.3, 0.6, 0, 0, Math.PI * 2); g.fill();
    });
    detail('concha', 6, 4, 3, 2, function (g) {
      g.fillStyle = '#fff3e6'; g.beginPath(); g.ellipse(0, 0, 1.4, 0.9, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = 'rgba(200,140,120,0.8)'; g.lineWidth = 0.3; g.beginPath(); g.moveTo(-1, 0); g.lineTo(1, 0); g.stroke();
    });
    detail('graveto', 9, 4, 4.5, 2, function (g) {
      g.strokeStyle = '#7a5434'; g.lineWidth = 0.6; g.beginPath(); g.moveTo(-3, 0.5); g.lineTo(3, -0.5); g.moveTo(0.5, 0); g.lineTo(1.6, -1.2); g.stroke();
    });
    detail('cogumelo', 6, 6, 3, 5, function (g) {
      g.fillStyle = '#f2e6d6'; g.fillRect(-0.4, -1.8, 0.8, 1.8);
      g.fillStyle = '#d9483b'; g.beginPath(); g.ellipse(0, -2, 1.6, 0.9, 0, Math.PI, 0); g.fill();
      g.fillStyle = '#fff'; g.beginPath(); g.arc(-0.5, -2.3, 0.25, 0, Math.PI * 2); g.fill();
    });
  }

  function init() {
    if (tex.grama) return;
    buildGround(); buildCobble(); buildWater(); buildStrata(); buildDetails();
    scratch = cv(4, 4);
  }

  // padrão com escala certa (as texturas têm TR texels por pixel do mundo)
  function pattern(name, scale) {
    var key = name + '_' + (scale || 1);
    if (pats[key]) return pats[key];
    var g = scratch.getContext('2d');
    var p = g.createPattern(tex[name], 'repeat');
    var s = 1 / (name === 'cobble' ? 192 : name === 'water' || name === 'waterBlobs' || name === 'strata' ? 1 : TR) * (scale || 1);
    if (p.setTransform && window.DOMMatrix) p.setTransform(new DOMMatrix([s, 0, 0, s, 0, 0]));
    pats[key] = p;
    return p;
  }
  // padrão novo (para animar com setTransform sem afetar o cache)
  function freshPattern(name) {
    return scratch.getContext('2d').createPattern(tex[name], 'repeat');
  }

  return { init: init, pattern: pattern, freshPattern: freshPattern, tex: tex, details: details, TR: TR };
})();

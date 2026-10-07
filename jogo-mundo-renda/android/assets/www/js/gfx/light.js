/* Mundo Renda - iluminação: cor do céu ao longo do dia, mapa de luz noturno (multiplicativo),
   janelas acesas, brilho das lâmpadas e vinheta */
'use strict';

var Light = (function () {
  var lc = null, lg = null, LS = 0.5, cwCss = 0, chCss = 0, dprv = 1;
  var glow = null, tinted = {}, vig = null, vigKey = '';

  // cor ambiente por hora do dia (multiplica a cena)
  var KEYS = [
    [0, [62, 74, 122]], [4.4, [62, 74, 122]], [5.4, [140, 120, 165]], [6.3, [255, 196, 178]], [7.6, [255, 246, 236]],
    [8.4, [255, 255, 255]], [16.4, [255, 255, 255]], [17.4, [255, 228, 186]], [18.4, [246, 168, 132]],
    [19.3, [150, 108, 156]], [20.3, [72, 80, 132]], [24, [62, 74, 122]]
  ];
  function ambient(t) {
    var h = (t % 1) * 24;
    for (var n = 0; n < KEYS.length - 1; n++) {
      var a = KEYS[n], b = KEYS[n + 1];
      if (h >= a[0] && h <= b[0]) {
        var f = (h - a[0]) / (b[0] - a[0]);
        f = f * f * (3 - 2 * f);
        return [a[1][0] + (b[1][0] - a[1][0]) * f, a[1][1] + (b[1][1] - a[1][1]) * f, a[1][2] + (b[1][2] - a[1][2]) * f];
      }
    }
    return [255, 255, 255];
  }

  function makeGlow(c0, c1) {
    var c = document.createElement('canvas'); c.width = c.height = 128;
    var g = c.getContext('2d'), gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, c0); gr.addColorStop(0.35, c1); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    return c;
  }

  function resize(cw, ch, dpr) {
    cwCss = cw; chCss = ch; dprv = dpr;
    if (!lc) { lc = document.createElement('canvas'); lg = lc.getContext('2d'); }
    var q = Render.high && !Render.high() ? 0.34 : LS;
    lc.width = Math.max(2, Math.ceil(cw * dpr * q)); lc.height = Math.max(2, Math.ceil(ch * dpr * q));
    lc._q = q;
    if (!glow) glow = makeGlow('rgba(255,224,170,1)', 'rgba(255,190,110,0.55)');
  }
  // brilho colorido (antenas, tochas, faróis): cor '#rrggbb'
  function glowOf(col) {
    if (!col) return glow;
    if (!tinted[col]) {
      var r = parseInt(col.substr(1, 2), 16), g = parseInt(col.substr(3, 2), 16), b = parseInt(col.substr(5, 2), 16);
      tinted[col] = makeGlow('rgba(' + r + ',' + g + ',' + b + ',1)', 'rgba(' + r + ',' + g + ',' + b + ',0.45)');
    }
    return tinted[col];
  }

  function darknessOf(amb) { return U.clamp(1 - (amb[0] * 0.3 + amb[1] * 0.55 + amb[2] * 0.15) / 255, 0, 1); }

  // aplica a luz sobre a cena já desenhada (ctx em transformação de mundo)
  function apply(ctx, t, lights, ems, cam, dpr, time, high) {
    var amb = ambient(t);
    if (amb[0] > 254 && amb[1] > 254 && amb[2] > 254) return;
    var dark = darknessOf(amb);
    var q = lc._q, w = lc.width, h = lc.height;
    lg.setTransform(1, 0, 0, 1, 0, 0);
    lg.globalCompositeOperation = 'source-over';
    lg.fillStyle = 'rgb(' + Math.round(amb[0]) + ',' + Math.round(amb[1]) + ',' + Math.round(amb[2]) + ')';
    lg.fillRect(0, 0, w, h);
    var night = U.clamp((dark - 0.12) / 0.5, 0, 1);
    if (night > 0 && lights.length) {
      var z = cam.z * dpr * q;
      lg.setTransform(z, 0, 0, z, (cwCss / 2 - cam.x * cam.z) * dpr * q, (chCss / 2 - cam.y * cam.z) * dpr * q);
      lg.globalCompositeOperation = 'lighter';
      for (var n = 0; n < lights.length; n++) {
        var L = lights[n], r = 34 * L[2] * (1 + 0.04 * Math.sin(time * 3 + n));
        lg.globalAlpha = night * (L[2] > 1.2 ? 0.95 : 0.75);
        lg.drawImage(glowOf(L[6]), L[0] - r, L[1] - r * 0.75, r * 2, r * 1.5);
      }
      lg.globalAlpha = 1;
    }
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = 'multiply';
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(lc, 0, 0, w, h, 0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.restore();
    if (night > 0.15) {
      // janelas acesas
      ctx.globalAlpha = Math.min(1, (night - 0.15) * 1.4);
      for (n = 0; n < ems.length; n++) {
        var e = ems[n], em = Sprites.emissive(e[0]);
        if (em) ctx.drawImage(em, e[1] - e[0].ox, e[2] - e[0].oy, e[0].w, e[0].h);
      }
      // brilho (bloom) das lâmpadas
      if (high) {
        ctx.globalCompositeOperation = 'lighter';
        for (n = 0; n < lights.length; n++) {
          var M = lights[n];
          if (M[2] < 1.1 && !M[6]) continue;
          var rr = 9 * M[2];
          ctx.globalAlpha = night * 0.45;
          ctx.drawImage(glowOf(M[6]), M[0] - rr, M[1] - rr, rr * 2, rr * 2);
        }
        ctx.globalCompositeOperation = 'source-over';
      }
      ctx.globalAlpha = 1;
    }
  }

  function vignette(ctx, W, H) {
    var key = W + 'x' + H;
    if (vigKey !== key) {
      vigKey = key;
      vig = document.createElement('canvas'); vig.width = Math.ceil(W / 4); vig.height = Math.ceil(H / 4);
      var g = vig.getContext('2d'), R = Math.sqrt(vig.width * vig.width + vig.height * vig.height) / 2;
      var gr = g.createRadialGradient(vig.width / 2, vig.height / 2, R * 0.45, vig.width / 2, vig.height / 2, R);
      gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(5,20,15,0.38)');
      g.fillStyle = gr; g.fillRect(0, 0, vig.width, vig.height);
    }
    ctx.drawImage(vig, 0, 0, W, H);
  }

  return { resize: resize, apply: apply, vignette: vignette, ambient: ambient, darknessOf: darknessOf };
})();

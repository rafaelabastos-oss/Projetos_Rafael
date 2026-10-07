/* Mundo Renda - utilitários: aleatoriedade com semente, ruído, formatação */
'use strict';

var U = (function () {
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hash2(i, j, seed) {
    var h = (Math.imul(i, 374761393) + Math.imul(j, 668265263) + Math.imul(seed, 1274126177)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }

  function noise(x, y, seed) {
    var xi = Math.floor(x), yi = Math.floor(y);
    var xf = x - xi, yf = y - yi;
    var a = hash2(xi, yi, seed), b = hash2(xi + 1, yi, seed);
    var c = hash2(xi, yi + 1, seed), d = hash2(xi + 1, yi + 1, seed);
    var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }

  function fbm(x, y, seed, oct) {
    var s = 0, amp = 0.5, f = 1, n = 0;
    for (var o = 0; o < (oct || 4); o++) {
      s += amp * noise(x * f, y * f, seed + o * 101);
      n += amp; amp *= 0.5; f *= 2;
    }
    return s / n;
  }

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

  function money(v) {
    var neg = v < 0; v = Math.abs(Math.round(v));
    var s = String(v).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (neg ? '-R$ ' : 'R$ ') + s;
  }

  function num(v) {
    v = Math.round(v);
    if (Math.abs(v) >= 1000000) return (v / 1000000).toFixed(1).replace('.', ',') + ' mi';
    if (Math.abs(v) >= 10000) return (v / 1000).toFixed(1).replace('.', ',') + ' mil';
    return String(v).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function shortMoney(v) {
    var a = Math.abs(v), s;
    if (a >= 1000000) s = (a / 1000000).toFixed(1).replace('.', ',') + 'mi';
    else if (a >= 10000) s = (a / 1000).toFixed(1).replace('.', ',') + 'mil';
    else s = String(Math.round(a)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return (v < 0 ? '-R$' : 'R$') + s;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function shade(hex, amt) {
    var c = hex.replace('#', '');
    if (c.length === 3) c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
    var r = parseInt(c.substr(0, 2), 16), g = parseInt(c.substr(2, 2), 16), b = parseInt(c.substr(4, 2), 16);
    if (amt >= 0) { r += (255 - r) * amt; g += (255 - g) * amt; b += (255 - b) * amt; }
    else { r *= 1 + amt; g *= 1 + amt; b *= 1 + amt; }
    return 'rgb(' + Math.round(r) + ',' + Math.round(g) + ',' + Math.round(b) + ')';
  }

  function pick(arr, r) { return arr[Math.floor(r * arr.length) % arr.length]; }

  function el(id) { return document.getElementById(id); }

  return {
    rng: rng, hash2: hash2, noise: noise, fbm: fbm, clamp: clamp, money: money, num: num,
    shortMoney: shortMoney, esc: esc, shade: shade, pick: pick, el: el
  };
})();

/* Mundo Renda - mundo aberto: mapa, geração procedural, regras de construção, desfazer, conexões e áreas de efeito */
'use strict';

var World = (function () {
  var W = 96, H = 96, N = W * H;
  var T = DATA.T, I = DATA.BY_ID;

  var w = {
    W: W, H: H, N: N,
    ter: new Uint8Array(N),
    obj: new Array(N),
    roadConn: new Uint8Array(N),
    beauty: new Float32Array(N),
    covSaude: new Uint8Array(N), covEscola: new Uint8Array(N), covCreche: new Uint8Array(N),
    waterB: new Uint8Array(N), solarB: new Uint8Array(N), houseN: new Uint8Array(N),
    hq: -1, dirty: true, mapVersion: 0,
    counts: {}, undo: [], action: null
  };

  var listeners = [];
  function onChange(fn) { listeners.push(fn); }
  function emit(k, prev, obj) { for (var n = 0; n < listeners.length; n++) listeners[n](k, prev, obj); }

  function idx(i, j) { return j * W + i; }
  function inside(i, j) { return i >= 0 && j >= 0 && i < W && j < H; }
  function iOf(k) { return k % W; }
  function jOf(k) { return (k / W) | 0; }

  function clear() {
    w.ter.fill(0);
    for (var k = 0; k < N; k++) w.obj[k] = null;
    w.hq = -1; w.undo = []; w.action = null;
    touch();
    emit(-1);
  }

  function touch() { w.dirty = true; w.mapVersion++; }

  /* ---------------- Geração procedural ---------------- */
  function generate(seed, preset) {
    clear();
    var r = U.rng(seed);
    var s1 = (seed * 7 + 13) | 0, s2 = (seed * 11 + 29) | 0, s3 = (seed * 17 + 5) | 0, s4 = (seed * 23 + 3) | 0;
    var i, j, k;
    var base = preset === 'cerrado' ? T.SECA : T.GRAMA;

    for (j = 0; j < H; j++) for (i = 0; i < W; i++) {
      k = idx(i, j);
      var g = U.fbm(i * 0.07, j * 0.07, s1, 4);
      var t = base;
      if (preset === 'cerrado') {
        if (g > 0.62) t = T.TERRA; else if (g < 0.36) t = T.GRAMA;
      } else {
        if (g > 0.6) t = T.CAMPO;
      }
      var hill = U.fbm(i * 0.05 + 40, j * 0.05 + 40, s2, 4);
      if (hill > 0.7) t = T.PEDRA;
      w.ter[k] = t;
    }

    var water = new Uint8Array(N);
    function wet(ii, jj) { if (inside(ii, jj)) water[idx(ii, jj)] = 1; }

    if (preset === 'rio' || preset === 'cerrado' || preset === 'litoral') {
      // rio sinuoso de cima para baixo (eixo j)
      var phase = r() * 6.28, baseI = W * (0.3 + r() * 0.4);
      var amp = preset === 'litoral' ? 10 : 16;
      var width = preset === 'cerrado' ? 0.8 : 1.6;
      for (j = -2; j < H + 2; j++) {
        var ci = baseI + Math.sin(j * 0.055 + phase) * amp + (U.fbm(j * 0.05, 3, s3, 3) - 0.5) * 18;
        var wd = width + U.fbm(j * 0.08, 9, s4, 2) * (preset === 'cerrado' ? 0.8 : 1.6);
        if (preset === 'litoral' && j > H * 0.75) continue;
        for (i = Math.floor(ci - wd - 1); i <= Math.ceil(ci + wd + 1); i++) {
          if (Math.abs(i - ci) <= wd) wet(i, j);
        }
      }
    }
    if (preset === 'litoral') {
      for (j = 0; j < H; j++) {
        var c2 = W - 15 - (U.fbm(j * 0.06, 7, s3 + 9, 3) - 0.5) * 14 - Math.sin(j * 0.09) * 3;
        for (i = 0; i < W; i++) if (i > c2) wet(i, j);
      }
    }
    if (preset === 'lagos' || preset === 'rio') {
      var thr = preset === 'lagos' ? 0.66 : 0.76;
      for (j = 0; j < H; j++) for (i = 0; i < W; i++) {
        if (U.fbm(i * 0.075 + 100, j * 0.075 + 100, s4, 4) > thr) wet(i, j);
      }
    }

    // praia/margem de areia
    for (j = 0; j < H; j++) for (i = 0; i < W; i++) {
      k = idx(i, j);
      if (water[k]) { w.ter[k] = T.AGUA; continue; }
      var near = 0;
      for (var dj = -2; dj <= 2; dj++) for (var di = -2; di <= 2; di++) {
        if (inside(i + di, j + dj) && water[idx(i + di, j + dj)]) {
          var d = Math.max(Math.abs(di), Math.abs(dj));
          near = Math.max(near, d === 1 ? 2 : 1);
        }
      }
      var sandy = preset === 'litoral' ? (i > W - 26) : false;
      if (near === 2 || (near === 1 && (sandy || r() < 0.35))) w.ter[k] = T.AREIA;
    }

    // vegetação e rochas
    for (j = 0; j < H; j++) for (i = 0; i < W; i++) {
      k = idx(i, j);
      var tt = w.ter[k];
      if (tt === T.AGUA) continue;
      var forest = U.fbm(i * 0.09 + 300, j * 0.09 + 300, s2 + 77, 4);
      var rr = r();
      var id = null;
      if (tt === T.PEDRA) {
        if (rr < 0.22) id = 'n_pedra'; else if (rr < 0.3) id = 'n_pinheiro';
      } else if (tt === T.AREIA) {
        if (preset === 'litoral' && rr < 0.08) id = 'n_palmeira';
        else if (rr < 0.02) id = 'n_arbusto';
      } else if (preset === 'cerrado') {
        if (forest > 0.58 && rr < 0.3) id = rr < 0.18 ? 'n_arbusto' : 'n_arvore';
        else if (rr < 0.025) id = 'n_arbusto';
        else if (rr < 0.035) id = 'n_pedra';
      } else {
        if (forest > 0.6) {
          if (rr < 0.55) { var hz = U.hash2(i, j, seed); id = hz < 0.035 ? 'n_ipe' : hz < 0.4 ? 'n_pinheiro' : 'n_arvore'; }
          else if (rr < 0.62) id = 'n_arbusto';
        } else if (forest > 0.52) {
          if (rr < 0.15) id = 'n_arvore'; else if (rr < 0.2) id = 'n_arbusto';
        } else if (rr < 0.012) id = rr < 0.0025 ? 'n_ipe' : 'n_arvore';
        else if (rr < 0.03) id = 'n_flores';
        else if (rr < 0.036) id = 'n_pedra';
      }
      if (id) w.obj[k] = { id: id, lv: 1 };
    }
    touch();
    emit(-1);
  }

  // procura um terreno livre perto do centro (para a câmera inicial)
  function findLand(ci, cj) {
    for (var rad = 0; rad < 40; rad++) {
      for (var dj = -rad; dj <= rad; dj++) for (var di = -rad; di <= rad; di++) {
        if (Math.max(Math.abs(di), Math.abs(dj)) !== rad) continue;
        var i = ci + di, j = cj + dj;
        if (!inside(i, j)) continue;
        var k = idx(i, j);
        if (w.ter[k] !== T.AGUA && landAround(i, j, 3)) return { i: i, j: j };
      }
    }
    return { i: ci, j: cj };
  }
  function landAround(i, j, r) {
    for (var dj = -r; dj <= r; dj++) for (var di = -r; di <= r; di++) {
      if (!inside(i + di, j + dj) || w.ter[idx(i + di, j + dj)] === T.AGUA) return false;
    }
    return true;
  }

  /* ---------------- Regras ---------------- */
  function isRoad(o) { return o && I[o.id].kind === 'road'; }
  function isBuilding(o) {
    if (!o) return false;
    var k = I[o.id].kind;
    return k !== 'road' && k !== 'decor' && k !== 'natural';
  }
  function isNatural(o) { return o && I[o.id].kind === 'natural'; }

  function unlocked(it) {
    var s = Game.s;
    if (it.id === 'hq') return w.hq < 0;
    if (!s || s.mode === 'criativo') return true;
    if (it.lvl <= s.level) return true;
    var br = branchOf(s);
    return !!(br && br.starters.indexOf(it.id) >= 0);
  }
  function branchOf(s) {
    for (var n = 0; n < DATA.BRANCHES.length; n++) if (DATA.BRANCHES[n].id === s.project.branch) return DATA.BRANCHES[n];
    return null;
  }

  function invested(it, lv) {
    var c = it.cost;
    if (lv >= 2) c += it.cost;
    if (lv >= 3) c += it.cost * 2;
    return c;
  }

  // Avalia o uso de uma ferramenta num ladrilho. Retorna {ok, cost, reason, apply()}.
  function evaluate(tool, k) {
    var it = I[tool], o = w.obj[k], t = w.ter[k];
    var res = { ok: false, cost: 0, reason: '' };
    if (!it && tool !== 'demolir') return res;
    var clearCost = isNatural(o) ? 5 : 0;

    if (tool === 'demolir') {
      if (!o) { res.reason = 'Nada para demolir'; return res; }
      if (o.id === 'hq') { res.reason = 'O Centro Comunitário não pode ser demolido'; return res; }
      var oi = I[o.id];
      res.ok = true;
      res.cost = oi.kind === 'natural' ? 5 : -Math.floor(invested(oi, o.lv) * 0.5);
      res.apply = function () { setTile(k, t, null); };
      return res;
    }

    if (it.kind === 'clear') {
      if (!isNatural(o)) { res.reason = 'Sem mato aqui'; return res; }
      res.ok = true; res.cost = it.cost;
      res.apply = function () { setTile(k, t, null); };
      return res;
    }

    if (it.kind === 'terrain') {
      if (it.fill) {
        if (t !== T.AGUA) { res.reason = 'Só funciona na água'; return res; }
        if (o) { res.reason = 'Retire a ponte antes'; return res; }
        res.ok = true; res.cost = it.cost;
        res.apply = function () { setTile(k, T.GRAMA, null); };
        return res;
      }
      if (t === T.AGUA) { res.reason = 'Isso é água (use Aterrar)'; return res; }
      if (o && !isNatural(o)) { res.reason = 'Ocupado'; return res; }
      if (it.terrain === T.AGUA) {
        res.ok = true; res.cost = it.cost + clearCost;
        res.apply = function () { setTile(k, T.AGUA, null); };
        return res;
      }
      if (t === it.terrain) { res.reason = 'Já é ' + it.name.toLowerCase(); return res; }
      res.ok = true; res.cost = it.cost;
      res.apply = function () { setTile(k, it.terrain, o); };
      return res;
    }

    if (it.kind === 'road') {
      if (t === T.AGUA) {
        if (o && o.id === 'ponte') { res.reason = 'Já existe ponte'; return res; }
        if (o) { res.reason = 'Ocupado'; return res; }
        res.ok = true; res.cost = I.ponte.cost;
        res.apply = function () { setTile(k, t, { id: 'ponte', lv: 1 }); };
        return res;
      }
      if (o && o.id === tool) { res.reason = 'Já existe'; return res; }
      if (o && !isNatural(o) && !isRoad(o)) { res.reason = 'Ocupado'; return res; }
      res.ok = true; res.cost = it.cost + clearCost;
      res.apply = function () { setTile(k, t, { id: tool, lv: 1 }); };
      return res;
    }

    // construções e decorações
    if (t === T.AGUA) { res.reason = 'Não dá para construir na água'; return res; }
    if (o && !isNatural(o)) { res.reason = 'Ocupado'; return res; }
    if (it.unique && w.hq >= 0) { res.reason = 'Você já tem um Centro Comunitário'; return res; }
    res.ok = true; res.cost = it.cost + (it.id === 'hq' ? 0 : clearCost);
    res.apply = function () { setTile(k, t, { id: tool, lv: 1 }); };
    return res;
  }

  function setTile(k, ter, obj) {
    var a = w.action;
    if (a && !a.seen[k]) {
      a.seen[k] = 1;
      a.changes.push({ k: k, ter: w.ter[k], obj: w.obj[k] ? { id: w.obj[k].id, lv: w.obj[k].lv } : null });
    }
    var prev = w.obj[k];
    w.ter[k] = ter;
    w.obj[k] = obj;
    if (prev && prev.id === 'hq') w.hq = -1;
    if (obj && obj.id === 'hq') w.hq = k;
    touch();
    emit(k, prev, obj);
  }

  function begin(label) { w.action = { label: label, changes: [], seen: {}, money: 0 }; }
  function commit() {
    var a = w.action; w.action = null;
    if (a && a.changes.length) {
      w.undo.push(a);
      if (w.undo.length > 40) w.undo.shift();
      return a;
    }
    return null;
  }
  function undo() {
    if (w.action) commit();
    var a = w.undo.pop();
    if (!a) return null;
    for (var n = a.changes.length - 1; n >= 0; n--) {
      var c = a.changes[n];
      var cur = w.obj[c.k];
      if (cur && cur.id === 'hq') w.hq = -1;
      w.ter[c.k] = c.ter;
      w.obj[c.k] = c.obj ? { id: c.obj.id, lv: c.obj.lv } : null;
      if (c.obj && c.obj.id === 'hq') w.hq = c.k;
      emit(c.k, cur, w.obj[c.k]);
    }
    touch();
    return a;
  }

  // Aplica uma ferramenta: valida dinheiro/desbloqueio, cobra e registra no desfazer.
  function apply(tool, k) {
    var s = Game.s;
    var it = I[tool];
    if (tool !== 'demolir' && it && !unlocked(it)) return { ok: false, reason: 'Desbloqueia no nível ' + it.lvl };
    var ev = evaluate(tool, k);
    if (!ev.ok) return ev;
    var cost = s.mode === 'criativo' ? 0 : ev.cost;
    if (cost > 0 && s.money < cost) return { ok: false, reason: 'Dinheiro insuficiente', money: true };
    var own = !w.action;
    if (own) begin(tool);
    ev.apply();
    s.money -= cost;
    w.action.money += cost;
    if (own) commit();
    return { ok: true, cost: cost };
  }

  function upgradeCost(it, lv) { return (it.cost || 1500) * lv; }

  function upgrade(k) {
    var s = Game.s, o = w.obj[k];
    if (!o) return { ok: false };
    var it = I[o.id];
    if (o.lv >= 3) return { ok: false, reason: 'Nível máximo' };
    var cost = s.mode === 'criativo' ? 0 : upgradeCost(it, o.lv);
    if (s.money < cost) return { ok: false, reason: 'Dinheiro insuficiente', money: true };
    begin('upgrade');
    setTile(k, w.ter[k], { id: o.id, lv: o.lv + 1 });
    s.money -= cost; w.action.money += cost;
    commit();
    return { ok: true, cost: cost };
  }

  function move(from, to) {
    var s = Game.s, o = w.obj[from];
    if (!o || from === to) return { ok: false, reason: 'Escolha outro lugar' };
    var t = w.ter[to], d = w.obj[to];
    if (t === T.AGUA) return { ok: false, reason: 'Não dá para construir na água' };
    if (d && !isNatural(d)) return { ok: false, reason: 'Ocupado' };
    var it = I[o.id];
    var cost = s.mode === 'criativo' ? 0 : Math.ceil(it.cost * 0.1) + (d ? 5 : 0);
    if (s.money < cost) return { ok: false, reason: 'Dinheiro insuficiente', money: true };
    begin('move');
    setTile(from, w.ter[from], null);
    setTile(to, t, { id: o.id, lv: o.lv });
    s.money -= cost; w.action.money += cost;
    commit();
    return { ok: true, cost: cost };
  }

  // caminho em "L" para estradas
  function linePath(a, b) {
    var ai = iOf(a), aj = jOf(a), bi = iOf(b), bj = jOf(b);
    var out = [], i = ai, j = aj;
    var di = bi > ai ? 1 : -1, dj = bj > aj ? 1 : -1;
    var iFirst = Math.abs(bi - ai) >= Math.abs(bj - aj);
    out.push(idx(i, j));
    if (iFirst) {
      while (i !== bi) { i += di; out.push(idx(i, j)); }
      while (j !== bj) { j += dj; out.push(idx(i, j)); }
    } else {
      while (j !== bj) { j += dj; out.push(idx(i, j)); }
      while (i !== bi) { i += di; out.push(idx(i, j)); }
    }
    return out;
  }

  /* ---------------- Conexões e efeitos ---------------- */
  var N4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];

  function connected(k) {
    if (w.hq < 0) return false;
    if (k === w.hq) return true;
    var i = iOf(k), j = jOf(k);
    for (var n = 0; n < 4; n++) {
      var ii = i + N4[n][0], jj = j + N4[n][1];
      if (!inside(ii, jj)) continue;
      var kk = idx(ii, jj);
      if (w.roadConn[kk] || kk === w.hq) return true;
    }
    return false;
  }

  function stamp(arr, k, r, v, falloff, maxv) {
    var i0 = iOf(k), j0 = jOf(k);
    for (var dj = -r; dj <= r; dj++) for (var di = -r; di <= r; di++) {
      var i = i0 + di, j = j0 + dj;
      if (!inside(i, j)) continue;
      var kk = idx(i, j);
      var d = Math.max(Math.abs(di), Math.abs(dj));
      var val = falloff ? v * (1 - d / (r + 1)) : v;
      if (maxv) arr[kk] = Math.max(arr[kk], val);
      else arr[kk] += val;
    }
  }

  function recompute() {
    if (!w.dirty) return;
    w.dirty = false;
    var k, o, it;
    // BFS de estradas a partir do Centro
    w.roadConn.fill(0);
    if (w.hq >= 0) {
      var q = [], hi = iOf(w.hq), hj = jOf(w.hq);
      for (var n = 0; n < 4; n++) {
        var ii = hi + N4[n][0], jj = hj + N4[n][1];
        if (inside(ii, jj) && isRoad(w.obj[idx(ii, jj)])) { w.roadConn[idx(ii, jj)] = 1; q.push(idx(ii, jj)); }
      }
      while (q.length) {
        k = q.pop();
        var ci = iOf(k), cj = jOf(k);
        for (var m = 0; m < 4; m++) {
          var ni = ci + N4[m][0], nj = cj + N4[m][1];
          if (!inside(ni, nj)) continue;
          var nk = idx(ni, nj);
          if (!w.roadConn[nk] && isRoad(w.obj[nk])) { w.roadConn[nk] = 1; q.push(nk); }
        }
      }
    }
    // mapas de efeito
    w.beauty.fill(0); w.covSaude.fill(0); w.covEscola.fill(0); w.covCreche.fill(0);
    w.waterB.fill(0); w.solarB.fill(0); w.houseN.fill(0);
    var counts = {};
    for (k = 0; k < N; k++) {
      if (w.ter[k] === T.AGUA && !w.obj[k]) {
        stamp(w.beauty, k, 2, 0.5, true, false);
        stamp(w.waterB, k, 2, 1, false, true);
      }
      o = w.obj[k];
      if (!o) continue;
      it = I[o.id];
      counts[o.id] = (counts[o.id] || 0) + 1;
      if (it.beauty) stamp(w.beauty, k, it.br || 0, it.beauty, true, false);
      if (it.kind === 'house' && connected(k)) stamp(w.houseN, k, 5, 1, false, false);
      if (it.eff) {
        var e = it.eff, active = connected(k);
        if (e.type === 'agua') stamp(w.waterB, k, e.r, 1, false, true);
        else if (e.type === 'solar') stamp(w.solarB, k, e.r, 1, false, true);
        else if (active && e.type === 'saude') stamp(w.covSaude, k, e.r, 1, false, true);
        else if (active && e.type === 'escola') stamp(w.covEscola, k, e.r, 1, false, true);
        else if (active && e.type === 'creche') stamp(w.covCreche, k, e.r, 1, false, true);
      }
    }
    w.counts = counts;
  }

  /* ---------------- Salvar / carregar ---------------- */
  function serialize() {
    var ter = '';
    for (var k = 0; k < N; k++) ter += String.fromCharCode(48 + w.ter[k]);
    var objs = [];
    for (k = 0; k < N; k++) {
      var o = w.obj[k];
      if (o) objs.push([k, I[o.id].num, o.lv]);
    }
    return { ter: ter, objs: objs };
  }
  function deserialize(d) {
    clear();
    for (var k = 0; k < N && k < d.ter.length; k++) w.ter[k] = d.ter.charCodeAt(k) - 48;
    for (var n = 0; n < d.objs.length; n++) {
      var e = d.objs[n], it = DATA.ITEMS[e[1]];
      if (!it) continue;
      w.obj[e[0]] = { id: it.id, lv: e[2] || 1 };
      if (it.id === 'hq') w.hq = e[0];
    }
    touch();
    emit(-1);
  }

  /* ---------------- Vila de demonstração (tela inicial) ---------------- */
  function buildDemo(seed) {
    generate(seed, 'rio');
    var c = findLand(W / 2 | 0, H / 2 | 0);
    var put = function (i, j, id) {
      if (!inside(i, j)) return;
      var k = idx(i, j);
      if (w.ter[k] === T.AGUA) { if (I[id].kind === 'road') w.obj[k] = { id: 'ponte', lv: 1 }; return; }
      w.obj[k] = { id: id, lv: 1 };
      if (id === 'hq') w.hq = k;
    };
    var ci = c.i, cj = c.j, d;
    for (d = -7; d <= 7; d++) { put(ci + d, cj + 1, 'rua'); put(ci + 1, cj + d, 'estrada'); }
    put(ci, cj, 'hq');
    var ring = [['casa', -2, 0], ['casa', -3, 0], ['casa', -5, 0], ['horta', -4, 2], ['horta', -5, 2], ['feira', 2, 0],
      ['galinheiro', 3, 2], ['cozinha', 4, 0], ['casa', 2, 2], ['casa', 0, 3], ['casa', 0, 4], ['escola', 2, -2], ['pomar', 0, -2],
      ['casa', 0, -4], ['loja', 2, -4], ['praca', -2, 2], ['fonte', 0, 6], ['arvore', -1, 2], ['flores', -1, 0], ['poste', 2, 1],
      ['arvore', -6, 0], ['creche', 2, 5], ['casa', 5, 2], ['pousada', 0, -6], ['casa', -6, 2], ['poco', -3, 2]];
    ring.forEach(function (e) {
      var i = ci + e[1], j = cj + e[2];
      if (inside(i, j) && !(w.obj[idx(i, j)] && I[w.obj[idx(i, j)].id].kind === 'road')) put(i, j, e[0]);
    });
    touch();
    emit(-1);
    return c;
  }

  return {
    w: w, idx: idx, inside: inside, iOf: iOf, jOf: jOf, clear: clear, generate: generate, findLand: findLand,
    evaluate: evaluate, apply: apply, upgrade: upgrade, upgradeCost: upgradeCost, move: move, begin: begin, commit: commit, undo: undo,
    linePath: linePath, recompute: recompute, connected: connected, isRoad: isRoad, isBuilding: isBuilding,
    isNatural: isNatural, unlocked: unlocked, invested: invested, branchOf: branchOf, serialize: serialize,
    deserialize: deserialize, buildDemo: buildDemo, touch: touch, onChange: onChange
  };
})();

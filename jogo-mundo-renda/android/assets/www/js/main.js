/* Mundo Renda - estado do jogo, laço principal, salvar/carregar, passeio e integração com o Android */
'use strict';

var Game = (function () {
  var G = {
    s: null,
    ui: { tool: null, hover: -1, hoverOk: false, linePath: [], selected: -1, moving: -1 },
    settings: { sound: true, music: false, vibrate: true, daynight: true, alerts: true, grid: true, quality: 'alta', badges: true, weather: true },
    walk: false, walkVec: { x: 0, y: 0 }
  };
  var perfT = 0, perfN = 0, perfSkip = 2;
  var last = 0, saveTimer = 0, titleBase = null, titleT = 0, hero = null, chatT = 0, dirtySave = false, errors = 0;

  function boot() {
    var st = Store.getJSON('mr_settings', null);
    if (st) for (var k in st) G.settings[k] = st[k];
    var cv = U.el('game');
    Render.init(cv);
    Input.init(cv);
    UI.init();
    window.addEventListener('resize', function () { Render.resize(); });
    document.addEventListener('visibilitychange', function () { if (document.hidden) save(); else perfSkip = 1; });
    window.onAndroidBack = function () { return UI.back(); };
    window.onAppPause = function () { save(); };
    U.el('walk-info').addEventListener('click', function () { if (G.walkTarget >= 0) UI.openBuilding(G.walkTarget); });
    startTitle();
    requestAnimationFrame(loop);
    var ld = U.el('loading');
    ld.classList.add('out');
    setTimeout(function () { ld.style.display = 'none'; }, 600);
  }

  window.addEventListener('error', function (e) {
    if (errors++ < 3 && typeof UI !== 'undefined') UI.toast('⚠️ ' + U.esc(String(e.message || e)), 'bad', 5000);
  });

  function startTitle() {
    G.s = null; G.walk = false; hero = null; Render.setHero(null);
    G.walkVec.x = G.walkVec.y = 0;
    UI.showWalk(false);
    G.ui.tool = null; G.ui.selected = -1; G.ui.moving = -1;
    Sprites.setBrand('#2e86de'); Sprites.clearCache();
    var c = World.buildDemo(Math.floor(Math.random() * 9999));
    Render.resetWalkers();
    Render.centerOn(c.i, c.j, 1.25);
    titleBase = { x: Render.cam.x, y: Render.cam.y };
    UI.showTitle();
  }

  function newState(o) {
    return {
      v: 1, id: 'p' + Date.now().toString(36) + Math.floor(Math.random() * 1000),
      project: { name: o.name, emoji: o.emoji, color: o.color, branch: o.branch, branchName: o.branchName },
      mode: o.mode, seed: o.seed, preset: o.preset, day: 1, t: 0.3, money: o.mode === 'criativo' ? 0 : DATA.START_MONEY,
      pop: 0, level: 1, pts: 0, stock: {}, mission: 0,
      stats: { revenue: 0, wages: 0, upkeep: 0, profit: 0, totalWages: 0, totalRevenue: 0, well: 50, lost: 0, sold: {}, produced: {}, bestProfit: 0, bestRevenue: 0 },
      history: [], events: [], nextEvent: 12, lastEvent: null, loan: null, speed: 1, created: Date.now()
    };
  }

  function newGame(o) {
    var s = newState(o);
    G.s = s;
    World.generate(s.seed, s.preset);
    applyBrand(); Sprites.clearCache(); Render.resetWalkers();
    var c = World.findLand(World.w.W / 2 | 0, World.w.H / 2 | 0);
    Render.centerOn(c.i, c.j, 1.2);
    Sim.refresh(s);
    UI.showHUD();
    UI.setTool('hq');
    UI.toast('🏛️ Toque num lugar livre do mapa para fundar o <b>Centro Comunitário</b>', 'good', 6000);
    save();
  }

  function onHQ() {
    UI.toast('🎉 ' + U.esc(G.s.project.name) + ' foi fundado! Agora abra estradas a partir do Centro.', 'good', 5000);
    checkMissions();
    UI.setCategory('vias');
    UI.setTool('estrada');
  }

  function applyBrand() {
    if (!G.s) return;
    Sprites.setBrand(G.s.project.color);
    Sprites.clearCache();
    document.documentElement.style.setProperty('--brand', G.s.project.color);
  }

  function onMapChanged() {
    var s = G.s;
    if (!s) return;
    Sim.refresh(s);
    checkMissions();
    UI.refreshHUD(true);
    UI.refreshPalette();
    if (UI.cardOpen() >= 0) UI.renderCard();
    dirtySave = true;
  }

  function checkMissions() {
    var s = G.s, guard = 0;
    while (s && guard++ < 30) {
      var m = DATA.MISSIONS[s.mission];
      if (!m || Sim.missionStat(s, m.stat) < m.goal) break;
      s.mission++;
      if (s.mode !== 'criativo' && m.reward) s.money += m.reward;
      if (typeof Fx !== 'undefined') Fx.confetti();
      UI.toast('🎯 Missão cumprida: <b>' + m.title + '</b>' + (m.reward && s.mode !== 'criativo' ? ' · +' + U.money(m.reward) : ''), 'good', 3500);
      Sfx.play('mission');
    }
  }

  function endDay() {
    var s = G.s, res = Sim.endDay(s);
    Render.dayFloats(res.report);
    if (res.leveled) {
      var news = DATA.ITEMS.filter(function (it) { return it.lvl === s.level && it.cat !== 'none'; }).map(function (it) { return it.icon; }).join(' ');
      UI.toast('⭐ Nível ' + s.level + ': <b>' + DATA.LEVEL_NAMES[s.level - 1] + '</b>!' + (news && s.mode !== 'criativo' ? ' Novidades: ' + news : ''), 'good', 5000);
      Sfx.play('level');
      if (typeof Fx !== 'undefined') Fx.confetti();
      UI.refreshPalette();
    }
    if (res.event) {
      UI.toast(res.event.icon + ' ' + res.event.text, 'event', 6000);
      Sfx.play('event');
    } else if (res.report.profit > 0) Sfx.play('coin');
    if (s.mode !== 'criativo' && s.money < 0 && s.day % 3 === 0) {
      UI.toast('💸 O caixa está negativo! Pegue microcrédito no painel do projeto ou reduza custos.', 'bad', 5000);
    }
    checkMissions();
    UI.refreshHUD(true);
    if (s.day % 2 === 0) save();
  }

  function loop(t) {
    var dt = Math.min(0.1, last ? (t - last) / 1000 : 0.016);
    last = t;
    var s = G.s;
    if (s) {
      if (s.speed > 0 && World.w.hq >= 0) {
        s.t += dt * s.speed / DATA.DAY_SEC;
        if (s.t >= 1) { s.t -= 1; endDay(); }
      }
      if (G.walk) updateHero(dt);
      saveTimer += dt;
      if (saveTimer > (dirtySave ? 6 : 30)) { saveTimer = 0; save(); }
    } else if (titleBase) {
      titleT += dt;
      Render.cam.x = titleBase.x + Math.sin(titleT * 0.06) * 260;
      Render.cam.y = titleBase.y + Math.sin(titleT * 0.045) * 120;
    }
    Render.draw(dt);
    if (s) UI.refreshHUD();
    // monitora o FPS a cada 4 s (ignora as primeiras janelas)
    perfT += dt; perfN++;
    if (perfT >= 4) {
      if (perfSkip > 0) perfSkip--;
      else if (perfN / perfT < 34) Render.downscale();
      perfT = 0; perfN = 0;
    }
    requestAnimationFrame(loop);
  }

  /* ---------------- Passeio ---------------- */
  var WALKABLE = { flores: 1, n_flores: 1, praca: 1, poste: 1, banco_praca: 1 };
  function walkable(i, j) {
    if (!World.inside(i, j)) return false;
    var k = World.idx(i, j), o = World.w.obj[k];
    if (World.w.ter[k] === DATA.T.AGUA) return !!(o && o.id === 'ponte');
    if (!o) return true;
    return DATA.BY_ID[o.id].kind === 'road' || !!WALKABLE[o.id];
  }
  function setWalk(on) {
    var s = G.s;
    if (!s) return;
    if (on) {
      var start = World.w.hq >= 0 ? World.w.hq : Render.screenToTile(innerWidth / 2, innerHeight / 2);
      var si = World.iOf(start), sj = World.jOf(start), found = null;
      for (var r = 0; r < 8 && !found; r++) for (var dj = -r; dj <= r && !found; dj++) for (var di = -r; di <= r && !found; di++) {
        if (walkable(si + di, sj + dj)) found = { i: si + di, j: sj + dj };
      }
      if (!found) { UI.toast('Não há onde caminhar aqui.', 'bad'); return; }
      hero = { i: found.i, j: found.j, hero: true, shirt: s.project.color, cap: '#ffffff', ph: 0, sp: 1, say: null, sayT: 0 };
      G.walk = true; G.walkTarget = -1;
      Render.setHero(hero);
      Render.cam.z = 1.9;
      UI.showWalk(true);
      UI.toast('🚶 Use o controle para passear pela comunidade. Chegue perto das pessoas e das construções!', '', 4000);
    } else {
      G.walk = false; hero = null; Render.setHero(null);
      G.walkVec.x = G.walkVec.y = 0;
      UI.showWalk(false);
    }
  }
  function updateHero(dt) {
    var v = G.walkVec, m = Math.sqrt(v.x * v.x + v.y * v.y);
    if (m > 0.12) {
      var spd = 95 * Math.min(1, m) * dt;
      var dx = v.x / m * spd, dy = v.y / m * spd;
      var di = (dx / 32 + dy / 16) / 2, dj = (dy / 16 - dx / 32) / 2;
      if (walkable(Math.round(hero.i + di), Math.round(hero.j))) hero.i += di;
      if (walkable(Math.round(hero.i), Math.round(hero.j + dj))) hero.j += dj;
      hero.ph += dt * 12;
      hero.dir = Math.abs(di) > Math.abs(dj) ? [di > 0 ? 1 : -1, 0] : [0, dj > 0 ? 1 : -1];
    }
    var p = Render.tileCenter(hero.i, hero.j);
    Render.cam.x += (p.x - Render.cam.x) * Math.min(1, dt * 6);
    Render.cam.y += (p.y - Render.cam.y) * Math.min(1, dt * 6);
    Render.clampCam();
    // conversa com moradores
    chatT -= dt;
    var ws = Render.walkers();
    for (var n = 0; n < ws.length && chatT <= 0; n++) {
      var a = ws[n], d = Math.abs(a.i - hero.i) + Math.abs(a.j - hero.j);
      if (d < 1.6 && !(a.sayT > 0)) { a.say = DATA.PHRASES[Math.floor(Math.random() * DATA.PHRASES.length)]; a.sayT = 3.5; chatT = 3; }
    }
    // construção mais próxima
    var best = -1, bd = 2.3, hi = Math.round(hero.i), hj = Math.round(hero.j);
    for (var dj = -2; dj <= 2; dj++) for (var di2 = -2; di2 <= 2; di2++) {
      var ii = hi + di2, jj = hj + dj;
      if (!World.inside(ii, jj)) continue;
      var k = World.idx(ii, jj), o = World.w.obj[k];
      if (!o || !World.isBuilding(o)) continue;
      var dd = Math.abs(ii - hero.i) + Math.abs(jj - hero.j);
      if (dd < bd) { bd = dd; best = k; }
    }
    G.walkTarget = best;
    if (best >= 0) {
      var it = DATA.BY_ID[World.w.obj[best].id], st = Sim.status(best) || {};
      var line = st.alert === 'road' ? 'Precisa de estrada' : st.alert === 'staff0' ? 'Sem trabalhadores' : st.alert === 'staff' ? 'Faltam trabalhadores' : st.alert === 'input' ? 'Faltam insumos' : 'Funcionando bem';
      UI.walkInfo('<span>' + it.icon + '</span><div><b>' + it.name + '</b><small>' + line + ' · toque para detalhes</small></div>');
    } else UI.walkInfo('');
  }

  /* ---------------- Salvar / carregar ---------------- */
  function save(manual) {
    var s = G.s;
    if (!s) return;
    dirtySave = false;
    s.cam = { x: Render.cam.x, y: Render.cam.y, z: Render.cam.z };
    s.updated = Date.now();
    var ok = Store.saveGame(s, World.serialize());
    if (manual) UI.toast(ok ? '💾 Projeto salvo!' : 'Não foi possível salvar.', ok ? 'good' : 'bad');
  }

  function load(id) {
    var d = Store.loadGame(id);
    if (!d || !d.s || !d.world) { UI.toast('Não foi possível abrir este projeto.', 'bad'); return; }
    var s = d.s, def = newState({ name: '', emoji: '🌱', color: '#2e86de', branch: 'agro', branchName: '', mode: 'desafio', seed: 1, preset: 'rio' });
    for (var k in def) if (s[k] === undefined) s[k] = def[k];
    for (var k2 in def.stats) if (s.stats[k2] === undefined) s.stats[k2] = def.stats[k2];
    G.s = s; G.walk = false; hero = null; Render.setHero(null);
    G.ui.tool = null; G.ui.selected = -1; G.ui.moving = -1;
    UI.showWalk(false);
    World.deserialize(d.world);
    applyBrand(); Render.resetWalkers();
    if (s.cam) { Render.cam.x = s.cam.x; Render.cam.y = s.cam.y; Render.cam.z = s.cam.z; Render.clampCam(); }
    Sim.refresh(s);
    UI.showHUD();
    if (World.w.hq < 0) UI.setTool('hq');
    UI.toast('Bem-vindo de volta ao ' + s.project.emoji + ' <b>' + U.esc(s.project.name) + '</b>!', 'good');
  }

  function undo(silent) {
    var a = World.undo();
    if (!a) { if (!silent) { UI.toast('Nada para desfazer.', ''); Sfx.play('error'); } return; }
    if (G.s.mode !== 'criativo') G.s.money += a.money;
    Sfx.play('click');
    onMapChanged();
    if (!silent) UI.toast('↩️ Desfeito' + (a.money > 0 && G.s.mode !== 'criativo' ? ' · +' + U.money(a.money) : ''), '');
    if (World.w.hq < 0) UI.setTool('hq');
  }

  function setSpeed(n) { if (G.s) { G.s.speed = n; UI.refreshHUD(true); } }

  function setSetting(key, val) {
    G.settings[key] = val;
    Store.setJSON('mr_settings', G.settings);
    if (key === 'music') { Sfx.unlock(); Sfx.setMusic(val); }
    if (key === 'quality') { Render.resetScale(); Sprites.clearCache(); }
  }

  function toTitle() { UI.closeModal(); startTitle(); }

  function exitApp() {
    save();
    if (window.AndroidBridge && window.AndroidBridge.exitApp) window.AndroidBridge.exitApp();
    else toTitle();
  }

  G.boot = boot; G.newGame = newGame; G.onHQ = onHQ; G.onMapChanged = onMapChanged; G.applyBrand = applyBrand;
  G.save = save; G.load = load; G.undo = undo; G.setSpeed = setSpeed; G.setSetting = setSetting; G.toTitle = toTitle;
  G.exitApp = exitApp; G.setWalk = setWalk; G.endDay = endDay; G.checkMissions = checkMissions;
  return G;
})();

window.addEventListener('load', function () { Game.boot(); });

/* Mundo Renda - interface: HUD, barra de ferramentas, paleta, cartões, painéis, diálogos e assistente de novo projeto */
'use strict';

var UI = (function () {
  var $ = U.el, I = DATA.BY_ID, G = DATA.GOODS;
  var curCat = null, cardK = -1, modalType = null, dialogCb = null;

  function init() {
    // barra de ferramentas
    var tb = $('toolbar');
    DATA.CATS.forEach(function (c) {
      var b = document.createElement('button');
      b.className = 'tool'; b.dataset.cat = c.id;
      b.innerHTML = '<span class="ti">' + c.icon + '</span><span class="tl">' + c.name + '</span>';
      b.addEventListener('click', function () { Sfx.unlock(); Sfx.play('click'); setCategory(c.id); });
      tb.appendChild(b);
    });
    Array.prototype.forEach.call(document.querySelectorAll('#speeds button'), function (b) {
      b.addEventListener('click', function () { Sfx.play('click'); Game.setSpeed(Number(b.dataset.speed)); });
    });
    $('btn-menu').addEventListener('click', function () { Sfx.play('click'); openModal('menu'); });
    $('btn-project').addEventListener('click', function () { Sfx.play('click'); openModal('projeto'); });
    $('mission').addEventListener('click', function () { Sfx.play('click'); openModal('missoes'); });
    $('hint-close').addEventListener('click', function () { Sfx.play('click'); setTool(null); });
    $('z-in').addEventListener('click', function () { Render.zoomAt(1.25, innerWidth / 2, innerHeight / 2); });
    $('z-out').addEventListener('click', function () { Render.zoomAt(0.8, innerWidth / 2, innerHeight / 2); });
    $('modal-close').addEventListener('click', closeModal);
    $('modal').addEventListener('click', function (e) { if (e.target.id === 'modal') closeModal(); });
    $('dlg-cancel').addEventListener('click', function () { closeDialog(false); });
    $('dlg-ok').addEventListener('click', function () { closeDialog(true); });
    $('walk-exit').addEventListener('click', function () { Game.setWalk(false); });
    var mm = $('minimap');
    var miniMove = function (e) {
      var r = mm.getBoundingClientRect(), p = Render.miniToWorld(e.clientX - r.left, e.clientY - r.top);
      Render.cam.x = p.x; Render.cam.y = p.y; Render.clampCam();
    };
    mm.addEventListener('pointerdown', function (e) { e.preventDefault(); mm.setPointerCapture(e.pointerId); mm._drag = true; miniMove(e); });
    mm.addEventListener('pointermove', function (e) { if (mm._drag) miniMove(e); });
    mm.addEventListener('pointerup', function () { mm._drag = false; });
    Render.setMini(mm);
    initJoystick();

    $('t-new').addEventListener('click', function () { Sfx.unlock(); Sfx.play('click'); showWizard(); });
    $('t-continue').addEventListener('click', function () { Sfx.unlock(); Sfx.play('click'); var l = Store.list(); if (l.length) Game.load(l[0].id); });
    $('t-load').addEventListener('click', function () { Sfx.unlock(); Sfx.play('click'); openModal('carregar'); });
    $('t-help').addEventListener('click', function () { Sfx.unlock(); Sfx.play('click'); openModal('ajuda'); });
  }

  /* ---------------- Telas ---------------- */
  function showTitle() {
    $('title').classList.remove('hidden');
    $('wizard').classList.add('hidden');
    $('hud').classList.add('hidden');
    closeBuilding(); closeModal();
    var l = Store.list();
    $('t-continue').classList.toggle('hidden', !l.length);
    $('t-load').classList.toggle('hidden', !l.length);
    if (l.length) $('t-continue').innerHTML = '▶ Continuar <small>' + U.esc(l[0].emoji + ' ' + l[0].name) + '</small>';
  }
  function showHUD() {
    $('title').classList.add('hidden');
    $('wizard').classList.add('hidden');
    $('hud').classList.remove('hidden');
    setCategory('info');
    refreshHUD(true);
  }

  /* ---------------- Assistente de novo projeto ---------------- */
  var wz = null;
  function showWizard() {
    wz = { step: 0, name: '', emoji: DATA.EMOJIS[0], color: DATA.COLORS[3], branch: 'agro', branchName: '', preset: 'rio',
      mode: 'desafio', seed: Math.floor(Math.random() * 99999) };
    $('title').classList.add('hidden');
    $('wizard').classList.remove('hidden');
    renderWizard();
  }
  function renderWizard() {
    var el = $('wizard'), h = '';
    var prev = el.querySelector('.wz-body'), keep = prev && wz.lastStep === wz.step ? prev.scrollTop : 0;
    var steps = ['Seu projeto', 'Ramo principal', 'Seu mundo'];
    h += '<div class="wz-box"><div class="wz-steps">' + steps.map(function (s, n) {
      return '<span class="' + (n === wz.step ? 'on' : n < wz.step ? 'done' : '') + '">' + (n + 1) + '. ' + s + '</span>';
    }).join('') + '</div><div class="wz-body">';
    if (wz.step === 0) {
      h += '<label class="lbl">Nome do projeto</label>' +
        '<input id="wz-name" maxlength="28" placeholder="Ex.: Cooperativa Mãos que Criam" value="' + U.esc(wz.name) + '">' +
        '<label class="lbl">Símbolo</label><div class="grid-emoji">' + DATA.EMOJIS.map(function (e) {
          return '<button class="emo' + (e === wz.emoji ? ' on' : '') + '" data-emo="' + e + '">' + e + '</button>';
        }).join('') + '</div>' +
        '<label class="lbl">Cor do projeto (telhados e placas)</label><div class="grid-color">' + DATA.COLORS.map(function (c) {
          return '<button class="sw' + (c === wz.color ? ' on' : '') + '" data-col="' + c + '" style="background:' + c + '"></button>';
        }).join('') + '</div>' +
        '<div class="wz-preview" style="border-color:' + wz.color + '"><span>' + wz.emoji + '</span><b>' + U.esc(wz.name || 'Meu Projeto') + '</b></div>';
    } else if (wz.step === 1) {
      h += '<p class="muted">Escolha o foco do seu projeto. Construções do ramo produzem +25% e já começam liberadas. Você pode construir de tudo!</p><div class="grid-cards">' +
        DATA.BRANCHES.map(function (b) {
          return '<button class="pick' + (b.id === wz.branch ? ' on' : '') + '" data-br="' + b.id + '"><span class="pi">' + b.icon + '</span><b>' + b.name + '</b><small>' + b.desc + '</small></button>';
        }).join('') + '</div>';
      if (wz.branch === 'livre') h += '<label class="lbl">Nome do seu ramo</label><input id="wz-brname" maxlength="30" placeholder="Ex.: Economia Criativa" value="' + U.esc(wz.branchName) + '">';
    } else {
      h += '<label class="lbl">Paisagem</label><div class="grid-cards small">' + DATA.PRESETS.map(function (p) {
        return '<button class="pick' + (p.id === wz.preset ? ' on' : '') + '" data-pre="' + p.id + '"><span class="pi">' + p.icon + '</span><b>' + p.name + '</b><small>' + p.desc + '</small></button>';
      }).join('') + '</div>' +
        '<label class="lbl">Modo de jogo</label><div class="grid-cards small two">' +
        '<button class="pick' + (wz.mode === 'desafio' ? ' on' : '') + '" data-mode="desafio"><span class="pi">🎯</span><b>Desafio</b><small>Comece com ' + U.money(DATA.START_MONEY) + ', cuide do caixa e libere construções subindo de nível.</small></button>' +
        '<button class="pick' + (wz.mode === 'criativo' ? ' on' : '') + '" data-mode="criativo"><span class="pi">🎨</span><b>Criativo</b><small>Dinheiro infinito e tudo liberado. Monte o layout dos sonhos!</small></button></div>' +
        '<label class="lbl">Semente do mundo</label><div class="row"><input id="wz-seed" type="number" inputmode="numeric" value="' + wz.seed + '"><button class="btn ghost" id="wz-dice">🎲</button></div>';
    }
    h += '</div><div class="wz-foot"><button class="btn ghost" id="wz-back">' + (wz.step ? '← Voltar' : '✕ Cancelar') + '</button>' +
      '<button class="btn" id="wz-next">' + (wz.step < 2 ? 'Próximo →' : '🌍 Criar mundo') + '</button></div></div>';
    el.innerHTML = h;
    el.querySelector('.wz-body').scrollTop = keep;
    wz.lastStep = wz.step;

    var nm = $('wz-name');
    if (nm) nm.addEventListener('input', function () { wz.name = nm.value; var pv = el.querySelector('.wz-preview b'); if (pv) pv.textContent = wz.name || 'Meu Projeto'; });
    var bn = $('wz-brname');
    if (bn) bn.addEventListener('input', function () { wz.branchName = bn.value; });
    var sd = $('wz-seed');
    if (sd) sd.addEventListener('input', function () { wz.seed = Math.abs(parseInt(sd.value, 10) || 0); });
    if ($('wz-dice')) $('wz-dice').addEventListener('click', function () { wz.seed = Math.floor(Math.random() * 99999); renderWizard(); });
    bind(el, '[data-emo]', function (b) { wz.emoji = b.dataset.emo; renderWizard(); });
    bind(el, '[data-col]', function (b) { wz.color = b.dataset.col; renderWizard(); });
    bind(el, '[data-br]', function (b) {
      wz.branch = b.dataset.br; renderWizard();
      if (wz.branch === 'livre' && $('wz-brname')) $('wz-brname').scrollIntoView({ block: 'center' });
    });
    bind(el, '[data-pre]', function (b) { wz.preset = b.dataset.pre; renderWizard(); });
    bind(el, '[data-mode]', function (b) { wz.mode = b.dataset.mode; renderWizard(); });
    $('wz-back').addEventListener('click', function () { Sfx.play('click'); if (wz.step) { wz.step--; renderWizard(); } else showTitle(); });
    $('wz-next').addEventListener('click', function () {
      Sfx.play('click');
      if (wz.step === 0 && !wz.name.trim()) { wz.name = 'Projeto ' + ['Esperança', 'Raízes', 'Futuro', 'União', 'Semear'][Math.floor(Math.random() * 5)]; }
      if (wz.step < 2) { wz.step++; renderWizard(); return; }
      Game.newGame({ name: wz.name.trim(), emoji: wz.emoji, color: wz.color, branch: wz.branch,
        branchName: wz.branch === 'livre' ? (wz.branchName.trim() || 'Projeto Personalizado') : '', preset: wz.preset, mode: wz.mode, seed: wz.seed });
    });
  }
  function bind(root, sel, fn) {
    Array.prototype.forEach.call(root.querySelectorAll(sel), function (b) { b.addEventListener('click', function () { Sfx.play('click'); fn(b); }); });
  }

  /* ---------------- Ferramentas ---------------- */
  function setCategory(cat) {
    var s = Game.s;
    if (!s) return;
    if (cat === 'desfazer') { Game.undo(); return; }
    if (cat === 'passear') { Game.setWalk(true); return; }
    if (Game.walk) Game.setWalk(false);
    closeBuilding();
    if (cat === 'info') { curCat = 'info'; setTool(null); }
    else if (cat === 'demolir') { curCat = 'demolir'; setTool('demolir'); }
    else {
      if (curCat === cat && !$('palette').classList.contains('hidden')) { curCat = 'info'; setTool(null); }
      else { curCat = cat; renderPalette(cat); }
    }
    highlightToolbar();
  }
  function highlightToolbar() {
    Array.prototype.forEach.call(document.querySelectorAll('#toolbar .tool'), function (b) {
      b.classList.toggle('on', b.dataset.cat === curCat);
    });
  }
  function renderPalette(cat) {
    var s = Game.s, p = $('palette');
    var items = DATA.ITEMS.filter(function (it) { return it.cat === cat && it.id !== 'hq'; });
    p.innerHTML = items.map(function (it) {
      var lock = !World.unlocked(it);
      var cost = s.mode === 'criativo' ? 'Grátis' : (it.cost ? U.shortMoney(it.cost) : 'Grátis');
      return '<button class="item' + (lock ? ' locked' : '') + (Game.ui.tool === it.id ? ' on' : '') + '" data-id="' + it.id + '">' +
        '<span class="ii">' + it.icon + '</span><span class="in">' + it.name + '</span>' +
        '<span class="ic">' + (lock ? '🔒 Nível ' + it.lvl : cost) + '</span></button>';
    }).join('');
    p.classList.remove('hidden');
    p.scrollLeft = 0;
    bind(p, '.item', function (b) {
      var it = I[b.dataset.id];
      if (!World.unlocked(it)) { toast('🔒 ' + it.name + ' desbloqueia no nível ' + it.lvl + ' (' + DATA.LEVEL_NAMES[it.lvl - 1] + ')', 'bad'); return; }
      setTool(it.id);
    });
  }
  function itemInfo(it) {
    var parts = [];
    if (it.jobs) parts.push('👷' + it.jobs);
    if (it.res) parts.push('👥' + it.res);
    if (it.out) for (var g in it.out) parts.push(G[g].icon + it.out[g] + '/dia');
    if (it.inp) { var ins = []; for (var g2 in it.inp) ins.push(G[g2].icon + it.inp[g2]); parts.push('usa ' + ins.join(' ')); }
    if (it.income) parts.push('💵' + U.shortMoney(it.income) + '/dia');
    if (it.sell) parts.push('🛒' + it.sell.cap + '/dia' + (it.sell.food ? ' (alimentos)' : ''));
    if (it.store) parts.push('📦+' + it.store);
    if (it.beauty && it.kind === 'decor') parts.push('✨ beleza +' + it.beauty);
    if (!parts.length && it.desc) parts.push(it.desc);
    return parts.join(' · ');
  }
  function setTool(id) {
    var ui = Game.ui;
    ui.tool = id; ui.linePath = []; ui.hover = -1;
    if (id !== null) ui.selected = -1;
    if (ui.moving >= 0 && id !== 'move') ui.moving = -1;
    var h = $('hint');
    if (!id || id === 'info') {
      h.classList.add('hidden');
      $('palette').classList.add('hidden');
      curCat = 'info';
      highlightToolbar();
      return;
    }
    var txt, icon;
    if (id === 'demolir') { icon = '🧨'; txt = '<b>Demolir</b> Toque ou arraste. Devolve 50% do valor.'; $('palette').classList.add('hidden'); }
    else if (id === 'move') { icon = '✋'; txt = '<b>Mover</b> Toque no novo lugar.'; $('palette').classList.add('hidden'); }
    else {
      var it = I[id];
      icon = it.icon;
      var how = it.brush === 'line' ? 'Arraste para traçar.' : it.brush === 'paint' ? 'Toque ou arraste para pintar.' : 'Toque no mapa para construir.';
      txt = '<b>' + it.name + '</b> ' + how + ' <span class="muted">' + U.esc(itemInfo(it)) + '</span>';
      Array.prototype.forEach.call(document.querySelectorAll('#palette .item'), function (b) { b.classList.toggle('on', b.dataset.id === id); });
    }
    $('hint-icon').textContent = icon;
    $('hint-txt').innerHTML = txt;
    $('hint-extra').textContent = '';
    h.classList.remove('hidden');
  }
  function setHintExtra(t) { $('hint-extra').textContent = t; }

  /* ---------------- Cartão da construção ---------------- */
  function openBuilding(k) {
    cardK = k;
    Game.ui.selected = k;
    renderCard();
    $('card').classList.remove('hidden');
  }
  function closeBuilding(keepSel) {
    cardK = -1;
    $('card').classList.add('hidden');
    if (!keepSel && Game.ui) Game.ui.selected = -1;
  }
  function renderCard() {
    var k = cardK, w = World.w, o = w.obj[k], s = Game.s;
    if (k < 0 || !o) { closeBuilding(); return; }
    var it = I[o.id], st = Sim.status(k) || {}, rep = Sim.report();
    var status = '<span class="st ok">✅ Funcionando</span>';
    if (st.alert === 'road') status = '<span class="st bad">🛣️ Sem estrada até o Centro Comunitário</span>';
    else if (st.alert === 'staff0') status = '<span class="st bad">👷 Sem trabalhadores: construa casas</span>';
    else if (st.alert === 'staff') status = '<span class="st warn">👷 Faltam trabalhadores</span>';
    else if (st.alert === 'input') status = '<span class="st warn">📦 Faltam insumos</span>';
    var rows = [];
    if (it.jobs) rows.push(['👷 Empregos', Math.round(it.jobs * o.lv * (st.staff || 0)) + ' de ' + it.jobs * o.lv]);
    if (it.res) rows.push(['👥 Moradores', it.res * o.lv + (st.well !== undefined ? ' · bem-estar ' + Math.round(st.well) + '%' : '')]);
    var outs = [];
    if (st.out) for (var g in st.out) outs.push(fmtQ(st.out[g]) + ' ' + G[g].icon + ' ' + G[g].name);
    if (outs.length) rows.push(['📦 Produção/dia', outs.join('<br>')]);
    else if (it.out) { var po = []; for (var g1 in it.out) po.push(it.out[g1] * o.lv + ' ' + G[g1].icon); rows.push(['📦 Produção máx./dia', po.join(' ')]); }
    if (it.inp) { var ins = []; for (var g2 in it.inp) ins.push(fmtQ(st.inp ? st.inp[g2] : it.inp[g2] * o.lv) + ' ' + G[g2].icon); rows.push(['🔁 Insumos/dia', ins.join(' ')]); }
    if (it.income) rows.push(['💵 Renda/dia', U.money(st.inc || 0)]);
    if (it.sell) rows.push(['🛒 Vendas/dia', fmtQ(st.sold || 0) + ' de ' + fmtQ(st.cap !== undefined ? st.cap : it.sell.cap * o.lv) + (it.sell.food ? ' (só alimentos)' : '')]);
    if (it.store) rows.push(['🏬 Estoque', '+' + it.store * o.lv]);
    if (it.eff) rows.push(['✨ Efeito', it.desc]);
    if (it.upkeep) rows.push(['🔧 Manutenção', U.money(it.upkeep * o.lv) + '/dia']);
    if (o.id === 'hq' && rep) rows.push(['🏛️ Projeto', U.esc(s.project.name)]);
    var bonus = (st.bonus && st.bonus.length) ? '<div class="bonus">' + st.bonus.map(function (b) { return '<span>' + b + '</span>'; }).join('') + '</div>' : '';
    var stars = '<span class="stars">' + '★★★'.substr(0, o.lv) + '<i>' + '★★★'.substr(o.lv) + '</i></span>';
    var upCost = s.mode === 'criativo' ? 0 : World.upgradeCost(it, o.lv);
    var refund = Math.floor(World.invested(it, o.lv) * 0.5);
    var acts = '';
    if (o.lv < 3 && it.kind !== 'decor') acts += '<button class="btn" data-act="up">⬆️ Melhorar <small>' + (upCost ? U.shortMoney(upCost) : 'grátis') + '</small></button>';
    if (o.id !== 'hq') acts += '<button class="btn ghost" data-act="move">✋ Mover</button><button class="btn danger" data-act="del">🧨 Demolir' + (s.mode === 'criativo' ? '' : ' <small>+' + U.shortMoney(refund) + '</small>') + '</button>';
    else acts += '<button class="btn ghost" data-act="move">✋ Mover</button>';
    $('card').innerHTML = '<div class="card-head"><span class="card-icon">' + it.icon + '</span><div class="card-t"><h3>' + it.name + ' ' + stars + '</h3>' + status + '</div>' +
      '<button class="round" id="card-close">✕</button></div>' +
      '<div class="card-body"><table>' + rows.map(function (r) { return '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td></tr>'; }).join('') + '</table>' + bonus +
      (it.eff ? '' : '<p class="desc">' + it.desc + '</p>') + '</div>' +
      '<div class="card-actions">' + acts + '</div>';
    $('card-close').addEventListener('click', function () { Sfx.play('click'); closeBuilding(); });
    bind($('card'), '[data-act]', function (b) {
      var act = b.dataset.act;
      if (act === 'up') {
        var r = World.upgrade(k);
        if (r.ok) { Sfx.play('level'); if (r.cost) Render.addFloat(k, '-' + U.shortMoney(r.cost), '#ffd27a'); Game.onMapChanged(); renderCard(); toast('⬆️ ' + it.name + ' agora é nível ' + w.obj[k].lv + '!', 'good'); }
        else { toast(r.reason, 'bad'); Sfx.play('error'); }
      } else if (act === 'move') {
        Game.ui.moving = k; closeBuilding(true); setTool('move'); Game.ui.moving = k;
      } else if (act === 'del') {
        confirmDlg('Demolir ' + it.name + '?', 'Você recebe de volta ' + U.money(s.mode === 'criativo' ? 0 : refund) + '. Dá para desfazer com ↩️.', 'Demolir', function () {
          var r2 = World.apply('demolir', k);
          if (r2.ok) { Sfx.play('demolish'); closeBuilding(); Game.onMapChanged(); }
        });
      }
    });
  }
  function fmtQ(q) { q = q || 0; return q >= 10 ? String(Math.round(q)) : (Math.round(q * 10) / 10).toString().replace('.', ','); }

  /* ---------------- HUD ---------------- */
  var lastHud = 0;
  function refreshHUD(force) {
    var s = Game.s;
    if (!s) return;
    var now = performance.now();
    if (!force && now - lastHud < 250) return;
    lastHud = now;
    var r = Sim.report();
    $('v-money').textContent = s.mode === 'criativo' ? '∞' : U.shortMoney(s.money);
    $('v-money').parentNode.classList.toggle('neg', s.mode !== 'criativo' && s.money < 0);
    $('v-jobs').textContent = (r ? r.employed : 0) + '/' + (r ? r.c.jobs : 0);
    $('v-jobs').parentNode.classList.toggle('warn', !!(r && r.c.jobs > 0 && r.employed < r.c.jobs * 0.7));
    $('v-pop').textContent = U.num(s.pop);
    $('v-well').textContent = Math.round(s.stats.well) + '%';
    $('v-well').parentNode.firstChild.textContent = s.stats.well >= 70 ? '😄' : s.stats.well >= 45 ? '🙂' : '😟';
    var hh = Math.floor(s.t * 24), mm = Math.floor((s.t * 24 - hh) * 6) * 10;
    $('v-date').textContent = 'Dia ' + s.day + ' · ' + (hh < 10 ? '0' : '') + hh + ':' + (mm < 10 ? '0' : '') + mm;
    $('proj-emoji').textContent = s.project.emoji;
    $('proj-name').textContent = s.project.name;
    $('proj-level').textContent = 'Nível ' + s.level + ' · ' + DATA.LEVEL_NAMES[s.level - 1];
    var lo = DATA.LEVELS[s.level - 1], hi = DATA.LEVELS[s.level] || lo;
    $('lvfill').style.width = (hi > lo ? U.clamp((s.pts - lo) / (hi - lo), 0, 1) * 100 : 100) + '%';
    Array.prototype.forEach.call(document.querySelectorAll('#speeds button'), function (b) { b.classList.toggle('on', Number(b.dataset.speed) === s.speed); });
    var m = DATA.MISSIONS[s.mission];
    if (m) {
      var pv = Sim.missionStat(s, m.stat);
      $('m-title').textContent = m.title;
      $('m-prog').textContent = m.desc + ' (' + U.num(Math.min(pv, m.goal)) + '/' + U.num(m.goal) + ')';
      $('mission').classList.remove('hidden');
    } else $('mission').classList.add('hidden');
    $('events').innerHTML = (s.events || []).map(function (e) {
      var ev = DATA.EVENTS.filter(function (x) { return x.id === e.id; })[0];
      return ev ? '<span class="evb" title="' + U.esc(ev.text) + '">' + ev.icon + ' ' + e.days + 'd</span>' : '';
    }).join('') + (s.loan ? '<span class="evb">💳 ' + s.loan.left + 'd</span>' : '');
    if (cardK >= 0 && !$('card').classList.contains('hidden') && force) renderCard();
    if (modalType === 'projeto' && force) renderModal();
  }

  /* ---------------- Painéis ---------------- */
  function openModal(type) {
    modalType = type;
    renderModal();
    $('modal').classList.remove('hidden');
  }
  function closeModal() { modalType = null; $('modal-body')._type = null; $('modal').classList.add('hidden'); }

  function renderModal() {
    var s = Game.s, title = '', body = '';
    if (modalType === 'projeto' && s) {
      var r = Sim.report() || { c: { jobs: 0, store: 0 }, employed: 0, labor: 0 };
      var br = World.branchOf(s);
      title = s.project.emoji + ' ' + U.esc(s.project.name);
      var st = s.stats;
      body += '<p class="muted">' + (s.project.branch === 'livre' ? '✨ ' + U.esc(s.project.branchName) : br.icon + ' ' + br.name) + ' · ' + (s.mode === 'criativo' ? '🎨 Criativo' : '🎯 Desafio') + ' · Nível ' + s.level + ' (' + DATA.LEVEL_NAMES[s.level - 1] + ') · ' + U.num(s.pts) + ' pts de impacto</p>';
      body += '<div class="stats">' +
        stat('💰 Caixa', s.mode === 'criativo' ? '∞' : U.money(s.money), s.money < 0 ? 'bad' : '') +
        stat('💵 Faturamento ontem', U.money(st.revenue)) +
        stat('🤝 Salários pagos ontem', U.money(st.wages), 'gold') +
        stat('🔧 Manutenção ontem', U.money(st.upkeep)) +
        stat('📈 Lucro ontem', U.money(st.profit), st.profit >= 0 ? 'good' : 'bad') +
        stat('🌟 Renda distribuída (total)', U.money(st.totalWages), 'gold') +
        stat('👷 Empregos', r.employed + ' de ' + r.c.jobs + ' vagas') +
        stat('🙋 Pessoas disponíveis', r.labor + ' (' + Math.round((r.part || 0.55) * 100) + '% dos moradores)') +
        stat('👥 População', U.num(s.pop)) +
        stat('😊 Bem-estar', Math.round(st.well) + '%') + '</div>';
      body += '<h4>Últimos dias</h4><canvas id="chart" class="chart"></canvas><div class="legend"><span class="lg1">Faturamento</span><span class="lg2">Salários</span><span class="lg3">Lucro</span></div>';
      var stock = s.stock, tot = Sim.stockTotal(stock);
      body += '<h4>Estoque <small class="muted">' + Math.round(tot) + ' / ' + r.c.store + '</small></h4><div class="bar"><i style="width:' + (r.c.store ? Math.min(100, tot / r.c.store * 100) : 0) + '%"></i></div>';
      var gk = Object.keys(stock).filter(function (g) { return stock[g] >= 0.5; });
      body += gk.length ? '<div class="goods">' + gk.map(function (g) { return '<span>' + G[g].icon + ' ' + G[g].name + ' <b>' + Math.floor(stock[g]) + '</b></span>'; }).join('') + '</div>' : '<p class="muted">Estoque vazio.</p>';
      if (st.lost > 0.5) body += '<p class="warnbox">⚠️ Ontem ' + Math.round(st.lost) + ' produtos foram perdidos por falta de espaço. Construa Armazéns ou mais pontos de venda.</p>';
      var sold = st.sold || {}, sk = Object.keys(sold).filter(function (g) { return sold[g] >= 0.5; });
      if (sk.length) body += '<h4>Vendido ontem</h4><div class="goods">' + sk.map(function (g) { return '<span>' + G[g].icon + ' <b>' + Math.round(sold[g]) + '</b></span>'; }).join('') + '</div>';
      if (s.mode !== 'criativo') {
        body += '<h4>💳 Microcrédito</h4>' + (s.loan ? '<p>Restam <b>' + s.loan.left + ' dias</b> de parcelas de ' + U.money(s.loan.daily) + '.</p>' :
          '<p class="muted">Receba ' + U.money(3000) + ' agora e pague ' + U.money(40) + ' por dia durante 90 dias.</p><button class="btn" id="btn-loan">Pegar microcrédito</button>');
      }
      body += '<h4>Personalizar</h4><div class="row wrap"><button class="btn ghost" id="btn-edit">✏️ Nome, símbolo e cor</button><button class="btn ghost" id="btn-share">📤 Compartilhar resultados</button></div>';
    } else if (modalType === 'missoes' && s) {
      title = '🎯 Missões';
      body = '<div class="missions">' + DATA.MISSIONS.map(function (m, n) {
        var cls = n < s.mission ? 'done' : n === s.mission ? 'cur' : 'next';
        var pv = Sim.missionStat(s, m.stat), pct = Math.min(1, pv / m.goal) * 100;
        return '<div class="mis ' + cls + '"><div class="mh"><b>' + (n < s.mission ? '✅ ' : n === s.mission ? '🎯 ' : '⬜ ') + m.title + '</b><span>' + (m.reward ? '+' + U.shortMoney(m.reward) : '') + '</span></div>' +
          '<small>' + m.desc + '</small>' + (n === s.mission ? '<div class="bar"><i style="width:' + pct + '%"></i></div><small class="hint">💡 ' + m.hint + '</small>' : '') + '</div>';
      }).join('') + '</div>';
    } else if (modalType === 'menu') {
      var set = Game.settings;
      title = '☰ Menu';
      body = '<div class="menu-list">' +
        '<button class="btn" id="m-save">💾 Salvar agora</button>' +
        '<button class="btn ghost" id="m-load">📂 Meus projetos</button>' +
        '<button class="btn ghost" id="m-help">❔ Como jogar</button>' +
        '<button class="btn ghost" id="m-title">🏠 Voltar ao início</button></div>' +
        '<h4>Configurações</h4><div class="toggles">' +
        tog('sound', '🔊 Efeitos sonoros', set.sound) + tog('music', '🎵 Música ambiente', set.music) +
        (Store.native ? tog('vibrate', '📳 Vibração', set.vibrate) : '') +
        tog('daynight', '🌙 Ciclo de dia e noite', set.daynight) + tog('alerts', '⚠️ Alertas nas construções', set.alerts) +
        tog('grid', '▦ Grade ao construir', set.grid) + tog('quality', '✨ Gráficos em alta qualidade', set.quality === 'alta') + '</div>' +
        '<p class="muted small">Mundo Renda v1.0 · jogo offline. Seu progresso é salvo automaticamente.</p>';
    } else if (modalType === 'carregar') {
      title = '📂 Meus projetos';
      var l = Store.list();
      body = l.length ? '<div class="saves">' + l.map(function (e) {
        return '<div class="save" style="border-color:' + e.color + '"><span class="se">' + e.emoji + '</span><div class="sd"><b>' + U.esc(e.name) + '</b><small>Dia ' + e.day + ' · Nível ' + e.level + ' · ' + (e.mode === 'criativo' ? 'Criativo' : U.shortMoney(e.money)) + '</small></div>' +
          '<button class="btn" data-load="' + e.id + '">Abrir</button><button class="round danger" data-del="' + e.id + '">🗑</button></div>';
      }).join('') + '</div>' : '<p class="muted">Nenhum projeto salvo ainda.</p>';
    } else if (modalType === 'ajuda') {
      title = '❔ Como jogar';
      body = helpHTML();
    } else if (modalType === 'editar' && s) {
      title = '✏️ Personalizar projeto';
      body = '<label class="lbl">Nome</label><input id="ed-name" maxlength="28" value="' + U.esc(s.project.name) + '">' +
        '<label class="lbl">Símbolo</label><div class="grid-emoji">' + DATA.EMOJIS.map(function (e) { return '<button class="emo' + (e === s.project.emoji ? ' on' : '') + '" data-emo="' + e + '">' + e + '</button>'; }).join('') + '</div>' +
        '<label class="lbl">Cor</label><div class="grid-color">' + DATA.COLORS.map(function (c) { return '<button class="sw' + (c === s.project.color ? ' on' : '') + '" data-col="' + c + '" style="background:' + c + '"></button>'; }).join('') + '</div>' +
        '<button class="btn" id="ed-ok">Salvar</button>';
    }
    var mb = $('modal-body'), keep = mb._type === modalType ? mb.scrollTop : 0;
    $('modal-title').innerHTML = title;
    mb.innerHTML = body;
    mb.scrollTop = keep;
    mb._type = modalType;
    wireModal();
  }
  function stat(l, v, cls) { return '<div class="stat ' + (cls || '') + '"><small>' + l + '</small><b>' + v + '</b></div>'; }
  function tog(key, label, on) { return '<label class="tog"><span>' + label + '</span><input type="checkbox" data-set="' + key + '"' + (on ? ' checked' : '') + '><i></i></label>'; }

  function wireModal() {
    var s = Game.s, body = $('modal-body');
    if ($('chart')) drawChart($('chart'));
    if ($('btn-loan')) $('btn-loan').addEventListener('click', function () { if (Sim.takeLoan(s)) { Sfx.play('coin'); toast('💳 Microcrédito de R$ 3.000 liberado!', 'good'); renderModal(); refreshHUD(true); } });
    if ($('btn-edit')) $('btn-edit').addEventListener('click', function () { openModal('editar'); });
    if ($('btn-share')) $('btn-share').addEventListener('click', share);
    if ($('m-save')) $('m-save').addEventListener('click', function () { Game.save(true); });
    if ($('m-load')) $('m-load').addEventListener('click', function () { Game.save(); openModal('carregar'); });
    if ($('m-help')) $('m-help').addEventListener('click', function () { openModal('ajuda'); });
    if ($('m-title')) $('m-title').addEventListener('click', function () { Game.save(); Game.toTitle(); });
    Array.prototype.forEach.call(body.querySelectorAll('[data-set]'), function (cb) {
      cb.addEventListener('change', function () { Game.setSetting(cb.dataset.set, cb.dataset.set === 'quality' ? (cb.checked ? 'alta' : 'baixa') : cb.checked); });
    });
    bind(body, '[data-load]', function (b) { closeModal(); Game.load(b.dataset.load); });
    bind(body, '[data-del]', function (b) {
      confirmDlg('Apagar projeto?', 'Isso não pode ser desfeito.', 'Apagar', function () {
        if (Game.s && Game.s.id === b.dataset.del) { toast('Esse projeto está aberto agora.', 'bad'); return; }
        Store.deleteGame(b.dataset.del); renderModal(); if (!Game.s) showTitle();
      });
    });
    if (modalType === 'editar') {
      var tmp = { emoji: s.project.emoji, color: s.project.color };
      bind(body, '[data-emo]', function (b) { tmp.emoji = b.dataset.emo; Array.prototype.forEach.call(body.querySelectorAll('[data-emo]'), function (x) { x.classList.toggle('on', x === b); }); });
      bind(body, '[data-col]', function (b) { tmp.color = b.dataset.col; Array.prototype.forEach.call(body.querySelectorAll('[data-col]'), function (x) { x.classList.toggle('on', x === b); }); });
      $('ed-ok').addEventListener('click', function () {
        var nm = $('ed-name').value.trim();
        if (nm) s.project.name = nm;
        s.project.emoji = tmp.emoji; s.project.color = tmp.color;
        Game.applyBrand(); World.touch(); refreshHUD(true); closeModal(); toast('✏️ Projeto atualizado!', 'good');
      });
    }
  }

  function drawChart(cv) {
    var s = Game.s, hst = s.history.slice(-30);
    var wd = cv.clientWidth || 300, ht = cv.clientHeight || 140, d = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = wd * d; cv.height = ht * d;
    var g = cv.getContext('2d'); g.scale(d, d);
    g.fillStyle = 'rgba(255,255,255,0.04)'; g.fillRect(0, 0, wd, ht);
    if (hst.length < 2) { g.fillStyle = '#9fb8ab'; g.font = '12px sans-serif'; g.textAlign = 'center'; g.fillText('Os dados aparecem depois de alguns dias.', wd / 2, ht / 2); return; }
    var max = 1, min = 0;
    hst.forEach(function (h) { max = Math.max(max, h.rev, h.wag); min = Math.min(min, h.pro); });
    var pad = 6, sy = (ht - pad * 2) / (max - min), y0 = ht - pad + min * sy, bw = (wd - pad * 2) / hst.length;
    g.strokeStyle = 'rgba(255,255,255,0.2)'; g.beginPath(); g.moveTo(0, y0); g.lineTo(wd, y0); g.stroke();
    hst.forEach(function (h, n) { g.fillStyle = 'rgba(60,207,122,0.55)'; g.fillRect(pad + n * bw + 1, y0 - h.rev * sy, Math.max(1, bw - 2), h.rev * sy); });
    function line(key, col) {
      g.strokeStyle = col; g.lineWidth = 2; g.beginPath();
      hst.forEach(function (h, n) { var x = pad + n * bw + bw / 2, y = y0 - h[key] * sy; if (n) g.lineTo(x, y); else g.moveTo(x, y); });
      g.stroke();
    }
    line('wag', '#ffc94a'); line('pro', '#6ab8ff');
  }

  function share() {
    var s = Game.s, st = s.stats;
    var txt = s.project.emoji + ' ' + s.project.name + ' — Mundo Renda\n' +
      'Dia ' + s.day + ' · Nível ' + s.level + ' (' + DATA.LEVEL_NAMES[s.level - 1] + ')\n' +
      '👷 ' + (Sim.report() ? Sim.report().employed : 0) + ' pessoas trabalhando\n' +
      '🤝 ' + U.money(st.totalWages) + ' de renda distribuída\n' +
      '😊 Bem-estar ' + Math.round(st.well) + '%';
    try {
      if (window.AndroidBridge && window.AndroidBridge.share) { window.AndroidBridge.share(txt); return; }
      if (navigator.share) { navigator.share({ text: txt }); return; }
    } catch (e) { /* ignora */ }
    toast('Resumo copiado para mostrar a quem quiser!', 'good');
    try { navigator.clipboard.writeText(txt); } catch (e2) { /* ignora */ }
  }

  function helpHTML() {
    return '<div class="help">' +
      '<h4>🎯 Objetivo</h4><p>Criar um projeto de geração de trabalho e renda do seu jeito: gerar empregos, distribuir renda para a comunidade e manter as pessoas felizes, construindo livremente num mundo aberto.</p>' +
      '<h4>🖐️ Controles</h4><ul><li><b>Mover o mapa:</b> arraste com um dedo (modo Selecionar) ou com dois dedos.</li><li><b>Zoom:</b> pinça com dois dedos ou botões ＋/－.</li>' +
      '<li><b>Construir:</b> escolha uma categoria na barra de baixo, toque num item e depois no mapa.</li><li><b>Estradas:</b> arraste o dedo para traçar. Sobre a água viram pontes.</li>' +
      '<li><b>Árvores, flores e terreno:</b> arraste para pintar.</li><li><b>Detalhes:</b> no modo 👆 Selecionar, toque numa construção para melhorar, mover ou demolir.</li>' +
      '<li><b>↩️ Desfazer</b> devolve o dinheiro. <b>🚶 Passear</b> deixa você caminhar pela comunidade.</li><li>Use o minimapa para ir rápido a qualquer lugar.</li></ul>' +
      '<h4>⚙️ Como funciona</h4><ul><li>Tudo precisa estar <b>ao lado de uma estrada ligada ao Centro Comunitário</b>.</li>' +
      '<li><b>Casas</b> trazem moradores; parte deles trabalha (<b>creches</b> aumentam essa parte).</li>' +
      '<li><b>Produção</b> gera produtos que vão para o estoque. <b>Beneficiamento</b> (cozinha, padaria, triagem, doces) transforma produtos em itens mais valiosos.</li>' +
      '<li><b>Pontos de venda</b> (feira, loja, entregas) transformam estoque em dinheiro. O Centro também vende um pouco.</li>' +
      '<li>Cada dia: <b>lucro = vendas + rendas − salários − manutenção</b>. Todo salário pago é <b>renda distribuída</b> para a comunidade.</li>' +
      '<li><b>Bem-estar</b> sobe com decoração perto das casas, emprego e serviços (saúde, escola, creche). Ele melhora os preços e atrai moradores.</li>' +
      '<li>Empregos e vendas geram <b>pontos de impacto</b>, que sobem seu nível e liberam novas construções.</li></ul>' +
      '<h4>💡 Dicas</h4><ul>' + DATA.TIPS.map(function (t) { return '<li>' + t + '</li>'; }).join('') + '</ul></div>';
  }

  /* ---------------- Diálogos e avisos ---------------- */
  function confirmDlg(title, text, ok, cb) {
    $('dlg-title').textContent = title;
    $('dlg-text').textContent = text;
    $('dlg-ok').textContent = ok || 'OK';
    dialogCb = cb;
    $('dialog').classList.remove('hidden');
  }
  function closeDialog(yes) {
    $('dialog').classList.add('hidden');
    var cb = dialogCb; dialogCb = null;
    if (yes && cb) cb();
  }
  function toast(msg, type, ms) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.innerHTML = msg;
    var box = $('toasts');
    box.appendChild(t);
    while (box.children.length > 2) box.removeChild(box.firstChild);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 400); }, ms || 2600);
  }

  // botão "voltar" do Android: fecha a camada de cima; retorna true se tratou
  function back() {
    if (!$('dialog').classList.contains('hidden')) { closeDialog(false); return true; }
    if (!$('modal').classList.contains('hidden')) { closeModal(); return true; }
    if (!$('wizard').classList.contains('hidden')) { if (wz && wz.step) { wz.step--; renderWizard(); } else showTitle(); return true; }
    if (Game.walk) { Game.setWalk(false); return true; }
    if (!$('card').classList.contains('hidden')) { closeBuilding(); return true; }
    if (Game.ui && (Game.ui.tool || Game.ui.moving >= 0)) { Game.ui.moving = -1; setTool(null); return true; }
    if (Game.s) { confirmDlg('Sair do jogo?', 'Seu projeto será salvo.', 'Sair', function () { Game.save(); Game.exitApp(); }); return true; }
    confirmDlg('Sair do jogo?', '', 'Sair', function () { Game.exitApp(); });
    return true;
  }

  /* ---------------- Passeio ---------------- */
  function initJoystick() {
    var joy = $('joy'), knob = $('joy-knob'), active = null;
    function upd(e) {
      var r = joy.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      var dx = e.clientX - cx, dy = e.clientY - cy, m = Math.sqrt(dx * dx + dy * dy), max = r.width / 2 - 10;
      if (m > max) { dx = dx / m * max; dy = dy / m * max; }
      knob.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
      Game.walkVec.x = dx / max; Game.walkVec.y = dy / max;
    }
    joy.addEventListener('pointerdown', function (e) { e.preventDefault(); active = e.pointerId; joy.setPointerCapture(e.pointerId); upd(e); });
    joy.addEventListener('pointermove', function (e) { if (active === e.pointerId) upd(e); });
    var end = function () { active = null; knob.style.transform = ''; Game.walkVec.x = 0; Game.walkVec.y = 0; };
    joy.addEventListener('pointerup', end); joy.addEventListener('pointercancel', end);
  }
  function showWalk(on) {
    $('walk').classList.toggle('hidden', !on);
    $('bottom').classList.toggle('hidden', on);
    $('side').classList.toggle('hidden', on);
    $('mission').classList.toggle('dim', on);
    if (on) { setTool(null); closeBuilding(); }
  }
  function walkInfo(html) { var el = $('walk-info'); if (el._h !== html) { el._h = html; el.innerHTML = html; el.classList.toggle('hidden', !html); } }

  return {
    init: init, showTitle: showTitle, showHUD: showHUD, setCategory: setCategory, setTool: setTool, setHintExtra: setHintExtra,
    openBuilding: openBuilding, closeBuilding: closeBuilding, renderCard: renderCard, refreshHUD: refreshHUD, openModal: openModal,
    closeModal: closeModal, toast: toast, confirm: confirmDlg, back: back, showWalk: showWalk, walkInfo: walkInfo,
    refreshPalette: function () { if (curCat && curCat !== 'info' && curCat !== 'demolir' && !$('palette').classList.contains('hidden')) renderPalette(curCat); },
    cardOpen: function () { return cardK; }
  };
})();

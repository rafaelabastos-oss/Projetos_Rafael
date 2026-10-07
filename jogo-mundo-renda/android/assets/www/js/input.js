/* Mundo Renda - toque e mouse: mover/zoom do mapa, tocar para construir, arrastar para estradas e pincéis */
'use strict';

var Input = (function () {
  var I = DATA.BY_ID, w = World.w;
  var canvas, pointers = {}, gesture = null;

  function init(cv) {
    canvas = cv;
    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointermove', onMove);
    canvas.addEventListener('pointerup', onUp);
    canvas.addEventListener('pointercancel', onCancel);
    canvas.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse' && !pointers[e.pointerId]) { Game.ui.hover = -1; } });
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault();
      Render.zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
    }, { passive: false });
    canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    window.addEventListener('keydown', onKey);
  }

  function brushMode() {
    var ui = Game.ui;
    if (!Game.s || Game.walk || ui.moving >= 0) return null;
    if (ui.tool === 'demolir') return 'paint';
    var it = I[ui.tool];
    if (!it) return null;
    return it.brush || null;
  }

  function count() { return Object.keys(pointers).length; }

  function onDown(e) {
    e.preventDefault();
    Sfx.unlock();
    try { canvas.setPointerCapture(e.pointerId); } catch (er) { /* ignora */ }
    pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
    var n = count();
    if (e.pointerType === 'mouse' && e.button !== 0) {
      gesture = { type: 'pan', lx: e.clientX, ly: e.clientY, id: e.pointerId };
      return;
    }
    if (n === 1) {
      var k = Render.screenToTile(e.clientX, e.clientY);
      var mode = brushMode();
      gesture = { type: 'pending', sx: e.clientX, sy: e.clientY, lx: e.clientX, ly: e.clientY, t: performance.now(), k: k, id: e.pointerId };
      if (mode === 'paint') {
        gesture.type = 'paint'; gesture.last = k; gesture.spent = false;
        World.begin('paint');
        paintAt(k);
      } else if (mode === 'line') {
        gesture.type = 'line'; gesture.start = k;
        updateLine(k);
      } else {
        updateHover(k);
      }
    } else if (n === 2) {
      if (gesture && (gesture.type === 'paint' || gesture.type === 'stopped')) {
        var a = World.commit();
        if (a && performance.now() - gesture.t < 300) Game.undo(true);
        else if (a) Game.onMapChanged();
      }
      Game.ui.linePath = [];
      UI.setHintExtra('');
      var ps = pts();
      gesture = { type: 'pinch', d: dist(ps), mx: (ps[0].x + ps[1].x) / 2, my: (ps[0].y + ps[1].y) / 2 };
    }
  }

  function pts() { var a = []; for (var id in pointers) a.push(pointers[id]); return a; }
  function dist(ps) { var dx = ps[0].x - ps[1].x, dy = ps[0].y - ps[1].y; return Math.sqrt(dx * dx + dy * dy) || 1; }

  function onMove(e) {
    var p = pointers[e.pointerId];
    if (!p) {
      if (e.pointerType === 'mouse' && Game.s && !Game.walk) updateHover(Render.screenToTile(e.clientX, e.clientY));
      return;
    }
    p.x = e.clientX; p.y = e.clientY;
    if (!gesture) return;
    if (gesture.type === 'pinch') {
      var ps = pts();
      if (ps.length < 2) return;
      var d = dist(ps), mx = (ps[0].x + ps[1].x) / 2, my = (ps[0].y + ps[1].y) / 2;
      Render.zoomAt(d / gesture.d, mx, my);
      Render.pan(mx - gesture.mx, my - gesture.my);
      gesture.d = d; gesture.mx = mx; gesture.my = my;
      return;
    }
    if (gesture.id !== e.pointerId) return;
    if (gesture.type === 'pending') {
      var dx = e.clientX - gesture.sx, dy = e.clientY - gesture.sy;
      if (dx * dx + dy * dy > 100) { gesture.type = 'pan'; }
      else return;
    }
    if (gesture.type === 'pan') {
      if (!Game.walk) Render.pan(e.clientX - gesture.lx, e.clientY - gesture.ly);
      gesture.lx = e.clientX; gesture.ly = e.clientY;
      return;
    }
    var k = Render.screenToTile(e.clientX, e.clientY);
    if (gesture.type === 'paint') {
      if (k !== gesture.last && k >= 0) {
        var path = gesture.last >= 0 ? stepPath(gesture.last, k) : [k];
        for (var n = 0; n < path.length; n++) if (!paintAt(path[n])) break;
        gesture.last = k;
      }
      Game.ui.hover = k;
    } else if (gesture.type === 'line') {
      updateLine(k);
    }
  }

  function onUp(e) {
    var had = pointers[e.pointerId];
    delete pointers[e.pointerId];
    if (!had || !gesture) return;
    if (gesture.type === 'pinch') {
      var ids = Object.keys(pointers);
      gesture = ids.length === 1 ? { type: 'pan', lx: pointers[ids[0]].x, ly: pointers[ids[0]].y, id: Number(ids[0]) } : null;
      return;
    }
    if (gesture.id !== e.pointerId) return;
    if (gesture.type === 'pending') {
      tap(Render.screenToTile(e.clientX, e.clientY));
    } else if (gesture.type === 'paint' || gesture.type === 'stopped') {
      var a = World.commit();
      if (a) { Sfx.play('place'); Game.onMapChanged(); }
    } else if (gesture.type === 'line') {
      commitLine();
    }
    gesture = null;
  }

  function onCancel(e) {
    delete pointers[e.pointerId];
    if (gesture && (gesture.type === 'paint' || gesture.type === 'stopped')) { var a = World.commit(); if (a) Game.onMapChanged(); }
    Game.ui.linePath = [];
    gesture = null;
  }

  // ladrilhos entre dois pontos (para o pincel não pular casas)
  function stepPath(a, b) {
    var ai = World.iOf(a), aj = World.jOf(a), bi = World.iOf(b), bj = World.jOf(b);
    var n = Math.max(Math.abs(bi - ai), Math.abs(bj - aj)), out = [];
    for (var s = 1; s <= n; s++) {
      var i = Math.round(ai + (bi - ai) * s / n), j = Math.round(aj + (bj - aj) * s / n);
      out.push(World.idx(i, j));
    }
    return out;
  }

  function paintAt(k) {
    if (k < 0) return true;
    var tool = Game.ui.tool;
    var r = World.apply(tool, k);
    if (r.ok) { gesture.spent = true; if (r.cost && Game.settings.sound) Sfx.play('tick'); return true; }
    if (r.money) { UI.toast('💸 Dinheiro insuficiente', 'bad'); Sfx.play('error'); gesture.type = 'stopped'; return false; }
    return true;
  }

  function updateLine(k) {
    if (k < 0 || gesture.start < 0) { Game.ui.linePath = []; return; }
    var path = World.linePath(gesture.start, k), tool = Game.ui.tool, total = 0;
    Game.ui.linePath = path.map(function (kk) {
      var ev = World.evaluate(tool, kk);
      if (ev.ok) total += ev.cost;
      return { k: kk, ok: ev.ok };
    });
    UI.setHintExtra(Game.s.mode === 'criativo' ? path.length + ' trechos' : path.length + ' trechos · ' + U.money(total));
  }

  function commitLine() {
    var path = Game.ui.linePath || [], tool = Game.ui.tool, placed = 0, broke = false;
    Game.ui.linePath = [];
    UI.setHintExtra('');
    if (!path.length) return;
    World.begin('road');
    for (var n = 0; n < path.length; n++) {
      if (!path[n].ok) continue;
      var r = World.apply(tool, path[n].k);
      if (r.ok) placed++;
      else if (r.money) { broke = true; break; }
    }
    var a = World.commit();
    if (broke) { UI.toast('💸 Dinheiro acabou no meio do caminho', 'bad'); Sfx.play('error'); }
    if (a && placed) { Sfx.play('place'); Game.onMapChanged(); }
    else if (!broke) { UI.toast('Não dá para construir aí', 'bad'); Sfx.play('error'); }
  }

  function updateHover(k) {
    var ui = Game.ui;
    ui.hover = k;
    if (k < 0) return;
    if (ui.moving >= 0) {
      var o = w.obj[k];
      ui.hoverOk = w.ter[k] !== DATA.T.AGUA && (!o || World.isNatural(o));
      return;
    }
    if (ui.tool && ui.tool !== 'info') {
      var ev = World.evaluate(ui.tool, k);
      ui.hoverOk = ev.ok && (ui.tool === 'demolir' || World.unlocked(I[ui.tool])) && (Game.s.mode === 'criativo' || Game.s.money >= ev.cost);
    }
  }

  function tap(k) {
    var ui = Game.ui, s = Game.s;
    if (!s || Game.walk) return;
    if (k < 0) { UI.closeBuilding(); return; }
    if (ui.moving >= 0) {
      var mv = World.move(ui.moving, k);
      if (mv.ok) {
        Sfx.play('place'); ui.moving = -1; UI.setTool(null);
        ui.selected = k; Game.onMapChanged(); UI.openBuilding(k);
        if (mv.cost) Render.addFloat(k, '-' + U.shortMoney(mv.cost), '#ffd27a');
      } else { UI.toast(mv.reason, 'bad'); Sfx.play('error'); }
      return;
    }
    var tool = ui.tool;
    if (!tool || tool === 'info') {
      var o = w.obj[k];
      if (o && World.isBuilding(o)) { ui.selected = k; UI.openBuilding(k); Sfx.play('click'); }
      else if (o) { ui.selected = k; UI.closeBuilding(true); UI.toast(I[o.id].icon + ' ' + I[o.id].name + (I[o.id].beauty ? ' · beleza +' + I[o.id].beauty : ''), ''); }
      else { ui.selected = -1; UI.closeBuilding(); }
      return;
    }
    var it = I[tool];
    var r = World.apply(tool, k);
    if (r.ok) {
      Sfx.play(tool === 'hq' ? 'level' : 'place');
      if (r.cost) Render.addFloat(k, '-' + U.shortMoney(r.cost), '#ffd27a');
      Game.onMapChanged();
      if (it && it.unique) { UI.setTool(null); Game.onHQ(k); }
    } else {
      UI.toast(r.reason || 'Não dá para construir aí', 'bad');
      Sfx.play('error');
    }
    updateHover(k);
  }

  function onKey(e) {
    if (!Game.s || e.target.tagName === 'INPUT') return;
    var step = 40;
    if (e.key === 'ArrowLeft' || e.key === 'a') Render.pan(step, 0);
    else if (e.key === 'ArrowRight' || e.key === 'd') Render.pan(-step, 0);
    else if (e.key === 'ArrowUp' || e.key === 'w') Render.pan(0, step);
    else if (e.key === 'ArrowDown' || e.key === 's') Render.pan(0, -step);
    else if (e.key === '+' || e.key === '=') Render.zoomAt(1.15, window.innerWidth / 2, window.innerHeight / 2);
    else if (e.key === '-') Render.zoomAt(1 / 1.15, window.innerWidth / 2, window.innerHeight / 2);
    else if (e.key === 'Escape') UI.back();
    else if ((e.ctrlKey || e.metaKey) && e.key === 'z') Game.undo();
  }

  return { init: init, updateHover: updateHover, tap: tap };
})();

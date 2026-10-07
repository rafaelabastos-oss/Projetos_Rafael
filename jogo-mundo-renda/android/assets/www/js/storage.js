/* Mundo Renda - salvamento. No Android usa arquivos do app (AndroidBridge); no navegador usa localStorage. */
'use strict';

var Store = (function () {
  var bridge = window.AndroidBridge || null;

  function get(key) {
    try {
      if (bridge) { var v = bridge.load(key); return v === undefined || v === '' ? null : v; }
      return window.localStorage.getItem(key);
    } catch (e) { return null; }
  }
  function set(key, val) {
    try {
      if (bridge) return bridge.save(key, val);
      window.localStorage.setItem(key, val);
      return true;
    } catch (e) { return false; }
  }
  function del(key) {
    try { if (bridge) bridge.remove(key); else window.localStorage.removeItem(key); } catch (e) { /* ignora */ }
  }
  function getJSON(key, def) {
    var v = get(key);
    if (!v) return def;
    try { return JSON.parse(v); } catch (e) { return def; }
  }
  function setJSON(key, obj) { return set(key, JSON.stringify(obj)); }

  // índice dos projetos salvos
  function list() { return getJSON('mr_index', []); }
  function saveGame(s, worldData) {
    var data = { v: 1, s: s, world: worldData };
    var ok = setJSON('mr_save_' + s.id, data);
    var idx = list().filter(function (e) { return e.id !== s.id; });
    idx.unshift({ id: s.id, name: s.project.name, emoji: s.project.emoji, color: s.project.color, day: s.day, money: Math.round(s.money),
      level: s.level, mode: s.mode, updated: Date.now() });
    setJSON('mr_index', idx.slice(0, 12));
    return ok !== false;
  }
  function loadGame(id) { return getJSON('mr_save_' + id, null); }
  function deleteGame(id) {
    del('mr_save_' + id);
    setJSON('mr_index', list().filter(function (e) { return e.id !== id; }));
  }

  return { get: get, set: set, del: del, getJSON: getJSON, setJSON: setJSON, list: list, saveGame: saveGame, loadGame: loadGame, deleteGame: deleteGame, native: !!bridge };
})();

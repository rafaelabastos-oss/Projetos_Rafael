/* Mundo Renda - trilha sonora original e ambiências (arquivos OGG em audio/, gerados por tools/audio/*.py).
   Três canais com troca suave: música (tema, manhã, feira, noite), ambiência (dia, noite, chuva) e mar
   (volume conforme quanto oceano aparece na tela). Se os arquivos faltarem, volta para a música sintetizada. */
'use strict';

var Music = (function () {
  var BASE = 'audio/';
  var FADE = 2.5;                       // segundos para trocar de faixa
  var LEVEL = { music: 0.55, amb: 0.45, mar: 0.5 };
  var MUSIC = { tema: 1, manha: 1, feira: 1, noite: 1 };
  var chans = {}, failed = {}, started = false, hidden = false, synthOn = false;

  function Chan(name) {
    this.name = name;
    this.voices = [];                   // { el, track, vol, target }
  }

  function makeEl(track) {
    var a = new Audio();
    a.preload = 'auto';
    a.loop = true;
    a.volume = 0;
    a.src = BASE + track + '.ogg';
    a.addEventListener('error', function () { failed[track] = true; });
    return a;
  }

  function tryPlay(a) {
    if (hidden) return;
    var now = Date.now();
    if (a._try && now - a._try < 1000) return;      // sem insistir a cada quadro antes do desbloqueio
    a._try = now;
    try {
      var p = a.play();
      if (p && p.catch) p.catch(function () { /* espera um toque (desbloqueio) */ });
    } catch (e) { /* ignora */ }
  }

  // pede uma faixa num canal; null silencia o canal
  Chan.prototype.want = function (track, level) {
    var v = this.voices, top = v.length ? v[v.length - 1] : null;
    if (track && failed[track]) track = null;
    if (top && top.track === track) { top.target = level; return; }
    for (var n = 0; n < v.length; n++) v[n].target = 0;
    if (!track) return;
    // reaproveita uma voz que ainda está sumindo com a mesma faixa
    for (n = 0; n < v.length; n++) {
      if (v[n].track === track) { var r = v.splice(n, 1)[0]; r.target = level; v.push(r); tryPlay(r.el); return; }
    }
    var el = makeEl(track);
    v.push({ el: el, track: track, vol: 0, target: level });
    tryPlay(el);
  };

  Chan.prototype.step = function (dt) {
    var v = this.voices;
    for (var n = v.length - 1; n >= 0; n--) {
      var x = v[n], d = x.target - x.vol, sp = dt / FADE;
      x.vol = Math.abs(d) <= sp ? x.target : x.vol + (d > 0 ? sp : -sp);
      var vol = Math.max(0, Math.min(1, x.vol * x.vol * (3 - 2 * x.vol)));
      if (Math.abs(x.el.volume - vol) > 0.004) x.el.volume = vol;
      if (x.vol <= 0 && x.target <= 0) {
        try { x.el.pause(); x.el.removeAttribute('src'); x.el.load(); } catch (e) { /* ignora */ }
        v.splice(n, 1);
      } else if (x.target > 0 && x.el.paused && !hidden) tryPlay(x.el);
    }
  };

  Chan.prototype.pauseAll = function () { this.voices.forEach(function (x) { try { x.el.pause(); } catch (e) { /* ignora */ } }); };
  Chan.prototype.resumeAll = function () { this.voices.forEach(function (x) { if (x.target > 0 || x.vol > 0) tryPlay(x.el); }); };

  function init() {
    if (started) return;
    started = true;
    chans.music = new Chan('music'); chans.amb = new Chan('amb'); chans.mar = new Chan('mar');
    document.addEventListener('visibilitychange', function () { setHidden(document.hidden); });
  }

  function setHidden(h) {
    hidden = h;
    for (var k in chans) { if (h) chans[k].pauseAll(); else chans[k].resumeAll(); }
  }

  // escolhe as faixas pelo estado do jogo; chamada a cada quadro
  function update(dt) {
    if (!started) return;
    var set = Game.settings || {}, s = Game.s;
    var ambOn = set.ambience !== false;
    var music = null, amb = null, marLvl = 0;
    if (!s) {
      music = 'tema';
      marLvl = 0.35;
    } else {
      var h = (s.t % 1) * 24;
      var night = h >= 18.6 || h < 5.3;
      var rain = s.events && s.events.some(function (e) { return e.id === 'chuva'; });
      var feiraEv = s.events && s.events.some(function (e) { return e.id === 'feira'; });
      music = night ? 'noite' : (feiraEv || s.day % 2 === 0 ? 'feira' : 'manha');
      amb = rain ? 'amb_chuva' : night ? 'amb_noite' : 'amb_dia';
      marLvl = Render.oceanAmount ? Render.oceanAmount() : 0;
      if (Game.walk) marLvl *= 1.2;
    }
    var walkDuck = Game.walk ? 0.7 : 1;
    // sem o arquivo da faixa (ex.: rodando no navegador sem a pasta audio): usa a música sintetizada antiga
    var useSynth = !!set.music && !!failed[music];
    if (useSynth !== synthOn && typeof Sfx !== 'undefined') { synthOn = useSynth; Sfx.setMusic(useSynth); }
    chans.music.want(set.music && !useSynth ? music : null, LEVEL.music * walkDuck);
    chans.amb.want(ambOn && amb ? amb : null, LEVEL.amb * (Game.walk ? 1.25 : 1));
    chans.mar.want(ambOn && marLvl > 0.02 ? 'amb_mar' : null, LEVEL.mar * Math.min(1, marLvl));
    for (var k in chans) chans[k].step(dt);
  }

  // chamado no primeiro toque: alguns navegadores só tocam áudio depois de um gesto
  function unlock() {
    init();
    for (var k in chans) chans[k].resumeAll();
  }

  return { init: init, update: update, unlock: unlock, setHidden: setHidden,
    available: function () { return !failed.tema; } };
})();

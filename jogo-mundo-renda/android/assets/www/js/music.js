/* Mundo Renda - trilha sonora original e ambiências (arquivos OGG em audio/, gerados por tools/audio/*.py).

   Música: um dia de jogo dura só 20 s, então a trilha NÃO segue o relógio do jogo quadro a quadro. Cada faixa toca
   inteira; perto do fim (a faixa é um loop sem emenda) escolhe-se a próxima pela hora do dia: noite -> "Noite na Vila";
   dia -> alterna "Manhã na Horta" e "Dia de Feira" (ou feira durante o evento de feira). Na tela inicial, o tema.
   Ambiências: dia e noite tocam juntas com volumes que acompanham a claridade (sem cortes), chuva por cima no evento
   de chuva e ondas conforme quanto mar aparece na tela.
   Cada faixa tem um único elemento <audio>; quando silencia, só pausa (não descarrega), e volta de onde parou.
   Se os arquivos faltarem, volta para a música sintetizada antiga (audio.js). */
'use strict';

var Music = (function () {
  var BASE = 'audio/';
  var FADE = 2.5;                                   // segundos para uma voz ir de 0 a 1
  var LEVEL = { music: 0.55, dia: 0.42, noite: 0.42, chuva: 0.5, mar: 0.5 };
  var voices = {}, failed = {}, started = false, hidden = false, synthOn = false;
  var cur = null, lastDay = 'feira';

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

  // volume alvo de uma faixa (cria o elemento só quando ela precisa soar)
  function want(track, level) {
    if (failed[track]) level = 0;
    var x = voices[track];
    if (!x) {
      if (level <= 0) return;
      x = voices[track] = { el: makeEl(track), vol: 0, target: 0 };
    }
    x.target = level;
  }

  function step(dt) {
    for (var track in voices) {
      var x = voices[track], d = x.target - x.vol, sp = dt / FADE;
      x.vol = Math.abs(d) <= sp ? x.target : x.vol + (d > 0 ? sp : -sp);
      var vol = Math.max(0, Math.min(1, x.vol * x.vol * (3 - 2 * x.vol)));
      if (Math.abs(x.el.volume - vol) > 0.004 || (vol === 0 && x.el.volume !== 0)) x.el.volume = vol;
      if (x.vol <= 0 && x.target <= 0) { if (!x.el.paused) { try { x.el.pause(); } catch (e) { /* ignora */ } } }
      else if (x.el.paused && !hidden && !failed[track]) tryPlay(x.el);
    }
  }

  function setHidden(h) {
    hidden = h;
    for (var track in voices) {
      var x = voices[track];
      if (h) { try { x.el.pause(); } catch (e) { /* ignora */ } }
      else if (x.target > 0 || x.vol > 0) tryPlay(x.el);
    }
  }

  function init() {
    if (started) return;
    started = true;
    document.addEventListener('visibilitychange', function () { setHidden(document.hidden); });
  }

  function isNight(s) { var h = (s.t % 1) * 24; return h >= 18.6 || h < 5.3; }
  function hasEvent(s, id) { return !!(s.events && s.events.some(function (e) { return e.id === id; })); }

  function pickMusic(s) {
    if (!s) return 'tema';
    if (isNight(s)) return 'noite';
    if (hasEvent(s, 'feira')) return 'feira';
    lastDay = lastDay === 'manha' ? 'feira' : 'manha';
    return lastDay;
  }

  // a faixa atual está chegando ao ponto do loop? (hora de decidir a próxima)
  function nearEnd(track) {
    var x = voices[track];
    if (!x || !x.el.duration || !isFinite(x.el.duration)) return false;
    var rem = x.el.duration - x.el.currentTime;
    if (rem > FADE + 0.4) { x.decided = false; return false; }
    if (x.decided) return false;
    x.decided = true;
    return true;
  }

  // escolhe as faixas pelo estado do jogo; chamada a cada quadro
  function update(dt) {
    if (!started) return;
    var set = Game.settings || {}, s = Game.s;
    var ambOn = set.ambience !== false;

    // música
    if (!s) cur = 'tema';
    else if (!cur || cur === 'tema' || failed[cur]) cur = pickMusic(s);
    else if (nearEnd(cur)) {
      var next = pickMusic(s);
      if (next !== cur && voices[next]) voices[next].decided = false;
      cur = next;
    }
    var useSynth = !!set.music && !!failed[cur];
    if (useSynth !== synthOn && typeof Sfx !== 'undefined') { synthOn = useSynth; Sfx.setMusic(useSynth); }
    var mLevel = set.music && !useSynth ? LEVEL.music * (Game.walk ? 0.7 : 1) : 0;
    for (var t in { tema: 1, manha: 1, feira: 1, noite: 1 }) want(t, t === cur ? mLevel : 0);

    // ambiências
    var dia = 0, noite = 0, chuva = 0, mar = 0;
    if (ambOn) {
      var boost = Game.walk ? 1.25 : 1;
      if (!s) { dia = 0.25; mar = 0.35; }
      else {
        var dark = Render.darkness ? Render.darkness(s.t) : (isNight(s) ? 1 : 0);
        var rain = hasEvent(s, 'chuva');
        var under = rain ? 0.35 : 1;
        dia = LEVEL.dia * (1 - dark) * under * boost;
        noite = LEVEL.noite * dark * under * boost;
        chuva = rain ? LEVEL.chuva * boost : 0;
        mar = LEVEL.mar * Math.min(1, (Render.oceanAmount ? Render.oceanAmount() : 0) * (Game.walk ? 1.2 : 1));
      }
    }
    want('amb_dia', dia); want('amb_noite', noite); want('amb_chuva', chuva); want('amb_mar', mar > 0.01 ? mar : 0);
    step(dt);
  }

  // chamado no primeiro toque: alguns navegadores só tocam áudio depois de um gesto
  function unlock() {
    init();
    for (var track in voices) { var x = voices[track]; if (x.target > 0) { x.el._try = 0; tryPlay(x.el); } }
  }

  return { init: init, update: update, unlock: unlock, setHidden: setHidden,
    available: function () { return !failed.tema; }, current: function () { return cur; } };
})();

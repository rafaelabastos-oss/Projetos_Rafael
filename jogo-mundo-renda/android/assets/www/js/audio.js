/* Mundo Renda - efeitos sonoros sintetizados (Web Audio) e música sintetizada de reserva (a trilha principal está em music.js) */
'use strict';

var Sfx = (function () {
  var ac = null, master = null, musicGain = null, musicTimer = null;

  function unlock() {
    if (!ac) {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      try { ac = new AC(); } catch (e) { return; }
      master = ac.createGain(); master.gain.value = 0.5; master.connect(ac.destination);
      musicGain = ac.createGain(); musicGain.gain.value = 0.0; musicGain.connect(master);
      if (typeof Music === 'undefined') setMusic(Game.settings && Game.settings.music);
    }
    if (ac.state === 'suspended') ac.resume();
    if (typeof Music !== 'undefined') Music.unlock();
  }

  function tone(freq, dur, type, vol, when, dest, slide) {
    if (!ac) return;
    var t = ac.currentTime + (when || 0);
    var o = ac.createOscillator(), g = ac.createGain();
    o.type = type || 'sine'; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(slide, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol || 0.2, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(dest || master);
    o.start(t); o.stop(t + dur + 0.05);
  }

  function buzz(ms) {
    try { if (window.AndroidBridge && Game.settings && Game.settings.vibrate) window.AndroidBridge.vibrate(ms); } catch (e) { /* ignora */ }
  }

  function play(name) {
    if (name === 'place' || name === 'demolish') buzz(14);
    else if (name === 'error') buzz(40);
    else if (name === 'level' || name === 'mission') buzz(30);
    if (!ac || !Game.settings || !Game.settings.sound) return;
    switch (name) {
      case 'click': tone(880, 0.06, 'triangle', 0.08); break;
      case 'tick': tone(660, 0.04, 'triangle', 0.04); break;
      case 'place': tone(220, 0.12, 'square', 0.07, 0, null, 110); tone(440, 0.1, 'triangle', 0.08, 0.03); break;
      case 'error': tone(180, 0.18, 'sawtooth', 0.06, 0, null, 120); break;
      case 'coin': tone(988, 0.08, 'square', 0.05); tone(1319, 0.18, 'square', 0.05, 0.07); break;
      case 'level': [523, 659, 784, 1047].forEach(function (f, n) { tone(f, 0.25, 'triangle', 0.1, n * 0.09); }); break;
      case 'mission': [784, 988, 1175].forEach(function (f, n) { tone(f, 0.2, 'sine', 0.12, n * 0.07); }); break;
      case 'event': tone(523, 0.15, 'sine', 0.1); tone(784, 0.25, 'sine', 0.1, 0.12); break;
      case 'demolish': tone(120, 0.25, 'sawtooth', 0.08, 0, null, 50); break;
    }
  }

  var SCALE = [261.6, 293.7, 329.6, 392.0, 440.0, 523.3, 587.3, 659.3];
  function setMusic(on) {
    if (!ac) return;
    musicGain.gain.setTargetAtTime(on ? 0.35 : 0.0, ac.currentTime, 0.5);
    if (on && !musicTimer) {
      var step = 0;
      musicTimer = setInterval(function () {
        if (document.hidden) return;
        var chord = [0, 2, 4, 5][Math.floor(step / 8) % 4];
        if (step % 8 === 0) { tone(SCALE[chord] / 2, 3.2, 'sine', 0.12, 0, musicGain); tone(SCALE[(chord + 2) % 8] / 2, 3.2, 'sine', 0.08, 0, musicGain); }
        if (Math.random() < 0.6) tone(SCALE[Math.floor(Math.random() * SCALE.length)] * (Math.random() < 0.3 ? 2 : 1), 0.9, 'triangle', 0.06, 0, musicGain);
        step++;
      }, 420);
    } else if (!on && musicTimer) { clearInterval(musicTimer); musicTimer = null; }
  }

  return { unlock: unlock, play: play, setMusic: setMusic };
})();

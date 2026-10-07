"""Mundo Renda - biblioteca de síntese de áudio (100% procedural, sem samples de terceiros).

Requisitos: Python 3, numpy, scipy e o programa ffmpeg (com libvorbis).

Ideia geral:
  - cada instrumento é uma função que devolve um vetor mono float64 (amplitude ~[-1, 1]);
  - `Mix` acumula notas em um buffer estéreo com panorâmica de potência constante;
  - `reverb`, `eq_*`, `limiter` tratam o mix; `seamless_loop` dobra a cauda sobre o início;
  - `master_and_export` normaliza a sonoridade (LUFS medido pelo ffmpeg/ebur128) e grava OGG Vorbis.

Tudo é determinístico: passe sementes (`seed`) e o mesmo script gera exatamente o mesmo arquivo.
"""
import os
import re
import subprocess
import tempfile

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d

SR = 44100

# ---------------------------------------------------------------------------
# Notas, acordes e tempo
# ---------------------------------------------------------------------------
_NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(name_or_num):
    """'C4' -> 60, 'F#3' -> 54, 'Bb2' -> 46; números passam direto."""
    if isinstance(name_or_num, (int, np.integer, float)):
        return float(name_or_num)
    m = re.match(r'^([A-Ga-g])([#b]*)(-?\d+)$', name_or_num.strip())
    if not m:
        raise ValueError('nota inválida: %r' % name_or_num)
    n = _NAMES[m.group(1).upper()] + m.group(2).count('#') - m.group(2).count('b')
    return float(n + 12 * (int(m.group(3)) + 1))


def freq(n):
    """Frequência (Hz) de uma nota MIDI ou nome."""
    return 440.0 * 2.0 ** ((midi(n) - 69.0) / 12.0)


_CHORD_TYPES = {
    '': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'maj7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10],
    '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9], '9': [0, 4, 7, 10, 14], 'maj9': [0, 4, 7, 11, 14], 'm9': [0, 3, 7, 10, 14],
    'add9': [0, 4, 7, 14], 'sus4': [0, 5, 7], 'sus2': [0, 2, 7], '7sus4': [0, 5, 7, 10], 'dim': [0, 3, 6], 'dim7': [0, 3, 6, 9],
    'm7b5': [0, 3, 6, 10], 'aug': [0, 4, 8], '69': [0, 4, 7, 9, 14], '13': [0, 4, 10, 14, 21], '7b9': [0, 4, 7, 10, 13],
}


def chord(sym, octave=3):
    """Acorde cifrado -> lista de notas MIDI a partir da fundamental na oitava dada.
    Ex.: chord('Am7') -> [57, 60, 64, 67];  chord('D7/F#') põe F# no baixo (uma oitava abaixo)."""
    bass = None
    if '/' in sym:
        sym, bass = sym.split('/')
    m = re.match(r'^([A-G][#b]?)(.*)$', sym)
    root = midi(m.group(1) + str(octave))
    kind = m.group(2)
    if kind not in _CHORD_TYPES:
        raise ValueError('acorde desconhecido: %r' % sym)
    notes = [root + i for i in _CHORD_TYPES[kind]]
    if bass:
        b = midi(bass + str(octave - 1))
        notes = [b] + notes
    return notes


def chord_root(sym, octave=2):
    """Nota MIDI do baixo do acorde (respeita a inversão '/X')."""
    if '/' in sym:
        return midi(sym.split('/')[1] + str(octave))
    m = re.match(r'^([A-G][#b]?)', sym)
    return midi(m.group(1) + str(octave))


def beats(bpm, n=1.0):
    """Duração em segundos de n tempos."""
    return 60.0 / bpm * n


# ---------------------------------------------------------------------------
# Envelopes e utilidades de sinal
# ---------------------------------------------------------------------------
def nsamp(dur):
    return max(1, int(round(dur * SR)))


def tarr(n):
    return np.arange(n) / SR


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2, curve=3.0):
    """Envelope ADSR com n amostras no total (a soltura acontece no fim do vetor)."""
    na, nd, nr = nsamp(a), nsamp(d), nsamp(r)
    na = min(na, n)
    nd = min(nd, max(0, n - na))
    nr = min(nr, max(0, n - na - nd))
    ns = max(0, n - na - nd - nr)
    env = np.empty(n)
    env[:na] = np.linspace(0, 1, na, endpoint=False) ** 1.0
    if nd:
        x = np.linspace(0, 1, nd, endpoint=False)
        env[na:na + nd] = s + (1 - s) * np.exp(-curve * x)
    env[na + nd:na + nd + ns] = s
    if nr:
        x = np.linspace(0, 1, nr)
        env[n - nr:] = s * np.exp(-curve * x) * (1 - x)
    return env


def expdecay(n, t60):
    """Decaimento exponencial que cai 60 dB em t60 segundos."""
    return np.exp(-6.9078 * tarr(n) / max(1e-4, t60))


def fade(x, fin=0.003, fout=0.01):
    x = x.copy()
    a, b = min(len(x), nsamp(fin)), min(len(x), nsamp(fout))
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


def lowpass(x, fc, order=2):
    fc = min(fc, SR * 0.45)
    sos = signal.butter(order, fc, 'low', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def highpass(x, fc, order=2):
    sos = signal.butter(order, fc, 'high', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def bandpass(x, lo, hi, order=2):
    hi = min(hi, SR * 0.45)
    sos = signal.butter(order, [lo, hi], 'band', fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=-1)


def peak_eq(x, f0, gain_db, q=1.0):
    """Filtro de pico (RBJ) para dar corpo/brilho."""
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / SR
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=-1)


def onepole_lp(x, coef):
    """Passa-baixas de um polo (coef 0..1, maior = mais escuro)."""
    return signal.lfilter([1 - coef], [1, -coef], x)


def noise(n, rng):
    return rng.standard_normal(n)


def pink(n, rng):
    """Ruído rosa (1/f) por filtro de Voss-McCartney aproximado (Paul Kellet)."""
    w = rng.standard_normal(n)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    return signal.lfilter(b, a, w) * 3.5


def vibrato(n, f0, rate=5.0, depth_cents=12.0, delay=0.15, rng=None):
    """Curva de frequência instantânea com vibrato que entra depois de `delay` s."""
    t = tarr(n)
    ph = 0.0 if rng is None else rng.uniform(0, 2 * np.pi)
    ramp = np.clip((t - delay) / 0.3, 0, 1)
    cents = depth_cents * ramp * np.sin(2 * np.pi * rate * t + ph)
    return f0 * 2 ** (cents / 1200.0)


def osc_phase(freqs):
    """Fase acumulada para um vetor de frequências instantâneas."""
    return 2 * np.pi * np.cumsum(freqs) / SR


def additive(freqs_inst, partials, n):
    """Soma de parciais: partials = [(multiplicador, amplitude, t60_ou_None), ...]."""
    ph = osc_phase(freqs_inst)
    out = np.zeros(n)
    t = tarr(n)
    nyq = SR * 0.48
    fmax = float(np.max(freqs_inst))
    for mult, amp, t60 in partials:
        if fmax * mult >= nyq:
            continue
        p = np.sin(ph * mult)
        if t60:
            p *= np.exp(-6.9078 * t / t60)
        out += amp * p
    return out


def saw_bl(freqs_inst, n, max_h=40, rolloff=1.0):
    """Dente de serra limitado em banda (soma de harmônicos até Nyquist)."""
    ph = osc_phase(freqs_inst)
    out = np.zeros(n)
    fmax = float(np.max(freqs_inst))
    for h in range(1, max_h + 1):
        if fmax * h >= SR * 0.45:
            break
        out += np.sin(ph * h) / (h ** rolloff)
    return out * 0.6


# ---------------------------------------------------------------------------
# Instrumentos melódicos
# ---------------------------------------------------------------------------
def karplus(f0, dur, bright=0.55, t60=2.5, pick_pos=0.18, seed=0):
    """Corda dedilhada (Karplus-Strong vetorizado por períodos).
    bright: 0 (abafado) .. 1 (brilhante); t60: sustentação da fundamental."""
    rng = np.random.default_rng(seed)
    n = nsamp(dur)
    P = SR / f0
    D = max(2, int(round(P - 0.5)))
    # excitação: ruído filtrado + pente da posição da palheta
    exc = rng.uniform(-1, 1, D)
    exc = onepole_lp(exc, 0.85 - 0.8 * bright)
    pp = max(1, int(D * pick_pos))
    exc = exc - np.concatenate([np.zeros(pp), exc[:-pp]])
    exc -= exc.mean()
    exc /= (np.max(np.abs(exc)) + 1e-9)
    # ganho por período para atingir o t60 pedido
    g = 10 ** (-3.0 * (D + 0.5) / (SR * t60))
    y = np.zeros(n + D + 1)
    y[1:D + 1] = exc
    k = D + 1
    while k < len(y):
        e = min(len(y), k + D)
        prev = y[k - D:e - D]
        prev2 = y[k - D - 1:e - D - 1]
        y[k:e] = g * 0.5 * (prev + prev2)
        k = e
    out = y[1:n + 1]
    return out


def nylon(note, dur, vel=0.8, bright=0.45, seed=0, t60=None):
    """Violão de nylon: Karplus-Strong + ressonância de corpo + leve ataque de unha."""
    f0 = freq(note)
    if t60 is None:
        t60 = float(np.clip(3.2 - (f0 - 80) / 500.0, 0.9, 3.2))
    s = karplus(f0, dur, bright=bright * (0.6 + 0.5 * vel), t60=t60, seed=seed)
    body = peak_eq(s, 105, 5.0, 1.2)
    body = peak_eq(body, 220, 3.0, 1.5)
    body = peak_eq(body, 2600, -2.5, 0.8)
    rng = np.random.default_rng(seed + 991)
    click = highpass(rng.standard_normal(nsamp(0.006)), 2500) * 0.08
    body[:len(click)] += click
    body = fade(body, 0.0005, min(0.08, dur * 0.2))
    return body * vel * 0.5


def bass_upright(note, dur, vel=0.8, seed=0):
    """Contrabaixo acústico: parciais com decaimento + ataque percussivo."""
    f0 = freq(note)
    n = nsamp(dur)
    rng = np.random.default_rng(seed)
    f = vibrato(n, f0, rate=4.5, depth_cents=3, delay=0.3, rng=rng)
    parts = [(1, 1.0, 1.6), (2, 0.55, 0.9), (3, 0.28, 0.55), (4, 0.16, 0.35), (5, 0.08, 0.25), (6, 0.04, 0.2)]
    s = additive(f, parts, n)
    thump = lowpass(rng.standard_normal(nsamp(0.03)), 400) * np.linspace(1, 0, nsamp(0.03)) * 0.25
    s[:len(thump)] += thump[:n]
    env = adsr(n, 0.008, 0.25, 0.55, min(0.12, dur * 0.3))
    return lowpass(s * env, 1800) * vel * 0.55


def bass_soft(note, dur, vel=0.8):
    """Baixo redondo (sintetizado suave) para faixas calmas."""
    f0 = freq(note)
    n = nsamp(dur)
    s = additive(np.full(n, f0), [(1, 1.0, None), (2, 0.25, 1.0), (3, 0.08, 0.6)], n)
    return s * adsr(n, 0.02, 0.3, 0.7, min(0.2, dur * 0.4)) * vel * 0.5


def accordion(note, dur, vel=0.8, seed=0, reeds=3, bright=0.6):
    """Sanfona: palhetas levemente desafinadas (batimento), fole (tremolo) e timbre anasalado."""
    f0 = freq(note)
    n = nsamp(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    detunes = [0.0, 6.0, -5.0][:reeds]
    for c in detunes:
        f = np.full(n, f0 * 2 ** (c / 1200.0))
        ph = osc_phase(f) + rng.uniform(0, 2 * np.pi)
        # onda de palheta: pulso estreito suavizado (harmônicos ímpares e pares)
        w = np.zeros(n)
        for h in range(1, 18):
            if f0 * h > SR * 0.45:
                break
            w += np.sin(ph * h) * (1.0 / h) * (0.9 if h % 2 else 0.6)
        out += w
    out /= len(detunes)
    out = peak_eq(out, 1300, 4.0, 1.2)
    out = lowpass(out, 2500 + 3500 * bright)
    bellows = 1.0 + 0.06 * np.sin(2 * np.pi * 5.5 * tarr(n) + rng.uniform(0, 6))
    env = adsr(n, 0.025, 0.08, 0.85, min(0.08, dur * 0.25))
    return out * env * bellows * vel * 0.35


def flute(note, dur, vel=0.8, seed=0):
    """Flauta: senoide com harmônicos fracos, sopro filtrado e vibrato atrasado."""
    f0 = freq(note)
    n = nsamp(dur)
    rng = np.random.default_rng(seed)
    f = vibrato(n, f0, rate=5.2, depth_cents=14, delay=0.2, rng=rng)
    s = additive(f, [(1, 1.0, None), (2, 0.22, None), (3, 0.09, None), (4, 0.03, None)], n)
    breath = bandpass(rng.standard_normal(n), f0 * 0.9, f0 * 3.5) * 0.12
    env = adsr(n, 0.06, 0.1, 0.85, min(0.15, dur * 0.3))
    chiff = np.zeros(n)
    m = min(n, nsamp(0.04))
    chiff[:m] = bandpass(rng.standard_normal(m), 1500, 6000) * np.linspace(0.25, 0, m)
    return (s + breath) * env * vel * 0.3 + chiff * vel * 0.3


def vibes(note, dur, vel=0.8, motor=True, seed=0):
    """Vibrafone: barras metálicas (parcial 4x), decaimento longo e motor (tremolo) opcional."""
    f0 = freq(note)
    n = nsamp(dur)
    s = additive(np.full(n, f0), [(1, 1.0, 3.2), (4.0, 0.25, 0.7), (10.0, 0.05, 0.15)], n)
    if motor:
        s *= 1 + 0.25 * np.sin(2 * np.pi * 5.0 * tarr(n) + seed)
    rng = np.random.default_rng(seed)
    m = min(n, nsamp(0.01))
    s[:m] += highpass(rng.standard_normal(m), 3000) * 0.05
    return fade(s, 0.001, min(0.25, dur * 0.3)) * vel * 0.3


def marimba(note, dur, vel=0.8, seed=0):
    """Marimba: madeira (parciais 1, 4, 9.9) com decaimento rápido."""
    f0 = freq(note)
    n = nsamp(dur)
    t60 = float(np.clip(1.4 - (f0 - 200) / 900.0, 0.35, 1.4))
    s = additive(np.full(n, f0), [(1, 1.0, t60), (3.93, 0.3, t60 * 0.25), (9.9, 0.08, t60 * 0.08)], n)
    return fade(s, 0.0008, min(0.1, dur * 0.3)) * vel * 0.35


def epiano(note, dur, vel=0.8, seed=0):
    """Piano elétrico (tipo Rhodes) por FM simples: brilho no ataque, sino suave."""
    f0 = freq(note)
    n = nsamp(dur)
    t = tarr(n)
    idx = (1.2 + 1.8 * vel) * np.exp(-t / 0.35)
    mod = np.sin(2 * np.pi * f0 * 14.0 * t) * 0.08 * np.exp(-t / 0.05) + np.sin(2 * np.pi * f0 * t) * idx
    s = np.sin(2 * np.pi * f0 * t + mod)
    s *= np.exp(-t / (1.8 if f0 < 400 else 1.1))
    s *= 1 + 0.08 * np.sin(2 * np.pi * 4.2 * t + seed)
    return fade(s, 0.001, min(0.2, dur * 0.3)) * vel * 0.28


def pad(notes, dur, vel=0.6, seed=0, bright=0.35, attack=1.2, release=1.5):
    """Colchão de cordas/sintetizador: serras desafinadas + filtro lento."""
    n = nsamp(dur)
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    for note in notes:
        f0 = freq(note)
        for c in (-7, 0, 7):
            f = vibrato(n, f0 * 2 ** (c / 1200.0), rate=rng.uniform(0.15, 0.35), depth_cents=4, delay=0, rng=rng)
            out += saw_bl(f, n, max_h=24, rolloff=1.15)
    out /= max(1, len(notes) * 3)
    cut = 500 + 2400 * bright
    out = lowpass(out, cut, order=2)
    out = lowpass(out, cut * 1.5, order=1)
    env = adsr(n, attack, 0.5, 0.85, min(release, dur * 0.45), curve=2.0)
    return out * env * vel * 0.5


# ---------------------------------------------------------------------------
# Percussão
# ---------------------------------------------------------------------------
def kick(vel=0.8, dur=0.35, f_hi=110, f_lo=48):
    n = nsamp(dur)
    t = tarr(n)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.04)
    s = np.sin(osc_phase(f)) * np.exp(-t / 0.12)
    return s * vel * 0.9


def zabumba(kind='bum', vel=0.8, seed=0):
    """Zabumba: 'bum' (pele grave, maceta), 'abafa' (grave abafado), 'bacalhau' (vareta na pele de baixo)."""
    rng = np.random.default_rng(seed)
    if kind == 'bacalhau':
        n = nsamp(0.09)
        t = tarr(n)
        s = bandpass(rng.standard_normal(n), 1200, 6000) * np.exp(-t / 0.018)
        s += np.sin(2 * np.pi * 340 * t) * np.exp(-t / 0.03) * 0.5
        return s * vel * 0.45
    dur = 0.55 if kind == 'bum' else 0.18
    n = nsamp(dur)
    t = tarr(n)
    f = 72 + 70 * np.exp(-t / 0.03)
    body = np.sin(osc_phase(f)) * np.exp(-t / (0.22 if kind == 'bum' else 0.06))
    body += np.sin(osc_phase(f * 1.6)) * np.exp(-t / 0.05) * 0.3
    hit = lowpass(rng.standard_normal(n), 900) * np.exp(-t / 0.012) * 0.6
    return (body + hit) * vel * 0.85


def triangle(open_=True, vel=0.8, seed=0):
    """Triângulo: parciais inarmônicos agudos; aberto soa longo, fechado (abafado) é curto."""
    dur = 0.9 if open_ else 0.07
    n = nsamp(dur)
    t = tarr(n)
    base = 2950.0
    s = np.zeros(n)
    for mult, amp in ((1.0, 1.0), (1.47, 0.6), (2.09, 0.5), (2.76, 0.35), (3.39, 0.2), (4.53, 0.12)):
        if base * mult < SR * 0.45:
            s += amp * np.sin(2 * np.pi * base * mult * t + seed * mult)
    s *= np.exp(-t / (0.35 if open_ else 0.018))
    return highpass(s, 1500) * vel * 0.12


def shaker(vel=0.6, dur=0.09, seed=0, bright=0.6):
    """Ganzá / chocalho: ruído agudo com envelope de 'arrasto'."""
    rng = np.random.default_rng(seed)
    n = nsamp(dur)
    t = tarr(n)
    env = (t / (dur * 0.35)) * np.exp(1 - t / (dur * 0.35))
    s = bandpass(rng.standard_normal(n), 3500 + 2500 * bright, 12000) * env
    return s * vel * 0.18


def pandeiro(kind='plat', vel=0.7, seed=0):
    """Pandeiro: 'plat' (platinelas), 'grave' (polegar na pele), 'tapa'."""
    rng = np.random.default_rng(seed)
    if kind == 'grave':
        n = nsamp(0.3)
        t = tarr(n)
        f = 110 + 60 * np.exp(-t / 0.02)
        s = np.sin(osc_phase(f)) * np.exp(-t / 0.12) + bandpass(rng.standard_normal(n), 5000, 11000) * np.exp(-t / 0.06) * 0.25
        return s * vel * 0.6
    if kind == 'tapa':
        n = nsamp(0.12)
        t = tarr(n)
        s = bandpass(rng.standard_normal(n), 800, 5000) * np.exp(-t / 0.02) + bandpass(rng.standard_normal(n), 5000, 11000) * np.exp(-t / 0.05) * 0.4
        return s * vel * 0.45
    n = nsamp(0.16)
    t = tarr(n)
    s = bandpass(rng.standard_normal(n), 5500, 13000) * np.exp(-t / 0.05)
    for f in (6200, 7400, 8900):
        s += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / 0.04) * 0.15
    return s * vel * 0.2


def woodblock(vel=0.7, f0=1850):
    n = nsamp(0.08)
    t = tarr(n)
    s = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.018) + np.sin(2 * np.pi * f0 * 2.7 * t) * np.exp(-t / 0.008) * 0.3
    return s * vel * 0.3


def brush(vel=0.5, dur=0.18, seed=0):
    """Vassourinha na caixa."""
    rng = np.random.default_rng(seed)
    n = nsamp(dur)
    t = tarr(n)
    s = bandpass(rng.standard_normal(n), 1800, 9000) * np.exp(-t / (dur * 0.35))
    return s * vel * 0.2


def rim(vel=0.6, seed=0):
    rng = np.random.default_rng(seed)
    n = nsamp(0.06)
    t = tarr(n)
    s = np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.01) * 0.6 + bandpass(rng.standard_normal(n), 2000, 7000) * np.exp(-t / 0.008)
    return s * vel * 0.3


def cabasa(vel=0.5, seed=0):
    return shaker(vel, dur=0.12, seed=seed, bright=0.9)


# ---------------------------------------------------------------------------
# Natureza (para as ambiências)
# ---------------------------------------------------------------------------
def wave_swell(dur, rng, size=1.0):
    """Uma onda: ruído rosa filtrado que cresce, quebra (brilho) e recua espumando."""
    n = nsamp(dur)
    t = tarr(n)
    x = t / dur
    env = np.sin(np.pi * np.clip(x, 0, 1)) ** 1.6
    crash = np.exp(-((x - 0.45) / 0.12) ** 2)
    base = lowpass(pink(n, rng), 500) * env
    foam = bandpass(pink(n, rng), 900, 6000) * (0.25 * env + 0.9 * crash) * (0.5 + 0.5 * size)
    fizz = highpass(rng.standard_normal(n), 5000) * np.clip(x - 0.45, 0, 1) * np.exp(-np.clip(x - 0.45, 0, 1) * 4) * 0.15
    return (base * 0.9 + foam * 0.55 + fizz) * size


def bird_chirp(f_start, f_end, dur, vel=0.5, harm=0.15, seed=0):
    """Pio: varredura de frequência com envelope curto e um pouco de harmônico."""
    n = nsamp(dur)
    t = tarr(n)
    x = t / dur
    f = f_start * (f_end / f_start) ** x
    ph = osc_phase(f)
    env = np.sin(np.pi * x) ** 0.8
    s = np.sin(ph) + harm * np.sin(2 * ph)
    return s * env * vel * 0.25


def bird_phrase(rng, kind='bemtevi', vel=0.5):
    """Frases de pássaros brasileiros (estilizadas). kind: 'bemtevi', 'sabia', 'tico', 'rolinha'."""
    out = []
    if kind == 'bemtevi':        # "bem-te-vi": 3 notas, a última descendente e longa
        out.append((0.00, bird_chirp(2400, 2900, 0.10, vel, seed=1)))
        out.append((0.16, bird_chirp(2700, 3300, 0.09, vel, seed=2)))
        out.append((0.32, bird_chirp(3400, 2300, 0.28, vel * 1.1, harm=0.25, seed=3)))
    elif kind == 'sabia':        # sabiá: frase melodiosa com várias notas
        tt = 0.0
        for k in range(int(rng.integers(5, 9))):
            f = rng.uniform(1600, 3200)
            d = rng.uniform(0.08, 0.22)
            out.append((tt, bird_chirp(f, f * rng.uniform(0.85, 1.25), d, vel * rng.uniform(0.6, 1.0), harm=0.1, seed=k)))
            tt += d + rng.uniform(0.03, 0.12)
    elif kind == 'tico':         # tico-tico: trinado rápido
        f = rng.uniform(4200, 5200)
        for k in range(int(rng.integers(6, 12))):
            out.append((k * 0.055, bird_chirp(f, f * 0.8, 0.04, vel * 0.7, seed=k)))
    else:                        # rolinha: "fogo-pagou" grave e suave
        for k, (a, b, d) in enumerate(((620, 640, 0.25), (560, 520, 0.22), (600, 560, 0.35))):
            out.append((k * 0.35, bird_chirp(a, b, d, vel * 0.8, harm=0.05, seed=k)))
    end = max(s + len(x) / SR for s, x in out)
    buf = np.zeros(nsamp(end) + 10)
    for s, x in out:
        i = nsamp(s)
        buf[i:i + len(x)] += x
    return buf


def cricket(dur, rng, f0=4600, rate=None, vel=0.4):
    """Grilo: pulsos de seno agudo em grupos (cri-cri)."""
    n = nsamp(dur)
    t = tarr(n)
    rate = rate or rng.uniform(2.2, 3.2)          # grupos por segundo
    group = (np.sin(2 * np.pi * rate * t) > 0.55).astype(float)
    pulses = (np.sin(2 * np.pi * 28 * t) > 0).astype(float)
    env = lowpass(group * pulses, 300)
    s = np.sin(2 * np.pi * f0 * t + 0.4 * np.sin(2 * np.pi * 28 * t))
    return s * env * vel * 0.15


def frog(rng, vel=0.5):
    """Sapo: 'croac' grave com pulsos rápidos."""
    dur = rng.uniform(0.25, 0.5)
    n = nsamp(dur)
    t = tarr(n)
    f0 = rng.uniform(180, 320)
    pulses = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rng.uniform(28, 45) * t))
    s = additive(np.full(n, f0), [(1, 1.0, None), (2, 0.6, None), (3, 0.3, None), (5, 0.15, None)], n)
    s = bandpass(s * lowpass(pulses, 200), 150, 1800)
    return s * np.sin(np.pi * t / dur) * vel * 0.35


def raindrops(dur, rng, density=40.0, vel=0.4):
    """Gotas individuais (estalos curtos de frequência variável)."""
    n = nsamp(dur)
    out = np.zeros(n)
    k = int(dur * density)
    for _ in range(k):
        i = int(rng.integers(0, n - 2000))
        m = nsamp(rng.uniform(0.01, 0.03))
        tt = tarr(m)
        f = rng.uniform(1800, 6000)
        out[i:i + m] += np.sin(2 * np.pi * f * tt * (1 + 2 * tt)) * np.exp(-tt / 0.006) * rng.uniform(0.2, 1.0)
    return out * vel * 0.2


def wind(dur, rng, strength=0.5):
    n = nsamp(dur)
    slow = np.interp(np.arange(n), np.linspace(0, n, 12), rng.uniform(0.3, 1.0, 12))
    s = bandpass(pink(n, rng), 200, 1400) * slow
    return s * strength * 0.25


def thunder(rng, vel=0.6):
    dur = rng.uniform(3.0, 5.0)
    n = nsamp(dur)
    t = tarr(n)
    env = np.exp(-t / (dur * 0.35)) * (1 - np.exp(-t / 0.08))
    rumble = lowpass(pink(n, rng), 160) * env
    crack = bandpass(rng.standard_normal(n), 300, 2500) * np.exp(-t / 0.25) * 0.4
    return (rumble * 2.2 + crack) * vel * 0.5


# ---------------------------------------------------------------------------
# Mixagem
# ---------------------------------------------------------------------------
class Mix:
    """Buffer estéreo. add(sinal, inicio_s, ganho, pan[-1..1])."""

    def __init__(self, dur):
        self.n = nsamp(dur)
        self.buf = np.zeros((2, self.n))

    def add(self, x, start, gain=1.0, pan=0.0):
        if x.ndim == 1:
            ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            st = np.vstack([x * np.cos(ang), x * np.sin(ang)]) * gain
        else:
            st = x * gain
        i = nsamp(start) if start > 0 else 0
        if i >= self.n:
            return
        m = min(st.shape[1], self.n - i)
        self.buf[:, i:i + m] += st[:, :m]

    def add_stereo(self, other, gain=1.0):
        m = min(other.shape[1], self.n)
        self.buf[:, :m] += other[:, :m] * gain


def stereo_widen(x, amount=0.3):
    """Alarga um sinal estéreo (M/S)."""
    m = (x[0] + x[1]) * 0.5
    s = (x[0] - x[1]) * 0.5 * (1 + amount)
    return np.vstack([m + s, m - s])


def make_ir(t60=1.8, predelay=0.012, bright=0.5, seed=7, early=True):
    """Resposta ao impulso estéreo sintética (ruído com decaimento, escurecendo com o tempo)."""
    rng = np.random.default_rng(seed)
    n = nsamp(t60 * 1.1)
    t = tarr(n)
    ir = np.zeros((2, n + nsamp(predelay)))
    for ch in range(2):
        x = rng.standard_normal(n) * np.exp(-6.9078 * t / t60)
        dark = lowpass(x, 1500 + 3000 * bright) * np.exp(-t / (t60 * 0.6))
        x = x * np.exp(-t / (t60 * 0.18)) * 0.35 + dark
        if early:
            for k in range(8):
                d = nsamp(rng.uniform(0.005, 0.045))
                if d < n:
                    x[d] += rng.uniform(-0.6, 0.6)
        ir[ch, nsamp(predelay):] = x
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    return ir


def reverb(x, wet=0.18, t60=1.8, predelay=0.012, bright=0.5, seed=7, hp=180):
    """Reverb por convolução; x estéreo (2, n). Retorna sinal com o mesmo tamanho."""
    ir = make_ir(t60, predelay, bright, seed)
    src = highpass(x, hp)
    out = np.zeros_like(x)
    for ch in range(2):
        out[ch] = signal.oaconvolve(src[ch], ir[ch])[:x.shape[1]]
    return x * (1 - wet * 0.5) + out * wet


def delay_fx(x, time=0.375, fb=0.35, wet=0.2, lp=3500):
    """Eco ping-pong simples (estéreo)."""
    d = nsamp(time)
    out = np.zeros_like(x)
    tap = x.copy()
    for k in range(6):
        tap = lowpass(np.roll(tap, d, axis=1), lp, order=1) * fb
        tap[:, :d] = 0
        if k % 2 == 0:
            out += tap[::-1]
        else:
            out += tap
    return x + out * wet


def compress(x, thresh_db=-18, ratio=2.5, attack=0.01, release=0.15, makeup_db=0.0):
    """Compressor de banda larga (detecção RMS, ganho suavizado)."""
    mono = np.sqrt(np.mean(x ** 2, axis=0) + 1e-12)
    a_a, a_r = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    lvl = signal.lfilter([1 - a_r], [1, -a_r], mono)
    db = 20 * np.log10(lvl + 1e-9)
    over = np.maximum(0, db - thresh_db)
    gain_db = -over * (1 - 1 / ratio) + makeup_db
    g = 10 ** (gain_db / 20)
    g = signal.lfilter([1 - a_a], [1, -a_a], g)
    return x * g


def limiter(x, ceiling_db=-1.0, lookahead=0.004, release=0.08):
    """Limitador com antecipação: nenhum pico passa do teto."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x), axis=0)
    la = nsamp(lookahead)
    peak = maximum_filter1d(peak, size=2 * la + 1)
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    a_r = np.exp(-1 / (release * SR))
    # suavização: queda imediata, recuperação lenta; o filtro começa em repouso (zi) para não
    # abafar o início do arquivo (o que criava um estalo na emenda dos loops)
    sm, _ = signal.lfilter([1 - a_r], [1, -a_r], need, zi=[a_r * need[0]])
    g = np.minimum(need, sm)
    y = x * g
    return np.clip(y, -ceil, ceil)


def seamless_loop(x, loop_len_s):
    """Dobra tudo o que passa do fim do loop (caudas de reverb, notas soando) sobre o início,
    e faz um cruzamento curtíssimo para não estalar. Retorna exatamente loop_len_s segundos."""
    L = nsamp(loop_len_s)
    if x.shape[1] <= L:
        y = np.zeros((2, L))
        y[:, :x.shape[1]] = x
        return y
    y = x[:, :L].copy()
    tail = x[:, L:]
    m = min(tail.shape[1], L)
    y[:, :m] += tail[:, :m]
    return y


def crossfade_loop(x, loop_len_s, xfade_s=2.0):
    """Loop para texturas contínuas (mar, chuva, grilos): renderize loop_len_s + xfade_s segundos;
    o trecho final é misturado sobre o início com cruzamento de potência constante."""
    L, C = nsamp(loop_len_s), nsamp(xfade_s)
    if x.shape[1] < L + C:
        raise ValueError('renderize pelo menos loop_len_s + xfade_s segundos')
    y = x[:, :L].copy()
    ang = np.linspace(0, np.pi / 2, C)
    y[:, :C] = x[:, :C] * np.sin(ang) + x[:, L:L + C] * np.cos(ang)
    return y


# ---------------------------------------------------------------------------
# Medição, master e exportação
# ---------------------------------------------------------------------------
def _write_wav(path, x):
    rng = np.random.default_rng(1234)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0       # dither TPDF
    y = np.clip(x + d, -1, 1)
    wavfile.write(path, SR, (y.T * 32767).astype(np.int16))


def measure(path_or_array):
    """Mede LUFS integrado, faixa de loudness e pico verdadeiro (dBTP) com o ffmpeg (ebur128)."""
    tmp = None
    path = path_or_array
    if not isinstance(path_or_array, str):
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        _write_wav(tmp.name, path_or_array)
        path = tmp.name
    try:
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-'],
                           capture_output=True, text=True)
        txt = r.stderr
        summ = txt[txt.rfind('Summary:'):]
        I = float(re.search(r'I:\s+(-?[\d.]+|-inf) LUFS', summ).group(1).replace('-inf', '-99'))
        LRA = float(re.search(r'LRA:\s+(-?[\d.]+) LU', summ).group(1))
        tp = re.search(r'Peak:\s+(-?[\d.]+|-inf) dBFS', summ)
        TP = float(tp.group(1).replace('-inf', '-99')) if tp else None
        return {'lufs': I, 'lra': LRA, 'true_peak_db': TP}
    finally:
        if tmp:
            os.unlink(tmp.name)


def loop_seam_report(x):
    """Compara o nível RMS dos últimos e primeiros 50 ms e o salto de amostra na emenda."""
    w = nsamp(0.05)
    a = np.sqrt(np.mean(x[:, -w:] ** 2)) + 1e-9
    b = np.sqrt(np.mean(x[:, :w] ** 2)) + 1e-9
    jump = float(np.max(np.abs(x[:, 0] - x[:, -1])))
    return {'rms_end_db': 20 * np.log10(a), 'rms_start_db': 20 * np.log10(b), 'level_diff_db': abs(20 * np.log10(a / b)), 'sample_jump': jump}


def master_and_export(x, out_path, target_lufs=-18.0, ceiling_db=-1.2, quality=4, loop=True, title=None):
    """Normaliza para o LUFS alvo, limita picos e grava OGG Vorbis (quality: -q:a do libvorbis).
    Se loop=True, a medição e a limitação consideram o arquivo como cíclico (emenda incluída)."""
    x = np.nan_to_num(x)
    x = x - np.mean(x, axis=1, keepdims=True)
    pre = 0.9 / (np.max(np.abs(x)) + 1e-9)          # mede sem saturar o WAV temporário
    m = measure(x * pre)
    gain = pre * 10 ** ((target_lufs - m['lufs']) / 20.0)
    y = x * gain
    if loop:
        pad = nsamp(0.01)
        ext = np.concatenate([y[:, -pad:], y, y[:, :pad]], axis=1)
        ext = limiter(ext, ceiling_db)
        y = ext[:, pad:-pad]
    else:
        y = limiter(y, ceiling_db)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    try:
        _write_wav(tmp.name, y)
        # bitexact: sem número de série aleatório no Ogg, então o mesmo script gera exatamente o mesmo arquivo
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp.name, '-fflags', '+bitexact', '-flags:a', '+bitexact',
               '-c:a', 'libvorbis', '-q:a', str(quality)]
        if title:
            cmd += ['-metadata', 'title=' + title, '-metadata', 'artist=Mundo Renda (trilha procedural)']
        cmd.append(out_path)
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(tmp.name)
    final = measure(out_path)
    final['seconds'] = round(y.shape[1] / SR, 3)
    final['bytes'] = os.path.getsize(out_path)
    final['seam'] = loop_seam_report(y) if loop else None
    return final


def spectrogram_png(path_or_array, png_path, seconds=None):
    """Desenha um espectrograma (para conferir visualmente a mixagem)."""
    from PIL import Image
    if isinstance(path_or_array, str):
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', path_or_array, '-ac', '1', '-ar', str(SR), tmp.name], check=True)
        _, d = wavfile.read(tmp.name)
        os.unlink(tmp.name)
        x = d.astype(np.float64) / 32768.0
    else:
        x = np.mean(path_or_array, axis=0) if path_or_array.ndim == 2 else path_or_array
    if seconds:
        x = x[:nsamp(seconds)]
    f, t, S = signal.spectrogram(x, fs=SR, nperseg=2048, noverlap=1024)
    S = 10 * np.log10(S + 1e-12)
    keep = f < 12000
    S = S[keep][::-1]
    S = np.clip((S - (S.max() - 80)) / 80, 0, 1)
    img = (np.stack([S ** 0.7, S ** 1.5, (1 - S) * 0.4 + S * 0.2], axis=-1) * 255).astype(np.uint8)
    Image.fromarray(img).resize((min(1600, img.shape[1]), 400)).save(png_path)
    return png_path

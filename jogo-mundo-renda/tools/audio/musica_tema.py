#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mundo Renda - Tema (tela de título). Música original, 100% sintetizada por código.

Sol maior, 92 BPM, 4/4, com levada brasileira leve (toada / bossa) e um toque cinematográfico.
Forma (66 compassos, ~2:52, loop perfeito):

  intro (4)  violão dedilhado + cordas; o vibrafone antecipa o motivo do tema
  A1    (8)  flauta canta o tema, vibrafone responde; baixo acústico em mínimas
  A2    (8)  inversão de papéis: vibrafone chama, flauta responde; fecha em ii-V para Dó
  B1    (8)  "subida" ao IV (Dó): flauta mais aguda, linha de cordas em contracanto
  C     (8)  cores de Mi menor: o violão vira solista, flauta descansa, linha cromática nas cordas
  A3    (8)  segunda metade: entram ganzá, bumbo e pandeiro grave; vibrafone harmoniza em terças
  B2    (8)  tutti, violoncelos dobram o contracanto
  T     (2)  ponte modulante (Bm7 -> E7) com virada de pandeiro e crescendo
  A4    (8)  clímax um tom acima (Lá maior)
  outro (4)  cadência de engano (E7 -> Cmaj9) que devolve a Sol; textura volta à da intro -> loop

Uso (a partir de jogo-mundo-renda/):  python3 tools/audio/musica_tema.py
Gera android/assets/www/audio/tema.ogg e imprime as medições. Determinístico (sementes fixas).
"""
import bisect
import os
import sys
import time

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth as sy  # noqa: E402

SR = sy.SR
BPM = 92.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
ROOT_DIR = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT_DIR, 'android', 'assets', 'www', 'audio', 'tema.ogg')
TARGET_LUFS = -18.0
QUALITY = 7            # libvorbis -q:a 7 (~220 kb/s): arquivo de vários MB, timbre acústico preservado
TAIL_S = 7.0           # cauda renderizada além do loop (dobrada sobre o início)

RNG = np.random.default_rng(20261007)      # humanização (ordem de chamadas fixa => determinístico)
_seed_counter = [1000]


def next_seed():
    _seed_counter[0] += 1
    return _seed_counter[0]


# ---------------------------------------------------------------------------
# Harmonia
# ---------------------------------------------------------------------------
INTRO = ['Gmaj9', 'Cmaj9', 'Gmaj9', [('D7sus4', 0), ('D7', 2)]]
A_G = ['Gmaj9', 'Em9', 'Am7', 'D7', 'Bm7', 'E7', 'Am7', [('D7sus4', 0), ('D7', 2)]]
A_G_TO_C = A_G[:7] + [[('Dm7', 0), ('G7', 2)]]
B_C = ['Cmaj9', 'D/C', 'Bm7', 'Em9', 'Am9', [('F#m7b5', 0), ('B7', 2)], [('Em7', 0), ('Em7/D', 2)],
       [('Cmaj7', 0), ('D7sus4', 2)]]
B_C_TO_A = B_C[:7] + [[('Cmaj7', 0), ('D/C', 2)]]
C_EM = ['Em9', 'C#m7b5', 'Cmaj7', [('B7sus4', 0), ('B7', 2)], 'Em9', 'A9', 'Am7', [('D7sus4', 0), ('D7', 2)]]
TRANS = ['Bm7', [('E7sus4', 0), ('E7', 2)]]
A_A = ['Amaj9', 'F#m9', 'Bm7', 'E7', 'C#m7', 'F#7', 'Bm7', [('E7sus4', 0), ('E7', 2)]]
OUTRO = ['Cmaj9', 'Am9', 'D9sus4', [('D7sus4', 0), ('D7', 2)]]

# nome, acordes por compasso, energia (escala as dinâmicas)
SECTIONS = [
    ('intro', INTRO, 0.84),
    ('A1', A_G, 0.88),
    ('A2', A_G_TO_C, 0.92),
    ('B1', B_C, 0.96),
    ('C', C_EM, 0.94),
    ('A3', A_G_TO_C, 1.00),
    ('B2', B_C_TO_A, 1.03),
    ('T', TRANS, 1.00),
    ('A4', A_A, 1.06),
    ('outro', OUTRO, 0.86),
]

SEC_START = {}
_b = 0
for _name, _ch, _e in SECTIONS:
    SEC_START[_name] = _b
    _b += len(_ch)
N_BARS = _b
LOOP_S = N_BARS * BAR

# linha do tempo de acordes: (tempo absoluto em tempos, cifra)
TIMELINE = []
for _name, _ch, _e in SECTIONS:
    for i, bar in enumerate(_ch):
        b0 = (SEC_START[_name] + i) * 4
        if isinstance(bar, str):
            TIMELINE.append((b0, bar))
        else:
            for sym, off in bar:
                TIMELINE.append((b0 + off, sym))
_TL_BEATS = [t for t, _ in TIMELINE]

_TYPES = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'maj7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10],
          'maj9': [0, 4, 7, 11, 2], 'm9': [0, 3, 7, 10, 2], '9': [0, 4, 7, 10, 2], '7sus4': [0, 5, 7, 10],
          '9sus4': [0, 5, 7, 10, 2], 'm7b5': [0, 3, 6, 10]}


def chord_pcs(sym):
    """Classes de altura (0-11) do acorde, incluindo o baixo da inversão."""
    bass = None
    if '/' in sym:
        sym, bass = sym.split('/')
    root = int(sy.midi(sym[:2] + '4' if len(sym) > 1 and sym[1] in '#b' else sym[0] + '4')) % 12
    kind = sym[2:] if len(sym) > 1 and sym[1] in '#b' else sym[1:]
    pcs = {(root + i) % 12 for i in _TYPES[kind]}
    if bass:
        pcs.add(int(sy.midi(bass + '4')) % 12)
    return pcs


def chord_at(beat):
    i = bisect.bisect_right(_TL_BEATS, beat + 1e-6) - 1
    return TIMELINE[max(0, i)][1]


def chord_spans():
    """[(início, fim, cifra)] em tempos absolutos."""
    out = []
    for k, (t, s) in enumerate(TIMELINE):
        e = TIMELINE[k + 1][0] if k + 1 < len(TIMELINE) else N_BARS * 4
        out.append((t, e, s))
    return out


# Vozes de violão: (baixo, baixo alternado, [4 notas de cima])
VOICINGS = {
    'Gmaj9': ('G2', 'D3', ['B3', 'D4', 'F#4', 'A4']),
    'Cmaj9': ('C3', 'G2', ['B3', 'D4', 'E4', 'G4']),
    'Cmaj7': ('C3', 'G2', ['B3', 'E4', 'G4', 'C5']),
    'Em9': ('E2', 'B2', ['G3', 'D4', 'F#4', 'B4']),
    'Em7': ('E2', 'B2', ['G3', 'D4', 'G4', 'B4']),
    'Em7/D': ('D3', 'B2', ['G3', 'B3', 'E4', 'G4']),
    'Am7': ('A2', 'E3', ['G3', 'C4', 'E4', 'A4']),
    'Am9': ('A2', 'E3', ['C4', 'E4', 'G4', 'B4']),
    'D7': ('D3', 'A2', ['A3', 'C4', 'F#4', 'A4']),
    'D7sus4': ('D3', 'A2', ['A3', 'C4', 'D4', 'G4']),
    'D9sus4': ('D3', 'A2', ['C4', 'E4', 'G4', 'A4']),
    'Bm7': ('B2', 'F#2', ['A3', 'D4', 'F#4', 'B4']),
    'E7': ('E2', 'B2', ['G#3', 'D4', 'E4', 'B4']),
    'E7sus4': ('E2', 'B2', ['A3', 'D4', 'E4', 'B4']),
    'Dm7': ('D3', 'A2', ['A3', 'C4', 'F4', 'A4']),
    'G7': ('G2', 'D3', ['B3', 'D4', 'F4', 'G4']),
    'D/C': ('C3', 'C3', ['A3', 'D4', 'F#4', 'A4']),
    'F#m7b5': ('F#2', 'C3', ['A3', 'C4', 'E4', 'A4']),
    'B7': ('B2', 'F#2', ['A3', 'D#4', 'F#4', 'B4']),
    'B7sus4': ('B2', 'F#2', ['A3', 'E4', 'F#4', 'B4']),
    'C#m7b5': ('C#3', 'G2', ['G3', 'B3', 'E4', 'G4']),
    'A9': ('A2', 'E3', ['C#4', 'E4', 'G4', 'B4']),
    'Amaj9': ('A2', 'E3', ['C#4', 'E4', 'G#4', 'B4']),
    'F#m9': ('F#2', 'C#3', ['A3', 'C#4', 'E4', 'G#4']),
    'C#m7': ('C#3', 'G#2', ['G#3', 'B3', 'E4', 'G#4']),
    'F#7': ('F#2', 'C#3', ['A#3', 'C#4', 'E4', 'F#4']),
}
for _s, (_bs, _al, _up) in VOICINGS.items():       # confere que toda nota pertence ao acorde
    _p = chord_pcs(_s)
    for _nn in [_bs, _al] + _up:
        assert int(sy.midi(_nn)) % 12 in _p, (_s, _nn)


def voicing(sym):
    b, a, up = VOICINGS[sym]
    return sy.midi(b), sy.midi(a), [sy.midi(u) for u in up]


def bass_root(sym):
    pc = int(sy.midi(sym.split('/')[1] + '2' if '/' in sym else
                     (sym[:2] if len(sym) > 1 and sym[1] in '#b' else sym[0]) + '2')) % 12
    n = 36 + pc
    if n > 46:
        n -= 12
    return float(n)


# ---------------------------------------------------------------------------
# Melodias (escritas à mão). Formato "NOTA:tempos", r = pausa.
# ---------------------------------------------------------------------------
FL_P1 = "r:.5 B4:.5 D5:.5 F#5:1.5 E5:.5 D5:2 B4:1 r:1.5"
FL_P2 = "r:.5 A4:.5 C5:.5 E5:1.5 D5:.5 C5:2 A4:1 r:1.5"
FL_P3 = "r:.5 D5:.5 F#5:.5 A5:1.5 B5:.5 G#5:2 F#5:.5 E5:1 r:1"
FL_P3B = "r:.5 D5:.5 F#5:.5 A5:.5 B5:.5 D6:1 B5:.5 G#5:1.5 F#5:.5 E5:1 r:1"
FL_P4 = "A5:1 E5:.5 G5:1 E5:.5 C5:1 D5:1.5 C5:.5 A4:.5 F#4:1.5"
FL_P4B = "A5:1 E5:.5 G5:1 E5:.5 C5:1 F5:1.5 E5:.5 D5:.5 B4:1.5"
FL_A2_ANS = "r:6.5 G5:.5 A5:.5 B5:1.5 r:5.5 F#5:.5 G5:.5 A5:1"
FL_B = ("E5:1 G5:.5 B5:2.5  A5:1.5 G5:.5 F#5:1 D5:1  r:.5 D5:.5 F#5:.5 A5:1.5 B5:1  G5:2.5 F#5:.5 E5:.5 D5:.5 "
        "r:.5 E5:.5 A5:.5 C6:1.5 B5:1  A5:1.5 F#5:.5 D#5:1.5 F#5:.5  G5:2 F#5:1 E5:1 ")
FL_B_END1 = "E5:.5 G5:.5 E5:.5 D5:1 C5:.5 A4:1"
FL_B_END2 = "E5:.5 G5:.5 B5:1 A5:1 F#5:1"
FL_T = "r:4 A5:2 G#5:2"
FL_OUT = "G4:1.5 r:.5 B4:.5 D5:.5 F#5:1 E5:2 D5:1 B4:1 A4:4 r:4"

GT_C_LEAD = ("B4:.5 E5:.5 F#5:.5 G5:1 F#5:.5 E5:.5 B4:.5  C#5:.5 E5:.5 G5:.5 B5:1.5 A5:.5 G5:.5 "
             "G5:1.5 E5:.5 B4:1 C5:.5 D5:.5  E5:1.5 F#5:.5 D#5:1.5 B4:.5 "
             "B4:.5 E5:.5 F#5:.5 G5:.5 B5:1 A5:.5 G5:.5  F#5:1 E5:.5 C#5:.5 E5:.5 G5:1.5 "
             "E5:1 C5:.5 A4:.5 C5:.5 E5:.5 G5:1  G5:1.5 E5:.5 F#5:1 C5:1")

VB_INTRO = "r:8.5 B4:.5 D5:.5 F#5:2.5 r:.5 A4:.5 C5:.5 E5:2.5"
VB_A1 = "r:6.5 A5:.5 G5:.5 E5:1.5 r:5.5 F#5:.5 E5:.5 C5:1.5 r:6 G#4:.5 B4:.5 C5:1 r:5 D5:.5 F#5:.5 A5:.5 C6:.5"
VB_A3_HEAD = "r:6.5 A5:.5 G5:.5 E5:1.5 r:5.5 F#5:.5 E5:.5 C5:1"
VB_T = "B4:.5 D5:.5 F#5:.5 A5:.5 B5:.5 A5:.5 F#5:.5 D5:.5 A4:.5 B4:.5 D5:.5 E5:.5 G#4:.5 B4:.5 D5:.5 E5:.5"
VB_OUT = "r:9 G5:.5 E5:.5 C5:2 r:2 C5:.5 D5:.5 F#5:1"

STR_B = "E4:4 F#4:4 D4:4 B3:2 D4:2 C4:4 C4:2 D#4:2 E4:2 D4:2 E4:2 D4:2"
STR_C = "G4:4 G4:4 E4:4 E4:2 D#4:2 D4:4 C#4:4 C4:4 C4:2 C4:2"
STR_T_LO = "D4:8"
STR_T_HI = "F#4:4 E4:4"
STR_A4 = "C#4:2 B3:2 A3:4 D4:2 F#4:2 G#4:2 D4:2 E4:4 E4:2 A#3:2 B3:2 D4:2 D4:4"
STR_OUT = "E4:4 E4:2 C4:2 C4:4 C4:4"


def parse(seq, start=0.0, transpose=0):
    """-> lista de (tempo_absoluto, midi, duração_em_tempos), comprimento total."""
    ev, b = [], start
    for tok in seq.split():
        name, d = tok.split(':')
        d = float(d)
        if name != 'r':
            ev.append((b, sy.midi(name) + transpose, d))
        b += d
    return ev, b - start


def place(section, *parts, transpose=0, expect=None):
    """Concatena trechos e posiciona no início da seção."""
    b0 = SEC_START[section] * 4
    events, total = [], 0.0
    for p in parts:
        ev, ln = parse(p, b0 + total, transpose)
        events += ev
        total += ln
    if expect is not None:
        assert abs(total - expect) < 1e-6, (section, total, expect)
    return events


def harmony_below(events, vel_scale=1.0):
    """Segunda voz: nota do acorde vigente uma terça (ou sexta/quarta) abaixo de cada nota da melodia."""
    out = []
    for b, m, d in events:
        pcs = chord_pcs(chord_at(b + min(d, 1.0) * 0.5))
        for iv in (3, 4, 8, 9, 5):
            h = m - iv
            if int(h) % 12 in pcs:
                out.append((b, h, d))
                break
    return out


# ---------------------------------------------------------------------------
# Tempo, swing e humanização
# ---------------------------------------------------------------------------
SWING8 = 0.016       # colcheias do contratempo ligeiramente atrasadas (balanço de toada)
SWING16 = 0.007


def when(beat):
    frac = beat % 1.0
    sw = 0.0
    if abs(frac - 0.5) < 1e-6:
        sw = SWING8
    elif abs(frac - 0.25) < 1e-6 or abs(frac - 0.75) < 1e-6:
        sw = SWING16
    return beat * BEAT + sw


def jit(sd=0.0035, lim=0.008):
    return float(np.clip(RNG.normal(0, sd), -lim, lim))


def energy_at(beat):
    bar = int(beat // 4)
    for name, ch, e in SECTIONS:
        if SEC_START[name] <= bar < SEC_START[name] + len(ch):
            return e
    return 1.0


# ---------------------------------------------------------------------------
# Buffers
# ---------------------------------------------------------------------------
class Stem:
    def __init__(self, n):
        self.buf = np.zeros((2, n), dtype=np.float32)

    def add(self, x, t, gain=1.0, pan=0.0):
        i = max(0, int(round(t * SR)))
        if i >= self.buf.shape[1]:
            return
        m = min(len(x), self.buf.shape[1] - i)
        ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        self.buf[0, i:i + m] += (x[:m] * (np.cos(ang) * gain)).astype(np.float32)
        self.buf[1, i:i + m] += (x[:m] * (np.sin(ang) * gain)).astype(np.float32)

    def add_stereo(self, x, t, gain=1.0):
        i = max(0, int(round(t * SR)))
        m = min(x.shape[1], self.buf.shape[1] - i)
        if m > 0:
            self.buf[:, i:i + m] += (x[:, :m] * gain).astype(np.float32)


# ---------------------------------------------------------------------------
# Instrumentos próprios (cordas com serra polyBLEP, tremolo do vibrafone)
# ---------------------------------------------------------------------------
def blep_saw(finst, phase0=0.0):
    dt = finst / SR
    ph = (np.cumsum(dt) + phase0) % 1.0
    y = 2.0 * ph - 1.0
    m1 = ph < dt
    x = ph[m1] / dt[m1]
    y[m1] -= x + x - x * x - 1.0
    m2 = ph > 1.0 - dt
    x = (ph[m2] - 1.0) / dt[m2]
    y[m2] -= x * x + x + x + 1.0
    return y


def strings_voice(notes, dur, seed, attack=0.35, release=0.7, bright=0.4, vib=6.0, detunes=(-7, 0, 6)):
    """Naipe de cordas (soma das notas): serras desafinadas, vibrato atrasado, filtro e formantes de corpo."""
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur + release)
    t = sy.tarr(n)
    out = np.zeros(n)
    for note in notes:
        f0 = sy.freq(note)
        for c in detunes:
            rate = rng.uniform(4.6, 5.6)
            ramp = np.clip((t - 0.25) / 0.6, 0, 1)
            cents = c + vib * ramp * np.sin(2 * np.pi * rate * t + rng.uniform(0, 6.3)) \
                + 2.5 * np.sin(2 * np.pi * rng.uniform(0.15, 0.4) * t + rng.uniform(0, 6.3))
            out += blep_saw(f0 * 2 ** (cents / 1200.0), rng.uniform(0, 1))
    out /= max(1, len(notes) * len(detunes))
    cut = 1100 + 2200 * bright
    out = sy.lowpass(out, cut, order=2)
    out = sy.lowpass(out, cut * 1.8, order=1)
    out = sy.peak_eq(out, 420, 2.5, 0.9)
    out = sy.peak_eq(out, 1500, 1.5, 1.2)
    # envelope: ataque em curva suave, sustentação, soltura
    na, nr = sy.nsamp(attack), sy.nsamp(release)
    nd = max(1, sy.nsamp(dur))
    env = np.ones(n)
    na = min(na, nd)
    env[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    env[nd:] = np.exp(-np.linspace(0, 5, n - nd)) * np.linspace(1, 0, n - nd)
    return out * env


def vibes_note(m, dur, vel, seed, motor=0.10):
    x = sy.vibes(m, dur, vel, motor=False, seed=seed)
    if motor:
        x = x * (1 + motor * np.sin(2 * np.pi * 4.3 * sy.tarr(len(x)) + seed % 7))
    return x


def flute_note(m, dur_s, vel, seed):
    x = sy.flute(m, dur_s, vel, seed=seed)
    if dur_s > 0.6:              # "messa di voce": cresce um pouco no meio das notas longas
        u = np.linspace(0, 1, len(x))
        x = x * (0.9 + 0.16 * np.sin(np.pi * u) ** 1.5)
    return x


def swell_noise(dur, seed):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur)
    u = np.linspace(0, 1, n)
    out = np.zeros((2, n))
    for ch in range(2):
        x = sy.pink(n, rng)
        lo = sy.lowpass(x, 700)
        hi = sy.bandpass(x, 700, 4000)
        out[ch] = lo * u ** 2 + hi * u ** 3
    out[:, -sy.nsamp(0.03):] *= np.linspace(1, 0, sy.nsamp(0.03))
    return out * 0.08


def boom(vel, seed):
    """Tímpano suave sintetizado (início do clímax)."""
    rng = np.random.default_rng(seed)
    n = sy.nsamp(2.0)
    t = sy.tarr(n)
    f = 58 + 22 * np.exp(-t / 0.06)
    s = np.sin(sy.osc_phase(f)) * np.exp(-t / 0.55)
    s += np.sin(sy.osc_phase(f * 1.5)) * np.exp(-t / 0.3) * 0.35
    s += sy.lowpass(rng.standard_normal(n), 600) * np.exp(-t / 0.03) * 0.25
    return s * vel * 0.6


# ---------------------------------------------------------------------------
# Execução das partes
# ---------------------------------------------------------------------------
def play_flute(stem, events, gain=1.0, pan=0.08):
    for b, m, d in events:
        e = energy_at(b)
        vel = e * (0.78 + 0.07 * np.clip((m - 76) / 12.0, -1, 1.6)) * RNG.uniform(0.93, 1.04)
        dur = d * BEAT + 0.045
        stem.add(flute_note(m, dur, vel, next_seed()), when(b) + jit(), gain, pan)


def play_vibes(stem, events, gain=1.0, pan=0.5, vel0=0.7, ring=1.3):
    for b, m, d in events:
        e = energy_at(b)
        vel = vel0 * e * RNG.uniform(0.88, 1.06)
        dur = d * BEAT + ring
        stem.add(vibes_note(m, dur, vel, next_seed()), when(b) + jit(), gain, pan)


def play_lead_guitar(stem, events, gain=1.0, pan=-0.12):
    for b, m, d in events:
        e = energy_at(b)
        vel = e * 0.82 * RNG.uniform(0.9, 1.05) * (1.05 if b % 1 == 0 else 0.95)
        dur = min(3.0, d * BEAT + 0.35)
        x = sy.nylon(m, dur, vel, bright=0.6, seed=next_seed(), t60=1.7)
        stem.add(x, when(b) + jit(), gain, pan)


def play_strings_line(stem, events, gain=1.0, pan=-0.2, bright=0.45, attack=0.4):
    for b, m, d in events:
        e = energy_at(b)
        x = strings_voice([m], d * BEAT + 0.08, next_seed(), attack=attack, release=0.7, bright=bright)
        stem.add(x * e, when(b) + jit(0.006), gain, pan)


ARP8 = [('B', 0.0), (0, 0.5), (1, 1.0), (2, 1.5), ('A', 2.0), (3, 2.5), (2, 3.0), (1, 3.5)]
ARP8B = [('B', 0.0), (1, 0.5), (2, 1.0), (3, 1.5), ('A', 2.0), (2, 2.5), (1, 3.0), (0, 3.5)]
ARPW = [('B', 0.0), (0, 0.5), (1, 1.0), (2, 1.5), (3, 2.0), ('T', 2.5), (3, 3.0), (2, 3.5)]


def guitar_arps(stem, bars, pattern, gain=1.0, pan=-0.35, vel0=0.68):
    spans = chord_spans()
    for bar in bars:
        b0 = bar * 4
        for slot, off in pattern:
            beat = b0 + off
            sym = chord_at(beat)
            st, en, _ = next(s for s in spans if s[0] <= beat + 1e-6 < s[1])
            bs, al, up = voicing(sym)
            if slot == 'B' or (slot == 'A' and abs(st - beat) < 1e-6):
                note, v = bs, 0.95
            elif slot == 'A':
                note, v = al, 0.8
            elif slot == 'T':
                note, v = up[1] + 12, 0.7
            else:
                note, v = up[slot], 0.72 + 0.08 * slot / 3
            if off in (0.0, 2.0):
                v *= 1.06
            ring = min(2.6, (en - beat) * BEAT + 0.3)
            vel = vel0 * v * energy_at(beat) * RNG.uniform(0.88, 1.06)
            x = sy.nylon(note, max(0.5, ring), vel, bright=0.42, seed=next_seed())
            stem.add(x, when(beat) + jit(), gain, pan)


BOSSA_ODD = [0.0, 1.0, 2.5, 3.5]
BOSSA_EVEN = [0.5, 1.5, 3.0]


def strum(stem, notes, t, vel, gain, pan, spread=0.014, dur=0.5, bright=0.4, up=False):
    order = list(notes)[::-1] if up else list(notes)
    for k, m in enumerate(order):
        v = vel * (1 - 0.06 * k) * RNG.uniform(0.9, 1.05)
        x = sy.nylon(m, dur, v, bright=bright, seed=next_seed())
        stem.add(x, t + k * spread * RNG.uniform(0.8, 1.2), gain, pan)


def guitar_bossa(stem, bars, gain=1.0, pan=0.32, vel0=0.5):
    for bar in bars:
        b0 = bar * 4
        for off in (0.0, 2.0):                      # polegar
            beat = b0 + off
            sym = chord_at(beat)
            bs, al, up = voicing(sym)
            note = bs if (off == 0.0 or chord_at(beat - 0.01) != sym) else al
            x = sy.nylon(note, 1.8 * BEAT, vel0 * 1.1 * energy_at(beat) * RNG.uniform(0.9, 1.05),
                         bright=0.35, seed=next_seed())
            stem.add(x, when(beat) + jit(), gain, pan)
        for off in (BOSSA_ODD if bar % 2 == 0 else BOSSA_EVEN):
            beat = b0 + off
            look = beat + 0.5 if (off % 1) == 0.5 and (beat + 0.5) % 2 == 0 else beat   # antecipação
            sym = chord_at(look)
            _, _, up = voicing(sym)
            strum(stem, up[:4], when(beat) + jit(), vel0 * 0.8 * energy_at(beat), gain, pan,
                  spread=0.009, dur=0.42 * BEAT + 0.12, bright=0.38, up=(off % 1 == 0.5))


def bass_line(stem, bars, style, gain=1.0, approach=False):
    for bar in bars:
        b0 = bar * 4
        s1 = chord_at(b0)
        s2 = chord_at(b0 + 2)
        nxt = chord_at(b0 + 4) if bar + 1 < N_BARS else TIMELINE[0][1]
        r1, r2, rn = bass_root(s1), bass_root(s2), bass_root(nxt)

        def fifth(r, s):
            iv = 6 if 'b5' in s else 7
            return r + iv if r + iv <= 50 else r + iv - 12

        notes = []
        if style == 'whole':
            notes = [(0, r1, 3.7, 0.85)] if s1 == s2 else [(0, r1, 1.9, 0.85), (2, r2, 1.8, 0.8)]
        elif style == 'half':
            notes = [(0, r1, 1.9, 0.9), (2, fifth(r1, s1) if s1 == s2 else r2, 1.8, 0.8)]
        elif style == 'bossa':
            if s1 == s2:
                notes = [(0, r1, 1.45, 0.95), (1.5, fifth(r1, s1), 0.45, 0.6), (2, fifth(r1, s1), 1.9, 0.8)]
            else:
                notes = [(0, r1, 1.45, 0.95), (1.5, r2, 0.45, 0.55), (2, r2, 1.9, 0.82)]
            if approach and rn != r2 and nxt != s2:
                last = notes[-1]
                notes[-1] = (last[0], last[1], 1.4, last[3])
                ap = rn + (1 if (bar % 2 == 0) else -1)
                notes.append((3.5, ap, 0.45, 0.55))
        for off, m, d, v in notes:
            beat = b0 + off
            vel = 0.8 * v * energy_at(beat) * RNG.uniform(0.92, 1.05)
            x = sy.bass_upright(m, d * BEAT + 0.06, vel, seed=next_seed())
            stem.add(x, when(beat) + jit(0.003), gain, 0.0)


def pad_bed(stem_l, bars, gain=1.0, bright=0.3):
    """Colchão de cordas por acorde, estéreo (dois naipes com sementes diferentes, abertos L/R)."""
    for st, en, sym in chord_spans():
        if int(st // 4) not in bars:
            continue
        _, _, up = voicing(sym)
        notes = [up[0], up[1], up[2]]
        e = energy_at(st)
        dur = (en - st) * BEAT + 0.15
        L = strings_voice(notes, dur, next_seed(), attack=0.9, release=1.3, bright=bright, vib=4.0,
                          detunes=(-9, 4))
        R = strings_voice(notes, dur, next_seed(), attack=0.9, release=1.3, bright=bright, vib=4.0,
                          detunes=(-3, 9))
        x = np.vstack([L * 0.92 + R * 0.25, R * 0.92 + L * 0.25]) * e
        stem_l.add_stereo(x, when(st) - 0.05, gain)


def vibes_dyads(stem, bars, offs=(0.0,), idx=(1, 2), gain=1.0, pan=0.5, vel0=0.45, oct_=0):
    for bar in bars:
        for off in offs:
            beat = bar * 4 + off
            _, _, up = voicing(chord_at(beat))
            for k, i in enumerate(idx):
                v = vel0 * energy_at(beat) * RNG.uniform(0.9, 1.05)
                x = vibes_note(up[i] + 12 * oct_, 2.2 * BEAT, v, next_seed())
                stem.add(x, when(beat) + jit() + 0.012 * k, gain, pan)


# percussão --------------------------------------------------------------------------------
def perc_groove(lo, hi, bars, shaker16=True, plat=False, grave=True, kick=True, tapa=False, shaker_vel=0.5):
    for bar in bars:
        b0 = bar * 4
        e = energy_at(b0)
        if kick:
            for off, v in ((0.0, 0.8), (1.5, 0.28), (2.0, 0.5)):
                x = sy.kick(v * e * RNG.uniform(0.92, 1.04), dur=0.4, f_hi=95, f_lo=50)
                lo.add(x, when(b0 + off) + jit(0.002), 1.0, 0.0)
        if grave:
            for off, v in ((2.0, 0.55), (3.5, 0.22)):
                x = sy.pandeiro('grave', v * e * RNG.uniform(0.9, 1.05), seed=next_seed())
                lo.add(x, when(b0 + off) + jit(0.003), 1.0, 0.15)
        step = 0.25 if shaker16 else 0.5
        acc16 = [1.0, 0.38, 0.62, 0.42]
        k = 0
        o = 0.0
        while o < 4 - 1e-6:
            a = acc16[int(round(o / 0.25)) % 4] if shaker16 else (0.6 if o % 1 else 1.0)
            x = sy.shaker(shaker_vel * a * e * RNG.uniform(0.85, 1.1), dur=0.085, seed=next_seed(), bright=0.35)
            hi.add(x, when(b0 + o) + jit(0.004), 1.0, -0.45)
            o += step
            k += 1
        if plat:
            for off in (0.5, 1.5, 2.5, 3.5):
                x = sy.pandeiro('plat', 0.3 * e * RNG.uniform(0.85, 1.1), seed=next_seed())
                hi.add(x, when(b0 + off) + jit(0.004), 1.0, 0.4)
        if tapa:
            for off in (1.0, 3.0):
                x = sy.pandeiro('tapa', 0.28 * e * RNG.uniform(0.9, 1.05), seed=next_seed())
                hi.add(x, when(b0 + off) + jit(0.004), 1.0, 0.3)


# ---------------------------------------------------------------------------
# Arranjo
# ---------------------------------------------------------------------------
def bars_of(*names):
    out = []
    for nm in names:
        s = SEC_START[nm]
        out += list(range(s, s + len(dict((n, c) for n, c, _ in SECTIONS)[nm])))
    return out


def arrange(n_total):
    st = {k: Stem(n_total) for k in ('gtr', 'bass', 'flute', 'vibes', 'strings', 'perc_lo', 'perc_hi', 'fx')}

    # --- flauta ---
    fl = []
    fl += place('A1', FL_P1, FL_P2, FL_P3, FL_P4, expect=32)
    fl += place('A2', FL_A2_ANS, FL_P3B.replace('r:.5 ', '', 1), FL_P4B, expect=32)
    fl += place('B1', FL_B, FL_B_END1, expect=32)
    fl += place('A3', FL_P1, FL_P2, FL_P3B, FL_P4B, expect=32)
    fl_b2 = place('B2', FL_B, FL_B_END2, expect=32)
    fl += fl_b2
    fl += place('T', FL_T, expect=8)
    fl_a4 = place('A4', FL_P1, FL_P2, FL_P3B, FL_P4, transpose=2, expect=32)
    fl += fl_a4
    fl += place('outro', FL_OUT, expect=16)
    play_flute(st['flute'], fl)

    # --- vibrafone (respostas, chamadas e segunda voz) ---
    vb = []
    vb += place('intro', VB_INTRO, expect=16)
    vb += place('A1', VB_A1, expect=32)
    vb += place('A2', FL_P1, FL_P2, expect=16)
    a2_lead = [e for e in fl if SEC_START['A2'] * 4 + 16 <= e[0] < SEC_START['A2'] * 4 + 32]
    vb_h = harmony_below(a2_lead)
    vb += place('A3', VB_A3_HEAD, expect=16.5)
    a3_lead = [e for e in fl if SEC_START['A3'] * 4 + 16 <= e[0] < SEC_START['A3'] * 4 + 32]
    vb_h += harmony_below(a3_lead)
    vb_h += harmony_below(fl_b2)
    vb += place('T', VB_T, expect=8)
    vb += place('A4', VB_A3_HEAD, transpose=2, expect=16.5)
    vb_h += harmony_below([e for e in fl_a4 if e[0] >= SEC_START['A4'] * 4 + 16])
    vb += place('outro', VB_OUT, expect=16)
    play_vibes(st['vibes'], vb, pan=0.5, vel0=0.72)
    play_vibes(st['vibes'], vb_h, pan=0.55, vel0=0.48, ring=0.9)
    vibes_dyads(st['vibes'], bars_of('B1'), offs=(0.0,), idx=(2, 3), vel0=0.42)
    vibes_dyads(st['vibes'], bars_of('C'), offs=(0.0, 2.5), idx=(1, 2), vel0=0.36)

    # --- violões ---
    guitar_arps(st['gtr'], bars_of('intro', 'A1'), ARP8, vel0=0.72)
    guitar_arps(st['gtr'], bars_of('A2'), ARP8B, vel0=0.70)
    guitar_arps(st['gtr'], bars_of('B1'), ARPW, vel0=0.64)
    lead_c = place('C', GT_C_LEAD, expect=32)
    play_lead_guitar(st['gtr'], lead_c)
    guitar_bossa(st['gtr'], bars_of('C'), vel0=0.42)
    guitar_arps(st['gtr'], bars_of('A3'), ARP8, vel0=0.6)
    guitar_bossa(st['gtr'], bars_of('A3'), vel0=0.45)
    guitar_arps(st['gtr'], bars_of('B2'), ARPW, vel0=0.58)
    guitar_bossa(st['gtr'], bars_of('B2'), vel0=0.45)
    # ponte: acordes rasgueados largos
    tb = SEC_START['T'] * 4
    for off, up_ in ((0.0, False), (2.5, True), (4.0, False), (6.0, False), (7.0, True)):
        sym = chord_at(tb + off)
        bs, al, upn = voicing(sym)
        strum(st['gtr'], [bs] + upn, when(tb + off) + jit(), 0.62 * energy_at(tb + off), 1.0, 0.3,
              spread=0.02, dur=1.6 if off in (0.0, 4.0) else 0.9, bright=0.45, up=up_)
    guitar_arps(st['gtr'], bars_of('T'), ARP8, vel0=0.5)
    guitar_arps(st['gtr'], bars_of('A4'), ARP8, vel0=0.6)
    guitar_bossa(st['gtr'], bars_of('A4'), vel0=0.47)
    guitar_arps(st['gtr'], bars_of('outro'), ARP8, vel0=0.7)

    # --- baixo ---
    bass_line(st['bass'], bars_of('intro'), 'whole')
    bass_line(st['bass'], bars_of('A1'), 'half')
    bass_line(st['bass'], bars_of('A2', 'B1', 'C'), 'bossa')
    bass_line(st['bass'], bars_of('A3', 'B2', 'T', 'A4'), 'bossa', approach=True)
    bass_line(st['bass'], bars_of('outro'), 'half')

    # --- cordas ---
    pad_bed(st['strings'], set(bars_of('intro', 'A1', 'A2')), gain=0.85, bright=0.25)
    pad_bed(st['strings'], set(bars_of('B1', 'C')), gain=1.0, bright=0.32)
    pad_bed(st['strings'], set(bars_of('A3')), gain=0.9, bright=0.3)
    pad_bed(st['strings'], set(bars_of('B2', 'T', 'A4')), gain=1.05, bright=0.36)
    pad_bed(st['strings'], set(bars_of('outro')), gain=0.9, bright=0.25)
    play_strings_line(st['strings'], place('B1', STR_B, expect=32), gain=0.85)
    play_strings_line(st['strings'], place('C', STR_C, expect=32), gain=0.8, pan=0.25)
    play_strings_line(st['strings'], place('B2', STR_B, expect=32), gain=0.95)
    play_strings_line(st['strings'], place('B2', STR_B, transpose=-12, expect=32), gain=0.75, pan=0.2,
                      bright=0.3)
    play_strings_line(st['strings'], place('T', STR_T_LO, expect=8), gain=0.9, pan=-0.25, attack=1.5)
    play_strings_line(st['strings'], place('T', STR_T_HI, expect=8), gain=0.8, pan=0.25, attack=1.2)
    play_strings_line(st['strings'], place('A4', STR_A4, expect=32), gain=0.95)
    play_strings_line(st['strings'], place('A4', STR_A4, transpose=-12, expect=32), gain=0.6, pan=0.2,
                      bright=0.3)
    play_strings_line(st['strings'], place('outro', STR_OUT, expect=16), gain=0.75)

    # --- percussão (segunda metade) ---
    perc_groove(st['perc_lo'], st['perc_hi'], bars_of('C')[4:], shaker16=False, kick=False, grave=False,
                shaker_vel=0.45)
    perc_groove(st['perc_lo'], st['perc_hi'], bars_of('A3'), shaker_vel=0.5)
    perc_groove(st['perc_lo'], st['perc_hi'], bars_of('B2'), plat=True, shaker_vel=0.52)
    perc_groove(st['perc_lo'], st['perc_hi'], [SEC_START['T']], plat=True, shaker_vel=0.5)
    perc_groove(st['perc_lo'], st['perc_hi'], bars_of('A4'), plat=True, tapa=True, shaker_vel=0.55)
    # virada de pandeiro na ponte (semicolcheias em crescendo) e entrada do clímax
    tb2 = (SEC_START['T'] + 1) * 4
    for k in range(16):
        o = k * 0.25
        v = 0.15 + 0.4 * (k / 15.0)
        kind = 'grave' if k % 4 == 0 else ('tapa' if k % 2 == 0 else 'plat')
        x = sy.pandeiro(kind, v * RNG.uniform(0.9, 1.05), seed=next_seed())
        (st['perc_lo'] if kind == 'grave' else st['perc_hi']).add(x, when(tb2 + o) + jit(0.003), 1.0, 0.2)
    st['fx'].add_stereo(swell_noise(BAR * 2, 77), when(SEC_START['T'] * 4))
    st['perc_lo'].add(boom(0.9, 5), when(SEC_START['A4'] * 4), 1.0, 0.0)
    # o último suspiro da percussão no primeiro tempo do outro
    ob = SEC_START['outro'] * 4
    st['perc_lo'].add(sy.kick(0.55, dur=0.5, f_hi=90, f_lo=48), when(ob), 1.0, 0.0)
    st['perc_lo'].add(sy.pandeiro('grave', 0.4, seed=9), when(ob + 2) + 0.004, 1.0, 0.15)
    return st


# ---------------------------------------------------------------------------
# Mixagem e master
# ---------------------------------------------------------------------------
STEM_GAIN = {'gtr': 0.85, 'bass': 0.95, 'flute': 1.25, 'vibes': 0.95, 'strings': 0.55,
             'perc_lo': 0.42, 'perc_hi': 0.55, 'fx': 0.6}
SEND = {'gtr': 0.22, 'bass': 0.03, 'flute': 0.34, 'vibes': 0.32, 'strings': 0.38,
        'perc_lo': 0.05, 'perc_hi': 0.16, 'fx': 0.3}


def process_stem(name, x):
    x = x.astype(np.float64)
    if name == 'gtr':
        x = sy.highpass(x, 105)
        x = sy.peak_eq(x, 3200, -1.5, 0.8)
    elif name == 'bass':
        x = sy.highpass(x, 38)
        x = sy.lowpass(x, 2200)
    elif name == 'flute':
        x = sy.highpass(x, 160)
        x = sy.lowpass(x, 7000)
        x = sy.delay_fx(x, time=BEAT * 0.75, fb=0.28, wet=0.13, lp=2800)
    elif name == 'vibes':
        x = sy.highpass(x, 160)
        x = sy.lowpass(x, 7500)
    elif name == 'strings':
        x = sy.highpass(x, 120)
        x = sy.lowpass(x, 5500)
        x = sy.stereo_widen(x, 0.25)
    elif name == 'perc_lo':
        x = sy.highpass(x, 36)
        x = sy.lowpass(x, 6000)
    elif name == 'perc_hi':
        x = sy.highpass(x, 400)
        x = sy.lowpass(x, 7200)
        x = sy.lowpass(x, 9000, order=1)
    elif name == 'fx':
        x = sy.highpass(x, 120)
    return x


def circular(fn, x, pad_s=3.0):
    """Aplica um processador com memória como se o sinal fosse cíclico (emenda sem degrau)."""
    p = sy.nsamp(pad_s)
    ext = np.concatenate([x[:, -p:], x, x[:, :p]], axis=1)
    return fn(ext)[:, p:-p]


def render():
    t0 = time.time()
    n_total = sy.nsamp(LOOP_S + TAIL_S)
    stems = arrange(n_total)
    t1 = time.time()
    ir = sy.make_ir(t60=2.4, predelay=0.024, bright=0.42, seed=11)
    mix = np.zeros((2, n_total))
    send = np.zeros((2, n_total))
    levels = {}
    for name, stem in stems.items():
        x = process_stem(name, stem.buf) * STEM_GAIN[name]
        stem.buf = None
        levels[name] = round(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12), 1)
        mix += x
        send += x * SEND[name]
    send = sy.lowpass(sy.highpass(send, 220), 6500)
    wet = np.vstack([signal.oaconvolve(send[c], ir[c])[:n_total] for c in range(2)])
    mix += wet * 0.42
    mix = sy.highpass(mix, 28)
    mix = sy.peak_eq(mix, 8000, -1.5, 0.7)        # alisa o topo (o jogo toca por horas)
    loop = sy.seamless_loop(mix, LOOP_S)
    loop *= 0.5 / (np.max(np.abs(loop)) + 1e-9)
    loop = circular(lambda y: sy.compress(y, thresh_db=-17, ratio=1.8, attack=0.025, release=0.3), loop)
    t2 = time.time()
    return loop, levels, (t1 - t0, t2 - t1)


def main():
    t0 = time.time()
    loop, levels, tm = render()
    res = sy.master_and_export(loop, OUT, target_lufs=TARGET_LUFS, ceiling_db=-1.2, quality=QUALITY, loop=True,
                               title='Mundo Renda - Tema')
    res['file'] = os.path.relpath(OUT, ROOT_DIR)
    res['bars'] = N_BARS
    res['bpm'] = BPM
    res['stem_rms_db'] = levels
    res['render_s'] = round(time.time() - t0, 1)
    print(res)
    return res


if __name__ == '__main__':
    main()

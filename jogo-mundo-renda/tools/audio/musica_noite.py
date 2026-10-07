#!/usr/bin/env python3
"""Mundo Renda - "Noite na Vila" (balada noturna, Fá maior, 72 BPM, 4/4).

Música original, 100% sintetizada por código (nenhum sample, nenhuma melodia existente).
A vila descansa: violão dedilhado (p-i-m-a), Rhodes cantando pouco e bonito, marimba
respondendo, colchão quente, baixo macio. Só a parte do meio ganha ganzá e vassourinha.

Forma (48 compassos = 160,0 s, loop perfeito: a coda prepara a volta da introdução):
  Intro (4)  Fmaj9 | Bbmaj9/F | Fmaj9 | Gm9 C7sus4      violão + colchão + baixo em pedal; vibrafone prenuncia a
                                                         célula do C, Rhodes "anuncia" a cabeça do tema, marimba responde
  A     (8)  Fmaj9 | Em7 A7 | Dm9 | Cm9 F13 |           tema no Rhodes (sexta ascendente C-A, desce em graus),
             Bbmaj9 | Bbm6 Eb9 | Am7 D7b9 | Gm9 C7sus4  marimba responde nos vazios; baixo macio
  A'    (8)  mesma harmonia, final Gm9 C9 (engano p/ Dm)  tema variado (giro ornamental, nova curva nos
                                                         compassos 3-4 e 7-8), contrabaixo entra, antecipações
  B     (8)  Dm9 | G13 | Dm9 | G13 |                     groove dórico em baião lento: pergunta da marimba,
             Bbmaj7 | A7sus4 A7 | Dm9 | Gm9 C7sus4       resposta do Rhodes; ganzá, vassourinha e zabumba bem leves
  C     (8)  Fmaj7 | Em7 | Dm9 | Cmaj7 |                 "escada" diatônica descendente; vibrafone canta uma
             Bbmaj7 | Am7 | Gm9 | C7sus4 C9              sequência (3a-9a-7a de cada acorde), Rhodes em décimas
                                                         paralelas com o baixo; violão em acordes arpejados
  A''   (8)  harmonia do A                               tema completo (sobe ao Dó6), vibrafone em terças/sextas
  Coda  (4)  Fmaj9 | Bbmaj9 | Am7 Abmaj7 | Gm9 C7sus4    fragmentos do tema; Sol comum sobre Am7->Abmaj7;
                                                         termina na 7a do C7sus4; o violão antecipa o Fmaj9 e cai na Intro

Humanização: atraso de swing leve nas colcheias, jitter de tempo (+-8 ms), dinâmica variável,
acordes arpejados com alguns ms por corda. Mix: baixo no centro, violão à esquerda,
marimba/vibrafone à direita, Rhodes levemente à direita com eco pingue-pongue em colcheia pontuada,
reverb de sala noturna por envio, compressão de barramento suave e cíclica (sem degrau na emenda).
O limitador de sy.master_and_export é trocado (só neste processo) por uma versão com o filtro de
recuperação iniciado em repouso: a original abafa os primeiros ~0,3 s do arquivo (degrau na emenda).

Uso (a partir de jogo-mundo-renda/):  python3 tools/audio/musica_noite.py
Saída: android/assets/www/audio/noite.ogg
"""
import os
import re
import sys
import time
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np                      # noqa: E402
from scipy import signal               # noqa: E402
from scipy.ndimage import maximum_filter1d  # noqa: E402

import synth as sy                     # noqa: E402

SR = sy.SR
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'android', 'assets', 'www', 'audio', 'noite.ogg')

BPM = 72.0
BEAT = 60.0 / BPM
SWING8 = 0.035          # fração de tempo que as colcheias do contratempo atrasam (~29 ms): balanço preguiçoso
SWING16 = 0.018         # semicolcheias ímpares
TARGET_LUFS = -19.0
QUALITY = 4
PRE = 1.0               # pré-rolagem (s): eventos antes do tempo 0 vão para o fim do loop
TAIL = 7.0              # cauda renderizada depois do fim (dobrada sobre o início)

# ---------------------------------------------------------------------------
# Harmonia e forma
# ---------------------------------------------------------------------------
H_A = [['Fmaj9'], ['Em7', 'A7'], ['Dm9'], ['Cm9', 'F13'],
       ['Bbmaj9'], ['Bbm6', 'Eb9'], ['Am7', 'D7b9'], ['Gm9', 'C7sus4']]
FORM = [
    ('intro', [['Fmaj9'], ['Bbmaj9/F'], ['Fmaj9'], ['Gm9', 'C7sus4']]),
    ('A', H_A),
    ('A2', H_A[:7] + [['Gm9', 'C9']]),
    ('B', [['Dm9'], ['G13'], ['Dm9'], ['G13'], ['Bbmaj7'], ['A7sus4', 'A7'], ['Dm9'], ['Gm9', 'C7sus4']]),
    ('C', [['Fmaj7'], ['Em7'], ['Dm9'], ['Cmaj7'], ['Bbmaj7'], ['Am7'], ['Gm9'], ['C7sus4', 'C9']]),
    ('A3', H_A),
    ('coda', [['Fmaj9'], ['Bbmaj9'], ['Am7', 'Abmaj7'], ['Gm9', 'C7sus4']]),
]

BARS = []               # (seção, índice do compasso na seção, acordes)
SEC_BAR = {}            # seção -> compasso inicial
for _name, _harm in FORM:
    SEC_BAR[_name] = len(BARS)
    for _k, _ch in enumerate(_harm):
        BARS.append((_name, _k, _ch))
NBARS = len(BARS)
LOOP = NBARS * 4 * BEAT                       # 160,0 s
N_TOTAL = sy.nsamp(PRE + LOOP + TAIL)

# segmentos de acorde: (batida global inicial, duração em batidas, cifra, seção)
SEGS = []
for _b, (_name, _k, _chs) in enumerate(BARS):
    _d = 4.0 / len(_chs)
    for _j, _c in enumerate(_chs):
        SEGS.append((_b * 4 + _j * _d, _d, _c, _name))

# ---------------------------------------------------------------------------
# Teoria: análise de cifras e condução de vozes
# ---------------------------------------------------------------------------
PCN = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
QUAL = {
    'maj7': [0, 4, 7, 11], 'maj9': [0, 4, 7, 11, 14], 'm7': [0, 3, 7, 10], 'm9': [0, 3, 7, 10, 14],
    '7': [0, 4, 7, 10], '7sus4': [0, 5, 7, 10], '9': [0, 4, 7, 10, 14], '13': [0, 4, 10, 14, 21],
    '7b9': [0, 4, 7, 10, 13], 'm6': [0, 3, 7, 9],
}


def pc_of(name):
    return (PCN[name[0]] + name[1:].count('#') - name[1:].count('b')) % 12


def parse(sym):
    """Cifra -> (classe da fundamental, {classe: intervalo}, classe do baixo)."""
    bass = None
    if '/' in sym:
        sym, bass = sym.split('/')
    m = re.match(r'^([A-G][#b]?)(.*)$', sym)
    r = pc_of(m.group(1))
    iv = QUAL[m.group(2)]
    pcs = {(r + i) % 12: i for i in iv}
    return r, pcs, (r if bass is None else pc_of(bass))


def voice(sym, prev, lo, hi, k, center, min_gap=2, max_gap=9):
    """Escolhe k notas do acorde em [lo, hi] com 3a (ou 4a sus) e 7a (ou 6a) obrigatórias,
    preferindo tensões (9a, 13a) e o menor movimento em relação ao voicing anterior."""
    r, pcs, _ = parse(sym)
    third = next(p for p, i in pcs.items() if i in (3, 4, 5))
    sev = next((p for p, i in pcs.items() if i in (9, 10, 11)), None)
    colors = {p for p, i in pcs.items() if i > 12}
    cands = [n for n in range(lo, hi + 1) if n % 12 in pcs]
    best, bcost = None, 1e9
    for combo in combinations(cands, k):
        g = np.diff(combo)
        if np.any(g < min_gap) or np.any(g > max_gap):
            continue
        cls = [n % 12 for n in combo]
        if len(set(cls)) < k or third not in cls or (sev is not None and sev not in cls):
            continue
        cost = 0.3 * abs(np.mean(combo) - center)
        if prev is not None:
            cost += 0.5 * sum(abs(a - b) for a, b in zip(combo, prev))
        if r in cls:
            cost += 1.2
        if colors & set(cls):
            cost -= 1.0
            if (r + 7) % 12 in cls:
                cost += 0.6
        if cost < bcost:
            best, bcost = combo, cost
    return list(best)


def low_note(pc, lo, hi):
    for n in range(lo, hi + 1):
        if n % 12 == pc:
            return n
    raise ValueError(pc)


# voicings calculados em ordem (condução de vozes contínua)
GTR_V, PAD_V = [], []
_pg, _pp = None, None
for _s in SEGS:
    _pg = voice(_s[2], _pg, 57, 74, 3, 65.0)
    _pp = voice(_s[2], _pp, 53, 77, 4, 64.0, min_gap=2, max_gap=10)
    GTR_V.append(_pg)
    PAD_V.append(_pp)


def gtr_bass(sym):
    """(p, p2) do polegar: baixo do acorde e a quinta (acima se couber, senão abaixo)."""
    r, pcs, b = parse(sym)
    p = low_note(b, 40, 52)
    if b != r:
        return p, low_note(r, 43, 55)
    p2 = p + 7 if p + 7 <= 55 else p - 5
    return p, p2


def bass_root(sym):
    _, _, b = parse(sym)
    return low_note(b, 38, 49)


def seg_index_at(gb):
    for k in range(len(SEGS) - 1, -1, -1):
        if SEGS[k][0] <= gb + 1e-9:
            return k
    return 0


# ---------------------------------------------------------------------------
# Tempo, humanização e buffers
# ---------------------------------------------------------------------------
HR = np.random.default_rng(2024)        # humanização (determinística)


def tsec(gb):
    """Batida global -> segundos, com swing leve no contratempo."""
    t = gb * BEAT
    fr = gb % 1.0
    if abs(fr - 0.5) < 1e-6:
        t += SWING8 * BEAT
    elif abs(fr - 0.25) < 1e-6 or abs(fr - 0.75) < 1e-6:
        t += SWING16 * BEAT
    return t


def jit(ms=7.0):
    return float(np.clip(HR.normal(0, ms / 2000.0), -ms / 1000.0, ms / 1000.0))


def hv(v, amt=0.07):
    return float(np.clip(v * (1 + HR.normal(0, amt)), 0.05, 1.0))


class Stem:
    """Buffer estéreo com pré-rolagem; add(mono ou estéreo, t, ganho, pan)."""

    def __init__(self):
        self.buf = np.zeros((2, N_TOTAL))

    def add(self, x, t, gain=1.0, pan=0.0):
        if x.ndim == 1:
            ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            x = np.vstack([x * np.cos(ang), x * np.sin(ang)])
        i = int(round((t + PRE) * SR))
        if i < 0:
            x = x[:, -i:]
            i = 0
        m = min(x.shape[1], N_TOTAL - i)
        if m > 0:
            self.buf[:, i:i + m] += x[:, :m] * gain


_seed = [300]


def nseed():
    _seed[0] += 1
    return _seed[0]


# ---------------------------------------------------------------------------
# Instrumentos próprios desta faixa (os demais vêm de synth.py)
# ---------------------------------------------------------------------------
def warm_pad(notes, dur, vel, seed, bright=0.3, att=0.8, rel=0.8):
    """Colchão quente estéreo: 3 serras levemente desafinadas por nota (esq./centro/dir.),
    harmônicos limitados, passa-baixas suave e respiração lenta do filtro.
    Envelope de potência constante: segmentos vizinhos se cruzam sem buraco."""
    n = sy.nsamp(dur + rel)
    rng = np.random.default_rng(seed)
    t = sy.tarr(n)
    side = {-1: np.zeros(n), 0: np.zeros(n), 1: np.zeros(n)}
    for note in notes:
        f0 = sy.freq(note)
        hmax = int(max(3, min(10, 2600.0 / f0)))
        for c, key in ((-7.0, -1), (0.0, 0), (7.0, 1)):
            drift = 1 + 0.0012 * np.sin(2 * np.pi * rng.uniform(0.08, 0.22) * t + rng.uniform(0, 6.28))
            ph = 2 * np.pi * np.cumsum(np.full(n, f0 * 2 ** (c / 1200.0)) * drift) / SR + rng.uniform(0, 6.28)
            w = np.zeros(n)
            for h in range(1, hmax + 1):
                w += np.sin(ph * h) / h ** 1.25
            side[key] += w
    norm = 1.0 / (len(notes) * 3)
    cut = 520 + 1500 * bright
    breath = 0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t + rng.uniform(0, 6.28))
    out = []
    for ch in (-1, 1):
        x = (side[ch] + 0.7 * side[0]) * norm
        a = sy.lowpass(x, cut, order=2)
        b = sy.lowpass(x, cut * 1.6, order=2)
        out.append(a * (1 - 0.35 * breath) + b * 0.35 * breath)
    env = np.ones(n)
    na, nd = sy.nsamp(att), sy.nsamp(dur)
    env[:na] = np.sin(np.linspace(0, np.pi / 2, na))
    env[nd:] = np.cos(np.linspace(0, np.pi / 2, n - nd))
    return np.vstack(out) * env * vel * 0.5


def vibes_soft(note, dur, vel=0.7, seed=0):
    """Vibrafone noturno: motor lento (3,4 Hz), baqueta de feltro, pouco brilho."""
    f0 = sy.freq(note)
    n = sy.nsamp(dur)
    t = sy.tarr(n)
    s = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 1.5)
    s += np.sin(2 * np.pi * f0 * 4.0 * t) * 0.10 * np.exp(-t / 0.22)
    s += np.sin(2 * np.pi * f0 * 2.0 * t) * 0.04 * np.exp(-t / 0.5)
    s *= 1 + 0.15 * np.sin(2 * np.pi * 3.4 * t + seed * 1.3)
    rng = np.random.default_rng(seed)
    m = min(n, sy.nsamp(0.01))
    s[:m] += sy.bandpass(rng.standard_normal(m), 700, 2500) * np.linspace(0.05, 0, m)
    return sy.fade(s, 0.002, min(0.35, dur * 0.35)) * vel * 0.3


def marimba_soft(note, dur, vel=0.7, seed=0):
    """Marimba de baqueta macia (menos 'tique' agudo que a padrão)."""
    x = sy.marimba(note, dur, vel, seed=seed)
    return sy.lowpass(x, 4200, order=1)


def brush_sweep(dur, vel, seed):
    """Vassourinha arrastada (swish) - só na seção do meio."""
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur)
    t = sy.tarr(n)
    x = t / dur
    s = sy.bandpass(rng.standard_normal(n), 600, 4200)
    s = sy.lowpass(s, 3200, order=1)
    env = np.sin(np.pi * x) ** 1.4 * (0.7 + 0.3 * x)
    return s * env * vel * 0.05


def brush_tap(vel, seed):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(0.12)
    t = sy.tarr(n)
    s = sy.bandpass(rng.standard_normal(n), 1200, 4800) * np.exp(-t / 0.03)
    s += np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.04) * 0.25
    a = sy.nsamp(0.003)
    s[:a] *= np.linspace(0, 1, a)
    return s * vel * 0.12


SHAKERS = [sy.lowpass(sy.shaker(1.0, dur=0.1, seed=500 + i, bright=0.05), 6500) for i in range(8)]
TAPS = [brush_tap(1.0, 600 + i) for i in range(6)]
ZAB = sy.lowpass(sy.zabumba('bum', 1.0, seed=7), 380)
ZAB_A = sy.lowpass(sy.zabumba('abafa', 1.0, seed=8), 380)

# ---------------------------------------------------------------------------
# Melodias: (compasso na seção, instrumento, [(batida, nota, duração em batidas), ...])
#   ep = Rhodes, mb = marimba, vb = vibrafone.  Motivo do tema: Dó-Lá (sexta subindo), Sol.
# ---------------------------------------------------------------------------
MEL = {
    'intro': [
        (1, 'vb', [(1.0, 'D5', .5), (1.5, 'C5', .5), (2.0, 'A4', 2.0)]),      # célula 3a-9a-7a (prenúncio do C)
        (2, 'ep', [(1.0, 'C5', .5), (1.5, 'A5', 1.5), (3.0, 'G5', 1.0)]),
        (3, 'mb', [(0, 'D5', .5), (0.5, 'F5', .5), (1.0, 'A5', 1.0), (2.0, 'G5', 1.0), (3.0, 'F5', 1.0)]),
    ],
    'A': [
        (0, 'ep', [(1.0, 'C5', .5), (1.5, 'A5', 1.5), (3.0, 'G5', 1.0)]),
        (1, 'ep', [(0, 'E5', 2.5)]),
        (1, 'mb', [(2.5, 'E4', .5), (3.0, 'C#5', 1.0)]),
        (2, 'ep', [(0, 'D5', 1.0), (1.0, 'E5', .5), (1.5, 'F5', .5), (2.0, 'A5', 2.0)]),
        (3, 'ep', [(0, 'G5', 1.5), (1.5, 'Eb5', .5), (2.0, 'D5', 2.0)]),
        (3, 'mb', [(3.0, 'A4', .5), (3.5, 'C5', .5)]),
        (4, 'ep', [(1.0, 'D5', .5), (1.5, 'C6', 1.5), (3.0, 'A5', 1.0)]),
        (5, 'ep', [(0, 'G5', 1.5), (1.5, 'F5', .5), (2.0, 'Db5', 2.0)]),
        (6, 'ep', [(0, 'E5', 1.5), (1.5, 'C5', .5), (2.0, 'Eb5', 2.0)]),
        (7, 'ep', [(0, 'D5', 1.5), (1.5, 'C5', .5), (2.0, 'Bb4', 2.0)]),
    ],
    'A2': [
        (0, 'ep', [(0, 'A4', .75), (1.0, 'C5', .5), (1.5, 'A5', 1.0), (2.5, 'G5', .5), (3.0, 'A5', .5), (3.5, 'G5', .5)]),
        (1, 'ep', [(0, 'E5', 2.0)]),
        (1, 'mb', [(2.0, 'A4', .5), (2.5, 'C#5', .5), (3.0, 'E5', .5), (3.5, 'G5', .5)]),
        (2, 'ep', [(0, 'F5', 1.0), (1.0, 'E5', .5), (1.5, 'D5', .5), (2.0, 'A5', 2.0)]),
        (3, 'ep', [(0, 'G5', 1.5), (1.5, 'Bb5', .5), (2.0, 'A5', 2.0)]),
        (3, 'mb', [(3.0, 'C5', .5), (3.5, 'Eb5', .5)]),
        (4, 'ep', [(1.0, 'D5', .5), (1.5, 'C6', 1.5), (3.0, 'A5', .5), (3.5, 'F5', .5)]),
        (5, 'ep', [(0, 'G5', 1.5), (1.5, 'F5', .5), (2.0, 'Db5', 2.0)]),
        (5, 'mb', [(3.0, 'Bb4', .5), (3.5, 'C5', .5)]),
        (6, 'ep', [(0, 'E5', 1.5), (1.5, 'G5', .5), (2.0, 'F#5', 1.5), (3.5, 'A5', .5)]),
        (7, 'ep', [(0, 'Bb5', 1.5), (1.5, 'A5', .5), (2.0, 'G5', 1.0), (3.0, 'E5', 1.0)]),
    ],
    'B': [
        (0, 'mb', [(0, 'D5', .5), (0.5, 'F5', .5), (1.0, 'A5', .75), (1.75, 'G5', .75), (2.5, 'E5', 1.5)]),
        (1, 'ep', [(1.0, 'B4', .5), (1.5, 'D5', .5), (2.0, 'E5', 1.0), (3.0, 'F5', 1.0)]),
        (2, 'mb', [(0, 'D5', .5), (0.5, 'F5', .5), (1.0, 'A5', .75), (1.75, 'C6', .75), (2.5, 'A5', .5), (3.0, 'G5', 1.0)]),
        (3, 'ep', [(0.5, 'F5', .5), (1.0, 'E5', 1.0), (2.0, 'D5', .5), (2.5, 'B4', 1.5)]),
        (4, 'ep', [(0, 'F5', 1.0), (1.0, 'A5', 1.5), (2.5, 'G5', .5), (3.0, 'F5', 1.0)]),
        (5, 'ep', [(0, 'E5', 1.5), (1.5, 'D5', .5), (2.0, 'C#5', 2.0)]),
        (5, 'mb', [(2.5, 'E5', .5), (3.0, 'G5', .5), (3.5, 'A5', .5)]),
        (6, 'mb', [(0, 'F5', .5), (0.5, 'E5', .5), (1.0, 'D5', .5), (1.5, 'A4', .5), (2.0, 'C5', 1.0), (3.0, 'D5', 1.0)]),
        (7, 'ep', [(0, 'D5', 1.5), (1.5, 'F5', .5), (2.0, 'G5', 2.0)]),
    ],
    'C': [
        # sequência descendente: 3a-9a-7a sobre Fmaj7, Dm9 e Bbmaj7
        (0, 'vb', [(0, 'A5', 1.5), (1.5, 'G5', .5), (2.0, 'E5', 2.0)]),
        (1, 'vb', [(0, 'G5', 1.0), (1.0, 'B5', 1.5), (2.5, 'A5', .5), (3.0, 'G5', 1.0)]),
        (2, 'vb', [(0, 'F5', 1.5), (1.5, 'E5', .5), (2.0, 'C5', 2.0)]),
        (3, 'vb', [(0, 'E5', 1.0), (1.0, 'G5', 1.5), (2.5, 'B5', .5), (3.0, 'A5', 1.0)]),
        (4, 'vb', [(0, 'D5', 1.5), (1.5, 'C5', .5), (2.0, 'A4', 2.0)]),
        (5, 'vb', [(0.5, 'C5', .5), (1.0, 'E5', 1.0), (2.0, 'G5', 1.5), (3.5, 'A5', .5)]),
        (6, 'vb', [(0, 'Bb5', 2.0), (2.0, 'A5', 1.0), (3.0, 'F5', 1.0)]),
        (7, 'vb', [(0, 'G5', 1.5), (1.5, 'F5', .5), (2.0, 'E5', 2.0)]),
    ],
    'A3': [
        (0, 'ep', [(1.0, 'C5', .5), (1.5, 'A5', 1.5), (3.0, 'G5', 1.0)]),
        (0, 'vb', [(1.5, 'C5', 1.5), (3.0, 'E5', 1.0)]),
        (1, 'ep', [(0, 'E5', 2.5)]),
        (1, 'mb', [(2.5, 'E4', .5), (3.0, 'C#5', .5), (3.5, 'E5', .5)]),
        (2, 'ep', [(0, 'D5', 1.0), (1.0, 'E5', .5), (1.5, 'F5', .5), (2.0, 'A5', 1.0), (3.0, 'C6', 1.0)]),
        (2, 'vb', [(2.0, 'F5', 1.0), (3.0, 'A5', 1.0)]),
        (3, 'ep', [(0, 'Bb5', 1.5), (1.5, 'G5', .5), (2.0, 'A5', 1.5), (3.5, 'F5', .5)]),
        (3, 'vb', [(0, 'G5', 1.5), (2.0, 'Eb5', 2.0)]),
        (4, 'ep', [(1.0, 'D5', .5), (1.5, 'C6', 1.5), (3.0, 'A5', 1.0)]),
        (4, 'vb', [(1.5, 'F5', 1.5), (3.0, 'D5', 1.0)]),
        (5, 'ep', [(0, 'G5', 1.5), (1.5, 'F5', .5), (2.0, 'Db5', 2.0)]),
        (5, 'vb', [(0, 'Bb4', 1.5), (2.0, 'G4', 2.0)]),
        (6, 'ep', [(0, 'C5', 1.5), (1.5, 'E5', .5), (2.0, 'F#5', 1.0), (3.0, 'Eb5', 1.0)]),
        (6, 'vb', [(0, 'A4', 1.5), (2.0, 'C5', 2.0)]),
        (7, 'ep', [(0, 'D5', 1.5), (1.5, 'C5', .5), (2.0, 'Bb4', 2.0)]),
        (7, 'vb', [(0, 'Bb4', 1.5), (2.0, 'G4', 2.0)]),
        (7, 'mb', [(3.0, 'G4', .5), (3.5, 'A4', .5)]),
    ],
    'coda': [
        (0, 'mb', [(1.0, 'C5', .5), (1.5, 'A5', 1.0), (2.5, 'G5', .5), (3.0, 'E5', 1.0)]),
        (1, 'ep', [(1.0, 'D5', .5), (1.5, 'C6', 1.5), (3.0, 'A5', 1.0)]),
        (2, 'ep', [(0, 'G5', 4.0)]),
        (2, 'mb', [(2.5, 'C5', .5), (3.0, 'Eb5', 1.0)]),
        (3, 'ep', [(0, 'F5', 1.5), (1.5, 'D5', .5), (2.0, 'Bb4', 2.0)]),
    ],
}

# Rhodes em décimas paralelas com o baixo na seção C (guias 7a+3a, descendo em graus)
C_DYADS = [(0, ['E4', 'A4'], 4), (1, ['D4', 'G4'], 4), (2, ['C4', 'F4'], 4), (3, ['B3', 'E4'], 4),
           (4, ['A3', 'D4'], 4), (5, ['G3', 'C4'], 4), (6, ['F3', 'Bb3'], 4)]
C_DYADS_LAST = [(7, ['Bb3', 'F4'], 0, 2), (7, ['Bb3', 'E4'], 2, 2)]

# baixo da seção C: F3 E3 D3 C3 Bb2 A2 G2 C3 (escada descendente; a quinta vem embaixo)
C_BASS = [53, 52, 50, 48, 46, 45, 43, 48]

# dinâmica por seção (multiplicadores)
DYN = {
    #        violão  melodia  colchão  brilho_colchão  baixo
    'intro': (0.62, 0.62, 1.00, 0.22, 0.55),
    'A':     (0.66, 0.70, 0.72, 0.26, 0.70),
    'A2':    (0.68, 0.72, 0.66, 0.28, 0.80),
    'B':     (0.70, 0.74, 0.60, 0.30, 0.86),
    'C':     (0.64, 0.72, 0.92, 0.40, 0.80),
    'A3':    (0.70, 0.78, 0.74, 0.30, 0.84),
    'coda':  (0.64, 0.66, 0.96, 0.24, 0.60),
}

GTR_PAT = {
    'arp':   [(0, 'p'), (0.5, 'i'), (1, 'm'), (1.5, 'a'), (2, 'p2'), (2.5, 'a'), (3, 'm'), (3.5, 'i')],
    'arp2':  [(0, 'p'), (0.5, 'i'), (1, 'm'), (1.5, 'a'), (2, 'p2'), (2.5, 'm'), (3, 'a'), (3.5, 'ANT')],
    'baiao': [(0, 'p'), (0.75, 'i'), (1.0, 'ma'), (1.5, 'i'), (2, 'p2'), (2.75, 'i'), (3.0, 'ma'), (3.5, 'i')],
    'roll':  [(0, 'p'), (0, 'IMA'), (1.5, 'i'), (2, 'p2'), (2.5, 'm'), (3, 'a'), (3.5, 'm')],
}
SEC_GTR = {'intro': 'arp', 'A': 'arp', 'A2': 'arp2', 'B': 'baiao', 'C': 'roll', 'A3': 'arp2', 'coda': 'arp2'}
G_VEL = {'p': 0.74, 'p2': 0.62, 'i': 0.50, 'm': 0.53, 'a': 0.58}
G_PAN = {'p': -0.18, 'p2': -0.24, 'i': -0.34, 'm': -0.46, 'a': -0.56}


# ---------------------------------------------------------------------------
# Renderização
# ---------------------------------------------------------------------------
def render():
    st = {k: Stem() for k in ('gtr', 'ep', 'mb', 'vb', 'pad', 'bass', 'perc')}

    # --- colchão --------------------------------------------------------------
    for k, (gb, d, sym, sec) in enumerate(SEGS):
        lvl, bright = DYN[sec][2], DYN[sec][3]
        t0 = tsec(gb) - 0.4
        x = warm_pad(PAD_V[k], d * BEAT, 0.6, seed=900 + k, bright=bright, att=0.8, rel=0.8)
        st['pad'].add(x, t0, lvl)

    # --- violão de nylon (p-i-m-a) --------------------------------------------
    def pluck(note, t, vel, dur, pan, seed):
        x = sy.nylon(note, dur, hv(vel, 0.08), bright=0.38, seed=seed)
        st['gtr'].add(x, t + jit(6), 1.0, pan)

    for b, (sec, kb, chs) in enumerate(BARS):
        g = DYN[sec][0]
        pat = GTR_PAT[SEC_GTR[sec]]
        for beat, v in pat:
            gb = b * 4 + beat
            k = seg_index_at(gb)
            seg = SEGS[k]
            sym = seg[2]
            seg_end = tsec(seg[0] + seg[1])
            t = tsec(gb)
            p, p2 = gtr_bass(sym)
            up = GTR_V[k]
            notes = {'p': p, 'p2': p2, 'i': up[0], 'm': up[1], 'a': up[2]}
            if v in ('p', 'p2'):
                dur = float(np.clip(seg_end - t + 0.25, 0.7, 3.2))
                soft = 0.65 if (b == 0 and beat == 0) else 1.0      # 1o polegar do loop mais leve (emenda macia)
                pluck(notes[v], t, G_VEL[v] * g * soft, dur, G_PAN[v], nseed())
            elif v in ('i', 'm', 'a'):
                dur = float(np.clip(seg_end - t + 0.35, 0.6, 2.6))
                pluck(notes[v], t, G_VEL[v] * g, dur, G_PAN[v], nseed())
            elif v in ('ma', 'IMA'):
                strings = ['m', 'a'] if v == 'ma' else ['i', 'm', 'a']
                spread = 0.009 if v == 'ma' else 0.028
                for j, s in enumerate(strings):
                    dur = float(np.clip(seg_end - t + 0.35, 0.8, 3.0))
                    pluck(notes[s], t + j * spread, G_VEL[s] * g * (0.9 if v == 'ma' else 0.95), dur, G_PAN[s], nseed())
            elif v == 'ANT':
                # antecipação brasileira: o acorde do próximo compasso chega meio tempo antes
                k2 = seg_index_at(gb + 0.5)
                if k2 != k:
                    up2 = GTR_V[k2]
                    seg2 = SEGS[k2]
                    end2 = tsec(seg2[0] + min(seg2[1], 2.0))
                    for j, s in enumerate(['i', 'm', 'a']):
                        dur = float(np.clip(end2 - t + 0.3, 0.8, 3.0))
                        pluck(up2[j], t + j * 0.016, G_VEL[s] * g * 0.92, dur, G_PAN[s], nseed())
                else:
                    dur = float(np.clip(seg_end - t + 0.35, 0.6, 2.6))
                    pluck(notes['i'], t, G_VEL['i'] * g, dur, G_PAN['i'], nseed())

    # --- melodias (Rhodes, marimba, vibrafone) --------------------------------
    for sec, items in MEL.items():
        base_bar = SEC_BAR[sec]
        lvl = DYN[sec][1]
        for kb, inst, notes in items:
            for j, (beat, nm, dur) in enumerate(notes):
                gb = (base_bar + kb) * 4 + beat
                t = tsec(gb) + jit(8)
                mm = sy.midi(nm)
                # frase: notas longas e agudas um pouco mais cheias; ataque inicial mais leve
                v = lvl * (0.86 + 0.08 * min(dur, 2.0) / 2.0 + 0.004 * (mm - 72))
                v = hv(v, 0.06)
                if inst == 'ep':
                    x = sy.epiano(nm, dur * BEAT + 0.9, v * 0.85, seed=nseed())
                    st['ep'].add(x, t)
                elif inst == 'mb':
                    x = marimba_soft(nm, max(1.0, dur * BEAT + 0.5), v, seed=nseed())
                    st['mb'].add(x, t)
                else:
                    x = vibes_soft(nm, dur * BEAT + 1.4, v, seed=nseed())
                    st['vb'].add(x, t, 1.0 if sec == 'C' else 0.55)

    # Rhodes em décimas na seção C (acordes arpejados suavemente)
    c0 = SEC_BAR['C']
    for item in C_DYADS + C_DYADS_LAST:
        if len(item) == 3:
            kb, nts, d = item
            beat = 0
        else:
            kb, nts, beat, d = item
        gb = (c0 + kb) * 4 + beat
        t = tsec(gb) + jit(6)
        for j, nm in enumerate(nts):
            x = sy.epiano(nm, d * BEAT + 0.6, hv(0.42, 0.05), seed=nseed())
            st['ep'].add(x, t + j * 0.03, 0.9)

    # --- baixo ----------------------------------------------------------------
    def bnote(note, gb, dur_beats, vel, soft, swell=0.0):
        t = tsec(gb) + jit(5)
        d = dur_beats * BEAT - 0.04
        if soft:
            x = sy.bass_soft(note, d + 0.15, hv(vel, 0.05)) * 0.6     # senoidal: soa mais cheio que o acústico
        else:
            x = sy.bass_upright(note, d + 0.1, hv(vel, 0.06), seed=nseed())
        if swell:
            # entrada em "swell": a volta do loop chega como um suspiro, sem pancada no grave
            k = sy.nsamp(swell)
            x[:k] *= np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        st['bass'].add(x, t)

    for b, (sec, kb, chs) in enumerate(BARS):
        lv = DYN[sec][4]
        gb0 = b * 4
        roots = [bass_root(c) for c in chs]
        nxt = bass_root(BARS[(b + 1) % NBARS][2][0])
        if sec == 'intro':
            if len(chs) == 1:
                bnote(bass_root('Fmaj9'), gb0, 4, 0.8 * lv, True, swell=0.35 if b == 0 else 0.0)
            else:
                bnote(roots[0], gb0, 2, 0.8 * lv, True)
                bnote(roots[1], gb0 + 2, 2, 0.8 * lv, True)
        elif sec in ('A', 'coda'):
            if len(chs) == 1:
                r = roots[0]
                if abs(nxt - r) > 2 and sec == 'A':
                    bnote(r, gb0, 3, 0.85 * lv, True)
                    appr = min((nxt - 1, nxt + 1), key=lambda q: abs(q - r))   # aproximação cromática
                    bnote(appr, gb0 + 3, 1, 0.7 * lv, True)
                else:
                    bnote(r, gb0, 4, 0.85 * lv, True)
            else:
                bnote(roots[0], gb0, 2, 0.85 * lv, True)
                bnote(roots[1], gb0 + 2, 2, 0.85 * lv, True)
        elif sec in ('A2', 'A3'):
            if len(chs) == 1:
                r = roots[0]
                fifth = r + 7 if r + 7 <= 50 else r - 5
                bnote(r, gb0, 2, 0.85 * lv, False)
                bnote(fifth, gb0 + 2, 1.5, 0.7 * lv, False)
                appr = min((nxt - 1, nxt + 1), key=lambda q: abs(q - fifth)) if nxt != r else fifth
                bnote(appr, gb0 + 3.5, 0.5, 0.62 * lv, False)
            else:
                bnote(roots[0], gb0, 2, 0.85 * lv, False)
                bnote(roots[1], gb0 + 2, 2, 0.8 * lv, False)
        elif sec == 'B':
            # baião lento: semínima pontuada + colcheia + mínima
            r0 = roots[0]
            r1 = roots[-1]
            fifth = r0 + 7 if r0 + 7 <= 50 else r0 - 5
            bnote(r0, gb0, 1.5, 0.9 * lv, False)
            bnote(r0, gb0 + 1.5, 0.5, 0.6 * lv, False)
            bnote(r1 if len(chs) == 2 and r1 != r0 else fifth, gb0 + 2, 2, 0.8 * lv, False)
        elif sec == 'C':
            # fundamentais descendo em graus (Fá3 ... Sol2), quinta embaixo na 2a mínima
            r0 = C_BASS[kb]
            bnote(r0, gb0, 2, 0.85 * lv, False)
            bnote(r0 - 5, gb0 + 2, 2, 0.72 * lv, False)

    # --- percussão leve (só B e C) ------------------------------------------------
    sh_acc = [0.38, 0.62, 0.42, 0.66, 0.38, 0.62, 0.45, 0.70]
    for b, (sec, kb, chs) in enumerate(BARS):
        if sec not in ('B', 'C'):
            continue
        gb0 = b * 4
        lvl = 1.0 if sec == 'B' else 0.62
        # entrada e saída suaves (primeiro compasso do B cresce; último do C diminui)
        if sec == 'B' and kb == 0:
            ramp = np.linspace(0.45, 1.0, 8)
        elif sec == 'C' and kb == 7:
            ramp = np.linspace(1.0, 0.35, 8)
        else:
            ramp = np.ones(8)
        for e in range(8):
            t = tsec(gb0 + e * 0.5) + jit(5)
            st['perc'].add(SHAKERS[int(HR.integers(0, 8))], t, hv(sh_acc[e] * lvl * ramp[e], 0.1) * 0.55, 0.5)
        # vassourinha arrastada em cada mínima, toque leve nos tempos 2 e 4 (só no B)
        for h in (0, 2):
            t = tsec(gb0 + h) + jit(5)
            st['perc'].add(brush_sweep(2 * BEAT * 0.95, hv(0.7 * lvl * ramp[h * 2], 0.08), nseed()), t, 1.0, -0.35)
        if sec == 'B':
            for h in (1, 3):
                t = tsec(gb0 + h) + jit(5)
                st['perc'].add(TAPS[int(HR.integers(0, 6))], t, hv(0.42 * ramp[h * 2], 0.1), -0.3)
            # zabumba bem baixinha acompanhando o baião do baixo
            st['perc'].add(ZAB, tsec(gb0) + jit(4), hv(0.30, 0.06), 0.0)
            st['perc'].add(ZAB_A, tsec(gb0 + 1.5) + jit(4), hv(0.20, 0.08), 0.0)
    return st


# ---------------------------------------------------------------------------
# Mixagem e loop
# ---------------------------------------------------------------------------
#          ganho  hp   lp     envio_reverb
MIXCFG = {
    'gtr':  (1.60, 110, 6500, 0.22),
    'ep':   (1.00, 140, 5200, 0.30),
    'mb':   (1.05, 150, 5200, 0.26),
    'vb':   (0.58, 150, 5600, 0.34),
    'pad':  (0.55, 120, 4000, 0.30),
    'bass': (0.70, 35, 1600, 0.04),
    'perc': (1.10, 160, 6800, 0.18),
}
LEAD_PAN = {'ep': 0.12, 'mb': 0.45, 'vb': 0.30}


def pan_stereo(x, pan):
    """Reposiciona um stem estéreo (soma mono -> pan) mantendo parte da largura original."""
    ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    m = (x[0] + x[1]) * 0.5
    return np.vstack([m * np.cos(ang) * np.sqrt(2), m * np.sin(ang) * np.sqrt(2)])


def mixdown(st, report=True):
    dry = np.zeros((2, N_TOTAL))
    send = np.zeros((2, N_TOTAL))
    P, L = sy.nsamp(PRE), sy.nsamp(LOOP)
    for name, (g, hp, lp, snd) in MIXCFG.items():
        x = st[name].buf
        x = sy.highpass(x, hp)
        x = sy.lowpass(x, lp)
        x = x * g
        if name in LEAD_PAN:
            x = pan_stereo(x, LEAD_PAN[name])
            # eco pingue-pongue em colcheia pontuada, escuro
            x = sy.delay_fx(x, time=BEAT * 0.75, fb=0.30, wet=0.20 if name != 'mb' else 0.14, lp=2600)
        if name == 'gtr':
            x = sy.stereo_widen(x, 0.2)
        if report:
            r = np.sqrt(np.mean(x[:, P:P + L] ** 2)) + 1e-12
            print('  stem %-5s rms %6.1f dB' % (name, 20 * np.log10(r)))
        dry += x
        send += x * snd
        st[name].buf = None
    ir = sy.make_ir(t60=2.5, predelay=0.028, bright=0.32, seed=17)
    send = sy.highpass(send, 220)
    wet = np.zeros_like(send)
    for ch in range(2):
        wet[ch] = signal.oaconvolve(send[ch], ir[ch])[:N_TOTAL]
    wet = sy.lowpass(wet, 5500)
    mix = dry + wet * 0.6
    mix = sy.highpass(mix, 30)
    mix = sy.peak_eq(mix, 280, -1.5, 0.9)          # menos "embolado" no médio-grave
    mix = sy.peak_eq(mix, 7000, -2.5, 0.7)         # agudos macios: o jogo toca por horas
    return mix


def fold_loop(mix):
    """Pré-rolagem -> fim do loop; cauda (reverb, notas soando) -> início (sy.seamless_loop)."""
    P = sy.nsamp(PRE)
    L = sy.nsamp(LOOP)
    main = mix[:, P:].copy()
    main[:, L - P:L] += mix[:, :P]
    return sy.seamless_loop(main, LOOP)


def cyclic_compress(y, **kw):
    """Compressão de barramento tratando o arquivo como cíclico (sem degrau de ganho na emenda)."""
    P = sy.nsamp(4.0)
    ext = np.concatenate([y[:, -P:], y, y[:, :P]], axis=1)
    ext = sy.compress(ext, **kw)
    return ext[:, P:-P]


def limiter_loopsafe(x, ceiling_db=-1.0, lookahead=0.004, release=0.08):
    """Mesmo limitador de synth.py, mas com o filtro de recuperação iniciado no estado de
    repouso (ganho = need[0]) em vez de zero. O original começa com ganho ~0 e sobe em ~0,3 s,
    o que abafa os primeiros ms do arquivo e cria um degrau/estalo na emenda do loop.
    Usado só neste processo (sy.limiter é substituído em tempo de execução; synth.py não muda)."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x), axis=0)
    la = sy.nsamp(lookahead)
    peak = maximum_filter1d(peak, size=2 * la + 1)
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    a_r = np.exp(-1 / (release * SR))
    sm, _ = signal.lfilter([1 - a_r], [1, -a_r], need, zi=[a_r * need[0]])
    g = np.minimum(need, sm)
    return np.clip(x * g, -ceil, ceil)


def main():
    t0 = time.time()
    print('Noite na Vila: %d compassos, %.2f s, %d BPM' % (NBARS, LOOP, BPM))
    st = render()
    print('  render %.1f s' % (time.time() - t0))
    mix = mixdown(st)
    y = fold_loop(mix)
    del mix
    rms = np.sqrt(np.mean(y ** 2))
    y *= 10 ** (-21 / 20) / rms
    y = cyclic_compress(y, thresh_db=-22, ratio=1.8, attack=0.03, release=0.3)
    sy.limiter = limiter_loopsafe               # ver docstring: evita o 'fade-in' de 0,3 s no início do arquivo
    res = sy.master_and_export(y, OUT, target_lufs=TARGET_LUFS, ceiling_db=-1.2, quality=QUALITY,
                               loop=True, title='Noite na Vila')
    print(res)
    print('  total %.1f s' % (time.time() - t0))
    return res


if __name__ == '__main__':
    main()

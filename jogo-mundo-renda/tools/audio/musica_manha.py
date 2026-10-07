#!/usr/bin/env python3
"""Mundo Renda - "Manhã na Horta" (bossa nova diurna, Ré maior, 100 BPM, 4/4).

Música original, 100% sintetizada por código (nenhum sample, nenhuma melodia existente).

Forma (76 compassos = 182,4 s, loop perfeito: o fim prepara a volta da introdução):
  Intro (4)  vamp ii-V  (Em9 | A13 | Em9 | A7b9)       violão, baixo, ganzá, vassourinha; vibrafone acena o tema
  A1    (8)  tema na flauta                             + bumbo e vassourinha completa
  A2    (8)  flauta + respostas do vibrafone            + aro (clave da bossa)
  B1    (8)  ponte: melodia no vibrafone                harmonia vai ao IV, iv menor emprestado, dim de passagem
  A3    (8)  flauta + Rhodes comping                    banda completa
  C     (8)  interlúdio em Si menor: Rhodes canta,      violão arpejado, baixo em mínimas, percussão rala
             (Bm9 | Bm9/A | Gmaj7#11 | G#m7b5 C#7b9 | F#m9 | B7b9 | Em9 | A7sus4 A13)
  S1    (8)  "trocas" de 2 compassos: vibrafone <-> flauta (pergunta e resposta) sobre a harmonia do A
  S2    (8)  Rhodes -> vibrafone -> flauta -> tutti em terças
  B2    (8)  vibrafone na ponte, flauta em notas-guia e terças
  A4    (8)  flauta + vibrafone em oitavas; turnaround Dmaj9 B7b9 devolve à Intro (Em9)

Harmonia do A: Dmaj9 | G13 | F#m7 | B7b9 (V/ii) | Em9 | A13 | F#m7 B9 | Em9 A13
Violão: batida de bossa (polegar nos tempos 1 e 3 alternando fundamental/quinta, pinçadas
sincopadas das cordas agudas num padrão de 2 compassos tipo clave, antecipações de acorde),
vozes calculadas por condução de vozes. Swing leve nas semicolcheias, humanização de tempo/dinâmica.

Uso (a partir de jogo-mundo-renda/):  python3 tools/audio/musica_manha.py
Saída: android/assets/www/audio/manha.ogg
"""
import os
import sys
import time
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np                      # noqa: E402
from scipy import signal               # noqa: E402

import synth as sy                     # noqa: E402

SR = sy.SR
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'android', 'assets', 'www', 'audio', 'manha.ogg')

BPM = 100.0
BEAT = 60.0 / BPM
S16 = BEAT / 4.0
SWING = 0.11            # fração de semicolcheia que as semicolcheias "fracas" atrasam (~16 ms)
TARGET_LUFS = -18.0
QUALITY = 7             # Vorbis -q:a 7 (~220 kbps): arquivo de vários MB, som limpo
PRE = 1.0               # pré-rolagem (s) para eventos antes do tempo 0 (vão para o fim do loop)
TAIL = 6.0              # cauda renderizada após o fim (dobrada sobre o início)

# ---------------------------------------------------------------------------
# Harmonia e forma
# ---------------------------------------------------------------------------
H_INTRO = [['Em9'], ['A13'], ['Em9'], ['A7b9']]
H_A1 = [['Dmaj9'], ['G13'], ['F#m7'], ['B7b9'], ['Em9'], ['A13'], ['F#m7', 'B9'], ['Em9', 'A13']]
H_A2 = H_A1[:6] + [['Em9', 'A13'], ['Dmaj9', 'D7']]
H_B = [['Gmaj7'], ['Gm6', 'C9'], ['F#m7'], ['Fdim7'], ['Em9'], ['A7sus4', 'A7b9'], ['Bm9', 'E9'], ['Em9', 'A13']]
H_A3 = H_A1[:6] + [['Em9', 'A13'], ['D69']]
H_C = [['Bm9'], ['Bm9/A'], ['Gmaj7#11'], ['G#m7b5', 'C#7b9'], ['F#m9'], ['B7b9'], ['Em9'], ['A7sus4', 'A13']]
H_A4 = H_A1[:6] + [['Em9', 'A13'], ['Dmaj9', 'B7b9']]

FORM = [('intro', H_INTRO), ('A1', H_A1), ('A2', H_A2), ('B1', H_B), ('A3', H_A3), ('C', H_C),
        ('S1', H_A1), ('S2', H_A2), ('B2', H_B), ('A4', H_A4)]

BARS = []               # por compasso: (seção, índice no trecho, lista de acordes)
SEC_START = {}          # seção -> tempo (em batidas) do início
for name, harm in FORM:
    SEC_START[name] = len(BARS) * 4
    for k, ch in enumerate(harm):
        BARS.append((name, k, ch))
NBARS = len(BARS)
TOTAL_BEATS = NBARS * 4
LOOP = TOTAL_BEATS * BEAT

# ---------------------------------------------------------------------------
# Acordes: análise, vozes (condução de vozes) e linha do tempo
# ---------------------------------------------------------------------------
PCN = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
# notas do voicing "de cima" (semitons acima da fundamental, em ordem de importância)
QUAL = {
    '': [4, 7, 0, 14], 'maj7': [4, 11, 14, 7], 'maj9': [4, 11, 14, 7], '69': [4, 9, 14, 7],
    'maj7#11': [4, 11, 6, 14], '6': [4, 9, 7, 0], '13': [4, 10, 14, 9], '9': [4, 10, 14, 7],
    '7': [4, 10, 7, 0], '7b9': [4, 10, 13, 7], '7sus4': [5, 10, 14, 7], 'm9': [3, 10, 14, 7],
    'm7': [3, 10, 7, 0], 'm6': [3, 9, 7, 0], 'm7b5': [3, 10, 6, 0], 'dim7': [0, 3, 6, 9],
}


def parse_chord(sym):
    bass = None
    if '/' in sym:
        sym, bass = sym.split('/')
    root = PCN[sym[0]]
    q = sym[1:]
    if q.startswith('#'):
        root += 1
        q = q[1:]
    elif q.startswith('b') and q[1:] in QUAL:
        root -= 1
        q = q[1:]
    root %= 12
    bpc = root
    if bass:
        bpc = (PCN[bass[0]] + bass.count('#') - bass[1:].count('b')) % 12
    return root, QUAL[q], bpc


def voice(sym, prev, lo, hi, k=4, center=64.0):
    root, tones, _ = parse_chord(sym)
    pcs = [(root + iv) % 12 for iv in tones[:k]]
    cands = [[m for m in range(lo, hi + 1) if m % 12 == pc] for pc in pcs]
    best = None
    for combo in product(*cands):
        v = sorted(combo)
        if len(set(v)) < k or v[-1] - v[0] > 16:
            continue
        gaps = np.diff(v)
        c = 0.0
        if prev is not None:
            c += sum(abs(a - b) for a, b in zip(v, prev))
        c += 4.0 * np.sum(gaps == 1) + 1.5 * np.sum(gaps > 7) + 0.4 * abs(np.mean(v) - center)
        c += 3.0 * sum(1 for i in range(k) for j in range(i + 1, k) if v[j] - v[i] == 13)
        if best is None or c < best[0]:
            best = (c, v)
    return best[1]


def low_note(pc, lo):
    """Nota MIDI da classe pc dentro de [lo, lo+11]."""
    return lo + (pc - lo) % 12


SEGS = []               # (batida_inicial, batida_final, cifra, voicing_violao, voicing_rhodes)
_pg, _pe = None, None
for b, (sec, k, chs) in enumerate(BARS):
    d = 4.0 / len(chs)
    for j, sym in enumerate(chs):
        _pg = voice(sym, _pg, 52, 72, 4, 63.0)
        _pe = voice(sym, _pe, 58, 75, 3, 67.0)
        SEGS.append((b * 4 + j * d, b * 4 + (j + 1) * d, sym, _pg, _pe))


def seg_at(gbeat):
    g = gbeat % TOTAL_BEATS
    for s in SEGS:
        if s[0] <= g + 1e-9 < s[1]:
            return s
    return SEGS[-1]


# ---------------------------------------------------------------------------
# Tempo, swing, humanização e buffers
# ---------------------------------------------------------------------------
HR = np.random.default_rng(20261007)
N_TOTAL = sy.nsamp(PRE + LOOP + TAIL)


def tsec(gbeat):
    """Batida global -> segundos, com swing leve nas semicolcheias ímpares."""
    t = gbeat * BEAT
    st = gbeat * 4.0
    k = int(round(st))
    if abs(st - k) < 1e-6 and k % 2 == 1:
        t += SWING * S16
    return t


def jit(ms=6.0):
    return float(np.clip(HR.normal(0, ms / 2000.0), -ms / 1000.0, ms / 1000.0))


def hv(v, amt=0.06):
    return float(np.clip(v * (1 + HR.normal(0, amt)), 0.05, 1.0))


class Stem:
    def __init__(self):
        self.buf = np.zeros(N_TOTAL)

    def add(self, x, t, gain=1.0):
        i = int(round((t + PRE) * SR))
        if i < 0:
            x = x[-i:]
            i = 0
        m = min(len(x), N_TOTAL - i)
        if m > 0:
            self.buf[i:i + m] += x[:m] * gain


_seed = [100]


def nseed():
    _seed[0] += 1
    return _seed[0]


# ---------------------------------------------------------------------------
# Instrumentos próprios desta faixa (os demais vêm de synth.py)
# ---------------------------------------------------------------------------
def vibes2(note, dur, vel=0.8, seed=0):
    """Vibrafone com motor lento e suave (4,2 Hz) e baqueta macia."""
    f0 = sy.freq(note)
    n = sy.nsamp(dur)
    t = sy.tarr(n)
    s = sy.additive(np.full(n, f0), [(1, 1.0, 3.4), (4.0, 0.2, 0.55), (10.0, 0.03, 0.1)], n)
    s += np.sin(2 * np.pi * f0 * 2.0 * t) * 0.05 * np.exp(-t / 0.4)
    s *= 1 + 0.16 * np.sin(2 * np.pi * 4.2 * t + seed * 1.7)
    rng = np.random.default_rng(seed)
    m = min(n, sy.nsamp(0.012))
    s[:m] += sy.bandpass(rng.standard_normal(m), 800, 3000) * np.linspace(0.06, 0, m)
    return sy.fade(s, 0.0015, min(0.35, dur * 0.35)) * vel * 0.3


def ep_note(note, dur, vel, seed):
    x = sy.epiano(note, dur, vel, seed=seed)
    return x


def brush_sweep(dur, vel, seed):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur)
    t = sy.tarr(n)
    x = t / dur
    s = sy.bandpass(rng.standard_normal(n), 450, 4800)
    s = sy.lowpass(s, 3800, order=1)
    env = np.sin(np.pi * x) ** 1.3 * (0.75 + 0.25 * np.sin(2 * np.pi * x + seed))
    return s * env * vel * 0.045


def brush_slap(vel, seed):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(0.32)
    t = sy.tarr(n)
    wires = sy.bandpass(rng.standard_normal(n), 1100, 5500) * np.exp(-t / 0.07)
    head = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.35
    head += sy.bandpass(rng.standard_normal(n), 250, 900) * np.exp(-t / 0.03) * 0.35
    s = wires + head
    a = sy.nsamp(0.004)
    s[:a] *= np.linspace(0, 1, a)
    return s * vel * 0.2


def brush_tap(vel, seed):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(0.1)
    t = sy.tarr(n)
    s = sy.bandpass(rng.standard_normal(n), 1500, 5500) * np.exp(-t / 0.025)
    a = sy.nsamp(0.003)
    s[:a] *= np.linspace(0, 1, a)
    return s * vel * 0.12


def shaker2(vel, seed, dur=0.09):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur)
    t = sy.tarr(n)
    env = (t / (dur * 0.32)) * np.exp(1 - t / (dur * 0.32))
    s = sy.bandpass(rng.standard_normal(n), 2600, 7200) * env
    return s * vel * 0.14


def felt_kick(vel):
    x = sy.kick(vel, dur=0.35, f_hi=92, f_lo=50)
    return sy.lowpass(x, 220)


SHAKERS = [shaker2(1.0, 500 + i) for i in range(8)]
TAPS = [brush_tap(1.0, 600 + i) for i in range(6)]
SLAPS = [brush_slap(1.0, 700 + i) for i in range(4)]
RIMS = [sy.lowpass(sy.rim(1.0, seed=800 + i), 5200) for i in range(4)]
KICK = felt_kick(1.0)


# ---------------------------------------------------------------------------
# Melodias (posição em batidas relativa ao início da seção : duração : nota [: dinâmica])
# ---------------------------------------------------------------------------
def mel(s, vel=0.8):
    out = []
    for tok in s.split():
        p = tok.split(':')
        out.append((float(p[0]), float(p[1]), p[2], float(p[3]) if len(p) > 3 else vel))
    return out


A_HEAD = """
-1:.5:A4 -.5:.5:B4
0:.75:C#5 .75:2.25:E5 3:.5:D5 3.5:.5:C#5
4:1.5:B4 5.5:.5:A4 6:.5:B4 6.5:.5:D5 7:.75:F5 7.75:2.25:F#5
10:.5:E5 10.5:.5:F#5 11:.75:E5 11.75:1.75:D#5
13.5:.5:C5 14:1:B4 15:.5:A4 15.5:.5:B4
16:.75:F#5 16.75:2.25:B5 19:.5:A5 19.5:.5:G5
20:1.5:F#5 21.5:.5:E5 22:.5:C#5 22.5:.5:E5 23:.75:G5 23.75:1.25:F#5
"""
A_HEAD2 = """
-1:.5:A4 -.5:.5:B4
0:.75:C#5 .75:1.75:E5 2.5:.25:F#5 2.75:.25:E5 3:.5:D5 3.5:.5:C#5
4:1:B4 5:.5:A4 5.5:.5:B4 6:.5:D5 6.5:.5:E5 7:.75:F5 7.75:2.25:F#5
10:.5:E5 10.5:.5:F#5 11:.75:E5 11.75:1.75:D#5
13.5:.5:C5 14:1:B4 15:.5:A4 15.5:.5:B4
16:.75:F#5 16.75:2.25:B5 19:.5:A5 19.5:.5:G5
20:1.5:F#5 21.5:.5:E5 22:.5:C#5 22.5:.5:E5 23:.75:G5 23.75:1.25:F#5
"""
END_A1 = "25:.5:E5 25.5:.5:C#5 26:1:D#5 27:.5:F#5 27.5:.5:A5 28:1.5:G5 29.5:.5:F#5 30:1:E5"
END_CAD = "25:.5:E5 25.5:.5:D5 26:1:G5 27:.5:E5 27.5:.5:C#5"
FL_A1 = mel(A_HEAD + END_A1, 0.8)
FL_A2 = mel(A_HEAD2 + END_CAD + " 28:2.5:D5", 0.82)
FL_A3 = mel(A_HEAD + END_CAD + " 28:3:D5", 0.85)
FL_A4 = mel(A_HEAD2 + END_CAD + " 28:1.5:D5 29.5:.5:E5 30:.5:F#5 30.5:.5:D#5 31:.5:C5 31.5:.5:A4 32:2.2:B4", 0.86)

VB_INTRO = mel("8:.75:F#5 8.75:.75:E5 9.5:2:B4 12:1:C#5 13:1:Bb4 14:1:A4", 0.55)
VB_A2 = mel("1.5:.5:A4 2:.5:C#5 2.5:1:B4 8.5:.5:C#5 9:.5:E5 9.5:1:A4 "
            "17.5:.5:D5 18:.5:F#5 18.5:1:E5 30:.5:F#5 30.5:.5:D5", 0.5)
B_MEL = """
-1:.5:A4 -.5:.5:C5
0:1:B4 1:.5:D5 1.5:1.5:F#5 3:.5:E5 3.5:.5:D5
4:1.5:Bb4 5.5:.5:D5 6:1:E5 7:.5:D5 7.5:.5:Bb4
8:1:A4 9:.5:C#5 9.5:1.5:E5 11:.5:C#5 11.5:.5:E5
12:1.5:D5 13.5:.5:B4 14:1:G#4 15:.5:B4 15.5:.5:D5
"""
VB_B1 = mel(B_MEL + """
16:1.5:G5 17.5:.5:F#5 18:.5:E5 18.5:.5:D5 19:1:B4
20:1.5:D5 21.5:.5:E5 22:1:C#5 23:.5:Bb4 23.5:.5:A4
24:1.5:C#5 25.5:.5:D5 26:1:F#5 27:.5:E5 27.5:.5:D5
28:1.5:B4 29.5:.5:D5 30:1:C#5""", 0.82)
VB_B2 = mel(B_MEL + """
16:1:G5 17:.5:A5 17.5:1.5:B5 19:.5:A5 19.5:.5:G5
20:1.5:E5 21.5:.5:D5 22:1:C#5 23:.5:Bb4 23.5:.5:A4
24:1.5:C#5 25.5:.5:D5 26:1:F#5 27:.5:E5 27.5:.5:D5
28:1.5:B4 29.5:.5:D5 30:1:C#5""", 0.84)
FL_B2 = mel("0:4:F#5:.4 4:4:E5:.38 8:4:E5:.4 12:4:D5:.38 "
            "16:1:E5:.5 17:.5:F#5:.5 17.5:1.5:G5:.55 19:.5:F#5:.5 19.5:.5:E5:.5 "
            "24:2:D5:.4 26:2:D5:.4 28:2:D5:.42 30:1:C#5:.4")

EP_C = mel("""
.5:.5:D5 1:.5:C#5 1.5:1.5:D5 3:1:F#5
4:2:E5 6:.5:D5 6.5:.5:C#5 7:1:B4
8.5:.5:D5 9:.5:C#5 9.5:1.5:D5 11:1:F#5
12:1:F#5 13:1:D5 14:1:F5 15:.5:D5 15.5:.5:B4
16:1.5:C#5 17.5:.5:E5 18:2:G#5
20:1:A5 21:.5:F#5 21.5:1:D#5 22.5:.5:C5 23:1:B4
24:.75:D5 24.75:2.25:F#5 27:.5:E5 27.5:.5:D5
28:1.5:E5 29.5:.5:D5 30:1.5:C#5""", 0.72)

VB_S1 = mel("""
0:.5:F#4 .5:.5:A4 1:.5:C#5 1.5:1:E5 2.5:.5:D5 3:.5:A4 3.5:.5:B4
4:.5:D5 4.5:.5:E5 5:.75:F5 5.75:.75:E5 6.5:.5:D5 7:1:B4
16:.75:B4 16.75:.75:D5 17.5:1:F#5 18.5:.5:E5 19:.5:D5 19.5:.5:B4
20:1:C#5 21:.5:E5 21.5:.5:F#5 22:1:G5 23:1:E5""", 0.8)
FL_S1 = mel("""
8.5:.5:C#5 9:.5:E5 9.5:1.5:A5 11:.5:G#5 11.5:.5:E5
12:1:D#5 13:.5:F#5 13.5:.5:A5 14:.5:C6 14.5:.5:B5 15:.5:A5 15.5:.5:F#5
24:.5:E5 24.5:.5:F#5 25:1:A5 26:.5:A5 26.5:.5:F#5 27:.5:D#5 27.5:.5:B4
28:.75:D5 28.75:1.25:F#5 30:.5:E5 30.5:.5:C#5 31:.5:B4 31.5:.5:A4""", 0.8)
EP_S2 = mel("""
.5:.5:E5 1:.5:F#5 1.5:1:A5 2.5:.5:F#5 3:1:E5
4:.5:D5 4.5:.5:B4 5:.5:D5 5.5:.5:E5 6:1:F5 7:.5:E5 7.5:.5:D5""", 0.72)
VB_S2 = mel("""
8:1:C#5 9:.5:A4 9.5:.5:C#5 10:1.5:E5 11.5:.5:D#5
12:1:F#5 13:.5:D#5 13.5:.5:C5 14:1:A4
24:1:E5:.6 25:.5:D5:.6 25.5:.5:B4:.6 26:1:E5:.6 27:.5:C#5:.6 27.5:.5:A4:.6 28:2:F#4:.6""", 0.8)
FL_S2 = mel("""
16:.75:F#5 16.75:2.25:B5 19:.5:A5 19.5:.5:G5
20:1:F#5 21:.5:E5 21.5:.5:C#5 22:.5:E5 22.5:.5:G5 23:1:F#5
24:1:G5 25:.5:F#5 25.5:.5:E5 26:1:G5 27:.5:E5 27.5:.5:C#5 28:2:D5""", 0.84)

# vibrafone dobra a flauta uma oitava abaixo no último A (compassos 1-6)
VB_A4 = [(p, d, sy.midi(n) - 12, 0.42) for (p, d, n, v) in FL_A4 if 0 <= p < 24]

# ---------------------------------------------------------------------------
# Arranjo por seção (intensidades)
# ---------------------------------------------------------------------------
DRUMS = {
    'intro': dict(shaker=.55, sweep=.5, slap=.0, tap=.35, rim=.0, kick=.0),
    'A1': dict(shaker=.7, sweep=.7, slap=.65, tap=.5, rim=.0, kick=.7),
    'A2': dict(shaker=.75, sweep=.75, slap=.7, tap=.55, rim=.7, kick=.75),
    'B1': dict(shaker=.8, sweep=.85, slap=.75, tap=.65, rim=.0, kick=.75),
    'A3': dict(shaker=.8, sweep=.8, slap=.8, tap=.6, rim=.8, kick=.8),
    'C': dict(shaker=.6, sweep=.45, slap=.0, tap=.4, rim=.65, kick=.0),
    'S1': dict(shaker=.82, sweep=.85, slap=.8, tap=.65, rim=.8, kick=.8),
    'S2': dict(shaker=.82, sweep=.85, slap=.82, tap=.65, rim=.8, kick=.8),
    'B2': dict(shaker=.8, sweep=.85, slap=.78, tap=.6, rim=.0, kick=.75),
    'A4': dict(shaker=.85, sweep=.85, slap=.82, tap=.65, rim=.82, kick=.8),
}
GTR_VEL = {'intro': .8, 'A1': .85, 'A2': .85, 'B1': .85, 'A3': .9, 'C': .8, 'S1': .9, 'S2': .9, 'B2': .85, 'A4': .9}
EP_COMP = {'A3', 'S1', 'S2', 'B2', 'A4'}

BAT_A = [(0, .66), (3, .55), (6, .64), (10, .57), (12, .6)]
BAT_B = [(2, .58), (5, .6), (9, .55), (12, .6), (14, .68)]
CLAVE_A, CLAVE_B = [0, 6, 12], [4, 10]


def bar_roots(b, lo):
    """Notas de baixo dos tempos 1 e 3 (fundamental/quinta ou 2º acorde)."""
    chs = BARS[b][2]
    r1 = low_note(parse_chord(chs[0])[2], lo)
    if len(chs) > 1:
        r2 = low_note(parse_chord(chs[1])[2], lo)
    else:
        r2 = r1 - 5 if r1 - 5 >= lo else r1 + 7
    return r1, r2


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render():
    st = {k: Stem() for k in ('gtr', 'thumb', 'bass', 'flute', 'vibes', 'ep', 'kick', 'brush', 'rim', 'shaker')}

    # ---------------- violão ----------------
    for b in range(NBARS):
        sec, k, chs = BARS[b]
        gb0 = b * 4
        gv = GTR_VEL[sec]
        if sec == 'A4' and k == 7:
            gv *= 0.92
        # polegar: tempos 1 e 3
        r1, r2 = bar_roots(b, 40)
        for pos, note, v in ((0.0, r1, .72), (2.0, r2, .64)):
            t = tsec(gb0 + pos) + jit(5) - 0.004
            x = sy.nylon(note, BEAT * 1.9, vel=hv(v * gv), bright=0.33, seed=nseed())
            st['thumb'].add(x, t)
        if sec == 'C':
            # interlúdio: arpejo dedilhado que deixa as cordas soarem
            order = [1, 2, 3, 2, 3, 1] if b % 2 == 0 else [1, 3, 2, 3, 1, 2]
            for step, vi in zip([2, 4, 6, 10, 12, 14], order):
                gb = gb0 + step / 4.0
                seg = seg_at(gb + 0.5) if step % 8 >= 6 else seg_at(gb)
                note = seg[3][vi]
                t = tsec(gb) + jit(7)
                x = sy.nylon(note, BEAT * 1.6, vel=hv(.58 * gv), bright=0.42, seed=nseed())
                st['gtr'].add(x, t)
            continue
        pat = BAT_A if b % 2 == 0 else BAT_B
        nxt = BAT_B if b % 2 == 0 else BAT_A
        steps = [p for p, _ in pat] + [16 + nxt[0][0]]
        for i, (step, v) in enumerate(pat):
            gb = gb0 + step / 4.0
            seg = seg_at(gb + 0.5) if step % 8 >= 6 else seg_at(gb)
            notes = list(seg[3])
            if v < 0.58 and HR.random() < 0.5:
                notes = notes[1:]                       # pinçada leve: só as 3 de cima
            gap = min(steps[i + 1] - step, 4)
            dur = gap * S16 + 0.05
            t0 = tsec(gb) + jit(6)
            vel = hv(v * gv)
            spread = HR.uniform(0.0015, 0.0035)
            for j, n in enumerate(notes):
                x = sy.nylon(n, dur + 0.12, vel=vel * (0.92 + 0.08 * j / 3), bright=0.48, seed=nseed())
                # abafa no fim (mão esquerda alivia a pressão)
                x[-sy.nsamp(0.1):] *= np.linspace(1, 0, sy.nsamp(0.1)) ** 2
                st['gtr'].add(x, t0 + j * spread)

    # ---------------- contrabaixo ----------------
    for b in range(NBARS):
        sec, k, chs = BARS[b]
        gb0 = b * 4
        r1, r2 = bar_roots(b, 33)
        if sec == 'C':
            for pos, note, v in ((0.0, r1, .8), (2.0, r2, .7)):
                st['bass'].add(sy.bass_upright(note, BEAT * 1.9, vel=hv(v, .04), seed=nseed()), tsec(gb0 + pos) + jit(4))
            continue
        evs = [(0.0, r1, 1.4, .82), (2.0, r2, 1.4, .72)]
        nb = (b + 1) % NBARS
        nr, _ = bar_roots(nb, 33)
        if sec != 'intro' and (b % 2 == 1 or len(chs) > 1) and nr != r2:
            appr = nr + (1 if r2 > nr else -1)
            evs.append((3.5, appr, 0.45, .55))
        elif sec != 'intro' and b % 4 == 2:
            evs.append((1.5, r1 + 12 if r1 + 12 <= 47 else r1, 0.45, .45))
        for pos, note, d, v in evs:
            st['bass'].add(sy.bass_upright(note, BEAT * d, vel=hv(v, .04), seed=nseed()), tsec(gb0 + pos) + jit(4))

    # ---------------- Rhodes (comping) ----------------
    for b in range(NBARS):
        sec, k, chs = BARS[b]
        if sec not in EP_COMP or (sec == 'S2' and k < 2):
            continue
        gb0 = b * 4
        hits = [(6, 7, .42)] if b % 2 == 0 else [(2, 3, .36), (10, 5, .4)]
        for step, ln, v in hits:
            gb = gb0 + step / 4.0
            seg = seg_at(gb + 0.5) if step % 8 >= 6 else seg_at(gb)
            t0 = tsec(gb) + jit(6)
            vel = hv(v)
            for j, n in enumerate(seg[4]):
                st['ep'].add(sy.epiano(n, ln * S16 + 0.25, vel=vel, seed=nseed()), t0 + j * 0.004)

    # ---------------- melodias ----------------
    def play(stem, notes, sec, fn, legato=0.04, gain=1.0, accent=True):
        base = SEC_START[sec]
        for pos, d, n, v in notes:
            gb = base + pos
            vv = v * (1.06 if (accent and abs(pos - round(pos)) < 1e-6 and round(pos) % 2 == 0) else 1.0)
            dur = d * BEAT + legato
            t = tsec(gb) + jit(7)
            stem.add(fn(n, dur, hv(vv, .05), nseed()), t, gain)

    flute = lambda n, d, v, s: sy.flute(n, d, v, seed=s)                       # noqa: E731
    vib = lambda n, d, v, s: vibes2(n, d + 0.6, v, seed=s)                     # noqa: E731
    epl = lambda n, d, v, s: sy.epiano(n, d + 0.3, v, seed=s)                 # noqa: E731

    play(st['flute'], FL_A1, 'A1', flute)
    play(st['flute'], FL_A2, 'A2', flute)
    play(st['flute'], FL_A3, 'A3', flute)
    play(st['flute'], FL_S1, 'S1', flute)
    play(st['flute'], FL_S2, 'S2', flute)
    play(st['flute'], FL_B2, 'B2', flute, legato=0.06)
    play(st['flute'], FL_A4, 'A4', flute)
    play(st['vibes'], VB_INTRO, 'intro', vib)
    play(st['vibes'], VB_A2, 'A2', vib)
    play(st['vibes'], VB_B1, 'B1', vib)
    play(st['vibes'], VB_S1, 'S1', vib)
    play(st['vibes'], VB_S2, 'S2', vib)
    play(st['vibes'], VB_B2, 'B2', vib)
    play(st['vibes'], VB_A4, 'A4', vib)
    play(st['ep'], EP_C, 'C', epl, gain=1.25)
    play(st['ep'], EP_S2, 'S2', epl, gain=1.25)

    # ---------------- percussão ----------------
    for b in range(NBARS):
        sec, k, chs = BARS[b]
        dr = dict(DRUMS[sec])
        if sec == 'intro':
            dr['shaker'] *= 0.85 + 0.05 * k
        if sec == 'A4' and k == 7:
            dr['kick'] = 0.0
            dr['slap'] *= 0.8
        gb0 = b * 4
        for s16 in range(16):
            gb = gb0 + s16 / 4.0
            t = tsec(gb) + jit(5)
            acc = (.55, .3, .8, .38)[s16 % 4]
            st['shaker'].add(SHAKERS[int(HR.integers(0, 8))], t, hv(acc * dr['shaker'], .1))
        if dr['sweep']:
            for h in range(2):
                t = tsec(gb0 + 2 * h) + jit(8)
                st['brush'].add(brush_sweep(2 * BEAT + 0.1, hv(dr['sweep'], .08), nseed()), t)
        if dr['slap']:
            for s16 in (4, 12):
                st['brush'].add(SLAPS[int(HR.integers(0, 4))], tsec(gb0 + s16 / 4.0) + jit(5), hv(dr['slap'], .07))
        if dr['tap']:
            for s16 in (3, 7, 11, 14):
                st['brush'].add(TAPS[int(HR.integers(0, 6))], tsec(gb0 + s16 / 4.0) + jit(5), hv(.45 * dr['tap'], .12))
        if dr['rim']:
            for s16 in (CLAVE_A if b % 2 == 0 else CLAVE_B):
                st['rim'].add(RIMS[int(HR.integers(0, 4))], tsec(gb0 + s16 / 4.0) + jit(4), hv(dr['rim'], .07))
        if dr['kick']:
            ks = [(0, .8), (8, .62)] if b % 2 == 0 else [(0, .78), (6, .35), (8, .6)]
            for s16, v in ks:
                st['kick'].add(KICK, tsec(gb0 + s16 / 4.0) + jit(3), hv(v * dr['kick'], .05))
    return st


# ---------------------------------------------------------------------------
# Mixagem
# ---------------------------------------------------------------------------
#        ganho   pan    HP    LP     envio reverb
MIXCFG = {
    'gtr':    (1.00, -0.34, 130, 9000, 0.22),
    'thumb':  (0.95, -0.12, 55, 5000, 0.10),
    'bass':   (1.15, 0.00, 35, 1800, 0.03),
    'flute':  (1.05, 0.26, 180, 9000, 0.30),
    'vibes':  (0.95, -0.40, 150, 8000, 0.32),
    'ep':     (0.95, 0.42, 120, 6000, 0.28),
    'kick':   (0.55, 0.00, 30, 220, 0.00),
    'brush':  (0.75, 0.18, 280, 7000, 0.18),
    'rim':    (0.42, -0.22, 400, 6500, 0.22),
    'shaker': (0.55, 0.58, 2200, 8000, 0.12),
}


def pan2(x, pan):
    ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.vstack([x * np.cos(ang), x * np.sin(ang)])


def mixdown(st, report=True):
    dry = np.zeros((2, N_TOTAL))
    send = np.zeros((2, N_TOTAL))
    for name, (g, pan, hp, lp, snd) in MIXCFG.items():
        x = st[name].buf
        x = sy.highpass(x, hp)
        x = sy.lowpass(x, lp)
        x = x * g
        s2 = pan2(x, pan)
        if name == 'flute':
            # eco discreto em colcheia pontuada (pingue-pongue)
            s2 = sy.delay_fx(s2, time=BEAT * 0.75, fb=0.28, wet=0.12, lp=2800)
        if name == 'gtr':
            s2 = sy.stereo_widen(s2, 0.25)
        if report:
            r = np.sqrt(np.mean(s2[:, sy.nsamp(PRE):sy.nsamp(PRE + LOOP)] ** 2)) + 1e-12
            print('  stem %-7s rms %6.1f dB' % (name, 20 * np.log10(r)))
        dry += s2
        send += s2 * snd
        st[name].buf = None
    ir = sy.make_ir(t60=2.2, predelay=0.024, bright=0.38, seed=11)
    send = sy.highpass(send, 220)
    wet = np.zeros_like(send)
    for ch in range(2):
        wet[ch] = signal.oaconvolve(send[ch], ir[ch])[:N_TOTAL]
    mix = dry + wet * 0.55
    # tons graves sujos fora, brilho extremo domado (jogo toca por horas)
    mix = sy.highpass(mix, 32)
    mix = sy.peak_eq(mix, 320, -1.5, 0.9)
    mix = sy.peak_eq(mix, 7500, -2.5, 0.7)
    return mix


def fold_loop(mix):
    """Pré-rolagem -> fim do loop; cauda -> início (sy.seamless_loop)."""
    P = sy.nsamp(PRE)
    L = sy.nsamp(LOOP)
    main = mix[:, P:].copy()
    main[:, L - P:L] += mix[:, :P]
    return sy.seamless_loop(main, LOOP)


def cyclic_compress(y, **kw):
    P = sy.nsamp(3.0)
    ext = np.concatenate([y[:, -P:], y, y[:, :P]], axis=1)
    ext = sy.compress(ext, **kw)
    return ext[:, P:-P]


def main():
    t0 = time.time()
    print('Manhã na Horta: %d compassos, %.2f s, %d BPM' % (NBARS, LOOP, BPM))
    st = render()
    print('  render %.1f s' % (time.time() - t0))
    mix = mixdown(st)
    y = fold_loop(mix)
    del mix
    rms = np.sqrt(np.mean(y ** 2))
    y *= 10 ** (-20 / 20) / rms                      # RMS ~ -20 dBFS antes da compressão de barramento
    y = cyclic_compress(y, thresh_db=-21, ratio=1.8, attack=0.02, release=0.25)
    res = sy.master_and_export(y, OUT, target_lufs=TARGET_LUFS, ceiling_db=-1.2, quality=QUALITY,
                               loop=True, title='Manhã na Horta')
    print(res)
    print('  total %.1f s' % (time.time() - t0))
    return res


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Mundo Renda - "Dia de Feira" (baião / forró pé-de-serra, Sol mixolídio, 118 BPM, 2/4).

Música original, 100% sintetizada por código (nenhum sample, nenhuma melodia existente).
Trio nordestino: sanfona, zabumba e triângulo, mais um baixo que dobra a zabumba e um pífano
que conversa com a sanfona. Cores de baião: sétima menor (Fá natural) e quarta aumentada
(Dó#, escala "nordestina" / lídio-dominante); seção C em Mi dórico (Dó#).

Forma (144 compassos de 2/4 = 146,4 s; loop perfeito: o fim do refrão puxa a introdução):
  intro (8)  "introdução" da sanfona (riff com b7 e #4) sobre G7 | G7 | F | G | G7 | G7 | C | D7
  A     (16) tema na sanfona; a segunda sanfona responde nos compassos 8 e 16
  B     (16) refrão em terças (duas sanfonas), zabumba mais cheia, baixo com aproximações
  riff  (8)  a introdução volta em oitavas (interlúdio)
  A'    (16) pergunta e resposta: sanfona chama (2 compassos), pífano responde (2 compassos)
  C     (16) Mi dórico, mais leve: pífano canta, sanfona responde; foles sustentados, zabumba rala
  C'    (8)  pífano + sanfona em terças, banda cheia de novo, cadência em D7
  S     (16) solo escrito da sanfona (semicolcheias), pífano responde nas brechas
  sobe  (6)  Am7 D7 Am7 D7 C C#dim7: subida em terças, zabumba cresce
  breque(2)  a banda para junto (3 golpes em D7), sanfona sozinha puxa o tema
  A''   (16) tema ornamentado em terças, pífano nas respostas
  B'    (16) refrão final em terças + pífano em uníssono; corrida cromática devolve à introdução

Groove: zabumba no baião clássico (bum no 1 e no "a" do 1, abafado no 2, bacalhau no "e" do 2
e fantasmas), triângulo em semicolcheias (fechado nos tempos, aberto nos contratempos, com a mão
abafando o toque aberto), baixo dobrando a zabumba, acordes da sanfona nos contratempos.
Humanização: swing leve nas semicolcheias pares, desvio de tempo de 2 a 6 ms, dinâmica variável.

Uso (a partir de jogo-mundo-renda/):  python3 tools/audio/musica_feira.py
Saída: android/assets/www/audio/feira.ogg
"""
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np                      # noqa: E402
from scipy import signal               # noqa: E402
from scipy.ndimage import maximum_filter1d  # noqa: E402

import synth as sy                     # noqa: E402

SR = sy.SR
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'android', 'assets', 'www', 'audio', 'feira.ogg')

BPM = 118.0
S16 = 60.0 / BPM / 4.0          # semicolcheia (s)
SWING = 0.07                    # atraso das semicolcheias "fracas" (fração de semicolcheia, ~9 ms)
TAIL = 4.0                      # cauda renderizada após o fim (dobrada sobre o início)
TARGET_LUFS = -18.0
QUALITY = 4

# ---------------------------------------------------------------------------
# Harmonia (um compasso de 2/4 por '|'; dois acordes num compasso dividem os tempos)
# ---------------------------------------------------------------------------
H_RIFF = 'G7 | G7 | F | G | G7 | G7 | C | D7'
H_HEAD = 'G | G | G7 | G7 | C | C | G | D7 | G | G | G7 | G7 | C | Cm6 | G/D D7 | G'
H_CHORUS = 'C | C | G | G | D7 | D7 | G | G7 | C | C | G | E7 | Am | D7 | G | D7'
H_C = 'Em | Em | A7 | A7 | Em | Em | B7 | B7 | Em | Em | A7 | A7 | C | B7 | Em | Em'
H_C2 = 'Em | Em | A7 | A7 | C | C | D7 | D7'
H_SOLO = 'G7 | G7 | C | C | G7 | G7 | D7 | D7 | G7 | G7 | C | Cm6 | G | E7 | Am7 D7 | G'
H_BUILD = 'Am7 | D7 | Am7 | D7 | C | C#dim7'
H_BRK = 'D7 | D7'

# ---------------------------------------------------------------------------
# Melodias escritas.  Ficha "NOTA:duração" em semicolcheias; r = pausa; "-:n" prolonga a nota
# anterior; "(X)NOTA" = apojatura (grace note) de X para NOTA; sufixo ">" = acento.
# Cada compasso soma 8 semicolcheias (verificado pelo parser).
# ---------------------------------------------------------------------------
RIFF = ('D6:1 C6:1 B5:1 G5:2 A5:1 B5:1 G5:1 | F5:3 G5:1 r:2 D5:1 E5:1 | '
        'F5:1 A5:1 C6:1 A5:2 G5:1 F5:1 E5:1 | (C#5)D5:3 B4:1 G4:2 r:2 | '
        'D6:1 C6:1 B5:1 G5:2 A5:1 B5:1 G5:1 | F5:3 G5:1 r:2 B5:1 C#6:1 | '
        'D6:1 E6:2 D6:1 C6:1 G5:1 E5:1 G5:1 | A5:2 F#5:1 A5:1 C6:2 A5:1 F#5:1')
RIFF2 = ('D6:1 C6:1 B5:1 G5:2 A5:1 B5:1 G5:1 | F5:3 G5:1 r:2 D5:1 E5:1 | '
         'F5:1 A5:1 C6:1 A5:2 G5:1 F5:1 E5:1 | (C#5)D5:3 B4:1 G4:2 B4:1 C#5:1 | '
         'D6:1 C6:1 B5:1 G5:2 A5:1 B5:1 D6:1 | F6:3 E6:1 D6:2 B5:1 C#6:1 | '
         'D6:1 E6:2 D6:1 C6:1 G5:1 E5:1 G5:1 | A5:2 F#5:1 A5:1 C6:2 A5:1 F#5:1')

HEAD = ('D5:2 G5:1 A5:1 B5:3 A5:1 | G5:3 E5:1 D5:4 | D5:2 G5:1 A5:1 B5:3 C6:1 | D6:4 C6:1 B5:1 A5:1 F5:1 | '
        'E5:2 G5:1 C6:1 E6:3 D6:1 | C6:3 A5:3 G5:2 | B5:2 A5:1 G5:1 E5:2 D5:2 | A5:4 r:4 | '
        'D5:2 G5:1 A5:1 B5:3 A5:1 | G5:3 E5:1 D5:4 | D5:2 G5:1 A5:1 B5:3 C#6:1 | D6:3 E6:1 F6:2 E6:1 D6:1 | '
        'C6:2 B5:1 A5:1 G5:3 E5:1 | Eb5:3 G5:3 A5:2 | B5:3 G5:1 A5:2 F#5:2 | G5:4 r:4')
HEAD_ORN = ('D5:2 (F#5)G5:1 A5:1 B5:3> A5:1 | G5:3 E5:1 (C#5)D5:4 | D5:2 G5:1 A5:1 B5:3> C6:1 | D6:4 C6:1 B5:1 A5:1 F5:1 | '
            'E5:2 G5:1 C6:1 (D#6)E6:3> D6:1 | C6:3 A5:3 G5:2 | B5:2 A5:1 G5:1 E5:2 D5:2 | A5:4 r:4 | '
            'D5:2 (F#5)G5:1 A5:1 B5:3> A5:1 | G5:3 E5:1 (C#5)D5:4 | D5:2 G5:1 A5:1 B5:3> C#6:1 | D6:3 E6:1 F6:2 E6:1 D6:1 | '
            'C6:2 B5:1 A5:1 G5:3 E5:1 | Eb5:3 G5:3 A5:2 | B5:3 G5:1 A5:2 F#5:2 | G5:4 r:4')
# respostas da segunda sanfona nas brechas do tema (compassos 8 e 16)
FILL_A = ('r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:4 D4:1 F#4:1 A4:1 C5:1 | '
          'r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:4 G4:1 A4:1 B4:1 D5:1')
# no A'' quem responde é o pífano (uma oitava acima)
FILL_A3_PIFE = ('r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:4 D6:1 C6:1 A5:1 F#5:1 | '
                'r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:4 B5:1 C6:1 C#6:1 D6:1')

CHORUS = ('E5:2 G5:1 A5:1 G5:2 E5:2 | G5:3 A5:1 G5:4 | D5:2 G5:1 A5:1 B5:2 G5:2 | B5:3 C6:1 B5:4 | '
          'A5:2 F#5:1 G5:1 A5:2 C6:2 | B5:3 A5:1 F#5:2 D5:2 | G5:3 A5:1 B5:2 D6:2 | D6:2 B5:1 G5:1 F5:4 | '
          'E5:2 G5:1 A5:1 G5:2 E5:2 | G5:3 A5:1 C6:4 | B5:2 A5:1 G5:1 D5:2 G5:2 | G#5:3 A5:1 B5:4 | '
          'C6:2 B5:1 A5:1 E5:2 A5:2 | C6:3 B5:1 A5:2 F#5:2 | G5:8 | r:4 A5:1 B5:1 C6:1 C#6:1')

# A': pergunta (sanfona) e resposta (pífano)
A2_SANF = ('D5:2 G5:1 A5:1 B5:3 A5:1 | G5:3 E5:1 D5:4 | r:8 | r:8 | '
           'E5:2 G5:1 C6:1 E6:3 D6:1 | C6:3 A5:3 G5:2 | r:8 | r:8 | '
           'D5:2 G5:1 A5:1 B5:3 A5:1 | G5:3 E5:1 (C#5)D5:4 | r:8 | r:8 | '
           'C6:2 B5:1 A5:1 G5:3 E5:1 | Eb5:3 G5:3 A5:2 | B5:3 G5:1 A5:2 F#5:2 | G5:4 r:4')
A2_PIFE = ('r:8 | r:8 | D6:2 B5:1 D6:1 E6:3 D6:1 | F6:2 E6:1 D6:1 B5:4 | '
           'r:8 | r:8 | B5:2 A5:1 G5:1 E5:2 D5:2 | F#5:3 G5:1 A5:4 | '
           'r:8 | r:8 | r:2 B5:1 C#6:1 D6:2 F6:2 | E6:3 D6:1 B5:4 | '
           'r:8 | r:8 | B5:3 G5:1 A5:2 F#5:2 | G5:4 r:4')

# C: Mi dórico.  Pífano chama, sanfona responde; depois cantam juntos (sanfona em terças)
C_PIFE = ('(A5)B5:3 A5:1 G5:2 F#5:2 | E5:6 r:2 | r:8 | r:8 | '
          'E5:2 G5:1 A5:1 B5:3 C#6:1 | D6:3 C#6:1 B5:4 | r:8 | r:8 | '
          '(A5)B5:3 A5:1 G5:2 F#5:2 | E5:3 F#5:1 G5:4 | A5:3 B5:1 C#6:2 E6:2 | D6:3 C#6:1 A5:4 | '
          'G5:2 E5:1 G5:1 C6:2 B5:2 | F#5:3 A5:1 B5:2 D#6:2 | E6:4 B5:2 G5:2 | E5:6 r:2')
C_SANF = ('r:8 | r:8 | C#5:1 E5:1 G5:1 A5:2 G5:1 E5:1 C#5:1 | D5:3 C#5:1 A4:4 | '
          'r:8 | r:8 | D#5:1 F#5:1 A5:1 B5:2 A5:1 F#5:1 D#5:1 | E5:3 D#5:1 B4:4 | '
          'r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8')
C2_PIFE = ('B5:3 A5:1 G5:2 F#5:2 | E5:3 F#5:1 G5:2 A5:2 | C#6:3 B5:1 A5:2 G5:2 | A5:3 B5:1 C#6:2 E6:2 | '
           'E6:3 D6:1 C6:2 G5:2 | A5:3 G5:1 E5:2 G5:2 | F#5:2 A5:1 C6:1 D6:2 C6:2 | A5:4 r:4')

SOLO = ('G5:1 B5:1 D6:1 F6:1 E6:1 D6:1 B5:1 G5:1 | (G#5)A5:1 B5:1 C#6:1 D6:1 E6:2 D6:2 | '
        'E6:1 D6:1 C6:1 G5:1 E5:1 G5:1 C6:1 E6:1 | (D#6)E6:3 D6:1 C6:2 r:2 | '
        'B5:1 D6:1 B5:1 G5:1 F5:1 G5:1 B5:1 D6:1 | F6:2 E6:1 D6:1 C#6:1 D6:1 B5:2 | '
        'A5:1 B5:1 C6:1 D6:1 C6:1 A5:1 F#5:1 A5:1 | C6:3 B5:1 A5:2 r:2 | '
        'D5:1 G5:1 B5:1 D6:1 G5:1 B5:1 D6:1 F6:1 | E6:1 F6:1 E6:1 D6:1 B5:1 C#6:1 D6:2 | '
        'C6:1 E6:1 G5:1 C6:1 E5:1 G5:1 C5:1 E5:1 | Eb5:1 G5:1 A5:1 C6:1 Eb6:2 C6:2 | '
        'B5:3 A5:1 G5:2 D5:2 | G#5:1 B5:1 D6:1 E6:1 D6:2 B5:2 | '
        'C6:1 B5:1 A5:1 E5:1 F#5:1 A5:1 C6:1 A5:1 | G5:4 r:4')
SOLO_PIFE = ('r:8 | r:8 | r:8 | r:6 G5:1 A5:1 | r:8 | r:8 | r:8 | r:6 F#5:1 A5:1 | '
             'r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:8 | r:4 B5:1 A5:1 G5:1 E5:1')

BUILD = ('E5:2 A5:2 C6:2 A5:2 | F#5:2 A5:2 C6:2 A5:2 | G5:2 C6:2 E6:2 C6:2 | A5:2 C6:2 D6:2 F#6:2 | '
         'E6:3 D6:1 C6:2 E6:2 | E6:1 C#6:1 A#5:1 G5:1 E5:1 G5:1 A#5:1 C#6:1')
BRK_LEAD = 'D6:1> r:2 D6:1> r:2 D6:2> | r:4 A4:1 B4:1 C5:1 C#5:1'
BRK_SEC = 'A5:1> r:2 A5:1> r:2 A5:2> | r:8'
BRK_PIFE = 'D6:1> r:2 D6:1> r:2 D6:2> | r:8'

# ---------------------------------------------------------------------------
# Forma
# ---------------------------------------------------------------------------
FORM = [('intro', 8, H_RIFF, 0.90), ('A', 16, H_HEAD, 0.88), ('B', 16, H_CHORUS, 0.97),
        ('riff', 8, H_RIFF, 0.95), ('A2', 16, H_HEAD, 0.88), ('C', 16, H_C, 0.74),
        ('C2', 8, H_C2, 0.90), ('S', 16, H_SOLO, 0.95), ('build', 6, H_BUILD, 0.93),
        ('brk', 2, H_BRK, 1.0), ('A3', 16, H_HEAD, 0.95), ('B2', 16, H_CHORUS, 1.0)]

SEC = {}          # nome -> (compasso inicial, nº de compassos, energia)
HARM = []         # por compasso: lista de acordes
_b = 0
for _name, _nb, _h, _en in FORM:
    _bars = [c.split() for c in _h.split('|')]
    assert len(_bars) == _nb, _name
    SEC[_name] = (_b, _nb, _en)
    HARM.extend(_bars)
    _b += _nb
NBARS = _b
LOOP = NBARS * 8 * S16
N_TOTAL = sy.nsamp(LOOP + TAIL)
SECTION_OF_BAR = []
for _name, _nb, _h, _en in FORM:
    SECTION_OF_BAR += [_name] * _nb

# ---------------------------------------------------------------------------
# Teoria: acordes, escalas (para as terças) e vozes
# ---------------------------------------------------------------------------
PCN = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
QUAL = {'': [0, 4, 7], '7': [0, 4, 7, 10], 'm': [0, 3, 7], 'm7': [0, 3, 7, 10], 'm6': [0, 3, 7, 9],
        'dim7': [0, 3, 6, 9]}
# escala usada para a segunda voz (terça diatônica abaixo) em cada acorde
SCALES = {
    'G': 'G A B C D E F', 'G7': 'G A B C D E F', 'C': 'C D E F G A B', 'F': 'F G A B C D E',
    'D7': 'D E F# G A B C', 'E7': 'E F# G# A B C D', 'Am': 'A B C D E F# G', 'Am7': 'A B C D E F# G',
    'Cm6': 'C D Eb F G A Bb', 'Em': 'E F# G A B C# D', 'A7': 'A B C# D E F# G', 'B7': 'B C D# E F# G A',
    'C#dim7': 'C# E G Bb',
}


def pc_of(name):
    return (PCN[name[0]] + name.count('#') - name.count('b')) % 12


def parse_chord(sym):
    """'G/D' -> (raiz, baixo, [pcs], tipo)."""
    bass = None
    if '/' in sym:
        sym, bass = sym.split('/')
    m = re.match(r'^([A-G][#b]?)(.*)$', sym)
    root = pc_of(m.group(1))
    q = m.group(2)
    pcs = [(root + i) % 12 for i in QUAL[q]]
    return root, (pc_of(bass) if bass else root), pcs, sym


def scale_pcs(sym):
    base = sym.split('/')[0]
    return [pc_of(x) for x in SCALES[base].split()]


def chord_at(t16):
    bar = int(t16 // 8) % NBARS
    chs = HARM[bar]
    k = min(len(chs) - 1, int((t16 % 8) * len(chs) // 8))
    return chs[k]


def third_below(note, sym, structural):
    """Terça diatônica abaixo de `note` na escala do acorde; em notas de apoio prefere nota do acorde."""
    sc = sorted(set(scale_pcs(sym)))
    _, _, pcs, _ = parse_chord(sym)
    note = int(note)
    cands = []
    k = 0
    m = note - 1
    while k < 2 and m > note - 7:            # 2 graus da escala abaixo
        if m % 12 in sc:
            k += 1
            if k == 2:
                cands.append(m)
        m -= 1
    if 'dim7' in sym:                        # arpejo diminuto: terça menor abaixo
        return note - 3
    if note % 12 not in sc:                  # nota cromática (ex.: Dó# sobre G7): terça "de verdade"
        opts = [m for m in (note - 3, note - 4) if m % 12 in sc]
        best = [m for m in opts if m % 12 in pcs]
        return (best or opts or [note - 3])[0]
    low = cands[0] if cands else note - 3
    if structural and low % 12 not in pcs:
        for alt in (note - 3, note - 4):
            if alt % 12 in pcs:
                return alt
    return low


def voicing(sym, prev, lo=52, hi=67):
    """Acorde fechado da mão esquerda (região E3..G4) com condução de vozes."""
    _, _, pcs, _ = parse_chord(sym)
    if len(pcs) == 4 and 'dim7' not in sym and 'm6' not in sym:
        pcs = [pcs[0], pcs[1], pcs[3]]       # tétrade de dominante: sem a quinta (fica leve)
    opts = []
    for base in range(lo, hi + 1):
        if base % 12 not in pcs:
            continue
        notes = []                           # monta o acorde acima da nota mais grave
        for p in pcs:
            n = base + ((p - base) % 12)
            notes.append(n)
        notes = sorted(notes)
        if notes[-1] <= hi:
            opts.append(notes)
    if prev is None:
        target = (lo + hi) / 2.0
        return min(opts, key=lambda v: abs(np.mean(v) - target))
    return min(opts, key=lambda v: sum(abs(a - b) for a, b in zip(sorted(v), sorted(prev))) + 0.1 * abs(np.mean(v) - 60))


# ---------------------------------------------------------------------------
# Parser de melodia
# ---------------------------------------------------------------------------
TOK = re.compile(r'^(?:\(([A-G][#b]?\d)\))?([A-G][#b]?\d|r|-):(\d+)(>?)$')


def parse(s, bar0):
    ev = []
    for bi, bar in enumerate(s.split('|')):
        pos = 0
        for tok in bar.split():
            m = TOK.match(tok)
            if not m:
                raise ValueError('ficha inválida: %r' % tok)
            grace, note, d, acc = m.groups()
            d = int(d)
            if note == '-':
                ev[-1]['d16'] += d
            elif note != 'r':
                ev.append({'t16': (bar0 + bi) * 8 + pos, 'd16': d, 'midi': sy.midi(note),
                           'acc': bool(acc), 'grace': sy.midi(grace) if grace else None})
            pos += d
        if pos != 8:
            raise ValueError('compasso %d soma %d semicolcheias: %r' % (bi, pos, bar))
    return ev


def thirds(events, transpose=0):
    out = []
    for e in events:
        sym = chord_at(e['t16'])
        structural = e['d16'] >= 2 or e['t16'] % 2 == 0
        lo = third_below(e['midi'] + transpose, sym, structural)
        g = None
        if e['grace'] is not None:
            g = lo - (e['midi'] - e['grace'])
        out.append(dict(e, midi=float(lo), grace=g))
    return out


def shift(events, semis):
    return [dict(e, midi=e['midi'] + semis, grace=(e['grace'] + semis if e['grace'] is not None else None))
            for e in events]


def t_of(t16):
    """Tempo (s) de uma posição em semicolcheias, com swing nas semicolcheias fracas."""
    t = t16 * S16
    if int(round(t16)) % 2 == 1:
        t += SWING * S16
    return t


# ---------------------------------------------------------------------------
# Instrumentos (definidos aqui; synth.py só fornece utilidades)
# ---------------------------------------------------------------------------
TBL = 2048
_TX = np.arange(TBL + 1)
_TCACHE = {}


def reed_table(f0, bright):
    """Um ciclo de palheta livre: harmônicos 1/h^0.8 (pares um pouco mais fracos), formante da
    câmara (~1,1 kHz), rolagem suave acima de 1,5-4,3 kHz e teto em 6 kHz (nada de zumbido)."""
    key = (int(round(f0 * 2)), int(round(bright * 40)))
    tb = _TCACHE.get(key)
    if tb is not None:
        return tb
    nh = max(1, int(min(48, SR * 0.40 / f0)))
    h = np.arange(1, nh + 1, dtype=float)
    f = h * f0
    amp = h ** -0.8
    amp *= np.where(h % 2 == 1, 1.0, 0.7)
    fc = 1500.0 + 2800.0 * bright
    amp *= 1.0 / np.sqrt(1.0 + (f / fc) ** 4)
    amp *= 1.0 + 0.7 * np.exp(-0.5 * (np.log2(f / 1100.0) / 0.55) ** 2)
    amp *= f / (f + 160.0)
    amp *= 1.0 / np.sqrt(1.0 + (f / 6000.0) ** 8)
    ph = 2 * np.pi * np.arange(TBL) / TBL
    phases = (0.5 * np.pi * h * h / nh) % (2 * np.pi)          # fases tipo Schroeder: menos pico
    tb = (amp[:, None] * np.sin(h[:, None] * ph[None, :] + phases[:, None])).sum(0)
    tb /= np.max(np.abs(tb)) + 1e-9
    tb = np.append(tb, tb[0])
    _TCACHE[key] = tb
    return tb


# registros (desafinação em cents, oitava, ganho): duas palhetas médias levemente desafinadas
# (batimento ~2-4 Hz, "tremolo" seco de sanfona de forró) + palheta grave para corpo
REG_LEAD = [(0.0, 0, 1.0), (7.0, 0, 0.72), (-1.5, -1, 0.40)]
REG_SEC = [(0.0, 0, 1.0), (-6.0, 0, 0.65), (1.0, -1, 0.30)]
REG_COMP = [(0.0, 0, 1.0), (5.0, 0, 0.55), (0.0, -1, 0.18)]


def sanfona(note, dur, vel, reg, bright, seed, att=0.016, rel=0.035):
    rng = np.random.default_rng(seed)
    n = sy.nsamp(dur + rel * 6)
    t = np.arange(n) / SR
    out = np.zeros(n)
    drift = rng.normal(0.0, 1.0)
    bloom = 1.0 - np.exp(-t / 0.03)              # os harmônicos agudos "abrem" logo após o ataque
    gsum = 0.0
    for cents, octv, g in reg:
        f0 = sy.freq(note + 12 * octv) * 2 ** ((cents + drift) / 1200.0)
        tb = reed_table(f0, bright)
        td = reed_table(f0, bright * 0.2)
        ph = ((rng.uniform() + f0 * t) % 1.0) * TBL
        a = np.interp(ph, _TX, tb)
        b = np.interp(ph, _TX, td)
        out += g * (b + (a - b) * bloom)
        gsum += g
    out /= gsum
    na = max(1, sy.nsamp(att))
    env = np.ones(n)
    env[:na] = (np.arange(na) / na) ** 1.4
    env *= 0.9 + 0.1 * np.exp(-t / 0.2)          # pressão do fole assenta
    nd = min(n, sy.nsamp(dur))
    env[nd:] *= np.exp(-(t[nd:] - dur) / rel)
    env[-sy.nsamp(0.004):] *= np.linspace(1, 0, sy.nsamp(0.004))
    return out * env * (vel ** 1.3) * 0.5


def pife(note, dur, vel, seed):
    """Pífano de taboca: quase senoidal, sopro audível, leve 'scoop' de afinação e vibrato tardio."""
    rng = np.random.default_rng(seed)
    f0 = sy.freq(note) * 2 ** (rng.normal(0.0, 3.0) / 1200.0)
    n = sy.nsamp(dur + 0.12)
    t = np.arange(n) / SR
    scoop = -28.0 * np.exp(-t / 0.025)
    ramp = np.clip((t - 0.16) / 0.25, 0, 1)
    vib = 10.0 * ramp * np.sin(2 * np.pi * 5.4 * t + rng.uniform(0, 6.28))
    f = f0 * 2 ** ((scoop + vib) / 1200.0)
    ph = 2 * np.pi * np.cumsum(f) / SR + rng.uniform(0, 6.28)
    s = np.sin(ph) + 0.30 * np.sin(2 * ph + 0.4) + 0.11 * np.sin(3 * ph + 1.3) + 0.035 * np.sin(4 * ph + 2.0)
    nz = rng.standard_normal(n)
    breath = sy.bandpass(nz, f0 * 0.85, min(f0 * 2.6, 9000.0)) * 0.18
    hiss = sy.lowpass(sy.highpass(nz, 1500.0), 5500.0) * 0.012
    na = sy.nsamp(0.035)
    env = np.ones(n)
    env[:na] = np.linspace(0, 1, na) ** 1.2
    env *= 1.0 + 0.12 * np.exp(-t / 0.06)
    nd = min(n, sy.nsamp(dur))
    env[nd:] *= np.exp(-(t[nd:] - dur) / 0.03)
    env[-sy.nsamp(0.004):] *= np.linspace(1, 0, sy.nsamp(0.004))
    y = (s + breath + hiss) * env
    m = sy.nsamp(0.03)
    y[:m] += sy.bandpass(rng.standard_normal(m), 1800, 5500) * np.linspace(0.18, 0, m)
    return y * vel * 0.32


def baixo(note, dur, vel, seed):
    """Baixo dedilhado redondo: fundamental firme, harmônicos que somem rápido, 'thump' do dedo."""
    rng = np.random.default_rng(seed)
    f0 = sy.freq(note)
    n = sy.nsamp(dur + 0.25)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f0 * t + rng.uniform(0, 6.28)
    s = (np.sin(ph) + 0.50 * np.exp(-t / 0.35) * np.sin(2 * ph) + 0.22 * np.exp(-t / 0.18) * np.sin(3 * ph)
         + 0.10 * np.exp(-t / 0.10) * np.sin(4 * ph) + 0.05 * np.exp(-t / 0.06) * np.sin(5 * ph))
    env = (1 - np.exp(-t / 0.003)) * (0.6 + 0.4 * np.exp(-t / 0.25))
    nd = min(n, sy.nsamp(dur))
    env[nd:] *= np.exp(-(t[nd:] - dur) / 0.04)
    m = sy.nsamp(0.02)
    thump = np.zeros(n)
    thump[:m] = sy.lowpass(rng.standard_normal(m), 900) * np.linspace(1, 0, m) * 0.12
    y = sy.lowpass(s * env + thump, 1600)
    y[-sy.nsamp(0.004):] *= np.linspace(1, 0, sy.nsamp(0.004))
    return y * vel * 0.6


def zabumba(kind, vel, seed):
    """'bum' (maceta, pele grave aberta), 'abafa' (maceta com a pele abafada), 'bac' (bacalhau)."""
    rng = np.random.default_rng(seed)
    if kind == 'bac':
        n = sy.nsamp(0.16)
        t = np.arange(n) / SR
        snap = sy.bandpass(rng.standard_normal(n), 800, 4200) * np.exp(-t / 0.014)
        tone = 0.55 * np.sin(2 * np.pi * 395 * t) * np.exp(-t / 0.04) + 0.3 * np.sin(2 * np.pi * 640 * t + 1) * np.exp(-t / 0.022)
        thump = 0.3 * np.sin(2 * np.pi * 88 * t) * np.exp(-t / 0.06)
        s = sy.lowpass(snap * 0.9 + tone + thump, 6000)
        return sy.fade(s, 0.0005, 0.01) * vel * 0.5
    bum = kind == 'bum'
    n = sy.nsamp(0.7 if bum else 0.22)
    t = np.arange(n) / SR
    f = (68.0 if bum else 76.0) + 52.0 * np.exp(-t / 0.02)
    ph = 2 * np.pi * np.cumsum(f) / SR
    dec = 0.32 if bum else 0.075
    body = (np.sin(ph) * np.exp(-t / dec) + 0.32 * np.sin(1.58 * ph) * np.exp(-t / (dec * 0.4))
            + 0.16 * np.sin(2.15 * ph + 0.5) * np.exp(-t / (dec * 0.25)))
    mallet = sy.lowpass(rng.standard_normal(n), 1100) * np.exp(-t / 0.007) * (0.45 if bum else 0.6)
    s = body * (1.0 if bum else 0.85) + mallet
    return sy.fade(s, 0.0005, 0.02) * vel * 0.9


TRI_BASE = 1180.0
TRI_P = [(1.0, 0.35), (1.64, 0.6), (2.36, 0.85), (3.08, 1.0), (3.81, 0.9), (4.52, 0.55), (5.27, 0.2), (6.0, 0.06)]


def triangulo(open_, vel, ring, seed):
    """Triângulo: o toque aberto soa até a mão abafar no toque seguinte (ring s)."""
    rng = np.random.default_rng(seed)
    n = sy.nsamp((ring + 0.02) if open_ else 0.07)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, (m, a) in enumerate(TRI_P):
        dec = (1.2 / (1 + 0.35 * k)) if open_ else 0.012
        s += a * np.sin(2 * np.pi * TRI_BASE * m * t + rng.uniform(0, 6.28)) * np.exp(-t / dec)
    if open_:
        nr = min(n, sy.nsamp(ring))
        s[nr:] *= np.exp(-(t[nr:] - ring) / 0.006)
    m = sy.nsamp(0.003)
    s[:m] += sy.highpass(rng.standard_normal(m), 3000) * 0.25
    s = sy.lowpass(sy.highpass(s, 1000), 6800)
    return sy.fade(s, 0.0003, 0.004) * vel * 0.1


# ---------------------------------------------------------------------------
# Execução (performance) e mixagem por trilhas
# ---------------------------------------------------------------------------
class Stems:
    def __init__(self, names):
        self.b = {k: np.zeros((2, N_TOTAL)) for k in names}

    def add(self, name, x, t, gain=1.0, pan=0.0):
        if t < 0:
            t += LOOP                       # o que cai antes do 0 vai para o fim do loop
        i = int(round(t * SR))
        if i >= N_TOTAL:
            return
        m = min(len(x), N_TOTAL - i)
        ang = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        self.b[name][0, i:i + m] += x[:m] * np.cos(ang) * gain
        self.b[name][1, i:i + m] += x[:m] * np.sin(ang) * gain


def bellows(t16):
    """Dinâmica de fole: frases de 4 compassos crescem até o meio e relaxam."""
    return 1.0 + 0.06 * np.sin(np.pi * ((t16 % 32) / 32.0))


def play_reeds(st, stem, events, reg, vel, bright, pan, rng, legato=0.88, jitter=0.005, seed0=0, energy=None):
    for k, e in enumerate(events):
        t = t_of(e['t16']) + float(np.clip(rng.normal(0, jitter), -2 * jitter, 2 * jitter))
        d16 = e['d16']
        lg = legato if d16 >= 2 else min(legato, 0.78)
        dur = max(0.05, d16 * S16 * lg)
        v = vel * bellows(e['t16']) * (1 + rng.normal(0, 0.05))
        if e['acc']:
            v *= 1.12
        if e['t16'] % 8 in (0, 3):
            v *= 1.04                       # apoio do baião: 1 e "a" do 1
        if energy is not None:
            v *= energy(e['t16'])
        v = float(np.clip(v, 0.2, 1.15))
        sd = seed0 + 7919 * k
        if e['grace'] is not None:
            g = sanfona(e['grace'], 0.045, v * 0.8, reg, bright, sd + 1)
            st.add(stem, g, t - 0.034, 1.0, pan)
            t += 0.004
        x = sanfona(e['midi'], dur, v, reg, bright * (0.85 + 0.25 * v), sd)
        st.add(stem, x, t, 1.0, pan)


def play_pife(st, events, vel, pan, rng, legato=0.9, seed0=0):
    for k, e in enumerate(events):
        t = t_of(e['t16']) + float(np.clip(rng.normal(0, 0.006), -0.012, 0.012))
        d16 = e['d16']
        lg = legato if d16 >= 2 else 0.8
        dur = max(0.05, d16 * S16 * lg)
        v = vel * (1 + rng.normal(0, 0.05)) * (1.1 if e['acc'] else 1.0)
        sd = seed0 + 104729 * k
        if e['grace'] is not None:
            st.add('pife', pife(e['grace'], 0.04, v * 0.8, sd + 1), t - 0.032, 1.0, pan)
            t += 0.004
        st.add('pife', pife(e['midi'], dur, v, sd), t, 1.0, pan)


# --- padrões rítmicos (posições em semicolcheias dentro do compasso de 2/4) ---
ZAB_MAIN = [(0, 'bum', 1.0), (2, 'bac', 0.35), (3, 'bum', 0.85), (4, 'abafa', 0.6), (6, 'bac', 0.8)]
ZAB_CHORUS = ZAB_MAIN + [(5, 'bac', 0.28), (7, 'bac', 0.42)]
ZAB_LIGHT = [(0, 'bum', 0.72), (3, 'bum', 0.55), (6, 'bac', 0.55)]
ZAB_FILL = [(0, 'bum', 1.0), (2, 'bac', 0.5), (3, 'bum', 0.85), (4, 'bac', 0.6), (5, 'bac', 0.5), (6, 'bum', 0.9), (7, 'bac', 0.75)]
ZAB_ROLL = [(p, 'bum' if p % 2 == 0 else 'bac', 0.55 + 0.06 * p) for p in range(8)]
ZAB_BRK1 = [(0, 'bum', 1.0), (3, 'bum', 1.0), (6, 'bum', 1.05)]
ZAB_BRK2 = [(6, 'bac', 0.35), (7, 'bac', 0.5)]

TRI_FULL = [(0, 'c', 0.85), (1, 'c', 0.4), (2, 'o', 0.75), (3, 'c', 0.5), (4, 'c', 0.75), (5, 'c', 0.4), (6, 'o', 0.8), (7, 'c', 0.5)]
TRI_LIGHT = [(0, 'c', 0.7), (2, 'o', 0.6), (4, 'c', 0.6), (5, 'c', 0.3), (6, 'o', 0.65)]
TRI_BRK1 = [(0, 'c', 0.9), (3, 'c', 0.9), (6, 'o', 0.9)]

# barras (globais) com virada da zabumba
FILL_BARS = set()
for _nm, _rel in (('intro', [7]), ('A', [7, 15]), ('B', [15]), ('riff', [7]), ('A2', [15]),
                  ('C2', [7]), ('S', [7, 15]), ('A3', [7, 15]), ('B2', [15])):
    for _r in _rel:
        FILL_BARS.add(SEC[_nm][0] + _r)


def sec_bar(name, rel):
    return SEC[name][0] + rel


def render():
    st = Stems(['lead', 'sec', 'comp', 'pife', 'bass', 'zab', 'bac', 'tri'])
    rng = np.random.default_rng(2024)

    def ev(s, name, rel=0):
        return parse(s, SEC[name][0] + rel)

    # ---------------- sanfona solista (lead) e segunda sanfona (sec) ----------------
    P_LEAD, P_SEC = 0.12, -0.30
    play_reeds(st, 'lead', ev(RIFF, 'intro'), REG_LEAD, 0.82, 0.55, P_LEAD, rng, legato=0.85, seed0=100)
    play_reeds(st, 'lead', ev(HEAD, 'A'), REG_LEAD, 0.80, 0.52, P_LEAD, rng, legato=0.9, seed0=200)
    play_reeds(st, 'sec', ev(FILL_A, 'A'), REG_SEC, 0.72, 0.45, P_SEC, rng, legato=0.85, seed0=300)
    ch = ev(CHORUS, 'B')
    play_reeds(st, 'lead', ch, REG_LEAD, 0.84, 0.58, P_LEAD, rng, legato=0.95, seed0=400)
    play_reeds(st, 'sec', thirds(ch), REG_SEC, 0.74, 0.5, P_SEC, rng, legato=0.95, seed0=500)
    rf = ev(RIFF2, 'riff')
    play_reeds(st, 'lead', rf, REG_LEAD, 0.84, 0.58, P_LEAD, rng, legato=0.85, seed0=600)
    play_reeds(st, 'sec', shift(rf, -12), REG_SEC, 0.8, 0.5, P_SEC, rng, legato=0.85, seed0=700)
    play_reeds(st, 'lead', ev(A2_SANF, 'A2'), REG_LEAD, 0.8, 0.52, P_LEAD, rng, legato=0.9, seed0=800)
    # C: sanfona responde e depois canta em terças sob o pífano
    play_reeds(st, 'lead', ev(C_SANF, 'C'), REG_LEAD, 0.74, 0.45, P_LEAD, rng, legato=0.9, seed0=900)
    cp = ev(C_PIFE, 'C')
    cp_late = [e for e in cp if e['t16'] >= sec_bar('C', 10) * 8 and e['t16'] < sec_bar('C', 15) * 8]
    play_reeds(st, 'lead', thirds(cp_late), REG_LEAD, 0.66, 0.42, P_LEAD, rng, legato=0.95, seed0=1000)
    c2 = ev(C2_PIFE, 'C2')
    play_reeds(st, 'lead', thirds(c2), REG_LEAD, 0.76, 0.5, P_LEAD, rng, legato=0.93, seed0=1100)
    play_reeds(st, 'lead', ev(SOLO, 'S'), REG_LEAD, 0.8, 0.55, P_LEAD, rng, legato=0.85, seed0=1200)
    bu = ev(BUILD, 'build')
    b0 = SEC['build'][0] * 8

    def grow(t16):
        return 0.9 + 0.12 * (t16 - b0) / 48.0
    play_reeds(st, 'lead', bu, REG_LEAD, 0.8, 0.55, P_LEAD, rng, legato=0.88, seed0=1300, energy=grow)
    play_reeds(st, 'sec', thirds(bu), REG_SEC, 0.74, 0.5, P_SEC, rng, legato=0.88, seed0=1400, energy=grow)
    play_reeds(st, 'lead', ev(BRK_LEAD, 'brk'), REG_LEAD, 0.9, 0.6, P_LEAD, rng, legato=0.7, jitter=0.002, seed0=1500)
    play_reeds(st, 'sec', ev(BRK_SEC, 'brk'), REG_SEC, 0.85, 0.55, P_SEC, rng, legato=0.7, jitter=0.002, seed0=1600)
    h3 = ev(HEAD_ORN, 'A3')
    play_reeds(st, 'lead', h3, REG_LEAD, 0.84, 0.56, P_LEAD, rng, legato=0.9, seed0=1700)
    play_reeds(st, 'sec', thirds(h3), REG_SEC, 0.74, 0.5, P_SEC, rng, legato=0.9, seed0=1800)
    ch2 = ev(CHORUS, 'B2')
    play_reeds(st, 'lead', ch2, REG_LEAD, 0.87, 0.6, P_LEAD, rng, legato=0.95, seed0=1900)
    play_reeds(st, 'sec', thirds(ch2), REG_SEC, 0.77, 0.52, P_SEC, rng, legato=0.95, seed0=2000)

    # ---------------- pífano ----------------
    P_PIFE = 0.34
    play_pife(st, ev(A2_PIFE, 'A2'), 0.78, P_PIFE, rng, seed0=10)
    play_pife(st, cp, 0.8, P_PIFE, rng, seed0=20)
    play_pife(st, c2, 0.84, P_PIFE, rng, seed0=30)
    play_pife(st, ev(SOLO_PIFE, 'S'), 0.7, P_PIFE, rng, seed0=40)
    play_pife(st, [e for e in bu if e['t16'] >= (b0 + 32)], 0.62, P_PIFE, rng, seed0=50)
    play_pife(st, ev(BRK_PIFE, 'brk'), 0.75, P_PIFE, rng, legato=0.7, seed0=60)
    play_pife(st, ev(FILL_A3_PIFE, 'A3'), 0.76, P_PIFE, rng, seed0=70)
    play_pife(st, ch2, 0.5, P_PIFE, rng, legato=0.93, seed0=80)        # uníssono no refrão final

    # ---------------- acordes da sanfona (mão esquerda) ----------------
    prev = None
    P_COMP = -0.42
    for bar in range(NBARS):
        name = SECTION_OF_BAR[bar]
        energy = SEC[name][2]
        rel = bar - SEC[name][0]
        chs = HARM[bar]
        if name == 'brk':
            hits = [(0, 1, 0.95), (3, 1, 0.95), (6, 2, 1.0)] if rel == 0 else []
        elif name == 'C':
            hits = [('sus', None, 0.42)]
        elif name in ('B', 'B2', 'S', 'build'):
            hits = [(2, 1, 0.68), (6, 1, 0.74)] + ([(7, 1, 0.42)] if bar % 2 == 1 else [(3, 1, 0.38)])
        else:
            hits = [(2, 1, 0.62), (6, 1, 0.7)]
        for h in hits:
            if h[0] == 'sus':
                for ci, sym in enumerate(chs):
                    v = voicing(sym, prev)
                    prev = v
                    seg = 8 // len(chs)
                    t0 = t_of(bar * 8 + ci * seg)
                    for j, nt in enumerate(v):
                        x = sanfona(nt, seg * S16 * 0.97, h[2] * (1 + rng.normal(0, 0.04)), REG_COMP, 0.28,
                                    seed=bar * 31 + ci * 7 + j, att=0.07, rel=0.06)
                        st.add('comp', x, t0 + 0.004 * j, 1.0, P_COMP)
                continue
            pos, d, vv = h
            sym = chord_at(bar * 8 + pos)
            v = voicing(sym, prev)
            prev = v
            t0 = t_of(bar * 8 + pos) + float(np.clip(rng.normal(0, 0.004), -0.008, 0.008))
            dur = 0.105 if d == 1 else 0.2
            vel = vv * energy * (1 + rng.normal(0, 0.05))
            for j, nt in enumerate(v):
                x = sanfona(nt, dur, vel, REG_COMP, 0.32 + 0.2 * energy, seed=bar * 131 + pos * 17 + j,
                            att=0.008, rel=0.03)
                st.add('comp', x, t0 + 0.003 * j, 1.0, P_COMP)

    # ---------------- baixo (dobra a zabumba) ----------------
    def broot(sym):
        _, b, _, _ = parse_chord(sym)
        r = 36 + b
        while r < 38:
            r += 12
        while r > 49:
            r -= 12
        return r

    def fifth(r):
        return r + 7 if r + 7 <= 52 else r - 5

    for bar in range(NBARS):
        name = SECTION_OF_BAR[bar]
        energy = SEC[name][2]
        rel = bar - SEC[name][0]
        chs = HARM[bar]
        nxt = HARM[(bar + 1) % NBARS][0]
        notes = []                             # (pos, dur16, nota, vel)
        if name == 'brk':
            if rel == 0:
                r = broot('D7')
                notes = [(0, 1, r, 1.0), (3, 1, r, 1.0), (6, 2, r, 1.05)]
        elif len(chs) == 2:
            r1, r2 = broot(chs[0]), broot(chs[1])
            notes = [(0, 3, r1, 1.0), (3, 1, fifth(r1), 0.8), (4, 3, r2, 0.95), (7, 1, fifth(r2), 0.7)]
        else:
            r = broot(chs[0])
            rn = broot(nxt)
            if name == 'C':
                notes = [(0, 3, r, 0.85), (3, 4, fifth(r), 0.7)]
            else:
                notes = [(0, 3, r, 1.0), (3, 4, fifth(r), 0.85)]
                walk = name in ('B', 'B2', 'S', 'build') or rel % 4 == 3
                if walk and rn != r:
                    app = rn - 1 if rn - 1 >= 37 else rn + 1
                    notes = [(0, 3, r, 1.0), (3, 3, fifth(r), 0.85), (6, 1, fifth(r) if abs(fifth(r) - app) > 2 else r, 0.6), (7, 1, app, 0.75)]
        for k, (pos, d, nt, v) in enumerate(notes):
            t0 = t_of(bar * 8 + pos) + float(np.clip(rng.normal(0, 0.003), -0.006, 0.006))
            x = baixo(nt, d * S16 * 0.92, v * (0.88 + 0.12 * energy) * (1 + rng.normal(0, 0.04)), seed=bar * 13 + k)
            st.add('bass', x, t0, 1.0, 0.0)

    # ---------------- zabumba ----------------
    for bar in range(NBARS):
        name = SECTION_OF_BAR[bar]
        energy = SEC[name][2]
        rel = bar - SEC[name][0]
        if name == 'brk':
            pat = ZAB_BRK1 if rel == 0 else ZAB_BRK2
        elif name == 'build' and rel == 5:
            pat = ZAB_ROLL
        elif bar in FILL_BARS:
            pat = ZAB_FILL
        elif name == 'C':
            pat = ZAB_LIGHT + ([(2, 'bac', 0.25)] if rel % 2 == 1 else [])
        elif name in ('B', 'B2', 'S') or (name == 'build' and rel >= 3):
            pat = ZAB_CHORUS
        else:
            pat = ZAB_MAIN + ([(7, 'bac', 0.3)] if bar % 2 == 1 else [])
        for k, (pos, kind, v) in enumerate(pat):
            t0 = t_of(bar * 8 + pos) + float(np.clip(rng.normal(0, 0.0025), -0.005, 0.005))
            if pos == 3 and kind == 'bum':
                t0 += 0.004                   # o "arrastado" do segundo bum
            vel = v * (0.82 + 0.18 * energy) * (1 + rng.normal(0, 0.06))
            x = zabumba(kind, vel, seed=bar * 17 + k)
            if kind == 'bac':
                st.add('bac', x, t0, 1.0, 0.12)
            else:
                st.add('zab', x, t0, 1.0, -0.04)

    # ---------------- triângulo ----------------
    strokes = []
    for bar in range(NBARS):
        name = SECTION_OF_BAR[bar]
        energy = SEC[name][2]
        rel = bar - SEC[name][0]
        if name == 'brk':
            pat = TRI_BRK1 if rel == 0 else []
        elif name == 'C':
            pat = TRI_LIGHT
        else:
            pat = TRI_FULL
        for pos, kind, v in pat:
            vel = v * (0.75 + 0.25 * energy) * (1 + rng.normal(0, 0.08))
            if name in ('B', 'B2') and pos in (2, 6):
                vel *= 1.08
            strokes.append((t_of(bar * 8 + pos) + float(np.clip(rng.normal(0, 0.002), -0.004, 0.004)), kind, vel))
    strokes.sort()
    for k, (t0, kind, vel) in enumerate(strokes):
        t_next = strokes[(k + 1) % len(strokes)][0]
        if t_next <= t0:
            t_next += LOOP
        ring = min(0.45, t_next - t0)
        x = triangulo(kind == 'o', vel, ring, seed=k)
        st.add('tri', x, t0, 1.0, 0.45)
    return st


# alvo de RMS (dBFS, medido só onde a trilha toca) e envio de reverb por trilha
TARGET = {'lead': -16.5, 'sec': -20.5, 'comp': -23.5, 'pife': -18.5, 'bass': -19.5, 'zab': -18.5, 'bac': -27.5,
          'tri': -32.0}
SEND = {'lead': 0.22, 'sec': 0.25, 'comp': 0.18, 'pife': 0.30, 'bass': 0.0, 'zab': 0.07, 'bac': 0.12, 'tri': 0.16}


def gated_rms_db(x):
    w = sy.nsamp(0.5)
    m = np.mean(x ** 2, axis=0)
    k = len(m) // w
    blocks = m[:k * w].reshape(k, w).mean(1)
    if blocks.max() <= 0:
        return -120.0
    keep = blocks > blocks.max() * 10 ** (-30 / 10)
    return 10 * np.log10(np.mean(blocks[keep]) + 1e-20)


def mixdown(st, report=True):
    dry = np.zeros((2, N_TOTAL))
    send = np.zeros((2, N_TOTAL))
    for name in ('lead', 'sec', 'comp', 'pife', 'bass', 'zab', 'bac', 'tri'):
        x = st.b[name]
        if name in ('lead', 'sec'):
            x = sy.highpass(x, 140)
            x = sy.peak_eq(x, 2900, -1.5, 1.0)
            x = sy.lowpass(x, 7000, order=1)
        elif name == 'comp':
            x = sy.highpass(x, 150)
            x = sy.lowpass(x, 3600)
            x = sy.stereo_widen(x, 0.0)
        elif name == 'pife':
            x = sy.highpass(x, 320)
            x = sy.lowpass(x, 6500)
        elif name == 'bass':
            x = sy.highpass(x, 36)
        elif name == 'zab':
            x = sy.highpass(x, 32)
            x = sy.peak_eq(x, 300, -2.0, 1.0)
        elif name == 'bac':
            x = sy.highpass(x, 120)
        elif name == 'tri':
            x = sy.lowpass(x, 7500)
        g = 10 ** ((TARGET[name] - gated_rms_db(x)) / 20)
        x = x * g
        if report:
            print('  trilha %-5s ganho %+6.1f dB' % (name, 20 * np.log10(g)))
        dry += x
        send += x * SEND[name]
        st.b[name] = None
    ir = sy.make_ir(t60=1.35, predelay=0.018, bright=0.38, seed=23)
    send = sy.highpass(send, 220)
    wet = np.zeros_like(send)
    for ch in range(2):
        wet[ch] = signal.oaconvolve(send[ch], ir[ch])[:N_TOTAL]
    mix = dry + wet * 0.5
    mix = sy.highpass(mix, 30)
    mix = sy.peak_eq(mix, 320, -1.0, 0.9)
    mix = sy.peak_eq(mix, 7500, -2.0, 0.7)
    return mix


def limiter_sem_rampa(x, ceiling_db=-1.0, lookahead=0.004, release=0.08):
    """Mesmo algoritmo do sy.limiter, mas o filtro de recuperação começa em regime
    (zi = need[0]); o original começa em zero e atenua o início do arquivo."""
    ceil = 10 ** (ceiling_db / 20)
    peak = np.max(np.abs(x), axis=0)
    la = sy.nsamp(lookahead)
    peak = maximum_filter1d(peak, size=2 * la + 1)
    need = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    a_r = np.exp(-1 / (release * SR))
    sm, _ = signal.lfilter([1 - a_r], [1, -a_r], need, zi=[need[0] * a_r])
    g = np.minimum(need, sm)
    return np.clip(x * g, -ceil, ceil)


def cyclic(fn, y, pad_s=3.0, **kw):
    P = sy.nsamp(pad_s)
    ext = np.concatenate([y[:, -P:], y, y[:, :P]], axis=1)
    ext = fn(ext, **kw)
    return ext[:, P:-P]


def main():
    t0 = time.time()
    print('Dia de Feira: %d compassos de 2/4, %.2f s, %d BPM' % (NBARS, LOOP, BPM))
    st = render()
    print('  render %.1f s' % (time.time() - t0))
    mix = mixdown(st)
    y = sy.seamless_loop(mix, LOOP)
    del mix
    rms = np.sqrt(np.mean(y ** 2))
    y *= 10 ** (-20 / 20) / rms
    y = cyclic(sy.compress, y, thresh_db=-20, ratio=2.0, attack=0.015, release=0.2)
    sy.limiter = limiter_sem_rampa          # só neste processo; synth.py não é alterado
    res = sy.master_and_export(y, OUT, target_lufs=TARGET_LUFS, ceiling_db=-1.2, quality=QUALITY,
                               loop=True, title='Dia de Feira')
    print(res)
    print('  total %.1f s' % (time.time() - t0))
    return res


if __name__ == '__main__':
    main()

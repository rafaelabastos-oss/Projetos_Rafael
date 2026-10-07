#!/usr/bin/env python3
"""Mundo Renda - ambiências (sem música), 100% sintetizadas por código (nenhum sample).

Gera quatro loops em android/assets/www/audio/:

  amb_mar.ogg    64 s, -24 LUFS  Mar em volta da ilha. Ondas em intervalos irregulares: na praia
                                 (esquerda/centro) a quebra corre de um lado para o outro e a espuma
                                 recua puxando seixos; no costão (direita) o golpe é grave, com borrifo
                                 e gotas caindo nas pedras. Marulho constante largo por baixo e
                                 gaivotas distantes (três aparições, uma com resposta).
  amb_dia.ogg    64 s, -24 LUFS  Campo de dia. Bem-te-vi (perto, à esquerda, e outro longe respondendo),
                                 sabiá-laranjeira (frases variadas em dois "turnos" e um vizinho
                                 distante), tico-tico (longe à direita e outro mais perto), rolinha
                                 fogo-apagou (perto, quase ao centro), piados curtos esparsos; vento nas
                                 folhas com rajadas que atravessam o estéreo (três árvores), um galo bem
                                 longe (uma vez, com eco no morro), duas abelhas passando e zumbido de
                                 insetos baixinho.
  amb_noite.ogg  64 s, -25 LUFS  Noite. Três grilos perto/meio (alturas, ritmos e lados diferentes),
                                 grilo-de-árvore contínuo e coro distante; sapos-ferreiro ("tóinc"),
                                 pererecas ("crec-crec"), rã "uóp" e sapo-cururu em pergunta-e-resposta
                                 na lagoa; murucututu (coruja) duas vezes; brisa morna.
  amb_chuva.ogg  48 s, -23 LUFS  Chuva média constante em folhas, telhado e chão (EQ inclinado para o
                                 escuro), goteira da calha caindo na poça, pingos na madeira, pingos
                                 grossos esparsos e um trovão distante rolando no meio (~20 s).

Como o loop fecha sem emenda:
  - o "leito" contínuo (marulho, vento, chiado da chuva) é renderizado com pré-rolagem e sobra e
    fechado com sy.crossfade_loop (cruzamento de potência constante de 4 s);
  - os eventos (ondas, pássaros, sapos, coruja, trovão, goteiras) vão para um barramento com cauda;
    o reverb é calculado sobre ele inteiro e tudo que passa do fim é dobrado sobre o início com
    sy.seamless_loop. Eventos de fala (pássaros, sapos, coruja, gaivotas, trovão) terminam antes do
    fim; ondas e goteiras usam intervalos distribuídos num círculo de período exato do loop;
  - grilos são trens de pulsos com número inteiro de cantos por volta (período exato do loop);
  - EQ final é cíclica e o limitador do master é trocado (só neste processo) por uma versão que
    começa em repouso: o original sobe do zero em ~0,3 s e criaria um degrau na emenda.

Uso (a partir de jogo-mundo-renda/):  python3 tools/audio/ambiencias.py [mar] [dia] [noite] [chuva]
Sem argumentos gera as quatro. Determinístico (sementes fixas).
"""
import os
import sys
import time

import numpy as np
from scipy import signal
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth as sy  # noqa: E402

SR = sy.SR
nsamp, tarr = sy.nsamp, sy.tarr
OUT_DIR = os.path.normpath(os.path.join(HERE, '..', '..', 'android', 'assets', 'www', 'audio'))
QUALITY = 3


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def idx(t):
    """Índice de amostra (ao contrário de sy.nsamp, idx(0) == 0)."""
    return int(round(t * SR))


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-12)


def set_rms(x, target_db):
    return x * 10 ** ((target_db - rms_db(x)) / 20)


def peak_rms_db(x, w_s=0.05):
    e = np.square(x) if x.ndim == 1 else np.mean(np.square(x), axis=0)
    w = max(1, min(len(e), nsamp(w_s)))
    c = np.concatenate([[0.0], np.cumsum(e)])
    return 10 * np.log10(np.max((c[w:] - c[:-w]) / w) + 1e-20)


def set_peak(x, target_db):
    """Escala para que o maior RMS de 50 ms seja target_db (dBFS)."""
    return x * 10 ** ((target_db - peak_rms_db(x)) / 20)


def pan_gains(p):
    ang = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return np.cos(ang), np.sin(ang)


def smooth_noise(n, fc, rng):
    """Ruído suave (passa-baixas em fc) com desvio-padrão 1."""
    pre = nsamp(min(1.0, 2.0 / fc))
    x = sy.lowpass(rng.standard_normal(n + pre), fc, order=2)[pre:]
    return x / (np.std(x) + 1e-12)


def slow_curve(n, step_s, rng, lo, hi):
    """Curva lenta aleatória (PCHIP por pontos a cada ~step_s s, com jitter)."""
    dur = n / SR
    k = int(np.ceil(dur / step_s)) + 3
    xs = (np.arange(k) - 1.0) * step_s + rng.uniform(-0.3, 0.3, k) * step_s
    ys = rng.uniform(lo, hi, k)
    return PchipInterpolator(xs, ys)(tarr(n))


def pink_st(n, rng, corr=0.3):
    """Ruído rosa estéreo com correlação parcial entre os canais (largura natural)."""
    c, a, b = sy.pink(n, rng), sy.pink(n, rng), sy.pink(n, rng)
    g1, g2 = np.sqrt(corr), np.sqrt(1 - corr)
    return np.vstack([g1 * c + g2 * a, g1 * c + g2 * b])


def pinkf(n, rng, lo=None, hi=None, order=2):
    """Ruído rosa mono filtrado, com pré-rolagem para os filtros assentarem."""
    pre = 4410
    x = sy.pink(n + pre, rng)
    if lo and hi:
        x = sy.bandpass(x, lo, hi, order)
    elif hi:
        x = sy.lowpass(x, hi, order)
    elif lo:
        x = sy.highpass(x, lo, order)
    return x[pre:]


def shelf(x, f0, gain_db, high=True, S=0.7):
    """Prateleira RBJ (high=True: agudos; False: graves)."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    al = sw / 2 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    sa = 2 * np.sqrt(A) * al
    if high:
        b = [A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa)]
        a = [(A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa]
    else:
        b = [A * ((A + 1) - (A - 1) * cw + sa), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sa)]
        a = [(A + 1) + (A - 1) * cw + sa, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sa]
    b, a = np.array(b) / a[0], np.array(a) / a[0]
    return signal.lfilter(b, a, x, axis=-1)


def cyclic(fn, y, pad_s=2.0):
    """Aplica fn tratando o sinal como cíclico (o estado dos filtros atravessa a emenda)."""
    P = idx(pad_s)
    ext = np.concatenate([y[:, -P:], y, y[:, :P]], axis=1)
    return fn(ext)[:, P:-P]


def reverb_wet(x, t60=1.6, predelay=0.02, bright=0.4, seed=7, hp=150):
    """Só o sinal molhado do reverb de convolução de synth.py (IR sintética)."""
    ir = sy.make_ir(t60, predelay, bright, seed)
    src = sy.highpass(x, hp)
    out = np.zeros_like(x)
    for ch in range(2):
        out[ch] = signal.oaconvolve(src[ch], ir[ch])[:x.shape[1]]
    return out


def win(n, a, r, shape=1.0):
    """Janela com subida e descida em cosseno (a, r em segundos)."""
    e = np.ones(n)
    na = min(n, max(1, int(a * SR)))
    nr = min(n - na, max(1, int(r * SR)))
    e[:na] = 0.5 - 0.5 * np.cos(np.pi * np.arange(na) / na)
    if nr > 0:
        e[n - nr:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(1, nr + 1) / nr)
    return e ** shape if shape != 1.0 else e


def contour(pts, n):
    """Curva de frequência por pontos (x 0..1, Hz), interpolada em escala log."""
    xs = np.array([p[0] for p in pts], float)
    ys = np.log(np.array([p[1] for p in pts], float))
    return np.exp(np.interp(np.linspace(0, 1, n), xs, ys))


def tone(f, harm=(1.0,), phase0=0.0):
    """Oscilador aditivo sobre uma curva de frequência instantânea."""
    ph = 2 * np.pi * np.cumsum(f) / SR + phase0
    out = np.zeros(len(f))
    fmax = float(np.max(f))
    for k, a in enumerate(harm, 1):
        if a and fmax * k < 0.45 * SR:
            out += a * np.sin(k * ph)
    return out


def syl(dur, pts, harm=(1.0, 0.1), a=0.008, r=0.03, rough=0.0, rough_f=120.0, wob=0.0, rng=None, shape=1.0):
    """Sílaba de canto: contorno de altura + harmônicos + envelope; aspereza por AM opcional."""
    n = nsamp(dur)
    f = contour(pts, n)
    if wob and rng is not None:
        f = f * (1 + wob * smooth_noise(n, 35, rng))
    s = tone(f, harm, 0.0 if rng is None else rng.uniform(0, 6.28))
    if rough:
        s *= 1 - rough * (0.5 + 0.5 * np.sin(2 * np.pi * rough_f * tarr(n)))
    return s * win(n, a, r, shape)


def assemble(parts):
    """[(t, mono)] -> buffer mono."""
    end = max(t + len(x) / SR for t, x in parts)
    buf = np.zeros(idx(end) + 4)
    for t, x in parts:
        i = idx(t)
        buf[i:i + len(x)] += x
    return buf


def impulses(n, rate, rng, dens=None, amp_pow=1.6, signed=True):
    """Trem de impulsos de Poisson (rate por segundo); dens (0..1) rarefaz no tempo."""
    cnt = rng.poisson(rate * n / SR)
    pos = rng.integers(0, n, cnt)
    amp = rng.random(cnt) ** amp_pow
    if signed:
        amp *= rng.choice([-1.0, 1.0], cnt)
    if dens is not None:
        keep = rng.random(cnt) < dens[pos]
        pos, amp = pos[keep], amp[keep]
    imp = np.zeros(n)
    np.add.at(imp, pos, amp)
    return imp


def k_noise(dur, lo, hi, tau, rng):
    """Núcleo de grão: ruído em banda com decaimento exponencial (normalizado em pico)."""
    n = nsamp(dur)
    t = tarr(n)
    k = sy.bandpass(rng.standard_normal(n), lo, hi) * np.exp(-t / tau)
    return k / (np.max(np.abs(k)) + 1e-12)


def k_res(f, tau, noise=0.0, rng=None, lo=500, hi=4000):
    """Núcleo ressonante (madeira, folha, telha): seno amortecido + um pouco de ruído."""
    n = nsamp(tau * 7)
    t = tarr(n)
    k = np.sin(2 * np.pi * f * t) * np.exp(-t / tau) * np.clip(t / 0.0004, 0, 1)
    if noise and rng is not None:
        k += sy.bandpass(rng.standard_normal(n), lo, hi) * np.exp(-t / (tau * 0.3)) * noise
    return k / (np.max(np.abs(k)) + 1e-12)


def conv(imp, kern):
    return signal.oaconvolve(imp, kern)[:len(imp)]


def circle_times(L, n_events, lo, hi, rng, offset=0.0):
    """n_events instantes num círculo de período L, com intervalos irregulares entre lo e hi
    (reescalados para somar exatamente L: o intervalo que atravessa a emenda também é natural)."""
    gaps = rng.uniform(lo, hi, n_events)
    gaps *= L / gaps.sum()
    return (offset + np.concatenate([[0.0], np.cumsum(gaps)[:-1]])) % L, gaps


class Bus:
    """Barramento de eventos com cauda: seco + envio de reverb; render() dobra a cauda no início."""

    def __init__(self, loop_s, tail_s):
        self.L = loop_s
        self.n = idx(loop_s + tail_s)
        self.dry = np.zeros((2, self.n))
        self.send = np.zeros((2, self.n))

    def add(self, x, t, gain=1.0, pan=0.0, send=0.0):
        i = idx(t % self.L)
        if x.ndim == 1:
            gl, gr = pan_gains(pan)
            x = np.vstack([x * gl, x * gr])
        m = x.shape[1]
        if i + m > self.n:
            raise ValueError('cauda do barramento curta demais (%.2f s)' % ((i + m - self.n) / SR))
        self.dry[:, i:i + m] += x * gain
        if send:
            self.send[:, i:i + m] += x * send

    def render(self, t60=1.6, predelay=0.02, bright=0.4, seed=7, hp=150):
        y = self.dry + reverb_wet(self.send, t60, predelay, bright, seed, hp)
        return sy.seamless_loop(y, self.L)


def put(bus, x, t, level_db, pan, d, send_extra=0.0, norm=True):
    """Coloca um evento a uma distância d (0 perto .. 1 longe): passa-baixas da absorção do ar,
    ganho direto menor e mais envio de reverb. A fonte é normalizada para pico (RMS 50 ms) de
    -20 dBFS; level_db é relativo a isso."""
    if norm:
        x = set_peak(x, -20.0)
    pad = nsamp(0.03)
    x = np.concatenate([x, np.zeros(pad)])
    if isinstance(pan, np.ndarray):
        pan = np.concatenate([pan, np.full(pad, pan[-1])])
    x = sy.lowpass(x, 9500.0 * 0.2 ** d, order=2)
    g = 10 ** ((level_db - 12.0 * d) / 20)
    s = 10 ** (level_db / 20) * (0.12 + 0.45 * d + send_extra)
    bus.add(x, t, g, pan, s)


def bed_len(pre, L, X):
    return idx(pre) + idx(L) + idx(X) + 16


def close_bed(bed, pre, L, X):
    """Corta a pré-rolagem e fecha o leito contínuo com cruzamento (sy.crossfade_loop)."""
    return sy.crossfade_loop(bed[:, idx(pre):], L, X)


def finish(y, fname, target, title, hp=30, shelf_f=6500, shelf_db=-3.0):
    """EQ final cíclica (grave limpo, agudos macios), master e exportação."""
    y = cyclic(lambda z: shelf(sy.highpass(z, hp, order=2), shelf_f, shelf_db), y)
    path = os.path.join(OUT_DIR, fname)
    res = sy.master_and_export(y, path, target_lufs=target, ceiling_db=-1.2, quality=QUALITY, loop=True, title=title)
    return path, res


# ---------------------------------------------------------------------------
# MAR
# ---------------------------------------------------------------------------
def wave_event(rng, size, kind, pan0, sweep):
    """Uma onda (estéreo): corpo grave que cresce, quebra (que corre no estéreo), espuma subindo
    a areia e, na praia, o refluxo puxando seixos; no costão, golpe grave, borrifo e gotas."""
    dur = (7.5 + 3.0 * size) if kind == 'praia' else (7.0 + 2.5 * size)
    n = nsamp(dur)
    t = tarr(n)
    tb = 1.3 + 1.0 * size + rng.uniform(-0.25, 0.25)        # instante da quebra

    def ramp(t0, t1, p=1.0):
        return np.clip((t - t0) / (t1 - t0), 0, 1) ** p

    def decay(t0, tau):
        return np.exp(-np.maximum(0.0, t - t0) / tau)

    p_t = pan0 + sweep * (ramp(tb - 0.9, tb + 2.6) - 0.5)
    gl, gr = pan_gains(p_t)
    out = np.zeros((2, n))

    def add(a, b, env, gain, width, moving=True):
        if moving:
            out[0] += (a * gl + width * b) * env * gain
            out[1] += (a * gr - width * b) * env * gain
        else:
            out[0] += (a + width * b) * env * gain * 0.707
            out[1] += (a - width * b) * env * gain * 0.707

    # corpo: massa de água chegando
    body_env = ramp(0, tb, 2.0) * decay(tb, 1.3 + 0.7 * size)
    add(pinkf(n, rng, 40, 340), pinkf(n, rng, 40, 340), body_env, 0.9, 0.15, moving=False)
    if kind == 'praia':
        crash_env = ramp(tb - 0.5 - 0.4 * size, tb, 2.2) * decay(tb, 0.5 + 0.35 * size)
        add(pinkf(n, rng, 260, 3400), pinkf(n, rng, 260, 3400), crash_env, 1.0, 0.45)
        # espuma subindo: escurece com o tempo e "crepita" (bolhas)
        rush_env = ramp(tb - 0.15, tb + 0.6, 1.2) * decay(tb + 0.6, 1.5 + 1.0 * size)
        dark = np.clip((t - tb) / 3.0, 0, 1)
        crack = 0.55 + 0.45 * np.abs(smooth_noise(n, 28, rng))
        bright_a, bright_b = pinkf(n, rng, 700, 5200), pinkf(n, rng, 700, 5200)
        dark_a, dark_b = pinkf(n, rng, 450, 2300), pinkf(n, rng, 450, 2300)
        add(bright_a * (1 - dark) + dark_a * dark * 1.3, bright_b * (1 - dark) + dark_b * dark * 1.3,
            rush_env * crack, 0.6, 0.7)
        # refluxo: chiado fino + seixos rolando
        bt = tb + 2.7 + 0.9 * size
        back_env = np.exp(-((t - bt) / 0.85) ** 2) * (0.7 + 0.3 * size)
        add(pinkf(n, rng, 1500, 5000), pinkf(n, rng, 1500, 5000), back_env, 0.2, 0.8)
        kern = k_noise(0.006, 1800, 4800, 0.0011, rng)
        pa = conv(impulses(n, 1100, rng, back_env / back_env.max()), kern)
        pb = conv(impulses(n, 1100, rng, back_env / back_env.max()), kern)
        add(pa, pb, back_env, 0.13, 0.9)
    else:
        # costão: golpe seco
        crash_env = ramp(tb - 0.14, tb, 1.5) * decay(tb, 0.35 + 0.2 * size)
        add(pinkf(n, rng, 200, 3000), pinkf(n, rng, 200, 3000), crash_env, 1.0, 0.4)
        tt = np.maximum(0.0, t - tb)
        fb = 46 + 26 * np.exp(-tt / 0.06)
        boom = np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tt / 0.32) * (t >= tb) * ramp(tb, tb + 0.006)
        boom += pinkf(n, rng, None, 220) * np.exp(-tt / 0.08) * (t >= tb) * 2.0
        out[0] += boom * 0.55 * size
        out[1] += boom * 0.55 * size
        spray_env = ramp(tb - 0.03, tb + 0.05) * decay(tb + 0.05, 0.35)
        add(pinkf(n, rng, 900, 6000), pinkf(n, rng, 900, 6000), spray_env, 0.45, 0.8)
        # gotas do borrifo caindo nas pedras
        drop_env = ramp(tb + 0.15, tb + 0.5) * decay(tb + 0.5, 0.9)
        da, db_ = np.zeros(n), np.zeros(n)
        for fq in rng.uniform(1700, 4200, 6):          # gotas de tamanhos diferentes (sem altura fixa)
            kd = k_res(fq, rng.uniform(0.002, 0.004), 0.8, rng, 1200, 5000)
            da += conv(impulses(n, 45, rng, drop_env), kd)
            db_ += conv(impulses(n, 45, rng, drop_env), kd)
        add(da, db_, np.ones(n), 0.16, 0.9)
        # água escorrendo das pedras: bolhas
        rush_env = ramp(tb, tb + 0.8) * decay(tb + 0.8, 1.8)
        add(pinkf(n, rng, 500, 2600), pinkf(n, rng, 500, 2600), rush_env * (0.6 + 0.4 * np.abs(smooth_noise(n, 20, rng))), 0.35, 0.6)
        gc = tb + 2.6
        gul = np.exp(-((t - gc) / 1.2) ** 2)
        bub = np.zeros(n)
        for tb_ in np.sort(rng.uniform(gc - 1.6, gc + 1.8, 18)):
            i0 = idx(tb_)
            m = nsamp(rng.uniform(0.02, 0.04))
            if i0 < 0 or i0 + m >= n:
                continue
            tt2 = tarr(m)
            f0 = rng.uniform(450, 1100)
            fq = f0 * (1 + 0.6 * (1 - np.exp(-tt2 / 0.01)))
            bub[i0:i0 + m] += np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-tt2 / 0.01) * rng.uniform(0.3, 1.0) * gul[i0]
        add(bub, np.zeros(n), np.ones(n), 0.12, 0.0)
    return out * win(n, 0.05, 1.2)


def gull_note(rng, dur, pts, rough=0.3):
    n = nsamp(dur)
    t = tarr(n)
    f = contour(pts, n) * (1 + 0.01 * smooth_noise(n, 25, rng))
    s = tone(f, (0.45, 1.0, 0.85, 0.6, 0.4, 0.25, 0.14, 0.08), rng.uniform(0, 6))
    s *= 1 - rough * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(85, 115) * t))
    s = sy.peak_eq(s, 2400, 5.0, 1.0)
    s += sy.bandpass(rng.standard_normal(n), 1500, 4000) * 0.04 * np.std(s) / 0.3
    return s * win(n, 0.02, 0.07)


def gull_call(rng, kind, k=1.0):
    """Gaivota estilizada: 'kyow' (miado), 'long' (chamado longo: 'kyaa' + 'ka-ka-ka'), 'ha' (risada)."""
    parts = []
    if kind in ('kyow', 'kyow2'):
        parts.append((0.0, gull_note(rng, 0.5, [(0, 780 * k), (0.2, 1220 * k), (0.5, 1150 * k), (1, 720 * k)])))
        if kind == 'kyow2':
            k2 = k * 0.94
            parts.append((0.78, 0.85 * gull_note(rng, 0.46, [(0, 760 * k2), (0.22, 1180 * k2), (0.5, 1100 * k2), (1, 700 * k2)])))
    elif kind == 'long':
        parts.append((0.0, gull_note(rng, 0.38, [(0, 980 * k), (0.25, 1330 * k), (1, 1040 * k)], 0.35)))
        tt = 0.55
        for j in range(6):
            kk = k * (1.0 - 0.022 * j)
            parts.append((tt, (0.95 - 0.09 * j) * gull_note(rng, 0.15, [(0, 900 * kk), (0.3, 1160 * kk), (1, 980 * kk)], 0.4)))
            tt += 0.22 + rng.uniform(-0.015, 0.02)
    else:
        tt = 0.0
        for j in range(4):
            kk = k * (1.0 - 0.03 * j)
            parts.append((tt, (0.9 - 0.12 * j) * gull_note(rng, 0.14, [(0, 920 * kk), (0.35, 1120 * kk), (1, 950 * kk)], 0.45)))
            tt += 0.19 + rng.uniform(-0.01, 0.02)
    return assemble(parts)


def amb_mar():
    L, X, PRE = 64.0, 4.0, 1.0
    rng = np.random.default_rng(4101)
    n = bed_len(PRE, L, X)
    # leito: marulho grave + arrebentação distante + chiado de espuma bem baixo (largo)
    sw1 = slow_curve(n, 5.0, rng, 0.55, 1.0)
    sw2 = slow_curve(n, 3.3, rng, 0.35, 1.0)
    wash = sy.highpass(sy.lowpass(pink_st(n, rng, 0.35), 600), 40) * sw1
    surf = sy.bandpass(pink_st(n, rng, 0.2), 280, 2400) * sw2
    fizz = sy.bandpass(pink_st(n, rng, 0.0), 1800, 5200) * (0.3 + 0.7 * sw2 ** 2)
    bed = set_rms(wash, -31.0) + set_rms(surf, -35.0) + set_rms(fizz, -47.0)
    bed = close_bed(sy.stereo_widen(bed, 0.3), PRE, L, X)

    ev = Bus(L, 16.0)
    # ondas: 9 por volta em "séries" irregulares (intervalos de 4,9 a 9,8 s que somam 64 s; o
    # intervalo que atravessa a emenda é um deles)
    gaps = np.array([6.1, 8.4, 5.3, 9.8, 7.2, 4.9, 8.9, 6.6, 6.8])
    starts = 0.9 + np.concatenate([[0.0], np.cumsum(gaps)[:-1]])
    sizes = [0.62, 0.9, 1.0, 0.5, 0.42, 0.8, 0.95, 0.6, 0.48]
    kinds = ['praia', 'praia', 'rocha', 'praia', 'praia', 'rocha', 'praia', 'praia', 'rocha']
    for k, (t0, sz, kd) in enumerate(zip(starts, sizes, kinds)):
        wrng = np.random.default_rng(5000 + k)
        if kd == 'praia':
            pan0, sweep = wrng.uniform(-0.55, 0.15), wrng.choice([-1, 1]) * wrng.uniform(0.35, 0.6)
        else:
            pan0, sweep = wrng.uniform(0.45, 0.72), wrng.uniform(-0.15, 0.15)
        w = wave_event(wrng, sz, kd, pan0, sweep)
        w = set_peak(w, -17.0 + 11.0 * np.log10(sz))
        ev.add(w, t0, 1.0, 0.0, 0.12)
    # gaivotas distantes
    grng = np.random.default_rng(4202)
    for t0, kind, k, pan, d, lvl in ((7.6, 'kyow2', 1.0, -0.6, 0.78, -1.0),
                                     (27.4, 'long', 0.97, 0.35, 0.62, -2.0),
                                     (29.5, 'ha', 1.05, 0.78, 0.86, -2.5),
                                     (49.8, 'kyow', 1.03, -0.25, 0.8, -1.5),
                                     (51.0, 'ha', 1.0, -0.3, 0.82, -3.0)):
        put(ev, gull_call(grng, kind, k), t0, lvl, pan, d)
    y = bed + ev.render(t60=2.4, predelay=0.035, bright=0.35, seed=11)
    return finish(y, 'amb_mar.ogg', -24.0, 'Mar da Ilha (ambiência)', hp=40, shelf_f=6000, shelf_db=-3.0)


# ---------------------------------------------------------------------------
# DIA
# ---------------------------------------------------------------------------
def bemtevi(rng, k=1.0, var=0):
    """Bem-te-vi: 'bem' curto subindo, 'te' agudo, 'viii' longo descendo, com leve aspereza."""
    tm = rng.uniform(0.94, 1.06)
    kk = k * rng.uniform(0.985, 1.015)
    h = (1.0, 0.25, 0.05)
    p1 = syl(0.085 * tm, [(0, 2350 * kk), (0.6, 2950 * kk), (1, 2800 * kk)], h, 0.006, 0.025, 0.22, 150, 0.006, rng)
    p2 = syl(0.07 * tm, [(0, 2900 * kk), (1, 3150 * kk)], h, 0.005, 0.02, 0.22, 150, 0.006, rng)
    p3 = syl(0.30 * tm, [(0, 3450 * kk), (0.22, 3620 * kk), (1, 2350 * kk)], h, 0.01, 0.08, 0.3, 140, 0.006, rng)
    if var == 1:     # só "te-viii"
        return assemble([(0.0, p2 * 0.8), (0.13 * tm, p3)])
    return assemble([(0.0, p1 * 0.8), (0.15 * tm, p2 * 0.75), (0.29 * tm, p3)])


SABIA_PHRASES = [
    [('u', 1.0, 0.14, 0.05), ('w', 1.25, 0.18, 0.07), ('d', 1.1, 0.16, 0.04), ('c', 1.4, 0.05, 0.03), ('a', 0.95, 0.22, 0)],
    [('w', 1.1, 0.12, 0.04), ('w', 1.1, 0.12, 0.06), ('u', 0.9, 0.15, 0.05), ('t', 1.35, 0.28, 0.05), ('d', 1.0, 0.2, 0)],
    [('a', 1.2, 0.2, 0.08), ('d', 0.95, 0.14, 0.05), ('u', 1.05, 0.17, 0.04), ('w', 1.3, 0.1, 0.03), ('w', 1.18, 0.12, 0)],
    [('c', 1.5, 0.05, 0.03), ('c', 1.45, 0.05, 0.06), ('a', 1.0, 0.24, 0.07), ('d', 1.2, 0.18, 0.05), ('u', 0.88, 0.2, 0)],
    [('u', 1.0, 0.12, 0.05), ('d', 1.3, 0.13, 0.05), ('u', 1.0, 0.12, 0.05), ('d', 1.3, 0.13, 0.08), ('w', 0.92, 0.26, 0)],
]


def sabia(rng, k=1.0, phrase=0):
    """Sabiá-laranjeira: frase assobiada (flauta), com glissandos, chips e às vezes um trinado."""
    base = 2150.0 * k
    parts, tt = [], 0.0
    h = (1.0, 0.08, 0.02)
    for typ, ratio, dur, gap in SABIA_PHRASES[phrase]:
        f = base * ratio * rng.uniform(0.98, 1.02)
        dur *= rng.uniform(0.93, 1.07)
        vel = rng.uniform(0.75, 1.0)
        if typ == 't':
            m = int(round(dur / 0.045))
            for j in range(m):
                parts.append((tt + j * 0.045, vel * 0.85 * syl(0.032, [(0, f * 1.1), (1, f * 0.92)], h, 0.004, 0.012)))
        else:
            pts = {'w': [(0, f), (1, f * 1.03)], 'u': [(0, f * 0.86), (1, f * 1.14)], 'd': [(0, f * 1.14), (1, f * 0.86)],
                   'a': [(0, f * 0.9), (0.5, f * 1.12), (1, f * 0.95)], 'c': [(0, f * 1.2), (1, f)]}[typ]
            parts.append((tt, vel * syl(dur, pts, h, 0.012 if typ != 'c' else 0.004, 0.03 if typ != 'c' else 0.012,
                                        wob=0.004, rng=rng)))
        tt += dur + gap * rng.uniform(0.85, 1.15)
    return assemble(parts)


def ticotico(rng, k=1.0, var=0):
    """Tico-tico: um ou dois assobios ligados e um trinado no fim ('tiii-tiuu-trrrr')."""
    h = (1.0, 0.06)
    kk = k * rng.uniform(0.985, 1.015)
    if var == 0:
        n1 = syl(0.2, [(0, 4300 * kk), (1, 3700 * kk)], h, 0.012, 0.03)
        n2 = syl(0.18, [(0, 3300 * kk), (1, 4150 * kk)], h, 0.012, 0.03)
        parts = [(0.0, n1), (0.27, n2 * 0.9)]
        t0, m, sp, fa, fb = 0.54, 10, 0.05, 4000, 3300
    else:
        n1 = syl(0.24, [(0, 3900 * kk), (1, 3950 * kk)], h, 0.015, 0.04)
        n2 = syl(0.2, [(0, 4500 * kk), (1, 3600 * kk)], h, 0.012, 0.03)
        parts = [(0.0, n1), (0.31, n2 * 0.95)]
        t0, m, sp, fa, fb = 0.6, 8, 0.062, 3500, 2900
    for j in range(m):
        parts.append((t0 + j * sp, (0.85 - 0.03 * j) * syl(0.032, [(0, fa * kk), (1, fb * kk)], h, 0.004, 0.012)))
    return assemble(parts)


def rolinha(rng, k=1.0, var=0):
    """Rolinha fogo-apagou: arrulho grave e macio em quatro sílabas ('fo-go-a-pa-gou' estilizado)."""
    h = (1.0, 0.12, 0.03)
    kk = k * rng.uniform(0.98, 1.02)
    notes = [(0.0, 0.17, [(0, 540), (0.5, 600), (1, 580)], 0.9), (0.25, 0.12, [(0, 525), (1, 500)], 0.7),
             (0.43, 0.13, [(0, 580), (1, 605)], 0.8), (0.63, 0.34, [(0, 620), (0.3, 645), (1, 520)], 1.0)]
    if var == 1:
        notes = notes[:1] + notes[2:]
    parts = []
    for t0, d, pts, a in notes:
        s = syl(d, [(x, f * kk) for x, f in pts], h, 0.03, 0.08, wob=0.003, rng=rng)
        s += sy.lowpass(rng.standard_normal(len(s)), 900) * win(len(s), 0.03, 0.08) * 0.05
        parts.append((t0, s * a))
    return assemble(parts)


def tsip(rng, k=1.0):
    """Piado curto de passarinho miúdo."""
    return syl(0.05, [(0, 5000 * k), (1, 4200 * k)], (1.0, 0.04), 0.004, 0.02)


def galo(rng):
    """Galo estilizado ('có-có-ri-cóóó'): fonte rica em harmônicos, formantes de vogal e aspereza;
    eco no morro para soar longe."""
    sylls = [(0.00, 0.13, [(0, 470), (1, 520)], 'o', 0.8),
             (0.20, 0.12, [(0, 500), (1, 560)], 'o', 0.85),
             (0.37, 0.15, [(0, 560), (1, 650)], 'i', 0.9),
             (0.57, 1.10, [(0, 630), (0.12, 720), (0.6, 700), (0.85, 610), (1, 430)], 'o', 1.0)]
    form = {'o': ((550, 1.0), (950, 0.6), (2500, 0.18)), 'i': ((400, 0.7), (2100, 0.6), (2900, 0.25))}
    parts = []
    for t0, d, pts, v, a in sylls:
        n = nsamp(d)
        f = contour(pts, n) * (1 + 0.02 * smooth_noise(n, 40, rng))
        src = tone(f, tuple(1.0 / hh ** 0.8 for hh in range(1, 16)))
        src *= 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(60, 80) * tarr(n)))
        s = sum(g * sy.bandpass(src, fc / 1.25, fc * 1.25) for fc, g in form[v])
        parts.append((t0, s * win(n, 0.02, 0.05 if d < 0.5 else 0.3) * a))
    dry = assemble(parts)
    echo = np.zeros(len(dry) + idx(0.45))
    echo[idx(0.45):] = sy.lowpass(dry, 1200) * 0.35
    echo[:len(dry)] += dry
    return echo


def abelha(rng, dur=3.6, direction=1):
    """Abelha passando: zumbido com Doppler, aproximação/afastamento e travessia no estéreo."""
    n = nsamp(dur)
    t = tarr(n)
    tc = dur * rng.uniform(0.42, 0.58)
    f0 = rng.uniform(200, 235)
    f = f0 * (1 + 0.03 * np.tanh((tc - t) / 0.35)) * (1 + 0.012 * smooth_noise(n, 6, rng))
    s = sy.lowpass(tone(f, tuple(1.0 / hh ** 1.15 for hh in range(1, 22))), 2600)
    prox = 1.0 / (0.35 + ((t - tc) / 0.7) ** 2)
    s *= prox / prox.max() * win(n, 0.3, 0.4)
    pan = direction * np.clip((t - tc) / (dur * 0.5), -1, 1) * 0.8
    return s, pan


def amb_dia():
    L, X, PRE = 64.0, 4.0, 1.0
    rng = np.random.default_rng(2202)
    n = bed_len(PRE, L, X)
    t = tarr(n)
    # vento: rajadas lentas que atravessam três árvores (esquerda -> centro -> direita)
    gust = slow_curve(n, 4.2, rng, 0.18, 1.0)
    gust = sy.lowpass(np.clip(gust, 0.12, 1.0), 1.5, order=1)
    body = sy.bandpass(pink_st(n, rng, 0.5), 110, 650) * (0.3 + 0.7 * gust)
    leaves = np.zeros((2, n))
    kern = k_noise(0.008, 1500, 4800, 0.0016, rng)
    for pan, lag, gain in ((-0.7, 0.0, 1.0), (0.05, 0.9, 0.8), (0.75, 1.8, 0.95)):
        g = np.roll(gust, idx(lag))
        sh = pinkf(n, rng, 1100, 4600) * g ** 2 * (0.5 + 0.8 * np.abs(smooth_noise(n, 14, rng)))
        gr = conv(impulses(n, 520, rng, np.clip(g, 0, 1) ** 2), kern) * 0.08
        mono = set_rms(sh, -40) + set_rms(gr, -44)
        gl, grr = pan_gains(pan)
        side = set_rms(pinkf(n, rng, 1100, 4600) * g ** 2, rms_db(mono) - 8.0)
        leaves[0] += (mono * gl + side) * gain
        leaves[1] += (mono * grr - side) * gain
    # insetos bem baixinho: moscas/abelhas ao longe (zumbidos que vagueiam) + chiado distante
    hum = np.zeros((2, n))
    for j in range(4):
        f0 = rng.uniform(175, 260)
        f = f0 * (1 + 0.035 * smooth_noise(n, 0.5, rng))
        b = tone(f, tuple(1.0 / hh ** 1.2 for hh in range(1, 9)), rng.uniform(0, 6))
        b = sy.lowpass(b, 1400) * slow_curve(n, 1.7, rng, -0.6, 1.0).clip(0, 1) ** 2
        gl, gr = pan_gains(rng.uniform(-0.8, 0.8))
        hum[0] += b * gl
        hum[1] += b * gr
    chor = sy.bandpass(pink_st(n, rng, 0.0), 3000, 4400) * (0.8 + 0.2 * np.sin(2 * np.pi * 23 * t)) * slow_curve(n, 6.0, rng, 0.4, 1.0)
    bed = (set_rms(body, -35.5) + set_rms(leaves, -36.5) + set_rms(hum, -52.0) + set_rms(chor, -57.0))
    bed = close_bed(bed, PRE, L, X)

    ev = Bus(L, 6.0)
    erng = np.random.default_rng(2303)
    birds = {   # indivíduo: (função, k (altura), pan, distância, nível dB)
        'btvA': (bemtevi, 1.0, -0.5, 0.28, 0.0), 'btvB': (bemtevi, 0.95, 0.72, 0.82, -1.0),
        'sabA': (sabia, 1.0, 0.38, 0.42, -2.0), 'sabB': (sabia, 0.93, -0.72, 0.82, -2.0),
        'ticA': (ticotico, 1.0, 0.78, 0.74, -2.0), 'ticB': (ticotico, 0.96, -0.2, 0.5, -3.0),
        'rolA': (rolinha, 1.0, -0.15, 0.15, -5.0),
    }
    timeline = [
        (1.3, 'rolA', 0), (2.6, 'rolA', 0), (4.0, 'rolA', 1),
        (5.7, 'btvA', 0), (6.9, 'btvA', 0),
        (9.3, 'ticA', 0),
        (12.8, 'sabA', 0), (15.6, 'sabA', 1), (18.9, 'sabA', 2), (21.7, 'sabA', 0), (25.0, 'sabA', 3),
        (29.4, 'ticA', 0),
        (34.2, 'btvA', 1), (35.9, 'btvB', 0),
        (38.6, 'rolA', 0), (40.0, 'rolA', 1),
        (42.4, 'sabB', 4),
        (44.6, 'ticB', 1),
        (48.2, 'sabA', 1), (51.4, 'sabA', 4),
        (55.6, 'btvA', 0),
        (58.4, 'ticA', 0),
        (61.6, 'rolA', 0),
    ]
    for t0, who, var in timeline:
        fn, k, pan, d, lvl = birds[who]
        x = fn(erng, k, var)
        put(ev, x, t0 + erng.uniform(-0.05, 0.05), lvl + erng.uniform(-1.0, 1.0), pan + erng.uniform(-0.05, 0.05), d)
    for t0, pan, d in ((11.6, 0.3, 0.7), (23.2, -0.6, 0.75), (46.0, 0.6, 0.65), (46.27, 0.6, 0.65), (60.6, -0.3, 0.8)):
        put(ev, tsip(erng, erng.uniform(0.95, 1.05)), t0, -6.0, pan, d)
    put(ev, galo(erng), 31.0, -9.5, -0.6, 0.92, send_extra=0.15)
    for t0, direction in ((19.6, 1), (52.6, -1)):
        s, pan = abelha(erng, 3.6, direction)
        put(ev, s, t0, -15.0, pan, 0.2)
    y = bed + ev.render(t60=1.4, predelay=0.025, bright=0.4, seed=21)
    return finish(y, 'amb_dia.ogg', -24.0, 'Dia no Campo (ambiência)', hp=40, shelf_f=6500, shelf_db=-2.5)


# ---------------------------------------------------------------------------
# NOITE
# ---------------------------------------------------------------------------
def cricket_kernel(f0, nsyl, syl_d=0.016, gap=0.011):
    """Canto de grilo: nsyl sílabas de seno puro com leve queda de altura."""
    parts = []
    for j in range(nsyl):
        n = nsamp(syl_d)
        tt = tarr(n)
        f = f0 * (1.015 - 0.035 * tt / syl_d)
        a = (0.75, 1.0, 0.95, 0.85, 0.8)[min(j, 4)]
        parts.append((j * (syl_d + gap), np.sin(2 * np.pi * np.cumsum(f) / SR) * win(n, 0.003, 0.007) * a))
    return assemble(parts)


def cricket_track(L, rng, f0, period, nsyl, rests=1):
    """Grilo com número inteiro de cantos por volta: periodicidade exata do loop. Pequeno jitter,
    dinâmica variável e uma ou duas pausas por volta."""
    N = int(round(L / period))
    per = L / N
    times = rng.uniform(0, per) + per * np.arange(N) + rng.normal(0, per * 0.03, N)
    amps = np.clip(1 + 0.12 * rng.standard_normal(N), 0.6, 1.3)
    amps *= 1 + 0.18 * np.sin(2 * np.pi * rng.integers(1, 4) * times / L + rng.uniform(0, 6))
    for _ in range(rests):
        a0 = rng.uniform(0, L)
        dur = rng.uniform(2.0, 5.5)
        d = (times - a0) % L
        amps[d < dur] = 0.0
        amps[(d >= dur) & (d < dur + per * 2.5)] *= 0.6        # volta devagar
    kern = cricket_kernel(f0, nsyl)
    imp = np.zeros(idx(L) + 1)
    np.add.at(imp, np.array([idx(x % L) for x in times]), amps)
    return conv(np.concatenate([imp, np.zeros(len(kern))]), kern)


def tree_cricket_track(L, rng, f0=2750.0, rate=46.0):
    """Grilo-de-árvore: trinado contínuo e macio, em trechos longos com respiros."""
    N = int(round(L * rate))
    per = L / N
    times = np.arange(N) * per + rng.normal(0, per * 0.02, N)
    env = np.ones(N)
    tcur = rng.uniform(0, 3)
    while tcur < L:
        on = rng.uniform(4.0, 9.0)
        off = rng.uniform(0.8, 2.6)
        d = (times - (tcur + on)) % L
        env[d < off] = 0.0
        tcur += on + off
    env = np.convolve(np.concatenate([env[-12:], env, env[:12]]), np.hanning(25) / np.hanning(25).sum(), 'same')[12:-12]
    n = nsamp(0.013)
    k = np.sin(2 * np.pi * f0 * tarr(n)) * win(n, 0.004, 0.007)
    imp = np.zeros(idx(L) + 1)
    np.add.at(imp, np.array([idx(x % L) for x in times]), env * (0.9 + 0.1 * rng.random(N)))
    return conv(np.concatenate([imp, np.zeros(len(k))]), k)


def ferreiro(rng, f0):
    """Sapo-ferreiro: 'tóinc' metálico (martelo na bigorna)."""
    n = nsamp(0.24)
    t = tarr(n)
    f = f0 * (1 + 0.07 * np.exp(-t / 0.008))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) * np.exp(-t / 0.055) + 0.32 * np.sin(2.01 * ph + 0.3) * np.exp(-t / 0.03)
         + 0.1 * np.sin(3.03 * ph) * np.exp(-t / 0.014))
    s *= np.clip(t / 0.0025, 0, 1)
    s += sy.bandpass(rng.standard_normal(n), 900, 3500) * np.exp(-t / 0.003) * 0.25
    return s


def ferreiro_series(rng, f0, count, spacing=0.66):
    parts, tt = [], 0.0
    for j in range(count):
        parts.append((tt, ferreiro(rng, f0 * rng.uniform(0.985, 1.015)) * rng.uniform(0.75, 1.0)))
        tt += spacing * rng.uniform(0.9, 1.12)
    return assemble(parts)


def perereca(rng, f0, count):
    """Perereca: notas pulsadas 'crec' em série."""
    parts, tt = [], 0.0
    for j in range(count):
        npl = int(rng.integers(9, 15))
        rate = rng.uniform(85, 110)
        dur = npl / rate
        n = nsamp(dur + 0.02)
        t = tarr(n)
        pul = np.abs(np.sin(np.pi * rate * t)) ** 4 * (t < dur)
        car = tone(f0 * (1 + 0.03 * t / dur), (1.0, 0.15))
        parts.append((tt, car * pul * win(n, 0.015, 0.03) * rng.uniform(0.75, 1.0)))
        tt += dur + rng.uniform(0.12, 0.2)
    return assemble(parts)


def cururu(rng, dur, f0=560.0, rate=15.0):
    """Sapo-cururu: trinado grave e longo."""
    n = nsamp(dur)
    t = tarr(n)
    rate *= rng.uniform(0.95, 1.05)
    pul = np.abs(np.sin(np.pi * rate * t)) ** 2.5
    f = f0 * (1 + 0.01 * smooth_noise(n, 5, rng))
    s = sy.bandpass(tone(f, (1.0, 0.55, 0.3, 0.12)), 250, 2200)
    return s * pul * win(n, 0.35, 0.25)


def uop(rng, k=1.0):
    """Rã 'uóp': assobio grave que sobe, com leve aspereza."""
    kk = k * rng.uniform(0.97, 1.03)
    return syl(0.12, [(0, 300 * kk), (0.6, 420 * kk), (1, 460 * kk)], (1.0, 0.6, 0.35, 0.15), 0.006, 0.05, 0.25, 70)


def murucututu(rng, f0=360.0, nhoots=8):
    """Coruja murucututu: série de pios graves e macios que acelera e desce ('pu-pu-pu-pupupu')."""
    parts, tt = [], 0.0
    for j in range(nhoots):
        x = j / (nhoots - 1)
        dur = 0.115 - 0.04 * x
        f = f0 * (1.06 - 0.12 * x)
        h = syl(dur, [(0, f * 0.96), (0.3, f * 1.02), (1, f * 0.9)], (1.0, 0.18, 0.05), 0.018, 0.05)
        h += sy.lowpass(rng.standard_normal(len(h)), 700) * win(len(h), 0.018, 0.05) * 0.05
        amp = (0.75 + 0.25 * np.sin(np.pi * x * 0.9)) * (1 - 0.35 * x ** 2)
        parts.append((tt, h * amp))
        tt += 0.31 - 0.15 * x
    return assemble(parts)


def amb_noite():
    L, X, PRE = 64.0, 4.0, 1.0
    rng = np.random.default_rng(3303)
    n = bed_len(PRE, L, X)
    # brisa morna + folhas quase paradas
    gust = sy.lowpass(slow_curve(n, 6.0, rng, 0.2, 1.0), 1.0, order=1)
    breeze = sy.bandpass(pink_st(n, rng, 0.45), 100, 700) * (0.35 + 0.65 * gust)
    leaves = sy.bandpass(pink_st(n, rng, 0.1), 900, 3200) * gust ** 2 * (0.6 + 0.6 * np.abs(smooth_noise(n, 10, rng)))
    bed = close_bed(set_rms(breeze, -38.0) + set_rms(leaves, -49.0), PRE, L, X)

    ev = Bus(L, 6.0)
    crng = np.random.default_rng(3404)
    # grilos perto/meio: (f0, período, sílabas, pan, distância, nível)
    for f0, per, ns, pan, d, lvl in ((4400, 0.42, 3, -0.55, 0.35, -6.0),
                                     (4750, 0.61, 4, 0.6, 0.45, -7.0),
                                     (4100, 0.36, 2, 0.18, 0.62, -9.0)):
        tr = cricket_track(L, crng, f0, per, ns, rests=int(crng.integers(1, 3)))
        put(ev, tr, 0.0, lvl, pan, d)
    tree = tree_cricket_track(L, crng)
    put(ev, tree, 0.0, -14.0, -0.82, 0.55)
    # coro distante: muitos grilos longe, bem filtrados e com reverb
    chorus = np.zeros((2, idx(L) + nsamp(0.3)))
    for j in range(10):
        tr = cricket_track(L, crng, crng.uniform(3900, 5100), crng.uniform(0.3, 0.75), int(crng.integers(2, 5)), rests=1)
        gl, gr = pan_gains(crng.uniform(-0.95, 0.95))
        m = min(len(tr), chorus.shape[1])
        chorus[0, :m] += tr[:m] * gl * crng.uniform(0.5, 1.0)
        chorus[1, :m] += tr[:m] * gr * crng.uniform(0.5, 1.0)
    chorus = set_rms(sy.lowpass(chorus, 4200), -20.0)
    ev.add(chorus, 0.0, 10 ** (-26 / 20), 0.0, 10 ** (-20 / 20))

    frng = np.random.default_rng(3505)
    fer = {'A': (1020.0, -0.5, 0.35), 'B': (930.0, 0.5, 0.5), 'C': (1100.0, 0.05, 0.8)}
    for t0, who, cnt in ((2.0, 'A', 3), (4.3, 'B', 2), (6.0, 'A', 2), (7.5, 'B', 3),
                         (22.0, 'C', 3), (24.1, 'B', 3), (26.2, 'A', 2), (27.6, 'B', 1), (28.5, 'A', 1),
                         (43.5, 'A', 2), (45.0, 'C', 2), (46.3, 'B', 3), (48.4, 'A', 3),
                         (58.5, 'B', 2), (60.2, 'A', 2)):
        f0, pan, d = fer[who]
        put(ev, ferreiro_series(frng, f0, cnt), t0, -2.0, pan, d)
    per = {'1': (3000.0, 0.72, 0.4), '2': (2650.0, 0.3, 0.75), '3': (2850.0, -0.8, 0.6)}
    for t0, who, cnt in ((10.0, '1', 3), (10.9, '2', 2), (11.6, '1', 2), (12.4, '2', 3),
                         (31.0, '3', 3), (31.9, '1', 2), (32.6, '3', 2), (33.4, '2', 3), (34.4, '1', 4),
                         (52.5, '2', 2), (53.2, '1', 3), (54.1, '3', 2)):
        f0, pan, d = per[who]
        put(ev, perereca(frng, f0, cnt), t0, -7.0, pan, d)
    for t0, dur in ((14.6, 2.4), (37.6, 3.0), (56.0, 2.2)):
        put(ev, cururu(frng, dur), t0, -13.0, -0.1, 0.85)
    for t0 in (6.8, 19.2, 19.85, 35.6, 50.1, 50.7, 62.0):
        put(ev, uop(frng), t0, -5.0, -0.75, 0.3)
    put(ev, murucututu(frng, 370.0, 8), 17.2, -2.0, -0.65, 0.65, send_extra=-0.2)
    put(ev, murucututu(frng, 345.0, 7), 47.8, -3.0, 0.7, 0.8, send_extra=-0.2)
    y = bed + ev.render(t60=1.5, predelay=0.03, bright=0.3, seed=31)
    return finish(y, 'amb_noite.ogg', -25.0, 'Noite na Lagoa (ambiência)', hp=40, shelf_f=6000, shelf_db=-3.0)


# ---------------------------------------------------------------------------
# CHUVA
# ---------------------------------------------------------------------------
def plip(rng, f0):
    """Gota caindo na poça: bolha com altura subindo + estalinho do impacto."""
    n = nsamp(0.07)
    t = tarr(n)
    f = f0 * (1 + 0.8 * (1 - np.exp(-t / 0.012)))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.012) * np.clip(t / 0.0005, 0, 1)
    s += sy.bandpass(rng.standard_normal(n), 1000, 4500) * np.exp(-t / 0.0009) * 0.3
    return s


def trovao(rng, dur=10.0):
    """Trovão distante que rola: vários estrondos sobrepostos, grave com um pouco de médio
    (para aparecer em alto-falante pequeno) e tremulação lenta."""
    n = nsamp(dur)
    t = tarr(n)
    out = np.zeros((2, n))
    for t0, amp, att, tau in ((0.0, 1.0, 0.35, 1.0), (0.85, 0.85, 0.45, 1.3), (2.0, 0.7, 0.6, 1.4),
                              (3.4, 0.5, 0.8, 1.6), (5.1, 0.32, 0.9, 1.8)):
        for ch in range(2):
            tt = t - t0 - rng.uniform(-0.04, 0.04)
            env = np.clip(tt / att, 0, 1) ** 1.5 * np.exp(-np.maximum(0.0, tt - att) / tau)
            rumble = pinkf(n, rng, None, 140) * 1.0 + pinkf(n, rng, 120, 700) * 0.75
            out[ch] += rumble * env * amp * (0.9 if ch == 0 else 0.75)
    out *= 1 + 0.35 * smooth_noise(n, 5, rng)
    crack = pinkf(n, rng, 300, 1500) * np.clip(t / 0.15, 0, 1) * np.exp(-t / 0.45) * 0.25
    out[0] += crack * 0.6
    out[1] += crack * 0.4
    return out * win(n, 0.02, 2.0)


def amb_chuva():
    L, X, PRE = 48.0, 4.0, 1.0
    rng = np.random.default_rng(5505)
    n = bed_len(PRE, L, X)
    inten = sy.lowpass(slow_curve(n, 6.0, rng, 0.82, 1.08), 1.0, order=1)
    # chiado (muitas gotas longe): rosa, inclinado para o escuro
    hiss = sy.lowpass(sy.highpass(pink_st(n, rng, 0.15), 280), 5500, order=2)
    hiss = shelf(hiss, 2500, -5.0) * inten
    # gotas em folhas (esquerda/larga), telhado (direita), chão/grama (centro)
    leaves = np.zeros((2, n))
    roof = np.zeros((2, n))
    ground = np.zeros((2, n))
    k_leaf = [k_noise(0.008, 1400, 4200, 0.0012, rng), k_res(1300, 0.004, 0.6, rng, 900, 3500),
              k_res(1750, 0.003, 0.6, rng, 1000, 4000), k_res(2150, 0.0025, 0.5, rng, 1200, 4500)]
    k_roof = [k_res(f, 0.009, 0.5, rng, 400, 2200) for f in (640, 760, 880, 990)]
    k_ground = [k_noise(0.03, 300, 1600, 0.006, rng)]
    for ch in range(2):
        for k in k_leaf:
            leaves[ch] += conv(impulses(n, 420, rng, inten / 1.1), k)
        for k in k_roof:
            roof[ch] += conv(impulses(n, 160 * (0.6 if ch == 0 else 1.0), rng, inten / 1.1), k)
        for k in k_ground:
            ground[ch] += conv(impulses(n, 500, rng, inten / 1.1), k)
    leaves = sy.stereo_widen(leaves, 0.2)
    leaves[0] *= 1.12
    leaves[1] *= 0.88
    body = sy.lowpass(pink_st(n, rng, 0.5), 300) * inten
    bed = (set_rms(hiss, -27.0) + set_rms(sy.lowpass(leaves, 6000), -30.5) + set_rms(roof, -32.0)
           + set_rms(ground, -33.0) + set_rms(body, -36.0))
    bed = close_bed(bed, PRE, L, X)

    ev = Bus(L, 12.0)
    drng = np.random.default_rng(5606)
    # goteira da calha na poça (direita, perto): ritmo irregular num círculo de 48 s
    times, _ = circle_times(L, 52, 0.55, 1.35, drng, offset=0.3)
    for j, t0 in enumerate(times):
        x = plip(drng, drng.uniform(820, 1250)) * drng.uniform(0.55, 1.0)
        put(ev, x, t0, 2.0 + drng.uniform(-2.5, 1.0), 0.42 + drng.uniform(-0.04, 0.04), 0.25)
        if drng.random() < 0.12:     # pingo duplo
            put(ev, plip(drng, drng.uniform(900, 1300)) * 0.6, t0 + 0.11, -2.0, 0.45, 0.25)
    # pingos na madeira da varanda (esquerda), mais lentos
    times, _ = circle_times(L, 27, 1.1, 2.5, drng, offset=0.8)
    for t0 in times:
        x = k_res(drng.uniform(700, 980), 0.012, 0.6, drng, 600, 3000)
        put(ev, x, t0, -4.0 + drng.uniform(-2.5, 1.5), -0.52 + drng.uniform(-0.05, 0.05), 0.3)
    # pingos grossos nas folhas largas (bananeira), espalhados
    for _ in range(34):
        t0 = drng.uniform(0.0, L - 0.2)
        x = k_res(drng.uniform(260, 380), 0.02) * 0.5
        x[:nsamp(0.05)] += k_noise(0.05, 500, 2800, 0.012, drng)
        put(ev, x, t0, -7.0 + drng.uniform(-3, 2), drng.uniform(-0.85, 0.85), drng.uniform(0.2, 0.5))
    # trovão distante no meio
    th = set_peak(trovao(np.random.default_rng(5707), 10.0), -20.0)
    th = sy.lowpass(th, 2000)
    ev.add(th, 20.0, 10 ** (6.5 / 20), 0.0, 10 ** (0.0 / 20))
    y = bed + ev.render(t60=1.6, predelay=0.02, bright=0.3, seed=41, hp=60)
    return finish(y, 'amb_chuva.ogg', -23.0, 'Chuva (ambiência)', hp=35, shelf_f=5000, shelf_db=-3.5)


# ---------------------------------------------------------------------------
JOBS = {'mar': amb_mar, 'dia': amb_dia, 'noite': amb_noite, 'chuva': amb_chuva}


def main(args):
    t0 = time.time()
    names = [a for a in args if a in JOBS] or list(JOBS)
    results = {}
    for name in names:
        t1 = time.time()
        path, res = JOBS[name]()
        results[name] = res
        print('%s -> %s' % (name, os.path.relpath(path, os.getcwd())))
        print('  ', res, ' (%.1f s)' % (time.time() - t1))
    print('total %.1f s' % (time.time() - t0))
    return results


if __name__ == '__main__':
    main(sys.argv[1:])

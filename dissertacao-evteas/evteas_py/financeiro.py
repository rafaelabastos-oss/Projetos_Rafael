"""EVTEAS-Py — módulo financeiro.

Indicadores de análise de investimentos vetorizados (cada linha é uma realização das premissas):
VPL, TIR com diagnóstico explícito e payback simples e descontado
(Casarotto Filho; Kopittke, 2007; Assaf Neto, 2014).
"""
from __future__ import annotations

from typing import Tuple

import numpy as np


def _2d(fluxos) -> np.ndarray:
    f = np.asarray(fluxos, dtype=float)
    return f[None, :] if f.ndim == 1 else f


def vpl(taxa, fluxos) -> np.ndarray:
    """Valor Presente Líquido por período: sum(F_t / (1 + i)^t), t = 0..T.

    ``taxa`` é escalar ou vetor (uma taxa por linha); ``fluxos`` tem forma (T+1,) ou (n, T+1).
    """
    f = _2d(fluxos)
    n, m = f.shape
    i = np.broadcast_to(np.asarray(taxa, dtype=float), (n,))[:, None]
    t = np.arange(m)[None, :]
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        desconto = (1.0 + i) ** (-t)
    return np.sum(f * desconto, axis=1)


def trocas_de_sinal(fluxos) -> np.ndarray:
    """Número de trocas de sinal do fluxo (ignorando zeros) — regra de sinais de Descartes."""
    f = _2d(fluxos)
    s = np.sign(f)
    trocas = np.zeros(f.shape[0], dtype=int)
    ultimo = np.zeros(f.shape[0])
    for t in range(f.shape[1]):
        st = s[:, t]
        mudou = (st != 0) & (ultimo != 0) & (st != ultimo)
        trocas += mudou
        ultimo = np.where(st != 0, st, ultimo)
    return trocas


def tir(fluxos, lo: float = -0.90, hi: float = 1.0, pontos: int = 160,
        iteracoes: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """TIR por varredura de malha + bisseção vetorizada, com diagnóstico explícito.

    Retorna (taxa por período, diagnóstico). A taxa é ``nan`` quando não há raiz no intervalo:
    nunca é forçada ao limite numérico do algoritmo. Diagnósticos: ``convencional`` (uma raiz e
    uma troca de sinal no fluxo), ``multiplas`` (mais de uma raiz na malha), ``multiplas_possiveis``
    (uma raiz, mas mais de uma troca de sinal — regra de Descartes) e ``sem_solucao`` (o VPL não
    muda de sinal no intervalo pesquisado).
    """
    f = _2d(fluxos)
    n = f.shape[0]
    malha = np.unique(np.concatenate([np.linspace(lo, -0.5, 12), np.linspace(-0.5, hi, pontos)]))
    valores = np.vstack([vpl(np.full(n, r), f) for r in malha]).T  # (n, pontos)
    troca = (valores[:, :-1] * valores[:, 1:]) <= 0
    n_raizes = troca.sum(axis=1)
    existe = n_raizes > 0
    k = np.where(existe, troca.argmax(axis=1), 0)
    a, b = malha[k].astype(float), malha[k + 1].astype(float)
    fa = valores[np.arange(n), k]
    for _ in range(iteracoes):
        m = (a + b) / 2
        fm = vpl(m, f)
        esquerda = (fa * fm) <= 0
        b = np.where(esquerda, m, b)
        a = np.where(esquerda, a, m)
        fa = np.where(esquerda, fa, fm)
    raiz = np.where(existe, (a + b) / 2, np.nan)
    trocas = trocas_de_sinal(f)
    diag = np.where(~existe, "sem_solucao",
                    np.where(n_raizes > 1, "multiplas",
                             np.where(trocas > 1, "multiplas_possiveis", "convencional")))
    return raiz, diag


def payback(fluxos, taxa=None) -> np.ndarray:
    """Período (fracionário) em que o saldo acumulado se torna não negativo.

    Sem ``taxa``: payback simples; com ``taxa``: payback descontado. ``nan`` se não houver
    recuperação dentro do horizonte. A interpolação é linear dentro do período de virada.
    """
    f = _2d(fluxos)
    n, m = f.shape
    if taxa is not None:
        i = np.broadcast_to(np.asarray(taxa, dtype=float), (n,))[:, None]
        f = f * (1.0 + i) ** (-np.arange(m)[None, :])
    acum = np.cumsum(f, axis=1)
    pos = acum >= 0
    # primeiro período a partir do qual o saldo nunca mais volta a ser negativo
    ultimo_negativo = np.where((~pos).any(axis=1), m - 1 - np.argmax((~pos)[:, ::-1], axis=1), -1)
    t = ultimo_negativo + 1
    recupera = (t < m) & (t > 0)
    tt = np.clip(t, 1, m - 1)
    antes = acum[np.arange(n), tt - 1]
    ganho = f[np.arange(n), tt]
    frac = np.where(ganho != 0, -antes / np.where(ganho != 0, ganho, 1.0), 0.0)
    pb = (tt - 1) + np.clip(frac, 0.0, 1.0)
    pb = np.where(t == 0, 0.0, pb)
    return np.where(recupera | (t == 0), pb, np.nan)

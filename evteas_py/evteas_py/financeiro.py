"""Utilitários numéricos e de engenharia econômica (vetorizados).

Todas as funções aceitam fluxos com forma (M+1,) ou (n, M+1), em que n é o
número de iterações de Monte Carlo. Assim o modelo determinístico e o
estocástico usam exatamente as mesmas fórmulas (verificação de consistência).
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np


def safe_float(x, default: float = 0.0) -> float:
    try:
        x = float(x)
        return x if np.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def pct(x):
    return np.asarray(x, dtype=float) / 100.0


def safe_div(a, b, default=0.0):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(np.abs(b) < 1e-15, default, a / np.where(np.abs(b) < 1e-15, 1.0, b))
    return out if out.ndim else float(out)


def clamp(x, lo=0.0, hi=1.0):
    out = np.clip(np.nan_to_num(np.asarray(x, dtype=float), nan=lo), lo, hi)
    return out if out.ndim else float(out)


def taxa_anual_para_mensal(taxa_aa) -> np.ndarray:
    return (1 + np.asarray(taxa_aa, dtype=float)) ** (1 / 12) - 1


def taxa_mensal_para_anual(taxa_am) -> np.ndarray:
    return (1 + np.asarray(taxa_am, dtype=float)) ** 12 - 1


def _2d(fluxos) -> np.ndarray:
    f = np.asarray(fluxos, dtype=float)
    return f[None, :] if f.ndim == 1 else f


def vpl(taxa, fluxos):
    """Valor presente líquido; o índice 0 é a data focal (não descontado)."""
    f = _2d(fluxos)
    taxa = np.asarray(taxa, dtype=float).reshape(-1, 1)
    t = np.arange(f.shape[1])[None, :]
    with np.errstate(over="ignore", invalid="ignore"):
        out = (f / (1 + taxa) ** t).sum(axis=1)
    return float(out[0]) if np.ndim(fluxos) == 1 else out


def trocas_de_sinal(fluxos) -> np.ndarray:
    f = _2d(fluxos)
    s = np.sign(f)
    out = np.zeros(f.shape[0], dtype=int)
    for i in range(f.shape[0]):
        nz = s[i][s[i] != 0]
        out[i] = int(np.sum(nz[1:] != nz[:-1])) if nz.size > 1 else 0
    return out


def tir(fluxos, lo: float = -0.90, hi: float = 1.0, pontos: int = 160,
        iteracoes: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """TIR por varredura de malha + bisseção vetorizada, com diagnóstico explícito.

    Retorna (taxa por período, diagnóstico). A taxa é ``nan`` quando não há raiz
    no intervalo: nunca é forçada ao limite numérico (a ausência de raiz não
    pode ser confundida com uma taxa de -0,90). Diagnósticos: ``convencional`` (uma raiz e uma
    troca de sinal no fluxo), ``multiplas`` (mais de uma raiz na malha),
    ``multiplas_possiveis`` (uma raiz, mas mais de uma troca de sinal —
    regra de Descartes) e ``sem_solucao`` (o VPL não muda de sinal).
    """
    f = _2d(fluxos)
    n = f.shape[0]
    malha = np.unique(np.concatenate([np.linspace(lo, -0.5, 12), np.linspace(-0.5, hi, pontos)]))
    valores = np.vstack([vpl(np.full(n, r), f) for r in malha]).T          # (n, pontos)
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
    """Payback (simples se ``taxa`` é None, descontado caso contrário), em períodos.

    Retorna ``nan`` quando o investimento não é recuperado no horizonte.
    Interpolação linear dentro do período de recuperação.
    """
    f = _2d(fluxos)
    if taxa is not None:
        t = np.arange(f.shape[1])[None, :]
        f = f / (1 + np.asarray(taxa, dtype=float).reshape(-1, 1)) ** t
    acum = np.cumsum(f, axis=1)
    out = np.full(f.shape[0], np.nan)
    for i in range(f.shape[0]):
        idx = np.where((acum[i, 1:] >= 0) & (acum[i, :-1] < 0))[0]
        if idx.size:
            k = idx[0] + 1
            out[i] = (k - 1) + safe_div(-acum[i, k - 1], f[i, k], 0.0)
    return out


def percentis(valores, ps=(1, 5, 10, 25, 50, 75, 90, 95, 99)) -> Dict[str, float]:
    x = np.asarray(valores, dtype=float)
    x = x[np.isfinite(x)]
    if not x.size:
        return {f"p{p}": float("nan") for p in ps}
    return {f"p{p}": float(np.percentile(x, p)) for p in ps}

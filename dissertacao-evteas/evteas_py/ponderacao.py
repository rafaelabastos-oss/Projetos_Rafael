"""EVTEAS-Py — módulo ponderacao.

Normalização dos KPIs (sentido e faixa de referência declarados), scores dimensionais, índice
integrado EVTEAS, pesos (preset, escala Likert do Quadro 7 ou AHP de Saaty, 1980), regra de
decisão em dois estágios com vetos não compensatórios e ordenação de alternativas por TOPSIS
(Hwang; Yoon, 1981).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import EVTEASConfig

DIMENSOES = ["tecnica", "economica", "ambiental", "social"]
NOMES_DIMENSOES = {"tecnica": "Técnica", "economica": "Econômica", "ambiental": "Ambiental", "social": "Social"}

# KPI: (dimensão, rótulo, sentido, mínimo de referência, máximo de referência, extrator)
KPIS: Dict[str, tuple] = {
    "oee": ("tecnica", "OEE", "benefício", 0.0, 1.0, lambda r: r["tecnico"]["oee"]),
    "fcr": ("tecnica", "FCR", "custo", 1.0, 2.5, lambda r: r["tecnico"]["fcr"]),
    "produtividade_relativa": ("tecnica", "Produtividade relativa", "benefício", 0.0, 1.0,
                               lambda r: r["tecnico"]["produtividade_relativa"]),
    "vpl_investimento": ("economica", "VPL/investimento", "benefício", -1.0, 1.0,
                         lambda r: r["economico"]["vpl"] / r["economico"]["investimento"]),
    "roi": ("economica", "ROI anual", "benefício", -0.10, 0.30, lambda r: r["economico"]["roi_regime"]),
    "margem_seguranca": ("economica", "Margem de segurança", "benefício", 0.0, 0.50,
                         lambda r: r["economico"]["margem_seguranca"]),
    "ph_azul": ("ambiental", "PH azul (m³/t)", "custo", 0.0, 3000.0, lambda r: r["ambiental"]["ph_azul_m3_t"]),
    "ph_cinza": ("ambiental", "PH cinza (m³/t)", "custo", 0.0, 100000.0, lambda r: r["ambiental"]["ph_cinza_m3_t"]),
    "ecoeficiencia": ("ambiental", "Ecoeficiência (R$/kgCO2e)", "benefício", 0.0, 10.0,
                      lambda r: np.nan_to_num(r["ambiental"]["ecoeficiencia_rs_kgco2e"], nan=0.0)),
    "intensidade_carbono": ("ambiental", "Intensidade de carbono (kgCO2e/kg)", "custo", 0.0, 4.0,
                            lambda r: r["ambiental"]["intensidade_carbono_kg_kg"]),
    "conformidade": ("ambiental", "Conformidade ambiental (0–10)", "benefício", 0.0, 10.0,
                     lambda r: r["ambiental"]["score_conformidade_0_10"]),
    "lso": ("social", "LSO (0–100)", "benefício", 0.0, 100.0, lambda r: r["social"]["lso_0_100"]),
    "rvl": ("social", "RVL (%)", "benefício", 0.0, 100.0, lambda r: r["social"]["rvl_pct"]),
    "radar_social": ("social", "Radar Social", "benefício", 0.0, 1.0, lambda r: r["social"]["radar_social_media"]),
}


def normalizar(valor, sentido: str, minimo: float, maximo: float) -> np.ndarray:
    """Normalização min–máx com saturação em [0, 1]; custos são invertidos."""
    v = np.asarray(valor, dtype=float)
    x = (v - minimo) / (maximo - minimo)
    x = np.clip(np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    return 1.0 - x if sentido == "custo" else x


# ---------------------------------------------------------------------------------------------
# Pesos
# ---------------------------------------------------------------------------------------------
def pesos_likert(escores: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Pesos a partir da escala Likert (Quadro 7): média dos escores (1 a 5) de cada KPI entre os
    avaliadores, dividida pela soma total, de modo que os pesos somem 1. Também calcula a
    concordância média entre avaliadores (1 = escores idênticos; 0 = amplitude máxima de 4 pontos)."""
    if not escores:
        raise ValueError("Informe os escores Likert de pelo menos um avaliador")
    avaliadores = list(escores)
    for av, d in escores.items():
        faltam = [k for k in KPIS if k not in d]
        if faltam:
            raise ValueError(f"Avaliador {av!r} sem escore para: {faltam}")
        for k, v in d.items():
            if k in KPIS and not (1 <= int(v) <= 5):
                raise ValueError(f"Escore Likert fora de 1..5 ({av}, {k}: {v})")
    media = {k: float(np.mean([escores[a][k] for a in avaliadores])) for k in KPIS}
    total = sum(media.values())
    peso_kpi = {k: v / total for k, v in media.items()}
    peso_dim = {d: sum(p for k, p in peso_kpi.items() if KPIS[k][0] == d) for d in DIMENSOES}
    amplitude = {k: max(escores[a][k] for a in avaliadores) - min(escores[a][k] for a in avaliadores) for k in KPIS}
    concordancia = {k: 1 - amp / 4 for k, amp in amplitude.items()}
    return {"metodo": "likert", "dimensoes": peso_dim, "kpis": peso_kpi, "media_escores": media,
            "concordancia_por_kpi": concordancia, "concordancia_media": float(np.mean(list(concordancia.values()))),
            "avaliadores": avaliadores}


RI_SAATY = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def pesos_ahp(matriz) -> Dict[str, Any]:
    """Pesos pelo autovetor principal da matriz de comparação par a par (Saaty, 1980), com índice
    e razão de consistência (RC <= 0,10 indica julgamentos consistentes)."""
    A = np.asarray(matriz, dtype=float)
    k = A.shape[0]
    if A.shape != (k, k) or k != len(DIMENSOES):
        raise ValueError("A matriz AHP deve ser 4 x 4 (técnica, econômica, ambiental, social)")
    if np.any(A <= 0) or not np.allclose(A * A.T, 1.0, atol=1e-6):
        raise ValueError("A matriz AHP deve ser positiva e recíproca (a_ji = 1/a_ij)")
    autovalores, autovetores = np.linalg.eig(A)
    i = int(np.argmax(autovalores.real))
    w = np.abs(autovetores[:, i].real)
    w = w / w.sum()
    lam = float(autovalores[i].real)
    ic = (lam - k) / (k - 1)
    rc = ic / RI_SAATY[k] if RI_SAATY[k] else 0.0
    return {"metodo": "ahp", "dimensoes": dict(zip(DIMENSOES, w.tolist())), "kpis": None,
            "lambda_max": lam, "indice_consistencia": ic, "razao_consistencia": rc, "consistente": rc <= 0.10}


def resolver_pesos(cfg: EVTEASConfig) -> Dict[str, Any]:
    p = cfg.pesos
    if p.metodo == "likert":
        return pesos_likert(p.likert)
    if p.metodo == "ahp":
        return pesos_ahp(p.ahp)
    if p.metodo != "preset":
        raise ValueError("Método de pesos deve ser 'preset', 'likert' ou 'ahp'")
    soma = sum(p.preset[d] for d in DIMENSOES)
    return {"metodo": "preset", "dimensoes": {d: p.preset[d] / soma for d in DIMENSOES}, "kpis": None}


# ---------------------------------------------------------------------------------------------
# Índice integrado
# ---------------------------------------------------------------------------------------------
def calcular_indice(cfg: EVTEASConfig, tec, eco, amb, soc, gov, pesos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Scores dimensionais (médias ponderadas dos KPIs normalizados) e índice EVTEAS (média
    ponderada das quatro dimensões)."""
    pesos = pesos or resolver_pesos(cfg)
    r = {"tecnico": tec, "economico": eco, "ambiental": amb, "social": soc}
    n = np.size(eco["vpl"])
    brutos, normalizados = {}, {}
    for k, (dim, rotulo, sentido, mn, mx, f) in KPIS.items():
        v = np.broadcast_to(np.asarray(f(r), dtype=float), (n,))
        brutos[k] = v
        normalizados[k] = normalizar(v, sentido, mn, mx)
    peso_kpi = pesos.get("kpis")
    scores = {}
    for d in DIMENSOES:
        ks = [k for k in KPIS if KPIS[k][0] == d]
        w = np.array([peso_kpi[k] for k in ks]) if peso_kpi else np.ones(len(ks))
        w = w / w.sum()
        scores[d] = np.sum(np.vstack([normalizados[k] for k in ks]) * w[:, None], axis=0)
    wd = pesos["dimensoes"]
    indice = sum(wd[d] * scores[d] for d in DIMENSOES)
    esg = {"ambiental": scores["ambiental"], "social": scores["social"],
           "governanca": np.full(n, gov["score_governanca"])}
    esg_score = (esg["ambiental"] + esg["social"] + esg["governanca"]) / 3
    return {"kpis_brutos": brutos, "kpis_normalizados": normalizados, "scores": scores,
            "pesos": pesos, "indice_evteas": indice, "pilares_esg": esg, "score_esg": esg_score}


def tabela_normalizacao(indice: Dict[str, Any], linha: int = 0) -> pd.DataFrame:
    linhas = []
    for k, (dim, rotulo, sentido, mn, mx, _) in KPIS.items():
        linhas.append({"Dimensão": NOMES_DIMENSOES[dim], "KPI": rotulo, "Sentido": sentido,
                       "Faixa de referência": f"{mn:g} a {mx:g}",
                       "Valor bruto": float(np.asarray(indice["kpis_brutos"][k])[linha]),
                       "Normalizado": float(np.asarray(indice["kpis_normalizados"][k])[linha])})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------------------------
# Regra de decisão
# ---------------------------------------------------------------------------------------------
def classificar(cfg: EVTEASConfig, vpl: float, indice: float, lso: float, vetos_ambientais: List[str],
                prob_vpl_positivo: Optional[float] = None) -> Dict[str, Any]:
    """Regra de decisão em dois estágios: vetos não compensatórios + índice compensatório.

    O índice agregado sozinho pode ocultar fragilidades; por isso VPL negativo, item ambiental
    eliminatório não atendido ou LSO abaixo do mínimo impedem a classificação "VIÁVEL",
    qualquer que seja o índice (Garnett; Röös; Little, 2015).
    """
    d = cfg.decisao
    motivos = []
    if d.aplicar_vetos:
        if vpl < 0:
            motivos.append("VPL negativo (veto econômico)")
        motivos += [f"Item eliminatório não atendido: {v}" for v in vetos_ambientais]
        if lso < d.lso_minimo:
            motivos.append(f"LSO abaixo do mínimo ({lso:.0f} < {d.lso_minimo:.0f})")
    ressalvas = []
    if prob_vpl_positivo is not None and prob_vpl_positivo < d.prob_vpl_positivo_minima:
        ressalvas.append(f"P(VPL > 0) = {prob_vpl_positivo:.0%} abaixo de {d.prob_vpl_positivo_minima:.0%}")
    if motivos:
        classe = "NÃO VIÁVEL"
    elif indice >= d.limiar_indice_viavel and not ressalvas:
        classe = "VIÁVEL"
    elif indice >= d.limiar_indice_ressalvas:
        classe = "VIÁVEL COM RESSALVAS"
        if indice < d.limiar_indice_viavel:
            ressalvas.append(f"Índice EVTEAS {indice:.3f} abaixo do limiar {d.limiar_indice_viavel:.2f}")
    else:
        classe = "NÃO VIÁVEL"
        motivos.append(f"Índice EVTEAS {indice:.3f} abaixo de {d.limiar_indice_ressalvas:.2f}")
    return {"classificacao": classe, "vetos": motivos, "ressalvas": ressalvas}


# ---------------------------------------------------------------------------------------------
# TOPSIS
# ---------------------------------------------------------------------------------------------
def topsis(matriz, pesos, sentidos: List[str]) -> np.ndarray:
    """Proximidade relativa à solução ideal (0 a 1) de cada alternativa (linhas da matriz).

    ``sentidos``: 'benefício' ou 'custo' por critério (colunas). Normalização vetorial.
    """
    X = np.asarray(matriz, dtype=float)
    w = np.asarray(pesos, dtype=float)
    w = w / w.sum()
    norma = np.sqrt((X ** 2).sum(axis=0))
    R = X / np.where(norma == 0, 1.0, norma)
    V = R * w
    beneficio = np.array([s == "benefício" for s in sentidos])
    ideal = np.where(beneficio, V.max(axis=0), V.min(axis=0))
    anti = np.where(beneficio, V.min(axis=0), V.max(axis=0))
    d_mais = np.sqrt(((V - ideal) ** 2).sum(axis=1))
    d_menos = np.sqrt(((V - anti) ** 2).sum(axis=1))
    return np.where(d_mais + d_menos > 0, d_menos / (d_mais + d_menos), 0.0)

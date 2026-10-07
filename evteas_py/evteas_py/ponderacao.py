"""Normalização dos KPIs, ponderação (preset, Likert, AHP), índice EVTEAS,
regras de decisão e TOPSIS para comparação de alternativas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .config import KPIS_POR_DIMENSAO, EVTEASConfig
from .financeiro import clamp, safe_div

DIMENSOES = ["tecnico", "economico", "ambiental", "social"]

# Referências de normalização explícitas (auditáveis na V&V). sentido: +1
# benefício (maior é melhor), -1 custo (menor é melhor).
REFERENCIAS_NORMALIZACAO = {
    "oee": (+1, 0.0, 1.0, "fração (Nakajima, 1988)"),
    "fcr": (-1, 1.0, 2.5, "kg ração/kg ganho"),
    "produtividade": (+1, 0.0, 1.0, "fração do potencial do sistema"),
    "vpl": (+1, -1.0, 1.0, "VPL / investimento total"),
    "roi": (+1, -0.10, 0.30, "lucro líquido anual / investimento"),
    "margem_seguranca": (+1, 0.0, 0.50, "fração da receita"),
    "ph_azul": (-1, 0.0, 3000.0, "m³/t"),
    "ph_cinza": (-1, 0.0, 100000.0, "m³/t"),
    "ecoeficiencia": (+1, 0.0, 10.0, "R$ de valor adicionado/kgCO2e"),
    "intensidade_carbono": (-1, 0.0, 4.0, "kgCO2e/kg"),
    "conformidade": (+1, 0.0, 10.0, "score 0–10"),
    "lso": (+1, 0.0, 100.0, "score 0–100 (Hurst; Ihlen, 2018)"),
    "rvl": (+1, 0.0, 100.0, "% do custo operacional (GRI 201-1/204-1)"),
    "radar_social": (+1, 0.0, 1.0, "média dos eixos do Radar Social"),
}


def normalizar(valor, sentido: int, minimo: float, maximo: float):
    v = np.nan_to_num(np.asarray(valor, dtype=float), nan=(minimo if sentido > 0 else maximo))
    if maximo <= minimo:
        return np.full_like(v, 0.5)
    z = (v - minimo) / (maximo - minimo) if sentido > 0 else (maximo - v) / (maximo - minimo)
    return np.clip(z, 0, 1)


def kpis_brutos(tec, eco, amb, soc) -> Dict[str, np.ndarray]:
    return {
        "oee": tec["oee"],
        "fcr": tec["fcr"],
        "produtividade": tec["produtividade_relativa"],
        "vpl": safe_div(eco["vpl"], eco["investimento_total"], 0.0),
        "roi": eco["roi_anual_regime"],
        "margem_seguranca": eco["margem_seguranca"],
        "ph_azul": amb["ph_azul_m3_t"],
        "ph_cinza": amb["ph_cinza_m3_t"],
        "ecoeficiencia": amb["ecoeficiencia_r_por_kgco2e"],   # NaN (indefinida) -> 0
        "intensidade_carbono": amb["intensidade_carbono_kgco2e_kg"],
        "conformidade": np.full_like(tec["oee"], amb["conformidade_0_10"]),
        "lso": soc["lso_0_100"],
        "rvl": soc["rvl_pct"],
        "radar_social": soc["radar_social_score"],
    }


# ---------------------------------------------------------------------------
# Pesos: Likert (Quadro 7), AHP e preset
# ---------------------------------------------------------------------------

def pesos_likert(avaliacoes: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
    """Pesos relativos a partir da escala Likert de 1 a 5 (Seção 3.4).

    Para cada avaliador, peso = escore / soma dos escores; o peso final é a
    média entre avaliadores (triangulação). Informa a divergência por critério.
    """
    if not avaliacoes:
        raise ValueError("Nenhuma avaliação Likert informada")
    df = pd.DataFrame(avaliacoes).astype(float)          # linhas: critérios; colunas: avaliadores
    if df.isna().any().any():
        raise ValueError("Todos os avaliadores devem pontuar todos os critérios")
    if ((df < 1) | (df > 5)).any().any() or (df % 1 != 0).any().any():
        raise ValueError("Escores Likert devem ser inteiros entre 1 e 5")
    pesos_av = df / df.sum(axis=0)
    pesos = pesos_av.mean(axis=1)
    pesos = pesos / pesos.sum()
    tabela = df.copy()
    tabela.columns = [f"Escore — {c}" for c in df.columns]
    tabela["Divergência (máx − mín)"] = df.max(axis=1) - df.min(axis=1)
    tabela["Peso normalizado"] = pesos
    return {"pesos": pesos.to_dict(), "tabela": tabela.reset_index().rename(columns={"index": "Critério"}),
            "concordancia_media": float(1 - (df.max(axis=1) - df.min(axis=1)).mean() / 4)}


INDICE_ALEATORIO = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def pesos_ahp(matriz: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """Pesos AHP (autovetor principal) e razão de consistência (Saaty)."""
    A = np.asarray(matriz, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("Matriz AHP deve ser quadrada")
    if np.any(A <= 0) or not np.allclose(A * A.T, 1.0, atol=1e-6):
        raise ValueError("Matriz AHP deve ser positiva e recíproca (a_ji = 1/a_ij)")
    vals, vecs = np.linalg.eig(A)
    k = int(np.argmax(vals.real))
    lam = float(vals.real[k])
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    n = A.shape[0]
    ci = (lam - n) / (n - 1) if n > 1 else 0.0
    ri = INDICE_ALEATORIO.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0
    return {"pesos": w, "lambda_max": lam, "ic": ci, "rc": cr, "consistente": cr <= 0.10}


def resolver_pesos(cfg: EVTEASConfig) -> Dict[str, Any]:
    p = cfg.pesos
    info: Dict[str, Any] = {"metodo": p.metodo}
    if p.metodo == "preset":
        dim = p.vetor()
    elif p.metodo == "likert":
        lk = pesos_likert(p.likert_dimensoes)
        faltando = set(DIMENSOES) - set(lk["pesos"])
        if faltando:
            raise ValueError(f"Likert sem as dimensões: {faltando}")
        dim = {d: lk["pesos"][d] for d in DIMENSOES}
        info["likert_dimensoes"] = lk
    elif p.metodo == "ahp":
        if p.ahp_matriz is None:
            raise ValueError("Método AHP exige ahp_matriz (ordem: técnico, econômico, ambiental, social)")
        ahp = pesos_ahp(p.ahp_matriz)
        dim = dict(zip(DIMENSOES, ahp["pesos"].tolist()))
        info["ahp"] = ahp
    else:
        raise ValueError(f"Método de ponderação desconhecido: {p.metodo}")

    kpi: Dict[str, float] = {}
    if p.likert_kpis:
        lk = pesos_likert(p.likert_kpis)
        info["likert_kpis"] = lk
        kpi_bruto = lk["pesos"]
    else:
        kpi_bruto = p.kpi
    for d, nomes in KPIS_POR_DIMENSAO.items():
        w = np.array([max(float(kpi_bruto.get(k, 1.0)), 0.0) for k in nomes])
        w = w / w.sum() if w.sum() > 0 else np.full(len(nomes), 1 / len(nomes))
        kpi.update(dict(zip(nomes, w.tolist())))
    info["dimensoes"] = dim
    info["kpi_intra_dimensao"] = kpi
    return info


# ---------------------------------------------------------------------------
# Índice integrado, ESG e decisão
# ---------------------------------------------------------------------------

def calcular_indice(cfg: EVTEASConfig, tec, eco, amb, soc, gov, pesos=None) -> Dict[str, Any]:
    pesos = pesos or resolver_pesos(cfg)
    brutos = kpis_brutos(tec, eco, amb, soc)
    norm = {k: normalizar(v, *REFERENCIAS_NORMALIZACAO[k][:3]) for k, v in brutos.items()}
    dims = {}
    for d, nomes in KPIS_POR_DIMENSAO.items():
        dims[d] = sum(norm[k] * pesos["kpi_intra_dimensao"][k] for k in nomes)
    indice = sum(dims[d] * pesos["dimensoes"][d] for d in DIMENSOES)
    esg = {"E": dims["ambiental"], "S": dims["social"], "G": np.full_like(indice, gov["score_0_1"])}
    esg_score = (esg["E"] + esg["S"] + esg["G"]) / 3
    return {"kpis_brutos": brutos, "kpis_normalizados": norm, "dimensoes": dims,
            "indice_evteas": np.clip(indice, 0, 1), "esg": esg, "esg_score": esg_score, "pesos": pesos}


def classificar(cfg: EVTEASConfig, vpl: float, indice: float, lso: float, vetos_ambientais: List[str],
                prob_vpl_positivo: Optional[float] = None) -> Dict[str, Any]:
    """Regra de decisão em dois estágios: vetos não compensatórios + índice compensatório.

    O índice agregado sozinho pode ocultar fragilidades (Rev. 186, Seção 5.4);
    por isso VPL negativo, item ambiental eliminatório não atendido ou LSO abaixo
    do mínimo impedem a classificação "VIÁVEL", qualquer que seja o índice.
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


# ---------------------------------------------------------------------------
# TOPSIS — comparação de alternativas de projeto
# ---------------------------------------------------------------------------

def topsis(df: pd.DataFrame, criterios: List[str], pesos: Sequence[float], beneficio: Sequence[bool]) -> pd.DataFrame:
    X = df[criterios].astype(float).to_numpy()
    if np.isnan(X).any():
        raise ValueError("TOPSIS não aceita valores ausentes na matriz de decisão")
    W = np.asarray(pesos, dtype=float)
    W = W / W.sum()
    den = np.sqrt((X ** 2).sum(axis=0))
    den[den == 0] = 1
    V = X / den * W
    ben = np.asarray(beneficio, dtype=bool)
    ideal = np.where(ben, V.max(axis=0), V.min(axis=0))
    anti = np.where(ben, V.min(axis=0), V.max(axis=0))
    d_mais = np.sqrt(((V - ideal) ** 2).sum(axis=1))
    d_menos = np.sqrt(((V - anti) ** 2).sum(axis=1))
    out = df.copy()
    out["D+"] = d_mais
    out["D-"] = d_menos
    out["TOPSIS"] = d_menos / (d_mais + d_menos + 1e-15)
    out["Ranking"] = out["TOPSIS"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("Ranking").reset_index(drop=True)

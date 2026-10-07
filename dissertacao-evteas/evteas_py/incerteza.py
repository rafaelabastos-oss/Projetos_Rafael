"""EVTEAS-Py — módulo incerteza.

Simulação de Monte Carlo sobre o motor único (Rubinstein; Kroese, 2017), estatísticas de risco,
convergência, importância das variáveis (correlação de postos de Spearman), sensibilidade de um
fator por vez, valores críticos (VPL = 0) e cenários pessimista e otimista.
"""
from __future__ import annotations

from statistics import NormalDist
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import EVTEASConfig, copiar, definir_por_caminho, obter_por_caminho
from .modelo import motor
from .ponderacao import resolver_pesos

VARIAVEIS_SENSIBILIDADE = [
    "economico.preco_venda_kg", "economico.custo_racao_kg", "tecnico.fcr",
    "tecnico.desempenho_crescimento_pct", "economico.custos_fixos_fator", "economico.capex_fator",
    "economico.tma_aa_pct", "tecnico.mortalidade_pct", "economico.tarifa_energia_kwh",
    "economico.custo_alevino_milheiro",
]

ROTULOS = {
    "economico.preco_venda_kg": "Preço de venda (R$/kg)",
    "economico.custo_racao_kg": "Custo da ração (R$/kg)",
    "economico.custo_alevino_milheiro": "Milheiro de alevinos (R$)",
    "economico.tarifa_energia_kwh": "Tarifa de energia (R$/kWh)",
    "economico.custos_fixos_fator": "Fator de custos fixos",
    "economico.capex_fator": "Fator de CAPEX (AACE Classe 5)",
    "economico.tma_aa_pct": "TMA (% a.a.)",
    "tecnico.fcr": "FCR",
    "tecnico.mortalidade_pct": "Mortalidade (%)",
    "tecnico.desempenho_crescimento_pct": "Desempenho de crescimento (%)",
}


def rotulo(caminho: str) -> str:
    return ROTULOS.get(caminho, caminho)


def amostrar(cfg: EVTEASConfig, n: int, seed: int) -> Dict[str, np.ndarray]:
    """Amostras das premissas incertas, em ordem fixa (alfabética) de variáveis, o que garante a
    reprodutibilidade com a mesma semente (np.random.default_rng)."""
    rng = np.random.default_rng(seed)
    entradas = {}
    for caminho in sorted(cfg.distribuicoes):
        d = cfg.distribuicoes[caminho]
        if d.tipo == "triangular":
            if d.minimo == d.maximo:
                entradas[caminho] = np.full(n, float(d.minimo))
            else:
                entradas[caminho] = rng.triangular(d.minimo, d.mais_provavel, d.maximo, size=n)
        else:
            entradas[caminho] = rng.uniform(d.minimo, d.maximo, size=n)
    return entradas


def _estatisticas(x: np.ndarray, nivel: float = 0.95) -> Dict[str, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    media, dp = float(np.mean(x)), float(np.std(x, ddof=1)) if n > 1 else 0.0
    ep = dp / np.sqrt(n) if n else np.nan
    z = NormalDist().inv_cdf((1 + nivel) / 2)
    p5, p50, p95 = np.percentile(x, [5, 50, 95])
    corte = np.percentile(x, 5)
    cvar = float(x[x <= corte].mean()) if np.any(x <= corte) else float(corte)
    return {"n": n, "media": media, "ic_inf": media - z * ep, "ic_sup": media + z * ep, "mediana": float(p50),
            "desvio_padrao": dp, "coef_variacao": abs(dp / media) if media else np.nan, "p5": float(p5),
            "p50": float(p50), "p95": float(p95), "var_5": float(corte), "cvar_5": cvar, "erro_padrao": ep,
            "minimo": float(np.min(x)), "maximo": float(np.max(x))}


def monte_carlo(cfg: EVTEASConfig, n: Optional[int] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    """Simulação de Monte Carlo estática: cada iteração amostra um vetor de premissas e recalcula
    os fluxos de todo o horizonte com o mesmo motor da análise determinística."""
    n = int(n or cfg.monte_carlo.iteracoes)
    seed = int(cfg.monte_carlo.seed if seed is None else seed)
    if not cfg.distribuicoes:
        raise ValueError("Nenhuma distribuição de incerteza definida (cfg.distribuicoes vazio)")
    entradas = amostrar(cfg, n, seed)
    pesos = resolver_pesos(cfg)
    r = motor(cfg, entradas, n, pesos)
    eco, tec, amb, soc, idx = r["economico"], r["tecnico"], r["ambiental"], r["social"], r["indice"]
    tma = cfg.economico.tma_aa_pct / 100

    amostra = pd.DataFrame({k: v for k, v in entradas.items()})
    amostra["VPL"] = eco["vpl"]
    amostra["TIR a.a."] = eco["tir_aa"]
    amostra["VPL beneficiário"] = eco["vpl_beneficiario"]
    amostra["Índice EVTEAS"] = idx["indice_evteas"]
    amostra["OEE"] = tec["oee"]
    amostra["Intensidade de carbono"] = amb["intensidade_carbono_kg_kg"]
    amostra["RVL (%)"] = soc["rvl_pct"]

    est = _estatisticas(eco["vpl"], cfg.monte_carlo.nivel_confianca)
    tir_aa = eco["tir_aa"]
    tir_fin = tir_aa[np.isfinite(tir_aa)]
    est.update({
        "prob_vpl_positivo": float(np.mean(eco["vpl"] > 0)),
        "prob_tir_maior_tma": float(np.mean(np.nan_to_num(tir_aa, nan=-np.inf) > tma)),
        "tir_p5": float(np.percentile(tir_fin, 5)) if len(tir_fin) else np.nan,
        "tir_p50": float(np.percentile(tir_fin, 50)) if len(tir_fin) else np.nan,
        "tir_p95": float(np.percentile(tir_fin, 95)) if len(tir_fin) else np.nan,
        "tir_sem_solucao": float(np.mean(~np.isfinite(tir_aa))),
        "indice_media": float(np.mean(idx["indice_evteas"])),
        "prob_indice_viavel": float(np.mean(idx["indice_evteas"] >= cfg.decisao.limiar_indice_viavel)),
        "vpl_beneficiario_media": float(np.mean(eco["vpl_beneficiario"])),
        "prob_vpl_beneficiario_positivo": float(np.mean(eco["vpl_beneficiario"] > 0)),
        "payback_descontado_mediana": float(np.nanmedian(eco["payback_descontado_meses"]))
        if np.any(np.isfinite(eco["payback_descontado_meses"])) else np.nan,
    })

    # Convergência: média acumulada e intervalo de confiança
    v = eco["vpl"]
    k = np.arange(1, n + 1)
    media_acum = np.cumsum(v) / k
    var_acum = np.maximum(np.cumsum(v ** 2) / k - media_acum ** 2, 0) * k / np.maximum(k - 1, 1)
    ep_acum = np.sqrt(var_acum / k)
    passos = np.unique(np.geomspace(10, n, num=min(200, n)).astype(int)) if n >= 10 else np.arange(1, n + 1)
    convergencia = pd.DataFrame({"Iterações": passos, "Média do VPL": media_acum[passos - 1],
                                 "IC inferior": media_acum[passos - 1] - 1.96 * ep_acum[passos - 1],
                                 "IC superior": media_acum[passos - 1] + 1.96 * ep_acum[passos - 1]})

    # Importância das variáveis: correlação de postos de Spearman entre entradas e VPL
    imp = []
    for c in entradas:
        if np.std(entradas[c]) > 0:
            rho = pd.Series(entradas[c]).rank().corr(pd.Series(v).rank())
            imp.append({"Variável": c, "Rótulo": rotulo(c), "Spearman (VPL)": float(rho)})
    importancia = pd.DataFrame(imp, columns=["Variável", "Rótulo", "Spearman (VPL)"])
    importancia = importancia.sort_values("Spearman (VPL)", key=lambda s: -s.abs()).reset_index(drop=True)
    return {"n": n, "seed": seed, "entradas": entradas, "amostra": amostra, "estatisticas": est,
            "convergencia": convergencia, "importancia": importancia, "vpl": v,
            "indice": idx["indice_evteas"], "vpl_beneficiario": eco["vpl_beneficiario"]}


def _vpl_com(cfg: EVTEASConfig, caminho: str, valor: float) -> float:
    r = motor(cfg, {caminho: np.array([float(valor)])}, 1)
    return float(r["economico"]["vpl"][0])


def sensibilidade(cfg: EVTEASConfig, variaveis: Optional[List[str]] = None,
                  variacoes=(-0.20, -0.10, 0.10, 0.20)) -> pd.DataFrame:
    """Sensibilidade de um fator por vez: cada premissa varia ±10% e ±20%, as demais no caso-base."""
    variaveis = variaveis or VARIAVEIS_SENSIBILIDADE
    base = float(motor(cfg, None, 1)["economico"]["vpl"][0])
    linhas = []
    for var in variaveis:
        x = float(obter_por_caminho(cfg, var))
        linha = {"Variável": var, "Rótulo": rotulo(var), "Valor base": x}
        for d in variacoes:
            linha[f"ΔVPL ({d:+.0%})"] = _vpl_com(cfg, var, x * (1 + d)) - base
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    col = [c for c in df.columns if c.startswith("ΔVPL (+10")]
    if col:
        df = df.reindex(df[col[0]].abs().sort_values(ascending=False).index).reset_index(drop=True)
    return df


def valores_criticos(cfg: EVTEASConfig, variaveis: Optional[List[str]] = None) -> pd.DataFrame:
    """Valor de cada variável que zera o VPL (demais premissas no caso-base), por bisseção."""
    variaveis = variaveis or [v for v in VARIAVEIS_SENSIBILIDADE if v != "economico.tma_aa_pct"]
    linhas = []
    for var in variaveis:
        x = float(obter_por_caminho(cfg, var))
        a, b = 0.0, max(x * 5, 1.0)
        if var == "tecnico.mortalidade_pct":
            b = 99.0
        fa, fb = _vpl_com(cfg, var, a), _vpl_com(cfg, var, b)
        critico = float("nan")
        if fa * fb <= 0:
            for _ in range(80):
                m = (a + b) / 2
                fm = _vpl_com(cfg, var, m)
                if fa * fm <= 0:
                    b, fb = m, fm
                else:
                    a, fa = m, fm
            critico = (a + b) / 2
        folga = (critico - x) / x if (x and np.isfinite(critico)) else float("nan")
        linhas.append({"Variável": var, "Rótulo": rotulo(var), "Valor base": x,
                       "Valor crítico (VPL = 0)": critico, "Folga relativa": folga})
    return pd.DataFrame(linhas)


def cenarios(cfg: EVTEASConfig) -> pd.DataFrame:
    """Cenários pessimista e otimista: cada premissa incerta no extremo desfavorável (ou
    favorável) da sua distribuição; o sentido é dado pelo efeito marginal sobre o VPL."""
    from .ponderacao import classificar
    base = motor(cfg, None, 1)
    vpl_base = float(base["economico"]["vpl"][0])
    pess, otim = {}, {}
    for caminho, d in cfg.distribuicoes.items():
        x = float(obter_por_caminho(cfg, caminho))
        delta = _vpl_com(cfg, caminho, x * 1.01 if x else 0.01) - vpl_base
        favoravel_max = delta >= 0
        pess[caminho] = np.array([d.minimo if favoravel_max else d.maximo])
        otim[caminho] = np.array([d.maximo if favoravel_max else d.minimo])
    linhas = []
    for nome, ov in (("Pessimista", pess), ("Caso-base", None), ("Otimista", otim)):
        r = motor(cfg, ov, 1)
        e, s, a, i = r["economico"], r["social"], r["ambiental"], r["indice"]
        dec = classificar(cfg, float(e["vpl"][0]), float(i["indice_evteas"][0]), float(s["lso_0_100"]),
                          a["vetos_ambientais"])
        linhas.append({"Cenário": nome, "VPL": float(e["vpl"][0]), "TIR a.a.": float(e["tir_aa"][0]),
                       "Índice EVTEAS": float(i["indice_evteas"][0]), "Classificação": dec["classificacao"]})
    return pd.DataFrame(linhas)

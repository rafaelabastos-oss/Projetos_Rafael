"""Tratamento da incerteza: Monte Carlo, sensibilidade, valores críticos e cenários."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import (FAIXAS_AACE, VARIAVEIS_ESTOCASTICAS, Distribuicao, EVTEASConfig, definir_por_caminho,
                     obter_por_caminho)
from .financeiro import percentis


def distribuicoes_efetivas(cfg: EVTEASConfig) -> Dict[str, Distribuicao]:
    d = dict(cfg.monte_carlo.distribuicoes)
    if cfg.monte_carlo.incluir_capex_aace and "economico.capex_fator" not in d:
        lo, hi = FAIXAS_AACE.get(int(cfg.economico.classe_estimativa_aace), FAIXAS_AACE[5])
        d["economico.capex_fator"] = Distribuicao("triangular", 1 + lo, 1.0, 1 + hi)
    for caminho, dist in d.items():
        obter_por_caminho(cfg, caminho)  # valida o caminho
        if caminho not in VARIAVEIS_ESTOCASTICAS:
            raise ValueError(f"Distribuição em '{caminho}', parâmetro que o modelo não amostra no Monte Carlo. "
                             f"Parâmetros aceitos: {', '.join(VARIAVEIS_ESTOCASTICAS)}")
        dist.validar()
    return d


def amostrar(cfg: EVTEASConfig, n: int, seed: int) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    # ordem fixa (alfabética) => reprodutibilidade independente da ordem de inserção
    return {k: dist.amostrar(rng, n) for k, dist in sorted(distribuicoes_efetivas(cfg).items())}


def monte_carlo(cfg: EVTEASConfig, n: Optional[int] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    from .pipeline import motor  # import tardio (evita ciclo)

    n = int(n or cfg.monte_carlo.iteracoes)
    seed = int(cfg.monte_carlo.seed if seed is None else seed)
    entradas = amostrar(cfg, n, seed)
    r = motor(cfg, entradas, n)
    eco, tec, amb, idx = r["economico"], r["tecnico"], r["ambiental"], r["indice"]
    tma = cfg.economico.tma_aa_pct / 100

    amostra = pd.DataFrame({k: v for k, v in entradas.items()})
    amostra["VPL"] = eco["vpl"]
    amostra["TIR_aa"] = eco["tir_anual"]
    amostra["Diagnostico_TIR"] = eco["diagnostico_tir"]
    amostra["Payback_desc_meses"] = eco["payback_descontado_meses"]
    amostra["IL"] = eco["indice_lucratividade"]
    amostra["VPL_beneficiario"] = eco["vpl_beneficiario"]
    amostra["ROI_anual"] = eco["roi_anual_regime"]
    amostra["Producao_kg_ano"] = tec["producao_kg_ano"]
    amostra["OEE"] = tec["oee"]
    amostra["PH_cinza_m3_t"] = amb["ph_cinza_m3_t"]
    amostra["Intensidade_kgCO2e_kg"] = amb["intensidade_carbono_kgco2e_kg"]
    amostra["Indice_EVTEAS"] = idx["indice_evteas"]

    v = amostra["VPL"].to_numpy()
    p5 = np.percentile(v, 5)
    media, dp = float(v.mean()), float(v.std(ddof=1))
    erro = dp / np.sqrt(n)
    tir_valida = amostra["TIR_aa"].to_numpy()
    tir_valida = tir_valida[np.isfinite(tir_valida)]
    estat = {
        "n": n, "seed": seed,
        "media_vpl": media, "mediana_vpl": float(np.median(v)), "desvio_vpl": dp,
        "variancia_vpl": dp ** 2, "cv_vpl": dp / abs(media) if media else float("nan"),
        "ic95_media_vpl": (media - 1.96 * erro, media + 1.96 * erro),
        "prob_vpl_negativo": float((v < 0).mean()),
        "prob_vpl_positivo": float((v > 0).mean()),
        "prob_tir_maior_tma": float((amostra["TIR_aa"] > tma).mean()),
        "media_vpl_beneficiario": float(amostra["VPL_beneficiario"].mean()),
        "prob_vpl_beneficiario_positivo": float((amostra["VPL_beneficiario"] > 0).mean()),
        "fracao_tir_indefinida": float((~np.isfinite(amostra["TIR_aa"])).mean()),
        "var5_vpl": float(p5),
        "cvar5_vpl": float(v[v <= p5].mean()),
        "percentis_vpl": percentis(v),
        "percentis_tir": percentis(tir_valida),
        "percentis_payback_desc": percentis(amostra["Payback_desc_meses"]),
        "percentis_indice": percentis(amostra["Indice_EVTEAS"]),
        "media_indice": float(amostra["Indice_EVTEAS"].mean()),
        "prob_indice_maior_limiar": float((amostra["Indice_EVTEAS"] >= cfg.decisao.limiar_indice_viavel).mean()),
    }
    # Convergência: média acumulada e erro-padrão em pontos de controle
    pontos = sorted({int(x) for x in np.unique(np.geomspace(100, n, num=12).astype(int)) if x <= n} | {n})
    conv = pd.DataFrame([{"Iterações": k, "Média VPL": float(v[:k].mean()),
                          "Erro-padrão": float(v[:k].std(ddof=1) / np.sqrt(k)),
                          "P(VPL>0)": float((v[:k] > 0).mean())} for k in pontos])
    # Importância: correlação de postos (Spearman) entre entradas e saídas
    ranks = amostra[list(entradas) + ["VPL", "Indice_EVTEAS"]].rank()
    constantes = [k for k in ranks if ranks[k].nunique() <= 1]
    ranks[constantes] = np.nan       # correlação indefinida para entradas sem variação
    imp = pd.DataFrame({
        "Variável": list(entradas),
        "Spearman com VPL": [float(ranks[k].corr(ranks["VPL"])) for k in entradas],
        "Spearman com Índice": [float(ranks[k].corr(ranks["Indice_EVTEAS"])) for k in entradas],
    })
    imp = imp.reindex(imp["Spearman com VPL"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    return {"amostra": amostra, "estatisticas": estat, "convergencia": conv, "importancia": imp,
            "distribuicoes": {k: vars(d) for k, d in distribuicoes_efetivas(cfg).items()}}


# ---------------------------------------------------------------------------
# Sensibilidade determinística (um fator por vez)
# ---------------------------------------------------------------------------

VARIAVEIS_SENSIBILIDADE = [
    "economico.preco_venda_kg", "tecnico.fcr", "economico.custo_racao_kg", "tecnico.mortalidade_pct",
    "tecnico.desempenho_crescimento_pct", "economico.capex_fator", "economico.custos_fixos_fator",
    "economico.tarifa_energia_kwh", "economico.custo_alevino_milheiro", "economico.tma_aa_pct",
]


def _vpl_com(cfg: EVTEASConfig, caminho: str, valor: float) -> float:
    from .pipeline import motor
    if caminho == "economico.tma_aa_pct":
        c = copy.deepcopy(cfg)
        definir_por_caminho(c, caminho, valor)
        return float(motor(c, None, 1)["economico"]["vpl"][0])
    return float(motor(cfg, {caminho: np.array([valor])}, 1)["economico"]["vpl"][0])


def sensibilidade(cfg: EVTEASConfig, variaveis: Optional[List[str]] = None,
                  amplitudes=(0.10, 0.20)) -> pd.DataFrame:
    variaveis = variaveis or VARIAVEIS_SENSIBILIDADE
    from .pipeline import motor
    base = float(motor(cfg, None, 1)["economico"]["vpl"][0])
    linhas = []
    for var in variaveis:
        x = float(obter_por_caminho(cfg, var))
        for amp in amplitudes:
            d = abs(x) * amp if x != 0 else amp
            lo, hi = _vpl_com(cfg, var, x - d), _vpl_com(cfg, var, x + d)
            elasticidade = ((hi - lo) / base) / (2 * d / x) if (base and x) else float("nan")
            linhas.append({"Variável": var, "Amplitude": amp, "Valor base": x, "VPL base": base,
                           "VPL (−)": lo, "VPL (+)": hi, "Δ VPL (−)": lo - base, "Δ VPL (+)": hi - base,
                           "Amplitude do efeito": abs(hi - lo),
                           "Δ VPL por 1% da variável": (hi - lo) / (2 * amp * 100),
                           "Elasticidade": elasticidade})
    df = pd.DataFrame(linhas)
    ordem = df[df["Amplitude"] == amplitudes[0]].sort_values("Amplitude do efeito", ascending=False)["Variável"]
    df["_o"] = df["Variável"].map({v: i for i, v in enumerate(ordem)})
    return df.sort_values(["_o", "Amplitude"]).drop(columns="_o").reset_index(drop=True)


def valores_criticos(cfg: EVTEASConfig, variaveis: Optional[List[str]] = None) -> pd.DataFrame:
    """Valor de cada variável que zera o VPL (demais premissas nos valores informados)."""
    variaveis = variaveis or [v for v in VARIAVEIS_SENSIBILIDADE if v != "economico.tma_aa_pct"]
    linhas = []
    for var in variaveis:
        x = float(obter_por_caminho(cfg, var))
        a, b = 0.0, max(x * 5, 1.0)
        fa, fb = _vpl_com(cfg, var, a), _vpl_com(cfg, var, b)
        if var == "tecnico.mortalidade_pct":
            b = 99.0
            fb = _vpl_com(cfg, var, b)
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
        linhas.append({"Variável": var, "Valor base": x, "Valor crítico (VPL = 0)": critico,
                       "Folga relativa": folga})
    return pd.DataFrame(linhas)


def cenarios(cfg: EVTEASConfig) -> pd.DataFrame:
    """Cenários pessimista, base e otimista a partir dos extremos das distribuições."""
    from .pipeline import motor
    dists = distribuicoes_efetivas(cfg)
    base = motor(cfg, None, 1)["economico"]["vpl"][0]
    pess, otim = {}, {}
    for k, d in dists.items():
        vmin = _vpl_com(cfg, k, d.minimo) if k != "economico.tma_aa_pct" else base
        vmax = _vpl_com(cfg, k, d.maximo) if k != "economico.tma_aa_pct" else base
        favoravel_max = vmax >= vmin
        pess[k] = np.array([d.minimo if favoravel_max else d.maximo])
        otim[k] = np.array([d.maximo if favoravel_max else d.minimo])
    linhas = []
    for nome, ov in (("Pessimista", pess), ("Base", None), ("Otimista", otim)):
        r = motor(cfg, ov, 1)
        e, i = r["economico"], r["indice"]
        linhas.append({"Cenário": nome, "VPL": float(e["vpl"][0]), "TIR a.a.": float(e["tir_anual"][0]),
                       "Payback descontado (meses)": float(e["payback_descontado_meses"][0]),
                       "Produção (kg/ano)": float(r["tecnico"]["producao_kg_ano"][0]),
                       "Índice EVTEAS": float(i["indice_evteas"][0])})
    return pd.DataFrame(linhas)

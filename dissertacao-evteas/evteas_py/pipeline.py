"""EVTEAS-Py — módulo pipeline.

Ponto único de entrada para execução reprodutível (Etapas 6 e 7 da DSR): valida a configuração,
resolve os pesos, executa o motor das quatro dimensões, monta DRE, curva de crescimento, ODS e
tabela de premissas, habilita Monte Carlo, sensibilidade, valores críticos e cenários, aplica a
regra de decisão e registra a verificação por invariantes.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .config import VERSAO, EVTEASConfig, obter_por_caminho, validar_config
from .modelo import (alinhamento_ods, curva_crescimento, distribuicao_sobras, dre_anual, dre_mensal, motor)
from .ponderacao import KPIS, classificar, resolver_pesos, tabela_normalizacao, topsis


def _escalar(d):
    """Converte vetores de tamanho 1 em escalares (resultado determinístico)."""
    if isinstance(d, dict):
        return {k: _escalar(v) for k, v in d.items()}
    if isinstance(d, np.ndarray):
        if d.ndim == 1 and d.size == 1:
            v = d[0]
            return v.item() if hasattr(v, "item") else v
        if d.ndim == 2 and d.shape[0] == 1:
            return d[0]
    return d


def tabela_premissas(cfg: EVTEASConfig) -> pd.DataFrame:
    """Entradas informadas, com marcador, unidade e origem declarada (rastreabilidade, Seção 3.6)."""
    from .entradas import tabela_entradas
    return tabela_entradas(cfg)


def executar_evteas(cfg: EVTEASConfig, executar_mc: bool = True, executar_sens: bool = True,
                    n_mc: Optional[int] = None) -> Dict[str, Any]:
    if not isinstance(cfg, EVTEASConfig):
        raise TypeError("cfg deve ser uma instância de EVTEASConfig")
    from .entradas import EntradasInvalidas
    problemas = validar_config(cfg)
    if executar_mc and not cfg.distribuicoes:
        problemas.append("[E-D] Nenhuma distribuição de incerteza informada: preencha ao menos uma premissa "
                         "do Quadro de distribuições para executar o Monte Carlo")
    if problemas:
        raise EntradasInvalidas(problemas)
    from .incerteza import cenarios, monte_carlo, sensibilidade, valores_criticos
    from .vv import validar_invariantes

    inicio = time.perf_counter()
    pesos = resolver_pesos(cfg)
    r = motor(cfg, None, 1, pesos)
    df_m = dre_mensal(r["economico"])
    det = {k: _escalar(v) for k, v in r.items()}
    resultado: Dict[str, Any] = {
        "versao": VERSAO,
        "config": asdict(cfg),
        **det,
        "curva_crescimento": curva_crescimento(cfg),
        "dre_mensal": df_m,
        "dre_anual": dre_anual(df_m),
        "fluxo_caixa": r["economico"]["fluxo_caixa"][0],
        "sobras": distribuicao_sobras(cfg, r["economico"]),
        "ods": alinhamento_ods(cfg, r["tecnico"], r["economico"], r["ambiental"], r["social"], r["governanca"]),
        "premissas": tabela_premissas(cfg),
        "normalizacao": tabela_normalizacao(r["indice"]),
    }
    prob = None
    if executar_mc:
        resultado["monte_carlo"] = monte_carlo(cfg, n=n_mc)
        prob = resultado["monte_carlo"]["estatisticas"]["prob_vpl_positivo"]
    if executar_sens:
        resultado["sensibilidade"] = sensibilidade(cfg)
        resultado["valores_criticos"] = valores_criticos(cfg)
        resultado["cenarios"] = cenarios(cfg)
    resultado["decisao"] = classificar(cfg, det["economico"]["vpl"], det["indice"]["indice_evteas"],
                                       det["social"]["lso_0_100"], det["ambiental"]["vetos_ambientais"], prob)
    resultado["vv"] = validar_invariantes(cfg, resultado, r)
    resultado["tempo_execucao_s"] = time.perf_counter() - inicio
    return resultado


CRITERIOS_TOPSIS = [
    ("VPL", "benefício"), ("P(VPL>0)", "benefício"), ("OEE", "benefício"), ("PH cinza (m³/t)", "custo"),
    ("kgCO2e/kg", "custo"), ("LSO", "benefício"), ("RVL (%)", "benefício"),
]


def comparar_alternativas(alternativas: Dict[str, EVTEASConfig], n_mc: Optional[int] = None,
                          pesos_criterios=None) -> pd.DataFrame:
    """Compara alternativas de projeto por TOPSIS (sete critérios), cada uma com Monte Carlo."""
    from .incerteza import monte_carlo
    linhas = []
    for nome, cfg in alternativas.items():
        r = motor(cfg, None, 1)
        mc = monte_carlo(cfg, n=n_mc)
        e, t, a, s, i = r["economico"], r["tecnico"], r["ambiental"], r["social"], r["indice"]
        linhas.append({"Alternativa": nome, "Descrição": cfg.projeto, "VPL": float(e["vpl"][0]),
                       "P(VPL>0)": mc["estatisticas"]["prob_vpl_positivo"], "OEE": float(t["oee"][0]),
                       "PH cinza (m³/t)": float(a["ph_cinza_m3_t"][0]), "kgCO2e/kg": float(a["intensidade_carbono_kg_kg"][0]),
                       "LSO": float(s["lso_0_100"]), "RVL (%)": float(s["rvl_pct"][0]),
                       "Índice": float(i["indice_evteas"][0])})
    df = pd.DataFrame(linhas)
    crit = [c for c, _ in CRITERIOS_TOPSIS]
    sentidos = [s for _, s in CRITERIOS_TOPSIS]
    w = pesos_criterios if pesos_criterios is not None else np.ones(len(crit))
    df["TOPSIS"] = topsis(df[crit].to_numpy(), w, sentidos)
    df = df.sort_values("TOPSIS", ascending=False).reset_index(drop=True)
    df["Posição"] = [f"{k}º" for k in range(1, len(df) + 1)]
    return df

"""Pipeline principal reproduzível do EVTEAS-Py."""
from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .config import EVTEASConfig, VERSAO
from .modelo import (Contexto, alinhamento_ods, calcular_ambiental, calcular_economico, calcular_governanca,
                     calcular_lean_green, calcular_social, calcular_tecnico, curva_crescimento, distribuicao_sobras,
                     dre_anual, dre_mensal)
from .ponderacao import calcular_indice, classificar, resolver_pesos, topsis


def motor(cfg: EVTEASConfig, overrides: Optional[Dict[str, np.ndarray]] = None, n: int = 1,
          pesos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Executa as quatro dimensões e o índice para n realizações das premissas."""
    ctx = Contexto(cfg, overrides, n)
    tec = calcular_tecnico(ctx)
    eco = calcular_economico(ctx, tec)
    amb = calcular_ambiental(ctx, tec, eco)
    soc = calcular_social(ctx, eco)
    gov = calcular_governanca(cfg)
    lean = calcular_lean_green(ctx, tec, eco)
    idx = calcular_indice(cfg, tec, eco, amb, soc, gov, pesos)
    return {"tecnico": tec, "economico": eco, "ambiental": amb, "social": soc,
            "governanca": gov, "lean_green": lean, "indice": idx}


def _escalar(obj, i: int = 0):
    """Extrai a realização i (determinística) de estruturas com vetores."""
    if isinstance(obj, dict):
        return {k: _escalar(v, i) for k, v in obj.items() if k != "_series"}
    if isinstance(obj, np.ndarray):
        if obj.ndim == 1:
            v = obj[i]
            return v.item() if hasattr(v, "item") else v
        return obj
    return obj


def tabela_premissas(cfg: EVTEASConfig) -> pd.DataFrame:
    """Registro de origem de cada premissa (Seção 3.6): valor, fonte e distribuição."""
    from .config import CATEGORIAS_FONTE, caminhos_numericos, obter_por_caminho
    from .incerteza import distribuicoes_efetivas
    dists = distribuicoes_efetivas(cfg)
    linhas = []
    for caminho in caminhos_numericos(cfg) + [k for k in dists if k not in caminhos_numericos(cfg)]:
        fonte = cfg.fontes.get(caminho)
        d = dists.get(caminho)
        linhas.append({
            "Parâmetro": caminho, "Valor": obter_por_caminho(cfg, caminho),
            "Categoria da fonte": CATEGORIAS_FONTE[fonte.categoria] if fonte else CATEGORIAS_FONTE["autor"],
            "Referência": fonte.referencia if fonte else "",
            "Distribuição": d.tipo if d else "determinístico",
            "Mínimo": d.minimo if d else None, "Mais provável": d.moda if d else None, "Máximo": d.maximo if d else None,
        })
    return pd.DataFrame(linhas)


def executar_evteas(cfg: EVTEASConfig, executar_mc: bool = True, executar_sens: bool = True,
                    n_mc: Optional[int] = None) -> Dict[str, Any]:
    if not isinstance(cfg, EVTEASConfig):
        raise TypeError("cfg deve ser uma instância de EVTEASConfig")
    from .incerteza import cenarios, monte_carlo, sensibilidade, valores_criticos
    from .vv import validar_invariantes

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
    return resultado


def comparar_alternativas(alternativas: Dict[str, EVTEASConfig], pesos_criterios: Optional[Dict[str, float]] = None,
                          n_mc: int = 2000) -> Dict[str, Any]:
    """Executa cada alternativa e as ordena por TOPSIS (critérios das quatro dimensões)."""
    from .incerteza import monte_carlo
    criterios = {  # nome: (extrator, benefício?)
        "VPL (R$)": (lambda r, m: r["economico"]["vpl"], True),
        "P(VPL>0)": (lambda r, m: m["estatisticas"]["prob_vpl_positivo"], True),
        "OEE": (lambda r, m: r["tecnico"]["oee"], True),
        "PH cinza (m³/t)": (lambda r, m: r["ambiental"]["ph_cinza_m3_t"], False),
        "Intensidade carbono (kgCO2e/kg)": (lambda r, m: r["ambiental"]["intensidade_carbono_kgco2e_kg"], False),
        "LSO": (lambda r, m: r["social"]["lso_0_100"], True),
        "RVL (%)": (lambda r, m: r["social"]["rvl_pct"], True),
    }
    pesos_criterios = pesos_criterios or {"VPL (R$)": 0.20, "P(VPL>0)": 0.15, "OEE": 0.15,
                                          "PH cinza (m³/t)": 0.15, "Intensidade carbono (kgCO2e/kg)": 0.10,
                                          "LSO": 0.10, "RVL (%)": 0.15}
    linhas, resultados = [], {}
    for nome, cfg in alternativas.items():
        r = executar_evteas(cfg, executar_mc=False, executar_sens=False)
        m = monte_carlo(cfg, n=n_mc)
        resultados[nome] = r
        linha = {"Alternativa": nome}
        for c, (f, _) in criterios.items():
            linha[c] = float(f(r, m))
        linha["Índice EVTEAS"] = r["indice"]["indice_evteas"]
        linha["Classificação"] = classificar(cfg, r["economico"]["vpl"], r["indice"]["indice_evteas"],
                                             r["social"]["lso_0_100"], r["ambiental"]["vetos_ambientais"],
                                             m["estatisticas"]["prob_vpl_positivo"])["classificacao"]
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    nomes = list(criterios)
    # critério indefinido (ex.: pegada por tonelada com produção zero) recebe o pior valor observado
    avisos, matriz = [], df.copy()
    for c in nomes:
        faltam = matriz[c].isna()
        if faltam.any():
            validos = matriz.loc[~faltam, c]
            pior = (validos.min() if criterios[c][1] else validos.max()) if len(validos) else 0.0
            matriz.loc[faltam, c] = pior
            avisos.append(f"{c} indefinido para {', '.join(matriz.loc[faltam, 'Alternativa'])}: adotado o pior valor "
                          "observado no TOPSIS")
    ranking = topsis(matriz, nomes, [pesos_criterios[c] for c in nomes], [criterios[c][1] for c in nomes])
    for c in nomes:                       # a tabela mostra o valor calculado (indefinido continua indefinido)
        ranking[c] = ranking["Alternativa"].map(df.set_index("Alternativa")[c])
    return {"matriz": df, "ranking": ranking, "pesos": pesos_criterios, "resultados": resultados, "avisos": avisos}


def copiar(cfg: EVTEASConfig) -> EVTEASConfig:
    return copy.deepcopy(cfg)

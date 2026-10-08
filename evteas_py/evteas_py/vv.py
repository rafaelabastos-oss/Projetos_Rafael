"""Verificação computacional (Boehm, 1984): invariantes e testes de regressão.

A verificação responde "estamos construindo o produto corretamente?". A
validação junto aos especialistas (Seção 3.3.2) é conduzida fora do código,
mas seus escores Likert entram em ``PesosConfig`` e ficam rastreáveis.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from .config import EVTEASConfig
from .financeiro import payback, tir, vpl


def validar_invariantes(cfg: EVTEASConfig, resultado: Dict[str, Any], bruto: Dict[str, Any] = None) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    def chk(nome: str, ok: bool, detalhe: str = ""):
        checks.append({"Verificação": nome, "Aprovada": bool(ok), "Detalhe": detalhe})

    t, e, a, s, i = (resultado["tecnico"], resultado["economico"], resultado["ambiental"],
                     resultado["social"], resultado["indice"])
    chk("OEE em [0, 1]", 0 <= t["oee"] <= 1, f"OEE = {t['oee']:.4f}")
    chk("OEE = Disponibilidade × Performance × Qualidade",
        abs(t["oee"] - t["disponibilidade"] * t["performance"] * t["qualidade"]) < 1e-12)
    chk("FCR não negativo", t["fcr"] >= 0)
    chk("Ciclos/ano compatíveis com a duração do ciclo",
        cfg.tecnico.ciclos_ano <= 365 / max(cfg.tecnico.ciclo_dias, 1) + 1e-9,
        f"{cfg.tecnico.ciclos_ano} ≤ {365 / cfg.tecnico.ciclo_dias:.2f}")
    chk("Biomassa de despesca ≤ capacidade de suporte",
        t["biomassa_despesca_ciclo_kg"] <= t["volume_util_m3"] * t["capacidade_suporte_kg_m3"] * t["disponibilidade"] + 1e-6)
    chk("Ração = FCR × ganho de biomassa", abs(t["racao_ciclo_kg"] - t["fcr"] * t["ganho_biomassa_ciclo_kg"]) < 1e-6)

    df = resultado["dre_mensal"]
    close = lambda x, y: bool(np.allclose(x, y, rtol=1e-9, atol=1e-6))
    chk("DRE: Receita Líquida = Receita Bruta − Impostos s/ Faturamento",
        close(df["Receita Líquida"], df["Receita Bruta"] - df["Impostos s/ Faturamento"]))
    chk("DRE: Lucro Bruto = Receita Líquida − Custos Variáveis",
        close(df["Lucro Bruto"], df["Receita Líquida"] - df["Custos Variáveis"]))
    chk("DRE: EBITDA = Lucro Bruto − Custos Fixos", close(df["EBITDA"], df["Lucro Bruto"] - df["Custos Fixos"]))
    chk("DRE: Resultado = LAIR − Impostos s/ Lucro", close(df["Resultado Líquido"], df["LAIR"] - df["Impostos s/ Lucro"]))
    chk("Fluxo de caixa operacional = Resultado + Depreciação",
        close(df["Fluxo de Caixa Operacional"], df["Resultado Líquido"] + df["Depreciação"]))
    chk("Conservação de massa: produção vendida ≤ produção em engorda",
        df["Venda (kg)"].sum() <= df["Produção em engorda (kg)"].sum() + 1e-6)

    fc = resultado["fluxo_caixa"]
    chk("VPL recalculado de forma independente", abs(vpl(e["tma_mensal"], fc) - e["vpl"]) < 1e-6)
    if np.isfinite(e["tir_mensal"]):
        chk("VPL na TIR ≈ 0", abs(vpl(e["tir_mensal"], fc)) < 1e-3 * max(1.0, abs(fc[0])), e["diagnostico_tir"])
    else:
        chk("TIR indefinida acompanhada de diagnóstico", e["diagnostico_tir"] == "sem_solucao",
            e["diagnostico_tir"])
    chk("Payback descontado ≥ payback simples (quando ambos existem)",
        not (np.isfinite(e["payback_descontado_meses"]) and np.isfinite(e["payback_simples_meses"]))
        or e["payback_descontado_meses"] >= e["payback_simples_meses"] - 1e-9)

    chk("Balanço de N: aportado ≥ retido", a["n_aportado_kg"] >= a["n_retido_kg"])
    chk("Balanço de P: aportado ≥ retido", a["p_aportado_kg"] >= a["p_retido_kg"])
    chk("Score de conformidade em [0, 10]", 0 <= a["conformidade_0_10"] <= 10)
    chk("Ecoeficiência indefinida somente com valor adicionado ≤ 0",
        (a["ecoeficiencia_status"] == "definida") == (a["valor_adicionado_regime"] > 0))
    chk("LSO em [0, 100]", 0 <= s["lso_0_100"] <= 100)
    chk("Risco social em [0, 1]", 0 <= s["risco_social"] <= 1)

    from .config import obter_por_caminho
    for caminho, d in cfg.monte_carlo.distribuicoes.items():
        v = float(obter_por_caminho(cfg, caminho))
        ok = d.minimo - 1e-9 <= v <= d.maximo + 1e-9 and (d.tipo == "uniforme" or abs(d.moda - v) <= 1e-9 * max(1.0, abs(v)))
        chk(f"Distribuição de {caminho} contém o valor determinístico como mais provável", ok,
            f"valor {v:g}; distribuição {d.tipo} ({d.minimo:g}, {d.moda:g}, {d.maximo:g})")

    pesos = i["pesos"]
    chk("Pesos dimensionais somam 1", abs(sum(pesos["dimensoes"].values()) - 1) < 1e-9)
    chk("Pesos dimensionais não negativos", min(pesos["dimensoes"].values()) >= 0)
    chk("Índice EVTEAS em [0, 1]", 0 <= i["indice_evteas"] <= 1, f"{i['indice_evteas']:.4f}")
    chk("KPIs normalizados em [0, 1]", all(0 <= v <= 1 for v in i["kpis_normalizados"].values()))
    if "ahp" in pesos:
        chk("AHP consistente (RC ≤ 0,10)", pesos["ahp"]["consistente"], f"RC = {pesos['ahp']['rc']:.3f}")

    if "monte_carlo" in resultado:
        mc = resultado["monte_carlo"]
        st = mc["estatisticas"]
        chk("Monte Carlo: P(VPL>0) + P(VPL<0) ≤ 1", st["prob_vpl_positivo"] + st["prob_vpl_negativo"] <= 1 + 1e-12)
        chk("Monte Carlo: P5 ≤ mediana ≤ P95",
            st["percentis_vpl"]["p5"] <= st["mediana_vpl"] <= st["percentis_vpl"]["p95"])
        conv = mc["convergencia"]
        chk("Monte Carlo: erro-padrão final < 2% do desvio-padrão",
            conv["Erro-padrão"].iloc[-1] < 0.02 * st["desvio_vpl"] or st["n"] < 2500,
            f"EP = {conv['Erro-padrão'].iloc[-1]:,.0f}")

    falhas = [c for c in checks if not c["Aprovada"]]
    return {"valido": not falhas, "quantidade_verificacoes": len(checks), "quantidade_erros": len(falhas),
            "erros": [c["Verificação"] for c in falhas], "verificacoes": checks}


def teste_regressao_deterministica() -> bool:
    """Casos com solução analítica conhecida (executáveis sem pytest)."""
    assert abs(vpl(0.0, [-100, 50, 50]) - 0.0) < 1e-12
    assert abs(vpl(0.10, [-100, 110]) - 0.0) < 1e-9
    r, d = tir([-100, 110])
    assert abs(r[0] - 0.10) < 1e-9 and d[0] == "convencional"
    r, d = tir([-100, -10, -10])
    assert np.isnan(r[0]) and d[0] == "sem_solucao"
    assert abs(payback([-100, 40, 40, 40])[0] - 2.5) < 1e-12
    assert np.isnan(payback([-100, 10, 10])[0])
    return True

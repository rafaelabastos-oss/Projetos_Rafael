"""EVTEAS-Py — módulo vv (Verificação e Validação).

Verificação em duas camadas (Boehm, 1984): (1) invariantes conferidos a cada execução e
(2) testes automatizados com casos de solução conhecida, executáveis no próprio notebook.
A validação com especialistas é feita por questionários (Apêndices C e D) após a simulação.
"""
from __future__ import annotations

import math
import traceback
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from .config import EVTEASConfig, safe_div, taxa_anual_para_mensal


def validar_invariantes(cfg: EVTEASConfig, resultado: Dict[str, Any], bruto: Dict[str, Any] = None) -> Dict[str, Any]:
    from .financeiro import vpl as f_vpl
    checks: List[Dict[str, Any]] = []

    def chk(nome: str, ok, detalhe: str = ""):
        checks.append({"Verificação": nome, "Aprovada": bool(ok), "Detalhe": detalhe})

    t, e, a, s, i = (resultado["tecnico"], resultado["economico"], resultado["ambiental"],
                     resultado["social"], resultado["indice"])
    g = lambda d, k: float(np.atleast_1d(np.asarray(d[k], dtype=float))[0])
    # Técnicas (6)
    chk("OEE em [0, 1]", 0 <= g(t, "oee") <= 1, f"OEE = {g(t, 'oee'):.4f}")
    chk("OEE = Disponibilidade × Performance × Qualidade",
        abs(g(t, "oee") - g(t, "disponibilidade") * g(t, "performance") * g(t, "qualidade")) < 1e-12)
    chk("FCR não negativo", g(t, "fcr") >= 0)
    chk("Ciclos/ano compatíveis com a duração do ciclo",
        cfg.tecnico.ciclos_ano <= 365 / max(cfg.tecnico.ciclo_dias, 1) + 1e-9,
        f"{cfg.tecnico.ciclos_ano} ≤ {365 / cfg.tecnico.ciclo_dias:.2f}")
    chk("Biomassa de despesca ≤ capacidade de suporte",
        g(t, "biomassa_despesca_ciclo_kg") <= g(t, "volume_util_m3") * g(t, "capacidade_suporte_kg_m3") * g(t, "disponibilidade") + 1e-6)
    chk("Ração = FCR × ganho de biomassa", abs(g(t, "racao_ciclo_kg") - g(t, "fcr") * g(t, "ganho_biomassa_ciclo_kg")) < 1e-6)

    # Econômicas (10)
    df = resultado["dre_mensal"]
    close = lambda x, y: bool(np.allclose(x, y, rtol=1e-9, atol=1e-6))
    chk("DRE: Receita Líquida = Receita Bruta − Impostos s/ Faturamento",
        close(df["Receita Líquida"], df["Receita Bruta"] - df["Impostos s/ Faturamento"]))
    chk("DRE: Lucro Bruto = Receita Líquida − Custos Variáveis",
        close(df["Lucro Bruto"], df["Receita Líquida"] - df["Custos Variáveis"]))
    chk("DRE: EBITDA = Lucro Bruto − Custos Fixos", close(df["EBITDA"], df["Lucro Bruto"] - df["Custos Fixos"]))
    chk("DRE: Resultado = LAIR − Impostos s/ Lucro", close(df["Resultado Líquido"], df["LAIR"] - df["Impostos s/ Lucro"]))
    chk("Fluxo operacional = Resultado + Depreciação",
        close(df["Fluxo de Caixa Operacional"], df["Resultado Líquido"] + df["Depreciação"]))
    fluxo = np.asarray(resultado["fluxo_caixa"], dtype=float)
    tma_am = float(taxa_anual_para_mensal(cfg.economico.tma_aa_pct / 100))
    vpl_manual = sum(f / (1 + tma_am) ** k for k, f in enumerate(fluxo))
    chk("VPL = recálculo independente (laço explícito)", abs(vpl_manual - e["vpl"]) < 1e-6 * max(1.0, abs(vpl_manual)),
        f"diferença = {abs(vpl_manual - e['vpl']):.2e}")
    tir_am = e["tir_am"]
    if isinstance(tir_am, float) and math.isfinite(tir_am):
        chk("VPL nulo na TIR", abs(float(f_vpl(tir_am, fluxo)[0])) < 1e-3 * max(1.0, abs(fluxo[0])),
            f"VPL(TIR) = {float(f_vpl(tir_am, fluxo)[0]):.2e}")
    else:
        chk("VPL nulo na TIR (TIR indefinida declarada)", e["diagnostico_tir"] == "sem_solucao", str(e["diagnostico_tir"]))
    pbs, pbd = e["payback_simples_meses"], e["payback_descontado_meses"]
    chk("Payback descontado ≥ payback simples", (not math.isfinite(pbd)) or (math.isfinite(pbs) and pbd >= pbs - 1e-9),
        f"simples = {pbs:.1f}; descontado = {pbd:.1f}")
    chk("Sinal do VPL coerente com TIR × TMA",
        (not math.isfinite(e["tir_aa"])) or ((e["vpl"] >= 0) == (e["tir_aa"] >= cfg.economico.tma_aa_pct / 100 - 1e-9))
        or e["diagnostico_tir"] != "convencional")
    chk("Investimento do beneficiário = investimento − fomento",
        abs(e["investimento_beneficiario"] - (e["investimento"] - e["fomento"])) < 1e-6)

    # Ambientais (6)
    chk("Balanço de N: aportado = retido + lançado + removido",
        g(a, "n_aportado_kg") >= g(a, "n_lancado_kg") - 1e-9 and g(a, "n_retido_kg") >= 0)
    chk("Balanço de P: lançado ≤ aportado − retido",
        g(a, "p_lancado_kg") <= max(g(a, "p_aportado_kg") - g(a, "p_retido_kg"), 0) + 1e-9)
    chk("Pegada hídrica cinza = máximo entre N e P",
        abs(g(a, "ph_cinza_m3_t") - max(g(a, "ph_cinza_n_m3_t"), g(a, "ph_cinza_p_m3_t"))) < 1e-6)
    chk("Água consumida (evaporação) ≤ água captada", g(a, "agua_evaporada_m3") <= g(a, "agua_captada_m3_ano") + 1e-6)
    chk("Emissões = ração + energia + diesel",
        abs(g(a, "co2_total_kg") - (g(a, "co2_racao_kg") + g(a, "co2_energia_kg") + g(a, "co2_diesel_kg"))) < 1e-6)
    status = str(np.atleast_1d(a["status_ecoeficiencia"])[0])
    chk("Ecoeficiência coerente com o status declarado",
        (status == "definida") == math.isfinite(g(a, "ecoeficiencia_rs_kgco2e")), status)

    # Sociais e índice (5)
    chk("LSO em [0, 100]", 0 <= s["lso_0_100"] <= 100, f"LSO = {s['lso_0_100']:.1f}")
    chk("Risco social em [0, 1]", 0 <= s["risco_social"] <= 1)
    pesos = i["pesos"]["dimensoes"]
    chk("Pesos dimensionais somam 1", abs(sum(pesos.values()) - 1) < 1e-9, str({k: round(v, 3) for k, v in pesos.items()}))
    chk("Scores e índice em [0, 1]",
        all(0 <= g(i["scores"], d) <= 1 for d in i["scores"]) and 0 <= g(i, "indice_evteas") <= 1,
        f"índice = {g(i, 'indice_evteas'):.4f}")
    chk("Índice = Σ peso × score", abs(g(i, "indice_evteas") - sum(pesos[d] * g(i["scores"], d) for d in pesos)) < 1e-9)

    # Monte Carlo (1)
    if "monte_carlo" in resultado:
        st = resultado["monte_carlo"]["estatisticas"]
        chk("Monte Carlo: P5 ≤ mediana ≤ P95 e P(VPL>0) em [0, 1]",
            st["p5"] <= st["mediana"] <= st["p95"] and 0 <= st["prob_vpl_positivo"] <= 1)
    tabela = pd.DataFrame(checks)
    return {"tabela": tabela, "total": len(tabela), "aprovadas": int(tabela["Aprovada"].sum()),
            "todas_aprovadas": bool(tabela["Aprovada"].all())}


# ---------------------------------------------------------------------------------------------
# Dados sintéticos de teste (verificação do software)
# ---------------------------------------------------------------------------------------------
# ATENÇÃO: os valores abaixo são DADOS SINTÉTICOS usados somente para testar o código (casos com
# resultado conhecido, monotonicidade, reprodutibilidade). Não são entradas do estudo e não devem
# ser citados na dissertação: as entradas do estudo são informadas pelo usuário antes da simulação.
DADOS_SINTETICOS_TESTE = {
    "projeto": "Dados sintéticos de teste", "especie": "Espécie de teste", "sistema_produtivo": "semi-intensivo",
    "area_lamina_m2": "40.000", "profundidade_media_m": "1,4", "numero_tanques": "32", "tanques_ativos": "30",
    "peso_inicial_g": "30", "peso_final_g": "800", "ciclo_dias": "180", "ciclos_ano": "1,8",
    "produtividade_esperada_kg_m2_ciclo": "1,3", "fcr": "1,5", "mortalidade_pct": "10",
    "tipo_organizacao": "cooperativa", "capital_giro": "60000", "valor_residual_pct": "25",
    "fomento_nao_reembolsavel_pct": "70", "preco_venda_kg": "10,50", "custo_racao_kg": "3,10",
    "custo_alevino_milheiro": "280", "tarifa_energia_kwh": "0,75", "outros_variaveis_kg": "0,30",
    "mao_obra_mes": "12000", "encargos_pct": "20", "cooperados_trabalhadores": "6", "perc_sobras_trabalhadores": "100",
    "manutencao_pct_capex_ano": "2", "administrativo_mes": "2500", "seguros_outros_fixos_mes": "1200",
    "tributos_faturamento_pct": "2,3", "tributos_resultado_pct": "0", "tma_aa_pct": "10", "horizonte_anos": "10",
    "rampa_inicial_pct": "70", "rampa_meses": "12", "ano_regime": "3",
    "renovacao_agua_pct_dia": "3", "enchimentos_ano": "1,8", "evaporacao_mm_dia": "3,75", "infiltracao_mm_dia": "0,5",
    "metodo_tratamento": "bacia de sedimentação", "remocao_n_tratamento_pct": "40", "remocao_p_tratamento_pct": "60",
    "proteina_racao_pct": "32", "fosforo_racao_pct": "1", "nitrogenio_peixe_pct": "2,7", "fosforo_peixe_pct": "0,7",
    "classe_corpo_receptor": "classe 2, lótico", "n_max_mg_l": "2,18", "n_natural_mg_l": "0,3", "p_max_mg_l": "0,1",
    "p_natural_mg_l": "0,02", "fonte_energia": "rede", "fracao_renovavel_pct": "0", "consumo_kwh_kg": "0,6",
    "fator_emissao_rede_kg_kwh": "0,0817", "fator_emissao_racao_kgco2e_kg": "1,1", "diesel_l_ano": "600",
    "fator_emissao_diesel_kg_l": "2,68", "distancia_app_m": "50", "distancia_minima_app_m": "30",
    "amb_licenca_ambiental": "sim", "amb_outorga_agua": "sim", "amb_app_respeitada": "sim",
    "amb_tratamento_efluentes": "sim", "amb_monitoramento_agua": "sim", "amb_car": "sim", "amb_plano_residuos": "não",
    "amb_prevencao_escape": "sim", "amb_energia_renovavel": "não",
    "empregos_diretos": "6", "empregos_indiretos": "10", "mao_obra_local_pct": "100", "compras_locais_pct": "25",
    "salario_minimo": "1518", "aderencia_nr": "sim", "programa_capacitacao": "sim", "participacao_mulheres_pct": "33",
    "relacao_comunidade": "parcial", "canais_formais_comunicacao": "sim", "reunioes_comunidade_ano": "6",
    "conflitos_registrados_ano": "1",
    "gov_estatuto_registrado": "sim", "gov_assembleias_regulares": "sim", "gov_conselho_fiscal": "sim",
    "gov_prestacao_contas_publica": "não", "gov_plano_negocios": "sim", "gov_registro_premissas_auditavel": "sim",
    "gov_canal_denuncia": "não",
    "fcr_referencia": "1,4", "mortalidade_referencia_pct": "5", "consumo_kwh_kg_referencia": "0,4",
    "capex_01": "Viveiros; 380.000; 20", "capex_02": "Abastecimento e drenagem; 95.000; 15",
    "capex_03": "Aeradores e quadro elétrico; 85.000; 8", "capex_04": "Galpão e depósito; 90.000; 20",
    "capex_05": "Equipamentos de manejo; 35.000; 5", "capex_06": "Veículo utilitário; 40.000; 10",
    "capex_07": "Licenciamento e projeto; 20.000; 10",
    "dist_preco_venda_kg": "9; 11,5", "dist_custo_racao_kg": "2,8; 3,7", "dist_custo_alevino_milheiro": "230; 350",
    "dist_tarifa_energia_kwh": "0,65; 0,95", "dist_custos_fixos_fator": "0,95; 1,15", "dist_capex_fator": "0,7; 1,5",
    "dist_fcr": "1,3; 1,85", "dist_mortalidade_pct": "5; 20", "dist_desempenho_crescimento_pct": "85; 105",
    "alt_B_nome": "Alternativa sintética B", "alt_B_alteracoes": "fonte_energia = solar; fracao_renovavel_pct = 90; "
    "remocao_n_tratamento_pct = 70; remocao_p_tratamento_pct = 80; amb_energia_renovavel = sim",
    "alt_B_capex_adicional": "Usina solar; 120.000; 25 | Wetland construído; 60.000; 20",
    "alt_C_nome": "Alternativa sintética C", "alt_C_alteracoes": "produtividade_esperada_kg_m2_ciclo = 1,8; "
    "capacidade_suporte_kg_m3 = 1,6; consumo_kwh_kg = 0,85; empregos_diretos = 8",
    "alt_C_capex_adicional": "Aeradores adicionais; 90.000; 8",
}


def config_sintetica_teste():
    """Configuração com os dados sintéticos de teste (somente para a verificação do software)."""
    from .entradas import config_de_formulario
    return config_de_formulario(DADOS_SINTETICOS_TESTE)


# ---------------------------------------------------------------------------------------------
# Testes automatizados (segunda camada da verificação)
# ---------------------------------------------------------------------------------------------
def testes_automatizados(rapido: bool = True) -> pd.DataFrame:
    """Executa a suíte de testes e devolve uma tabela (nome, aprovado, detalhe).

    Pode ser rodada no Colab sem pytest. Com ``rapido=True`` usa menos iterações de Monte Carlo.
    """
    from . import entradas, financeiro, incerteza, interface, modelo, pipeline, ponderacao, relatorios
    from .config import Distribuicao, carregar_config, copiar, salvar_config
    resultados = []

    def teste(nome: str):
        def deco(fn: Callable[[], Any]):
            try:
                det = fn()
                resultados.append({"Teste": nome, "Aprovado": True, "Detalhe": det or ""})
            except Exception as exc:  # noqa: BLE001
                resultados.append({"Teste": nome, "Aprovado": False,
                                   "Detalhe": f"{type(exc).__name__}: {exc} | {traceback.format_exc(limit=2)[-300:]}"})
            return fn
        return deco

    N = 2000 if rapido else 10000

    @teste("VPL com solução analítica (perpetuidade truncada)")
    def _():
        f = [-1000] + [100] * 10
        esperado = -1000 + 100 * (1 - 1.05 ** -10) / 0.05
        assert abs(financeiro.vpl(0.05, f)[0] - esperado) < 1e-9

    @teste("VPL e TIR conferidos com numpy-financial (se instalado)")
    def _():
        try:
            import numpy_financial as npf
        except ImportError:
            return "numpy-financial não instalado: conferido contra solução analítica"
        f = np.array([-805000] + [9000] * 119 + [400000])
        assert abs(financeiro.vpl(0.008, f)[0] - npf.npv(0.008, f)) < 1e-4
        r, d = financeiro.tir(f)
        assert abs(r[0] - npf.irr(f)) < 1e-7 and d[0] == "convencional"

    @teste("TIR de fluxo simples (−100, +110) = 10%")
    def _():
        r, d = financeiro.tir([-100, 110])
        assert abs(r[0] - 0.10) < 1e-10 and d[0] == "convencional"

    @teste("Fluxo sem TIR declara 'sem_solucao' (não força o limite numérico)")
    def _():
        r, d = financeiro.tir([-100, -50, -10])
        assert np.isnan(r[0]) and d[0] == "sem_solucao"

    @teste("Fluxo com duas TIR é diagnosticado como 'multiplas'")
    def _():
        r, d = financeiro.tir([-1600, 10000, -10000])     # raízes em 25% e 400%
        r2, d2 = financeiro.tir([-1600, 10000, -10000], hi=5.0, pontos=400)
        assert d2[0] == "multiplas"

    @teste("Payback simples e descontado")
    def _():
        assert abs(financeiro.payback([-100, 50, 50, 50])[0] - 2.0) < 1e-12
        assert abs(financeiro.payback([-100, 40, 40, 40])[0] - 2.5) < 1e-12
        assert np.isnan(financeiro.payback([-100, 10, 10])[0])
        assert financeiro.payback([-100, 60, 60], 0.10)[0] > financeiro.payback([-100, 60, 60])[0]

    @teste("Pegada hídrica cinza confere com cálculo manual")
    def _():
        cfg = config_sintetica_teste()
        r = modelo.motor(cfg)
        t, a = r["tecnico"], r["ambiental"]
        c = cfg.ambiental
        p_in = t["racao_ano_kg"][0] * c.fosforo_racao_pct / 100
        p_ret = t["ganho_biomassa_ano_kg"][0] * c.fosforo_peixe_pct / 100
        p_lanc = (p_in - p_ret) * (1 - c.remocao_p_tratamento_pct / 100)
        manual_p = p_lanc * 1000 / (c.p_max_mg_l - c.p_natural_mg_l) / (t["producao_ano_kg"][0] / 1000)
        assert abs(a["ph_cinza_p_m3_t"][0] - manual_p) < 1e-6

    @teste("Monte Carlo degenerado na moda reproduz o determinístico")
    def _():
        cfg = config_sintetica_teste()
        cfg.distribuicoes = {k: Distribuicao("triangular", d.mais_provavel, d.mais_provavel, d.mais_provavel)
                             for k, d in cfg.distribuicoes.items()}
        mc = incerteza.monte_carlo(cfg, n=50, seed=1)
        det = modelo.motor(cfg)["economico"]["vpl"][0]
        assert np.allclose(mc["vpl"], det, rtol=0, atol=1e-6)

    @teste("Reprodutibilidade por semente")
    def _():
        cfg = config_sintetica_teste()
        a = incerteza.monte_carlo(cfg, n=500, seed=7)["vpl"]
        b = incerteza.monte_carlo(cfg, n=500, seed=7)["vpl"]
        c = incerteza.monte_carlo(cfg, n=500, seed=8)["vpl"]
        assert np.array_equal(a, b) and not np.array_equal(a, c)

    @teste("Vetos: VPL negativo impede 'VIÁVEL'")
    def _():
        cfg = config_sintetica_teste()
        assert ponderacao.classificar(cfg, -1.0, 0.95, 80, [])["classificacao"] == "NÃO VIÁVEL"

    @teste("Vetos: item ambiental eliminatório e LSO baixa")
    def _():
        cfg = config_sintetica_teste()
        assert ponderacao.classificar(cfg, 1e6, 0.95, 80, ["Licença ambiental"])["classificacao"] == "NÃO VIÁVEL"
        assert ponderacao.classificar(cfg, 1e6, 0.95, 20, [])["classificacao"] == "NÃO VIÁVEL"
        assert ponderacao.classificar(cfg, 1e6, 0.95, 80, [], 0.9)["classificacao"] == "VIÁVEL"
        assert ponderacao.classificar(cfg, 1e6, 0.55, 80, [], 0.9)["classificacao"] == "VIÁVEL COM RESSALVAS"

    @teste("Licença ambiental ausente gera veto no pipeline")
    def _():
        cfg = config_sintetica_teste()
        cfg.ambiental.checklist["licenca_ambiental"] = False
        r = pipeline.executar_evteas(cfg, executar_mc=False, executar_sens=False)
        assert r["decisao"]["classificacao"] == "NÃO VIÁVEL"

    @teste("Normalização: benefício, custo e saturação")
    def _():
        assert ponderacao.normalizar(5, "benefício", 0, 10) == 0.5
        assert ponderacao.normalizar(2.5, "custo", 1, 2.5) == 0.0
        assert ponderacao.normalizar(99, "benefício", 0, 10) == 1.0

    @teste("Pesos Likert somam 1 e concordância é calculada")
    def _():
        k = list(ponderacao.KPIS)
        p = ponderacao.pesos_likert({"A": {x: 4 for x in k}, "B": {x: 2 for x in k}})
        assert abs(sum(p["dimensoes"].values()) - 1) < 1e-12 and abs(p["concordancia_media"] - 0.5) < 1e-12

    @teste("AHP: matriz consistente tem RC ≈ 0 e pesos corretos")
    def _():
        w = np.array([0.4, 0.3, 0.2, 0.1])
        A = w[:, None] / w[None, :]
        p = ponderacao.pesos_ahp(A)
        assert np.allclose(list(p["dimensoes"].values()), w) and p["razao_consistencia"] < 1e-9

    @teste("TOPSIS ordena alternativa dominante em 1º")
    def _():
        c = ponderacao.topsis([[10, 1], [5, 5], [1, 10]], [1, 1], ["benefício", "custo"])
        assert c[0] == 1.0 and c[2] == 0.0

    @teste("Invariantes aprovados com os dados sintéticos de teste")
    def _():
        r = pipeline.executar_evteas(config_sintetica_teste(), executar_mc=True, executar_sens=False, n_mc=500)
        assert r["vv"]["todas_aprovadas"], r["vv"]["tabela"][~r["vv"]["tabela"]["Aprovada"]].to_string()
        return f"{r['vv']['aprovadas']}/{r['vv']['total']} invariantes"

    @teste("Monotonicidade: preço maior aumenta o VPL; FCR maior reduz")
    def _():
        cfg = config_sintetica_teste()
        b = modelo.motor(cfg)["economico"]["vpl"][0]
        assert modelo.motor(cfg, {"economico.preco_venda_kg": np.array([11.0])})["economico"]["vpl"][0] > b
        assert modelo.motor(cfg, {"tecnico.fcr": np.array([1.7])})["economico"]["vpl"][0] < b

    @teste("Mortalidade maior reduz a biomassa despescada (estocagem fixa)")
    def _():
        cfg = config_sintetica_teste()
        a = modelo.motor(cfg)["tecnico"]["biomassa_despesca_ciclo_kg"][0]
        b = modelo.motor(cfg, {"tecnico.mortalidade_pct": np.array([20.0])})["tecnico"]["biomassa_despesca_ciclo_kg"][0]
        assert b < a

    @teste("Valor crítico do preço zera o VPL")
    def _():
        cfg = config_sintetica_teste()
        vc = incerteza.valores_criticos(cfg, ["economico.preco_venda_kg"])
        p = vc["Valor crítico (VPL = 0)"][0]
        assert abs(modelo.motor(cfg, {"economico.preco_venda_kg": np.array([p])})["economico"]["vpl"][0]) < 1.0

    @teste("Fomento aumenta o VPL do beneficiário exatamente no valor aportado")
    def _():
        e = modelo.motor(config_sintetica_teste())["economico"]
        assert abs((e["vpl_beneficiario"][0] - e["vpl"][0]) - e["fomento"][0]) < 1e-6

    @teste("Salvar e carregar configuração em JSON preserva o resultado")
    def _():
        import os
        import tempfile
        cfg = config_sintetica_teste()
        caminho = os.path.join(tempfile.mkdtemp(), "cfg.json")
        salvar_config(cfg, caminho)
        cfg2 = carregar_config(caminho)
        assert abs(modelo.motor(cfg)["economico"]["vpl"][0] - modelo.motor(cfg2)["economico"]["vpl"][0]) < 1e-9

    @teste("Entradas em branco impedem a execução (nenhum valor predefinido)")
    def _():
        cfg = entradas.config_vazia()
        faltam = entradas.entradas_faltantes(cfg)
        assert len(faltam) > 80, len(faltam)
        try:
            pipeline.executar_evteas(cfg, executar_mc=False, executar_sens=False)
        except entradas.EntradasInvalidas as exc:
            return f"{len(exc.erros)} entradas obrigatórias apontadas"
        raise AssertionError("a execução deveria ser bloqueada")

    @teste("Formulário: vírgula decimal, milhar com ponto, sim/não e opção sem acento")
    def _():
        assert entradas.ler_numero("1.234,56") == 1234.56 and entradas.ler_numero("40.000") == 40000
        assert entradas.ler_numero("1,5") == 1.5 and entradas.ler_numero("0.0817") == 0.0817
        assert entradas.ler_bool("Não") is False and entradas.ler_bool("sim") is True
        assert entradas.converter(entradas.POR_VAR["tipo_organizacao"], "associacao") == "associação"
        dados = dict(DADOS_SINTETICOS_TESTE, profundidade_media_m="abc", mortalidade_pct="120")
        cfg, erros = entradas.ler_formulario(dados)
        assert any("E-T04" in e for e in erros) and any("E-T15" in e for e in erros), erros

    @teste("Moda da distribuição deve coincidir com o valor determinístico")
    def _():
        dados = dict(DADOS_SINTETICOS_TESTE, dist_preco_venda_kg="9; 10; 11,5")
        cfg, erros = entradas.ler_formulario(dados)
        assert any("moda" in e for e in erros), erros

    @teste("Planilha de entradas: gerar, preencher e ler reproduz o formulário")
    def _():
        import os
        import tempfile
        cfg = config_sintetica_teste()
        caminho = os.path.join(tempfile.mkdtemp(), "entradas.xlsx")
        entradas.gerar_planilha_entradas(caminho, cfg)
        cfg2 = entradas.config_de_planilha(caminho)
        assert abs(modelo.motor(cfg)["economico"]["vpl"][0] - modelo.motor(cfg2)["economico"]["vpl"][0]) < 1e-6
        vazia = os.path.join(tempfile.mkdtemp(), "vazia.xlsx")
        entradas.gerar_planilha_entradas(vazia)
        try:
            entradas.config_de_planilha(vazia)
        except entradas.EntradasInvalidas:
            return "planilha em branco recusada; planilha preenchida aceita"
        raise AssertionError("planilha em branco deveria ser recusada")

    @teste("Assistente interativo com respostas simuladas")
    def _():
        dados = DADOS_SINTETICOS_TESTE
        respostas = []
        for e in entradas.ENTRADAS:
            if e.metodo:
                continue
            if e.var == "profundidade_media_m":
                respostas += ["abc", "-3"]          # inválidas: devem ser recusadas
            respostas.append(str(dados.get(e.var, "")))
        respostas += [dados[f"capex_{i:02d}"] for i in range(1, 8)] + [""]
        respostas += [dados.get(d[1], "") for d in entradas.DISTRIBUICOES]
        it = iter(respostas)
        cfg = interface.wizard_evteas(entrada=lambda _: next(it), silencioso=True)
        ref = config_sintetica_teste()
        assert abs(modelo.motor(cfg)["economico"]["vpl"][0] - modelo.motor(ref)["economico"]["vpl"][0]) < 1e-6

    @teste("Assistente com configuração-base: Enter mantém os valores")
    def _():
        it = iter([""] * 1000)
        base = config_sintetica_teste()
        cfg = interface.wizard_evteas(entrada=lambda _: next(it), base=base, silencioso=True)
        assert abs(modelo.motor(cfg)["economico"]["vpl"][0] - modelo.motor(base)["economico"]["vpl"][0]) < 1e-9

    @teste("Análise de preços por percentis e curva de demanda")
    def _():
        df = pd.DataFrame({"preco": [9, 10, 11, 12, 13], "quantidade": [1000, 900, 800, 700, 600]})
        r = interface.analise_precos(df, custo_variavel_kg=6.0)
        assert r["sugestoes"]["Mediana (P50)"] == 11 and r["preco_otimo"] is not None

    @teste("Comparação de alternativas por TOPSIS")
    def _():
        alts = entradas.alternativas_de_formulario(config_sintetica_teste(), DADOS_SINTETICOS_TESTE)
        df = pipeline.comparar_alternativas(alts, n_mc=300)
        assert len(df) == 3 and df["TOPSIS"].between(0, 1).all()

    @teste("Exportação (Excel, JSON, Markdown e marcadores)")
    def _():
        import os
        import tempfile
        cfg = config_sintetica_teste()
        r = pipeline.executar_evteas(cfg, n_mc=300)
        d = tempfile.mkdtemp()
        arqs = relatorios.exportar_tudo(r, cfg, d, figuras=False, alternativas=None)
        mk = relatorios.marcadores(r, cfg)
        assert {"E-T03", "E-T03F", "R-E04", "R-M06", "R-I08"} <= set(mk["Marcador"])
        assert all(os.path.exists(p) for p in arqs.values()), arqs
        return f"{len(arqs)} arquivos"

    return pd.DataFrame(resultados)

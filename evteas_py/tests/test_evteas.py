"""Testes automatizados do EVTEAS-Py (verificação — Boehm, 1984)."""
import copy

import numpy as np
import numpy_financial as npf
import pandas as pd
import pytest

from evteas_py import (Distribuicao, classificar, comparar_alternativas, criar_alternativas, criar_config_caso_base,
                       criar_config_legado_rev186, executar_evteas, exemplo_validacao_especialistas, exportar,
                       gerar_graficos, monte_carlo, motor, normalizar, payback, pesos_ahp, pesos_likert,
                       tir, topsis, vpl)
from evteas_py import teste_regressao_deterministica as regressao_embutida
from evteas_py.config import EVTEASConfig, PesosConfig, config_de_dict, config_para_dict
from evteas_py.interface import analisar_precos, carregar_config, salvar_config, wizard_evteas
from evteas_py.modelo import Contexto, calcular_tecnico, curva_crescimento


@pytest.fixture(scope="module")
def cfg():
    return criar_config_caso_base()


@pytest.fixture(scope="module")
def resultado(cfg):
    return executar_evteas(cfg, executar_mc=True, executar_sens=True, n_mc=3000)


# --- Engenharia econômica: comparação com numpy_financial ---------------------------

@pytest.mark.parametrize("taxa,fluxo", [(0.01, [-1000, 100, 200, 300, 400, 500]), (0.0, [-50, 10, 10]),
                                        (0.12, [-250000] + [40000] * 10)])
def test_vpl_igual_numpy_financial(taxa, fluxo):
    assert vpl(taxa, fluxo) == pytest.approx(npf.npv(taxa, fluxo), rel=1e-12)


@pytest.mark.parametrize("fluxo", [[-1000, 100, 200, 300, 400, 500], [-250000] + [40000] * 10, [-100, 60, 60]])
def test_tir_igual_numpy_financial(fluxo):
    r, d = tir(fluxo)
    assert r[0] == pytest.approx(npf.irr(fluxo), abs=1e-8)
    assert d[0] == "convencional"


def test_tir_sem_solucao_nao_vira_limite_numerico():
    r, d = tir([-1000, -10, -10, -10])
    assert np.isnan(r[0]) and d[0] == "sem_solucao"


def test_tir_multiplas_trocas_de_sinal():
    r, d = tir([-100, 230, -132])          # raízes 10% e 20%
    assert d[0] == "multiplas" and r[0] == pytest.approx(0.10, abs=1e-9)


def test_payback_simples_e_descontado():
    assert payback([-100, 40, 40, 40])[0] == pytest.approx(2.5)
    f = [-100, 50, 50, 50]
    assert payback(f, 0.10)[0] > payback(f)[0] == pytest.approx(2.0)
    assert np.isnan(payback([-100, 10, 10])[0])


def test_regressao_embutida():
    assert regressao_embutida()


# --- Dimensão técnica ------------------------------------------------------------------

def test_oee_produto_dos_fatores(resultado):
    t = resultado["tecnico"]
    assert t["oee"] == pytest.approx(t["disponibilidade"] * t["performance"] * t["qualidade"])
    assert t["qualidade"] == pytest.approx(t["sobrevivencia"])     # Quadro 5


def test_racao_igual_fcr_vezes_ganho(resultado):
    t = resultado["tecnico"]
    assert t["racao_ciclo_kg"] == pytest.approx(t["fcr"] * t["ganho_biomassa_ciclo_kg"])


def test_restricao_dupla_de_biomassa(cfg):
    c = copy.deepcopy(cfg)
    c.tecnico.produtividade_esperada_kg_m2_ciclo = 0.0           # só capacidade de suporte
    t1 = calcular_tecnico(Contexto(c))
    c.tecnico.produtividade_esperada_kg_m2_ciclo = 0.5           # área passa a restringir
    t2 = calcular_tecnico(Contexto(c))
    assert t2["biomassa_despesca_ciclo_kg"][0] < t1["biomassa_despesca_ciclo_kg"][0]
    assert t2["restricao_biomassa"] == "produtividade por área"


def test_mortalidade_maior_reduz_producao(cfg):
    r = motor(cfg, {"tecnico.mortalidade_pct": np.array([5.0, 10.0, 20.0])}, 3)
    p = r["tecnico"]["producao_kg_ano"]
    assert p[0] >= p[1] > p[2]


def test_curva_crescimento_reproduz_peso_final(cfg):
    cc = curva_crescimento(cfg, passo_dias=1)
    assert cc["Peso médio (g)"].iloc[-1] == pytest.approx(cfg.tecnico.peso_final_g, rel=1e-9)
    assert cc["Peso médio (g)"].is_monotonic_increasing


# --- Dimensão econômica ----------------------------------------------------------------

def test_vpl_recalculado_do_fluxo(resultado):
    e = resultado["economico"]
    assert vpl(e["tma_mensal"], resultado["fluxo_caixa"]) == pytest.approx(e["vpl"])


def test_receita_comeca_apos_primeira_despesca(resultado):
    df = resultado["dre_mensal"]
    L = resultado["economico"]["meses_ate_despesca"]
    assert (df["Receita Bruta"].iloc[:L] == 0).all() and df["Receita Bruta"].iloc[L] > 0


def test_fomento_aumenta_vpl_do_beneficiario(resultado):
    e = resultado["economico"]
    assert e["vpl_beneficiario"] - e["vpl"] == pytest.approx(e["fomento_nao_reembolsavel"])


def test_preco_maior_aumenta_vpl(cfg):
    r = motor(cfg, {"economico.preco_venda_kg": np.array([9.0, 10.5, 12.0])}, 3)
    assert np.all(np.diff(r["economico"]["vpl"]) > 0)


def test_mix_de_produtos_preco_medio(cfg):
    c = copy.deepcopy(cfg)
    c.economico.mix_produtos = [{"nome": "Inteiro", "participacao_pct": 50, "preco_kg": 10.0},
                                {"nome": "Eviscerado", "participacao_pct": 50, "preco_kg": 12.0}]
    r = motor(c, None, 1)
    assert r["economico"]["preco_medio_kg"][0] == pytest.approx(11.0)


def test_impostos_configurados_por_base(cfg):
    c = copy.deepcopy(cfg)
    c.economico.impostos_configurados = [{"nome": "IRPJ", "aliquota_pct": 15, "base": "lucro"}]
    r0, r1 = motor(cfg, None, 1), motor(c, None, 1)
    assert r1["economico"]["vpl"][0] < r0["economico"]["vpl"][0]
    c.economico.impostos_configurados = [{"nome": "X", "aliquota_pct": 1, "base": "inexistente"}]
    with pytest.raises(ValueError):
        motor(c, None, 1)


# --- Ambiental, social, índice --------------------------------------------------------

def test_pegada_cinza_calculo_manual(resultado, cfg):
    a = resultado["ambiental"]
    esperado = a["p_lancado_kg"] * 1000 / (cfg.ambiental.p_max_mg_l - cfg.ambiental.p_natural_mg_l)
    assert a["ph_cinza_m3_ano"] == pytest.approx(max(esperado, a["n_lancado_kg"] * 1000 /
                                                     (cfg.ambiental.n_max_mg_l - cfg.ambiental.n_natural_mg_l)))


def test_ecoeficiencia_indefinida_quando_va_negativo(cfg):
    r = motor(cfg, {"economico.preco_venda_kg": np.array([1.0])}, 1)
    assert np.isnan(r["ambiental"]["ecoeficiencia_r_por_kgco2e"][0])
    assert r["ambiental"]["ecoeficiencia_status"][0].startswith("não definida")


def test_item_eliminatorio_gera_veto(cfg):
    c = copy.deepcopy(cfg)
    c.ambiental.distancia_app_m = 10.0
    r = executar_evteas(c, executar_mc=False, executar_sens=False)
    assert r["decisao"]["classificacao"] == "NÃO VIÁVEL"
    assert any("Preservação Permanente" in v for v in r["decisao"]["vetos"])


def test_classificacao_regras(cfg):
    assert classificar(cfg, 1.0, 0.7, 80, [], 0.9)["classificacao"] == "VIÁVEL"
    assert classificar(cfg, 1.0, 0.7, 80, [], 0.5)["classificacao"] == "VIÁVEL COM RESSALVAS"
    assert classificar(cfg, -1.0, 0.9, 80, [], 0.9)["classificacao"] == "NÃO VIÁVEL"
    assert classificar(cfg, 1.0, 0.3, 80, [], 0.9)["classificacao"] == "NÃO VIÁVEL"


def test_normalizacao_limites():
    assert normalizar(5, +1, 0, 10) == pytest.approx(0.5)
    assert normalizar(5, -1, 0, 10) == pytest.approx(0.5)
    assert normalizar(50, +1, 0, 10) == 1.0 and normalizar(-5, +1, 0, 10) == 0.0
    assert normalizar(np.nan, +1, 0, 10) == 0.0


def test_indice_entre_zero_e_um(resultado):
    assert 0 <= resultado["indice"]["indice_evteas"] <= 1
    assert sum(resultado["indice"]["pesos"]["dimensoes"].values()) == pytest.approx(1)


# --- Pesos: Likert e AHP ---------------------------------------------------------------

def test_likert_normaliza_e_triangula():
    lk = pesos_likert({"A": {"x": 5, "y": 3, "z": 2}, "B": {"x": 5, "y": 3, "z": 2}})
    assert lk["pesos"]["x"] == pytest.approx(0.5)
    assert sum(lk["pesos"].values()) == pytest.approx(1)
    assert lk["concordancia_media"] == pytest.approx(1)
    with pytest.raises(ValueError):
        pesos_likert({"A": {"x": 6}})


def test_ahp_matriz_consistente():
    w = np.array([0.4, 0.3, 0.2, 0.1])
    A = w[:, None] / w[None, :]
    ahp = pesos_ahp(A)
    assert np.allclose(ahp["pesos"], w) and ahp["rc"] == pytest.approx(0, abs=1e-9)


def test_ahp_rejeita_matriz_nao_reciproca():
    with pytest.raises(ValueError):
        pesos_ahp([[1, 2], [2, 1]])


def test_pipeline_com_pesos_likert_e_ahp(cfg):
    r = executar_evteas(exemplo_validacao_especialistas(cfg), executar_mc=False, executar_sens=False)
    assert r["indice"]["pesos"]["metodo"] == "likert" and r["vv"]["valido"]
    c = copy.deepcopy(cfg)
    c.pesos = PesosConfig(metodo="ahp", ahp_matriz=[[1, 1 / 2, 2, 2], [2, 1, 3, 3], [1 / 2, 1 / 3, 1, 1], [1 / 2, 1 / 3, 1, 1]])
    r = executar_evteas(c, executar_mc=False, executar_sens=False)
    assert r["indice"]["pesos"]["ahp"]["consistente"]


# --- TOPSIS ---------------------------------------------------------------------------

def test_topsis_alternativa_dominante_vence():
    df = pd.DataFrame({"Alt": ["a", "b", "c"], "lucro": [10, 5, 1], "custo": [1, 5, 10]})
    out = topsis(df, ["lucro", "custo"], [0.5, 0.5], [True, False])
    assert out.iloc[0]["Alt"] == "a" and out.iloc[0]["TOPSIS"] == pytest.approx(1.0)


# --- Incerteza ------------------------------------------------------------------------

def test_monte_carlo_reprodutivel(cfg):
    a = monte_carlo(cfg, n=500, seed=7)["amostra"]["VPL"]
    b = monte_carlo(cfg, n=500, seed=7)["amostra"]["VPL"]
    assert np.array_equal(a.to_numpy(), b.to_numpy())


def test_monte_carlo_degenerado_igual_deterministico(cfg):
    """Com distribuições fixas na moda, o Monte Carlo reproduz o caso determinístico
    (o mesmo motor serve às duas camadas — corrige a divergência da Rev. 186)."""
    c = copy.deepcopy(cfg)
    c.monte_carlo.distribuicoes = {k: Distribuicao("fixa", d.moda, d.moda, d.moda)
                                   for k, d in c.monte_carlo.distribuicoes.items()}
    c.monte_carlo.incluir_capex_aace = False
    mc = monte_carlo(c, n=50)
    det = executar_evteas(c, executar_mc=False, executar_sens=False)
    assert np.allclose(mc["amostra"]["VPL"], det["economico"]["vpl"])


def test_distribuicoes_invalidas():
    with pytest.raises(ValueError):
        Distribuicao("triangular", 1, 5, 3).validar()
    with pytest.raises(ValueError):
        Distribuicao("lognormal", 1, 2, 3).validar()
    rng = np.random.default_rng(1)
    x = Distribuicao("uniforme", 2, 2, 4).amostrar(rng, 1000)
    assert x.min() >= 2 and x.max() <= 4
    y = Distribuicao("normal", 0, 5, 10).amostrar(rng, 1000)
    assert y.min() >= 0 and y.max() <= 10


def test_sensibilidade_e_valores_criticos(resultado, cfg):
    s = resultado["sensibilidade"]
    assert s.iloc[0]["Variável"] == "economico.preco_venda_kg"
    vc = resultado["valores_criticos"].set_index("Variável")
    p = vc.loc["economico.preco_venda_kg", "Valor crítico (VPL = 0)"]
    assert motor(cfg, {"economico.preco_venda_kg": np.array([p])}, 1)["economico"]["vpl"][0] == pytest.approx(0, abs=1.0)


def test_cenarios_ordenados(resultado):
    c = resultado["cenarios"].set_index("Cenário")["VPL"]
    assert c["Pessimista"] < c["Base"] < c["Otimista"]


# --- V&V, regressão do preset legado e alternativas -------------------------------------

def test_invariantes_aprovados(resultado):
    assert resultado["vv"]["valido"], resultado["vv"]["erros"]


def test_preset_legado_rev186():
    r = executar_evteas(criar_config_legado_rev186(), executar_mc=True, executar_sens=False, n_mc=2000)
    assert r["economico"]["vpl"] < -5e6
    assert r["economico"]["diagnostico_tir"] == "sem_solucao" and np.isnan(r["economico"]["tir_anual"])
    assert r["monte_carlo"]["estatisticas"]["prob_vpl_positivo"] == 0
    assert r["decisao"]["classificacao"] == "NÃO VIÁVEL"


def test_comparar_alternativas():
    comp = comparar_alternativas(criar_alternativas(), n_mc=300)
    assert set(comp["ranking"]["Alternativa"]) == {"A", "B", "C"}
    assert comp["ranking"]["TOPSIS"].between(0, 1).all()


# --- Entradas e saídas ----------------------------------------------------------------

def test_config_json_ida_e_volta(cfg, tmp_path):
    p = salvar_config(cfg, tmp_path / "cfg.json")
    c2 = carregar_config(p)
    assert config_para_dict(c2) == config_para_dict(cfg)
    assert isinstance(config_de_dict(config_para_dict(cfg)), EVTEASConfig)


def test_wizard_aceita_enter_para_manter_valores(cfg):
    respostas = iter([""] * 500)
    c = wizard_evteas(entrada=lambda _: next(respostas), base=copy.deepcopy(cfg))
    assert config_para_dict(c) == config_para_dict(cfg)


def test_wizard_altera_valores(cfg):
    respostas = iter(["Projeto X", "", "50000"] + [""] * 500)
    c = wizard_evteas(entrada=lambda _: next(respostas), base=copy.deepcopy(cfg))
    assert c.projeto == "Projeto X" and c.tecnico.area_lamina_m2 == 50000


def test_analise_precos():
    rng = np.random.default_rng(0)
    p = rng.uniform(8, 12, 60)
    df = pd.DataFrame({"preco": p, "qtd": 1000 - 60 * p + rng.normal(0, 5, 60)})
    out = analisar_precos(df, "preco", "qtd", custo_unitario=6.0)
    assert out["demanda"]["inclinacao"] < 0
    assert out["preco_otimo"] == pytest.approx((6.0 + 1000 / 60) / 2, rel=0.05)


def test_exportacao_e_graficos(resultado, tmp_path):
    arquivos = exportar(resultado, tmp_path)
    assert all((tmp_path / f).exists() or __import__("os").path.exists(f) for f in arquivos)
    figs = gerar_graficos(resultado, tmp_path / "fig")
    assert len(figs) >= 6

"""Testes da dimensão social, da governança, dos ODS e do Lean-Green.

A matriz de rastreabilidade da DSR (evteas_py.dsr) mostrou que os requisitos R07 e
R08 tinham funções implementadas, mas sem teste dedicado; estes testes fecham a lacuna.
"""
import copy
import math

import pytest

from evteas_py import criar_config_caso_base, motor
from evteas_py.modelo import energia_kwh_kg


@pytest.fixture
def cfg():
    return criar_config_caso_base()


def test_rvl_segue_formula_do_quadro_5(cfg):
    """RVL = (mão de obra local + fornecedores locais) / custo operacional total."""
    r = motor(cfg, None, 1)
    e, s = r["economico"], r["social"]
    opex = e["custos_variaveis_regime"][0] + e["custos_fixos_regime"][0]
    compras = opex - e["pessoal_regime"][0]
    esperado = 100 * (s["massa_salarial_anual"][0] * cfg.social.mao_obra_local_pct / 100
                      + compras * cfg.social.compras_locais_pct / 100) / opex
    assert s["rvl_pct"][0] == pytest.approx(esperado)
    # sem mão de obra nem compras locais, nada é retido
    c = copy.deepcopy(cfg)
    c.social.mao_obra_local_pct, c.social.compras_locais_pct = 0.0, 0.0
    assert motor(c, None, 1)["social"]["rvl_pct"][0] == pytest.approx(0.0)
    # a receita não entra na RVL (o denominador é o custo operacional)
    c = copy.deepcopy(cfg)
    c.economico.preco_venda_kg *= 1.2
    for p in c.economico.mix_produtos:
        p["preco_kg"] = p.get("preco_kg", 0) * 1.2
    assert motor(c, None, 1)["social"]["rvl_pct"][0] == pytest.approx(s["rvl_pct"][0], rel=1e-6)


def test_lso_e_risco_social(cfg):
    s = motor(cfg, None, 1)["social"]
    # parcial (0,5), canais (1), 6/12 reuniões (0,5), 1 conflito (e^-0,5), assembleias (1)
    esperado = 100 * (0.5 + 1 + 0.5 + math.exp(-0.5) + 1) / 5
    assert s["lso_0_100"][0] == pytest.approx(esperado)
    assert s["risco_social"][0] == pytest.approx(1 / (1 + math.exp(8 * (esperado / 100 - 0.5))))

    c = copy.deepcopy(cfg)
    c.social.relacao_comunidade, c.social.reunioes_comunidade_ano, c.social.conflitos_registrados_ano = "consolidado", 12, 0
    alto = motor(c, None, 1)["social"]
    assert alto["lso_0_100"][0] == pytest.approx(100.0)
    c.social.relacao_comunidade, c.social.canais_formais_comunicacao = "inexistente", False
    c.social.reunioes_comunidade_ano, c.social.conflitos_registrados_ano = 0, 50
    c.governanca.itens["assembleias_regulares"] = False
    baixo = motor(c, None, 1)["social"]
    assert baixo["lso_0_100"][0] == pytest.approx(0.0, abs=1e-6)
    assert alto["risco_social"][0] < 0.05 < 0.95 < baixo["risco_social"][0]
    c.social.relacao_comunidade = "boa"
    with pytest.raises(ValueError, match="relacao_comunidade"):
        motor(c, None, 1)


def test_governanca_e_ods(cfg):
    from evteas_py import executar_evteas
    r = executar_evteas(cfg, executar_mc=False, executar_sens=False)
    assert r["governanca"]["score_0_1"] == pytest.approx(5 / 7)
    ods = r["ods"].set_index("ODS")["Atendido"]
    assert ods["ODS 16 — Instituições eficazes"] and not ods["ODS 7 — Energia limpa"]

    c = copy.deepcopy(cfg)
    c.ambiental.fonte_energia = "solar"
    c.governanca.itens = {k: False for k in c.governanca.itens}
    r2 = executar_evteas(c, executar_mc=False, executar_sens=False)
    ods2 = r2["ods"].set_index("ODS")["Atendido"]
    assert r2["governanca"]["score_0_1"] == 0
    assert ods2["ODS 7 — Energia limpa"] and not ods2["ODS 16 — Instituições eficazes"]


def test_lean_green_zerado_na_referencia(cfg):
    c = copy.deepcopy(cfg)
    c.tecnico.fcr = c.tecnico.fcr_referencia
    c.tecnico.mortalidade_pct = c.tecnico.mortalidade_referencia_pct
    c.ambiental.energia_referencia_kwh_kg = energia_kwh_kg(c)
    lg = motor(c, None, 1)["lean_green"]
    assert lg["total_r_ano"][0] == pytest.approx(0.0, abs=1e-6)
    assert all(v[0] == pytest.approx(0.0, abs=1e-6) for v in lg["desperdicios_r_ano"].values())


def test_lean_green_racao_excedente(cfg):
    r = motor(cfg, None, 1)
    t, lg = r["tecnico"], r["lean_green"]
    excedente = (cfg.tecnico.fcr - cfg.tecnico.fcr_referencia) * t["ganho_biomassa_ano_kg"][0] \
        * r["economico"]["fator_volume_regime"][0]
    assert lg["racao_excedente_kg"][0] == pytest.approx(excedente)
    assert lg["desperdicios_r_ano"]["Ração excedente (superalimentação/FCR)"][0] == \
        pytest.approx(excedente * cfg.economico.custo_racao_kg)
    # desperdício maior com FCR pior
    c = copy.deepcopy(cfg)
    c.tecnico.fcr += 0.2
    assert motor(c, None, 1)["lean_green"]["total_r_ano"][0] > lg["total_r_ano"][0]

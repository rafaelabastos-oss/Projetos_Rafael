"""Testes de regressão dos problemas apontados na revisão independente da entrada de dados."""
import copy

import numpy as np
import pytest

from evteas_py import criar_config_caso_base, executar_evteas, iniciar_entradas, monte_carlo, salvar_config, wizard_evteas
from evteas_py.config import Distribuicao, PesosConfig
from evteas_py.interface import BLOCOS, Perguntador, expandir_blocos
from evteas_py.modelo import Contexto, calcular_tecnico, dre_mensal
from evteas_py.pipeline import motor
from evteas_py.ponderacao import resolver_pesos

from usuario_simulado import UsuarioSimulado


def _corrigir(cfg, bloco, regras):
    """Abre o arquivo de entradas, corrige um bloco e confirma a execução."""
    u = UsuarioSimulado(regras + [(r".*", "")], padrao_falha=False)
    return wizard_evteas(entrada=u.entrada, base=copy.deepcopy(cfg), saida=u.saida, blocos=[bloco]), u


def test_corrigir_preco_reposiciona_distribuicao():
    cfg = criar_config_caso_base()
    novo, u = _corrigir(cfg, "Mix e receitas", [(r"^\s+Preço de venda", "12")])
    d = novo.monte_carlo.distribuicoes["economico.preco_venda_kg"]
    assert d.moda == pytest.approx(12.0)
    assert d.minimo == pytest.approx(9.0 * 12 / 10.5) and d.maximo == pytest.approx(11.5 * 12 / 10.5)
    assert any("reposicionada" in t for t in u.transcricao)
    assert executar_evteas(novo, executar_mc=False, executar_sens=False)["vv"]["valido"]


def test_distribuicao_do_alevino_em_reais_por_unidade():
    cfg = criar_config_caso_base()
    regras = [(r"Tipo de distribuição", "1"), (r"^\s+Mínimo", "0,25"), (r"^\s+Máximo", "0,31")]
    u = UsuarioSimulado(regras, padrao_falha=False)
    P = Perguntador(u.entrada, u.saida, "novo")
    from evteas_py.interface import _perguntar_distribuicao
    d = _perguntar_distribuicao(P, cfg, "economico.custo_alevino_milheiro", "Custo do alevino (R$/unidade)", None, 1 / 1000)
    assert (d.minimo, d.moda, d.maximo) == pytest.approx((250.0, 280.0, 310.0))


def test_alevinos_acompanham_volume_de_vendas_e_crescimento():
    cfg = criar_config_caso_base()
    base = motor(cfg, None, 1)["economico"]["custo_alevinos_regime"][0]
    c = copy.deepcopy(cfg)
    c.economico.producao_vendas_kg_mes = 2 * float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
    assert motor(c, None, 1)["economico"]["custo_alevinos_regime"][0] == pytest.approx(2 * base)
    c = copy.deepcopy(cfg)
    c.economico.crescimento_vendas_aa_pct = 10.0
    ano = motor(c, None, 1)["economico"]["ano_regime"]
    assert motor(c, None, 1)["economico"]["custo_alevinos_regime"][0] == pytest.approx(base * 1.1 ** (ano - 1))


def test_outros_custos_variaveis_mensais():
    cfg = criar_config_caso_base()
    c = copy.deepcopy(cfg)
    c.economico.outros_custos_variaveis_mes = 1000.0
    a, b = dre_mensal(motor(c, None, 1)["economico"]), dre_mensal(motor(cfg, None, 1)["economico"])
    dif = (a["Outros Custos Variáveis"] - b["Outros Custos Variáveis"]).to_numpy()
    assert dif[-1] == pytest.approx(1000.0) and dif[0] == pytest.approx(1000.0 * cfg.economico.capacidade_inicial_pct / 100)


def test_valores_em_reais_nao_mudam_com_o_capex():
    cfg = criar_config_caso_base()
    cfg.economico.manutencao_mes, cfg.economico.valor_residual_rs = 1241.67, 223500.0
    c = copy.deepcopy(cfg)
    c.economico.capex_itens["Novo item"] = 100000.0
    a, b = dre_mensal(motor(c, None, 1)["economico"]), dre_mensal(motor(cfg, None, 1)["economico"])
    # custos fixos iguais (manutenção em R$); só a depreciação muda
    assert np.allclose(a["Custos Fixos"], b["Custos Fixos"])
    assert motor(c, None, 1)["economico"]["fluxo_caixa"][0][-1] - motor(cfg, None, 1)["economico"]["fluxo_caixa"][0][-1] \
        == pytest.approx(a["Fluxo de Caixa Operacional"].iloc[-1] - b["Fluxo de Caixa Operacional"].iloc[-1])


def test_trocar_tipo_de_organizacao_revisa_pessoas_e_tributos():
    assert expandir_blocos(["Identificação"]) == ["Identificação", "Pessoas", "Tributos", "Social e governança"]
    assert expandir_blocos(["Técnico"]) == ["Técnico", "Mix e receitas", "Custos operacionais", "Tributos",
                                            "Projeção e TMA", "Ambiental"]
    cfg = criar_config_caso_base()
    regras = [(r"Tipo de pessoa jurídica", "1"), (r"^Número de funcionários CLT", "1"),
              (r"Cargo do funcionário CLT nº 1", "Técnico"), (r"Salário bruto mensal de 'Técnico", "3000"),
              (r"^Outra mão de obra não detalhada", "0"), (r"^Configurar INSS patronal", "s"),
              (r"Alíquota de INSS patronal", "20"), (r"^Configurar FGTS", "s"), (r"Alíquota de FGTS", "8"),
              (r"^Configurar PIS sobre a folha", "n")]       # encargos novos não têm padrão: precisam de resposta
    novo, _ = _corrigir(cfg, "Identificação", regras)
    e = novo.economico
    assert e.tipo_organizacao == "empresa" and e.retirada_cooperados_mes == 0 and e.cooperados_trabalhadores == 0
    assert sum(i["aliquota_pct"] for i in e.impostos_configurados if i["base"] == "folha_clt") == pytest.approx(28)


def test_likert_de_kpis_ignorado_fora_do_metodo_likert():
    cfg = criar_config_caso_base()
    cfg.pesos = PesosConfig(metodo="preset", likert_kpis={"A": {k: 1 for k in ["oee", "fcr", "produtividade"]}})
    w = resolver_pesos(cfg)["kpi_intra_dimensao"]
    assert w["oee"] == pytest.approx(1 / 3) and "likert_kpis" not in resolver_pesos(cfg)


def test_carencia_zero_permitida():
    cfg = criar_config_caso_base()
    cfg.economico.carencia_automatica, cfg.economico.meses_ate_primeira_receita = False, 0
    df = dre_mensal(motor(cfg, None, 1)["economico"])
    assert df["Receita Bruta"].iloc[0] > 0


def test_carencia_maior_que_horizonte_e_recusada():
    cfg = criar_config_caso_base()
    cfg.economico.carencia_automatica, cfg.economico.meses_ate_primeira_receita = False, 130
    with pytest.raises(ValueError, match="carência"):
        motor(cfg, None, 1)


def test_menu_aace_numero_igual_a_classe():
    cfg = criar_config_caso_base()
    regras = [(r"Detalhar o CAPEX", "n"), (r"Investimento inicial total", "745000"),
              (r"Maturidade da estimativa", "3")]
    novo, u = _corrigir(cfg, "Investimento", regras)
    assert novo.economico.classe_estimativa_aace == 3
    assert any("Classe 1" in t and "1." in t for t in u.transcricao)


def test_ambiental_acompanha_volume_vendido():
    cfg = criar_config_caso_base()
    c = copy.deepcopy(cfg)
    c.economico.producao_vendas_kg_mes = 2 * float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
    a, b = motor(c, None, 1)["ambiental"], motor(cfg, None, 1)["ambiental"]
    assert a["producao_t_ano"][0] == pytest.approx(2 * b["producao_t_ano"][0])
    assert a["co2e_racao_t"][0] == pytest.approx(2 * b["co2e_racao_t"][0])


def test_revisar_preserva_mao_de_obra_mista():
    """Configuração com retirada, mão de obra genérica e tributo sobre a folha genérica."""
    cfg = criar_config_caso_base()
    e = cfg.economico
    e.retirada_cooperados_mes, e.mao_obra_mes, e.encargos_mao_obra_pct = 5000.0, 7000.0, 20.0
    e.impostos_configurados = [{"nome": "INSS retirada", "base": "pro_labore", "aliquota_pct": 20.0},
                               {"nome": "Seguro", "base": "folha", "aliquota_pct": 1.0}]
    respostas = iter([""] * 3000)
    c = wizard_evteas(entrada=lambda _: next(respostas), base=copy.deepcopy(cfg), saida=lambda *a, **k: None)
    assert motor(c, None, 1)["economico"]["vpl"][0] == pytest.approx(motor(cfg, None, 1)["economico"]["vpl"][0], rel=1e-9)


def test_renda_e_rvl_em_precos_do_ano_de_regime():
    cfg = criar_config_caso_base()
    cfg.economico.crescimento_custos_aa_pct = 5.0
    r = motor(cfg, None, 1)
    ano = r["economico"]["ano_regime"]
    esperado = 12000 * 12 * 1.05 ** (ano - 1)
    assert r["social"]["massa_salarial_anual"][0] == pytest.approx(esperado)

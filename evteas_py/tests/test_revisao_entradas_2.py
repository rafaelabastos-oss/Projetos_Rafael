"""Testes de regressão da segunda rodada de revisão independente da entrada de dados."""
import copy
import json

import numpy as np
import pytest

from evteas_py import (comparar_alternativas, criar_config_caso_base, criar_config_caso_controle, executar_evteas,
                       iniciar_entradas, motor, salvar_config, wizard_evteas)
from evteas_py.config import Distribuicao
from evteas_py.incerteza import distribuicoes_efetivas
from evteas_py.interface import (EntradaCancelada, Perguntador, _fmt, _perguntar_distribuicao, carregar_config,
                                 converter_numero, ler_entradas, nome_arquivo)

from usuario_simulado import UsuarioCasoBase, UsuarioSimulado


def _vpl(cfg):
    return motor(cfg, None, 1)["economico"]["vpl"][0]


# --- números no padrão brasileiro ------------------------------------------------------------

def test_ponto_de_milhar_e_formato_sem_notacao_cientifica():
    assert converter_numero("40.000") == 40000 and converter_numero("R$ 400.000") == 400000
    assert converter_numero("1.234.567") == 1234567 and converter_numero("-1.500") == -1500
    assert converter_numero("10.5") == 10.5 and converter_numero("0.280") == pytest.approx(0.28)
    assert _fmt(1500000.0) == "1.500.000" and _fmt(1316250.0) == "1.316.250" and _fmt(0.0817) == "0,0817"
    assert converter_numero(_fmt(60000.0)) == 60000      # o valor exibido entre colchetes pode ser redigitado


def test_wizard_le_milhar_e_avisa():
    u = UsuarioCasoBase([(r"^Área de lâmina", "40.000"), (r"^Volume útil total", "56.000"),
                         (r"Valor de 'Escavação", "400.000")])
    cfg = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=False)
    assert cfg.tecnico.area_lamina_m2 == 40000 and cfg.economico.capex_itens["Escavação e construção de viveiros"] == 400000
    assert _vpl(cfg) == pytest.approx(_vpl(criar_config_caso_base()))
    assert any("ponto como separador de milhar" in t for t in u.transcricao)


def test_digito_unicode_no_menu_nao_quebra():
    respostas = iter(["²", "3"])
    P = Perguntador(lambda _: next(respostas), lambda *a, **k: None)
    assert P.opcao("Menu", [("a", "A"), ("b", "B"), ("c", "C")])[0] == "c"


# --- arquivos de entradas ----------------------------------------------------------------------

def test_arquivo_que_nao_e_de_entradas_e_recusado():
    for dados in ([], {}, {"cells": []}, {"tecnico": {}}):
        with pytest.raises(ValueError, match="não é um arquivo de entradas"):
            ler_entradas(dados)


def test_campos_ausentes_nao_viram_caso_ilustrativo(tmp_path):
    d = json.loads(json.dumps(__import__("dataclasses").asdict(criar_config_caso_base())))
    del d["economico"]["capex_itens"], d["economico"]["tma_aa_pct"], d["tecnico"]["sistema_produtivo"]
    cfg, avisos, pendentes = ler_entradas(d)
    assert {"economico.capex_itens", "economico.tma_aa_pct", "tecnico.sistema_produtivo"} <= set(pendentes)
    p = tmp_path / "x.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="entradas ausentes"):
        carregar_config(p)


def test_arquivo_de_resultados_e_formato_antigo(tmp_path):
    cfg = criar_config_caso_base()
    r = executar_evteas(cfg, executar_mc=False, executar_sens=False)
    from evteas_py.relatorios import serializar
    c2, avisos, pend = ler_entradas(json.loads(json.dumps(serializar({"config": r["config"], "vv": r["vv"]}))))
    assert not pend and "resultados" in avisos[0] and _vpl(c2) == pytest.approx(_vpl(cfg))
    # tributo com 'aliquota' em fração e base com nome antigo; arquivo com BOM (Bloco de Notas)
    d = __import__("dataclasses").asdict(cfg)
    d["economico"]["impostos_configurados"] = [{"nome": "COFINS", "base": "faturamento_bruto", "aliquota": 0.03}]
    p = tmp_path / "antigo.json"
    p.write_text(json.dumps(d), encoding="utf-8-sig")
    c3 = carregar_config(p, avisos=[])
    assert c3.economico.impostos_configurados == [{"nome": "COFINS", "base": "faturamento", "aliquota_pct": 3.0}]


def test_distribuicoes_do_arquivo_sao_reposicionadas_e_filtradas():
    d = __import__("dataclasses").asdict(criar_config_caso_base())
    d["tecnico"]["fcr"] = 1.8                                       # distribuição salva continua em torno de 1,5
    d["monte_carlo"]["distribuicoes"]["economico.tma_aa_pct"] = {"tipo": "triangular", "minimo": 8, "moda": 10, "maximo": 12}
    cfg, avisos, _ = ler_entradas(d)
    dist = cfg.monte_carlo.distribuicoes
    assert dist["tecnico.fcr"].moda == pytest.approx(1.8) and "economico.tma_aa_pct" not in dist
    assert executar_evteas(cfg, executar_mc=True, executar_sens=False, n_mc=200)["vv"]["valido"]


def test_parametro_nao_amostrado_nao_e_aceito_no_monte_carlo():
    cfg = criar_config_caso_base()
    cfg.monte_carlo.distribuicoes["tecnico.peso_final_g"] = Distribuicao("triangular", 600, 800, 900)
    with pytest.raises(ValueError, match="não amostra"):
        distribuicoes_efetivas(cfg)
    with pytest.raises(ValueError, match="não amostra"):
        motor(cfg, {"tecnico.peso_final_g": np.array([600.0, 900.0])}, 2)


# --- interrupções -----------------------------------------------------------------------------

def test_sair_salva_rascunho_que_pode_ser_retomado(tmp_path):
    u = UsuarioCasoBase([(r"^Renovação diária", "sair")])
    with pytest.raises(EntradaCancelada, match="rascunho|salvas") as exc:
        iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=True, pasta_saida=str(tmp_path))
    assert exc.value._render_traceback_()[0].startswith("⚠")
    rascunho = next(tmp_path.glob("*_rascunho.json"))
    cfg, _, pendentes = ler_entradas(json.loads(rascunho.read_text(encoding="utf-8")))
    assert cfg.tecnico.area_lamina_m2 == 40000 and "ambiental.renovacao_pct_dia" in pendentes
    # opção 2: o arquivo com pendências obriga a revisão, e o estudo é concluído
    u2 = UsuarioCasoBase([(r"Como deseja informar os dados", "2"), (r"^Caminho do arquivo", str(rascunho)),
                          (r"^Atualizar a origem", "n"), (r"^Refazer a lista", "n")])
    cfg2 = iniciar_entradas(entrada=u2.entrada, saida=u2.saida, salvar=False)
    assert _vpl(cfg2) == pytest.approx(_vpl(criar_config_caso_base()))


def test_sair_na_correcao_mantem_entradas_e_no_menu_salva(tmp_path):
    u = UsuarioCasoBase([(r"Bloco a corrigir", "5")])
    menus, racao = {"n": 0}, {"n": 0}
    original = u.entrada

    def entrada(prompt):
        if prompt.startswith("Opção (") and "O que deseja fazer" in (u._titulo_menu() or ""):
            menus["n"] += 1
            u.transcricao.append(prompt)
            u.ultimas_saidas = []
            return "2" if menus["n"] == 1 else "sair"      # corrige um bloco; depois digita sair no menu
        if prompt.startswith("Custo da ração"):
            racao["n"] += 1
            return "3,10" if racao["n"] == 1 else "sair"   # desiste no meio da correção
        return original(prompt)
    with pytest.raises(EntradaCancelada, match="salvas"):
        iniciar_entradas(entrada=entrada, saida=u.saida, salvar=True, pasta_saida=str(tmp_path))
    assert menus["n"] == 2 and any("Correção cancelada" in t for t in u.transcricao)
    salvo = carregar_config(next(tmp_path.glob("entradas_*.json")))
    assert salvo.economico.custo_racao_kg == pytest.approx(3.10)


# --- casos-limite do wizard ------------------------------------------------------------------

def test_viveiros_ativos_e_capex_com_nomes_repetidos():
    u = UsuarioCasoBase([(r"^Item de CAPEX nº 2 ", "Escavação e construção de viveiros")])
    contagem = {"ativos": 0}
    original = u.entrada

    def entrada(prompt):
        if prompt.startswith("Número de viveiros/tanques ativos"):
            contagem["ativos"] += 1
            return "0" if contagem["ativos"] == 1 else "30"
        return original(prompt)
    cfg = iniciar_entradas(entrada=entrada, saida=u.saida, salvar=False)
    assert contagem["ativos"] == 2 and cfg.tecnico.tanques_ativos == 30
    assert "Escavação e construção de viveiros (2)" in cfg.economico.capex_itens
    assert cfg.economico.capex_total == pytest.approx(745000 - 70000 + 400000)   # nenhum item sobrescrito


def test_distribuicao_aceita_maximo_igual_ao_valor_e_respeita_dominio():
    cfg = criar_config_caso_base()
    cfg.economico.custo_alevino_milheiro = 350.0
    u = UsuarioSimulado([(r"Tipo de distribuição", "1"), (r"^\s+Mínimo", "0,25"), (r"^\s+Máximo", "0,35")], padrao_falha=False)
    d = _perguntar_distribuicao(Perguntador(u.entrada, u.saida), cfg, "economico.custo_alevino_milheiro",
                                "Custo do alevino (R$/unidade)", None, 1 / 1000)
    assert d.maximo == pytest.approx(350.0) and d.moda == pytest.approx(350.0)
    respostas = iter(["1", "-5", "5", "150", "20"])
    saidas = []
    d = _perguntar_distribuicao(Perguntador(lambda _: next(respostas), saidas.append), criar_config_caso_base(),
                                "tecnico.mortalidade_pct", "Mortalidade (%)", None)
    assert (d.minimo, d.maximo) == (5, 20) and sum("maior ou igual" in s or "menor ou igual" in s for s in saidas) == 2


def test_cooperativa_sem_cooperados_na_operacao_nao_infla_renda():
    cfg = criar_config_caso_base()
    cfg.economico.cooperados_trabalhadores, cfg.economico.perc_sobras_trabalhadores = 0, 0.0
    cfg.social.empregos_diretos = 3
    renda = motor(cfg, None, 1)["social"]["renda_mensal_trabalhador"][0]
    assert renda == pytest.approx(12000 * 1 / 3)       # retiradas divididas por quem trabalha, sem sobras fictícias


def test_topsis_com_alternativa_sem_producao():
    alts = {"A": criar_config_caso_base()}
    b = copy.deepcopy(alts["A"])
    b.projeto, b.tecnico.tanques_ativos = "B", 0
    alts["B"] = b
    comp = comparar_alternativas(alts, n_mc=100)
    assert len(comp["ranking"]) == 2 and comp["avisos"]


def test_trocar_sistema_atualiza_referencias():
    u = UsuarioCasoBase()
    wiz = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=False)    # referências do semi-intensivo aceitas
    v = UsuarioSimulado([(r"Sistema produtivo:", "3"), (r".*", "")], padrao_falha=False)
    novo = wizard_evteas(entrada=v.entrada, base=copy.deepcopy(wiz), saida=v.saida, blocos=["Técnico"])
    from evteas_py.config import SISTEMAS_PRODUTIVOS
    assert novo.tecnico.sistema_produtivo != wiz.tecnico.sistema_produtivo
    ref = SISTEMAS_PRODUTIVOS[novo.tecnico.sistema_produtivo]
    assert novo.ambiental.energia_kwh_kg == pytest.approx(ref["energia_kwh_kg"])
    assert novo.ambiental.renovacao_pct_dia == pytest.approx(ref["renovacao_pct_dia"])
    assert novo.tecnico.capacidade_suporte_kg_m3 == pytest.approx(ref["capacidade_suporte_kg_m3"])


def test_caso_controle_e_rampa_revisados_com_enter_preservam_resultado():
    for cfg in (criar_config_caso_controle(), criar_config_caso_base()):
        if cfg.economico.capacidade_inicial_pct >= 100:
            cfg.economico.meses_rampa = 12
        u = UsuarioSimulado([(r".*", "")], padrao_falha=False)
        c = wizard_evteas(entrada=u.entrada, base=copy.deepcopy(cfg), saida=u.saida)
        assert _vpl(c) == pytest.approx(_vpl(cfg), rel=1e-9)
        assert c.economico.meses_rampa == cfg.economico.meses_rampa


def test_origem_do_bloco_tecnico_e_nomes_de_arquivo():
    u = UsuarioCasoBase([(r"^Origem dos dados informados no bloco 'técnico", "1")])
    cfg = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=False)
    assert cfg.fontes["tecnico.area_lamina_m2"].categoria == "historico"
    assert cfg.fontes["tecnico.fcr"].categoria == "historico"
    a, b = copy.deepcopy(cfg), copy.deepcopy(cfg)
    a.projeto = "Piscicultura de tilápia em viveiros escavados — Associação de Pescadores — cenário pessimista"
    b.projeto = "Piscicultura de tilápia em viveiros escavados — Associação de Pescadores — cenário otimista"
    assert nome_arquivo(a) != nome_arquivo(b)


def test_ciclos_por_ano_no_limite_mantem_vv_valido():
    u = UsuarioCasoBase([(r"^Ciclos por ano", "2,0277")])                  # máximo exibido para ciclo de 180 dias
    cfg = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=False)
    assert cfg.tecnico.ciclos_ano == pytest.approx(2.0277)
    assert executar_evteas(cfg, executar_mc=False, executar_sens=False)["vv"]["valido"]


def test_lista_de_variaveis_estocasticas_igual_ao_que_o_motor_le():
    import inspect
    import re
    from evteas_py import modelo
    from evteas_py.config import VARIAVEIS_ESTOCASTICAS
    lidas = set(re.findall(r'ctx\.v\("([^"]+)"\)', inspect.getsource(modelo)))
    assert lidas == set(VARIAVEIS_ESTOCASTICAS)


def test_renda_em_salarios_minimos_no_mesmo_nivel_de_precos():
    cfg = criar_config_caso_base()
    cfg.economico.crescimento_custos_aa_pct = 5.0                 # retiradas e salário mínimo reajustados juntos
    r = motor(cfg, None, 1)
    ano = r["economico"]["ano_regime"]
    sm_regime = cfg.social.salario_minimo * 1.05 ** (ano - 1)
    assert r["social"]["renda_em_salarios_minimos"][0] == pytest.approx(r["social"]["renda_mensal_trabalhador"][0] / sm_regime)


def test_outros_custos_mensais_nao_escalam_pelo_mix():
    from evteas_py.modelo import Contexto, calcular_tecnico, dre_mensal
    cfg = criar_config_caso_base()
    cfg.economico.outros_custos_variaveis_mes = 1000.0
    a = copy.deepcopy(cfg)
    a.economico.producao_vendas_kg_mes = 1.5 * float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
    d1, d2 = dre_mensal(motor(cfg, None, 1)["economico"]), dre_mensal(motor(a, None, 1)["economico"])
    # a diferença de outros custos variáveis vem só da parcela por kg vendido, não do valor mensal
    extra_kg = (d2["Outros Custos Variáveis"] - d1["Outros Custos Variáveis"]).iloc[-1]
    vendido = 0.5 * float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
    assert extra_kg == pytest.approx(vendido * cfg.economico.outros_custos_variaveis_kg)


def test_reposicionamento_respeita_dominio():
    from evteas_py.interface import ajustar_distribuicao
    d = ajustar_distribuicao(Distribuicao("triangular", 5, 10, 20), 10, 60, "tecnico.mortalidade_pct")
    assert d.maximo <= 99 and d.moda == 60
    d0 = ajustar_distribuicao(Distribuicao("triangular", 5, 10, 20), 10, 0, "tecnico.mortalidade_pct")
    assert d0.minimo == 0 and d0.maximo > 0                        # a incerteza não desaparece
    cfg = criar_config_caso_base()
    cfg.tecnico.mortalidade_pct = 60.0
    cfg.monte_carlo.distribuicoes["tecnico.mortalidade_pct"] = Distribuicao("triangular", 30, 60, 120)
    vv = executar_evteas(cfg, executar_mc=False, executar_sens=False)["vv"]
    assert not vv["valido"] and any("domínio" in e for e in vv["erros"])

"""Testes da entrada de dados: o estudo só produz resultados a partir das entradas."""
import copy
import json
import math

import numpy as np
import pytest

from evteas_py import (config_em_branco, criar_config_caso_base, entradas_pendentes, executar_evteas,
                       iniciar_entradas, salvar_config, wizard_evteas)
from evteas_py.interface import EntradaCancelada, Perguntador, converter_numero
from evteas_py.pipeline import motor

from usuario_simulado import UsuarioCasoBase, UsuarioSimulado


def _rodar_novo(tmp_path, extra=None):
    u = UsuarioCasoBase(extra)
    cfg = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=True, pasta_saida=str(tmp_path))
    return cfg, u


def test_novo_projeto_reproduz_caso_base(tmp_path):
    cfg, u = _rodar_novo(tmp_path)
    assert entradas_pendentes(cfg) == []
    ref = criar_config_caso_base()
    a, b = motor(cfg, None, 1)["economico"], motor(ref, None, 1)["economico"]
    assert a["vpl"][0] == pytest.approx(b["vpl"][0], rel=1e-6)
    assert a["receita_regime"][0] == pytest.approx(b["receita_regime"][0], rel=1e-9)
    assert list(tmp_path.glob("entradas_Caso_base_PGTR_de_piscicultura_de_tilapia*.json"))


def test_monte_carlo_da_entrada_igual_ao_caso_base(tmp_path):
    from evteas_py import monte_carlo
    cfg, _ = _rodar_novo(tmp_path)
    a = monte_carlo(cfg, n=500)["amostra"]["VPL"].to_numpy()
    b = monte_carlo(criar_config_caso_base(), n=500)["amostra"]["VPL"].to_numpy()
    assert np.allclose(a, b, rtol=1e-6)


def test_fontes_registradas(tmp_path):
    cfg, _ = _rodar_novo(tmp_path)
    assert cfg.fontes["tecnico.fcr"].categoria == "autor"
    assert cfg.fontes["ambiental.n_max_mg_l"].categoria == "normativo"
    assert cfg.fontes["ambiental.evaporacao_mm_dia"].categoria == "bibliografico"


def test_modo_novo_nao_aceita_enter_sem_referencia():
    respostas = iter(["", "", "abc", "-5", "12,5"])
    msgs = []
    P = Perguntador(lambda _: next(respostas), msgs.append, "novo")
    v, origem = P.numero("Área", None, minimo=0)
    assert v == 12.5 and origem == "usuario"
    assert sum("obrigatório" in m for m in msgs) == 2 and any("inválido" in m for m in msgs)


def test_modo_revisar_enter_mantem_valor():
    P = Perguntador(lambda _: "", print, "revisar")
    assert P.numero("x", 7.0)[0] == 7.0
    assert P.sim_nao("y", True)[0] is True


def test_config_em_branco_nao_tem_valores():
    cfg = config_em_branco()
    assert len(entradas_pendentes(cfg)) > 100
    assert math.isnan(cfg.tecnico.fcr) and math.isnan(cfg.economico.preco_venda_kg)


def test_conversao_de_numeros():
    assert converter_numero("1.234,56") == pytest.approx(1234.56)
    assert converter_numero("1,234.56") == pytest.approx(1234.56)
    assert converter_numero("R$ 10,5") == pytest.approx(10.5)
    assert converter_numero("1/3") == pytest.approx(1 / 3)
    with pytest.raises(ValueError):
        converter_numero("abc")


def test_sair_interrompe():
    P = Perguntador(lambda _: "sair", print, "novo")
    with pytest.raises(EntradaCancelada):
        P.numero("x")


def test_carregar_arquivo_e_executar(tmp_path):
    ref = criar_config_caso_base()
    arq = salvar_config(ref, tmp_path / "e.json")
    u = UsuarioSimulado([(r"Como deseja informar", "2"), (r"Caminho do arquivo", arq),
                         (r"Revisar as entradas carregadas", "n"), (r"O que deseja fazer", "1")])
    cfg = iniciar_entradas(u.entrada, u.saida, salvar=False)
    assert motor(cfg, None, 1)["economico"]["vpl"][0] == pytest.approx(motor(ref, None, 1)["economico"]["vpl"][0])


def test_revisar_um_bloco_altera_resultado(tmp_path):
    ref = criar_config_caso_base()
    arq = salvar_config(ref, tmp_path / "e.json")
    u = UsuarioSimulado([(r"Como deseja informar", "2"), (r"Caminho do arquivo", arq),
                         (r"Revisar as entradas carregadas", "n"),
                         (r"O que deseja fazer", None), (r"Bloco a corrigir", "Custos operacionais"),
                         (r"^Custo da ração", "3,50"), (r"Atualizar a origem", "n"), (r".*", "")],
                        padrao_falha=False)
    acoes = iter(["2", "1"])
    u.regras[3] = (u.regras[3][0], None)
    original = u.entrada

    def entrada(prompt):
        alvo = (u._titulo_menu() or "") + prompt
        if "O que deseja fazer" in alvo:
            u.ultimas_saidas = []
            return next(acoes)
        return original(prompt)
    cfg = iniciar_entradas(entrada, u.saida, salvar=False)
    assert cfg.economico.custo_racao_kg == pytest.approx(3.5)
    assert motor(cfg, None, 1)["economico"]["vpl"][0] < motor(ref, None, 1)["economico"]["vpl"][0]


def test_exemplo_avisa_que_e_demonstracao():
    u = UsuarioSimulado([(r"Como deseja informar", "3"), (r"O que deseja fazer", "1")])
    iniciar_entradas(u.entrada, u.saida, salvar=False)
    assert any("NÃO representam o seu projeto" in t for t in u.transcricao)


def test_salvar_e_encerrar_nao_executa(tmp_path):
    u = UsuarioSimulado([(r"Como deseja informar", "3"), (r"O que deseja fazer", "3")])
    with pytest.raises(EntradaCancelada):
        iniciar_entradas(u.entrada, u.saida, salvar=True, pasta_saida=str(tmp_path))
    assert list(tmp_path.glob("entradas_*.json"))


def test_empresa_com_clt_e_tributos_sobre_folha(tmp_path):
    extra = [(r"Tipo de pessoa jurídica", "1"), (r"^Número de funcionários CLT", "2"),
             (r"Cargo do funcionário CLT nº 1", "Técnico em aquicultura"), (r"Salário bruto mensal de 'Técnico", "3000"),
             (r"Cargo do funcionário CLT nº 2", "Auxiliar"), (r"Salário bruto mensal de 'Auxiliar", "2000"),
             (r"^Configurar INSS patronal", "s"), (r"Alíquota de INSS patronal", "20"),
             (r"^Configurar FGTS", "s"), (r"Alíquota de FGTS", "8"), (r"^Empregos diretos", "2")]
    cfg, _ = _rodar_novo(tmp_path, extra)
    assert cfg.economico.tipo_organizacao == "empresa"
    assert sum(cfg.economico.salarios_clt_por_cargo.values()) == 5000
    from evteas_py.modelo import aliquotas_configuradas, custo_pessoal_mensal
    assert custo_pessoal_mensal(cfg, aliquotas_configuradas(cfg)) == pytest.approx(5000 * 1.28)
    r = executar_evteas(cfg, executar_mc=False, executar_sens=False)
    assert r["vv"]["valido"]


def test_notebook_autocontido_sem_colisao_de_nomes():
    """O notebook concatena os módulos; nomes de nível superior não podem se repetir."""
    import ast
    import collections
    import re
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1] / "evteas_py"
    nomes = collections.defaultdict(list)
    def nomes_do_alvo(t):
        if isinstance(t, ast.Name):
            return [t.id]
        if isinstance(t, (ast.Tuple, ast.List)):
            return [x for e in t.elts for x in nomes_do_alvo(e)]
        return []

    modulos = re.search(r"MODULOS = (\[.*?\])", (raiz.parent / "gerar_notebook.py").read_text(encoding="utf-8")).group(1)
    for m in ast.literal_eval(modulos):
        for n in ast.parse((raiz / f"{m}.py").read_text(encoding="utf-8")).body:
            alvos = [n.name] if isinstance(n, (ast.FunctionDef, ast.ClassDef)) else \
                [x for t in getattr(n, "targets", []) for x in nomes_do_alvo(t)] + \
                (nomes_do_alvo(n.target) if isinstance(n, ast.AnnAssign) else [])
            for a in alvos:
                nomes[a].append(m)
    assert {k: v for k, v in nomes.items() if len(v) > 1} == {}


def test_notebook_identico_ao_pacote():
    """O notebook do Colab deve conter exatamente o código do pacote testado
    (regenerar com: python gerar_notebook.py)."""
    import json
    from pathlib import Path
    import gerar_notebook
    nb = json.loads((Path(gerar_notebook.__file__).parent / "EVTEAS_Py_Rev187.ipynb").read_text(encoding="utf-8"))
    codigo = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    esperado = [c["source"] for c in gerar_notebook.celulas() if c["cell_type"] == "code"]
    defasadas = [m for m in gerar_notebook.MODULOS if gerar_notebook.codigo_do_modulo(m) not in codigo]
    assert not defasadas, f"notebook desatualizado nos módulos: {defasadas}"
    assert codigo == esperado

"""Testes do registro de lacunas do texto (códigos E, S, K e N) e dos prints que ilustram o Capítulo 4."""
import copy
import re
from pathlib import Path

import pytest

from evteas_py import comparar_alternativas, criar_alternativas, criar_config_caso_base, executar_evteas
from evteas_py.campos_texto import (CAMPOS, POR_CODIGO, PRINTS, exportar_valores_para_o_texto, lacuna, reais,
                                    roteiro_de_prints, valores_para_o_texto)

DOCUMENTACAO = Path(__file__).resolve().parents[1] / "documentacao"
CODIGO = re.compile(r"\[([ESKN]\d{2,3})(?: – [^\]]*)?\]")
PRINT = re.compile(r"\[INSERIR PRINT (P\d{2}) – ")


@pytest.fixture(scope="module")
def execucao():
    cfg = criar_config_caso_base()
    r = executar_evteas(cfg, executar_mc=True, executar_sens=True, n_mc=500)
    comp = comparar_alternativas(criar_alternativas(), n_mc=200)
    return cfg, r, comp


def test_todos_os_campos_tem_valor_no_caso_base(execucao):
    df = valores_para_o_texto(*execucao)
    assert df["Código"].is_unique and len(df) == len(CAMPOS)
    indisponiveis = df[df["Valor"].str.startswith("indisponível")]
    assert indisponiveis.empty, indisponiveis.to_string()
    assert not df["Valor"].str.contains(r"\bnan\b|\(sem_solucao\)|reunião\(ões\)", regex=True).any()


def test_valores_acompanham_as_entradas_do_usuario(execucao):
    cfg, r, _ = execucao
    c = copy.deepcopy(cfg)
    c.tecnico.fcr = 1.7
    c.monte_carlo.distribuicoes.pop("tecnico.fcr", None)
    r2 = executar_evteas(c, executar_mc=False, executar_sens=False)
    v1 = valores_para_o_texto(cfg, r).set_index("Código")["Valor"]
    v2 = valores_para_o_texto(c, r2).set_index("Código")["Valor"]
    assert v2["E14"] == "1,70" and v1["E14"] == "1,50"
    assert v2["S23"] == reais(r2["economico"]["vpl"]) != v1["S23"]
    assert v2["E55"] == "sem incerteza (valor fixo)"
    # sem Monte Carlo e sem comparação, as lacunas correspondentes avisam o motivo
    assert v2["S84"].startswith("indisponível") and v2["S98"] == "comparação não realizada"


def test_exportacao_da_tabela_de_valores(execucao, tmp_path):
    caminho = exportar_valores_para_o_texto(valores_para_o_texto(*execucao), tmp_path)
    assert Path(caminho).exists()


@pytest.mark.skipif(not (DOCUMENTACAO / "conteudo_capitulos.py").exists(), reason="gerador do texto fora do repositório")
def test_lacunas_do_texto_existem_no_registro():
    import sys
    sys.path.insert(0, str(DOCUMENTACAO))
    import conteudo_capitulos
    blocos = conteudo_capitulos.blocos()
    texto = "\n".join([x.get("t", "") for x in blocos] +
                      [str(c) for x in blocos if x["k"] == "tbl" for linha in x["linhas"] for c in linha])
    usados = set(CODIGO.findall(texto))
    assert usados <= set(POR_CODIGO), sorted(usados - set(POR_CODIGO))
    assert set(POR_CODIGO) <= usados, sorted(set(POR_CODIGO) - usados)        # nenhum valor sem lugar no texto
    assert PRINT.findall(texto) == [p.codigo for p in PRINTS]                  # cada print uma vez, na ordem
    assert not re.search(r"[⟪⟫⟦⟧]", texto)                                     # nenhuma marcação sem resolver
    assert lacuna("S23") == "[S23 – VPL do projeto]"
    assert list(roteiro_de_prints()["Print"]) == [p.codigo for p in PRINTS]


# --- casos-limite dos valores ------------------------------------------------------

def _valores(cfg, **kw):
    r = executar_evteas(cfg, **kw)
    return valores_para_o_texto(cfg, r).set_index("Código")["Valor"], r


def test_payback_e_tir_indefinidos_viram_frases():
    cfg = criar_config_caso_base()
    cfg.economico.preco_venda_kg = 3.0
    cfg.economico.mix_produtos = []
    cfg.monte_carlo.distribuicoes.pop("economico.preco_venda_kg", None)
    v, r = _valores(cfg, executar_mc=False, executar_sens=False)
    assert v["S25"] == "prazo superior ao horizonte de análise"
    assert v["S24"].startswith("não definida") or "% a.a." in v["S24"]
    textos = " ".join(v.astype(str))
    assert not re.search(r"\bnan\b", textos.lower()) and "definido%" not in textos
    assert "sem_solucao" not in textos and "multiplas" not in textos


def test_ponderacao_likert_e_ahp():
    from evteas_py import exemplo_validacao_especialistas
    cfg = criar_config_caso_base()
    v, _ = _valores(exemplo_validacao_especialistas(cfg), executar_mc=False, executar_sens=False)
    assert "concordância média" in v["S102"] and v["E39"].startswith("escala Likert")
    c = copy.deepcopy(cfg)
    c.pesos.metodo, c.pesos.ahp_matriz = "ahp", [[1, 1, 2, 2], [1, 1, 2, 2], [0.5, 0.5, 1, 1], [0.5, 0.5, 1, 1]]
    v, _ = _valores(c, executar_mc=False, executar_sens=False)
    assert v["E39"].startswith("AHP") and v["S102"].startswith("não se aplica")


def test_valor_critico_com_base_nula_e_tma():
    from evteas_py import tabela_sensibilidade
    cfg = criar_config_caso_base()
    cfg.tecnico.mortalidade_pct = 0.0
    cfg.monte_carlo.distribuicoes.pop("tecnico.mortalidade_pct", None)
    r = executar_evteas(cfg, executar_mc=False, executar_sens=True)
    tab = tabela_sensibilidade(r).set_index("Variável")["Valor crítico (VPL = 0) e folga"]
    assert "definido%" not in " ".join(tab)
    assert tab["TMA (% a.a.)"].endswith("(= TIR)")


def test_tipos_de_distribuicao_no_texto():
    from evteas_py.config import Distribuicao
    cfg = criar_config_caso_base()
    cfg.monte_carlo.distribuicoes["economico.preco_venda_kg"] = Distribuicao("Uniforme", 9.0, 10.5, 11.5)
    cfg.monte_carlo.distribuicoes["tecnico.fcr"] = Distribuicao("fixa", 1.5, 1.5, 1.5)
    v = valores_para_o_texto(cfg, executar_evteas(cfg, executar_mc=False, executar_sens=False)).set_index("Código")["Valor"]
    assert v["E50"].startswith("uniforme (mínimo 9,00; máximo 11,50") and "mais provável" not in v["E50"]
    assert v["E55"] == "fixa em 1,50"
    assert "AACE" in v["E58"]                          # incerteza do CAPEX derivada da classe da estimativa


def test_resultado_de_outras_entradas_e_recusado(execucao):
    cfg, r, _ = execucao
    c = copy.deepcopy(cfg)
    c.tecnico.fcr = 1.9
    from evteas_py.interface import EntradaCancelada
    with pytest.raises(EntradaCancelada, match="outras entradas"):
        valores_para_o_texto(c, r)


def test_comparacao_de_outras_entradas_e_ignorada():
    from evteas_py import comparar_alternativas as comparar
    cfg = criar_config_caso_base()
    antigo = copy.deepcopy(cfg)
    alt = copy.deepcopy(cfg)
    alt.projeto = "Alternativa solar"
    alt.ambiental.fonte_energia = "solar"
    comp = comparar({antigo.projeto: antigo, alt.projeto: alt}, n_mc=200)
    v = valores_para_o_texto(cfg, executar_evteas(cfg, executar_mc=False, executar_sens=False), comp)
    v = v.set_index("Código")["Valor"]
    assert v["S97"] == "Alternativa solar"                      # o projeto não é contado como alternativa
    cfg.tecnico.fcr = 1.7
    cfg.monte_carlo.distribuicoes.pop("tecnico.fcr", None)
    v2 = valores_para_o_texto(cfg, executar_evteas(cfg, executar_mc=False, executar_sens=False), comp)
    assert v2.set_index("Código").loc["S97", "Valor"].startswith("comparação feita com outras entradas")


def test_wizard_anuncia_os_prints_e_registra_origens():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from usuario_simulado import UsuarioCasoBase
    from evteas_py import iniciar_entradas
    u = UsuarioCasoBase([])
    cfg = iniciar_entradas(entrada=u.entrada, saida=u.saida, salvar=False)
    anuncios = [t.split(" — ")[0].replace("\n", "").replace("▶ PRINT ", "") for t in u.transcricao if "▶ PRINT" in t]
    esperados = ["P01", "P03", "P05", "P06", "P08", "P09", "P11", "P14", "P02"]
    assert anuncios == esperados, anuncios
    r = executar_evteas(cfg, executar_mc=False, executar_sens=False)
    v = valores_para_o_texto(cfg, r).set_index("Código")
    for cod in ("E05", "E14", "E16", "E20", "E24", "E26", "E31", "E34"):
        assert v.loc[cod, "Origem declarada"] not in ("", "não registrada"), cod

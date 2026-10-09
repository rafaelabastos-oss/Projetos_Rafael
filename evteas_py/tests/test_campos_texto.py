"""Testes do registro de lacunas do texto (códigos E, R, K e N) e dos prints que ilustram o Capítulo 4."""
import copy
import re
from pathlib import Path

import pytest

from evteas_py import comparar_alternativas, criar_alternativas, criar_config_caso_base, executar_evteas
from evteas_py.campos_texto import (CAMPOS, POR_CODIGO, PRINTS, exportar_valores_para_o_texto, lacuna, reais,
                                    roteiro_de_prints, valores_para_o_texto)

DOCUMENTACAO = Path(__file__).resolve().parents[1] / "documentacao"
CODIGO = re.compile(r"\[([ERKN]\d{2,3})(?: – [^\]]*)?\]")
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
    assert (df.loc[df["Código"].str.startswith("E"), "Origem declarada"] != "").all()


def test_valores_acompanham_as_entradas_do_usuario(execucao):
    cfg, r, _ = execucao
    c = copy.deepcopy(cfg)
    c.tecnico.fcr = 1.7
    c.monte_carlo.distribuicoes.pop("tecnico.fcr", None)
    r2 = executar_evteas(c, executar_mc=False, executar_sens=False)
    v1 = valores_para_o_texto(cfg, r).set_index("Código")["Valor"]
    v2 = valores_para_o_texto(c, r2).set_index("Código")["Valor"]
    assert v2["E14"] == "1,70" and v1["E14"] == "1,50"
    assert v2["R23"] == reais(r2["economico"]["vpl"]) != v1["R23"]
    assert v2["E55"] == "sem incerteza (valor fixo)"
    # sem Monte Carlo e sem comparação, as lacunas correspondentes avisam o motivo
    assert v2["R84"].startswith("indisponível") and v2["R98"] == "comparação não realizada"


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
    assert lacuna("R23") == "[R23 – VPL do projeto]"
    assert list(roteiro_de_prints()["Print"]) == [p.codigo for p in PRINTS]

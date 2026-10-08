"""Testes do registro do ciclo DSR (etapas, comparação, rastreabilidade e aprendizagens)."""
from pathlib import Path

import pytest

from evteas_py import dsr

TESTES = Path(__file__).resolve().parent


def test_doze_etapas_em_ordem_com_evidencia():
    assert [e.numero for e in dsr.ETAPAS_DSR] == list(range(1, 13))
    assert all(e.produto and e.evidencias and e.situacao for e in dsr.ETAPAS_DSR)
    assert len(dsr.etapas_dsr()) == 12


def test_todos_os_requisitos_implementados_e_verificados():
    m = dsr.matriz_rastreabilidade(TESTES)
    pendentes = m[m["Situação"] != "implementado e verificado"]
    assert pendentes.empty, pendentes[["Requisito", "Faltando"]].to_string()


def test_rastreabilidade_aponta_teste_ou_funcao_inexistente():
    falso = dsr.Requisito("RX", "teste", "—", ("modelo.nao_existe",), ("test_evteas.py::test_nao_existe",))
    sem_teste = dsr.Requisito("RY", "teste", "—", ("modelo.calcular_tecnico",), ("test_evteas.py::test_nao_existe",))
    m = dsr.matriz_rastreabilidade(TESTES, [falso, sem_teste]).set_index("Requisito")["Situação"]
    assert m["RX"] == "pendente" and m["RY"] == "implementado, sem teste"


def test_matriz_sem_pasta_de_testes_nao_declara_verificado(tmp_path):
    m = dsr.matriz_rastreabilidade(tmp_path)
    assert (m["Situação"] == "implementado, sem teste").all()


def test_aprendizagens_apontam_testes_existentes():
    nomes = dsr._testes_existentes(TESTES)
    for a in dsr.APRENDIZAGENS:
        arquivo, teste = a.evidencia.split("::")
        assert teste in nomes[arquivo], a.evidencia


def test_comparacao_wazlawick():
    tab = dsr.tabela_comparativa()
    assert list(tab.columns[1:]) == list(dsr.ARTEFATOS)
    valores = set(tab[list(dsr.ARTEFATOS)].to_numpy().ravel())
    assert valores <= {dsr.SIM, dsr.NAO, dsr.NI}
    r = dsr.combinacao_inedita()
    assert r["inedita"] and r["exclusivas"]
    assert set(dsr.EVIDENCIA_EVTEAS) == set(dsr.COMPARACAO_ARTEFATOS)
    for prop, ev in dsr.EVIDENCIA_EVTEAS.items():
        for alvo in ev.split("; "):
            nome = alvo.split(" ")[0]
            if "." in nome and not nome.startswith("pacote"):
                assert dsr._objeto_existe(nome), (prop, nome)


@pytest.mark.parametrize("etapa", [e for e in dsr.ETAPAS_DSR])
def test_evidencias_de_codigo_existem(etapa):
    for ev in etapa.evidencias:
        if ev.startswith(("config.", "modelo.", "pipeline.", "interface.", "vv.", "relatorios.", "dsr.")):
            assert dsr._objeto_existe(ev), ev

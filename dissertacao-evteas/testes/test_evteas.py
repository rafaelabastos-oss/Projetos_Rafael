"""Executa a suíte de verificação do EVTEAS-Py com pytest (a mesma suíte roda no notebook, Seção 4)."""
import pytest

from evteas_py import testes_automatizados

RESULTADOS = testes_automatizados(rapido=True)


@pytest.mark.parametrize("linha", RESULTADOS.to_dict("records"), ids=lambda r: r["Teste"])
def test_evteas(linha):
    assert linha["Aprovado"], linha["Detalhe"]

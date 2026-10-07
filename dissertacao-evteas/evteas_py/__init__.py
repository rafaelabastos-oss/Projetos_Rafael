"""EVTEAS-Py — framework computacional para Estudos de Viabilidade Técnica, Econômica, Ambiental e
Social (EVTEAS) de projetos de piscicultura.

Fluxo de uso:
    1. informar as entradas do projeto (formulário do Colab, planilha ou ``wizard_evteas``);
    2. ``executar_evteas(cfg)`` — análise determinística, Monte Carlo, sensibilidade e decisão;
    3. ``marcadores(...)`` / ``exportar_tudo(...)`` — valores [E-xx] e [R-xx] para o texto;
    4. ``preencher_docx(...)`` — substitui os marcadores no .docx da dissertação (opcional).
Nenhuma entrada do projeto tem valor predefinido.
"""
from .config import VERSAO, EVTEASConfig, carregar_config, salvar_config, validar_config
from .entradas import (ENTRADAS, EntradasInvalidas, alternativas_de_formulario, coletar_formulario,
                       config_de_formulario, config_de_planilha, config_vazia, entradas_faltantes,
                       gerar_planilha_entradas, ler_formulario, tabela_entradas)
from .interface import analise_precos, wizard_evteas
from .pipeline import comparar_alternativas, executar_evteas
from .relatorios import (exportar_tudo, gerar_figuras, marcadores, preencher_docx, resumo_executivo,
                         tabelas_dissertacao)
from .vv import testes_automatizados, validar_invariantes

__version__ = VERSAO
__all__ = [
    "VERSAO", "EVTEASConfig", "carregar_config", "salvar_config", "validar_config", "ENTRADAS", "EntradasInvalidas",
    "alternativas_de_formulario", "coletar_formulario", "config_de_formulario", "config_de_planilha", "config_vazia",
    "entradas_faltantes", "gerar_planilha_entradas", "ler_formulario", "tabela_entradas", "analise_precos",
    "wizard_evteas", "comparar_alternativas", "executar_evteas", "exportar_tudo", "gerar_figuras", "marcadores",
    "preencher_docx", "resumo_executivo", "tabelas_dissertacao", "testes_automatizados", "validar_invariantes",
]

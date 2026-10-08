"""EVTEAS-Py — framework de Estudo de Viabilidade Técnica, Econômica, Ambiental
e Social aplicado à piscicultura (Bastos, UFF/MESC)."""
from .config import *  # noqa: F401,F403
from .financeiro import payback, percentis, safe_div, taxa_anual_para_mensal, taxa_mensal_para_anual, tir, vpl  # noqa: F401
from .modelo import curva_crescimento, dre_anual, dre_mensal  # noqa: F401
from .ponderacao import REFERENCIAS_NORMALIZACAO, classificar, normalizar, pesos_ahp, pesos_likert, topsis  # noqa: F401
from .incerteza import cenarios, monte_carlo, sensibilidade, valores_criticos  # noqa: F401
from .pipeline import comparar_alternativas, executar_evteas, motor, tabela_premissas  # noqa: F401
from .vv import teste_regressao_deterministica, validar_invariantes  # noqa: F401
from .casos import (criar_alternativas, criar_config_caso_base, criar_config_caso_controle,  # noqa: F401
                    exemplo_validacao_especialistas)

from .relatorios import diagrama_arquitetura, exportar, gerar_graficos, relatorio_markdown, resumo_executivo  # noqa: F401,E402
from .interface import (analisar_precos, carregar_config, config_em_branco, definir_e_comparar_alternativas,  # noqa: F401,E402
                        entradas_pendentes, exigir_entradas, iniciar_entradas, ler_entradas, resumo_entradas,
                        salvar_config, wizard_evteas)
from .dsr import aprendizagens, etapas_dsr, matriz_rastreabilidade, relatorio_dsr, tabela_comparativa  # noqa: F401,E402

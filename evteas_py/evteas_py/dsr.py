"""Registro do ciclo da Design Science Research (DSR) na construção do EVTEAS-Py.

Operacionaliza, como dados verificáveis, as 12 etapas de Dresch, Lacerda e
Antunes Jr. (2015) descritas na Seção 3.3.1 da dissertação:

* ETAPAS_DSR: o que cada etapa produziu nesta pesquisa e onde está a evidência;
* COMPARACAO_ARTEFATOS (Etapa 4): propriedades do EVTEAS-Py e dos artefatos
  preexistentes da Seção 2.8.1, no formato de tabela comparativa de Wazlawick (2009);
* REQUISITOS (Etapa 5) e matriz_rastreabilidade() (Etapa 8): requisito →
  funções que o implementam → testes que o verificam, conferidos no próprio código;
* APRENDIZAGENS (Etapa 9): dificuldades, erros superados e decisões de projeto.

A matriz é recalculada a partir do código e dos arquivos de teste, de modo que um
requisito sem função ou sem teste aparece como pendente, e não como atendido.
"""
from __future__ import annotations

import ast
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# As 12 etapas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Etapa:
    numero: int
    nome: str
    fase: str                      # fases macro da Seção 3.2
    produto: str                   # o que a etapa produziu nesta pesquisa
    evidencias: Tuple[str, ...]    # onde verificar (seção, módulo, arquivo)
    situacao: str                  # concluída | primeira iteração concluída | em andamento | prevista


FASE1, FASE2, FASE3 = "Fase 1 – Imersão bibliográfica", "Fase 2 – Ciclo DSR", "Fase 3 – V&V"

ETAPAS_DSR: Tuple[Etapa, ...] = (
    Etapa(1, "Identificação do problema", FASE1,
          "Produtores e investidores da piscicultura sem instrumento sistemático para avaliar de forma integrada "
          "a viabilidade técnica, econômica, ambiental e social de seus empreendimentos.",
          ("Seção 1.3",), "concluída"),
    Etapa(2, "Compreensão do problema", FASE1,
          "Causas: variáveis dissimilares (custos, efluentes, aceitação comunitária) sem modelo que pondere dados "
          "exatos e critérios qualitativos; estudos em planilhas determinísticas; requisitos de uso extraídos dos "
          "notebooks de estudo de viabilidade econômica utilizados pelo autor (entradas, mix, tributos, cooperados).",
          ("Seções 1.2, 2.8 a 2.10",), "concluída"),
    Etapa(3, "Revisão sistemática da literatura", FASE1,
          "Corpus selecionado pelo protocolo PRISMA e referencial teórico dos três eixos temáticos.",
          ("Seções 2.1 a 2.7",), "concluída"),
    Etapa(4, "Identificação de artefatos e configuração da classe de problemas", FASE2,
          "Classe: modelagem de suporte à decisão multicritério sob incerteza em agroindústrias. Comparação de "
          "propriedades com quatro artefatos preexistentes (Wazlawick, 2009).",
          ("Seção 2.8.1", "dsr.COMPARACAO_ARTEFATOS"), "concluída"),
    Etapa(5, "Proposição do artefato", FASE2,
          "EVTEAS-Py como instanciação (framework operante) conjugada a um modelo (representação matemática da "
          "viabilidade), com requisitos de alto nível rastreáveis.",
          ("dsr.REQUISITOS",), "concluída"),
    Etapa(6, "Design do artefato", FASE2,
          "Configuração única (EVTEASConfig) com registro de fontes; motor vetorizado comum às camadas "
          "determinística e estocástica; fluxo entrada → processamento → saída → verificação; interface de "
          "entrada em blocos.",
          ("config.EVTEASConfig", "modelo.Contexto", "pipeline.motor"), "primeira iteração concluída"),
    Etapa(7, "Desenvolvimento do artefato", FASE2,
          "Pacote evteas_py com onze módulos, notebook autocontido para o Google Colab e entrada de dados "
          "interativa ou por arquivo.",
          ("Apêndice A", "pipeline.executar_evteas", "interface.iniciar_entradas"), "primeira iteração concluída"),
    Etapa(8, "Avaliação do artefato", FASE3,
          "Verificação: invariantes a cada execução, suíte de testes automatizados, caso de controle de inviabilidade e "
          "revisão independente da entrada de dados. Validação com os dois especialistas a realizar.",
          ("vv.validar_invariantes", "Apêndice B", "dsr.matriz_rastreabilidade"),
          "verificação concluída; validação prevista"),
    Etapa(9, "Explicitação das aprendizagens", FASE3,
          "Registro das dificuldades, dos erros lógicos superados e das decisões de projeto que deles resultaram.",
          ("dsr.APRENDIZAGENS",), "em andamento"),
    Etapa(10, "Conclusão", FASE3,
          "Síntese dos resultados, do atendimento aos objetivos e das limitações do artefato.",
          ("Capítulo 5",), "primeira iteração concluída"),
    Etapa(11, "Generalização para a classe de problemas", FASE3,
          "Princípios de projeto transferíveis a outras cadeias agroindustriais, com recalibração dos parâmetros.",
          ("Seção 5.5",), "primeira iteração concluída"),
    Etapa(12, "Comunicação dos resultados", FASE3,
          "Dissertação, código e testes registrados no repositório do projeto, notebook executável, arquivo de entradas, relatórios "
          "exportados e apêndices com o código-fonte; artigos previstos.",
          ("Apêndices A e B", "relatorios.exportar"), "em andamento"),
)


def etapas_dsr() -> pd.DataFrame:
    return pd.DataFrame([{"Etapa": e.numero, "Nome": e.nome, "Fase": e.fase, "Produto": e.produto,
                          "Evidências": "; ".join(e.evidencias), "Situação": e.situacao} for e in ETAPAS_DSR])


# ---------------------------------------------------------------------------
# Etapa 4: comparação de propriedades com artefatos preexistentes (Wazlawick, 2009)
# ---------------------------------------------------------------------------

SIM, NAO, NI = "sim", "não", "não identificado"

ARTEFATOS = ("Costa Magalhães (2022)", "pyteea (Maier; Weyand, 2025)", "AQUA+ (Ramos et al., 2024)",
             "AquaSpace (Gimpel et al., 2018)", "EVTEAS-Py")

# Somente o que a Seção 2.8.1 descreve sobre cada artefato; o restante fica como "não identificado".
COMPARACAO_ARTEFATOS: Dict[str, Tuple[str, ...]] = {
    "Implementação em Python":                         (SIM, SIM, NI, NI, SIM),
    "Aplicação à aquicultura":                         (NAO, NAO, SIM, SIM, SIM),
    "Avaliação no nível do empreendimento":            (SIM, NI, SIM, NAO, SIM),
    "Viabilidade técnica do processo produtivo":       (NI, SIM, NI, NI, SIM),
    "Viabilidade econômico-financeira (VPL, TIR)":     (SIM, SIM, SIM, NI, SIM),
    "Indicadores ambientais":                          (NI, SIM, NAO, SIM, SIM),
    "Indicadores sociais":                             (NI, NI, NAO, SIM, SIM),
    "Governança, ESG e Lean Green":                    (NI, NI, NAO, NI, SIM),
    "Simulação estocástica (Monte Carlo)":             (NI, NI, NI, NI, SIM),
    "Ponderação multicritério com regra de decisão":   (NI, NI, NI, NI, SIM),
}

EVIDENCIA_EVTEAS = {
    "Implementação em Python": "pacote evteas_py",
    "Aplicação à aquicultura": "piscicultura continental (casos.criar_config_caso_base)",
    "Avaliação no nível do empreendimento": "configuração por projeto (config.EVTEASConfig)",
    "Viabilidade técnica do processo produtivo": "modelo.calcular_tecnico",
    "Viabilidade econômico-financeira (VPL, TIR)": "modelo.calcular_economico; financeiro.tir",
    "Indicadores ambientais": "modelo.calcular_ambiental",
    "Indicadores sociais": "modelo.calcular_social",
    "Governança, ESG e Lean Green": "modelo.calcular_governanca; modelo.calcular_lean_green",
    "Simulação estocástica (Monte Carlo)": "incerteza.monte_carlo",
    "Ponderação multicritério com regra de decisão": "ponderacao.resolver_pesos; ponderacao.classificar",
}


def tabela_comparativa() -> pd.DataFrame:
    linhas = [{"Propriedade": p, **dict(zip(ARTEFATOS, v))} for p, v in COMPARACAO_ARTEFATOS.items()]
    return pd.DataFrame(linhas)


def combinacao_inedita(artefato: str = "EVTEAS-Py") -> Dict[str, object]:
    """Verifica o critério de Wazlawick (2009): propriedades exclusivas ou combinação
    de propriedades que nenhum outro artefato comparado reúne."""
    k = ARTEFATOS.index(artefato)
    proprias = [p for p, v in COMPARACAO_ARTEFATOS.items() if v[k] == SIM]
    exclusivas = [p for p in proprias
                  if all(v != SIM for j, v in enumerate(COMPARACAO_ARTEFATOS[p]) if j != k)]
    cobertura = {a: sum(COMPARACAO_ARTEFATOS[p][j] == SIM for p in proprias)
                 for j, a in enumerate(ARTEFATOS) if j != k}
    return {"propriedades": proprias, "exclusivas": exclusivas, "cobertura_dos_demais": cobertura,
            "inedita": all(c < len(proprias) for c in cobertura.values())}


# ---------------------------------------------------------------------------
# Etapa 5: requisitos e Etapa 8: rastreabilidade requisito → código → teste
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Requisito:
    codigo: str
    descricao: str
    origem: str
    funcoes: Tuple[str, ...]       # "modulo.objeto" dentro de evteas_py
    testes: Tuple[str, ...]        # "arquivo.py::test_nome" dentro de tests/


REQUISITOS: Tuple[Requisito, ...] = (
    Requisito("R01", "Ser processado em Python, com núcleo reutilizável e notebook executável no Google Colab",
              "Etapa 5", ("pipeline.executar_evteas",),
              ("test_entradas.py::test_notebook_autocontido_sem_colisao_de_nomes",)),
    Requisito("R02", "Começar pela entrada de dados, sem resultado antes das premissas e sem valor herdado em silêncio",
              "Seção 2.8.3 (PMBOK)", ("interface.iniciar_entradas", "interface.config_em_branco",
                                      "interface.entradas_pendentes"),
              ("test_entradas.py::test_config_em_branco_nao_tem_valores",
               "test_entradas.py::test_modo_novo_nao_aceita_enter_sem_referencia",
               "test_entradas.py::test_novo_projeto_reproduz_caso_base",
               "test_entradas.py::test_salvar_e_encerrar_nao_executa",
               "test_entradas_robustez.py::test_sair_salva_rascunho_que_pode_ser_retomado")),
    Requisito("R03", "Registrar a origem de cada premissa e permitir revisar um estudo salvo",
              "Seção 3.6", ("config.Fonte", "pipeline.tabela_premissas", "interface.salvar_config",
                            "interface.carregar_config"),
              ("test_entradas.py::test_fontes_registradas", "test_evteas.py::test_config_json_ida_e_volta",
               "test_entradas.py::test_modo_revisar_enter_mantem_valor",
               "test_entradas_coerencia.py::test_revisar_preserva_mao_de_obra_mista",
               "test_entradas_robustez.py::test_campos_ausentes_nao_viram_caso_ilustrativo")),
    Requisito("R04", "Dimensionar a produção e calcular os KPIs técnicos (OEE, FCR, produtividade)",
              "Quadro 5", ("modelo.calcular_tecnico", "modelo.curva_crescimento"),
              ("test_evteas.py::test_oee_produto_dos_fatores", "test_evteas.py::test_racao_igual_fcr_vezes_ganho",
               "test_evteas.py::test_restricao_dupla_de_biomassa",
               "test_evteas.py::test_curva_crescimento_reproduz_peso_final")),
    Requisito("R05", "Projetar DRE e fluxo de caixa e calcular VPL, TIR, payback e ROI",
              "Seção 2.8.6", ("modelo.calcular_economico", "financeiro.vpl", "financeiro.tir", "financeiro.payback"),
              ("test_evteas.py::test_vpl_igual_numpy_financial", "test_evteas.py::test_tir_igual_numpy_financial",
               "test_evteas.py::test_tir_sem_solucao_nao_vira_limite_numerico",
               "test_evteas.py::test_payback_simples_e_descontado", "test_evteas.py::test_vpl_recalculado_do_fluxo",
               "test_evteas.py::test_impostos_configurados_por_base")),
    Requisito("R06", "Calcular água, pegadas hídricas, emissões, ecoeficiência e conformidade ambiental",
              "Quadro 5", ("modelo.calcular_ambiental", "modelo.score_conformidade"),
              ("test_evteas.py::test_pegada_cinza_calculo_manual",
               "test_evteas.py::test_ecoeficiencia_indefinida_quando_va_negativo",
               "test_evteas.py::test_item_eliminatorio_gera_veto",
               "test_entradas_coerencia.py::test_ambiental_acompanha_volume_vendido")),
    Requisito("R07", "Calcular RVL, LSO, risco e Radar Social, governança e alinhamento aos ODS",
              "Quadro 5", ("modelo.calcular_social", "modelo.calcular_governanca", "modelo.alinhamento_ods"),
              ("test_social_lean_green.py::test_rvl_segue_formula_do_quadro_5",
               "test_social_lean_green.py::test_lso_e_risco_social",
               "test_social_lean_green.py::test_governanca_e_ods",
               "test_entradas_coerencia.py::test_renda_e_rvl_em_precos_do_ano_de_regime")),
    Requisito("R08", "Quantificar em reais os desperdícios Lean-Green",
              "Seção 2.9.1", ("modelo.calcular_lean_green",),
              ("test_social_lean_green.py::test_lean_green_zerado_na_referencia",
               "test_social_lean_green.py::test_lean_green_racao_excedente")),
    Requisito("R09", "Traduzir julgamentos qualitativos em pesos (Likert, AHP ou preset)",
              "Seção 3.4; Quadro 7", ("ponderacao.pesos_likert", "ponderacao.pesos_ahp", "ponderacao.resolver_pesos"),
              ("test_evteas.py::test_likert_normaliza_e_triangula", "test_evteas.py::test_ahp_matriz_consistente",
               "test_evteas.py::test_ahp_rejeita_matriz_nao_reciproca",
               "test_evteas.py::test_pipeline_com_pesos_likert_e_ahp")),
    Requisito("R10", "Integrar as dimensões em índice normalizado com decisão não compensatória",
              "Seção 2.8.6", ("ponderacao.normalizar", "ponderacao.calcular_indice", "ponderacao.classificar"),
              ("test_evteas.py::test_normalizacao_limites", "test_evteas.py::test_indice_entre_zero_e_um",
               "test_evteas.py::test_classificacao_regras")),
    Requisito("R11", "Traduzir a incerteza das entradas em risco financeiro (Monte Carlo no mesmo motor)",
              "Etapa 5; Seção 3.6", ("incerteza.monte_carlo", "pipeline.motor"),
              ("test_evteas.py::test_monte_carlo_reprodutivel",
               "test_evteas.py::test_monte_carlo_degenerado_igual_deterministico",
               "test_evteas.py::test_distribuicoes_invalidas",
               "test_entradas.py::test_monte_carlo_da_entrada_igual_ao_caso_base",
               "test_entradas_robustez.py::test_parametro_nao_amostrado_nao_e_aceito_no_monte_carlo")),
    Requisito("R12", "Identificar variáveis críticas (sensibilidade, valores críticos e cenários)",
              "Seção 3.6", ("incerteza.sensibilidade", "incerteza.valores_criticos", "incerteza.cenarios"),
              ("test_evteas.py::test_sensibilidade_e_valores_criticos", "test_evteas.py::test_cenarios_ordenados")),
    Requisito("R13", "Comparar alternativas de projeto e explicitar trade-offs (TOPSIS)",
              "Objetivo específico 2", ("ponderacao.topsis", "pipeline.comparar_alternativas",
                                         "interface.definir_e_comparar_alternativas"),
              ("test_evteas.py::test_topsis_alternativa_dominante_vence", "test_evteas.py::test_comparar_alternativas")),
    Requisito("R14", "Verificar o próprio resultado a cada execução e manter testes de regressão",
              "Seção 3.3.2 (Boehm, 1984)", ("vv.validar_invariantes", "vv.teste_regressao_deterministica"),
              ("test_evteas.py::test_invariantes_aprovados", "test_evteas.py::test_regressao_embutida",
               "test_evteas.py::test_caso_controle_inviavel")),
    Requisito("R15", "Exportar resultados auditáveis (Excel, JSON, Markdown e figuras)",
              "Etapa 12", ("relatorios.exportar", "relatorios.gerar_graficos", "relatorios.resumo_executivo"),
              ("test_evteas.py::test_exportacao_e_graficos",)),
)


def _testes_existentes(pasta: Path) -> Dict[str, set]:
    nomes = {}
    for arq in sorted(pasta.glob("test_*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        nomes[arq.name] = {n.name for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    return nomes


def _objeto_existe(caminho: str) -> bool:
    modulo, _, nome = caminho.partition(".")
    try:
        return hasattr(importlib.import_module(f"evteas_py.{modulo}"), nome)
    except ImportError:                          # notebook autocontido: um único espaço de nomes
        return nome in globals()


def pasta_testes_padrao() -> Optional[Path]:
    arquivo = globals().get("__file__")          # ausente no notebook autocontido
    if not arquivo:
        return None
    p = Path(arquivo).resolve().parents[1] / "tests"
    return p if p.is_dir() else None


def matriz_rastreabilidade(pasta_testes: Optional[Path] = None,
                           requisitos: Sequence[Requisito] = REQUISITOS) -> pd.DataFrame:
    """Confere, no código e nos arquivos de teste, cada vínculo requisito → função → teste.

    Situação: "implementado e verificado" (todas as funções e testes existem),
    "implementado, sem teste" ou "pendente" (alguma função não existe). Sem a pasta
    de testes (por exemplo, no notebook autocontido), os testes não são conferidos.
    """
    pasta = Path(pasta_testes) if pasta_testes else pasta_testes_padrao()
    existentes = _testes_existentes(pasta) if pasta else None
    linhas = []
    for r in requisitos:
        faltam_f = [f for f in r.funcoes if not _objeto_existe(f)]
        if existentes is None:
            faltam_t, conferido = [], False
        else:
            faltam_t = [t for t in r.testes if t.split("::")[1] not in existentes.get(t.split("::")[0], set())]
            conferido = True
        if faltam_f:
            situacao = "pendente"
        elif not r.testes or len(faltam_t) == len(r.testes):
            situacao = "implementado, sem teste"
        elif faltam_t:
            situacao = "implementado, testes incompletos"
        else:
            situacao = "implementado e verificado" if conferido else "implementado (testes não conferidos)"
        linhas.append({"Requisito": r.codigo, "Descrição": r.descricao, "Origem": r.origem,
                       "Funções": ", ".join(r.funcoes), "Testes": len(r.testes) - len(faltam_t),
                       "Faltando": "; ".join(faltam_f + faltam_t), "Situação": situacao})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Etapa 9: aprendizagens explicitadas durante a construção
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Aprendizagem:
    numero: int
    dificuldade: str               # o que foi observado
    causa: str                     # por que ocorria
    decisao: str                   # o que mudou no artefato
    evidencia: str                 # teste ou função que impede a regressão


APRENDIZAGENS: Tuple[Aprendizagem, ...] = (
    Aprendizagem(1, "Na implementação inicial, a média do VPL simulado ficava acima do VPL determinístico, mesmo com riscos "
                    "desfavoráveis.",
                 "Monte Carlo usava um modelo anual simplificado, diferente do modelo mensal determinístico.",
                 "Motor único vetorizado: o mesmo código produz o resultado pontual (n = 1) e a simulação (n = 10.000).",
                 "test_evteas.py::test_monte_carlo_degenerado_igual_deterministico"),
    Aprendizagem(2, "TIR reportada como −0,95 em fluxos sem raiz, confundida com um resultado.",
                 "A bisseção devolvia o limite do intervalo quando não havia troca de sinal.",
                 "Varredura de malha seguida de bisseção, sempre com diagnóstico (convencional, múltiplas, múltiplas possíveis ou sem solução).",
                 "test_evteas.py::test_tir_sem_solucao_nao_vira_limite_numerico"),
    Aprendizagem(3, "Ecoeficiência igual a zero em projetos com prejuízo.",
                 "O numerador era zerado quando o lucro era negativo.",
                 "Ecoeficiência como valor adicionado por unidade de impacto (WBCSD, 2000), declarada indefinida quando o valor adicionado não é positivo.",
                 "test_evteas.py::test_ecoeficiencia_indefinida_quando_va_negativo"),
    Aprendizagem(4, "RVL e OEE divergiam das fórmulas do Quadro 5.",
                 "A RVL era dividida pela receita e a qualidade do OEE era um parâmetro independente.",
                 "RVL sobre o custo operacional; qualidade do OEE igual à sobrevivência.",
                 "test_social_lean_green.py::test_rvl_segue_formula_do_quadro_5"),
    Aprendizagem(5, "Rotinas de AHP e TOPSIS existiam, mas não eram chamadas pelo pipeline.",
                 "Funções desenvolvidas sem requisito e sem teste que as exigisse.",
                 "Rastreabilidade requisito → função → teste; AHP e TOPSIS integrados ao fluxo.",
                 "test_evteas.py::test_pipeline_com_pesos_likert_e_ahp"),
    Aprendizagem(6, "O notebook produzia resultados ao ser executado, antes de o usuário informar o projeto.",
                 "Premissas do caso ilustrativo funcionavam como valores padrão silenciosos.",
                 "Estudo começa pela entrada de dados; modo novo parte de configuração em branco e recusa pendências.",
                 "test_entradas.py::test_modo_novo_nao_aceita_enter_sem_referencia"),
    Aprendizagem(7, "Valores informados em reais (manutenção, valor residual) mudavam quando o CAPEX era revisto.",
                 "Eram convertidos e guardados como percentual do CAPEX.",
                 "Valores em reais guardados em reais; percentual apenas quando informado como percentual.",
                 "test_entradas_coerencia.py::test_valores_em_reais_nao_mudam_com_o_capex"),
    Aprendizagem(8, "Corrigir um bloco de entradas deixava distribuições e blocos dependentes incoerentes.",
                 "Cada bloco era tratado como independente, e as distribuições não acompanhavam o valor determinístico.",
                 "Dependências declaradas entre blocos e reposicionamento das distribuições na revisão.",
                 "test_entradas_coerencia.py::test_corrigir_preco_reposiciona_distribuicao"),
    Aprendizagem(9, "A rastreabilidade de requisitos revelou funções sociais, de governança e Lean-Green sem teste.",
                 "Os testes tinham sido escritos a partir dos cálculos financeiros, e não dos requisitos.",
                 "Testes dedicados para RVL, LSO, governança, ODS e Lean-Green.",
                 "test_social_lean_green.py::test_lso_e_risco_social"),
    Aprendizagem(10, "Valores digitados no padrão brasileiro (40.000) eram lidos como 40, sem aviso.",
                 "O conversor tratava todo ponto como separador decimal.",
                 "Ponto seguido de grupos de três dígitos é lido como milhar, e o valor interpretado é mostrado.",
                 "test_entradas_robustez.py::test_ponto_de_milhar_e_formato_sem_notacao_cientifica"),
    Aprendizagem(11, "Um arquivo de entradas incompleto ou de outro tipo era completado com o caso ilustrativo.",
                 "Os valores padrão das estruturas de configuração eram os do caso-base.",
                 "Leitura a partir de configuração em branco: o que falta vira pendência e obriga a revisão.",
                 "test_entradas_robustez.py::test_campos_ausentes_nao_viram_caso_ilustrativo"),
    Aprendizagem(12, "Incerteza informada em parâmetros que o motor não amostra não chegava ao resultado.",
                 "O wizard oferecia qualquer parâmetro numérico, mas só nove são lidos de forma vetorizada.",
                 "Lista única de variáveis estocásticas, verificada pelo próprio motor.",
                 "test_entradas_robustez.py::test_parametro_nao_amostrado_nao_e_aceito_no_monte_carlo"),
)


def aprendizagens() -> pd.DataFrame:
    return pd.DataFrame([{"Nº": a.numero, "Dificuldade observada": a.dificuldade, "Causa": a.causa,
                          "Decisão de projeto": a.decisao, "Evidência": a.evidencia} for a in APRENDIZAGENS])


def relatorio_dsr(pasta_testes: Optional[Path] = None) -> Dict[str, pd.DataFrame]:
    return {"DSR_Etapas": etapas_dsr(), "DSR_Comparacao": tabela_comparativa(),
            "DSR_Rastreabilidade": matriz_rastreabilidade(pasta_testes), "DSR_Aprendizagens": aprendizagens()}

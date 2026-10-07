"""EVTEAS-Py — módulo entradas.

Registro único das entradas do estudo (Quadro de premissas), com marcadores [E-xx] para o texto.
Nenhuma entrada do projeto tem valor predefinido: o usuário as informa pelo formulário do Colab,
pela planilha de entradas (.xlsx) ou pelo assistente interativo, e o estudo só é executado quando
todas as entradas obrigatórias estão preenchidas. Apenas os parâmetros do método (Monte Carlo,
pesos do preset e regra de decisão, descritos no Capítulo 3) vêm com valores documentados, que
podem ser alterados.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .config import (CATEGORIAS_FONTE, CHAVES_CHECKLIST_AMBIENTAL, CHAVES_GOVERNANCA, Distribuicao, EVTEASConfig,
                     Fonte, ItemCapex, Produto, Tributo, copiar, definir_por_caminho, fmt_num, obter_por_caminho)


@dataclass(frozen=True)
class Entrada:
    marcador: str            # identificador no texto: [E-T03]
    var: str                 # nome do campo no formulário e na planilha
    caminho: str             # caminho na configuração ("tecnico.area_lamina_m2")
    rotulo: str
    unidade: str
    tipo: str                # 'num', 'int', 'texto', 'opcao' ou 'bool'
    grupo: str
    obrigatorio: bool = True
    opcoes: Tuple[str, ...] = ()
    vazio: Any = None        # valor adotado quando a entrada opcional fica em branco
    minimo: Optional[float] = None
    maximo: Optional[float] = None
    ajuda: str = ""
    metodo: bool = False     # parâmetro do método (valor documentado no Capítulo 3)
    padrao: Any = None       # valor documentado do parâmetro do método


def _E(*a, **k) -> Entrada:
    return Entrada(*a, **k)


GRUPOS = ["Identificação", "Técnica", "Econômica", "Ambiental", "Social", "Governança", "Lean-Green",
          "Parâmetros do método"]

ROTULOS_CHECKLIST = {
    "licenca_ambiental": "Licença ambiental da aquicultura (eliminatório)",
    "outorga_agua": "Outorga de direito de uso da água (eliminatório)",
    "app_respeitada": "Área de Preservação Permanente respeitada (eliminatório)",
    "tratamento_efluentes": "Tratamento de efluentes",
    "monitoramento_agua": "Monitoramento da qualidade da água",
    "car": "Cadastro Ambiental Rural (CAR)",
    "plano_residuos": "Plano de gestão de resíduos",
    "prevencao_escape": "Prevenção de escape de peixes",
    "energia_renovavel": "Uso de energia renovável",
}
ROTULOS_GOVERNANCA = {
    "estatuto_registrado": "Estatuto social registrado",
    "assembleias_regulares": "Assembleias regulares",
    "conselho_fiscal": "Conselho fiscal atuante",
    "prestacao_contas_publica": "Prestação de contas pública",
    "plano_negocios": "Plano de negócios aprovado",
    "registro_premissas_auditavel": "Registro auditável das premissas",
    "canal_denuncia": "Canal de denúncia",
}

ENTRADAS: List[Entrada] = [
    # Identificação
    _E("E-I01", "projeto", "projeto", "Nome do projeto", "—", "texto", "Identificação"),
    _E("E-I02", "localizacao", "localizacao", "Localização (município/UF)", "—", "texto", "Identificação", False, vazio=""),
    _E("E-I03", "responsavel", "responsavel", "Responsável pelo estudo", "—", "texto", "Identificação", False, vazio=""),
    # Técnica
    _E("E-T01", "especie", "tecnico.especie", "Espécie cultivada", "—", "texto", "Técnica"),
    _E("E-T02", "sistema_produtivo", "tecnico.sistema_produtivo", "Sistema produtivo", "—", "opcao", "Técnica",
       opcoes=("extensivo", "semi-intensivo", "intensivo", "superintensivo")),
    _E("E-T03", "area_lamina_m2", "tecnico.area_lamina_m2", "Área de lâmina d'água", "m²", "num", "Técnica", minimo=1),
    _E("E-T04", "profundidade_media_m", "tecnico.profundidade_media_m", "Profundidade média", "m", "num", "Técnica",
       minimo=0.1, maximo=20),
    _E("E-T05", "numero_tanques", "tecnico.numero_tanques", "Número de viveiros/tanques", "un.", "int", "Técnica", minimo=1),
    _E("E-T06", "tanques_ativos", "tecnico.tanques_ativos", "Viveiros/tanques em operação simultânea", "un.", "int",
       "Técnica", minimo=0),
    _E("E-T07", "capacidade_suporte_kg_m3", "tecnico.capacidade_suporte_kg_m3", "Capacidade de suporte", "kg/m³", "num",
       "Técnica", False, vazio=0.0, minimo=0, ajuda="Em branco: valor de referência do sistema produtivo (Kubitza, 2017)"),
    _E("E-T08", "peso_inicial_g", "tecnico.peso_inicial_g", "Peso inicial dos juvenis", "g", "num", "Técnica", minimo=0.01),
    _E("E-T09", "peso_final_g", "tecnico.peso_final_g", "Peso de abate", "g", "num", "Técnica", minimo=0.01),
    _E("E-T10", "ciclo_dias", "tecnico.ciclo_dias", "Duração do ciclo de engorda", "dias", "int", "Técnica",
       minimo=1, maximo=730),
    _E("E-T11", "ciclos_ano", "tecnico.ciclos_ano", "Ciclos por ano", "ciclos/ano", "num", "Técnica", minimo=0.01),
    _E("E-T12", "produtividade_esperada_kg_m2_ciclo", "tecnico.produtividade_esperada_kg_m2_ciclo",
       "Produtividade esperada por área", "kg/m²/ciclo", "num", "Técnica", False, vazio=0.0, minimo=0,
       ajuda="Em branco: sem restrição por área (vale só a capacidade de suporte)"),
    _E("E-T13", "alevinos_por_ciclo", "tecnico.alevinos_por_ciclo", "Juvenis estocados por ciclo", "un./ciclo", "num",
       "Técnica", False, vazio=0.0, minimo=0, ajuda="Em branco: estocagem dimensionada pelo modelo"),
    _E("E-T14", "fcr", "tecnico.fcr", "Conversão alimentar aparente (FCR)", "kg ração/kg", "num", "Técnica",
       minimo=0.1, maximo=10),
    _E("E-T15", "mortalidade_pct", "tecnico.mortalidade_pct", "Mortalidade no ciclo", "%", "num", "Técnica",
       minimo=0, maximo=99.9),
    # Econômica
    _E("E-E01", "tipo_organizacao", "economico.tipo_organizacao", "Tipo de organização", "—", "opcao", "Econômica",
       opcoes=("cooperativa", "associação", "empresa")),
    _E("E-E02", "capital_giro", "economico.capital_giro", "Capital de giro", "R$", "num", "Econômica", minimo=0),
    _E("E-E03", "valor_residual_pct", "economico.valor_residual_pct", "Valor residual ao fim do horizonte",
       "% do CAPEX", "num", "Econômica", minimo=0, maximo=100),
    _E("E-E04", "fomento_nao_reembolsavel_pct", "economico.fomento_nao_reembolsavel_pct",
       "Fomento não reembolsável", "% do CAPEX", "num", "Econômica", minimo=0, maximo=100),
    _E("E-E05", "preco_venda_kg", "economico.preco_venda_kg", "Preço de venda", "R$/kg", "num", "Econômica",
       minimo=0.01),
    _E("E-E06", "receita_servicos_mes", "economico.receita_servicos_mes", "Outras receitas (serviços)", "R$/mês", "num",
       "Econômica", False, vazio=0.0, minimo=0),
    _E("E-E07", "custo_racao_kg", "economico.custo_racao_kg", "Custo da ração", "R$/kg", "num", "Econômica", minimo=0.01),
    _E("E-E08", "custo_alevino_milheiro", "economico.custo_alevino_milheiro", "Custo do milheiro de juvenis", "R$/mil",
       "num", "Econômica", minimo=0),
    _E("E-E09", "tarifa_energia_kwh", "economico.tarifa_energia_kwh", "Tarifa de energia elétrica", "R$/kWh", "num",
       "Econômica", minimo=0),
    _E("E-E10", "outros_variaveis_kg", "economico.outros_variaveis_kg",
       "Outros custos variáveis (embalagem, gelo, frete, comercialização)", "R$/kg", "num", "Econômica", minimo=0),
    _E("E-E11", "mao_obra_mes", "economico.mao_obra_mes", "Retiradas/salários", "R$/mês", "num", "Econômica", minimo=0),
    _E("E-E12", "encargos_pct", "economico.encargos_pct", "Encargos sobre retiradas/salários", "%", "num", "Econômica",
       minimo=0, maximo=200),
    _E("E-E13", "cooperados_trabalhadores", "economico.cooperados_trabalhadores", "Cooperados/trabalhadores", "pessoas",
       "int", "Econômica", minimo=0),
    _E("E-E14", "perc_sobras_trabalhadores", "economico.perc_sobras_trabalhadores",
       "Sobras distribuídas aos trabalhadores", "%", "num", "Econômica", minimo=0, maximo=100),
    _E("E-E15", "manutencao_pct_capex_ano", "economico.manutencao_pct_capex_ano", "Manutenção", "% do CAPEX/ano", "num",
       "Econômica", minimo=0, maximo=100),
    _E("E-E16", "administrativo_mes", "economico.administrativo_mes", "Despesas administrativas", "R$/mês", "num",
       "Econômica", minimo=0),
    _E("E-E17", "seguros_outros_fixos_mes", "economico.seguros_outros_fixos_mes", "Seguros e outros custos fixos",
       "R$/mês", "num", "Econômica", minimo=0),
    _E("E-E18", "tributos_faturamento_pct", "economico.tributos#faturamento", "Tributos sobre o faturamento", "%",
       "num", "Econômica", minimo=0, maximo=100),
    _E("E-E19", "tributos_resultado_pct", "economico.tributos#lucro", "Tributos sobre o resultado", "%", "num",
       "Econômica", minimo=0, maximo=100),
    _E("E-E20", "tma_aa_pct", "economico.tma_aa_pct", "Taxa mínima de atratividade (TMA)", "% a.a.", "num", "Econômica",
       minimo=0, maximo=100),
    _E("E-E21", "horizonte_anos", "economico.horizonte_anos", "Horizonte de análise", "anos", "int", "Econômica",
       minimo=1, maximo=40),
    _E("E-E22", "rampa_inicial_pct", "economico.rampa_inicial_pct", "Produção inicial da rampa", "% do regime", "num",
       "Econômica", minimo=0, maximo=100),
    _E("E-E23", "rampa_meses", "economico.rampa_meses", "Duração da rampa de produção", "meses", "int", "Econômica",
       minimo=0, maximo=120),
    _E("E-E24", "ano_regime", "economico.ano_regime", "Ano de regime (indicadores anuais)", "ano", "int", "Econômica",
       minimo=1, maximo=40),
    # Ambiental
    _E("E-A01", "renovacao_agua_pct_dia", "ambiental.renovacao_agua_pct_dia", "Renovação de água", "% do volume/dia",
       "num", "Ambiental", minimo=0, maximo=100),
    _E("E-A02", "enchimentos_ano", "ambiental.enchimentos_ano", "Enchimentos completos dos viveiros", "por ano", "num",
       "Ambiental", minimo=0),
    _E("E-A03", "evaporacao_mm_dia", "ambiental.evaporacao_mm_dia", "Evaporação", "mm/dia", "num", "Ambiental", minimo=0),
    _E("E-A04", "infiltracao_mm_dia", "ambiental.infiltracao_mm_dia", "Infiltração", "mm/dia", "num", "Ambiental",
       minimo=0),
    _E("E-A05", "metodo_tratamento", "ambiental.metodo_tratamento", "Método de tratamento de efluentes", "—", "texto",
       "Ambiental"),
    _E("E-A06", "remocao_n_tratamento_pct", "ambiental.remocao_n_tratamento_pct", "Remoção de nitrogênio no tratamento",
       "%", "num", "Ambiental", minimo=0, maximo=100),
    _E("E-A07", "remocao_p_tratamento_pct", "ambiental.remocao_p_tratamento_pct", "Remoção de fósforo no tratamento", "%",
       "num", "Ambiental", minimo=0, maximo=100),
    _E("E-A08", "proteina_racao_pct", "ambiental.proteina_racao_pct", "Proteína bruta da ração", "%", "num", "Ambiental",
       minimo=0, maximo=100),
    _E("E-A09", "fosforo_racao_pct", "ambiental.fosforo_racao_pct", "Fósforo da ração", "%", "num", "Ambiental",
       minimo=0, maximo=100),
    _E("E-A10", "nitrogenio_peixe_pct", "ambiental.nitrogenio_peixe_pct", "Nitrogênio retido na biomassa", "% do peso",
       "num", "Ambiental", minimo=0, maximo=100),
    _E("E-A11", "fosforo_peixe_pct", "ambiental.fosforo_peixe_pct", "Fósforo retido na biomassa", "% do peso", "num",
       "Ambiental", minimo=0, maximo=100),
    _E("E-A12", "classe_corpo_receptor", "ambiental.classe_corpo_receptor", "Classe e ambiente do corpo receptor", "—",
       "texto", "Ambiental", ajuda="Ex.: classe 2, ambiente lótico (Resolução CONAMA nº 357/2005)"),
    _E("E-A13", "n_max_mg_l", "ambiental.n_max_mg_l", "Concentração máxima de N total (padrão da classe)", "mg/L", "num",
       "Ambiental", minimo=0),
    _E("E-A14", "n_natural_mg_l", "ambiental.n_natural_mg_l", "Concentração natural de N total", "mg/L", "num",
       "Ambiental", minimo=0),
    _E("E-A15", "p_max_mg_l", "ambiental.p_max_mg_l", "Concentração máxima de P total (padrão da classe)", "mg/L", "num",
       "Ambiental", minimo=0),
    _E("E-A16", "p_natural_mg_l", "ambiental.p_natural_mg_l", "Concentração natural de P total", "mg/L", "num",
       "Ambiental", minimo=0),
    _E("E-A17", "fonte_energia", "ambiental.fonte_energia", "Fonte principal de energia", "—", "opcao", "Ambiental",
       opcoes=("rede", "solar", "biomassa")),
    _E("E-A18", "fracao_renovavel_pct", "ambiental.fracao_renovavel_pct", "Energia renovável de fonte própria", "%",
       "num", "Ambiental", minimo=0, maximo=100),
    _E("E-A19", "consumo_kwh_kg", "ambiental.consumo_kwh_kg", "Consumo de energia (aeração e bombeamento)", "kWh/kg",
       "num", "Ambiental", minimo=0),
    _E("E-A20", "fator_emissao_rede_kg_kwh", "ambiental.fator_emissao_rede_kg_kwh", "Fator de emissão da rede elétrica",
       "kgCO2e/kWh", "num", "Ambiental", minimo=0),
    _E("E-A21", "fator_emissao_racao_kgco2e_kg", "ambiental.fator_emissao_racao_kgco2e_kg", "Fator de emissão da ração",
       "kgCO2e/kg", "num", "Ambiental", minimo=0),
    _E("E-A22", "diesel_l_ano", "ambiental.diesel_l_ano", "Consumo de diesel", "L/ano", "num", "Ambiental", minimo=0),
    _E("E-A23", "fator_emissao_diesel_kg_l", "ambiental.fator_emissao_diesel_kg_l", "Fator de emissão do diesel",
       "kgCO2e/L", "num", "Ambiental", minimo=0),
    _E("E-A24", "distancia_app_m", "ambiental.distancia_app_m", "Distância dos viveiros ao curso d'água", "m", "num",
       "Ambiental", minimo=0),
    _E("E-A25", "distancia_minima_app_m", "ambiental.distancia_minima_app_m", "Largura mínima da APP aplicável", "m",
       "num", "Ambiental", minimo=0),
] + [
    _E(f"E-A{26 + i:02d}", f"amb_{k}", f"ambiental.checklist.{k}", ROTULOS_CHECKLIST[k], "sim/não", "bool", "Ambiental")
    for i, k in enumerate(CHAVES_CHECKLIST_AMBIENTAL)
] + [
    # Social
    _E("E-S01", "empregos_diretos", "social.empregos_diretos", "Empregos diretos", "postos", "int", "Social", minimo=0),
    _E("E-S02", "empregos_indiretos", "social.empregos_indiretos", "Empregos indiretos", "postos", "int", "Social",
       minimo=0),
    _E("E-S03", "mao_obra_local_pct", "social.mao_obra_local_pct", "Mão de obra local", "%", "num", "Social", minimo=0,
       maximo=100),
    _E("E-S04", "compras_locais_pct", "social.compras_locais_pct", "Compras de insumos no município/região", "%", "num",
       "Social", minimo=0, maximo=100),
    _E("E-S05", "salario_minimo", "social.salario_minimo", "Salário mínimo vigente", "R$/mês", "num", "Social",
       minimo=1),
    _E("E-S06", "aderencia_nr", "social.aderencia_nr", "Aderência às Normas Regulamentadoras", "sim/não", "bool",
       "Social"),
    _E("E-S07", "programa_capacitacao", "social.programa_capacitacao", "Programa de capacitação", "sim/não", "bool",
       "Social"),
    _E("E-S08", "participacao_mulheres_pct", "social.participacao_mulheres_pct", "Participação de mulheres", "%", "num",
       "Social", minimo=0, maximo=100),
    _E("E-S09", "relacao_comunidade", "social.relacao_comunidade", "Relação com a comunidade", "—", "opcao", "Social",
       opcoes=("inexistente", "parcial", "consolidada")),
    _E("E-S10", "canais_formais_comunicacao", "social.canais_formais_comunicacao", "Canais formais de comunicação",
       "sim/não", "bool", "Social"),
    _E("E-S11", "reunioes_comunidade_ano", "social.reunioes_comunidade_ano", "Reuniões com a comunidade", "por ano",
       "int", "Social", minimo=0),
    _E("E-S12", "conflitos_registrados_ano", "social.conflitos_registrados_ano", "Conflitos registrados", "por ano",
       "int", "Social", minimo=0),
] + [
    _E(f"E-G{1 + i:02d}", f"gov_{k}", f"governanca.itens.{k}", ROTULOS_GOVERNANCA[k], "sim/não", "bool", "Governança")
    for i, k in enumerate(CHAVES_GOVERNANCA)
] + [
    # Lean-Green
    _E("E-L01", "fcr_referencia", "lean_green.fcr_referencia", "FCR de referência (boa prática)", "kg/kg", "num",
       "Lean-Green", minimo=0.1),
    _E("E-L02", "mortalidade_referencia_pct", "lean_green.mortalidade_referencia_pct", "Mortalidade de referência", "%",
       "num", "Lean-Green", minimo=0, maximo=99),
    _E("E-L03", "consumo_kwh_kg_referencia", "lean_green.consumo_kwh_kg_referencia", "Consumo de energia de referência",
       "kWh/kg", "num", "Lean-Green", minimo=0),
    # Parâmetros do método (Capítulo 3) — valores documentados, alteráveis
    _E("E-M01", "mc_iteracoes", "monte_carlo.iteracoes", "Iterações do Monte Carlo", "iterações", "int",
       "Parâmetros do método", minimo=100, maximo=500_000, metodo=True, padrao=10_000),
    _E("E-M02", "mc_semente", "monte_carlo.seed", "Semente do gerador pseudoaleatório", "—", "int",
       "Parâmetros do método", minimo=0, metodo=True, padrao=20260612),
    _E("E-M03", "mc_nivel_confianca", "monte_carlo.nivel_confianca", "Nível de confiança", "fração", "num",
       "Parâmetros do método", minimo=0.5, maximo=0.999, metodo=True, padrao=0.95),
    _E("E-M04", "pesos_metodo", "pesos.metodo", "Método de ponderação", "—", "opcao", "Parâmetros do método",
       opcoes=("preset", "likert", "ahp"), metodo=True, padrao="preset"),
    _E("E-M05", "peso_tecnica", "pesos.preset.tecnica", "Peso da dimensão técnica (preset)", "fração", "num",
       "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.25),
    _E("E-M06", "peso_economica", "pesos.preset.economica", "Peso da dimensão econômica (preset)", "fração", "num",
       "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.35),
    _E("E-M07", "peso_ambiental", "pesos.preset.ambiental", "Peso da dimensão ambiental (preset)", "fração", "num",
       "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.20),
    _E("E-M08", "peso_social", "pesos.preset.social", "Peso da dimensão social (preset)", "fração", "num",
       "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.20),
    _E("E-M09", "aplicar_vetos", "decisao.aplicar_vetos", "Aplicar vetos não compensatórios", "sim/não", "bool",
       "Parâmetros do método", metodo=True, padrao=True),
    _E("E-M10", "lso_minimo", "decisao.lso_minimo", "LSO mínima", "0–100", "num", "Parâmetros do método",
       minimo=0, maximo=100, metodo=True, padrao=40.0),
    _E("E-M11", "limiar_indice_viavel", "decisao.limiar_indice_viavel", "Limiar do índice para 'viável'", "0–1", "num",
       "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.60),
    _E("E-M12", "limiar_indice_ressalvas", "decisao.limiar_indice_ressalvas", "Limiar do índice para 'com ressalvas'",
       "0–1", "num", "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.50),
    _E("E-M13", "prob_vpl_positivo_minima", "decisao.prob_vpl_positivo_minima", "Probabilidade mínima de VPL > 0",
       "fração", "num", "Parâmetros do método", minimo=0, maximo=1, metodo=True, padrao=0.70),
]

POR_VAR: Dict[str, Entrada] = {e.var: e for e in ENTRADAS}
POR_CAMINHO: Dict[str, Entrada] = {e.caminho: e for e in ENTRADAS}
POR_MARCADOR: Dict[str, Entrada] = {e.marcador: e for e in ENTRADAS}

# Premissas incertas (Quadro 13): informe "mín; máx" (a moda é o valor determinístico informado)
# ou "mín; moda; máx" (a moda deve coincidir com o valor informado). Em branco = determinística.
DISTRIBUICOES = [
    ("E-D01", "dist_preco_venda_kg", "economico.preco_venda_kg", "Preço de venda", "R$/kg"),
    ("E-D02", "dist_custo_racao_kg", "economico.custo_racao_kg", "Custo da ração", "R$/kg"),
    ("E-D03", "dist_custo_alevino_milheiro", "economico.custo_alevino_milheiro", "Custo do milheiro de juvenis", "R$/mil"),
    ("E-D04", "dist_tarifa_energia_kwh", "economico.tarifa_energia_kwh", "Tarifa de energia", "R$/kWh"),
    ("E-D05", "dist_custos_fixos_fator", "economico.custos_fixos_fator", "Fator de custos fixos (moda = 1)", "fator"),
    ("E-D06", "dist_capex_fator", "economico.capex_fator", "Fator de CAPEX (moda = 1)", "fator"),
    ("E-D07", "dist_fcr", "tecnico.fcr", "Conversão alimentar (FCR)", "kg/kg"),
    ("E-D08", "dist_mortalidade_pct", "tecnico.mortalidade_pct", "Mortalidade", "%"),
    ("E-D09", "dist_desempenho_crescimento_pct", "tecnico.desempenho_crescimento_pct",
     "Desempenho de crescimento (moda = 100)", "%"),
]
N_CAPEX = 12
CAMPOS_ALTERNATIVAS = ("B", "C")


class EntradasInvalidas(ValueError):
    """Entradas em branco ou inválidas; ``erros`` lista cada problema com o seu marcador."""

    def __init__(self, erros: List[str]):
        self.erros = list(erros)
        super().__init__("Entradas em branco ou inválidas:\n- " + "\n- ".join(self.erros))


# ---------------------------------------------------------------------------------------------
# Conversão de textos digitados (vírgula decimal, sim/não, opções sem acento)
# ---------------------------------------------------------------------------------------------
def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn").lower().strip()


def ler_numero(texto) -> float:
    """'1.234,56' -> 1234.56; '1,5' -> 1.5; '1500' -> 1500; aceita R$, %, espaços e sinal '−'."""
    if isinstance(texto, bool):
        raise ValueError("valor lógico não é número")
    if isinstance(texto, (int, float)):
        return float(texto)
    t = str(texto).strip().replace("R$", "").replace("%", "").replace(" ", "").replace(" ", "").replace("−", "-")
    if not t:
        raise ValueError("vazio")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        if t.count(",") > 1:
            raise ValueError(f"número inválido: {texto!r}")
        t = t.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        raise ValueError(f"número inválido: {texto!r}") from None


def ler_bool(texto) -> bool:
    if isinstance(texto, bool):
        return texto
    t = _sem_acento(texto)
    if t in ("sim", "s", "yes", "y", "true", "verdadeiro", "1", "x", "atendido"):
        return True
    if t in ("nao", "n", "no", "false", "falso", "0", "nao atendido"):
        return False
    raise ValueError(f"responda sim ou não: {texto!r}")


def _vazio(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, float) and v != v)


def converter(entrada: Entrada, texto) -> Any:
    """Converte e valida o texto digitado para o tipo da entrada (ValueError com mensagem clara)."""
    if entrada.tipo == "texto":
        return str(texto).strip()
    if entrada.tipo == "bool":
        return ler_bool(texto)
    if entrada.tipo == "opcao":
        alvo = _sem_acento(texto)
        for op in entrada.opcoes:
            if _sem_acento(op) == alvo:
                return op
        raise ValueError(f"opção inválida {texto!r}; use uma de: {', '.join(entrada.opcoes)}")
    v = ler_numero(texto)
    if entrada.tipo == "int":
        if abs(v - round(v)) > 1e-9:
            raise ValueError(f"informe um número inteiro: {texto!r}")
        v = int(round(v))
    if entrada.minimo is not None and v < entrada.minimo:
        raise ValueError(f"valor {fmt_auto(v)} abaixo do mínimo admitido ({fmt_auto(entrada.minimo)})")
    if entrada.maximo is not None and v > entrada.maximo:
        raise ValueError(f"valor {fmt_auto(v)} acima do máximo admitido ({fmt_auto(entrada.maximo)})")
    return v


def fmt_auto(v) -> str:
    """Formata número em pt-BR com as casas decimais necessárias (até 4)."""
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, (int, float)):
        if float(v).is_integer():
            return fmt_num(v, 0)
        s = fmt_num(v, 4).rstrip("0")
        return s[:-1] if s.endswith(",") else s
    return str(v)


def tipo_do_caminho(caminho: str) -> str:
    e = POR_CAMINHO.get(caminho)
    return e.tipo if e else "num"


# ---------------------------------------------------------------------------------------------
# Leitura e escrita de valores na configuração
# ---------------------------------------------------------------------------------------------
_NOME_TRIBUTO = {"faturamento": "Tributos sobre o faturamento", "lucro": "Tributos sobre o resultado"}


def obter_valor(cfg: EVTEASConfig, entrada: Entrada):
    if "#" in entrada.caminho:
        base = entrada.caminho.split("#")[1]
        trib = [t for t in cfg.economico.tributos if t.base == base]
        if trib:
            return sum(t.aliquota_pct for t in trib)
        return None if not cfg.economico.tributos else 0.0
    try:
        return obter_por_caminho(cfg, entrada.caminho)
    except KeyError:
        return None


def definir_valor(cfg: EVTEASConfig, entrada: Entrada, valor) -> None:
    if "#" in entrada.caminho:
        base = entrada.caminho.split("#")[1]
        cfg.economico.tributos = [t for t in cfg.economico.tributos if t.base != base]
        cfg.economico.tributos.append(Tributo(_NOME_TRIBUTO[base], float(valor), base))
        return
    if entrada.caminho in ("projeto", "localizacao", "responsavel"):
        setattr(cfg, entrada.caminho, valor)
        return
    if entrada.tipo in ("texto", "opcao"):
        bloco, campo = entrada.caminho.split(".", 1)
        setattr(getattr(cfg, bloco), campo, valor)
        return
    definir_por_caminho(cfg, entrada.caminho, valor)


def config_vazia() -> EVTEASConfig:
    """Configuração sem nenhuma entrada do projeto (apenas os parâmetros do método)."""
    return EVTEASConfig()


def entradas_faltantes(cfg: EVTEASConfig) -> List[str]:
    """Entradas obrigatórias em branco, no formato '[E-xx] Rótulo (unidade)'."""
    faltam = []
    for e in ENTRADAS:
        if e.obrigatorio and _vazio(obter_valor(cfg, e)):
            faltam.append(f"[{e.marcador}] {e.rotulo} ({e.unidade})")
    if not cfg.economico.capex:
        faltam.append("[E-C] Itens de investimento (CAPEX)")
    return faltam


# ---------------------------------------------------------------------------------------------
# Listas: CAPEX, mix de produtos, distribuições, alterações das alternativas e fontes
# ---------------------------------------------------------------------------------------------
def _partes(texto: str, sep: str = ";") -> List[str]:
    return [p.strip() for p in str(texto).split(sep) if p.strip()]


def ler_item_capex(texto: str) -> ItemCapex:
    """'Escavação dos viveiros; 380.000; 20' -> ItemCapex (descrição; valor em R$; vida útil em anos)."""
    p = _partes(texto)
    if len(p) != 3:
        raise ValueError(f"use 'descrição; valor; vida útil (anos)': {texto!r}")
    valor, vida = ler_numero(p[1]), ler_numero(p[2])
    if valor < 0 or vida <= 0:
        raise ValueError(f"valor negativo ou vida útil não positiva: {texto!r}")
    return ItemCapex(p[0], valor, vida)


def ler_mix(texto: str) -> List[Produto]:
    """'Inteira; 0,7; 1 | Filé; 0,3; 2,4' -> lista de produtos (nome; participação; fator de preço)."""
    itens = []
    for bloco in _partes(texto, "|"):
        p = _partes(bloco)
        if len(p) != 3:
            raise ValueError(f"use 'nome; participação; fator de preço': {bloco!r}")
        itens.append(Produto(p[0], ler_numero(p[1]), ler_numero(p[2])))
    return itens


def ler_distribuicao(texto: str, valor_deterministico: float) -> Distribuicao:
    """'mín; máx' (moda = valor determinístico) ou 'mín; moda; máx'."""
    p = [ler_numero(x) for x in _partes(texto)]
    if len(p) == 2:
        return Distribuicao("triangular", p[0], float(valor_deterministico), p[1])
    if len(p) == 3:
        return Distribuicao("triangular", p[0], p[1], p[2])
    raise ValueError(f"use 'mín; máx' ou 'mín; moda; máx': {texto!r}")


def ler_alteracoes(texto: str) -> Dict[str, Any]:
    """'fonte_energia = solar; fracao_renovavel_pct = 90' -> {var: valor convertido}."""
    alt = {}
    for par in _partes(texto):
        if "=" not in par:
            raise ValueError(f"use 'variável = valor': {par!r}")
        var, val = (x.strip() for x in par.split("=", 1))
        if var not in POR_VAR:
            raise ValueError(f"variável desconhecida {var!r} (use os nomes do formulário)")
        alt[var] = converter(POR_VAR[var], val)
    return alt


def ler_fontes(texto: str) -> Dict[str, Fonte]:
    """'preco_venda_kg = cotação (CEASA-RJ, jun. 2026); fcr = parâmetro bibliográfico (Kubitza, 2017)'."""
    fontes = {}
    for par in _partes(texto):
        if "=" not in par:
            raise ValueError(f"use 'variável = categoria (referência)': {par!r}")
        var, resto = (x.strip() for x in par.split("=", 1))
        caminho = POR_VAR[var].caminho if var in POR_VAR else None
        if caminho is None:
            raise ValueError(f"variável desconhecida em fontes: {var!r}")
        m = re.match(r"([^()]+)(\((.*)\))?", resto)
        cat = _sem_acento(m.group(1)) if m else ""
        categoria = next((c for c in CATEGORIAS_FONTE if _sem_acento(c).startswith(cat) or cat.startswith(_sem_acento(c))),
                         None)
        if categoria is None:
            raise ValueError(f"categoria de fonte inválida em {par!r}; use uma de {CATEGORIAS_FONTE}")
        fontes[caminho] = Fonte(categoria, (m.group(3) or "").strip() if m else "")
    return fontes


# ---------------------------------------------------------------------------------------------
# Construção da configuração a partir do formulário (dicionário var -> texto)
# ---------------------------------------------------------------------------------------------
def campos_formulario() -> List[str]:
    nomes = [e.var for e in ENTRADAS] + [f"capex_{i:02d}" for i in range(1, N_CAPEX + 1)] + ["mix_produtos"]
    nomes += [d[1] for d in DISTRIBUICOES] + ["fontes"]
    for a in CAMPOS_ALTERNATIVAS:
        nomes += [f"alt_{a}_nome", f"alt_{a}_alteracoes", f"alt_{a}_capex_adicional"]
    return nomes


def coletar_formulario(namespace: Dict[str, Any]) -> Dict[str, Any]:
    """Recolhe do namespace do notebook (globals()) os campos do formulário."""
    return {k: namespace[k] for k in campos_formulario() if k in namespace}


def ler_formulario(valores: Dict[str, Any], base: Optional[EVTEASConfig] = None) -> Tuple[EVTEASConfig, List[str]]:
    """Monta a configuração e devolve (cfg, erros). Campos em branco: obrigatórios geram erro;
    opcionais recebem o valor 'não se aplica'; parâmetros do método mantêm o valor documentado."""
    cfg = copiar(base) if base is not None else config_vazia()
    erros: List[str] = []
    for e in ENTRADAS:
        bruto = valores.get(e.var)
        if _vazio(bruto):
            if base is not None and not _vazio(obter_valor(cfg, e)):
                continue
            if e.metodo:
                continue
            if not e.obrigatorio:
                definir_valor(cfg, e, e.vazio)
                continue
            erros.append(f"[{e.marcador}] {e.rotulo} ({e.unidade}): em branco")
            continue
        try:
            definir_valor(cfg, e, converter(e, bruto))
        except ValueError as exc:
            erros.append(f"[{e.marcador}] {e.rotulo}: {exc}")
    capex = []
    for i in range(1, N_CAPEX + 1):
        t = valores.get(f"capex_{i:02d}")
        if not _vazio(t):
            try:
                capex.append(ler_item_capex(t))
            except ValueError as exc:
                erros.append(f"[E-C{i:02d}] Item de CAPEX {i}: {exc}")
    if capex:
        cfg.economico.capex = capex
    elif not cfg.economico.capex:
        erros.append("[E-C] Itens de investimento (CAPEX): informe ao menos um item ('descrição; valor; vida útil')")
    if not _vazio(valores.get("mix_produtos")):
        try:
            cfg.economico.mix_produtos = ler_mix(valores["mix_produtos"])
        except ValueError as exc:
            erros.append(f"[E-E25] Mix de produtos: {exc}")
    for marcador, var, caminho, rot, _ in DISTRIBUICOES:
        t = valores.get(var)
        if _vazio(t):
            continue
        try:
            atual = obter_por_caminho(cfg, caminho)
            if atual is None:
                raise ValueError("informe primeiro o valor determinístico desta premissa")
            cfg.distribuicoes[caminho] = ler_distribuicao(t, float(atual))
        except ValueError as exc:
            erros.append(f"[{marcador}] Distribuição de {rot}: {exc}")
    if not _vazio(valores.get("fontes")):
        try:
            cfg.fontes.update(ler_fontes(valores["fontes"]))
        except ValueError as exc:
            erros.append(f"Fontes das premissas: {exc}")
    if not erros:
        from .config import validar_config
        erros += validar_config(cfg)
    return cfg, erros


def config_de_formulario(valores: Dict[str, Any], base: Optional[EVTEASConfig] = None) -> EVTEASConfig:
    cfg, erros = ler_formulario(valores, base)
    if erros:
        raise EntradasInvalidas(erros)
    return cfg


# ---------------------------------------------------------------------------------------------
# Alternativas de projeto definidas pelo usuário (comparação por TOPSIS)
# ---------------------------------------------------------------------------------------------
def criar_alternativa(base: EVTEASConfig, nome: str, alteracoes: Dict[str, Any],
                      capex_adicional: Optional[List[ItemCapex]] = None) -> EVTEASConfig:
    cfg = copiar(base)
    cfg.projeto = nome
    for var, valor in alteracoes.items():
        definir_valor(cfg, POR_VAR[var], valor)
    if capex_adicional:
        cfg.economico.capex = list(cfg.economico.capex) + list(capex_adicional)
    # Distribuições acompanham o novo valor determinístico (mantida a amplitude relativa)
    for caminho, d in list(cfg.distribuicoes.items()):
        novo = float(obter_por_caminho(cfg, caminho))
        antigo = float(obter_por_caminho(base, caminho))
        if abs(novo - antigo) > 1e-12 and antigo:
            f = novo / antigo
            cfg.distribuicoes[caminho] = Distribuicao(d.tipo, d.minimo * f, novo, d.maximo * f)
    return cfg


def alternativas_de_formulario(base: EVTEASConfig, valores: Dict[str, Any]) -> Dict[str, EVTEASConfig]:
    """Alternativa A = entradas informadas; B e C = alterações declaradas no formulário (opcionais)."""
    alts = {"A": copiar(base)}
    erros = []
    for a in CAMPOS_ALTERNATIVAS:
        nome = valores.get(f"alt_{a}_nome")
        if _vazio(nome):
            continue
        try:
            alt = ler_alteracoes(valores.get(f"alt_{a}_alteracoes") or "")
            capex = [ler_item_capex(b) for b in _partes(valores.get(f"alt_{a}_capex_adicional") or "", "|")]
            if not alt and not capex:
                raise ValueError("declare ao menos uma alteração ou um item de CAPEX adicional")
            alts[a] = criar_alternativa(base, str(nome).strip(), alt, capex)
        except ValueError as exc:
            erros.append(f"[E-X{a}] Alternativa {a}: {exc}")
    if erros:
        raise EntradasInvalidas(erros)
    return alts


# ---------------------------------------------------------------------------------------------
# Quadro de premissas e marcadores [E-xx]
# ---------------------------------------------------------------------------------------------
def _origem(cfg: EVTEASConfig, caminho: str) -> str:
    f = cfg.fontes.get(caminho)
    if f is None:
        return "não informada"
    return f.categoria + (f" ({f.referencia})" if f.referencia else "")


def tabela_entradas(cfg: EVTEASConfig, incluir_metodo: bool = True) -> pd.DataFrame:
    linhas = []
    for e in ENTRADAS:
        if e.metodo and not incluir_metodo:
            continue
        v = obter_valor(cfg, e)
        if not e.obrigatorio and (v == e.vazio or _vazio(v)):
            txt = "não se aplica" if not e.ajuda else "em branco (" + e.ajuda.split(":", 1)[-1].strip() + ")"
        else:
            txt = "em branco" if _vazio(v) else fmt_auto(v)
        linhas.append({"Marcador": e.marcador, "Grupo": e.grupo, "Parâmetro": e.rotulo, "Valor": txt,
                       "Unidade": e.unidade, "Origem": _origem(cfg, e.caminho)})
    for i, item in enumerate(cfg.economico.capex, start=1):
        linhas.append({"Marcador": f"E-C{i:02d}", "Grupo": "CAPEX", "Parâmetro": item.descricao,
                       "Valor": fmt_num(item.valor, 2), "Unidade": f"R$ (vida útil {fmt_auto(item.vida_util_anos)} anos)",
                       "Origem": _origem(cfg, "economico.capex")})
    linhas.append({"Marcador": "E-C00", "Grupo": "CAPEX", "Parâmetro": "CAPEX total",
                   "Valor": fmt_num(sum(i.valor for i in cfg.economico.capex), 2), "Unidade": "R$",
                   "Origem": _origem(cfg, "economico.capex")})
    mix = cfg.economico.mix_produtos
    linhas.append({"Marcador": "E-E25", "Grupo": "Econômica", "Parâmetro": "Mix de produtos",
                   "Valor": " | ".join(f"{p.nome}: {fmt_auto(p.participacao * 100)}% (fator de preço {fmt_auto(p.fator_preco)})"
                                       for p in mix) if mix else "produto único",
                   "Unidade": "—", "Origem": _origem(cfg, "economico.mix_produtos")})
    for marcador, var, caminho, rot, unid in DISTRIBUICOES:
        d = cfg.distribuicoes.get(caminho)
        txt = (f"{fmt_auto(d.minimo)} / {fmt_auto(d.mais_provavel)} / {fmt_auto(d.maximo)}" if d is not None
               else "determinística (sem distribuição)")
        linhas.append({"Marcador": marcador, "Grupo": "Distribuições (mín./moda/máx.)", "Parâmetro": rot, "Valor": txt,
                       "Unidade": unid, "Origem": _origem(cfg, caminho)})
    return pd.DataFrame(linhas)


def marcadores_entradas(cfg: EVTEASConfig, alternativas: Optional[Dict[str, EVTEASConfig]] = None) -> List[tuple]:
    """(marcador, descrição, valor, seção) para as entradas; '-F' indica a origem declarada."""
    L = []
    for _, r in tabela_entradas(cfg).iterrows():
        L.append((r["Marcador"], f"{r['Parâmetro']} ({r['Unidade']})", r["Valor"], "4.2"))
        L.append((r["Marcador"] + "F", f"Origem: {r['Parâmetro']}", r["Origem"], "4.2"))
    if alternativas:
        for k, alt in alternativas.items():
            if k == "A":
                continue
            difs = []
            for e in ENTRADAS:
                va, vb = obter_valor(cfg, e), obter_valor(alt, e)
                if va != vb and e.var != "projeto":
                    difs.append(f"{e.rotulo}: {fmt_auto(va)} → {fmt_auto(vb)}")
            extra = alt.economico.capex[len(cfg.economico.capex):]
            difs += [f"CAPEX adicional: {i.descricao} (R$ {fmt_num(i.valor, 2)}; {fmt_auto(i.vida_util_anos)} anos)"
                     for i in extra]
            L.append((f"E-X{k}", f"Alternativa {k}: {alt.projeto}", "; ".join(difs) or "sem alterações", "4.9"))
    return L


# ---------------------------------------------------------------------------------------------
# Planilha de entradas (.xlsx): alternativa ao formulário, com coluna de origem por premissa
# ---------------------------------------------------------------------------------------------
def gerar_planilha_entradas(caminho: str, cfg: Optional[EVTEASConfig] = None) -> str:
    """Gera a planilha de entradas em branco (ou com os valores de ``cfg``, para revisão)."""
    linhas = []
    for e in ENTRADAS:
        v = obter_valor(cfg, e) if cfg is not None else (e.padrao if e.metodo else None)
        f = cfg.fontes.get(e.caminho) if cfg is not None else None
        linhas.append({"Marcador": e.marcador, "Grupo": e.grupo, "Variável": e.var, "Parâmetro": e.rotulo,
                       "Unidade": e.unidade, "Obrigatório": "sim" if e.obrigatorio and not e.metodo else "não",
                       "Opções": " / ".join(e.opcoes) if e.opcoes else ("sim / não" if e.tipo == "bool" else ""),
                       "Valor": "" if _vazio(v) else (("sim" if v else "não") if isinstance(v, bool) else v),
                       "Categoria da fonte": f.categoria if f else "", "Referência": f.referencia if f else "",
                       "Orientação": e.ajuda})
    capex = [{"Item": f"E-C{i:02d}", "Descrição": "", "Valor (R$)": "", "Vida útil (anos)": ""} for i in range(1, N_CAPEX + 1)]
    if cfg is not None:
        for i, it in enumerate(cfg.economico.capex[:N_CAPEX]):
            capex[i].update({"Descrição": it.descricao, "Valor (R$)": it.valor, "Vida útil (anos)": it.vida_util_anos})
    dist = []
    for marcador, var, cam, rot, unid in DISTRIBUICOES:
        d = cfg.distribuicoes.get(cam) if cfg is not None else None
        dist.append({"Marcador": marcador, "Variável": var, "Premissa": rot, "Unidade": unid,
                     "Mínimo": d.minimo if d else "", "Máximo": d.maximo if d else "",
                     "Orientação": "Em branco = determinística; a moda é o valor informado na aba Entradas"})
    alts = [{"Alternativa": a, "Nome": "", "Alterações (variável = valor; ...)": "",
             "CAPEX adicional (descrição; valor; vida | ...)": ""} for a in CAMPOS_ALTERNATIVAS]
    with pd.ExcelWriter(caminho, engine="openpyxl") as w:
        pd.DataFrame(linhas).to_excel(w, sheet_name="Entradas", index=False)
        pd.DataFrame(capex).to_excel(w, sheet_name="CAPEX", index=False)
        pd.DataFrame(dist).to_excel(w, sheet_name="Distribuições", index=False)
        pd.DataFrame(alts).to_excel(w, sheet_name="Alternativas", index=False)
        pd.DataFrame({"Categorias de fonte admitidas (Seção 3.6)": CATEGORIAS_FONTE}).to_excel(
            w, sheet_name="Categorias de fonte", index=False)
    return caminho


def valores_de_planilha(caminho: str) -> Tuple[Dict[str, Any], Dict[str, Fonte]]:
    """Lê a planilha preenchida e devolve (valores no formato do formulário, fontes)."""
    abas = pd.read_excel(caminho, sheet_name=None, dtype=object)
    valores: Dict[str, Any] = {}
    fontes: Dict[str, Fonte] = {}
    for _, r in abas["Entradas"].iterrows():
        var = str(r["Variável"]).strip()
        if var not in POR_VAR:
            continue
        v = r.get("Valor")
        valores[var] = "" if _vazio(v) else v
        cat = r.get("Categoria da fonte")
        if not _vazio(cat):
            alvo = _sem_acento(cat)
            categoria = next((c for c in CATEGORIAS_FONTE if _sem_acento(c) == alvo), None)
            if categoria is None:
                raise EntradasInvalidas([f"[{r['Marcador']}] Categoria de fonte inválida: {cat!r}"])
            ref = r.get("Referência")
            fontes[POR_VAR[var].caminho] = Fonte(categoria, "" if _vazio(ref) else str(ref))
    for i, (_, r) in enumerate(abas.get("CAPEX", pd.DataFrame()).iterrows(), start=1):
        if _vazio(r.get("Descrição")) and _vazio(r.get("Valor (R$)")):
            continue
        valores[f"capex_{i:02d}"] = f"{r.get('Descrição')}; {r.get('Valor (R$)')}; {r.get('Vida útil (anos)')}"
    for _, r in abas.get("Distribuições", pd.DataFrame()).iterrows():
        if _vazio(r.get("Mínimo")) and _vazio(r.get("Máximo")):
            continue
        valores[str(r["Variável"]).strip()] = f"{r.get('Mínimo')}; {r.get('Máximo')}"
    for _, r in abas.get("Alternativas", pd.DataFrame()).iterrows():
        a = str(r["Alternativa"]).strip()
        if a in CAMPOS_ALTERNATIVAS and not _vazio(r.get("Nome")):
            valores[f"alt_{a}_nome"] = r.get("Nome")
            valores[f"alt_{a}_alteracoes"] = r.get("Alterações (variável = valor; ...)") or ""
            valores[f"alt_{a}_capex_adicional"] = r.get("CAPEX adicional (descrição; valor; vida | ...)") or ""
    return valores, fontes


def config_de_planilha(caminho: str) -> EVTEASConfig:
    valores, fontes = valores_de_planilha(caminho)
    cfg, erros = ler_formulario(valores)
    if erros:
        raise EntradasInvalidas(erros)
    cfg.fontes.update(fontes)
    return cfg

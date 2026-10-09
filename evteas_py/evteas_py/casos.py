"""Configurações de referência: caso-base ilustrativo e alternativas.

O caso-base representa um Projeto de Geração de Trabalho e Renda (PGTR) de
piscicultura de tilápia em viveiros escavados, conduzido por cooperativa de
pescadores artesanais. Os valores são estimativas ilustrativas, registradas
com sua origem; não constituem dados de um empreendimento real e devem ser
recalibrados na validação com o especialista em piscicultura.
"""
from __future__ import annotations

import copy

from .config import (AmbientalConfig, Distribuicao, EconomicoConfig, EVTEASConfig, Fonte, MonteCarloConfig,
                     PesosConfig, SocialConfig, TecnicoConfig)

REF_KUBITZA = "Kubitza (2017) — faixa zootécnica de referência para tilápia"
REF_CONAMA = "Resolução CONAMA nº 357/2005, classe 2, ambiente lótico"
REF_COTACAO = "Estimativa ilustrativa; substituir por cotação regional atualizada"


def criar_config_caso_base() -> EVTEASConfig:
    cfg = EVTEASConfig(projeto="Caso-base — PGTR de piscicultura de tilápia em viveiros escavados")
    cfg.tecnico = TecnicoConfig()
    cfg.economico = EconomicoConfig()
    cfg.ambiental = AmbientalConfig()
    cfg.social = SocialConfig()
    cfg.economico.fomento_nao_reembolsavel_pct = 70.0
    cfg.economico.cooperados_fornecedores = 14      # associados que não atuam na operação (mínimo legal de 20)
    cfg.fontes = {
        "economico.fomento_nao_reembolsavel_pct": Fonte("autor", "Hipótese de aporte por projeto de compensação do licenciamento federal (IBAMA, 2010, 2012)"),
        "tecnico.fcr": Fonte("bibliografico", REF_KUBITZA),
        "tecnico.mortalidade_pct": Fonte("bibliografico", REF_KUBITZA),
        "tecnico.peso_final_g": Fonte("bibliografico", REF_KUBITZA),
        "tecnico.ciclo_dias": Fonte("bibliografico", REF_KUBITZA),
        "tecnico.produtividade_esperada_kg_m2_ciclo": Fonte("bibliografico", REF_KUBITZA),
        "tecnico.area_lamina_m2": Fonte("autor", "Dimensionamento conceitual (sem definição de terreno)"),
        "economico.preco_venda_kg": Fonte("cotacao", REF_COTACAO),
        "economico.custo_racao_kg": Fonte("cotacao", REF_COTACAO),
        "economico.custo_alevino_milheiro": Fonte("cotacao", REF_COTACAO),
        "economico.tarifa_energia_kwh": Fonte("cotacao", REF_COTACAO),
        "economico.classe_estimativa_aace": Fonte("normativo", "AACE International (2020), estimativa Classe 5"),
        "economico.tma_aa_pct": Fonte("autor", "Custo de oportunidade de recursos de fomento"),
        "ambiental.n_max_mg_l": Fonte("normativo", REF_CONAMA),
        "ambiental.p_max_mg_l": Fonte("normativo", REF_CONAMA),
        "ambiental.faixa_app_minima_m": Fonte("normativo", "Lei nº 12.651/2012, art. 4º, I, a"),
        "ambiental.proteina_racao_pct": Fonte("bibliografico", REF_KUBITZA),
        "ambiental.evaporacao_mm_dia": Fonte("bibliografico", "Kubitza (2017); calibrar com dados climáticos locais"),
        "social.salario_minimo": Fonte("normativo", "Salário mínimo nacional vigente"),
    }
    return cfg


def criar_alternativas() -> dict:
    """Três alternativas de projeto para comparação por TOPSIS."""
    a = criar_config_caso_base()
    a.projeto = "A — Viveiros semi-intensivos, energia da rede"

    b = criar_config_caso_base()
    b.projeto = "B — A + energia solar + wetland para efluentes"
    b.economico.capex_itens["Usina fotovoltaica"] = 55000.0
    b.economico.capex_itens["Wetland construído"] = 25000.0
    b.economico.tarifa_energia_kwh = 0.12           # custo residual (disponibilidade, O&M)
    b.monte_carlo.distribuicoes["economico.tarifa_energia_kwh"] = Distribuicao("triangular", 0.08, 0.12, 0.18)
    b.ambiental.fonte_energia = "solar"
    b.ambiental.remocao_p_tratamento_pct = 80.0
    b.ambiental.remocao_n_tratamento_pct = 60.0
    b.ambiental.checklist["energia_renovavel"] = True
    b.ambiental.checklist["gestao_residuos"] = True
    b.ambiental.residuos_reaproveitados_pct = 70.0

    c = criar_config_caso_base()
    c.projeto = "C — Intensificação com maior aeração"
    c.tecnico.sistema_produtivo = "intensivo"
    c.tecnico.produtividade_esperada_kg_m2_ciclo = 2.0
    c.economico.capex_itens["Aeradores e quadro elétrico"] = 140000.0
    c.economico.mao_obra_mes = 14000.0
    c.monte_carlo.distribuicoes["tecnico.mortalidade_pct"] = Distribuicao("triangular", 6.0, 12.0, 25.0)
    c.tecnico.mortalidade_pct = 12.0
    return {"A": a, "B": b, "C": c}


def exemplo_validacao_especialistas(cfg: EVTEASConfig) -> EVTEASConfig:
    """Ilustra a parametrização por Likert (Quadro 7) com dois avaliadores.

    Os escores abaixo são *placeholders* de demonstração; devem ser
    substituídos pelas respostas efetivas dos especialistas na Fase 3.
    """
    c = copy.deepcopy(cfg)
    c.pesos = PesosConfig(metodo="likert", likert_dimensoes={
        "Especialista em framework": {"tecnico": 4, "economico": 5, "ambiental": 4, "social": 3},
        "Especialista em piscicultura": {"tecnico": 5, "economico": 5, "ambiental": 3, "social": 4},
    })
    return c

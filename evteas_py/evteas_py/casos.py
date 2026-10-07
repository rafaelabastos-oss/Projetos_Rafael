"""Configurações de referência: caso-base ilustrativo, alternativas e preset legado.

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


def criar_config_legado_rev186() -> EVTEASConfig:
    """Reproduz as premissas do preset da Rev. 186 (teste de regressão)."""
    cfg = EVTEASConfig(projeto="Preset legado da Rev. 186")
    cfg.tecnico = TecnicoConfig(sistema_produtivo="superintensivo", area_lamina_m2=1500, profundidade_media_m=1.0,
                                numero_tanques=10, tanques_ativos=9, capacidade_suporte_kg_m3=30.0,
                                produtividade_esperada_kg_m2_ciclo=8.0, peso_inicial_g=30, peso_final_g=850,
                                ciclo_dias=240, ciclos_ano=1.4, mortalidade_pct=8.0, fcr=1.60)
    cfg.economico = EconomicoConfig(
        tipo_organizacao="empresa", capex_itens={"CAPEX (preset)": 250000.0}, capital_giro=0.0,
        vida_util_anos=0.0, valor_residual_pct=0.0, preco_venda_kg=9.50, custo_racao_kg=3.20,
        custo_alevino_milheiro=450.0, tarifa_energia_kwh=0.0, outros_custos_variaveis_kg=0.0,
        mao_obra_mes=42000.0, encargos_mao_obra_pct=0.0, assistencia_tecnica_mes=25000.0,
        administrativo_mes=20000.0, manutencao_capex_pct_aa=0.0, taxa_impostos_faturamento_pct=15.0,
        taxa_impostos_lucro_pct=0.0, tma_aa_pct=12.0, horizonte_anos=10, capacidade_inicial_pct=50.0,
        meses_rampa=12, cooperados_trabalhadores=0)
    cfg.ambiental = AmbientalConfig(energia_kwh_kg=1.2)
    cfg.social = SocialConfig(empregos_diretos=10, empregos_indiretos=15, mao_obra_local_pct=80,
                              compras_locais_pct=60, conformidade_nr_pct=95, conflitos_registrados_ano=1)
    cfg.monte_carlo = MonteCarloConfig(distribuicoes={
        "economico.preco_venda_kg": Distribuicao("triangular", 8.0, 9.5, 11.0),
        "tecnico.fcr": Distribuicao("triangular", 1.35, 1.60, 1.90),
        "tecnico.mortalidade_pct": Distribuicao("triangular", 4.0, 8.0, 14.0),
        "economico.custo_racao_kg": Distribuicao("triangular", 2.70, 3.20, 4.00),
        "economico.custos_fixos_fator": Distribuicao("triangular", 0.90, 1.00, 1.15),
    }, incluir_capex_aace=False)
    cfg.monte_carlo.distribuicoes["economico.capex_fator"] = Distribuicao("triangular", 0.90, 1.00, 1.20)
    return cfg


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

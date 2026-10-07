"""EVTEAS-Py — módulo modelo.

Motor único e vetorizado das quatro dimensões do EVTEAS (técnica, econômica, ambiental e social),
mais governança e desperdícios Lean-Green. A classe ``Contexto`` devolve qualquer parâmetro
numérico como um vetor de tamanho n: com n = 1 o modelo é determinístico; com n = 10.000, é a
própria simulação de Monte Carlo (mesma fórmula nas duas camadas).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import (EVTEASConfig, capacidade_suporte, obter_por_caminho, safe_div,
                     taxa_anual_para_mensal, taxa_mensal_para_anual)
from .financeiro import payback, tir, vpl

DIAS_POR_MES = 365.25 / 12
RELACAO_COMUNIDADE = {"inexistente": 0.0, "parcial": 0.5, "consolidada": 1.0}

# Checklist normativo ambiental: (rótulo, peso, eliminatório) — pesos somam 10 (Score 0 a 10)
CHECKLIST_AMBIENTAL = {
    "licenca_ambiental": ("Licença ambiental da aquicultura", 1.50, True),
    "outorga_agua": ("Outorga de direito de uso da água", 1.50, True),
    "app_respeitada": ("Área de Preservação Permanente respeitada", 1.50, True),
    "tratamento_efluentes": ("Tratamento de efluentes", 1.25, False),
    "monitoramento_agua": ("Monitoramento da qualidade da água", 1.00, False),
    "car": ("Cadastro Ambiental Rural (CAR)", 1.00, False),
    "plano_residuos": ("Plano de gestão de resíduos", 0.75, False),
    "prevencao_escape": ("Prevenção de escape de peixes", 1.00, False),
    "energia_renovavel": ("Uso de energia renovável", 0.50, False),
}

ITENS_GOVERNANCA = {
    "estatuto_registrado": "Estatuto social registrado",
    "assembleias_regulares": "Assembleias regulares",
    "conselho_fiscal": "Conselho fiscal atuante",
    "prestacao_contas_publica": "Prestação de contas pública",
    "plano_negocios": "Plano de negócios aprovado",
    "registro_premissas_auditavel": "Registro auditável das premissas",
    "canal_denuncia": "Canal de denúncia",
}


class Contexto:
    """Acesso vetorizado aos parâmetros, com substituições (overrides) por caminho."""

    def __init__(self, cfg: EVTEASConfig, overrides: Optional[Dict[str, np.ndarray]] = None, n: int = 1):
        self.cfg = cfg
        self.overrides = overrides or {}
        self.n = int(n)
        for k, v in self.overrides.items():
            if np.ndim(v) and len(v) != self.n:
                raise ValueError(f"Override '{k}' com tamanho {len(v)} != n={self.n}")

    def v(self, caminho: str) -> np.ndarray:
        if caminho in self.overrides:
            return np.broadcast_to(np.asarray(self.overrides[caminho], dtype=float), (self.n,)).astype(float)
        valor = obter_por_caminho(self.cfg, caminho)
        return np.full(self.n, float(valor), dtype=float)


# ---------------------------------------------------------------------------------------------
# Dimensão técnica
# ---------------------------------------------------------------------------------------------
def calcular_tecnico(ctx: Contexto) -> Dict[str, Any]:
    """Infraestrutura, parâmetros biológicos e eficiência de insumos (Seção 2.8.6; Quadro 5)."""
    cfg = ctx.cfg
    t = cfg.tecnico
    vol = t.area_lamina_m2 * t.profundidade_media_m
    cap = capacidade_suporte(cfg)
    disponibilidade = t.tanques_ativos / t.numero_tanques
    # Restrição dupla da biomassa: capacidade de suporte (volume) e produtividade (área)
    limite_volume = vol * cap * disponibilidade
    limite_area = (t.area_lamina_m2 * t.produtividade_esperada_kg_m2_ciclo * disponibilidade
                   if t.produtividade_esperada_kg_m2_ciclo > 0 else np.inf)
    biomassa_alvo = min(limite_volume, limite_area)
    restricao = "capacidade de suporte (volume)" if limite_volume <= limite_area else "produtividade por área"

    peso_final_kg = t.peso_final_g / 1000
    sobrevivencia_planejada = 1 - t.mortalidade_pct / 100
    # A estocagem é decisão de projeto; a mortalidade e o crescimento são incertos.
    alevinos = (t.alevinos_por_ciclo if t.alevinos_por_ciclo > 0
                else safe_div(biomassa_alvo, peso_final_kg * sobrevivencia_planejada, 0.0))
    sobrevivencia = 1 - np.clip(ctx.v("tecnico.mortalidade_pct"), 0, 99.9) / 100
    desempenho = np.maximum(ctx.v("tecnico.desempenho_crescimento_pct"), 0) / 100
    fcr = ctx.v("tecnico.fcr")
    ciclos = ctx.v("tecnico.ciclos_ano")

    biomassa_despesca = np.minimum(alevinos * sobrevivencia * peso_final_kg * desempenho, limite_volume)
    biomassa_inicial = alevinos * t.peso_inicial_g / 1000
    ganho_ciclo = np.maximum(biomassa_despesca - biomassa_inicial, 0)
    racao_ciclo = ganho_ciclo * fcr

    producao_ano = biomassa_despesca * ciclos
    performance = np.minimum(desempenho, 1.0)
    qualidade = sobrevivencia                      # Quadro 5: Qualidade = taxa de sobrevivência
    oee = disponibilidade * performance * qualidade
    potencial_ano = vol * cap * ciclos             # capacidade plena de todos os viveiros
    return {
        "volume_util_m3": vol, "capacidade_suporte_kg_m3": cap, "disponibilidade": disponibilidade,
        "limite_volume_kg": limite_volume, "limite_area_kg": limite_area, "biomassa_alvo_kg": biomassa_alvo,
        "restricao_ativa": restricao, "alevinos_por_ciclo": alevinos, "alevinos_ano": alevinos * ciclos,
        "densidade_peixes_m3": safe_div(alevinos, vol * disponibilidade, 0.0),
        "sobrevivencia": sobrevivencia, "desempenho": desempenho, "fcr": fcr, "ciclos_ano": ciclos,
        "biomassa_despesca_ciclo_kg": biomassa_despesca, "biomassa_inicial_ciclo_kg": biomassa_inicial,
        "ganho_biomassa_ciclo_kg": ganho_ciclo, "racao_ciclo_kg": racao_ciclo,
        "producao_ano_kg": producao_ano, "producao_kg_mes": producao_ano / 12,
        "ganho_biomassa_ano_kg": ganho_ciclo * ciclos, "racao_ano_kg": racao_ciclo * ciclos,
        "produtividade_kg_m2_ano": producao_ano / t.area_lamina_m2,
        "produtividade_volumetrica_kg_m3_ano": producao_ano / vol,
        "produtividade_relativa": safe_div(producao_ano, potencial_ano, 0.0),
        "performance": performance, "qualidade": qualidade, "oee": oee,
    }


def curva_crescimento(cfg: EVTEASConfig, pontos: int = 0) -> pd.DataFrame:
    """Curva diária do ciclo: taxa de crescimento específico constante, mortalidade distribuída
    ao longo do ciclo e arraçoamento calibrado para reproduzir o FCR do ciclo."""
    tec = calcular_tecnico(Contexto(cfg))
    t = cfg.tecnico
    dias = np.arange(0, t.ciclo_dias + 1)
    peso_final = t.peso_final_g * t.desempenho_crescimento_pct / 100
    tce = math.log(peso_final / t.peso_inicial_g) / t.ciclo_dias      # taxa de crescimento específico
    peso = t.peso_inicial_g * np.exp(tce * dias)
    sobrev_final = 1 - t.mortalidade_pct / 100
    z = -math.log(sobrev_final) / t.ciclo_dias if sobrev_final < 1 else 0.0
    vivos = float(tec["alevinos_por_ciclo"][0] if np.ndim(tec["alevinos_por_ciclo"]) else tec["alevinos_por_ciclo"]) * np.exp(-z * dias)
    biomassa = vivos * peso / 1000
    ganho_diario = np.maximum(np.diff(biomassa, prepend=biomassa[0]), 0)
    ganho_total = max(ganho_diario.sum(), 1e-9)
    racao_total = float(np.atleast_1d(tec["racao_ciclo_kg"])[0])
    racao_diaria = ganho_diario / ganho_total * racao_total
    df = pd.DataFrame({"Dia": dias, "Peso médio (g)": peso, "Peixes vivos": vivos, "Biomassa (kg)": biomassa,
                       "Ração diária (kg)": racao_diaria, "Ração acumulada (kg)": np.cumsum(racao_diaria)})
    if pontos and pontos < len(df):
        df = df.iloc[np.linspace(0, len(df) - 1, pontos).astype(int)].reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------------------------
# Dimensão econômica
# ---------------------------------------------------------------------------------------------
def aliquotas(cfg: EVTEASConfig) -> Dict[str, float]:
    a = {"faturamento": 0.0, "lucro": 0.0, "folha": 0.0}
    for tr in cfg.economico.tributos:
        if tr.base not in a:
            raise ValueError(f"Base de tributo inválida: {tr.base!r}")
        a[tr.base] += tr.aliquota_pct / 100
    return a


def fator_mix(cfg: EVTEASConfig) -> float:
    """Preço médio relativo do mix de produtos; sem mix informado, produto único (fator 1)."""
    mix = cfg.economico.mix_produtos
    return float(sum(p.participacao * p.fator_preco for p in mix)) if mix else 1.0


def calcular_economico(ctx: Contexto, tec: Dict[str, Any]) -> Dict[str, Any]:
    """Projeção mensal, DRE, fluxo de caixa e indicadores (Casarotto Filho; Kopittke, 2007)."""
    cfg, e, n = ctx.cfg, ctx.cfg.economico, ctx.n
    M = int(e.horizonte_anos * 12)
    meses = np.arange(1, M + 1)
    L = max(1, int(round(cfg.tecnico.ciclo_dias / DIAS_POR_MES)))     # meses até a 1ª despesca
    rampa = e.rampa_inicial_pct / 100 + (1 - e.rampa_inicial_pct / 100) * np.minimum(
        np.arange(M) / max(e.rampa_meses, 1), 1.0)
    aliq = aliquotas(cfg)

    prod_mes = tec["producao_kg_mes"][:, None]
    em_engorda = prod_mes * rampa[None, :]                    # kg/mês em crescimento
    vendida = np.zeros((n, M))
    vendida[:, L:] = em_engorda[:, : M - L]                   # despesca após o 1º ciclo

    preco = ctx.v("economico.preco_venda_kg")[:, None] * fator_mix(cfg)
    receita_produtos = vendida * preco
    receita_servicos = np.where(meses > L, e.receita_servicos_mes, 0.0)[None, :] * np.ones((n, 1))
    receita = receita_produtos + receita_servicos

    producao_ano = np.maximum(tec["producao_ano_kg"], 1e-9)
    racao_kg = (tec["racao_ano_kg"] / producao_ano)[:, None]
    alevinos_kg = (tec["alevinos_ano"] / producao_ano)[:, None]
    kwh_kg = ctx.v("ambiental.consumo_kwh_kg")[:, None]
    fracao_compra = 1 - ctx.v("ambiental.fracao_renovavel_pct")[:, None] / 100
    custo_racao = em_engorda * racao_kg * ctx.v("economico.custo_racao_kg")[:, None]
    custo_alevinos = em_engorda * alevinos_kg * ctx.v("economico.custo_alevino_milheiro")[:, None] / 1000
    custo_energia = em_engorda * kwh_kg * fracao_compra * ctx.v("economico.tarifa_energia_kwh")[:, None]
    custo_outros_var = vendida * e.outros_variaveis_kg
    custos_variaveis = custo_racao + custo_alevinos + custo_energia + custo_outros_var

    capex_nominal = sum(i.valor for i in e.capex)
    fator_capex = ctx.v("economico.capex_fator")
    capex = capex_nominal * fator_capex
    fator_fixos = ctx.v("economico.custos_fixos_fator")[:, None]
    pessoal = e.mao_obra_mes * (1 + e.encargos_pct / 100 + aliq["folha"]) * fator_fixos * np.ones((1, M))
    manutencao = (capex * e.manutencao_pct_capex_ano / 100 / 12)[:, None] * fator_fixos * np.ones((1, M))
    outros_fixos = (e.administrativo_mes + e.seguros_outros_fixos_mes) * fator_fixos * np.ones((1, M))
    custos_fixos = pessoal + manutencao + outros_fixos

    dep_mes = np.zeros(M)
    for item in e.capex:
        vida_m = max(int(round(item.vida_util_anos * 12)), 1)
        dep_mes[:min(vida_m, M)] += item.valor * (1 - e.valor_residual_pct / 100) / vida_m
    depreciacao = dep_mes[None, :] * fator_capex[:, None]

    impostos_fat = receita * aliq["faturamento"]
    receita_liquida = receita - impostos_fat
    lucro_bruto = receita_liquida - custos_variaveis
    ebitda = lucro_bruto - custos_fixos
    lair = ebitda - depreciacao
    impostos_lucro = np.maximum(lair, 0) * aliq["lucro"]
    lucro_liquido = lair - impostos_lucro
    fco = lucro_liquido + depreciacao

    investimento = capex + e.capital_giro
    residual = capex * e.valor_residual_pct / 100
    estoque_final = ((custo_racao + custo_alevinos + custo_energia)[:, M - L:].sum(axis=1)
                     if L > 0 else np.zeros(n))
    terminal = residual + e.capital_giro + estoque_final

    fluxo = np.zeros((n, M + 1))
    fluxo[:, 0] = -investimento
    fluxo[:, 1:] = fco
    fluxo[:, -1] += terminal

    tma_am = taxa_anual_para_mensal(ctx.v("economico.tma_aa_pct") / 100)
    vpl_v = vpl(tma_am, fluxo)
    tir_am, diag_tir = tir(fluxo)
    tir_aa = taxa_mensal_para_anual(tir_am)
    pb_s = payback(fluxo)
    pb_d = payback(fluxo, tma_am)
    il = safe_div(vpl_v + investimento, investimento, np.nan)

    # Perspectiva do beneficiário: parte do CAPEX aportada por fomento não reembolsável
    fomento = capex * e.fomento_nao_reembolsavel_pct / 100
    fluxo_b = fluxo.copy()
    fluxo_b[:, 0] += fomento
    vpl_b = vpl(tma_am, fluxo_b)
    tir_b_am, diag_b = tir(fluxo_b)
    pb_d_b = payback(fluxo_b, tma_am)

    # Ano de regime (indicadores anuais do Quadro 5)
    a0, a1 = (e.ano_regime - 1) * 12, e.ano_regime * 12
    soma = lambda x: x[:, a0:a1].sum(axis=1)
    receita_r = soma(receita)
    vendida_r = soma(vendida)
    cv_r, cf_r, dep_r = soma(custos_variaveis), soma(custos_fixos), soma(depreciacao)
    imp_fat_r, imp_luc_r, ll_r = soma(impostos_fat), soma(impostos_lucro), soma(lucro_liquido)
    custo_op_r = cv_r + cf_r
    preco_medio = (preco[:, 0] if preco.ndim == 2 else preco)
    cv_unit = safe_div(cv_r, vendida_r, 0.0) + preco_medio * aliq["faturamento"]
    margem_unit = preco_medio - cv_unit
    pe_kg = np.where(margem_unit > 0, safe_div(cf_r + dep_r, margem_unit, np.inf), np.inf)
    margem_seg = np.where(vendida_r > 0, 1 - safe_div(pe_kg, vendida_r, np.inf), -np.inf)
    insumos_externos_r = (soma(custo_racao) + soma(custo_alevinos) + soma(custo_energia)
                          + soma(custo_outros_var) + soma(manutencao) + soma(outros_fixos))
    return {
        "meses": M, "meses_ate_despesca": L, "rampa": rampa,
        "vendida_kg": vendida, "receita": receita, "receita_servicos": receita_servicos,
        "custo_racao": custo_racao, "custo_alevinos": custo_alevinos, "custo_energia": custo_energia,
        "custo_outros_variaveis": custo_outros_var, "custos_variaveis": custos_variaveis,
        "pessoal": pessoal, "manutencao": manutencao, "outros_fixos": outros_fixos, "custos_fixos": custos_fixos,
        "impostos_faturamento": impostos_fat, "receita_liquida": receita_liquida, "lucro_bruto": lucro_bruto,
        "ebitda": ebitda, "depreciacao": depreciacao, "lair": lair, "impostos_lucro": impostos_lucro,
        "lucro_liquido": lucro_liquido, "fco": fco, "fluxo_caixa": fluxo, "fluxo_caixa_beneficiario": fluxo_b,
        "capex": capex, "investimento": investimento, "residual": residual, "estoque_final": estoque_final,
        "terminal": terminal, "tma_am": tma_am,
        "vpl": vpl_v, "tir_am": tir_am, "tir_aa": tir_aa, "diagnostico_tir": diag_tir,
        "payback_simples_meses": pb_s, "payback_descontado_meses": pb_d, "indice_lucratividade": il,
        "fomento": fomento, "investimento_beneficiario": investimento - fomento,
        "vpl_beneficiario": vpl_b, "tir_aa_beneficiario": taxa_mensal_para_anual(tir_b_am),
        "diagnostico_tir_beneficiario": diag_b, "payback_descontado_beneficiario_meses": pb_d_b,
        "receita_regime": receita_r, "producao_vendida_regime_kg": vendida_r,
        "custos_variaveis_regime": cv_r, "custos_fixos_regime": cf_r, "depreciacao_regime": dep_r,
        "pessoal_regime": soma(pessoal), "impostos_regime": imp_fat_r + imp_luc_r,
        "lucro_liquido_regime": ll_r, "custo_operacional_regime": custo_op_r,
        "custo_racao_regime": soma(custo_racao),
        "roi_regime": safe_div(ll_r, investimento, np.nan),
        "ponto_equilibrio_kg_ano": pe_kg, "margem_seguranca": margem_seg,
        "custo_total_kg": safe_div(custo_op_r + dep_r, vendida_r, np.nan),
        "custo_operacional_kg": safe_div(custo_op_r, vendida_r, np.nan),
        "participacao_racao_custo_op": safe_div(soma(custo_racao), custo_op_r, np.nan),
        "valor_adicionado_regime": receita_r - insumos_externos_r,
        "preco_medio_kg": preco_medio,
    }


def dre_mensal(eco: Dict[str, Any], linha: int = 0) -> pd.DataFrame:
    """Demonstração do Resultado mensal da realização ``linha`` (0 = determinística)."""
    M = eco["meses"]
    col = lambda k: np.asarray(eco[k])[linha]
    df = pd.DataFrame({
        "Mês": np.arange(1, M + 1),
        "Produção vendida (kg)": col("vendida_kg"),
        "Receita Bruta": col("receita"),
        "Impostos s/ Faturamento": col("impostos_faturamento"),
        "Receita Líquida": col("receita_liquida"),
        "Custos Variáveis": col("custos_variaveis"),
        "Lucro Bruto": col("lucro_bruto"),
        "Custos Fixos": col("custos_fixos"),
        "EBITDA": col("ebitda"),
        "Depreciação": col("depreciacao"),
        "LAIR": col("lair"),
        "Impostos s/ Lucro": col("impostos_lucro"),
        "Resultado Líquido": col("lucro_liquido"),
        "Fluxo de Caixa Operacional": col("fco"),
    })
    return df


def dre_anual(df_mensal: pd.DataFrame) -> pd.DataFrame:
    df = df_mensal.copy()
    df.insert(0, "Ano", (df["Mês"] - 1) // 12 + 1)
    return df.drop(columns="Mês").groupby("Ano", as_index=False).sum()


def distribuicao_sobras(cfg: EVTEASConfig, eco: Dict[str, Any], linha: int = 0) -> Dict[str, float]:
    """Destinação das sobras do ano de regime (Lei nº 5.764/1971, art. 28: Fundo de Reserva
    mínimo de 10% e FATES mínimo de 5% das sobras líquidas)."""
    e = cfg.economico
    sobras = max(float(np.asarray(eco["lucro_liquido_regime"])[linha]), 0.0)
    if e.tipo_organizacao == "empresa":
        return {"Resultado líquido do ano de regime": sobras, "Fundo de Reserva": 0.0, "FATES": 0.0,
                "Distribuído aos trabalhadores": 0.0, "Retido/reinvestido": sobras}
    reserva, fates = 0.10 * sobras, 0.05 * sobras
    distribuivel = sobras - reserva - fates
    trab = distribuivel * e.perc_sobras_trabalhadores / 100
    return {"Sobras líquidas do ano de regime": sobras, "Fundo de Reserva (10%)": reserva, "FATES (5%)": fates,
            "Distribuído aos trabalhadores": trab, "Retido/reinvestido": distribuivel - trab}


def sobras_trabalhadores(cfg: EVTEASConfig, eco: Dict[str, Any]) -> np.ndarray:
    """Vetor das sobras distribuídas aos trabalhadores no ano de regime."""
    e = cfg.economico
    ll = np.maximum(np.asarray(eco["lucro_liquido_regime"], dtype=float), 0)
    if e.tipo_organizacao == "empresa":
        return np.zeros_like(ll)
    return ll * 0.85 * e.perc_sobras_trabalhadores / 100


# ---------------------------------------------------------------------------------------------
# Dimensão ambiental
# ---------------------------------------------------------------------------------------------
def calcular_ambiental(ctx: Contexto, tec: Dict[str, Any], eco: Dict[str, Any]) -> Dict[str, Any]:
    """Água (Hoekstra, 2017), nutrientes e pegada hídrica cinza (CONAMA 357/2005), energia,
    emissões, ecoeficiência (WBCSD, 2000) e conformidade normativa."""
    cfg = ctx.cfg
    a, t = cfg.ambiental, cfg.tecnico
    vol = tec["volume_util_m3"]
    producao_t = np.maximum(tec["producao_ano_kg"], 1e-9) / 1000

    # Água captada (enchimentos, renovação e reposição de perdas) e água consumida (evaporação)
    enchimento = vol * a.enchimentos_ano
    renovacao = vol * tec["disponibilidade"] * ctx.v("ambiental.renovacao_agua_pct_dia") / 100 * 365
    perdas = t.area_lamina_m2 * (a.evaporacao_mm_dia + a.infiltracao_mm_dia) / 1000 * 365
    captada = enchimento + renovacao + perdas
    evaporada = t.area_lamina_m2 * a.evaporacao_mm_dia / 1000 * 365
    ph_azul = evaporada / producao_t                                     # m³/t (água consumida)
    indice_uso_agua = safe_div(tec["producao_ano_kg"], captada, 0.0)    # kg de peixe por m³ captado

    # Balanço de nutrientes e pegada hídrica cinza (poluente crítico)
    racao = tec["racao_ano_kg"]
    ganho = tec["ganho_biomassa_ano_kg"]
    n_in = racao * a.proteina_racao_pct / 100 / 6.25
    p_in = racao * a.fosforo_racao_pct / 100
    n_ret = ganho * a.nitrogenio_peixe_pct / 100
    p_ret = ganho * a.fosforo_peixe_pct / 100
    remocao_n = ctx.v("ambiental.remocao_n_tratamento_pct") / 100
    remocao_p = ctx.v("ambiental.remocao_p_tratamento_pct") / 100
    n_carga = np.maximum(n_in - n_ret, 0) * (1 - remocao_n)
    p_carga = np.maximum(p_in - p_ret, 0) * (1 - remocao_p)
    dn = a.n_max_mg_l - a.n_natural_mg_l
    dp = a.p_max_mg_l - a.p_natural_mg_l
    if dn <= 0 or dp <= 0:
        raise ValueError("Concentração máxima deve superar a natural (pegada hídrica cinza indefinida)")
    cinza_n = n_carga * 1000 / dn          # kg -> g; mg/L = g/m³
    cinza_p = p_carga * 1000 / dp
    cinza = np.maximum(cinza_n, cinza_p)
    critico = np.where(cinza_p >= cinza_n, "fósforo total", "nitrogênio total")

    # Energia e emissões (proxy da pegada de carbono)
    kwh = tec["producao_ano_kg"] * ctx.v("ambiental.consumo_kwh_kg")
    fracao_rede = 1 - ctx.v("ambiental.fracao_renovavel_pct") / 100
    fe_rede = ctx.v("ambiental.fator_emissao_rede_kg_kwh")
    co2_racao = racao * a.fator_emissao_racao_kgco2e_kg
    co2_energia = kwh * fracao_rede * fe_rede
    co2_diesel = np.full(ctx.n, a.diesel_l_ano * a.fator_emissao_diesel_kg_l)
    co2_total = co2_racao + co2_energia + co2_diesel
    intensidade = safe_div(co2_total, tec["producao_ano_kg"], np.nan)

    va = eco["valor_adicionado_regime"]
    # Ecoeficiência (WBCSD): valor adicionado / influência ambiental. Indefinida se VA <= 0.
    eco_carbono = np.where(va > 0, safe_div(va, co2_total, np.nan), np.nan)
    eco_agua = np.where(va > 0, safe_div(va, captada, np.nan), np.nan)
    status_eco = np.where(va > 0, "definida", "não definida (valor adicionado <= 0)")

    # Conformidade normativa: checklist ponderado (0 a 10) com itens eliminatórios
    itens = dict(a.checklist)
    if a.distancia_app_m < a.distancia_minima_app_m:
        itens["app_respeitada"] = False
    score = 0.0
    vetos: List[str] = []
    tabela = []
    for chave, (rotulo, peso, elim) in CHECKLIST_AMBIENTAL.items():
        ok = bool(itens.get(chave, False))
        score += peso if ok else 0.0
        if elim and not ok:
            vetos.append(rotulo)
        tabela.append({"Item": rotulo, "Peso": peso, "Eliminatório": "sim" if elim else "não",
                       "Atendido": "sim" if ok else "não"})
    return {
        "agua_captada_m3_ano": captada, "agua_enchimento_m3": enchimento, "agua_renovacao_m3": renovacao,
        "agua_reposicao_perdas_m3": perdas, "agua_evaporada_m3": evaporada, "indice_uso_agua_kg_m3": indice_uso_agua,
        "ph_azul_m3_t": ph_azul, "n_aportado_kg": n_in, "p_aportado_kg": p_in, "n_retido_kg": n_ret,
        "p_retido_kg": p_ret, "n_lancado_kg": n_carga, "p_lancado_kg": p_carga,
        "ph_cinza_n_m3_t": cinza_n / 1 / producao_t, "ph_cinza_p_m3_t": cinza_p / producao_t,
        "ph_cinza_m3_t": cinza / producao_t, "poluente_critico": critico,
        "energia_kwh_ano": kwh, "co2_racao_kg": co2_racao, "co2_energia_kg": co2_energia,
        "co2_diesel_kg": co2_diesel, "co2_total_kg": co2_total, "intensidade_carbono_kg_kg": intensidade,
        "ecoeficiencia_rs_kgco2e": eco_carbono, "ecoeficiencia_rs_m3": eco_agua, "status_ecoeficiencia": status_eco,
        "score_conformidade_0_10": score, "vetos_ambientais": vetos, "checklist": pd.DataFrame(tabela),
    }


# ---------------------------------------------------------------------------------------------
# Dimensão social
# ---------------------------------------------------------------------------------------------
def calcular_social(ctx: Contexto, eco: Dict[str, Any]) -> Dict[str, Any]:
    """Emprego, renda, Retenção de Valor Local (Quadro 5; GRI 201-1 e 204-1), Índice de Impacto
    Local, Licença Social para Operar (Hurst; Ihlen, 2018), risco social e Radar Social."""
    cfg = ctx.cfg
    s = cfg.social
    massa_anual = cfg.economico.mao_obra_mes * 12
    massa_local = massa_anual * s.mao_obra_local_pct / 100
    compras = (eco["custos_variaveis_regime"] + eco["custos_fixos_regime"] - eco["pessoal_regime"])
    compras_locais = np.maximum(compras, 0) * s.compras_locais_pct / 100
    custo_operacional = eco["custos_variaveis_regime"] + eco["custos_fixos_regime"]
    rvl = 100 * safe_div(massa_local + compras_locais, custo_operacional, 0.0)

    sobras = sobras_trabalhadores(cfg, eco)
    renda_local = massa_local + sobras * s.mao_obra_local_pct / 100
    iil = safe_div(renda_local, eco["receita_regime"], 0.0)
    n_trab = max(cfg.economico.cooperados_trabalhadores if cfg.economico.tipo_organizacao != "empresa"
                 else s.empregos_diretos, 1)
    renda_mensal = (massa_anual + sobras) / n_trab / 12
    renda_sm = renda_mensal / s.salario_minimo

    relacao = RELACAO_COMUNIDADE.get(s.relacao_comunidade)
    if relacao is None:
        raise ValueError(f"relacao_comunidade deve ser uma de {list(RELACAO_COMUNIDADE)}")
    participacao = 1.0 if cfg.governanca.itens.get("assembleias_regulares") else 0.0
    componentes_lso = {
        "Relação com a comunidade": relacao,
        "Canais formais de comunicação": 1.0 if s.canais_formais_comunicacao else 0.0,
        "Frequência de engajamento": min(s.reunioes_comunidade_ano / 12, 1.0),
        "Ausência de conflitos": math.exp(-0.5 * max(s.conflitos_registrados_ano, 0)),
        "Participação na governança": participacao,
    }
    lso = 100 * float(np.mean(list(componentes_lso.values())))
    risco = 1 / (1 + math.exp(8 * (lso / 100 - 0.5)))      # heurística logística (a calibrar)

    area_ha = cfg.tecnico.area_lamina_m2 / 10_000
    radar = {
        "Emprego": min(s.empregos_diretos / max(area_ha, 1e-9), 1.0),        # referência: 1 emprego/ha
        "Renda": np.minimum(renda_sm / 2.0, 1.0),                              # referência: 2 salários mínimos
        "Segurança do trabalho": 1.0 if s.aderencia_nr else 0.0,
        "Capacitação": 1.0 if s.programa_capacitacao else 0.0,
        "Relação com a comunidade": relacao,
        "Inclusão": min(s.participacao_mulheres_pct / 50.0, 1.0),             # referência: paridade
    }
    radar_vals = [np.broadcast_to(np.asarray(v, dtype=float), (ctx.n,)) for v in radar.values()]
    radar_media = np.mean(np.vstack(radar_vals), axis=0)
    return {
        "massa_salarial_anual": massa_anual, "massa_salarial_local": massa_local,
        "compras_locais": compras_locais, "rvl_pct": rvl, "renda_local": renda_local,
        "indice_impacto_local": iil, "sobras_trabalhadores": sobras, "renda_mensal_trabalhador": renda_mensal,
        "renda_salarios_minimos": renda_sm, "componentes_lso": componentes_lso, "lso_0_100": lso,
        "risco_social": risco, "radar": radar, "radar_social_media": radar_media,
        "empregos_diretos": s.empregos_diretos, "empregos_indiretos": s.empregos_indiretos,
    }


def calcular_governanca(cfg: EVTEASConfig) -> Dict[str, Any]:
    itens = cfg.governanca.itens
    atendidos = sum(1 for k in ITENS_GOVERNANCA if itens.get(k))
    tabela = pd.DataFrame([{"Item": rot, "Atendido": "sim" if itens.get(k) else "não"}
                           for k, rot in ITENS_GOVERNANCA.items()])
    return {"itens_atendidos": atendidos, "itens_total": len(ITENS_GOVERNANCA),
            "score_governanca": atendidos / len(ITENS_GOVERNANCA), "checklist": tabela}


def calcular_lean_green(ctx: Contexto, tec: Dict[str, Any], eco: Dict[str, Any]) -> Dict[str, Any]:
    """Desperdícios evitáveis em R$/ano frente às referências declaradas (Lawrence et al., 2023)."""
    cfg = ctx.cfg
    lg, t = cfg.lean_green, cfg.tecnico
    preco_racao = ctx.v("economico.custo_racao_kg")
    racao_excedente_kg = np.maximum(tec["fcr"] - lg.fcr_referencia, 0) * tec["ganho_biomassa_ano_kg"]
    racao_rs = racao_excedente_kg * preco_racao
    mort = 100 * (1 - tec["sobrevivencia"])
    mortos_evitaveis = np.maximum(mort - lg.mortalidade_referencia_pct, 0) / 100 * tec["alevinos_ano"]
    racao_por_peixe_morto = 0.5 * (t.peso_final_g - t.peso_inicial_g) / 1000 * tec["fcr"]
    custo_peixe_morto = ctx.v("economico.custo_alevino_milheiro") / 1000 + racao_por_peixe_morto * preco_racao
    mortalidade_rs = mortos_evitaveis * custo_peixe_morto
    kwh_kg = ctx.v("ambiental.consumo_kwh_kg")
    energia_excedente = np.maximum(kwh_kg - lg.consumo_kwh_kg_referencia, 0) * tec["producao_ano_kg"]
    energia_rs = energia_excedente * (1 - ctx.v("ambiental.fracao_renovavel_pct") / 100) * ctx.v("economico.tarifa_energia_kwh")
    total = racao_rs + mortalidade_rs + energia_rs
    return {"racao_excedente_kg": racao_excedente_kg, "racao_excedente_rs": racao_rs,
            "mortalidade_evitavel_peixes": mortos_evitaveis, "mortalidade_evitavel_rs": mortalidade_rs,
            "energia_excedente_kwh": energia_excedente, "energia_excedente_rs": energia_rs,
            "desperdicio_total_rs": total,
            "desperdicio_pct_custo_operacional": safe_div(total, eco["custo_operacional_regime"], np.nan)}


def alinhamento_ods(cfg: EVTEASConfig, tec, eco, amb, soc, gov, linha: int = 0) -> pd.DataFrame:
    """Alinhamento aos ODS por regras explícitas e auditáveis."""
    g = lambda d, k: float(np.atleast_1d(np.asarray(d[k], dtype=float))[linha])
    s, a = cfg.social, cfg.ambiental
    regras = [
        ("ODS 1", "Erradicação da pobreza", g(soc, "renda_salarios_minimos") >= 1.0, "renda por trabalhador ≥ 1 salário mínimo"),
        ("ODS 2", "Fome zero e agricultura sustentável", g(tec, "producao_ano_kg") > 0, "produção de alimento proteico"),
        ("ODS 5", "Igualdade de gênero", s.participacao_mulheres_pct >= 30, "participação de mulheres ≥ 30%"),
        ("ODS 6", "Água potável e saneamento", bool(a.checklist.get("tratamento_efluentes")), "tratamento de efluentes"),
        ("ODS 7", "Energia limpa e acessível", a.fracao_renovavel_pct >= 50 or a.fonte_energia != "rede", "≥ 50% de energia renovável própria"),
        ("ODS 8", "Trabalho decente e crescimento econômico", s.aderencia_nr and g(soc, "renda_salarios_minimos") >= 1.0, "NR atendidas e renda ≥ 1 SM"),
        ("ODS 12", "Consumo e produção responsáveis", g(tec, "fcr") <= 1.8, "FCR ≤ 1,8"),
        ("ODS 13", "Ação contra a mudança do clima", g(amb, "intensidade_carbono_kg_kg") <= 3.0, "intensidade ≤ 3 kgCO2e/kg"),
        ("ODS 14", "Vida na água", bool(a.checklist.get("prevencao_escape")) and bool(a.checklist.get("tratamento_efluentes")), "prevenção de escape e tratamento"),
        ("ODS 15", "Vida terrestre", bool(a.checklist.get("app_respeitada")) and a.distancia_app_m >= a.distancia_minima_app_m, "APP respeitada"),
        ("ODS 16", "Paz, justiça e instituições eficazes", gov["score_governanca"] >= 0.5, "governança ≥ 50% dos itens"),
    ]
    return pd.DataFrame([{"ODS": o, "Tema": tema, "Atendido": "sim" if ok else "não", "Regra": regra}
                         for o, tema, ok, regra in regras])


# ---------------------------------------------------------------------------------------------
# Motor único
# ---------------------------------------------------------------------------------------------
def motor(cfg: EVTEASConfig, overrides: Optional[Dict[str, np.ndarray]] = None, n: int = 1,
          pesos: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Executa as quatro dimensões e o índice para n realizações das premissas."""
    from .ponderacao import calcular_indice
    ctx = Contexto(cfg, overrides, n)
    tec = calcular_tecnico(ctx)
    eco = calcular_economico(ctx, tec)
    amb = calcular_ambiental(ctx, tec, eco)
    soc = calcular_social(ctx, eco)
    gov = calcular_governanca(cfg)
    lean = calcular_lean_green(ctx, tec, eco)
    idx = calcular_indice(cfg, tec, eco, amb, soc, gov, pesos)
    return {"tecnico": tec, "economico": eco, "ambiental": amb, "social": soc,
            "governanca": gov, "lean_green": lean, "indice": idx}

"""Núcleo de cálculo vetorizado das quatro dimensões do EVTEAS.

Cada função recebe um ``Contexto``, que devolve qualquer parâmetro numérico
como vetor de tamanho n. Com n = 1 o modelo é determinístico; com n igual ao número de iterações
ele é a própria simulação de Monte Carlo. Não existe um "modelo simplificado"
para a camada estocástica: o mesmo código produz os dois resultados.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .config import (CHECKLIST_AMBIENTAL, FATORES_EMISSAO_ENERGIA, RELACAO_COMUNIDADE,
                     SISTEMAS_PRODUTIVOS, VARIAVEIS_ESTOCASTICAS, EVTEASConfig, obter_por_caminho)
from .financeiro import clamp, payback, pct, safe_div, taxa_anual_para_mensal, taxa_mensal_para_anual, tir, vpl


class Contexto:
    """Acesso vetorizado aos parâmetros, com substituições (overrides) por caminho."""

    def __init__(self, cfg: EVTEASConfig, overrides: Optional[Dict[str, np.ndarray]] = None, n: int = 1):
        self.cfg = cfg
        self.overrides = overrides or {}
        self.n = int(n)
        desconhecidos = sorted(set(self.overrides) - set(VARIAVEIS_ESTOCASTICAS))
        if desconhecidos:
            raise ValueError("O modelo não amostra estes parâmetros (sem efeito no Monte Carlo): "
                             + ", ".join(desconhecidos))
        for k, v in self.overrides.items():
            if np.ndim(v) and len(v) != self.n:
                raise ValueError(f"Override '{k}' com tamanho {len(v)} != n={self.n}")

    def v(self, caminho: str) -> np.ndarray:
        if caminho not in VARIAVEIS_ESTOCASTICAS:
            raise KeyError(f"{caminho} não está em VARIAVEIS_ESTOCASTICAS (config.py)")
        if caminho in self.overrides:
            return np.broadcast_to(np.asarray(self.overrides[caminho], dtype=float), (self.n,)).astype(float)
        valor = obter_por_caminho(self.cfg, caminho)
        return np.full(self.n, float(valor), dtype=float)


def referencia_sistema(cfg: EVTEASConfig, chave: str) -> float:
    sistema = cfg.tecnico.sistema_produtivo
    if sistema not in SISTEMAS_PRODUTIVOS:
        raise ValueError(f"Sistema produtivo desconhecido: {sistema}")
    return float(SISTEMAS_PRODUTIVOS[sistema][chave])


def capacidade_suporte(cfg: EVTEASConfig) -> float:
    c = cfg.tecnico.capacidade_suporte_kg_m3
    return float(c) if c is not None else referencia_sistema(cfg, "capacidade_suporte_kg_m3")


def energia_kwh_kg(cfg: EVTEASConfig) -> float:
    e = cfg.ambiental.energia_kwh_kg
    return float(e) if e is not None else referencia_sistema(cfg, "energia_kwh_kg")


def renovacao_pct_dia(cfg: EVTEASConfig) -> float:
    r = cfg.ambiental.renovacao_pct_dia
    return float(r) if r is not None else referencia_sistema(cfg, "renovacao_pct_dia")


# ---------------------------------------------------------------------------
# 1. Dimensão técnica
# ---------------------------------------------------------------------------

def calcular_tecnico(ctx: Contexto) -> Dict[str, Any]:
    t = ctx.cfg.tecnico
    vol = t.area_lamina_m2 * t.profundidade_media_m
    disponibilidade = safe_div(t.tanques_ativos, t.numero_tanques, 0.0)
    cap = capacidade_suporte(ctx.cfg)

    mort = np.clip(ctx.v("tecnico.mortalidade_pct"), 0, 100)
    sobrevivencia = 1 - mort / 100
    desempenho = np.clip(ctx.v("tecnico.desempenho_crescimento_pct"), 0, None) / 100
    fcr = np.maximum(ctx.v("tecnico.fcr"), 0)
    ciclos = max(float(t.ciclos_ano), 0.0)

    # Restrição dupla da biomassa: capacidade de suporte (volume) e produtividade (área)
    limite_volume = vol * cap * disponibilidade
    limite_area = (t.area_lamina_m2 * t.produtividade_esperada_kg_m2_ciclo * disponibilidade
                   if t.produtividade_esperada_kg_m2_ciclo > 0 else np.inf)
    biomassa_alvo = min(limite_volume, limite_area)
    restricao = "capacidade de suporte (volume)" if limite_volume <= limite_area else "produtividade por área"

    peso_final_kg = t.peso_final_g / 1000
    sobrevivencia_planejada = 1 - t.mortalidade_pct / 100
    alevinos = (t.alevinos_por_ciclo if t.alevinos_por_ciclo > 0
                else safe_div(biomassa_alvo, peso_final_kg * sobrevivencia_planejada, 0.0))

    # A estocagem é decisão de projeto; a mortalidade e o crescimento são incertos.
    biomassa_despesca = np.minimum(alevinos * sobrevivencia * peso_final_kg * desempenho, limite_volume)
    biomassa_inicial = alevinos * t.peso_inicial_g / 1000
    ganho_ciclo = np.maximum(biomassa_despesca - biomassa_inicial, 0)
    racao_ciclo = ganho_ciclo * fcr

    producao_ano = biomassa_despesca * ciclos
    performance = np.minimum(desempenho, 1.0)
    oee = disponibilidade * performance * sobrevivencia     # Quadro 5: Qualidade = sobrevivência

    potencial_kg_m2_ano = cap * t.profundidade_media_m * min(ciclos, 365 / max(t.ciclo_dias, 1))
    produtividade_kg_m2_ano = safe_div(producao_ano, t.area_lamina_m2, 0.0)

    return {
        "especie": t.especie,
        "sistema_produtivo": t.sistema_produtivo,
        "volume_util_m3": vol,
        "capacidade_suporte_kg_m3": cap,
        "restricao_biomassa": restricao,
        "disponibilidade": np.full(ctx.n, disponibilidade),
        "performance": performance,
        "qualidade": sobrevivencia,
        "oee": oee,
        "sobrevivencia": sobrevivencia,
        "fcr": fcr,
        "alevinos_ciclo": np.full(ctx.n, alevinos),
        "alevinos_ano": np.full(ctx.n, alevinos * ciclos),
        "densidade_estocagem_peixes_m3": np.full(ctx.n, safe_div(alevinos, vol * disponibilidade, 0.0)),
        "biomassa_inicial_ciclo_kg": np.full(ctx.n, biomassa_inicial),
        "biomassa_despesca_ciclo_kg": biomassa_despesca,
        "ganho_biomassa_ciclo_kg": ganho_ciclo,
        "ganho_biomassa_ano_kg": ganho_ciclo * ciclos,
        "racao_ciclo_kg": racao_ciclo,
        "racao_ano_kg": racao_ciclo * ciclos,
        "racao_por_kg_produzido": safe_div(racao_ciclo, biomassa_despesca, 0.0),
        "producao_kg_ano": producao_ano,
        "producao_kg_mes": producao_ano / 12,
        "produtividade_kg_m2_ano": produtividade_kg_m2_ano,
        "produtividade_volumetrica_kg_m3_ciclo": safe_div(biomassa_despesca, vol, 0.0),
        "produtividade_relativa": clamp(safe_div(produtividade_kg_m2_ano, potencial_kg_m2_ano, 0.0), 0, 1),
        "ciclos_ano": ciclos,
    }


def curva_crescimento(cfg: EVTEASConfig, passo_dias: int = 7) -> pd.DataFrame:
    """Curva de crescimento e de arraçoamento de um ciclo (modelo de TCE).

    Peso: W(d) = W0 · exp(TCE · d), TCE = ln(Wf/W0)/ciclo. Mortalidade
    distribuída exponencialmente ao longo do ciclo. A ração diária é
    proporcional ao ganho de biomassa e calibrada para reproduzir o FCR.
    """
    t = cfg.tecnico
    ctx = Contexto(cfg)
    tec = calcular_tecnico(ctx)
    n0 = float(tec["alevinos_ciclo"][0])
    w0, wf = t.peso_inicial_g / 1000, t.peso_final_g / 1000 * t.desempenho_crescimento_pct / 100
    dias = np.arange(0, t.ciclo_dias + 1)
    tce = math.log(wf / w0) / t.ciclo_dias if wf > w0 > 0 else 0.0
    peso = w0 * np.exp(tce * dias)
    m_diaria = 1 - (1 - t.mortalidade_pct / 100) ** (1 / t.ciclo_dias)
    vivos = n0 * (1 - m_diaria) ** dias
    biomassa = vivos * peso
    ganho = np.diff(biomassa, prepend=biomassa[0]).clip(min=0)
    racao_dia = ganho * t.fcr
    df = pd.DataFrame({
        "Dia": dias, "Peso médio (g)": peso * 1000, "Peixes vivos": vivos,
        "Biomassa (kg)": biomassa, "Ração do dia (kg)": racao_dia,
        "Ração acumulada (kg)": np.cumsum(racao_dia),
        "TCE (%/dia)": tce * 100,
    })
    if passo_dias <= 1:
        return df
    return df[(df["Dia"] % passo_dias == 0) | (df["Dia"] == t.ciclo_dias)].reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. Dimensão econômica
# ---------------------------------------------------------------------------

def preco_medio(cfg: EVTEASConfig) -> float:
    mix = cfg.economico.mix_produtos
    if not mix:
        return float(cfg.economico.preco_venda_kg)
    part = np.array([float(p.get("participacao_pct", 0)) for p in mix])
    preco = np.array([float(p.get("preco_kg", cfg.economico.preco_venda_kg)) for p in mix])
    if part.sum() <= 0:
        raise ValueError("Participações do mix de produtos devem somar mais que zero")
    return float((part / part.sum() * preco).sum())


BASES_TRIBUTARIAS = {
    # base interna: apelidos aceitos (nomes usados nos notebooks de viabilidade econômica)
    "faturamento": ("faturamento", "faturamento_bruto"),
    "produtos": ("produtos",),
    "servicos": ("servicos", "serviços"),
    "lucro": ("lucro", "lucro_antes_ir_csll"),
    "folha": ("folha",),
    "folha_clt": ("folha_clt",),
    "pro_labore": ("pro_labore", "pro_labore_cooperados"),
}


def aliquotas_configuradas(cfg: EVTEASConfig) -> Dict[str, float]:
    """Consolida alíquotas individuais (ICMS, IPI, ISS, PIS, COFINS, CSLL, IRPJ, INSS, FGTS) por base."""
    base = {k: 0.0 for k in BASES_TRIBUTARIAS}
    base["faturamento"] = float(cfg.economico.taxa_impostos_faturamento_pct) / 100
    base["lucro"] = float(cfg.economico.taxa_impostos_lucro_pct) / 100
    base["folha"] = float(cfg.economico.encargos_mao_obra_pct) / 100
    apelidos = {a: k for k, v in BASES_TRIBUTARIAS.items() for a in v}
    for imp in cfg.economico.impostos_configurados:
        b = apelidos.get(imp.get("base", "faturamento"))
        if b is None:
            raise ValueError(f"Base tributária desconhecida: {imp.get('base')}")
        aliq = imp["aliquota_pct"] / 100 if "aliquota_pct" in imp else float(imp.get("aliquota", 0))
        base[b] += float(aliq)
    return base


def remuneracao_mensal(cfg: EVTEASConfig) -> Dict[str, float]:
    """Remuneração bruta mensal: CLT (por cargo), retirada dos cooperados e mão de obra genérica."""
    e = cfg.economico
    clt = float(sum(e.salarios_clt_por_cargo.values()))
    ret = float(e.retirada_cooperados_mes)
    outros = float(e.mao_obra_mes)
    return {"clt": clt, "retirada": ret, "outros": outros, "total": clt + ret + outros}


def custo_pessoal_mensal(cfg: EVTEASConfig, aliq: Dict[str, float]) -> float:
    r = remuneracao_mensal(cfg)
    return r["clt"] * (1 + aliq["folha_clt"]) + r["retirada"] * (1 + aliq["pro_labore"]) + r["outros"] * (1 + aliq["folha"])


def meses_ate_despesca(cfg: EVTEASConfig) -> int:
    e = cfg.economico
    if e.meses_ate_primeira_receita > 0 or not e.carencia_automatica:
        return int(max(e.meses_ate_primeira_receita, 0))
    return int(math.ceil(cfg.tecnico.ciclo_dias / 30.4375))


def calcular_economico(ctx: Contexto, tec: Dict[str, Any]) -> Dict[str, Any]:
    cfg, e = ctx.cfg, ctx.cfg.economico
    n = ctx.n
    H = int(max(e.horizonte_anos, 1))
    M = H * 12
    meses = np.arange(1, M + 1)
    ano = np.ceil(meses / 12).astype(int)
    L = meses_ate_despesca(cfg)
    if L >= M:
        raise ValueError(f"A carência até a primeira receita ({L} meses) deve ser menor que o horizonte ({M} meses)")
    aliq = aliquotas_configuradas(cfg)

    # Rampa de capacidade (aprendizado) aplicada à produção em engorda
    cap0 = e.capacidade_inicial_pct / 100
    rampa = cap0 + (1 - cap0) * np.minimum((meses - 1) / max(e.meses_rampa, 1), 1.0) if e.meses_rampa > 0 else np.ones(M)
    rampa = rampa[None, :]

    fator_preco = ((1 + e.crescimento_preco_aa_pct / 100) ** (ano - 1))[None, :]
    fator_custo = ((1 + e.crescimento_custos_aa_pct / 100) ** (ano - 1))[None, :]

    fator_vendas = ((1 + e.crescimento_vendas_aa_pct / 100) ** (ano - 1))[None, :]
    prod_mes = tec["producao_kg_mes"][:, None]
    if e.producao_vendas_kg_mes > 0:
        # volume de vendas informado no mix; a incerteza técnica é preservada pela razão amostra/base
        base_tec = float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
        prod_mes = e.producao_vendas_kg_mes * safe_div(prod_mes, base_tec, 1.0)
    em_engorda = prod_mes * rampa * fator_vendas                    # kg/mês em crescimento
    vendida = np.zeros((n, M))
    vendida[:, L:] = em_engorda[:, : M - L]                        # despesca após o 1º ciclo

    escala_preco = safe_div(ctx.v("economico.preco_venda_kg"), e.preco_venda_kg, 1.0)
    preco = preco_medio(cfg) * escala_preco[:, None] * fator_preco
    receita_produtos = vendida * preco
    receita_servicos = np.where(meses > L, e.receita_servicos_mes, 0.0)[None, :] * fator_preco * np.ones((n, 1))
    receita = receita_produtos + receita_servicos

    custo_racao = em_engorda * tec["racao_por_kg_produzido"][:, None] * ctx.v("economico.custo_racao_kg")[:, None] * fator_custo
    # escala de volume: vendas informadas no mix e crescimento de vendas também movem a estocagem
    escala_volume = safe_div(prod_mes, tec["producao_kg_mes"][:, None], 1.0) * fator_vendas
    alevinos_mes = tec["alevinos_ano"][:, None] / 12 * rampa * escala_volume
    custo_alevinos = alevinos_mes * ctx.v("economico.custo_alevino_milheiro")[:, None] / 1000 * fator_custo
    kwh_kg = energia_kwh_kg(cfg)
    custo_energia = em_engorda * kwh_kg * ctx.v("economico.tarifa_energia_kwh")[:, None] * fator_custo
    # valor mensal informado "a 100% da capacidade": acompanha a rampa e o crescimento de vendas
    outros_var = (vendida * e.outros_custos_variaveis_kg
                  + e.outros_custos_variaveis_mes * rampa * fator_vendas) * fator_custo
    custos_variaveis = custo_racao + custo_alevinos + custo_energia + outros_var

    capex = e.capex_total * ctx.v("economico.capex_fator")
    fixos_fator = ctx.v("economico.custos_fixos_fator")[:, None]
    pessoal = custo_pessoal_mensal(cfg, aliq)
    if e.manutencao_mes is not None:
        # valor informado em R$/mês para o CAPEX estimado; acompanha o CAPEX sorteado no Monte Carlo
        manutencao = float(e.manutencao_mes) * ctx.v("economico.capex_fator")[:, None]
    else:
        manutencao = capex[:, None] * e.manutencao_capex_pct_aa / 100 / 12
    custos_fixos = (pessoal + e.assistencia_tecnica_mes + e.administrativo_mes + manutencao) * fixos_fator * fator_custo

    vida_meses = max(e.vida_util_anos, 0.0) * 12
    depreciacao = np.where(meses <= vida_meses, 1.0, 0.0)[None, :] * safe_div(capex, vida_meses, 0.0)[:, None]

    impostos_fat = (receita_produtos * (aliq["faturamento"] + aliq["produtos"])
                    + receita_servicos * (aliq["faturamento"] + aliq["servicos"]))
    receita_liquida = receita - impostos_fat
    lucro_bruto = receita_liquida - custos_variaveis
    ebitda = lucro_bruto - custos_fixos
    lair = ebitda - depreciacao
    impostos_lucro = np.maximum(lair, 0) * aliq["lucro"]
    lucro_liquido = lair - impostos_lucro
    fco = lucro_liquido + depreciacao

    investimento = capex + e.capital_giro
    residual = (float(e.valor_residual_rs) * ctx.v("economico.capex_fator") if e.valor_residual_rs is not None
                else capex * e.valor_residual_pct / 100)
    estoque_final = (custo_racao + custo_alevinos + custo_energia)[:, M - L:].sum(axis=1) if L > 0 else np.zeros(n)
    terminal = residual + e.capital_giro + estoque_final

    fluxo = np.zeros((n, M + 1))
    fluxo[:, 0] = -investimento
    fluxo[:, 1:] = fco
    fluxo[:, -1] += terminal

    tma_am = float(taxa_anual_para_mensal(e.tma_aa_pct / 100))
    vpl_v = vpl(np.full(n, tma_am), fluxo)
    tir_am, diag_tir = tir(fluxo)
    tir_aa = taxa_mensal_para_anual(tir_am)
    pb_s = payback(fluxo)
    pb_d = payback(fluxo, np.full(n, tma_am))
    il = safe_div(vpl_v + investimento, investimento, np.nan)

    # Perspectiva do beneficiário: parte do CAPEX aportada por fomento não reembolsável
    fomento = capex * e.fomento_nao_reembolsavel_pct / 100
    fluxo_benef = fluxo.copy()
    fluxo_benef[:, 0] += fomento
    vpl_benef = vpl(np.full(n, tma_am), fluxo_benef)
    tir_benef_am, _ = tir(fluxo_benef)

    # Ano de regime: primeiro ano inteiro com capacidade plena e vendas
    ano_regime = int(min(math.ceil((max(e.meses_rampa, 0) + L) / 12) + 1, H))
    sel = ano == ano_regime

    def anual(x):
        return x[:, sel].sum(axis=1)

    rec_r, var_r, fix_r = anual(receita), anual(custos_variaveis), anual(custos_fixos)
    imp_r, dep_r, ll_r = anual(impostos_fat), anual(depreciacao), anual(lucro_liquido)
    kg_r = anual(vendida)
    imc = safe_div(rec_r - imp_r - var_r, rec_r, 0.0)
    pe_receita = np.where(imc > 0, safe_div(fix_r + dep_r, np.where(imc > 0, imc, 1.0), np.nan), np.nan)
    margem_seg = np.where(np.isfinite(pe_receita), safe_div(rec_r - pe_receita, rec_r, np.nan), -1.0)
    valor_adicionado = rec_r - (anual(custo_racao) + anual(custo_alevinos) + anual(custo_energia) + anual(outros_var))

    return {
        "meses_ate_despesca": L,
        "ano_regime": ano_regime,
        "aliquotas": aliq,
        "preco_medio_kg": preco[:, 0],
        "capex": capex,
        "investimento_total": investimento,
        "fluxo_caixa": fluxo,
        "tma_mensal": tma_am,
        "vpl": vpl_v,
        "tir_mensal": tir_am,
        "tir_anual": tir_aa,
        "diagnostico_tir": diag_tir,
        "payback_simples_meses": pb_s,
        "payback_descontado_meses": pb_d,
        "indice_lucratividade": il,
        "fomento_nao_reembolsavel": fomento,
        "fluxo_caixa_beneficiario": fluxo_benef,
        "vpl_beneficiario": vpl_benef,
        "tir_anual_beneficiario": taxa_mensal_para_anual(tir_benef_am),
        "payback_descontado_beneficiario_meses": payback(fluxo_benef, np.full(n, tma_am)),
        "receita_regime": rec_r,
        "custos_variaveis_regime": var_r,
        "custos_fixos_regime": fix_r,
        "impostos_faturamento_regime": imp_r,
        "depreciacao_regime": dep_r,
        "lucro_liquido_regime": ll_r,
        "ebitda_regime": anual(ebitda),
        "kg_vendidos_regime": kg_r,
        "custo_racao_regime": anual(custo_racao),
        "custo_alevinos_regime": anual(custo_alevinos),
        "custo_energia_regime": anual(custo_energia),
        "outros_variaveis_regime": anual(outros_var),
        "pessoal_regime": anual(pessoal * fixos_fator * fator_custo * np.ones((n, M))),
        "remuneracao_regime": {k: anual(v * fixos_fator * fator_custo * np.ones((n, M)))
                               for k, v in remuneracao_mensal(cfg).items()},
        "fator_volume_regime": safe_div(anual(em_engorda), tec["producao_kg_ano"], 1.0),
        "valor_adicionado_regime": valor_adicionado,
        "indice_margem_contribuicao": imc,
        "ponto_equilibrio_receita_ano": pe_receita,
        "ponto_equilibrio_kg_ano": safe_div(pe_receita, safe_div(rec_r, kg_r, np.nan), np.nan),
        "margem_seguranca": margem_seg,
        "roi_anual_regime": safe_div(ll_r, investimento, np.nan),
        "roi_horizonte": safe_div(lucro_liquido.sum(axis=1), investimento, np.nan),
        "margem_liquida_regime": safe_div(ll_r, rec_r, np.nan),
        "custo_total_kg": safe_div(var_r + fix_r + dep_r + imp_r, kg_r, np.nan),
        "custo_operacional_efetivo_kg": safe_div(var_r + fix_r, kg_r, np.nan),
        "receita_total": receita.sum(axis=1),
        "lucro_liquido_total": lucro_liquido.sum(axis=1),
        "_series": {  # séries mensais (n, M) para a DRE
            "meses": meses, "ano": ano, "capacidade": np.broadcast_to(rampa, (n, M)),
            "producao_engorda": em_engorda, "vendida": vendida, "preco": preco,
            "receita_produtos": receita_produtos, "receita_servicos": receita_servicos,
            "receita": receita, "impostos_fat": impostos_fat, "receita_liquida": receita_liquida,
            "custo_racao": custo_racao, "custo_alevinos": custo_alevinos, "custo_energia": custo_energia,
            "outros_var": outros_var, "custos_variaveis": custos_variaveis, "lucro_bruto": lucro_bruto,
            "custos_fixos": custos_fixos, "ebitda": ebitda, "depreciacao": depreciacao, "lair": lair,
            "impostos_lucro": impostos_lucro, "lucro_liquido": lucro_liquido, "fco": fco,
        },
    }


def dre_mensal(eco: Dict[str, Any], i: int = 0) -> pd.DataFrame:
    s = eco["_series"]
    df = pd.DataFrame({
        "Mês": s["meses"], "Ano": s["ano"], "Capacidade (%)": s["capacidade"][i] * 100,
        "Produção em engorda (kg)": s["producao_engorda"][i], "Venda (kg)": s["vendida"][i],
        "Preço (R$/kg)": s["preco"][i], "Receita Produtos": s["receita_produtos"][i],
        "Receita Serviços": s["receita_servicos"][i], "Receita Bruta": s["receita"][i],
        "Impostos s/ Faturamento": s["impostos_fat"][i], "Receita Líquida": s["receita_liquida"][i],
        "Custo Ração": s["custo_racao"][i], "Custo Alevinos": s["custo_alevinos"][i],
        "Custo Energia": s["custo_energia"][i], "Outros Custos Variáveis": s["outros_var"][i],
        "Custos Variáveis": s["custos_variaveis"][i], "Lucro Bruto": s["lucro_bruto"][i],
        "Custos Fixos": s["custos_fixos"][i], "EBITDA": s["ebitda"][i], "Depreciação": s["depreciacao"][i],
        "LAIR": s["lair"][i], "Impostos s/ Lucro": s["impostos_lucro"][i],
        "Resultado Líquido": s["lucro_liquido"][i], "Fluxo de Caixa Operacional": s["fco"][i],
    })
    return df


def dre_anual(df_mensal: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in df_mensal.columns if c not in ("Mês", "Ano", "Capacidade (%)", "Preço (R$/kg)")]
    return df_mensal.groupby("Ano")[cols].sum().reset_index()


def distribuicao_sobras(cfg: EVTEASConfig, eco: Dict[str, Any]) -> Dict[str, float]:
    """Renda por cooperado (retirada + sobras) em regime — organizações cooperativas."""
    e = cfg.economico
    sobras = float(max(eco["lucro_liquido_regime"][0], 0.0))
    trab = sobras * e.perc_sobras_trabalhadores / 100
    forn = sobras - trab
    n_trab = max(e.cooperados_trabalhadores, 0)
    r = eco["remuneracao_regime"]            # em preços do ano de regime
    retirada_anual = float(r["retirada"][0] + r["outros"][0])
    renda_mensal = safe_div(retirada_anual + trab, n_trab * 12, 0.0) if n_trab else 0.0
    return {
        "termo_resultado": "Lucro líquido" if e.tipo_organizacao == "empresa" else "Sobras líquidas",
        "sobras_regime": sobras,
        "sobras_trabalhadores": trab,
        "sobras_fornecedores": forn,
        "sobra_media_trabalhador": safe_div(trab, n_trab, 0.0),
        "sobra_media_fornecedor": safe_div(forn, e.cooperados_fornecedores, 0.0),
        "renda_mensal_por_trabalhador": float(renda_mensal),
    }


# ---------------------------------------------------------------------------
# 3. Dimensão ambiental
# ---------------------------------------------------------------------------

def fator_emissao_energia(cfg: EVTEASConfig) -> float:
    a = cfg.ambiental
    fatores = dict(FATORES_EMISSAO_ENERGIA, rede=a.fator_emissao_rede_kgco2_kwh)
    if a.fonte_energia == "mista":
        return fatores["rede"] * (1 - a.fracao_renovavel_mista)
    if a.fonte_energia not in fatores:
        raise ValueError(f"Fonte de energia desconhecida: {a.fonte_energia}")
    return fatores[a.fonte_energia]


def score_conformidade(cfg: EVTEASConfig) -> Dict[str, Any]:
    a = cfg.ambiental
    itens = dict(a.checklist)
    itens["respeita_app"] = bool(itens.get("respeita_app", False)) and a.distancia_app_m >= a.faixa_app_minima_m
    total = sum(p for _, p, _ in CHECKLIST_AMBIENTAL.values())
    obtido = sum(p for k, (_, p, _) in CHECKLIST_AMBIENTAL.items() if itens.get(k, False))
    vetos = [CHECKLIST_AMBIENTAL[k][0] for k, (_, _, elim) in CHECKLIST_AMBIENTAL.items() if elim and not itens.get(k, False)]
    detalhe = [{"Item": d, "Peso": p, "Eliminatório": elim, "Atendido": bool(itens.get(k, False))}
               for k, (d, p, elim) in CHECKLIST_AMBIENTAL.items()]
    return {"score_0_10": 10 * obtido / total, "vetos": vetos, "detalhe": detalhe}


def calcular_ambiental(ctx: Contexto, tec: Dict[str, Any], eco: Dict[str, Any]) -> Dict[str, Any]:
    cfg, a, t = ctx.cfg, ctx.cfg.ambiental, ctx.cfg.tecnico
    # volume efetivo no ano de regime (vendas do mix e crescimento de vendas incluídos)
    fator = eco["fator_volume_regime"]
    prod = tec["producao_kg_ano"] * fator
    prod_t = prod / 1000
    vol = tec["volume_util_m3"]
    disp = float(tec["disponibilidade"][0])

    # Gestão hídrica (m³/ano)
    enchimento = vol * disp * t.ciclos_ano if a.esvaziamento_por_ciclo else vol * disp / max(eco_horizonte(cfg), 1)
    renovacao = vol * disp * renovacao_pct_dia(cfg) / 100 * 365
    evaporacao = a.evaporacao_mm_dia / 1000 * t.area_lamina_m2 * disp * 365
    infiltracao = a.infiltracao_mm_dia / 1000 * t.area_lamina_m2 * disp * 365
    captada = enchimento + renovacao + evaporacao + infiltracao
    azul = evaporacao + a.fracao_retorno_perdida * (enchimento + renovacao)
    ph_azul = safe_div(azul, prod_t, np.nan)

    # Balanço de nutrientes e pegada hídrica cinza (poluente crítico)
    racao = tec["racao_ano_kg"] * fator
    ganho = tec["ganho_biomassa_ano_kg"] * fator
    n_in = racao * a.proteina_racao_pct / 100 / 6.25
    p_in = racao * a.fosforo_racao_pct / 100
    n_ret = ganho * a.nitrogenio_peixe_pct / 100
    p_ret = ganho * a.fosforo_peixe_pct / 100
    n_carga = np.maximum(n_in - n_ret, 0) * (1 - a.remocao_n_tratamento_pct / 100)
    p_carga = np.maximum(p_in - p_ret, 0) * (1 - a.remocao_p_tratamento_pct / 100)
    dn = a.n_max_mg_l - a.n_natural_mg_l
    dp = a.p_max_mg_l - a.p_natural_mg_l
    if dn <= 0 or dp <= 0:
        raise ValueError("Concentração máxima deve superar a natural (pegada hídrica cinza indefinida)")
    cinza_n = n_carga * 1000 / dn       # kg -> g; mg/L = g/m³
    cinza_p = p_carga * 1000 / dp
    cinza = np.maximum(cinza_n, cinza_p)
    critico = np.where(cinza_p >= cinza_n, "fósforo total", "nitrogênio total")

    # Energia e emissões (proxy de pegada de carbono)
    energia = energia_kwh_kg(cfg) * prod
    fe = fator_emissao_energia(cfg)
    co2_energia = energia * fe
    co2_racao = racao * a.fator_emissao_racao_kgco2_kg
    co2_diesel = np.full(ctx.n, a.diesel_l_ano * a.fator_emissao_diesel_kgco2_l)
    co2_total = co2_energia + co2_racao + co2_diesel
    intensidade = safe_div(co2_total, prod, np.nan)

    residuos = prod * a.residuos_kg_por_kg
    conf = score_conformidade(cfg)

    va = eco["valor_adicionado_regime"]
    # Ecoeficiência (WBCSD): valor adicionado / influência ambiental. Indefinida se VA <= 0.
    eco_carbono = np.where(va > 0, safe_div(va, co2_total, np.nan), np.nan)
    eco_agua = np.where(va > 0, safe_div(va, azul, np.nan), np.nan)

    return {
        "producao_t_ano": prod_t,
        "agua_captada_m3_ano": captada,
        "agua_enchimento_m3_ano": np.full(ctx.n, enchimento),
        "agua_renovacao_m3_ano": np.full(ctx.n, renovacao),
        "agua_evaporacao_m3_ano": np.full(ctx.n, evaporacao),
        "agua_infiltracao_m3_ano": np.full(ctx.n, infiltracao),
        "ph_azul_m3_ano": np.full(ctx.n, azul) if np.ndim(azul) == 0 else azul,
        "ph_azul_m3_t": ph_azul,
        "indice_uso_agua_kg_m3": safe_div(prod, captada, 0.0),
        "n_aportado_kg": n_in, "n_retido_kg": n_ret, "n_lancado_kg": n_carga,
        "p_aportado_kg": p_in, "p_retido_kg": p_ret, "p_lancado_kg": p_carga,
        "ph_cinza_m3_ano": cinza,
        "ph_cinza_m3_t": safe_div(cinza, prod_t, np.nan),
        "poluente_critico": critico,
        "energia_kwh_ano": energia,
        "fator_emissao_energia": fe,
        "co2e_energia_t": co2_energia / 1000,
        "co2e_racao_t": co2_racao / 1000,
        "co2e_diesel_t": co2_diesel / 1000,
        "co2e_total_t_ano": co2_total / 1000,
        "intensidade_carbono_kgco2e_kg": intensidade,
        "residuos_kg_ano": residuos,
        "residuos_reaproveitados_kg_ano": residuos * a.residuos_reaproveitados_pct / 100,
        "valor_adicionado_regime": va,
        "ecoeficiencia_r_por_kgco2e": eco_carbono,
        "ecoeficiencia_r_por_m3_azul": eco_agua,
        "ecoeficiencia_status": np.where(va > 0, "definida", "não definida (valor adicionado ≤ 0)"),
        "conformidade_0_10": conf["score_0_10"],
        "conformidade_detalhe": conf["detalhe"],
        "vetos_ambientais": conf["vetos"],
    }


def eco_horizonte(cfg: EVTEASConfig) -> int:
    return int(cfg.economico.horizonte_anos)


# ---------------------------------------------------------------------------
# 4. Dimensão social e governança
# ---------------------------------------------------------------------------

def calcular_social(ctx: Contexto, eco: Dict[str, Any]) -> Dict[str, Any]:
    cfg, s = ctx.cfg, ctx.cfg.social
    rem = eco["remuneracao_regime"]          # remuneração anual em preços do ano de regime
    massa_anual = rem["total"]
    massa_local = massa_anual * s.mao_obra_local_pct / 100
    compras = (eco["custos_variaveis_regime"] + eco["custos_fixos_regime"] - eco["pessoal_regime"])
    compras_locais = np.maximum(compras, 0) * s.compras_locais_pct / 100
    custo_operacional = eco["custos_variaveis_regime"] + eco["custos_fixos_regime"]
    rvl = 100 * safe_div(massa_local + compras_locais, custo_operacional, 0.0)

    sobras = np.maximum(eco["lucro_liquido_regime"], 0) * cfg.economico.perc_sobras_trabalhadores / 100
    if cfg.economico.tipo_organizacao == "empresa":
        sobras = np.zeros(ctx.n)
    renda_local = massa_local + sobras * s.mao_obra_local_pct / 100
    iil = safe_div(renda_local, eco["receita_regime"], 0.0)
    if cfg.economico.tipo_organizacao != "empresa" and cfg.economico.cooperados_trabalhadores > 0:
        n_trab = cfg.economico.cooperados_trabalhadores
        renda_mensal = (rem["retirada"] + rem["outros"] + sobras) / n_trab / 12
    else:   # empresa, ou cooperativa sem cooperados na operação: renda paga a quem trabalha
        n_trab = max(s.empregos_diretos, 1)
        renda_mensal = (rem["clt"] + rem["outros"] + rem["retirada"]) / n_trab / 12
    # renda em preços do ano de regime: o salário mínimo é levado ao mesmo nível de preços
    sm_regime = s.salario_minimo * (1 + cfg.economico.crescimento_custos_aa_pct / 100) ** (eco["ano_regime"] - 1)
    renda_sm = renda_mensal / sm_regime

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
    risco = 1 / (1 + math.exp(8 * (lso / 100 - 0.5)))   # heurística logística (a calibrar)

    radar = {
        "Emprego local": np.full(ctx.n, s.mao_obra_local_pct / 100),
        "Renda": clamp((renda_sm - 0.5) / 1.5),
        "Segurança (NR)": np.full(ctx.n, s.conformidade_nr_pct / 100),
        "Capacitação": np.full(ctx.n, min(s.capacitacao_horas_pessoa_ano / 40, 1.0)),
        "Relação com a comunidade": np.full(ctx.n, relacao),
        "Inclusão": np.full(ctx.n, 0.5 * min(s.mulheres_pct / 50, 1) + 0.5 * min(s.jovens_pct / 30, 1)),
    }
    radar_score = np.mean(np.vstack(list(radar.values())), axis=0)

    return {
        "empregos_diretos": s.empregos_diretos,
        "empregos_indiretos": s.empregos_indiretos,
        "empregos_totais": s.empregos_diretos + s.empregos_indiretos,
        "massa_salarial_anual": massa_anual,
        "massa_salarial_local": massa_local,
        "compras_locais_regime": compras_locais,
        "rvl_pct": rvl,
        "indice_impacto_local": iil,
        "renda_mensal_trabalhador": renda_mensal,
        "renda_em_salarios_minimos": renda_sm,
        "lso_0_100": np.full(ctx.n, lso),
        "lso_componentes": componentes_lso,
        "risco_social": np.full(ctx.n, risco),
        "radar_social": radar,
        "radar_social_score": radar_score,
    }


def calcular_governanca(cfg: EVTEASConfig) -> Dict[str, Any]:
    itens = cfg.governanca.itens
    return {"score_0_1": safe_div(sum(bool(v) for v in itens.values()), len(itens), 0.0), "itens": dict(itens)}


def alinhamento_ods(cfg: EVTEASConfig, tec, eco, amb, soc, gov, i: int = 0):
    """Identificação automática dos ODS atendidos (regras explícitas e auditáveis)."""
    a, s = cfg.ambiental, cfg.social
    regras = [
        ("ODS 1 — Erradicação da pobreza", s.publico_vulneravel and soc["renda_em_salarios_minimos"][i] >= 1.0,
         "renda média por trabalhador ≥ 1 salário mínimo em público vulnerável"),
        ("ODS 2 — Fome zero e agricultura sustentável", tec["producao_kg_ano"][i] > 0,
         "produção de proteína animal de base aquícola"),
        ("ODS 5 — Igualdade de gênero", s.mulheres_pct >= 30, "participação feminina ≥ 30%"),
        ("ODS 6 — Água potável e saneamento", bool(a.checklist.get("tratamento_efluentes")) and bool(a.checklist.get("outorga_agua")),
         "tratamento de efluentes e outorga de uso da água"),
        ("ODS 7 — Energia limpa", a.fonte_energia in ("solar", "biomassa") or (a.fonte_energia == "mista" and a.fracao_renovavel_mista >= 0.5),
         "fonte de energia predominantemente renovável"),
        ("ODS 8 — Trabalho decente e crescimento econômico", s.conformidade_nr_pct >= 80 and soc["renda_em_salarios_minimos"][i] >= 1.0,
         "conformidade com NR ≥ 80% e renda ≥ 1 salário mínimo"),
        ("ODS 12 — Consumo e produção responsáveis", tec["fcr"][i] <= cfg.tecnico.fcr_referencia * 1.15 and a.residuos_reaproveitados_pct >= 50,
         "FCR até 15% acima da referência e reaproveitamento de resíduos ≥ 50%"),
        ("ODS 13 — Ação contra a mudança do clima", amb["intensidade_carbono_kgco2e_kg"][i] <= 2.0,
         "intensidade de carbono ≤ 2,0 kgCO2e/kg"),
        ("ODS 14 — Vida na água (meta 14.b: pescadores artesanais)", s.publico_vulneravel,
         "acesso de pescadores artesanais a recursos e mercados"),
        ("ODS 15 — Vida terrestre", a.distancia_app_m >= a.faixa_app_minima_m and bool(a.checklist.get("prevencao_escape")),
         "APP preservada e prevenção de escape de espécie exótica"),
        ("ODS 16 — Instituições eficazes", gov["score_0_1"] >= 0.7, "governança cooperativa ≥ 70% do checklist"),
    ]
    return pd.DataFrame([{"ODS": o, "Atendido": bool(c), "Critério": crit} for o, c, crit in regras])


# ---------------------------------------------------------------------------
# 5. Lean-Green: custo dos desperdícios evitáveis
# ---------------------------------------------------------------------------

def calcular_lean_green(ctx: Contexto, tec, eco) -> Dict[str, Any]:
    cfg, t = ctx.cfg, ctx.cfg.tecnico
    custo_racao = ctx.v("economico.custo_racao_kg")
    fator = eco["fator_volume_regime"]
    racao_exc = np.maximum(tec["fcr"] - t.fcr_referencia, 0) * tec["ganho_biomassa_ano_kg"] * fator
    mort = ctx.v("tecnico.mortalidade_pct")
    peixes_perdidos = np.maximum(mort - t.mortalidade_referencia_pct, 0) / 100 * tec["alevinos_ano"] * fator
    # perdas ocorrem, em média, na metade do ciclo (metade do peso final e da ração)
    custo_peixe = (ctx.v("economico.custo_alevino_milheiro") / 1000
                   + 0.5 * t.peso_final_g / 1000 * tec["fcr"] * custo_racao)
    kwh = energia_kwh_kg(cfg)
    energia_exc = max(kwh - cfg.ambiental.energia_referencia_kwh_kg, 0) * tec["producao_kg_ano"] * fator
    custos = {
        "Ração excedente (superalimentação/FCR)": racao_exc * custo_racao,
        "Mortalidade evitável": peixes_perdidos * custo_peixe,
        "Energia excedente": energia_exc * ctx.v("economico.tarifa_energia_kwh"),
    }
    total = sum(custos.values())
    opex = eco["custos_variaveis_regime"] + eco["custos_fixos_regime"]
    return {"desperdicios_r_ano": custos, "total_r_ano": total, "pct_opex": safe_div(total, opex, 0.0),
            "racao_excedente_kg": racao_exc, "peixes_perdidos_evitaveis": peixes_perdidos,
            "energia_excedente_kwh": energia_exc}

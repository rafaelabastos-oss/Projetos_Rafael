"""Interfaces de entrada: wizard interativo, arquivos JSON e análise de preços.

O wizard preserva o percurso de coleta das versões anteriores (Viabilidade
econômica Rev. 8/9 e EVTEAS master): tipo de organização, mix de produtos,
CAPEX, custos, cooperados, tributos, rampa e parâmetros ESG. Toda pergunta
aceita Enter para manter o valor exibido entre colchetes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

from .config import EVTEASConfig, config_de_dict, config_para_dict
from .casos import criar_config_caso_base


def salvar_config(cfg: EVTEASConfig, caminho) -> str:
    Path(caminho).write_text(json.dumps(config_para_dict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(caminho)


def carregar_config(caminho) -> EVTEASConfig:
    return config_de_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))


def _num(txt: str) -> float:
    txt = txt.strip().replace("R$", "").replace("%", "").strip()
    if "," in txt and "." in txt:
        txt = txt.replace(".", "").replace(",", ".") if txt.rfind(",") > txt.rfind(".") else txt.replace(",", "")
    elif "," in txt:
        txt = txt.replace(",", ".")
    return float(txt)


def perguntar_numero(rotulo: str, atual: float, minimo: Optional[float] = 0.0, maximo: Optional[float] = None,
                     entrada: Callable[[str], str] = input) -> float:
    while True:
        txt = entrada(f"{rotulo} [{atual}]: ").strip()
        if not txt:
            return atual
        try:
            v = _num(txt)
        except ValueError:
            print("  Valor inválido; use números (vírgula ou ponto decimal).")
            continue
        if minimo is not None and v < minimo:
            print(f"  Valor deve ser ≥ {minimo}.")
        elif maximo is not None and v > maximo:
            print(f"  Valor deve ser ≤ {maximo}.")
        else:
            return v


def perguntar_opcao(rotulo: str, atual: str, opcoes, entrada: Callable[[str], str] = input) -> str:
    while True:
        txt = entrada(f"{rotulo} {list(opcoes)} [{atual}]: ").strip()
        if not txt:
            return atual
        if txt in opcoes:
            return txt
        print("  Opção inválida.")


def perguntar_sim_nao(rotulo: str, atual: bool, entrada: Callable[[str], str] = input) -> bool:
    while True:
        txt = entrada(f"{rotulo} (s/n) [{'s' if atual else 'n'}]: ").strip().lower()
        if not txt:
            return atual
        if txt in ("s", "n"):
            return txt == "s"


def wizard_evteas(entrada: Callable[[str], str] = input, base: Optional[EVTEASConfig] = None) -> EVTEASConfig:
    """Coleta guiada das premissas, bloco a bloco (lógica PMBOK de iniciação/planejamento)."""
    cfg = base or criar_config_caso_base()
    t, e, a, s = cfg.tecnico, cfg.economico, cfg.ambiental, cfg.social
    print("=== EVTEAS-Py — entrada de dados (Enter mantém o valor) ===")
    cfg.projeto = entrada(f"Nome do projeto [{cfg.projeto}]: ").strip() or cfg.projeto

    print("\n--- 1. Técnico: infraestrutura ---")
    t.sistema_produtivo = perguntar_opcao("Sistema produtivo", t.sistema_produtivo,
                                          ["extensivo", "semi-intensivo", "intensivo", "superintensivo"], entrada)
    t.area_lamina_m2 = perguntar_numero("Área de lâmina d'água (m²)", t.area_lamina_m2, 1, None, entrada)
    t.profundidade_media_m = perguntar_numero("Profundidade média (m)", t.profundidade_media_m, 0.1, 10, entrada)
    t.numero_tanques = int(perguntar_numero("Número de viveiros/tanques", t.numero_tanques, 1, None, entrada))
    t.tanques_ativos = int(perguntar_numero("Viveiros ativos", t.tanques_ativos, 0, t.numero_tanques, entrada))
    print("--- 1. Técnico: parâmetros biológicos e insumos ---")
    t.peso_inicial_g = perguntar_numero("Peso inicial dos alevinos/juvenis (g)", t.peso_inicial_g, 0.1, None, entrada)
    t.peso_final_g = perguntar_numero("Peso de abate (g)", t.peso_final_g, t.peso_inicial_g, None, entrada)
    t.ciclo_dias = int(perguntar_numero("Duração do ciclo (dias)", t.ciclo_dias, 1, 730, entrada))
    t.ciclos_ano = perguntar_numero("Ciclos por ano (escalonados)", t.ciclos_ano, 0, 365 / t.ciclo_dias, entrada)
    t.produtividade_esperada_kg_m2_ciclo = perguntar_numero("Produtividade esperada (kg/m²/ciclo; 0 ignora)",
                                                            t.produtividade_esperada_kg_m2_ciclo, 0, None, entrada)
    t.fcr = perguntar_numero("Conversão alimentar — FCR/TCA", t.fcr, 0.5, 5, entrada)
    t.mortalidade_pct = perguntar_numero("Mortalidade (%)", t.mortalidade_pct, 0, 100, entrada)

    print("\n--- 2. Econômico ---")
    e.tipo_organizacao = perguntar_opcao("Tipo de organização", e.tipo_organizacao,
                                         ["empresa", "coop_trabalho", "coop_agro"], entrada)
    if perguntar_sim_nao("Detalhar itens de CAPEX?", False, entrada):
        itens = {}
        while True:
            nome = entrada("  Item de CAPEX (Enter encerra): ").strip()
            if not nome:
                break
            itens[nome] = perguntar_numero(f"  Valor de '{nome}' (R$)", 0.0, 0, None, entrada)
        if itens:
            e.capex_itens = itens
    e.classe_estimativa_aace = int(perguntar_numero("Classe da estimativa AACE (1 a 5)", e.classe_estimativa_aace, 1, 5, entrada))
    e.capital_giro = perguntar_numero("Capital de giro (R$)", e.capital_giro, 0, None, entrada)
    e.fomento_nao_reembolsavel_pct = perguntar_numero("Fomento não reembolsável (% do CAPEX)",
                                                      e.fomento_nao_reembolsavel_pct, 0, 100, entrada)
    if perguntar_sim_nao("Informar mix de produtos?", bool(e.mix_produtos), entrada):
        mix = []
        k = int(perguntar_numero("  Quantidade de produtos", max(len(e.mix_produtos), 1), 1, None, entrada))
        for j in range(k):
            nome = entrada(f"  Nome do produto {j + 1}: ").strip() or f"Produto {j + 1}"
            mix.append({"nome": nome,
                        "participacao_pct": perguntar_numero(f"  Participação de '{nome}' no volume (%)", 100 / k, 0, 100, entrada),
                        "preco_kg": perguntar_numero(f"  Preço de '{nome}' (R$/kg)", e.preco_venda_kg, 0, None, entrada)})
        e.mix_produtos = mix
    else:
        e.preco_venda_kg = perguntar_numero("Preço de venda (R$/kg)", e.preco_venda_kg, 0, None, entrada)
    e.custo_racao_kg = perguntar_numero("Custo da ração (R$/kg)", e.custo_racao_kg, 0, None, entrada)
    e.custo_alevino_milheiro = perguntar_numero("Custo do milheiro de alevinos (R$)", e.custo_alevino_milheiro, 0, None, entrada)
    e.tarifa_energia_kwh = perguntar_numero("Tarifa de energia (R$/kWh)", e.tarifa_energia_kwh, 0, None, entrada)
    e.mao_obra_mes = perguntar_numero("Mão de obra / retiradas (R$/mês)", e.mao_obra_mes, 0, None, entrada)
    e.encargos_mao_obra_pct = perguntar_numero("Encargos sobre a mão de obra (%)", e.encargos_mao_obra_pct, 0, 100, entrada)
    if e.tipo_organizacao != "empresa":
        minimo = 7 if e.tipo_organizacao == "coop_trabalho" else 20
        print(f"  (Lei nº 12.690/2012 e Lei nº 5.764/1971: mínimo usual de {minimo} cooperados no total)")
        e.cooperados_trabalhadores = int(perguntar_numero("Cooperados que trabalham", e.cooperados_trabalhadores, 0, None, entrada))
        e.cooperados_fornecedores = int(perguntar_numero("Cooperados fornecedores", e.cooperados_fornecedores, 0, None, entrada))
        e.perc_sobras_trabalhadores = perguntar_numero("% das sobras aos trabalhadores", e.perc_sobras_trabalhadores, 0, 100, entrada)
    e.taxa_impostos_faturamento_pct = perguntar_numero("Tributos sobre faturamento (%)", e.taxa_impostos_faturamento_pct, 0, 100, entrada)
    e.taxa_impostos_lucro_pct = perguntar_numero("Tributos sobre lucro (%)", e.taxa_impostos_lucro_pct, 0, 100, entrada)
    e.tma_aa_pct = perguntar_numero("TMA (% a.a.)", e.tma_aa_pct, 0, 100, entrada)
    e.horizonte_anos = int(perguntar_numero("Horizonte (anos)", e.horizonte_anos, 1, 50, entrada))

    print("\n--- 3. Ambiental ---")
    a.fonte_energia = perguntar_opcao("Fonte de energia", a.fonte_energia, ["rede", "solar", "biomassa", "mista"], entrada)
    a.remocao_p_tratamento_pct = perguntar_numero("Remoção de fósforo no tratamento (%)", a.remocao_p_tratamento_pct, 0, 100, entrada)
    a.distancia_app_m = perguntar_numero("Distância da APP (m)", a.distancia_app_m, 0, None, entrada)
    for k in list(a.checklist):
        a.checklist[k] = perguntar_sim_nao(f"Atende: {k.replace('_', ' ')}?", a.checklist[k], entrada)

    print("\n--- 4. Social ---")
    s.empregos_diretos = int(perguntar_numero("Empregos diretos", s.empregos_diretos, 0, None, entrada))
    s.empregos_indiretos = int(perguntar_numero("Empregos indiretos", s.empregos_indiretos, 0, None, entrada))
    s.mao_obra_local_pct = perguntar_numero("Mão de obra local (%)", s.mao_obra_local_pct, 0, 100, entrada)
    s.compras_locais_pct = perguntar_numero("Compras locais (%)", s.compras_locais_pct, 0, 100, entrada)
    s.conformidade_nr_pct = perguntar_numero("Conformidade com NR (%)", s.conformidade_nr_pct, 0, 100, entrada)
    s.relacao_comunidade = perguntar_opcao("Relação com a comunidade", s.relacao_comunidade,
                                           ["inexistente", "parcial", "consolidado"], entrada)
    s.reunioes_comunidade_ano = int(perguntar_numero("Reuniões com a comunidade por ano", s.reunioes_comunidade_ano, 0, None, entrada))
    s.conflitos_registrados_ano = int(perguntar_numero("Conflitos registrados por ano", s.conflitos_registrados_ano, 0, None, entrada))
    s.mulheres_pct = perguntar_numero("Participação feminina (%)", s.mulheres_pct, 0, 100, entrada)

    print("\n--- 5. Governança ---")
    for k in list(cfg.governanca.itens):
        cfg.governanca.itens[k] = perguntar_sim_nao(f"Atende: {k.replace('_', ' ')}?", cfg.governanca.itens[k], entrada)
    print("\nEntradas registradas.")
    return cfg


# ---------------------------------------------------------------------------
# Análise de preços a partir de planilha (herdada da versão anterior)
# ---------------------------------------------------------------------------

def analisar_precos(df: pd.DataFrame, col_preco: str, col_qtd: Optional[str] = None,
                    custo_unitario: float = 0.0, z_corte: float = 3.0) -> Dict[str, Any]:
    """Histórico de preços (estatísticas e estratégias) ou, com quantidades,
    curva de demanda linear e preço que maximiza a margem de contribuição."""
    d = df[[c for c in (col_preco, col_qtd) if c]].apply(pd.to_numeric, errors="coerce").dropna()
    d = d[d[col_preco] > 0]
    if len(d) > 10:
        z = ((d - d.mean()) / d.std(ddof=0)).abs()
        d = d[(z <= z_corte).all(axis=1)]
    if d.empty:
        raise ValueError("Sem dados válidos de preço")
    p = d[col_preco]
    out: Dict[str, Any] = {"n": int(len(d)), "estatisticas": p.describe().to_dict(),
                           "sugestoes": {"Econômico (P25)": float(p.quantile(.25)), "Mediana": float(p.median()),
                                         "Premium (P75)": float(p.quantile(.75))}}
    if col_qtd and len(d) >= 5:
        b, a = np.polyfit(p, d[col_qtd], 1)
        r2 = float(np.corrcoef(p, d[col_qtd])[0, 1] ** 2)
        out["demanda"] = {"intercepto": float(a), "inclinacao": float(b), "r2": r2}
        if b < 0:
            otimo = (custo_unitario - a / b) / 2   # max (P − c)(a + bP)
            out["preco_otimo"] = float(otimo)
    return out

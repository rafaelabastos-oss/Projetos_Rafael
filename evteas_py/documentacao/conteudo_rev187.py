"""Conteúdo dos Capítulos 4 e 5 da Rev. 187, gerado a partir da execução real.

Todos os números citados no texto vêm de ``saidas/resumo_execucao.json``
(produzido por ``executar_estudo.py``), de modo que texto e código não divergem.
"""
from __future__ import annotations

import inspect
import json
import math
import re
from pathlib import Path

import evteas_py
from evteas_py import config, dsr, financeiro, incerteza, interface, modelo, pipeline, ponderacao, vv

RAIZ = Path(__file__).resolve().parents[1]
R = json.loads((RAIZ / "saidas" / "resumo_execucao.json").read_text(encoding="utf-8"))
CB = R["caso_base"]
T, E, A, S = CB["tecnico"], CB["economico"], CB["ambiental"], CB["social"]
G, LG, D = CB["governanca"], CB["lean_green"], CB["decisao"]
I, MC = R["indice"], R["mc"]
ST = MC["estatisticas"]
LEG, LK = R["legado"], R["likert"]
FONTE_COD = "Fonte: elaboração própria, a partir do pacote evteas_py 2.0 (notebook EVTEAS_Py_Rev187)."
FONTE_RES = "Fonte: elaboração própria, a partir da execução do EVTEAS-Py 2.0 (seed 20260612)."


# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------

def n(v, c=2):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "n/d"
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def rs(v, c=0):
    neg = v < 0
    s = "R$ " + n(abs(v), c)
    return ("−" + s) if neg else s


def mil(v, c=1):
    return rs(v / 1000, c) + " mil"


def pc(v, c=1):
    return n(v * 100, c) + "%"


def var(caminho):
    return caminho.split(".")[1]


# ---------------------------------------------------------------------------
# Trechos de código (extraídos do pacote; "..." indica omissão)
# ---------------------------------------------------------------------------

def fonte(obj):
    return inspect.getsource(obj).rstrip("\n")


def trecho(obj, inicio, fim, incluir_cabecalho=True):
    linhas = fonte(obj).split("\n")
    i = next(k for k, l in enumerate(linhas) if inicio in l)
    j = next(k for k, l in enumerate(linhas) if k >= i and fim in l)
    corpo = linhas[i:j + 1]
    if incluir_cabecalho and i > 0:
        cab = []
        for l in linhas:
            cab.append(l)
            if l.rstrip().endswith(":") and ("def " in l or "class " in l or l.startswith(" ")):
                break
        corpo = cab + ["    # (...)"] + corpo
    return "\n".join(corpo)


def juntar(*partes):
    return "\n    # (...)\n".join(p.rstrip("\n") for p in partes)


COD_CONFIG = "\n".join(fonte(config.EVTEASConfig).split("\n")[:15])
COD_MOTOR = fonte(modelo.Contexto) + "\n\n\n" + fonte(pipeline.motor)
COD_WIZARD = fonte(interface.iniciar_entradas)
TESTES = json.loads((RAIZ / "saidas" / "verificacao_testes.json").read_text(encoding="utf-8"))
# Revisões adversariais independentes da entrada de dados (Etapa 8), registradas em documentacao/revisoes.json
REVISOES = json.loads((Path(__file__).resolve().parent / "revisoes.json").read_text(encoding="utf-8"))
COD_TECNICO = trecho(modelo.calcular_tecnico, "# Restrição dupla", "oee = disponibilidade")
COD_ECONOMICO = juntar(
    trecho(modelo.calcular_economico, "prod_mes = tec", "receita = receita_produtos"),
    "\n".join(fonte(modelo.calcular_economico).split("\n")[
        next(k for k, l in enumerate(fonte(modelo.calcular_economico).split("\n")) if "impostos_fat = (" in l):
        next(k for k, l in enumerate(fonte(modelo.calcular_economico).split("\n")) if "il = safe_div" in l) + 1]),
)
COD_AMBIENTAL = juntar(
    trecho(modelo.calcular_ambiental, "# Balanço de nutrientes", 'critico = np.where'),
    "\n".join(l for l in fonte(modelo.calcular_ambiental).split("\n")
              if "va = eco[" in l or "Ecoeficiência (WBCSD)" in l or "eco_carbono = " in l),
)
COD_SOCIAL = trecho(modelo.calcular_social, "rem = eco[\"remuneracao_regime\"]", "risco = 1 /")
COD_DECISAO = fonte(ponderacao.classificar)
COD_TIR = fonte(financeiro.tir)
COD_MC = trecho(incerteza.monte_carlo, "n = int(n or", 'amostra["VPL"] = eco["vpl"]')
COD_CRITICOS = fonte(incerteza.valores_criticos)
COD_VV = "\n".join(fonte(vv.validar_invariantes).split("\n")[:22]) + "\n    # (...)"
COD_PIPELINE = trecho(pipeline.executar_evteas, "def executar_evteas", 'resultado["vv"] = validar_invariantes', False) + "\n    return resultado"


# ---------------------------------------------------------------------------
# Tabelas auxiliares
# ---------------------------------------------------------------------------

def _revisao_independente():
    r1, r2 = REVISOES["rodadas"][0], REVISOES["rodadas"][1]
    texto = ("Além dos testes, a entrada de dados foi submetida a revisões adversariais independentes, conduzidas com "
             "apoio de inteligência artificial generativa sob supervisão do pesquisador, nos termos da Seção 3.5. Agentes "
             "revisores, separados do desenvolvimento, tentaram quebrar o wizard com respostas inválidas e casos-limite, "
             "examinaram a clareza das perguntas e a execução no Google Colab e testaram a reabertura de arquivos de "
             f"entradas, inclusive de versões anteriores. A primeira rodada apontou {r1['apontados']} problemas, entre "
             "eles distribuições de Monte Carlo que não acompanhavam a correção de um valor, unidades diferentes entre a "
             "pergunta e o armazenamento do custo do alevino e valores em reais convertidos em percentual do CAPEX; todos "
             "foram reproduzidos, corrigidos e cobertos por testes de regressão. ")
    if r2.get("concluida"):
        texto += (f"Na segunda rodada, realizada sobre o código corrigido, cada achado foi reproduzido por um agente "
                  f"verificador independente antes de ser aceito: dos {r2['apontados']} apontamentos, {r2['confirmados']} "
                  f"foram confirmados e corrigidos{r2.get('complemento', '')}.")
    return texto


def tabela_premissas():
    cfg = evteas_py.criar_config_caso_base()
    t, e = cfg.tecnico, cfg.economico
    linhas = [
        ["Bloco", "Premissa", "Valor no caso-base", "Origem declarada"],
        ["Infraestrutura", "Área de lâmina d'água / profundidade", f"{n(t.area_lamina_m2, 0)} m² / {n(t.profundidade_media_m, 1)} m", "Estimativa do autor"],
        ["Infraestrutura", "Viveiros (total / ativos); sistema", f"{t.numero_tanques} / {t.tanques_ativos}; semi-intensivo", "Estimativa do autor"],
        ["Biológico", "Peso inicial / de abate; ciclo", f"{n(t.peso_inicial_g, 0)} g / {n(t.peso_final_g, 0)} g; {t.ciclo_dias} dias", "Bibliográfico (Kubitza, 2017)"],
        ["Biológico", "Ciclos/ano (escalonados); produtividade", f"{n(t.ciclos_ano, 1)}; {n(t.produtividade_esperada_kg_m2_ciclo, 1)} kg/m²/ciclo", "Bibliográfico (Kubitza, 2017)"],
        ["Insumos", "FCR; mortalidade", f"{n(t.fcr)}; {n(t.mortalidade_pct, 0)}%", "Bibliográfico (Kubitza, 2017)"],
        ["Econômico", "CAPEX (7 itens); capital de giro", f"{rs(e.capex_total)}; {rs(e.capital_giro)}", "Estimativa Classe 5 (AACE, 2020)"],
        ["Econômico", "Fomento não reembolsável", f"{n(e.fomento_nao_reembolsavel_pct, 0)}% do CAPEX", "Hipótese (IBAMA, 2010, 2012)"],
        ["Econômico", "Preço; ração; milheiro de alevinos", f"R$ {n(e.preco_venda_kg)}/kg; R$ {n(e.custo_racao_kg)}/kg; {rs(e.custo_alevino_milheiro)}", "Cotação (a atualizar)"],
        ["Econômico", "Retiradas de 6 cooperados; encargos", f"{rs(e.mao_obra_mes)}/mês; {n(e.encargos_mao_obra_pct, 0)}%", "Estimativa do autor"],
        ["Econômico", "TMA; horizonte; rampa", f"{n(e.tma_aa_pct, 0)}% a.a.; {e.horizonte_anos} anos; {n(e.capacidade_inicial_pct, 0)}% → 100% em {e.meses_rampa} meses", "Estimativa do autor"],
        ["Ambiental", "Limites de N e P (classe 2, lótico)", f"{n(cfg.ambiental.n_max_mg_l)} e {n(cfg.ambiental.p_max_mg_l)} mg/L", "Normativo (CONAMA 357/2005)"],
        ["Ambiental", "Remoção de N/P no tratamento; energia", f"{n(cfg.ambiental.remocao_n_tratamento_pct, 0)}% / {n(cfg.ambiental.remocao_p_tratamento_pct, 0)}%; rede", "Estimativa do autor"],
        ["Social", "Empregos diretos/indiretos; mão de obra local", f"{cfg.social.empregos_diretos} / {cfg.social.empregos_indiretos}; {n(cfg.social.mao_obra_local_pct, 0)}%", "Estimativa do autor"],
    ]
    return linhas


def tabela_economica():
    return [
        ["Indicador", "Projeto", "Beneficiário (com fomento)"],
        ["Investimento inicial (CAPEX + capital de giro)", rs(E["investimento_total"]), rs(E["investimento_total"] - E["fomento_nao_reembolsavel"])],
        ["VPL (TMA de 10% a.a.)", rs(E["vpl"]), rs(E["vpl_beneficiario"])],
        ["TIR anual (diagnóstico)", f"{pc(E['tir_anual'])} ({E['diagnostico_tir']})", pc(E["tir_anual_beneficiario"])],
        ["Payback descontado (meses)", n(E["payback_descontado_meses"], 1), n(E["payback_descontado_beneficiario_meses"], 1)],
        ["Payback simples (meses)", n(E["payback_simples_meses"], 1), "—"],
        ["Índice de lucratividade", n(E["indice_lucratividade"], 3), "—"],
        ["Receita bruta no ano de regime (ano 3)", rs(E["receita_regime"]), "—"],
        ["Lucro (sobras) líquido no ano de regime", rs(E["lucro_liquido_regime"]), "—"],
        ["ROI anual em regime (Quadro 5)", pc(E["roi_anual_regime"]), "—"],
        ["Ponto de equilíbrio (kg/ano) e margem de segurança", f"{n(E['ponto_equilibrio_kg_ano'], 0)} kg; {pc(E['margem_seguranca'])}", "—"],
        ["Custo total e custo operacional efetivo (R$/kg)", f"{n(E['custo_total_kg'])} e {n(E['custo_operacional_efetivo_kg'])}", "—"],
    ]


def tabela_ambiental_social():
    comp = S.get("lso_componentes", {})
    return [
        ["Dimensão", "Indicador", "Resultado"],
        ["Ambiental", "Água captada / índice de uso da água", f"{n(A['agua_captada_m3_ano'], 0)} m³/ano; {n(A['indice_uso_agua_kg_m3'], 3)} kg/m³"],
        ["Ambiental", "Pegada hídrica azul", f"{n(A['ph_azul_m3_t'], 0)} m³/t"],
        ["Ambiental", "Pegada hídrica cinza (poluente crítico)", f"{n(A['ph_cinza_m3_t'], 0)} m³/t ({A['poluente_critico']})"],
        ["Ambiental", "N e P lançados após tratamento", f"{n(A['n_lancado_kg'], 0)} kg N; {n(A['p_lancado_kg'], 0)} kg P"],
        ["Ambiental", "Emissões (ração / energia / diesel)", f"{n(A['co2e_total_t_ano'], 1)} tCO2e/ano ({n(A['co2e_racao_t'], 1)} / {n(A['co2e_energia_t'], 1)} / {n(A['co2e_diesel_t'], 1)})"],
        ["Ambiental", "Intensidade de carbono; ecoeficiência", f"{n(A['intensidade_carbono_kgco2e_kg'])} kgCO2e/kg; R$ {n(A['ecoeficiencia_r_por_kgco2e'])}/kgCO2e"],
        ["Ambiental", "Score de conformidade ambiental", f"{n(A['conformidade_0_10'], 2)} de 10"],
        ["Social", "Retenção de Valor Local (RVL)", f"{n(S['rvl_pct'], 1)}% do custo operacional"],
        ["Social", "Índice de Impacto Local", f"{pc(S['indice_impacto_local'])} da receita retorna como renda local"],
        ["Social", "Renda mensal por cooperado", f"{rs(S['renda_mensal_trabalhador'])} ({n(S['renda_em_salarios_minimos'])} salários mínimos)"],
        ["Social", "LSO; Score de Risco Social", f"{n(S['lso_0_100'], 1)} de 100; {n(S['risco_social'], 3)}"],
        ["Social", "Radar Social (média dos seis eixos)", n(S["radar_social_score"], 3)],
        ["Governança", "Checklist do pilar G", f"{n(G['score_0_1'] * 7, 0)} de 7 itens ({n(G['score_0_1'], 3)})"],
    ]


def tabela_mc():
    p = ST["percentis_vpl"]
    return [
        ["Estatística", "Valor"],
        ["Média do VPL (IC 95% da média)", f"{rs(ST['media_vpl'])} ({rs(ST['ic95_media_vpl'][0])} a {rs(ST['ic95_media_vpl'][1])})"],
        ["Mediana; desvio-padrão; coeficiente de variação", f"{rs(ST['mediana_vpl'])}; {rs(ST['desvio_vpl'])}; {n(ST['cv_vpl'], 2)}"],
        ["Percentis P5 / P50 / P95", f"{rs(p['p5'])} / {rs(p['p50'])} / {rs(p['p95'])}"],
        ["VaR 5% e CVaR 5% do VPL", f"{rs(ST['var5_vpl'])} e {rs(ST['cvar5_vpl'])}"],
        ["P(VPL > 0) = P(TIR > TMA)", pc(ST["prob_vpl_positivo"])],
        ["TIR anual: P5 / P50 / P95", f"{pc(ST['percentis_tir']['p5'])} / {pc(ST['percentis_tir']['p50'])} / {pc(ST['percentis_tir']['p95'])}"],
        ["Índice EVTEAS: média; P(índice ≥ 0,60)", f"{n(ST['media_indice'], 3)}; {pc(ST['prob_indice_maior_limiar'])}"],
        ["VPL do beneficiário: média; P(VPL > 0)", f"{rs(ST['media_vpl_beneficiario'])}; {pc(ST['prob_vpl_beneficiario_positivo'])}"],
        ["Erro-padrão da média com 10.000 iterações", f"{rs(MC['convergencia'][-1]['Erro-padrão'])} ({pc(MC['convergencia'][-1]['Erro-padrão'] / ST['desvio_vpl'])} do desvio-padrão)"],
    ]


def tabela_distribuicoes():
    rot = {"economico.preco_venda_kg": ("Preço de venda (R$/kg)", 2), "economico.custo_racao_kg": ("Custo da ração (R$/kg)", 2),
           "economico.custo_alevino_milheiro": ("Milheiro de alevinos (R$)", 0), "economico.tarifa_energia_kwh": ("Tarifa de energia (R$/kWh)", 2),
           "economico.custos_fixos_fator": ("Fator de custos fixos", 2), "economico.capex_fator": ("Fator de CAPEX (AACE Classe 5)", 2),
           "tecnico.fcr": ("FCR", 2), "tecnico.mortalidade_pct": ("Mortalidade (%)", 0),
           "tecnico.desempenho_crescimento_pct": ("Desempenho de crescimento (%)", 0)}
    linhas = [["Variável", "Distribuição", "Mínimo", "Mais provável", "Máximo"]]
    for k, (nome, c) in rot.items():
        d = MC["distribuicoes"][k]
        linhas.append([nome, d["tipo"], n(d["minimo"], c), n(d["moda"], c), n(d["maximo"], c)])
    return linhas


def tabela_sensibilidade():
    sens = [s for s in R["sensibilidade"] if abs(s["Amplitude"] - 0.10) < 1e-9]
    crit = {c["Variável"]: c for c in R["valores_criticos"]}
    imp = {c["Variável"]: c for c in MC["importancia"]}
    linhas = [["Variável", "ΔVPL (−10%)", "ΔVPL (+10%)", "Valor crítico (VPL = 0)", "Spearman (MC)"]]
    for s in sens:
        v = s["Variável"]
        c = crit.get(v)
        vc = "—" if not c or c["Valor crítico (VPL = 0)"] is None else f"{n(c['Valor crítico (VPL = 0)'], 3)} ({'+' if c['Folga relativa'] >= 0 else '−'}{n(abs(c['Folga relativa']) * 100, 1)}%)"
        sp = "—" if v not in imp else n(imp[v]["Spearman com VPL"], 3)
        linhas.append([var(v), rs(s["Δ VPL (−)"]), rs(s["Δ VPL (+)"]), vc, sp])
    return linhas


def tabela_topsis():
    linhas = [["Alternativa", "VPL", "P(VPL>0)", "PH cinza (m³/t)", "kgCO2e/kg", "RVL (%)", "Índice", "TOPSIS", "Posição"]]
    for t in R["topsis"]:
        linhas.append([t["Alternativa"], rs(t["VPL (R$)"]), pc(t["P(VPL>0)"]), n(t["PH cinza (m³/t)"], 0),
                       n(t["Intensidade carbono (kgCO2e/kg)"]), n(t["RVL (%)"], 1), n(t["Índice EVTEAS"], 3),
                       n(t["TOPSIS"], 3), f"{t['Ranking']}º"])
    return linhas


def tabela_regressao():
    le, lm = LEG["economico"], LEG["mc"]
    return [
        ["Resultado do preset legado", "Rev. 186 (notebook master)", "Rev. 187 (EVTEAS-Py 2.0)"],
        ["Produção anual (kg)", "15.456", n(LEG["tecnico"]["producao_kg_ano"], 0)],
        ["OEE", "0,828", n(LEG["tecnico"]["oee"], 3)],
        ["VPL determinístico", "−R$ 6,206 milhões", f"−R$ {n(-le['vpl'] / 1e6, 3)} milhões"],
        ["Média do VPL no Monte Carlo", "−R$ 6,022 milhões", f"−R$ {n(-lm['media_vpl'] / 1e6, 3)} milhões"],
        ["Relação média MC × determinístico", "média acima do determinístico", "média abaixo do determinístico"],
        ["TIR", "−0,95 (limite da bisseção)", f"indefinida ({le['diagnostico_tir']})"],
        ["Ecoeficiência", "0 (numerador zerado)", "definida (valor adicionado > 0)"],
        ["Pegada hídrica cinza (m³/t)", "100.000", n(LEG["ambiental"]["ph_cinza_m3_t"], 0)],
        ["Classificação", "REQUER AJUSTES / NÃO VIÁVEL", LEG["decisao"]["classificacao"]],
    ]


def quadro_modulos():
    return [
        ["Módulo", "Responsabilidade", "Vínculo com a dissertação"],
        ["config", "Premissas, distribuições e registro de fontes", "Seções 2.8.6 e 3.6"],
        ["financeiro", "VPL, TIR com diagnóstico e payback (vetorizados)", "Seção 2.8.6; Assaf Neto (2014)"],
        ["modelo", "Dimensões técnica, econômica, ambiental, social e Lean-Green", "Seção 2.8.6; Quadro 5"],
        ["ponderacao", "Normalização, pesos (preset, Likert, AHP), índice, decisão e TOPSIS", "Seção 3.4; Quadro 7"],
        ["incerteza", "Monte Carlo, sensibilidade, valores críticos e cenários", "Seção 3.6"],
        ["pipeline", "Execução integrada e comparação de alternativas", "Etapas 6 e 7 da DSR"],
        ["vv", "Invariantes e testes de regressão", "Seção 3.3.2 (Boehm, 1984)"],
        ["casos", "Caso-base, alternativas e preset legado", "Etapa 8 da DSR"],
        ["relatorios", "Resumo executivo, Excel, JSON, Markdown e figuras", "Etapa 12 da DSR"],
        ["interface", "Menu inicial, wizard completo de entradas, arquivos JSON e análise de preços", "Seção 2.8.3 (PMBOK)"],
        ["dsr", "Etapas da DSR, comparação com artefatos, requisitos, rastreabilidade e aprendizagens", "Seção 3.3.1 (Etapas 4, 5, 8 e 9)"],
    ]


# ---------------------------------------------------------------------------
# Quadros do ciclo DSR (gerados a partir de evteas_py.dsr)
# ---------------------------------------------------------------------------

ONDE_ETAPA = {1: "Seção 1.3", 2: "Seções 1.2 e 2.8 a 2.10", 3: "Seções 2.1 a 2.7", 4: "⟦Seção:dsr_requisitos⟧",
              5: "⟦Seção:dsr_requisitos⟧", 6: "Seções ⟦n:design⟧ a ⟦n:sensibilidade⟧",
              7: "Seções ⟦n:design⟧ a ⟦n:sensibilidade⟧; Apêndice A", 8: "⟦Seção:vv⟧; Apêndice B",
              9: "⟦Seção:aprendizagens⟧", 10: "Seções ⟦n:sintese⟧ a ⟦n:limitacoes⟧", 11: "⟦Seção:generalizacao⟧",
              12: "⟦Seção:comunicacao⟧"}


def _codigo(ev):
    return "." in ev and not ev.startswith(("Seção", "Seções", "Apêndice", "Capítulo"))


def quadro_etapas_dsr():
    linhas = [["Etapa", "Produto nesta pesquisa", "Onde verificar", "Situação"]]
    for e in dsr.ETAPAS_DSR:
        modulos = list(dict.fromkeys(ev.split(".")[0] for ev in e.evidencias if _codigo(ev)))
        cod = ([f"módulo{'s' if len(modulos) > 1 else ''} " + (", ".join(modulos[:-1]) + " e " + modulos[-1] if len(modulos) > 1 else modulos[0])]
               if modulos else [])
        linhas.append([f"{e.numero}. {e.nome}", e.produto, "; ".join([ONDE_ETAPA[e.numero]] + cod), e.situacao])
    return linhas


ABREV = {dsr.SIM: "sim", dsr.NAO: "não", dsr.NI: "n.i."}


def quadro_comparacao():
    cab = ["Propriedade", "Costa Magalhães (2022)", "pyteea (Maier; Weyand, 2025)", "AQUA+ (Ramos et al., 2024)",
           "AquaSpace (Gimpel et al., 2018)", "EVTEAS-Py"]
    return [cab] + [[p] + [ABREV[x] for x in v] for p, v in dsr.COMPARACAO_ARTEFATOS.items()]


def quadro_requisitos():
    return [["Requisito", "Descrição", "Origem"]] + [[r.codigo, r.descricao, r.origem] for r in dsr.REQUISITOS]


def quadro_rastreabilidade():
    m = dsr.matriz_rastreabilidade(RAIZ / "tests")
    return [["Requisito", "Funções que o implementam", "Testes", "Situação"]] + \
        [[x["Requisito"], x["Funções"], str(x["Testes"]), x["Situação"]] for _, x in m.iterrows()]


def quadro_aprendizagens():
    return [["Nº", "Dificuldade observada", "Causa identificada", "Decisão de projeto"]] + \
        [[str(a.numero), a.dificuldade, a.causa, a.decisao] for a in dsr.APRENDIZAGENS]


def quadro_normalizacao():
    rot = {"oee": "OEE", "fcr": "FCR", "produtividade": "Produtividade relativa", "vpl": "VPL/investimento",
           "roi": "ROI anual", "margem_seguranca": "Margem de segurança", "ph_azul": "PH azul (m³/t)",
           "ph_cinza": "PH cinza (m³/t)", "ecoeficiencia": "Ecoeficiência (R$/kgCO2e)",
           "intensidade_carbono": "Intensidade de carbono", "conformidade": "Conformidade (0–10)",
           "lso": "LSO (0–100)", "rvl": "RVL (%)", "radar_social": "Radar Social"}
    dim = {k: d for d, ks in config.KPIS_POR_DIMENSAO.items() for k in ks}
    nomes_dim = {"tecnico": "Técnica", "economico": "Econômica", "ambiental": "Ambiental", "social": "Social"}
    linhas = [["Dimensão", "KPI", "Sentido", "Faixa de referência", "Valor bruto", "Normalizado"]]
    for k, (sent, lo, hi, _) in ponderacao.REFERENCIAS_NORMALIZACAO.items():
        c = 3 if abs(I["kpis_brutos"][k]) < 10 else 0
        linhas.append([nomes_dim[dim[k]], rot[k], "benefício" if sent > 0 else "custo", f"{n(lo, 2)} a {n(hi, 2)}",
                       n(I["kpis_brutos"][k], c), n(I["kpis_normalizados"][k], 3)])
    return linhas


# ---------------------------------------------------------------------------
# Blocos do documento
# ---------------------------------------------------------------------------

def H1(t): return {"k": "h1", "t": t}
def H2(t, chave=None): return {"k": "h2", "t": t, "chave": chave}
def P(t): return {"k": "p", "t": t}
def B(t): return {"k": "bullet", "t": "• " + t}
def _cap(rotulo, chave, titulo): return {"k": "cap", "rotulo": rotulo, "chave": chave, "titulo": titulo}
def COD(chave, titulo, codigo): return [_cap("Código", chave, titulo), {"k": "code", "t": codigo}, {"k": "fonte", "t": FONTE_COD}]
def FIG(chave, titulo, arquivo, fonte=FONTE_RES): return [_cap("Figura", chave, titulo), {"k": "img", "arquivo": arquivo}, {"k": "fonte", "t": fonte}]
def TAB(rotulo, chave, titulo, linhas, larguras=None, fonte=FONTE_RES): return [_cap(rotulo, chave, titulo), {"k": "tbl", "linhas": linhas, "larguras": larguras}, {"k": "fonte", "t": fonte}]


# Numeração automática: o Capítulo 3 termina no Quadro 9, na Figura 10 e na Tabela 2.
INICIO_NUMERACAO = {"Quadro": 10, "Figura": 11, "Tabela": 3, "Código": 1}
REFERENCIA = re.compile(r"⟦(\w+):(\w+)⟧")


def numerar(b):
    """Numera seções, quadros, figuras, tabelas e códigos na ordem em que aparecem e
    resolve as referências cruzadas ⟦Rótulo:chave⟧ (Seção, n = só o número da seção)."""
    cont, mapa, capitulo, secao = dict(INICIO_NUMERACAO), {}, None, 0
    for x in b:
        if x["k"] == "h1":
            capitulo, secao = x["t"].split()[0], 0
        elif x["k"] == "h2":
            secao += 1
            x["t"] = f"{capitulo}.{secao} {x['t']}"
            if x.get("chave"):
                mapa[("Seção", x["chave"])] = f"Seção {capitulo}.{secao}"
                mapa[("n", x["chave"])] = f"{capitulo}.{secao}"
        elif x["k"] == "cap":
            x["num"] = cont[x["rotulo"]]
            cont[x["rotulo"]] += 1
            x["t"] = f"{x['rotulo']} {x['num']} - {x['titulo']}"
            mapa[(x["rotulo"], x["chave"])] = f"{x['rotulo']} {x['num']}"

    def resolver(m):
        if (m.group(1), m.group(2)) not in mapa:
            raise KeyError(f"referência cruzada inexistente: {m.group(0)}")
        return mapa[(m.group(1), m.group(2))]

    for x in b:
        if "t" in x:
            x["t"] = REFERENCIA.sub(resolver, x["t"])
        if x["k"] == "tbl":
            x["linhas"] = [[REFERENCIA.sub(resolver, str(c)) for c in linha] for linha in x["linhas"]]
    return b, mapa


def referencias():
    return numerar(_blocos())[1]


def fig(nome):
    return str(RAIZ / "saidas" / "figuras" / f"{nome}.png")


def blocos():
    return numerar(_blocos())[0]


def _blocos():
    b = []
    b += [H1("4 RESULTADOS E DISCUSSÃO"),
          P("O Capítulo 4 apresenta os resultados da construção e da execução computacional do EVTEAS-Py, tomando como evidência central o código efetivamente implementado e uma execução reproduzível do caso-base incorporado ao próprio artefato. A apresentação segue a lógica Input → Processamento → Output → Verificação → Interpretação, aproximando a descrição do framework do percurso metodológico definido no Capítulo 3. O caso-base não é tratado como validação empírica de um empreendimento real; trata-se de uma configuração ilustrativa, registrada com a origem de cada premissa, utilizada para verificar a coerência funcional do pipeline, demonstrar a propagação das entradas e produzir uma primeira leitura dos indicadores."),
          P("Nesta revisão, o notebook da versão anterior foi reestruturado como o pacote Python evteas_py 2.0, acompanhado do notebook autocontido EVTEAS_Py_Rev187, de uma suíte de testes automatizados e de um script de execução do estudo. O estudo começa obrigatoriamente pela entrada de dados: nenhum resultado é calculado antes que as premissas do projeto sejam informadas. As premissas do caso-base foram registradas no arquivo de entradas entradas_caso_base_rev187.json, carregado pela mesma interface utilizada para qualquer projeto, e a análise foi executada pela função executar_evteas(), com Monte Carlo habilitado, 10.000 iterações e seed 20260612. O caso-base representa um Projeto de Geração de Trabalho e Renda (PGTR) de tilapicultura em viveiros escavados, conduzido por cooperativa de pescadores artesanais, com 4 ha de lâmina d'água. Dessa forma, os números apresentados adiante constituem resultados computacionais reproduzíveis do próprio artefato, não observações de campo. Essa distinção preserva a coerência entre o que efetivamente foi executado e o que ainda depende de validação externa."),
          P("O preset utilizado na Rev. 186 foi mantido no pacote como caso de regressão. Na revisão anterior, ele produzia custos fixos de R$ 87.000 mensais para uma receita mensal da ordem de R$ 12.000, o que tornava o diagnóstico de inviabilidade trivial e pouco informativo. A comparação entre as duas versões é apresentada na ⟦Seção:vv⟧ como evidência de verificação.")]

    b += [P("A organização do capítulo acompanha o ciclo da Design Science Research definido na Seção 3.3.1 (Dresch; Lacerda; Antunes Jr., 2015). A ⟦Seção:dsr⟧ sintetiza o percurso das doze etapas; a ⟦Seção:dsr_requisitos⟧ registra a identificação de artefatos preexistentes, a classe de problemas e os requisitos do artefato (Etapas 4 e 5); as Seções ⟦n:design⟧ a ⟦n:sensibilidade⟧ apresentam o design, o desenvolvimento e os resultados do EVTEAS-Py (Etapas 6 e 7); a ⟦Seção:vv⟧ trata da avaliação (Etapa 8); e a ⟦Seção:aprendizagens⟧, da explicitação das aprendizagens (Etapa 9). As Etapas 10 a 12 são tratadas no Capítulo 5.")]

    m_dsr = dsr.matriz_rastreabilidade(RAIZ / "tests")
    ined = dsr.combinacao_inedita()
    b += [H2("Percurso da Design Science Research na construção do EVTEAS-Py", "dsr"),
          P("A construção do EVTEAS-Py seguiu as doze etapas da Design Science Research adotadas no Capítulo 3. Para que o percurso fosse verificável, e não apenas declarado, cada etapa foi registrada no próprio artefato, no módulo dsr, com o produto que a etapa gerou, o local em que a evidência pode ser conferida e a situação em que se encontra. O ⟦Quadro:etapas⟧ sintetiza esse registro. As Etapas 1 a 3 correspondem aos Capítulos 1 e 2; as Etapas 4 a 9 são apresentadas neste capítulo; e as Etapas 10 a 12, no Capítulo 5.")]
    b += TAB("Quadro", "etapas", "Etapas da Design Science Research e evidências no EVTEAS-Py", quadro_etapas_dsr(),
             [1800, 3800, 1700, 1200], "Fonte: elaboração própria (2026), com base em Dresch, Lacerda e Antunes Jr. (2015).")
    b += [P("Em relação ao cronograma do Quadro 8, as Etapas 4 a 7 tiveram uma primeira iteração concluída nesta revisão, e a Etapa 8 foi realizada na sua parte de verificação, o que antecipa parte da Fase 3. A validação com os dois especialistas, prevista na Seção 3.3.2, permanece pendente e dará início à segunda iteração do ciclo: as observações dos especialistas retornarão às Etapas 6 e 7 como anomalias e sugestões de melhoria, e o artefato será novamente verificado e avaliado. A DSR é, portanto, aplicada de forma iterativa, e os resultados deste capítulo correspondem à primeira volta do ciclo.")]

    b += [H2("Artefatos preexistentes, classe de problemas e requisitos (Etapas 4 e 5)", "dsr_requisitos"),
          P("A Etapa 4 enquadra o problema na classe “modelagem de suporte à decisão multicritério sob incerteza em agroindústrias” e confronta o EVTEAS-Py com os artefatos identificados na Seção 2.8.1. Seguindo Wazlawick (2009), a comparação foi organizada como tabela de propriedades (⟦Quadro:comparacao⟧). Para não atribuir aos outros artefatos limitações que as fontes não afirmam, cada célula registra apenas o que a Seção 2.8.1 descreve: “sim” quando a propriedade é descrita, “não” quando a fonte indica que ela está fora do escopo do artefato e “n.i.” quando a fonte consultada não a menciona. A comparação é, portanto, conservadora: “não identificado” não equivale a ausência da propriedade.")]
    b += TAB("Quadro", "comparacao", "Propriedades do EVTEAS-Py e de artefatos preexistentes", quadro_comparacao(),
             [2600, 1180, 1180, 1180, 1180, 1180], "Fonte: elaboração própria (2026), com base na Seção 2.8.1 e em Wazlawick (2009). n.i.: não identificado na fonte consultada.")
    b += [P(f"Nenhum dos artefatos comparados reúne mais de {max(ined['cobertura_dos_demais'].values())} das {len(ined['propriedades'])} propriedades do EVTEAS-Py, e {len(ined['exclusivas'])} delas não foram identificadas em nenhum outro: {', '.join(p.lower() for p in ined['exclusivas'][:-1])} e {ined['exclusivas'][-1].lower()}. Pelo critério de Wazlawick (2009), a contribuição do EVTEAS-Py está na combinação inédita dessas propriedades em um único artefato, e não em cada propriedade isoladamente. Há ferramentas que calculam a viabilidade econômica em Python (Costa Magalhães, 2022), que integram métricas técnico-econômicas e ambientais (Maier; Weyand, 2025), que atendem ao produtor aquícola (Ramos et al., 2024) ou que articulam indicadores econômicos, ambientais e socioculturais (Gimpel et al., 2018), mas nenhuma das descritas reúne essas dimensões com tratamento da incerteza e regra de decisão no nível do empreendimento aquícola."),
          P(f"Na Etapa 5, a proposição do artefato foi desdobrada em {len(dsr.REQUISITOS)} requisitos, derivados dos objetivos da pesquisa, da Seção 2.8 e dos procedimentos do Capítulo 3 (⟦Quadro:requisitos⟧). Os requisitos R02 e R03 também incorporam o retorno do uso das versões anteriores do notebook: o estudo deve começar pela entrada de dados, e um estudo salvo deve poder ser reaberto e revisto. Cada requisito foi registrado no módulo dsr com as funções que o implementam e os testes que o verificam, o que permite conferir a rastreabilidade a cada versão do código (⟦Seção:vv⟧).")]
    b += TAB("Quadro", "requisitos", "Requisitos do EVTEAS-Py e sua origem", quadro_requisitos(), [1100, 5400, 2000],
             "Fonte: elaboração própria (2026).")

    b += [H2("Design e desenvolvimento do artefato EVTEAS-Py (Etapas 6 e 7)", "design"),
          P("O EVTEAS-Py foi estruturado como um framework modular em Python. A decisão central foi concentrar as premissas em estruturas de configuração e fazer com que um único objeto EVTEASConfig atravesse o pipeline. A configuração (⟦Código:config⟧) agrega os blocos técnico, econômico, ambiental, social, de governança, de pesos, de decisão e de Monte Carlo, além de um registro de fontes que associa cada premissa à sua origem. Essa organização permite separar a camada de aquisição de dados das rotinas analíticas e facilita a reprodução do estudo com um novo conjunto de premissas."),
          P("O código foi distribuído em onze módulos, cada um vinculado a uma seção da dissertação, como sintetiza o ⟦Quadro:modulos⟧. A ⟦Figura:arquitetura⟧ apresenta o fluxo entre as camadas.")]
    b += TAB("Quadro", "modulos", "Módulos do pacote evteas_py e vínculo com a dissertação", quadro_modulos(), [1500, 4300, 2700], "Fonte: elaboração própria (2026).")
    b += FIG("arquitetura", "Arquitetura do EVTEAS-Py 2.0", fig("00_arquitetura"), "Fonte: elaboração própria (2026).")
    b += COD("config", "Estrutura de configuração do EVTEAS-Py", COD_CONFIG)
    b += [P("A principal decisão arquitetural desta revisão foi a vetorização do núcleo de cálculo. A classe Contexto devolve qualquer parâmetro numérico como um vetor de tamanho n: com n = 1 o modelo é determinístico; com n = 10.000 ele é a própria simulação de Monte Carlo. Na Rev. 186, a simulação estocástica utilizava um modelo anual simplificado, distinto do modelo mensal determinístico, o que fazia as duas camadas divergirem. Com o motor único (⟦Código:motor⟧), a mesma fórmula produz o resultado pontual e a distribuição de resultados, e essa equivalência passou a ser verificada por teste automatizado.")]
    b += COD("motor", "Contexto vetorizado e motor único das quatro dimensões", COD_MOTOR)
    b += [P("As rotinas de AHP e TOPSIS, que na Rev. 186 estavam implementadas mas não eram chamadas pelo pipeline, foram integradas. O AHP é uma das três formas de obter os pesos dimensionais (ao lado do preset e da escala Likert do Quadro 7), com cálculo da razão de consistência (Saaty, 1980); o TOPSIS ordena alternativas de projeto pela proximidade relativa à solução ideal (Hwang; Yoon, 1981) e é utilizado na ⟦Seção:sensibilidade⟧.")]

    b += [H2("Interface de entrada e parametrização do estudo", "interface"),
          P("A entrada de dados é a primeira etapa de execução do EVTEAS-Py, coerente com a lógica dos grupos de processos de iniciação e planejamento do PMBOK (PMI, 2021): o artefato obriga o usuário a percorrer todas as etapas de levantamento de requisitos técnicos, econômicos, ambientais e sociais antes de produzir qualquer indicador. A função iniciar_entradas() (⟦Código:wizard⟧) apresenta um menu com três modos. No modo “novo projeto”, todas as premissas precisam ser digitadas; somente coeficientes técnicos com referência normativa ou bibliográfica, como os limites de nitrogênio e fósforo da Resolução CONAMA nº 357/2005 ou o teor de nitrogênio retido no peixe, aparecem como sugestão explícita, aceita com Enter e registrada como tal. No modo “carregar arquivo”, um estudo salvo é reaberto e cada valor pode ser revisto; no modo “exemplo”, o caso ilustrativo da dissertação é carregado com o aviso de que os resultados não representam o projeto do usuário."),
          P("Para garantir que nenhum valor seja herdado silenciosamente, o modo “novo projeto” parte de uma configuração em branco, na qual todos os parâmetros numéricos estão indefinidos; ao final, a função entradas_pendentes() confere se algum permaneceu sem resposta e, nesse caso, interrompe o estudo indicando o parâmetro. O wizard está organizado em dezesseis blocos: identificação; infraestrutura; parâmetros biológicos e insumos; investimento; mix de produtos e receitas; custos operacionais; cooperados e funcionários CLT; tributos; rampa, projeção e TMA; água e efluentes; energia, emissões e resíduos; conformidade ambiental; dimensão social; governança; pesos e regras de decisão; e incerteza. Esse percurso preserva os campos das versões anteriores do estudo de viabilidade econômica, como tipo de organização, quantidades e preços de cada produto do mix, receita de transporte, carência, retiradas dos cooperados, mínimo legal de cooperados, salário de cada cargo CLT, distribuição de sobras e cada tributo com sua base de cálculo, e acrescenta os parâmetros técnico-ambientais-sociais."),
          P("As respostas são validadas quanto a tipo e limites e aceitam números no padrão brasileiro, como 40.000 ou 1.500,50; quando o ponto é lido como separador de milhar, o wizard mostra o valor interpretado. O usuário pode digitar “sair” a qualquer momento, e as respostas já dadas são salvas num arquivo de rascunho que pode ser reaberto para continuar de onde parou. Ao reabrir um arquivo de entradas, inclusive de versões anteriores, o artefato não completa o que falta com os valores do caso ilustrativo: os campos ausentes são listados e pedidos na revisão, e as distribuições do Monte Carlo são reposicionadas quando o valor determinístico do arquivo mudou. A incerteza só pode ser atribuída às variáveis que o motor de cálculo amostra, o que evita distribuições cadastradas sem efeito no resultado. Ao final de cada bloco, o wizard pergunta a origem dos dados informados (histórico, dado secundário, cotação, valor normativo, parâmetro bibliográfico, empreendimento análogo, especialista ou estimativa do autor), o que operacionaliza a rastreabilidade da Seção 3.6. Em seguida, apresenta um resumo das entradas, permite corrigir qualquer bloco e salva o arquivo entradas_<projeto>.json, que pode ser reaberto para revisão e versionado junto com os resultados. A análise de preços a partir de planilha, herdada das versões anteriores, foi mantida em forma enxuta: com uma coluna de preços, o artefato sugere preços por estratégia (percentis 25, 50 e 75); com preços e quantidades, estima uma curva de demanda linear e o preço que maximiza a margem de contribuição.")]
    b += COD("wizard", "Início do estudo pela entrada de dados", COD_WIZARD)
    b += [P("A rastreabilidade prevista na Seção 3.6 foi operacionalizada pela tabela de premissas, exportada junto com os resultados: cada parâmetro numérico aparece com seu valor, a categoria da fonte (dado histórico, dado secundário, cotação, valor normativo, parâmetro bibliográfico, empreendimento análogo, especialista ou estimativa do autor), a referência e, quando houver, a distribuição de probabilidade com mínimo, valor mais provável e máximo. O ⟦Quadro:premissas⟧ resume as principais premissas do caso-base."),
          ]
    b += TAB("Quadro", "premissas", "Principais premissas do caso-base e origem declarada", tabela_premissas(), [1300, 2700, 2500, 2000], "Fonte: elaboração própria (2026).")
    b += [P("A parametrização tributária aceita alíquotas individuais (ICMS, PIS, COFINS, IRPJ, CSLL e contribuições sobre a folha ou sobre os cooperados) associadas a uma base de cálculo (faturamento, lucro ou folha), que o modelo consolida antes do cálculo econômico. No caso-base, adotou-se 2,3% sobre o faturamento e alíquota nula sobre o resultado, coerente com o tratamento do ato cooperativo. Isso é diferente de afirmar que o framework reproduz integralmente a complexidade jurídico-contábil de todos os regimes tributários.")]

    b += [H2("Resultados da dimensão técnica", "tecnica"),
          P("A função calcular_tecnico() operacionaliza a dimensão técnica a partir dos três blocos de entrada descritos na Seção 2.8.6: infraestrutura, parâmetros biológicos e eficiência de insumos. Nesta revisão, a estocagem passou a ser tratada como decisão de projeto: o número de alevinos por ciclo é dimensionado para atingir a biomassa-alvo com a mortalidade esperada, enquanto a mortalidade e o desempenho de crescimento efetivos são incertos. Assim, quando a mortalidade simulada é maior, a biomassa despescada diminui, o que não ocorria na versão anterior."),
          P("Uma particularidade importante é o mecanismo de restrição dupla da biomassa (⟦Código:tecnico⟧). A biomassa-alvo é o menor valor entre o limite dado pela capacidade de suporte (volume útil × kg/m³) e o limite dado pela produtividade esperada por área. O OEE aquícola resulta do produto de disponibilidade (viveiros ativos/total), performance (crescimento realizado/esperado) e qualidade. Em alinhamento ao Quadro 5, a qualidade passou a ser a taxa de sobrevivência, e não um parâmetro independente, como ocorria na Rev. 186.")]
    b += COD("tecnico", "Cálculo da dimensão técnica e OEE (trecho)", COD_TECNICO)
    b += [P(f"No caso-base, com {n(40000, 0)} m² de lâmina, 1,4 m de profundidade média, 32 viveiros (30 ativos), produtividade esperada de 1,3 kg/m² por ciclo, peso de abate de 800 g, ciclo de 180 dias, 1,8 ciclo por ano, FCR de 1,50 e mortalidade de 10%, a restrição ativa foi a produtividade por área. O modelo dimensionou {n(T['alevinos_ciclo'], 0)} juvenis por ciclo (densidade de {n(T['densidade_estocagem_peixes_m3'], 2)} peixes/m³), com despesca de {n(T['biomassa_despesca_ciclo_kg'], 0)} kg por ciclo e produção de {n(T['producao_kg_ano'], 0)} kg/ano ({n(T['produtividade_kg_m2_ano'], 2)} kg/m²/ano, {pc(T['produtividade_relativa'])} do potencial do sistema). O OEE foi {n(T['oee'], 3)}, resultado de disponibilidade {n(T['disponibilidade'], 4)}, performance {n(T['performance'], 2)} e sobrevivência {n(T['sobrevivencia'], 2)}. O consumo de ração foi {n(T['racao_ano_kg'], 0)} kg/ano."),
          P("A curva de crescimento (⟦Figura:curva⟧) é obtida por taxa de crescimento específico constante, com mortalidade distribuída ao longo do ciclo e arraçoamento calibrado para reproduzir o FCR. A curva subsidia o planejamento logístico do estoque de ração, em linha com a lógica Lean de redução de desperdícios.")]
    b += FIG("curva", "Curva de crescimento, biomassa e ração acumulada no ciclo do caso-base", fig("01_curva_crescimento"))
    b += [P(f"O módulo Lean-Green quantifica, em reais por ano, os desperdícios evitáveis em relação a referências declaradas (FCR de 1,40, mortalidade de 5% e 0,40 kWh/kg). No caso-base, a ração excedente custa {rs(LG['desperdicios_r_ano']['Ração excedente (superalimentação/FCR)'])} por ano, a mortalidade evitável {rs(LG['desperdicios_r_ano']['Mortalidade evitável'])} e a energia excedente {rs(LG['desperdicios_r_ano']['Energia excedente'])}, totalizando {rs(LG['total_r_ano'])}, ou {pc(LG['pct_opex'])} do custo operacional. Esse resultado traduz em valor monetário a identificação sistemática de desperdícios defendida por Lawrence et al. (2023).")]

    b += [H2("Resultados da dimensão econômica", "economica"),
          P("A função calcular_economico() (⟦Código:economico⟧) transforma a produção técnica em uma projeção mensal. Três refinamentos foram introduzidos em relação à Rev. 186. Primeiro, a receita só ocorre após a primeira despesca (6 meses no caso-base), enquanto ração, alevinos e energia são desembolsados durante a engorda; ao final do horizonte, o estoque em engorda é recuperado pelo seu custo, junto com o valor residual e o capital de giro. Segundo, a depreciação passou a compor a base dos tributos sobre o resultado e é somada de volta no fluxo de caixa operacional. Terceiro, foi incluída a perspectiva do beneficiário, na qual parte do CAPEX é aportada por fomento não reembolsável, situação típica de projetos financiados por condicionantes do licenciamento ambiental federal (IBAMA, 2010, 2012).")]
    b += COD("economico", "Projeção econômica mensal, DRE e indicadores financeiros (trecho)", COD_ECONOMICO)
    b += [P("A DRE mensal produz Receita Bruta, Impostos sobre Faturamento, Receita Líquida, Custos Variáveis, Lucro Bruto, Custos Fixos, EBITDA, Depreciação, LAIR, Impostos sobre Lucro e Resultado Líquido. O vetor de fluxo de caixa é então utilizado para calcular VPL, TIR, payback simples e descontado, índice de lucratividade, ponto de equilíbrio, margem de segurança e ROI. A TIR é obtida por varredura de malha seguida de bisseção vetorizada e retorna sempre um diagnóstico (convencional, múltiplas, múltiplas possíveis ou sem solução), de modo que a ausência de raiz nunca é confundida com o limite numérico do algoritmo (⟦Código:tir⟧). A ⟦Tabela:economica⟧ apresenta os resultados.")]
    b += TAB("Tabela", "economica", "Indicadores econômicos do caso-base", tabela_economica(), [4300, 2100, 2100])
    b += [P(f"Na perspectiva do projeto, com investimento total de {rs(E['investimento_total'])}, o VPL foi {rs(E['vpl'])} e a TIR {pc(E['tir_anual'])} a.a., ligeiramente acima da TMA de 10% a.a. O empreendimento é, portanto, marginalmente viável no cenário determinístico. Dois sinais indicam fragilidade: o payback descontado de {n(E['payback_descontado_meses'], 1)} meses ocorre praticamente no último mês do horizonte, graças ao valor terminal, e o índice de lucratividade é de apenas {n(E['indice_lucratividade'], 3)}. Em regime, a margem de segurança de {pc(E['margem_seguranca'])} significa que as vendas podem cair até esse percentual antes de o resultado operacional se anular."),
          P(f"Na perspectiva da cooperativa, com {n(70, 0)}% do CAPEX aportado como fomento, o VPL sobe para {rs(E['vpl_beneficiario'])} e a TIR para {pc(E['tir_anual_beneficiario'])} a.a., com payback descontado de {n(E['payback_descontado_beneficiario_meses'], 1)} meses. As sobras de {rs(E['lucro_liquido_regime'])} no ano de regime, somadas às retiradas, proporcionam renda média de {rs(S['renda_mensal_trabalhador'])} mensais a cada um dos seis cooperados. A distinção entre as perspectivas é relevante para o órgão fomentador: o recurso não reembolsável não torna o projeto economicamente eficiente, mas pode viabilizar a geração de renda para o público beneficiário."),
          P(f"O custo total de produção foi R$ {n(E['custo_total_kg'])}/kg, dos quais a ração representa {pc(E['custo_racao_regime'] / (E['custos_variaveis_regime'] + E['custos_fixos_regime']))} dos custos operacionais. O resultado evidencia que o diagnóstico de viabilidade depende não apenas da produção, mas da relação entre capacidade, preço, custos e investimento. A ⟦Figura:economica⟧ apresenta a evolução da receita, dos custos e do fluxo de caixa acumulado.")]
    b += FIG("economica", "Receita, custos operacionais e fluxo de caixa acumulado do caso-base", fig("02_projecao_economica"))

    b += [H2("Resultados da dimensão ambiental", "ambiental"),
          P("A função calcular_ambiental() utiliza a produção e o consumo de ração para estimar água, nutrientes, energia, emissões e resíduos. A pegada hídrica azul passou a seguir a definição de Hoekstra (2017): água consumida, isto é, evaporada ou devolvida a outra bacia, e não toda a água captada. A água captada (enchimento, renovação e reposição de perdas) alimenta o Índice de Uso de Água previsto na Seção 2.8.6."),
          P("A pegada hídrica cinza foi reformulada a partir de um balanço de nutrientes (⟦Código:ambiental⟧). O nitrogênio e o fósforo aportados pela ração, descontados os retidos na biomassa e os removidos pelo tratamento de efluentes, constituem a carga lançada; o volume de diluição é calculado pela diferença entre a concentração máxima da classe do corpo receptor (Brasil, 2005) e a concentração natural, e o poluente que exige maior volume define a pegada. Na Rev. 187, a ecoeficiência foi redefinida, segundo o WBCSD (2000), como valor adicionado (receita menos insumos externos) por unidade de impacto. Quando o valor adicionado não é positivo, o indicador é declarado não definido, distinguindo essa situação de uma ecoeficiência igual a zero, como recomendado na revisão anterior.")]
    b += COD("ambiental", "Balanço de nutrientes, pegada hídrica cinza e ecoeficiência (trecho)", COD_AMBIENTAL)
    b += [P(f"No caso-base, a água captada foi de {n(A['agua_captada_m3_ano'], 0)} m³/ano, dominada pela renovação diária, com Índice de Uso de Água de {n(A['indice_uso_agua_kg_m3'], 3)} kg/m³. A pegada hídrica azul foi {n(A['ph_azul_m3_t'], 0)} m³/t, correspondente à evaporação. A pegada hídrica cinza foi {n(A['ph_cinza_m3_t'], 0)} m³/t, tendo o fósforo total como poluente crítico: dos {n(A['p_aportado_kg'], 0)} kg de P aportados, {n(A['p_retido_kg'], 0)} kg ficam na biomassa e {n(A['p_lancado_kg'], 0)} kg são lançados após remoção de 60% no tratamento. O resultado é muito sensível à classe do corpo receptor e à eficiência de remoção de fósforo, o que reforça a lógica Lean Green de tratar o efluente como ineficiência de processo."),
          P(f"As emissões estimadas foram {n(A['co2e_total_t_ano'], 1)} tCO2e/ano, ou {n(A['intensidade_carbono_kgco2e_kg'])} kgCO2e por kg de peixe, das quais {pc(A['co2e_racao_t'] / A['co2e_total_t_ano'])} decorrem da ração, o que desloca a prioridade de mitigação para o FCR e não para a matriz elétrica. A ecoeficiência foi R$ {n(A['ecoeficiencia_r_por_kgco2e'])} de valor adicionado por kgCO2e. O Score de Conformidade Ambiental, calculado sobre um checklist normativo ponderado (licença ambiental da aquicultura, outorga, APP, tratamento de efluentes, monitoramento, CAR, gestão de resíduos, prevenção de escape e energia renovável), foi {n(A['conformidade_0_10'], 2)} de 10. Os itens não atendidos foram o plano de gestão de resíduos e o uso de energia renovável; nenhum item eliminatório foi violado. A ⟦Tabela:ambiental_social⟧ reúne esses indicadores e os das dimensões social e de governança, discutidos na seção seguinte."),
          ]
    b += TAB("Tabela", "ambiental_social", "Indicadores ambientais, sociais e de governança do caso-base", tabela_ambiental_social(), [1600, 3700, 3200])

    b += [H2("Resultados da dimensão social e ESG", "social"),
          P("O módulo social (⟦Código:social⟧) transforma emprego, renda local, compras locais e relacionamento com stakeholders em indicadores comparáveis. Nesta revisão, a Retenção de Valor Local (RVL) passou a seguir exatamente a fórmula do Quadro 5: despesas com mão de obra e fornecedores locais divididas pelo custo operacional total. A Rev. 186 dividia esse valor pela receita, o que misturava as bases. O Índice de Impacto Local estima a proporção da receita que retorna à economia local como renda (massa salarial local e sobras distribuídas)."),
          P("A Licença Social para Operar (LSO) é um índice de 0 a 100 composto por cinco componentes: relação com a comunidade (inexistente, parcial ou consolidada), existência de canais formais de comunicação, frequência de engajamento, ausência de conflitos e participação da comunidade na governança (Hurst; Ihlen, 2018). O Score de Risco Social converte o déficit de LSO em uma escala de 0 a 1 por função logística; trata-se de heurística explícita, a ser calibrada com os especialistas, e não de probabilidade estimada estatisticamente.")]
    b += COD("social", "Cálculo da dimensão social, RVL e LSO (trecho)", COD_SOCIAL)
    ods = R["ods"]
    atendidos = [o["ODS"].split(" — ")[0] for o in ods if o["Atendido"]]
    nao = [o["ODS"].split(" — ")[0] for o in ods if not o["Atendido"]]
    b += [P(f"No caso-base, com 6 empregos diretos e 10 indiretos, 100% de mão de obra local e 25% de compras locais, a RVL foi {n(S['rvl_pct'], 1)}% e o Índice de Impacto Local {pc(S['indice_impacto_local'])}. A renda média por cooperado correspondeu a {n(S['renda_em_salarios_minimos'])} salários mínimos. A LSO foi {n(S['lso_0_100'], 1)}, reduzida pela relação apenas parcial com a comunidade, pela frequência de engajamento de seis reuniões anuais e por um conflito registrado; o risco social foi {n(S['risco_social'], 3)}. O Radar Social (⟦Figura:radar⟧) obteve média {n(S['radar_social_score'], 3)}, com menores valores nos eixos de relação com a comunidade e inclusão."),
          P(f"O alinhamento aos Objetivos de Desenvolvimento Sustentável é identificado automaticamente por regras explícitas e auditáveis. O caso-base atende a {len(atendidos)} dos {len(ods)} ODS avaliados ({', '.join(atendidos)}); {', '.join(nao)} não é atendido porque a energia provém da rede. O pilar de governança, avaliado por checklist de sete itens (estatuto, assembleias, conselho fiscal, prestação de contas pública, plano de negócios, registro auditável das premissas e canal de denúncia), obteve {n(G['score_0_1'], 3)}. O score ESG, média dos pilares ambiental ({n(I['esg']['E'], 3)}), social ({n(I['esg']['S'], 3)}) e de governança ({n(I['esg']['G'], 3)}), foi {n(I['esg_score'], 3)}.")]
    b += FIG("radar", "Radar Social do caso-base", fig("04_radar_social"))

    b += [H2("Índice integrado EVTEAS", "indice"),
          P("O índice integrado usa uma etapa explícita de normalização para transformar KPIs com escalas e sentidos diferentes em valores de 0 a 1. Cada KPI recebe um sentido (benefício ou custo) e uma faixa de referência declarada, que fica disponível para auditoria e pode ser revisada pelos especialistas. O ⟦Quadro:normalizacao⟧ apresenta as referências, os valores brutos e os valores normalizados do caso-base. Os scores dimensionais são médias ponderadas dos KPIs de cada dimensão, e o índice EVTEAS é a média ponderada das quatro dimensões.")]
    b += TAB("Quadro", "normalizacao", "Normalização dos KPIs do caso-base", quadro_normalizacao(), [1200, 2300, 1100, 1700, 1100, 1100])
    dims = I["dimensoes"]
    b += [P(f"Com os pesos do preset (0,25 técnica, 0,35 econômica, 0,20 ambiental e 0,20 social), os scores dimensionais foram {n(dims['tecnico'], 3)}, {n(dims['economico'], 3)}, {n(dims['ambiental'], 3)} e {n(dims['social'], 3)}, respectivamente, resultando em índice EVTEAS de {n(I['indice_evteas'], 3)} (⟦Figura:dimensoes⟧). Os KPIs de pior desempenho relativo foram a ecoeficiência e a RVL, o que aponta onde concentrar ajustes de projeto."),
          P("A regra de decisão (⟦Código:decisao⟧) foi reformulada em dois estágios para evitar que o índice compensatório oculte fragilidades, limitação apontada na Rev. 186. No primeiro estágio, vetos não compensatórios impedem a classificação “VIÁVEL” quando o VPL do projeto é negativo, quando um item ambiental eliminatório não é atendido ou quando a LSO está abaixo de 40. No segundo, o índice é comparado aos limiares de 0,60 (viável) e 0,50 (viável com ressalvas), e a probabilidade de VPL positivo obtida no Monte Carlo é confrontada com o mínimo de 70%. Essa estrutura responde à crítica da “eficiência obscena” de Garnett, Röös e Little (2015): bom desempenho econômico não compensa violação ambiental ou social.")]
    b += COD("decisao", "Regra de decisão com vetos não compensatórios", COD_DECISAO)
    lkp = LK["pesos"]["likert_dimensoes"]
    b += [P(f"O caso-base foi classificado como “{D['classificacao']}”: não houve vetos e o índice superou 0,60, mas a probabilidade de VPL positivo ({pc(ST['prob_vpl_positivo'])}) ficou abaixo do mínimo. O limiar de 0,60 e a probabilidade mínima de 70% são regras operacionais do artefato e devem ser tratados como parâmetros de decisão, não como padrões universais de mercado ou de engenharia."),
          P(f"Para demonstrar a parametrização prevista na Seção 3.4, o pipeline foi executado com escores Likert ilustrativos de dois avaliadores. Os pesos normalizados resultaram em {n(lkp['pesos']['tecnico'], 3)} (técnica), {n(lkp['pesos']['economico'], 3)} (econômica), {n(lkp['pesos']['ambiental'], 3)} (ambiental) e {n(lkp['pesos']['social'], 3)} (social), com concordância média de {n(lkp['concordancia_media'], 3)} entre os avaliadores, e o índice passou a {n(LK['indice'], 3)}. Os escores efetivos dos especialistas substituirão esses valores na Fase 3 da pesquisa, e a divergência por critério será registrada como evidência da triangulação.")]
    b += FIG("dimensoes", "Scores dimensionais e índice EVTEAS do caso-base", fig("03_dimensoes"))

    b += [H2("Simulação de Monte Carlo", "mc"),
          P("A camada de incerteza (⟦Código:mc⟧) utiliza Monte Carlo sobre o mesmo motor vetorizado do modelo determinístico. As distribuições adotadas são apresentadas no ⟦Quadro:distribuicoes⟧. Seguindo Oliveira e Medeiros Neto (2012), utilizou-se a distribuição triangular quando havia valor mais provável. A incerteza do CAPEX deriva da faixa de exatidão de uma estimativa Classe 5 da AACE International (2020), de −30% a +50%. As amostras são geradas com np.random.default_rng(20260612), em ordem fixa de variáveis, o que garante reprodutibilidade.")]
    b += TAB("Quadro", "distribuicoes", "Distribuições de incerteza do caso-base", tabela_distribuicoes(), [3300, 1300, 1300, 1300, 1300], "Fonte: elaboração própria (2026).")
    b += COD("mc", "Simulação de Monte Carlo sobre o motor único (trecho)", COD_MC)
    b += TAB("Tabela", "mc", "Estatísticas da simulação de Monte Carlo (n = 10.000)", tabela_mc(), [4300, 4200])
    b += [P(f"A ⟦Tabela:mc⟧ e a ⟦Figura:vpl⟧ apresentam os resultados. O mais relevante é o contraste entre a análise determinística e a estocástica. Embora o VPL calculado na moda das premissas seja positivo ({rs(E['vpl'])}), a média do VPL simulado é {rs(ST['media_vpl'])} e a probabilidade de VPL positivo é de apenas {pc(ST['prob_vpl_positivo'])}. A diferença decorre da assimetria das distribuições: mortalidade (5%, 10%, 20%), FCR (1,30; 1,50; 1,85), CAPEX (−30%, +50%) e custos fixos têm caudas mais longas no lado desfavorável, de modo que a média de cada premissa é pior que o seu valor mais provável. Um estudo de viabilidade baseado apenas no cenário mais provável, como os elaborados em planilhas, tende, portanto, a superestimar a viabilidade de projetos com riscos assimétricos."),
          P(f"A convergência foi verificada pela média acumulada e pelo erro-padrão (⟦Figura:convergencia⟧). Com 10.000 iterações, o erro-padrão da média do VPL foi {rs(MC['convergencia'][-1]['Erro-padrão'])}, inferior a 1% do desvio-padrão. Na perspectiva da cooperativa, a probabilidade de VPL positivo sobe para {pc(ST['prob_vpl_beneficiario_positivo'])}, o que confirma que o fomento reduz substancialmente o risco do beneficiário, mas não o elimina.")]
    b += FIG("vpl", "Distribuição e função de probabilidade acumulada do VPL", fig("05_monte_carlo_vpl"))
    b += FIG("convergencia", "Convergência da média do VPL com intervalo de confiança de 95%", fig("06_convergencia_mc"))

    vc = {c["Variável"]: c for c in R["valores_criticos"]}
    imp = MC["importancia"]
    cen = {c["Cenário"]: c for c in R["cenarios"]}
    top = R["topsis"]
    b += [H2("Análise de sensibilidade e identificação das variáveis críticas", "sensibilidade"),
          P("A identificação das variáveis críticas combina quatro procedimentos complementares. A sensibilidade de um fator por vez varia cada premissa em ±10% e ±20%, mantendo as demais no caso-base. Os valores críticos são obtidos por bisseção e indicam o valor de cada variável que anula o VPL. A correlação de postos de Spearman entre as entradas amostradas e o VPL mede a importância de cada variável sob variação simultânea. Por fim, os cenários pessimista e otimista combinam os extremos desfavoráveis e favoráveis das distribuições.")]
    b += COD("tir", "TIR com diagnóstico e valores críticos das premissas", COD_TIR + "\n\n\n" + COD_CRITICOS)
    b += TAB("Tabela", "sensibilidade", "Sensibilidade, valores críticos e importância das variáveis", tabela_sensibilidade(), [2500, 1500, 1500, 1800, 1200])
    b += [P(f"O preço de venda foi o fator de maior impacto (⟦Tabela:sensibilidade⟧ e ⟦Figura:tornado⟧): a variação de ±10% alterou o VPL em {rs(abs(R['sensibilidade'][0]['Δ VPL (+)']))}, e o preço crítico de R$ {n(vc['economico.preco_venda_kg']['Valor crítico (VPL = 0)'])}/kg está apenas {n(abs(vc['economico.preco_venda_kg']['Folga relativa']) * 100, 1)}% abaixo do preço-base. FCR e custo da ração têm o mesmo efeito, pois entram no modelo como produto, e uma piora de {n(vc['tecnico.fcr']['Folga relativa'] * 100, 1)}% em qualquer um deles anula o VPL. A mortalidade, com valor crítico de {n(vc['tecnico.mortalidade_pct']['Valor crítico (VPL = 0)'], 1)}%, tem efeito marginal menor, porque a perda de biomassa é parcialmente compensada pela economia de ração. A ordem de importância no Monte Carlo (Spearman de {n(imp[0]['Spearman com VPL'], 3)} para o preço, {n(imp[1]['Spearman com VPL'], 3)} para o FCR e {n(imp[2]['Spearman com VPL'], 3)} para a ração) confirma a sensibilidade determinística e indica onde concentrar a coleta de dados de mercado e o controle zootécnico."),
          P(f"Os cenários delimitam a faixa de resultados: no pessimista, o VPL é {rs(cen['Pessimista']['VPL'])} e o índice {n(cen['Pessimista']['Índice EVTEAS'], 3)}; no otimista, {rs(cen['Otimista']['VPL'])} e {n(cen['Otimista']['Índice EVTEAS'], 3)}. A amplitude reforça que o caso-base está próximo do limiar de viabilidade e que a decisão depende de ações de mitigação de risco, como contratos de venda que estabilizem o preço e manejo alimentar que reduza o FCR.")]
    b += FIG("tornado", "Diagrama de tornado da sensibilidade do VPL a ±10%", fig("07_tornado"))
    b += [P(f"Para examinar trade-offs entre dimensões, três alternativas de projeto foram comparadas por TOPSIS (⟦Tabela:topsis⟧ e ⟦Figura:topsis⟧), com sete critérios: VPL, probabilidade de VPL positivo, OEE, pegada hídrica cinza, intensidade de carbono, LSO e RVL. A alternativa A é o caso-base. A alternativa B acrescenta energia solar e wetland construído para o tratamento de efluentes. A alternativa C intensifica a produção com maior aeração."),
          ]
    b += TAB("Tabela", "topsis", "Comparação de alternativas de projeto por TOPSIS", tabela_topsis(), [900, 1300, 900, 1000, 900, 800, 800, 900, 900])
    tb = {t["Alternativa"]: t for t in top}
    b += [P(f"A intensificação (C) obteve a maior proximidade à solução ideal ({n(tb['C']['TOPSIS'], 3)}), porque dilui custos fixos e eleva o VPL para {rs(tb['C']['VPL (R$)'])}. A alternativa B reduziu a pegada hídrica cinza à metade ({n(tb['B']['PH cinza (m³/t)'], 0)} m³/t) e aumentou o VPL em relação ao caso-base, pela economia de energia. Nenhuma das alternativas, entretanto, atingiu probabilidade de VPL positivo de 70%; a maior foi a de C, com {pc(tb['C']['P(VPL>0)'])}. O resultado ilustra a função do framework: em vez de declarar uma alternativa ótima, ele explicita o que se ganha e o que se perde em cada dimensão e permite combinar soluções, como intensificar com tratamento de efluentes.")]
    b += FIG("topsis", "Proximidade relativa à solução ideal das alternativas de projeto", fig("08_topsis"))

    vvr = R["vv"]
    b += [H2("Verificação computacional e avaliação do artefato (Etapa 8)", "vv"),
          P(f"A verificação foi conduzida em duas camadas. A função validar_invariantes() (⟦Código:vv⟧) executa {vvr['quantidade_verificacoes']} verificações a cada execução: limites de OEE, índices e scores; identidade OEE = disponibilidade × performance × qualidade; ração = FCR × ganho de biomassa; quatro identidades da DRE; fluxo de caixa operacional = resultado + depreciação; recálculo independente do VPL; VPL nulo na TIR; coerência entre paybacks; balanços de nitrogênio e fósforo; soma unitária dos pesos; coerência do status da ecoeficiência; e consistência estatística do Monte Carlo. No caso-base, todas foram aprovadas."),
          P(f"A segunda camada é uma suíte de {TESTES['testes']} testes automatizados (pytest), executada fora do pipeline. Os testes comparam VPL e TIR com a biblioteca numpy-financial, verificam casos com solução analítica conhecida (inclusive fluxos sem TIR e com duas TIR), conferem o cálculo manual da pegada hídrica cinza, os vetos, a normalização, os pesos Likert e AHP, o TOPSIS, a reprodutibilidade por seed e a exportação. Um teste central verifica que, com distribuições degeneradas na moda, o Monte Carlo reproduz exatamente o resultado determinístico. Outro grupo testa a entrada de dados com um usuário simulado: digitando no wizard, no modo “novo projeto”, as premissas do caso-base, o artefato reproduz exatamente o VPL e a amostra de Monte Carlo da configuração de referência; o modo de revisão, com Enter em todas as perguntas, preserva os resultados; e entradas inválidas são recusadas com mensagem ao usuário. A cobertura de código medida foi de {n(TESTES['cobertura_pct'], 0)}% das instruções, métrica de testabilidade prevista na Seção 3.4.")]
    b += COD("vv", "Verificação por invariantes (trecho)", COD_VV)
    verificados = int((m_dsr["Situação"] == "implementado e verificado").sum())
    b += [P(f"A rastreabilidade entre requisitos, código e testes é conferida pela função matriz_rastreabilidade(), que verifica no código-fonte se cada função vinculada a um requisito existe e, nos arquivos de teste, se cada teste citado está definido (⟦Quadro:rastreabilidade⟧). Na primeira conferência, os requisitos R07 (dimensão social, governança e ODS) e R08 (Lean-Green) apareceram como implementados, mas sem teste dedicado. Foram então escritos testes para a fórmula da RVL, a composição da LSO e do risco social, o checklist de governança, as regras dos ODS e o custo dos desperdícios. Com eles, {verificados} dos {len(m_dsr)} requisitos estão na situação “implementado e verificado”. A própria matriz é verificada por teste, de modo que um requisito cuja função ou teste deixe de existir volta a aparecer como pendente.")]
    b += TAB("Quadro", "rastreabilidade", "Matriz de rastreabilidade entre requisitos, código e testes", quadro_rastreabilidade(),
             [1100, 4600, 800, 2000], "Fonte: elaboração própria (2026), a partir da função matriz_rastreabilidade() do EVTEAS-Py.")
    b += [P(_revisao_independente())]
    b += [P("Como teste de regressão, o preset da Rev. 186 foi reproduzido no novo motor (⟦Tabela:regressao⟧). As diferenças são explicadas pelas correções: a produção é ligeiramente menor porque a qualidade passou a ser a sobrevivência e a estocagem é dimensionada; a média do Monte Carlo passou a ficar abaixo do VPL determinístico, como esperado com distribuições assimétricas desfavoráveis, ao passo que na Rev. 186 ficava acima, sintoma do uso de modelos diferentes nas duas camadas; a TIR deixou de ser reportada como −0,95; e a ecoeficiência deixou de ser zerada, pois o valor adicionado permanece positivo mesmo com prejuízo. A conclusão de inviabilidade foi preservada.")]
    b += TAB("Tabela", "regressao", "Regressão do preset legado: Rev. 186 versus Rev. 187", tabela_regressao(), [3100, 2700, 2700])
    b += [P("É importante manter a distinção entre verificação e validação. A verificação demonstra aderência do código às regras codificadas; a validação busca demonstrar que o artefato é adequado ao problema real. Para a segunda, continuam necessárias a avaliação pelos dois especialistas, cujos escores Likert já têm destino definido no código, e a comparação com dados de empreendimentos reais, conforme delimitado no Capítulo 3.")]

    b += [H2("Explicitação das aprendizagens (Etapa 9)", "aprendizagens"),
          P("A Etapa 9 exige registrar o que a construção ensinou, e não apenas o artefato final. As aprendizagens foram registradas no módulo dsr, cada uma com a dificuldade observada, a causa identificada, a decisão de projeto que dela resultou e o teste que impede que o problema volte a ocorrer (⟦Quadro:aprendizagens⟧).")]
    b += TAB("Quadro", "aprendizagens", "Aprendizagens explicitadas na construção do EVTEAS-Py", quadro_aprendizagens(),
             [500, 2700, 2600, 2700], "Fonte: elaboração própria (2026), a partir do registro de aprendizagens do EVTEAS-Py.")
    b += [P("Três lições têm alcance além do caso. A primeira é que a coerência entre camadas de análise deve ser garantida pela arquitetura, e não pela atenção do desenvolvedor: enquanto o Monte Carlo usou um modelo distinto do determinístico, as duas camadas divergiram sem que nenhum cálculo isolado estivesse errado. A segunda é que um artefato de apoio à decisão não deve ter valores padrão silenciosos: quando o notebook produzia resultados antes das entradas, o caso ilustrativo podia ser tomado pelo projeto do usuário. A terceira é que requisitos explícitos e rastreáveis revelam lacunas que uma execução bem-sucedida esconde: rotinas de AHP e TOPSIS implementadas e não utilizadas, e funções sociais e Lean-Green sem teste, só apareceram quando cada requisito foi ligado ao código e aos testes. Essas lições fundamentam os princípios de projeto formulados na ⟦Seção:generalizacao⟧.")]

    b += [H2("Exportação, reprodutibilidade e documentação dos resultados", "exportacao"),
          P("O framework produz um resumo executivo, um workbook Excel, um arquivo JSON, um relatório em Markdown e nove figuras. O workbook reúne 23 abas, entre elas premissas com origem, curva de crescimento, DRE mensal e anual, fluxo de caixa, indicadores ambientais, checklist de conformidade, indicadores sociais, ODS, desperdícios Lean-Green, KPIs normalizados, amostra e estatísticas do Monte Carlo, convergência, importância das variáveis, sensibilidade, valores críticos, cenários e o registro da verificação. Somado ao arquivo de entradas salvo ao final do wizard, esse material estabelece uma trilha entre premissas, cálculo e resultados auditáveis."),
          P(f"A reprodução depende do registro da versão do pacote, do arquivo de entradas, da seed e do número de iterações. A execução completa do estudo, incluindo o caso-base com 10.000 iterações, as três alternativas com 10.000 iterações cada, o preset legado e o cenário com pesos Likert, levou cerca de {n(R['tempo_execucao_s'], 0)} segundos em ambiente de nuvem. O código, os testes e as saídas estão versionados no repositório do projeto, e o notebook autocontido pode ser executado no Google Colab sem instalação do pacote. O notebook traz ainda uma seção opcional que exibe o registro da DSR (etapas, comparação com artefatos, matriz de rastreabilidade e aprendizagens), o que torna o percurso metodológico consultável junto com os resultados.")]

    b += [H2("Discussão integrada e retorno à lacuna científica", "discussao"),
          P("A principal evidência desta execução é que o EVTEAS-Py não atua apenas como uma coleção de fórmulas. O fluxo integrado conduz as entradas da parametrização ao desempenho técnico, deste à projeção econômica, às métricas ambientais e sociais e, por fim, ao índice síntese, à regra de decisão e às análises de risco. Dessa forma, a proposta materializa computacionalmente a integração que a revisão de literatura identificou como lacuna instrumental (Calabrese et al., 2019; Silva Araújo; Keesman; Goddek, 2021)."),
          P(f"O caso-base explicita os trade-offs. O módulo técnico produziu OEE de {pc(T['oee'])} e o social LSO de {n(S['lso_0_100'], 1)} e renda de {n(S['renda_em_salarios_minimos'])} salários mínimos por cooperado, mas a viabilidade econômica é marginal e frágil sob incerteza. O framework, portanto, não mascara a fragilidade econômica em razão de bons resultados em outras dimensões; ao contrário, torna o conflito entre dimensões visível, o que corresponde à metáfora do painel de instrumentos de Kaplan e Norton (1992)."),
          P("A camada probabilística é a contribuição mais relevante desta revisão. O mesmo projeto que uma planilha determinística classificaria como viável apresenta 86% de probabilidade de destruir valor na perspectiva do projeto. Esse resultado transforma um diagnóstico estático em informação de decisão, ao indicar as variáveis críticas (preço, FCR e custo da ração), a folga de cada uma e o papel do fomento na redução do risco do beneficiário. Para pequenos produtores e comunidades pesqueiras, essa informação é mais útil do que um único VPL, porque orienta onde negociar contratos de venda, onde investir em manejo e qual aporte não reembolsável é necessário."),
          P("A quantificação dos desperdícios Lean-Green e a decomposição das emissões mostram, em linha com Mesquita et al. (2022) e Kosasih, Pujawan e Karningsih (2023), que eficiência operacional e desempenho ambiental convergem no caso da ração: reduzir o FCR melhora simultaneamente o VPL, a pegada de carbono e a pegada hídrica cinza. A regra de vetos, por sua vez, impede a compensação entre dimensões que Wang et al. (2025) associam aos excessos da busca por eficiência."),
          P("Em termos de Design Science Research, a evidência desta revisão sustenta a existência de um artefato funcional, verificável e reprodutível em nível computacional. A validade externa, porém, permanece limitada porque o caso-base é ilustrativo, as distribuições e as faixas de normalização foram parametrizadas pelo desenvolvedor e a avaliação dos especialistas ainda não foi concluída. A generalização deve, portanto, ser formulada em termos de princípios de projeto, arquitetura e procedimento de avaliação, e não como validade universal dos parâmetros utilizados.")]
    b += COD("pipeline", "Pipeline principal reproduzível do EVTEAS-Py", COD_PIPELINE)
    b += [P("O pipeline principal (⟦Código:pipeline⟧) é a evidência mais direta da integração: ele valida o tipo da configuração, resolve os pesos, executa o motor das quatro dimensões, monta a DRE, a curva de crescimento, os ODS e a tabela de premissas, habilita Monte Carlo, sensibilidade, valores críticos e cenários quando solicitado, aplica a regra de decisão e, ao final, registra a verificação. A ordem das chamadas reproduz a dependência lógica dos resultados e fornece um ponto único de entrada para execução reprodutível.")]

    # ------------------------------------------------------------------ Capítulo 5
    b += [H1("5 CONSIDERAÇÕES FINAIS"),
          P("A pesquisa teve como problema a necessidade de estruturar um EVTEAS computacional que integrasse dimensões técnica, econômica, ambiental e social e ainda oferecesse mecanismos de tratamento da incerteza e apoio à decisão. A versão 2.0 do EVTEAS-Py materializa essa proposta em um pacote Python com motor único vetorizado, entradas interativas e por arquivo, rastreabilidade das premissas, índice integrado com regra de decisão não compensatória, Monte Carlo, sensibilidade, comparação de alternativas, verificação automatizada e exportação. A execução do caso-base demonstra o funcionamento do artefato e evidencia como os módulos produzem um diagnóstico integrado."),
          P("Em termos do ciclo da Design Science Research, este capítulo corresponde às três últimas etapas: a conclusão (Etapa 10), nas Seções ⟦n:sintese⟧ a ⟦n:limitacoes⟧; a generalização para a classe de problemas (Etapa 11), na ⟦Seção:generalizacao⟧; e a comunicação dos resultados (Etapa 12), na ⟦Seção:comunicacao⟧. Como a validação com especialistas ainda não foi realizada, as conclusões referem-se à primeira iteração do ciclo e serão revistas na versão final da dissertação."),
          H2("Síntese da resposta ao problema de pesquisa", "sintese"),
          P("A resposta ao problema é afirmativa quanto à viabilidade de estruturar, em Python, uma cadeia integrada de processamento para EVTEAS aplicado à piscicultura. O artefato reúne os dados em uma configuração central, propaga resultados entre módulos com o mesmo código nas camadas determinística e estocástica e conserva uma trilha de verificação. A conclusão, porém, deve ser qualificada: a pesquisa demonstra viabilidade computacional e metodológica do framework, mas ainda não demonstra validade universal para empreendimentos reais."),
          P("Quanto à hipótese, a execução completa do estudo em cerca de um minuto, a partir de um único arquivo de premissas, indica que a automação reduz o tempo de elaboração e de revisão de cenários em relação ao fluxo manual em planilhas e documentos. A confirmação quantitativa desse ganho depende de comparação controlada com o processo tradicional, prevista como trabalho futuro."),
          H2("Atendimento ao objetivo geral e aos objetivos específicos", "objetivos"),
          P("O objetivo geral foi atendido no nível de desenvolvimento do artefato: as dimensões técnica, econômica, ambiental e social estão integradas no mesmo fluxo e podem ser submetidas a Monte Carlo, sensibilidade e verificação. O primeiro objetivo específico foi atendido com a operacionalização dos oito KPIs do Quadro 5 e de indicadores complementares (pegada hídrica cinza, intensidade de carbono, conformidade, Radar Social, ODS e governança). O segundo foi atendido com o desenvolvimento do pacote e a explicitação de trade-offs por índice, vetos e TOPSIS. O terceiro, a validação com especialistas, permanece como etapa necessária; o código já recebe os escores Likert e registra a divergência entre avaliadores. O quarto foi atendido parcialmente, pela simulação de um caso ilustrativo."),
          P(f"A execução do caso-base demonstra a aplicação do artefato. Foram obtidos OEE de {n(T['oee'], 3)}, produção anual de {n(T['producao_kg_ano'], 0)} kg, VPL determinístico de {rs(E['vpl'])}, probabilidade de VPL positivo de {pc(ST['prob_vpl_positivo'])} e índice EVTEAS de {n(I['indice_evteas'], 3)}, com classificação “{D['classificacao']}”. Esses resultados comprovam que o framework produz um diagnóstico integrado, mas não devem ser tratados como evidência de desempenho de uma unidade real."),
          H2("Contribuições científicas, metodológicas e aplicadas", "contribuicoes"),
          P("A contribuição científica está na proposição de um artefato e de uma arquitetura de integração para uma classe delimitada de problemas de viabilidade aquícola. A contribuição metodológica está na combinação de Design Science Research, modelagem computacional, análise qualiquantitativa, verificação automatizada, simulação e sensibilidade, com a regra de que o mesmo motor sirva às camadas determinística e estocástica. A contribuição computacional está na consolidação das entradas, no registro da origem das premissas, no processamento modular e na exportação estruturada. A contribuição gerencial consiste em tornar explícitos trade-offs entre desempenho técnico, retorno econômico, impacto ambiental e dimensão social, e em separar a perspectiva do projeto da perspectiva do beneficiário de fomento."),
          P("Outra contribuição emerge da própria execução: o framework revelou que a avaliação na moda das premissas superestima a viabilidade quando os riscos são assimétricos, e que a pegada hídrica cinza da tilapicultura em viveiros é dominada pelo fósforo. O valor do artefato, nesse sentido, não está apenas em calcular, mas em tornar visíveis premissas e resultados que demandam revisão."),
          H2("Limitações da pesquisa e do artefato", "limitacoes"),
          P("A primeira limitação é a dependência da qualidade das entradas. A segunda é a delimitação da pesquisa à piscicultura e a um caso-base ilustrativo, sem dados de um empreendimento real. A terceira é a ausência, nesta versão, de validação independente por especialistas e de confronto sistemático com dados observados de empreendimentos reais."),
          P("Há ainda limitações na própria modelagem. As faixas de normalização, a heurística logística do risco social e os pesos dos componentes da LSO foram definidos pelo autor e precisam de calibração. O crescimento segue taxa específica constante, sem efeito da temperatura e da sazonalidade. Os tributos sobre o resultado são aproximados mensalmente. Os fatores de emissão da ração e da energia são parâmetros bibliográficos que devem ser atualizados ao ano-base de cada estudo. As variáveis do Monte Carlo são amostradas de forma independente, sem correlação entre elas, como entre preço da ração e preço do pescado."),
          H2("Generalização para a classe de problemas (Etapa 11)", "generalizacao"),
          P("A generalização mais defensável é arquitetural e metodológica. É transferível a lógica de organizar requisitos, entradas com origem declarada, processamento vetorizado, indicadores normalizados, regra de decisão não compensatória, incerteza, verificação e exportação em um único artefato. Parâmetros zootécnicos, econômicos, ambientais e sociais devem, contudo, ser recalibrados para cada novo contexto, espécie, sistema produtivo ou território."),
          P("Na forma de regras tecnológicas, no sentido atribuído pela Design Science Research (Dresch; Lacerda; Antunes Jr., 2015), a primeira iteração permite formular os seguintes princípios de projeto para artefatos da classe de problemas definida na Etapa 4, cada um associado à evidência que o sustenta neste trabalho:"),
          B("para que as análises determinística e estocástica sejam coerentes, usar um único motor de cálculo vetorizado, no qual o cenário determinístico seja a simulação com uma única amostra (⟦Seção:design⟧ e ⟦Seção:mc⟧);"),
          B("para que o resultado represente o projeto do usuário, começar pela entrada de dados, sem valores padrão silenciosos, e registrar a origem de cada premissa (⟦Seção:interface⟧);"),
          B("para que bons resultados em uma dimensão não ocultem falhas em outra, combinar o índice compensatório com vetos não compensatórios (⟦Seção:indice⟧);"),
          B("para que a decisão considere o risco, e não apenas o cenário mais provável, informar a probabilidade de VPL positivo e os valores críticos das premissas (Seções ⟦n:mc⟧ e ⟦n:sensibilidade⟧);"),
          B("para que o artefato continue correto ao evoluir, ligar cada requisito às funções que o implementam e aos testes que o verificam, e conferir essa ligação automaticamente (⟦Seção:vv⟧)."),
          P("Para aplicar esses princípios a outras cadeias agroindustriais, substituem-se os modelos técnico e ambiental pelos da nova cadeia e mantêm-se a configuração com origem declarada, o motor vetorizado, a normalização, a regra de decisão, a camada de incerteza e a verificação."),
          H2("Comunicação dos resultados (Etapa 12)", "comunicacao"),
          P("A comunicação dos resultados foi tratada como parte do artefato. Para o público acadêmico, esta dissertação apresenta o percurso e os resultados, e os Apêndices A e B reproduzem o código-fonte e os testes na versão utilizada. Para reprodução e auditoria, o código, os testes, o arquivo de entradas do caso-base, as saídas da execução de referência e os scripts que geram os Capítulos 4 e 5 estão versionados no repositório do projeto; os números citados no Capítulo 4 são lidos diretamente das saídas da execução, o que impede divergência entre o texto e o código. Para os profissionais do setor, o notebook autocontido orienta a execução no Google Colab, do preenchimento das entradas à exportação de planilhas, relatórios e figuras. Estão previstos, ainda, artigos científicos derivados e um manual de uso voltado a técnicos de extensão e cooperativas, a serem elaborados após a validação com especialistas."),
          H2("Trabalhos futuros e continuidade do EVTEAS-Py", "futuros"),
          B("Conduzir a segunda iteração do ciclo DSR a partir da validação com especialistas, retornando às Etapas 6 a 9 e atualizando a matriz de rastreabilidade e o registro de aprendizagens."),
          B("Realizar a avaliação estruturada com os dois especialistas, registrar os escores Likert e as observações e incorporar os ajustes ao artefato."),
          B("Calibrar as distribuições de Monte Carlo com séries históricas reais e introduzir correlação entre variáveis, como entre o preço da ração e o do pescado."),
          B("Incorporar modelos de crescimento dependentes da temperatura e o tratamento da sazonalidade de preços e da produção."),
          B("Calibrar as faixas de normalização, os componentes da LSO e a função de risco social com especialistas e dados de campo."),
          B("Expandir o framework para outras espécies e sistemas de produção após nova parametrização e V&V."),
          B("Integrar bases confiáveis de preço, energia, água, clima e parâmetros zootécnicos, mantendo registro das fontes."),
          B("Desenvolver uma interface de usuário final como camada separada do núcleo científico-computacional."),
          B("Comparar, em experimento controlado, o tempo e a consistência de estudos elaborados com o EVTEAS-Py e com o fluxo tradicional em planilhas, para testar a hipótese da pesquisa."),
          B("Realizar validação longitudinal por comparação entre projeções e desempenho observado em empreendimentos implantados."),
          ]
    return b


NOVAS_REFERENCIAS = [
    # (texto da referência, texto inicial da referência existente antes da qual inserir)
    ("BRASIL. Lei nº 5.764, de 16 de dezembro de 1971. Define a Política Nacional de Cooperativismo, institui o regime jurídico das sociedades cooperativas, e dá outras providências. Diário Oficial da União, Brasília, DF, 16 dez. 1971.", None),
    ("BRASIL. Lei nº 9.433, de 8 de janeiro de 1997. Institui a Política Nacional de Recursos Hídricos, cria o Sistema Nacional de Gerenciamento de Recursos Hídricos. Diário Oficial da União, Brasília, DF, 9 jan. 1997.", None),
    ("BRASIL. Conselho Nacional do Meio Ambiente. Resolução nº 413, de 26 de junho de 2009. Dispõe sobre o licenciamento ambiental da aquicultura, e dá outras providências. Diário Oficial da União, Brasília, DF, 30 jun. 2009.", None),
    ("BRASIL. Conselho Nacional do Meio Ambiente. Resolução nº 430, de 13 de maio de 2011. Dispõe sobre as condições e padrões de lançamento de efluentes. Diário Oficial da União, Brasília, DF, 16 maio 2011.", None),
    ("BRASIL. Lei nº 12.651, de 25 de maio de 2012. Dispõe sobre a proteção da vegetação nativa. Diário Oficial da União, Brasília, DF, 28 maio 2012.", None),
    ("BRASIL. Lei nº 12.690, de 19 de julho de 2012. Dispõe sobre a organização e o funcionamento das Cooperativas de Trabalho. Diário Oficial da União, Brasília, DF, 20 jul. 2012.", None),
    ("HWANG, C.-L.; YOON, K. Multiple attribute decision making: methods and applications. Berlin: Springer-Verlag, 1981.", None),
    ("SAATY, T. L. The analytic hierarchy process: planning, priority setting, resource allocation. New York: McGraw-Hill, 1980.", None),
    ("WBCSD – WORLD BUSINESS COUNCIL FOR SUSTAINABLE DEVELOPMENT. Eco-efficiency: creating more value with less impact. Geneva: WBCSD, 2000.", None),
]

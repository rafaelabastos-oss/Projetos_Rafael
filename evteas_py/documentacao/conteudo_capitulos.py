"""Conteúdo dos Capítulos 4 e 5: texto-modelo com lacunas a preencher pela execução do usuário.

O texto não traz resultados de uma simulação prévia. Cada valor de entrada ou de
resultado aparece como lacuna identificada por código (⟪E05⟫, ⟪S23⟫, ⟪K01⟫, ⟪N01⟫),
resolvida a partir do registro ``evteas_py.campos_texto``; o notebook exibe e exporta
o valor de cada código na execução do usuário. Os prints (⟪P01⟫ a ⟪P20⟫) indicam a tela
do wizard ou a saída do notebook a capturar. Os números que permanecem no texto vêm do
próprio código (estrutura, testes e rastreabilidade), e não de uma execução do estudo.
"""
from __future__ import annotations

import inspect
import json
import math
import re
from pathlib import Path

import evteas_py
from evteas_py import campos_texto as CT
from evteas_py import config, dsr, financeiro, incerteza, interface, modelo, pipeline, ponderacao, vv

RAIZ = Path(__file__).resolve().parents[1]
FONTE_COD = "Fonte: elaboração própria (2026), a partir do código do EVTEAS-Py."
FONTE_RES = "Fonte: elaboração própria (2026), a partir da execução do EVTEAS-Py."
FONTE_WIZ = "Fonte: elaboração própria (2026), a partir do wizard de entrada do EVTEAS-Py."


# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------

def n(v, c=2):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "n/d"
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def rs(v, c=0):
    neg = v < 0
    s = "R$ " + n(abs(v), c)
    return ("−" + s) if neg else s


def mil(v, c=1):
    return rs(v / 1000, c) + " mil"


def pc(v, c=1):
    return n(v * 100, c) + "%"


EXTENSO = {1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez"}


def extenso(k, genero="m"):
    t = EXTENSO.get(k, str(k))
    return {"um": "uma", "dois": "duas"}.get(t, t) if genero == "f" else t


EXCLUSIVAS_TEXTO = {
    "Governança, ESG e Lean Green": "governança, ESG e Lean Green",
    "Simulação estocástica (Monte Carlo)": "simulação estocástica (Monte Carlo)",
    "Ponderação multicritério com regra de decisão": "ponderação multicritério com regra de decisão",
}


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
COD_PIPELINE = trecho(pipeline.executar_evteas, "def executar_evteas", 'resultado["tempo_execucao_s"]', False) + "\n    return resultado"


# ---------------------------------------------------------------------------
# Tabelas auxiliares
# ---------------------------------------------------------------------------

def _revisao_independente():
    r1, r2 = REVISOES["rodadas"][0], REVISOES["rodadas"][1]
    texto = ("Além dos testes, a entrada de dados foi submetida a revisões adversariais independentes, conduzidas com "
             "apoio de inteligência artificial generativa sob supervisão do pesquisador, nos termos da Seção 3.5. Agentes "
             "revisores, separados do desenvolvimento, tentaram quebrar o wizard com respostas inválidas e casos-limite, "
             "examinaram a clareza das perguntas e a execução no Google Colab e testaram a reabertura de arquivos de "
             f"entradas, inclusive incompletos ou de outro tipo. A primeira rodada apontou {r1['apontados']} problemas, entre "
             "eles distribuições de Monte Carlo que não acompanhavam a correção de um valor, unidades diferentes entre a "
             "pergunta e o armazenamento do custo do alevino e valores em reais convertidos em percentual do CAPEX; todos "
             "foram reproduzidos, corrigidos e cobertos por testes de regressão. ")
    if r2.get("concluida"):
        texto += (f"Na segunda rodada, cada achado foi reproduzido por um agente "
                  f"verificador independente antes de ser aceito: dos {r2['apontados']} apontamentos, {r2['confirmados']} "
                  f"foram confirmados e corrigidos{r2.get('complemento', '')}.")
    return texto


# Tabelas de preenchimento: ⟪E05:c⟫ vira "[E05]", e ⟪E05:o⟫, "[E05 – origem]" (valor e origem
# declarada vêm da tabela "Valores para o texto" do notebook).

def tabela_premissas():
    return [
        ["Bloco", "Premissa", "Valor informado", "Origem declarada"],
        ["Infraestrutura", "Área de lâmina d'água; profundidade média", "⟪E05:c⟫ m²; ⟪E06:c⟫ m", "⟪E05:o⟫; ⟪E06:o⟫"],
        ["Infraestrutura", "Viveiros (total / ativos); sistema produtivo", "⟪E07:c⟫ / ⟪E08:c⟫; ⟪E04:c⟫", "⟪E07:o⟫; ⟪E08:o⟫"],
        ["Biológico", "Peso inicial / de abate; duração do ciclo", "⟪E10:c⟫ g / ⟪E11:c⟫ g; ⟪E12:c⟫ dias", "⟪E10:o⟫; ⟪E11:o⟫; ⟪E12:o⟫"],
        ["Biológico", "Ciclos por ano; produtividade esperada", "⟪E13:c⟫; ⟪E09:c⟫ kg/m²/ciclo", "⟪E13:o⟫; ⟪E09:o⟫"],
        ["Insumos", "FCR; mortalidade esperada; alevinos por ciclo", "⟪E14:c⟫; ⟪E15:c⟫; ⟪E44:c⟫", "⟪E14:o⟫; ⟪E15:o⟫; ⟪E44:o⟫"],
        ["Econômico", "CAPEX (classe da estimativa); capital de giro", "⟪E16:c⟫ (⟪E17:c⟫); ⟪E18:c⟫", "⟪E16:o⟫; ⟪E17:o⟫; ⟪E18:o⟫"],
        ["Econômico", "Fomento não reembolsável", "⟪E19:c⟫ do CAPEX", "⟪E19:o⟫"],
        ["Econômico", "Preço de venda; ração; alevino; energia", "⟪E20:c⟫/kg; ⟪E21:c⟫/kg; ⟪E22:c⟫/un; ⟪E23:c⟫/kWh",
         "⟪E20:o⟫; ⟪E21:o⟫; ⟪E22:o⟫; ⟪E23:o⟫"],
        ["Econômico", "Remuneração mensal da equipe; cooperados", "⟪E24:c⟫; ⟪E25:c⟫", "⟪E24:o⟫; ⟪E25:o⟫"],
        ["Econômico", "TMA; horizonte; capacidade inicial", "⟪E26:c⟫; ⟪E27:c⟫ anos; ⟪E28:c⟫", "⟪E26:o⟫; ⟪E27:o⟫; ⟪E28:o⟫"],
        ["Econômico", "Tributos sobre o faturamento; sobre o resultado; sobre o trabalho e os serviços",
         "⟪E29:c⟫; ⟪E30:c⟫; ⟪E45:c⟫", "⟪E45:o⟫"],
        ["Ambiental", "Limites de N e P do corpo receptor", "⟪E31:c⟫", "⟪E31:o⟫"],
        ["Ambiental", "Remoção de N e P no tratamento; fonte de energia", "⟪E32:c⟫; ⟪E33:c⟫", "⟪E32:o⟫"],
        ["Social", "Empregos; mão de obra local; compras locais", "⟪E34:c⟫; ⟪E35:c⟫; ⟪E36:c⟫", "⟪E34:o⟫; ⟪E35:o⟫; ⟪E36:o⟫"],
    ]


def tabela_economica():
    return [
        ["Indicador", "Projeto", "Beneficiário (com fomento)"],
        ["Investimento inicial (CAPEX + capital de giro)", "⟪S21:c⟫", "⟪S22:c⟫"],
        ["VPL à TMA informada", "⟪S23:c⟫", "⟪S37:c⟫"],
        ["TIR anual (diagnóstico)", "⟪S24:c⟫", "⟪S38:c⟫"],
        ["Payback descontado", "⟪S25:c⟫", "⟪S39:c⟫"],
        ["Payback simples", "⟪S26:c⟫", "—"],
        ["Índice de lucratividade", "⟪S27:c⟫", "—"],
        ["Receita bruta no ano de regime (ano ⟪S28:c⟫)", "⟪S29:c⟫", "—"],
        ["Resultado líquido no ano de regime", "⟪S30:c⟫", "—"],
        ["ROI anual em regime (Quadro 5)", "⟪S31:c⟫", "—"],
        ["Ponto de equilíbrio (kg/ano); margem de segurança", "⟪S32:c⟫; ⟪S33:c⟫", "—"],
        ["Custo total e custo operacional efetivo (por kg)", "⟪S34:c⟫ e ⟪S35:c⟫", "—"],
    ]


def tabela_ambiental_social():
    return [
        ["Dimensão", "Indicador", "Resultado"],
        ["Ambiental", "Água captada (m³/ano); índice de uso da água (kg/m³)", "⟪S41:c⟫; ⟪S42:c⟫"],
        ["Ambiental", "Pegada hídrica azul (m³/t)", "⟪S43:c⟫"],
        ["Ambiental", "Pegada hídrica cinza (m³/t); poluente crítico", "⟪S44:c⟫; ⟪S45:c⟫"],
        ["Ambiental", "Balanço do nitrogênio (kg/ano)", "⟪S46:c⟫"],
        ["Ambiental", "Balanço do fósforo (kg/ano)", "⟪S47:c⟫"],
        ["Ambiental", "Emissões totais (tCO2e/ano)", "⟪S50:c⟫"],
        ["Ambiental", "Emissões por fonte", "⟪S51:c⟫"],
        ["Ambiental", "Intensidade de carbono (kgCO2e/kg); ecoeficiência", "⟪S53:c⟫; ⟪S54:c⟫"],
        ["Ambiental", "Score de conformidade ambiental (0–10)", "⟪S55:c⟫"],
        ["Social", "Retenção de Valor Local (% do custo operacional)", "⟪S60:c⟫"],
        ["Social", "Índice de Impacto Local (% da receita)", "⟪S61:c⟫"],
        ["Social", "Renda mensal por trabalhador; em salários mínimos", "⟪S40:c⟫; ⟪S62:c⟫"],
        ["Social", "LSO (0–100); score de risco social (0–1)", "⟪S63:c⟫; ⟪S64:c⟫"],
        ["Social", "Radar Social (média dos seis eixos)", "⟪S65:c⟫"],
        ["Governança", "Checklist do pilar G", "⟪S69:c⟫"],
    ]


def tabela_mc():
    return [
        ["Estatística", "Valor"],
        ["Média do VPL", "⟪S80:c⟫"],
        ["Mediana; desvio-padrão; coeficiente de variação do VPL", "⟪S81:c⟫"],
        ["Percentis P5 / P50 / P95 do VPL", "⟪S82:c⟫"],
        ["VaR 5% e CVaR 5% do VPL", "⟪S83:c⟫"],
        ["P(VPL > 0)", "⟪S84:c⟫"],
        ["TIR anual: P5 / P50 / P95", "⟪S86:c⟫"],
        ["Índice EVTEAS: média; P(índice ≥ limiar de viabilidade)", "⟪S87:c⟫"],
        ["VPL do beneficiário", "⟪S88:c⟫"],
        ["Erro-padrão da média do VPL", "⟪S89:c⟫"],
    ]


def tabela_distribuicoes():
    linhas = [["Variável", "Distribuição informada (tipo e parâmetros)"]]
    for i, (_, nome, *_) in enumerate(CT.VARIAVEIS_DIST):
        linhas.append([nome, f"⟪E{50 + i}:c⟫"])
    return linhas


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
        ["casos", "Caso ilustrativo e alternativas de referência, usados nos testes e no modo “exemplo”", "Etapa 8 da DSR"],
        ["relatorios", "Resumo executivo, Excel, JSON, Markdown e figuras", "Etapa 12 da DSR"],
        ["interface", "Menu inicial, wizard completo de entradas, arquivos JSON e análise de preços", "Seção 2.8.3 (PMBOK)"],
        ["dsr", "Etapas da DSR, comparação com artefatos, requisitos, rastreabilidade e aprendizagens", "Seção 3.3.1 (Etapas 4, 5, 8 e 9)"],
        ["campos_texto", "Valores da execução que preenchem o relato dos resultados e roteiro de prints", "Etapa 12 da DSR"],
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
    dim = {k: d for d, ks in config.KPIS_POR_DIMENSAO.items() for k in ks}
    nomes_dim = {"tecnico": "Técnica", "economico": "Econômica", "ambiental": "Ambiental", "social": "Social"}
    linhas = [["Dimensão", "KPI", "Sentido", "Faixa de referência", "Valor bruto", "Normalizado"]]
    for k, (sent, lo, hi, _) in ponderacao.REFERENCIAS_NORMALIZACAO.items():
        c = CT.CODIGO_KPI[k]
        linhas.append([nomes_dim[dim[k]], CT.ROTULO_KPI[k], "benefício" if sent > 0 else "custo", f"{n(lo, 2)} a {n(hi, 2)}",
                       f"⟪K{c}:c⟫", f"⟪N{c}:c⟫"])
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
def PRINT(chave, titulo, codigo, fonte=FONTE_RES): return [_cap("Figura", chave, titulo), {"k": "print", "t": f"⟪{codigo}⟫"}, {"k": "fonte", "t": fonte}]


# Lacunas: ⟪S23⟫ → "[R23 – VPL do projeto]"; ⟪S23:c⟫ → "[R23]" (tabelas); ⟪E05:o⟫ → "[E05 – origem]";
# ⟪P04⟫ → "[INSERIR PRINT P04 – ...]". Comentários de redação ficam como [INTERPRETAR: ...] e [PREENCHER: ...].
LACUNA = re.compile(r"⟪([ESKNP]\d{2,3})(?::([co]))?⟫")


def resolver_lacuna(m):
    codigo, forma = m.group(1), m.group(2)
    if codigo.startswith("P"):
        return CT.PRINT_POR_CODIGO[codigo].lacuna
    if codigo not in CT.POR_CODIGO:
        raise KeyError(f"lacuna sem registro em evteas_py.campos_texto: {codigo}")
    return {"c": f"[{codigo}]", "o": f"[{codigo} – origem]"}.get(forma, CT.lacuna(codigo))


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
            x["t"] = LACUNA.sub(resolver_lacuna, REFERENCIA.sub(resolver, x["t"]))
        if x["k"] == "tbl":
            x["linhas"] = [[LACUNA.sub(resolver_lacuna, REFERENCIA.sub(resolver, str(c))) for c in linha] for linha in x["linhas"]]
    return b, mapa


def referencias():
    return numerar(_blocos())[1]


def fig(nome):
    return str(RAIZ / "saidas" / "figuras" / f"{nome}.png")      # só a arquitetura (não depende de uma execução)


def blocos():
    return numerar(_blocos())[0]


def _blocos():
    b = []
    b += [H1("4 RESULTADOS E DISCUSSÃO"),
          P("[NOTA AO AUTOR – excluir após o preenchimento: os trechos destacados em amarelo nos Capítulos 4 e 5 são lacunas a preencher com a execução do estudo de caso no notebook EVTEAS_Py. Os códigos E correspondem às entradas informadas no wizard, e os códigos S, K e N, aos resultados (saídas) da análise; o valor de cada código é exibido na seção “Valores para o texto” do notebook e gravado na planilha valores_para_o_texto.xlsx. Nas tabelas, a lacuna aparece só com o código (por exemplo, [S23]); [E05 – origem] corresponde à coluna “Origem declarada” da linha E05, e, quando várias origens de uma mesma linha coincidirem, basta citá-las uma vez. O mesmo código pode aparecer mais de uma vez nos dois capítulos; use a busca do editor pelo código. Os marcadores INSERIR PRINT indicam a tela do wizard ou a saída do notebook a capturar: o wizard e o notebook anunciam cada uma com a linha “▶ PRINT” e o mesmo código P, e a aba “Roteiro de prints” da planilha explica como capturá-la; ao inserir a imagem, substitua o parágrafo da caixa tracejada (apague-o e insira a figura num parágrafo centralizado, sem borda e sem recuo), mantendo a legenda e a fonte. Para a Seção ⟦n:sensibilidade⟧, execute também a comparação de alternativas do notebook antes de gerar os valores para o texto. Os marcadores INTERPRETAR indicam a análise a redigir com base nos valores obtidos, e os marcadores PREENCHER, informações que o artefato não produz. Após o preenchimento, remover o realce.]"),

          P("O Capítulo 4 apresenta os resultados da construção do EVTEAS-Py e da sua aplicação ao estudo de caso, tomando como evidência central o código efetivamente implementado e a execução do artefato com as entradas informadas pelo pesquisador. A apresentação segue a lógica Entrada → Processamento → Saída → Verificação → Interpretação, aproximando a descrição do framework do percurso metodológico definido no Capítulo 3: em cada dimensão, apresentam-se as telas de entrada preenchidas, o processamento implementado, as saídas produzidas e a sua interpretação."),
          P("O EVTEAS-Py foi implementado como o pacote Python evteas_py, acompanhado de um notebook autocontido para o Google Colab e de uma suíte de testes automatizados. O estudo começa obrigatoriamente pela entrada de dados: nenhum resultado é calculado antes que as premissas do projeto sejam informadas. O estudo de caso corresponde ao projeto ⟪E01⟫, conduzido por uma ⟪E02⟫, para o cultivo de ⟪E03⟫ em sistema ⟪E04⟫. [PREENCHER: localização, público beneficiário e contexto do empreendimento.] As premissas foram informadas no wizard de entrada e registradas no arquivo ⟪E00⟫, e a análise foi executada pela função executar_evteas(), com Monte Carlo habilitado, ⟪E41⟫ iterações e seed ⟪E42⟫. As telas de entrada e as saídas reproduzidas nas figuras deste capítulo foram capturadas dessa execução. Os números apresentados adiante são, portanto, resultados computacionais reproduzíveis a partir do arquivo de entradas e da seed, e não observações de campo; essa distinção preserva a coerência entre o que efetivamente foi executado e o que ainda depende de validação externa.")]

    b += [P("A organização do capítulo acompanha o ciclo da Design Science Research definido na Seção 3.3.1 (Dresch; Lacerda; Antunes Jr., 2015). A ⟦Seção:dsr⟧ sintetiza o percurso das doze etapas; a ⟦Seção:dsr_requisitos⟧ registra a identificação de artefatos preexistentes, a classe de problemas e os requisitos do artefato (Etapas 4 e 5); as Seções ⟦n:design⟧ a ⟦n:sensibilidade⟧ apresentam o design, o desenvolvimento e os resultados do EVTEAS-Py (Etapas 6 e 7); a ⟦Seção:vv⟧ trata da avaliação (Etapa 8); a ⟦Seção:aprendizagens⟧, da explicitação das aprendizagens (Etapa 9); a ⟦Seção:exportacao⟧, da exportação e da reprodutibilidade; e a ⟦Seção:discussao⟧, da discussão integrada dos resultados. As Etapas 10 a 12 são tratadas no Capítulo 5.")]

    m_dsr = dsr.matriz_rastreabilidade(RAIZ / "tests")
    ined = dsr.combinacao_inedita()
    b += [H2("Percurso da Design Science Research na construção do EVTEAS-Py", "dsr"),
          P("A construção do EVTEAS-Py seguiu as doze etapas da Design Science Research adotadas no Capítulo 3. Para que o percurso fosse verificável, e não apenas declarado, cada etapa foi registrada no próprio artefato, no módulo dsr, com o produto que a etapa gerou, o local em que a evidência pode ser conferida e a situação em que se encontra. O ⟦Quadro:etapas⟧ sintetiza esse registro. As Etapas 1 a 3 correspondem aos Capítulos 1 e 2; as Etapas 4 a 9 são apresentadas neste capítulo; e as Etapas 10 a 12, no Capítulo 5.")]
    b += TAB("Quadro", "etapas", "Etapas da Design Science Research e evidências no EVTEAS-Py", quadro_etapas_dsr(),
             [1800, 3800, 1700, 1200], "Fonte: elaboração própria (2026), com base em Dresch, Lacerda e Antunes Jr. (2015).")
    b += [P("Em relação ao cronograma do Quadro 8, as Etapas 4 a 7 tiveram uma primeira iteração concluída, e a Etapa 8 foi realizada na sua parte de verificação, o que antecipa parte da Fase 3. A validação com os dois especialistas, prevista na Seção 3.3.2, permanece pendente e dará início à segunda iteração do ciclo: as observações dos especialistas retornarão às Etapas 6 e 7 como anomalias e sugestões de melhoria, e o artefato será novamente verificado e avaliado. A DSR é, portanto, aplicada de forma iterativa, e os resultados deste capítulo correspondem à primeira volta do ciclo.")]

    b += [H2("Artefatos preexistentes, classe de problemas e requisitos (Etapas 4 e 5)", "dsr_requisitos"),
          P("A Etapa 4 enquadra o problema na classe “modelagem de suporte à decisão multicritério sob incerteza em agroindústrias” e confronta o EVTEAS-Py com os artefatos identificados na Seção 2.8.1. Seguindo Wazlawick (2009), a comparação foi organizada como tabela de propriedades (⟦Quadro:comparacao⟧). Para não atribuir aos outros artefatos limitações que as fontes não afirmam, cada célula registra apenas o que a Seção 2.8.1 descreve: “sim” quando a propriedade é descrita, “não” quando a fonte indica que ela está fora do escopo do artefato e “n.i.” quando a fonte consultada não a menciona. A comparação é, portanto, conservadora: “não identificado” não equivale a ausência da propriedade.")]
    b += TAB("Quadro", "comparacao", "Propriedades do EVTEAS-Py e de artefatos preexistentes", quadro_comparacao(),
             [2600, 1180, 1180, 1180, 1180, 1180], "Fonte: elaboração própria (2026), com base na Seção 2.8.1 e em Wazlawick (2009). n.i.: não identificado na fonte consultada.")
    excl = [EXCLUSIVAS_TEXTO.get(p, p) for p in ined["exclusivas"]]
    b += [P(f"Nenhum dos artefatos comparados reúne mais de {extenso(max(ined['cobertura_dos_demais'].values()))} das {extenso(len(ined['propriedades']))} propriedades do EVTEAS-Py, e {extenso(len(excl), 'f')} delas não foram identificadas em nenhum dos demais: {'; '.join(excl[:-1])}; e {excl[-1]}. Pelo critério de Wazlawick (2009), a contribuição do EVTEAS-Py está na combinação inédita dessas propriedades em um único artefato, e não em cada propriedade isoladamente. Há ferramentas que calculam a viabilidade econômica em Python (Costa Magalhães, 2022), que integram métricas técnico-econômicas e ambientais (Maier; Weyand, 2025), que atendem ao produtor aquícola (Ramos et al., 2024) ou que articulam indicadores econômicos, ambientais e socioculturais (Gimpel et al., 2018), mas nenhuma das descritas reúne essas dimensões com tratamento da incerteza e regra de decisão no nível do empreendimento aquícola."),
          P(f"Na Etapa 5, a proposição do artefato foi desdobrada em {len(dsr.REQUISITOS)} requisitos, derivados dos objetivos da pesquisa, da Seção 2.8 e dos procedimentos do Capítulo 3 (⟦Quadro:requisitos⟧). Os requisitos R02 e R03 também incorporam a experiência de uso dos notebooks de estudo de viabilidade econômica empregados pelo autor: o estudo deve começar pela entrada de dados, e um estudo salvo deve poder ser reaberto e revisto. O requisito R16 decorre da mesma preocupação com a reprodutibilidade: os valores citados no relato dos resultados devem ser os da execução feita com as entradas do usuário. Cada requisito foi registrado no módulo dsr com as funções que o implementam e os testes que o verificam, o que permite conferir a rastreabilidade a cada alteração do código (⟦Seção:vv⟧).")]
    b += TAB("Quadro", "requisitos", "Requisitos do EVTEAS-Py e sua origem", quadro_requisitos(), [1100, 5400, 2000],
             "Fonte: elaboração própria (2026).")

    n_modulos = len(quadro_modulos()) - 1
    b += [H2("Design e desenvolvimento do artefato EVTEAS-Py (Etapas 6 e 7)", "design"),
          P("O EVTEAS-Py foi estruturado como um framework modular em Python. A decisão central foi concentrar as premissas em estruturas de configuração e fazer com que um único objeto EVTEASConfig atravesse o pipeline. A configuração (⟦Código:config⟧) agrega os blocos técnico, econômico, ambiental, social, de governança, de pesos, de decisão e de Monte Carlo, além de um registro de fontes que associa cada premissa à sua origem. Essa organização permite separar a camada de aquisição de dados das rotinas analíticas e facilita a reprodução do estudo com um novo conjunto de premissas."),
          P(f"O código foi distribuído em {extenso(n_modulos) if n_modulos <= 10 else {11: 'onze', 12: 'doze', 13: 'treze'}[n_modulos]} módulos, cada um vinculado a uma seção da dissertação, como sintetiza o ⟦Quadro:modulos⟧. A ⟦Figura:arquitetura⟧ apresenta o fluxo entre as camadas.")]
    b += TAB("Quadro", "modulos", "Módulos do pacote evteas_py e vínculo com a dissertação", quadro_modulos(), [1500, 4300, 2700], "Fonte: elaboração própria (2026).")
    b += FIG("arquitetura", "Arquitetura do EVTEAS-Py", fig("00_arquitetura"), "Fonte: elaboração própria (2026).")
    b += COD("config", "Estrutura de configuração do EVTEAS-Py", COD_CONFIG)
    b += [P("A principal decisão arquitetural foi a vetorização do núcleo de cálculo. A classe Contexto devolve qualquer parâmetro numérico como um vetor de tamanho n: com n = 1 o modelo é determinístico; com n igual ao número de iterações, ele é a própria simulação de Monte Carlo. Com o motor único (⟦Código:motor⟧), a mesma fórmula produz o resultado pontual e a distribuição de resultados, o que impede que as camadas determinística e estocástica divirjam. Essa equivalência é verificada por teste automatizado, e a aprendizagem associada a essa decisão arquitetural está registrada no ⟦Quadro:aprendizagens⟧.")]
    b += COD("motor", "Contexto vetorizado e motor único das quatro dimensões", COD_MOTOR)
    b += [P("O pipeline executa também o AHP e o TOPSIS. O AHP é uma das três formas de obter os pesos dimensionais (ao lado do preset e da escala Likert do Quadro 7), com cálculo da razão de consistência (Saaty, 1980); o TOPSIS ordena alternativas de projeto pela proximidade relativa à solução ideal (Hwang; Yoon, 1981) e é utilizado na ⟦Seção:sensibilidade⟧.")]

    b += [H2("Interface de entrada e parametrização do estudo", "interface"),
          P("A entrada de dados é a primeira etapa de execução do EVTEAS-Py, coerente com a lógica dos grupos de processos de iniciação e planejamento do PMBOK (PMI, 2021): o artefato obriga o usuário a percorrer todas as etapas de levantamento de requisitos técnicos, econômicos, ambientais e sociais antes de produzir qualquer indicador. A função iniciar_entradas() (⟦Código:wizard⟧) apresenta um menu com três modos. No modo “novo projeto”, todas as premissas precisam ser digitadas; somente coeficientes técnicos com referência normativa ou bibliográfica, como os limites de nitrogênio e fósforo da Resolução CONAMA nº 357/2005 ou o teor de nitrogênio retido no peixe, e alguns parâmetros de configuração do próprio artefato, como o número de iterações, a seed e os limiares de decisão, aparecem como sugestão explícita, aceita com Enter e registrada com a sua origem. No modo “carregar arquivo”, um estudo salvo é reaberto e cada valor pode ser revisto; no modo “exemplo”, o caso ilustrativo incorporado ao pacote é carregado com o aviso de que os resultados não representam o projeto do usuário."),
          P("Para garantir que nenhum valor seja herdado silenciosamente, o modo “novo projeto” parte de uma configuração em branco, na qual todos os parâmetros numéricos estão indefinidos; ao final, a função entradas_pendentes() confere se algum permaneceu sem resposta e, nesse caso, interrompe o estudo indicando o parâmetro. O wizard está organizado em dezesseis blocos: identificação; infraestrutura; parâmetros biológicos e insumos; investimento; mix de produtos e receitas; custos operacionais; cooperados e funcionários CLT; tributos; rampa, projeção e TMA; água e efluentes; energia, emissões e resíduos; conformidade ambiental; dimensão social; governança; pesos e regras de decisão; e incerteza. Esse percurso contempla os campos econômicos levantados como requisitos de uso na Etapa 2 (⟦Quadro:etapas⟧), como tipo de organização, quantidades e preços de cada produto do mix, receita de transporte, carência, retiradas dos cooperados, mínimo legal de cooperados, salário de cada cargo CLT, distribuição de sobras e cada tributo com sua base de cálculo, e acrescenta os parâmetros técnico-ambientais-sociais."),
          P("As respostas são validadas quanto a tipo e limites e aceitam números no padrão brasileiro, como 40.000 ou 1.500,50; quando o ponto é lido como separador de milhar, o wizard mostra o valor interpretado. O usuário pode digitar “sair” a qualquer momento, e as respostas já dadas são salvas num arquivo de rascunho que pode ser reaberto para continuar de onde parou. Ao reabrir um arquivo de entradas, mesmo incompleto, os campos ausentes permanecem indefinidos, são listados como pendências e pedidos na revisão, e as distribuições do Monte Carlo são reposicionadas sempre que não forem coerentes com o valor determinístico registrado no arquivo. A incerteza só pode ser atribuída às variáveis que o motor de cálculo amostra, o que evita distribuições cadastradas sem efeito no resultado. Ao final de cada bloco, o wizard pergunta a origem dos dados informados (histórico, dado secundário, cotação, valor normativo, parâmetro bibliográfico, empreendimento análogo, especialista ou estimativa do autor), o que operacionaliza a rastreabilidade da Seção 3.6. Em seguida, apresenta um resumo das entradas, permite corrigir qualquer bloco e salva o arquivo entradas_<projeto>.json, que pode ser reaberto para revisão e guardado junto com os resultados. O artefato inclui ainda uma análise de preços a partir de planilha: com uma coluna de preços, sugere preços por estratégia (percentis 25, 50 e 75); com preços e quantidades, estima uma curva de demanda linear e o preço que maximiza a margem de contribuição.")]
    b += COD("wizard", "Início do estudo pela entrada de dados", COD_WIZARD)
    b += [P("A ⟦Figura:tela_menu⟧ reproduz o início da entrada de dados do estudo de caso: o menu inicial, com a opção escolhida, e o bloco de identificação do projeto. Durante a entrada, o wizard anuncia com a linha “▶ PRINT” cada tela reproduzida neste capítulo. Concluídos os dezesseis blocos, o wizard exibe o resumo das entradas para conferência antes de qualquer cálculo (⟦Figura:tela_resumo⟧). [INTERPRETAR: indicar se o estudo foi iniciado como novo projeto ou pela reabertura de um arquivo de entradas, e se alguma entrada foi corrigida após o resumo.]")]
    b += PRINT("tela_menu", "Menu inicial e identificação do projeto no wizard de entrada", "P01", FONTE_WIZ)
    b += PRINT("tela_resumo", "Resumo das entradas do estudo de caso antes da confirmação", "P02", FONTE_WIZ)
    b += [P("A rastreabilidade prevista na Seção 3.6 foi operacionalizada pela tabela de premissas, exportada junto com os resultados: cada parâmetro numérico aparece com seu valor, a categoria da fonte (dado histórico, dado secundário, cotação, valor normativo, parâmetro bibliográfico, empreendimento análogo, especialista ou estimativa do autor), a referência e, quando houver, a distribuição de probabilidade com mínimo, valor mais provável e máximo. O ⟦Quadro:premissas⟧ resume as principais premissas do estudo de caso e a origem declarada de cada uma; quando uma linha reúne premissas de origens diferentes, todas são indicadas. [INTERPRETAR: comentar a predominância de dados históricos, cotações ou estimativas e as premissas que mais dependem de validação.]")]
    b += TAB("Quadro", "premissas", "Principais premissas do estudo de caso e origem declarada", tabela_premissas(), [1300, 2700, 2500, 2000], FONTE_RES)
    b += [P("A parametrização tributária aceita alíquotas individuais (ICMS, PIS, COFINS, IRPJ, CSLL e contribuições sobre a folha ou sobre os cooperados) associadas a uma base de cálculo (faturamento, lucro ou folha), que o modelo consolida antes do cálculo econômico. No estudo de caso, a alíquota consolidada foi de ⟪E29⟫ sobre o faturamento e de ⟪E30⟫ sobre o resultado; sobre a remuneração do trabalho e os serviços, as alíquotas foram: ⟪E45⟫. [INTERPRETAR: justificar o enquadramento tributário adotado, por exemplo o tratamento do ato cooperativo (Brasil, 1971).] Essa parametrização, contudo, não significa que o framework reproduza integralmente a complexidade jurídico-contábil de todos os regimes tributários.")]

    b += [H2("Resultados da dimensão técnica", "tecnica"),
          P("A função calcular_tecnico() operacionaliza a dimensão técnica a partir dos três blocos de entrada descritos na Seção 2.8.6: infraestrutura, parâmetros biológicos e eficiência de insumos. A estocagem é tratada como decisão de projeto: quando o usuário não informa o número de alevinos por ciclo, o modelo o dimensiona para atingir a biomassa-alvo com a mortalidade esperada, enquanto a mortalidade e o desempenho de crescimento efetivos são incertos. Assim, quando a mortalidade simulada é maior, a biomassa despescada diminui."),
          P("Uma particularidade importante é o mecanismo de restrição dupla da biomassa (⟦Código:tecnico⟧). A biomassa-alvo é o menor valor entre o limite dado pela capacidade de suporte (volume útil × kg/m³) e o limite dado pela produtividade esperada por área. O OEE aquícola resulta do produto de disponibilidade (viveiros ativos/total), performance (crescimento realizado/esperado) e qualidade, que, em alinhamento ao Quadro 5, corresponde à taxa de sobrevivência.")]
    b += COD("tecnico", "Cálculo da dimensão técnica e OEE (trecho)", COD_TECNICO)
    b += [P("As entradas técnicas do estudo de caso foram informadas nos blocos 2 e 3 do wizard (⟦Figura:tela_tecnica⟧): ⟪E05⟫ m² de lâmina d'água, profundidade média de ⟪E06⟫ m, ⟪E07⟫ viveiros, dos quais ⟪E08⟫ ativos, produtividade esperada de ⟪E09⟫ kg/m² por ciclo, peso inicial de ⟪E10⟫ g, peso de abate de ⟪E11⟫ g, ciclo de ⟪E12⟫ dias, ⟪E13⟫ ciclos por ano, FCR de ⟪E14⟫ e mortalidade esperada de ⟪E15⟫. O número de alevinos por ciclo foi ⟪E44⟫.")]
    b += PRINT("tela_tecnica", "Entradas da dimensão técnica (blocos 2 e 3 do wizard)", "P03", FONTE_WIZ)
    b += [P("Com essas entradas, a restrição ativa da biomassa foi a ⟪S01⟫. Foram estocados ⟪S02⟫ alevinos por ciclo (densidade de ⟪S03⟫ peixes/m³), com despesca de ⟪S04⟫ kg por ciclo e produção de ⟪S05⟫ kg/ano (⟪S06⟫ kg/m²/ano, ⟪S07⟫ do potencial do sistema). O OEE foi ⟪S08⟫, resultado de disponibilidade ⟪S09⟫, performance ⟪S10⟫ e sobrevivência ⟪S11⟫, e o consumo de ração foi de ⟪S12⟫ kg/ano. [INTERPRETAR: indicar qual componente do OEE mais o reduziu e se a produtividade obtida é compatível com a do sistema produtivo na literatura (Kubitza, 2017).]"),
          P("A curva de crescimento (⟦Figura:curva⟧) é obtida por taxa de crescimento específico constante, com mortalidade distribuída ao longo do ciclo e arraçoamento calibrado para reproduzir o FCR. A curva subsidia o planejamento logístico do estoque de ração, em linha com a lógica Lean de redução de desperdícios.")]
    b += PRINT("curva", "Curva de crescimento, biomassa e ração acumulada no ciclo", "P04")
    b += [P("O módulo Lean-Green quantifica, em reais por ano, os desperdícios evitáveis em relação às referências declaradas na entrada de dados: ⟪E43⟫. No estudo de caso, a ração excedente custa ⟪S13⟫ por ano, a mortalidade evitável ⟪S14⟫ e a energia excedente ⟪S15⟫, totalizando ⟪S16⟫, ou ⟪S17⟫ do custo operacional. [INTERPRETAR: indicar o desperdício predominante e a ação de manejo que o reduziria.] Esse resultado traduz em valor monetário a identificação sistemática de desperdícios defendida por Lawrence et al. (2023).")]

    b += [H2("Resultados da dimensão econômica", "economica"),
          P("A função calcular_economico() (⟦Código:economico⟧) transforma a produção técnica em uma projeção mensal com três características principais. Primeiro, a receita só ocorre após a primeira despesca (no estudo de caso, ⟪S20⟫), enquanto ração, alevinos e energia são desembolsados durante a engorda; ao final do horizonte, o estoque em engorda é recuperado pelo seu custo, junto com o valor residual e o capital de giro. Segundo, a depreciação compõe a base dos tributos sobre o resultado e é somada de volta no fluxo de caixa operacional. Terceiro, o modelo inclui a perspectiva do beneficiário, na qual parte do CAPEX é aportada por fomento não reembolsável, situação típica de projetos financiados por condicionantes do licenciamento ambiental federal (IBAMA, 2010, 2012).")]
    b += COD("economico", "Projeção econômica mensal, DRE e indicadores financeiros (trecho)", COD_ECONOMICO)
    b += [P("As entradas econômicas foram informadas nos blocos 4 a 9 do wizard (⟦Figura:tela_economica1⟧ e ⟦Figura:tela_economica2⟧): CAPEX de ⟪E16⟫, estimado como ⟪E17⟫ da AACE International (2020), capital de giro de ⟪E18⟫, fomento não reembolsável de ⟪E19⟫ do CAPEX, preço médio de venda de ⟪E20⟫ por kg, ração a ⟪E21⟫ por kg, alevinos a ⟪E22⟫ por unidade, energia a ⟪E23⟫ por kWh, remuneração mensal da equipe de ⟪E24⟫ (⟪E25⟫), TMA de ⟪E26⟫, horizonte de ⟪E27⟫ anos e ⟪E28⟫.")]
    b += PRINT("tela_economica1", "Entradas de investimento, receitas e custos operacionais (blocos 4 a 6 do wizard)", "P05", FONTE_WIZ)
    b += PRINT("tela_economica2", "Entradas de pessoas, tributos, rampa, projeção e TMA (blocos 7 a 9 do wizard)", "P06", FONTE_WIZ)
    b += [P("A DRE mensal produz Receita Bruta, Impostos sobre Faturamento, Receita Líquida, Custos Variáveis, Lucro Bruto, Custos Fixos, EBITDA, Depreciação, LAIR, Impostos sobre Lucro e Resultado Líquido. O vetor de fluxo de caixa é então utilizado para calcular VPL, TIR, payback simples e descontado, índice de lucratividade, ponto de equilíbrio, margem de segurança e ROI. A TIR é obtida por varredura de malha seguida de bisseção vetorizada e retorna sempre um diagnóstico (convencional, múltiplas, múltiplas possíveis ou sem solução), de modo que a ausência de raiz nunca é confundida com o limite numérico do algoritmo (⟦Código:tir⟧). A ⟦Tabela:economica⟧ apresenta os resultados.")]
    b += TAB("Tabela", "economica", "Indicadores econômicos do estudo de caso", tabela_economica(), [4300, 2100, 2100])
    b += [P("Na perspectiva do projeto, com investimento total de ⟪S21⟫, o VPL foi ⟪S23⟫ e a TIR, ⟪S24⟫, para uma TMA de ⟪E26⟫. [INTERPRETAR: o VPL é positivo? A TIR supera a TMA? Classificar o projeto como viável, marginal ou inviável no cenário determinístico.] Em valor presente, o investimento é recuperado em ⟪S25⟫, para um horizonte de ⟪E27⟫ anos, e o índice de lucratividade é de ⟪S27⟫. [INTERPRETAR: avaliar a folga do payback em relação ao horizonte e o que o índice de lucratividade indica sobre a robustez do retorno.] Em regime, a margem de segurança foi de ⟪S33⟫. [INTERPRETAR: se positiva, a margem indica quanto as vendas podem cair até o resultado operacional se anular; se negativa, indica o aumento de vendas necessário para atingir o ponto de equilíbrio; se o ponto de equilíbrio não for definido, a margem é registrada como −100%, e nenhum aumento de vendas torna o resultado operacional positivo.]"),
          P("Na perspectiva do beneficiário, com ⟪E19⟫ do CAPEX aportado como fomento não reembolsável, o VPL foi de ⟪S37⟫; a TIR, ⟪S38⟫; e o investimento do beneficiário é recuperado, em valor presente, em ⟪S39⟫. O resultado líquido no ano de regime foi de ⟪S30⟫. [INTERPRETAR: comparar as perspectivas do projeto e do beneficiário e o que a diferença representa para o público atendido. Se não houver fomento, excluir este parágrafo e a coluna do beneficiário da ⟦Tabela:economica⟧.] A distinção entre as perspectivas é relevante para o órgão fomentador: o recurso não reembolsável não altera a eficiência econômica do projeto, mas pode viabilizar a geração de renda para o público beneficiário."),
          P("O custo total de produção foi de ⟪S34⟫ por kg, e o custo operacional efetivo, de ⟪S35⟫ por kg; a ração respondeu por ⟪S36⟫ dos custos operacionais. [INTERPRETAR: comparar o custo por kg com o preço de venda e indicar o principal item de custo.] O diagnóstico de viabilidade depende não apenas da produção, mas da relação entre capacidade, preço, custos e investimento. A ⟦Figura:economica⟧ apresenta a evolução da receita, dos custos e do fluxo de caixa acumulado.")]
    b += PRINT("economica", "Receita, custos operacionais e fluxo de caixa acumulado", "P07")

    b += [H2("Resultados da dimensão ambiental", "ambiental"),
          P("A função calcular_ambiental() utiliza a produção e o consumo de ração para estimar água, nutrientes, energia, emissões e resíduos. A pegada hídrica azul segue a definição de Hoekstra (2017): água consumida, isto é, evaporada ou devolvida a outra bacia, e não toda a água captada. A água captada (enchimento, renovação e reposição de perdas) alimenta o Índice de Uso de Água previsto na Seção 2.8.6."),
          P("A pegada hídrica cinza é calculada a partir de um balanço de nutrientes (⟦Código:ambiental⟧). O nitrogênio e o fósforo aportados pela ração, descontados os retidos na biomassa e os removidos pelo tratamento de efluentes, constituem a carga lançada; o volume de diluição é calculado pela diferença entre a concentração máxima da classe do corpo receptor (Brasil, 2005) e a concentração natural, e o poluente que exige maior volume define a pegada. A ecoeficiência segue o WBCSD (2000): valor adicionado (receita menos insumos externos) por unidade de impacto. Quando o valor adicionado não é positivo, o indicador é declarado não definido, o que distingue essa situação de uma ecoeficiência igual a zero.")]
    b += COD("ambiental", "Balanço de nutrientes, pegada hídrica cinza e ecoeficiência (trecho)", COD_AMBIENTAL)
    b += [P("As entradas ambientais foram informadas nos blocos 10 a 12 do wizard (⟦Figura:tela_ambiental⟧). Entre elas, destacam-se os limites de nitrogênio e de fósforo do corpo receptor (⟪E31⟫), a eficiência de remoção no tratamento de efluentes (⟪E32⟫), a fonte de energia (⟪E33⟫) e as respostas ao checklist de conformidade.")]
    b += PRINT("tela_ambiental", "Entradas da dimensão ambiental (blocos 10 a 12 do wizard)", "P08", FONTE_WIZ)
    b += [P("A água captada foi de ⟪S41⟫ m³/ano, com Índice de Uso de Água de ⟪S42⟫ kg/m³. A pegada hídrica azul foi de ⟪S43⟫ m³/t, e a cinza, de ⟪S44⟫ m³/t, tendo o ⟪S45⟫ como poluente crítico. No balanço anual de nutrientes, o nitrogênio teve ⟪S46⟫; e o fósforo, ⟪S47⟫. [INTERPRETAR: explicar o que define o poluente crítico e a sensibilidade da pegada cinza à classe do corpo receptor e à eficiência de remoção, à luz da lógica Lean Green de tratar o efluente como ineficiência de processo.]"),
          P("As emissões estimadas foram de ⟪S50⟫ tCO2e/ano, sendo ⟪S51⟫, o que corresponde a ⟪S53⟫ kgCO2e por kg de peixe; a ração respondeu por ⟪S52⟫ das emissões. [INTERPRETAR: indicar a fonte dominante e se a prioridade de mitigação está no FCR ou na matriz elétrica.] Quanto à ecoeficiência, o resultado foi: ⟪S54⟫. O Score de Conformidade Ambiental, calculado sobre um checklist normativo ponderado (licença ambiental da aquicultura, outorga, APP, tratamento de efluentes, monitoramento, CAR, gestão de resíduos, prevenção de escape e energia renovável), foi de ⟪S55⟫ de 10. Itens não atendidos: ⟪S56⟫. Itens eliminatórios não atendidos: ⟪S57⟫. A ⟦Tabela:ambiental_social⟧ reúne esses indicadores e os das dimensões social e de governança, discutidos na seção seguinte.")]
    b += TAB("Tabela", "ambiental_social", "Indicadores ambientais, sociais e de governança do estudo de caso", tabela_ambiental_social(), [1600, 3700, 3200])

    b += [H2("Resultados da dimensão social e ESG", "social"),
          P("O módulo social (⟦Código:social⟧) transforma emprego, renda local, compras locais e relacionamento com stakeholders em indicadores comparáveis. A Retenção de Valor Local (RVL) segue a fórmula do Quadro 5: despesas com mão de obra e fornecedores locais divididas pelo custo operacional total, de modo que numerador e denominador estejam na mesma base de custos. O Índice de Impacto Local estima a proporção da receita que retorna à economia local como renda (massa salarial local e sobras distribuídas)."),
          P("A Licença Social para Operar (LSO) é um índice de 0 a 100 composto por cinco componentes: relação com a comunidade (inexistente, parcial ou consolidada), existência de canais formais de comunicação, frequência de engajamento, ausência de conflitos e participação da comunidade na governança (Hurst; Ihlen, 2018). O Score de Risco Social converte o déficit de LSO em uma escala de 0 a 1 por função logística; trata-se de heurística explícita, a ser calibrada com os especialistas, e não de probabilidade estimada estatisticamente.")]
    b += COD("social", "Cálculo da dimensão social, RVL e LSO (trecho)", COD_SOCIAL)
    b += [P("As entradas sociais e de governança foram informadas nos blocos 13 e 14 do wizard (⟦Figura:tela_social⟧).")]
    b += PRINT("tela_social", "Entradas da dimensão social e de governança (blocos 13 e 14 do wizard)", "P09", FONTE_WIZ)
    b += [P("Com ⟪E34⟫, ⟪E35⟫ de mão de obra local e ⟪E36⟫ de compras locais, a RVL foi de ⟪S60⟫ e o Índice de Impacto Local, de ⟪S61⟫. A renda média mensal por trabalhador foi de ⟪S40⟫, o equivalente a ⟪S62⟫ salários mínimos. A LSO foi de ⟪S63⟫, com relação ⟪E37⟫ com a comunidade, ⟪E38⟫ por ano e risco social de ⟪S64⟫. Os componentes da LSO, na escala de 0 a 1, foram: ⟪S59⟫. [INTERPRETAR: indicar os componentes que mais reduziram a LSO e o que o nível de renda representa para o público beneficiário.] O Radar Social (⟦Figura:radar⟧) obteve média de ⟪S65⟫, com menores valores nos eixos ⟪S66⟫."),
          P("O alinhamento aos Objetivos de Desenvolvimento Sustentável é identificado automaticamente por regras explícitas e auditáveis. No estudo de caso, os ODS atendidos foram ⟪S67⟫; os não atendidos, ⟪S68⟫. [INTERPRETAR: explicar, pelas regras do artefato, por que os ODS não atendidos não foram alcançados.] O pilar de governança, avaliado por checklist de sete itens (estatuto, assembleias, conselho fiscal, prestação de contas pública, plano de negócios, registro auditável das premissas e canal de denúncia), obteve ⟪S69⟫. Os scores dos pilares ESG foram: ⟪S70⟫.")]
    b += PRINT("radar", "Radar Social do estudo de caso", "P10")

    b += [H2("Índice integrado EVTEAS", "indice"),
          P("O índice integrado usa uma etapa explícita de normalização para transformar KPIs com escalas e sentidos diferentes em valores de 0 a 1. Cada KPI recebe um sentido (benefício ou custo) e uma faixa de referência declarada, que fica disponível para auditoria e pode ser revisada pelos especialistas. O ⟦Quadro:normalizacao⟧ apresenta as referências, os valores brutos e os valores normalizados do estudo de caso. Os scores dimensionais são médias ponderadas dos KPIs de cada dimensão, e o índice EVTEAS é a média ponderada das quatro dimensões.")]
    b += TAB("Quadro", "normalizacao", "Normalização dos KPIs do estudo de caso", quadro_normalizacao(), [1200, 2300, 1100, 1700, 1100, 1100])
    b += [P("Os pesos das dimensões e as regras de decisão foram informados no bloco 15 do wizard (⟦Figura:tela_pesos⟧).")]
    b += PRINT("tela_pesos", "Pesos do índice e regras de decisão (bloco 15 do wizard)", "P11", FONTE_WIZ)
    b += [P("O método de ponderação e os pesos das dimensões foram: ⟪E39⟫. Com esses pesos, os scores dimensionais foram ⟪S71⟫, e o índice EVTEAS foi de ⟪S72⟫ (⟦Figura:dimensoes⟧). Os KPIs de pior desempenho relativo foram ⟪S73⟫. [INTERPRETAR: indicar onde esses KPIs apontam a necessidade de ajustes de projeto.]")]
    b += PRINT("dimensoes", "Scores dimensionais e índice EVTEAS do estudo de caso", "P12")
    b += [P("A regra de decisão (⟦Código:decisao⟧) tem dois estágios, para evitar que o índice compensatório oculte fragilidades. No primeiro estágio, vetos não compensatórios impedem a classificação “VIÁVEL” quando o VPL do projeto é negativo, quando um item ambiental eliminatório não é atendido ou quando a LSO está abaixo do mínimo estabelecido. No segundo, o índice é comparado aos limiares de viabilidade e de viabilidade com ressalvas, e a probabilidade de VPL positivo obtida no Monte Carlo é confrontada com um mínimo. No estudo de caso, as regras informadas foram: ⟪E40⟫. [INTERPRETAR: se os vetos foram desativados, justificar a escolha e excluir a descrição do primeiro estágio.] Essa estrutura responde à crítica da “eficiência obscena” de Garnett, Röös e Little (2015): bom desempenho econômico não compensa violação ambiental ou social.")]
    b += COD("decisao", "Regra de decisão com vetos não compensatórios", COD_DECISAO)
    b += [P("O estudo de caso foi classificado como “⟪S74⟫” (⟦Figura:classificacao⟧). Vetos e ressalvas registrados: ⟪S75⟫. [INTERPRETAR: explicar a classificação a partir dos vetos, do índice e da probabilidade de VPL positivo.] Os limiares do índice e a probabilidade mínima são regras operacionais do artefato e devem ser tratados como parâmetros de decisão, não como padrões universais de mercado ou de engenharia."),
          P("Quando os pesos são obtidos pela escala Likert prevista na Seção 3.4, o artefato registra os pesos normalizados e a concordância entre os avaliadores; na execução do estudo de caso, esse registro foi: ⟪S102⟫. [INTERPRETAR: se a ponderação foi feita por escala Likert, comentar os pesos e a concordância; caso contrário, excluir este parágrafo.] Os escores efetivos dos especialistas serão incorporados na Fase 3 da pesquisa, e a divergência por critério será registrada como evidência da triangulação.")]
    b += PRINT("classificacao", "Classificação e resumo executivo do estudo de caso", "P13")

    b += [H2("Simulação de Monte Carlo", "mc"),
          P("A camada de incerteza (⟦Código:mc⟧) utiliza Monte Carlo sobre o mesmo motor vetorizado do modelo determinístico. As distribuições foram informadas no bloco 16 do wizard (⟦Figura:tela_incerteza⟧) e são apresentadas no ⟦Quadro:distribuicoes⟧. A distribuição triangular é recomendada quando há valor mais provável (Oliveira; Medeiros Neto, 2012). Quando o usuário não informa uma distribuição própria para o CAPEX, sua incerteza deriva da classe da estimativa (⟪E17⟫), segundo a AACE International (2020); para a Classe 5, o artefato adota de −30% a +50%, dentro da faixa indicada para essa classe. As amostras são geradas com np.random.default_rng(seed), em ordem fixa de variáveis, o que garante reprodutibilidade.")]
    b += PRINT("tela_incerteza", "Distribuições de incerteza informadas (bloco 16 do wizard)", "P14", FONTE_WIZ)
    b += TAB("Quadro", "distribuicoes", "Distribuições de incerteza do estudo de caso", tabela_distribuicoes(), [3300, 5200], FONTE_RES)
    b += COD("mc", "Simulação de Monte Carlo sobre o motor único (trecho)", COD_MC)
    b += TAB("Tabela", "mc", "Estatísticas da simulação de Monte Carlo", tabela_mc(), [4300, 4200])
    b += [P("A ⟦Tabela:mc⟧ e a ⟦Figura:vpl⟧ apresentam os resultados. O VPL calculado no valor mais provável das premissas foi de ⟪S23⟫, enquanto a média do VPL simulado foi de ⟪S80⟫ e a probabilidade de VPL positivo, de ⟪S84⟫. [INTERPRETAR: comparar o VPL determinístico com a média simulada e relacionar a diferença à forma das distribuições do ⟦Quadro:distribuicoes⟧.] Quando as distribuições têm caudas mais longas no lado desfavorável, a média de cada premissa é pior que o seu valor mais provável; nesse caso, um estudo de viabilidade baseado apenas no cenário mais provável, como os elaborados em planilhas, tende a superestimar a viabilidade do projeto."),
          P("A convergência foi verificada pela média acumulada e pelo erro-padrão (⟦Figura:convergencia⟧). Com ⟪E41⟫ iterações, o erro-padrão da média do VPL foi de ⟪S89⟫. [INTERPRETAR: avaliar se o número de iterações é suficiente para a precisão requerida.] Na perspectiva do beneficiário, o VPL simulado teve ⟪S88⟫. [INTERPRETAR: avaliar em que medida o fomento reduz o risco do beneficiário.]")]
    b += PRINT("vpl", "Distribuição e função de probabilidade acumulada do VPL", "P15")
    b += PRINT("convergencia", "Convergência da média do VPL com intervalo de confiança de 95%", "P16")

    b += [H2("Análise de sensibilidade e identificação das variáveis críticas", "sensibilidade"),
          P("A identificação das variáveis críticas combina quatro procedimentos complementares. A sensibilidade de um fator por vez varia cada premissa em ±10% e ±20% (±0,1 e ±0,2 em valor absoluto quando o valor informado é nulo), mantendo as demais no valor informado. Os valores críticos são obtidos por bisseção e indicam o valor de cada variável que anula o VPL. A correlação de postos de Spearman entre as entradas amostradas e o VPL mede a importância de cada variável sob variação simultânea. Por fim, os cenários pessimista e otimista combinam os extremos desfavoráveis e favoráveis das distribuições.")]
    b += COD("tir", "TIR com diagnóstico e valores críticos das premissas", COD_TIR + "\n\n\n" + COD_CRITICOS)
    b += [P("A ⟦Figura:sensibilidade⟧ reúne a variação do VPL com ±10% em cada premissa, o valor crítico de cada uma, com a folga em relação ao valor informado, e a correlação de Spearman obtida no Monte Carlo. A variável de maior impacto foi ⟪S90⟫ (⟦Figura:tornado⟧): as variações de −10% e de +10% alteraram o VPL em ⟪S91⟫, respectivamente; ⟪S93⟫. As três variáveis de maior impacto foram ⟪S92⟫, e as maiores correlações de Spearman com o VPL foram as de ⟪S94⟫. Como FCR e custo da ração entram no modelo como produto no custo da ração, variações percentuais iguais nessas duas premissas têm o mesmo efeito sobre o VPL. [INTERPRETAR: verificar se a ordem de importância no Monte Carlo confirma a sensibilidade determinística e indicar onde concentrar a coleta de dados de mercado e o controle zootécnico.]"),
          P("Os cenários delimitam a faixa de resultados: o pessimista resultou em ⟪S95⟫; o otimista, em ⟪S96⟫. [INTERPRETAR: avaliar a amplitude entre os cenários, a proximidade do projeto ao limiar de viabilidade e as ações de mitigação de risco cabíveis, como contratos de venda que estabilizem o preço e manejo alimentar que reduza o FCR.]")]
    b += PRINT("sensibilidade", "Sensibilidade, valores críticos e importância das variáveis", "P17")
    b += PRINT("tornado", "Diagrama de tornado da sensibilidade do VPL a ±10%", "P18")
    b += [P("Para examinar trade-offs entre dimensões, o projeto e as alternativas ⟪S97⟫ foram comparados por TOPSIS (⟦Figura:topsis_tabela⟧ e ⟦Figura:topsis⟧), com sete critérios: VPL, probabilidade de VPL positivo, OEE, pegada hídrica cinza, intensidade de carbono, LSO e RVL. Cada alternativa parte das entradas do estudo de caso, com alteração dos blocos do wizard escolhidos pelo usuário, e o Monte Carlo de todas usa o mesmo número de iterações da análise principal. [PREENCHER: descrever cada alternativa e os blocos de entrada alterados em relação ao projeto.] [INTERPRETAR: se a comparação não for realizada, excluir este parágrafo, o seguinte e as duas figuras correspondentes.]")]
    b += PRINT("topsis_tabela", "Comparação das alternativas de projeto por TOPSIS", "P19")
    b += [P("A alternativa melhor classificada foi ⟪S98⟫, e apresentou ⟪S99⟫. [INTERPRETAR: indicar o que se ganha e o que se perde em cada dimensão em cada alternativa e se alguma combinação de soluções seria preferível.] Em vez de declarar uma alternativa ótima, o framework explicita o que se ganha e o que se perde em cada dimensão e permite combinar soluções.")]
    b += PRINT("topsis", "Proximidade relativa à solução ideal das alternativas de projeto", "P20")

    b += [H2("Verificação computacional e avaliação do artefato (Etapa 8)", "vv"),
          P("A verificação foi conduzida em duas camadas. A função validar_invariantes() (⟦Código:vv⟧) executa um conjunto de verificações a cada execução: limites de OEE, índices e scores; identidade OEE = disponibilidade × performance × qualidade; ração = FCR × ganho de biomassa; quatro identidades da DRE; fluxo de caixa operacional = resultado + depreciação; recálculo independente do VPL; VPL nulo na TIR; coerência entre paybacks; balanços de nitrogênio e fósforo; soma unitária dos pesos; coerência do status da ecoeficiência; domínio das distribuições; e consistência estatística do Monte Carlo. Na execução do estudo de caso, o resultado foi de ⟪S100⟫."),
          P(f"A segunda camada é uma suíte de {TESTES['testes']} testes automatizados (pytest), executada fora do pipeline. Os testes comparam VPL e TIR com a biblioteca numpy-financial, verificam casos com solução analítica conhecida (inclusive fluxos sem TIR e com duas TIR), conferem o cálculo manual da pegada hídrica cinza, os vetos, a normalização, os pesos Likert e AHP, o TOPSIS, a reprodutibilidade por seed e a exportação. Um teste central verifica que, com distribuições degeneradas na moda, o Monte Carlo reproduz exatamente o resultado determinístico. Outro grupo testa a entrada de dados com um usuário simulado: quando esse usuário digita no wizard, no modo “novo projeto”, as premissas do caso ilustrativo incorporado ao pacote, o artefato reproduz exatamente o VPL e a amostra de Monte Carlo da configuração de referência; o modo de revisão, com Enter em todas as perguntas, preserva os resultados; e entradas inválidas são recusadas com mensagem ao usuário. Há ainda testes que conferem se cada lacuna do texto deste capítulo corresponde a um valor produzido pela execução, e vice-versa. A cobertura de código medida foi de {n(TESTES['cobertura_pct'], 0)}% das instruções, métrica de testabilidade prevista na Seção 3.4.")]
    b += COD("vv", "Verificação por invariantes (trecho)", COD_VV)
    verificados = int((m_dsr["Situação"] == "implementado e verificado").sum())
    b += [P(f"A rastreabilidade entre requisitos, código e testes é conferida pela função matriz_rastreabilidade(), que verifica no código-fonte se cada função vinculada a um requisito existe e, nos arquivos de teste, se cada teste citado está definido (⟦Quadro:rastreabilidade⟧). {('Todos os ' + str(len(m_dsr))) if verificados == len(m_dsr) else (str(verificados) + ' dos ' + str(len(m_dsr)))} requisitos encontram-se na situação “implementado e verificado”; os requisitos R07 (dimensão social, governança e ODS) e R08 (Lean-Green) contam com testes dedicados à fórmula da RVL, à composição da LSO e do risco social, ao checklist de governança, às regras dos ODS e ao custo dos desperdícios. A própria matriz é verificada por teste, de modo que um requisito cuja função ou teste deixe de existir volta a aparecer como pendente.")]
    b += TAB("Quadro", "rastreabilidade", "Matriz de rastreabilidade entre requisitos, código e testes", quadro_rastreabilidade(),
             [1100, 4600, 800, 2000], "Fonte: elaboração própria (2026), a partir da função matriz_rastreabilidade() do EVTEAS-Py.")
    b += [P(_revisao_independente())]
    b += [P("É importante manter a distinção entre verificação e validação. A verificação demonstra aderência do código às regras codificadas; a validação busca demonstrar que o artefato é adequado ao problema real. Para a segunda, continuam necessárias a avaliação pelos dois especialistas, cujos escores Likert já têm destino definido no código, e a comparação com dados de empreendimentos reais, conforme delimitado no Capítulo 3.")]

    b += [H2("Explicitação das aprendizagens (Etapa 9)", "aprendizagens"),
          P("A Etapa 9 exige registrar o que a construção ensinou, e não apenas o artefato final. As aprendizagens foram registradas no módulo dsr, cada uma com a dificuldade observada, a causa identificada, a decisão de projeto que dela resultou e o teste que impede que o problema volte a ocorrer (⟦Quadro:aprendizagens⟧).")]
    b += TAB("Quadro", "aprendizagens", "Aprendizagens explicitadas na construção do EVTEAS-Py", quadro_aprendizagens(),
             [500, 2700, 2600, 2700], "Fonte: elaboração própria (2026), a partir do registro de aprendizagens do EVTEAS-Py.")
    b += [P("Três lições têm alcance além do caso. A primeira é que a coerência entre camadas de análise deve ser garantida pela arquitetura, e não pela atenção do desenvolvedor: se o Monte Carlo usa um modelo distinto do determinístico, as duas camadas podem divergir sem que nenhum cálculo isolado esteja errado. A segunda é que um artefato de apoio à decisão não deve ter valores padrão silenciosos: se resultados são produzidos antes das entradas, o caso ilustrativo pode ser tomado pelo projeto do usuário. A terceira é que requisitos explícitos e rastreáveis revelam lacunas que uma execução bem-sucedida esconde, como rotinas implementadas e não utilizadas ou funções sem teste, que só aparecem quando cada requisito é ligado ao código e aos testes. Essas lições fundamentam os princípios de projeto formulados na ⟦Seção:generalizacao⟧.")]

    b += [H2("Exportação, reprodutibilidade e documentação dos resultados", "exportacao"),
          P("O framework produz um resumo executivo, um workbook Excel, um arquivo JSON, um relatório em Markdown e até nove figuras (o gráfico do TOPSIS depende da comparação de alternativas). O workbook reúne 23 abas, entre elas premissas com origem, curva de crescimento, DRE mensal e anual, fluxo de caixa, indicadores ambientais, checklist de conformidade, indicadores sociais, ODS, desperdícios Lean-Green, KPIs normalizados, amostra e estatísticas do Monte Carlo, convergência, importância das variáveis, sensibilidade, valores críticos, cenários e o registro da verificação. Somado ao arquivo de entradas salvo ao final do wizard, esse material estabelece uma trilha entre premissas, cálculo e resultados auditáveis."),
          P("Para que o relato dos resultados permaneça atrelado às entradas, o módulo campos_texto registra cada valor citado nos Capítulos 4 e 5 com um código e uma descrição. Ao final da análise, o notebook exibe a tabela “Valores para o texto”, com o valor de cada código na execução do usuário e a origem declarada de cada entrada, e a exporta para a planilha valores_para_o_texto.xlsx, que traz também o roteiro de prints; o wizard e o notebook identificam, pelo código do print, cada tela e cada saída reproduzida nas figuras. A função que gera esses valores recusa um resultado calculado com entradas diferentes das atuais, o que impede que o texto misture entradas de uma execução com resultados de outra. Desse modo, uma nova execução com outras entradas produz o conjunto completo de valores e figuras necessário para atualizar o relato, sem que números de uma execução anterior permaneçam no texto (requisito R16)."),
          P("A reprodução do estudo depende do código-fonte, do arquivo de entradas, da seed e do número de iterações. A análise do estudo de caso (cálculo determinístico, Monte Carlo com ⟪E41⟫ iterações, sensibilidade e verificação) foi executada em ⟪S101⟫. [PREENCHER: ambiente de execução, por exemplo Google Colab com a configuração padrão.] O código e os testes estão registrados no repositório do projeto, e o notebook autocontido pode ser executado no Google Colab sem instalação do pacote; nele, a pasta de saídas, com planilhas, relatório e figuras, é compactada e baixada ao final. O notebook traz ainda uma seção opcional que exibe o registro da DSR (etapas, comparação com artefatos, matriz de rastreabilidade e aprendizagens), o que torna o percurso metodológico consultável junto com os resultados.")]

    b += [H2("Discussão integrada e retorno à lacuna científica", "discussao"),
          P("A principal evidência desta aplicação é que o EVTEAS-Py não atua apenas como uma coleção de fórmulas. O fluxo integrado conduz as entradas da parametrização ao desempenho técnico, deste à projeção econômica, às métricas ambientais e sociais e, por fim, ao índice síntese, à regra de decisão e às análises de risco. Dessa forma, a proposta materializa computacionalmente a integração que a revisão de literatura identificou como lacuna instrumental (Calabrese et al., 2019; Silva Araújo; Keesman; Goddek, 2021)."),
          P("No estudo de caso, o módulo técnico produziu OEE de ⟪S08⟫; o social, LSO de ⟪S63⟫ e renda de ⟪S62⟫ salários mínimos por trabalhador; e o econômico, VPL de ⟪S23⟫, com probabilidade de VPL positivo de ⟪S84⟫. [INTERPRETAR: indicar se os resultados das dimensões convergem ou conflitam e como o índice e os vetos tratam esse conflito.] O framework não mascara a fragilidade de uma dimensão em razão de bons resultados em outras; ao contrário, torna o conflito entre dimensões visível, o que corresponde à metáfora do painel de instrumentos de Kaplan e Norton (1992)."),
          P("A camada probabilística permite confrontar o diagnóstico determinístico com o risco: no estudo de caso, a probabilidade de o projeto destruir valor foi de ⟪S85⟫. [INTERPRETAR: avaliar em que medida esse resultado altera a leitura do VPL determinístico.] Ao indicar as variáveis críticas, a folga de cada uma e o papel do fomento na redução do risco do beneficiário, a análise transforma um diagnóstico estático em informação de decisão. Para pequenos produtores e para o público beneficiário de projetos de fomento, essa informação é mais útil do que um único VPL, porque orienta onde negociar contratos de venda, onde investir em manejo e em que medida o aporte não reembolsável reduz o risco do beneficiário."),
          P("No modelo, a ração conecta a eficiência operacional ao desempenho ambiental: reduzir o FCR melhora simultaneamente o VPL, a pegada de carbono e a pegada hídrica cinza, em linha com Mesquita et al. (2022) e Kosasih, Pujawan e Karningsih (2023). [INTERPRETAR: dimensionar esse efeito no estudo de caso com os desperdícios Lean-Green e a participação da ração nas emissões apresentados nas Seções ⟦n:tecnica⟧ e ⟦n:ambiental⟧.] A regra de vetos, por sua vez, impede a compensação entre dimensões que Wang et al. (2025) associam aos excessos da busca por eficiência."),
          P("Em termos de Design Science Research, a evidência obtida sustenta a existência de um artefato funcional, verificável e reprodutível em nível computacional. A validade externa, porém, permanece limitada, porque a aplicação se restringe a um estudo de caso, as faixas de normalização foram parametrizadas pelo desenvolvedor e a avaliação dos especialistas ainda não foi concluída. A generalização deve, portanto, ser formulada em termos de princípios de projeto, arquitetura e procedimento de avaliação, e não como validade universal dos parâmetros utilizados.")]
    b += COD("pipeline", "Pipeline principal reproduzível do EVTEAS-Py", COD_PIPELINE)
    b += [P("O pipeline principal (⟦Código:pipeline⟧) é a evidência mais direta da integração: ele valida o tipo da configuração, resolve os pesos, executa o motor das quatro dimensões, monta a DRE, a curva de crescimento, os ODS e a tabela de premissas, habilita Monte Carlo, sensibilidade, valores críticos e cenários quando solicitado, aplica a regra de decisão e, ao final, registra a verificação e o tempo de execução. A ordem das chamadas reproduz a dependência lógica dos resultados e fornece um ponto único de entrada para execução reprodutível.")]

    # ------------------------------------------------------------------ Capítulo 5
    b += [H1("5 CONSIDERAÇÕES FINAIS"),
          P("A pesquisa teve como problema a necessidade de estruturar um EVTEAS computacional que integrasse dimensões técnica, econômica, ambiental e social e ainda oferecesse mecanismos de tratamento da incerteza e apoio à decisão. O EVTEAS-Py materializa essa proposta em um pacote Python com motor único vetorizado, entradas interativas e por arquivo, rastreabilidade das premissas, índice integrado com regra de decisão não compensatória, Monte Carlo, sensibilidade, comparação de alternativas, verificação automatizada e exportação. A aplicação ao estudo de caso demonstra o funcionamento do artefato e evidencia como os módulos produzem um diagnóstico integrado."),
          P("Em termos do ciclo da Design Science Research, este capítulo corresponde às três últimas etapas: a conclusão (Etapa 10), nas Seções ⟦n:sintese⟧ a ⟦n:limitacoes⟧; a generalização para a classe de problemas (Etapa 11), na ⟦Seção:generalizacao⟧; e a comunicação dos resultados (Etapa 12), na ⟦Seção:comunicacao⟧. Como a validação com especialistas ainda não foi realizada, as conclusões referem-se à primeira iteração do ciclo e serão revistas após essa validação."),
          H2("Síntese da resposta ao problema de pesquisa", "sintese"),
          P("A resposta ao problema é afirmativa quanto à viabilidade de estruturar, em Python, uma cadeia integrada de processamento para EVTEAS aplicado à piscicultura. O artefato reúne os dados em uma configuração central, propaga resultados entre módulos com o mesmo código nas camadas determinística e estocástica e conserva uma trilha de verificação. A conclusão, porém, deve ser qualificada: a pesquisa demonstra viabilidade computacional e metodológica do framework, mas ainda não demonstra validade universal para empreendimentos reais."),
          P("Quanto à hipótese, a análise do estudo de caso foi executada em ⟪S101⟫ a partir de um único arquivo de premissas, e uma nova execução com outras entradas regenera todos os resultados e os valores do relato. [INTERPRETAR: avaliar, à luz do tempo medido e do tempo gasto no preenchimento do wizard, o indício que a aplicação oferece a favor da hipótese de que a automação reduz o tempo de elaboração e de revisão de cenários em relação ao fluxo manual em planilhas e documentos.] A confirmação quantitativa desse ganho depende de comparação controlada com o processo tradicional, prevista como trabalho futuro."),
          H2("Atendimento ao objetivo geral e aos objetivos específicos", "objetivos"),
          P("O objetivo geral foi atendido no nível de desenvolvimento do artefato: as dimensões técnica, econômica, ambiental e social estão integradas no mesmo fluxo e podem ser submetidas a Monte Carlo, sensibilidade e verificação. O primeiro objetivo específico foi atendido com a operacionalização dos oito KPIs do Quadro 5 e de indicadores complementares (pegada hídrica cinza, intensidade de carbono, conformidade, Radar Social, ODS e governança). O segundo foi atendido com o desenvolvimento do pacote e a explicitação de trade-offs por índice, vetos e TOPSIS. O terceiro, a validação com especialistas, permanece como etapa necessária; o código já recebe os escores Likert e registra a divergência entre avaliadores. O quarto foi atendido com a aplicação do framework ao estudo de caso. [INTERPRETAR: indicar se o atendimento é integral ou parcial, conforme os dados sejam do empreendimento ou estimativas.]"),
          P("No estudo de caso, foram obtidos OEE de ⟪S08⟫, produção anual de ⟪S05⟫ kg, VPL determinístico de ⟪S23⟫, probabilidade de VPL positivo de ⟪S84⟫ e índice EVTEAS de ⟪S72⟫, com classificação “⟪S74⟫”. [INTERPRETAR: sintetizar o diagnóstico do estudo de caso.] Esses resultados mostram que o framework produz um diagnóstico integrado; sua validade como retrato do empreendimento depende, contudo, da qualidade das entradas e da validação com especialistas."),
          H2("Contribuições científicas, metodológicas e aplicadas", "contribuicoes"),
          P("A contribuição científica está na proposição de um artefato e de uma arquitetura de integração para uma classe delimitada de problemas de viabilidade aquícola. A contribuição metodológica está na combinação de Design Science Research, modelagem computacional, análise qualiquantitativa, verificação automatizada, simulação e sensibilidade, com a regra de que o mesmo motor sirva às camadas determinística e estocástica. A contribuição computacional está na consolidação das entradas, no registro da origem das premissas, no processamento modular e na exportação estruturada. A contribuição gerencial consiste em tornar explícitos trade-offs entre desempenho técnico, retorno econômico, impacto ambiental e dimensão social, e em separar a perspectiva do projeto da perspectiva do beneficiário de fomento."),
          P("[INTERPRETAR: contribuição que emerge da aplicação ao estudo de caso, por exemplo a diferença entre o VPL determinístico e a média simulada, as variáveis críticas identificadas ou o poluente crítico da pegada hídrica cinza.] O valor do artefato, nesse sentido, não está apenas em calcular, mas em tornar visíveis premissas e resultados que demandam revisão."),
          H2("Limitações da pesquisa e do artefato", "limitacoes"),
          P("A primeira limitação é a dependência da qualidade das entradas. A segunda é a delimitação da pesquisa à piscicultura e a um único estudo de caso. [PREENCHER: indicar se as entradas do estudo de caso são dados do empreendimento ou estimativas.] A terceira é a ausência, até o momento, de validação independente por especialistas e de confronto sistemático com dados observados de empreendimentos reais."),
          P("Há ainda limitações na própria modelagem. As faixas de normalização, a heurística logística do risco social e os pesos dos componentes da LSO foram definidos pelo autor e precisam de calibração. O crescimento segue taxa específica constante, sem efeito da temperatura e da sazonalidade. Os tributos sobre o resultado são aproximados mensalmente. Os fatores de emissão da ração e da energia são parâmetros bibliográficos que devem ser atualizados ao ano-base de cada estudo. As variáveis do Monte Carlo são amostradas de forma independente, sem correlação entre elas, como entre preço da ração e preço do pescado."),
          H2("Generalização para a classe de problemas (Etapa 11)", "generalizacao"),
          P("A generalização mais defensável é arquitetural e metodológica. É transferível a lógica de organizar requisitos, entradas com origem declarada, processamento vetorizado, indicadores normalizados, regra de decisão não compensatória, incerteza, verificação e exportação em um único artefato. Parâmetros zootécnicos, econômicos, ambientais e sociais devem, contudo, ser recalibrados para cada novo contexto, espécie, sistema produtivo ou território."),
          P("Na forma de regras tecnológicas, no sentido atribuído pela Design Science Research (Dresch; Lacerda; Antunes Jr., 2015), a primeira iteração permite formular os seguintes princípios de projeto para artefatos da classe de problemas definida na Etapa 4, cada um associado à evidência que o sustenta neste trabalho:"),
          B("para que as análises determinística e estocástica sejam coerentes, usar um único motor de cálculo vetorizado, no qual o cenário determinístico seja a simulação com uma única amostra (Seções ⟦n:design⟧ e ⟦n:mc⟧);"),
          B("para que o resultado represente o projeto do usuário, começar pela entrada de dados, sem valores padrão silenciosos, e registrar a origem de cada premissa (⟦Seção:interface⟧);"),
          B("para que bons resultados em uma dimensão não ocultem falhas em outra, combinar o índice compensatório com vetos não compensatórios (⟦Seção:indice⟧);"),
          B("para que a decisão considere o risco, e não apenas o cenário mais provável, informar a probabilidade de VPL positivo e os valores críticos das premissas (Seções ⟦n:mc⟧ e ⟦n:sensibilidade⟧);"),
          B("para que o artefato continue correto ao evoluir, ligar cada requisito às funções que o implementam e aos testes que o verificam, e conferir essa ligação automaticamente (⟦Seção:vv⟧)."),
          P("Para aplicar esses princípios a outras cadeias agroindustriais, substituem-se os modelos técnico e ambiental pelos da nova cadeia e mantêm-se a configuração com origem declarada, o motor vetorizado, a normalização, a regra de decisão, a camada de incerteza e a verificação."),
          H2("Comunicação dos resultados (Etapa 12)", "comunicacao"),
          P("A comunicação dos resultados foi tratada como parte do artefato. Para o público acadêmico, esta dissertação apresenta o percurso e os resultados, e os Apêndices A e B reproduzem o código-fonte e os testes do EVTEAS-Py. Para reprodução e auditoria, o código, os testes e os scripts que geram os Capítulos 4 e 5 estão registrados no repositório do projeto, e o arquivo de entradas do estudo de caso acompanha a dissertação; os valores citados nos Capítulos 4 e 5 foram transcritos da planilha valores_para_o_texto.xlsx, gerada pelo notebook na execução do estudo, que associa cada valor ao trecho do texto em que ele aparece. Para os profissionais do setor, o notebook autocontido orienta a execução no Google Colab, do preenchimento das entradas à exportação de planilhas, relatórios e figuras. Estão previstos, ainda, artigos científicos derivados e um manual de uso voltado a técnicos de extensão e cooperativas, a serem elaborados após a validação com especialistas."),
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

"""Campos do texto da dissertação preenchidos com a execução do usuário.

O relato dos resultados (Capítulo 4) traz lacunas identificadas por código, como
``[E14 – FCR]`` ou ``[S23 – VPL do projeto]``. Este módulo é o registro único desses
códigos: o gerador do texto lê daqui a descrição de cada lacuna, e o notebook usa a
mesma lista para mostrar, ao final da análise, o valor de cada código na execução
feita pelo usuário (``valores_para_o_texto``). Assim, texto e resultados ficam
atrelados às entradas informadas, e não a uma simulação prévia.

Prefixos: E = entrada informada no wizard; S = saída (resultado) da análise; K = valor bruto
de um KPI; N = valor normalizado de um KPI. (O prefixo R fica reservado aos requisitos do módulo dsr.)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from .config import CATEGORIAS_FONTE, KPIS_POR_DIMENSAO, EVTEASConfig


# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------

def _f(v) -> float:
    if isinstance(v, (list, tuple, np.ndarray)):
        v = np.asarray(v).ravel()[0]
    return float(v)


def num(v, casas: int = 2) -> str:
    try:
        x = _f(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(x):
        return "não definido"
    s = f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.replace("-", "−")


def reais(v, casas: int = 0) -> str:
    x = _f(v)
    if not math.isfinite(x):
        return "não definido"
    return ("−" if x < 0 else "") + "R$ " + num(abs(x), casas)


def pct_br(v, casas: int = 1) -> str:
    x = _f(v)
    return "não definido" if not math.isfinite(x) else num(x * 100, casas) + "%"


def lista(itens) -> str:
    itens = [str(i) for i in itens]
    if not itens:
        return "nenhum"
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


# ---------------------------------------------------------------------------
# Registro dos campos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Campo:
    codigo: str
    secao: str                       # seção do texto em que o campo aparece
    descricao: str                   # rótulo curto exibido na lacuna do texto
    valor: Callable[[EVTEASConfig, Dict[str, Any], Optional[Dict[str, Any]]], str]
    caminhos: tuple = ()             # parâmetros cuja origem declarada acompanha o valor (entradas)

    @property
    def lacuna(self) -> str:
        return f"[{self.codigo} – {self.descricao}]"


SEC_ESTUDO, SEC_PREMISSAS, SEC_TEC = "Estudo de caso", "Premissas", "Dimensão técnica"
SEC_ECO, SEC_AMB, SEC_SOC = "Dimensão econômica", "Dimensão ambiental", "Dimensão social e ESG"
SEC_IND, SEC_MC, SEC_SENS = "Índice integrado e decisão", "Monte Carlo", "Sensibilidade e alternativas"
SEC_VV = "Verificação e execução"

NOMES_ORGANIZACAO = {"empresa": "empresa", "coop_trabalho": "cooperativa de trabalho", "coop_agro": "cooperativa agropecuária"}
NOMES_ENERGIA = {"rede": "rede pública", "solar": "solar fotovoltaica", "biomassa": "biomassa", "mista": "mista (rede + renovável)"}
NOMES_RELACAO = {"inexistente": "inexistente", "parcial": "parcial", "consolidado": "consolidada"}
NOMES_METODO = {"preset": "pesos informados diretamente", "likert": "escala Likert", "ahp": "AHP"}
NOMES_RESTRICAO = {"capacidade_suporte": "capacidade de suporte", "produtividade_area": "produtividade por área"}
NOMES_DIM = {"tecnico": "técnica", "economico": "econômica", "ambiental": "ambiental", "social": "social"}
DIAGNOSTICO_TIR = {"convencional": "fluxo convencional", "multiplas": "múltiplas TIR",
                   "multiplas_possiveis": "possíveis múltiplas TIR", "sem_solucao": "sem solução"}
ROTULO_KPI = {"oee": "OEE", "fcr": "FCR", "produtividade": "Produtividade relativa", "vpl": "VPL/investimento",
              "roi": "ROI anual", "margem_seguranca": "Margem de segurança", "ph_azul": "PH azul (m³/t)",
              "ph_cinza": "PH cinza (m³/t)", "ecoeficiencia": "Ecoeficiência (R$/kgCO2e)",
              "intensidade_carbono": "Intensidade de carbono", "conformidade": "Conformidade (0–10)",
              "lso": "LSO (0–100)", "rvl": "RVL (%)", "radar_social": "Radar Social"}
PROSA_KPI = {"oee": "OEE", "fcr": "FCR", "produtividade": "produtividade relativa", "vpl": "VPL por investimento",
             "roi": "ROI anual", "margem_seguranca": "margem de segurança", "ph_azul": "pegada hídrica azul",
             "ph_cinza": "pegada hídrica cinza", "ecoeficiencia": "ecoeficiência",
             "intensidade_carbono": "intensidade de carbono", "conformidade": "conformidade ambiental",
             "lso": "LSO", "rvl": "RVL", "radar_social": "Radar Social"}
VARIAVEIS_DIST = [  # caminho, nome (tabelas), escala de exibição, casas, nome em prosa, unidade
    ("economico.preco_venda_kg", "Preço de venda (R$/kg)", 1.0, 2, "preço de venda", "R$/kg"),
    ("economico.custo_racao_kg", "Custo da ração (R$/kg)", 1.0, 2, "custo da ração", "R$/kg"),
    ("economico.custo_alevino_milheiro", "Custo do alevino (R$/un)", 1 / 1000, 3, "custo do alevino", "R$/un"),
    ("economico.tarifa_energia_kwh", "Tarifa de energia (R$/kWh)", 1.0, 2, "tarifa de energia", "R$/kWh"),
    ("economico.custos_fixos_fator", "Fator dos custos fixos", 1.0, 2, "custos fixos", "(fator multiplicativo)"),
    ("tecnico.fcr", "FCR", 1.0, 2, "FCR", ""),
    ("tecnico.mortalidade_pct", "Mortalidade (%)", 1.0, 1, "mortalidade", "%"),
    ("tecnico.desempenho_crescimento_pct", "Desempenho de crescimento (%)", 1.0, 1, "desempenho de crescimento", "%"),
    ("economico.capex_fator", "Fator do CAPEX", 1.0, 2, "CAPEX", "(fator multiplicativo)"),
]
_VAR = {v[0]: v for v in VARIAVEIS_DIST}
PRINT_DO_BLOCO = {2: "P03", 4: "P05", 7: "P06", 10: "P08", 13: "P09", 15: "P11", 16: "P14"}


def lista_itens(itens) -> str:
    """Itens de checklist entre aspas, com inicial minúscula, separados por ponto e vírgula."""
    itens = [f"“{i[:1].lower() + i[1:]}”" for i in itens]
    if not itens:
        return "nenhum"
    return itens[0] if len(itens) == 1 else "; ".join(itens[:-1]) + "; e " + itens[-1]


def plural(n, singular, plural_, nenhum="nenhum"):
    n = int(round(_f(n)))
    return f"{nenhum if n == 0 else n} {singular if n in (0, 1) else plural_}"


def meses_ou_horizonte(v) -> str:
    x = _f(v)
    return f"{num(x, 1)} meses" if math.isfinite(x) else "prazo superior ao horizonte de análise"


def tir_txt(v, diagnostico=None) -> str:
    x = _f(v)
    base = f"{num(100 * x, 1)}% a.a." if math.isfinite(x) else "não definida"
    return f"{base} ({DIAGNOSTICO_TIR.get(diagnostico, diagnostico)})" if diagnostico else base


def _remuneracao(cfg):
    from .modelo import remuneracao_mensal
    r = remuneracao_mensal(cfg)
    return reais(r["clt"] + r["retirada"] + r["outros"])


def _aliquota(cfg, bases):
    from .modelo import aliquotas_configuradas
    aq = aliquotas_configuradas(cfg)
    return num(100 * sum(aq[b] for b in bases), 2) + "%"


def _encargos(cfg):
    from .modelo import aliquotas_configuradas
    aq = aliquotas_configuradas(cfg)
    partes = [(aq["folha_clt"], "sobre a folha CLT"), (aq["pro_labore"], "sobre a retirada dos cooperados"),
              (aq["folha"], "de encargos sobre a mão de obra informada em valor global"), (aq["servicos"], "sobre os serviços")]
    textos = [f"{num(100 * a, 2)}% {onde}" for a, onde in partes if a > 0]
    return lista(textos) if textos else "nenhuma"


def _distribuicao(cfg, r, caminho, escala, casas):
    from .incerteza import distribuicoes_efetivas
    d = distribuicoes_efetivas(cfg).get(caminho)
    if d is None:
        return "sem incerteza (valor fixo)"
    t = d.tipo.lower()
    if t == "fixa":
        return f"fixa em {num(d.moda * escala, casas)}"
    if t == "normal":
        texto = (f"normal (média {num(d.moda * escala, casas)}; truncada entre {num(d.minimo * escala, casas)} e "
                 f"{num(d.maximo * escala, casas)})")
    else:
        mais_provavel = "" if t == "uniforme" else f"; mais provável {num(d.moda * escala, casas)}"
        texto = f"{t} (mínimo {num(d.minimo * escala, casas)}{mais_provavel}; máximo {num(d.maximo * escala, casas)})"
    if caminho == "economico.capex_fator" and caminho not in cfg.monte_carlo.distribuicoes:
        texto += f", derivada da faixa da Classe {int(cfg.economico.classe_estimativa_aace)} da AACE"
    return texto


def _mc(r):
    if "monte_carlo" not in r:
        raise KeyError("execute a análise com Monte Carlo (executar_mc=True)")
    return r["monte_carlo"]["estatisticas"]


def _sens10(r):
    s = r["sensibilidade"]
    return s[np.isclose(s["Amplitude"], s["Amplitude"].min())].reset_index(drop=True)


def _rotulo_var(caminho):
    return _VAR[caminho][1] if caminho in _VAR else ("TMA (% a.a.)" if caminho.endswith("tma_aa_pct") else caminho)


def _prosa_var(caminho):
    return _VAR[caminho][4] if caminho in _VAR else ("TMA" if caminho.endswith("tma_aa_pct") else caminho)


def _alternativas(cfg, comp):
    """Nomes das alternativas comparadas, sem o próprio projeto (que entra na matriz como referência)."""
    return [a for a in comp["matriz"]["Alternativa"] if a not in (cfg.projeto, "Projeto informado")]


def _topsis(comp, f):
    if not comp:
        return "comparação não realizada"
    return f(comp["ranking"])


def _e(codigo, descricao, valor, *caminhos, secao=SEC_PREMISSAS):
    return Campo(codigo, secao, descricao, lambda cfg, r, c: valor(cfg), tuple(caminhos))


def _r(codigo, secao, descricao, valor):
    return Campo(codigo, secao, descricao, lambda cfg, r, c: valor(r))


def _arquivo(cfg):
    from .interface import nome_arquivo
    return nome_arquivo(cfg)


def _n_mc(cfg, r):
    """Iterações e seed efetivamente usadas na execução (ou as configuradas, se não houve Monte Carlo)."""
    st = r.get("monte_carlo", {}).get("estatisticas", {}) if isinstance(r, dict) else {}
    return int(st.get("n", cfg.monte_carlo.iteracoes)), int(st.get("seed", cfg.monte_carlo.seed))


def _rampa(c):
    e = c.economico
    if e.capacidade_inicial_pct >= 100:
        return "operação a 100% da capacidade desde o início, sem rampa"
    return f"rampa de capacidade de {num(e.capacidade_inicial_pct, 0)}% a 100% em {plural(e.meses_rampa, 'mês', 'meses')}"


def _decisao(c):
    d = c.decisao
    vetos = "vetos não compensatórios aplicados" if d.aplicar_vetos else "vetos não compensatórios desativados"
    return (f"{vetos}; índice EVTEAS ≥ {num(d.limiar_indice_viavel, 2)} para “viável” e ≥ "
            f"{num(d.limiar_indice_ressalvas, 2)} para “viável com ressalvas”; P(VPL > 0) mínima de "
            f"{pct_br(d.prob_vpl_positivo_minima, 0)}; LSO mínima de {num(d.lso_minimo, 0)}")


def _alevinos(c):
    a = c.tecnico.alevinos_por_ciclo
    return "dimensionado pelo modelo" if not a or a <= 0 else f"informado pelo usuário ({num(a, 0)} por ciclo)"


CAMPOS: List[Campo] = [
    # ---------------------------------------------------------------- estudo de caso e entradas
    _e("E00", "arquivo de entradas", lambda c: _arquivo(c), secao=SEC_ESTUDO),
    _e("E01", "nome do projeto", lambda c: c.projeto, secao=SEC_ESTUDO),
    _e("E02", "tipo de organização", lambda c: NOMES_ORGANIZACAO.get(c.economico.tipo_organizacao, c.economico.tipo_organizacao), secao=SEC_ESTUDO),
    _e("E03", "espécie", lambda c: c.tecnico.especie, "tecnico.especie", secao=SEC_ESTUDO),
    _e("E04", "sistema produtivo", lambda c: c.tecnico.sistema_produtivo, secao=SEC_ESTUDO),
    _e("E05", "área de lâmina d'água (m²)", lambda c: num(c.tecnico.area_lamina_m2, 0), "tecnico.area_lamina_m2"),
    _e("E06", "profundidade média (m)", lambda c: num(c.tecnico.profundidade_media_m, 2), "tecnico.profundidade_media_m"),
    _e("E07", "viveiros/tanques no total", lambda c: num(c.tecnico.numero_tanques, 0), "tecnico.numero_tanques"),
    _e("E08", "viveiros/tanques ativos", lambda c: num(c.tecnico.tanques_ativos, 0), "tecnico.tanques_ativos"),
    _e("E09", "produtividade esperada (kg/m²/ciclo)", lambda c: num(c.tecnico.produtividade_esperada_kg_m2_ciclo, 2),
       "tecnico.produtividade_esperada_kg_m2_ciclo"),
    _e("E10", "peso inicial (g)", lambda c: num(c.tecnico.peso_inicial_g, 1), "tecnico.peso_inicial_g"),
    _e("E11", "peso final (g)", lambda c: num(c.tecnico.peso_final_g, 0), "tecnico.peso_final_g"),
    _e("E12", "duração do ciclo (dias)", lambda c: num(c.tecnico.ciclo_dias, 0), "tecnico.ciclo_dias"),
    _e("E13", "ciclos por ano", lambda c: num(c.tecnico.ciclos_ano, 2), "tecnico.ciclos_ano"),
    _e("E14", "FCR", lambda c: num(c.tecnico.fcr, 2), "tecnico.fcr"),
    _e("E15", "mortalidade esperada (%)", lambda c: num(c.tecnico.mortalidade_pct, 1) + "%", "tecnico.mortalidade_pct"),
    _e("E44", "número de alevinos por ciclo", _alevinos, "tecnico.alevinos_por_ciclo"),
    _e("E16", "CAPEX total", lambda c: reais(c.economico.capex_total), "economico.capex_itens"),
    _e("E17", "classe AACE da estimativa", lambda c: f"Classe {c.economico.classe_estimativa_aace}", "economico.classe_estimativa_aace"),
    _e("E18", "capital de giro", lambda c: reais(c.economico.capital_giro), "economico.capital_giro"),
    _e("E19", "fomento não reembolsável (% do CAPEX)", lambda c: num(c.economico.fomento_nao_reembolsavel_pct, 1) + "%",
       "economico.fomento_nao_reembolsavel_pct"),
    _e("E20", "preço médio de venda (R$/kg)", lambda c: reais(c.economico.preco_venda_kg, 2), "economico.mix_produtos", "economico.preco_venda_kg"),
    _e("E21", "custo da ração (R$/kg)", lambda c: reais(c.economico.custo_racao_kg, 2), "economico.custo_racao_kg"),
    _e("E22", "custo do alevino (R$/un)", lambda c: reais(c.economico.custo_alevino_milheiro / 1000, 3), "economico.custo_alevino_milheiro"),
    _e("E23", "tarifa de energia (R$/kWh)", lambda c: reais(c.economico.tarifa_energia_kwh, 2), "economico.tarifa_energia_kwh"),
    _e("E24", "remuneração mensal da equipe (R$/mês)", _remuneracao, "economico.salarios_clt_por_cargo",
       "economico.retirada_cooperados_mes", "economico.mao_obra_mes"),
    _e("E25", "cooperados na operação", lambda c: plural(c.economico.cooperados_trabalhadores, "cooperado na operação",
                                                         "cooperados na operação"), "economico.cooperados_trabalhadores"),
    _e("E26", "TMA (% a.a.)", lambda c: num(c.economico.tma_aa_pct, 1) + "% a.a.", "economico.tma_aa_pct"),
    _e("E27", "horizonte (anos)", lambda c: num(c.economico.horizonte_anos, 0), "economico.horizonte_anos"),
    _e("E28", "rampa de capacidade", _rampa, "economico.capacidade_inicial_pct", "economico.meses_rampa"),
    _e("E29", "alíquota sobre o faturamento", lambda c: _aliquota(c, ("faturamento", "produtos")), "economico.impostos_configurados"),
    _e("E30", "alíquota sobre o lucro", lambda c: _aliquota(c, ("lucro",)), "economico.impostos_configurados"),
    _e("E45", "alíquotas sobre a folha, a retirada dos cooperados e os serviços", _encargos,
       "economico.impostos_configurados", "economico.encargos_mao_obra_pct"),
    _e("E31", "limites de N e P do corpo receptor", lambda c: f"{num(c.ambiental.n_max_mg_l, 2)} mg/L de N e "
                                                             f"{num(c.ambiental.p_max_mg_l, 2)} mg/L de P", "ambiental.n_max_mg_l", "ambiental.p_max_mg_l"),
    _e("E32", "remoção de N e P no tratamento", lambda c: f"{num(c.ambiental.remocao_n_tratamento_pct, 0)}% do N e "
                                                       f"{num(c.ambiental.remocao_p_tratamento_pct, 0)}% do P",
       "ambiental.remocao_n_tratamento_pct", "ambiental.remocao_p_tratamento_pct"),
    _e("E33", "fonte de energia", lambda c: NOMES_ENERGIA.get(c.ambiental.fonte_energia, c.ambiental.fonte_energia)),
    _e("E34", "empregos diretos e indiretos", lambda c: f"{plural(c.social.empregos_diretos, 'emprego direto', 'empregos diretos')} "
                                                       f"e {plural(c.social.empregos_indiretos, 'indireto', 'indiretos')}",
       "social.empregos_diretos", "social.empregos_indiretos"),
    _e("E35", "mão de obra local (%)", lambda c: num(c.social.mao_obra_local_pct, 0) + "%", "social.mao_obra_local_pct"),
    _e("E36", "compras locais (%)", lambda c: num(c.social.compras_locais_pct, 0) + "%", "social.compras_locais_pct"),
    _e("E37", "relação com a comunidade", lambda c: NOMES_RELACAO.get(c.social.relacao_comunidade, c.social.relacao_comunidade)),
    _e("E38", "reuniões e conflitos por ano", lambda c: f"{plural(c.social.reunioes_comunidade_ano, 'reunião', 'reuniões', nenhum='nenhuma')} e "
                                                     f"{plural(c.social.conflitos_registrados_ano, 'conflito registrado', 'conflitos registrados')}",
       "social.reunioes_comunidade_ano", "social.conflitos_registrados_ano"),
    _e("E39", "método e pesos das dimensões", lambda c: _pesos_texto(c)),
    _e("E40", "regras de decisão", _decisao),
    Campo("E41", SEC_MC, "iterações do Monte Carlo", lambda cfg, r, c: num(_n_mc(cfg, r)[0], 0)),
    Campo("E42", SEC_MC, "seed", lambda cfg, r, c: str(_n_mc(cfg, r)[1])),
    _e("E43", "referências Lean-Green", lambda c: f"FCR de {num(c.tecnico.fcr_referencia, 2)}, mortalidade de "
                                                   f"{num(c.tecnico.mortalidade_referencia_pct, 1)}% e consumo de energia de "
                                                   f"{num(c.ambiental.energia_referencia_kwh_kg, 2)} kWh/kg",
       "tecnico.fcr_referencia", "tecnico.mortalidade_referencia_pct", "ambiental.energia_referencia_kwh_kg", secao=SEC_TEC),
]
CAMPOS += [Campo(f"E{50 + i}", SEC_MC, f"distribuição — {nome}",
                 (lambda cam, esc, cas: lambda cfg, r, c: _distribuicao(cfg, r, cam, esc, cas))(cam, esc, cas))
           for i, (cam, nome, esc, cas, _, _) in enumerate(VARIAVEIS_DIST)]


def _pesos_texto(c):
    from .ponderacao import resolver_pesos
    w = resolver_pesos(c)["dimensoes"]
    return (f"{NOMES_METODO.get(c.pesos.metodo, c.pesos.metodo)}, com " +
            lista([f"{NOMES_DIM[d]} {num(w[d], 3)}" for d in ("tecnico", "economico", "ambiental", "social")]))


def _balanco(r, nutriente):
    a = r[Am]
    return (f"{num(a[f'{nutriente}_aportado_kg'], 0)} kg aportados pela ração, {num(a[f'{nutriente}_retido_kg'], 0)} kg "
            f"retidos na biomassa e {num(a[f'{nutriente}_lancado_kg'], 0)} kg lançados após o tratamento")


def _piores_kpis(r):
    norm = {k: _f(v) for k, v in r["indice"]["kpis_normalizados"].items()}
    ordem = sorted(norm, key=lambda k: norm[k])
    corte = norm[ordem[min(1, len(ordem) - 1)]]
    return lista([PROSA_KPI[k] for k in ordem if norm[k] <= corte + 1e-12])


T, Ec, Am, So = "tecnico", "economico", "ambiental", "social"
CAMPOS += [
    # ---------------------------------------------------------------- técnica e Lean-Green
    _r("S01", SEC_TEC, "restrição de biomassa ativa", lambda r: NOMES_RESTRICAO.get(r[T]["restricao_biomassa"], str(r[T]["restricao_biomassa"]))),
    _r("S02", SEC_TEC, "alevinos estocados por ciclo", lambda r: num(r[T]["alevinos_ciclo"], 0)),
    _r("S03", SEC_TEC, "densidade de estocagem (peixes/m³)", lambda r: num(r[T]["densidade_estocagem_peixes_m3"], 2)),
    _r("S04", SEC_TEC, "biomassa despescada por ciclo (kg)", lambda r: num(r[T]["biomassa_despesca_ciclo_kg"], 0)),
    _r("S05", SEC_TEC, "produção anual (kg/ano)", lambda r: num(r[T]["producao_kg_ano"], 0)),
    _r("S06", SEC_TEC, "produtividade (kg/m²/ano)", lambda r: num(r[T]["produtividade_kg_m2_ano"], 2)),
    _r("S07", SEC_TEC, "produtividade relativa ao potencial", lambda r: pct_br(r[T]["produtividade_relativa"])),
    _r("S08", SEC_TEC, "OEE", lambda r: num(r[T]["oee"], 3)),
    _r("S09", SEC_TEC, "disponibilidade", lambda r: num(r[T]["disponibilidade"], 3)),
    _r("S10", SEC_TEC, "performance", lambda r: num(r[T]["performance"], 3)),
    _r("S11", SEC_TEC, "sobrevivência (qualidade)", lambda r: num(r[T]["sobrevivencia"], 3)),
    _r("S12", SEC_TEC, "ração consumida (kg/ano)", lambda r: num(r[T]["racao_ano_kg"], 0)),
    _r("S13", SEC_TEC, "desperdício de ração (R$/ano)", lambda r: reais(r["lean_green"]["desperdicios_r_ano"]["Ração excedente (superalimentação/FCR)"])),
    _r("S14", SEC_TEC, "mortalidade evitável (R$/ano)", lambda r: reais(r["lean_green"]["desperdicios_r_ano"]["Mortalidade evitável"])),
    _r("S15", SEC_TEC, "energia excedente (R$/ano)", lambda r: reais(r["lean_green"]["desperdicios_r_ano"]["Energia excedente"])),
    _r("S16", SEC_TEC, "desperdícios evitáveis (R$/ano)", lambda r: reais(r["lean_green"]["total_r_ano"])),
    _r("S17", SEC_TEC, "desperdícios / custo operacional", lambda r: pct_br(r["lean_green"]["pct_opex"])),
    # ---------------------------------------------------------------- econômica
    _r("S20", SEC_ECO, "prazo até a primeira receita",
       lambda r: (lambda m: "a receita ocorre desde o primeiro mês" if m == 0 else
                  f"{plural(m, 'mês', 'meses')} até a primeira receita")(int(_f(r[Ec]["meses_ate_despesca"])))),
    _r("S21", SEC_ECO, "investimento total", lambda r: reais(r[Ec]["investimento_total"])),
    _r("S22", SEC_ECO, "investimento do beneficiário", lambda r: reais(_f(r[Ec]["investimento_total"]) - _f(r[Ec]["fomento_nao_reembolsavel"]))),
    _r("S23", SEC_ECO, "VPL do projeto", lambda r: reais(r[Ec]["vpl"])),
    _r("S24", SEC_ECO, "TIR anual do projeto (diagnóstico)", lambda r: tir_txt(r[Ec]["tir_anual"], r[Ec]["diagnostico_tir"])),
    _r("S25", SEC_ECO, "payback descontado", lambda r: meses_ou_horizonte(r[Ec]["payback_descontado_meses"])),
    _r("S26", SEC_ECO, "payback simples", lambda r: meses_ou_horizonte(r[Ec]["payback_simples_meses"])),
    _r("S27", SEC_ECO, "índice de lucratividade", lambda r: num(r[Ec]["indice_lucratividade"], 3)),
    _r("S28", SEC_ECO, "ano de regime", lambda r: num(r[Ec]["ano_regime"], 0)),
    _r("S29", SEC_ECO, "receita bruta no ano de regime", lambda r: reais(r[Ec]["receita_regime"])),
    _r("S30", SEC_ECO, "resultado líquido no ano de regime", lambda r: reais(r[Ec]["lucro_liquido_regime"])),
    _r("S31", SEC_ECO, "ROI anual em regime", lambda r: pct_br(r[Ec]["roi_anual_regime"])),
    _r("S32", SEC_ECO, "ponto de equilíbrio (kg/ano)", lambda r: num(r[Ec]["ponto_equilibrio_kg_ano"], 0)),
    _r("S33", SEC_ECO, "margem de segurança", lambda r: pct_br(r[Ec]["margem_seguranca"])),
    _r("S34", SEC_ECO, "custo total (R$/kg)", lambda r: reais(r[Ec]["custo_total_kg"], 2)),
    _r("S35", SEC_ECO, "custo operacional efetivo (R$/kg)", lambda r: reais(r[Ec]["custo_operacional_efetivo_kg"], 2)),
    _r("S36", SEC_ECO, "participação da ração nos custos operacionais",
       lambda r: pct_br(_f(r[Ec]["custo_racao_regime"]) / (_f(r[Ec]["custos_variaveis_regime"]) + _f(r[Ec]["custos_fixos_regime"])))),
    _r("S37", SEC_ECO, "VPL do beneficiário", lambda r: reais(r[Ec]["vpl_beneficiario"])),
    _r("S38", SEC_ECO, "TIR anual do beneficiário", lambda r: tir_txt(r[Ec]["tir_anual_beneficiario"])),
    _r("S39", SEC_ECO, "payback descontado do beneficiário", lambda r: meses_ou_horizonte(r[Ec]["payback_descontado_beneficiario_meses"])),
    _r("S40", SEC_ECO, "renda mensal por trabalhador", lambda r: reais(r[So]["renda_mensal_trabalhador"])),
    # ---------------------------------------------------------------- ambiental
    _r("S41", SEC_AMB, "água captada (m³/ano)", lambda r: num(r[Am]["agua_captada_m3_ano"], 0)),
    _r("S42", SEC_AMB, "índice de uso da água (kg/m³)", lambda r: num(r[Am]["indice_uso_agua_kg_m3"], 3)),
    _r("S43", SEC_AMB, "pegada hídrica azul (m³/t)", lambda r: num(r[Am]["ph_azul_m3_t"], 0)),
    _r("S44", SEC_AMB, "pegada hídrica cinza (m³/t)", lambda r: num(r[Am]["ph_cinza_m3_t"], 0)),
    _r("S45", SEC_AMB, "poluente crítico", lambda r: str(r[Am]["poluente_critico"])),
    _r("S46", SEC_AMB, "balanço do nitrogênio (kg/ano)", lambda r: _balanco(r, "n")),
    _r("S47", SEC_AMB, "balanço do fósforo (kg/ano)", lambda r: _balanco(r, "p")),
    _r("S50", SEC_AMB, "emissões totais (tCO2e/ano)", lambda r: num(r[Am]["co2e_total_t_ano"], 1)),
    _r("S51", SEC_AMB, "emissões por fonte",
       lambda r: f"{num(r[Am]['co2e_racao_t'], 1)} tCO2e/ano da ração, {num(r[Am]['co2e_energia_t'], 1)} tCO2e/ano da energia "
                 f"e {num(r[Am]['co2e_diesel_t'], 1)} tCO2e/ano do diesel"),
    _r("S52", SEC_AMB, "participação da ração nas emissões", lambda r: pct_br(_f(r[Am]["co2e_racao_t"]) / _f(r[Am]["co2e_total_t_ano"]))),
    _r("S53", SEC_AMB, "intensidade de carbono (kgCO2e/kg)", lambda r: num(r[Am]["intensidade_carbono_kgco2e_kg"], 2)),
    _r("S54", SEC_AMB, "ecoeficiência",
       lambda r: (reais(r[Am]["ecoeficiencia_r_por_kgco2e"], 2) + " de valor adicionado por kgCO2e"
                  if r[Am]["ecoeficiencia_status"] == "definida" else "não definida (valor adicionado não positivo)")),
    _r("S55", SEC_AMB, "score de conformidade ambiental (0–10)", lambda r: num(r[Am]["conformidade_0_10"], 2)),
    _r("S56", SEC_AMB, "itens do checklist não atendidos",
       lambda r: lista_itens(d["Item"] for d in r[Am]["conformidade_detalhe"] if not d["Atendido"])),
    _r("S57", SEC_AMB, "itens eliminatórios não atendidos", lambda r: lista_itens(r[Am]["vetos_ambientais"])),
    # ---------------------------------------------------------------- social e ESG
    _r("S60", SEC_SOC, "RVL (% do custo operacional)", lambda r: num(r[So]["rvl_pct"], 1) + "%"),
    _r("S61", SEC_SOC, "índice de impacto local", lambda r: pct_br(r[So]["indice_impacto_local"])),
    _r("S62", SEC_SOC, "renda em salários mínimos", lambda r: num(r[So]["renda_em_salarios_minimos"], 2)),
    _r("S63", SEC_SOC, "LSO (0–100)", lambda r: num(r[So]["lso_0_100"], 1)),
    _r("S59", SEC_SOC, "componentes da LSO (0–1)",
       lambda r: lista([f"{k[:1].lower() + k[1:]} {num(v, 2)}" for k, v in r[So]["lso_componentes"].items()])),
    _r("S64", SEC_SOC, "score de risco social", lambda r: num(r[So]["risco_social"], 3)),
    _r("S65", SEC_SOC, "Radar Social (média dos eixos)", lambda r: num(r[So]["radar_social_score"], 3)),
    _r("S66", SEC_SOC, "eixos do Radar com menores valores",
       lambda r: lista([k[:1].lower() + k[1:] for k, _ in sorted(r[So]["radar_social"].items(), key=lambda kv: _f(kv[1]))[:2]])),
    _r("S67", SEC_SOC, "ODS atendidos", lambda r: lista(o.split(" — ")[0] for o in r["ods"].loc[r["ods"]["Atendido"], "ODS"])),
    _r("S68", SEC_SOC, "ODS não atendidos", lambda r: lista(o.split(" — ")[0] for o in r["ods"].loc[~r["ods"]["Atendido"], "ODS"])),
    _r("S69", SEC_SOC, "itens de governança atendidos",
       lambda r: f"{sum(bool(v) for v in r['governanca']['itens'].values())} de {len(r['governanca']['itens'])} itens "
                 f"atendidos (score {num(r['governanca']['score_0_1'], 3)})"),
    _r("S70", SEC_SOC, "scores ESG",
       lambda r: f"ambiental {num(r['indice']['esg']['E'], 3)}, social {num(r['indice']['esg']['S'], 3)} e governança "
                 f"{num(r['indice']['esg']['G'], 3)}, com score ESG (média) de {num(r['indice']['esg_score'], 3)}"),
    # ---------------------------------------------------------------- índice e decisão
    _r("S71", SEC_IND, "scores dimensionais",
       lambda r: lista([f"{NOMES_DIM[d]} {num(r['indice']['dimensoes'][d], 3)}" for d in ("tecnico", "economico", "ambiental", "social")])),
    _r("S72", SEC_IND, "índice EVTEAS", lambda r: num(r["indice"]["indice_evteas"], 3)),
    _r("S73", SEC_IND, "KPIs de pior desempenho relativo", _piores_kpis),
    _r("S74", SEC_IND, "classificação", lambda r: r["decisao"]["classificacao"]),
    _r("S75", SEC_IND, "vetos e ressalvas",
       lambda r: "; ".join(list(r["decisao"]["vetos"]) + list(r["decisao"]["ressalvas"])) or "nenhum"),
    # ---------------------------------------------------------------- Monte Carlo
    _r("S80", SEC_MC, "média do VPL simulado (IC 95% da média)",
       lambda r: f"{reais(_mc(r)['media_vpl'])} (IC 95% da média: {reais(_mc(r)['ic95_media_vpl'][0])} a "
                 f"{reais(_mc(r)['ic95_media_vpl'][1])})"),
    _r("S81", SEC_MC, "mediana; desvio-padrão; CV do VPL",
       lambda r: f"{reais(_mc(r)['mediana_vpl'])}; {reais(_mc(r)['desvio_vpl'])}; {num(_mc(r)['cv_vpl'], 2)}"),
    _r("S82", SEC_MC, "VPL P5 / P50 / P95",
       lambda r: " / ".join(reais(_mc(r)["percentis_vpl"][p]) for p in ("p5", "p50", "p95"))),
    _r("S83", SEC_MC, "VaR 5% e CVaR 5% do VPL", lambda r: f"{reais(_mc(r)['var5_vpl'])} e {reais(_mc(r)['cvar5_vpl'])}"),
    _r("S84", SEC_MC, "P(VPL > 0)", lambda r: pct_br(_mc(r)["prob_vpl_positivo"])),
    _r("S85", SEC_MC, "probabilidade de VPL negativo", lambda r: pct_br(1 - _f(_mc(r)["prob_vpl_positivo"]))),
    _r("S86", SEC_MC, "TIR anual P5 / P50 / P95", lambda r: " / ".join(pct_br(_mc(r)["percentis_tir"][p]) for p in ("p5", "p50", "p95"))),
    _r("S87", SEC_MC, "índice médio; P(índice ≥ limiar)",
       lambda r: f"{num(_mc(r)['media_indice'], 3)}; {pct_br(_mc(r)['prob_indice_maior_limiar'])}"),
    _r("S88", SEC_MC, "VPL do beneficiário: média e P(VPL > 0)",
       lambda r: f"média de {reais(_mc(r)['media_vpl_beneficiario'])} e P(VPL > 0) de {pct_br(_mc(r)['prob_vpl_beneficiario_positivo'])}"),
    _r("S89", SEC_MC, "erro-padrão da média do VPL e precisão relativa", lambda r: _precisao(r)),
    # ---------------------------------------------------------------- sensibilidade, cenários e alternativas
    _r("S90", SEC_SENS, "variável de maior impacto no VPL (±10%)", lambda r: _prosa_var(_sens10(r).iloc[0]["Variável"])),
    _r("S91", SEC_SENS, "variação do VPL com −10% e +10% na variável de maior impacto",
       lambda r: f"{reais(_sens10(r).iloc[0]['Δ VPL (−)'])} e {reais(_sens10(r).iloc[0]['Δ VPL (+)'])}"),
    _r("S92", SEC_SENS, "três variáveis de maior impacto", lambda r: lista(_prosa_var(v) for v in _sens10(r)["Variável"][:3])),
    _r("S93", SEC_SENS, "valor que anula o VPL na variável de maior impacto", lambda r: _critico_frase(r, _sens10(r).iloc[0]["Variável"])),
    _r("S94", SEC_SENS, "correlação de Spearman das três variáveis mais importantes",
       lambda r: lista(f"{_prosa_var(x['Variável'])} (ρ = {num(x['Spearman com VPL'], 3)})"
                       for _, x in r["monte_carlo"]["importancia"].head(3).iterrows())),
    _r("S95", SEC_SENS, "cenário pessimista: VPL e índice", lambda r: _cenario(r, "Pessimista")),
    _r("S96", SEC_SENS, "cenário otimista: VPL e índice", lambda r: _cenario(r, "Otimista")),
    Campo("S97", SEC_SENS, "alternativas comparadas ao projeto", lambda cfg, r, c: _topsis(c, lambda t: lista(_alternativas(cfg, c)))),
    Campo("S98", SEC_SENS, "alternativa melhor classificada no TOPSIS",
          lambda cfg, r, c: _topsis(c, lambda t: f"{t.iloc[0]['Alternativa']}, com proximidade relativa à solução ideal de "
                                                 f"{num(t.iloc[0]['TOPSIS'], 3)}")),
    Campo("S99", SEC_SENS, "VPL e P(VPL > 0) da alternativa melhor classificada",
          lambda cfg, r, c: _topsis(c, lambda t: f"VPL de {reais(t.iloc[0]['VPL (R$)'])} e P(VPL > 0) de {pct_br(t.iloc[0]['P(VPL>0)'])}")),
    # ---------------------------------------------------------------- verificação e execução
    _r("S100", SEC_VV, "verificações executadas e aprovadas",
       lambda r: f"{r['vv']['quantidade_verificacoes'] - r['vv']['quantidade_erros']} de "
                 f"{r['vv']['quantidade_verificacoes']} verificações aprovadas"),
    _r("S101", SEC_VV, "tempo de execução da análise (determinística, Monte Carlo, sensibilidade e verificação)",
       lambda r: f"{num(r.get('tempo_execucao_s', float('nan')), 0)} segundos"),
    Campo("S102", SEC_IND, "pesos obtidos pela escala Likert e concordância entre avaliadores", lambda cfg, r, c: _likert(r)),
]
CASAS_KPI = {"ph_azul": 0, "ph_cinza": 0, "lso": 1, "rvl": 1}
CAMPOS += [_r(f"K{i:02d}", SEC_IND, f"{ROTULO_KPI[k]} — valor bruto",
              (lambda kk: lambda r: num(r["indice"]["kpis_brutos"][kk], CASAS_KPI.get(kk, 3)))(k))
           for i, k in enumerate([k for ks in KPIS_POR_DIMENSAO.values() for k in ks], 1)]
CAMPOS += [_r(f"N{i:02d}", SEC_IND, f"{ROTULO_KPI[k]} — normalizado",
              (lambda kk: lambda r: num(r["indice"]["kpis_normalizados"][kk], 3))(k))
           for i, k in enumerate([k for ks in KPIS_POR_DIMENSAO.values() for k in ks], 1)]


def _precisao(r):
    ep = _f(r["monte_carlo"]["convergencia"].iloc[-1]["Erro-padrão"])
    media = abs(_f(_mc(r)["media_vpl"]))
    rel = f", equivalente a {pct_br(1.96 * ep / media)} da média em módulo" if media > 0 else ""
    return f"{reais(ep)}; a semiamplitude do IC 95% da média foi de {reais(1.96 * ep)}{rel}"


def _critico(r, var):
    """Valor crítico (VPL = 0) e folga em relação ao valor informado, em forma curta (tabelas)."""
    if var.endswith("tma_aa_pct"):
        tir = _f(r[Ec]["tir_anual"])
        return f"{num(100 * tir, 1)}% a.a. (= TIR)" if math.isfinite(tir) else "não definido (TIR inexistente)"
    vc = r["valores_criticos"].set_index("Variável")
    if var not in vc.index or not math.isfinite(_f(vc.loc[var, "Valor crítico (VPL = 0)"])):
        return "sem valor crítico no intervalo analisado"
    escala, casas = (_VAR[var][2], _VAR[var][3]) if var in _VAR else (1.0, 2)
    valor = num(_f(vc.loc[var, "Valor crítico (VPL = 0)"]) * escala, min(casas + 1, 3))
    folga = _f(vc.loc[var, "Folga relativa"])
    if not math.isfinite(folga):
        return f"{valor} (valor informado nulo)"
    return f"{valor} ({'+' if folga >= 0 else '−'}{num(abs(folga) * 100, 1)}%)"


def _critico_frase(r, var):
    """Valor crítico (VPL = 0) da variável em frase completa (texto)."""
    if var.endswith("tma_aa_pct"):
        tir = _f(r[Ec]["tir_anual"])
        return (f"o VPL se anula quando a TMA iguala a TIR do projeto ({num(100 * tir, 1)}% a.a.)" if math.isfinite(tir)
                else "não há TMA que anule o VPL, pois a TIR não é definida")
    vc = r["valores_criticos"].set_index("Variável")
    if var not in vc.index or not math.isfinite(_f(vc.loc[var, "Valor crítico (VPL = 0)"])):
        return "não há valor que anule o VPL no intervalo analisado"
    escala, casas, unidade = (_VAR[var][2], _VAR[var][3], _VAR[var][5]) if var in _VAR else (1.0, 2, "")
    valor = num(_f(vc.loc[var, "Valor crítico (VPL = 0)"]) * escala, min(casas + 1, 3))
    if unidade == "%":
        valor = f"{valor}%"
    elif unidade.startswith("R$/"):
        valor = f"R$ {valor}/{unidade[3:]}"
    else:
        valor = f"{valor} {unidade}".strip()
    folga = _f(vc.loc[var, "Folga relativa"])
    if not math.isfinite(folga):
        return f"o valor que anula o VPL é {valor} (o valor informado é nulo)"
    return (f"o valor que anula o VPL é {valor}, {num(abs(folga) * 100, 1)}% "
            f"{'acima' if folga >= 0 else 'abaixo'} do valor informado")


def _cenario(r, nome):
    c = r["cenarios"].set_index("Cenário")
    return f"VPL de {reais(c.loc[nome, 'VPL'])} e índice de {num(c.loc[nome, 'Índice EVTEAS'], 3)}"


def _likert(r):
    pesos = r["indice"]["pesos"]
    lk = pesos.get("likert_dimensoes")
    if not lk:
        return "não se aplica (método de ponderação diferente da escala Likert)"
    w = lk["pesos"]
    return (lista([f"{NOMES_DIM[d]} {num(w[d], 3)}" for d in ("tecnico", "economico", "ambiental", "social")])
            + f", com concordância média de {num(lk['concordancia_media'], 3)}")


POR_CODIGO: Dict[str, Campo] = {c.codigo: c for c in CAMPOS}
CODIGO_KPI = {k: f"{i:02d}" for i, k in enumerate([k for ks in KPIS_POR_DIMENSAO.values() for k in ks], 1)}


# ---------------------------------------------------------------------------
# Prints (telas do wizard e saídas do notebook) que ilustram o texto
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Print:
    codigo: str
    descricao: str
    onde: str                        # onde a tela ou a saída aparece no notebook
    como: str = ""                   # orientação de captura (roteiro)

    @property
    def lacuna(self) -> str:
        return f"[INSERIR PRINT {self.codigo} – {self.descricao} ({self.onde})]"


WIZARD = "wizard de entrada, seção “Entrada de dados do projeto” do notebook"
ANALISE = "seção “Análise com as entradas informadas” do notebook"
GRAFICOS = "seção “Exportação e gráficos” do notebook"
COMO_WIZARD = ("Capture as perguntas e as respostas dos blocos indicados, que o wizard anuncia com a linha ▶ PRINT. "
               "Se não couberem numa tela, use mais de uma captura, dispostas lado a lado ou em sequência. Use a opção "
               "“Novo projeto” ou, ao reabrir um arquivo, responda s à revisão bloco a bloco; se corrigir um bloco depois "
               "do resumo, refaça a captura correspondente.")
COMO_GRAFICO = ("Insira o arquivo PNG gravado em evteas_output/figuras (incluído em evteas_output.zip, baixado no Colab) "
                "ou capture o gráfico exibido abaixo da linha ▶ PRINT.")
COMO_TABELA = "Capture a tabela exibida abaixo da linha ▶ PRINT."
PRINTS: List[Print] = [
    Print("P01", "menu inicial e bloco 1 do wizard (identificação do projeto)", WIZARD, COMO_WIZARD),
    Print("P02", "resumo das entradas exibido antes da confirmação", WIZARD, COMO_TABELA),
    Print("P03", "blocos 2 e 3 do wizard (infraestrutura; parâmetros biológicos e insumos)", WIZARD, COMO_WIZARD),
    Print("P04", "curva de crescimento, biomassa e arraçoamento (gráfico 01_curva_crescimento)", GRAFICOS, COMO_GRAFICO),
    Print("P05", "blocos 4 a 6 do wizard (investimento; mix de produtos e receitas; custos operacionais)", WIZARD, COMO_WIZARD),
    Print("P06", "blocos 7 a 9 do wizard (pessoas; tributos; rampa, projeção e TMA)", WIZARD, COMO_WIZARD),
    Print("P07", "receita, custos e fluxo de caixa acumulado (gráfico 02_projecao_economica)", GRAFICOS, COMO_GRAFICO),
    Print("P08", "blocos 10 a 12 do wizard (água e efluentes; energia, emissões e resíduos; conformidade)", WIZARD, COMO_WIZARD),
    Print("P09", "blocos 13 e 14 do wizard (dimensão social; governança)", WIZARD, COMO_WIZARD),
    Print("P10", "Radar Social (gráfico 04_radar_social)", GRAFICOS, COMO_GRAFICO),
    Print("P11", "bloco 15 do wizard (pesos do índice e regras de decisão)", WIZARD, COMO_WIZARD),
    Print("P12", "scores dimensionais e índice EVTEAS (gráfico 03_dimensoes)", GRAFICOS, COMO_GRAFICO),
    Print("P13", "classificação e resumo executivo", ANALISE, COMO_TABELA),
    Print("P14", "bloco 16 do wizard (distribuições do Monte Carlo)", WIZARD, COMO_WIZARD),
    Print("P15", "distribuição e probabilidade acumulada do VPL (gráfico 05_monte_carlo_vpl)", GRAFICOS, COMO_GRAFICO),
    Print("P16", "convergência da simulação (gráfico 06_convergencia_mc)", GRAFICOS, COMO_GRAFICO),
    Print("P17", "tabela de sensibilidade, valores críticos e importância das variáveis", GRAFICOS, COMO_TABELA),
    Print("P18", "diagrama de tornado (gráfico 07_tornado)", GRAFICOS, COMO_GRAFICO),
    Print("P19", "ranking TOPSIS das alternativas", "seção “Comparação com alternativas de projeto” do notebook", COMO_TABELA),
    Print("P20", "proximidade relativa à solução ideal (gráfico 08_topsis)", GRAFICOS, COMO_GRAFICO),
]
PRINT_POR_CODIGO: Dict[str, Print] = {p.codigo: p for p in PRINTS}
FIGURA_DO_PRINT = {"01_curva_crescimento": "P04", "02_projecao_economica": "P07", "04_radar_social": "P10",
                   "03_dimensoes": "P12", "05_monte_carlo_vpl": "P15", "06_convergencia_mc": "P16",
                   "07_tornado": "P18", "08_topsis": "P20"}


def roteiro_de_prints() -> pd.DataFrame:
    """Prints que ilustram o texto, na ordem em que aparecem, com o local e o modo de captura."""
    return pd.DataFrame([{"Print": p.codigo, "Conteúdo": p.descricao, "Onde capturar": p.onde, "Como capturar": p.como}
                         for p in PRINTS])


def titulo_print(codigo: str) -> str:
    """Cabeçalho exibido no notebook (e no wizard) antes da tela ou da saída a capturar."""
    p = PRINT_POR_CODIGO[codigo]
    return f"▶ PRINT {p.codigo} — {p.descricao}"


def lacuna(codigo: str) -> str:
    """Texto da lacuna, como aparece na dissertação (ex.: '[S23 – VPL do projeto]')."""
    return POR_CODIGO[codigo].lacuna


def _origem(cfg: EVTEASConfig, caminhos) -> str:
    """Origem declarada dos parâmetros da lacuna; origens diferentes são listadas todas."""
    vistas = []
    for c in caminhos:
        f = cfg.fontes.get(c)
        if f is not None:
            cat = CATEGORIAS_FONTE.get(getattr(f, "categoria", ""), getattr(f, "categoria", ""))
            ref = getattr(f, "referencia", "")
            texto = f"{cat}{' — ' + ref if ref else ''}"
            if texto not in vistas:
                vistas.append(texto)
    if vistas:
        return "; ".join(vistas)
    return "—" if not caminhos else "não registrada"


def _assinatura(config) -> str:
    import json
    from dataclasses import asdict, is_dataclass
    return json.dumps(asdict(config) if is_dataclass(config) else config, sort_keys=True, default=str, ensure_ascii=False)


def valores_para_o_texto(cfg: EVTEASConfig, resultado: Dict[str, Any],
                         comparacao: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Valor de cada lacuna do texto na execução do usuário, na ordem do texto.

    Use após ``executar_evteas(cfg, executar_mc=True, executar_sens=True)``; ``comparacao``
    é o resultado de ``definir_e_comparar_alternativas`` (opcional). O resultado precisa ter
    sido calculado com estas mesmas entradas, para que entradas e resultados não se misturem."""
    from .interface import EntradaCancelada
    if not isinstance(resultado, dict) or ("config" in resultado and _assinatura(resultado["config"]) != _assinatura(cfg)):
        raise EntradaCancelada("O resultado foi calculado com outras entradas. Execute novamente a análise "
                               "(seção “Análise com as entradas informadas”) antes de gerar os valores para o texto.")
    aviso_comparacao = None
    base = (comparacao or {}).get("resultados", {}).get(cfg.projeto or "Projeto informado")
    if base is not None:
        if _assinatura(base["config"]) != _assinatura(cfg):
            comparacao, aviso_comparacao = None, ("comparação feita com outras entradas: refaça a seção "
                                                  "“Comparação com alternativas de projeto”")
    linhas = []
    for c in CAMPOS:
        try:
            valor = c.valor(cfg, resultado, comparacao)
        except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError) as exc:
            valor = f"indisponível ({exc})"
        if aviso_comparacao and c.codigo in ("S97", "S98", "S99"):
            valor = aviso_comparacao
        linhas.append({"Código": c.codigo, "Seção": c.secao, "Lacuna no texto": c.lacuna, "Valor": valor,
                       "Origem declarada": _origem(cfg, c.caminhos) if c.codigo.startswith("E") else ""})
    return pd.DataFrame(linhas)


def exportar_valores_para_o_texto(df: pd.DataFrame, pasta: str = "evteas_output", baixar: bool = False) -> str:
    """Grava a tabela em Excel (com o roteiro de prints numa segunda aba); no Colab, ``baixar`` faz o download."""
    from pathlib import Path
    Path(pasta).mkdir(parents=True, exist_ok=True)
    caminho = str(Path(pasta) / "valores_para_o_texto.xlsx")
    with pd.ExcelWriter(caminho) as xl:
        df.to_excel(xl, sheet_name="Valores para o texto", index=False)
        roteiro_de_prints().to_excel(xl, sheet_name="Roteiro de prints", index=False)
    if baixar:
        from .interface import _baixar_no_colab
        _baixar_no_colab(caminho)
    return caminho

"""Entrada de dados do EVTEAS-Py: menu inicial, wizard completo, arquivos JSON e análise de preços.

O estudo começa SEMPRE pela entrada de dados (``iniciar_entradas``). Há três modos:

1. **Novo projeto** — todas as premissas do projeto precisam ser digitadas; o
   wizard não usa valores prontos. Apenas coeficientes técnicos com referência
   normativa ou bibliográfica (ex.: limites da Resolução CONAMA nº 357/2005,
   teor de nitrogênio no peixe) aparecem como "referência — Enter aceita", e a
   origem fica registrada no estudo.
2. **Carregar e revisar** — lê um arquivo JSON salvo numa entrada anterior;
   cada pergunta mostra o valor salvo, e Enter o mantém.
3. **Exemplo ilustrativo** — carrega o caso-base da dissertação, apenas para
   demonstração do artefato.

O wizard preserva o percurso das versões anteriores (Viabilidade econômica
Rev. 8/9 e EVTEAS master): tipo de organização, mix de produtos com
quantidades e preços, serviços de transporte, carência, custos, cooperados,
funcionários CLT por cargo, tributos individuais, rampa, crescimento e TMA. Acrescenta os
parâmetros técnico-ambientais-sociais, a governança, os pesos (preset,
Likert ou AHP), as regras de decisão, as distribuições do Monte Carlo e a
origem das premissas (Seção 3.6).
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import (CATEGORIAS_FONTE, CHECKLIST_AMBIENTAL, CLASSES_CORPO_RECEPTOR, FAIXAS_AACE,
                     KPIS_POR_DIMENSAO, SISTEMAS_PRODUTIVOS, AmbientalConfig, DecisaoConfig, Distribuicao,
                     EconomicoConfig, EVTEASConfig, Fonte, GovernancaConfig, MonteCarloConfig, PesosConfig,
                     SocialConfig, TecnicoConfig, caminhos_numericos, config_de_dict, config_para_dict,
                     definir_por_caminho, obter_por_caminho)
from .casos import criar_config_caso_base

LINHA = "-" * 78


# ---------------------------------------------------------------------------
# Arquivos de entradas
# ---------------------------------------------------------------------------

def salvar_config(cfg: EVTEASConfig, caminho) -> str:
    Path(caminho).write_text(json.dumps(config_para_dict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(caminho)


def carregar_config(caminho) -> EVTEASConfig:
    return config_de_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))


def nome_arquivo(cfg: EVTEASConfig) -> str:
    import unicodedata
    ascii_ = unicodedata.normalize("NFKD", cfg.projeto or "").encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "_", ascii_).strip("_")[:60] or "projeto"
    return f"entradas_{base}.json"


# ---------------------------------------------------------------------------
# Leitura de valores digitados
# ---------------------------------------------------------------------------

def converter_numero(txt: str) -> float:
    """Aceita 1234,56 · 1.234,56 · 1234.56 · 1,234.56 · 12% · R$ 10 · frações como 1/3."""
    t = txt.strip().replace("R$", "").replace("%", "").replace(" ", "")
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?/\d+(?:[.,]\d+)?", t):
        a, b = t.split("/")
        return converter_numero(a) / converter_numero(b)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    v = float(t)
    if not math.isfinite(v):
        raise ValueError("valor não finito")
    return v


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "s" if v else "n"
    if isinstance(v, float):
        return f"{v:,.6g}".replace(",", "X").replace(".", ",").replace("X", ".") if abs(v) >= 1000 else f"{v:.6g}".replace(".", ",")
    return str(v)


class EntradaCancelada(Exception):
    """Levantada quando o usuário digita 'sair' em qualquer pergunta."""


class Perguntador:
    """Faz as perguntas, valida as respostas e registra a origem de cada premissa.

    modo ``novo``: o valor é obrigatório (não há padrão), exceto quando há
    uma referência técnica explícita, que o usuário aceita com Enter.
    modo ``revisar``: Enter mantém o valor atual (carregado de arquivo).
    """

    def __init__(self, entrada: Callable[[str], str] = input, saida: Callable[..., None] = print, modo: str = "novo"):
        if modo not in ("novo", "revisar"):
            raise ValueError("modo deve ser 'novo' ou 'revisar'")
        self.entrada, self.saida, self.modo = entrada, saida, modo
        self.digitados: List[str] = []                    # caminhos informados pelo usuário no bloco atual
        self.referencias: Dict[str, Fonte] = {}           # caminhos aceitos por referência

    # -- leitura bruta -------------------------------------------------------
    def _ler(self, prompt: str) -> str:
        txt = self.entrada(prompt)
        txt = "" if txt is None else str(txt).strip()
        if txt.lower() in ("sair", "cancelar"):
            raise EntradaCancelada("entrada interrompida pelo usuário")
        return txt

    def _sufixo(self, atual, referencia):
        if self.modo == "revisar" and atual is not None:
            return f" [{_fmt(atual)}]"
        if referencia is not None:
            return f" [referência: {_fmt(referencia)} — Enter aceita]"
        return ""

    def _padrao(self, atual, referencia):
        if self.modo == "revisar" and atual is not None:
            return atual, "mantido"
        if referencia is not None:
            return referencia, "referencia"
        return None, None

    # -- tipos ---------------------------------------------------------------
    def numero(self, rotulo: str, atual=None, minimo: Optional[float] = None, maximo: Optional[float] = None,
               inteiro: bool = False, referencia=None, unidade: str = "") -> Tuple[float, str]:
        un = f" ({unidade})" if unidade else ""
        while True:
            txt = self._ler(f"{rotulo}{un}{self._sufixo(atual, referencia)}: ")
            if not txt:
                v, origem = self._padrao(atual, referencia)
                if v is None:
                    self.saida("  ⚠ Valor obrigatório. Digite um número (vírgula ou ponto decimal).")
                    continue
            else:
                try:
                    v = converter_numero(txt)
                except (ValueError, ZeroDivisionError):
                    self.saida("  ⚠ Valor inválido. Use apenas números, por exemplo 1500 ou 1.500,50.")
                    continue
                origem = "usuario"
            if inteiro and abs(v - round(v)) > 1e-9:
                self.saida("  ⚠ Informe um número inteiro.")
                continue
            if minimo is not None and v < minimo:
                self.saida(f"  ⚠ O valor deve ser maior ou igual a {_fmt(minimo)}.")
                continue
            if maximo is not None and v > maximo:
                self.saida(f"  ⚠ O valor deve ser menor ou igual a {_fmt(maximo)}.")
                continue
            return (int(round(v)) if inteiro else float(v)), origem

    def opcao(self, rotulo: str, opcoes: Sequence[Tuple[str, str]], atual=None, referencia=None) -> Tuple[str, str]:
        self.saida(rotulo)
        for k, (_, desc) in enumerate(opcoes, 1):
            self.saida(f"  {k}. {desc}")
        chaves = [c for c, _ in opcoes]
        idx_atual = chaves.index(atual) + 1 if atual in chaves else None
        idx_ref = chaves.index(referencia) + 1 if referencia in chaves else None
        while True:
            txt = self._ler(f"Opção (1–{len(opcoes)}){self._sufixo(idx_atual, idx_ref)}: ")
            if not txt:
                v, origem = self._padrao(idx_atual, idx_ref)
                if v is None:
                    self.saida("  ⚠ Escolha obrigatória.")
                    continue
                return chaves[v - 1], origem
            if txt.isdigit() and 1 <= int(txt) <= len(opcoes):
                return chaves[int(txt) - 1], "usuario"
            if txt in chaves:
                return txt, "usuario"
            self.saida("  ⚠ Opção inválida.")

    def sim_nao(self, rotulo: str, atual: Optional[bool] = None, referencia: Optional[bool] = None) -> Tuple[bool, str]:
        while True:
            txt = self._ler(f"{rotulo} (s/n){self._sufixo(atual, referencia)}: ").lower()
            if not txt:
                v, origem = self._padrao(atual, referencia)
                if v is None:
                    self.saida("  ⚠ Responda s ou n.")
                    continue
                return bool(v), origem
            if txt in ("s", "sim", "y"):
                return True, "usuario"
            if txt in ("n", "nao", "não", "no"):
                return False, "usuario"
            self.saida("  ⚠ Responda s ou n.")

    def texto(self, rotulo: str, atual: Optional[str] = None, obrigatorio: bool = True, referencia: Optional[str] = None) -> str:
        while True:
            txt = self._ler(f"{rotulo}{self._sufixo(atual or None, referencia)}: ")
            if txt:
                return txt
            v, _ = self._padrao(atual or None, referencia)
            if v is not None:
                return v
            if not obrigatorio:
                return ""
            self.saida("  ⚠ Texto obrigatório.")

    # -- atalhos que leem e gravam diretamente na configuração ----------------
    def _registrar(self, caminho: str, origem: str, fonte_ref: Optional[Fonte]):
        if origem == "usuario":
            self.digitados.append(caminho)
            self.referencias.pop(caminho, None)
        elif origem == "referencia" and fonte_ref is not None:
            self.referencias[caminho] = fonte_ref

    def campo(self, cfg: EVTEASConfig, caminho: str, rotulo: str, minimo=None, maximo=None, inteiro=False,
              referencia=None, unidade: str = "", fonte_ref: Optional[Fonte] = None) -> float:
        atual = obter_por_caminho(cfg, caminho)
        v, origem = self.numero(rotulo, atual, minimo, maximo, inteiro, referencia, unidade)
        definir_por_caminho(cfg, caminho, v)
        self._registrar(caminho, origem, fonte_ref)
        return v

    def campo_pct(self, cfg, caminho, rotulo, minimo=0.0, maximo=100.0, referencia=None, fonte_ref=None) -> float:
        return self.campo(cfg, caminho, rotulo, minimo, maximo, False, referencia, "%", fonte_ref)

    def campo_sn(self, cfg, caminho, rotulo, referencia=None) -> bool:
        v, origem = self.sim_nao(rotulo, obter_por_caminho(cfg, caminho), referencia)
        definir_por_caminho(cfg, caminho, v)
        return v

    def bloco(self, titulo: str):
        self.saida("\n" + LINHA + f"\n{titulo}\n" + LINHA)
        self.digitados = []


FONTE_KUBITZA = Fonte("bibliografico", "Kubitza (2017)")
FONTE_CONAMA = Fonte("normativo", "Resolução CONAMA nº 357/2005")
FONTE_SISTEMA = Fonte("bibliografico", "Referência do sistema produtivo no EVTEAS-Py (calibrar com especialista)")
FONTE_AUTOR = Fonte("autor", "Valor de referência do EVTEAS-Py")


def _fontes_do_bloco(P: Perguntador, cfg: EVTEASConfig, nome_bloco: str):
    """Registra a origem das premissas digitadas no bloco (Seção 3.6)."""
    caminhos = list(dict.fromkeys(P.digitados))
    for c, f in P.referencias.items():
        cfg.fontes[c] = f
    if not caminhos:
        return
    if P.modo == "revisar":
        mudar, _ = P.sim_nao(f"Atualizar a origem dos dados do bloco '{nome_bloco}'?", False)
        if not mudar:
            return
    opcoes = list(CATEGORIAS_FONTE.items())
    cat, _ = P.opcao(f"Origem dos dados informados no bloco '{nome_bloco}':", opcoes)
    ref = P.texto("Referência (documento, cotação, autor, data)", obrigatorio=False)
    for c in caminhos:
        cfg.fontes[c] = Fonte(cat, ref)
    detalhar, _ = P.sim_nao("Algum parâmetro deste bloco tem origem diferente?", False if P.modo == "revisar" else None)
    while detalhar:
        for k, c in enumerate(caminhos, 1):
            P.saida(f"  {k}. {c}")
        k, _ = P.numero("Número do parâmetro", None, 1, len(caminhos), inteiro=True)
        cat_k, _ = P.opcao("Origem desse parâmetro:", opcoes)
        cfg.fontes[caminhos[k - 1]] = Fonte(cat_k, P.texto("Referência", obrigatorio=False))
        detalhar, _ = P.sim_nao("Detalhar outro parâmetro?", False if P.modo == "revisar" else None)


# ---------------------------------------------------------------------------
# Blocos do wizard
# ---------------------------------------------------------------------------

TIPOS_ORGANIZACAO = [("empresa", "Empresa"), ("coop_trabalho", "Cooperativa de Trabalho"),
                     ("coop_agro", "Cooperativa Agropecuária")]
MINIMO_COOPERADOS = {"coop_trabalho": 7, "coop_agro": 20}   # Lei nº 12.690/2012; Lei nº 5.764/1971


def bloco_identificacao(P: Perguntador, cfg: EVTEASConfig):
    P.bloco("1. IDENTIFICAÇÃO DO PROJETO")
    cfg.projeto = P.texto("Nome do projeto", cfg.projeto if P.modo == "revisar" else None)
    cfg.autor = P.texto("Responsável pelo estudo", cfg.autor if P.modo == "revisar" else None)
    tipo, _ = P.opcao("Tipo de pessoa jurídica:", TIPOS_ORGANIZACAO,
                      cfg.economico.tipo_organizacao if P.modo == "revisar" else None)
    cfg.economico.tipo_organizacao = tipo


def bloco_tecnico(P: Perguntador, cfg: EVTEASConfig):
    t = cfg.tecnico
    P.bloco("2. DIMENSÃO TÉCNICA — INFRAESTRUTURA")
    t.especie = P.texto("Espécie cultivada", t.especie if P.modo == "revisar" else None,
                        referencia="Tilápia-do-nilo (Oreochromis niloticus)")
    sistemas = [(k, f"{k} (referência: {v['capacidade_suporte_kg_m3']} kg/m³; {v['energia_kwh_kg']} kWh/kg)")
                for k, v in SISTEMAS_PRODUTIVOS.items()]
    t.sistema_produtivo, _ = P.opcao("Sistema produtivo:", sistemas, t.sistema_produtivo if P.modo == "revisar" else None)
    ref = SISTEMAS_PRODUTIVOS[t.sistema_produtivo]
    vol_atual = t.area_lamina_m2 * t.profundidade_media_m      # volume salvo (antes de alterar a área)
    P.campo(cfg, "tecnico.area_lamina_m2", "Área de lâmina d'água", minimo=1, unidade="m²")
    vol, origem = P.numero("Volume útil total dos viveiros/tanques", vol_atual if P.modo == "revisar" else None,
                           minimo=0.01, unidade="m³")
    t.profundidade_media_m = vol / t.area_lamina_m2
    if origem == "usuario":
        P.digitados.append("tecnico.profundidade_media_m")
    P.saida(f"  → profundidade média equivalente: {_fmt(round(t.profundidade_media_m, 3))} m")
    P.campo(cfg, "tecnico.numero_tanques", "Número total de viveiros/tanques", minimo=1, inteiro=True)
    P.campo(cfg, "tecnico.tanques_ativos", "Número de viveiros/tanques ativos", minimo=0, maximo=t.numero_tanques, inteiro=True)
    cap_atual = t.capacidade_suporte_kg_m3
    cap, origem = P.numero("Capacidade de suporte ao final do ciclo", cap_atual if P.modo == "revisar" else None,
                           minimo=0.0001, referencia=ref["capacidade_suporte_kg_m3"], unidade="kg/m³")
    t.capacidade_suporte_kg_m3 = cap
    P._registrar("tecnico.capacidade_suporte_kg_m3", origem, FONTE_SISTEMA)
    P.campo(cfg, "tecnico.produtividade_esperada_kg_m2_ciclo", "Produtividade esperada por área (0 = não restringe)",
            minimo=0, unidade="kg/m²/ciclo")

    P.bloco("3. DIMENSÃO TÉCNICA — PARÂMETROS BIOLÓGICOS E INSUMOS")
    P.campo(cfg, "tecnico.peso_inicial_g", "Peso inicial dos alevinos/juvenis", minimo=0.01, unidade="g")
    P.campo(cfg, "tecnico.peso_final_g", "Peso final de abate/venda", minimo=t.peso_inicial_g * 1.0001, unidade="g")
    P.campo(cfg, "tecnico.ciclo_dias", "Duração do ciclo produtivo", minimo=1, maximo=1095, inteiro=True, unidade="dias")
    P.campo(cfg, "tecnico.ciclos_ano", "Ciclos por ano (escalonados entre os viveiros)", minimo=0.01,
            maximo=round(365 / t.ciclo_dias, 4))
    P.campo(cfg, "tecnico.alevinos_por_ciclo", "Alevinos estocados por ciclo (0 = dimensionar pela biomassa-alvo)",
            minimo=0, unidade="unidades")
    P.campo(cfg, "tecnico.fcr", "Conversão alimentar — FCR/TCA", minimo=0.3, maximo=6, unidade="kg ração/kg ganho")
    P.campo_pct(cfg, "tecnico.mortalidade_pct", "Mortalidade esperada no ciclo", maximo=99)
    P.campo(cfg, "tecnico.desempenho_crescimento_pct", "Desempenho de crescimento (peso atingido / peso-alvo)",
            minimo=1, maximo=150, referencia=100.0, unidade="%", fonte_ref=FONTE_AUTOR)
    P.campo(cfg, "tecnico.fcr_referencia", "FCR de referência para o diagnóstico Lean-Green", minimo=0.3, maximo=6,
            referencia=1.40, fonte_ref=FONTE_KUBITZA)
    P.campo_pct(cfg, "tecnico.mortalidade_referencia_pct", "Mortalidade de referência para o diagnóstico Lean-Green",
                referencia=5.0, fonte_ref=FONTE_KUBITZA)
    from .modelo import Contexto, calcular_tecnico
    tec = calcular_tecnico(Contexto(cfg))
    P.saida(f"  → Produção estimada: {_fmt(round(float(tec['producao_kg_ano'][0]), 1))} kg/ano "
            f"({_fmt(round(float(tec['producao_kg_mes'][0]), 1))} kg/mês); restrição ativa: {tec['restricao_biomassa']}; "
            f"alevinos/ciclo: {_fmt(round(float(tec['alevinos_ciclo'][0])))}; OEE: {float(tec['oee'][0]):.3f}")
    _fontes_do_bloco(P, cfg, "técnico")


def bloco_investimento(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("4. DIMENSÃO ECONÔMICA — INVESTIMENTO (CAPEX)")
    detalhar, _ = P.sim_nao("Detalhar o CAPEX por item (s) ou informar o total (n)?",
                            (len(e.capex_itens) > 1) if P.modo == "revisar" else None)
    if detalhar:
        if P.modo == "revisar" and e.capex_itens:
            P.saida("Itens atuais: " + "; ".join(f"{k}: R$ {_fmt(v)}" for k, v in e.capex_itens.items()))
            refazer, _ = P.sim_nao("Refazer a lista de itens?", False)
        else:
            refazer = True
        if refazer:
            itens: Dict[str, float] = {}
            while True:
                nome = P.texto(f"Item de CAPEX nº {len(itens) + 1} (Enter vazio encerra)", obrigatorio=not itens)
                if not nome:
                    break
                itens[nome], _ = P.numero(f"  Valor de '{nome}'", None, 0, unidade="R$")
            e.capex_itens = itens
    else:
        total, _ = P.numero("Investimento inicial total — CAPEX", e.capex_total if P.modo == "revisar" else None, 0,
                            unidade="R$")
        e.capex_itens = {"CAPEX total": total}
    P.digitados.append("economico.capex_itens")
    P.saida(f"  → CAPEX total: R$ {_fmt(e.capex_total)}")
    classes = [(k, f"Classe {k} (faixa de exatidão {int(lo * 100)}% a +{int(hi * 100)}%)") for k, (lo, hi) in FAIXAS_AACE.items()]
    cl, origem = P.opcao("Maturidade da estimativa de CAPEX (AACE International):", classes,
                         e.classe_estimativa_aace if P.modo == "revisar" else None, referencia=5)
    e.classe_estimativa_aace = int(cl)
    P._registrar("economico.classe_estimativa_aace", origem, Fonte("normativo", "AACE International (2020)"))
    P.campo(cfg, "economico.capital_giro", "Capital de giro inicial", minimo=0, unidade="R$")
    P.campo(cfg, "economico.vida_util_anos", "Vida útil média dos ativos para depreciação", minimo=0, maximo=100,
            unidade="anos")
    residual, origem = P.numero("Valor residual dos ativos ao final do horizonte",
                                e.capex_total * e.valor_residual_pct / 100 if P.modo == "revisar" else None,
                                minimo=0, maximo=e.capex_total, unidade="R$")
    e.valor_residual_pct = 100 * residual / e.capex_total if e.capex_total else 0.0
    if origem == "usuario":
        P.digitados.append("economico.valor_residual_pct")
    P.campo_pct(cfg, "economico.fomento_nao_reembolsavel_pct", "Parcela do CAPEX coberta por fomento não reembolsável")
    _fontes_do_bloco(P, cfg, "investimento")


def bloco_receitas(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("5. DIMENSÃO ECONÔMICA — MIX DE PRODUTOS E RECEITAS (a 100% da capacidade)")
    if P.modo == "revisar" and not e.mix_produtos:
        from .modelo import Contexto, calcular_tecnico
        prod = e.producao_vendas_kg_mes or float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
        e.mix_produtos = [{"nome": "Produto principal", "quantidade_kg_mes": round(prod, 4),
                           "preco_kg": e.preco_venda_kg, "participacao_pct": 100.0}]
    for p in e.mix_produtos:          # arquivos antigos: só participação → quantidade equivalente
        if "quantidade_kg_mes" not in p:
            from .modelo import Contexto, calcular_tecnico
            prod = e.producao_vendas_kg_mes or float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
            p["quantidade_kg_mes"] = prod * float(p.get("participacao_pct", 100)) / 100
    n_atual = len(e.mix_produtos) if (P.modo == "revisar" and e.mix_produtos) else None
    n, _ = P.numero("Quantidade de produtos no mix de vendas", n_atual, 1, 20, inteiro=True)
    mix = []
    for i in range(n):
        ant = e.mix_produtos[i] if (P.modo == "revisar" and i < len(e.mix_produtos)) else {}
        P.saida(f"\nProduto #{i + 1}")
        nome = P.texto("  Nome do produto", ant.get("nome"))
        qtd, _ = P.numero("  Quantidade vendida por mês", ant.get("quantidade_kg_mes"), 0, unidade="kg/mês")
        preco, _ = P.numero("  Preço de venda", ant.get("preco_kg"), 0, unidade="R$/kg")
        mix.append({"nome": nome, "quantidade_kg_mes": qtd, "preco_kg": preco})
    total = sum(p["quantidade_kg_mes"] for p in mix)
    for p in mix:
        p["participacao_pct"] = 100 * p["quantidade_kg_mes"] / total if total else 100 / len(mix)
    e.mix_produtos = mix
    e.preco_venda_kg = (sum(p["quantidade_kg_mes"] * p["preco_kg"] for p in mix) / total if total
                        else float(np.mean([p["preco_kg"] for p in mix])))
    P.digitados += ["economico.mix_produtos", "economico.preco_venda_kg"]
    P.saida(f"  → Preço médio ponderado: R$ {_fmt(round(e.preco_venda_kg, 4))}/kg")

    from .modelo import Contexto, calcular_tecnico, meses_ate_despesca
    prod_tec = float(calcular_tecnico(Contexto(cfg))["producao_kg_mes"][0])
    opcoes = [("tecnico", f"Produção calculada pelo módulo técnico ({_fmt(round(prod_tec, 1))} kg/mês)"),
              ("mix", f"Quantidades informadas no mix ({_fmt(round(total, 1))} kg/mês)")]
    atual = ("mix" if e.producao_vendas_kg_mes > 0 else "tecnico") if P.modo == "revisar" else None
    base, _ = P.opcao("Volume de vendas a utilizar:", opcoes, atual)
    e.producao_vendas_kg_mes = total if base == "mix" else 0.0
    if total and abs(total - prod_tec) / max(prod_tec, 1e-9) > 0.10:
        P.saida(f"  ⚠ O mix difere {abs(total / prod_tec - 1):.0%} da produção técnica; verifique as premissas.")

    servicos, _ = P.sim_nao("Há receita de serviços (ex.: transporte para terceiros)?",
                            (e.receita_servicos_mes > 0) if P.modo == "revisar" else None)
    if servicos:
        modo_km, _ = P.sim_nao("Calcular por quilômetro rodado (valor/km × km/mês)?", None if P.modo == "novo" else False)
        if modo_km:
            vkm, _ = P.numero("  Valor cobrado por km", None, 0, unidade="R$/km")
            km, _ = P.numero("  Quilômetros rodados por mês", None, 0, unidade="km/mês")
            e.receita_servicos_mes = vkm * km
        else:
            P.campo(cfg, "economico.receita_servicos_mes", "Receita mensal de serviços", minimo=0, unidade="R$/mês")
        P.digitados.append("economico.receita_servicos_mes")
    else:
        e.receita_servicos_mes = 0.0
    L_calc = int(math.ceil(cfg.tecnico.ciclo_dias / 30.4375))
    meses, origem = P.numero("Meses até a primeira receita (carência)",
                             meses_ate_despesca(cfg) if P.modo == "revisar" else None, 1, 60, inteiro=True,
                             referencia=L_calc)
    e.meses_ate_primeira_receita = 0 if meses == L_calc else meses
    P._registrar("economico.meses_ate_primeira_receita", origem, FONTE_AUTOR)
    _fontes_do_bloco(P, cfg, "receitas")


def bloco_custos(P: Perguntador, cfg: EVTEASConfig):
    e, a = cfg.economico, cfg.ambiental
    P.bloco("6. DIMENSÃO ECONÔMICA — CUSTOS OPERACIONAIS")
    P.campo(cfg, "economico.custo_racao_kg", "Custo da ração", minimo=0, unidade="R$/kg")
    un, origem = P.numero("Custo do alevino por unidade", e.custo_alevino_milheiro / 1000 if P.modo == "revisar" else None,
                          minimo=0, unidade="R$/un")
    e.custo_alevino_milheiro = un * 1000
    if origem == "usuario":
        P.digitados.append("economico.custo_alevino_milheiro")
    ref_kwh = SISTEMAS_PRODUTIVOS[cfg.tecnico.sistema_produtivo]["energia_kwh_kg"]
    kwh, origem = P.numero("Consumo de energia (aeração e bombeamento)", a.energia_kwh_kg if P.modo == "revisar" else None,
                           minimo=0, referencia=ref_kwh, unidade="kWh/kg produzido")
    a.energia_kwh_kg = kwh
    P._registrar("ambiental.energia_kwh_kg", origem, FONTE_SISTEMA)
    P.campo(cfg, "economico.tarifa_energia_kwh", "Tarifa de energia elétrica", minimo=0, unidade="R$/kWh")
    P.campo(cfg, "economico.outros_custos_variaveis_kg", "Outros custos variáveis (despesca, gelo, frete, embalagem)",
            minimo=0, unidade="R$/kg vendido")
    P.campo(cfg, "economico.assistencia_tecnica_mes", "Assistência técnica", minimo=0, unidade="R$/mês")
    P.campo(cfg, "economico.administrativo_mes", "Outros custos fixos (aluguel, contabilidade, seguros, administração)",
            minimo=0, unidade="R$/mês")
    man, origem = P.numero("Manutenção de instalações e equipamentos",
                           e.capex_total * e.manutencao_capex_pct_aa / 100 / 12 if P.modo == "revisar" else None,
                           minimo=0, unidade="R$/mês")
    e.manutencao_capex_pct_aa = 100 * man * 12 / e.capex_total if e.capex_total else 0.0
    if origem == "usuario":
        P.digitados.append("economico.manutencao_capex_pct_aa")
    from .modelo import Contexto, calcular_tecnico
    tec = calcular_tecnico(Contexto(cfg))
    prod = e.producao_vendas_kg_mes or float(tec["producao_kg_mes"][0])
    racao = prod * float(tec["racao_por_kg_produzido"][0]) * e.custo_racao_kg
    alev = float(tec["alevinos_ano"][0]) / 12 * e.custo_alevino_milheiro / 1000
    ener = prod * kwh * e.tarifa_energia_kwh
    outros = prod * e.outros_custos_variaveis_kg
    P.saida(f"  → Custo variável estimado a 100%: R$ {_fmt(round(racao + alev + ener + outros, 2))}/mês "
            f"(ração R$ {_fmt(round(racao, 2))}; alevinos R$ {_fmt(round(alev, 2))}; energia R$ {_fmt(round(ener, 2))}; "
            f"outros R$ {_fmt(round(outros, 2))})")
    _fontes_do_bloco(P, cfg, "custos")


def bloco_pessoas(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("7. PESSOAS — COOPERADOS E FUNCIONÁRIOS CLT")
    migrar_formato_detalhado(cfg)
    if e.tipo_organizacao != "empresa":
        minimo = MINIMO_COOPERADOS[e.tipo_organizacao]
        P.campo(cfg, "economico.retirada_cooperados_mes", "Retirada/pró-labore mensal TOTAL dos cooperados",
                minimo=0, unidade="R$/mês")
        while True:
            P.campo(cfg, "economico.cooperados_trabalhadores", "Cooperados que trabalham na operação", minimo=0, inteiro=True)
            forn, _ = P.sim_nao("Há cooperados que apenas entregam matéria-prima ou não atuam na operação?",
                                (e.cooperados_fornecedores > 0) if P.modo == "revisar" else None)
            if forn:
                P.campo(cfg, "economico.cooperados_fornecedores", "  Número desses cooperados", minimo=1, inteiro=True)
                e.nome_materia_prima = P.texto("  Principal matéria-prima fornecida (se houver)",
                                               e.nome_materia_prima or None, obrigatorio=False)
            else:
                e.cooperados_fornecedores = 0
            total = e.cooperados_trabalhadores + e.cooperados_fornecedores
            if total >= minimo:
                break
            P.saida(f"  ⚠ A legislação exige pelo menos {minimo} cooperados (informado: {total}).")
            seguir, _ = P.sim_nao("Prosseguir mesmo assim (ex.: grupo ainda em formalização)?", None)
            if seguir:
                break
        if e.cooperados_trabalhadores and e.cooperados_fornecedores:
            P.campo_pct(cfg, "economico.perc_sobras_trabalhadores", "Parcela das sobras destinada aos cooperados trabalhadores")
        else:
            e.perc_sobras_trabalhadores = 100.0
    else:
        e.retirada_cooperados_mes = 0.0
        e.cooperados_trabalhadores = 0
        e.cooperados_fornecedores = 0
        e.perc_sobras_trabalhadores = 100.0
    minimo_clt = 1 if e.tipo_organizacao == "empresa" else 0
    n_atual = len(e.salarios_clt_por_cargo) if P.modo == "revisar" else None
    n, _ = P.numero(f"Número de funcionários CLT (mínimo {minimo_clt})", n_atual, minimo_clt, 500, inteiro=True)
    antigos = list(e.salarios_clt_por_cargo.items())
    cargos: Dict[str, float] = {}
    for i in range(n):
        ant_nome, ant_sal = antigos[i] if (P.modo == "revisar" and i < len(antigos)) else (None, None)
        cargo = P.texto(f"  Cargo do funcionário CLT nº {i + 1}", ant_nome)
        while cargo in cargos:
            cargo = f"{cargo} ({i + 1})"
        cargos[cargo], _ = P.numero(f"  Salário bruto mensal de '{cargo}'", ant_sal, 0, unidade="R$")
    e.salarios_clt_por_cargo = cargos
    if n:
        P.digitados.append("economico.salarios_clt_por_cargo")
    _fontes_do_bloco(P, cfg, "pessoas")


TRIBUTOS = [  # nome, base, sugestão de alíquota (%)
    ("ICMS", "produtos", None), ("IPI", "produtos", None), ("ISS", "servicos", None),
    ("PIS (faturamento)", "faturamento", 0.65), ("COFINS", "faturamento", 3.0),
    ("CSLL", "lucro", 9.0), ("IRPJ", "lucro", 15.0),
    ("INSS patronal (CLT)", "folha_clt", 20.0), ("FGTS (CLT)", "folha_clt", 8.0), ("PIS sobre a folha (CLT)", "folha_clt", 1.0),
    ("INSS sobre a retirada dos cooperados", "pro_labore", 20.0),
]


def migrar_formato_detalhado(cfg: EVTEASConfig) -> None:
    """Converte entradas consolidadas (mão de obra genérica e alíquotas totais) para o
    formato detalhado do wizard, sem alterar o resultado do modelo."""
    e = cfg.economico
    if e.mao_obra_mes and e.mao_obra_mes > 0:
        if e.tipo_organizacao != "empresa":
            e.retirada_cooperados_mes = (e.retirada_cooperados_mes or 0.0) + e.mao_obra_mes
            base = "pro_labore"
        else:
            e.salarios_clt_por_cargo = dict(e.salarios_clt_por_cargo)
            e.salarios_clt_por_cargo["Mão de obra (não detalhada)"] = e.mao_obra_mes
            base = "folha_clt"
        if e.encargos_mao_obra_pct:
            e.impostos_configurados = list(e.impostos_configurados) + [
                {"nome": "Encargos sobre a mão de obra (consolidado)", "base": base, "aliquota_pct": e.encargos_mao_obra_pct}]
        e.mao_obra_mes = 0.0
    e.mao_obra_mes = 0.0 if (e.mao_obra_mes is None or (isinstance(e.mao_obra_mes, float) and math.isnan(e.mao_obra_mes))) else e.mao_obra_mes
    e.encargos_mao_obra_pct = 0.0
    for campo, base, nome in (("taxa_impostos_faturamento_pct", "faturamento", "Tributos sobre o faturamento (consolidado)"),
                              ("taxa_impostos_lucro_pct", "lucro", "Tributos sobre o lucro (consolidado)")):
        v = getattr(e, campo)
        if v and not (isinstance(v, float) and math.isnan(v)) and v > 0:
            e.impostos_configurados = list(e.impostos_configurados) + [{"nome": nome, "base": base, "aliquota_pct": v}]
        setattr(e, campo, 0.0)


def bloco_tributos(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("8. CONFIGURAÇÃO TRIBUTÁRIA (responda s para configurar cada tributo)")
    migrar_formato_detalhado(cfg)
    atuais = {i.get("nome"): i for i in e.impostos_configurados}
    tem_clt = bool(e.salarios_clt_por_cargo)
    tem_ret = e.retirada_cooperados_mes > 0
    novos = []
    for nome, base, sug in TRIBUTOS:
        if base == "folha_clt" and not tem_clt:
            continue
        if base == "pro_labore" and not tem_ret:
            continue
        ant = atuais.get(nome)
        dica = f" (alíquota usual: {_fmt(sug)}%)" if sug is not None else ""
        usar, _ = P.sim_nao(f"Configurar {nome}{dica}?", (ant is not None) if P.modo == "revisar" else None)
        if usar:
            aliq, _ = P.numero(f"  Alíquota de {nome}", ant.get("aliquota_pct") if ant else None, 0, 100, unidade="%")
            novos.append({"nome": nome, "base": base, "aliquota_pct": aliq})
    outros = [i for i in e.impostos_configurados if i.get("nome") not in {t[0] for t in TRIBUTOS}]
    if P.modo == "revisar" and outros:
        manter, _ = P.sim_nao(f"Manter os demais tributos já cadastrados ({', '.join(i['nome'] for i in outros)})?", True)
        if manter:
            novos += outros
    mais, _ = P.sim_nao("Incluir outro tributo ou contribuição?", False if P.modo == "revisar" else None)
    bases = [("faturamento", "Receita bruta total"), ("produtos", "Receita de produtos"), ("servicos", "Receita de serviços"),
             ("lucro", "Lucro antes de IR/CSLL"), ("folha_clt", "Folha CLT"), ("pro_labore", "Retirada dos cooperados")]
    while mais:
        nome = P.texto("  Nome do tributo")
        base, _ = P.opcao("  Base de cálculo:", bases)
        aliq, _ = P.numero("  Alíquota", None, 0, 100, unidade="%")
        novos.append({"nome": nome, "base": base, "aliquota_pct": aliq})
        mais, _ = P.sim_nao("Incluir outro tributo?", None)
    e.impostos_configurados = novos
    from .modelo import aliquotas_configuradas
    aq = aliquotas_configuradas(cfg)
    P.saida("  → Alíquotas consolidadas: " + "; ".join(f"{k} {_fmt(round(v * 100, 4))}%" for k, v in aq.items() if v))
    P.digitados.append("economico.impostos_configurados")
    _fontes_do_bloco(P, cfg, "tributos")


def bloco_projecao(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("9. RAMPA DE CAPACIDADE, PROJEÇÃO DE LONGO PRAZO E TMA")
    rampa, _ = P.sim_nao("Haverá aumento gradual da capacidade produtiva (rampa)?",
                         (e.capacidade_inicial_pct < 100) if P.modo == "revisar" else None)
    if rampa:
        P.campo_pct(cfg, "economico.capacidade_inicial_pct", "Capacidade produtiva inicial", minimo=1)
        P.campo(cfg, "economico.meses_rampa", "Meses até atingir 100% da capacidade", minimo=1, maximo=120, inteiro=True)
    else:
        e.capacidade_inicial_pct, e.meses_rampa = 100.0, 0
    P.campo(cfg, "economico.horizonte_anos", "Horizonte de análise", minimo=1, maximo=50, inteiro=True, unidade="anos")
    P.campo(cfg, "economico.crescimento_vendas_aa_pct", "Crescimento anual de vendas", minimo=-50, maximo=100, unidade="% a.a.")
    P.campo(cfg, "economico.crescimento_custos_aa_pct", "Inflação anual de custos e despesas", minimo=-50, maximo=100, unidade="% a.a.")
    P.campo(cfg, "economico.crescimento_preco_aa_pct", "Reajuste anual de preços", minimo=-50, maximo=100, unidade="% a.a.")
    P.campo(cfg, "economico.tma_aa_pct", "Taxa Mínima de Atratividade (TMA)", minimo=0, maximo=100, unidade="% a.a.")
    _fontes_do_bloco(P, cfg, "projeção")


FAIXAS_APP = [  # Lei nº 12.651/2012, art. 4º, I
    (30.0, "Curso d'água com menos de 10 m de largura — 30 m"),
    (50.0, "Curso d'água de 10 a 50 m — 50 m"),
    (100.0, "Curso d'água de 50 a 200 m — 100 m"),
    (200.0, "Curso d'água de 200 a 600 m — 200 m"),
    (500.0, "Curso d'água com mais de 600 m — 500 m"),
    (-1.0, "Outra situação (informar a faixa)"),
]


def bloco_ambiental(P: Perguntador, cfg: EVTEASConfig):
    a, t = cfg.ambiental, cfg.tecnico
    ref = SISTEMAS_PRODUTIVOS[t.sistema_produtivo]
    P.bloco("10. DIMENSÃO AMBIENTAL — ÁGUA E EFLUENTES")
    ren, origem = P.numero("Renovação diária de água", a.renovacao_pct_dia if P.modo == "revisar" else None, 0, 100,
                           referencia=ref["renovacao_pct_dia"], unidade="% do volume/dia")
    a.renovacao_pct_dia = ren
    P._registrar("ambiental.renovacao_pct_dia", origem, FONTE_SISTEMA)
    P.campo_sn(cfg, "ambiental.esvaziamento_por_ciclo", "Os viveiros são esvaziados a cada ciclo?")
    P.campo(cfg, "ambiental.evaporacao_mm_dia", "Evaporação", minimo=0, maximo=20, referencia=4.0, unidade="mm/dia",
            fonte_ref=Fonte("bibliografico", "Kubitza (2017); calibrar com dados climáticos locais"))
    P.campo(cfg, "ambiental.infiltracao_mm_dia", "Infiltração", minimo=0, maximo=50, referencia=2.0, unidade="mm/dia",
            fonte_ref=FONTE_KUBITZA)
    P.campo(cfg, "ambiental.fracao_retorno_perdida", "Fração da água devolvida a outra bacia (0 a 1)", minimo=0, maximo=1,
            referencia=0.0, fonte_ref=FONTE_AUTOR)
    P.campo_pct(cfg, "ambiental.proteina_racao_pct", "Proteína bruta da ração", minimo=1, maximo=70, referencia=32.0, fonte_ref=FONTE_KUBITZA)
    P.campo_pct(cfg, "ambiental.fosforo_racao_pct", "Fósforo da ração", maximo=10, referencia=1.0, fonte_ref=FONTE_KUBITZA)
    P.campo_pct(cfg, "ambiental.nitrogenio_peixe_pct", "Nitrogênio retido no peixe (peso vivo)", maximo=10, referencia=2.6, fonte_ref=FONTE_KUBITZA)
    P.campo_pct(cfg, "ambiental.fosforo_peixe_pct", "Fósforo retido no peixe (peso vivo)", maximo=10, referencia=0.7, fonte_ref=FONTE_KUBITZA)
    P.campo_pct(cfg, "ambiental.remocao_n_tratamento_pct", "Remoção de nitrogênio no tratamento de efluentes")
    P.campo_pct(cfg, "ambiental.remocao_p_tratamento_pct", "Remoção de fósforo no tratamento de efluentes")
    classes = [(k, f"{k} (N total {v['n_max_mg_l']} mg/L; P total {v['p_max_mg_l']} mg/L)") for k, v in CLASSES_CORPO_RECEPTOR.items()]
    classes.append(("manual", "Informar os limites manualmente"))
    atual = next((k for k, v in CLASSES_CORPO_RECEPTOR.items()
                  if v["n_max_mg_l"] == a.n_max_mg_l and v["p_max_mg_l"] == a.p_max_mg_l), "manual")
    cl, origem = P.opcao("Corpo receptor dos efluentes (Resolução CONAMA nº 357/2005):", classes,
                         atual if P.modo == "revisar" else None)
    if cl == "manual":
        P.campo(cfg, "ambiental.n_max_mg_l", "Limite de nitrogênio total", minimo=0.001, unidade="mg/L")
        P.campo(cfg, "ambiental.p_max_mg_l", "Limite de fósforo total", minimo=0.0001, unidade="mg/L")
    else:
        a.n_max_mg_l = CLASSES_CORPO_RECEPTOR[cl]["n_max_mg_l"]
        a.p_max_mg_l = CLASSES_CORPO_RECEPTOR[cl]["p_max_mg_l"]
        cfg.fontes["ambiental.n_max_mg_l"] = cfg.fontes["ambiental.p_max_mg_l"] = Fonte("normativo", f"CONAMA 357/2005 — {cl}")
    P.campo(cfg, "ambiental.n_natural_mg_l", "Concentração natural de N total no corpo receptor", minimo=0,
            maximo=a.n_max_mg_l * 0.999, referencia=min(0.5, a.n_max_mg_l * 0.5), unidade="mg/L",
            fonte_ref=Fonte("autor", "Calibrar com monitoramento local"))
    P.campo(cfg, "ambiental.p_natural_mg_l", "Concentração natural de P total no corpo receptor", minimo=0,
            maximo=a.p_max_mg_l * 0.999, referencia=min(0.02, a.p_max_mg_l * 0.5), unidade="mg/L",
            fonte_ref=Fonte("autor", "Calibrar com monitoramento local"))
    _fontes_do_bloco(P, cfg, "água e efluentes")

    P.bloco("11. DIMENSÃO AMBIENTAL — ENERGIA, EMISSÕES E RESÍDUOS")
    fontes_en = [("rede", "Rede pública"), ("solar", "Solar fotovoltaica"), ("biomassa", "Biomassa"), ("mista", "Mista (rede + renovável)")]
    a.fonte_energia, _ = P.opcao("Fonte de energia elétrica:", fontes_en, a.fonte_energia if P.modo == "revisar" else None)
    if a.fonte_energia == "mista":
        P.campo(cfg, "ambiental.fracao_renovavel_mista", "Fração renovável da energia (0 a 1)", minimo=0, maximo=1)
    if a.fonte_energia in ("rede", "mista"):
        P.campo(cfg, "ambiental.fator_emissao_rede_kgco2_kwh", "Fator de emissão da rede", minimo=0, maximo=2,
                referencia=0.0817, unidade="kgCO2e/kWh", fonte_ref=Fonte("secundario", "Fator médio do SIN (MCTI); atualizar ao ano-base"))
    P.campo(cfg, "ambiental.fator_emissao_racao_kgco2_kg", "Fator de emissão da ração", minimo=0, maximo=10,
            referencia=1.1, unidade="kgCO2e/kg", fonte_ref=Fonte("bibliografico", "Estimativa bibliográfica; validar"))
    P.campo(cfg, "ambiental.diesel_l_ano", "Consumo de diesel (geradores, veículos, despesca)", minimo=0, unidade="L/ano")
    P.campo(cfg, "ambiental.fator_emissao_diesel_kgco2_l", "Fator de emissão do diesel", minimo=0, maximo=5,
            referencia=2.6, unidade="kgCO2e/L", fonte_ref=Fonte("bibliografico", "Fator de combustão do diesel; validar"))
    P.campo(cfg, "ambiental.residuos_kg_por_kg", "Resíduos sólidos e lodo gerados", minimo=0, maximo=2, referencia=0.04,
            unidade="kg/kg de peixe", fonte_ref=FONTE_AUTOR)
    P.campo_pct(cfg, "ambiental.residuos_reaproveitados_pct", "Resíduos reaproveitados (compostagem, ração, adubo)")
    P.campo(cfg, "ambiental.energia_referencia_kwh_kg", "Consumo de energia de referência (diagnóstico Lean-Green)",
            minimo=0, referencia=0.40, unidade="kWh/kg", fonte_ref=FONTE_AUTOR)
    _fontes_do_bloco(P, cfg, "energia e resíduos")

    P.bloco("12. DIMENSÃO AMBIENTAL — CONFORMIDADE (checklist normativo)")
    P.campo(cfg, "ambiental.distancia_app_m", "Distância das instalações até a Área de Preservação Permanente", minimo=0, unidade="m")
    faixa_atual = next((f for f, _ in FAIXAS_APP if f == a.faixa_app_minima_m), -1.0)
    faixa, _ = P.opcao("Faixa mínima de APP aplicável (Lei nº 12.651/2012):", [(f, d) for f, d in FAIXAS_APP],
                       faixa_atual if P.modo == "revisar" else None)
    if faixa < 0:
        P.campo(cfg, "ambiental.faixa_app_minima_m", "Faixa mínima de APP", minimo=0, unidade="m")
    else:
        a.faixa_app_minima_m = faixa
        cfg.fontes["ambiental.faixa_app_minima_m"] = Fonte("normativo", "Lei nº 12.651/2012, art. 4º, I")
    for chave, (descricao, _, elim) in CHECKLIST_AMBIENTAL.items():
        marca = " [ELIMINATÓRIO]" if elim else ""
        v, _ = P.sim_nao(f"{descricao}{marca}", a.checklist.get(chave) if P.modo == "revisar" else None)
        a.checklist[chave] = v
    if a.checklist.get("respeita_app") and a.distancia_app_m < a.faixa_app_minima_m:
        P.saida("  ⚠ A distância informada é menor que a faixa mínima de APP: o item será considerado NÃO atendido.")
    _fontes_do_bloco(P, cfg, "conformidade")


RELACOES = [("inexistente", "Inexistente"), ("parcial", "Parcial (contatos eventuais)"),
            ("consolidado", "Consolidado (canal permanente e acordos)")]


def bloco_social(P: Perguntador, cfg: EVTEASConfig):
    s, e = cfg.social, cfg.economico
    P.bloco("13. DIMENSÃO SOCIAL — EMPREGO, RENDA E RELAÇÃO COM A COMUNIDADE")
    sug = e.cooperados_trabalhadores + len(e.salarios_clt_por_cargo)
    P.campo(cfg, "social.empregos_diretos", "Empregos diretos", minimo=0, inteiro=True,
            referencia=sug if sug else None, fonte_ref=FONTE_AUTOR)
    P.campo(cfg, "social.empregos_indiretos", "Empregos indiretos", minimo=0, inteiro=True)
    P.campo_pct(cfg, "social.mao_obra_local_pct", "Mão de obra residente no município/comunidade")
    P.campo_pct(cfg, "social.compras_locais_pct", "Compras de insumos e serviços feitas localmente")
    P.campo(cfg, "social.salario_minimo", "Salário mínimo vigente", minimo=1, referencia=1518.0, unidade="R$",
            fonte_ref=Fonte("normativo", "Salário mínimo nacional vigente"))
    P.campo(cfg, "social.capacitacao_horas_pessoa_ano", "Capacitação", minimo=0, unidade="h/pessoa/ano")
    P.campo_pct(cfg, "social.conformidade_nr_pct", "Aderência às Normas Regulamentadoras (NR)")
    s.relacao_comunidade, _ = P.opcao("Relação com a comunidade e pescadores artesanais:", RELACOES,
                                      s.relacao_comunidade if P.modo == "revisar" else None)
    P.campo_sn(cfg, "social.canais_formais_comunicacao", "Existem canais formais de comunicação com a comunidade?")
    P.campo(cfg, "social.reunioes_comunidade_ano", "Reuniões com a comunidade por ano", minimo=0, maximo=365, inteiro=True)
    P.campo(cfg, "social.conflitos_registrados_ano", "Conflitos com stakeholders registrados por ano", minimo=0, inteiro=True)
    P.campo_pct(cfg, "social.mulheres_pct", "Participação de mulheres na equipe")
    P.campo_pct(cfg, "social.jovens_pct", "Participação de jovens (até 29 anos) na equipe")
    P.campo_sn(cfg, "social.publico_vulneravel", "O público beneficiário é vulnerável (ex.: pescadores artesanais, PGTR)?")
    _fontes_do_bloco(P, cfg, "social")

    P.bloco("14. GOVERNANÇA (pilar G do ESG)")
    rotulos = {
        "estatuto_regimento": "Estatuto ou regimento interno aprovado",
        "assembleias_regulares": "Assembleias/reuniões deliberativas regulares",
        "conselho_fiscal": "Conselho fiscal ou instância de controle",
        "prestacao_contas_publica": "Prestação de contas pública",
        "plano_negocios_aprovado": "Plano de negócios aprovado",
        "registro_auditavel_premissas": "Registro auditável das premissas do estudo",
        "canal_denuncia_ouvidoria": "Canal de denúncia ou ouvidoria",
    }
    for chave, rot in rotulos.items():
        v, _ = P.sim_nao(rot, cfg.governanca.itens.get(chave) if P.modo == "revisar" else None)
        cfg.governanca.itens[chave] = v


DIMENSOES_ROTULOS = [("tecnico", "Técnica"), ("economico", "Econômica"), ("ambiental", "Ambiental"), ("social", "Social")]


def bloco_pesos(P: Perguntador, cfg: EVTEASConfig):
    p = cfg.pesos
    P.bloco("15. PESOS DO ÍNDICE EVTEAS E REGRAS DE DECISÃO")
    metodos = [("preset", "Informar diretamente os pesos das quatro dimensões"),
               ("likert", "Escala Likert de 1 a 5 atribuída por avaliadores (Quadro 7)"),
               ("ahp", "Comparação par a par (AHP — Saaty)")]
    p.metodo, _ = P.opcao("Método de ponderação:", metodos, p.metodo if P.modo == "revisar" else None)
    if p.metodo == "preset":
        P.saida("Os pesos serão normalizados para somar 1.")
        for d, nome in DIMENSOES_ROTULOS:
            P.campo(cfg, f"pesos.{d}", f"Peso da dimensão {nome}", minimo=0)
        if p.tecnico + p.economico + p.ambiental + p.social <= 0:
            P.saida("  ⚠ A soma dos pesos deve ser positiva; adotados pesos iguais.")
            p.tecnico = p.economico = p.ambiental = p.social = 1.0
    elif p.metodo == "likert":
        P.saida("Escala: 1 irrelevante · 2 pouco relevante · 3 moderadamente relevante · 4 muito relevante · 5 essencial")
        antigos = list(p.likert_dimensoes.items())
        n_av, _ = P.numero("Número de avaliadores", len(antigos) if (P.modo == "revisar" and antigos) else None, 1, 20, inteiro=True)
        lk = {}
        for i in range(n_av):
            nome_ant, esc_ant = antigos[i] if (P.modo == "revisar" and i < len(antigos)) else (None, {})
            nome = P.texto(f"Nome/área do avaliador nº {i + 1}", nome_ant)
            lk[nome] = {}
            for d, rot in DIMENSOES_ROTULOS:
                lk[nome][d], _ = P.numero(f"  {nome} — relevância da dimensão {rot}", esc_ant.get(d), 1, 5, inteiro=True)
        p.likert_dimensoes = lk
        usar_kpi, _ = P.sim_nao("Os avaliadores também pontuarão cada KPI dentro das dimensões?",
                                bool(p.likert_kpis) if P.modo == "revisar" else None)
        if usar_kpi:
            kp = {}
            for nome in lk:
                kp[nome] = {}
                for d, kpis in KPIS_POR_DIMENSAO.items():
                    for k in kpis:
                        kp[nome][k], _ = P.numero(f"  {nome} — relevância do KPI {k} ({d})",
                                                  p.likert_kpis.get(nome, {}).get(k), 1, 5, inteiro=True)
            p.likert_kpis = kp
        else:
            p.likert_kpis = {}
    else:
        from .ponderacao import pesos_ahp
        P.saida("Escala de Saaty: 1 igual · 3 moderada · 5 forte · 7 muito forte · 9 extrema; use 1/3, 1/5... quando a "
                "segunda dimensão for mais importante.")
        while True:
            A = np.ones((4, 4))
            for i in range(4):
                for j in range(i + 1, 4):
                    ant = p.ahp_matriz[i][j] if (P.modo == "revisar" and p.ahp_matriz) else None
                    v, _ = P.numero(f"Importância de {DIMENSOES_ROTULOS[i][1]} em relação a {DIMENSOES_ROTULOS[j][1]}", ant, 1 / 9, 9)
                    A[i, j], A[j, i] = v, 1 / v
            res = pesos_ahp(A)
            P.saida(f"  → Pesos: " + "; ".join(f"{n} {w:.3f}" for (_, n), w in zip(DIMENSOES_ROTULOS, res["pesos"]))
                    + f" | razão de consistência = {res['rc']:.3f}")
            p.ahp_matriz = A.tolist()
            if res["consistente"]:
                break
            refazer, _ = P.sim_nao("  ⚠ RC > 0,10 (julgamentos inconsistentes). Refazer as comparações?", None)
            if not refazer:
                break
    d = cfg.decisao
    P.campo(cfg, "decisao.limiar_indice_viavel", "Índice EVTEAS mínimo para 'VIÁVEL'", 0, 1, referencia=0.60, fonte_ref=FONTE_AUTOR)
    P.campo(cfg, "decisao.limiar_indice_ressalvas", "Índice EVTEAS mínimo para 'VIÁVEL COM RESSALVAS'", 0,
            d.limiar_indice_viavel, referencia=min(0.50, d.limiar_indice_viavel), fonte_ref=FONTE_AUTOR)
    pmin, origem = P.numero("Probabilidade mínima de VPL positivo no Monte Carlo",
                            d.prob_vpl_positivo_minima * 100 if P.modo == "revisar" else None, 0, 100,
                            referencia=70.0, unidade="%")
    d.prob_vpl_positivo_minima = pmin / 100
    P.campo(cfg, "decisao.lso_minimo", "LSO mínima (0–100)", 0, 100, referencia=40.0, fonte_ref=FONTE_AUTOR)
    P.campo_sn(cfg, "decisao.aplicar_vetos", "Aplicar vetos não compensatórios (VPL < 0, item eliminatório, LSO baixa)?",
               referencia=True)


VARIAVEIS_INCERTAS = [
    ("economico.preco_venda_kg", "Preço de venda (R$/kg)"),
    ("economico.custo_racao_kg", "Custo da ração (R$/kg)"),
    ("economico.custo_alevino_milheiro", "Custo do milheiro de alevinos (R$)"),
    ("economico.tarifa_energia_kwh", "Tarifa de energia (R$/kWh)"),
    ("economico.custos_fixos_fator", "Fator multiplicador dos custos fixos (1 = valor informado)"),
    ("tecnico.fcr", "FCR"),
    ("tecnico.mortalidade_pct", "Mortalidade (%)"),
    ("tecnico.desempenho_crescimento_pct", "Desempenho de crescimento (%)"),
]
TIPOS_DIST = [("triangular", "Triangular (mínimo, mais provável, máximo)"),
              ("uniforme", "Uniforme (apenas mínimo e máximo conhecidos)"),
              ("normal", "Normal truncada em [mínimo, máximo]"),
              ("fixa", "Sem incerteza (valor fixo)")]


def _perguntar_distribuicao(P: Perguntador, cfg: EVTEASConfig, caminho: str, rotulo: str, atual: Optional[Distribuicao]):
    base = float(obter_por_caminho(cfg, caminho))
    P.saida(f"\n{rotulo} — valor determinístico informado: {_fmt(base)}")
    tipo, _ = P.opcao("  Tipo de distribuição:", TIPOS_DIST, atual.tipo if (P.modo == "revisar" and atual) else None)
    if tipo == "fixa":
        return Distribuicao("fixa", base, base, base)
    while True:
        mn, _ = P.numero("  Mínimo", atual.minimo if (P.modo == "revisar" and atual) else None)
        moda = base
        if tipo in ("triangular", "normal"):
            moda, _ = P.numero("  Mais provável", atual.moda if (P.modo == "revisar" and atual) else None, referencia=base)
        mx, _ = P.numero("  Máximo", atual.maximo if (P.modo == "revisar" and atual) else None)
        try:
            return Distribuicao(tipo, mn, moda if tipo != "uniforme" else (mn + mx) / 2, mx).validar()
        except ValueError as exc:
            P.saida(f"  ⚠ {exc}. Informe novamente.")


def bloco_incerteza(P: Perguntador, cfg: EVTEASConfig):
    mc = cfg.monte_carlo
    P.bloco("16. INCERTEZA — SIMULAÇÃO DE MONTE CARLO")
    P.saida("Para cada variável, escolha a distribuição: uniforme quando só os limites são conhecidos; triangular "
            "quando também há um valor mais provável (Oliveira; Medeiros Neto, 2012).")
    P.campo(cfg, "monte_carlo.iteracoes", "Número de iterações", minimo=100, maximo=200000, inteiro=True,
            referencia=10000, fonte_ref=FONTE_AUTOR)
    P.campo(cfg, "monte_carlo.seed", "Semente aleatória (seed) para reprodutibilidade", minimo=0, inteiro=True,
            referencia=20260612, fonte_ref=FONTE_AUTOR)
    novas: Dict[str, Distribuicao] = {}
    for caminho, rotulo in VARIAVEIS_INCERTAS:
        novas[caminho] = _perguntar_distribuicao(P, cfg, caminho, rotulo, mc.distribuicoes.get(caminho))
    lo, hi = FAIXAS_AACE[int(cfg.economico.classe_estimativa_aace)]
    P.saida(f"\nCAPEX: a estimativa Classe {cfg.economico.classe_estimativa_aace} da AACE implica faixa de "
            f"{int(lo * 100)}% a +{int(hi * 100)}%.")
    usar_aace, _ = P.sim_nao("Usar essa faixa para a incerteza do CAPEX?",
                             ("economico.capex_fator" not in mc.distribuicoes) if P.modo == "revisar" else True)
    mc.incluir_capex_aace = usar_aace
    if not usar_aace:
        novas["economico.capex_fator"] = _perguntar_distribuicao(P, cfg, "economico.capex_fator",
                                                                 "Fator multiplicador do CAPEX (1 = valor informado)",
                                                                 mc.distribuicoes.get("economico.capex_fator"))
    extras = [c for c in caminhos_numericos(cfg) if c not in novas and c != "economico.capex_fator"]
    for c, d in mc.distribuicoes.items():   # preserva variáveis extras já cadastradas
        if c not in novas and c in extras and P.modo == "revisar":
            manter, _ = P.sim_nao(f"Manter a distribuição já cadastrada para {c}?", True)
            if manter:
                novas[c] = d
    mais, _ = P.sim_nao("Incluir incerteza em outro parâmetro?", False)
    while mais:
        for k, c in enumerate(extras, 1):
            P.saida(f"  {k}. {c} = {_fmt(obter_por_caminho(cfg, c))}")
        k, _ = P.numero("Número do parâmetro", None, 1, len(extras), inteiro=True)
        novas[extras[k - 1]] = _perguntar_distribuicao(P, cfg, extras[k - 1], extras[k - 1], None)
        mais, _ = P.sim_nao("Incluir outro parâmetro?", None)
    mc.distribuicoes = novas


BLOCOS = [
    ("Identificação", bloco_identificacao), ("Técnico", bloco_tecnico), ("Investimento", bloco_investimento),
    ("Mix e receitas", bloco_receitas), ("Custos operacionais", bloco_custos), ("Pessoas", bloco_pessoas),
    ("Tributos", bloco_tributos), ("Projeção e TMA", bloco_projecao), ("Ambiental", bloco_ambiental),
    ("Social e governança", bloco_social), ("Pesos e decisão", bloco_pesos), ("Incerteza (Monte Carlo)", bloco_incerteza),
]


# ---------------------------------------------------------------------------
# Resumo, confirmação e ponto de entrada
# ---------------------------------------------------------------------------

def resumo_entradas(cfg: EVTEASConfig) -> pd.DataFrame:
    from .modelo import Contexto, aliquotas_configuradas, calcular_tecnico, remuneracao_mensal
    t, e, a = cfg.tecnico, cfg.economico, cfg.ambiental
    tec = calcular_tecnico(Contexto(cfg))
    rem = remuneracao_mensal(cfg)
    aq = aliquotas_configuradas(cfg)
    linhas = [
        ("Projeto", cfg.projeto), ("Organização", e.tipo_organizacao),
        ("Sistema / espécie", f"{t.sistema_produtivo} / {t.especie}"),
        ("Lâmina d'água / volume", f"{_fmt(t.area_lamina_m2)} m² / {_fmt(round(t.volume_util_m3, 1))} m³"),
        ("Viveiros (ativos/total)", f"{t.tanques_ativos}/{t.numero_tanques}"),
        ("Peso inicial → final; ciclo", f"{_fmt(t.peso_inicial_g)} g → {_fmt(t.peso_final_g)} g; {t.ciclo_dias} dias; {_fmt(t.ciclos_ano)} ciclos/ano"),
        ("FCR; mortalidade", f"{_fmt(t.fcr)}; {_fmt(t.mortalidade_pct)}%"),
        ("Produção técnica estimada", f"{_fmt(round(float(tec['producao_kg_ano'][0]), 1))} kg/ano"),
        ("Volume de vendas", "mix informado" if e.producao_vendas_kg_mes > 0 else "produção técnica"),
        ("Preço médio", f"R$ {_fmt(round(e.preco_venda_kg, 4))}/kg"),
        ("CAPEX (classe AACE)", f"R$ {_fmt(e.capex_total)} (Classe {e.classe_estimativa_aace})"),
        ("Fomento não reembolsável", f"{_fmt(e.fomento_nao_reembolsavel_pct)}% do CAPEX"),
        ("Ração; alevino; energia", f"R$ {_fmt(e.custo_racao_kg)}/kg; R$ {_fmt(e.custo_alevino_milheiro)}/milheiro; R$ {_fmt(e.tarifa_energia_kwh)}/kWh"),
        ("Remuneração mensal (CLT / retiradas / outras)", f"R$ {_fmt(rem['clt'])} / R$ {_fmt(rem['retirada'])} / R$ {_fmt(rem['outros'])}"),
        ("Tributos (faturamento / lucro)", f"{_fmt(round((aq['faturamento'] + aq['produtos']) * 100, 4))}% / {_fmt(round(aq['lucro'] * 100, 4))}%"),
        ("TMA; horizonte", f"{_fmt(e.tma_aa_pct)}% a.a.; {e.horizonte_anos} anos"),
        ("Energia; remoção de P", f"{a.fonte_energia}; {_fmt(a.remocao_p_tratamento_pct)}%"),
        ("Pesos", cfg.pesos.metodo),
        ("Monte Carlo", f"{cfg.monte_carlo.iteracoes} iterações; {len(cfg.monte_carlo.distribuicoes)} variáveis incertas"),
        ("Premissas com origem registrada", str(len(cfg.fontes))),
    ]
    return pd.DataFrame(linhas, columns=["Entrada", "Valor"])


BLOCOS_EM_BRANCO = ("tecnico", "economico", "ambiental", "social", "decisao", "monte_carlo")
NEUTROS = {  # parâmetros que não são perguntas (multiplicadores da incerteza) ou só se aplicam em certos casos
    "economico.capex_fator": 1.0, "economico.custos_fixos_fator": 1.0,
}


def config_em_branco() -> EVTEASConfig:
    """Configuração sem nenhum valor numérico: todo parâmetro precisa vir da entrada."""
    from dataclasses import fields as campos
    cfg = EVTEASConfig(projeto="", autor="")
    for bloco in BLOCOS_EM_BRANCO:
        obj = getattr(cfg, bloco)
        for f in campos(obj):
            v = getattr(obj, f.name)
            if (isinstance(v, (int, float)) and not isinstance(v, bool)) or (v is None and bloco == "tecnico"):
                setattr(obj, f.name, float("nan"))
            elif isinstance(v, bool):
                setattr(obj, f.name, None)
    e = cfg.economico
    e.capex_itens, e.mix_produtos, e.impostos_configurados, e.salarios_clt_por_cargo = {}, [], [], {}
    cfg.ambiental.checklist = {k: None for k in cfg.ambiental.checklist}
    cfg.ambiental.renovacao_pct_dia = cfg.ambiental.energia_kwh_kg = float("nan")
    cfg.governanca.itens = {k: None for k in cfg.governanca.itens}
    cfg.monte_carlo.distribuicoes = {}
    cfg.fontes = {}
    for caminho, valor in NEUTROS.items():
        definir_por_caminho(cfg, caminho, valor)
    return cfg


def entradas_pendentes(cfg: EVTEASConfig) -> List[str]:
    """Lista parâmetros que continuam vazios (NaN/None) após o wizard."""
    from dataclasses import fields as campos
    faltam = []
    for bloco in BLOCOS_EM_BRANCO:
        obj = getattr(cfg, bloco)
        for f in campos(obj):
            v = getattr(obj, f.name)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                faltam.append(f"{bloco}.{f.name}")
    faltam += [f"ambiental.checklist.{k}" for k, v in cfg.ambiental.checklist.items() if v is None]
    faltam += [f"governanca.itens.{k}" for k, v in cfg.governanca.itens.items() if v is None]
    if not cfg.economico.capex_itens:
        faltam.append("economico.capex_itens")
    if not cfg.economico.mix_produtos:
        faltam.append("economico.mix_produtos")
    return faltam


def _completar_condicionais(cfg: EVTEASConfig) -> None:
    """Valores que só são perguntados em certas situações recebem o valor neutro correspondente."""
    a = cfg.ambiental
    if a.fonte_energia != "mista":
        a.fracao_renovavel_mista = 0.0
    if a.fonte_energia not in ("rede", "mista") and (a.fator_emissao_rede_kgco2_kwh is None or math.isnan(a.fator_emissao_rede_kgco2_kwh)):
        a.fator_emissao_rede_kgco2_kwh = 0.0817     # não utilizado com fonte solar ou biomassa


def wizard_evteas(entrada: Callable[[str], str] = input, base: Optional[EVTEASConfig] = None,
                  saida: Callable[..., None] = print, blocos: Optional[Sequence[str]] = None) -> EVTEASConfig:
    """Wizard completo. Sem ``base``: modo NOVO (valores obrigatórios). Com ``base``: modo REVISAR."""
    if base is None:
        cfg = config_em_branco()
        P = Perguntador(entrada, saida, "novo")
        saida("=" * 78 + "\nEVTEAS-Py — ENTRADA COMPLETA DE DADOS (novo projeto)\n" + "=" * 78)
        saida("Todos os valores do projeto são obrigatórios. Use vírgula ou ponto decimal; digite 'sair' para interromper.")
    else:
        cfg = base
        P = Perguntador(entrada, saida, "revisar")
        saida("=" * 78 + "\nEVTEAS-Py — REVISÃO DAS ENTRADAS (Enter mantém o valor entre colchetes)\n" + "=" * 78)
    for nome, func in BLOCOS:
        if blocos is None or nome in blocos:
            func(P, cfg)
    _completar_condicionais(cfg)
    if base is None:
        faltam = entradas_pendentes(cfg)
        if faltam:
            raise RuntimeError("Entradas não preenchidas pelo wizard: " + ", ".join(faltam))
    return cfg


def definir_e_comparar_alternativas(cfg: EVTEASConfig, entrada: Callable[[str], str] = input,
                                    saida: Callable[..., None] = print, n_mc: Optional[int] = None):
    """Compara o projeto informado com alternativas definidas pelo usuário (TOPSIS)."""
    import copy
    from .pipeline import comparar_alternativas
    P = Perguntador(entrada, saida, "novo")
    quer, _ = P.sim_nao("Deseja comparar o projeto com alternativas de projeto (TOPSIS)?")
    if not quer:
        return None
    alternativas = {cfg.projeto or "Projeto informado": copy.deepcopy(cfg)}
    n, _ = P.numero("Quantas alternativas adicionais", None, 1, 5, inteiro=True)
    opcoes = [(nome, nome) for nome, _ in BLOCOS if nome != "Identificação"] + [("fim", "Concluir esta alternativa")]
    for i in range(n):
        nome = P.texto(f"\nNome da alternativa {i + 1}")
        alt = copy.deepcopy(cfg)
        alt.projeto = nome
        while True:
            bloco, _ = P.opcao(f"Bloco a alterar em '{nome}':", opcoes)
            if bloco == "fim":
                break
            alt = wizard_evteas(entrada, alt, saida, blocos=[bloco])
        alternativas[nome] = alt
    criterios = ["VPL (R$)", "P(VPL>0)", "OEE", "PH cinza (m³/t)", "Intensidade carbono (kgCO2e/kg)", "LSO", "RVL (%)"]
    pesos = None
    informar, _ = P.sim_nao("Informar os pesos dos critérios do TOPSIS (n = pesos padrão)?")
    if informar:
        pesos = {c: P.numero(f"  Peso do critério {c}", None, 0)[0] for c in criterios}
        if sum(pesos.values()) <= 0:
            saida("  ⚠ Soma dos pesos nula; usando pesos padrão.")
            pesos = None
    return comparar_alternativas(alternativas, pesos, n_mc=n_mc or min(cfg.monte_carlo.iteracoes, 5000))


def _baixar_no_colab(caminho: str):
    try:
        from google.colab import files  # type: ignore
        files.download(caminho)
    except Exception:
        pass


def _carregar_arquivo(entrada: Callable[[str], str], saida) -> EVTEASConfig:
    try:
        from google.colab import files  # type: ignore
        saida("Selecione o arquivo JSON de entradas salvo anteriormente.")
        enviado = files.upload()
        nome, conteudo = next(iter(enviado.items()))
        return config_de_dict(json.loads(conteudo.decode("utf-8")))
    except ImportError:
        pass
    while True:
        caminho = entrada("Caminho do arquivo JSON de entradas: ").strip().strip('"').strip("'")
        if caminho.lower() in ("sair", "cancelar"):
            raise EntradaCancelada("entrada interrompida pelo usuário")
        try:
            return carregar_config(caminho)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            saida(f"  ⚠ Não foi possível ler o arquivo ({exc}). Tente novamente.")


def iniciar_entradas(entrada: Callable[[str], str] = input, saida: Callable[..., None] = print,
                     salvar: bool = True, pasta_saida: str = ".") -> EVTEASConfig:
    """Ponto de partida do estudo: nenhum resultado é calculado antes das entradas."""
    saida("=" * 78 + "\nEVTEAS-Py — INÍCIO DO ESTUDO\n" + "=" * 78)
    P = Perguntador(entrada, saida, "novo")
    modo, _ = P.opcao("Como deseja informar os dados do projeto?", [
        ("novo", "Novo projeto — digitar todas as entradas"),
        ("arquivo", "Carregar arquivo de entradas (JSON) e revisar"),
        ("exemplo", "Exemplo ilustrativo da dissertação (apenas demonstração)"),
    ])
    if modo == "novo":
        cfg = wizard_evteas(entrada, None, saida)
    elif modo == "arquivo":
        cfg = _carregar_arquivo(entrada, saida)
        revisar, _ = P.sim_nao("Revisar as entradas carregadas bloco a bloco?", None)
        if revisar:
            cfg = wizard_evteas(entrada, cfg, saida)
    else:
        cfg = criar_config_caso_base()
        saida("⚠ Exemplo ilustrativo carregado: os resultados NÃO representam o seu projeto.")
    while True:
        saida("\nResumo das entradas:")
        saida(resumo_entradas(cfg).to_string(index=False))
        acao, _ = P.opcao("\nO que deseja fazer?", [("executar", "Confirmar e executar a análise"),
                                                     ("editar", "Corrigir um bloco de entradas"),
                                                     ("sair", "Salvar as entradas e encerrar sem executar")])
        if acao == "editar":
            nomes = [(n, n) for n, _ in BLOCOS]
            bloco, _ = P.opcao("Bloco a corrigir:", nomes)
            cfg = wizard_evteas(entrada, cfg, saida, blocos=[bloco])
            continue
        break
    if salvar:
        caminho = str(Path(pasta_saida) / nome_arquivo(cfg))
        salvar_config(cfg, caminho)
        saida(f"Entradas salvas em: {caminho} (use a opção 2 para reabrir e revisar).")
        _baixar_no_colab(caminho)
    if acao == "sair":
        raise EntradaCancelada("entradas salvas; análise não executada")
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
            out["preco_otimo"] = float((custo_unitario - a / b) / 2)   # max (P − c)(a + bP)
    return out

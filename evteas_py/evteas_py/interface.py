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

O wizard incorpora os campos dos estudos de viabilidade econômica em notebook
utilizados pelo autor: tipo de organização, mix de produtos com
quantidades e preços, serviços de transporte, carência, custos, cooperados,
funcionários CLT por cargo, tributos individuais, rampa, crescimento e TMA. Acrescenta os
parâmetros técnico-ambientais-sociais, a governança, os pesos (preset,
Likert ou AHP), as regras de decisão, as distribuições do Monte Carlo e a
origem das premissas (Seção 3.6).
"""
from __future__ import annotations

import copy
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
                     SocialConfig, TecnicoConfig, VARIAVEIS_ESTOCASTICAS, config_de_dict, config_para_dict,
                     definir_por_caminho, obter_por_caminho)
from .casos import criar_config_caso_base

LINHA = "-" * 78


# ---------------------------------------------------------------------------
# Arquivos de entradas
# ---------------------------------------------------------------------------

def salvar_config(cfg: EVTEASConfig, caminho) -> str:
    Path(caminho).write_text(json.dumps(config_para_dict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(caminho)


def carregar_config(caminho, avisos: Optional[List[str]] = None, permitir_pendentes: bool = False) -> EVTEASConfig:
    """Lê um arquivo de entradas (aceita arquivos incompletos e o JSON de resultados).

    Campos ausentes não são completados com o caso ilustrativo: ficam pendentes e, salvo
    ``permitir_pendentes``, impedem a leitura. Os avisos vão para ``avisos`` (ou ``warnings``)."""
    cfg, msgs, pendentes = ler_entradas(json.loads(Path(caminho).read_text(encoding="utf-8-sig")))
    if avisos is not None:
        avisos.extend(msgs)
    else:
        import warnings
        for m in msgs:
            warnings.warn(m, stacklevel=2)
    if pendentes and not permitir_pendentes:
        raise ValueError("entradas ausentes no arquivo: " + ", ".join(pendentes))
    return cfg


def nome_arquivo(cfg: EVTEASConfig) -> str:
    import unicodedata
    ascii_ = unicodedata.normalize("NFKD", cfg.projeto or "").encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "_", ascii_).strip("_")
    if len(base) > 60:                      # nomes longos parecidos não se sobrescrevem
        import hashlib
        base = base[:53].rstrip("_") + "_" + hashlib.sha1((cfg.projeto or "").encode("utf-8")).hexdigest()[:6]
    return f"entradas_{base or 'projeto'}.json"


# ---------------------------------------------------------------------------
# Leitura de valores digitados
# ---------------------------------------------------------------------------

MILHAR_COM_PONTO = re.compile(r"-?[1-9]\d{0,2}(?:\.\d{3})+")    # 40.000 · 1.234.567 (padrão brasileiro)


def usa_ponto_de_milhar(txt: str) -> bool:
    t = txt.strip().replace("R$", "").replace("%", "").replace(" ", "")
    return "," not in t and bool(MILHAR_COM_PONTO.fullmatch(t))


def converter_numero(txt: str) -> float:
    """Aceita 1234,56 · 1.234,56 · 40.000 · 1.234.567 · 1234.56 · 1,234.56 · 12% · R$ 10 · frações como 1/3.

    Ponto seguido de grupos de exatamente três dígitos (40.000) é separador de milhar,
    como no padrão brasileiro; nos demais casos (10.5, 0.280), ponto é decimal."""
    t = txt.strip().replace("R$", "").replace("%", "").replace(" ", "")
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?/\d+(?:[.,]\d+)?", t):
        a, b = t.split("/")
        return converter_numero(a) / converter_numero(b)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    elif MILHAR_COM_PONTO.fullmatch(t):
        t = t.replace(".", "")
    v = float(t)
    if not math.isfinite(v):
        raise ValueError("valor não finito")
    return v


def _fmt(v, casas: int = 6) -> str:
    """Número no padrão brasileiro (1.500.000; 0,28), sem notação científica."""
    if isinstance(v, (bool, np.bool_)):
        return "s" if v else "n"
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}".replace(",", ".")
    if isinstance(v, (float, np.floating)):
        v = float(v)
        if not math.isfinite(v):
            return "—"
        if v != 0 and abs(v) < 10 ** -casas:
            return f"{v:.3g}".replace(".", ",")
        s = f"{v:,.{casas}f}".rstrip("0").rstrip(".")
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return "0" if s in ("-0", "") else s
    return str(v)


def vazio(v) -> bool:
    """Valor ainda não informado (None ou NaN), que não pode servir de padrão."""
    return v is None or (isinstance(v, (float, np.floating)) and math.isnan(v))


class EntradaCancelada(Exception):
    """Levantada quando o usuário digita 'sair' ou encerra sem executar a análise.

    No Jupyter/Colab, aparece como uma mensagem curta, e não como traceback."""

    def _render_traceback_(self):
        return [f"⚠ {self}"]


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
        self.rotulos: Dict[str, str] = dict(ROTULOS_CAMINHOS)   # caminho -> rótulo exibido ao usuário

    # -- leitura bruta -------------------------------------------------------
    def _ler(self, prompt: str) -> str:
        txt = self.entrada(prompt)
        txt = "" if txt is None else str(txt).strip()
        if txt.lower() in ("sair", "cancelar"):
            raise EntradaCancelada("entrada interrompida pelo usuário")
        return txt

    def _sufixo(self, atual, referencia):
        if self.modo == "revisar" and not vazio(atual):
            return f" [{_fmt(atual)}]"
        if referencia is not None:
            return f" [referência: {_fmt(referencia)} — Enter aceita]"
        return ""

    def _padrao(self, atual, referencia):
        if self.modo == "revisar" and not vazio(atual):
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
                    self.saida("  ⚠ Valor inválido. Use apenas números, por exemplo 1500, 1.500 ou 1.500,50.")
                    continue
                if usa_ponto_de_milhar(txt):
                    self.saida(f"  → lido como {_fmt(v)} (ponto como separador de milhar; para decimais use vírgula)")
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
        curto = lambda i: opcoes[i - 1][1] if len(opcoes[i - 1][1]) <= 45 else opcoes[i - 1][1][:44] + "…"
        if self.modo == "revisar" and idx_atual is not None:
            sufixo = f" [{idx_atual}: {curto(idx_atual)}]"
        elif idx_ref is not None:
            sufixo = f" [referência: {idx_ref}: {curto(idx_ref)} — Enter aceita]"
        else:
            sufixo = ""
        while True:
            txt = self._ler(f"Opção (1–{len(opcoes)}){sufixo}: ")
            if not txt:
                v, origem = self._padrao(idx_atual, idx_ref)
                if v is None:
                    self.saida("  ⚠ Escolha obrigatória.")
                    continue
                return chaves[v - 1], origem
            if txt.isdecimal() and 1 <= int(txt) <= len(opcoes):
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
        self.rotulos[caminho] = rotulo + (f" ({unidade})" if unidade else "")
        atual = obter_por_caminho(cfg, caminho)
        v, origem = self.numero(rotulo, atual, minimo, maximo, inteiro, referencia, unidade)
        definir_por_caminho(cfg, caminho, v)
        self._registrar(caminho, origem, fonte_ref)
        return v

    def campo_pct(self, cfg, caminho, rotulo, minimo=0.0, maximo=100.0, referencia=None, fonte_ref=None) -> float:
        return self.campo(cfg, caminho, rotulo, minimo, maximo, False, referencia, "%", fonte_ref)

    def campo_sn(self, cfg, caminho, rotulo, referencia=None) -> bool:
        self.rotulos[caminho] = rotulo
        v, origem = self.sim_nao(rotulo, obter_por_caminho(cfg, caminho), referencia)
        definir_por_caminho(cfg, caminho, v)
        return v

    def bloco(self, titulo: str):
        self.saida("\n" + LINHA + f"\n{titulo}\n" + LINHA)
        self.digitados = []


ROTULOS_CAMINHOS = {  # parâmetros perguntados sem P.campo (montados a partir de várias respostas)
    "tecnico.profundidade_media_m": "Volume útil (profundidade média)",
    "tecnico.capacidade_suporte_kg_m3": "Capacidade de suporte (kg/m³)",
    "economico.capex_itens": "Itens de CAPEX",
    "economico.classe_estimativa_aace": "Maturidade da estimativa de CAPEX (AACE)",
    "economico.valor_residual_rs": "Valor residual (R$)",
    "economico.mix_produtos": "Mix de produtos (quantidades e preços)",
    "economico.preco_venda_kg": "Preço médio de venda (R$/kg)",
    "economico.receita_servicos_mes": "Receita de serviços (R$/mês)",
    "economico.meses_ate_primeira_receita": "Meses até a primeira receita",
    "economico.custo_alevino_milheiro": "Custo do alevino (R$/un)",
    "ambiental.energia_kwh_kg": "Consumo de energia (kWh/kg)",
    "economico.manutencao_mes": "Manutenção (R$/mês)",
    "economico.salarios_clt_por_cargo": "Salários dos funcionários CLT",
    "economico.impostos_configurados": "Tributos e alíquotas",
    "ambiental.renovacao_pct_dia": "Renovação diária de água (%)",
}
ROTULOS_KPI = {
    "oee": "OEE aquícola", "fcr": "Conversão alimentar (FCR)", "produtividade": "Produtividade relativa",
    "vpl": "VPL sobre o investimento", "roi": "ROI anual", "margem_seguranca": "Margem de segurança",
    "ph_azul": "Pegada hídrica azul", "ph_cinza": "Pegada hídrica cinza", "ecoeficiencia": "Ecoeficiência",
    "intensidade_carbono": "Intensidade de carbono", "conformidade": "Conformidade ambiental",
    "lso": "Licença Social para Operar (LSO)", "rvl": "Retenção de Valor Local (RVL)", "radar_social": "Radar Social",
}
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
            P.saida(f"  {k}. {P.rotulos.get(c, c)}")
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
    sistemas = [(k, f"{k} (referência: {_fmt(float(v['capacidade_suporte_kg_m3']))} kg/m³; "
                    f"{_fmt(float(v['energia_kwh_kg']))} kWh/kg)") for k, v in SISTEMAS_PRODUTIVOS.items()]
    sistema_anterior = t.sistema_produtivo
    t.sistema_produtivo, _ = P.opcao("Sistema produtivo:", sistemas, t.sistema_produtivo if P.modo == "revisar" else None)
    ref = SISTEMAS_PRODUTIVOS[t.sistema_produtivo]
    if P.modo == "revisar" and sistema_anterior in SISTEMAS_PRODUTIVOS and sistema_anterior != t.sistema_produtivo:
        _trocar_referencias_do_sistema(P, cfg, sistema_anterior)
    vol_atual = t.area_lamina_m2 * t.profundidade_media_m      # volume salvo (antes de alterar a área)
    P.campo(cfg, "tecnico.area_lamina_m2", "Área de lâmina d'água", minimo=1, unidade="m²")
    vol, origem = P.numero("Volume útil total dos viveiros/tanques", vol_atual if P.modo == "revisar" else None,
                           minimo=0.01, unidade="m³")
    t.profundidade_media_m = vol / t.area_lamina_m2
    if origem == "usuario":
        P.digitados.append("tecnico.profundidade_media_m")
    P.saida(f"  → profundidade média equivalente: {_fmt(round(t.profundidade_media_m, 3))} m")
    if not 0.3 <= t.profundidade_media_m <= 10:
        P.saida("  ⚠ Profundidade fora da faixa usual de viveiros e tanques (0,3 a 10 m): confira a área e o volume.")
    P.campo(cfg, "tecnico.numero_tanques", "Número total de viveiros/tanques", minimo=1, inteiro=True)
    P.campo(cfg, "tecnico.tanques_ativos", "Número de viveiros/tanques ativos", minimo=1, maximo=t.numero_tanques, inteiro=True)
    cap_atual = t.capacidade_suporte_kg_m3
    cap, origem = P.numero("Capacidade de suporte ao final do ciclo", cap_atual if P.modo == "revisar" else None,
                           minimo=0.0001, referencia=ref["capacidade_suporte_kg_m3"], unidade="kg/m³")
    t.capacidade_suporte_kg_m3 = cap
    P._registrar("tecnico.capacidade_suporte_kg_m3", origem, FONTE_SISTEMA)
    P.campo(cfg, "tecnico.produtividade_esperada_kg_m2_ciclo", "Produtividade esperada por área (0 = não restringe)",
            minimo=0, unidade="kg/m²/ciclo")
    _fontes_do_bloco(P, cfg, "técnico — infraestrutura")

    P.bloco("3. DIMENSÃO TÉCNICA — PARÂMETROS BIOLÓGICOS E INSUMOS")
    P.campo(cfg, "tecnico.peso_inicial_g", "Peso inicial dos alevinos/juvenis", minimo=0.01, unidade="g")
    P.campo(cfg, "tecnico.peso_final_g", "Peso final de abate/venda", minimo=t.peso_inicial_g * 1.0001, unidade="g")
    P.campo(cfg, "tecnico.ciclo_dias", "Duração do ciclo produtivo", minimo=1, maximo=1095, inteiro=True, unidade="dias")
    P.campo(cfg, "tecnico.ciclos_ano", "Ciclos por ano (escalonados entre os viveiros)", minimo=0.01,
            maximo=math.floor(365 / t.ciclo_dias * 1e4) / 1e4)
    P.campo(cfg, "tecnico.alevinos_por_ciclo",
            "Alevinos estocados por ciclo — total de todos os viveiros ativos (0 = dimensionar pela biomassa-alvo)",
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
            f"alevinos/ciclo: {_fmt(round(float(tec['alevinos_ciclo'][0])))} "
            f"(≈ {_fmt(round(float(tec['alevinos_ciclo'][0]) / max(t.tanques_ativos, 1)))} por viveiro ativo); "
            f"OEE: {_fmt(round(float(tec['oee'][0]), 3))}")
    _fontes_do_bloco(P, cfg, "técnico — parâmetros biológicos e insumos")


REFERENCIAS_DO_SISTEMA = {  # parâmetro -> chave em SISTEMAS_PRODUTIVOS
    "tecnico.capacidade_suporte_kg_m3": "capacidade_suporte_kg_m3",
    "ambiental.energia_kwh_kg": "energia_kwh_kg",
    "ambiental.renovacao_pct_dia": "renovacao_pct_dia",
}


def _trocar_referencias_do_sistema(P: Perguntador, cfg: EVTEASConfig, anterior: str):
    """Ao trocar o sistema produtivo, os valores que eram a referência do sistema anterior
    passam à referência do novo; valores informados pelo usuário são mantidos, com aviso."""
    novo = cfg.tecnico.sistema_produtivo
    for caminho, chave in REFERENCIAS_DO_SISTEMA.items():
        atual = obter_por_caminho(cfg, caminho)
        ref_antiga, ref_nova = SISTEMAS_PRODUTIVOS[anterior][chave], SISTEMAS_PRODUTIVOS[novo][chave]
        rotulo = P.rotulos.get(caminho, caminho)
        if vazio(atual) or abs(float(atual) - float(ref_antiga)) <= 1e-9 * max(1.0, abs(ref_antiga)):
            definir_por_caminho(cfg, caminho, float(ref_nova))
            cfg.fontes[caminho] = FONTE_SISTEMA
            P.saida(f"  → {rotulo}: referência do sistema {anterior} ({_fmt(float(ref_antiga))}) substituída pela do "
                    f"sistema {novo} ({_fmt(float(ref_nova))}).")
        else:
            P.saida(f"  ⚠ {rotulo} = {_fmt(float(atual))} foi informado para o sistema {anterior}; a referência do "
                    f"sistema {novo} é {_fmt(float(ref_nova))}. Revise-o no bloco correspondente.")


def bloco_investimento(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("4. DIMENSÃO ECONÔMICA — INVESTIMENTO (CAPEX)")
    detalhar, _ = P.sim_nao("Detalhar o CAPEX por item (s) ou informar o total (n)?",
                            (len(e.capex_itens) > 1) if (P.modo == "revisar" and e.capex_itens) else None)
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
                base_nome, k = nome, 2
                while nome in itens:                     # nomes repetidos não se sobrescrevem
                    nome, k = f"{base_nome} ({k})", k + 1
                if nome != base_nome:
                    P.saida(f"  (já existe um item '{base_nome}'; este será registrado como '{nome}')")
                itens[nome], _ = P.numero(f"  Valor de '{nome}'", None, 0, unidade="R$")
                P.saida(f"  → subtotal do CAPEX: R$ {_fmt(sum(itens.values()))}")
            e.capex_itens = itens
    else:
        total, _ = P.numero("Investimento inicial total — CAPEX",
                            e.capex_total if (P.modo == "revisar" and e.capex_itens) else None, 0, unidade="R$")
        e.capex_itens = {"CAPEX total": total}
    P.digitados.append("economico.capex_itens")
    P.saida(f"  → CAPEX total: R$ {_fmt(e.capex_total)}")
    classes = [(k, f"Classe {k} (faixa de exatidão {int(lo * 100)}% a +{int(hi * 100)}%)")
               for k, (lo, hi) in sorted(FAIXAS_AACE.items())]
    cl, origem = P.opcao("Maturidade da estimativa de CAPEX (AACE International):", classes,
                         e.classe_estimativa_aace if P.modo == "revisar" else None, referencia=5)
    e.classe_estimativa_aace = int(cl)
    P._registrar("economico.classe_estimativa_aace", origem, Fonte("normativo", "AACE International (2020)"))
    P.campo(cfg, "economico.capital_giro", "Capital de giro inicial", minimo=0, unidade="R$")
    P.campo(cfg, "economico.vida_util_anos", "Vida útil média dos ativos para depreciação", minimo=0, maximo=100,
            unidade="anos")
    atual_res = (e.valor_residual_rs if e.valor_residual_rs is not None else e.capex_total * e.valor_residual_pct / 100)
    residual, origem = P.numero("Valor residual dos ativos ao final do horizonte",
                                atual_res if P.modo == "revisar" else None, minimo=0, unidade="R$")
    e.valor_residual_rs = residual          # guardado em R$: não muda se o CAPEX for alterado depois
    e.valor_residual_pct = 100 * residual / e.capex_total if e.capex_total else 0.0
    if origem == "usuario":
        P.digitados.append("economico.valor_residual_rs")
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
    for p in e.mix_produtos:          # produto informado apenas pela participação (%) → quantidade equivalente
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
        nome = P.texto("  Nome do produto", ant.get("nome") or (f"Produto {i + 1}" if ant else None))
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
    opcoes = [("tecnico", f"Produção calculada pelo módulo técnico ({_fmt(round(prod_tec, 1))} kg/mês)")]
    if total > 0:
        opcoes.append(("mix", f"Quantidades informadas no mix ({_fmt(round(total, 1))} kg/mês)"))
    else:
        P.saida("  (as quantidades do mix somam 0 kg/mês: o volume de vendas será a produção técnica)")
    atual = ("mix" if e.producao_vendas_kg_mes > 0 and total > 0 else "tecnico") if P.modo == "revisar" else None
    base, _ = P.opcao("Volume de vendas a utilizar:", opcoes, atual)
    e.producao_vendas_kg_mes = total if base == "mix" else 0.0
    if total and prod_tec > 0 and abs(total - prod_tec) / prod_tec > 0.10:
        P.saida(f"  ⚠ O mix difere {_fmt(round(abs(total / prod_tec - 1) * 100))}% da produção técnica; verifique as premissas.")
    elif prod_tec <= 0:
        P.saida("  ⚠ A produção técnica calculada é zero; verifique os parâmetros técnicos.")

    servicos, _ = P.sim_nao("Há receita de serviços (ex.: transporte para terceiros)?",
                            (e.receita_servicos_mes > 0) if (P.modo == "revisar" and not vazio(e.receita_servicos_mes)) else None)
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
    P.saida(f"  (a primeira despesca ocorre após um ciclo de {cfg.tecnico.ciclo_dias} dias ≈ {L_calc} meses; "
            "informe 0 se a receita começar no primeiro mês)")
    meses, origem = P.numero("Meses até a primeira receita (carência)",
                             meses_ate_despesca(cfg) if P.modo == "revisar" else None, 0, 60, inteiro=True,
                             referencia=L_calc)
    if origem == "referencia":
        e.carencia_automatica, e.meses_ate_primeira_receita = True, 0      # acompanha a duração do ciclo
    elif origem == "usuario":
        e.carencia_automatica, e.meses_ate_primeira_receita = False, meses
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
    P.campo(cfg, "economico.outros_custos_variaveis_mes",
            "Outros custos variáveis mensais a 100% da capacidade (matéria-prima e insumos não listados; 0 se não houver)",
            minimo=0, unidade="R$/mês")
    P.campo(cfg, "economico.assistencia_tecnica_mes", "Assistência técnica", minimo=0, unidade="R$/mês")
    P.campo(cfg, "economico.administrativo_mes", "Outros custos fixos (aluguel, contabilidade, seguros, administração)",
            minimo=0, unidade="R$/mês")
    atual_man = e.manutencao_mes if e.manutencao_mes is not None else e.capex_total * e.manutencao_capex_pct_aa / 100 / 12
    man, origem = P.numero("Manutenção de instalações e equipamentos", atual_man if P.modo == "revisar" else None,
                           minimo=0, unidade="R$/mês")
    e.manutencao_mes = man                  # guardada em R$/mês: não muda se o CAPEX for alterado depois
    e.manutencao_capex_pct_aa = 100 * man * 12 / e.capex_total if e.capex_total else 0.0
    if origem == "usuario":
        P.digitados.append("economico.manutencao_mes")
    from .modelo import Contexto, calcular_tecnico
    tec = calcular_tecnico(Contexto(cfg))
    prod_tec = float(tec["producao_kg_mes"][0])
    prod = e.producao_vendas_kg_mes or prod_tec
    racao = prod * float(tec["racao_por_kg_produzido"][0]) * e.custo_racao_kg
    # como no modelo: a estocagem acompanha o volume de vendas
    alev = float(tec["alevinos_ano"][0]) / 12 * e.custo_alevino_milheiro / 1000 * (prod / prod_tec if prod_tec else 1.0)
    ener = prod * kwh * e.tarifa_energia_kwh
    outros = prod * e.outros_custos_variaveis_kg + e.outros_custos_variaveis_mes
    P.saida(f"  → Custo variável estimado a 100%: R$ {_fmt(round(racao + alev + ener + outros, 2))}/mês "
            f"(ração R$ {_fmt(round(racao, 2))}; alevinos R$ {_fmt(round(alev, 2))}; energia R$ {_fmt(round(ener, 2))}; "
            f"outros R$ {_fmt(round(outros, 2))})")
    _fontes_do_bloco(P, cfg, "custos")


def bloco_pessoas(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("7. PESSOAS — COOPERADOS E FUNCIONÁRIOS CLT")
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
            seguir, _ = P.sim_nao("Prosseguir mesmo assim (ex.: grupo ainda em formalização)?",
                                  True if P.modo == "revisar" else None)
            if seguir:
                break
        if e.cooperados_trabalhadores and e.cooperados_fornecedores:
            P.campo_pct(cfg, "economico.perc_sobras_trabalhadores", "Parcela das sobras destinada aos cooperados trabalhadores")
        else:
            e.perc_sobras_trabalhadores = 100.0 if e.cooperados_trabalhadores else 0.0
    else:
        e.retirada_cooperados_mes = 0.0
        e.cooperados_trabalhadores = 0
        e.cooperados_fornecedores = 0
        e.perc_sobras_trabalhadores = 100.0
    sem_cargos_com_mao_obra = P.modo == "revisar" and not vazio(e.mao_obra_mes) and e.mao_obra_mes > 0
    minimo_clt = 1 if (e.tipo_organizacao == "empresa" and not sem_cargos_com_mao_obra) else 0
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
    P.campo(cfg, "economico.mao_obra_mes",
            "Outra mão de obra não detalhada acima (diaristas, terceiros; 0 se não houver)", minimo=0, unidade="R$/mês")
    if e.mao_obra_mes > 0:
        P.campo_pct(cfg, "economico.encargos_mao_obra_pct", "Encargos sobre essa mão de obra", maximo=200)
    else:
        e.encargos_mao_obra_pct = 0.0
    _fontes_do_bloco(P, cfg, "pessoas")


TRIBUTOS = [  # nome, base, sugestão de alíquota (%)
    ("ICMS", "produtos", None), ("IPI", "produtos", None), ("ISS", "servicos", None),
    ("PIS (faturamento)", "faturamento", 0.65), ("COFINS", "faturamento", 3.0),
    ("CSLL", "lucro", 9.0), ("IRPJ", "lucro", 15.0),
    ("INSS patronal (CLT)", "folha_clt", 20.0), ("FGTS (CLT)", "folha_clt", 8.0), ("PIS sobre a folha (CLT)", "folha_clt", 1.0),
    ("INSS sobre a retirada dos cooperados", "pro_labore", 20.0),
]


def detalhar_tributos_consolidados(cfg: EVTEASConfig) -> None:
    """Converte alíquotas consolidadas (taxa sobre faturamento/lucro) em itens da lista de
    tributos do wizard, sem alterar o resultado do modelo (as bases são aditivas)."""
    e = cfg.economico
    for campo, base, nome in (("taxa_impostos_faturamento_pct", "faturamento", "Tributos sobre o faturamento (consolidado)"),
                              ("taxa_impostos_lucro_pct", "lucro", "Tributos sobre o lucro (consolidado)")):
        v = getattr(e, campo)
        if v and not (isinstance(v, float) and math.isnan(v)) and v > 0:
            e.impostos_configurados = list(e.impostos_configurados) + [{"nome": nome, "base": base, "aliquota_pct": v}]
        setattr(e, campo, 0.0)


def bloco_tributos(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("8. CONFIGURAÇÃO TRIBUTÁRIA (responda s para configurar cada tributo)")
    detalhar_tributos_consolidados(cfg)
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
        # base que passou a existir na revisão (ex.: primeiro funcionário CLT): sem decisão anterior, sem padrão
        sem_decisao = base in ("folha_clt", "pro_labore") and not any(i.get("base") == base for i in atuais.values())
        usar, _ = P.sim_nao(f"Configurar {nome}{dica}?",
                            (ant is not None) if (P.modo == "revisar" and not sem_decisao) else None)
        if usar:
            atual_aliq = None
            if ant:   # arquivo com 'aliquota' em fração
                atual_aliq = ant.get("aliquota_pct", float(ant["aliquota"]) * 100 if "aliquota" in ant else None)
            aliq, _ = P.numero(f"  Alíquota de {nome}", atual_aliq, 0, 100, unidade="%")
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
    nomes_bases = dict(bases) | {"folha": "Outra mão de obra"}
    P.saida("  → Alíquotas consolidadas: " + "; ".join(f"{nomes_bases.get(k, k)} {_fmt(round(v * 100, 4))}%"
                                                     for k, v in aq.items() if v))
    P.digitados.append("economico.impostos_configurados")
    _fontes_do_bloco(P, cfg, "tributos")


def bloco_projecao(P: Perguntador, cfg: EVTEASConfig):
    e = cfg.economico
    P.bloco("9. RAMPA DE CAPACIDADE, PROJEÇÃO DE LONGO PRAZO E TMA")
    rampa_atual = None
    if P.modo == "revisar" and not vazio(e.capacidade_inicial_pct):
        rampa_atual = bool(e.capacidade_inicial_pct < 100 or (not vazio(e.meses_rampa) and e.meses_rampa > 0))
    rampa, _ = P.sim_nao("Haverá aumento gradual da capacidade produtiva (rampa)?", rampa_atual)
    if rampa:
        P.campo_pct(cfg, "economico.capacidade_inicial_pct", "Capacidade produtiva inicial", minimo=1)
        P.campo(cfg, "economico.meses_rampa", "Meses até atingir 100% da capacidade", minimo=1, maximo=120, inteiro=True)
    else:
        e.capacidade_inicial_pct, e.meses_rampa = 100.0, 0
    from .modelo import meses_ate_despesca
    h_min = meses_ate_despesca(cfg) // 12 + 1
    P.campo(cfg, "economico.horizonte_anos", f"Horizonte de análise (mínimo {h_min}, para incluir a carência)",
            minimo=h_min, maximo=50, inteiro=True, unidade="anos")
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
    classes = [(k, f"{k} (N total {_fmt(float(v['n_max_mg_l']))} mg/L; P total {_fmt(float(v['p_max_mg_l']))} mg/L)")
               for k, v in CLASSES_CORPO_RECEPTOR.items()]
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
    a.fonte_energia, _ = P.opcao("Fonte de energia elétrica:", FONTES_ENERGIA, a.fonte_energia if P.modo == "revisar" else None)
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
    faixa_atual = next((f for f, _ in FAIXAS_APP if f == a.faixa_app_minima_m), -1.0)
    faixa, _ = P.opcao("Faixa mínima de APP aplicável (Lei nº 12.651/2012), medida a partir da borda da calha do leito regular:",
                       [(f, d) for f, d in FAIXAS_APP], faixa_atual if P.modo == "revisar" else None)
    if faixa < 0:
        P.campo(cfg, "ambiental.faixa_app_minima_m", "Faixa mínima de APP", minimo=0, unidade="m")
    else:
        a.faixa_app_minima_m = faixa
        cfg.fontes["ambiental.faixa_app_minima_m"] = Fonte("normativo", "Lei nº 12.651/2012, art. 4º, I")
    P.campo(cfg, "ambiental.distancia_app_m",
            "Distância das instalações até a margem do curso d'água (borda da calha do leito regular)", minimo=0, unidade="m")
    if a.distancia_app_m < a.faixa_app_minima_m:
        P.saida(f"  ⚠ As instalações estão a {_fmt(a.distancia_app_m)} m da margem, dentro da faixa de APP de "
                f"{_fmt(a.faixa_app_minima_m)} m: o item 'Instalações fora da APP' será considerado NÃO atendido.")
    for chave, (descricao, _, elim) in CHECKLIST_AMBIENTAL.items():
        marca = " [ELIMINATÓRIO]" if elim else ""
        v, _ = P.sim_nao(f"{descricao}{marca}", a.checklist.get(chave) if P.modo == "revisar" else None)
        a.checklist[chave] = v
    if a.checklist.get("respeita_app") and a.distancia_app_m < a.faixa_app_minima_m:
        P.saida("  ⚠ Pela distância informada, as instalações estão dentro da APP: o item continua NÃO atendido "
                "(a resposta do checklist não prevalece sobre a distância).")
    _fontes_do_bloco(P, cfg, "conformidade")


FONTES_ENERGIA = [("rede", "Rede pública"), ("solar", "Solar fotovoltaica"), ("biomassa", "Biomassa"),
                  ("mista", "Mista (rede + renovável)")]
RELACOES = [("inexistente", "Inexistente"), ("parcial", "Parcial (contatos eventuais)"),
            ("consolidado", "Consolidado (canal permanente e acordos)")]


def bloco_social(P: Perguntador, cfg: EVTEASConfig):
    s, e = cfg.social, cfg.economico
    P.bloco("13. DIMENSÃO SOCIAL — EMPREGO, RENDA E RELAÇÃO COM A COMUNIDADE")
    sug = e.cooperados_trabalhadores + len(e.salarios_clt_por_cargo)
    if P.modo == "revisar" and sug and s.empregos_diretos != sug:
        P.saida(f"  (cooperados na operação + funcionários CLT = {sug}; o valor salvo é {s.empregos_diretos})")
    P.campo(cfg, "social.empregos_diretos", "Empregos diretos", minimo=0, inteiro=True,
            referencia=sug if sug else None, fonte_ref=FONTE_AUTOR)
    P.campo(cfg, "social.empregos_indiretos", "Empregos indiretos", minimo=0, inteiro=True)
    P.campo_pct(cfg, "social.mao_obra_local_pct", "Mão de obra residente no município/comunidade")
    P.campo_pct(cfg, "social.compras_locais_pct", "Compras de insumos e serviços feitas localmente")
    P.campo(cfg, "social.salario_minimo", "Salário mínimo vigente no ano-base do estudo", minimo=1, unidade="R$")
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


METODOS_PESOS = [("preset", "Informar diretamente os pesos das quatro dimensões"),
                 ("likert", "Escala Likert de 1 a 5 atribuída por avaliadores (Quadro 7)"),
                 ("ahp", "Comparação par a par (AHP — Saaty)")]
DIMENSOES_ROTULOS = [("tecnico", "Técnica"), ("economico", "Econômica"), ("ambiental", "Ambiental"), ("social", "Social")]


def bloco_pesos(P: Perguntador, cfg: EVTEASConfig):
    p = cfg.pesos
    P.bloco("15. PESOS DO ÍNDICE EVTEAS E REGRAS DE DECISÃO")
    p.metodo, _ = P.opcao("Método de ponderação:", METODOS_PESOS, p.metodo if P.modo == "revisar" else None)
    if p.metodo != "likert":
        p.likert_kpis = {}            # escores de KPIs só se aplicam ao método Likert
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
            while nome in lk:
                P.saida("  ⚠ Já existe um avaliador com esse nome; informe outro.")
                nome = P.texto(f"Nome/área do avaliador nº {i + 1}")
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
                        kp[nome][k], _ = P.numero(f"  {nome} — relevância do KPI {ROTULOS_KPI.get(k, k)} "
                                                  f"(dimensão {dict(DIMENSOES_ROTULOS)[d].lower()})",
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
            P.saida("  → Pesos: " + "; ".join(f"{n} {_fmt(round(float(w), 3))}" for (_, n), w in zip(DIMENSOES_ROTULOS, res["pesos"]))
                    + f" | razão de consistência = {_fmt(round(float(res['rc']), 3))}")
            p.ahp_matriz = A.tolist()
            if res["consistente"]:
                break
            refazer, _ = P.sim_nao("  ⚠ RC > 0,10 (julgamentos inconsistentes). Refazer as comparações?",
                                   False if P.modo == "revisar" else None)
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


VARIAVEIS_INCERTAS = [  # caminho, rótulo, escala de exibição (valor exibido = valor interno × escala)
    ("economico.preco_venda_kg", "Preço de venda (R$/kg)", 1.0),
    ("economico.custo_racao_kg", "Custo da ração (R$/kg)", 1.0),
    ("economico.custo_alevino_milheiro", "Custo do alevino (R$/unidade)", 1 / 1000),
    ("economico.tarifa_energia_kwh", "Tarifa de energia (R$/kWh)", 1.0),
    ("economico.custos_fixos_fator", "Fator multiplicador dos custos fixos (1 = valor informado)", 1.0),
    ("tecnico.fcr", "FCR", 1.0),
    ("tecnico.mortalidade_pct", "Mortalidade (%)", 1.0),
    ("tecnico.desempenho_crescimento_pct", "Desempenho de crescimento (%)", 1.0),
]
DOMINIO_INCERTAS = {  # limites (na unidade exibida) dos mínimos e máximos das distribuições
    "economico.preco_venda_kg": (0.0, None), "economico.custo_racao_kg": (0.0, None),
    "economico.custo_alevino_milheiro": (0.0, None), "economico.tarifa_energia_kwh": (0.0, None),
    "economico.custos_fixos_fator": (0.0, None), "economico.capex_fator": (0.01, None),
    "tecnico.fcr": (0.3, 6.0), "tecnico.mortalidade_pct": (0.0, 99.0), "tecnico.desempenho_crescimento_pct": (1.0, 150.0),
}
DOMINIO_INTERNO = {c: tuple(None if v is None else v / escala for v in DOMINIO_INCERTAS[c])
                   for c, _, escala in VARIAVEIS_INCERTAS}
DOMINIO_INTERNO["economico.capex_fator"] = DOMINIO_INCERTAS["economico.capex_fator"]
TIPOS_DIST = [("triangular", "Triangular (mínimo, mais provável, máximo)"),
              ("uniforme", "Uniforme (apenas mínimo e máximo conhecidos)"),
              ("normal", "Normal truncada em [mínimo, máximo]"),
              ("fixa", "Sem incerteza (valor fixo)")]


def ajustar_distribuicao(d: Distribuicao, antigo: float, novo: float, caminho: Optional[str] = None) -> Distribuicao:
    """Reposiciona uma distribuição quando o valor determinístico muda (mantém a amplitude relativa,
    dentro do domínio da variável)."""
    if d.tipo == "fixa":
        return Distribuicao("fixa", novo, novo, novo)
    if antigo and novo:
        f = novo / antigo
        lo, hi = sorted((d.minimo * f, d.maximo * f))
    else:   # com valor nulo, o fator proporcional colapsaria a distribuição: desloca a amplitude
        lo, hi = d.minimo + (novo - antigo), d.maximo + (novo - antigo)
    dom_lo, dom_hi = DOMINIO_INTERNO.get(caminho, (None, None))
    if dom_lo is not None:
        lo = max(lo, dom_lo)
    if dom_hi is not None:
        hi = min(hi, dom_hi)
    moda = novo if d.tipo != "uniforme" else (lo + hi) / 2
    return Distribuicao(d.tipo, min(lo, novo), moda, max(hi, novo))


def distribuicao_coerente(d: Distribuicao, valor: float, tol: float = 1e-9) -> bool:
    """O valor determinístico deve estar no intervalo e ser o mais provável (triangular/normal/fixa)."""
    ok = d.minimo - tol <= valor <= d.maximo + tol
    if d.tipo in ("triangular", "normal", "fixa"):
        ok = ok and abs(d.moda - valor) <= tol * max(1.0, abs(valor))
    return ok


def _perguntar_distribuicao(P: Perguntador, cfg: EVTEASConfig, caminho: str, rotulo: str,
                            atual: Optional[Distribuicao], escala: float = 1.0):
    base = float(obter_por_caminho(cfg, caminho))
    if P.modo == "revisar" and atual is not None and not distribuicao_coerente(atual, base):
        referencia_antiga = atual.moda if atual.tipo != "uniforme" else (atual.minimo + atual.maximo) / 2
        atual = ajustar_distribuicao(atual, referencia_antiga, base, caminho)
        P.saida(f"  (a distribuição salva foi reposicionada proporcionalmente ao valor atual de {rotulo})")
    vb = base * escala
    P.saida(f"\n{rotulo} — valor determinístico informado: {_fmt(vb)}")
    # no modo revisar, variável sem distribuição cadastrada continua fixa (Enter preserva o resultado)
    tipo_atual = (atual.tipo if atual else "fixa") if P.modo == "revisar" else None
    tipo, _ = P.opcao("  Tipo de distribuição:", TIPOS_DIST, tipo_atual)
    if tipo == "fixa":
        return Distribuicao("fixa", base, base, base)
    if tipo in ("triangular", "normal"):
        P.saida(f"  Valor mais provável = valor determinístico informado ({_fmt(vb)})")
    lo_dom, hi_dom = DOMINIO_INCERTAS.get(caminho, (None, None))
    revisa = P.modo == "revisar" and atual is not None and atual.tipo != "fixa"
    tol = 1e-9 * max(1.0, abs(vb))
    while True:
        mn, _ = P.numero("  Mínimo", atual.minimo * escala if revisa else None, lo_dom, hi_dom)
        mx, _ = P.numero("  Máximo", atual.maximo * escala if revisa else None, lo_dom, hi_dom)
        if not (mn - tol <= vb <= mx + tol):
            P.saida(f"  ⚠ O intervalo deve conter o valor determinístico ({_fmt(vb)}). Informe novamente.")
            continue
        try:
            moda = base if tipo != "uniforme" else (mn + mx) / 2 / escala
            # valores digitados na unidade exibida: o arredondamento da escala não pode excluir o valor-base
            return Distribuicao(tipo, min(mn / escala, base), moda, max(mx / escala, base)).validar()
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
    for caminho, rotulo, escala in VARIAVEIS_INCERTAS:
        novas[caminho] = _perguntar_distribuicao(P, cfg, caminho, rotulo, mc.distribuicoes.get(caminho), escala)
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
    # Só as variáveis que o motor amostra (VARIAVEIS_ESTOCASTICAS) têm efeito no Monte Carlo; distribuições
    # atribuídas a outros parâmetros no arquivo carregado são descartadas com aviso.
    ignoradas = [c for c in mc.distribuicoes if c not in novas and c not in VARIAVEIS_ESTOCASTICAS]
    if ignoradas:
        P.saida("  ⚠ Distribuições descartadas (o modelo não amostra esses parâmetros): "
                + ", ".join(P.rotulos.get(c, c) for c in ignoradas))
    mc.distribuicoes = {c: d for c, d in novas.items() if c in VARIAVEIS_ESTOCASTICAS}


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
        ("Projeto", cfg.projeto), ("Organização", dict(TIPOS_ORGANIZACAO).get(e.tipo_organizacao, e.tipo_organizacao)),
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
        ("Ração; alevino; energia", f"R$ {_fmt(e.custo_racao_kg)}/kg; R$ {_fmt(e.custo_alevino_milheiro / 1000)}/un; R$ {_fmt(e.tarifa_energia_kwh)}/kWh"),
        ("Remuneração mensal (CLT / retiradas / outras)", f"R$ {_fmt(rem['clt'])} / R$ {_fmt(rem['retirada'])} / R$ {_fmt(rem['outros'])}"),
        ("Tributos (faturamento / lucro)", f"{_fmt(round((aq['faturamento'] + aq['produtos']) * 100, 4))}% / {_fmt(round(aq['lucro'] * 100, 4))}%"),
        ("TMA; horizonte", f"{_fmt(e.tma_aa_pct)}% a.a.; {e.horizonte_anos} anos"),
        ("Energia; remoção de P", f"{dict(FONTES_ENERGIA).get(a.fonte_energia, a.fonte_energia)}; {_fmt(a.remocao_p_tratamento_pct)}%"),
        ("Pesos", dict(METODOS_PESOS).get(cfg.pesos.metodo, cfg.pesos.metodo)),
        ("Monte Carlo", f"{_fmt(cfg.monte_carlo.iteracoes)} iterações; {len(cfg.monte_carlo.distribuicoes)} variáveis incertas"),
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


OPCIONAIS = {  # None é válido: usa a referência do sistema produtivo ou o percentual correspondente
    "tecnico.capacidade_suporte_kg_m3", "ambiental.renovacao_pct_dia", "ambiental.energia_kwh_kg",
    "economico.valor_residual_rs", "economico.manutencao_mes",
}


def entradas_pendentes(cfg: EVTEASConfig) -> List[str]:
    """Lista parâmetros que continuam sem valor (NaN, ou None fora dos opcionais)."""
    from dataclasses import fields as campos
    faltam = []
    for bloco in BLOCOS_EM_BRANCO:
        obj = getattr(cfg, bloco)
        for f in campos(obj):
            v, caminho = getattr(obj, f.name), f"{bloco}.{f.name}"
            if (v is None and caminho not in OPCIONAIS) or (isinstance(v, float) and math.isnan(v)):
                faltam.append(caminho)
    faltam += [f"ambiental.checklist.{k}" for k, v in cfg.ambiental.checklist.items() if v is None]
    faltam += [f"governanca.itens.{k}" for k, v in cfg.governanca.itens.items() if v is None]
    if not cfg.economico.capex_itens:
        faltam.append("economico.capex_itens")
    if not cfg.economico.mix_produtos and vazio(cfg.economico.preco_venda_kg):
        faltam.append("economico.mix_produtos")
    for p in cfg.economico.mix_produtos:
        if any(vazio(p.get(k)) for k in ("preco_kg",)):
            faltam.append("economico.mix_produtos")
            break
    return faltam


# ---------------------------------------------------------------------------
# Leitura de arquivos de entradas (inclusive incompletos)
# ---------------------------------------------------------------------------

SECOES_CONFIG = ("tecnico", "economico", "ambiental", "social", "governanca", "pesos", "decisao", "monte_carlo")
NEUTROS_AUSENTES = {"carencia_automatica", "incluir_capex_aace"}   # opções que recebem padrão neutro quando ausentes do arquivo


def _neutro(nome: str, padrao) -> bool:
    """Indica se o campo, quando ausente do arquivo de entradas, pode receber o valor padrão sem alterar o
    estudo (0, vazio, None, fator 1), em vez de ficar pendente."""
    if nome in NEUTROS_AUSENTES or nome.endswith("_fator"):
        return True
    if isinstance(padrao, bool):
        return False
    return padrao is None or padrao == "" or (isinstance(padrao, (int, float)) and padrao == 0) or \
        (isinstance(padrao, (list, dict)) and not padrao)


def _normalizar_formatos_alternativos(dados: Dict[str, Any], avisos: List[str]) -> Dict[str, Any]:
    """Aceita tributos com 'aliquota' em fração e bases com nomes alternativos (apelidos de BASES_TRIBUTARIAS);
    nomeia os produtos do mix informados sem nome."""
    from .modelo import BASES_TRIBUTARIAS
    apelidos = {a: k for k, v in BASES_TRIBUTARIAS.items() for a in v}
    e = dados.get("economico")
    if not isinstance(e, dict):
        return dados
    convertidos = 0
    for i, imp in enumerate(e.get("impostos_configurados") or []):
        if not isinstance(imp, dict):
            raise ValueError("tributo em formato inválido no arquivo")
        if "aliquota_pct" not in imp and "aliquota" in imp:
            imp["aliquota_pct"] = float(imp.pop("aliquota")) * 100
            convertidos += 1
        if imp.get("base", "faturamento") in apelidos:
            imp["base"] = apelidos[imp.get("base", "faturamento")]
        imp.setdefault("nome", f"Tributo {i + 1}")
    if convertidos:
        avisos.append(f"{convertidos} tributo(s) com alíquota em fração convertido(s) para %.")
    for i, prod in enumerate(e.get("mix_produtos") or []):
        if isinstance(prod, dict) and not prod.get("nome"):
            prod["nome"] = f"Produto {i + 1}"
    return dados


def _valor_lido(secao: str, nome: str, valor, atual):
    if nome == "distribuicoes":
        if not isinstance(valor, dict):
            raise ValueError("distribuições do Monte Carlo em formato inválido")
        saida = {}
        for c, d in valor.items():
            extras = set(d) - {"tipo", "minimo", "moda", "maximo"} if isinstance(d, dict) else {"?"}
            if extras:
                raise ValueError(f"distribuição de {c} com campos desconhecidos: {', '.join(sorted(map(str, extras)))}")
            saida[c] = Distribuicao(**d)
        return saida
    if (secao, nome) in (("governanca", "itens"), ("ambiental", "checklist")) and isinstance(valor, dict):
        return {**{k: None for k in atual}, **valor}       # item ausente fica pendente
    return valor


def ler_entradas(dados) -> Tuple[EVTEASConfig, List[str], List[str]]:
    """Monta a configuração a partir do conteúdo de um arquivo de entradas, sem completar o que falta com
    o caso ilustrativo. Devolve (configuração, avisos, entradas pendentes)."""
    import copy
    from dataclasses import fields as campos
    avisos: List[str] = []
    if isinstance(dados, dict) and isinstance(dados.get("config"), dict) and "vv" in dados:
        avisos.append("O arquivo é de resultados do EVTEAS-Py: foram usadas as entradas registradas nele.")
        dados = dados["config"]
    if not isinstance(dados, dict) or not all(isinstance(dados.get(k), dict) for k in ("tecnico", "economico")):
        raise ValueError("não é um arquivo de entradas do EVTEAS-Py (faltam as seções 'tecnico' e 'economico')")
    dados = _normalizar_formatos_alternativos(copy.deepcopy(dados), avisos)
    cfg, padrao = config_em_branco(), EVTEASConfig()
    conhecidas = {f.name for f in campos(EVTEASConfig)}
    desconhecidas = [k for k in dados if k not in conhecidas and k != "versao"]   # rótulo do artefato, aceito sem aviso
    neutros, faltam_texto = [], []
    cfg.projeto, cfg.autor = str(dados.get("projeto") or ""), str(dados.get("autor") or "")
    for secao in SECOES_CONFIG:
        bruto = dados.get(secao)
        if bruto is None:
            if secao == "pesos":
                avisos.append("O arquivo não traz os pesos: adotado o preset do EVTEAS-Py (revise no bloco 'Pesos').")
            continue
        if not isinstance(bruto, dict):
            raise ValueError(f"a seção '{secao}' do arquivo está em formato inválido")
        obj, ref = getattr(cfg, secao), getattr(padrao, secao)
        nomes = {f.name for f in campos(obj)}
        desconhecidas += [f"{secao}.{k}" for k in bruto if k not in nomes]
        for f in campos(obj):
            if f.name in bruto:
                setattr(obj, f.name, _valor_lido(secao, f.name, bruto[f.name], getattr(obj, f.name)))
            elif _neutro(f.name, getattr(ref, f.name)):
                setattr(obj, f.name, copy.deepcopy(getattr(ref, f.name)))
                neutros.append(f"{secao}.{f.name}")
            elif isinstance(getattr(ref, f.name), str):
                setattr(obj, f.name, None)                   # texto ausente: pendente
                faltam_texto.append(f"{secao}.{f.name}")
    fontes = dados.get("fontes") or {}
    if not isinstance(fontes, dict):
        raise ValueError("registro de fontes em formato inválido")
    cfg.fontes = {k: Fonte(**v) for k, v in fontes.items() if isinstance(v, dict)}
    # distribuições: só variáveis amostradas pelo motor, coerentes com o valor determinístico
    mc = cfg.monte_carlo
    for c in list(mc.distribuicoes):
        if c not in VARIAVEIS_ESTOCASTICAS:
            del mc.distribuicoes[c]
            avisos.append(f"Distribuição de {c} descartada: o modelo não amostra esse parâmetro no Monte Carlo.")
            continue
        v, d = obter_por_caminho(cfg, c), mc.distribuicoes[c]
        if not vazio(v) and not distribuicao_coerente(d, float(v)):
            antigo = d.moda if d.tipo != "uniforme" else (d.minimo + d.maximo) / 2
            mc.distribuicoes[c] = ajustar_distribuicao(d, antigo, float(v), c)
            avisos.append(f"Distribuição de {c} reposicionada para o valor determinístico do arquivo ({_fmt(float(v))}).")
    _completar_condicionais(cfg)
    if neutros:
        avisos.append("Campos ausentes no arquivo preenchidos com valor neutro: " + ", ".join(neutros))
    if desconhecidas:
        avisos.append("Campos desconhecidos ignorados: " + ", ".join(desconhecidas))
    return cfg, avisos, entradas_pendentes(cfg)


def _completar_condicionais(cfg: EVTEASConfig) -> None:
    """Valores que só são perguntados em certas situações recebem o valor neutro correspondente."""
    a = cfg.ambiental
    if a.fonte_energia != "mista":
        a.fracao_renovavel_mista = 0.0
    if a.fonte_energia not in ("rede", "mista") and (a.fator_emissao_rede_kgco2_kwh is None or math.isnan(a.fator_emissao_rede_kgco2_kwh)):
        a.fator_emissao_rede_kgco2_kwh = 0.0817     # não utilizado com fonte solar ou biomassa


DEPENDENCIAS = {  # ao corrigir um bloco, os dependentes também são revistos (Enter mantém os valores)
    "Identificação": ["Pessoas", "Tributos", "Social e governança"],   # organização: pessoas, encargos, empregos
    "Técnico": ["Mix e receitas", "Custos operacionais", "Ambiental"],  # produção, carência e referências do sistema
    "Pessoas": ["Tributos", "Social e governança"],   # cargos e retiradas: encargos e empregos diretos
    "Mix e receitas": ["Tributos", "Projeção e TMA"],  # receita de serviços (ISS); a carência limita o horizonte
}


def expandir_blocos(blocos: Sequence[str]) -> List[str]:
    pendentes, vistos = list(blocos), set()
    while pendentes:
        b = pendentes.pop()
        if b not in vistos:
            vistos.add(b)
            pendentes += DEPENDENCIAS.get(b, [])
    return [nome for nome, _ in BLOCOS if nome in vistos]


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
    if blocos is not None:
        blocos = expandir_blocos(blocos)
        if len(blocos) > 1:
            saida("Blocos que dependem da correção também serão revistos: " + ", ".join(blocos))
    antes = {c: float(obter_por_caminho(cfg, c)) for c in cfg.monte_carlo.distribuicoes} if base is not None else {}
    try:
        for nome, func in BLOCOS:
            if blocos is None or nome in blocos:
                func(P, cfg)
    except EntradaCancelada as exc:
        exc.cfg = cfg                       # respostas já dadas, para o rascunho
        raise
    if blocos is not None and "Incerteza (Monte Carlo)" not in blocos:
        for c, v0 in antes.items():
            v1 = float(obter_por_caminho(cfg, c))
            if v1 != v0 and c in cfg.monte_carlo.distribuicoes:
                cfg.monte_carlo.distribuicoes[c] = ajustar_distribuicao(cfg.monte_carlo.distribuicoes[c], v0, v1, c)
                saida(f"  → Distribuição de {c} reposicionada para o novo valor ({_fmt(v0)} → {_fmt(v1)}); "
                      "revise-a no bloco 'Incerteza (Monte Carlo)' se necessário.")
    _completar_condicionais(cfg)
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
        while nome in alternativas:
            saida("  ⚠ Já existe uma alternativa (ou o projeto) com esse nome; informe outro.")
            nome = P.texto(f"Nome da alternativa {i + 1}")
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


def _no_colab() -> bool:
    try:
        import google.colab  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def _carregar_arquivo(entrada: Callable[[str], str], saida) -> Tuple[EVTEASConfig, List[str]]:
    """Lê o arquivo de entradas, com nova tentativa em caso de erro. Devolve (configuração, pendências)."""
    colab = _no_colab()
    while True:
        prompt = ("Enter para enviar o arquivo JSON do computador, ou caminho de um arquivo já no ambiente: " if colab
                  else "Caminho do arquivo JSON de entradas: ")
        caminho = (entrada(prompt) or "").strip().strip('"').strip("'")
        if caminho.lower() in ("sair", "cancelar"):
            raise EntradaCancelada("entrada interrompida pelo usuário")
        try:
            if colab and not caminho:
                from google.colab import files  # type: ignore
                saida("Selecione o arquivo JSON de entradas salvo anteriormente.")
                enviado = files.upload()
                if not enviado:
                    raise ValueError("nenhum arquivo selecionado")
                texto = next(iter(enviado.values())).decode("utf-8-sig")
            elif not caminho:
                raise ValueError("informe o caminho do arquivo")
            else:
                texto = Path(caminho).read_text(encoding="utf-8-sig")
            cfg, avisos, pendentes = ler_entradas(json.loads(texto))
        except EntradaCancelada:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError) as exc:
            saida(f"  ⚠ Não foi possível usar o arquivo ({exc}). Tente novamente ou digite 'sair'.")
            continue
        for a in avisos:
            saida(f"  ⚠ {a}")
        return cfg, pendentes


def exigir_entradas(cfg: Optional[EVTEASConfig]) -> EVTEASConfig:
    """Usada no notebook antes da análise: sem entradas concluídas, interrompe com mensagem curta."""
    if cfg is None:
        raise EntradaCancelada("A entrada de dados não foi concluída: execute a célula 'Entrada de dados do projeto'.")
    return cfg


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
    try:
        if modo == "novo":
            cfg = wizard_evteas(entrada, None, saida)
        elif modo == "arquivo":
            cfg, pendentes = _carregar_arquivo(entrada, saida)
            if pendentes:
                saida(f"⚠ O arquivo não traz {len(pendentes)} entrada(s), que serão pedidas na revisão a seguir: "
                      + ", ".join(pendentes[:12]) + (" …" if len(pendentes) > 12 else ""))
                revisar = True
            else:
                revisar, _ = P.sim_nao("Revisar as entradas carregadas bloco a bloco?", None)
            if revisar:
                cfg = wizard_evteas(entrada, cfg, saida)
        else:
            cfg = criar_config_caso_base()
            cfg.projeto = f"EXEMPLO ILUSTRATIVO — {cfg.projeto}"
            saida("⚠ Exemplo ilustrativo carregado: os resultados NÃO representam o seu projeto.")
    except EntradaCancelada as exc:
        parcial = getattr(exc, "cfg", None)
        if salvar and parcial is not None:
            caminho = str(Path(pasta_saida) / nome_arquivo(parcial).replace(".json", "_rascunho.json"))
            salvar_config(parcial, caminho)
            _baixar_no_colab(caminho)
            raise EntradaCancelada(f"Entrada interrompida. As respostas dadas foram salvas em {caminho}; "
                                   "use a opção 2 para continuar de onde parou.") from None
        raise
    while True:
        saida("\nResumo das entradas:")
        saida(resumo_entradas(cfg).to_string(index=False))
        try:
            acao, _ = P.opcao("\nO que deseja fazer?", [("executar", "Confirmar e executar a análise"),
                                                         ("editar", "Corrigir um bloco de entradas"),
                                                         ("sair", "Salvar as entradas e encerrar sem executar")])
        except EntradaCancelada:
            acao = "sair"                    # 'sair' no menu final salva antes de encerrar
        if acao == "editar":
            nomes = [(n, n) for n, _ in BLOCOS]
            try:
                bloco, _ = P.opcao("Bloco a corrigir:", nomes)
                cfg = wizard_evteas(entrada, copy.deepcopy(cfg), saida, blocos=[bloco])
            except EntradaCancelada:
                saida("Correção cancelada: as entradas anteriores foram mantidas.")
            continue
        break
    if salvar:
        caminho = str(Path(pasta_saida) / nome_arquivo(cfg))
        salvar_config(cfg, caminho)
        saida(f"Entradas salvas em: {caminho} (use a opção 2 para reabrir e revisar).")
        _baixar_no_colab(caminho)
    if acao == "sair":
        raise EntradaCancelada("Entradas salvas; a análise não foi executada.")
    return cfg


# ---------------------------------------------------------------------------
# Análise de preços a partir de planilha
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

"""EVTEAS-Py — módulo interface.

Assistente interativo de entrada de dados (alternativa ao formulário do Colab e à planilha),
com validação a cada resposta, e análise de preços de mercado para apoiar a definição do preço
de venda e da sua distribuição de incerteza.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

from .config import EVTEASConfig, copiar, fmt_num, obter_por_caminho
from .entradas import (DISTRIBUICOES, ENTRADAS, Entrada, EntradasInvalidas, config_vazia, converter, definir_valor,
                       fmt_auto, ler_distribuicao, ler_item_capex, obter_valor)

MAX_TENTATIVAS = 20


def _vazio(t) -> bool:
    return t is None or not str(t).strip()


def perguntar(entrada: Entrada, ler: Callable[[str], str], atual: Any = None, mostrar: Callable[[str], None] = print):
    """Pergunta até obter um valor válido. Enter mantém o valor atual (se houver); numa entrada
    opcional sem valor atual, Enter adota 'não se aplica'; numa obrigatória, repete a pergunta."""
    sufixo = f" ({entrada.unidade})" if entrada.unidade not in ("—", "") else ""
    if entrada.opcoes:
        sufixo += f" [{' / '.join(entrada.opcoes)}]"
    elif entrada.tipo == "bool":
        sufixo += " [sim / não]"
    if atual is not None and atual != "":
        sufixo += f" (Enter = {fmt_auto(atual)})"
    elif not entrada.obrigatorio:
        sufixo += " (opcional: Enter = não se aplica)"
    texto = f"[{entrada.marcador}] {entrada.rotulo}{sufixo}: "
    for _ in range(MAX_TENTATIVAS):
        resp = ler(texto)
        if _vazio(resp):
            if atual is not None and atual != "":
                return atual
            if not entrada.obrigatorio:
                return entrada.vazio
            mostrar("  Entrada obrigatória: informe um valor.")
            continue
        try:
            return converter(entrada, resp)
        except ValueError as exc:
            mostrar(f"  Valor não aceito: {exc}")
    raise EntradasInvalidas([f"[{entrada.marcador}] {entrada.rotulo}: número máximo de tentativas excedido"])


def wizard_evteas(entrada: Callable[[str], str] = input, base: Optional[EVTEASConfig] = None,
                  silencioso: bool = False, perguntar_metodo: bool = False) -> EVTEASConfig:
    """Assistente de entrada de dados, bloco a bloco (identificação, técnica, econômica, ambiental,
    social, governança, Lean-Green, CAPEX e distribuições de incerteza).

    ``base``: configuração existente (por exemplo, carregada de JSON) cujos valores são mantidos com
    Enter. Sem ``base``, todas as entradas obrigatórias precisam ser digitadas.
    """
    mostrar = (lambda *_: None) if silencioso else print
    cfg = copiar(base) if base is not None else config_vazia()
    grupo = None
    for e in ENTRADAS:
        if e.metodo and not perguntar_metodo:
            continue
        if e.grupo != grupo:
            grupo = e.grupo
            mostrar(f"\n=== {grupo} ===")
        atual = obter_valor(cfg, e)
        if atual is None or (base is None and not e.metodo):
            atual = None if not e.metodo else atual
        valor = perguntar(e, entrada, atual, mostrar)
        definir_valor(cfg, e, valor)

    mostrar("\n=== Investimento (CAPEX) ===")
    mostrar("Informe um item por linha: 'descrição; valor (R$); vida útil (anos)'. Linha vazia encerra.")
    if base is not None and base.economico.capex:
        mostrar(f"  (Enter na primeira linha mantém os {len(base.economico.capex)} itens atuais)")
    itens = []
    for k in range(1, 61):
        resp = entrada(f"[E-C{k:02d}] Item {k}: ")
        if _vazio(resp):
            break
        try:
            itens.append(ler_item_capex(resp))
        except ValueError as exc:
            mostrar(f"  Valor não aceito: {exc}")
    if itens:
        cfg.economico.capex = itens
    elif not cfg.economico.capex:
        raise EntradasInvalidas(["[E-C] Informe ao menos um item de CAPEX"])

    mostrar("\n=== Distribuições de incerteza (Monte Carlo) ===")
    mostrar("Informe 'mín; máx' (a moda é o valor informado acima). Enter = premissa determinística"
            + (" ou mantém a distribuição atual." if base is not None else "."))
    for marcador, var, caminho, rot, unid in DISTRIBUICOES:
        valor = float(obter_por_caminho(cfg, caminho))
        atual = cfg.distribuicoes.get(caminho)
        dica = f" (Enter = {fmt_auto(atual.minimo)}; {fmt_auto(atual.maximo)})" if atual else ""
        for _ in range(MAX_TENTATIVAS):
            resp = entrada(f"[{marcador}] {rot} — valor informado {fmt_auto(valor)} {unid}{dica}: ")
            if _vazio(resp):
                break
            try:
                cfg.distribuicoes[caminho] = ler_distribuicao(resp, valor)
                break
            except ValueError as exc:
                mostrar(f"  Valor não aceito: {exc}")
    from .config import validar_config
    problemas = validar_config(cfg)
    if problemas:
        raise EntradasInvalidas(problemas)
    mostrar("\nEntradas registradas. Execute executar_evteas(cfg) para simular.")
    return cfg


# ---------------------------------------------------------------------------------------------
# Análise de preços de mercado
# ---------------------------------------------------------------------------------------------
def analise_precos(dados: pd.DataFrame, custo_variavel_kg: Optional[float] = None,
                   coluna_preco: str = "preco", coluna_quantidade: str = "quantidade") -> Dict[str, Any]:
    """Resume uma amostra de preços (cotações) por percentis e, se houver quantidades, ajusta uma
    curva de demanda linear q = a − b·p por mínimos quadrados. Com o custo variável unitário c,
    o preço que maximiza a margem de contribuição (p − c)·q(p) é p* = (a/b + c)/2.

    Os percentis P10 e P90 podem orientar o mínimo e o máximo da distribuição do preço (Quadro 13).
    """
    p = pd.to_numeric(dados[coluna_preco], errors="coerce").dropna().to_numpy(dtype=float)
    if len(p) < 2:
        raise ValueError("Informe ao menos duas cotações de preço")
    sugestoes = {"Mínimo": float(p.min()), "P10": float(np.percentile(p, 10)), "P25": float(np.percentile(p, 25)),
                 "Mediana (P50)": float(np.percentile(p, 50)), "Média": float(p.mean()),
                 "P75": float(np.percentile(p, 75)), "P90": float(np.percentile(p, 90)), "Máximo": float(p.max())}
    r: Dict[str, Any] = {"n": int(len(p)), "sugestoes": sugestoes, "preco_otimo": None, "elasticidade_media": None,
                         "demanda": None,
                         "distribuicao_sugerida": f"{fmt_num(sugestoes['P10'], 2)}; {fmt_num(sugestoes['P90'], 2)}"}
    if coluna_quantidade in dados.columns:
        d = dados[[coluna_preco, coluna_quantidade]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(d) >= 3 and d[coluna_preco].nunique() > 1:
            inc, intercepto = np.polyfit(d[coluna_preco], d[coluna_quantidade], 1)
            a, b = float(intercepto), float(-inc)
            r["demanda"] = {"a": a, "b": b,
                            "r2": float(np.corrcoef(d[coluna_preco], d[coluna_quantidade])[0, 1] ** 2)}
            if b > 0:
                pm, qm = float(d[coluna_preco].mean()), float(d[coluna_quantidade].mean())
                r["elasticidade_media"] = -b * pm / qm if qm else None
                if custo_variavel_kg is not None:
                    r["preco_otimo"] = (a / b + float(custo_variavel_kg)) / 2
    return r

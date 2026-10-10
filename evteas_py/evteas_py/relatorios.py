"""Resumo executivo, exportação (Excel/JSON/Markdown) e gráficos."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def moeda(v) -> str:
    if v is None or not np.isfinite(v):
        return "n/d"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(v, casas: int = 1) -> str:
    if v is None or not np.isfinite(v):
        return "n/d"
    return f"{v * 100:.{casas}f}%".replace(".", ",")


def numero(v, casas: int = 2) -> str:
    if v is None or not np.isfinite(v):
        return "n/d"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def resumo_executivo(r: Dict[str, Any]) -> pd.DataFrame:
    """Indicadores principais, no mesmo formato dos valores para o texto (campos_texto)."""
    from .campos_texto import meses_ou_horizonte, num, pct_br, reais, tir_txt
    t, e, a, s, i = r["tecnico"], r["economico"], r["ambiental"], r["social"], r["indice"]
    cfg = r.get("config")
    projeto = getattr(cfg, "projeto", None) if not isinstance(cfg, dict) else cfg.get("projeto")
    linhas = [("Projeto", projeto or "(sem nome)")] if cfg is not None else []
    linhas += [
        ("Classificação", r["decisao"]["classificacao"]),
        ("Produção anual (kg)", num(t["producao_kg_ano"], 0)),
        ("OEE aquícola (0–1)", num(t["oee"], 3)),
        ("FCR (kg ração/kg ganho)", num(t["fcr"], 2)),
        ("Investimento total", reais(e["investimento_total"])),
        ("VPL (projeto)", reais(e["vpl"])),
        ("TIR (projeto)", tir_txt(e["tir_anual"], e["diagnostico_tir"])),
        ("Payback descontado", meses_ou_horizonte(e["payback_descontado_meses"])),
        ("VPL (beneficiário, com fomento)", reais(e["vpl_beneficiario"])),
        ("ROI anual em regime", pct_br(e["roi_anual_regime"])),
        ("Margem de segurança", pct_br(e["margem_seguranca"])),
        ("Custo total (R$/kg)", reais(e["custo_total_kg"], 2)),
        ("Pegada hídrica azul (m³/t)", num(a["ph_azul_m3_t"], 0)),
        ("Pegada hídrica cinza (m³/t)", num(a["ph_cinza_m3_t"], 0) + f" [{a['poluente_critico']}]"),
        ("Intensidade de carbono (kgCO2e/kg)", num(a["intensidade_carbono_kgco2e_kg"], 2)),
        ("Ecoeficiência (R$ VA/kgCO2e)", num(a["ecoeficiencia_r_por_kgco2e"], 2) if a["ecoeficiencia_status"] == "definida"
         else a["ecoeficiencia_status"]),
        ("Conformidade ambiental (0–10)", num(a["conformidade_0_10"], 2)),
        ("LSO (0–100)", num(s["lso_0_100"], 1)),
        ("RVL (%)", num(s["rvl_pct"], 1)),
        ("Renda mensal por trabalhador", reais(s["renda_mensal_trabalhador"])),
        ("Índice EVTEAS (0–1)", num(i["indice_evteas"], 3)),
        ("Score ESG (0–1)", num(i["esg_score"], 3)),
    ]
    if "monte_carlo" in r:
        st = r["monte_carlo"]["estatisticas"]
        linhas += [("P(VPL > 0) — Monte Carlo", pct_br(st["prob_vpl_positivo"])),
                   ("VPL médio — Monte Carlo", reais(st["media_vpl"])),
                   ("P(VPL beneficiário > 0)", pct_br(st["prob_vpl_beneficiario_positivo"]))]
    return pd.DataFrame(linhas, columns=["Indicador", "Valor"])


def tabela_sensibilidade(r: Dict[str, Any]) -> pd.DataFrame:
    """Sensibilidade a ±10%, valor crítico e correlação de Spearman de cada variável, formatadas para o texto."""
    from .campos_texto import _critico, _rotulo_var, _sens10, num, reais
    sens = _sens10(r)
    imp = r["monte_carlo"]["importancia"].set_index("Variável")["Spearman com VPL"] if "monte_carlo" in r else {}
    linhas = []
    for _, x in sens.iterrows():
        v = x["Variável"]
        nulo = "Valor base" in x and float(x["Valor base"]) == 0
        linhas.append({"Variável": _rotulo_var(v) + (" (valor nulo: variação absoluta de ±0,1)" if nulo else ""),
                       "Δ VPL (−10%)": reais(x["Δ VPL (−)"]), "Δ VPL (+10%)": reais(x["Δ VPL (+)"]),
                       "Valor crítico (VPL = 0) e folga": _critico(r, v),
                       "Spearman com o VPL (Monte Carlo)": num(imp[v], 3) if v in imp else "—"})
    return pd.DataFrame(linhas)


def tabela_topsis(comparacao: Dict[str, Any]) -> pd.DataFrame:
    """Ranking TOPSIS das alternativas, formatado para o texto."""
    from .campos_texto import num, pct_br, reais
    t = comparacao["ranking"]
    return pd.DataFrame([{
        "Posição": f"{int(x['Ranking'])}º", "Alternativa": x["Alternativa"], "VPL": reais(x["VPL (R$)"]),
        "P(VPL>0)": pct_br(x["P(VPL>0)"]), "OEE": num(x["OEE"], 3), "PH cinza (m³/t)": num(x["PH cinza (m³/t)"], 0),
        "kgCO2e/kg": num(x["Intensidade carbono (kgCO2e/kg)"], 2), "LSO": num(x["LSO"], 1), "RVL (%)": num(x["RVL (%)"], 1),
        "Índice EVTEAS": num(x["Índice EVTEAS"], 3), "TOPSIS": num(x["TOPSIS"], 3), "Classificação": x["Classificação"]}
        for _, x in t.iterrows()])


def serializar(obj):
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    if isinstance(obj, pd.Series):
        return obj.to_dict()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return obj.item()
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    if isinstance(obj, dict):
        return {str(k): serializar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serializar(v) for v in obj]
    return obj


def _df_dict(d: Dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([{"Indicador": k, "Valor": v} for k, v in d.items()
                         if not isinstance(v, (dict, list, pd.DataFrame, np.ndarray))])


def exportar(r: Dict[str, Any], pasta="evteas_output") -> List[str]:
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    xlsx = pasta / "EVTEAS_Py_resultados.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        resumo_executivo(r).to_excel(w, sheet_name="Resumo", index=False)
        r["premissas"].to_excel(w, sheet_name="Premissas", index=False)
        _df_dict(r["tecnico"]).to_excel(w, sheet_name="Tecnico", index=False)
        r["curva_crescimento"].to_excel(w, sheet_name="Curva_Crescimento", index=False)
        _df_dict({k: v for k, v in r["economico"].items() if k != "aliquotas"}).to_excel(w, sheet_name="Economico", index=False)
        r["dre_mensal"].to_excel(w, sheet_name="DRE_Mensal", index=False)
        r["dre_anual"].to_excel(w, sheet_name="DRE_Anual", index=False)
        pd.DataFrame({"Mês": range(len(r["fluxo_caixa"])), "Fluxo de caixa": r["fluxo_caixa"]}).to_excel(
            w, sheet_name="Fluxo_Caixa", index=False)
        _df_dict(r["ambiental"]).to_excel(w, sheet_name="Ambiental", index=False)
        pd.DataFrame(r["ambiental"]["conformidade_detalhe"]).to_excel(w, sheet_name="Conformidade", index=False)
        _df_dict(r["social"]).to_excel(w, sheet_name="Social", index=False)
        r["ods"].to_excel(w, sheet_name="ODS", index=False)
        pd.DataFrame([{"Desperdício": k, "R$/ano": v} for k, v in r["lean_green"]["desperdicios_r_ano"].items()]
                     ).to_excel(w, sheet_name="Lean_Green", index=False)
        pd.DataFrame({"KPI": list(r["indice"]["kpis_brutos"]),
                      "Valor bruto": list(r["indice"]["kpis_brutos"].values()),
                      "Normalizado": [r["indice"]["kpis_normalizados"][k] for k in r["indice"]["kpis_brutos"]]}
                     ).to_excel(w, sheet_name="KPIs", index=False)
        pd.DataFrame([{"Dimensão": k, "Score": v, "Peso": r["indice"]["pesos"]["dimensoes"][k]}
                      for k, v in r["indice"]["dimensoes"].items()]).to_excel(w, sheet_name="Indice", index=False)
        if "monte_carlo" in r:
            mc = r["monte_carlo"]
            mc["amostra"].to_excel(w, sheet_name="MC_Amostra", index=False)
            _df_dict({k: (str(v) if isinstance(v, tuple) else v) for k, v in mc["estatisticas"].items()}).to_excel(
                w, sheet_name="MC_Estatisticas", index=False)
            mc["convergencia"].to_excel(w, sheet_name="MC_Convergencia", index=False)
            mc["importancia"].to_excel(w, sheet_name="MC_Importancia", index=False)
        for chave, aba in (("sensibilidade", "Sensibilidade"), ("valores_criticos", "Valores_Criticos"),
                           ("cenarios", "Cenarios")):
            if chave in r:
                r[chave].to_excel(w, sheet_name=aba, index=False)
        pd.DataFrame(r["vv"]["verificacoes"]).to_excel(w, sheet_name="VV", index=False)
    arquivos.append(str(xlsx))
    js = pasta / "EVTEAS_Py_resultados.json"
    leve = {k: v for k, v in r.items() if k not in ("dre_mensal",)}
    if "monte_carlo" in leve:
        leve = dict(leve)
        leve["monte_carlo"] = {k: v for k, v in r["monte_carlo"].items() if k != "amostra"}
    with open(js, "w", encoding="utf-8") as f:
        json.dump(serializar(leve), f, ensure_ascii=False, indent=2, default=str)
    arquivos.append(str(js))
    md = pasta / "EVTEAS_Py_relatorio.md"
    md.write_text(relatorio_markdown(r), encoding="utf-8")
    arquivos.append(str(md))
    return arquivos


def relatorio_markdown(r: Dict[str, Any]) -> str:
    linhas = [f"# Relatório EVTEAS-Py — {r['config']['projeto']}", "", f"Gerado por: {r['artefato']}", "",
              "## Resumo executivo", "", "| Indicador | Valor |", "|---|---|"]
    linhas += [f"| {a} | {b} |" for a, b in resumo_executivo(r).itertuples(index=False)]
    d = r["decisao"]
    linhas += ["", "## Decisão", "", f"**{d['classificacao']}**", ""]
    linhas += [f"- Veto: {v}" for v in d["vetos"]] + [f"- Ressalva: {v}" for v in d["ressalvas"]]
    linhas += ["", "## ODS atendidos", ""] + [f"- {o}" for o, ok in zip(r["ods"]["ODS"], r["ods"]["Atendido"]) if ok]
    vv = r["vv"]
    linhas += ["", "## Verificação", "", f"{vv['quantidade_verificacoes']} verificações; {vv['quantidade_erros']} falha(s)."]
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
                         "figure.dpi": 100, "savefig.dpi": 220})
    return plt


AZUL, LARANJA, VERDE, CINZA, VERMELHO = "#2a6f97", "#e07a1f", "#4c956c", "#6c757d", "#c0392b"


def gerar_graficos(r: Dict[str, Any], pasta="evteas_output/figuras", comparacao: Dict[str, Any] = None) -> Dict[str, str]:
    plt = _plt()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    figs: Dict[str, str] = {}

    from matplotlib.ticker import ScalarFormatter

    class FormatadorBR(ScalarFormatter):               # vírgula decimal e ponto de milhar nos eixos
        def __call__(self, x, pos=None):
            return super().__call__(x, pos).replace(",", "X").replace(".", ",").replace("X", ".")

    def salvar(fig, nome):
        p = pasta / nome
        for ax in fig.axes:
            for eixo in (ax.xaxis, ax.yaxis):
                if type(eixo.get_major_formatter()) is ScalarFormatter and eixo.get_scale() == "linear":
                    eixo.set_major_formatter(FormatadorBR())
        fig.tight_layout()
        fig.savefig(p, bbox_inches="tight")
        plt.close(fig)
        figs[nome.split(".")[0]] = str(p)

    # 1. Curva de crescimento
    cc = r["curva_crescimento"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(cc["Dia"], cc["Peso médio (g)"], color=AZUL, lw=2, label="Peso médio (g)")
    ax.set_xlabel("Dia do ciclo"); ax.set_ylabel("Peso médio (g)", color=AZUL)
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(cc["Dia"], cc["Biomassa (kg)"] / 1000, color=LARANJA, lw=2, label="Biomassa (t)")
    ax2.plot(cc["Dia"], cc["Ração acumulada (kg)"] / 1000, color=CINZA, lw=1.5, ls="--", label="Ração acumulada (t)")
    ax2.set_ylabel("t", color=LARANJA)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    ax.set_title("Curva de crescimento, biomassa e arraçoamento por ciclo")
    salvar(fig, "01_curva_crescimento.png")

    # 2. Receita, custos e fluxo acumulado
    df = r["dre_mensal"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["Mês"], df["Receita Bruta"] / 1000, color=AZUL, lw=1.8, label="Receita bruta")
    ax.plot(df["Mês"], (df["Custos Variáveis"] + df["Custos Fixos"]) / 1000, color=LARANJA, lw=1.8, label="Custos operacionais")
    ax.set_xlabel("Mês"); ax.set_ylabel("R$ mil/mês")
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(range(len(r["fluxo_caixa"])), np.cumsum(r["fluxo_caixa"]) / 1000, color=VERDE, lw=2, label="Fluxo de caixa acumulado")
    ax2.axhline(0, color=CINZA, lw=0.8)
    ax2.set_ylabel("R$ mil (acumulado)", color=VERDE)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", frameon=False)
    ax.set_title("Projeção mensal: receita, custos e fluxo de caixa acumulado")
    salvar(fig, "02_projecao_economica.png")

    # 3. Scores dimensionais
    dims = r["indice"]["dimensoes"]
    rot = {"tecnico": "Técnica", "economico": "Econômica", "ambiental": "Ambiental", "social": "Social"}
    fig, ax = plt.subplots(figsize=(7, 3.6))
    vals = [dims[k] for k in rot]
    ax.barh(list(rot.values()), vals, color=[AZUL, LARANJA, VERDE, CINZA])
    for y, v in enumerate(vals):
        ax.text(v + 0.01, y, f"{v:.3f}".replace(".", ","), va="center")
    ax.axvline(r["indice"]["indice_evteas"], color=VERMELHO, ls="--", lw=1.2,
               label=f"Índice EVTEAS = {r['indice']['indice_evteas']:.3f}".replace(".", ","))
    ax.set_xlim(0, 1); ax.set_xlabel("Score normalizado (0–1)"); ax.invert_yaxis()
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, -0.18)); ax.set_title("Scores dimensionais e índice integrado")
    salvar(fig, "03_dimensoes.png")

    # 4. Radar social
    radar = r["social"]["radar_social"]
    nomes = list(radar); valores = [radar[k] for k in nomes]
    ang = np.linspace(0, 2 * np.pi, len(nomes), endpoint=False).tolist()
    fig = plt.figure(figsize=(5.2, 5.2)); ax = fig.add_subplot(111, polar=True)
    ax.plot(ang + ang[:1], valores + valores[:1], color=VERDE, lw=2)
    ax.fill(ang + ang[:1], valores + valores[:1], color=VERDE, alpha=0.25)
    ax.set_xticks(ang); ax.set_xticklabels(nomes, fontsize=9); ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels(["0,25", "0,50", "0,75", "1,00"], fontsize=7, color=CINZA)
    ax.tick_params(axis="x", pad=8)
    ax.set_title("Radar Social", pad=18)
    salvar(fig, "04_radar_social.png")

    if "monte_carlo" in r:
        mc = r["monte_carlo"]; v = mc["amostra"]["VPL"] / 1000; st = mc["estatisticas"]
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
        axs[0].hist(v, bins=60, color=AZUL, alpha=0.85)
        axs[0].axvline(0, color=VERMELHO, ls="--", lw=1.2, label="VPL = 0")
        axs[0].axvline(r["economico"]["vpl"] / 1000, color=LARANJA, lw=1.5, label="Determinístico (moda)")
        axs[0].axvline(st["media_vpl"] / 1000, color=VERDE, lw=1.5, label="Média Monte Carlo")
        axs[0].set_xlabel("VPL (R$ mil)"); axs[0].set_ylabel("Frequência"); axs[0].legend(frameon=False, fontsize=8)
        axs[0].set_title("Distribuição do VPL")
        xs = np.sort(v); axs[1].plot(xs, np.arange(1, len(xs) + 1) / len(xs), color=AZUL, lw=2)
        axs[1].axvline(0, color=VERMELHO, ls="--", lw=1.2)
        axs[1].set_xlabel("VPL (R$ mil)"); axs[1].set_ylabel("Probabilidade acumulada")
        axs[1].set_title(f"P(VPL ≤ 0) = {st['prob_vpl_negativo']:.1%}".replace(".", ","))
        salvar(fig, "05_monte_carlo_vpl.png")

        conv = mc["convergencia"]
        fig, ax = plt.subplots(figsize=(7, 3.6))
        ax.errorbar(conv["Iterações"], conv["Média VPL"] / 1000, yerr=1.96 * conv["Erro-padrão"] / 1000,
                    color=AZUL, marker="o", ms=3, capsize=3)
        ax.set_xscale("log"); ax.set_xlabel("Iterações (escala log)"); ax.set_ylabel("Média do VPL (R$ mil) ± IC95%")
        ax.set_title("Convergência da simulação de Monte Carlo")
        salvar(fig, "06_convergencia_mc.png")

    if "sensibilidade" in r:
        s = r["sensibilidade"]; s = s[s["Amplitude"] == s["Amplitude"].min()].copy()
        s = s.sort_values("Amplitude do efeito")
        from .campos_texto import _rotulo_var
        rotulo = s["Variável"].map(_rotulo_var)
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.barh(rotulo, s["Δ VPL (−)"] / 1000, color=LARANJA, label="−10%")
        ax.barh(rotulo, s["Δ VPL (+)"] / 1000, color=AZUL, label="+10%")
        ax.axvline(0, color="black", lw=0.8)
        ax.set_xlabel("Variação do VPL (R$ mil)"); ax.legend(frameon=False)
        ax.set_title("Diagrama de tornado — sensibilidade do VPL a ±10%")
        salvar(fig, "07_tornado.png")

    if comparacao is not None:
        import textwrap
        rk = comparacao["ranking"]
        fig, ax = plt.subplots(figsize=(7, 1.4 + 0.55 * len(rk)))
        nomes_alt = [textwrap.fill(str(a), 30) for a in rk["Alternativa"]]
        ax.barh(nomes_alt, rk["TOPSIS"], color=[VERDE, AZUL, CINZA][: len(rk)])
        for y, v in enumerate(rk["TOPSIS"]):
            ax.text(v + 0.01, y, f"{v:.3f}".replace(".", ","), va="center")
        ax.set_xlim(0, 1); ax.invert_yaxis(); ax.set_xlabel("Proximidade relativa à solução ideal (TOPSIS)")
        ax.set_title("Comparação de alternativas de projeto")
        salvar(fig, "08_topsis.png")
    return figs


def diagrama_arquitetura(caminho="evteas_output/figuras/00_arquitetura.png") -> str:
    """Diagrama do fluxo Input → Processamento → Output → Verificação."""
    plt = _plt()
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(10, 4.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    caixas = [
        (0.1, 3.3, 2.0, 1.4, "Entradas\nEVTEASConfig\n+ registro de fontes", "#dbe9f6"),
        (2.6, 3.3, 2.2, 1.4, "Motor vetorizado\ntécnico → econômico\n→ ambiental → social", "#fde8d0"),
        (5.3, 3.3, 2.0, 1.4, "Normalização\npesos (preset/\nLikert/AHP)", "#e3f1e6"),
        (7.8, 3.3, 2.1, 1.4, "Índice EVTEAS\nESG, ODS\nregra de decisão", "#eee"),
        (2.6, 0.6, 2.2, 1.6, "Incerteza\nMonte Carlo (n iterações)\nsensibilidade, cenários,\nvalores críticos", "#fde8d0"),
        (5.3, 0.6, 2.0, 1.6, "Verificação (V&V)\ninvariantes e\ntestes automatizados", "#e3f1e6"),
        (7.8, 0.6, 2.1, 1.6, "Saídas\nExcel, JSON,\nrelatório e figuras\nTOPSIS", "#eee"),
    ]
    for x, y, w, h, txt, cor in caixas:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=cor, ec="#555", lw=1))
        ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=9)
    seta = dict(arrowstyle="->", color="#333", lw=1.2)
    for (x1, y1), (x2, y2) in [((2.15, 4.0), (2.55, 4.0)), ((4.85, 4.0), (5.25, 4.0)), ((7.35, 4.0), (7.75, 4.0)),
                               ((3.7, 3.25), (3.7, 2.25)), ((4.85, 1.4), (5.25, 1.4)), ((7.35, 1.4), (7.75, 1.4)),
                               ((8.85, 3.25), (8.85, 2.25))]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=seta)
    ax.set_title("Arquitetura do EVTEAS-Py", fontsize=12)
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, bbox_inches="tight"); plt.close(fig)
    return caminho

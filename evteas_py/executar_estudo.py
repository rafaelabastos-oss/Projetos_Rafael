"""Executa o estudo completo do caso-base e gera todas as saídas utilizadas no Capítulo 4.

Uso: python executar_estudo.py [pasta_saida]
"""
import json
import sys
import time

from evteas_py import (comparar_alternativas, criar_alternativas, criar_config_caso_base, criar_config_caso_controle,
                       diagrama_arquitetura, executar_evteas, exemplo_validacao_especialistas, exportar,
                       gerar_graficos, relatorio_dsr, resumo_executivo, teste_regressao_deterministica)
from evteas_py.interface import carregar_config, salvar_config
from evteas_py.relatorios import serializar

ENTRADAS_CASO_BASE = "entradas/entradas_caso_base.json"


def main(pasta="saidas"):
    t0 = time.perf_counter()
    assert teste_regressao_deterministica()
    # As premissas do caso-base ficam em um arquivo de entradas, como as de qualquer projeto:
    # no notebook, ele é aberto pela opção "Carregar arquivo de entradas e revisar".
    from pathlib import Path
    Path(ENTRADAS_CASO_BASE).parent.mkdir(exist_ok=True)
    salvar_config(criar_config_caso_base(), ENTRADAS_CASO_BASE)
    cfg = carregar_config(ENTRADAS_CASO_BASE)
    r = executar_evteas(cfg, executar_mc=True, executar_sens=True)
    comp = comparar_alternativas(criar_alternativas(), n_mc=10000)
    controle = executar_evteas(criar_config_caso_controle(), executar_mc=True, executar_sens=False)
    likert = executar_evteas(exemplo_validacao_especialistas(cfg), executar_mc=False, executar_sens=False)
    arquivos = exportar(r, pasta)
    figs = gerar_graficos(r, f"{pasta}/figuras", comp)
    figs["00_arquitetura"] = diagrama_arquitetura(f"{pasta}/figuras/00_arquitetura.png")
    comp["ranking"].to_csv(f"{pasta}/topsis_alternativas.csv", index=False)
    # Registro do ciclo DSR (etapas, comparação, rastreabilidade e aprendizagens)
    dsr_tabelas = relatorio_dsr(Path(__file__).resolve().parent / "tests")
    for nome, tabela in dsr_tabelas.items():
        tabela.to_csv(f"{pasta}/{nome}.csv", index=False)
    resumo = {
        "tempo_execucao_s": time.perf_counter() - t0,
        "caso_base": serializar({k: r[k] for k in ("tecnico", "economico", "ambiental", "social", "governanca",
                                                    "lean_green", "decisao", "sobras")}),
        "indice": serializar({k: v for k, v in r["indice"].items() if k != "pesos"}),
        "pesos": serializar(r["indice"]["pesos"]),
        "mc": serializar({k: v for k, v in r["monte_carlo"].items() if k != "amostra"}),
        "sensibilidade": serializar(r["sensibilidade"]),
        "valores_criticos": serializar(r["valores_criticos"]),
        "cenarios": serializar(r["cenarios"]),
        "vv": serializar(r["vv"]),
        "ods": serializar(r["ods"]),
        "topsis": serializar(comp["ranking"]),
        "controle": serializar({"economico": controle["economico"], "tecnico": controle["tecnico"],
                              "ambiental": controle["ambiental"], "indice": {k: v for k, v in controle["indice"].items() if k != "pesos"},
                              "mc": controle["monte_carlo"]["estatisticas"], "decisao": controle["decisao"]}),
        "likert": serializar({"pesos": likert["indice"]["pesos"], "indice": likert["indice"]["indice_evteas"],
                              "decisao": likert["decisao"]}),
        "dsr": {"rastreabilidade": serializar(dsr_tabelas["DSR_Rastreabilidade"])},
        "figuras": figs, "arquivos": arquivos,
    }
    with open(f"{pasta}/resumo_execucao.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)
    print(resumo_executivo(r).to_string(index=False))
    print(comp["ranking"][["Alternativa", "TOPSIS", "Ranking", "Classificação"]].to_string(index=False))
    print(f"V&V: {r['vv']['quantidade_verificacoes']} verificações, {r['vv']['quantidade_erros']} falha(s)")
    print(f"Tempo total: {resumo['tempo_execucao_s']:.1f} s")


if __name__ == "__main__":
    main(*sys.argv[1:])

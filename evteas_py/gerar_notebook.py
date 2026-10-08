"""Gera EVTEAS_Py_Rev187.ipynb autocontido (para Google Colab) a partir do pacote."""
import re
from pathlib import Path

import nbformat as nbf

MODULOS = ["config", "financeiro", "modelo", "ponderacao", "incerteza", "pipeline", "vv", "casos", "relatorios", "interface", "dsr"]
TITULOS = {
    "config": "1. Configuração, premissas e rastreabilidade das fontes",
    "financeiro": "2. Engenharia econômica vetorizada (VPL, TIR com diagnóstico, payback)",
    "modelo": "3. Núcleo de cálculo: dimensões técnica, econômica, ambiental, social e Lean-Green",
    "ponderacao": "4. Normalização, pesos (preset, Likert, AHP), índice EVTEAS, decisão e TOPSIS",
    "incerteza": "5. Incerteza: Monte Carlo, sensibilidade, valores críticos e cenários",
    "pipeline": "6. Pipeline principal reproduzível",
    "vv": "7. Verificação (V&V): invariantes e testes de regressão",
    "casos": "8. Caso-base, alternativas e preset legado da Rev. 186",
    "relatorios": "9. Resumo executivo, exportação e gráficos",
    "interface": "10. Entrada de dados: menu inicial, wizard completo, arquivos JSON e análise de preços",
    "dsr": "11. Registro do ciclo da Design Science Research: etapas, requisitos, comparação e aprendizagens",
}


RAIZ = Path(__file__).resolve().parent


def codigo_do_modulo(m: str) -> str:
    return limpar((RAIZ / "evteas_py" / f"{m}.py").read_text(encoding="utf-8")).strip()


def limpar(codigo: str) -> str:
    codigo = re.sub(r"^[ \t]*from \.\w* import \([^)]*\)\n", "", codigo, flags=re.M | re.S)
    codigo = re.sub(r"^[ \t]*from \.\w* import [^\n]*\n", "", codigo, flags=re.M)
    codigo = codigo.replace("from __future__ import annotations\n", "")
    return codigo


def celulas():
    c = [nbf.v4.new_markdown_cell(
        "# EVTEAS-Py 2.0 (Rev. 187)\n\n"
        "Framework computacional para Estudo de Viabilidade Técnica, Econômica, Ambiental e Social (EVTEAS) "
        "aplicado à piscicultura — dissertação de Rafael Alves Bastos (UFF/MESC).\n\n"
        "**Como usar**\n\n"
        "1. Execute as células das Seções 1 a 11 (definições do framework). Elas não calculam nenhum resultado.\n"
        "2. Execute a célula da **Seção 12 — Entrada de dados** e responda às perguntas. Há três opções:\n"
        "   - **Novo projeto**: todas as entradas são digitadas (sem valores prontos). Só os coeficientes técnicos com "
        "referência normativa ou bibliográfica aparecem como sugestão, aceita com Enter e registrada como tal;\n"
        "   - **Carregar arquivo**: reabre um arquivo `entradas_*.json` salvo anteriormente e permite revisar cada valor;\n"
        "   - **Exemplo**: carrega o caso ilustrativo da dissertação, apenas para demonstração.\n"
        "3. Confira o resumo das entradas, confirme e execute as Seções 13 a 15. A Seção 16 (opcional) mostra a "
        "rastreabilidade do artefato segundo as etapas da Design Science Research.\n\n"
        "Os resultados dependem integralmente das entradas informadas. Ao final da entrada, o arquivo "
        "`entradas_<projeto>.json` é salvo (e baixado no Colab) para que o estudo possa ser reaberto e revisado. "
        "Digite `sair` em qualquer pergunta para interromper."),
        nbf.v4.new_code_cell("# Dependências (no Colab, apenas numpy-financial costuma faltar)\n"
                             "%pip install -q numpy pandas matplotlib openpyxl numpy-financial"),
        nbf.v4.new_code_cell("from __future__ import annotations\nimport warnings\nwarnings.filterwarnings('ignore', category=RuntimeWarning)")]
    for m in MODULOS:
        c.append(nbf.v4.new_markdown_cell(f"## {TITULOS[m]}"))
        c.append(nbf.v4.new_code_cell(codigo_do_modulo(m)))
    c += [
        nbf.v4.new_markdown_cell("## 12. Entrada de dados do projeto\n\n"
                                 "Execute a célula e responda às perguntas. Nenhum resultado é calculado antes desta etapa."),
        nbf.v4.new_code_cell("cfg = iniciar_entradas()"),
        nbf.v4.new_markdown_cell("## 13. Análise com as entradas informadas"),
        nbf.v4.new_code_cell("assert teste_regressao_deterministica()\n"
                             "resultado = executar_evteas(cfg, executar_mc=True, executar_sens=True,\n"
                             "                            n_mc=int(cfg.monte_carlo.iteracoes))\n"
                             "print('Classificação:', resultado['decisao']['classificacao'])\n"
                             "for motivo in resultado['decisao']['vetos'] + resultado['decisao']['ressalvas']:\n"
                             "    print(' -', motivo)\n"
                             "resumo_executivo(resultado)"),
        nbf.v4.new_code_cell("resultado['premissas']   # valor, origem e distribuição de cada premissa"),
        nbf.v4.new_code_cell("resultado['dre_anual'].round(0)"),
        nbf.v4.new_code_cell("st = resultado['monte_carlo']['estatisticas']\n"
                             "{k: v for k, v in st.items() if not isinstance(v, dict)}"),
        nbf.v4.new_code_cell("resultado['monte_carlo']['importancia']"),
        nbf.v4.new_code_cell("display(resultado['valores_criticos'])\ndisplay(resultado['cenarios'])"),
        nbf.v4.new_code_cell("resultado['ods']"),
        nbf.v4.new_code_cell("import pandas as pd\npd.DataFrame(resultado['vv']['verificacoes'])"),
        nbf.v4.new_markdown_cell("## 14. Comparação com alternativas de projeto (opcional, TOPSIS)\n\n"
                                 "Cada alternativa parte das entradas do projeto; escolha os blocos a alterar e informe os novos valores."),
        nbf.v4.new_code_cell("comparacao = definir_e_comparar_alternativas(cfg)\n"
                             "comparacao['ranking'] if comparacao else 'Comparação não solicitada.'"),
        nbf.v4.new_markdown_cell("## 15. Exportação e gráficos"),
        nbf.v4.new_code_cell("pasta = 'evteas_output'\n"
                             "arquivos = exportar(resultado, pasta)\n"
                             "figuras = gerar_graficos(resultado, pasta + '/figuras', comparacao)\n"
                             "diagrama_arquitetura(pasta + '/figuras/00_arquitetura.png')\n"
                             "from IPython.display import Image\n"
                             "for f in sorted(figuras.values()):\n    display(Image(f))\narquivos"),
        nbf.v4.new_markdown_cell("## 16. Rastreabilidade do artefato (Design Science Research) — opcional\n\n"
                                 "Etapas da DSR (Dresch; Lacerda; Antunes Jr., 2015), comparação com artefatos preexistentes "
                                 "(Wazlawick, 2009), matriz requisito → função → teste e aprendizagens registradas. "
                                 "Fora do repositório, a pasta de testes não está disponível e os testes não são conferidos."),
        nbf.v4.new_code_cell("for nome, tabela in relatorio_dsr().items():\n    print(nome)\n    display(tabela)"),
    ]
    return c


def main(destino="EVTEAS_Py_Rev187.ipynb"):
    nb = nbf.v4.new_notebook()
    nb["cells"] = celulas()
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbf.write(nb, destino)
    print("ok", len(nb["cells"]), "células")


if __name__ == "__main__":
    main()

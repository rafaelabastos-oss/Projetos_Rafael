"""Gera EVTEAS_Py.ipynb autocontido (para Google Colab) a partir do pacote."""
import re
from pathlib import Path

import nbformat as nbf

MODULOS = ["config", "financeiro", "modelo", "ponderacao", "incerteza", "pipeline", "vv", "casos", "relatorios", "interface", "dsr", "campos_texto"]
TITULOS = {
    "config": "1. Configuração, premissas e rastreabilidade das fontes",
    "financeiro": "2. Engenharia econômica vetorizada (VPL, TIR com diagnóstico, payback)",
    "modelo": "3. Núcleo de cálculo: dimensões técnica, econômica, ambiental, social e Lean-Green",
    "ponderacao": "4. Normalização, pesos (preset, Likert, AHP), índice EVTEAS, decisão e TOPSIS",
    "incerteza": "5. Incerteza: Monte Carlo, sensibilidade, valores críticos e cenários",
    "pipeline": "6. Pipeline principal reproduzível",
    "vv": "7. Verificação (V&V): invariantes e testes de regressão",
    "casos": "8. Caso ilustrativo e alternativas de referência",
    "relatorios": "9. Resumo executivo, exportação e gráficos",
    "interface": "10. Entrada de dados: menu inicial, wizard completo, arquivos JSON e análise de preços",
    "dsr": "11. Registro do ciclo da Design Science Research: etapas, requisitos, comparação e aprendizagens",
    "campos_texto": "12. Valores para o texto: lacunas E, R, K e N do relato dos resultados",
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
        "# EVTEAS-Py\n\n"
        "Framework computacional para Estudo de Viabilidade Técnica, Econômica, Ambiental e Social (EVTEAS) "
        "aplicado à piscicultura — dissertação de Rafael Alves Bastos (UFF/MESC).\n\n"
        "**Como usar**\n\n"
        "1. Execute as células das Seções 1 a 12 (definições do framework). Elas não calculam nenhum resultado.\n"
        "2. Execute a célula da **Seção 13 — Entrada de dados** e responda às perguntas. Há três opções:\n"
        "   - **Novo projeto**: todas as entradas são digitadas (sem valores prontos). Só os coeficientes técnicos com "
        "referência normativa ou bibliográfica aparecem como sugestão, aceita com Enter e registrada como tal;\n"
        "   - **Carregar arquivo**: reabre um arquivo `entradas_*.json` salvo anteriormente e permite revisar cada valor;\n"
        "   - **Exemplo**: carrega o caso ilustrativo incorporado ao pacote, apenas para demonstração.\n"
        "3. Confira o resumo das entradas, confirme e execute as Seções 14 a 17. A Seção 18 (opcional) mostra a "
        "rastreabilidade do artefato segundo as etapas da Design Science Research.\n\n"
        "**Relato dos resultados na dissertação.** Os Capítulos 4 e 5 trazem lacunas com código ([E..] para entradas e "
        "[S..], [K..] e [N..] para resultados) e espaços para prints ([INSERIR PRINT P..]). A Seção 16 mostra e exporta o "
        "valor de cada código nesta execução (`valores_para_o_texto.xlsx`, com o roteiro de prints numa segunda aba), e "
        "cada tela do wizard ou saída a capturar é anunciada por uma linha `▶ PRINT P..`. Para a dissertação, execute "
        "também a Seção 15 (comparação de alternativas) antes da Seção 16.\n\n"
        "Os resultados dependem integralmente das entradas informadas. Ao final da entrada, o arquivo "
        "`entradas_<projeto>.json` é salvo (e baixado no Colab) para que o estudo possa ser reaberto e revisado. "
        "Digite `sair` em qualquer pergunta para interromper: as respostas já dadas são salvas num arquivo "
        "`entradas_<projeto>_rascunho.json`, que pode ser reaberto pela opção 2 para continuar de onde parou. "
        "Números podem ser digitados no padrão brasileiro (40.000 ou 1.500,50)."),
        nbf.v4.new_code_cell("# Dependências (no Colab, apenas numpy-financial costuma faltar)\n"
                             "%pip install -q numpy pandas matplotlib openpyxl numpy-financial"),
        nbf.v4.new_code_cell("from __future__ import annotations\nimport warnings\nwarnings.filterwarnings('ignore', category=RuntimeWarning)")]
    for m in MODULOS:
        c.append(nbf.v4.new_markdown_cell(f"## {TITULOS[m]}"))
        c.append(nbf.v4.new_code_cell(codigo_do_modulo(m)))
    c += [
        nbf.v4.new_markdown_cell("## 13. Entrada de dados do projeto\n\n"
                                 "Execute a célula e responda às perguntas. Nenhum resultado é calculado antes desta etapa. "
                                 "Para o relato do Capítulo 4, capture as telas do wizard indicadas no roteiro de prints."),
        nbf.v4.new_code_cell("roteiro_de_prints()        # telas e saídas que ilustram o Capítulo 4"),
        nbf.v4.new_code_cell("cfg = resultado = comparacao = None   # nada de uma execução anterior é reaproveitado\n"
                             "cfg = iniciar_entradas()"),
        nbf.v4.new_markdown_cell("## 14. Análise com as entradas informadas"),
        nbf.v4.new_code_cell("exigir_entradas(cfg)\n"
                             "assert teste_regressao_deterministica()\n"
                             "resultado = executar_evteas(cfg, executar_mc=True, executar_sens=True,\n"
                             "                            n_mc=int(cfg.monte_carlo.iteracoes))\n"
                             "print(titulo_print('P13'))\n"
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
        nbf.v4.new_markdown_cell("## 15. Comparação com alternativas de projeto (TOPSIS)\n\n"
                                 "Cada alternativa parte das entradas do projeto; escolha os blocos a alterar e informe os novos valores. "
                                 "É opcional para o uso do artefato, mas a Seção 4 da dissertação a utiliza: execute-a antes da Seção 16. "
                                 "O Monte Carlo de cada alternativa usa as mesmas iterações e a mesma seed da análise principal."),
        nbf.v4.new_code_cell("comparacao = None\n"
                             "comparacao = definir_e_comparar_alternativas(exigir_entradas(cfg), n_mc=int(cfg.monte_carlo.iteracoes))\n"
                             "for aviso in (comparacao or {}).get('avisos', []):\n    print('⚠', aviso)\n"
                             "if comparacao:\n    print(titulo_print('P19'))\n"
                             "tabela_topsis(comparacao) if comparacao else 'Comparação não solicitada.'"),
        nbf.v4.new_markdown_cell("## 16. Valores para o texto\n\n"
                                 "Valor de cada lacuna dos Capítulos 4 e 5 nesta execução, na ordem do texto, com a origem declarada "
                                 "de cada entrada. A tabela é gravada em `evteas_output/valores_para_o_texto.xlsx` (baixada no Colab), "
                                 "com o roteiro de prints numa segunda aba."),
        nbf.v4.new_code_cell("exigir_entradas(cfg)\n"
                             "valores = valores_para_o_texto(cfg, resultado, globals().get('comparacao'))\n"
                             "print('Planilha:', exportar_valores_para_o_texto(valores, 'evteas_output', baixar=True))\n"
                             "pd.set_option('display.max_rows', None, 'display.max_colwidth', None)\n"
                             "valores"),
        nbf.v4.new_markdown_cell("## 17. Exportação e gráficos\n\n"
                                 "Cada gráfico é precedido da linha `▶ PRINT P..` que indica a figura do Capítulo 4 a que se destina. "
                                 "Os PNGs ficam em `evteas_output/figuras`; no Colab, a pasta `evteas_output` é compactada e baixada."),
        nbf.v4.new_code_cell("pasta = 'evteas_output'\n"
                             "arquivos = exportar(resultado, pasta)\n"
                             "figuras = gerar_graficos(resultado, pasta + '/figuras', globals().get('comparacao'))\n"
                             "diagrama_arquitetura(pasta + '/figuras/00_arquitetura.png')\n"
                             "from IPython.display import Image\n"
                             "saidas = {codigo: figuras[nome] for nome, codigo in FIGURA_DO_PRINT.items() if nome in figuras}\n"
                             "saidas['P17'] = None          # tabela de sensibilidade\n"
                             "for codigo in sorted(saidas):\n"
                             "    print(titulo_print(codigo))\n"
                             "    display(tabela_sensibilidade(resultado) if codigo == 'P17' else Image(saidas[codigo]))\n"
                             "import shutil\n"
                             "pacote = shutil.make_archive('evteas_output', 'zip', pasta)\n"
                             "baixar_no_colab(pacote)       # figuras, planilhas e relatório (só tem efeito no Colab)\n"
                             "arquivos"),
        nbf.v4.new_markdown_cell("## 18. Rastreabilidade do artefato (Design Science Research) — opcional\n\n"
                                 "Etapas da DSR (Dresch; Lacerda; Antunes Jr., 2015), comparação com artefatos preexistentes "
                                 "(Wazlawick, 2009), matriz requisito → função → teste e aprendizagens registradas. "
                                 "Fora do repositório, a pasta de testes não está disponível e os testes não são conferidos."),
        nbf.v4.new_code_cell("for nome, tabela in relatorio_dsr().items():\n    print(nome)\n    display(tabela)"),
    ]
    return c


def main(destino="EVTEAS_Py.ipynb"):
    nb = nbf.v4.new_notebook()
    nb["cells"] = celulas()
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbf.write(nb, destino)
    print("ok", len(nb["cells"]), "células")


if __name__ == "__main__":
    main()

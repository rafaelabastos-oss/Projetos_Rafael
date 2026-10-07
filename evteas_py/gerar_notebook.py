"""Gera EVTEAS_Py_Rev187.ipynb autocontido (para Google Colab) a partir do pacote."""
import re
import nbformat as nbf

MODULOS = ["config", "financeiro", "modelo", "ponderacao", "incerteza", "pipeline", "vv", "casos", "relatorios", "interface"]
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
    "interface": "10. Entrada interativa (wizard), arquivos JSON e análise de preços",
}


def limpar(codigo: str) -> str:
    codigo = re.sub(r"^[ \t]*from \.\w* import \([^)]*\)\n", "", codigo, flags=re.M | re.S)
    codigo = re.sub(r"^[ \t]*from \.\w* import [^\n]*\n", "", codigo, flags=re.M)
    codigo = codigo.replace("from __future__ import annotations\n", "")
    return codigo


nb = nbf.v4.new_notebook()
c = [nbf.v4.new_markdown_cell(
    "# EVTEAS-Py 2.0 (Rev. 187)\n\n"
    "Framework computacional para Estudo de Viabilidade Técnica, Econômica, Ambiental e Social (EVTEAS) "
    "aplicado à piscicultura — dissertação de Rafael Alves Bastos (UFF/MESC).\n\n"
    "Este notebook é autocontido: reúne o código do pacote `evteas_py` em células, na ordem "
    "Input → Processamento → Output → Verificação. As premissas do caso-base são ilustrativas e "
    "devem ser substituídas pelos dados do projeto avaliado e calibradas na validação com especialistas."),
    nbf.v4.new_code_cell("# Dependências (no Colab, apenas numpy-financial costuma faltar)\n"
                         "%pip install -q numpy pandas matplotlib openpyxl numpy-financial"),
    nbf.v4.new_code_cell("from __future__ import annotations\nimport warnings\nwarnings.filterwarnings('ignore', category=RuntimeWarning)")]
for m in MODULOS:
    c.append(nbf.v4.new_markdown_cell(f"## {TITULOS[m]}"))
    c.append(nbf.v4.new_code_cell(limpar(open(f"evteas_py/{m}.py", encoding="utf-8").read()).strip()))
c += [
    nbf.v4.new_markdown_cell("## 11. Execução do caso-base\n\nPara usar outro projeto: `cfg = wizard_evteas()` "
                             "(entrada interativa) ou `cfg = carregar_config('meu_projeto.json')`."),
    nbf.v4.new_code_cell("assert teste_regressao_deterministica()\n"
                         "cfg = criar_config_caso_base()\n"
                         "# cfg = wizard_evteas()            # entrada interativa completa\n"
                         "resultado = executar_evteas(cfg, executar_mc=True, executar_sens=True)\n"
                         "resumo_executivo(resultado)"),
    nbf.v4.new_code_cell("print(resultado['decisao'])\nresultado['premissas'].head(20)"),
    nbf.v4.new_code_cell("resultado['dre_anual'].round(0)"),
    nbf.v4.new_code_cell("st = resultado['monte_carlo']['estatisticas']\n"
                         "{k: v for k, v in st.items() if not isinstance(v, dict)}"),
    nbf.v4.new_code_cell("resultado['monte_carlo']['importancia']"),
    nbf.v4.new_code_cell("display(resultado['valores_criticos'])\ndisplay(resultado['cenarios'])"),
    nbf.v4.new_code_cell("resultado['ods']"),
    nbf.v4.new_code_cell("import pandas as pd\npd.DataFrame(resultado['vv']['verificacoes'])"),
    nbf.v4.new_markdown_cell("## 12. Comparação de alternativas (TOPSIS) e parametrização por especialistas (Likert)"),
    nbf.v4.new_code_cell("comparacao = comparar_alternativas(criar_alternativas(), n_mc=5000)\ncomparacao['ranking']"),
    nbf.v4.new_code_cell("r_likert = executar_evteas(exemplo_validacao_especialistas(cfg), executar_mc=False, executar_sens=False)\n"
                         "display(r_likert['indice']['pesos']['likert_dimensoes']['tabela'])\nprint(r_likert['decisao'])"),
    nbf.v4.new_markdown_cell("## 13. Exportação e gráficos"),
    nbf.v4.new_code_cell("arquivos = exportar(resultado, 'evteas_output')\n"
                         "figuras = gerar_graficos(resultado, 'evteas_output/figuras', comparacao)\n"
                         "diagrama_arquitetura('evteas_output/figuras/00_arquitetura.png')\n"
                         "salvar_config(cfg, 'evteas_output/config_caso_base.json')\n"
                         "from IPython.display import Image\n"
                         "for f in sorted(figuras.values()):\n    display(Image(f))\narquivos"),
]
nb["cells"] = c
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "EVTEAS_Py_Rev187.ipynb")
print("ok", len(c), "células")

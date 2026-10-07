"""Gera o notebook autocontido do Google Colab (EVTEAS_Py_Colab.ipynb) a partir do pacote evteas_py.

Os formulários são gerados a partir do registro único de entradas (evteas_py/entradas.py), de modo que
notebook, planilha, assistente e marcadores [E-xx] permanecem sincronizados. Nenhuma entrada do
projeto é preenchida: os campos começam em branco.
Uso: python ferramentas/gerar_notebook.py [saida.ipynb]
"""
import sys
from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from evteas_py import entradas as ent  # noqa: E402
from evteas_py.config import VERSAO  # noqa: E402
from evteas_py.ponderacao import KPIS  # noqa: E402

MODULOS = ["config", "financeiro", "entradas", "modelo", "ponderacao", "incerteza", "pipeline", "relatorios",
           "interface", "vv", "__init__"]
DESCRICAO_MODULOS = {
    "config": "estrutura das entradas, parâmetros do método, conversão de taxas e formatação",
    "financeiro": "VPL, TIR com diagnóstico e payback",
    "entradas": "registro das entradas [E-xx], formulário, planilha e alternativas",
    "modelo": "motor único das dimensões técnica, econômica, ambiental e social, governança e Lean-Green",
    "ponderacao": "normalização dos KPIs, pesos (preset, Likert, AHP), índice, decisão e TOPSIS",
    "incerteza": "Monte Carlo, importância, sensibilidade, valores críticos e cenários",
    "pipeline": "execução integrada do estudo e comparação de alternativas",
    "relatorios": "marcadores [R-xx], tabelas, figuras, exportações e preenchimento do .docx",
    "interface": "assistente interativo de entrada e análise de preços",
    "vv": "verificação por invariantes e testes automatizados (dados sintéticos de teste)",
    "__init__": "interface pública do pacote",
}

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip("\n")))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip("\n")))


def _val_metodo(e):
    v = e.padrao
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return ent.fmt_auto(v)
    return str(v)


def campo(e):
    obrig = " \\*" if (e.obrigatorio and not e.metodo) else ""
    unid = f" — {e.unidade}" if e.unidade not in ("—", "") else ""
    ajuda = f" ({e.ajuda})" if e.ajuda else ""
    linhas = [f"#@markdown **[{e.marcador}]** {e.rotulo}{unid}{obrig}{ajuda}"]
    padrao = _val_metodo(e) if e.metodo else ""
    if e.tipo == "opcao":
        ops = ", ".join(f'"{o}"' for o in (("",) if not e.metodo else ()) + tuple(e.opcoes))
        linhas.append(f'{e.var} = "{padrao}"  #@param [{ops}]')
    elif e.tipo == "bool":
        ops = '"sim", "não"' if e.metodo else '"", "sim", "não"'
        linhas.append(f'{e.var} = "{padrao}"  #@param [{ops}]')
    else:
        linhas.append(f'{e.var} = "{padrao}"  #@param {{type:"string"}}')
    return linhas


def form(titulo, intro, entradas_):
    linhas = [f'#@title {titulo} {{ display-mode: "form" }}']
    for t in intro:
        linhas.append(f"#@markdown {t}")
    linhas.append("#@markdown ---")
    for e in entradas_:
        linhas += campo(e)
    code("\n".join(linhas))


por_grupo = lambda g: [e for e in ent.ENTRADAS if e.grupo == g]
INSTR = ["Campos com \\* são obrigatórios. Use vírgula decimal (1,5); o ponto de milhar é opcional (40.000).",
         "Campos opcionais em branco = \"não se aplica\". Após preencher, execute a célula (▶)."]

# ------------------------------------------------------------------------------------------------
md(f"""
# EVTEAS-Py {VERSAO} — Estudo de Viabilidade Técnica, Econômica, Ambiental e Social de projetos de piscicultura

Notebook autocontido do *framework* EVTEAS-Py (APÊNDICE A da dissertação). Executa no Google Colab sem
instalação local: a Seção 1 grava o código-fonte e as demais seções conduzem o estudo.

**Sequência de uso**

1. **Seção 1** — instala as dependências e grava o código do EVTEAS-Py (execute uma vez por sessão).
2. **Seção 2** — informe as entradas do projeto. **Nenhuma entrada vem preenchida**: o estudo só é executado
   quando todas as entradas obrigatórias estiverem informadas. Escolha o modo de entrada na célula 2.0:
   formulários desta seção, planilha `.xlsx`, arquivo de premissas `.json` de uma execução anterior ou
   assistente interativo.
3. **Seção 3** — valida as entradas e executa o estudo (determinístico, Monte Carlo, sensibilidade,
   valores críticos, cenários, decisão e, se declaradas, alternativas por TOPSIS).
4. **Seção 4** — verificação (invariantes e testes automatizados).
5. **Seção 5** — tabela de marcadores: cada `[E-xx]` (entrada) e `[R-xx]` (resultado) do texto da
   dissertação recebe o valor desta execução.
6. **Seção 6** — baixa todas as saídas em um `.zip` (Excel, JSON, Markdown, CSV de marcadores e figuras).
7. **Seção 7** (opcional) — preenche automaticamente os marcadores do `.docx` da dissertação.
8. **Seção 8** — somente **após** os questionários de validação (Apêndices C e D): pesos Likert dos especialistas.

Menu *Ambiente de execução → Executar tudo* executa as seções em ordem; a execução para na Seção 3 e
lista as entradas pendentes enquanto houver campos obrigatórios em branco.
""")

md("## 1 Preparação do ambiente e código-fonte")
code("""
#@title 1.1 Instalar dependências { display-mode: "form" }
%pip install -q python-docx openpyxl
""")
code("""
#@title 1.2 Criar a pasta do pacote { display-mode: "form" }
import os
os.makedirs("evteas_py", exist_ok=True)
print("Pasta evteas_py pronta.")
""")
md("### 1.3 Código-fonte do EVTEAS-Py\n\nCada célula grava um módulo do pacote (`%%writefile`). "
   "O código pode ser lido e auditado aqui; não é necessário editá-lo para realizar o estudo.")
for m in MODULOS:
    fonte = (RAIZ / "evteas_py" / f"{m}.py").read_text(encoding="utf-8")
    md(f"#### Módulo `{m}` — {DESCRICAO_MODULOS[m]}")
    code(f"%%writefile evteas_py/{m}.py\n{fonte}")
code("""
#@title 1.4 Carregar o pacote { display-mode: "form" }
import sys
sys.path.insert(0, ".")
for _m in [m for m in sys.modules if m.startswith("evteas_py")]:
    del sys.modules[_m]
import pandas as pd
from IPython.display import HTML, Markdown, display
import evteas_py as ev
from evteas_py import entradas as ent, relatorios as rel, vv

pd.set_option("display.max_colwidth", 140)
pd.set_option("display.max_rows", 500)
try:
    from google.colab import files as colab_files
except ImportError:          # execução fora do Colab (Jupyter local)
    colab_files = None


class Pendencia(Exception):
    \"\"\"Interrompe a execução com uma mensagem curta (sem rastreamento de pilha).\"\"\"
    def _render_traceback_(self):
        return [f"⚠ {self}"]


def baixar(caminho):
    if colab_files is not None:
        colab_files.download(caminho)
    else:
        print("Arquivo gerado em:", os.path.abspath(caminho))


def enviar(extensao, caminho_informado=""):
    if caminho_informado:
        return caminho_informado
    if colab_files is None:
        raise Pendencia(f"Fora do Colab, informe o caminho do arquivo {extensao} no campo correspondente.")
    enviados = colab_files.upload()
    nomes = [n for n in enviados if n.lower().endswith(extensao)]
    if not nomes:
        raise Pendencia(f"Nenhum arquivo {extensao} foi enviado.")
    return nomes[0]


print(f"EVTEAS-Py {ev.VERSAO} carregado. Prossiga para a Seção 2.")
""")

# ------------------------------------------------------------------------------------------------
md("""
## 2 Entradas do projeto

Todas as entradas começam **em branco**. Os marcadores entre colchetes (por exemplo, **[E-T03]**) são os
mesmos do Quadro de premissas da dissertação (Seção 4.2), preenchido com os valores informados aqui.
Os parâmetros do método (célula 2.10) vêm com os valores documentados no Capítulo 3 e podem ser alterados.
""")
code("""
#@title 2.0 Modo de entrada { display-mode: "form" }
#@markdown **formulário**: preencha as células 2.1 a 2.10. **planilha (.xlsx)**: gere a planilha na célula 2.11,
#@markdown preencha-a (com a origem de cada premissa) e envie-a na Seção 3. **arquivo de premissas (.json)**: reutiliza
#@markdown as entradas de uma execução anterior (EVTEAS_premissas.json). **assistente interativo**: perguntas uma a uma.
MODO_ENTRADA = "formulário"  #@param ["formulário", "planilha (.xlsx)", "arquivo de premissas (.json)", "assistente interativo"]
#@markdown Caminho do arquivo (opcional; em branco, o Colab pede o envio do arquivo):
ARQUIVO_ENTRADAS = ""  #@param {type:"string"}
""")
form("2.1 Identificação e dimensão técnica", INSTR, por_grupo("Identificação") + por_grupo("Técnica"))
form("2.2 Dimensão econômica", INSTR + ["Mix de produtos (opcional): `nome; participação; fator de preço | ...` "
                                         "(ex.: `Inteira; 0,7; 1 | Filé; 0,3; 2,4`). Em branco = produto único."],
     por_grupo("Econômica"))
cells[-1].source += '\n#@markdown **[E-E25]** Mix de produtos (opcional)\nmix_produtos = ""  #@param {type:"string"}'
code("\n".join(['#@title 2.3 Investimento (CAPEX) { display-mode: "form" }',
                "#@markdown Um item por campo, no formato `descrição; valor (R$); vida útil (anos)`, por exemplo",
                "#@markdown `Escavação dos viveiros; 380.000; 20`. Informe ao menos um item. Campos vazios são ignorados.",
                "#@markdown ---"]
               + [f'capex_{i:02d} = ""  #@param {{type:"string"}}' for i in range(1, ent.N_CAPEX + 1)]))
form("2.4 Dimensão ambiental", INSTR + ["Limites da Resolução CONAMA nº 357/2005 para águas doces classe 2 (art. 15): "
                                        "P total 0,030 mg/L (lêntico), 0,050 mg/L (intermediário) e 0,1 mg/L (lótico); "
                                        "N total 1,27 mg/L (lêntico) e 2,18 mg/L (lótico), quando o N for limitante. "
                                        "Confira a classe do corpo receptor no enquadramento vigente."],
     por_grupo("Ambiental"))
form("2.5 Dimensão social e governança", INSTR, por_grupo("Social") + por_grupo("Governança"))
form("2.6 Referências Lean-Green (boas práticas declaradas)",
     ["Valores de referência usados para quantificar desperdícios evitáveis (FCR, mortalidade e energia)."],
     por_grupo("Lean-Green"))
code("\n".join(['#@title 2.7 Distribuições de incerteza para o Monte Carlo { display-mode: "form" }',
                "#@markdown Informe `mín; máx` (a moda é o valor determinístico informado nas células anteriores) ou",
                "#@markdown `mín; moda; máx` (a moda deve coincidir com o valor informado). Em branco = premissa determinística.",
                "#@markdown Para os fatores de CAPEX e de custos fixos a moda é 1; para o desempenho de crescimento, 100.",
                "#@markdown Informe ao menos uma distribuição. ---"]
               + sum([[f"#@markdown **[{m}]** {rot} — {unid}", f'{var} = ""  #@param {{type:"string"}}']
                      for m, var, cam, rot, unid in ent.DISTRIBUICOES], [])))
alt_linhas = ['#@title 2.8 Alternativas de projeto para comparação por TOPSIS (opcional) { display-mode: "form" }',
              "#@markdown A alternativa A é o projeto informado acima. Para B e C, informe um nome, as alterações",
              "#@markdown no formato `variável = valor; variável = valor` (nomes dos campos dos formulários, por exemplo",
              "#@markdown `fonte_energia = solar; fracao_renovavel_pct = 90`) e, se houver, o CAPEX adicional no formato",
              "#@markdown `descrição; valor; vida útil | descrição; valor; vida útil`. Em branco = alternativa não avaliada.",
              "#@markdown ---"]
for a in ent.CAMPOS_ALTERNATIVAS:
    alt_linhas += [f"#@markdown **[E-X{a}]** Alternativa {a}",
                   f'alt_{a}_nome = ""  #@param {{type:"string"}}',
                   f'alt_{a}_alteracoes = ""  #@param {{type:"string"}}',
                   f'alt_{a}_capex_adicional = ""  #@param {{type:"string"}}']
code("\n".join(alt_linhas))
code("\n".join(['#@title 2.9 Origem das premissas (rastreabilidade, Seção 3.6) { display-mode: "form" }',
                "#@markdown Formato: `variável = categoria (referência); ...`, por exemplo",
                "#@markdown `preco_venda_kg = cotação (CEASA-RJ, jun. 2026); fcr = parâmetro bibliográfico (Kubitza, 2017)`.",
                "#@markdown Categorias: " + "; ".join(ent.CATEGORIAS_FONTE) + ".",
                "#@markdown Premissas sem origem aparecem como \"não informada\" no Quadro de premissas. Na planilha .xlsx há",
                "#@markdown uma coluna própria para a origem de cada premissa.",
                'fontes = ""  #@param {type:"string"}']))
form("2.10 Parâmetros do método (Capítulo 3)",
     ["Valores documentados no Capítulo 3. Altere somente se a mudança for justificada no texto."],
     por_grupo("Parâmetros do método"))
code("""
#@title 2.11 Planilha de entradas em branco (somente no modo planilha) { display-mode: "form" }
if MODO_ENTRADA.startswith("planilha"):
    ent.gerar_planilha_entradas("EVTEAS_entradas.xlsx")
    print("Planilha gerada: preencha as abas Entradas, CAPEX, Distribuições e Alternativas e envie-a na Seção 3.")
    baixar("EVTEAS_entradas.xlsx")
else:
    print("Modo atual:", MODO_ENTRADA, "— esta célula não se aplica.")
""")

# ------------------------------------------------------------------------------------------------
md("## 3 Simulação")
code("""
#@title 3.1 Ler e validar as entradas { display-mode: "form" }
valores = ent.coletar_formulario(globals())
fontes_planilha = {}
if MODO_ENTRADA == "formulário":
    cfg, erros = ent.ler_formulario(valores)
elif MODO_ENTRADA.startswith("planilha"):
    v_planilha, fontes_planilha = ent.valores_de_planilha(enviar(".xlsx", ARQUIVO_ENTRADAS))
    valores.update({k: v for k, v in v_planilha.items() if str(v).strip()})
    cfg, erros = ent.ler_formulario(v_planilha)
    cfg.fontes.update(fontes_planilha)
elif MODO_ENTRADA.startswith("arquivo"):
    cfg = ev.carregar_config(enviar(".json", ARQUIVO_ENTRADAS))
    erros = ev.validar_config(cfg)
else:
    cfg = ev.wizard_evteas()
    erros = []
if erros:
    display(HTML("<b>Entradas pendentes ou inválidas</b><ul>" + "".join(f"<li>{e}</li>" for e in erros) + "</ul>"))
    raise Pendencia(f"{len(erros)} entrada(s) em branco ou inválida(s). Corrija-as na Seção 2 e execute esta célula novamente.")
alternativas_cfg = ent.alternativas_de_formulario(cfg, valores)
print(f"Entradas válidas. Alternativas declaradas: {', '.join(alternativas_cfg)}.")
display(ent.tabela_entradas(cfg))
""")
code("""
#@title 3.2 Executar o estudo { display-mode: "form" }
resultado = ev.executar_evteas(cfg)
alternativas = ev.comparar_alternativas(alternativas_cfg) if len(alternativas_cfg) > 1 else None
print(ev.resumo_executivo(resultado, cfg))
print(f"\\nTempo de execução: {resultado['tempo_execucao_s']:.1f} s")
""")
code("""
#@title 3.3 Tabelas de resultados (formato da dissertação) { display-mode: "form" }
for nome, tabela in ev.tabelas_dissertacao(resultado, cfg, alternativas).items():
    display(Markdown(f"**{nome}**"))
    display(tabela)
display(Markdown("**Decisão**"))
print(resultado["decisao"])
""")
code("""
#@title 3.4 Figuras { display-mode: "form" }
figuras = ev.gerar_figuras(resultado, cfg, "saidas/figuras", alternativas, mostrar=True)
""")

# ------------------------------------------------------------------------------------------------
md("## 4 Verificação")
code("""
#@title 4.1 Invariantes desta execução e testes automatizados { display-mode: "form" }
EXECUTAR_TESTES = True  #@param {type:"boolean"}
display(resultado["vv"]["tabela"])
print(f"Invariantes aprovados: {resultado['vv']['aprovadas']} de {resultado['vv']['total']}")
testes = None
if EXECUTAR_TESTES:
    print("Executando os testes automatizados (dados sintéticos de teste, não são dados do estudo)...")
    testes = ev.testes_automatizados(rapido=True)
    display(testes)
    print(f"Testes aprovados: {int(testes['Aprovado'].sum())} de {len(testes)}")
""")

# ------------------------------------------------------------------------------------------------
md("""
## 5 Marcadores para o texto da dissertação

Cada marcador do texto (`[E-xx]` = entrada informada; `[R-xx]` = resultado da simulação) recebe o valor
da coluna **Valor**. Os marcadores terminados em `F` trazem a origem declarada da entrada. Os textos
`R-TXTxx` são sugestões geradas por regras explícitas e devem ser revisados antes do uso.
""")
code("""
#@title 5.1 Tabela de marcadores { display-mode: "form" }
SECAO = "todas"  #@param ["todas", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "4.9", "4.10", "4.11", "4.x"]
marcadores = ev.marcadores(resultado, cfg, alternativas, testes, alternativas_cfg)
display(marcadores if SECAO == "todas" else marcadores[marcadores["Seção"] == SECAO])
""")

# ------------------------------------------------------------------------------------------------
md("## 6 Exportar as saídas")
code("""
#@title 6.1 Gerar e baixar o pacote de saídas (.zip) { display-mode: "form" }
arquivos = ev.exportar_tudo(resultado, cfg, "saidas", figuras=True, alternativas=alternativas, testes=testes,
                            configs_alternativas=alternativas_cfg)
for k, v in arquivos.items():
    print(f"{k:>18}: {v}")
baixar(arquivos["zip"])
""")

# ------------------------------------------------------------------------------------------------
md("""
## 7 Preencher o .docx da dissertação (opcional)

Envie o `.docx` que contém os marcadores `[E-xx]`, `[R-xx]` e `[FIG-...]`. O EVTEAS-Py troca cada marcador pelo
valor desta execução (mantendo a formatação do trecho), insere as figuras e devolve uma cópia preenchida.
Depois, no Word, atualize o sumário e as listas (Ctrl+A, F9).
""")
code("""
#@title 7.1 Preencher marcadores no .docx { display-mode: "form" }
ARQUIVO_DOCX = ""  #@param {type:"string"}
entrada_docx = enviar(".docx", ARQUIVO_DOCX)
saida_docx = os.path.splitext(os.path.basename(entrada_docx))[0] + "_preenchido.docx"
rel_docx = ev.preencher_docx(entrada_docx, saida_docx, marcadores, figuras)
print(rel_docx)
baixar(saida_docx)
""")

# ------------------------------------------------------------------------------------------------
md("""
## 8 Pesos Likert dos especialistas (somente após os questionários)

Preencha com as notas de 1 a 5 atribuídas pelos especialistas a cada KPI no questionário de validação
(Apêndice C, bloco de relevância dos indicadores). O avaliador 2 é opcional. A célula reexecuta o estudo com
os pesos Likert e gera os marcadores `[R-L01]` a `[R-L05]`, que comparam o resultado com o preset.
""")
lk = ['#@title 8.1 Notas Likert por KPI (1 = nada relevante; 5 = extremamente relevante) { display-mode: "form" }',
      'AVALIADOR_1 = ""  #@param {type:"string"}', 'AVALIADOR_2 = ""  #@param {type:"string"}', "#@markdown ---"]
for k, (dim, rot, *_r) in KPIS.items():
    lk.append(f"#@markdown **{rot}** (dimensão {dim})")
    lk.append(f'likert1_{k} = ""  #@param ["", "1", "2", "3", "4", "5"]')
    lk.append(f'likert2_{k} = ""  #@param ["", "1", "2", "3", "4", "5"]')
code("\n".join(lk))
code("""
#@title 8.2 Reexecutar com os pesos Likert { display-mode: "form" }
from evteas_py.config import copiar
from evteas_py.ponderacao import KPIS
escores = {}
for n, nome in ((1, AVALIADOR_1), (2, AVALIADOR_2)):
    notas = {k: globals().get(f"likert{n}_{k}", "") for k in KPIS}
    if not nome.strip() and not any(notas.values()):
        continue
    faltam = [KPIS[k][1] for k, v in notas.items() if not str(v).strip()]
    if faltam or not nome.strip():
        raise Pendencia(f"Avaliador {n}: informe o nome e as notas de todos os KPIs (faltam: {', '.join(faltam) or 'nome'}).")
    escores[nome.strip()] = {k: int(v) for k, v in notas.items()}
if not escores:
    raise Pendencia("Preencha as notas de ao menos um avaliador na célula 8.1 (após os questionários).")
cfg_likert = copiar(cfg)
cfg_likert.pesos.metodo = "likert"
cfg_likert.pesos.likert = escores
resultado_likert = ev.executar_evteas(cfg_likert)
comparacao_pesos = rel.comparar_pesos(resultado, resultado_likert)
display(comparacao_pesos)
marcadores = pd.concat([ev.marcadores(resultado, cfg, alternativas, testes, alternativas_cfg), comparacao_pesos],
                       ignore_index=True)
comparacao_pesos.to_csv("saidas/EVTEAS_marcadores_likert.csv", sep=";", index=False, encoding="utf-8-sig")
print("Marcadores [R-Lxx] acrescentados à tabela de marcadores (use a Seção 7 para preencher o .docx).")
""")

# ------------------------------------------------------------------------------------------------
md("## 9 Ferramenta de apoio: análise de preços de mercado (opcional)")
code("""
#@title 9.1 Percentis de cotações e curva de demanda { display-mode: "form" }
#@markdown Envie um .csv com a coluna `preco` (R$/kg) e, opcionalmente, `quantidade` (kg). Os percentis P10 e P90
#@markdown orientam o mínimo e o máximo da distribuição do preço (célula 2.7).
ARQUIVO_PRECOS = ""  #@param {type:"string"}
CUSTO_VARIAVEL_KG = ""  #@param {type:"string"}
precos = pd.read_csv(enviar(".csv", ARQUIVO_PRECOS), sep=None, engine="python", decimal=",")
analise = ev.analise_precos(precos, ent.ler_numero(CUSTO_VARIAVEL_KG) if CUSTO_VARIAVEL_KG.strip() else None)
display(pd.Series(analise["sugestoes"], name="R$/kg"))
print("Distribuição sugerida para o preço (P10; P90):", analise["distribuicao_sugerida"])
if analise["preco_otimo"] is not None:
    print(f"Preço que maximiza a margem de contribuição: R$ {ent.fmt_auto(round(analise['preco_otimo'], 2))}/kg")
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb["metadata"] = {"colab": {"provenance": [], "toc_visible": True, "name": "EVTEAS_Py_Colab.ipynb"},
                  "kernelspec": {"display_name": "Python 3", "name": "python3"},
                  "language_info": {"name": "python"}}
saida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "EVTEAS_Py_Colab.ipynb"
nbf.write(nb, saida)
print(f"Notebook gerado: {saida} ({len(cells)} células)")

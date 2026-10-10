# EVTEAS-Py

Framework em Python para Estudo de Viabilidade Técnica, Econômica, Ambiental e
Social (EVTEAS) aplicado à piscicultura — dissertação de Rafael Alves Bastos (UFF/MESC).

## Conteúdo

| Caminho | O que é |
|---|---|
| `evteas_py/` | Pacote: `config`, `financeiro`, `modelo`, `ponderacao`, `incerteza`, `pipeline`, `vv`, `casos`, `relatorios`, `interface`, `dsr`, `campos_texto` |
| `EVTEAS_Py.ipynb` | Notebook autocontido (Google Colab), gerado por `gerar_notebook.py` |
| `tests/` | Testes automatizados (pytest); números atualizados em `saidas/verificacao_testes.json` |
| `saidas/` | Figura de arquitetura e resultado da suíte de testes (não há execução de referência do estudo) |
| `documentacao/` | Scripts que geram os Capítulos 4 e 5 da dissertação (com controle de alterações) |

## Relato dos resultados (Capítulo 4)

O texto dos Capítulos 4 e 5 é um **modelo de preenchimento**: não traz números de uma simulação
prévia. Cada valor aparece como lacuna com código — `[E14 – FCR]` para uma entrada, `[S23 – VPL do
projeto]` para um resultado, `[K01]`/`[N01]` para o KPI bruto/normalizado — e cada figura de entrada
ou saída é um espaço `[INSERIR PRINT P01 – ...]`. Ao executar o notebook com os seus dados, a seção
**16. Valores para o texto** mostra o valor de cada código e grava `valores_para_o_texto.xlsx`
(com o roteiro de prints numa segunda aba); cada tela ou gráfico a capturar é anunciado por
`▶ PRINT P..`. O registro dos códigos fica em `evteas_py/campos_texto.py`, e o teste
`tests/test_campos_texto.py` garante que texto e registro tenham exatamente os mesmos códigos.

## Uso rápido

```bash
pip install -r requirements.txt
python -m pytest -q --cov=evteas_py tests/
```

```python
from evteas_py import executar_evteas, iniciar_entradas, resumo_executivo, valores_para_o_texto
cfg = iniciar_entradas()                # menu: novo projeto, carregar arquivo de entradas ou exemplo
r = executar_evteas(cfg)                # técnico, econômico, ambiental, social, índice, MC, sensibilidade, V&V
print(resumo_executivo(r))
print(valores_para_o_texto(cfg, r))     # valor de cada lacuna do Capítulo 4
```

## O que o código cobre (mapa para o texto)

- **Seção 2.8.6 / Quadro 5** — três blocos de entrada técnicos, CAPEX/OPEX/receitas, gestão hídrica,
  energética e conformidade, Radar Social; KPIs OEE, FCR, ROI, margem de segurança, pegada hídrica azul,
  ecoeficiência, LSO e RVL, mais pegada hídrica cinza (balanço de N e P), intensidade de carbono, ODS e governança.
- **Seção 3.4 / Quadro 7** — pesos por escala Likert de dois avaliadores (com divergência), AHP com razão de
  consistência ou preset; TOPSIS para comparar alternativas.
- **Seção 3.6** — registro da origem de cada premissa; distribuições uniforme/triangular/normal; Monte Carlo
  com média, mediana, desvio, variância, percentis, IC 95%, P(VPL<0), VaR/CVaR, convergência e Spearman.
- **Seção 3.3.2** — invariantes verificados a cada execução e suíte de testes independente.
- **Seção 3.3.1 (DSR, Dresch; Lacerda; Antunes Jr., 2015)** — módulo `dsr`: registro das 12 etapas com
  produto, evidência e situação; comparação de propriedades com artefatos preexistentes (Wazlawick, 2009);
  16 requisitos com a matriz requisito → função → teste conferida no código (`matriz_rastreabilidade()`,
  verificada em `tests/test_dsr.py`); e aprendizagens da Etapa 9.

## Decisões de projeto

1. Motor único vetorizado: o Monte Carlo usa o mesmo modelo mensal do cálculo determinístico.
2. TIR com diagnóstico (`convencional`, `multiplas`, `multiplas_possiveis`, `sem_solucao`); nunca um limite numérico.
3. Ecoeficiência = valor adicionado / impacto (WBCSD); “não definida” quando VA ≤ 0.
4. Qualidade do OEE = sobrevivência (Quadro 5); estocagem dimensionada e mortalidade incerta.
5. RVL com denominador do Quadro 5 (custo operacional total).
6. Receita após a 1ª despesca, depreciação, valor terminal e perspectiva do beneficiário de fomento.
7. Decisão em dois estágios: vetos não compensatórios + índice + P(VPL>0).
8. AHP e TOPSIS integrados ao pipeline.
9. Entrada de dados obrigatória antes de qualquer resultado; arquivos incompletos geram pendências.

O caso ilustrativo do pacote (opção “exemplo” e testes) tem premissas **ilustrativas**; os resultados da dissertação vêm da execução do autor com os dados do estudo de caso.

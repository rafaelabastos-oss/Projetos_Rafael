# EVTEAS-Py 2.0 (Rev. 187)

Framework em Python para Estudo de Viabilidade Técnica, Econômica, Ambiental e
Social (EVTEAS) aplicado à piscicultura — dissertação de Rafael Alves Bastos (UFF/MESC).

## Conteúdo

| Caminho | O que é |
|---|---|
| `evteas_py/` | Pacote: `config`, `financeiro`, `modelo`, `ponderacao`, `incerteza`, `pipeline`, `vv`, `casos`, `relatorios`, `interface`, `dsr` |
| `EVTEAS_Py_Rev187.ipynb` | Notebook autocontido (Google Colab), gerado por `gerar_notebook.py` |
| `executar_estudo.py` | Roda o estudo completo e grava `saidas/` |
| `tests/` | Testes automatizados (pytest); números atualizados em `saidas/verificacao_testes.json` |
| `saidas/` | Resultados da execução de referência (Excel, JSON, relatório, figuras) |
| `documentacao/` | Scripts que geram o texto da Rev. 187 com controle de alterações |

## Uso rápido

```bash
pip install -r requirements.txt
python executar_estudo.py saidas        # caso-base, alternativas, preset legado, Likert
python -m pytest -q --cov=evteas_py tests/
```

```python
from evteas_py import criar_config_caso_base, executar_evteas, resumo_executivo, wizard_evteas
cfg = criar_config_caso_base()          # ou wizard_evteas() / carregar_config("projeto.json")
r = executar_evteas(cfg)                # técnico, econômico, ambiental, social, índice, MC, sensibilidade, V&V
print(resumo_executivo(r))
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
  15 requisitos com a matriz requisito → função → teste conferida no código (`matriz_rastreabilidade()`,
  verificada em `tests/test_dsr.py`); e aprendizagens da Etapa 9.

## Correções em relação à Rev. 186

1. Motor único vetorizado: o Monte Carlo usa o mesmo modelo mensal do cálculo determinístico.
2. TIR com diagnóstico (`convencional`, `multiplas`, `multiplas_possiveis`, `sem_solucao`); nunca −0,95.
3. Ecoeficiência = valor adicionado / impacto (WBCSD); “não definida” quando VA ≤ 0.
4. Qualidade do OEE = sobrevivência (Quadro 5); estocagem dimensionada e mortalidade incerta.
5. RVL com denominador do Quadro 5 (custo operacional total).
6. Receita após a 1ª despesca, depreciação, valor terminal e perspectiva do beneficiário de fomento.
7. Decisão em dois estágios: vetos não compensatórios + índice + P(VPL>0).
8. AHP e TOPSIS integrados ao pipeline.

As premissas do caso-base são **ilustrativas** e devem ser recalibradas na validação com especialistas.

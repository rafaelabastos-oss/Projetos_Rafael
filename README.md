# Projeto SFI — Rota da Tilápia

Material didático para oficinas com cooperativas de pesca no âmbito do PEA Pescarte — pensado para ser usado em **qualquer município**.

Abra `index.html` no navegador para acessar o portal do projeto.

| Conteúdo | Caminho | Descrição |
|---|---|---|
| **Aquipólis Tycoon** | [`jogo/index.html`](jogo/index.html) | Simulação 3D de gestão da Unidade de Produção Aquícola (UPA), com expansão para UBP e UPP |
| Oficina UPA | [`oficinas/oficina-upa.html`](oficinas/oficina-upa.html) | Modelagem BPMN — Unidade de Produção Aquícola |
| Oficina UBP-M | [`oficinas/oficina-ubp-m.html`](oficinas/oficina-ubp-m.html) | Modelagem BPMN — Unidade de Beneficiamento de Pescado |
| Oficina UPP | [`oficinas/oficina-upp.html`](oficinas/oficina-upp.html) | Modelagem BPMN — Unidade de Processamento de Pescado |
| Documentos | [`docs/`](docs/) | Análises de impacto e comparação de layouts da UBP |

## Aquipólis Tycoon v1.1

### Novidades da v1.1

- **Qualquer município**: o nome da cidade é escolhido na introdução (padrão: *Aquipólis*, cidade fictícia) e aparece
  no jogo, nas notícias e no mural. Saíram todas as referências fixas a uma cidade ou região específica.
- **Aviso chamativo de despesca** (sugestão da turma): quando tanques ficam prontos, surge um alerta no centro da tela com som,
  uma faixa dourada fixa com a quantidade de tanques prontos e um contador no botão *Vender*, sem precisar clicar tanque por tanque.
- **Modo decisões** (sugestão da turma, “um jogo em que só aparecem as decisões”): a equipe cuida da rotina (povoar, alimentar,
  despescar e vender) e, a cada 10 dias, surge uma **demanda do dia**. As escolhas mudam o cenário: chuva, árvores plantadas
  em mutirão e o canteiro de obra que avança ou para.
- **Estatuto do GAO integrado ao jogo**:
  - a UBP e a UPP passam a exigir a **eleição do GAO** com as regras do Art. 27 (9 a 21 membros, ao menos 30% de mulheres e 1 a 3 jovens);
  - a construção vira uma **obra de ~2 meses acompanhada pelo GAO**, com canteiro e grua no cenário;
  - **reuniões do GAO** a cada 20 dias com situações do estatuto: atrasos, devolutivas obrigatórias, promessa de emprego, propaganda
    partidária, faltas, ata atrasada, abaixo-assinado por assembleia extraordinária e licenças;
  - no **Modo oficina**, a turma **vota** as opções e vence a maioria simples (50% + 1, Art. 31, VI);
  - cada decisão gera uma **ata** no novo **Mural de transparência** (tecla 9), que também reúne devolutivas, obras e contas;
  - na inauguração, a turma empossa o **CAE** (3 a 7 membros, remunerado) e o **CFE** (mínimo de 7), como preveem os Art. 16 e 24;
  - o relatório final ganha a dimensão **Gestão democrática e transparência**.
- Resumo didático do estatuto em *Aprender → Estatuto do GAO*.

As oficinas BPMN também deixaram de citar cidades nos títulos e textos. Só a linha “Fonte” mantém o nome do estudo de
viabilidade de origem. As etapas de licenciamento seguem as normas estaduais citadas nesses estudos.

Jogo de gestão em que o grupo conduz, por 12 meses, a unidade aquícola de uma cooperativa de 22 famílias:
organizar equipes, cuidar da água e da ração, negociar com compradores e decidir diante de imprevistos.
Com boa gestão, a cooperativa conquista os convênios da UBP (beneficiamento) e da UPP (processamento),
completando a Rota da Tilápia.

### Edição profissional v1.0 (base Rev. 18.3)

- **Tela de carregamento e menu principal** com o cenário 3D em órbita ao fundo.
- **Salvar e continuar**: salvamento automático ao fim de cada mês e ao fechar a aba; botão “Continuar” no menu.
- **Menu de pausa** (Esc ou ☰): continuar, salvar, configurações, atalhos, tutorial e voltar ao menu.
- **Configurações persistentes**: qualidade gráfica (baixa/média/alta), placas, efeitos sonoros, som ambiente,
  volume, tamanho da interface (90–130%, útil em projetores) e avisos de rotina.
- **Interface redesenhada** com ícones vetoriais consistentes no HUD, na barra de ações e nos controles,
  mais uma barra de progresso dos 12 meses.
- **Dicas ao passar o mouse** sobre tanques (estado, ciclo, biomassa, água) e prédios.
- **Atalhos de teclado**: `Espaço` pausa · `1–9` ações · `WASD`/setas câmera · `Q/E` girar · `F` centralizar ·
  `L` placas · `M` som · `H` lista de atalhos · `Esc` fechar/menu.
- **Balanço mensal** com indicadores e gráfico do resultado de cada mês.
- **Relatório final** com pontuação (0–100), conceito, gráfico da evolução do caixa e estrelas por dimensão.
- **Menos ruído**: avisos repetitivos (ração baixa, fome, despesca) passam a ter intervalo mínimo.
- **Correções**: o relatório final não sobrescreve mais a decisão e o balanço do 12º mês; as placas
  “Filtro rizosférico” agora respeitam o botão de mostrar/ocultar placas; o fundo do modal não fecha mais a introdução.
- Links para as oficinas de processos no menu **Aprender**.

### Como executar

Basta abrir `jogo/index.html` em um navegador moderno com WebGL (Chrome, Edge, Firefox ou Safari).
É necessária conexão com a internet para carregar o three.js (cdnjs) e as fontes (Google Fonts).
Para que os links entre o jogo, o portal e as oficinas funcionem, mantenha a estrutura de pastas do repositório.

O progresso do jogo e as anotações das oficinas ficam salvos apenas no navegador (`localStorage`).

# 🌱 Prompt Mestre — **Mundo Renda**

> Jogo para Android (APK) em que você cria **o seu projeto de geração de trabalho e renda** e o constrói, do seu jeito, num **mundo aberto**.

Este documento é o **prompt mestre** do jogo: a especificação completa, escrita para ser colada numa IA (Claude, por exemplo) ou entregue a uma equipe para **recriar, revisar ou expandir** o jogo. A versão 1.0 que está nesta pasta (`android/`) foi construída exatamente a partir dele, e o APK pronto está em `dist/MundoRenda.apk`.

**Como usar**

1. Copie tudo entre `INÍCIO DO PROMPT MESTRE` e `FIM DO PROMPT MESTRE`.
2. Cole numa conversa com uma IA de programação.
3. Para pedir mudanças, acrescente no final, por exemplo: *"Com base no prompt mestre acima, adicione um sistema de cooperativas vizinhas que compram seus produtos"*.

---

```text
==================== INÍCIO DO PROMPT MESTRE ====================
```

## 1. Papel

Você é um(a) **game designer e desenvolvedor(a) sênior** especializado(a) em jogos mobile de construção e simulação (estilo *city-builder* aconchegante), em **economia solidária** e em **Android**. Escreve código limpo, comentado em português, sem dependências externas, e entrega um APK funcional.

## 2. Missão

Criar o jogo **Mundo Renda**, um APK Android **100% offline**, no qual o jogador:

1. **Inventa o próprio projeto de geração de trabalho e renda**: nome, símbolo, cor e ramo de atuação (agricultura familiar, reciclagem, cozinha, costura, artesanato e turismo, tecnologia, ou um ramo personalizado com nome livre).
2. **Constrói esse projeto num mundo aberto**, escolhendo livremente onde e como colocar cada casa, horta, oficina, feira, estrada, praça, árvore, lago e caminho: o layout é dele.
3. **Gera empregos, distribui renda e cuida do bem-estar da comunidade**, aprendendo na prática como funciona uma cadeia produtiva solidária.

## 3. Público, tom e valores

- **Público:** jovens e adultos, incluindo educadores, agentes comunitários, estudantes e participantes de programas de trabalho e renda. Fácil para quem nunca jogou *city-builder*.
- **Idioma:** português do Brasil, linguagem simples e acolhedora.
- **Tom:** positivo, colaborativo, sem violência e sem "game over" punitivo. O dinheiro pode ficar negativo; o jogo orienta (microcrédito, dicas) em vez de castigar.
- **Valores transmitidos:** trabalho digno, cooperação, renda que circula na comunidade, sustentabilidade, beleza do espaço público, capacitação, cuidado (creche, saúde).

## 4. Pilares de design

1. **Liberdade de layout:** nada é fixo. Construir, mover, melhorar, demolir, pintar o terreno, cavar lagos, aterrar, traçar estradas e pontes. Desfazer devolve o dinheiro.
2. **Impacto social visível:** os indicadores principais são **empregos**, **renda distribuída** (salários pagos) e **bem-estar**, não só o lucro.
3. **Aprender fazendo:** missões em sequência funcionam como tutorial; cada número tem explicação no jogo.
4. **Mundo vivo:** moradores andam nas ruas, dia e noite, números que sobem das construções, eventos, conversas no modo Passeio.
5. **Acessível e leve:** toque simples, botões grandes, roda em celulares modestos, sem internet.

## 5. Loop principal

```
Escolher ferramenta → Construir/arrumar o layout → Dia passa (produção → beneficiamento → vendas → salários)
→ Ver resultados (dinheiro, empregos, bem-estar, impacto) → Subir de nível / cumprir missão → Liberar novidades → repetir
```

## 6. Fluxo de telas

1. **Tela inicial:** uma vila de demonstração animada ao fundo; botões *Continuar* (último projeto), *Novo projeto*, *Meus projetos*, *Como jogar*.
2. **Assistente "Novo projeto"** (3 passos):
   - *Seu projeto:* nome (até 28 caracteres), símbolo (12 emojis) e cor (8 cores, usada em telhados, placas, bandeira e chapéu do personagem).
   - *Ramo principal:* 7 cartões (ver catálogo). "Personalizado" pede o nome do ramo.
   - *Seu mundo:* paisagem (Vale do Rio, Litoral, Terra dos Lagos, Cerrado), modo (**Desafio** ou **Criativo**) e semente numérica (com dado 🎲).
3. **Fundação:** o jogo pede para tocar num lugar livre do mapa e fundar o **Centro Comunitário** (grátis, único). O tempo só começa a correr depois disso.
4. **Jogo (HUD):** barra superior, missão atual, minimapa, zoom, barra de ferramentas inferior e paleta de itens.
5. **Painéis:** Projeto (indicadores, gráfico, estoque, microcrédito, personalização, compartilhar), Missões, Menu (salvar, projetos, ajuda, configurações, voltar ao início), cartão de construção.

## 7. Mecânicas detalhadas

### 7.1 Mundo aberto procedural
- Mapa isométrico de **96 × 96 ladrilhos**, gerado por **ruído fractal com semente** (mesma semente = mesmo mundo).
- Terrenos: grama, campo, grama seca, areia, terra, pedregulho e água (com espuma animada nas margens).
- Paisagens: **Vale do Rio** (rio sinuoso + lagos + colinas), **Litoral** (mar num lado, praia e coqueiros), **Terra dos Lagos**, **Cerrado** (chão seco, riacho fino, vegetação esparsa).
- Natureza gerada: árvores nativas, pinheiros, coqueiros, arbustos, rochas e flores do campo. Elas dão um pouco de beleza e podem ser removidas (R$ 5).
- Bordas do mapa com "laje" de terra, para parecer um tabuleiro flutuante.

### 7.2 Construção livre
- **Tocar** num item da paleta e depois no mapa constrói. Prévia fantasma verde (pode) ou vermelha (não pode), com o raio de efeito desenhado.
- **Estradas:** arrastar traça um caminho em "L", com o custo total mostrado. Sobre a água vira **ponte** automaticamente.
- **Pincéis:** árvores, flores, cerca viva, postes, terreno e demolir funcionam arrastando o dedo.
- Construir em cima de vegetação nativa limpa o terreno automaticamente (+R$ 5).
- **Cartão da construção** (toque no modo Selecionar): status, vagas ocupadas, produção real do dia, insumos, vendas, bônus ativos, manutenção, e ações **Melhorar** (até nível 3), **Mover** (10% do custo) e **Demolir** (devolve 50% do investido).
- **Melhorar** custa *custo × nível atual*; no nível N multiplica vagas, produção, moradores, vendas, estoque, renda e manutenção por N, e o prédio fica mais alto, com estrelas na placa.
- **Desfazer (↩️):** pilha de 40 ações, inclusive pinceladas e estradas inteiras; devolve ou estorna o dinheiro.

### 7.3 Conexão por estradas (o layout importa)
- Uma construção só funciona se estiver **ao lado (4 vizinhos) de uma estrada ligada ao Centro Comunitário** ou encostada nele. A ligação é calculada por busca em largura a partir do Centro.
- Construções sem acesso mostram um balão 🛣️ e não produzem, não vendem e não trazem moradores. Poço e painéis solares não precisam de estrada.

### 7.4 Economia (um ciclo por dia de jogo)
- **1 dia = 20 s** na velocidade 1× (velocidades: pausa, 1×, 2×, 4×). O dia vira à meia-noite.
- **Caixa inicial (Desafio):** R$ 6.000. **Salário:** R$ 18 por trabalhador por dia.
- **Trabalhadores:** `disponíveis = floor(população × participação)`, com `participação = 0,55 + 0,06 × creches (máx. 4) ≤ 0,85`. `empregados = min(disponíveis, vagas)`. A ocupação `o = empregados / vagas` vale igualmente para todas as construções.
- **Produtividade global:** `(1 + 0,06 × escolas, máx. 5) × eventos`.
- **Produção de cada unidade:** `base × nível × o × produtividade × bônus de ramo (+25%, ou +10% em tudo no ramo Personalizado) × bônus locais` (água/poço +20%, solar +10%, flores para o apiário até +100%, casas próximas para a coleta até +50%, eventos agrícolas).
- **Beneficiamento:** consome insumos do estoque na mesma proporção; se faltar insumo, produz proporcionalmente (alerta 📦).
- **Vendas:** primeiro as feiras (só alimentos), depois lojas e entregas. Cada ponto vende os produtos **mais caros primeiro**, até sua capacidade × nível × ocupação. `preço = base × multiplicador do ponto × (0,85 + 0,3 × bem-estar/100) × (1 + 0,05 × bancos, máx. 2)`.
- **Estoque:** Centro 300 + Armazéns 400 cada. O excedente se perde (aviso no painel), descartando primeiro o que vale menos.
- **Lucro do dia** = vendas + rendas diretas − salários − manutenção − parcela do microcrédito.
- **Renda distribuída** = soma de todos os salários pagos (indicador de impacto principal).

### 7.5 População e bem-estar
- Casas ligadas definem a capacidade. A população cresce a cada dia: `+max(1, round((capacidade − população) × 0,3 × (0,4 + bem-estar/100)))`.
- **Bem-estar de cada casa** = 40 + beleza ao redor (até 25) + saúde 12 + escola 5 + creche 6 (se dentro do raio) + 15 × taxa de emprego + eventos. O bem-estar geral é a média ponderada pelos moradores.
- **Beleza** é um mapa de influência: cada decoração soma seu valor com queda linear até o raio; água e ruas de pedra também embelezam.

### 7.6 Impacto, níveis e desbloqueios
- Pontos de impacto por dia = empregados + (vendas + rendas) / 50.
- 10 níveis (tabela abaixo). Cada item tem um nível mínimo; os itens do ramo escolhido começam liberados. Ao subir de nível, um aviso mostra as novidades.

### 7.7 Missões, eventos e microcrédito
- 18 missões em sequência servem de tutorial (tabela abaixo), com dica 💡 e recompensa em dinheiro.
- Eventos aleatórios a cada 10–18 dias (só no Desafio): editais, doações, chuva, estiagem, feira regional, curso, reportagem, quebra de equipamento. Os ativos aparecem como selos com os dias restantes.
- **Microcrédito:** R$ 3.000 na hora; paga R$ 40 por dia durante 90 dias (um por vez).

### 7.8 Modo Passeio (mundo aberto em primeira pessoa)
- Botão 🚶: um personagem com camiseta na cor do projeto aparece perto do Centro. **Joystick virtual** para andar; a câmera segue.
- Anda em grama, estradas, pontes, praças e canteiros; árvores, prédios e água bloqueiam.
- Ao chegar perto de uma construção, um cartão mostra o nome e o status (toque para detalhes). Moradores próximos falam frases sobre a vida no projeto em **balões de fala** desenhados por cima de tudo.

### 7.9 Vida no mundo
- **Moradores animados** andam pelas calçadas (ciclo de caminhada de 4 quadros, de frente e de costas, 18 visuais: tom de pele, cabelo, roupa, vestido, chapéu, bolsa). Quantidade proporcional a empregos e casas, menos à noite.
- **Veículos** nas ruas, na mão direita: bicicletas, **motos de entrega** com baú na cor do projeto e caminhonetes (com faróis à noite); mais veículos com lojas, beneficiamento e a Central de Entregas.
- **Ciclo de dia e noite com luz de verdade:** amanhecer rosado, meio-dia neutro, entardecer dourado, noite azulada; janelas acendem, postes e lampiões iluminam o chão ao redor, antenas piscam em vermelho.
- **Efeitos:** construções "brotam" do chão com poeira; demolição solta poeira e entulho; chaminés soltam fumaça quando a construção está funcionando; moedas saltam de quem vendeu no fim do dia; bandeiras tremulam, a fonte jorra, o catavento gira, árvores balançam; bandos de pássaros cruzam o céu com sombra no chão; nuvens (com sombra) aparecem ao afastar a câmera; chuva e tom acinzentado no evento de chuva, tom quente na estiagem; confete ao cumprir missão ou subir de nível.
- Ao fim de cada dia, números flutuantes mostram a produção (+16 🥬) e o lucro sobre o Centro.

### 7.10 Modos
- **Desafio:** dinheiro, níveis, eventos e missões com recompensas.
- **Criativo:** dinheiro infinito, tudo liberado, sem eventos: para montar o layout dos sonhos.

## 8. Catálogo de conteúdo

### Produtos

| Produto | Preço base | Alimento? |
|---|---|---|
| 🥬 Hortaliças | R$ 5 | sim |
| 🍎 Frutas | R$ 7 | sim |
| 🥚 Ovos | R$ 4 | sim |
| 🍯 Mel | R$ 18 | sim |
| 🍞 Pães | R$ 4 | sim |
| 🍱 Marmitas | R$ 24 | sim |
| 🍓 Doces e geleias | R$ 26 | sim |
| 🌱 Mudas | R$ 6 | não |
| ♻️ Recicláveis | R$ 2 | não |
| 📦 Fardos reciclados | R$ 16 | não |
| 👕 Roupas | R$ 40 | não |
| 🏺 Artesanato | R$ 30 | não |
| 🛋️ Móveis | R$ 90 | não |

### Comunidade

| Construção | Custo | Manut./dia | Vagas | Produz/dia | Consome/dia | Outros efeitos | Nível |
|---|---|---|---|---|---|---|---|
| 🏛️ Centro Comunitário | R$ 0 | R$ 0 | 1 | — | — | vende 15/dia ×0.9; +300 estoque | início |
| 🏠 Casa | R$ 300 | R$ 1 | 0 | — | — | 4 moradores | 1 |
| 🏘️ Sobrado | R$ 800 | R$ 3 | 0 | — | — | 10 moradores | 3 |
| 💧 Poço Artesiano | R$ 250 | R$ 1 | 0 | — | — | +20% de produção para hortas, pomares, viveiros e estufas num raio de 3. | 1 |
| 🧸 Creche Comunitária | R$ 900 | R$ 8 | 2 | — | — | Mães e pais podem trabalhar: +6% de pessoas disponíveis para o trabalho (até 4 creches). Bem-estar +6 no raio. | 2 |
| 🎓 Escola de Capacitação | R$ 1.500 | R$ 14 | 3 | — | — | Cursos profissionalizantes: +6% de produtividade em todo o projeto (até 5 escolas). Bem-estar +5 no raio. | 3 |
| 🏥 Posto de Saúde | R$ 1.400 | R$ 14 | 3 | — | — | Cuida da comunidade: bem-estar +12 para as casas no raio de 7. | 4 |
| ☀️ Painéis Solares | R$ 900 | R$ 0 | 0 | — | — | Energia limpa e barata: +10% de produção para construções num raio de 3. | 4 |
| 🏦 Banco Comunitário | R$ 2.000 | R$ 10 | 3 | — | — | Moeda social e crédito local: +5% no preço de todas as vendas (até 2 bancos). | 5 |

### Produção

| Construção | Custo | Manut./dia | Vagas | Produz/dia | Consome/dia | Outros efeitos | Nível |
|---|---|---|---|---|---|---|---|
| 🥬 Horta Comunitária | R$ 200 | R$ 3 | 2 | 16 🥬 Hortaliças | — | +20% perto de água/poço; ramo: agro | 1 |
| 🐔 Galinheiro | R$ 350 | R$ 5 | 2 | 20 🥚 Ovos | — | ramo: agro | 1 |
| 🍎 Pomar | R$ 450 | R$ 5 | 2 | 14 🍎 Frutas | — | +20% perto de água/poço; ramo: agro | 2 |
| 🌱 Viveiro de Mudas | R$ 400 | R$ 4 | 2 | 15 🌱 Mudas | — | +20% perto de água/poço; ramo: agro | 2 |
| 🐝 Apiário | R$ 500 | R$ 3 | 1 | 3 🍯 Mel | — | até +100% com flores/árvores; ramo: agro | 3 |
| 🌿 Estufa | R$ 1.200 | R$ 12 | 3 | 40 🥬 Hortaliças | — | +20% perto de água/poço; ramo: agro | 4 |
| ♻️ Ponto de Coleta | R$ 300 | R$ 3 | 2 | 40 ♻️ Recicláveis | — | +5% por casa no raio 5 (máx. +50%); ramo: recicla | 1 |
| 📦 Galpão de Triagem | R$ 900 | R$ 8 | 3 | 12 📦 Fardos reciclados | 36 ♻️ Recicláveis | ramo: recicla | 2 |
| 🍞 Padaria Comunitária | R$ 700 | R$ 12 | 3 | 45 🍞 Pães | 6 🥚 Ovos | ramo: cozinha | 2 |
| 🍲 Cozinha Comunitária | R$ 800 | R$ 8 | 3 | 9 🍱 Marmitas | 10 🥬 Hortaliças + 6 🥚 Ovos | ramo: cozinha | 2 |
| 🍓 Fábrica de Doces | R$ 900 | R$ 6 | 2 | 6 🍓 Doces e geleias | 10 🍎 Frutas | ramo: cozinha | 3 |
| 🏺 Ateliê de Artesanato | R$ 600 | R$ 6 | 2 | 4 🏺 Artesanato | — | ramo: arte | 2 |
| 🧵 Ateliê de Costura | R$ 1.000 | R$ 20 | 4 | 7 👕 Roupas | — | ramo: moda | 3 |
| 🔨 Marcenaria | R$ 1.500 | R$ 20 | 4 | 4 🛋️ Móveis | — | ramo: arte | 5 |
| 💻 Centro de Tecnologia | R$ 2.500 | R$ 30 | 5 | — | — | renda direta R$ 450; ramo: tech | 6 |
| 🏨 Pousada Ecológica | R$ 1.800 | R$ 15 | 3 | — | — | renda direta R$ 100 + até R$ 300 pela beleza; ramo: arte | 4 |

### Comércio

| Construção | Custo | Manut./dia | Vagas | Produz/dia | Consome/dia | Outros efeitos | Nível |
|---|---|---|---|---|---|---|---|
| ⛺ Feira Livre | R$ 500 | R$ 5 | 1 | — | — | vende 60/dia (só alimentos) ×1.1 | 1 |
| 🏪 Loja Solidária | R$ 900 | R$ 8 | 2 | — | — | vende 45/dia ×1 | 2 |
| 🏬 Armazém | R$ 700 | R$ 5 | 1 | — | — | +400 estoque | 2 |
| 🛵 Central de Entregas | R$ 1.600 | R$ 12 | 3 | — | — | vende 90/dia ×0.95 | 5 |

### Vias

| Ferramenta | Custo por ladrilho | Função |
|---|---|---|
| 🟫 Estrada de Terra | R$ 8 | Arraste para traçar. Sobre a água vira ponte (R$ 60). |
| ⬜ Rua de Pedra | R$ 20 | Calçamento bonito que valoriza o bairro. Arraste para traçar. |
| 🌉 Ponte | R$ 60 | Passagem sobre a água. |

### Decoração

| Item | Custo | Beleza | Raio | Nível |
|---|---|---|---|---|
| 🌳 Árvore | R$ 20 | +3 | 2 | 1 |
| 🌲 Pinheiro | R$ 20 | +3 | 2 | 1 |
| 🌴 Palmeira | R$ 30 | +3 | 2 | 1 |
| 🌷 Canteiro de Flores | R$ 15 | +2 | 1 | 1 |
| 🌿 Cerca Viva | R$ 10 | +1 | 1 | 1 |
| 💺 Banco | R$ 30 | +2 | 2 | 1 |
| 💡 Poste de Luz | R$ 40 | +2 | 2 | 1 |
| 🏞️ Praça | R$ 150 | +5 | 3 | 1 |
| ⛲ Fonte | R$ 250 | +6 | 3 | 2 |
| 🎠 Parquinho | R$ 300 | +7 | 3 | 2 |
| 🎨 Mural de Arte | R$ 200 | +6 | 3 | 3 |
| 🗿 Monumento | R$ 500 | +9 | 4 | 4 |
| 🌸 Ipê Florido | R$ 35 | +4 | 2 | 1 |
| 🌀 Cata-vento | R$ 180 | +4 | 2 | 2 |
| 🎶 Coreto | R$ 400 | +8 | 3 | 3 |

### Terreno

| Ferramenta | Custo por ladrilho | Função |
|---|---|---|
| 🟩 Grama | R$ 2 | Pinte o chão com grama. |
| 🍀 Campo | R$ 2 | Grama mais escura. |
| 🟤 Terra | R$ 2 | Chão de terra. |
| 🟨 Areia | R$ 2 | Chão de areia. |
| ⬛ Pedregulho | R$ 2 | Chão de pedra. |
| 🌊 Cavar Lago | R$ 30 | Cria água em terreno livre. Água deixa o bairro mais bonito e ajuda as hortas. |
| 🏝️ Aterrar | R$ 30 | Transforma água em terra firme. |
| ✂️ Limpar Mato | R$ 5 | Remove árvores, arbustos e pedras naturais. |

### Ramos do projeto

| Ramo | Começa liberado | Descrição |
|---|---|---|
| 🥬 Agricultura Familiar | Horta Comunitária, Galinheiro, Pomar | Hortas, pomares, galinheiros e apiários. Comida boa e renda no campo. |
| ♻️ Cooperativa de Reciclagem | Ponto de Coleta, Galpão de Triagem | Coleta, triagem e venda de recicláveis. Renda e cidade limpa. |
| 🍞 Cozinha e Panificação | Padaria Comunitária, Cozinha Comunitária, Galinheiro, Horta Comunitária | Padaria, marmitas e doces caseiros com ingredientes locais. |
| 🧵 Costura e Moda | Ateliê de Costura | Ateliês de costura e confecção de roupas. |
| 🏺 Artesanato e Turismo | Ateliê de Artesanato, Pousada Ecológica | Arte local, ateliês e turismo comunitário. |
| 💻 Tecnologia e Serviços | Centro de Tecnologia | Inclusão digital, serviços e programação. |
| ✨ Personalizado | — (+10% em tudo) | Invente o seu ramo! Sem foco único: +10% de produção em tudo. |

### Níveis de impacto

| Nível | Nome | Pontos necessários |
|---|---|---|
| 1 | Semente | 0 |
| 2 | Broto | 100 |
| 3 | Muda | 320 |
| 4 | Raiz Forte | 800 |
| 5 | Árvore Jovem | 1600 |
| 6 | Referência | 3000 |
| 7 | Rede Solidária | 5000 |
| 8 | Polo Regional | 8000 |
| 9 | Inspiração | 12000 |
| 10 | Lenda | 18000 |

### Missões (tutorial guiado, em sequência)

| # | Missão | Objetivo | Recompensa |
|---|---|---|---|
| 1 | Funde seu projeto | Construa o Centro Comunitário. | — |
| 2 | Abra caminhos | Faça 6 trechos de estrada ligados ao Centro. | R$ 150 |
| 3 | Lar doce lar | Construa 3 casas ao lado das estradas. | R$ 300 |
| 4 | Mãos à obra | Construa 2 unidades de produção ligadas à estrada. | R$ 300 |
| 5 | Hora de vender | Construa uma Feira Livre ou Loja Solidária. | R$ 400 |
| 6 | Primeiros empregos | Tenha 6 pessoas trabalhando. | R$ 500 |
| 7 | Bairro bonito | Coloque 10 decorações. | R$ 300 |
| 8 | No azul | Feche um dia com lucro de R$ 100. | R$ 600 |
| 9 | Cadeia produtiva | Construa uma unidade de beneficiamento. | R$ 800 |
| 10 | Gerando oportunidades | Tenha 15 pessoas trabalhando. | R$ 1.000 |
| 11 | Comunidade feliz | Alcance 70% de bem-estar. | R$ 800 |
| 12 | Capacitação | Construa uma Escola de Capacitação. | R$ 1.000 |
| 13 | Negócio sustentável | Fature R$ 600 em um único dia. | R$ 1.500 |
| 14 | Projeto que transforma | Tenha 30 pessoas trabalhando. | R$ 2.000 |
| 15 | Renda que circula | Distribua R$ 10.000 em salários no total. | R$ 2.500 |
| 16 | Referência regional | Alcance o nível 6 de impacto. | R$ 3.000 |
| 17 | Polo de trabalho e renda | Tenha 60 pessoas trabalhando. | R$ 5.000 |
| 18 | Lenda da economia solidária | Alcance o nível 10. | R$ 10.000 |

### Eventos aleatórios (modo Desafio, a cada 10–18 dias)

- 📜 Edital aprovado! O projeto recebeu R$ 1.500 de fomento.
- 🎁 Doação de ferramentas e equipamentos: +R$ 600.
- 🌧️ Chuva forte: produção agrícola -40% por 2 dias.
- ☀️ Estiagem: produção agrícola -25% por 3 dias.
- 🎪 Feira regional na cidade: vendas +50% por 3 dias!
- 📚 Curso gratuito de gestão: +15% de produtividade por 5 dias.
- 📸 Reportagem sobre o projeto! Bem-estar +8 por 5 dias.
- 🔧 Um equipamento quebrou. Conserto: -R$ 300.

## 9. Interface e controles

- **Barra superior:** símbolo e nome do projeto, nível, caixa (∞ no Criativo), empregados/vagas (fica laranja se faltar gente), população, bem-estar com carinha, dia e hora, velocidades e menu. Uma barra fina dourada mostra o progresso do nível.
- **Missão atual** no canto superior esquerdo; **minimapa** isométrico tocável no canto direito com o retângulo da câmera; botões ＋/－.
- **Barra inferior:** 👆 Selecionar · 🏘️ Comunidade · 🌾 Produção · 🛒 Comércio · 🛣️ Vias · 🌳 Decorar · ⛰️ Terreno · 🧨 Demolir · ↩️ Desfazer · 🚶 Passear. Categorias abrem uma **paleta horizontal** com **miniatura renderizada** da construção (ou do bloco de chão/via), nome, custo ou cadeado com o nível (miniatura em tons de cinza quando bloqueada). As miniaturas são geradas aos poucos em segundo plano.
- **Cartão da construção** com miniatura do nível atual.
- **Dica da ferramenta** acima da paleta: nome, como usar, números principais e custo total da estrada sendo traçada.
- **Gestos:** um dedo arrasta o mapa (no modo Selecionar ou com ferramentas de toque), dois dedos movem e dão zoom (pinça), toque constrói ou seleciona. Mouse: botão direito arrasta, roda dá zoom. Teclado (para testes): setas/WASD, +/−, Esc, Ctrl+Z.
- **Botão Voltar do Android:** fecha a camada de cima (diálogo → painel → passeio → cartão → ferramenta); por último pergunta se quer sair (salvando antes).
- Layout responsivo para **retrato e paisagem**, respeitando entalhes (safe area). Alvos de toque de pelo menos 40 px.
- Avisos curtos (toasts) para missões, níveis, eventos e erros; diálogo de confirmação para demolir e apagar.

## 10. Direção de arte e áudio

- **Isométrico 2:1** (ladrilho 64 × 32), estilo ilustrado colorido e aconchegante, com luz vindo do alto à esquerda e **sombras projetadas** suaves.
- **Toda a arte é procedural** (desenhada em canvas por código e guardada em cache), sem arquivos de imagem:
  - **Terreno contínuo** (sem grade aparente): texturas sem emenda para grama, campo, grama seca, areia, terra e pedregulho; as transições entre tipos são **bordas orgânicas** (cantos côncavos e convexos suavizados, prioridade de quem "derrama" sobre quem); variação de cor em grande escala; tufos, flores, cogumelos e pedrinhas espalhados.
  - **Água em camadas animadas** (manchas, ondulações em dois sentidos, brilhos), **cor por profundidade** (mais clara na margem, mais escura no meio), espuma no litoral.
  - **Estradas** com cantos arredondados que se ligam sozinhas: terra com trilhas de pneu, rua de pedra (paralelepípedos) com meio-fio, ponte de madeira sobre a água.
  - **A ilha no mar:** o mapa é uma ilha com **falésia** em camadas de terra e rocha (grama caindo na borda, degradê úmido perto da água), **espuma batendo na base**, cachoeiras onde rios encontram a borda, faixa de água rasa turquesa e mar com gradiente de profundidade e brilhos.
  - **Construções detalhadas** com volumes, telhados (duas águas, quatro águas, pirâmide, laje), telhas, janelas com caixilho, portas, toldos listrados, placas, chaminés, caixas d'água, antenas, ar-condicionado, painéis solares inclinados, cercas, vasos e arbustos; variações de cor nas casas; níveis 2 e 3 ganham andares e detalhes.
  - **Natureza brasileira:** árvores frondosas, araucárias, coqueiros, **ipês amarelos e roxos**, arbustos, rochas, flores.
  - Contorno suave em cada sprite e **sombras projetadas calculadas a partir dos volumes** (gravadas no chão do terreno).
- **Luz:** cor ambiente por hora do dia (mapa de luz multiplicativo), janelas acesas à noite (camada emissiva por sprite), brilho (bloom) de postes e lampiões, faróis dos veículos, vinheta suave nas bordas da tela.
- Telhados das construções do projeto na **cor escolhida** pelo jogador; o Centro tem bandeira tremulando e o símbolo do projeto; placas redondas com o emoji do que cada construção produz (podem ser ocultadas).
- Paleta da interface: verde-escuro (#14261F), verde de destaque (#3CCF7A), dourado (#FFC94A).
- **Trilha sonora original** (arquivos OGG Vorbis em `assets/www/audio/`, compostos e sintetizados por código em `tools/audio/`, sem samples de terceiros), com loops sem emenda e volume normalizado (LUFS):
  - **Tema** (tela inicial): violão, cordas, flauta e vibrafone, Sol maior, com modulação no clímax;
  - **Manhã na Horta** (dia): bossa nova com violão na batida, contrabaixo, vassourinha, flauta e vibrafone;
  - **Dia de Feira** (dia, alternando com a manhã e durante o evento de feira): baião/forró pé-de-serra com sanfona, zabumba e triângulo;
  - **Noite na Vila** (noite): pads, violão dedilhado e melodia suave.
  - **Ambiências** em camada separada: passarinhos brasileiros (bem-te-vi, sabiá, tico-tico, rolinha) de dia; grilos, sapos e coruja à noite; chuva com trovões no evento de chuva; **ondas do mar** com volume proporcional ao quanto de oceano aparece na tela.
  - Troca suave (crossfade) entre faixas conforme a hora do dia, o clima e o modo passeio; pausa quando o app vai para segundo plano.
- **Efeitos sonoros sintetizados** (Web Audio): clique, construir, erro, moedas, missão, nível, evento, demolir. Sem os arquivos de música, cai para uma música pentatônica sintetizada. Vibração curta ao construir (Android).
- **Emojis embutidos:** fonte Noto Color Emoji (OFL) em `assets/www/fonts/`, aplicada só aos caracteres de emoji (`unicode-range`) na interface e no canvas, para os ícones ficarem iguais em qualquer Android, inclusive versões antigas.

## 11. Requisitos técnicos

- **Plataforma:** Android 5.0+ (minSdk 21), targetSdk 34, APK assinado (esquemas v1, v2 e v3), ~26 MB (≈15 MB de trilha sonora + 10,8 MB de fonte de emojis).
- **Compatibilidade com WebView antigo** (Android 5–7 sem atualização): toque por eventos de ponteiro com reserva para eventos de toque, polyfill de `TypedArray.fill`, CSS sem `inset` e com áreas seguras (`env()`) só via `@supports`, texturas inclinadas sem depender de `CanvasPattern.setTransform`.
- **Arquitetura:** app nativo mínimo em Java (`MainActivity`) com **WebView em tela cheia imersiva** carregando `file:///android_asset/www/index.html`; o jogo é **HTML5 Canvas 2D + JavaScript puro** (ES5, sem frameworks, sem CDN, sem internet).
- **Ponte nativa (`AndroidBridge`):** `save/load/remove` em arquivos privados do app (gravação atômica), `vibrate`, `share` (compartilhar resumo do projeto) e `exitApp`. No navegador, cai para `localStorage`.
- **Ciclo de vida:** salva e pausa a trilha ao pausar o app (`onAppPause`), retoma a trilha ao voltar (`onAppResume`), salva a cada 2 dias de jogo e alguns segundos após mudanças no mapa; tela sempre ligada durante o jogo; sem permissões perigosas (apenas `VIBRATE`).
- **Desempenho:** o terreno é desenhado em **blocos de 8 × 8 ladrilhos guardados em cache em várias resoluções** (refinados aos poucos dentro de um orçamento de milissegundos por quadro, com descarte LRU por memória) e redesenhados só quando um ladrilho próximo muda; sprites e quadros de animação em cache; desenha só o que está na tela; resolução limitada a 2× e **resolução dinâmica** (reduz sozinha se o FPS cair abaixo de ~34); opção de gráficos leves (menos camadas de água, sem pássaros/nuvens/chuva/brilhos, menos moradores, mapa de luz em resolução menor).
- **Build sem Android Studio:** `build-apk.sh` usa `aapt2`, `javac`, `d8/dx`, `zipalign` e `apksigner` (pacotes do Ubuntu/Debian) e gera `dist/MundoRenda.apk`.

## 12. Arquitetura do código

```
android/
  AndroidManifest.xml
  java/br/org/mundorenda/MainActivity.java   ← WebView + ponte nativa
  res/                                        ← ícones (legado + adaptativo), tema, cores, nome
  assets/www/
    index.html, css/style.css
    js/util.js      ← aleatório com semente, ruído fractal, formatação em R$
    js/data.js      ← TODO o conteúdo: produtos, construções, ramos, níveis, missões, eventos, frases
    js/world.js     ← mapa, geração procedural, regras de construção, desfazer, conexões, mapas de efeito
    js/sim.js       ← simulação diária (produção, beneficiamento, vendas, salários, bem-estar, níveis)
    js/gfx/tex.js     ← texturas procedurais sem emenda (chão, estradas, água, falésia) e detalhes do chão
    js/sprites.js     ← construções, natureza e pontes procedurais com volumes, sombras, luzes, janelas e animações; miniaturas
    js/gfx/terrain.js ← terreno contínuo em blocos com cache multirresolução (bordas orgânicas, água, estradas, sombras)
    js/gfx/light.js   ← cor do céu por hora, mapa de luz noturno, janelas acesas, brilho e vinheta
    js/gfx/fx.js      ← partículas, construção brotando, fumaça, moedas, pássaros, nuvens, chuva, confete
    js/gfx/people.js  ← moradores animados e veículos (bicicleta, moto de entrega, caminhonete)
    js/render.js      ← câmera, mar e ilha, desenho por profundidade, camadas de efeitos e luz, minimapa, resolução dinâmica
    js/input.js     ← toque/mouse: tocar, arrastar estradas, pincéis, pinça
    js/ui.js        ← HUD, paleta, cartões, painéis, assistente, diálogos, avisos, joystick
    js/audio.js     ← efeitos sonoros sintetizados (e música de reserva)
    js/music.js     ← trilha sonora e ambiências (canais com crossfade por hora do dia, clima e mar)
    audio/          ← tema, manha, feira, noite + amb_dia, amb_noite, amb_chuva, amb_mar (OGG)
    fonts/          ← NotoColorEmoji.ttf + OFL.txt
    js/storage.js   ← salvar/carregar (AndroidBridge ou localStorage)
    js/main.js      ← estado do jogo, laço principal, passeio, salvar/carregar, botão voltar
tools/gen_icons.py  ← gera os ícones
tools/audio/        ← synth.py (biblioteca de síntese: violão Karplus-Strong, baixo, sanfona, flauta, vibrafone,
                       percussão brasileira, natureza, reverb, loop sem emenda, LUFS, OGG) + um script por faixa
build-apk.sh        ← gera o APK
```

Regras: todo o balanceamento fica em `data.js` (editar números não exige mexer na lógica); toda alteração do mapa passa por `World.apply`, que valida, cobra e registra no desfazer.

## 13. Salvamento

- Até 12 projetos salvos, com índice (nome, símbolo, cor, dia, caixa, nível, modo).
- Formato JSON: estado do jogo + terreno compactado em texto (1 caractere por ladrilho) + lista de objetos `[ladrilho, item, nível]` + posição da câmera.
- Configurações separadas: efeitos sonoros, trilha sonora, sons da natureza, vibração, dia/noite, alertas, placas das construções, clima (nuvens, pássaros e chuva), grade, qualidade.

## 14. Critérios de aceite

1. O APK instala e abre offline num Android 5+; mostra a tela inicial com a vila animada em menos de 2 s.
2. É possível criar um projeto com nome, símbolo, cor, ramo (inclusive personalizado), paisagem, modo e semente.
3. O Centro Comunitário é fundado com um toque; estradas são traçadas arrastando, viram ponte na água e mostram o custo.
4. Construções sem estrada até o Centro não funcionam e mostram alerta; ao ligar a estrada, passam a funcionar.
5. Casas trazem moradores; vagas são ocupadas; produção, beneficiamento e vendas acontecem a cada dia; o caixa muda conforme a fórmula.
6. Missões avançam em sequência com recompensa; níveis liberam itens; eventos aparecem no Desafio.
7. Melhorar, mover, demolir (com reembolso) e desfazer funcionam e mantêm o dinheiro coerente.
8. Pintar terreno, cavar lago, aterrar e limpar mato funcionam.
9. O modo Passeio anda com joystick, respeita obstáculos e mostra informações das construções e falas dos moradores.
10. O progresso é salvo automaticamente e recarregado de forma idêntica; o botão Voltar do Android se comporta como descrito.
11. A interface funciona em retrato e paisagem, sem textos cortados nos tamanhos comuns de celular.
12. Nenhum erro de JavaScript no console durante uma sessão completa.

## 15. Entregáveis e formato da resposta

1. Código-fonte completo na estrutura acima, comentado em português.
2. Script de build e o **APK assinado** pronto para instalar.
3. README com instalação no celular, como jogar e como recompilar.
4. Ao responder, mostre primeiro um resumo do que foi feito, depois os arquivos completos (sem "..."), e por fim como testar.

## 16. Roteiro de expansão (fora da v1)

- Construções maiores que 1 ladrilho e rotação.
- Rede de cooperativas vizinhas (comércio entre projetos), feiras sazonais e pedidos especiais.
- Moeda social própria e assembleias (votações que mudam regras do projeto).
- Personagens com nome e histórias de vida que evoluem com o emprego.
- Estações do ano, clima visível (chuva) e calendário agrícola.
- Conquistas, relatório de impacto em PDF e modo professor(a) com metas personalizadas.
- Multijogador local (vários projetos no mesmo mundo) e compartilhamento de mapas por código.

```text
==================== FIM DO PROMPT MESTRE ====================
```

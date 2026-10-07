# 🌱 Mundo Renda

Jogo para **Android** em que você cria **o seu projeto de geração de trabalho e renda** e o constrói, do seu jeito, num **mundo aberto** isométrico. Funciona 100% offline.

- 📱 **APK pronto:** [`dist/MundoRenda.apk`](dist/MundoRenda.apk)
- 🧠 **Prompt mestre** (especificação completa para recriar ou expandir com IA): [`PROMPT_MESTRE.md`](PROMPT_MESTRE.md)

## O que dá para fazer

- Dar **nome, símbolo e cor** ao projeto e escolher o **ramo**: agricultura familiar, reciclagem, cozinha e panificação, costura e moda, artesanato e turismo, tecnologia, ou um ramo **personalizado** com o nome que quiser.
- Gerar um **mundo aberto** (96 × 96) por semente: vale com rio, litoral, lagos ou cerrado.
- **Construir livremente**: casas, hortas, galinheiros, pomares, estufas, apiários, coleta e triagem de recicláveis, padaria, cozinha comunitária, fábrica de doces, ateliês, marcenaria, centro de tecnologia, pousada, feiras, lojas, armazéns, creche, escola, posto de saúde, banco comunitário, painéis solares e poços.
- **Desenhar o layout**: estradas e pontes arrastando o dedo, praças, fontes, parquinhos, murais, árvores, flores, postes; pintar o chão, cavar lagos e aterrar.
- **Melhorar, mover, demolir e desfazer** qualquer coisa.
- Acompanhar **empregos, renda distribuída, lucro e bem-estar**, cumprir **18 missões**, subir **10 níveis de impacto**, enfrentar **eventos** e usar **microcrédito**.
- **Passear** pela comunidade com um personagem (joystick) e conversar com os moradores.
- Modo **Desafio** (dinheiro e progresso) ou **Criativo** (tudo liberado e dinheiro infinito).

## Gráficos

Toda a arte é desenhada por código (sem arquivos de imagem): terreno contínuo com texturas e bordas orgânicas, água animada com profundidade, a ilha cercada de mar com falésia e espuma, construções detalhadas com sombras projetadas, árvores brasileiras (ipês, araucárias, coqueiros), moradores animados e veículos nas ruas, ciclo de dia e noite com janelas e postes acesos, fumaça, poeira, pássaros, nuvens, chuva e confete. Em celulares mais simples, desligue **Gráficos em alta qualidade** no menu; a resolução também se ajusta sozinha.

## Instalar no celular

1. Baixe o arquivo `dist/MundoRenda.apk` no celular (pelo GitHub: abra o arquivo e toque em *Download raw file* / *Baixar*).
2. Toque no arquivo baixado. Se o Android pedir, permita **"Instalar apps desconhecidos"** para o navegador ou o gerenciador de arquivos.
3. Abra **Mundo Renda**.

> Requer Android 5.0 ou mais novo (recomendado Android 9+ para todos os emojis aparecerem). O APK é assinado com uma **chave de testes** (`keystore/mundorenda-debug.jks`, senha `android`): ótima para instalar e atualizar o jogo, mas **não use essa chave para publicar na Play Store** — gere a sua própria (veja abaixo).

## Como jogar (resumo)

1. Toque num lugar livre para fundar o **Centro Comunitário**.
2. Em 🛣️ **Vias**, arraste o dedo a partir do Centro para abrir estradas.
3. Construa **casas** ao lado das estradas (moradores = trabalhadores).
4. Construa **produção** (hortas, galinheiros…) e **pontos de venda** (feira, loja).
5. Acompanhe o painel do projeto (toque no nome do projeto no topo) e siga as **missões**.

Dicas: tudo precisa estar ao lado de uma estrada ligada ao Centro; beneficiar produtos (marmitas, doces, fardos) rende mais; decoração perto das casas aumenta o bem-estar; ↩️ desfaz e devolve o dinheiro.

## Recompilar o APK

Não precisa de Android Studio. Em Ubuntu/Debian:

```bash
sudo apt-get install -y aapt apksigner zipalign dalvik-exchange android-sdk-platform-23 default-jdk zip
./build-apk.sh                      # gera dist/MundoRenda.apk
VERSION_CODE=2 VERSION_NAME=1.1.0 ./build-apk.sh   # nova versão (para atualizar por cima)
```

Para publicar, crie a sua chave e use-a:

```bash
keytool -genkeypair -keystore minha-chave.jks -alias minhachave -keyalg RSA -keysize 2048 -validity 10000
KEYSTORE=minha-chave.jks KEY_ALIAS=minhachave KS_PASS='sua-senha' ./build-apk.sh
```

Para testar no computador, sirva a pasta do jogo e abra no navegador (o salvamento usa `localStorage`):

```bash
cd android/assets/www && python3 -m http.server 8000   # abra http://localhost:8000
```

## Estrutura

```
PROMPT_MESTRE.md          especificação completa do jogo (prompt mestre)
build-apk.sh              build do APK (aapt2 + javac + dx + zipalign + apksigner)
tools/gen_icons.py        gera os ícones do app
keystore/                 chave de testes
dist/MundoRenda.apk       APK pronto
android/
  AndroidManifest.xml
  java/…/MainActivity.java   WebView em tela cheia + ponte nativa (salvar, vibrar, compartilhar, sair)
  res/                       ícones, tema e nome
  assets/www/                o jogo (HTML5 Canvas + JavaScript puro, sem dependências)
    js/data.js               todo o conteúdo e balanceamento (fácil de editar)
    js/world.js              mundo aberto, geração procedural e regras de construção
    js/sim.js                economia e simulação social
    js/sprites.js            construções e natureza procedurais (volumes, sombras, luzes, miniaturas)
    js/gfx/                  texturas, terreno em blocos, luz, efeitos, moradores e veículos
    js/render.js             câmera, mar e ilha, ordem de desenho e camadas
    js/input.js, ui.js       controles e interface
    js/main.js               estado, laço principal, salvar/carregar, modo passeio
```

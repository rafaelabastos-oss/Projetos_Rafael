/* Mundo Renda - catálogo de conteúdo (produtos, construções, ramos, missões, eventos) */
'use strict';

var DATA = (function () {
  var WAGE = 18;            // salário por trabalhador por dia (R$)
  var DAY_SEC = 20;         // segundos reais por dia na velocidade 1x
  var START_MONEY = 6000;

  var GOODS = {
    hortalicas: { name: 'Hortaliças', icon: '🥬', price: 5, food: true },
    frutas: { name: 'Frutas', icon: '🍎', price: 7, food: true },
    ovos: { name: 'Ovos', icon: '🥚', price: 4, food: true },
    mel: { name: 'Mel', icon: '🍯', price: 18, food: true },
    paes: { name: 'Pães', icon: '🍞', price: 4, food: true },
    marmitas: { name: 'Marmitas', icon: '🍱', price: 24, food: true },
    doces: { name: 'Doces e geleias', icon: '🍓', price: 26, food: true },
    mudas: { name: 'Mudas', icon: '🌱', price: 6, food: false },
    reciclaveis: { name: 'Recicláveis', icon: '♻️', price: 2, food: false },
    fardos: { name: 'Fardos reciclados', icon: '📦', price: 16, food: false },
    roupas: { name: 'Roupas', icon: '👕', price: 40, food: false },
    artesanato: { name: 'Artesanato', icon: '🏺', price: 30, food: false },
    moveis: { name: 'Móveis', icon: '🛋️', price: 90, food: false }
  };

  var TERRAIN = [
    { id: 'grama', name: 'Grama', color: '#7cc65a' },
    { id: 'campo', name: 'Campo', color: '#62b04c' },
    { id: 'seca', name: 'Grama seca', color: '#b9c463' },
    { id: 'areia', name: 'Areia', color: '#ead79a' },
    { id: 'terra', name: 'Terra', color: '#b98a5b' },
    { id: 'pedra', name: 'Pedregulho', color: '#9ea4a6' },
    { id: 'agua', name: 'Água', color: '#3f9fd8' }
  ];
  var T = { GRAMA: 0, CAMPO: 1, SECA: 2, AREIA: 3, TERRA: 4, PEDRA: 5, AGUA: 6 };

  var CATS = [
    { id: 'info', icon: '👆', name: 'Selecionar' },
    { id: 'comunidade', icon: '🏘️', name: 'Comunidade' },
    { id: 'producao', icon: '🌾', name: 'Produção' },
    { id: 'comercio', icon: '🛒', name: 'Comércio' },
    { id: 'vias', icon: '🛣️', name: 'Vias' },
    { id: 'decor', icon: '🌳', name: 'Decorar' },
    { id: 'terreno', icon: '⛰️', name: 'Terreno' },
    { id: 'demolir', icon: '🧨', name: 'Demolir' },
    { id: 'desfazer', icon: '↩️', name: 'Desfazer' },
    { id: 'passear', icon: '🚶', name: 'Passear' }
  ];

  // kind: hq, house, producer, processor, service, shop, storage, infra, road, decor, natural, terrain
  var ITEMS = [
    // ---------- Comunidade ----------
    { id: 'hq', name: 'Centro Comunitário', icon: '🏛️', cat: 'comunidade', kind: 'hq', cost: 0, upkeep: 0, jobs: 1,
      store: 300, sell: { cap: 15, mult: 0.9 }, unique: true, lvl: 99,
      desc: 'Sede do seu projeto. Guarda o estoque e vende um pouco de tudo. Todas as construções precisam estar ligadas a ele por estradas.',
      draw: { p: 'hq' } },
    { id: 'casa', name: 'Casa', icon: '🏠', cat: 'comunidade', kind: 'house', cost: 300, upkeep: 1, res: 4, lvl: 1,
      desc: 'Moradia para 4 pessoas da comunidade. Quem mora aqui pode trabalhar no projeto.', draw: { p: 'house' } },
    { id: 'sobrado', name: 'Sobrado', icon: '🏘️', cat: 'comunidade', kind: 'house', cost: 800, upkeep: 3, res: 10, lvl: 3,
      desc: 'Moradia maior, para 10 pessoas.', draw: { p: 'sobrado' } },
    { id: 'poco', name: 'Poço Artesiano', icon: '💧', cat: 'comunidade', kind: 'infra', cost: 250, upkeep: 1, lvl: 1,
      eff: { type: 'agua', r: 3, v: 0.2 }, desc: '+20% de produção para hortas, pomares, viveiros e estufas num raio de 3.',
      draw: { p: 'poco' } },
    { id: 'creche', name: 'Creche Comunitária', icon: '🧸', cat: 'comunidade', kind: 'service', cost: 900, upkeep: 8, jobs: 2, lvl: 2,
      eff: { type: 'creche', r: 6, v: 6 }, desc: 'Mães e pais podem trabalhar: +6% de pessoas disponíveis para o trabalho (até 4 creches). Bem-estar +6 no raio.',
      draw: { p: 'box', h: 16, wall: '#fbe3a1', roof: 'gable', roofC: '#ef7d57', win: 2 } },
    { id: 'escola', name: 'Escola de Capacitação', icon: '🎓', cat: 'comunidade', kind: 'service', cost: 1500, upkeep: 14, jobs: 3, lvl: 3,
      eff: { type: 'escola', r: 7, v: 5 }, desc: 'Cursos profissionalizantes: +6% de produtividade em todo o projeto (até 5 escolas). Bem-estar +5 no raio.',
      draw: { p: 'box', h: 24, wall: '#e9eef5', roof: 'flat', roofC: '#5b7bd5', win: 3 } },
    { id: 'saude', name: 'Posto de Saúde', icon: '🏥', cat: 'comunidade', kind: 'service', cost: 1400, upkeep: 14, jobs: 3, lvl: 4,
      eff: { type: 'saude', r: 7, v: 12 }, desc: 'Cuida da comunidade: bem-estar +12 para as casas no raio de 7.',
      draw: { p: 'box', h: 20, wall: '#ffffff', roof: 'flat', roofC: '#e05555', win: 3 } },
    { id: 'solar', name: 'Painéis Solares', icon: '☀️', cat: 'comunidade', kind: 'infra', cost: 900, upkeep: 0, lvl: 4,
      eff: { type: 'solar', r: 3, v: 0.1 }, desc: 'Energia limpa e barata: +10% de produção para construções num raio de 3.',
      draw: { p: 'solar' } },
    { id: 'banco', name: 'Banco Comunitário', icon: '🏦', cat: 'comunidade', kind: 'service', cost: 2000, upkeep: 10, jobs: 3, lvl: 5,
      eff: { type: 'banco', r: 0, v: 0.05 }, desc: 'Moeda social e crédito local: +5% no preço de todas as vendas (até 2 bancos).',
      draw: { p: 'box', h: 22, wall: '#efe6d2', roof: 'pyramid', roofC: '#3d8f6e', win: 2 } },

    // ---------- Produção ----------
    { id: 'horta', name: 'Horta Comunitária', icon: '🥬', cat: 'producao', kind: 'producer', tag: 'agro', cost: 200, upkeep: 3, jobs: 2,
      out: { hortalicas: 16 }, water: true, lvl: 1, desc: 'Canteiros de verduras e legumes. Rende mais perto de água ou poço.', draw: { p: 'horta' } },
    { id: 'galinheiro', name: 'Galinheiro', icon: '🐔', cat: 'producao', kind: 'producer', tag: 'agro', cost: 350, upkeep: 5, jobs: 2,
      out: { ovos: 20 }, lvl: 1, desc: 'Galinhas caipiras que produzem ovos todos os dias.', draw: { p: 'galinheiro' } },
    { id: 'pomar', name: 'Pomar', icon: '🍎', cat: 'producao', kind: 'producer', tag: 'agro', cost: 450, upkeep: 5, jobs: 2,
      out: { frutas: 14 }, water: true, lvl: 2, desc: 'Árvores frutíferas. Rende mais perto de água ou poço.', draw: { p: 'pomar' } },
    { id: 'viveiro', name: 'Viveiro de Mudas', icon: '🌱', cat: 'producao', kind: 'producer', tag: 'agro', cost: 400, upkeep: 4, jobs: 2,
      out: { mudas: 15 }, water: true, lvl: 2, desc: 'Produz mudas de plantas nativas e ornamentais.', draw: { p: 'viveiro' } },
    { id: 'apiario', name: 'Apiário', icon: '🐝', cat: 'producao', kind: 'producer', tag: 'agro', cost: 500, upkeep: 3, jobs: 1,
      out: { mel: 3 }, flowers: true, lvl: 3, desc: 'Abelhas produzem mel. Quanto mais flores e árvores por perto, mais mel (até o dobro).', draw: { p: 'apiario' } },
    { id: 'estufa', name: 'Estufa', icon: '🌿', cat: 'producao', kind: 'producer', tag: 'agro', cost: 1200, upkeep: 12, jobs: 3,
      out: { hortalicas: 40 }, water: true, lvl: 4, desc: 'Cultivo protegido com alta produtividade.', draw: { p: 'estufa' } },
    { id: 'coleta', name: 'Ponto de Coleta', icon: '♻️', cat: 'producao', kind: 'producer', tag: 'recicla', cost: 300, upkeep: 3, jobs: 2,
      out: { reciclaveis: 40 }, houses: true, lvl: 1, desc: 'Recolhe material reciclável. Rende mais com casas por perto (+5% por casa no raio de 5, até +50%).', draw: { p: 'coleta' } },
    { id: 'triagem', name: 'Galpão de Triagem', icon: '📦', cat: 'producao', kind: 'processor', tag: 'recicla', cost: 900, upkeep: 8, jobs: 3,
      inp: { reciclaveis: 36 }, out: { fardos: 12 }, lvl: 2, desc: 'Separa e prensa recicláveis em fardos de alto valor.',
      draw: { p: 'box', h: 18, wall: '#c9d3c0', roof: 'gable', roofC: 'brand', win: 1, wide: true } },
    { id: 'padaria', name: 'Padaria Comunitária', icon: '🍞', cat: 'producao', kind: 'processor', tag: 'cozinha', cost: 700, upkeep: 12, jobs: 3,
      inp: { ovos: 6 }, out: { paes: 45 }, lvl: 2, desc: 'Pão fresquinho todo dia. Usa ovos (a farinha entra na manutenção).',
      draw: { p: 'box', h: 18, wall: '#f6d9a8', roof: 'gable', roofC: 'brand', win: 2, chimney: true } },
    { id: 'cozinha', name: 'Cozinha Comunitária', icon: '🍲', cat: 'producao', kind: 'processor', tag: 'cozinha', cost: 800, upkeep: 8, jobs: 3,
      inp: { hortalicas: 10, ovos: 6 }, out: { marmitas: 9 }, lvl: 2, desc: 'Transforma hortaliças e ovos em marmitas saudáveis.',
      draw: { p: 'box', h: 18, wall: '#fff1d6', roof: 'gable', roofC: 'brand', win: 2, chimney: true } },
    { id: 'doceria', name: 'Fábrica de Doces', icon: '🍓', cat: 'producao', kind: 'processor', tag: 'cozinha', cost: 900, upkeep: 6, jobs: 2,
      inp: { frutas: 10 }, out: { doces: 6 }, lvl: 3, desc: 'Geleias e doces artesanais feitos com as frutas do pomar.',
      draw: { p: 'box', h: 18, wall: '#ffd9e2', roof: 'gable', roofC: 'brand', win: 2 } },
    { id: 'artesanato', name: 'Ateliê de Artesanato', icon: '🏺', cat: 'producao', kind: 'producer', tag: 'arte', cost: 600, upkeep: 6, jobs: 2,
      out: { artesanato: 4 }, lvl: 2, desc: 'Cerâmica, cestaria e bordados feitos à mão.',
      draw: { p: 'box', h: 16, wall: '#e8c39e', roof: 'gable', roofC: 'brand', win: 1 } },
    { id: 'costura', name: 'Ateliê de Costura', icon: '🧵', cat: 'producao', kind: 'producer', tag: 'moda', cost: 1000, upkeep: 20, jobs: 4,
      out: { roupas: 7 }, lvl: 3, desc: 'Confecção de roupas. O tecido entra na manutenção.',
      draw: { p: 'box', h: 22, wall: '#e6dcf5', roof: 'flat', roofC: 'brand', win: 3 } },
    { id: 'marcenaria', name: 'Marcenaria', icon: '🔨', cat: 'producao', kind: 'producer', tag: 'arte', cost: 1500, upkeep: 20, jobs: 4,
      out: { moveis: 4 }, lvl: 5, desc: 'Móveis sob medida com madeira certificada.',
      draw: { p: 'box', h: 20, wall: '#c89b6d', roof: 'gable', roofC: 'brand', win: 2, wide: true } },
    { id: 'tecnologia', name: 'Centro de Tecnologia', icon: '💻', cat: 'producao', kind: 'producer', tag: 'tech', cost: 2500, upkeep: 30, jobs: 5,
      income: 450, lvl: 6, desc: 'Serviços digitais, manutenção de computadores e programação. Gera renda direta.',
      draw: { p: 'box', h: 34, wall: '#dbe7f0', roof: 'flat', roofC: 'brand', win: 4, glass: true } },
    { id: 'pousada', name: 'Pousada Ecológica', icon: '🏨', cat: 'producao', kind: 'producer', tag: 'arte', cost: 1800, upkeep: 15, jobs: 3,
      income: 100, beautyIncome: true, lvl: 4, desc: 'Turismo comunitário. Renda direta que cresce com a beleza ao redor (árvores, praças, água).',
      draw: { p: 'box', h: 22, wall: '#f3e2c4', roof: 'pyramid', roofC: 'brand', win: 3 } },

    // ---------- Comércio ----------
    { id: 'feira', name: 'Feira Livre', icon: '⛺', cat: 'comercio', kind: 'shop', cost: 500, upkeep: 5, jobs: 1, lvl: 1,
      sell: { cap: 60, mult: 1.1, food: true }, desc: 'Vende até 60 alimentos por dia com preço 10% melhor.', draw: { p: 'feira' } },
    { id: 'loja', name: 'Loja Solidária', icon: '🏪', cat: 'comercio', kind: 'shop', cost: 900, upkeep: 8, jobs: 2, lvl: 2,
      sell: { cap: 45, mult: 1.0 }, desc: 'Vende até 45 produtos de qualquer tipo por dia.',
      draw: { p: 'box', h: 18, wall: '#fff4e0', roof: 'flat', roofC: 'brand', win: 2, awning: true } },
    { id: 'armazem', name: 'Armazém', icon: '🏬', cat: 'comercio', kind: 'storage', cost: 700, upkeep: 5, jobs: 1, lvl: 2,
      store: 400, desc: '+400 de capacidade de estoque.', draw: { p: 'box', h: 20, wall: '#d7c3a5', roof: 'gable', roofC: '#8a6d4c', win: 0, wide: true } },
    { id: 'entrega', name: 'Central de Entregas', icon: '🛵', cat: 'comercio', kind: 'shop', cost: 1600, upkeep: 12, jobs: 3, lvl: 5,
      sell: { cap: 90, mult: 0.95 }, desc: 'Vendas por aplicativo e entregas: até 90 produtos por dia.',
      draw: { p: 'box', h: 18, wall: '#ffe9a8', roof: 'flat', roofC: 'brand', win: 2, awning: true } },

    // ---------- Vias ----------
    { id: 'estrada', name: 'Estrada de Terra', icon: '🟫', cat: 'vias', kind: 'road', cost: 8, upkeep: 0, lvl: 1, brush: 'line',
      desc: 'Arraste para traçar. Sobre a água vira ponte (R$ 60).' },
    { id: 'rua', name: 'Rua de Pedra', icon: '⬜', cat: 'vias', kind: 'road', cost: 20, upkeep: 0, lvl: 1, brush: 'line', beauty: 1, br: 1,
      desc: 'Calçamento bonito que valoriza o bairro. Arraste para traçar.' },
    { id: 'ponte', name: 'Ponte', icon: '🌉', cat: 'none', kind: 'road', cost: 60, upkeep: 1, lvl: 1, desc: 'Passagem sobre a água.' },

    // ---------- Decoração ----------
    { id: 'arvore', name: 'Árvore', icon: '🌳', cat: 'decor', kind: 'decor', cost: 20, beauty: 3, br: 2, lvl: 1, brush: 'paint', draw: { p: 'tree' } },
    { id: 'pinheiro', name: 'Pinheiro', icon: '🌲', cat: 'decor', kind: 'decor', cost: 20, beauty: 3, br: 2, lvl: 1, brush: 'paint', draw: { p: 'pine' } },
    { id: 'palmeira', name: 'Palmeira', icon: '🌴', cat: 'decor', kind: 'decor', cost: 30, beauty: 3, br: 2, lvl: 1, brush: 'paint', draw: { p: 'palm' } },
    { id: 'flores', name: 'Canteiro de Flores', icon: '🌷', cat: 'decor', kind: 'decor', cost: 15, beauty: 2, br: 1, lvl: 1, brush: 'paint', draw: { p: 'flowers' } },
    { id: 'cerca', name: 'Cerca Viva', icon: '🌿', cat: 'decor', kind: 'decor', cost: 10, beauty: 1, br: 1, lvl: 1, brush: 'paint', draw: { p: 'hedge' } },
    { id: 'banco_praca', name: 'Banco', icon: '💺', cat: 'decor', kind: 'decor', cost: 30, beauty: 2, br: 2, lvl: 1, draw: { p: 'bench' } },
    { id: 'poste', name: 'Poste de Luz', icon: '💡', cat: 'decor', kind: 'decor', cost: 40, beauty: 2, br: 2, lvl: 1, light: true, brush: 'paint', draw: { p: 'lamp' } },
    { id: 'praca', name: 'Praça', icon: '🏞️', cat: 'decor', kind: 'decor', cost: 150, beauty: 5, br: 3, lvl: 1, draw: { p: 'praca' } },
    { id: 'fonte', name: 'Fonte', icon: '⛲', cat: 'decor', kind: 'decor', cost: 250, beauty: 6, br: 3, lvl: 2, draw: { p: 'fonte' } },
    { id: 'parquinho', name: 'Parquinho', icon: '🎠', cat: 'decor', kind: 'decor', cost: 300, beauty: 7, br: 3, lvl: 2, draw: { p: 'parquinho' } },
    { id: 'mural', name: 'Mural de Arte', icon: '🎨', cat: 'decor', kind: 'decor', cost: 200, beauty: 6, br: 3, lvl: 3, draw: { p: 'mural' } },
    { id: 'estatua', name: 'Monumento', icon: '🗿', cat: 'decor', kind: 'decor', cost: 500, beauty: 9, br: 4, lvl: 4, draw: { p: 'estatua' } },

    // ---------- Terreno ----------
    { id: 't_grama', name: 'Grama', icon: '🟩', cat: 'terreno', kind: 'terrain', cost: 2, terrain: 0, brush: 'paint', lvl: 1, desc: 'Pinte o chão com grama.' },
    { id: 't_campo', name: 'Campo', icon: '🍀', cat: 'terreno', kind: 'terrain', cost: 2, terrain: 1, brush: 'paint', lvl: 1, desc: 'Grama mais escura.' },
    { id: 't_terra', name: 'Terra', icon: '🟤', cat: 'terreno', kind: 'terrain', cost: 2, terrain: 4, brush: 'paint', lvl: 1, desc: 'Chão de terra.' },
    { id: 't_areia', name: 'Areia', icon: '🟨', cat: 'terreno', kind: 'terrain', cost: 2, terrain: 3, brush: 'paint', lvl: 1, desc: 'Chão de areia.' },
    { id: 't_pedra', name: 'Pedregulho', icon: '⬛', cat: 'terreno', kind: 'terrain', cost: 2, terrain: 5, brush: 'paint', lvl: 1, desc: 'Chão de pedra.' },
    { id: 't_agua', name: 'Cavar Lago', icon: '🌊', cat: 'terreno', kind: 'terrain', cost: 30, terrain: 6, brush: 'paint', lvl: 1, beauty: 2, br: 2, desc: 'Cria água em terreno livre. Água deixa o bairro mais bonito e ajuda as hortas.' },
    { id: 't_aterrar', name: 'Aterrar', icon: '🏝️', cat: 'terreno', kind: 'terrain', cost: 30, terrain: 0, fill: true, brush: 'paint', lvl: 1, desc: 'Transforma água em terra firme.' },
    { id: 't_limpar', name: 'Limpar Mato', icon: '✂️', cat: 'terreno', kind: 'clear', cost: 5, brush: 'paint', lvl: 1, desc: 'Remove árvores, arbustos e pedras naturais.' },

    // ---------- Natureza (gerada pelo mundo) ----------
    { id: 'n_arvore', name: 'Árvore nativa', icon: '🌳', cat: 'none', kind: 'natural', beauty: 1, br: 1, draw: { p: 'tree' } },
    { id: 'n_pinheiro', name: 'Pinheiro nativo', icon: '🌲', cat: 'none', kind: 'natural', beauty: 1, br: 1, draw: { p: 'pine' } },
    { id: 'n_palmeira', name: 'Coqueiro', icon: '🌴', cat: 'none', kind: 'natural', beauty: 1, br: 1, draw: { p: 'palm' } },
    { id: 'n_arbusto', name: 'Arbusto', icon: '🌿', cat: 'none', kind: 'natural', beauty: 0, br: 0, draw: { p: 'bush' } },
    { id: 'n_pedra', name: 'Rocha', icon: '⛰️', cat: 'none', kind: 'natural', beauty: 0, br: 0, draw: { p: 'rock' } },
    { id: 'n_flores', name: 'Flores do campo', icon: '🌼', cat: 'none', kind: 'natural', beauty: 1, br: 1, draw: { p: 'wildflowers' } }
  ];

  var BY_ID = {};
  ITEMS.forEach(function (it, n) { it.num = n; BY_ID[it.id] = it; });

  var BRANCHES = [
    { id: 'agro', name: 'Agricultura Familiar', icon: '🥬', tag: 'agro', starters: ['horta', 'galinheiro', 'pomar'],
      desc: 'Hortas, pomares, galinheiros e apiários. Comida boa e renda no campo.' },
    { id: 'recicla', name: 'Cooperativa de Reciclagem', icon: '♻️', tag: 'recicla', starters: ['coleta', 'triagem'],
      desc: 'Coleta, triagem e venda de recicláveis. Renda e cidade limpa.' },
    { id: 'cozinha', name: 'Cozinha e Panificação', icon: '🍞', tag: 'cozinha', starters: ['padaria', 'cozinha', 'galinheiro', 'horta'],
      desc: 'Padaria, marmitas e doces caseiros com ingredientes locais.' },
    { id: 'moda', name: 'Costura e Moda', icon: '🧵', tag: 'moda', starters: ['costura'],
      desc: 'Ateliês de costura e confecção de roupas.' },
    { id: 'arte', name: 'Artesanato e Turismo', icon: '🏺', tag: 'arte', starters: ['artesanato', 'pousada'],
      desc: 'Arte local, ateliês e turismo comunitário.' },
    { id: 'tech', name: 'Tecnologia e Serviços', icon: '💻', tag: 'tech', starters: ['tecnologia'],
      desc: 'Inclusão digital, serviços e programação.' },
    { id: 'livre', name: 'Personalizado', icon: '✨', tag: null, starters: [],
      desc: 'Invente o seu ramo! Sem foco único: +10% de produção em tudo.' }
  ];
  var BRANCH_BONUS = 0.25, FREE_BONUS = 0.10;

  var PRESETS = [
    { id: 'rio', name: 'Vale do Rio', icon: '🏞️', desc: 'Um rio corta o vale, com matas e colinas.' },
    { id: 'litoral', name: 'Litoral', icon: '🏖️', desc: 'Praia, coqueiros e mar de um lado do mapa.' },
    { id: 'lagos', name: 'Terra dos Lagos', icon: '💧', desc: 'Vários lagos e muito verde.' },
    { id: 'cerrado', name: 'Cerrado', icon: '🌾', desc: 'Clima seco, chão de terra e um riacho.' }
  ];

  var COLORS = ['#e4572e', '#f3a712', '#29bf12', '#2e86de', '#8e44ad', '#e84393', '#16a085', '#34495e'];
  var EMOJIS = ['🌱', '🤝', '🌻', '🏡', '⭐', '💚', '🔆', '🧺', '🛠️', '🎯', '🌈', '🐝'];

  var LEVELS = [0, 100, 320, 800, 1600, 3000, 5000, 8000, 12000, 18000];
  var LEVEL_NAMES = ['Semente', 'Broto', 'Muda', 'Raiz Forte', 'Árvore Jovem', 'Referência', 'Rede Solidária', 'Polo Regional', 'Inspiração', 'Lenda'];

  var MISSIONS = [
    { id: 'hq', title: 'Funde seu projeto', desc: 'Construa o Centro Comunitário.', hint: 'Toque em um terreno livre no mapa.', goal: 1, stat: 'hq', reward: 0 },
    { id: 'road', title: 'Abra caminhos', desc: 'Faça 6 trechos de estrada ligados ao Centro.', hint: 'Toque em 🛣️ Vias e arraste o dedo começando ao lado do Centro.', goal: 6, stat: 'roads', reward: 150 },
    { id: 'casas', title: 'Lar doce lar', desc: 'Construa 3 casas ao lado das estradas.', hint: 'Em 🏘️ Comunidade escolha Casa e toque ao lado de uma estrada.', goal: 3, stat: 'houses', reward: 300 },
    { id: 'prod', title: 'Mãos à obra', desc: 'Construa 2 unidades de produção ligadas à estrada.', hint: 'Abra 🌾 Produção. Hortas e galinheiros são baratos para começar.', goal: 2, stat: 'producers', reward: 300 },
    { id: 'venda', title: 'Hora de vender', desc: 'Construa uma Feira Livre ou Loja Solidária.', hint: 'Abra 🛒 Comércio. Pontos de venda transformam produtos em dinheiro.', goal: 1, stat: 'shops', reward: 400 },
    { id: 'emp6', title: 'Primeiros empregos', desc: 'Tenha 6 pessoas trabalhando.', hint: 'Mais casas = mais gente disponível. Mais construções = mais vagas.', goal: 6, stat: 'employed', reward: 500 },
    { id: 'decor', title: 'Bairro bonito', desc: 'Coloque 10 decorações.', hint: 'Árvores, flores e bancos (🌳 Decorar) aumentam o bem-estar.', goal: 10, stat: 'decor', reward: 300 },
    { id: 'lucro', title: 'No azul', desc: 'Feche um dia com lucro de R$ 100.', hint: 'Lucro = vendas - salários - manutenção. Veja o painel do projeto.', goal: 100, stat: 'profit', reward: 600 },
    { id: 'cadeia', title: 'Cadeia produtiva', desc: 'Construa uma unidade de beneficiamento.', hint: 'Cozinha, Padaria, Triagem ou Fábrica de Doces transformam produtos em itens de maior valor.', goal: 1, stat: 'processors', reward: 800 },
    { id: 'emp15', title: 'Gerando oportunidades', desc: 'Tenha 15 pessoas trabalhando.', hint: 'Creches liberam mais pessoas para trabalhar.', goal: 15, stat: 'employed', reward: 1000 },
    { id: 'bem70', title: 'Comunidade feliz', desc: 'Alcance 70% de bem-estar.', hint: 'Decoração perto das casas, emprego e serviços (creche, escola, saúde).', goal: 70, stat: 'well', reward: 800 },
    { id: 'escola', title: 'Capacitação', desc: 'Construa uma Escola de Capacitação.', hint: 'Cada escola aumenta a produtividade de todo o projeto.', goal: 1, stat: 'escola', reward: 1000 },
    { id: 'fat600', title: 'Negócio sustentável', desc: 'Fature R$ 600 em um único dia.', hint: 'Garanta pontos de venda suficientes e produtos de maior valor.', goal: 600, stat: 'revenue', reward: 1500 },
    { id: 'emp30', title: 'Projeto que transforma', desc: 'Tenha 30 pessoas trabalhando.', hint: 'Sobrados abrigam 10 pessoas.', goal: 30, stat: 'employed', reward: 2000 },
    { id: 'renda10k', title: 'Renda que circula', desc: 'Distribua R$ 10.000 em salários no total.', hint: 'Todo salário pago é renda para a comunidade.', goal: 10000, stat: 'totalWages', reward: 2500 },
    { id: 'lvl6', title: 'Referência regional', desc: 'Alcance o nível 6 de impacto.', hint: 'Empregos e vendas geram pontos de impacto.', goal: 6, stat: 'level', reward: 3000 },
    { id: 'emp60', title: 'Polo de trabalho e renda', desc: 'Tenha 60 pessoas trabalhando.', hint: 'Melhore construções (nível 2 e 3) para abrir mais vagas.', goal: 60, stat: 'employed', reward: 5000 },
    { id: 'lvl10', title: 'Lenda da economia solidária', desc: 'Alcance o nível 10.', hint: 'Você chegou longe. Continue construindo do seu jeito!', goal: 10, stat: 'level', reward: 10000 }
  ];

  var EVENTS = [
    { id: 'edital', icon: '📜', text: 'Edital aprovado! O projeto recebeu R$ 1.500 de fomento.', money: 1500 },
    { id: 'doacao', icon: '🎁', text: 'Doação de ferramentas e equipamentos: +R$ 600.', money: 600 },
    { id: 'chuva', icon: '🌧️', text: 'Chuva forte: produção agrícola -40% por 2 dias.', eff: 'agro', mult: 0.6, days: 2 },
    { id: 'seca', icon: '☀️', text: 'Estiagem: produção agrícola -25% por 3 dias.', eff: 'agro', mult: 0.75, days: 3 },
    { id: 'feira', icon: '🎪', text: 'Feira regional na cidade: vendas +50% por 3 dias!', eff: 'sell', mult: 1.5, days: 3 },
    { id: 'curso', icon: '📚', text: 'Curso gratuito de gestão: +15% de produtividade por 5 dias.', eff: 'prod', mult: 1.15, days: 5 },
    { id: 'reportagem', icon: '📸', text: 'Reportagem sobre o projeto! Bem-estar +8 por 5 dias.', eff: 'well', add: 8, days: 5 },
    { id: 'quebra', icon: '🔧', text: 'Um equipamento quebrou. Conserto: -R$ 300.', money: -300 }
  ];

  var PHRASES = [
    'Consegui meu primeiro emprego aqui!', 'A horta mudou a vida da minha família.', 'Agora tenho renda própria!',
    'Que bairro bonito ficou!', 'Juntos somos mais fortes.', 'Bom dia, vizinho!', 'Hoje a feira está cheia!',
    'Fiz um curso e fui promovida!', 'Meus filhos ficam na creche enquanto trabalho.', 'Economia solidária funciona!',
    'Vendi tudo hoje!', 'Precisamos de mais casas por aqui.', 'Adoro passear na praça.', 'Esse projeto é nosso!'
  ];

  var TIPS = [
    'Construções precisam estar ao lado de uma estrada ligada ao Centro Comunitário.',
    'Casas trazem moradores. Parte deles pode trabalhar (creches aumentam essa parte).',
    'Sem pontos de venda, os produtos ficam parados no estoque.',
    'Beneficiar produtos (marmitas, doces, fardos) rende muito mais que vender cru.',
    'Toque numa construção para ver detalhes, melhorar, mover ou demolir.',
    'Use dois dedos para mover o mapa e aproximar. Com o modo Selecionar, um dedo também move.',
    'Errou? Toque em ↩️ Desfazer: o dinheiro volta.',
    'Pegue microcrédito no painel do projeto se o caixa apertar.'
  ];

  return {
    WAGE: WAGE, DAY_SEC: DAY_SEC, START_MONEY: START_MONEY, GOODS: GOODS, TERRAIN: TERRAIN, T: T, CATS: CATS,
    ITEMS: ITEMS, BY_ID: BY_ID, BRANCHES: BRANCHES, BRANCH_BONUS: BRANCH_BONUS, FREE_BONUS: FREE_BONUS,
    PRESETS: PRESETS, COLORS: COLORS, EMOJIS: EMOJIS, LEVELS: LEVELS, LEVEL_NAMES: LEVEL_NAMES,
    MISSIONS: MISSIONS, EVENTS: EVENTS, PHRASES: PHRASES, TIPS: TIPS
  };
})();

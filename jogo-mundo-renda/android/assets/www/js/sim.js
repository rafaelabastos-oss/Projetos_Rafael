/* Mundo Renda - simulação econômica e social (um ciclo por dia de jogo) */
'use strict';

var Sim = (function () {
  var I = DATA.BY_ID, G = DATA.GOODS, w = World.w;
  var status = {};       // estado de cada construção (por índice do ladrilho)
  var lastReport = null;

  function activeMult(s, eff) {
    var m = 1;
    (s.events || []).forEach(function (e) { if (e.eff === eff && e.mult) m *= e.mult; });
    return m;
  }
  function activeAdd(s, eff) {
    var a = 0;
    (s.events || []).forEach(function (e) { if (e.eff === eff && e.add) a += e.add; });
    return a;
  }

  function branchMult(s, it) {
    if (s.project.branch === 'livre') return 1 + DATA.FREE_BONUS;
    var br = World.branchOf(s);
    return (it.tag && br && br.tag === it.tag) ? 1 + DATA.BRANCH_BONUS : 1;
  }

  function stockTotal(st) { var t = 0; for (var g in st) t += st[g]; return t; }

  // Calcula o resultado de um dia com o mapa atual. Não altera o estado.
  function compute(s) {
    World.recompute();
    var list = [], k, o, it;
    var c = { houses: 0, cap: 0, jobs: 0, creche: 0, escola: 0, banco: 0, store: 0, roads: 0, decor: 0,
      producers: 0, processors: 0, shops: 0 };
    for (k = 0; k < w.N; k++) {
      o = w.obj[k];
      if (w.roadConn[k]) c.roads++;
      if (!o) continue;
      it = I[o.id];
      if (it.kind === 'decor') { c.decor++; continue; }
      if (it.kind === 'natural' || it.kind === 'road') continue;
      var con = World.connected(k);
      var b = { k: k, it: it, lv: o.lv, con: con };
      list.push(b);
      if (!con) continue;
      if (it.kind === 'house') { c.houses++; c.cap += it.res * o.lv; }
      if (it.jobs) c.jobs += it.jobs * o.lv;
      if (it.store) c.store += it.store * o.lv;
      if (it.id === 'creche') c.creche++;
      if (it.id === 'escola') c.escola++;
      if (it.id === 'banco') c.banco++;
      if (it.kind === 'producer') c.producers++;
      if (it.kind === 'processor') { c.processors++; c.producers++; }
      if (it.kind === 'shop') c.shops++;
    }

    var part = Math.min(0.85, 0.55 + 0.06 * Math.min(4, c.creche));
    var labor = Math.floor(s.pop * part);
    var employed = Math.min(labor, c.jobs);
    var staff = c.jobs > 0 ? employed / c.jobs : 0;
    var prodMult = (1 + 0.06 * Math.min(5, c.escola)) * activeMult(s, 'prod');
    var agroMult = activeMult(s, 'agro');

    var stock = {}, g;
    for (g in s.stock) stock[g] = s.stock[g];
    var produced = {}, income = 0, st = {}, outputs = [];

    // produtores
    list.forEach(function (b) {
      var it = b.it, info = { con: b.con, staff: it.jobs ? staff : 1, out: {}, inc: 0, bonus: [], ratio: 1 };
      st[b.k] = info;
      if (!b.con) { if (it.kind !== 'infra') info.alert = 'road'; return; }
      if (it.jobs && staff < 0.5) info.alert = staff <= 0 ? 'staff0' : 'staff';
      if (it.kind !== 'producer') return;
      var f = b.lv * staff * prodMult * branchMult(s, it);
      if (branchMult(s, it) > 1) info.bonus.push('Ramo do projeto +' + Math.round((branchMult(s, it) - 1) * 100) + '%');
      if (it.water && w.waterB[b.k]) { f *= 1.2; info.bonus.push('Água por perto +20%'); }
      if (w.solarB[b.k]) { f *= 1.1; info.bonus.push('Energia solar +10%'); }
      if (it.flowers) { var fb = Math.min(1, w.beauty[b.k] / 15); f *= 1 + fb; if (fb > 0) info.bonus.push('Flores e árvores +' + Math.round(fb * 100) + '%'); }
      if (it.houses) { var hb = Math.min(0.5, 0.05 * w.houseN[b.k]); f *= 1 + hb; if (hb > 0) info.bonus.push('Casas por perto +' + Math.round(hb * 100) + '%'); }
      if (it.tag === 'agro' && agroMult !== 1) f *= agroMult;
      if (it.out) for (var gg in it.out) {
        var q = it.out[gg] * f;
        info.out[gg] = q;
        produced[gg] = (produced[gg] || 0) + q;
      }
      if (it.income) {
        var inc = it.income;
        if (it.beautyIncome) { var bi = Math.min(300, w.beauty[b.k] * 10); inc += bi; if (bi > 0) info.bonus.push('Beleza ao redor +' + U.money(bi)); }
        inc *= f;
        info.inc = inc; income += inc;
      }
      outputs.push(b);
    });
    for (g in produced) stock[g] = (stock[g] || 0) + produced[g];

    // beneficiamento (consome insumos do estoque)
    list.forEach(function (b) {
      var it = b.it, info = st[b.k];
      if (it.kind !== 'processor' || !b.con) return;
      var f = b.lv * staff * prodMult * branchMult(s, it);
      if (branchMult(s, it) > 1) info.bonus.push('Ramo do projeto +' + Math.round((branchMult(s, it) - 1) * 100) + '%');
      if (w.solarB[b.k]) { f *= 1.1; info.bonus.push('Energia solar +10%'); }
      var ratio = 1, gi;
      for (gi in it.inp) {
        var need = it.inp[gi] * f;
        if (need > 0) ratio = Math.min(ratio, (stock[gi] || 0) / need);
      }
      ratio = U.clamp(ratio, 0, 1);
      info.ratio = ratio;
      info.inp = {};
      for (gi in it.inp) { var used = it.inp[gi] * f * ratio; stock[gi] = (stock[gi] || 0) - used; info.inp[gi] = used; }
      for (gi in it.out) {
        var q = it.out[gi] * f * ratio;
        info.out[gi] = q;
        produced[gi] = (produced[gi] || 0) + q;
        stock[gi] = (stock[gi] || 0) + q;
      }
      if (f > 0 && ratio < 0.5 && !info.alert) info.alert = 'input';
      outputs.push(b);
    });

    // vendas: primeiro as feiras (só alimentos), depois as lojas gerais
    var priceMult = (0.85 + 0.3 * (s.stats.well / 100)) * (1 + 0.05 * Math.min(2, c.banco));
    var sellMult = activeMult(s, 'sell');
    var shops = list.filter(function (b) { return b.con && b.it.sell; });
    shops.sort(function (a, b) { return (b.it.sell.food ? 1 : 0) - (a.it.sell.food ? 1 : 0); });
    var goodsByPrice = Object.keys(G).sort(function (a, b) { return G[b].price - G[a].price; });
    var revenue = 0, sold = {};
    shops.forEach(function (b) {
      var sp = b.it.sell, capLeft = sp.cap * b.lv * (b.it.jobs ? staff : 1) * sellMult, info = st[b.k];
      info.sold = 0; info.cap = capLeft;
      for (var n = 0; n < goodsByPrice.length && capLeft > 0.01; n++) {
        var gg = goodsByPrice[n];
        if (sp.food && !G[gg].food) continue;
        var have = stock[gg] || 0;
        if (have <= 0.01) continue;
        var q = Math.min(have, capLeft);
        stock[gg] = have - q; capLeft -= q;
        sold[gg] = (sold[gg] || 0) + q;
        info.sold += q;
        revenue += q * G[gg].price * sp.mult * priceMult;
      }
    });

    // capacidade de estoque
    var lost = 0, total = stockTotal(stock);
    if (total > c.store) {
      var excess = total - c.store;
      var cheap = goodsByPrice.slice().reverse();
      for (var n2 = 0; n2 < cheap.length && excess > 0; n2++) {
        var gq = stock[cheap[n2]] || 0, rem = Math.min(gq, excess);
        stock[cheap[n2]] = gq - rem; excess -= rem; lost += rem;
      }
    }
    for (g in stock) if (stock[g] < 0.001) delete stock[g];

    // custos
    var wages = employed * DATA.WAGE;
    var upkeep = 0;
    for (k = 0; k < w.N; k++) {
      o = w.obj[k];
      if (o && I[o.id].upkeep) upkeep += I[o.id].upkeep * o.lv;
    }
    var loanPay = s.loan ? s.loan.daily : 0;
    var profit = revenue + income - wages - upkeep - loanPay;

    // bem-estar
    var wsum = 0, wres = 0;
    var empRate = labor > 0 ? employed / labor : 1;
    var wellAdd = activeAdd(s, 'well');
    list.forEach(function (b) {
      if (b.it.kind !== 'house' || !b.con) return;
      var v = 40 + Math.min(25, w.beauty[b.k]) + (w.covSaude[b.k] ? 12 : 0) + (w.covEscola[b.k] ? 5 : 0) +
        (w.covCreche[b.k] ? 6 : 0) + empRate * 15 + wellAdd;
      v = U.clamp(v, 0, 100);
      st[b.k].well = v;
      var r = b.it.res * b.lv;
      wsum += v * r; wres += r;
    });
    var well = wres > 0 ? wsum / wres : 50;

    return {
      c: c, part: part, labor: labor, employed: employed, staff: staff, prodMult: prodMult, priceMult: priceMult,
      produced: produced, sold: sold, stock: stock, revenue: revenue, income: income, wages: wages, upkeep: upkeep,
      loanPay: loanPay, profit: profit, well: well, lost: lost, st: st, outputs: outputs, list: list
    };
  }

  // Avança um dia: aplica o resultado no estado do jogo.
  function endDay(s) {
    var r = compute(s);
    s.stock = r.stock;
    s.money += r.profit;
    s.stats.revenue = r.revenue + r.income;
    s.stats.wages = r.wages;
    s.stats.upkeep = r.upkeep + r.loanPay;
    s.stats.profit = r.profit;
    s.stats.totalWages += r.wages;
    s.stats.totalRevenue += r.revenue + r.income;
    s.stats.lost = r.lost;
    s.stats.sold = r.sold;
    s.stats.produced = r.produced;
    s.stats.bestProfit = Math.max(s.stats.bestProfit || 0, r.profit);
    s.stats.bestRevenue = Math.max(s.stats.bestRevenue || 0, r.revenue + r.income);
    // população se aproxima da capacidade das casas
    var cap = r.c.cap;
    if (s.pop < cap) s.pop = Math.min(cap, s.pop + Math.max(1, Math.round((cap - s.pop) * 0.3 * (0.4 + r.well / 100))));
    else if (s.pop > cap) s.pop = cap;
    s.stats.well = r.well;
    // impacto e nível
    var gained = r.employed + Math.floor(Math.max(0, r.revenue + r.income) / 50);
    s.pts += gained;
    var leveled = false;
    while (s.level < DATA.LEVELS.length && s.pts >= DATA.LEVELS[s.level]) { s.level++; leveled = true; }
    // microcrédito
    if (s.loan) { s.loan.left--; if (s.loan.left <= 0) s.loan = null; }
    // eventos
    s.events = (s.events || []).filter(function (e) { e.days--; return e.days > 0; });
    var ev = null;
    if (s.mode !== 'criativo' && s.day >= s.nextEvent && World.w.hq >= 0) {
      var pool = DATA.EVENTS.filter(function (e) { return e.id !== s.lastEvent; });
      ev = pool[Math.floor(Math.random() * pool.length)];
      s.lastEvent = ev.id;
      if (ev.money) s.money += ev.money;
      if (ev.eff) s.events.push({ id: ev.id, eff: ev.eff, mult: ev.mult, add: ev.add, days: ev.days });
      s.nextEvent = s.day + 10 + Math.floor(Math.random() * 9);
    }
    s.history.push({ d: s.day, rev: Math.round(r.revenue + r.income), wag: r.wages, upk: Math.round(r.upkeep + r.loanPay),
      pro: Math.round(r.profit), emp: r.employed, pop: s.pop });
    if (s.history.length > 60) s.history.shift();
    s.day++;
    status = r.st;
    lastReport = r;
    return { report: r, leveled: leveled, event: ev };
  }

  function refresh(s) {
    var r = compute(s);
    status = r.st;
    lastReport = r;
    return r;
  }

  function missionStat(s, stat) {
    var r = lastReport, c = r ? r.c : {};
    switch (stat) {
      case 'hq': return World.w.hq >= 0 ? 1 : 0;
      case 'roads': return c.roads || 0;
      case 'houses': return c.houses || 0;
      case 'producers': return c.producers || 0;
      case 'processors': return c.processors || 0;
      case 'shops': return c.shops || 0;
      case 'employed': return r ? r.employed : 0;
      case 'decor': return c.decor || 0;
      case 'profit': return Math.max(0, s.stats.bestProfit || 0);
      case 'well': return Math.round(s.stats.well);
      case 'escola': return c.escola || 0;
      case 'revenue': return Math.max(0, s.stats.bestRevenue || 0);
      case 'totalWages': return s.stats.totalWages;
      case 'level': return s.level;
    }
    return 0;
  }

  function takeLoan(s) {
    if (s.loan) return false;
    s.money += 3000;
    s.loan = { left: 90, daily: 40 };
    return true;
  }

  return {
    compute: compute, endDay: endDay, refresh: refresh, missionStat: missionStat, takeLoan: takeLoan,
    status: function (k) { return status[k]; }, report: function () { return lastReport; }, stockTotal: stockTotal
  };
})();

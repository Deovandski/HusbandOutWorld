// Minari (reusable component): the carved-statue game from #HusbandOutWorld, as a working prototype against
// the computer (#131). Built new for this site; its pattern (a JSON game in data-game, every word in a hidden
// strings block read by msg()) follows site/js/iso-darts.js.
//
// The series says (World Lore › Minari, Vol 1 Ch II, Vol 3, Arc #2 notes): carved statues bound with nari stones,
// a carved 3D table whose pieces plug in, "like Gwent" with pieces instead of cards, rounds, and one statue that
// hides the nari stone: eliminate it to win. Deo's rules (#131): statues are Races, Fauna and Beasts and the
// creature is the strength; Flora are bases that help or hurt the statue on them; terrain squares (type and
// height) give bonuses; each player hides their own stone; three opponents (Nina easy, Aurora medium, Neferteri
// challenging); painting is cosmetic; no dialogue.
//
// Usage: minari_html(game, uid, info) in tools/build.py writes
//   <div class="minari" data-game='{"rules":…,"terrains":[…],"regions":[…],"statues":[…],"flora":[…],"opponents":[…]}'>
//     <div class="minari__strings" hidden><span data-k="pass">Pass</span>…</div>   (every word it shows)
//     <details class="minari__rules">…</details>  <div class="minari__app"></div>  <p class="minari__live" aria-live="polite"></p>
//   </div>
// and the page loads this script and site/css/minari.css. Several on one page work.
// Options (data-game): rules { statuesPerPlayer, floraPerPlayer, lanes, statuesPerSquare, roundsToWin, homeBonus,
// heightBonus, shieldBonus }; terrains [{ id, color }]; regions [{ mix: { terrain: weight }, height: [min, max], lore }];
// statues [{ power, homes: [terrain], traits: [flying|armor|shield|cloak], kind, img, lore }];
// flora [{ effect: { plus | plusOn: [terrain, n] | plusHeight: [h, n] | plusKind: [kind, n] | foeLane | foeTop |
// random: [min, max] }, img, lore }]; opponents [{ id, level: easy|medium|hard, img, lore }].
// Names come from the strings block: s_<i> (statues), f_<i> (flora), r_<i> (regions), o_<id> (opponents), t_<id> (terrains).
// Theme: --minari-wood, --minari-ink, --minari-accent, --minari-line (see minari.css).
// Accessible: everything is a button (Tab, arrow keys within a row, Enter or Space); every move, lane result and
// reveal is announced; nothing shows which hidden statue holds the stone; no animation needed (reduced motion: none).
(function () {
  'use strict';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var OTHER = { you: 'ai', ai: 'you' };

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function sample(n, k) { return shuffle(Array.from({ length: n }, function (_, i) { return i; })).slice(0, k); }
  function weighted(mix) {
    var keys = Object.keys(mix), total = keys.reduce(function (s, k) { return s + mix[k]; }, 0), r = Math.random() * total;
    for (var i = 0; i < keys.length; i++) { r -= mix[keys[i]]; if (r < 0) return keys[i]; }
    return keys[keys.length - 1];
  }
  function el(tag, attrs, kids) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') e.textContent = v;
      else if (k === 'class') e.className = v;
      else if (k.slice(0, 2) === 'on') e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    });
    (kids || []).forEach(function (c) { if (c) e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return e;
  }

  document.querySelectorAll('.minari[data-game]').forEach(function (root) {
    var G = JSON.parse(root.dataset.game), R = G.rules;
    var app = root.querySelector('.minari__app'), live = root.querySelector('.minari__live');
    function msg(key, vars) {
      vars = vars || {};
      var s = root.querySelector('.minari__strings [data-k="' + key + '"]');
      return (s ? s.textContent : key).replace(/\{(\w+)\}/g, function (m, k) { return k in vars ? String(vars[k]) : m; });
    }
    var TERR = {}; G.terrains.forEach(function (t) { TERR[t.id] = t; });
    var tName = function (id) { return msg('t_' + id); };
    var sName = function (i) { return msg('s_' + i); };
    var fName = function (i) { return msg('f_' + i); };
    var oppOf = function (id) { return G.opponents.filter(function (o) { return o.id === id; })[0]; };

    var S = { opp: G.opponents[0].id, paint: false, setup: true, you: newSide(), ai: newSide() };
    var log = [];
    function newSide() { return { pool: [], hand: [], flora: [], stone: null }; }
    function draft(side) {
      side.pool = sample(G.statues.length, R.statuesPerPlayer);
      side.flora = sample(G.flora.length, R.floraPerPlayer);
      side.stone = null;
    }
    draft(S.you);

    function say(text, keep) {
      live.textContent = text;
      if (keep !== false) { log.unshift(text); log = log.slice(0, 8); }
    }
    function oppName() { return msg('o_' + S.opp); }
    function who(side) { return side === 'you' ? msg('you') : oppName(); }

    // ---------------------------------------------------------------- powers
    function effectText(e) {
      var parts = [];
      if ('plus' in e) parts.push(msg('effPlus', { sign: e.plus < 0 ? '−' : '+', n: Math.abs(e.plus) }));
      if (e.plusOn) parts.push(msg('effPlusOn', { n: e.plusOn[1], terrain: tName(e.plusOn[0]) }));
      if (e.plusHeight) parts.push(msg('effHeight', { n: e.plusHeight[1], h: e.plusHeight[0] }));
      if (e.plusKind) parts.push(msg('effKind', { n: e.plusKind[1], kind: msg('kind_' + e.plusKind[0]) }));
      if (e.foeLane) parts.push(msg('effFoeLane', { n: e.foeLane }));
      if (e.foeTop) parts.push(msg('effFoeTop', { n: e.foeTop }));
      if (e.random) parts.push(msg('effRandom', { min: e.random[0], max: e.random[1] }));
      return parts.join('; ');
    }
    function selfPower(lane, side, p) {
      var st = G.statues[p.s], sq = lane.sq[side], o = lane.sq[OTHER[side]], v = st.power;
      if (st.homes.indexOf(sq.t) >= 0) v += R.homeBonus;
      var d = (sq.h - o.h) * R.heightBonus;
      if (d < 0 && st.traits.indexOf('flying') >= 0) d = 0;
      v += d;
      if (p.f !== null) {
        var e = G.flora[p.f].effect;
        if ('plus' in e) v += e.plus;
        if (e.plusOn && e.plusOn[0] === sq.t) v += e.plusOn[1];
        if (e.plusHeight && sq.h >= e.plusHeight[0]) v += e.plusHeight[1];
        if (e.plusKind && e.plusKind[0] === st.kind) v += e.plusKind[1];
        if (e.random) v += p.rnd;
      }
      return v;
    }
    // Powers in one lane. `viewer` sees the other side's cloaked statues as `guess` (or as hidden when guess is null).
    function laneP(lane, viewer, guess) {
      var out = {};
      ['you', 'ai'].forEach(function (side) { out[side] = lane[side].map(function (p) { return selfPower(lane, side, p); }); });
      ['you', 'ai'].forEach(function (side) {
        var foe = OTHER[side];
        lane[side].forEach(function (p) {
          if (p.f === null) return;
          var e = G.flora[p.f].effect;
          if (e.foeLane) out[foe] = out[foe].map(function (v) { return v - e.foeLane; });
          if (e.foeTop && out[foe].length) {
            var top = 0;
            out[foe].forEach(function (v, i) { if (v > out[foe][top]) top = i; });
            out[foe][top] -= e.foeTop;
          }
        });
      });
      ['you', 'ai'].forEach(function (side) {
        var outnumbered = lane[side].length < lane[OTHER[side]].length;
        out[side] = out[side].map(function (v, i) {
          var st = G.statues[lane[side][i].s];
          if (outnumbered && st.traits.indexOf('shield') >= 0) v += R.shieldBonus;
          if (st.traits.indexOf('armor') >= 0) v = Math.max(v, st.power);
          v = Math.max(0, v);
          if (viewer && side !== viewer && !lane.counted && st.traits.indexOf('cloak') >= 0) v = guess;
          return v;
        });
      });
      out.tYou = out.you.reduce(function (a, b) { return a + (b === null ? 0 : b); }, 0);
      out.tAi = out.ai.reduce(function (a, b) { return a + (b === null ? 0 : b); }, 0);
      out.hidden = { you: out.you.indexOf(null) >= 0, ai: out.ai.indexOf(null) >= 0 };
      return out;
    }

    // ---------------------------------------------------------------- match flow
    function newBoard() {
      var ri = Math.floor(Math.random() * G.regions.length), reg = G.regions[ri];
      S.region = ri;
      S.board = [];
      for (var l = 0; l < R.lanes; l++) {
        var sq = {};
        ['you', 'ai'].forEach(function (side) {
          sq[side] = { t: weighted(reg.mix), h: reg.height[0] + Math.floor(Math.random() * (reg.height[1] - reg.height[0] + 1)) };
        });
        S.board.push({ sq: sq, you: [], ai: [] });
      }
    }
    function startMatch() {
      S.setup = false;
      S.you.hand = S.you.pool.slice();
      S.ai = newSide(); draft(S.ai);
      S.ai.hand = S.ai.pool.slice();
      S.ai.stone = aiStone();
      S.wins = { you: 0, ai: 0 };
      S.round = 0; S.over = null; S.found = { you: null, ai: null };
      log = [];
      nextRound();
    }
    function nextRound() {
      S.round++;
      S.passed = { you: false, ai: false };
      S.placed = { you: 0, ai: 0 };
      S.summary = null;
      S.sel = null; S.selF = null;
      newBoard();
      S.turn = S.round % 2 === 1 ? 'you' : 'ai';
      say(msg('round', { n: S.round }) + '. ' + msg('field', { region: msg('r_' + S.region) }));
      autoPass();
      render();
      if (!S.summary && S.turn === 'ai') aiTurn();
    }
    function autoPass() {
      ['you', 'ai'].forEach(function (side) { if (!S[side].hand.length) S.passed[side] = true; });
      if (S.passed.you && S.passed.ai) resolve();
      else if (S.passed[S.turn]) S.turn = OTHER[S.turn];
    }
    function legal(side) {
      var moves = [], hand = S[side].hand, fl = [null].concat(S[side].flora);
      hand.forEach(function (s) {
        S.board.forEach(function (lane, l) {
          if (lane[side].length >= R.statuesPerSquare) return;
          fl.forEach(function (f) { moves.push({ s: s, l: l, f: f }); });
        });
      });
      return moves;
    }
    function play(side, m) {
      var lane = S.board[m.l], st = G.statues[m.s];
      var rnd = m.f !== null && G.flora[m.f].effect.random ? G.flora[m.f].effect.random[0] + Math.floor(Math.random() * (G.flora[m.f].effect.random[1] - G.flora[m.f].effect.random[0] + 1)) : 0;
      lane[side].push({ s: m.s, f: m.f, rnd: rnd });
      S[side].hand.splice(S[side].hand.indexOf(m.s), 1);
      if (m.f !== null) S[side].flora.splice(S[side].flora.indexOf(m.f), 1);
      S.placed[side]++;
      var P = laneP(lane, 'you', null), i = lane[side].length - 1, pw = P[side][i];
      var vars = { who: who(side), name: sName(m.s), terrain: tName(lane.sq[side].t), power: pw === null ? msg('hidden') : pw, flora: m.f !== null ? fName(m.f) : '' };
      say(msg(m.f !== null ? 'playedBase' : 'played', vars));
      void st;
      endTurn(side);
    }
    function pass(side) {
      S.passed[side] = true;
      say(msg('passed', { who: who(side) }));
      endTurn(side);
    }
    function endTurn(side) {
      if (!S[side].hand.length) S.passed[side] = true;
      if (S.passed.you && S.passed.ai) return resolve();
      S.turn = S.passed[OTHER[side]] ? side : OTHER[side];
      S.sel = null; S.selF = null;
      render();
      if (S.turn === 'ai') aiTurn();
      else focusFirst('.minari__hand button:not([disabled])');
    }
    function resolve() {
      var lanes = { you: 0, ai: 0 }, total = { you: 0, ai: 0 }, lines = [];
      S.board.forEach(function (lane, l) {
        lane.counted = true;
        if (!lane.you.length && !lane.ai.length) return;
        var P = laneP(lane);
        total.you += P.tYou; total.ai += P.tAi;
        var a = P.tAi, b = P.tYou;
        if (P.tYou === P.tAi) { lines.push(msg('laneTie', { n: l + 1, a: a, b: b })); return; }
        var win = P.tYou > P.tAi ? 'you' : 'ai', lose = OTHER[win];
        lanes[win]++;
        lines.push(msg(win === 'you' ? 'laneWinYou' : 'laneWin', { n: l + 1, who: who(win), a: Math.max(a, b), b: Math.min(a, b) }));
        lane[lose].forEach(function (p) {
          p.out = true;
          var hasStone = S[lose].stone === p.s;
          lines.push(msg('eliminated', { name: sName(p.s), result: msg(hasStone ? 'stoneYes' : 'stoneNo') }));
          if (hasStone) { S.found[win] = p.s; lines.push(msg(win === 'you' ? 'foundYou' : 'found', { who: who(win), name: sName(p.s) })); }
        });
      });
      var rw = lanes.you !== lanes.ai ? (lanes.you > lanes.ai ? 'you' : 'ai') : total.you !== total.ai ? (total.you > total.ai ? 'you' : 'ai') : null;
      if (rw) { S.wins[rw]++; lines.push(msg(rw === 'you' ? 'roundWinYou' : 'roundWin', { who: who(rw), n: S.round })); }
      else { S.wins.you++; S.wins.ai++; lines.push(msg('roundDraw', { n: S.round })); }
      var f = S.found;
      if (f.you !== null && f.ai !== null) S.over = 'draw';
      else if (f.you !== null) S.over = 'you';
      else if (f.ai !== null) S.over = 'ai';
      else if (S.wins.you >= R.roundsToWin || S.wins.ai >= R.roundsToWin || (!S.you.hand.length && !S.ai.hand.length) || S.round >= R.roundsToWin * 2 - 1) {
        S.over = S.wins.you === S.wins.ai ? 'draw' : S.wins.you > S.wins.ai ? 'you' : 'ai';
      }
      if (S.over) lines.push(S.over === 'you' ? msg('matchWin') : S.over === 'ai' ? msg('matchLose', { opp: oppName() }) : msg('matchDraw'));
      S.summary = lines;
      say(lines.join(' '), false);
      log = [];
      render();
      focusFirst('.minari__summary button');
    }

    // ---------------------------------------------------------------- the computer
    function aiStone() {
      var hand = S.ai.pool.slice().sort(function (a, b) { return G.statues[a].power - G.statues[b].power; });
      var lvl = oppOf(S.opp).level;
      if (lvl === 'easy') return hand[Math.floor(Math.random() * hand.length)];
      if (lvl === 'medium') return hand[Math.floor(hand.length / 2)];
      return hand[Math.floor(Math.random() * 3)]; // hard: a small statue she can keep back (and nobody suspects)
    }
    function evalBoard(lvl) {
      var sc = 0;
      S.board.forEach(function (lane) {
        if (!lane.you.length && !lane.ai.length) return;
        var P = laneP(lane, 'ai', 4);
        var stoneHere = lane.ai.some(function (p) { return p.s === S.ai.stone; });
        if (P.tAi > P.tYou) sc += 10 + lane.you.length * (lvl === 'hard' ? 3 : 2) + (lvl === 'hard' ? Math.min(3, P.tAi - P.tYou) * 0.3 : 0);
        else if (P.tAi < P.tYou) sc -= 10 + lane.ai.length * 2 + (stoneHere ? 80 : 0);
        else if (stoneHere) sc -= 20;
      });
      return sc;
    }
    function lanesLead() {
      var n = 0;
      S.board.forEach(function (lane) {
        if (!lane.you.length && !lane.ai.length) return;
        var P = laneP(lane, 'ai', 4);
        n += P.tAi > P.tYou ? 1 : P.tAi < P.tYou ? -1 : 0;
      });
      return n;
    }
    function tryMove(m, lvl) {
      var lane = S.board[m.l];
      var p = { s: m.s, f: m.f, rnd: m.f !== null && G.flora[m.f].effect.random ? (G.flora[m.f].effect.random[0] + G.flora[m.f].effect.random[1]) / 2 : 0 };
      lane.ai.push(p);
      var v = evalBoard(lvl);
      lane.ai.pop();
      var cost = lvl === 'hard' ? 1 + G.statues[m.s].power * 0.35 : 1.5;
      if (m.f !== null) cost += lvl === 'hard' ? 2.5 : 1.5;
      if (m.s === S.ai.stone) cost += lvl === 'hard' ? 12 : 6;
      return v - cost;
    }
    function aiChoose() {
      var lvl = oppOf(S.opp).level, moves = legal('ai');
      if (!moves.length) return null;
      if (lvl === 'easy') {
        if (S.passed.you && lanesLead() > 0) return null;
        if (S.placed.ai >= 2 && Math.random() < 0.12) return null;
        var plain = moves.filter(function (m) { return m.f === null; });
        var pool = Math.random() < 0.7 && plain.length ? plain : moves;
        return pool[Math.floor(Math.random() * pool.length)];
      }
      var now = evalBoard(lvl), best = null, bestScore = -Infinity;
      moves.forEach(function (m) {
        if (m.s === S.ai.stone && S.ai.hand.length > (lvl === 'hard' ? 2 : 3)) return; // keep the stone back
        var sc = tryMove(m, lvl);
        if (sc > bestScore) { bestScore = sc; best = m; }
      });
      if (!best) best = moves.filter(function (m) { return m.f === null; })[0] || moves[0], bestScore = tryMove(best, lvl);
      var gain = bestScore - now, lead = lanesLead();
      if (S.passed.you) return lead > 0 ? null : gain > 0 ? best : null;
      if (lvl === 'hard') {
        // save pieces: pass when ahead and the reader has spent more, or "dry pass" an early round she's losing badly
        if (lead >= 2 && S.ai.hand.length <= S.you.hand.length) return null;
        if (S.wins.ai > S.wins.you && lead > 0) return null;
        if (S.round === 1 && S.placed.you - S.placed.ai >= 3 && lead < -1) return null;
        return gain > -4 ? best : null;
      }
      if (lead >= 2 && S.ai.hand.length < S.you.hand.length) return null;
      return gain > -3 ? best : null;
    }
    function aiTurn() {
      render();
      window.setTimeout(function () {
        if (S.setup || S.summary || S.turn !== 'ai') return;
        var m = aiChoose();
        if (m) play('ai', m); else pass('ai');
      }, reduced ? 200 : 750);
    }

    // ---------------------------------------------------------------- drawing
    function statueToken(i, opts) {
      opts = opts || {};
      var st = G.statues[i];
      var kids = [
        st.img ? el('img', { src: st.img, alt: '', loading: 'lazy', width: 48, height: 48 }) : el('span', { class: 'minari__blank', 'aria-hidden': 'true' }),
        el('b', { class: 'minari__pw', text: opts.power !== undefined ? String(opts.power) : String(st.power) }),
        el('span', { class: 'minari__nm', text: sName(i) })
      ];
      if (opts.stone) kids.push(el('span', { class: 'minari__gem', title: msg('stoneMark'), 'aria-hidden': 'true' }));
      return el('span', { class: 'minari__statue' + (opts.painted ? ' is-painted' : '') + (opts.out ? ' is-out' : '') }, kids);
    }
    function statueInfo(i) {
      var st = G.statues[i];
      var tr = st.traits.map(function (t) { return msg(t) + ' (' + msg(t + 'Help') + ')'; });
      return msg('statueInfo', { name: sName(i), kind: msg('kind_' + st.kind), power: st.power,
        terrains: st.homes.map(tName).join(', '), traits: tr.length ? '; ' + tr.join(', ') : '' });
    }
    function rowKeys(e) {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].indexOf(e.key) < 0) return;
      var btns = Array.prototype.slice.call(e.currentTarget.querySelectorAll('button:not([disabled])'));
      var i = btns.indexOf(document.activeElement);
      if (i < 0) return;
      e.preventDefault();
      var rtl = getComputedStyle(root).direction === 'rtl';
      var step = (e.key === 'ArrowRight' || e.key === 'ArrowDown') !== rtl ? 1 : -1;
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') step = e.key === 'ArrowDown' ? 1 : -1;
      btns[(i + step + btns.length) % btns.length].focus();
    }
    function focusFirst(sel) {
      if (!root.contains(document.activeElement) && document.activeElement !== document.body) return;
      var b = app.querySelector(sel);
      if (b) b.focus({ preventScroll: true });
    }
    function render() {
      var keep = document.activeElement && root.contains(document.activeElement) ? document.activeElement.getAttribute('data-focus') : null;
      app.textContent = '';
      app.appendChild(S.setup ? renderSetup() : renderTable());
      if (keep) { var f = app.querySelector('[data-focus="' + keep + '"]'); if (f && !f.disabled) f.focus({ preventScroll: true }); }
    }

    function renderSetup() {
      var opps = el('div', { class: 'minari__opps', role: 'group', 'aria-label': msg('pickOpponent'), onkeydown: rowKeys },
        G.opponents.map(function (o) {
          return el('button', { type: 'button', class: 'minari__opp', 'aria-pressed': String(S.opp === o.id), 'data-focus': 'opp-' + o.id,
            onclick: function () { S.opp = o.id; render(); } }, [
            o.img ? el('img', { src: o.img, alt: '', width: 56, height: 56, loading: 'lazy' }) : null,
            el('strong', { text: msg('o_' + o.id) }), el('span', { text: msg('lv_' + o.level) })]);
        }));
      var bat = el('div', { class: 'minari__pool', role: 'group', 'aria-label': msg('hideStone'), onkeydown: rowKeys },
        S.you.pool.map(function (i) {
          return el('button', { type: 'button', class: 'minari__pick', 'aria-pressed': String(S.you.stone === i), 'data-focus': 'pool-' + i,
            'aria-label': statueInfo(i) + (S.you.stone === i ? '. ' + msg('stoneHidden') : ''), title: statueInfo(i),
            onclick: function () { S.you.stone = i; say(msg('stoneIn', { name: sName(i) })); render(); } },
            [statueToken(i, { painted: S.paint, stone: S.you.stone === i })]);
        }));
      var floraRow = el('ul', { class: 'minari__flora-list' }, S.you.flora.map(function (f) {
        return el('li', {}, [el('strong', { text: fName(f) }), ' ', el('span', { text: effectText(G.flora[f].effect) })]);
      }));
      return el('div', { class: 'minari__setup' }, [
        el('h3', { text: msg('pickOpponent') }), opps,
        el('h3', { text: msg('yourBattalion') }),
        el('p', { class: 'minari__hint', text: S.you.stone === null ? msg('hideStone') : msg('stoneIn', { name: sName(S.you.stone) }) }),
        bat,
        el('h3', { text: msg('bases') }), floraRow,
        el('div', { class: 'minari__setup-actions' }, [
          el('button', { type: 'button', class: 'minari__btn', 'data-focus': 'reroll', onclick: function () { draft(S.you); say(msg('yourBattalion')); render(); } }, [msg('reroll')]),
          el('label', { class: 'minari__paint' }, [el('input', { type: 'checkbox', checked: S.paint, 'data-focus': 'paint', onchange: function (e) { S.paint = e.target.checked; render(); } }), ' ' + msg('paint')]),
          el('button', { type: 'button', class: 'minari__btn minari__btn--main', 'data-focus': 'start', onclick: function () {
            if (S.you.stone === null) { say(msg('needStone')); return; }
            startMatch();
          } }, [msg('start')])
        ])
      ]);
    }

    function squareEl(lane, l, side) {
      var sq = lane.sq[side], t = TERR[sq.t];
      var P = laneP(lane, 'you', null);
      var pieces = lane[side].map(function (p, i) {
        var hidden = P[side][i] === null;
        var mine = side === 'you';
        var tok = statueToken(p.s, { power: hidden ? msg('hidden') : P[side][i], painted: mine && S.paint,
          stone: mine && S.you.stone === p.s || (p.out && S[side].stone === p.s), out: p.out });
        var label = msg('statueOn', { name: sName(p.s), power: hidden ? msg('hidden') : P[side][i] }) +
          (p.f !== null ? ', ' + msg('withBase', { flora: fName(p.f) }) : '') + (p.out ? ', ' + msg('out') : '');
        return el('li', { class: 'minari__piece' + (p.f !== null ? ' has-base' : ''), title: p.f !== null ? fName(p.f) + ': ' + effectText(G.flora[p.f].effect) : null },
          [el('span', { class: 'minari__sr', text: label }), tok, p.f !== null ? el('span', { class: 'minari__base', 'aria-hidden': 'true', text: fName(p.f) }) : null]);
      });
      var head = el('span', { class: 'minari__sq-label', text: msg('square', { terrain: tName(sq.t), h: sq.h }) });
      var body = [head, el('ul', { class: 'minari__pieces' }, pieces)];
      var style = '--sq:' + t.color + ';--h:' + sq.h;
      if (side === 'you' && !S.summary) {
        var can = S.turn === 'you' && S.sel !== null && lane.you.length < R.statuesPerSquare;
        return el('button', { type: 'button', class: 'minari__sq minari__sq--you', style: style, disabled: !can, 'data-focus': 'sq-' + l,
          'aria-label': msg('laneLabel', { n: l + 1 }) + ': ' + msg('square', { terrain: tName(sq.t), h: sq.h }),
          onclick: function () {
            if (lane.you.length >= R.statuesPerSquare) { say(msg('full')); return; }
            play('you', { s: S.sel, l: l, f: S.selF });
          } }, body);
      }
      return el('div', { class: 'minari__sq', style: style, role: 'group', 'aria-label': msg('laneLabel', { n: l + 1 }) + ': ' + msg('square', { terrain: tName(sq.t), h: sq.h }) }, body);
    }

    function renderTable() {
      var opp = oppOf(S.opp);
      var status = el('div', { class: 'minari__status' }, [
        el('strong', { text: msg('round', { n: S.round }) }),
        el('span', { text: msg('score', { you: S.wins.you, opp: oppName(), them: S.wins.ai }) }),
        el('a', { href: G.regions[S.region].lore, text: msg('field', { region: msg('r_' + S.region) }) })
      ]);
      var theirs = el('div', { class: 'minari__row minari__row--ai' }, S.board.map(function (lane, l) { return squareEl(lane, l, 'ai'); }));
      var totals = el('div', { class: 'minari__row minari__totals', 'aria-hidden': 'true' }, S.board.map(function (lane) {
        var P = laneP(lane, 'you', null);
        return el('span', { title: oppName() + ' : ' + msg('you'), text: msg('laneTotals', { a: P.hidden.ai ? msg('hidden') : P.tAi, b: P.tYou }) });
      }));
      var mine = el('div', { class: 'minari__row minari__row--you', onkeydown: rowKeys }, S.board.map(function (lane, l) { return squareEl(lane, l, 'you'); }));
      var board = el('div', { class: 'minari__board' }, [
        el('p', { class: 'minari__side', text: msg('theirSide', { opp: oppName() }) }), theirs, totals, mine,
        el('p', { class: 'minari__side', text: msg('yourSide') })]);
      var parts = [el('div', { class: 'minari__top' }, [
        opp.img ? el('img', { class: 'minari__opp-pic', src: opp.img, alt: '', width: 44, height: 44 }) : null, status]), board];
      if (S.summary) {
        parts.push(el('div', { class: 'minari__summary' }, [
          el('ul', {}, S.summary.map(function (t) { return el('li', { text: t }); })),
          el('button', { type: 'button', class: 'minari__btn minari__btn--main', 'data-focus': 'next', onclick: function () {
            if (S.over) { S.setup = true; draft(S.you); render(); focusFirst('.minari__opp'); } else nextRound();
          } }, [S.over ? msg('again') : msg('nextRound')])]));
        return el('div', { class: 'minari__table' }, parts);
      }
      var yourTurn = S.turn === 'you';
      var hand = el('div', { class: 'minari__hand', role: 'group', 'aria-label': msg('hand'), onkeydown: rowKeys },
        S.you.hand.length ? S.you.hand.map(function (i) {
          return el('button', { type: 'button', class: 'minari__pick', 'aria-pressed': String(S.sel === i), disabled: !yourTurn, 'data-focus': 'hand-' + i,
            'aria-label': statueInfo(i) + (S.you.stone === i ? '. ' + msg('stoneHidden') : ''), title: statueInfo(i),
            onclick: function () { S.sel = S.sel === i ? null : i; if (S.sel !== null) say(msg('pickSquare', { name: sName(i) }), false); render(); } },
            [statueToken(i, { painted: S.paint, stone: S.you.stone === i })]);
        }) : [el('p', { text: msg('empty') })]);
      var bases = el('div', { class: 'minari__bases', role: 'group', 'aria-label': msg('bases'), onkeydown: rowKeys },
        [el('button', { type: 'button', class: 'minari__base-btn', 'aria-pressed': String(S.selF === null), disabled: !yourTurn, 'data-focus': 'base-none',
          onclick: function () { S.selF = null; render(); } }, [msg('noBase')])].concat(S.you.flora.map(function (f) {
          return el('button', { type: 'button', class: 'minari__base-btn', 'aria-pressed': String(S.selF === f), disabled: !yourTurn, 'data-focus': 'base-' + f,
            title: effectText(G.flora[f].effect), 'aria-label': msg('baseInfo', { name: fName(f), effect: effectText(G.flora[f].effect) }),
            onclick: function () { S.selF = S.selF === f ? null : f; render(); } }, [
            G.flora[f].img ? el('img', { src: G.flora[f].img, alt: '', width: 28, height: 28, loading: 'lazy' }) : null, fName(f)]);
        })));
      var turnLine = yourTurn ? (S.sel === null ? msg('yourTurn') : msg('pickSquare', { name: sName(S.sel) })) : msg('oppTurn', { opp: oppName() });
      parts.push(el('p', { class: 'minari__turn', text: turnLine }));
      parts.push(el('h3', { class: 'minari__h', text: msg('hand') }), hand, el('h3', { class: 'minari__h', text: msg('bases') }), bases);
      parts.push(el('div', { class: 'minari__actions' }, [el('button', { type: 'button', class: 'minari__btn', disabled: !yourTurn, 'data-focus': 'pass',
        onclick: function () { pass('you'); } }, [msg('pass')])]));
      parts.push(el('ol', { class: 'minari__log', 'aria-hidden': 'true' }, log.map(function (t) { return el('li', { text: t }); })));
      return el('div', { class: 'minari__table' }, parts);
    }

    render();
  });
})();

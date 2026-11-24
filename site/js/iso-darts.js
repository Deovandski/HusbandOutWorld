// Iso darts (reusable component): an "on-rails" darts scene in an isometric room. A script of speech
// bubbles walks the reader through the game; some lines trigger a step (a warm-up throw, a practice
// throw, the timed round where both players throw at once, the ending). The board is round, split into
// coloured territories: land a dart on one to claim it, land where the other player's dart is and both
// cancel, smaller territories are worth more. The reader's aim sways (more with every throw); the rival
// throws on their own. Built for Territory Snipping from Vol 2 (Lab Soreno), on the Playground page.
//
// Ported from Deovandski/Deovandski (src/components/reusable/IsoDarts.astro, the Board Games tab) for
// #128: same game, same rules, same strings; Astro + TypeScript turned into this script, the styles into
// site/css/iso-darts.css and the markup into iso_darts_html() in tools/build.py.
//
// Usage: iso_darts_html(game, title, uid) in tools/build.py writes
//   <div class="iso-darts" data-game='{"players":…,"dartsPerPlayer":10,"roundSeconds":25,"script":[…]}'>
//     <div class="iso-darts__strings" hidden><span data-k="you">Harry</span>…</div>  (every word it shows)
//     … the scene (SVG), the speech bubble, the HUD, the buttons, the live line, the legend
//   </div>
// and the page loads this script and site/css/iso-darts.css. Several on one page work.
// Options (data-game, JSON): players.you / players.rival ({ name, color, feather }), dartsPerPlayer,
// roundSeconds, script: [{ who: "you" | "rival", text, do? }] where `do` runs a step after the line:
// warmup, practice, hiromiMiss (the rival aims at green and misses), round or end.
// Words: the names, the script's lines and every message come from the hidden .iso-darts__strings block
// ({name} slots filled in here), so the site's translations reach them.
// Theme: --darts-accent, --darts-text, --darts-on-accent (see iso-darts.css).
// Accessible: Next, Throw! and Play again are buttons (Space or Enter throws); every line and every
// dart's result goes to an aria-live line. Reduced motion: no sway (the aim drifts slowly) and no spin.
(function () {
  var SVG = 'http://www.w3.org/2000/svg';
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The board: a circle split into coloured territories, like a baseball field spun into a full circle.
  // The tiny yellow centre is worth the most; the bigger the territory, the less it's worth.
  var RINGS = [
    { r0: 0, r1: 11, n: 1, colors: [['#f2c12e', 'yellow']], value: 10 },
    { r0: 11, r1: 32, n: 4, colors: [['#e8833a', 'orange'], ['#8e4fc7', 'purple'], ['#e8833a', 'orange'], ['#8e4fc7', 'purple']], value: 5 },
    { r0: 32, r1: 62, n: 8, colors: [['#3f9e4a', 'green'], ['#3a7bd5', 'blue'], ['#3f9e4a', 'green'], ['#c8443a', 'red'], ['#3f9e4a', 'green'], ['#3a7bd5', 'blue'], ['#3f9e4a', 'green'], ['#c8443a', 'red']], value: 3 },
    { r0: 62, r1: 100, n: 8, colors: [['#8e4fc7', 'purple'], ['#3f9e4a', 'green'], ['#e8833a', 'orange'], ['#3f9e4a', 'green'], ['#8e4fc7', 'purple'], ['#3f9e4a', 'green'], ['#e8833a', 'orange'], ['#3f9e4a', 'green']], value: 1 }
  ];
  var ZONES = [];
  RINGS.forEach(function (ring) {
    var step = (Math.PI * 2) / ring.n;
    var off = ring.n === 4 ? -Math.PI / 4 : -Math.PI / 2;
    for (var i = 0; i < ring.n; i++) {
      ZONES.push({ id: ZONES.length, color: ring.colors[i][0], name: ring.colors[i][1], value: ring.value,
        r0: ring.r0, r1: ring.r1, a0: off + i * step, a1: off + (i + 1) * step });
    }
  });
  function zoneAt(x, y) {
    var r = Math.hypot(x, y);
    if (r > 100) return null;
    var a = Math.atan2(y, x);
    for (var i = 0; i < ZONES.length; i++) {
      var z = ZONES[i];
      if (r < z.r0 || r >= z.r1) continue;
      if (z.r0 === 0) return z;
      var aa = a;
      while (aa < z.a0) aa += Math.PI * 2;
      while (aa >= z.a0 + Math.PI * 2) aa -= Math.PI * 2;
      if (aa < z.a1) return z;
    }
    return null;
  }
  function wedge(z) {
    if (z.r0 === 0) return '<circle r="' + z.r1 + '" fill="' + z.color + '" stroke="#2b1d16" stroke-width="1.5"/>';
    var p = function (r, a) { return (r * Math.cos(a)).toFixed(2) + ' ' + (r * Math.sin(a)).toFixed(2); };
    var large = z.a1 - z.a0 > Math.PI ? 1 : 0;
    return '<path d="M' + p(z.r0, z.a0) + ' L' + p(z.r1, z.a0) + ' A' + z.r1 + ' ' + z.r1 + ' 0 ' + large + ' 1 ' + p(z.r1, z.a1) +
      ' L' + p(z.r0, z.a1) + ' A' + z.r0 + ' ' + z.r0 + ' 0 ' + large + ' 0 ' + p(z.r0, z.a0) + 'Z" fill="' + z.color + '" stroke="#2b1d16" stroke-width="1.5"/>';
  }
  function center(z) {
    if (z.r0 === 0) return { x: 0, y: 0 };
    var a = (z.a0 + z.a1) / 2, r = (z.r0 + z.r1) / 2;
    return { x: r * Math.cos(a), y: r * Math.sin(a) };
  }
  function gauss() { return (Math.random() + Math.random() + Math.random() - 1.5) / 1.5; }

  document.querySelectorAll('.iso-darts[data-game]').forEach(function (root) {
    var game = JSON.parse(root.dataset.game);
    var $ = function (sel) { return root.querySelector(sel); };
    // The page's (possibly translated) words; {name} slots are filled in here.
    function msg(key, vars) {
      vars = vars || {};
      var el = root.querySelector('.iso-darts__strings [data-k="' + key + '"]');
      return (el ? el.textContent : key).replace(/\{(\w+)\}/g, function (m, k) { return k in vars ? String(vars[k]) : m; });
    }
    var P = game.players;
    P.you.name = msg('you');
    P.rival.name = msg('rival');
    game.script.forEach(function (s, i) { s.text = msg('line' + i); });
    var pts = function (n) { return msg(n === 1 ? 'pt' : 'pts', { n: n }); };

    var scene = $('.iso-darts__scene'), boardG = $('.iso-darts__board'), dartsG = $('.iso-darts__darts');
    var reticle = $('.iso-darts__reticle'), bubble = $('.iso-darts__bubble'), whoEl = $('.iso-darts__who');
    var lineEl = $('.iso-darts__line'), hud = $('.iso-darts__hud'), clock = $('.iso-darts__clock');
    var tally = $('.iso-darts__tally'), next = $('.iso-darts__next'), throwBtn = $('.iso-darts__throw');
    var restart = $('.iso-darts__restart'), live = $('.iso-darts__live'), legend = $('.iso-darts__legend');

    boardG.innerHTML = ZONES.map(wedge).join('');
    legend.innerHTML = RINGS.map(function (r) {
      var k = r.n === 1 ? 'ringCentre' : r.r1 <= 32 ? 'ringInner' : r.r1 <= 62 ? 'ringMiddle' : 'ringOuter';
      return '<div><dt>' + msg(k) + '</dt><dd>' + pts(r.value) + '</dd></div>';
    }).join('');

    var step = -1, darts = [], mode = 'talk', left = { you: 0, rival: 0 }, sway = 10;
    var t0 = 0, endsAt = 0, rivalTimer = 0, aim = { x: 0, y: 0 }, raf = 0;

    function drawDart(d) {
      var pl = P[d.who];
      var g = document.createElementNS(SVG, 'g');
      g.setAttribute('transform', 'translate(' + d.x.toFixed(1) + ' ' + d.y.toFixed(1) + ')');
      g.innerHTML = '<line x1="0" y1="0" x2="10" y2="-10" stroke="#ccc" stroke-width="2.5"/><path d="M8 -8 l8 -2 l-2 8z" fill="' + pl.feather +
        '" stroke="' + pl.color + '" stroke-width="2"/><circle r="2.5" fill="' + pl.color + '"/>';
      dartsG.appendChild(g);
      d.el = g;
    }
    // A dart lands: claim the territory, or cancel against the other player's dart there.
    function land(who, x, y, quiet) {
      var z = zoneAt(x, y);
      if (!z) {
        if (!quiet) live.textContent = msg('bounced', { player: P[who].name });
        return;
      }
      var other = darts.find(function (d) { return d.zone === z.id && d.who !== who; });
      if (other) {
        if (other.el) other.el.remove();
        darts = darts.filter(function (d) { return d !== other; });
        if (!quiet) live.textContent = msg('cancelled', { colour: msg(z.name) });
        var puff = document.createElementNS(SVG, 'circle'); // a quick puff where they cancelled
        puff.setAttribute('cx', String(x)); puff.setAttribute('cy', String(y));
        puff.setAttribute('r', '6'); puff.setAttribute('fill', '#fff'); puff.setAttribute('opacity', '0.8');
        dartsG.appendChild(puff);
        window.setTimeout(function () { puff.remove(); }, 350);
        renderTally();
        return;
      }
      var d = { x: x, y: y, who: who, zone: z.id };
      darts.push(d);
      drawDart(d);
      if (!quiet) live.textContent = msg('snipes', { player: P[who].name, colour: msg(z.name), points: pts(z.value) });
      renderTally();
    }
    function scores() {
      var s = { you: 0, rival: 0 }, owned = new Map();
      darts.forEach(function (d) { if (d.zone !== null) owned.set(d.zone, d.who); });
      owned.forEach(function (who, id) { s[who] += ZONES[id].value; });
      return s;
    }
    function renderTally() {
      var s = scores();
      tally.textContent = P.you.name + ' ' + s.you + ' · ' + P.rival.name + ' ' + s.rival;
    }
    function say(s) {
      bubble.dataset.who = s.who;
      whoEl.textContent = P[s.who].name;
      whoEl.style.setProperty('--who', s.who === 'you' ? '#f4a3a8' : P.rival.color);
      lineEl.textContent = s.text;
      live.textContent = P[s.who].name + ': ' + s.text;
    }

    // The aim drifts in a figure-eight that grows with every throw (Harry has had a lot to drink).
    function moveAim(now) {
      var t = (now - t0) / 1000;
      var amp = reduced ? Math.min(sway, 30) : sway;
      var speed = reduced ? 0.35 : 1;
      aim = { x: Math.sin(t * 1.7 * speed) * amp * 2.2 + Math.sin(t * 0.6 * speed) * amp * 0.6, y: Math.sin(t * 2.3 * speed + 1) * amp * 1.6 };
      reticle.setAttribute('transform', 'translate(' + aim.x.toFixed(1) + ' ' + aim.y.toFixed(1) + ')');
      if (mode === 'round') {
        var secs = Math.max(0, Math.ceil((endsAt - now) / 1000));
        clock.textContent = msg('clock', { seconds: secs, you: P.you.name, youLeft: left.you, rival: P.rival.name, rivalLeft: left.rival });
        if (now >= endsAt || (left.you === 0 && left.rival === 0)) return finishRound();
      }
      if (mode === 'practice' || mode === 'round') raf = requestAnimationFrame(moveAim);
    }
    function startAim() {
      reticle.setAttribute('visibility', 'visible');
      throwBtn.hidden = false;
      next.hidden = true;
      t0 = performance.now();
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(moveAim);
      throwBtn.focus({ preventScroll: true });
    }
    function stopAim() {
      cancelAnimationFrame(raf);
      reticle.setAttribute('visibility', 'hidden');
      throwBtn.hidden = true;
      next.hidden = false;
      next.focus({ preventScroll: true });
    }
    function throwDart() {
      if (mode === 'practice') {
        // As in the book: the first one flies low and lodges below the board.
        land('you', aim.x * 0.3, 112 + Math.random() * 10);
        live.textContent = msg('low');
        mode = 'talk';
        stopAim();
        return;
      }
      if (mode !== 'round' || left.you <= 0) return;
      left.you--;
      land('you', aim.x + gauss() * 6, aim.y + gauss() * 6);
      sway += 3.5;
      if (left.you === 0) throwBtn.disabled = true;
    }
    // Hiromi throws on his own, fast and sweaty, going for the valuable territories.
    function rivalThrow() {
      if (mode !== 'round' || left.rival <= 0) return;
      left.rival--;
      var targets = ZONES.filter(function (z) { return !darts.some(function (d) { return d.zone === z.id && d.who === 'rival'; }); });
      var weights = targets.map(function (z) { return z.value * (darts.some(function (d) { return d.zone === z.id && d.who === 'you'; }) ? 1.6 : 1); });
      var r = Math.random() * weights.reduce(function (a, b) { return a + b; }, 0);
      var pick = targets[0];
      for (var i = 0; i < targets.length; i++) {
        r -= weights[i];
        if (r <= 0) { pick = targets[i]; break; }
      }
      var c = center(pick);
      land('rival', c.x + gauss() * 26, c.y + gauss() * 26);
      rivalTimer = window.setTimeout(rivalThrow, 900 + Math.random() * 900);
    }
    function finishRound() {
      mode = 'talk';
      window.clearTimeout(rivalTimer);
      stopAim();
      throwBtn.disabled = false;
      live.textContent = msg('time');
      if (!reduced) {
        scene.classList.remove('is-spinning');
        void scene.getBoundingClientRect();
        scene.classList.add('is-spinning');
      }
    }

    var actions = {
      warmup: function () {
        // First dart clings, then falls to the ground; the second lands on a green near the centre.
        land('rival', 40, 104, true);
        window.setTimeout(function () {
          var g = dartsG.lastElementChild;
          if (g) g.remove();
          darts = darts.filter(function (d) { return d.el !== g; });
          land('rival', 18, -40, true);
          live.textContent = msg('warmup');
        }, 600);
      },
      practice: function () {
        mode = 'practice';
        sway = 18;
        live.textContent = msg('yourTurn');
        startAim();
      },
      hiromiMiss: function () {
        land('rival', 20, -85, true);
        live.textContent = msg('miss');
      },
      round: function () {
        // Clear the practice darts; both players throw at once until the darts or the time run out.
        darts.forEach(function (d) { if (d.el) d.el.remove(); });
        darts = [];
        mode = 'round';
        left = { you: game.dartsPerPlayer, rival: game.dartsPerPlayer };
        sway = 12;
        hud.hidden = false;
        endsAt = performance.now() + game.roundSeconds * 1000;
        renderTally();
        startAim();
        rivalTimer = window.setTimeout(rivalThrow, 500);
      },
      end: function () {
        var s = scores();
        var verdict = s.you > s.rival ? msg('youWin', { you: P.you.name }) : s.you === s.rival ? msg('draw') : msg('rivalWins', { rival: P.rival.name });
        var v = { you: P.you.name, youScore: s.you, rival: P.rival.name, rivalScore: s.rival, verdict: verdict };
        live.textContent = msg('finalLive', v);
        tally.textContent = msg('finalTally', v);
        next.hidden = true;
        restart.hidden = false;
        mode = 'done';
        restart.focus({ preventScroll: true });
      }
    };

    function advance() {
      if (mode === 'practice' || mode === 'round') return;
      step++;
      var s = game.script[step];
      if (!s) return;
      say(s);
      if (s.do && actions[s.do]) actions[s.do]();
      if (step >= game.script.length - 1 && s.do !== 'end') next.hidden = true;
    }

    next.addEventListener('click', advance);
    throwBtn.addEventListener('click', throwDart);
    root.addEventListener('keydown', function (ev) {
      if ((ev.key === ' ' || ev.key === 'Enter') && (mode === 'practice' || mode === 'round') && ev.target !== throwBtn) {
        ev.preventDefault();
        throwDart();
      }
    });
    restart.addEventListener('click', function () {
      darts.forEach(function (d) { if (d.el) d.el.remove(); });
      darts = [];
      hud.hidden = true;
      restart.hidden = true;
      next.hidden = false;
      step = -1;
      mode = 'talk';
      advance();
      next.focus();
    });
    advance();
  });
})();

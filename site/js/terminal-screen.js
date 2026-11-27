// Terminal screen (reusable component): an old-school computer terminal (green phosphor on black, amber headings)
// that types its text out one character at a time, fast, the way old PCs filled the screen. Built for the
// "Stats for nerds" page (/debug/, #146).
// Ported from Deovandski/Deovandski-repo-template (src/components/reusable/TerminalScreen.astro, template#19):
// same classes, events and timing.
//
// Usage: terminal_screen_html(inner_html, label=, title=, duration=, wait=) in tools/build.py writes
//   <div role="region" dir="ltr" class="terminal" data-terminal data-duration="1800" [data-wait] aria-label="…">
//     <div class="terminal__bar" aria-hidden="true" translate="no">… title …</div>
//     <div class="terminal__screen" translate="no" tabindex="0"> lines … <span class="terminal__cursor"></span></div>
//   </div>
// and the page loads this script and site/css/terminal-screen.css. Several on one page work.
// Content: each direct child of the screen is one line, revealed in order; its text is typed. Classes: .term-h
// (amber heading), .term-row with .term-k (key) and .term-v (value), .term-dim, .term-hi, .term-amber, .term-warn,
// .term-gap (an empty line), .term-bar (a bar of characters), .term-pre (keeps spaces). Links keep working.
// Options (data attributes): data-duration (about how long the whole text takes, in ms; default 1800),
// data-wait (don't start by itself: wait for a `terminal:start` event).
// Events (on the element): `terminal:start` (types it, again if already typed), `terminal:done` (typing ended).
// Click, tap or any key while it types shows everything at once. Reduced motion: all at once, no blinking cursor.
// While typing, aria-busy="true" tells screen readers to wait for the full text. Always left to right, and
// translate="no": it's machine output, like code.
// Theme: --term-bg, --term-ink, --term-dim, --term-amber, --term-warn, --term-font, --term-size, --term-key.
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  function setup(root) {
    var screen = root.querySelector('.terminal__screen');
    var cursor = screen.querySelector('.terminal__cursor');
    var stop = null;

    function start() {
      if (stop) stop();
      var lines = Array.prototype.filter.call(screen.children, function (el) { return el !== cursor; });
      // Every text node of every line, with its full text kept aside.
      var texts = lines.map(function (line) {
        var w = document.createTreeWalker(line, NodeFilter.SHOW_TEXT), nodes = [];
        for (var n = w.nextNode(); n; n = w.nextNode()) nodes.push({ node: n, full: n.data });
        return nodes;
      });
      var flat = [].concat.apply([], texts);
      var total = flat.reduce(function (sum, t) { return sum + t.full.length; }, 0);
      function finish() {
        flat.forEach(function (t) { t.node.data = t.full; });
        lines.forEach(function (l) { l.removeAttribute('data-term-hidden'); });
        screen.appendChild(cursor);
        root.removeAttribute('data-typing');
        root.removeAttribute('aria-busy');
        stop = null;
        root.dispatchEvent(new CustomEvent('terminal:done'));
      }
      if (reduce.matches || total === 0) return finish();

      root.setAttribute('data-typing', '');
      root.setAttribute('aria-busy', 'true');
      flat.forEach(function (t) { t.node.data = ''; });
      lines.forEach(function (l) { l.setAttribute('data-term-hidden', ''); });
      var duration = Number(root.dataset.duration) || 1800;
      var line = 0, node = 0, raf = 0, last = performance.now(), budget = 0;
      var perMs = Math.max(total / duration, 0.06);
      function step(now) {
        budget += (now - last) * perMs;
        last = now;
        while (budget >= 1 && line < lines.length) {
          lines[line].removeAttribute('data-term-hidden');
          var t = texts[line][node];
          if (!t) { line++; node = 0; continue; } // a line with no (more) text: next line
          var take = Math.min(Math.floor(budget), t.full.length - t.node.data.length);
          t.node.data = t.full.slice(0, t.node.data.length + take);
          budget -= take;
          t.node.parentNode.insertBefore(cursor, t.node.nextSibling);
          if (t.node.data.length === t.full.length) node++;
        }
        if (line >= lines.length) return finish();
        raf = requestAnimationFrame(step);
      }
      raf = requestAnimationFrame(step);
      stop = function () { cancelAnimationFrame(raf); finish(); };
    }

    // Show everything at once: click, tap or any key while it types.
    function skip() { if (root.hasAttribute('data-typing') && stop) stop(); }
    screen.addEventListener('click', skip);
    window.addEventListener('keydown', function (e) { if (!e.metaKey && !e.ctrlKey && !e.altKey) skip(); });
    root.addEventListener('terminal:start', start);
    if (!root.hasAttribute('data-wait')) start();
  }

  document.querySelectorAll('[data-terminal]').forEach(setup);
})();

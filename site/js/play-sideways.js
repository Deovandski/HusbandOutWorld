// Play sideways (reusable component): wraps a game that needs a wide screen. On a phone held upright it
// shows "Turn your phone sideways to play" instead of the game, and the game appears as soon as the phone
// is sideways. Where the browser can (Android), "Play full screen" goes full screen and locks the screen
// sideways; "Play upright instead" shows the game as it is. Desktops, tablets and phones held sideways
// see the game straight away.
// Adapted from Deovandski/Deovandski (src/components/GimmickPlay.astro, its "turn your phone sideways"
// screen) for #128, without the tab and FastTab parts that only that site has.
//
// Usage: play_sideways_html(title, inner_html) in tools/build.py writes
//   <div class="play-sideways">
//     <div class="play-sideways__gate" role="group" aria-label="…: turn your phone sideways" hidden>
//       … icon, title, "Turn your phone sideways to play." …
//       <button type="button" class="play-sideways__full" hidden>Play full screen</button>
//       <button type="button" class="play-sideways__upright">Play upright instead</button>
//     </div>
//     <div class="play-sideways__game"> the game </div>
//   </div>
// and the page loads this script and site/css/play-sideways.css. Several on one page work; each has its
// own gate. All its words are in the markup, so the translations cover them.
// Theme: --sideways-accent, --sideways-muted, --sideways-bg (the full-screen background).
// Accessible: real buttons, focus moves to the gate's first button and back to the game; no animation.
(function () {
  var phoneUpright = window.matchMedia('(pointer: coarse) and (orientation: portrait) and (max-width: 600px)');
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.play-sideways'));
  if (!boxes.length) return;

  function canLock() {
    return !!(screen.orientation && typeof screen.orientation.lock === 'function' &&
              typeof document.documentElement.requestFullscreen === 'function');
  }
  function update(box, moveFocus) {
    var gate = box.querySelector('.play-sideways__gate');
    var game = box.querySelector('.play-sideways__game');
    var waiting = phoneUpright.matches && !box.dataset.upright && document.fullscreenElement !== box;
    var was = !gate.hidden;
    gate.hidden = !waiting;
    game.hidden = waiting;
    if (!moveFocus || was === waiting) return;
    var target = waiting ? gate.querySelector('button:not([hidden])') : game.querySelector('button:not([hidden]), [tabindex]');
    if (target && box.contains(document.activeElement)) target.focus({ preventScroll: true });
  }

  boxes.forEach(function (box) {
    var full = box.querySelector('.play-sideways__full');
    var upright = box.querySelector('.play-sideways__upright');
    if (full) {
      full.hidden = !canLock();
      full.addEventListener('click', function () {
        box.requestFullscreen({ navigationUI: 'hide' })
          .then(function () { return screen.orientation.lock('landscape'); })
          .then(function () { update(box, true); })
          .catch(function () {
            // No full screen or no lock here: keep waiting for the phone to turn.
            if (document.fullscreenElement === box) document.exitFullscreen().catch(function () {});
            full.hidden = true;
            update(box, true);
          });
      });
    }
    upright.addEventListener('click', function () {
      box.dataset.upright = '1';
      update(box, true);
    });
    update(box, false);
  });

  var onChange = function () { boxes.forEach(function (b) { update(b, true); }); };
  if (phoneUpright.addEventListener) phoneUpright.addEventListener('change', onChange);
  else if (phoneUpright.addListener) phoneUpright.addListener(onChange);
  document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement) {
      try { screen.orientation.unlock(); } catch (e) { /* not supported */ }
    }
    onChange();
  });
})();

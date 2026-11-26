// Install app (reusable component): an "Install app" button for a site that's installable (a web app manifest and
// a service worker; see tools/pwa.py). It shows the button only when the browser can install the site right now
// (Chrome, Edge, Samsung Internet), and otherwise a short line on how to get there: "Open this page in Chrome" on
// Android (links opened from WhatsApp, Instagram or Gmail land in a viewer with no install option), "Share, then
// Add to Home Screen" on iPhone and iPad, and which browsers can install it anywhere else. Inside the installed app
// it says so. Built for the Settings menu (#144).
// Ported from Deovandski/Deovandski (src/components/reusable/InstallApp.astro, #292/#293): same behaviour and words.
//
// Usage: install_app_html() in tools/build.py writes
//   <div class="install-app" data-install-app>
//     <span class="install-app__strings" hidden><span data-k="install">Install app</span>…</span>
//     <button type="button" class="install-app__btn" hidden>…Install app</button>
//     <p class="install-app__note" aria-live="polite"></p>
//   </div>
//   <script> (keeps the browser's install offer, even if it comes before this script runs) </script>
// and every page loads this script and site/css/install-app.css. Several on one page work.
// Words (data-k): install, installed, done, android, ios, other. They live in the page, so the translations
// reach them. Nothing is saved.
// Accessible: a real button; the line under it is read out when it changes (aria-live); no animation.
// Theme: --install-accent, --install-ink (the button's text), --install-muted (see install-app.css).
(function () {
  var keep = function () { return window.__installAppPrompt; };
  var standalone = function () {
    return window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  };
  var ua = navigator.userAgent;
  var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var android = /Android/.test(ua);

  document.querySelectorAll('[data-install-app]').forEach(function (root) {
    var btn = root.querySelector('.install-app__btn');
    var note = root.querySelector('.install-app__note');
    var msg = function (k) {
      var s = root.querySelector('.install-app__strings [data-k="' + k + '"]');
      return s ? s.textContent : '';
    };
    // What to show: the button when the browser can install the site now, otherwise how to get there.
    function show() {
      if (standalone()) {
        btn.hidden = true;
        note.textContent = msg('installed');
      } else if (keep() && keep().event) {
        btn.hidden = false;
        note.textContent = '';
      } else {
        btn.hidden = true;
        note.textContent = msg(ios ? 'ios' : android ? 'android' : 'other');
      }
    }
    btn.addEventListener('click', function () {
      var e = keep() && keep().event;
      if (!e) return show();
      keep().event = null; // the offer can only be used once
      e.prompt();
      e.userChoice.then(function (choice) {
        if (choice.outcome === 'accepted') {
          btn.hidden = true;
          note.textContent = msg('done');
        } else show();
      });
    });
    document.addEventListener('install-app:ready', show);
    window.addEventListener('appinstalled', function () {
      btn.hidden = true;
      note.textContent = msg('done');
    });
    show();
  });
})();

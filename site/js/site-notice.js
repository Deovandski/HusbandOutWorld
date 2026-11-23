// Site notice (reusable component): a one-line message across the top of every page, with a × to
// dismiss it, shown until a date. Used for "the site moved to husbandoutworld.com" (#122).
//
// Usage: notice_html() in tools/build.py writes it from "notice" in content/site.json, and the page
// loads this script and site/css/site-notice.css:
//   <aside class="site-notice" role="note" data-notice-id="moved-2026-11" data-until="2027-03-01" hidden>
//     <p>Message text, links allowed.</p>
//     <button type="button" class="site-notice-close" aria-label="Dismiss">×</button>
//   </aside>
// Options (data attributes):
//   data-notice-id  required; a dismissed notice stays hidden on this device. Give a new notice a new id.
//   data-until      optional YYYY-MM-DD; the notice hides itself after that day.
// It starts hidden and this script shows it, so a dismissed notice never flashes. Several on one page
// work. The words (the message, "Dismiss") are in the markup, so the translations cover them.
// Dismissals are saved in localStorage under "site-notice:<id>" (nothing is sent anywhere).
// Accessible: role="note", a real button with a label, focus moves to the main content after dismissing.
// No animation. Theme with --notice-bg, --notice-ink, --notice-line, --notice-link (see site-notice.css).
(function () {
  var today = new Date().toISOString().slice(0, 10);
  document.querySelectorAll('.site-notice[data-notice-id]').forEach(function (el) {
    var key = 'site-notice:' + el.dataset.noticeId;
    var dismissed = false;
    try { dismissed = localStorage.getItem(key) === '1'; } catch (e) { /* storage blocked: show it */ }
    if (dismissed || (el.dataset.until && today > el.dataset.until)) return;
    el.hidden = false;
    var close = el.querySelector('.site-notice-close');
    if (close) close.addEventListener('click', function () {
      el.hidden = true;
      try { localStorage.setItem(key, '1'); } catch (e) { /* storage blocked: hidden for this page only */ }
      var main = document.getElementById('main');
      if (main) { main.setAttribute('tabindex', '-1'); main.focus({ preventScroll: true }); }
    });
  });
})();

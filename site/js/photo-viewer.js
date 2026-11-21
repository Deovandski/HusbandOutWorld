// Photo viewer (reusable component): every picture on the site opens bigger when pressed.
// Ported from Deovandski/Deovandski (src/components/reusable/PhotoViewer.astro); it replaces this site's
// old lightbox and keeps what it did (the Blog grid's captions, ‹ › through a data-gallery).
//
// Usage: photo_viewer_html() in tools/build.py writes the <dialog id="photo-viewer"> on every page, and
// every page loads this script and site/css/photo-viewer.css. Nothing else to wire up:
//   - <a class="img-link" href="big.webp" data-full="big.webp" [data-gallery="blog"] [data-caption="…"]>
//     (what the build writes around pictures) opens in the viewer; ‹ › step through its data-gallery.
//   - Any other content picture (an <img> with alt text) opens by itself: click, or Tab then Enter.
//   - Any other link straight to an image file opens in the viewer instead of leaving the page.
//   Without a data-gallery, ‹ › step through the other visible pictures on the page (or in the nearest
//   [data-zoom-group]).
//
// Skipped: decorative pictures (alt=""), pictures inside other links or buttons, the header and nav,
// dialogs, the webcomic reader (.wc-strip), pictures under 64px, and anything inside [data-no-zoom].
// data-zoom on an <img> forces it on.
//
// Caption: data-caption when the build wrote one (the Blog's already holds the date); otherwise the alt
// text, then the date when there is one: data-date="YYYY-MM-DD" (or data-date-label) on the link or
// picture, or a YYYY-MM-DD at the start of the file name. Dates are written in the page's language.
//
// Accessible: pictures that open get tabindex, role="button" and "Enlarge: …" (the word "Enlarge" sits
// in the dialog's markup, so translations cover it); Enter or Space opens; ← → move; Esc or × closes and
// focus goes back to the picture. Theme with --pv-bg, --pv-text, --pv-button (see photo-viewer.css).
(function () {
  var dlg = document.getElementById('photo-viewer');
  if (!dlg || typeof dlg.showModal !== 'function') return;
  var big = dlg.querySelector('.pv-fig img');
  var text = dlg.querySelector('.pv-text');
  var time = dlg.querySelector('.pv-date');
  var prev = dlg.querySelector('.pv-prev');
  var next = dlg.querySelector('.pv-next');
  var enlargeEl = dlg.querySelector('.pv-enlarge');
  var enlarge = (enlargeEl && enlargeEl.textContent.trim()) || 'Enlarge';
  var SKIP = 'a, button, header, nav, dialog, .wc-strip, [data-no-zoom]';
  var IMAGE_LINK = /\.(jpe?g|png|webp|avif|gif)(\?.*)?$/i;
  var items = [], at = 0, opener = null;

  function zoomableImg(img) {
    if (img.hasAttribute('data-zoom')) return true;
    if (!img.getAttribute('alt')) return false;
    if (img.closest(SKIP)) return false;
    var w = Number(img.getAttribute('width')) || img.naturalWidth || img.width;
    return !w || w >= 64;
  }
  function imageLink(a) {
    if (a.closest('[data-no-zoom]') || a.closest('.wc-strip')) return false;
    return a.classList.contains('img-link') || IMAGE_LINK.test(a.getAttribute('href') || '');
  }
  function fileDate(url) {
    var m = /(?:^|\/)(\d{4}-\d{2}-\d{2})[^\/]*$/.exec(String(url || '').split('?')[0]);
    return m ? m[1] : '';
  }
  function itemOf(el) {
    if (el.tagName === 'A') {
      var img = el.querySelector('img');
      var full = el.dataset.full || el.href;
      return { el: el, full: full, alt: (img && img.alt) || el.getAttribute('aria-label') || '', caption: el.dataset.caption || '',
        date: el.dataset.date || (img && img.dataset.date) || fileDate(full), dateLabel: el.dataset.dateLabel || '' };
    }
    var src = el.dataset.full || el.currentSrc || el.src;
    return { el: el, full: src, alt: el.alt, caption: '', date: el.dataset.date || fileDate(src), dateLabel: el.dataset.dateLabel || '' };
  }
  function groupOf(el) {
    if (el.dataset.gallery) return Array.prototype.slice.call(document.querySelectorAll('[data-gallery="' + el.dataset.gallery + '"]'));
    var scope = el.closest('[data-zoom-group]') || el.closest('main') || document.body;
    return Array.prototype.filter.call(scope.querySelectorAll('img, a[href]'), function (x) {
      var ok = x.tagName === 'IMG' ? zoomableImg(x) : imageLink(x);
      return ok && !x.dataset.gallery && (x === el || x.getClientRects().length > 0);
    });
  }
  function localDate(iso) {
    var p = iso.split('-').map(Number);
    try {
      return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(document.documentElement.lang || 'en', { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) { return iso; }
  }
  function show(i) {
    at = (i + items.length) % items.length;
    var it = items[at];
    big.src = it.full;
    big.alt = it.alt;
    // The build's caption already holds the date (the Blog's does), so it shows as is.
    var dateText = it.caption ? '' : (it.dateLabel || (it.date ? localDate(it.date) : ''));
    text.textContent = it.caption || it.alt;
    text.hidden = !text.textContent;
    time.textContent = dateText;
    time.hidden = !dateText;
    if (it.date && dateText) time.setAttribute('datetime', it.date); else time.removeAttribute('datetime');
  }
  function open(el) {
    var group = groupOf(el);
    if (group.indexOf(el) < 0) group = [el];
    items = group.map(itemOf);
    prev.hidden = next.hidden = items.length < 2;
    opener = el;
    show(group.indexOf(el));
    dlg.showModal();
  }
  function step(d) { if (items.length > 1) show(at + d); }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('#photo-viewer')) return;
    var a = t.closest('a[href]');
    if (a) {
      if (imageLink(a) && !e.metaKey && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); open(a); }
      return;
    }
    if (t.tagName === 'IMG' && zoomableImg(t)) open(t);
  });
  // Keyboard: content pictures become focusable buttons named "Enlarge: …".
  Array.prototype.forEach.call(document.querySelectorAll('img'), function (img) {
    if (!zoomableImg(img)) return;
    img.setAttribute('data-photo-viewer', '');
    img.tabIndex = 0;
    img.setAttribute('role', 'button');
    img.setAttribute('aria-label', enlarge + ': ' + img.alt);
  });
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if ((e.key === 'Enter' || e.key === ' ') && t.tagName === 'IMG' && t.hasAttribute('data-photo-viewer')) { e.preventDefault(); open(t); }
  });

  prev.addEventListener('click', function (e) { e.stopPropagation(); step(-1); });
  next.addEventListener('click', function (e) { e.stopPropagation(); step(1); });
  // Clicking anywhere else (the picture or the dark background) closes it, as the old lightbox did.
  dlg.addEventListener('click', function (e) { if (!e.target.closest('.pv-prev, .pv-next')) dlg.close(); });
  dlg.addEventListener('keydown', function (e) {
    var rtl = document.documentElement.dir === 'rtl';
    if (e.key === 'ArrowLeft') step(rtl ? 1 : -1);
    if (e.key === 'ArrowRight') step(rtl ? -1 : 1);
  });
  dlg.addEventListener('close', function () {
    big.removeAttribute('src');
    if (opener && opener.focus) opener.focus({ preventScroll: true });
    opener = null;
  });
})();

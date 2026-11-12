// #HusbandOutWorld webcomic: Webtoons-style reading (auto-hiding menus, progress, keyboard, resume where you left off).
(function () {
  'use strict';
  var root = document.documentElement;
  var BASE = root.dataset.base || '';
  var KEY = 'hoow-webcomic';
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
  function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode */ } }

  // ---------- landing page: "Continue" button and read markers
  var cont = document.querySelector('[data-wc-continue]');
  if (cont) {
    var s = load();
    if (s.last && s.last.url) {
      cont.hidden = false;
      cont.href = BASE + s.last.url + (s.last.slice > 1 ? '#s-' + s.last.slice : '');
      cont.textContent = 'Continue: ' + s.last.title;
      var start = document.querySelector('[data-wc-start]');
      if (start) start.textContent = 'Start from the beginning';
    }
    (s.done || []).forEach(function (u) {
      document.querySelectorAll('.ep-list a.ep-card[href="' + BASE + u + '"]').forEach(function (a) {
        a.classList.add('read');
        var st = document.createElement('span');
        st.className = 'ep-status'; st.textContent = 'Read';
        a.querySelector('.ep-text').appendChild(st);
      });
    });
  }

  // ---------- reader
  var strip = document.querySelector('.wc-strip');
  if (!strip) return;
  var topbar = document.querySelector('.topbar');
  var bar = document.querySelector('.wc-progress span');
  var title = (document.querySelector('.wc-title') || {}).textContent || document.title;
  var url = location.pathname.slice(BASE.length);
  var imgs = strip.querySelectorAll('img');

  function setTopbarH() { if (topbar) root.style.setProperty('--topbar-h', topbar.offsetHeight + 'px'); }
  setTopbarH();
  window.addEventListener('resize', setTopbarH);

  // menus hide while you scroll down into the comic and come back when you scroll up, tap, or reach either end
  var lastY = window.scrollY, ticking = false;
  function hide(h) { root.classList.toggle('wc-hide', h); }
  function onScroll() {
    ticking = false;
    var y = window.scrollY;
    var rect = strip.getBoundingClientRect();
    var total = rect.height - window.innerHeight;
    var done = Math.min(1, Math.max(0, -rect.top / (total > 0 ? total : 1)));
    if (bar) bar.style.width = (done * 100).toFixed(1) + '%';
    var inComic = rect.top < 0 && rect.bottom > window.innerHeight;
    if (!inComic) hide(false);
    else if (y > lastY + 6) hide(true);
    else if (y < lastY - 6) hide(false);
    lastY = y;
    remember(done);
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  strip.addEventListener('click', function () { hide(!root.classList.contains('wc-hide')); });

  // remember the episode and the slice you're on, so the Webcomic page can offer "Continue"
  var saveTimer = null;
  function remember(done) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      var mid = window.innerHeight / 2, n = 1;
      for (var i = 0; i < imgs.length; i++) { if (imgs[i].getBoundingClientRect().top <= mid) n = i + 1; else break; }
      var s = load();
      s.last = { url: url, title: title.trim(), slice: n };
      if (done > 0.97) { s.done = s.done || []; if (s.done.indexOf(url) < 0) s.done.push(url); }
      save(s);
    }, 300);
  }

  // keyboard: ← and → change episode (Space, Page Down and the arrow keys scroll as usual)
  document.addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || /input|textarea|select/i.test((e.target || {}).tagName || '')) return;
    if (e.key === 'ArrowRight' && strip.dataset.next) location.href = BASE + strip.dataset.next;
    if (e.key === 'ArrowLeft' && strip.dataset.prev) location.href = BASE + strip.dataset.prev;
  });

  // start loading the next stretch a little before it scrolls into view (lazy loading can be too lazy on fast flicks)
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var i = Array.prototype.indexOf.call(imgs, en.target);
        for (var k = i + 1; k <= i + 3 && k < imgs.length; k++) imgs[k].loading = 'eager';
        io.unobserve(en.target);
      });
    }, { rootMargin: '1200px 0px' });
    imgs.forEach(function (im) { io.observe(im); });
  }
  onScroll();
})();

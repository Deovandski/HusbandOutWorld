// #HusbandOutWorld website: mode switch, reading settings, search, lightbox.
(function () {
  'use strict';
  var root = document.documentElement;
  var KEY = 'hoow';
  var BASE = root.dataset.base || '';  // e.g. "/HusbandOutWorld" on a GitHub project page

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } }
  function save(patch) {
    var s = load();
    for (var k in patch) s[k] = patch[k];
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode: settings last for this page only */ }
  }

  // ---------- Public / Behind The Scenes
  var sw = document.querySelector('.mode-switch');
  var dialog = document.getElementById('spoiler-dialog');
  function setMode(mode) {
    root.dataset.mode = mode;
    save({ mode: mode });
    if (sw) sw.setAttribute('aria-checked', mode === 'bts' ? 'true' : 'false');
    document.dispatchEvent(new CustomEvent('modechange'));
  }
  function askBts() {
    if (!dialog || typeof dialog.showModal !== 'function') {
      if (window.confirm('Ready for spoilers? Behind The Scenes shows the author\'s full notes.')) setMode('bts');
      return;
    }
    dialog.returnValue = '';
    dialog.showModal();
  }
  if (dialog) dialog.addEventListener('close', function () { if (dialog.returnValue === 'ok') setMode('bts'); });
  if (sw) {
    sw.setAttribute('aria-checked', root.dataset.mode === 'bts' ? 'true' : 'false');
    sw.addEventListener('click', function () { root.dataset.mode === 'bts' ? setMode('public') : askBts(); });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-go-bts]');
    if (t) { e.preventDefault(); askBts(); }
  });

  // ---------- reading settings
  var sd = document.getElementById('settings-dialog');
  var sb = document.querySelector('.settings-btn');
  if (sb && sd) sb.addEventListener('click', function () { sd.showModal(); });
  if (sd) {
    var s = load();
    sd.querySelectorAll('[data-setting]').forEach(function (el) {
      var k = el.dataset.setting;
      if (k === 'theme') el.value = root.dataset.theme || 'dark';
      if (k === 'size') el.value = s.size || 18;
      if (k === 'vraki') el.checked = root.classList.contains('vraki');
      el.addEventListener('input', function () {
        if (k === 'theme') { root.dataset.theme = el.value; save({ theme: el.value }); }
        if (k === 'size') { root.style.setProperty('--fs', el.value + 'px'); save({ size: +el.value }); }
        if (k === 'vraki') { root.classList.toggle('vraki', el.checked); save({ vraki: el.checked }); }
      });
    });
  }

  // ---------- current nav item
  var path = location.pathname;
  document.querySelectorAll('.mainnav a').forEach(function (a) {
    if (path.indexOf(a.getAttribute('href')) === 0) a.setAttribute('aria-current', 'page');
  });

  // ---------- lightbox
  var lb = document.getElementById('lightbox');
  if (lb) {
    var lbImg = lb.querySelector('img');
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a.img-link');
      if (!a) return;
      e.preventDefault();
      var img = a.querySelector('img');
      lbImg.src = a.dataset.full || a.href;
      lbImg.alt = img ? img.alt : '';
      lb.hidden = false;
    });
    lb.addEventListener('click', function () { lb.hidden = true; lbImg.src = ''; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') lb.hidden = true; });
  }

  // ---------- list filter (glossary)
  document.querySelectorAll('input[data-filter]').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var q = inp.value.trim().toLowerCase();
      document.querySelectorAll(inp.dataset.filter).forEach(function (li) {
        li.style.display = !q || li.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
      });
    });
  });

  // ---------- search
  var box = document.getElementById('search-page-input');
  var list = document.getElementById('search-results');
  if (box && list) {
    var data = null;
    var q0 = new URLSearchParams(location.search).get('q') || '';
    box.value = q0;
    fetch(BASE + '/data/search.json').then(function (r) { return r.json(); }).then(function (d) { data = d; run(); });
    box.addEventListener('input', run);
    document.addEventListener('modechange', run);
    function esc(s) { return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function run() {
      if (!data) return;
      var q = box.value.trim().toLowerCase();
      var bts = root.dataset.mode === 'bts';
      list.innerHTML = '';
      if (q.length < 2) return;
      var words = q.split(/\s+/);
      var hits = [];
      data.forEach(function (it) {
        if (it.b && !bts) return;
        var title = (it.t || '').toLowerCase();
        var text = ((it.x || '') + ' ' + (bts ? it.xb || '' : '')).toLowerCase();
        var score = 0;
        for (var i = 0; i < words.length; i++) {
          var w = words[i];
          if (title.indexOf(w) >= 0) score += title === q ? 20 : 6;
          else if (text.indexOf(w) >= 0) score += 1;
          else return;
        }
        hits.push([score, it]);
      });
      hits.sort(function (a, b) { return b[0] - a[0]; });
      hits.slice(0, 60).forEach(function (h) {
        var it = h[1];
        var li = document.createElement('li');
        var snippet = it.x || (bts ? it.xb : '') || '';
        li.innerHTML = '<a href="' + esc(BASE + it.u) + '">' + esc(it.t) + '</a> <span class="sr-sec">' + esc(it.s) + '</span>' +
          (it.b ? '<span class="sr-bts">Behind the Scenes</span>' : '') + '<br><span class="muted">' + esc(snippet.slice(0, 220)) + '</span>';
        list.appendChild(li);
      });
      if (!hits.length) list.innerHTML = '<li class="muted">No matches' + (bts ? '' : ' in Public pages') + '.</li>';
    }
  }
})();

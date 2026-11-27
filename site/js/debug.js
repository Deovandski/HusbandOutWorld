// "Stats for nerds" (/debug/, #146): fills every [data-v] value of the terminal that debug_page() in tools/build.py
// writes, then starts the typing (site/js/terminal-screen.js). Build facts come from /stats.json (write_stats() in
// tools/build.py); the rest is what this browser tells the page. Nothing is saved or sent anywhere: the only requests
// are stats.json itself (once, plus three timed HEAD requests for "Ping"). A browser that doesn't share something
// shows "n/a". After the typing ends, a few values keep updating (clock, uptime, frame rate, JS heap, viewport, online).
// Ported from Deovandski/Deovandski-repo-template (src/scripts/debug.ts, template#19), with this site's extras
// (novel chapters, lore topics, webcomic, gallery, glossary, blog, the Vraki typeface).
(function () {
  'use strict';
  var root = document.documentElement;
  var BASE = root.dataset.base || '';
  var nav = navigator;
  var term = document.querySelector('.debug-terminal');
  if (!term) return;
  var word = function (k) { var s = document.querySelector('.debug-words [data-k="' + k + '"]'); return s ? s.textContent : k; };
  var NA = word('na');

  // ---------------------------------------------------------------- formatting
  function bytes(n) {
    if (n == null || !isFinite(n)) return NA;
    var u = ['B', 'KB', 'MB', 'GB', 'TB'], i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return n.toFixed(i && n < 10 ? 1 : 0) + ' ' + u[i];
  }
  var ms = function (n) { return n == null || !isFinite(n) || n < 0 ? NA : Math.round(n) + ' ms'; };
  var when = function (iso) { return iso ? new Date(iso).toLocaleString('en-CA', { hour12: false }).replace(',', '') : NA; };
  var yesNo = function (b) { return word(b ? 'yes' : 'no'); };
  function bar(pct, width) {
    width = width || 12;
    var full = Math.round((pct / 100) * width);
    return '[' + '█'.repeat(full) + '░'.repeat(width - full) + ']';
  }
  /** Put text (or a link) in a value. */
  function set(key, text, href) {
    var el = term.querySelector('[data-v="' + key + '"]');
    if (!el) return;
    if (href) {
      var a = document.createElement('a');
      a.href = href; a.rel = 'noopener'; a.textContent = text;
      el.textContent = '';
      el.appendChild(a);
    } else el.textContent = text;
  }
  function timeout(p, t) {
    return Promise.race([Promise.resolve(p).catch(function () { return null; }), new Promise(function (r) { setTimeout(function () { r(null); }, t || 1500); })]);
  }
  var rejected = function () { return Promise.reject(new Error('n/a')); };

  // ---------------------------------------------------------------- code, site, languages (stats.json)
  function fromStats() {
    return timeout(fetch(BASE + '/stats.json', { cache: 'no-cache' })).then(function (res) {
      return res && res.ok ? res.json() : null;
    }).then(function (stats) {
      if (!stats) {
        ['repo', 'build', 'i18nSummary'].forEach(function (k) { set(k, word('noStats')); });
        return;
      }
      var code = stats.code, site = stats.site, i18n = stats.i18n;
      if (code.repo) set('repo', code.repo, code.repoUrl); else set('repo', NA);
      set('visibility', code.public === null ? word('local') : word(code.public ? 'public' : 'private'));
      set('build', code.run ? '#' + code.run + ' · ' + code.builtBy : code.builtBy, code.runUrl);
      set('builtAt', when(code.builtAt));
      set('branch', code.branch || NA);
      set('commit', code.commit ? (code.commit.slice(0, 7) + ' ' + (code.commitSubject || '')).trim() : NA, code.commitUrl);
      set('commitDate', when(code.commitDate));
      set('pr', code.pr ? '#' + code.pr : NA, code.prUrl);
      set('run', code.run ? '#' + code.run : NA, code.runUrl);
      set('tools', Object.keys(code.tools).filter(function (k) { return code.tools[k]; }).map(function (k) { return k + ' ' + code.tools[k]; }).join(' · '));

      set('siteUrl', site.url || NA, site.url);
      set('pages', site.pages + ' × ' + site.languages + ' languages');
      set('deployed', site.files + ' files · ' + bytes(site.bytes));
      set('types', Object.keys(site.byType).slice(0, 4).map(function (ext) { return ext + ' ' + bytes(site.byType[ext].bytes); }).join(' · '));
      var x = site.extras || {};
      set('novel', x.chapters != null ? x.chapters + ' chapters in ' + x.volumes + ' volumes' : NA);
      set('lore', x.loreTopics != null ? x.loreTopics + ' topics · ' + x.glossary + ' glossary entries' : NA);
      set('webcomic', x.webcomic != null ? x.webcomic + ' episodes' : NA);
      set('gallery', x.gallery != null ? x.gallery + ' pictures' : NA);
      set('blog', x.blogPhotos != null ? 'the final post · ' + x.blogPhotos + ' photos' : NA);
      set('vraki', x.vraki ? x.vraki.file + ' · ' + bytes(x.vraki.bytes) : NA);
      var sw = term.querySelector('[data-v="sw"]');
      if (sw && site.serviceWorker) sw.setAttribute('data-version', site.serviceWorker);

      var e = i18n.english;
      set('i18nSummary', 'English: ' + e.pages + ' pages · ' + e.segments + ' segments · ' + e.words.toLocaleString('en') + ' words · indexed at ' + Math.round(i18n.indexCoverage * 100) + '%');
      var marker = term.querySelector('[data-langs-list]');
      var here = root.dataset.lang || 'en';
      i18n.languages.forEach(function (l) {
        var row = document.createElement('div'); row.className = 'term-row';
        var k = document.createElement('span'); k.className = 'term-k'; k.textContent = l.code + ' ' + l.name;
        var v = document.createElement('span'); v.className = 'term-v';
        var b = document.createElement('span'); b.className = 'term-bar';
        b.textContent = bar(l.percent) + ' ' + l.percent.toFixed(1).padStart(5) + '%';
        v.appendChild(b);
        v.appendChild(document.createTextNode(' ' + l.segments + '/' + e.segments + ' seg · ' + word('indexed') + ' ' + l.pagesIndexed + '/' + e.pages));
        if (l.percent < 50) b.classList.add('term-dim');
        if (l.code === here) { row.classList.add('term-hi'); v.appendChild(document.createTextNode(' ' + word('current'))); }
        row.appendChild(k); row.appendChild(v);
        marker.parentNode.insertBefore(row, marker);
      });
    });
  }

  // ---------------------------------------------------------------- this page and the browser
  function webgl() {
    try {
      var gl = document.createElement('canvas').getContext('webgl');
      if (!gl) return NA;
      var ext = gl.getExtension('WEBGL_debug_renderer_info');
      return String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    } catch (e) { return NA; }
  }
  function storageSummary(s) {
    try {
      if (!s) return NA;
      var size = 0, keys = [];
      for (var i = 0; i < s.length; i++) { var k = s.key(i); keys.push(k); size += k.length + (s.getItem(k) || '').length; }
      return keys.length ? keys.length + ' key' + (keys.length > 1 ? 's' : '') + ' · ' + bytes(size * 2) + ' · ' + keys.join(', ') : word('none');
    } catch (e) { return NA; }
  }
  function browserName() {
    var b = nav.userAgentData && nav.userAgentData.brands && nav.userAgentData.brands.filter(function (x) { return !/not.?a.?brand/i.test(x.brand); });
    if (b && b.length) return b.map(function (x) { return x.brand + ' ' + x.version; }).join(' · ');
    var m = navigator.userAgent.match(/(Firefox|Edg|OPR|SamsungBrowser|Chrome|Version)\/([\d.]+)/);
    if (!m) return NA;
    var name = m[1] === 'Version' ? 'Safari' : m[1] === 'Edg' ? 'Edge' : m[1] === 'OPR' ? 'Opera' : m[1];
    return name + ' ' + m[2];
  }
  function fromBrowser() {
    var mq = function (q) { return window.matchMedia(q).matches; };
    var store = term.dataset.store || '';
    set('path', location.pathname);
    set('pageLang', root.lang + (root.dir === 'rtl' ? ' (right to left)' : ''));
    set('readyLangs', (root.dataset.langs || '').trim() || word('none'));
    set('storeKey', store || NA);
    try { set('saved', localStorage.getItem(store) || word('none')); } catch (e) { set('saved', NA); }
    set('display', word(mq('(display-mode: standalone)') || nav.standalone ? 'standalone' : 'tab'));

    set('browser', browserName());
    set('platform', ((nav.userAgentData && nav.userAgentData.platform) || navigator.platform || NA) + (nav.userAgentData && nav.userAgentData.mobile ? ' (mobile)' : ''));
    set('ua', navigator.userAgent);
    set('cpu', navigator.hardwareConcurrency ? navigator.hardwareConcurrency + ' logical cores' : NA);
    set('deviceMemory', nav.deviceMemory ? '≥ ' + nav.deviceMemory + ' GB (rounded by the browser)' : NA);
    var cookies = document.cookie ? document.cookie.split(';').map(function (c) { return c.split('=')[0].trim(); }) : [];
    set('cookies', (navigator.cookieEnabled ? 'enabled' : 'blocked') + ' · ' + (cookies.length ? cookies.join(', ') : 'none set by this site'));
    try { set('local', storageSummary(localStorage)); } catch (e) { set('local', NA); }
    try { set('session', storageSummary(sessionStorage)); } catch (e) { set('session', NA); }
    set('screen', screen.width + '×' + screen.height + ' · ' + screen.colorDepth + '-bit colour' + (screen.orientation ? ' · ' + screen.orientation.type : ''));
    set('dpr', devicePixelRatio + '×');
    set('scheme', (mq('(prefers-color-scheme: dark)') ? 'dark' : 'light') + (mq('(prefers-contrast: more)') ? ' · more contrast' : '') + ' · site theme ' + (root.dataset.theme || NA));
    set('motion', word(mq('(prefers-reduced-motion: reduce)') ? 'reduce' : 'full'));
    set('input', (mq('(pointer: coarse)') ? 'touch' : mq('(pointer: fine)') ? 'mouse' : NA) + (navigator.maxTouchPoints ? ' · ' + navigator.maxTouchPoints + ' touch points' : ''));
    set('gpu', webgl());
    set('webgpu', yesNo(!!nav.gpu));
    var tz = Intl.DateTimeFormat().resolvedOptions(), off = -new Date().getTimezoneOffset();
    set('tz', tz.timeZone + ' (UTC' + (off >= 0 ? '+' : '') + off / 60 + ') · ' + tz.locale);
    set('langs', (navigator.languages || [navigator.language]).join(', '));
    set('secure', yesNo(window.isSecureContext));
    set('isolated', yesNo(!!window.crossOriginIsolated));

    var c = nav.connection;
    set('connection', c ? [c.type, c.effectiveType].filter(Boolean).join(' · ') || NA : NA);
    set('downlink', c && c.downlink != null ? c.downlink + ' Mbps (estimate)' : NA);
    set('rtt', c && c.rtt != null ? c.rtt + ' ms (estimate)' : NA);
    set('saveData', c && c.saveData != null ? yesNo(c.saveData) : NA);

    var st = navigator.storage;
    return Promise.all([
      timeout(st && st.estimate ? st.estimate() : rejected()),
      timeout(st && st.persisted ? st.persisted() : rejected()),
      'serviceWorker' in navigator ? timeout(navigator.serviceWorker.getRegistration()) : null,
      'caches' in window ? timeout(caches.keys()) : null,
      nav.getBattery ? timeout(nav.getBattery()) : null
    ]).then(function (r) {
      var est = r[0], persisted = r[1], reg = r[2], names = r[3], bat = r[4];
      set('storage', est ? bytes(est.usage) + ' used of ' + bytes(est.quota) + (persisted != null ? ' · persistent: ' + yesNo(persisted) : '') : NA);
      if (!('serviceWorker' in navigator)) set('sw', word('noWorker'));
      else {
        var version = term.querySelector('[data-v="sw"]').getAttribute('data-version');
        set('sw', reg ? word(navigator.serviceWorker.controller ? 'controlled' : 'notControlled') + (version ? ' · ' + version : '') + ' · scope ' + new URL(reg.scope).pathname : word('none'));
      }
      set('battery', bat ? Math.round(bat.level * 100) + '% · ' + word(bat.charging ? 'charging' : 'unplugged') : NA);
      if (!('caches' in window)) { set('caches', NA); return; }
      names = names || [];
      return Promise.all(names.map(function (n) {
        return timeout(caches.open(n).then(function (cache) { return cache.keys(); })).then(function (k) { return k ? k.length : 0; });
      })).then(function (counts) {
        set('caches', names.length ? names.map(function (n, i) { return n + ': ' + counts[i] + ' files'; }).join(' · ') : word('none'));
      });
    });
  }

  // ---------------------------------------------------------------- network and performance
  function observed(type) {
    var got = [];
    try {
      var o = new PerformanceObserver(function () {});
      o.observe({ type: type, buffered: true });
      got = o.takeRecords();
      o.disconnect();
    } catch (e) { /* not supported */ }
    return got;
  }
  function fromNetwork() {
    var nt = performance.getEntriesByType('navigation')[0];
    if (nt) {
      set('protocol', nt.nextHopProtocol || NA);
      set('servedFrom', word(nt.workerStart > 0 && nt.transferSize === 0 ? 'worker' : nt.transferSize === 0 ? 'memcache' : 'network'));
      set('dns', ms(nt.domainLookupEnd - nt.domainLookupStart));
      set('connect', ms(nt.connectEnd - nt.connectStart));
      set('tls', nt.secureConnectionStart > 0 ? ms(nt.connectEnd - nt.secureConnectionStart) : NA);
      set('ttfb', ms(nt.responseStart - nt.startTime));
      set('download', ms(nt.responseEnd - nt.responseStart));
      set('domReady', ms(nt.domContentLoadedEventEnd - nt.startTime));
      set('load', nt.loadEventEnd ? ms(nt.loadEventEnd - nt.startTime) : NA);
      set('transfer', bytes(nt.transferSize) + ' over the wire · ' + bytes(nt.decodedBodySize) + ' HTML');
    } else {
      ['protocol', 'servedFrom', 'dns', 'connect', 'tls', 'ttfb', 'download', 'domReady', 'load', 'transfer'].forEach(function (k) { set(k, NA); });
    }
    var res = performance.getEntriesByType('resource');
    set('resources', res.length + ' files · ' + bytes(res.reduce(function (n, r) { return n + (r.transferSize || 0); }, 0)) + ' over the wire');
    set('nodes', document.getElementsByTagName('*').length + ' elements');
    var fcp = performance.getEntriesByName('first-contentful-paint')[0];
    set('fcp', ms(fcp && fcp.startTime));
    var lcp = observed('largest-contentful-paint').slice(-1)[0];
    set('lcp', ms(lcp && lcp.startTime));
    var shifts = observed('layout-shift');
    var supported = PerformanceObserver.supportedEntryTypes && PerformanceObserver.supportedEntryTypes.indexOf('layout-shift') >= 0;
    set('cls', shifts.length || supported ? shifts.filter(function (s) { return !s.hadRecentInput; }).reduce(function (n, s) { return n + s.value; }, 0).toFixed(3) : NA);

    // Ping: three HEAD requests for stats.json, straight to the server (no-store skips every cache).
    var times = [], headers = null;
    function ping(i) {
      if (i >= 3) return Promise.resolve();
      var t0 = performance.now();
      return timeout(fetch(BASE + '/stats.json?ping=' + Date.now(), { method: 'HEAD', cache: 'no-store' }), 3000).then(function (r) {
        if (!r) return;
        times.push(performance.now() - t0);
        headers = headers || r.headers;
        return ping(i + 1);
      });
    }
    return ping(0).then(function () {
      set('ping', times.length ? 'min ' + ms(Math.min.apply(null, times)) + ' · avg ' + ms(times.reduce(function (a, b) { return a + b; }, 0) / times.length) + ' (' + times.length + ' HEAD requests)' : NA);
      var h = function (k) { return headers ? headers.get(k) : null; };
      set('server', h('server') || NA);
      set('cdn', h('x-served-by') || h('via') || NA);
      set('cdnCache', [h('x-cache'), h('cache-control'), h('age') ? 'age ' + h('age') + 's' : null].filter(Boolean).join(' · ') || NA);
    });
  }

  // ---------------------------------------------------------------- live values
  var frameCount = 0, fps = 0;
  function countFrames() { frameCount++; requestAnimationFrame(countFrames); }
  function live() {
    var heap = performance.memory;
    set('heap', heap ? bytes(heap.usedJSHeapSize) + ' used · ' + bytes(heap.totalJSHeapSize) + ' allocated · ' + bytes(heap.jsHeapSizeLimit) + ' limit' : NA);
    set('viewport', innerWidth + '×' + innerHeight);
    set('clock', new Date().toLocaleString('en-CA', { hour12: false }).replace(',', ''));
    var s = Math.floor(performance.now() / 1000);
    set('uptime', Math.floor(s / 60) + 'm ' + String(s % 60).padStart(2, '0') + 's on this page');
    set('fps', fps ? fps + ' fps' : word('measuring'));
    set('online', word(navigator.onLine ? 'online' : 'offline'));
  }

  function main() {
    set('now', when(new Date().toISOString()));
    set('memtest', nav.deviceMemory ? nav.deviceMemory * 1024 * 1024 + 'K' : '640K');
    live();
    requestAnimationFrame(countFrames);
    var startFps = performance.now();
    Promise.all([fromStats(), fromBrowser(), timeout(fromNetwork(), 2500)]).then(function () {
      // a first frame-rate reading before the typing starts, so no value is left waiting
      var elapsed = (performance.now() - startFps) / 1000;
      fps = Math.round(frameCount / Math.max(elapsed, 0.25));
      frameCount = 0;
      live();
      // anything a browser didn't answer in time shows "n/a" rather than "..."
      Array.prototype.forEach.call(term.querySelectorAll('[data-v]'), function (el) { if (el.textContent === '...') el.textContent = NA; });
      term.addEventListener('terminal:done', function () {
        setInterval(function () { fps = frameCount; frameCount = 0; live(); }, 1000);
      }, { once: true });
      term.dispatchEvent(new CustomEvent('terminal:start'));
    });
  }

  if (document.readyState === 'complete') main();
  else window.addEventListener('load', function () { setTimeout(main); }, { once: true }); // after load ends, so "Load" has its time
})();

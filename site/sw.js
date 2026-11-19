// Service worker: lets the installed app (and the site in Chrome) keep working with no signal.
// Adapted from Deovandski/Deovandski (public/sw.js, PR #160). Written into the site by tools/pwa.py,
// which fills in the __PLACEHOLDERS__ below.
//
// What it saves on the reader's device (never on a server):
//   - the home page with its CSS and scripts (not its pictures), when the worker installs;
//   - every page the reader opens, as text: a novel chapter read once can be read again offline
//     (set SAVE_VISITED_PAGES to false to save only the home pages);
//   - the CSS, scripts, fonts, the app manifest and the app icons.
// What it never saves: pictures (the gallery, the webcomic, chapter illustrations) or anything from
// other websites, so it can't fill the phone's storage.
//
// Pages come from the network first. If there's no answer within 4 seconds (or no signal), the saved
// copy is used when there is one. Everything is per device and stays there until the browser clears it.
//
// Change VERSION to throw away everything saved and start over.
const VERSION = '__VERSION__';
const PREFIX = '__PREFIX__';
const CACHE = `${PREFIX}-${VERSION}`;
const SAVE_VISITED_PAGES = __SAVE_VISITED__;
const NETWORK_TIMEOUT_MS = 4000;
const SCOPE = new URL(self.registration.scope);
const HOMES = __HOMES__.map((p) => new URL(p, SCOPE).href);          // the home page (and language homes)
const EXTRA = __EXTRA__.map((p) => new URL(p, SCOPE).href);          // manifest, icons, favicon
const SAVED_KINDS = ['style', 'script', 'font', 'manifest'];

// Same-origin stylesheets and scripts a page needs to draw itself (pictures are left out on purpose).
function assetsOf(html, pageUrl) {
  const found = new Set();
  const re = /<(?:link|script)\b[^>]*?\s(?:href|src)="([^"]+)"[^>]*>/gi;
  for (const m of html.matchAll(re)) {
    const tag = m[0];
    if (/^<link/i.test(tag) && !/rel="(?:stylesheet|modulepreload|preload|icon|manifest)"/i.test(tag)) continue;
    const url = new URL(m[1].replace(/&amp;/g, '&'), pageUrl);
    if (url.origin === SCOPE.origin && url.href.startsWith(SCOPE.href)) found.add(url.href);
  }
  return [...found];
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      for (const page of HOMES) {
        try {
          const res = await fetch(page, { cache: 'no-cache' });
          if (!res.ok) continue;
          const html = await res.clone().text();
          await cache.put(page, res);
          await Promise.allSettled(assetsOf(html, page).map((f) => cache.add(f)));
        } catch {
          // offline during install: the next visit fills the cache instead
        }
      }
      await Promise.allSettled(EXTRA.map((f) => cache.add(f)));
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) if (key.startsWith(`${PREFIX}-`) && key !== CACHE) await caches.delete(key);
      await self.clients.claim();
    })(),
  );
});

// A page's address without its #hash or ?query, so /lore/?x and /lore/#top share one saved copy.
const pageKey = (url) => url.origin + url.pathname;
const isHome = (key) => HOMES.includes(key) || /^\/[a-z]{2}\/$/.test(key.slice(SCOPE.href.length - 1));

async function networkFirst(request, key) {
  const cache = await caches.open(CACHE);
  const network = fetch(request).then((res) => {
    if (res.ok && (SAVE_VISITED_PAGES || isHome(key))) cache.put(key, res.clone());
    return res;
  });
  const timeout = new Promise((resolve) => setTimeout(resolve, NETWORK_TIMEOUT_MS));
  try {
    const res = await Promise.race([network, timeout]);
    if (res) return res;
  } catch {
    // offline: fall through to the saved copy
  }
  return (await cache.match(key)) ?? network.catch(() => offlinePage());
}

// Shown when there's no signal and the page was never opened before (so nothing was saved).
function offlinePage() {
  const home = SCOPE.href;
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offline</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#101719;color:#efe7dc;font:18px/1.6 Georgia,serif;text-align:center;padding:1.5rem}a{color:#9db8ff}</style>
<main><h1>You're offline</h1><p>This page hasn't been saved on this device yet.<br>Pages you've opened before still work without a signal.</p><p><a href="${home}">Go to the home page</a></p></main></html>`;
  return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

// CSS and scripts carry ?v=<hash> (a new address for every change), so the saved copy is matched with
// its query; storing a new version drops the older ones of the same file.
async function savedFirst(request) {
  const cache = await caches.open(CACHE);
  const saved = await cache.match(request);
  if (saved) return saved;
  const res = await fetch(request);
  if (res.ok && SAVED_KINDS.includes(request.destination)) {
    const path = new URL(request.url).pathname;
    for (const old of await cache.keys()) {
      const u = new URL(old.url);
      if (u.pathname === path && old.url !== request.url) await cache.delete(old);
    }
    await cache.put(request, res.clone());
  }
  return res;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== SCOPE.origin || !url.href.startsWith(SCOPE.href)) return; // other websites: hands off

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, pageKey(url)));
    return;
  }
  if (SAVED_KINDS.includes(request.destination) || EXTRA.includes(url.href)) {
    event.respondWith(savedFirst(request));
  }
  // anything else (pictures, search data): straight from the network, never saved
});

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
// other websites, so it can't fill the phone's storage. Files in SKIP (like a site-verification file) are
// left entirely to the browser.
//
// Always the latest deploy: pages, and any file whose address doesn't change when the file does (fonts,
// the manifest, icons), come from the network first, fetched with `cache: 'no-cache'` so the browser asks
// the server instead of reusing its own copy (GitHub Pages lets browsers keep files for 10 minutes; when
// nothing changed the server answers with a short "not modified"). If there's no answer within 4 seconds
// (or no signal), the saved copy is used when there is one. Only files with a ?v=<content hash> in their
// address (the CSS and scripts the build links) are answered from the saved copy first: a new deploy
// links new addresses, so an old copy can never be paired with a new page.
// Everything is per device and stays there until the browser clears it.
//
// Change VERSION to throw away everything saved and start over (done for #120: v2 drops copies the
// older worker may have saved from the browser's cache).
const VERSION = '__VERSION__';
const PREFIX = '__PREFIX__';
const CACHE = `${PREFIX}-${VERSION}`;
const SAVE_VISITED_PAGES = __SAVE_VISITED__;
const NETWORK_TIMEOUT_MS = 4000;
const SCOPE = new URL(self.registration.scope);
const HOMES = __HOMES__.map((p) => new URL(p, SCOPE).href);          // the home page (and language homes)
const EXTRA = __EXTRA__.map((p) => new URL(p, SCOPE).href);          // manifest, icons, favicon
const SKIP = __SKIP__.map((p) => new URL(p, SCOPE).href);            // never answered or saved by the worker
const SAVED_KINDS = ['style', 'script', 'font', 'manifest'];
const OFFLINE_COLORS = __OFFLINE_COLORS__;                           // background, text, link

// Ask the server, not the browser's own cache. A navigation request can't be copied with new options,
// hence the address.
const fresh = (url) => fetch(url, { cache: 'no-cache', credentials: 'same-origin' });
// The build gives its CSS and scripts a new ?v=<content hash> on every change.
const versioned = (url) => url.searchParams.has('v');

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

async function saveFresh(href) {
  const res = await fresh(href);
  if (res.ok) await (await caches.open(CACHE)).put(href, res);
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      for (const page of HOMES) {
        try {
          const res = await fresh(page);
          if (!res.ok) continue;
          const html = await res.clone().text();
          await cache.put(page, res);
          await Promise.allSettled(assetsOf(html, page).map(saveFresh));
        } catch {
          // offline during install: the next visit fills the cache instead
        }
      }
      await Promise.allSettled(EXTRA.map(saveFresh));
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

// The latest copy from the server, saved for offline use (when `save`); the saved copy only offline or
// after NETWORK_TIMEOUT_MS. Pages pass isPage, so a redirect (/lore -> /lore/) moves the address bar too
// and a page never opened before gets the "You're offline" page.
async function networkFirst(request, key, { save = true, isPage = false } = {}) {
  const cache = await caches.open(CACHE);
  const network = fresh(request.url).then((res) => {
    if (isPage && res.redirected) return Response.redirect(res.url, 302);
    if (res.ok && save) cache.put(key, res.clone());
    return res;
  });
  const timeout = new Promise((resolve) => setTimeout(resolve, NETWORK_TIMEOUT_MS));
  try {
    const res = await Promise.race([network, timeout]);
    if (res) return res;
  } catch {
    // offline: fall through to the saved copy
  }
  return (await cache.match(key)) ?? network.catch(() => (isPage ? offlinePage() : Response.error()));
}

// Shown when there's no signal and the page was never opened before (so nothing was saved).
function offlinePage() {
  const home = SCOPE.href;
  const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offline</title><style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:${OFFLINE_COLORS[0]};color:${OFFLINE_COLORS[1]};font:18px/1.6 Georgia,serif;text-align:center;padding:1.5rem}a{color:${OFFLINE_COLORS[2]}}</style>
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
  if (SKIP.includes(url.origin + url.pathname)) return; // e.g. a site-verification file: always the real one

  if (request.mode === 'navigate') {
    const key = pageKey(url);
    event.respondWith(networkFirst(request, key, { save: SAVE_VISITED_PAGES || isHome(key), isPage: true }));
    return;
  }
  if (SAVED_KINDS.includes(request.destination) || EXTRA.includes(url.href)) {
    event.respondWith(versioned(url) ? savedFirst(request) : networkFirst(request, url.href));
  }
  // anything else (pictures, search data): straight from the network, never saved
});

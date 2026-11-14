"""Translations of the website (Chinese, Japanese, Portuguese, Spanish, Arabic, Korean), written ahead of time and kept
in content/i18n/<lang>/. English stays the source; nothing in Legacy/ changes.

How it works
- After the build makes an English page, translate_page() splits it into segments: every element that holds text
  directly (a paragraph, heading, list item, button, label, caption, ...) plus a few attributes (alt, title,
  aria-label, placeholder, the page description). Each segment is keyed by a short hash of its English HTML.
- The translation of a segment is looked up by that hash. A segment with no translation stays in English, so a
  half-translated language still works.
- English that doesn't change keeps its hash, so it is never translated twice. Only new or edited segments show up
  in `todo`.

Store layout (content/i18n/<lang>/)
  meta.json         the language's name, the banner and other strings the build writes itself
  glossary.json     how names and recurring terms are written in this language (read by whoever translates)
  _shared.json      segments that appear on many pages (menu, footer, settings, ...)
  pages/<url>.json  everything else, one file per page: {"<hash>": {"en": "<English HTML>", "t": "<translation>"}}

Command line (run a build first; it writes .i18n-cache/segments.json)
  python tools/i18n.py status                       what's translated, per language and phase
  python tools/i18n.py todo --lang ja [--phase 1] [--max-words 6000] [--page /novel/] > work.json
                                                    only the segments that still need translating
  python tools/i18n.py apply work.json              save the "t" fields of a work file into the store
  python tools/i18n.py prune                        drop translations whose English no longer exists

Phases: 1 = site interface, home, About, Blog, Webcomic, Gallery and the public World Lore;
        2 = the novel; 3 = the Glossary and everything Behind The Scenes.
"""
import argparse, glob, hashlib, html, json, os, re, sys
from collections import Counter, defaultdict

from lxml import html as LH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, 'content', 'i18n')
CACHE = os.path.join(ROOT, '.i18n-cache')
INVENTORY = os.path.join(CACHE, 'segments.json')

SKIP_TAGS = {'script', 'style', 'svg', 'noscript', 'template', 'code', 'pre', 'textarea'}
ATTRS = ('alt', 'title', 'aria-label', 'placeholder')
SHARED_MIN_PAGES = 5          # a segment on at least this many pages lives in _shared.json
INDEX_COVERAGE = 0.9          # a language version is offered (auto-select, search engines) once this much is translated
ASSET_DIRS = ('media', 'css', 'js', 'fonts', 'data')
ASSET_EXT = ('.md', '.txt', '.xml', '.json', '.webp', '.png', '.jpg', '.jpeg', '.gif', '.woff2', '.pdf')
LETTER = re.compile(r'[^\W\d_]')


# ---------------------------------------------------------------- store

def norm(s):
    """Whitespace and quote style don't change a segment's meaning, so they don't change its hash."""
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip()


def seg_hash(en_html):
    return hashlib.sha1(norm(en_html).encode('utf-8')).hexdigest()[:12]


def languages(cfg):
    return [l for l in cfg.get('languages', []) if os.path.isdir(os.path.join(STORE, l['code']))]


def load_meta(code):
    p = os.path.join(STORE, code, 'meta.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def shard_files(code):
    base = os.path.join(STORE, code)
    return [p for p in [os.path.join(base, '_shared.json')] + glob.glob(os.path.join(base, 'pages', '**', '*.json'), recursive=True)
            if os.path.exists(p)]


def load_store(code):
    """hash -> translated HTML, from every shard of one language."""
    out = {}
    for p in shard_files(code):
        for h, v in json.load(open(p, encoding='utf-8')).items():
            if isinstance(v, dict) and v.get('t'):
                out[h] = v['t']
    return out


def page_shard(url):
    slug = url.strip('/').replace('/', os.sep) or 'home'
    if slug.endswith('.html'):
        slug = slug[:-5]
    return os.path.join('pages', slug + '.json')


# ---------------------------------------------------------------- segments

def inner_html(el):
    return (html.escape(el.text, quote=False) if el.text else '') + ''.join(
        LH.tostring(c, encoding='unicode', with_tail=True) for c in el)


def set_inner_html(el, frag_html):
    for c in list(el):
        el.remove(c)
    try:
        frag = LH.fragment_fromstring(frag_html, create_parent='div')
    except Exception:
        el.text = frag_html
        return
    el.text = frag.text
    for c in list(frag):
        el.append(c)


def has_direct_text(el):
    """Text right inside the element (not only in its children). Separators like " · " or ", " don't count."""
    if el.text and LETTER.search(el.text):
        return True
    return any(c.tail and LETTER.search(c.tail) for c in el)


def skipped(el):
    if not isinstance(el.tag, str) or el.tag in SKIP_TAGS:
        return True
    if el.get('translate') == 'no':
        return True
    return False


def in_bts(el):
    for a in el.iterancestors():
        c = (a.get('class') or '').split()
        if 'layer' in c and 'bts' in c:
            return True
    c = (el.get('class') or '').split()
    return 'layer' in c and 'bts' in c


def segments(doc):
    """Yield (element, attribute or None, English text/HTML) for every translatable piece of a page."""
    def walk(el):
        if skipped(el):
            return
        for a in ATTRS:
            v = el.get(a)
            if v and LETTER.search(v):
                yield el, a, v
        if el.tag != 'html' and el.tag != 'head' and el.tag != 'body' and has_direct_text(el):
            h = inner_html(el)
            if LETTER.search(el.text_content() or ''):
                yield el, None, h
            # attributes of descendants (alt on an image inside a paragraph) are part of that paragraph's HTML
            return
        for c in el:
            yield from walk(c)
    head = doc.find('head')
    if head is not None:
        for m in head.iter('meta'):
            if (m.get('name') == 'description' or m.get('property') in ('og:title', 'og:description')) and m.get('content'):
                yield m, 'content', m.get('content')
    yield from walk(doc)


def text_words(s):
    return len(re.sub(r'<[^>]+>', ' ', s).split())


# ---------------------------------------------------------------- pages

def lang_url(path, code):
    """'/novel/vol-1/' -> '/ja/novel/vol-1/' for site pages; files and assets stay where they are."""
    if not path.startswith('/') or path.startswith('//'):
        return path
    bare = path.split('#')[0].split('?')[0]
    first = bare.strip('/').split('/')[0]
    if first in ASSET_DIRS or bare.lower().endswith(ASSET_EXT) or first == code:
        return path
    return f'/{code}{path}'


def inventory(page_html_en, url, section):
    """Segments of one English page: [[hash, english, words, layer]]."""
    doc = LH.document_fromstring(page_html_en)
    out, seen = [], set()
    for el, attr, en in segments(doc):
        h = seg_hash(en)
        if h in seen:
            continue
        seen.add(h)
        out.append([h, en, text_words(en), 'bts' if in_bts(el) else 'public'])
    return out


def translate_page(page_html_en, url, code, meta, store, base_url):
    """English page HTML (before the base path is added) -> (translated page HTML, coverage 0..1)."""
    doc = LH.document_fromstring(page_html_en)
    total = done = 0
    for el, attr, en in list(segments(doc)):
        w = text_words(en) or 1
        total += w
        t = store.get(seg_hash(en))
        if not t:
            if attr is None:
                el.set('lang', 'en')        # still English: say so (screen readers, and left to right inside Arabic)
                if meta.get('dir') == 'rtl':
                    el.set('dir', 'ltr')
            continue
        done += w
        if attr:
            el.set(attr, t)
        else:
            set_inner_html(el, t)
    # links stay inside the language
    for el in doc.iter():
        if not isinstance(el.tag, str):
            continue
        for a in ('href', 'action', 'data-next', 'data-prev'):
            v = el.get(a)
            if v and v.startswith('/'):
                el.set(a, lang_url(v, code))
    root = doc.getroottree().getroot()
    root.set('lang', meta.get('html_lang', code))
    root.set('dir', meta.get('dir', 'ltr'))
    root.set('data-lang', code)
    head = doc.find('head')
    for link in head.iter('link'):
        if link.get('rel') == 'canonical':
            link.set('href', base_url + lang_url(url, code))
    coverage = (done / total) if total else 1.0
    # the AI-translation banner, right under the top bar
    body = doc.find('body')
    top = body.find('.//header')
    if top is not None and meta.get('banner'):
        banner = LH.fragment_fromstring(
            f'<div class="i18n-banner" role="note">{meta["banner"]} '
            f'<a href="{url}" class="i18n-en" data-lang-switch="en" hreflang="en" lang="en" translate="no">{html.escape(meta.get("english", "English"))}</a></div>')
        top.addnext(banner)
    out = LH.tostring(doc, encoding='unicode', method='html', doctype='<!doctype html>')
    return out, coverage


def head_extras(html_text, url, code_cov, base_url, this_code=None):
    """Tell search engines and the auto-select script which language versions are ready."""
    ready = [c for c, cov in code_cov.items() if cov >= INDEX_COVERAGE]
    alts = ''.join(f'<link rel="alternate" hreflang="{c}" href="{base_url}/{c}{url}">' for c in ready)
    if ready:
        alts = f'<link rel="alternate" hreflang="en" href="{base_url}{url}">' + alts
    if this_code and code_cov.get(this_code, 0) < INDEX_COVERAGE:
        alts += '<meta name="robots" content="noindex">'
    html_text = html_text.replace('</head>', alts + '</head>', 1)
    attr = f' data-langs="{" ".join(ready)}"'
    return re.sub(r'<html\b', '<html' + attr, html_text, count=1)


def phase(section, layer):
    if layer == 'bts' or section == 'Glossary':
        return 3
    if section == 'Light Novel':
        return 2
    return 1


# ---------------------------------------------------------------- command line

def load_inventory():
    if not os.path.exists(INVENTORY):
        sys.exit('No segment list yet: run a build first (python tools/build.py --out _site --no-images).')
    return json.load(open(INVENTORY, encoding='utf-8'))


def all_codes():
    return sorted(d for d in os.listdir(STORE) if os.path.isdir(os.path.join(STORE, d))) if os.path.isdir(STORE) else []


def unique_segments(inv):
    """hash -> {en, words, layer, pages[], phase}"""
    segs = {}
    for url, page in inv['pages'].items():
        for h, en, w, layer in page['segments']:
            s = segs.setdefault(h, {'en': en, 'words': w, 'layer': layer, 'pages': [], 'phase': 9})
            s['pages'].append(url)
            s['phase'] = min(s['phase'], phase(page['section'], layer))
    for s in segs.values():
        if len(s['pages']) >= SHARED_MIN_PAGES:
            s['phase'] = 1
    return segs


def cmd_status(a):
    inv = load_inventory()
    segs = unique_segments(inv)
    tot = Counter(); words = Counter()
    for s in segs.values():
        tot[s['phase']] += 1; words[s['phase']] += s['words']
    print(f'English: {len(segs):,} segments, {sum(words.values()):,} words '
          + ' · '.join(f'phase {p}: {words[p]:,} words' for p in sorted(words)))
    for code in all_codes():
        st = load_store(code)
        dw = Counter(); dn = Counter()
        for h, s in segs.items():
            if h in st:
                dw[s['phase']] += s['words']; dn[s['phase']] += 1
        waiting = sum(1 for h in segs if h not in st)
        print(f'{code}: {waiting:,} segments waiting · ' + ' · '.join(
            f'phase {p} {100 * dw[p] / max(1, words[p]):.0f}%' for p in sorted(words)))


def cmd_todo(a):
    inv = load_inventory()
    segs = unique_segments(inv)
    st = load_store(a.lang)
    items, budget = [], a.max_words or 10 ** 9
    for h, s in sorted(segs.items(), key=lambda kv: (kv[1]['phase'], kv[1]['pages'][0])):
        if h in st or (a.phase and s['phase'] != a.phase):
            continue
        if a.page and not any(p.startswith(a.page) for p in s['pages']):
            continue
        if items and s['words'] > budget:
            break
        budget -= s['words']
        items.append({'h': h, 'page': s['pages'][0], 'layer': s['layer'], 'en': s['en'], 't': ''})
    json.dump({'lang': a.lang, 'glossary': f'content/i18n/{a.lang}/glossary.json',
               'rules': 'Translate "en" into "t". Keep every HTML tag and attribute exactly (only translate visible text and alt/title text). '
                        'Write names as glossary.json says. Leave "t" empty to skip.',
               'items': items}, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write('\n')
    print(f'{len(items)} segments, {sum(text_words(i["en"]) for i in items):,} words', file=sys.stderr)


def tag_shape(s):
    return Counter(re.findall(r'<(/?[a-z0-9]+)', s or ''))


def cmd_apply(a):
    inv = load_inventory()
    segs = unique_segments(inv)
    work = json.load(open(a.file, encoding='utf-8'))
    code = work['lang']
    base = os.path.join(STORE, code)
    shards = {}
    saved = warned = 0
    for it in work['items']:
        t = (it.get('t') or '').strip()
        if not t:
            continue
        h = it['h']
        if tag_shape(t) != tag_shape(it['en']):
            print(f'warning: {h} ({it["page"]}): the HTML tags differ from the English; check it', file=sys.stderr)
            warned += 1
        s = segs.get(h, {'pages': [it['page']]})
        rel = '_shared.json' if len(s['pages']) >= SHARED_MIN_PAGES else page_shard(s['pages'][0])
        path = os.path.join(base, rel)
        if path not in shards:
            shards[path] = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
        shards[path][h] = {'en': it['en'], 't': t}
        saved += 1
    for path, data in shards.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(dict(sorted(data.items())), open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        open(path, 'a', encoding='utf-8').write('\n')
    print(f'{code}: saved {saved} translations into {len(shards)} files' + (f', {warned} to check' if warned else ''))


def cmd_prune(a):
    segs = unique_segments(load_inventory())
    for code in all_codes():
        dropped = 0
        for path in shard_files(code):
            data = json.load(open(path, encoding='utf-8'))
            keep = {h: v for h, v in data.items() if h in segs}
            dropped += len(data) - len(keep)
            if len(keep) != len(data):
                if keep:
                    json.dump(keep, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                    open(path, 'a', encoding='utf-8').write('\n')
                else:
                    os.remove(path)
        print(f'{code}: dropped {dropped} translations of English that no longer exists')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    t = sub.add_parser('todo'); t.add_argument('--lang', required=True); t.add_argument('--phase', type=int)
    t.add_argument('--max-words', type=int); t.add_argument('--page')
    p = sub.add_parser('apply'); p.add_argument('file')
    sub.add_parser('prune')
    a = ap.parse_args()
    {'status': cmd_status, 'todo': cmd_todo, 'apply': cmd_apply, 'prune': cmd_prune}[a.cmd](a)


if __name__ == '__main__':
    main()

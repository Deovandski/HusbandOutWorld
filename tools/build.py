#!/usr/bin/env python3
"""Build the #HusbandOutWorld website from the Legacy folder.

Everything the site shows comes from Legacy/ (the author's originals):
  * Legacy/Public            -> the "Public" layer (the old blog, as published)
  * Legacy/Behind The Scenes -> the "Behind The Scenes" layer (the full docs)
content/ holds the page map, alt text and typo fixes. Nothing here writes lore.

Usage: python tools/build.py [--out _site] [--cache .media-cache] [--no-images]
"""
import argparse, base64, hashlib, html, io, json, os, re, shutil, sys, unicodedata
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, unquote

from markdown_it import MarkdownIt
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i18n  # the translations (tools/i18n.py)
import mdtwin  # Markdown twins of translated pages (tools/mdtwin.py)
import pwa  # the installable app: manifest, icons, service worker (tools/pwa.py)

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, 'Legacy')
BTS = os.path.join(LEGACY, 'Behind The Scenes')
PUB = os.path.join(LEGACY, 'Public')
CONTENT = os.path.join(ROOT, 'content')
SITE_SRC = os.path.join(ROOT, 'site')

_ASSET_V = {}
def asset(url):
    """/css/site.css -> /css/site.css?v=<content hash>, so a browser never pairs a new page with an old cached stylesheet."""
    if url not in _ASSET_V:
        f = os.path.join(SITE_SRC, url.lstrip('/'))
        _ASSET_V[url] = hashlib.sha1(open(f, 'rb').read()).hexdigest()[:10] if os.path.exists(f) else ''
    return url + (f'?v={_ASSET_V[url]}' if _ASSET_V[url] else '')

CFG = json.load(open(os.path.join(CONTENT, 'site.json')))
ALT = json.load(open(os.path.join(CONTENT, 'alt-text.json'))) if os.path.exists(os.path.join(CONTENT, 'alt-text.json')) else {}
FIXES = json.load(open(os.path.join(CONTENT, 'fixes.json'))) if os.path.exists(os.path.join(CONTENT, 'fixes.json')) else {}
MD_MAX = 150_000              # a page's Markdown twin bigger than this splits its Behind The Scenes layer by category
BUNDLE_MAX = 300_000          # the smaller full-text files in /llms/ stay under this where a page allows (bytes)
SUB_HEADING_MAX = 4           # a heading inside entries that shows up this many times is template, not a term (search index)
BLUR = json.load(open(os.path.join(CONTENT, 'blur.json'))) if os.path.exists(os.path.join(CONTENT, 'blur.json')) else {}

def blur_image(raw, percent):
    """A blurred PNG of an image, for display only (content/blur.json). 100% blurs by 6% of the longer side."""
    im = Image.open(io.BytesIO(raw))
    im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
    out = io.BytesIO()
    im.filter(ImageFilter.GaussianBlur(max(im.size) * 0.06 * percent / 100)).save(out, 'PNG')
    return out.getvalue()

QA_POINTER = re.compile(r' ?\(See World Lore Q&A › [^)]*\)')

def read_legacy(path):
    """Read a Legacy file and apply its display-only fixes from content/fixes.json."""
    text = open(path, encoding='utf-8').read()
    for fx in FIXES.get(rel(path), []):
        if fx['find'] not in text:
            print(f'warning: fix not found in {rel(path)}: {fx["find"][:60]!r}', file=sys.stderr)
        text = text.replace(fx['find'], fx['replace'])
    # "(See World Lore Q&A › …)" pointers trace a World Lore line back to its Q&A entry in the repo; the website
    # leaves them out (AI-DISCLOSURE.md explains the Q&A instead)
    text = QA_POINTER.sub('', text)
    return text

SUMMARIES = json.load(open(os.path.join(CONTENT, 'summaries.json'))) if os.path.exists(os.path.join(CONTENT, 'summaries.json')) else {}
TYPOS = json.load(open(os.path.join(CONTENT, 'typos.json'))) if os.path.exists(os.path.join(CONTENT, 'typos.json')) else {}
GH_BLOB = CFG['repo_url'] + '/blob/main/'
BASE = ''  # path the site is served under, e.g. "/HusbandOutWorld" on a GitHub project page; "" on a custom domain

REPO_HREF = re.compile(r'href="((?:Legacy|content|tools|site|\.github)(?:/[^"]*)?|(?:AI-DISCLOSURE|README|LICENSE|CLAUDE)\.md[^"]*)"')

def with_base(html_text):
    """Prefix every site-internal link (href="/...", src="/...") with BASE. Links to repo paths (e.g. "Legacy/...",
    from AI-DISCLOSURE.md) point at GitHub. Done here, after translation, so the translated text keeps its hash."""
    html_text = REPO_HREF.sub(lambda m: 'href="' + GH_BLOB + m.group(1) + '"', html_text)
    if not BASE:
        return html_text
    html_text = re.sub(r'(http-equiv="refresh" content="0; url=)/(?!/)', lambda m: f'{m.group(1)}{BASE}/', html_text)
    return re.sub(r'\b(href|src|data-full|action)="/(?!/)', lambda m: f'{m.group(1)}="{BASE}/', html_text)

def md_absolute(md_text):
    """Make site-internal Markdown links absolute, so the .md copies work anywhere."""
    return re.sub(r'\]\(/(?!/)', lambda m: '](' + CFG['base_url'] + '/', md_text)

# --------------------------------------------------------------------------- text helpers

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s or 'section'

def clean_heading(raw):
    t = raw.replace('\\', '')
    t = re.sub(r'!\[[^\]]*\]\[[^\]]*\]|!\[[^\]]*\]\([^)]*\)', '', t)
    t = t.replace('**', '').replace('__', '').strip()
    return t

def is_category(raw):
    return clean_heading(raw).startswith('--')

def category_name(raw):
    return clean_heading(raw).strip('-—– ').strip()   # some headings close with an em dash instead of --

def norm(s):
    s = re.sub(r'\{[^}]*\}', '', s.lower())
    s = re.sub(r'\([^)]*\)', '', s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

PINNED_FIRST = {'documentation notation', 'distance cost tier', 'isekai history'}

def alpha_key(title):
    """Sort key for A-to-Z lists: ignores case, accents and punctuation (so "Harry's Journey" sorts as "harrys journey")."""
    t = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]', '', t).strip()

def name_score(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0
    if na == nb:
        return 1.0
    if na.rstrip('s') == nb.rstrip('s'):
        return 0.98
    if len(na) > 3 and len(nb) > 3 and (na in nb or nb in na):
        return 0.9
    return SequenceMatcher(None, na, nb).ratio()

def fix_typos(md, src):
    for wrong, right in TYPOS.get('global', {}).items():
        md = re.sub(r'\b%s\b' % re.escape(wrong), right, md)
    for wrong, right in TYPOS.get(src, {}).items():
        md = md.replace(wrong, right)
    return md

def esc(s):
    return html.escape(s, quote=True)

def first_sentences(text, n=220):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)|!\[[^\]]*\]\[[^\]]*\]', '', text)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'[*_`#>]|\\', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= n:
        return t
    cut = t[:n + 1]
    # end on the last whole sentence (keeping a closing quote mark), else on a whole word with an ellipsis
    ends = [m.end() for m in re.finditer(r'[.!?][”"’)]?(?= )', cut)]
    if ends and ends[-1] > 60:
        return cut[:ends[-1]]
    return cut[:n].rsplit(' ', 1)[0].rstrip(',;:—-') + '…'

def prose_only(md):
    """Markdown minus headings, pictures and rules, so a blurb starts with real sentences
    (not "Freeish (Freeishan) Freeish Kingdom The Freeish Kingdom…")."""
    keep = [l for l in md.split('\n')
            if not re.match(r'\s*(#|!\[|---|\*\*\*|<!--)', l)                  # headings, pictures, rules
            and not re.match(r'\s*[*-]\s+(#+\s*)?\*\*[^*]+\*\*:?\s*\\?\s*$', l)    # label-only bullets ("* **Isekai History**")
            and not re.match(r'\s*[*-]\s+#+\s', l)                              # bullets that are headings ("* ### None")
            and not re.match(r'\s*[*-]\s+!\[', l)                               # bullets that are pictures
            and not re.match(r'\s*([*-]\s+)?(none|tbd|n/?a|\?+)\s*\\?\s*$', l, re.I)]   # empty placeholders
    return '\n'.join(keep)

def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, '/')

def gh_link(path):
    return GH_BLOB + quote(rel(path))

# --------------------------------------------------------------------------- media

class Media:
    """Registers source images and writes web-sized copies (webp) into the site."""
    def __init__(self, out, cache, enabled=True):
        self.out, self.cache, self.enabled = out, cache, enabled
        self.jobs = {}      # key -> (source, kind)
        self.info = {}      # key -> dict(url, thumb, w, h, src)
        os.makedirs(os.path.join(out, 'media'), exist_ok=True)
        os.makedirs(cache, exist_ok=True)

    def _key(self, ident):
        return hashlib.sha1(ident.encode()).hexdigest()[:14]

    def file(self, path):
        if not os.path.exists(path):
            return None
        key = self._key(rel(path) + ':' + str(os.path.getsize(path)))
        if key not in self.info:
            self.jobs[key] = ('file', path)
            self.info[key] = {'src': rel(path), 'url': f'/media/{key}.webp', 'thumb': f'/media/{key}-t.webp'}
        return self.info[key]

    def video(self, path):
        """Copy a video (mp4/webm) into the site as is, named by its content, and return its URL. Videos are
        small and already web-ready, so they are copied even in a --no-images build."""
        if not os.path.exists(path):
            return None
        key = self._key(rel(path) + ':' + str(os.path.getsize(path)))
        ext = os.path.splitext(path)[1].lower()
        dst = os.path.join(self.out, 'media', key + ext)
        if not os.path.exists(dst):
            shutil.copyfile(path, dst)
        return {'src': rel(path), 'url': f'/media/{key}{ext}'}

    def derived(self, path, label):
        """Register a picture the build made itself (e.g. one cover cut out of a strip), labelled with its source."""
        key = self._key(label + ':' + str(os.path.getsize(path)))
        if key not in self.info:
            self.jobs[key] = ('file', path)
            self.info[key] = {'src': label, 'url': f'/media/{key}.webp', 'thumb': f'/media/{key}-t.webp'}
        return self.info[key]

    def data_uri(self, uri, origin):
        m = re.match(r'data:image/[a-z+]+;base64,(.*)', uri, re.S)
        if not m:
            return None
        raw = base64.b64decode(m.group(1))
        key = hashlib.sha1(raw).hexdigest()[:14]
        blur = BLUR.get(key, {}).get('blur')
        if blur:
            key += f'-b{blur}'  # a new name, so a cached unblurred copy is never reused
        if key not in self.info:
            p = os.path.join(self.cache, key + '.src')
            if not os.path.exists(p):
                open(p, 'wb').write(blur_image(raw, blur) if blur else raw)
            self.jobs[key] = ('file', p)
            self.info[key] = {'src': origin + ' (embedded image)', 'url': f'/media/{key}.webp', 'thumb': f'/media/{key}-t.webp'}
        return self.info[key]

    def process(self):
        todo = []
        for key, (_, path) in self.jobs.items():
            for suffix, size in (('', 1600), ('-t', 520)):
                c = os.path.join(self.cache, key + suffix + '.webp')
                if not os.path.exists(c):
                    todo.append((path, c, size))
        if todo and self.enabled:
            print(f'images: converting {len(todo)} files', flush=True)
            with ProcessPoolExecutor() as ex:
                for _ in ex.map(convert_image, todo, chunksize=4):
                    pass
        for key in self.jobs:
            for suffix in ('', '-t'):
                c = os.path.join(self.cache, key + suffix + '.webp')
                if os.path.exists(c):
                    shutil.copyfile(c, os.path.join(self.out, 'media', key + suffix + '.webp'))
            dims = os.path.join(self.cache, key + '.json')
            if os.path.exists(dims):
                self.info[key].update(json.load(open(dims)))

def convert_image(job):
    src, dst, size = job
    try:
        im = Image.open(src)
        im.draft('RGB', (size * 2, size * 2))
        if im.mode in ('P', 'LA', 'L'):
            im = im.convert('RGBA')
        elif im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGB')
        w, h = im.size
        if not dst.endswith('-t.webp'):
            json.dump({'w': w, 'h': h}, open(dst[:-5] + '.json', 'w'))
        im.thumbnail((size, size * 3), Image.LANCZOS)
        im.save(dst, 'WEBP', quality=82, method=4)
    except Exception as ex:
        print('image failed', src, ex, file=sys.stderr)

# --------------------------------------------------------------------------- markdown

class Renderer:
    def __init__(self, media):
        self.media = media
        self.md = MarkdownIt('commonmark', {'html': False, 'linkify': False, 'typographer': False}).enable(['table', 'strikethrough'])
        # markdown-it binds render rules to its renderer, so hand it plain functions
        # (a bound method gets re-bound on Python 3.12 and loses this object).
        self.md.add_render_rule('image', lambda renderer, tokens, idx, options, env: self._image(tokens, idx, options, env))
        self.md.add_render_rule('link_open', lambda renderer, tokens, idx, options, env: self._link_open(tokens, idx, options, env))
        self.md.add_render_rule('heading_open', lambda renderer, tokens, idx, options, env: self._heading_open(tokens, idx, options, env))

    def _heading_open(self, tokens, idx, options, env):
        """Give headings inside a lore entry an id ("<entry>--<heading>"), so search can link straight to them."""
        ids = env.get('ids')
        if ids is not None and idx + 1 < len(tokens):
            text = clean_heading(tokens[idx + 1].content)
            if text:
                base = ids['prefix'] + '--' + slugify(text)
                a, n = base, 2
                while a in ids['used']:
                    a, n = f'{base}-{n}', n + 1
                ids['used'].add(a)
                tokens[idx].attrSet('id', a)
        return self.md.renderer.renderToken(tokens, idx, options, env)

    def _image(self, tokens, idx, options, env):
        t = tokens[idx]
        src = t.attrGet('src') or ''
        alt = self.md.renderer.renderInlineAsText(t.children or [], options, env)
        if src.lower().endswith(VIDEO_EXT):  # ![caption](clip.mp4) becomes a video player
            v = self.video_file(src, env)
            return video_figure(v['url'], alt or default_alt(v['src'])) if v else ''
        info = self.resolve(src, env)
        if not info:
            if src.startswith('http'):
                return f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy">'
            return ''
        alt = alt or ALT.get(info['src'], {}).get('alt') or default_alt(info['src'])
        w = f' width="{info["w"]}" height="{info["h"]}"' if info.get('w') else ''
        return (f'<a class="img-link" href="{info["url"]}" data-full="{info["url"]}">'
                f'<img src="{info["url"]}" alt="{esc(alt)}" loading="lazy"{w}></a>')

    def _link_open(self, tokens, idx, options, env):
        t = tokens[idx]
        href = t.attrGet('href') or ''
        if href.startswith('http'):
            t.attrSet('rel', 'noopener')
        return self.md.renderer.renderToken(tokens, idx, options, env)

    def resolve(self, src, env):
        if src.startswith('data:'):
            return self.media.data_uri(src, env.get('origin', ''))
        if src.startswith('http'):
            return None
        base = env.get('base', ROOT)
        p = os.path.normpath(os.path.join(base, unquote(src)))
        if not os.path.exists(p) and os.path.isdir(os.path.dirname(p)):
            low = os.path.basename(p).lower()  # the docs sometimes differ in letter case (Worldmap.png)
            for f in os.listdir(os.path.dirname(p)):
                if f.lower() == low:
                    p = os.path.join(os.path.dirname(p), f)
                    break
        return self.media.file(p)

    def video_file(self, src, env):
        if src.startswith('http'):
            return None
        return self.media.video(os.path.normpath(os.path.join(env.get('base', ROOT), unquote(src))))

    def render(self, text, base=ROOT, origin='', refs=None, ids=None):
        if refs:
            text = re.sub(r'!\[([^\]]*)\]\[(image\d+)\]', lambda m: f'![{m.group(1)}]({refs[m.group(2)]})' if m.group(2) in refs else '', text)
        text = re.sub(r'!\[[^\]]*\]\[image\d+\]', '', text)  # references with no image behind them
        out = self.md.render(text, {'base': base, 'origin': origin, 'ids': ids})
        return re.sub(r'<p>(<figure class="hv-video">.*?</figure>)</p>', r'\1', out)  # a figure can't sit inside a <p>

def heading_sections(block):
    """(id, title, text below it) for every heading with an id in a block of rendered HTML."""
    out = []
    for m in re.finditer(r'<h([1-6]) id="([^"]+)">(.*?)</h\1>(.*?)(?=<h[1-6][ >]|$)', block, re.S):
        title = html.unescape(re.sub(r'<[^>]+>', '', m.group(3))).strip()
        text = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(4)))
        out.append((m.group(2), title, first_sentences(text, 300)))
    return out

def sub_heading_search(pub_html, bts_html, url, section, entry_title, entry_bts):
    """Search results for the headings inside a lore entry (e.g. "Sigil Rings" inside Darfaries Interface),
    so a term that is a heading, not an entry of its own, can still be found. Public first; a heading
    only in the full notes is Behind The Scenes."""
    items, seen = {}, {norm(entry_title)}
    for block, bts in ((pub_html, entry_bts), (bts_html, True)):
        for anchor, title, text in heading_sections(block):
            k = norm(title)
            if not k or k in seen and k not in items:
                continue
            if k in items:
                if bts and not items[k]['xb']:
                    items[k]['xb'] = text
                continue
            seen.add(k)
            items[k] = {'t': title, 'u': url + '#' + anchor, 's': section,
                        'x': '' if bts else text, 'xb': text, 'b': bts, 'sub': True}
    return list(items.values())

VIDEO_EXT = ('.mp4', '.webm')

def video_figure(url, caption):
    """Reusable component: a captioned video player (styles in site/css/video.css).

    Usage: video_figure('/media/abc.mp4', 'Feeding energy') -> <figure class="hv-video">...</figure>
    In Legacy or content markdown, write ![caption](path/to/clip.mp4) and the renderer calls this.
    Options: url (the video file), caption (shown under the player and used as its accessible name).
    It never autoplays, shows the browser's own keyboard-friendly controls, loads only the first frame
    until played (preload="metadata"), and offers a download link where video can't play."""
    c = esc(caption)
    return (f'<figure class="hv-video"><video controls preload="metadata" playsinline aria-label="{c}" src="{esc(url)}">'
            f'<a href="{esc(url)}">{c} (video)</a></video><figcaption>{c}</figcaption></figure>')

def default_alt(src):
    stem = os.path.splitext(os.path.basename(src))[0]
    folder = os.path.basename(os.path.dirname(src))
    return f'{stem} ({folder} illustration)'

# --------------------------------------------------------------------------- Legacy parsing

def split_refs(text):
    refs = {}
    def grab(m):
        refs[m.group(1)] = m.group(2)
        return ''
    text = re.sub(r'^\[(image\d+)\]:\s*<(data:image/[^>]+)>\s*$', grab, text, flags=re.M)
    return text, refs

def parse_lore(path):
    """Split a Behind The Scenes lore file into intro, categories and entries."""
    text, refs = split_refs(read_legacy(path))
    blocks, cur = [], {'kind': 'intro', 'title': '', 'lines': []}
    blocks.append(cur)
    for line in text.split('\n'):
        m = re.match(r'^# (.*)$', line)
        if not m:
            cur['lines'].append(line)
            continue
        raw = m.group(1).strip()
        imgs = re.findall(r'!\[[^\]]*\]\[[^\]]*\]|!\[[^\]]*\]\([^)]*\)', raw)
        title = clean_heading(raw)
        if not title:
            if imgs:
                cur['lines'].extend(['', *imgs, ''])
            continue
        kind = 'category' if is_category(raw) else 'entry'
        cur = {'kind': kind, 'title': category_name(raw) if kind == 'category' else title, 'lines': list(imgs)}
        blocks.append(cur)
    for b in blocks:
        b['body'] = '\n'.join(b['lines']).strip('\n')
        del b['lines']
    return blocks, refs

ABRIDGED = os.path.join(CONTENT, 'bts')   # abridged Behind The Scenes text (issue #103)

def load_abridged(src):
    """The abridged version of a Behind The Scenes doc, if there is one: {norm(entry title): Markdown}.
    content/bts/<same path as under Legacy/Behind The Scenes>, with one "# <entry title>" per abridged entry
    ("# <category> › <entry title>" when the same title appears under two categories).
    "# _intro" replaces the doc's intro (empty hides it). Entries not listed fall back to the raw Legacy text."""
    path = os.path.join(ABRIDGED, src)
    if not os.path.exists(path):
        return {}
    text = open(path, encoding='utf-8').read()
    text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.S)   # front matter: notes for editors
    out, cur = {}, None
    for line in text.split('\n'):
        m = re.match(r'^# (.+?)\s*$', line)
        if m:
            h = m.group(1)
            # "# <category> › <entry>" scopes an entry whose title repeats under another category
            cur = '_intro' if h == '_intro' else '/'.join(norm(x) for x in h.split(' › ', 1))
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: '\n'.join(v).strip('\n') for k, v in out.items()}

ABRIDGED_NOTE = ('<p class="abridged-note">Abridged from the author\'s original notes with the help of AI: his ramblings and '
                 'brain dumps rewritten into a more readable form. The original notes are below, and kept in the repository.</p>')

WD_RE = re.compile(r'^(\s*)[*-] \*\*(?:Website Description|Web Description)\*\*\s*$', re.I)

def extract_website_description(body):
    lines = body.split('\n')
    out, keep, i = [], [], 0
    while i < len(lines):
        m = WD_RE.match(lines[i])
        if m:
            ind = len(m.group(1).expandtabs(4))
            i += 1
            while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > ind):
                s = lines[i].strip()
                if s:
                    out.append(re.sub(r'^[*-]\s+', '', s))
                i += 1
            continue
        keep.append(lines[i])
        i += 1
    wd = '\n\n'.join(out).strip()
    if re.sub(r'[^a-z]', '', wd.lower()) in ('', 'none', 'tbd', 'na', 'todo'):
        wd = ''
    return wd, '\n'.join(keep).strip('\n')

def parse_public(name):
    path = os.path.join(PUB, name)
    text = read_legacy(path)
    meta = {}
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    if m:
        for line in m.group(1).split('\n'):
            k, _, v = line.partition(':')
            meta[k.strip()] = v.strip().strip('"')
        text = text[m.end():]
    text = re.sub(r'^# .*\n', '', text.lstrip(), count=1)
    sections, cur = [], {'heading': '', 'lines': []}
    sections.append(cur)
    for line in text.split('\n'):
        m = re.match(r'^#{1,3} (.*)$', line)
        if m and clean_heading(m.group(1)):
            cur = {'heading': clean_heading(m.group(1)), 'lines': []}
            sections.append(cur)
        else:
            cur['lines'].append(line)
    for s in sections:
        s['md'] = '\n'.join(s['lines']).strip()
        s['page'] = meta.get('title', name)
        s['file'] = name
        del s['lines']
    intro = sections.pop(0)
    return meta, intro, [s for s in sections if s['md'] or s['heading']]

def strip_images(md):
    return re.sub(r'!\[[^\]]*\]\([^)]*\)\s*', '', md).strip()

def first_image(md):
    m = re.search(r'!\[[^\]]*\]\(([^)]+)\)', md)
    return m.group(1) if m else None

# --------------------------------------------------------------------------- art index

class Art:
    def __init__(self):
        self.files = []
        root = os.path.join(BTS, 'Illustrations')
        for d, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    self.files.append(os.path.join(d, f))
        self.files.sort()

    def find(self, name, folders):
        best, score = None, 0
        dirs = [os.path.join(BTS, f) for f in folders]
        for p in self.files:
            if dirs and not any(p.startswith(d + os.sep) for d in dirs):
                continue
            stem = os.path.splitext(os.path.basename(p))[0]
            stem = re.sub(r'^(Insignia \d+ )', '', stem)
            s = name_score(name, stem)
            if s > score:
                best, score = p, s
        return best if score >= 0.86 else None

# --------------------------------------------------------------------------- page model

class Page:
    def __init__(self, url, title, section, layer='public', desc=''):
        self.url, self.title, self.section, self.layer, self.desc = url, title, section, layer, desc
        self.html = ''          # main content html
        self.md_public = ''     # markdown twin, public part
        self.md_bts = ''        # markdown twin, behind the scenes part
        self.toc = []           # (anchor, title, layer)
        self.sources = []       # Legacy paths
        self.search = []        # dicts for the search index
        self.jsonld = None
        self.prev = self.next = None

# --------------------------------------------------------------------------- builders

class Builder:
    def __init__(self, out, cache, images=True):
        self.out = out
        self.media = Media(out, cache, images)
        self.r = Renderer(self.media)
        self.art = Art()
        self.pages = []
        self.glossary = []
        self.used_art = set()

    # ---- helpers
    def add(self, page):
        # make repeated anchors unique (two blog sections can share a heading)
        seen = {}
        toc = []
        for anchor, title, layer, kind in page.toc:
            n = seen.get(anchor, 0)
            seen[anchor] = n + 1
            if n:
                new_anchor = f'{anchor}-{n + 1}'
                page.html = _renumber(page.html, anchor, n, new_anchor)
                anchor = new_anchor
            toc.append((anchor, title, layer, kind))
        page.toc = toc
        self.pages.append(page)
        return page

    def figure(self, info, caption=None):
        if not info:
            return ''
        alt = ALT.get(info['src'], {}).get('alt') or default_alt(info['src'])
        w = f' width="{info["w"]}" height="{info["h"]}"' if info.get('w') else ''
        cap = f'<figcaption>{esc(caption)}</figcaption>' if caption else ''
        return (f'<figure class="art"><a class="img-link" href="{info["url"]}" data-full="{info["url"]}">'
                f'<img src="{info["thumb"]}" alt="{esc(alt)}" loading="lazy"{w}></a>{cap}</figure>')

    def abridged_block(self, abridged_md, raw_md, refs, origin, ids=None):
        """Abridged Behind The Scenes text (issue #103), the AI note, and the raw notes behind a toggle (kept in English)."""
        html_out = self.md_bts_block(abridged_md, refs, origin, ids=ids) + ABRIDGED_NOTE
        if raw_md.strip():   # a section heading with no raw notes of its own has nothing to show
            raw_html = self.md_bts_block(raw_md, refs, origin)
            html_out += f'<details class="raw-notes" translate="no" lang="en"><summary>Show the original notes</summary>{raw_html}</details>'
        return html_out

    def md_bts_block(self, md, refs, origin, ids=None):
        return self.r.render(fix_typos(md, origin), base=os.path.join(ROOT, os.path.dirname(origin)), origin=origin, refs=refs, ids=ids)

    def story_notes_abridged(self, path, src, abridged):
        """A story-notes page with its abridged text (issue #103): each book (category) and chapter (entry)
        becomes its own section, abridged where content/bts has it, with the raw notes behind a toggle."""
        blocks, refs = parse_lore(path)
        origin = rel(path)
        # the notes open with a "# SPOILER WARNING!" heading: that's the doc's intro, not a chapter
        if len(blocks) > 1 and not blocks[0]['body'].strip() and blocks[1]['kind'] == 'entry' \
                and blocks[1]['title'].lower().startswith('spoiler warning'):
            blocks[0]['body'] = f"**{blocks[1]['title']}**\n\n{blocks[1]['body']}"
            del blocks[1]
        out, category, used = [], None, set()
        for b in blocks:
            if b['kind'] == 'intro':
                ab = abridged.get('_intro')
            elif b['kind'] == 'entry' and category and f"{norm(category['title'])}/{norm(b['title'])}" in abridged:
                ab = abridged[f"{norm(category['title'])}/{norm(b['title'])}"]
            else:
                ab = abridged.get(norm(b['title']))
            used.update(k for k, v in abridged.items() if v is ab)
            if b['kind'] == 'category':
                category = b
                anchor = 'cat-' + slugify(b['title'])
                out.append(f'<h2 class="category" id="{anchor}">{esc(b["title"])}</h2>')
            elif b['kind'] == 'entry':
                anchor = slugify(f"{category['title']} {b['title']}" if category else b['title'])
                out.append(f'<h3 id="{anchor}">{esc(b["title"])}</h3>')
            if ab is not None:
                out.append(self.abridged_block(ab, b['body'], refs, origin))
            elif b['body'].strip():
                out.append(self.md_bts_block(b['body'], refs, origin))
        for k in abridged.keys() - used:
            print(f'warning: abridged section "{k}" in content/bts/{src} matches no book or chapter', file=sys.stderr)
        return '\n'.join(out)

    # ---- lore topics
    def build_topic(self, t):
        url = f'/lore/{t["slug"]}/'
        page = Page(url, t['title'], 'World Lore')
        public_sections, public_intros = [], []
        for name in t['public']:
            meta, intro, secs = parse_public(name)
            page.sources.append(rel(os.path.join(PUB, name)))
            if intro['md']:
                public_intros.append(intro)
            skip = {norm(x) for x in t.get('exclude_public', [])}
            public_sections.extend(x for x in secs if norm(x['heading']) not in skip)
        entries, intro_bts, refs_all = [], [], {}
        for src in t['bts']:
            path = os.path.join(BTS, src)
            page.sources.append(rel(path))
            blocks, refs = parse_lore(path)
            origin = rel(path)
            abridged = load_abridged(src)
            category, used = None, set()
            for b in blocks:
                b['origin'], b['refs'] = origin, refs
                if b['kind'] == 'intro':
                    b['abridged'] = abridged.get('_intro')
                elif b['kind'] == 'entry' and category and f"{norm(category['title'])}/{norm(b['title'])}" in abridged:
                    b['abridged'] = abridged[f"{norm(category['title'])}/{norm(b['title'])}"]
                else:
                    b['abridged'] = abridged.get(norm(b['title']))
                used.update(k for k, v in abridged.items() if v is b['abridged'])
                if b['kind'] == 'intro':
                    if b['abridged'] is not None:
                        b['body'] = b['abridged']   # the intro is replaced outright (often a note to self)
                    if b['body'].strip():
                        intro_bts.append(b)
                elif b['kind'] == 'category':
                    category = b
                    b['entries'] = []
                    entries.append(b)
                else:
                    b['category'] = category
                    if category:
                        category['entries'].append(b)
                    else:
                        entries.append(b)
            for k in abridged.keys() - used:   # a heading in content/bts that matches no category or entry
                print(f'warning: abridged section "{k}" in content/bts/{src} matches no category or entry', file=sys.stderr)
        # A to Z within each category (author's rule, see CLAUDE.md). Notes about the docs themselves
        # (Documentation Notation, Distance Cost Tier, Isekai History) stay first. Topics whose order means
        # something (a timeline, tiers, colour order) set "order": "source" in content/site.json.
        if t.get('order') != 'source':
            pinned = lambda b: b['title'].lower() in PINNED_FIRST
            def az(lst):
                return [b for b in lst if pinned(b)] + sorted((b for b in lst if not pinned(b)), key=lambda b: alpha_key(b['title']))
            for b in entries:
                if b['kind'] == 'category':
                    b['entries'] = az(b['entries'])
            # top-level entries sort among themselves; categories keep their place in the doc
            loose = az([b for b in entries if b['kind'] != 'category' or not b['entries']])
            it = iter(loose)
            entries = [next(it) if (b['kind'] != 'category' or not b['entries']) else b for b in entries]
        # flatten: categories without entries act as entries themselves
        flat = []
        for b in entries:
            if b['kind'] == 'category' and b['entries']:
                flat.append(('cat', b))
                for e in b['entries']:
                    flat.append(('entry', e))
            elif b['kind'] == 'category':
                flat.append(('entry', b))
            else:
                flat.append(('entry', b))
        meta_cats = ('documentation notation', 'distance cost tier')
        # match public sections to entries
        used = set()
        ents = [b for k, b in flat if k == 'entry']
        for e in ents:
            e['public_secs'] = []
        for i, s in enumerate(public_sections):
            best, score = None, 0
            for e in ents:
                sc = name_score(s['heading'], e['title'])
                if sc > score:
                    best, score = e, sc
            if best and score >= 0.84:
                best['public_secs'].append(s)
                used.add(i)
        # whole blog pages that match an entry (e.g. "Kingdom - Gandew" -> Gandew)
        for e in ents:
            for i, s in enumerate(public_sections):
                if i in used:
                    continue
                pt = re.sub(r'^(Kingdom|City|Science)\s*-\s*', '', s['page'])
                if name_score(pt, e['title']) >= 0.9:
                    e['public_secs'].append(s)
                    used.add(i)
        leftovers = [s for i, s in enumerate(public_sections) if i not in used]
        if t.get('order') != 'source':  # blog sections with no matching doc entry: A to Z among themselves
            leftovers.sort(key=lambda s_: alpha_key(s_['heading'] or s_['page']))

        body = []
        # intro
        intro_html_pub = ''.join(self.r.render(fix_typos(s['md'], s['file']), base=PUB, origin=s['file']) for s in public_intros)
        summ = SUMMARIES.get(t['slug'])
        if not intro_html_pub and summ:
            intro_html_pub = (self.r.render(summ['md']) + '<p class="src">Summary written by AI from the author\'s notes ('
                              + ', '.join(f'<a href="{GH_BLOB}{quote(x)}">{esc(x.split("/")[-1])}</a>' for x in summ['sources'])
                              + '). <a href="/about/ai-disclosure/">AI disclosure</a></p>')
            public_intros.append({'md': summ['md'] + '\n\n*(Summary written by AI from the author\'s notes.)*', 'file': 'content/summaries.json'})
        if intro_html_pub:
            body.append(f'<div class="layer public intro">{intro_html_pub}</div>')
            page.md_public += '\n\n'.join(strip_images(s['md']) for s in public_intros) + '\n\n'
        for b in intro_bts:
            body.append(f'<div class="layer bts intro"><p class="bts-label">Behind the Scenes · notes</p>{self.md_bts_block(b["body"], b["refs"], b["origin"])}</div>')
            page.md_bts += b['body'] + '\n\n'
        hidden_count = 0
        for kind, b in flat:
            if kind == 'cat':
                is_meta = b['title'].lower() in meta_cats
                cls = 'bts' if is_meta or not any(e['public_secs'] or extract_website_description(e['body'])[0] for e in b['entries']) else 'both'
                anchor = 'cat-' + slugify(b['title'])
                body.append(f'<h2 class="category layer {cls}" id="{anchor}">{esc(b["title"])}</h2>')
                page.toc.append((anchor, b['title'], cls, 'cat'))
                if b['body'].strip() or b.get('abridged'):
                    notes = (self.abridged_block(b['abridged'], b['body'], b['refs'], b['origin']) if b.get('abridged')
                             else self.md_bts_block(b["body"], b["refs"], b["origin"]))
                    body.append(f'<div class="layer bts cat-notes">{notes}</div>')
                    page.md_bts += f'## {b["title"]}\n\n{b["body"]}\n\n'
                else:
                    page.md_bts += f'## {b["title"]}\n\n'
                if cls != 'bts':
                    page.md_public += f'## {b["title"]}\n\n'
                continue
            e = b
            is_meta = e['title'].lower() in meta_cats
            wd, rest = extract_website_description(e['body'])
            secs = e['public_secs']
            pub_render = '\n\n'.join((f'#### {x["heading"]}\n\n' if len(secs) > 1 and x['heading'] and norm(x['heading']) != norm(e['title']) else '') + x['md'] for x in secs)
            pub_md = strip_images(pub_render) or wd
            if not secs:
                pub_render = wd
            pub_src = ', '.join(sorted({s['file'] for s in e['public_secs']})) or ('Website Description in ' + e['origin'] if wd else '')
            img_src = None
            for s in e['public_secs']:
                fi = first_image(s['md'])
                if fi and not fi.startswith('http'):
                    img_src = self.r.resolve(fi, {'base': PUB})
                    # the first picture becomes the entry's figure; the rest stay in the text
                    pub_render = re.sub(r'!\[[^\]]*\]\(' + re.escape(fi) + r'\)\s*', '', pub_render, count=1)
                    break
            if not img_src and e['title'] in t.get('entry_image', {}):
                # the author's pick for this entry's picture (the name match can't know the King is Itagiba)
                img_src = self.media.file(os.path.join(BTS, t['entry_image'][e['title']]))
            if not img_src:
                p = self.art.find(e['title'], t.get('art', []))
                if p:
                    img_src = self.media.file(p)
            if img_src:
                self.used_art.add(img_src['src'])
            anchor = slugify(e['title'])
            layer = 'both' if pub_md and not is_meta else 'bts'
            if layer == 'bts':
                hidden_count += 1
            page.toc.append((anchor, e['title'], layer, 'entry'))
            h = [f'<section class="entry layer {layer}" id="{anchor}">', f'<h3>{esc(e["title"])}</h3>']
            fig = self.figure(img_src)
            ids = {'prefix': anchor, 'used': set()}
            pub_html = bts_html = ''
            if pub_md:
                pub_html = self.r.render(pub_render, base=PUB, ids=ids)
                h.append(f'<div class="layer public">{fig}{pub_html}'
                         f'<p class="src src-pub">Public text: {esc(pub_src)}</p></div>')
            if rest.strip() or wd:
                bts_md = rest if pub_md == wd else e['body']
                if e.get('abridged'):
                    bts_html = self.abridged_block(e['abridged'], bts_md, e["refs"], e["origin"], ids=ids)
                else:
                    bts_html = self.md_bts_block(bts_md, e["refs"], e["origin"], ids=ids)
                if t.get('glyph_tables'):
                    bts_html = glyph_grids(bts_html, e['title'])
                if e['title'] == t.get('scribe_in'):
                    bts_html = scribe_html() + bts_html
                for ap in t.get('entry_art', {}).get(e['title'], []):
                    info = self.media.file(os.path.join(BTS, ap))
                    if info:
                        self.used_art.add(info['src'])
                        bts_html += self.figure(info, os.path.splitext(os.path.basename(ap))[0]).replace('<figure class="art">', '<figure class="art wide">')
                label = 'Behind the Scenes · notes, abridged' if e.get('abridged') else 'Behind the Scenes · full notes'
                h.append(f'<div class="layer bts">{"" if pub_md else fig}<p class="bts-label">{label}</p>'
                         f'{bts_html}'
                         f'<p class="src">Source: <a href="{gh_link(os.path.join(ROOT, e["origin"]))}">{esc(e["origin"])}</a></p></div>')
            h.append('</section>')
            body.append('\n'.join(h))
            if pub_md:
                page.md_public += f'### {e["title"]}\n\n{pub_md}\n\n'
            page.md_bts += f'### {e["title"]}\n\n{e["body"]}\n\n'
            gl_desc = first_sentences(prose_only(pub_md)) if pub_md else first_sentences(prose_only(rest))
            if not is_meta:
                self.glossary.append({'term': e['title'], 'topic': t['title'], 'url': url + '#' + anchor,
                                      'public': bool(pub_md), 'desc': gl_desc,
                                      'category': (e.get('category') or {}).get('title', '')})
            page.search.append({'t': e['title'], 'u': url + '#' + anchor, 's': t['title'],
                                'x': first_sentences(pub_md or '', 300), 'xb': first_sentences(e.get('abridged') or e['body'], 400),
                                'b': layer == 'bts'})
            section = t['title'] if norm(e['title']) == norm(t['title']) else f'{t["title"]} · {e["title"]}'
            page.search.extend(sub_heading_search(pub_html, bts_html, url, section,
                                                  e['title'], layer == 'bts'))
        bts_now = False
        for s in leftovers:
            anchor = slugify(s['heading'] or s['page'])
            layer = 'bts' if bts_now else 'both'
            if t.get('bts_after') and s['heading'].startswith(t['bts_after']):
                bts_now = True  # everything after this heading is Behind The Scenes (author's choice)
            fi = first_image(s['md'])
            info = self.r.resolve(fi, {'base': PUB}) if fi and not fi.startswith('http') else None
            if not info:
                p = self.art.find(s['heading'], t.get('art', []))
                info = self.media.file(p) if p else None
            page.toc.append((anchor, s['heading'] or s['page'], layer, 'entry'))
            inner = (f'{self.figure(info)}{self.r.render(strip_images(s["md"]), base=PUB)}'
                     f'<p class="src src-pub">Public text: {esc(s["file"])}</p>')
            if layer == 'bts':
                hidden_count += 1
                inner = f'<div class="layer bts"><p class="bts-label">Behind the Scenes</p>{inner}</div>'
            else:
                inner = f'<div class="layer public">{inner}</div>'
            body.append(f'<section class="entry layer {layer}" id="{anchor}"><h3>{esc(s["heading"] or s["page"])}</h3>{inner}</section>')
            if layer == 'bts':
                page.md_bts += f'### {s["heading"]}\n\n{strip_images(s["md"])}\n\n'
            else:
                page.md_public += f'### {s["heading"]}\n\n{strip_images(s["md"])}\n\n'
            page.search.append({'t': s['heading'] or s['page'], 'u': url + '#' + anchor, 's': t['title'],
                                'x': '' if layer == 'bts' else first_sentences(s['md'], 300),
                                'xb': first_sentences(s['md'], 300), 'b': layer == 'bts'})
        if hidden_count:
            body.append(f'<p class="layer public-only more-bts">{hidden_count} more entr{"y" if hidden_count == 1 else "ies"} '
                        f'on this page {"is" if hidden_count == 1 else "are"} only in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        if not t['public']:
            body.insert(0, '<p class="layer public-only notice">The blog never had a public page for this topic, so Public mode shows a short summary. '
                           'The full entries are in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        page.html = '\n'.join(body)
        page.desc = first_sentences(prose_only(page.md_public or page.md_bts), 160)
        page.card = first_sentences(prose_only(page.md_public or page.md_bts), 140)  # the blurb on the World Lore page
        self.add(page)
        return page

    # ---- novel
    def parse_volume(self, v):
        path = os.path.join(BTS, v['source'])
        text, refs = split_refs(read_legacy(path))
        base = os.path.dirname(path)
        front, chapters, cur, sub = [], [], None, None
        def new_chapter(title):
            nonlocal cur, sub
            cur = {'title': title, 'subs': [], 'intro': []}
            chapters.append(cur)
            sub = None
        for line in text.split('\n'):
            m = re.match(r'^# (.*)$', line)
            stripped = line.strip()
            if m:
                raw = m.group(1).strip()
                sm = re.match(r'^(\d+)\s*!\[[^\]]*\]\(([^)]+)\)', raw)
                if sm:
                    if cur is None:
                        new_chapter('Prologue')
                    sub = {'n': int(sm.group(1)), 'img': sm.group(2), 'lines': []}
                    cur['subs'].append(sub)
                    continue
                title = clean_heading(raw)
                if title:
                    if cur is None and not re.match(r'(prologue|chapter|epilogue|afterword)', title, re.I):
                        front.extend(['', f'## {title}', ''])
                        imgs = re.findall(r'!\[[^\]]*\]\[[^\]]*\]|!\[[^\]]*\]\([^)]*\)', raw)
                        front.extend(imgs)
                        continue
                    new_chapter(title)
                    continue
                imgs = re.findall(r'!\[[^\]]*\]\[[^\]]*\]|!\[[^\]]*\]\([^)]*\)', raw)
                (sub['lines'] if sub else (cur['intro'] if cur else front)).extend(imgs)
                continue
            if stripped == '**Prologue**' and (cur is None or cur['title'] != 'Prologue'):
                new_chapter('Prologue')
                continue
            target = sub['lines'] if sub else (cur['intro'] if cur else front)
            target.append(line.lstrip('\t').lstrip() if not stripped.startswith(('* ', '- ')) else line)
        return path, base, refs, front, chapters

    def covers(self):
        """The real book covers, cut out of the old blog's strip of all four (images/172.png), by volume slug."""
        if hasattr(self, '_covers'):
            return self._covers
        self._covers = {}
        c = CFG.get('covers')
        if not c:
            return self._covers
        src = os.path.join(PUB, c['source'])
        im = Image.open(src).convert('RGBA')
        alpha = im.getchannel('A')
        w, h = im.size
        filled = [alpha.crop((x, 0, x + 1, h)).getextrema()[1] > 20 for x in range(w)]
        runs, start = [], None
        for x, f in enumerate(filled + [False]):  # the covers are separated by transparent gaps
            if f and start is None:
                start = x
            elif not f and start is not None:
                runs.append((start, x)); start = None
        if len(runs) != len(c['order']):
            print(f'warning: found {len(runs)} covers in {c["source"]}, expected {len(c["order"])}', file=sys.stderr)
        os.makedirs(self.media.cache, exist_ok=True)
        for slug, (x0, x1) in zip(c['order'], runs):
            out = os.path.join(self.media.cache, f'cover-{slug}.png')
            im.crop((x0, 0, x1, h)).save(out)
            self._covers[slug] = self.media.derived(out, f'{rel(src)} (cover {c["order"].index(slug) + 1} of {len(runs)})')
        return self._covers

    def chronology(self):
        """The blog's Story Chronology page: one timeline picture per volume, plus the Time Keeper quick reference."""
        if hasattr(self, '_chrono'):
            return self._chrono
        self._chrono = {'vols': {}, 'intro': '', 'keeper': None}
        name = CFG.get('novel_chronology')
        if not name:
            return self._chrono
        meta, intro, secs = parse_public(name)
        label = None
        for line in [l.strip() for l in (intro['md'] + '\n' + '\n'.join(s_['md'] for s_ in secs)).split('\n')]:
            img = re.match(r'!\[[^\]]*\]\(([^)]+)\)', line)
            if img and label:
                if 'time keeper' in label.lower():
                    self._chrono['keeper'] = (label, img.group(1))
                else:
                    self._chrono['vols'][norm(label)] = (label, img.group(1))
                label = None
            elif line and not img:
                if not self._chrono['intro'] and not label and not self._chrono['vols']:
                    self._chrono['intro'] = line
                label = line
        return self._chrono

    def chronology_html(self, vol_title):
        """Behind The Scenes section for one volume: its timeline, then the Time Keeper quick reference."""
        c = self.chronology()
        hit = c['vols'].get(norm(vol_title))
        if not hit:
            return '', ''
        figs, md = [], [f'## Story Chronology\n\n{c["intro"]}\n']
        for label, src in [hit] + ([c['keeper']] if c['keeper'] else []):
            info = self.r.resolve(src, {'base': PUB})
            figs.append(f'<h3>{esc(label)}</h3>' + (f'<figure class="chrono"><a class="img-link" href="{info["url"]}" data-full="{info["url"]}">'
                        f'<img src="{info["url"]}" alt="{esc(ALT.get(info["src"], {}).get("alt") or label + " timeline table")}" loading="lazy"></a></figure>' if info else ''))
            md.append(f'### {label}\n\n![{label}]({info["url"] if info else src})\n')
        # Behind The Scenes only (author's choice), even though the blog showed it
        return (f'<section id="story-chronology" class="layer bts chrono-section"><h2>Story Chronology</h2>'
                f'<p class="bts-label">Behind the Scenes</p><p>{esc(c["intro"])}</p>{"".join(figs)}'
                f'<p class="src">From the original blog page: <a href="https://husbandoutworld.blogspot.com/p/story-chronology.html">Story Chronology</a> '
                f'(archived in <a href="{gh_link(os.path.join(PUB, CFG["novel_chronology"]))}">{esc(rel(os.path.join(PUB, CFG["novel_chronology"])))}</a>)</p></section>'), '\n'.join(md)

    def build_novel(self):
        vols_html = []
        all_chapter_pages = []
        for vi, v in enumerate(CFG['volumes']):
            path, base, refs, front, chapters = self.parse_volume(v)
            vurl = f'/novel/{v["slug"]}/'
            vpage = Page(vurl, v['title'], 'Light Novel')
            vpage.sources.append(rel(path))
            front_md = '\n'.join(front).strip()
            toc = []
            chapter_pages = []
            for ci, ch in enumerate(chapters):
                t = ch['title']
                if t.lower().startswith('chapter'):
                    num = re.match(r'chapter\s+([ivxlc]+)', t, re.I)
                    cslug = 'chapter-' + str(roman(num.group(1))) if num else slugify(t)
                else:
                    cslug = slugify(t)
                curl = vurl + cslug + '/'
                cp = Page(curl, f'{t} · {v["title"]}', 'Light Novel')
                cp.sources.append(rel(path))
                parts = [f'<p class="eyebrow"><a href="{vurl}">{esc(v["title"])}</a> · {esc(v["arc"])}</p>',
                         f'<h1 class="chapter-title">{esc(t)}</h1>', amazon_note()]
                mdp = [f'# {t}\n\n*{v["title"]}*\n']
                if ch['intro']:
                    imd = '\n'.join(ch['intro']).strip()
                    if imd:
                        parts.append(self.r.render(imd, base=base, origin=rel(path), refs=refs))
                        mdp.append(imd)
                for s in ch['subs']:
                    info = self.r.resolve(s['img'], {'base': base})
                    smd = one_paragraph_per_line(s['lines'])
                    parts.append(f'<section class="subchapter" id="part-{s["n"]}"><div class="sub-n">{s["n"]}</div>'
                                 f'{self.figure(info)}{self.r.render(fix_typos(smd, rel(path)), base=base, origin=rel(path), refs=refs)}</section>')
                    mdp.append(f'## {s["n"]}\n\n![Subchapter illustration]({s["img"]})\n\n{smd}')
                    if info:
                        self.used_art.add(info['src'])
                cp.html = '\n'.join(parts)
                cp.md_public = '\n\n'.join(mdp)
                cp.desc = first_sentences('\n'.join('\n'.join(s['lines']) for s in ch['subs'][:1]) or t, 160)
                cp.search.append({'t': t, 'u': curl, 's': v['title'], 'x': cp.desc, 'b': False})
                cp.jsonld = {'@context': 'https://schema.org', '@type': 'Chapter', 'name': t,
                             'isPartOf': {'@type': 'Book', 'name': v['title'], 'url': CFG['base_url'] + vurl},
                             'author': {'@type': 'Person', 'name': CFG['author']}}
                chapter_pages.append(cp)
                toc.append((curl, t, len(ch['subs'])))
            for a, b in zip(chapter_pages, chapter_pages[1:]):
                a.next, b.prev = b, a
            all_chapter_pages.extend(chapter_pages)
            vparts = [f'<p class="eyebrow">{esc(v["arc"])}</p>', f'<h1>{esc(v["title"])}</h1>', amazon_note(),
                      f'<div class="front">{self.r.render(front_md, base=base, origin=rel(path), refs=refs)}</div>',
                      '<h2>Chapters</h2><ol class="chapter-list">']
            for curl, t, n in toc:
                vparts.append(f'<li><a href="{curl}">{esc(t)}</a> <span class="muted">{n} subchapter{"s" if n != 1 else ""}</span></li>' if n else f'<li><a href="{curl}">{esc(t)}</a></li>')
            vparts.append('</ol>')
            vpage.md_public = f'# {v["title"]}\n\n{front_md}\n\n' + '\n'.join(f'- [{t}]({u}index.md)' for u, t, _ in toc)
            ch_html, ch_md = self.chronology_html(v['title'])
            if ch_html:
                vparts.append(ch_html)
                vpage.md_bts += ch_md
                vpage.sources.append(rel(os.path.join(PUB, CFG['novel_chronology'])))
            vpage.html = '\n'.join(vparts)
            vpage.desc = f'{v["title"]}, {v["arc"]} of the #HusbandOutWorld light novel. Read it free here.'
            vpage.jsonld = {'@context': 'https://schema.org', '@type': 'Book', 'name': v['title'],
                            'isPartOf': {'@type': 'BookSeries', 'name': CFG['title']},
                            'author': {'@type': 'Person', 'name': CFG['author']},
                            'illustrator': [{'@type': 'Person', 'name': a} for a in CFG['artists']],
                            'url': CFG['base_url'] + vurl, 'sameAs': CFG['amazon_url'], 'inLanguage': 'en'}
            self.add(vpage)
            for cp in chapter_pages:
                self.add(cp)
            cover = self.covers().get(v['slug'])
            if not cover and chapters and chapters[0]['subs']:
                # the volume's first full-page colour illustration (2:3, the same shape as the book cover)
                cover = self.r.resolve(chapters[0]['subs'][0]['img'], {'base': base})
            vols_html.append((v, vurl, cover, toc))
        # announced volumes get a page too: the chapter list (not readable yet), work-in-progress label, chronology
        series = series_info()
        upcoming_urls = {}
        for u in CFG.get('upcoming_volumes', []):
            uurl = f'/novel/{u["slug"]}/'
            upcoming_urls[u['slug']] = uurl
            up = Page(uurl, u['title'], 'Light Novel')
            up.sources.append(rel(os.path.join(PUB, SERIES_PAGE)))
            info = series['vols'].get(norm(u['title']), {})
            uc = self.covers().get(u['slug'])
            chs = u.get('chapters', [])
            uparts = [f'<p class="eyebrow">{esc(u["arc"])}</p>', f'<h1>{esc(u["title"])}</h1>',
                      f'<p class="wip-line"><span class="wip-badge">Work in progress</span> <span class="muted">{esc(u["status"])}</span></p>']
            if uc:
                uparts.append(f'<figure class="art vol-wip-cover"><img src="{uc["thumb"]}" alt="{esc(ALT.get(uc["src"], {}).get("alt") or "Cover of " + u["title"])}" loading="lazy"></figure>')
            if info.get('blurb'):
                uparts.append(f'<div class="front">{self.r.render(info["blurb"], base=PUB)}</div>')
            if chs:
                uparts.append('<h2>Chapters</h2><p class="muted">The chapters can be read here once the volume is out.</p>'
                              '<ol class="chapter-list locked">' + ''.join(f'<li><span class="ch-locked">{esc(c)}</span></li>' for c in chs) + '</ol>')
            uparts.append(f'<p><a href="/novel/">← The Light Novel</a> · Catch up first: '
                          + ' · '.join(f'<a href="/novel/{v["slug"]}/">{esc(v["title"].split(" - ")[0])}</a>' for v in CFG['volumes']) + '</p>')
            up.md_public = (f'# {u["title"]}\n\n*Work in progress: {u["status"]}*\n\n{info.get("blurb", "")}\n\n'
                            + ('## Chapters (not out yet)\n\n' + '\n'.join(f'- {c}' for c in chs) if chs else ''))
            ch_html, ch_md = self.chronology_html(u['title'])
            if ch_html:
                uparts.append(ch_html)
                up.md_bts += ch_md
                up.sources.append(rel(os.path.join(PUB, CFG['novel_chronology'])))
            up.html = '\n'.join(uparts)
            up.desc = f'{u["title"]}, {u["arc"]} of the #HusbandOutWorld light novel: a work in progress ({u["status"]}).'
            up.search.append({'t': u['title'], 'u': uurl, 's': 'Light Novel', 'x': up.desc, 'b': False})
            up.jsonld = {'@context': 'https://schema.org', '@type': 'Book', 'name': u['title'], 'creativeWorkStatus': 'Incomplete',
                         'isPartOf': {'@type': 'BookSeries', 'name': CFG['title']},
                         'author': {'@type': 'Person', 'name': CFG['author']}, 'url': CFG['base_url'] + uurl, 'inLanguage': 'en'}
            self.add(up)
        # story notes (behind the scenes only)
        notes = []
        for n in CFG['story_notes']:
            path = os.path.join(BTS, n['source'])
            text, refs = split_refs(read_legacy(path))
            url = f'/novel/{n["slug"]}/'
            p = Page(url, n['title'], 'Light Novel', layer='bts')
            p.sources.append(rel(path))
            abridged = load_abridged(n['source'])
            if abridged:
                body_html = self.story_notes_abridged(path, n['source'], abridged)
            else:
                body_html = self.r.render(fix_typos(text, rel(path)), base=os.path.dirname(path), origin=rel(path), refs=refs)
            label = 'Behind the Scenes · story notes, abridged' if abridged else 'Behind the Scenes · story notes'
            p.html = (f'<h1>{esc(n["title"])}</h1>' + bts_gate('These are the author\'s story notes, including unreleased arcs.') +
                      f'<div class="layer bts"><p class="bts-label">{label}</p>{body_html}'
                      f'<p class="src">Source: <a href="{gh_link(path)}">{esc(rel(path))}</a></p></div>')
            p.md_bts = text
            p.desc = f'{n["title"]}: the author\'s story notes (spoilers).'
            p.search.append({'t': n['title'], 'u': url, 's': 'Story notes', 'xb': first_sentences(text, 400), 'b': True})
            self.add(p)
            notes.append((n, url))
        # novel index: the volumes, with the old blog's "Graphic/Light Novel Series" page merged in
        idx = Page('/novel/', 'The Light Novel', 'Light Novel')
        series = series_info()
        idx.sources.append(rel(os.path.join(PUB, SERIES_PAGE)))
        parts = ['<h1>The Light Novel</h1>', lede_html(), amazon_note()]
        mdi = [lede_text()]
        arc = series.get('arc')
        if arc:
            # (the blog's strip of four covers is cut up and shown on each volume below instead)
            arc_title = re.sub(r'\s+', ' ', arc['title'])
            parts.append(f'<section class="arc-head"><h2>{esc(arc_title)}</h2>'
                         f'{self.r.render(arc["blurb"], base=PUB)}</section>')
            mdi.append(f'## {arc_title}\n\n{arc["blurb"]}')
        parts.append('<div class="vol-list">')
        for v, vurl, cover, toc in vols_html:
            info = series['vols'].get(norm(v['title']), {})
            nch = sum(1 for _, t, _ in toc if t.lower().startswith('chapter'))
            img = (f'<img src="{cover["thumb"]}" alt="{esc(ALT.get(cover["src"], {}).get("alt") or "Cover of " + v["title"])}" loading="lazy"'
                   f'{" width=" + chr(34) + str(cover["w"]) + chr(34) + " height=" + chr(34) + str(cover["h"]) + chr(34) if cover.get("w") else ""}>') if cover else ''
            parts.append(f'<article class="vol-row" id="{v["slug"]}"><a class="vol-cover" href="{vurl}" tabindex="-1" aria-hidden="true">{img}</a><div class="vol-info">'
                         f'<h2 class="vol-title"><a href="{vurl}">{esc(v["title"])}</a></h2>'
                         + (self.r.render(info['blurb'], base=PUB) if info.get('blurb') else '')
                         + f'<p class="vol-meta">{nch} chapters' + (f' · {esc(info["size"])}' if info.get('size') else '') + '</p>'
                         + '</div>'  # the actions are the card's own second row, under the cover and the text
                         + f'<div class="vol-actions{" action-panel" if info.get("stores") else ""}"><a class="btn primary" href="{vurl}">Read {esc(v["title"].split(" - ")[0])}</a>'
                         + (store_links_html(info['stores']) if info.get('stores') else '')
                         + '</div></article>')
            mdi.append(f'### [{v["title"]}]({vurl}index.md)\n\n{info.get("blurb", "")}\n\n{nch} chapters' + (f', {info["size"]}' if info.get('size') else ''))
        for u in CFG.get('upcoming_volumes', []):
            # announced but not written yet: no link (the status is the author's own line from the blog)
            info = series['vols'].get(norm(u['title']), {})
            uc = self.covers().get(u.get('slug', ''))
            uurl = upcoming_urls[u['slug']]
            ucover = (f'<a class="vol-cover" href="{uurl}" tabindex="-1" aria-hidden="true"><img src="{uc["thumb"]}" alt="" loading="lazy"></a>' if uc else
                      f'<a class="vol-cover placeholder" href="{uurl}" tabindex="-1" aria-hidden="true"><span>{esc(u["title"].split(" - ")[0])}</span></a>')
            parts.append(f'<article class="vol-row upcoming" id="{u["slug"]}">{ucover}<div class="vol-info">'
                         f'<span class="wip-badge">Work in progress</span><h2 class="vol-title"><a href="{uurl}">{esc(u["title"])}</a></h2>'
                         + (self.r.render(info['blurb'], base=PUB) if info.get('blurb') else '')
                         + f'<p class="vol-meta">{sum(1 for c in u.get("chapters", []) if c.lower().startswith("chapter")) or "?"} chapters planned · {esc(u["status"])}</p>'
                         + '</div>'
                         + f'<div class="vol-actions"><a class="btn" href="{uurl}">See {esc(u["title"].split(" - ")[0])}</a></div></article>')
            mdi.append(f'### {u["title"]} (work in progress: {u["status"]})\n\n{info.get("blurb", "")}')
        parts.append('</div>')
        idx.toc_extra_md = '\n\n' + '\n\n'.join(mdi)
        parts.append('<h2 class="layer bts">Story notes</h2><ul class="layer bts">' + ''.join(f'<li><a href="{u}">{esc(n["title"])}</a></li>' for n, u in notes) + '</ul>')
        parts.append('<p class="layer public-only more-bts">The author\'s notes for Arcs #2 to #5, and each volume\'s story chronology, are in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        idx.html = '\n'.join(parts)
        idx.md_public = '# The Light Novel\n' + idx.toc_extra_md
        idx.md_bts = '\n'.join(f'- [{n["title"]}]({u}index.md)' for n, u in notes) + idx.md_bts
        idx.desc = 'Read the #HusbandOutWorld light novel, Arc #1 Dubious Contract, free online.'
        self.add(idx)

    # ---- about pages
    def public_page(self, name, level=2):
        """Render a blog page (Legacy/Public) section by section, with an anchor on each heading."""
        meta, intro, secs = parse_public(name)
        html_parts = [self.r.render(intro['md'], base=PUB, origin=name)] if intro['md'] else []
        md = [intro['md']] if intro['md'] else []
        toc = []
        for s_ in secs:
            if s_['heading']:
                anchor = slugify(s_['heading'])
                toc.append((anchor, s_['heading'], 'both', 'entry'))
                html_parts.append(f'<h{level} id="{anchor}">{esc(s_["heading"])}</h{level}>')
                md.append('#' * level + ' ' + s_['heading'])
            html_parts.append(self.r.render(s_['md'], base=PUB, origin=name))
            md.append(s_['md'])
        src = (f'<p class="src">From the original blog page: <a href="{esc(meta.get("original_url", ""))}">{esc(meta.get("original_url", ""))}</a> '
               f'(archived in <a href="{gh_link(os.path.join(PUB, name))}">{esc(rel(os.path.join(PUB, name)))}</a>)</p>')
        return '\n'.join(html_parts) + src, '\n\n'.join(md), toc

    def build_about(self):
        links = []
        for a in CFG['about_pages']:
            if CFG.get('webcomic') and a.get('url') == '/webcomic/':
                continue  # the webcomic has its own pages now (tools/webcomic.py)
            url = a.get('url') or f'/about/{a["slug"]}/'
            section = a.get('section', 'About')
            p = Page(url, a['title'], section)
            p.sources.append(rel(os.path.join(PUB, a['public'])))
            body, md, toc = self.public_page(a['public'])
            p.html = f'<h1>{esc(a["title"])}</h1>' + body
            if a.get('toc') and len(toc) > 1:
                p.toc = toc
            p.md_public = f'# {a["title"]}\n\n' + md
            p.desc = first_sentences(md, 160)
            p.search.append({'t': a['title'], 'u': url, 's': section, 'x': first_sentences(md, 300), 'b': False})
            self.add(p)
            if section == 'About':
                links.append((a['title'], url))
        # AI disclosure page from the repo file
        path = os.path.join(ROOT, 'AI-DISCLOSURE.md')
        if os.path.exists(path):
            text = read_legacy(path)
            p = Page('/about/ai-disclosure/', 'AI Disclosure', 'About')
            p.html = self.r.render(text, base=ROOT)  # repo-path links are pointed at GitHub in with_base()
            p.md_public = re.sub(r'\]\((?!https?:|/|#|mailto:)([^)]+)\)', lambda m: '](' + GH_BLOB + m.group(1) + ')', text)
            p.desc = 'Which parts of this website are human work, which parts an AI wrote, and how they fit together.'
            self.add(p)
            links.append(('AI Disclosure', '/about/ai-disclosure/'))
        # no About index page any more: its links are on the homepage ("About the series"); /about/ redirects there

    # ---- lore index
    def build_lore_index(self, topic_pages):
        p = Page('/lore/', 'World Lore', 'World Lore')
        parts = ['<h1>World Lore</h1>',
                 '<p class="lede">The world of Vraki: its kingdoms, peoples, soul energy science, beasts and plants. '
                 'Public mode shows what the old blog showed. Behind The Scenes adds the author\'s full notes.</p>']
        md = ['# World Lore\n']
        world = self.media.file(os.path.join(BTS, 'Illustrations', 'World Map', 'World Map (Final).png'))
        if world:
            alt = ALT.get(world['src'], {}).get('alt') or default_alt(world['src'])
            parts.append(f'<figure class="world-map"><a class="img-link" href="{world["url"]}" data-full="{world["url"]}">'
                         f'<img src="{world["url"]}" alt="{esc(alt)}" loading="lazy"></a></figure>')
            md.append(f'![{alt}]({world["url"]})\n')
        for g in CFG['lore_groups']:
            parts.append(f'<h2>{esc(g["title"])}</h2><div class="topic-grid">')
            md.append(f'## {g["title"]}\n')
            # A to Z by the title readers see, whatever order content/site.json lists them in (author's rule, see CLAUDE.md)
            for slug in sorted(g['topics'], key=lambda sl: alpha_key(topic_pages[sl].title)):
                tp = topic_pages[slug]
                pub = any(l != 'bts' for _, _, l, k in tp.toc if k == 'entry')
                cls = 'both' if pub or tp.md_public.strip() else 'bts'
                parts.append(f'<a class="topic-card layer {cls}" href="{tp.url}"><span>{esc(tp.title)}</span>'
                             f'<span class="muted">{esc(tp.card)}</span></a>')
                md.append(f'- [{tp.title}]({tp.url}index.md)')
            parts.append('</div>')
        p.html = '\n'.join(parts)
        p.md_public = '\n'.join(md)
        p.desc = 'The World Lore of the #HusbandOutWorld series: kingdoms, races, soul energy, beasts, fauna and flora.'
        self.add(p)

    # ---- gallery
    def build_gallery(self):
        root = os.path.join(BTS, 'Illustrations')
        folders = {}
        excluded = set(CFG.get('gallery_exclude', []))
        for p in self.art.files:
            if os.path.relpath(p, BTS).replace(os.sep, '/') in excluded:
                continue
            d = os.path.relpath(os.path.dirname(p), root)
            folders.setdefault(d, []).append(p)
        p = Page('/gallery/', 'Gallery', 'Gallery')
        parts = ['<h1>Gallery</h1>', f'<p class="lede">Every illustration in the series, by {" and ".join(CFG["artists"])}. '
                 'Click any picture to see it larger.</p>', '<nav class="chips">']
        for d in sorted(folders):
            parts.append(f'<a class="chip" href="#{slugify(d)}">{esc(d.replace(os.sep, " / "))}</a>')
        parts.append('</nav>')
        md = ['# Gallery\n']
        manifest = []
        for d in sorted(folders):
            parts.append(f'<h2 id="{slugify(d)}">{esc(d.replace(os.sep, " / "))}</h2><div class="gallery">')
            md.append(f'## {d}\n')
            for f in folders[d]:
                info = self.media.file(f)
                stem = os.path.splitext(os.path.basename(f))[0]
                alt = ALT.get(info['src'], {}).get('alt') or default_alt(info['src'])
                parts.append(f'<figure><a class="img-link" href="{info["url"]}" data-full="{info["url"]}"><img src="{info["thumb"]}" alt="{esc(alt)}" loading="lazy"></a>'
                             f'<figcaption>{esc(stem)}</figcaption></figure>')
                md.append(f'- ![{alt}]({info["url"]}) **{stem}**: {alt}')
            parts.append('</div>')
        p.html = '\n'.join(parts)
        p.md_public = '\n'.join(md)
        p.desc = 'All #HusbandOutWorld illustrations: characters, races, beasts, fauna, flora, emblems and more.'
        self.add(p)

    # ---- glossary
    def build_glossary(self):
        p = Page('/glossary/', 'Glossary', 'Glossary')
        terms = sorted({(g['term'].lower(), g['url']): g for g in self.glossary}.values(), key=lambda g: g['term'].lower())
        wav = os.path.join(BTS, 'World Lore', 'Word Pronunciation', 'Unique Words Pronounciation.wav')
        audio = ''
        if os.path.exists(wav):
            os.makedirs(os.path.join(self.out, 'media'), exist_ok=True)
            mp3 = os.path.join(self.out, 'media', 'pronunciation.mp3')
            src_name = 'pronunciation.mp3'
            if shutil.which('ffmpeg'):
                os.system(f'ffmpeg -loglevel error -y -i "{wav}" -b:a 96k "{mp3}"')
            else:
                src_name = 'pronunciation.wav'
                shutil.copyfile(wav, os.path.join(self.out, 'media', src_name))
            if True:
                audio = ('<div class="pronounce"><p><strong>Hear it from the author.</strong> A short recording of how the series\' unique words are said.</p>'
                         f'<audio controls preload="none" src="/media/{src_name}"></audio></div>')
        letters = sorted({g['term'][0].upper() for g in terms if g['term'][0].isalpha()})
        parts = ['<h1>Glossary</h1>', '<p class="lede">Every named thing in the World Lore, A to Z. Each one links to its entry.</p>', audio,
                 '<input class="filter" type="search" placeholder="Filter terms…" aria-label="Filter terms" data-filter=".glossary li">',
                 '<nav class="letters">' + ''.join(f'<a href="#l-{c}">{c}</a>' for c in letters) + '</nav><ul class="glossary">']
        md = ['# Glossary\n']
        last = None
        for g in terms:
            c = g['term'][0].upper()
            anchor = f' id="l-{c}"' if c != last and c.isalpha() else ''
            last = c
            cls = 'both' if g['public'] else 'bts'
            parts.append(f'<li class="layer {cls}"{anchor}><a href="{g["url"]}">{esc(g["term"])}</a> <span class="muted">{esc(g["topic"])}</span>'
                         f'<br><span class="gdesc">{esc(g["desc"])}</span></li>')
            md.append(f'- **{g["term"]}** ({g["topic"]}){" [Behind the Scenes]" if not g["public"] else ""}: {g["desc"]}')
        parts.append('</ul>')
        p.html = '\n'.join(parts)
        p.md_public = '\n'.join(md)
        p.desc = 'A to Z glossary of the #HusbandOutWorld world: races, places, beasts, plants, factions and more.'
        self.add(p)
        return terms

    # ---- home
    def build_home(self):
        p = Page('/', CFG['title'], 'Home')
        logo = self.media.file(os.path.join(PUB, 'images', '001.png'))  # the old blog's welcome banner
        emblem = self.media.file(os.path.join(BTS, 'Illustrations', 'Emblems', 'Forway city emblem.png'))
        meta, intro, secs = parse_public('webcomic.md')
        blurb = ''
        for s in [intro] + secs:
            m = re.search(r'A botched soul experiment[^\n]*', s['md'])
            if m:
                blurb = m.group(0)
                break
        # the webcomic's episodes so far (tools/webcomic.py reads the same folder when it builds the reader)
        import webcomic
        eps = webcomic.discover(os.path.join(BTS, CFG.get('webcomic', {}).get('source', 'Webcomic')))
        webcomic_card = ''
        if eps:
            chs = sorted({e['chapter'] for e in eps if e['kind'] == 'chapter'})
            parts_ = (['the Prologue'] if any(e['kind'] == 'prologue' for e in eps) else []) + [f'Chapter {webcomic.roman_numeral(c)}' for c in chs]
            webcomic_card = (f'<a class="home-card" href="/webcomic/"><h2>Webcomic</h2><p>Arc #1 in pictures: {" and ".join(parts_)} so far, '
                             f'{len(eps)} episodes. Scroll down to read, like on Webtoons.</p></a>')
        p.html = f'''
<section class="hero">
  <img class="hero-banner" src="{logo['url']}" alt="{esc(ALT.get(logo['src'], {}).get('alt', 'A Husband Out of This World'))}" width="2500" height="1626">
  <p class="hero-blurb">{esc(blurb)}</p>
  <div class="hero-actions">
    <a class="btn primary" href="/novel/vol-1/">Start reading Vol 1</a>
    <a class="btn" href="/lore/">Explore the World Lore</a>
  </div>
  {amazon_note()}
</section>
<section class="home-grid">
  <a class="home-card" href="/novel/"><h2>Novel</h2><p>Arc #1: Vols 1 to {len(CFG["volumes"])}, with every illustration{", and " + CFG["upcoming_volumes"][0]["title"].split(" - ")[0] + " on the way" if CFG.get("upcoming_volumes") else ""}.</p></a>
  {webcomic_card}
  <a class="home-card" href="/lore/"><h2>World Lore</h2><p>Kingdoms, races, soul energy, beasts and plants.</p></a>
  <a class="home-card" href="/gallery/"><h2>Gallery</h2><p>All the art by {" and ".join(CFG["artists"])}.</p></a>
  <a class="home-card" href="/glossary/"><h2>Glossary</h2><p>Every name A to Z, with the author's pronunciation.</p></a>
  <a class="home-card" href="/blog/"><h2>Blog</h2><p>The final blog post, and photos from seven years of making the series.</p></a>
</section>
<section class="home-about" id="about">
  <h2>About the series</h2>
  <div class="home-links">
    <a class="home-link" href="/about/faq/"><strong>FAQ</strong><span>Readers' questions, answered by the author.</span></a>
    <a class="home-link" href="/about/afterwords/"><strong>Afterwords</strong><span>The author's notes at the end of each volume.</span></a>
    <a class="home-link" href="/about/ai-disclosure/"><strong>AI Disclosure</strong><span>What a human made, what an AI made, and how they fit.</span></a>
    <a class="home-link ext" href="{CFG["dnd_url"]}" rel="noopener"><strong>D&amp;D West March Campaign</strong><span>A West Marches D&amp;D 5e campaign set in the world of #HusbandOutWorld.</span></a>
    <a class="home-link ext" href="{CFG["vraki_url"]}" rel="noopener"><strong>Vraki Language app</strong><span>The 2017 Windows app the Vraki writing grew from.</span></a>
    <a class="home-link ext" href="{CFG["repo_url"]}" rel="noopener"><strong>GitHub repository</strong><span>Every original: manuscripts, notes, art and spreadsheets.</span></a>
  </div>
</section>
<section class="modes-explainer">
  <img src="{emblem['thumb']}" alt="Forway city emblem" width="160" height="160">
  <div>
    <h2>Public or Behind The Scenes</h2>
    <p>Everything starts in <strong>Public</strong> mode: the story and the lore as readers first saw them, light on spoilers.
    Flip the switch at the top to <strong>Behind The Scenes</strong> and every page grows to include the author's full notes:
    secrets, unreleased arcs and all.</p>
  </div>
</section>
'''
        p.md_public = (f'# {CFG["title"]}\n\n{blurb}\n\n'
                       '- [Novel](/novel/index.md)\n' + ('- [Webcomic](/webcomic/index.md)\n' if webcomic_card else '')
                       + '- [World Lore](/lore/index.md)\n- [Gallery](/gallery/index.md)\n'
                       '- [Glossary](/glossary/index.md)\n- [Blog](/blog/index.md)\n'
                       '\n## About the series\n\n- [FAQ](/about/faq/index.md)\n- [Afterwords](/about/afterwords/index.md)\n'
                       '- [AI Disclosure](/about/ai-disclosure/index.md)\n'
                       f'- [D&D West March Campaign]({CFG["dnd_url"]})\n- [Vraki Language app]({CFG["vraki_url"]})\n'
                       f'- [GitHub repository]({CFG["repo_url"]})\n')
        p.desc = blurb[:160]
        p.jsonld = {'@context': 'https://schema.org', '@type': 'BookSeries', 'name': CFG['title'],
                    'alternateName': CFG['short_title'], 'author': {'@type': 'Person', 'name': CFG['author']},
                    'illustrator': [{'@type': 'Person', 'name': a} for a in CFG['artists']],
                    'url': CFG['base_url'] + '/', 'description': blurb,
                    'hasPart': [{'@type': 'Book', 'name': v['title'], 'url': CFG['base_url'] + f'/novel/{v["slug"]}/'} for v in CFG['volumes']],
                    'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/'}
        self.add(p)

    def write_translated_twin(self, code, meta, p, page_html_text):
        """index.md for a translated page (issue #76): its text as Markdown, with a header saying it is AI-translated."""
        title, body = mdtwin.page_markdown(page_html_text, CFG['base_url'])
        banner = re.sub(r'<[^>]+>', '', meta.get('banner', '')).strip()
        head = (f'---\ntitle: "{title.replace(chr(34), chr(39))}"\nurl: {CFG["base_url"]}/{code}{p.url}\n'
                f'language: {meta.get("name", code)} ({code})\ntranslation: "{banner.replace(chr(34), chr(39))}"\n'
                f'original: {CFG["base_url"]}{p.url}index.md\nsection: {p.section}\n'
                f'spoilers: {"yes (Behind The Scenes only)" if p.layer == "bts" else "public text first; Behind The Scenes blocks are marked"}\n---\n\n')
        path = os.path.join(self.out, code, p.url.lstrip('/'), 'index.md')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'w', encoding='utf-8').write(head + body)
        return title

    def build_search_page(self):
        p = Page('/search/', 'Search', 'Search')
        p.html = ('<h1>Search</h1><input id="search-page-input" class="filter" type="search" placeholder="Search the novel and the lore…" aria-label="Search">'
                  '<p class="muted layer public-only">Searching Public pages. Switch to Behind The Scenes to search the full notes too.</p>'
                  '<ol id="search-results" class="search-results"></ol>')
        p.desc = 'Search the #HusbandOutWorld website.'
        self.add(p)

    def build_404(self):
        p = Page('/404.html', 'Page not found', 'Home')
        p.html = '<h1>Lost in Endlessfog</h1><p>That page does not exist. Try the <a href="/">home page</a> or <a href="/search/">search</a>.</p>'
        self.add(p)

    # ---- output
    def write(self):
        nav = nav_html()
        # translations (tools/i18n.py): every page is also written once per language, from content/i18n/<lang>/
        langs = [(l['code'], i18n.load_meta(l['code']), i18n.load_store(l['code'])) for l in i18n.languages(CFG)]
        inv = {'pages': {}}
        self.lang_ready = []  # (code, url) pairs translated enough to offer
        self.lang_twins = {}  # code -> [(page, translated title)] that got a Markdown twin
        for p in self.pages:
            if p.url.endswith('.html'):
                path = os.path.join(self.out, p.url.lstrip('/'))
            else:
                path = os.path.join(self.out, p.url.lstrip('/'), 'index.html')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            en = page_html(p, nav)
            if p.url.endswith('.html') or not langs:
                open(path, 'w', encoding='utf-8').write(with_base(en))
            else:
                inv['pages'][p.url] = {'section': p.section, 'segments': i18n.inventory(en, p.url, p.section)}
                cov, outs = {}, {}
                for code, meta, store in langs:
                    outs[code], cov[code] = i18n.translate_page(en, p.url, code, meta, store, CFG['base_url'])
                open(path, 'w', encoding='utf-8').write(with_base(i18n.head_extras(en, p.url, cov, CFG['base_url'])))
                for code, meta, _ in langs:
                    lp = os.path.join(self.out, code, p.url.lstrip('/'), 'index.html')
                    os.makedirs(os.path.dirname(lp), exist_ok=True)
                    html_out = outs[code]
                    if cov[code] >= i18n.INDEX_COVERAGE:
                        self.lang_ready.append((code, p.url))
                        # a page translated enough to offer also gets a Markdown twin in its language
                        title = self.write_translated_twin(code, meta, p, html_out)
                        self.lang_twins.setdefault(code, []).append((p, title))
                        html_out = html_out.replace(f'href="{p.url}index.md"', f'href="/{code}{p.url}index.md"')
                    open(lp, 'w', encoding='utf-8').write(with_base(i18n.head_extras(html_out, p.url, cov, CFG['base_url'], this_code=code)))
            if not p.url.endswith('.html'):
                files = page_md_files(p)
                p.md_parts = [name for name in files if name != 'index.md']
                for name, text in files.items():
                    open(os.path.join(os.path.dirname(path), name), 'w', encoding='utf-8').write(text)
        if langs:
            os.makedirs(i18n.CACHE, exist_ok=True)
            json.dump(inv, open(i18n.INVENTORY, 'w', encoding='utf-8'), ensure_ascii=False)
        # search index
        idx = [s for p in self.pages for s in p.search]
        # a heading that repeats across many entries ("Economic Value", "Food/Drink", "None") is a field of the
        # docs' template, not a term anyone searches for, so only the rarer headings inside entries are kept
        sub_count = Counter(norm(s['t']) for s in idx if s.get('sub'))
        idx = [s for s in idx if not s.get('sub') or (sub_count[norm(s['t'])] < SUB_HEADING_MAX
                                                       and norm(s['t']) not in ('none', 'tbd', 'na'))]
        for s in idx:
            s.pop('sub', None)
        os.makedirs(os.path.join(self.out, 'data'), exist_ok=True)
        json.dump(idx, open(os.path.join(self.out, 'data', 'search.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        json.dump(self.glossary, open(os.path.join(self.out, 'data', 'glossary.json'), 'w'), ensure_ascii=False, indent=1)
        imgs = []
        for k, v in self.media.info.items():
            a = ALT.get(v['src'], {})
            imgs.append({'source': v['src'], 'url': CFG['base_url'] + v['url'], 'thumb': CFG['base_url'] + v['thumb'],
                         'width': v.get('w'), 'height': v.get('h'),
                         'alt': a.get('alt') or default_alt(v['src']), 'alt_written_by': 'AI (Claude)' if a.get('alt') else 'generated from file name'})
        imgs.sort(key=lambda i: i['source'])
        json.dump(imgs, open(os.path.join(self.out, 'data', 'images.json'), 'w'), ensure_ascii=False, indent=1)
        pages = [{'url': CFG['base_url'] + p.url, 'markdown': CFG['base_url'] + p.url + 'index.md', 'title': p.title,
                  'section': p.section, 'spoilers': p.layer == 'bts', 'sources': p.sources} for p in self.pages if not p.url.endswith('.html')]
        json.dump(pages, open(os.path.join(self.out, 'data', 'pages.json'), 'w'), ensure_ascii=False, indent=1)
        bundles = write_llms(self.out, self.pages, getattr(self, 'lang_twins', {}))
        write_sitemap(self.out, self.pages, getattr(self, 'lang_ready', []), bundles, getattr(self, 'lang_twins', {}))
        open(os.path.join(self.out, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {CFG["base_url"]}/sitemap.xml\n')
        # static assets
        for sub in ('css', 'js', 'fonts'):
            src = os.path.join(SITE_SRC, sub)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(self.out, sub), dirs_exist_ok=True)
        os.makedirs(os.path.join(self.out, 'fonts'), exist_ok=True)
        shutil.copyfile(os.path.join(BTS, 'Logo and Font', 'VrakiHusbandOutWorldSeries-Rg.woff2'), os.path.join(self.out, 'fonts', 'vraki.woff2'))
        lic = os.path.join(BTS, 'Logo and Font', 'LICENSE.md')
        if os.path.exists(lic):  # the Vraki typeface license asks for it to travel with the font
            shutil.copyfile(lic, os.path.join(self.out, 'fonts', 'VRAKI-FONT-LICENSE.md'))
        em = self.media.file(os.path.join(BTS, 'Illustrations', 'Emblems', 'Forway city emblem.png'))
        moved = list(CFG.get('redirects', {}).items())
        moved += [(f'/{l["code"]}{o}', i18n.lang_url(n, l['code'])) for l in i18n.languages(CFG) for o, n in CFG.get('redirects', {}).items()]
        for old, new in moved:
            # pages that moved: a tiny page that forwards old links (bookmarks, search results) to the new address
            path = os.path.join(self.out, old.lstrip('/'), 'index.html')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w', encoding='utf-8').write(with_base(
                f'<!doctype html><meta charset="utf-8"><title>Moved</title><link rel="canonical" href="{CFG["base_url"]}{new}">'
                f'<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={new}">'
                f'<p>This page moved to <a href="{new}">{new}</a>.</p>'))
        open(os.path.join(self.out, '.nojekyll'), 'w').write('')
        if os.path.exists(os.path.join(ROOT, 'CNAME')):
            shutil.copyfile(os.path.join(ROOT, 'CNAME'), os.path.join(self.out, 'CNAME'))
        return em

def _renumber(html_text, anchor, n, new_anchor):
    """Rename the (n+1)-th id="anchor" in the page to new_anchor."""
    parts = html_text.split(f'id="{anchor}"')
    if len(parts) <= n + 1:
        return html_text
    return f'id="{anchor}"'.join(parts[:n + 1]) + f'id="{new_anchor}"' + f'id="{anchor}"'.join(parts[n + 1:])

def glyph_grids(html_text, entry):
    """Turn the docs' glyph tables (a row of labels, then a row of hand-drawn glyphs, repeated) into tiles:
    the hand-drawn glyph, its English letter, and the same letter in the Vraki typeface (like the Vraki app's site)."""
    def table(m):
        rows = re.findall(r'<tr>(.*?)</tr>', m.group(0), re.S)
        cells = [re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S) for r in rows]
        tiles = []
        for labels, glyphs in zip(cells[0::2], cells[1::2]):
            for lab, g in zip(labels, glyphs):
                label = html.unescape(re.sub(r'<[^>]+>', '', lab)).strip()
                if not label or '<img' not in g:
                    continue
                typed = label.rstrip('*').split(' (')[0]
                font = '' if label.lower() == 'space' or '(' in label else typed
                g = re.sub(r'alt="[^"]*"', f'alt="{esc("Hand-drawn Vraki " + ("sign for " if not label.isalnum() else "") + label)}"', g)
                tiles.append(f'<figure class="glyph">{g}<figcaption class="keep-latin"><span class="glyph-latin">{esc(label)}</span>'
                             + (f'<span class="glyph-font" aria-hidden="true" translate="no" title="{esc(typed)} in the Vraki typeface">{esc(font)}</span>' if font else '')
                             + '</figcaption></figure>')
        if not tiles:
            return m.group(0)
        return f'<div class="glyph-grid" role="list" aria-label="{esc(entry)}">' + ''.join(tiles).replace('<figure class="glyph">', '<figure class="glyph" role="listitem">') + '</div>'
    return re.sub(r'<table>.*?</table>', table, html_text, flags=re.S)

def scribe_html():
    """A live 'write it in Vraki' box. Vraki is written letter for letter with English, so the typeface does the work."""
    return ('<div class="scribe keep-latin"><label for="scribe-in">Type anything in English to see it written in the Vraki typeface, letter for letter:</label>'
            '<input id="scribe-in" type="text" value="Be Awesome! Do Better!" maxlength="80" autocomplete="off" spellcheck="false">'
            '<div class="scribe-out" id="scribe-out" aria-live="polite" translate="no">Be Awesome! Do Better!</div>'
            '<p class="muted">The tiles below are the author\'s hand-drawn originals. The blue symbol next to each letter is the same letter in the finished Vraki typeface.</p></div>')

def one_paragraph_per_line(lines):
    """Novel text: every line of prose is its own paragraph.

    The manuscripts end most lines with a hard line break ("  " or "\\"), which Markdown turns into one long
    paragraph with <br>s inside, so only its first line got the paragraph indent. Splitting them gives
    every paragraph the same indent, like a printed book.
    """
    text = '\n'.join(lines).strip()
    return re.sub(r'(?:[ \t]{2,}|\\)\n(?=\S)', '\n\n', text)

def roman(s):
    vals = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}
    s = s.lower(); total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total

SERIES_PAGE = 'webcomic.md'  # the old blog's "Graphic/Light Novel Series" page (its file name is swapped with the Webcomic page's)

def series_info():
    """Per-volume blurb, size and store links from the old blog's series page, keyed by norm(volume title)."""
    meta, intro, secs = parse_public(SERIES_PAGE)
    out = {'vols': {}}
    for s_ in secs:
        md = s_['md']
        if s_['heading'].lower().startswith('arc'):
            img = first_image(md)
            out['arc'] = {'title': s_['heading'].replace('  ', ' '), 'img': img,
                          'blurb': strip_images(md).strip()}
            continue
        if not s_['heading'].lower().startswith('vol'):
            continue
        blocks = re.split(r'^\*\*(Chapters|Vol Size|Store Links)\*\*\s*$', md, flags=re.M)
        d = {'blurb': blocks[0].strip()}
        for k, val in zip(blocks[1::2], blocks[2::2]):
            val = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', val).strip()
            if k == 'Vol Size' and val.strip('? '):
                # pages and illustrations only; the author dropped the word counts ("~51,000 words, " / "~39,000, ")
                size = re.sub(r'^~?\s*[\d,.]+\s*(?:k\b)?\s*(?:words)?\s*,?\s*', '', val).rstrip('.').strip()
                if size:
                    d['size'] = size
            if k == 'Store Links':
                links = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', val)
                if links:
                    d['stores'] = links
        out['vols'][norm(s_['heading'])] = d
    return out

def store_links_html(links):
    """The eBook stores as a labelled group of buttons."""
    return ('<div class="buy-group" role="group" aria-label="Buy the eBook"><span class="buy-label">Buy the eBook!</span>'
            + ''.join(f'<a class="btn store" href="{esc(u)}" rel="noopener">{esc(t)}</a>' for t, u in links) + '</div>')

def lede_text():
    """How far along Arc #1 is: the published volumes, plus any volume still being written."""
    n, up = len(CFG['volumes']), CFG.get('upcoming_volumes', [])
    words = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six'}
    if not up:
        return f'Arc #1, *Dubious Contract*, is complete in {words.get(n, n)} volumes. Read every chapter here, with every subchapter illustration.'
    u = up[0]
    return (f'Arc #1, *Dubious Contract*, has {words.get(n + len(up), n + len(up))} volumes. Vols 1 to {n} are complete: read every chapter here, '
            f'with every subchapter illustration. {u["title"].split(" - ")[0]}, *{u["title"].split(" - ", 1)[-1]}*, is a work in progress ({u["status"][0].lower() + u["status"][1:]}).')

def lede_html():
    return '<p class="lede">' + re.sub(r'\*([^*]+)\*', r'<em>\1</em>', esc(lede_text())) + '</p>'

def amazon_note():
    return (f'<aside class="support-note">Reading for free is fine by the author. If you want the eBook, '
            f'<a href="{CFG["amazon_url"]}" rel="noopener">please support the series by getting it on Amazon</a>.</aside>')

def bts_gate(why):
    return (f'<div class="layer public-only gate"><p><strong>Behind The Scenes only.</strong> {esc(why)}</p>'
            '<button class="btn" data-go-bts>Show Behind The Scenes</button></div>')

# --------------------------------------------------------------------------- templates

NAV = [('Novel', '/novel/'), ('Webcomic', '/webcomic/'), ('World Lore', '/lore/'), ('Gallery', '/gallery/'), ('Glossary', '/glossary/'), ('Blog', '/blog/')]

def nav_html():
    return ''.join(f'<a href="{u}">{t}</a>' for t, u in NAV)

def lang_options():
    """The Language choices, each written in its own language (never translated)."""
    opts = ['<option value="en" lang="en" translate="no">English</option>']
    for l in i18n.languages(CFG):
        m = i18n.load_meta(l['code'])
        opts.append(f'<option value="{l["code"]}" lang="{m.get("html_lang", l["code"])}" translate="no">{esc(m.get("name", l["code"]))}</option>')
    return ''.join(opts)

def page_html(p, nav):
    title = p.title if p.url == '/' else f'{p.title} · {CFG["short_title"]}'
    toc = ''
    if p.toc:
        items = []
        for anchor, t, layer, kind in p.toc:
            items.append(f'<li class="layer {layer} toc-{kind}"><a href="#{anchor}">{esc(t)}</a></li>')
        allbts = all(layer == 'bts' for _, _, layer, _ in p.toc)
        toc = f'<nav class="toc{" layer bts" if allbts else ""}" aria-label="On this page"><p class="toc-title">On this page</p><ul>{"".join(items)}</ul></nav>'
    pager = ''
    if p.prev or p.next:
        pager = '<nav class="pager">' + (f'<a class="prev" href="{p.prev.url}">← {esc(p.prev.title.split(" · ")[0])}</a>' if p.prev else '<span></span>') + \
                (f'<a class="next" href="{p.next.url}">{esc(p.next.title.split(" · ")[0])} →</a>' if p.next else '<span></span>') + '</nav>'
    head_title = ''
    if p.section == 'World Lore' and p.url != '/lore/':
        head_title = f'<header class="page-head"><p class="vraki-overline" aria-hidden="true" translate="no">{esc(p.title)}</p><h1>{esc(p.title)}</h1></header>'
    jsonld = f'<script type="application/ld+json">{json.dumps(p.jsonld, ensure_ascii=False)}</script>' if p.jsonld else ''
    srcs = ''
    if p.sources:
        srcs = '<p class="page-sources"><span>Built from:</span> ' + ', '.join(f'<a href="{GH_BLOB}{quote(s)}" translate="no">{esc(s)}</a>' for s in p.sources) + '</p>'
    md_link = '' if p.url.endswith('.html') else f'<link rel="alternate" type="text/markdown" href="{p.url}index.md">'
    return f'''<!doctype html>
<html lang="en" data-mode="public" data-theme="dark" data-base="{BASE}"{' data-layout="' + p.layout + '"' if getattr(p, 'layout', '') else ''}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(p.desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(p.desc)}">
<meta property="og:type" content="{'book' if p.section == 'Light Novel' else 'website'}">
<link rel="canonical" href="{CFG['base_url']}{p.url}">
{md_link}
<link rel="icon" href="/media/favicon.png">
{pwa.head_tags(CFG['app']['theme_color']) if CFG.get('app') else ''}
<script>try{{var s=JSON.parse(localStorage.getItem('hoow')||'{{}}');var d=document.documentElement;if(s.mode)d.dataset.mode=s.mode;if(s.theme)d.dataset.theme=s.theme;if(s.vraki&&!d.dataset.lang)d.classList.add('vraki');if(s.size)d.style.setProperty('--fs',s.size+'px');
if(!d.dataset.lang){{var ok=(d.dataset.langs||'').split(' '),w=s.lang,n=navigator.languages||[navigator.language||''];for(var i=0;i<n.length&&!w;i++){{var c=String(n[i]).toLowerCase().split('-')[0];if(c==='en'||ok.indexOf(c)>=0)w=c}}if(w&&w!=='en'&&ok.indexOf(w)>=0){{var b=d.dataset.base||'';location.replace(b+'/'+w+location.pathname.slice(b.length)+location.search+location.hash)}}}}}}catch(e){{}}</script>
<link rel="stylesheet" href="{asset('/css/site.css')}">
{''.join(f'<link rel="stylesheet" href="{asset(c)}">' for c in getattr(p, 'extra_css', []) + (['/css/video.css'] if 'class="hv-video"' in p.html else []))}
{jsonld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar keep-latin">
  <a class="brand" href="/"><img class="brand-mark" src="/media/forway-emblem.png" alt="" width="30" height="30"><span class="brand-text" translate="no">#HusbandOutWorld</span></a>
  <nav class="mainnav">{nav}</nav>
  <div class="controls">
    <form class="searchbox" action="/search/" role="search"><input name="q" type="search" placeholder="Search" aria-label="Search the site"></form>
    <a class="search-link" href="/search/" aria-label="Search the site"><svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></a>
    <button class="mode-switch" type="button" role="switch" aria-checked="false" title="Switch between Public and Behind The Scenes">
      <span class="mode-public">Public</span><span class="knob" aria-hidden="true"></span><span class="mode-bts">Behind The Scenes</span>
    </button>
    <button class="settings-btn" type="button" aria-haspopup="dialog" aria-label="Settings" title="Settings"><svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true"><path fill="currentColor" d="M19.4 13a7.6 7.6 0 0 0 0-2l2.1-1.6a.5.5 0 0 0 .1-.6l-2-3.5a.5.5 0 0 0-.6-.2l-2.5 1a7.5 7.5 0 0 0-1.7-1l-.4-2.6a.5.5 0 0 0-.5-.5h-4a.5.5 0 0 0-.5.4l-.4 2.7c-.6.2-1.2.6-1.7 1l-2.5-1a.5.5 0 0 0-.6.2l-2 3.5a.5.5 0 0 0 .1.6L4.6 11a7.6 7.6 0 0 0 0 2l-2.1 1.6a.5.5 0 0 0-.1.6l2 3.5c.1.2.4.3.6.2l2.5-1c.5.4 1.1.8 1.7 1l.4 2.6c0 .3.2.5.5.5h4c.3 0 .5-.2.5-.4l.4-2.7c.6-.2 1.2-.6 1.7-1l2.5 1c.2.1.5 0 .6-.2l2-3.5a.5.5 0 0 0-.1-.6L19.4 13ZM12 15.5a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z"/></svg></button>
  </div>
</header>
<div class="mode-banner layer bts keep-latin">Behind The Scenes is on: pages include the author's full notes and spoilers.</div>
<main id="main" class="{'has-toc' if toc else ''}{' toc-bts-only' if toc and all(l == 'bts' for _, _, l, _ in p.toc) else ''}">
  {toc}
  <article class="content">
    {head_title}
    {p.html}
    {pager}
    {srcs}
  </article>
</main>
<footer class="footer keep-latin">
  <p>© {CFG['author']}. Art by {' and '.join(CFG['artists'])}. <em>A Husband Out of This World</em> and #HusbandOutWorld are trademarks of {CFG['author']}. Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>.
  Vraki typeface © 2024 Deovandski Skibinski Junior, https://husbandoutworld.com/ (<a href="/fonts/VRAKI-FONT-LICENSE.md">font license</a>).</p>
  <p>Monetized videos and posts about the series are welcome; other commercial use needs approval: <a href="https://www.linkedin.com/in/deovandski/">LinkedIn</a> or <a href="mailto:Deovandski@outlook.com">Deovandski@outlook.com</a>. <a href="{CFG['repo_url']}/blob/main/LICENSE.md#permissions-beyond-the-license">Permissions</a></p>
  <p><span>This site was built with AI assistance from the author's originals.</span> <a href="/about/ai-disclosure/">AI disclosure</a> · <a href="{CFG['repo_url']}">GitHub</a> · <a href="/llms.txt">llms.txt</a> · <a href="{p.url if not p.url.endswith('.html') else '/'}index.md">This page as Markdown</a></p>
  <p class="ai-files">Full text for AI tools: <a href="/llms-full.txt">llms-full.txt</a> · <a href="/llms-full-bts.txt">llms-full-bts.txt</a> (spoilers)</p>
</footer>
<dialog id="spoiler-dialog" class="keep-latin">
  <form method="dialog">
    <h2>Ready for spoilers?</h2>
    <p>Behind The Scenes shows everything: the author's full notes, secrets, and story notes for arcs that haven't been released.</p>
    <div class="dialog-actions"><button value="cancel" class="btn">Keep it Public</button><button value="ok" class="btn primary">Show me everything</button></div>
  </form>
</dialog>
<dialog id="settings-dialog" class="keep-latin">
  <form method="dialog">
    <h2>Settings</h2>
    <label class="setting"><span>Language</span><select data-setting="lang">{lang_options()}</select></label>
    <p class="setting-link"><a href="{CFG.get('i18n_issue_url', CFG['repo_url'] + '/issues/50')}" rel="noopener">Want a language added?</a></p>
    <label class="setting"><span>Theme</span><select data-setting="theme"><option value="dark">Dark</option><option value="light">Light</option></select></label>
    <label class="setting"><span>Text size</span><input data-setting="size" type="range" min="14" max="26" step="1" value="18"></label>
    <label class="setting"><span>Vraki mode <small>(read everything in the Vraki script)</small> <small class="vraki-note">Vraki mode works with the English text only.</small></span><input data-setting="vraki" type="checkbox"></label>
    <div class="dialog-actions"><button class="btn primary" value="close">Done</button></div>
  </form>
</dialog>
<div id="lightbox" class="lightbox keep-latin" hidden><button class="lb-close" aria-label="Close">×</button><button class="lb-prev" aria-label="Previous photo" hidden>‹</button><figure class="lb-fig"><img alt=""><figcaption class="lb-cap" hidden></figcaption></figure><button class="lb-next" aria-label="Next photo" hidden>›</button></div>
<script src="{asset('/js/app.js')}" defer></script>
{''.join(f'<script src="{asset(j)}" defer></script>' for j in getattr(p, 'extra_js', []))}
</body>
</html>
'''

def page_md(p, bts=None, public=None, title=None, extra_head=''):
    bts = p.md_bts if bts is None else bts
    public = p.md_public if public is None else public
    head = (f'---\ntitle: "{title or p.title}"\nurl: {CFG["base_url"]}{p.url}\nsection: {p.section}\n'
            f'spoilers: {"yes (Behind The Scenes only)" if p.layer == "bts" or not public.strip() else "public layer first, Behind The Scenes after"}\n'
            f'sources: [{", ".join(p.sources)}]\n{extra_head}---\n\n')
    out = head
    if public.strip():
        out += '<!-- PUBLIC LAYER: as published for readers -->\n\n' + public.strip() + '\n\n'
    if bts.strip():
        out += '<!-- BEHIND THE SCENES LAYER: the author\'s full notes, contains spoilers -->\n\n' + bts.strip() + '\n'
    out = md_absolute(out)
    out = re.sub(r'\[image\d+\]: <data:[^>]+>', '', out)
    out = re.sub(r'\(data:image/[^)]+\)', '(embedded-image)', out)
    return out

def page_md_files(p):
    """A page's Markdown twin as {file name: text}. A twin over MD_MAX bytes keeps its Public layer in index.md and
    splits its Behind The Scenes layer into one file per category (bts-<category>.md), which index.md links to,
    so readers that cut off long files still get all of it."""
    full = page_md(p)
    if len(full.encode('utf-8')) <= MD_MAX:
        return {'index.md': full}
    chunks = re.split(r'(?m)^(?=## )', p.md_bts.strip())
    intro, cats = chunks[0], chunks[1:]
    if len(cats) < 2:
        return {'index.md': full}
    files, links = {}, []
    for c in cats:
        cat = clean_heading(c.split('\n', 1)[0][3:])
        name = f'bts-{slugify(cat)}.md'
        files[name] = page_md(p, bts=c, public='', title=f'{p.title}: {cat} (Behind The Scenes)',
                              extra_head=f'part_of: {CFG["base_url"]}{p.url}index.md\n')
        links.append(f'- [{cat}]({p.url}{name})')
    note = ('The full notes for this page are long, so they are split into one file per category:\n\n' + '\n'.join(links))
    return {'index.md': page_md(p, bts=(intro.strip() + '\n\n' + note).strip()), **files}

def size_label(n):
    return f'{n / 1e6:.1f} MB' if n >= 1e6 else f'{max(1, round(n / 1e3))} KB'

def bundle_group(p):
    """(file name, label) of the smaller full-text bundle a page goes in."""
    m = re.match(r'/novel/(vol-\d+)/', p.url)
    if m:
        vol = next((v for v in CFG['volumes'] + CFG.get('upcoming_volumes', []) if v.get('slug') == m.group(1)), {})
        return f'novel-{m.group(1)}', f'Light Novel, {vol.get("title", m.group(1))}'
    if any(p.url == f'/novel/{n["slug"]}/' for n in CFG['story_notes']):
        return 'story-notes', 'Story notes for the unreleased arcs'
    m = re.match(r'/lore/([^/]+)/', p.url)
    if m:
        for g in CFG['lore_groups']:
            if m.group(1) in g['topics']:
                return f'lore-{slugify(g["title"])}', f'World Lore: {g["title"]}'
    if p.url.startswith('/glossary/'):
        return 'glossary', 'Glossary'
    return 'site', 'Home, novel overview, World Lore overview, Webcomic, Gallery, Blog and About'

def split_bundles(out, pages, head):
    """Write the full text again as smaller files in /llms/ (one per section, each under BUNDLE_MAX bytes where a page
    allows), Public and Behind The Scenes versions. Returns [(label, url, bytes, bts)]."""
    groups, labels = {}, {}
    for p in pages:
        name, label = bundle_group(p)
        groups.setdefault(name, []).append(p)
        labels[name] = label
    os.makedirs(os.path.join(out, 'llms'), exist_ok=True)
    made = []
    for bts in (False, True):
        for name, ps in groups.items():
            texts = [(f'\n\n---\nURL: {CFG["base_url"]}{p.url}\n\n' +
                      (page_md(p) if bts else md_absolute(p.md_public.strip())))
                     for p in ps if bts or p.md_public.strip()]
            if not texts:
                continue
            chunks, cur = [], ''
            for t in texts:
                if cur and len((cur + t).encode('utf-8')) > BUNDLE_MAX:
                    chunks.append(cur)
                    cur = ''
                cur += t
            if chunks and len(cur.encode('utf-8')) < BUNDLE_MAX // 10:
                chunks[-1] += cur  # a short last piece rides along with the one before it
            else:
                chunks.append(cur)
            for i, body in enumerate(chunks, 1):
                fname = name + (f'-part-{i}' if len(chunks) > 1 else '') + ('-bts' if bts else '') + '.txt'
                label = labels[name] + (f' (part {i} of {len(chunks)})' if len(chunks) > 1 else '')
                note = '(Public and Behind The Scenes layers. Contains spoilers.)' if bts else '(Public layer only.)'
                text = head + f'Part: {label}. {note}\n' + re.sub(r'\(data:image/[^)]+\)', '(embedded-image)', body)
                open(os.path.join(out, 'llms', fname), 'w', encoding='utf-8').write(text)
                made.append((label, f'/llms/{fname}', len(text.encode('utf-8')), bts))
    return made

def write_lang_llms(out, lang_twins):
    """/<lang>/llms.txt for each language with Markdown twins. Returns [(code, name, count)]."""
    names = {l['code']: l.get('name', l['code']) for l in i18n.languages(CFG)}
    made = []
    for code, items in sorted(lang_twins.items()):
        meta = i18n.load_meta(code)
        name = meta.get('name', names.get(code, code))
        lines = [f'# {CFG["title"]} ({CFG["short_title"]}): {name}', '',
                 f'> {re.sub(r"<[^>]+>", "", meta.get("banner", "")).strip()}', '',
                 f'Pages translated well enough to offer in {name}, each as Markdown. The English original of every page is listed in {CFG["base_url"]}/llms.txt.', '']
        for p, title in items:
            lines.append(f'- [{title}]({CFG["base_url"]}/{code}{p.url}index.md)' + (' (Behind The Scenes, spoilers)' if p.layer == 'bts' else ''))
        os.makedirs(os.path.join(out, code), exist_ok=True)
        open(os.path.join(out, code, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
        made.append((code, name, len(items)))
    return made

def write_llms(out, pages, lang_twins=None):
    pub_text, full_text, head = full_text_bundles(pages)
    open(os.path.join(out, 'llms-full.txt'), 'w', encoding='utf-8').write(pub_text)
    open(os.path.join(out, 'llms-full-bts.txt'), 'w', encoding='utf-8').write(full_text)
    sizes = {'pub': len(pub_text.encode('utf-8')), 'bts': len(full_text.encode('utf-8'))}
    order = {'Home': 0, 'Light Novel': 1, 'Webcomic': 1.5, 'World Lore': 2, 'Glossary': 3, 'Gallery': 4, 'About': 5}
    bundles = split_bundles(out, sorted([p for p in pages if not p.url.endswith('.html') and p.section != 'Search'],
                                        key=lambda p: order.get(p.section, 9)), head)
    by = {}
    for p in pages:
        if p.url.endswith('.html'):
            continue
        by.setdefault(p.section, []).append(p)
    lines = [f'# {CFG["title"]} ({CFG["short_title"]})', '',
             f'> A light novel series by {CFG["author"]}, illustrated by {" and ".join(CFG["artists"])}: '
             'a botched soul experiment leaves a stranger reborn without memory in the high-magic world of Vraki. '
             'This site has the full text of Arc #1 (Vols 1-3), every subchapter illustration, and the complete World Lore.', '',
             'Every page has a Markdown twin at the same URL plus `index.md`. Pages have two layers: PUBLIC (light on spoilers, '
             'as originally published) and BEHIND THE SCENES (the author\'s full notes, including unreleased story notes).',
             f'The eBook is on Amazon: {CFG["amazon_url"]}. Source files: {CFG["repo_url"]} (originals in the Legacy folder).',
             f'Copyright © {CFG["author"]}. "A Husband Out of This World" and "#HusbandOutWorld" are trademarks of {CFG["author"]}. '
             f'License: CC BY-NC-SA 4.0 (copyright only, no trademark rights). Monetized videos, streams and social media posts about the series are allowed with credit; '
             f'other commercial use needs approval (LinkedIn: https://www.linkedin.com/in/deovandski/, email: Deovandski@outlook.com). Built with AI assistance from the author\'s originals: {CFG["base_url"]}/about/ai-disclosure/', '',
             '## Full text bundles', '',
             'Many readers stop partway through a long file. If yours does, use the smaller files by section below, or each page\'s `index.md` twin.', '',
             f'- [Public layer, everything]({CFG["base_url"]}/llms-full.txt) ({size_label(sizes["pub"])}): the novel and the public lore in one file',
             f'- [Everything, including Behind The Scenes]({CFG["base_url"]}/llms-full-bts.txt) ({size_label(sizes["bts"])}): adds the full notes (spoilers)',
             f'- [Glossary JSON]({CFG["base_url"]}/data/glossary.json), [Image list with alt text]({CFG["base_url"]}/data/images.json), [Page list]({CFG["base_url"]}/data/pages.json)', '',
             f'### By section, Public layer (about {size_label(BUNDLE_MAX)} or less each)', '',
             *[f'- [{label}]({CFG["base_url"]}{u}) ({size_label(n)})' for label, u, n, b in bundles if not b], '',
             '### By section, including Behind The Scenes (spoilers)', '',
             *[f'- [{label}]({CFG["base_url"]}{u}) ({size_label(n)})' for label, u, n, b in bundles if b], '']
    for sec in ('Light Novel', 'Webcomic', 'World Lore', 'Gallery', 'Glossary', 'About'):
        if sec not in by:
            continue
        lines.append(f'## {sec}\n')
        for p in by[sec]:
            tag = ' (Behind The Scenes, spoilers)' if p.layer == 'bts' else ''
            parts = getattr(p, 'md_parts', [])
            more = f' Its full notes are split into {len(parts)} files, linked from that page.' if parts else ''
            lines.append(f'- [{p.title}]({CFG["base_url"]}{p.url}index.md){tag}: {p.desc}{more}')
        lines.append('')
    langs = write_lang_llms(out, lang_twins or {})
    if langs:
        lines += ['## Other languages', '',
                  'AI-translated versions of the pages, as Markdown (only pages translated well enough to offer):', '']
        lines += [f'- [{name}]({CFG["base_url"]}/{code}/llms.txt): {n} pages' for code, name, n in langs] + ['']
    open(os.path.join(out, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    return bundles

def full_text_bundles(pages):
    """The two all-in-one files: (Public text, Public + Behind The Scenes text, the header both start with)."""
    pub, full = [], []
    order = {'Home': 0, 'Light Novel': 1, 'Webcomic': 1.5, 'World Lore': 2, 'Glossary': 3, 'Gallery': 4, 'About': 5}
    for p in sorted([p for p in pages if not p.url.endswith('.html') and p.section != 'Search'], key=lambda p: order.get(p.section, 9)):
        if p.md_public.strip():
            pub.append(f'\n\n---\nURL: {CFG["base_url"]}{p.url}\n\n{md_absolute(p.md_public.strip())}')
        both = page_md(p)
        full.append(f'\n\n---\nURL: {CFG["base_url"]}{p.url}\n\n{both}')
    head = (f'# {CFG["title"]}: full text\n\nSource: {CFG["base_url"]}. Copyright © {CFG["author"]}; "A Husband Out of This World" and '
            f'"#HusbandOutWorld" are trademarks of {CFG["author"]}. License: CC BY-NC-SA 4.0. eBook: {CFG["amazon_url"]}\n')
    clean = lambda s: re.sub(r'\(data:image/[^)]+\)', '(embedded-image)', s)
    return (head + '(Public layer only.)\n' + clean(''.join(pub)),
            head + '(Public and Behind The Scenes layers. Contains spoilers.)\n' + clean(''.join(full)), head)

def write_sitemap(out, pages, lang_ready=(), bundles=(), lang_twins=None):
    pages = [p for p in pages if not p.url.endswith('.html')]
    locs = [p.url for p in pages]
    locs += [f'/{code}{url}' for code, url in lang_ready]
    # the files for AI readers: llms.txt, the full-text bundles and every page's Markdown twin
    locs += ['/llms.txt', '/llms-full.txt', '/llms-full-bts.txt'] + [u for _, u, _, _ in bundles]
    locs += [p.url + name for p in pages for name in ['index.md'] + getattr(p, 'md_parts', [])]
    for code, items in sorted((lang_twins or {}).items()):
        locs += [f'/{code}/llms.txt'] + [f'/{code}{p.url}index.md' for p, _ in items]
    urls = ''.join(f'<url><loc>{CFG["base_url"]}{quote(u)}</loc></url>' for u in locs)
    open(os.path.join(out, 'sitemap.xml'), 'w').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')

# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, '_site'))
    ap.add_argument('--cache', default=os.path.join(ROOT, '.media-cache'))
    ap.add_argument('--no-images', action='store_true')
    ap.add_argument('--base-path', default='', help='path the site is served under, e.g. /HusbandOutWorld (GitHub project page); empty for a custom domain')
    ap.add_argument('--site-url', default='', help='full public address of the site; defaults to base_url in content/site.json')
    a = ap.parse_args()
    global BASE
    BASE = a.base_path.rstrip('/')
    if a.site_url:
        CFG['base_url'] = a.site_url.rstrip('/')
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    b = Builder(a.out, a.cache, not a.no_images)
    b.build_home()
    b.build_novel()
    import webcomic  # the vertical-scroll webcomic reader (tools/webcomic.py)
    webcomic.build(b, sys.modules[__name__])
    import blog  # the Blog page and its photo grid (tools/blog.py)
    blog.build(b, sys.modules[__name__])
    topic_pages = {t['slug']: b.build_topic(t) for t in CFG['topics']}
    b.build_lore_index(topic_pages)
    b.build_gallery()
    b.build_glossary()
    b.build_about()
    b.build_search_page()
    b.build_404()
    b.media.process()
    b.write()
    fav = b.media.file(os.path.join(BTS, 'Illustrations', 'Emblems', 'Forway city emblem.png'))
    try:
        im = Image.open(os.path.join(BTS, 'Illustrations', 'Emblems', 'Forway city emblem.png'))
        im.thumbnail((128, 128)); im.save(os.path.join(a.out, 'media', 'forway-emblem.png'))  # the menu's logo
        im.thumbnail((64, 64)); im.save(os.path.join(a.out, 'media', 'favicon.png'))
    except Exception as ex:
        print('favicon failed', ex)
    app = CFG.get('app')
    if app:  # installable app (PWA): manifest, icons, service worker
        pwa.write(a.out, base=BASE, name=app['name'], short_name=app['short_name'], description=app['description'],
                  theme_color=app['theme_color'], background_color=app['background_color'],
                  logo=os.path.join(ROOT, app['logo']),
                  shortcuts=[{**sc, 'image': os.path.join(ROOT, sc['image'])} for sc in app.get('shortcuts', [])],
                  homes=['/'],  # a language's home page (/ja/ ...) is saved on its first visit
                  cache_prefix='hoow', version=app.get('version', 'v1'),
                  save_visited_pages=app.get('save_visited_pages', True),
                  extra_files=['/media/favicon.png', '/media/forway-emblem.png'])
    print(f'pages: {len(b.pages)}, images: {len(b.media.info)}, glossary terms: {len(b.glossary)}')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build the #HusbandOutWorld website from the Legacy folder.

Everything the site shows comes from Legacy/ (the author's originals):
  * Legacy/Public            -> the "Public" layer (the old blog, as published)
  * Legacy/Behind The Scenes -> the "Behind The Scenes" layer (the full docs)
content/ holds the page map, alt text and typo fixes. Nothing here writes lore.

Usage: python tools/build.py [--out _site] [--cache .media-cache] [--no-images]
"""
import argparse, base64, hashlib, html, json, os, re, shutil, sys, unicodedata
from concurrent.futures import ProcessPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import quote, unquote

from markdown_it import MarkdownIt
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, 'Legacy')
BTS = os.path.join(LEGACY, 'Behind The Scenes')
PUB = os.path.join(LEGACY, 'Public')
CONTENT = os.path.join(ROOT, 'content')
SITE_SRC = os.path.join(ROOT, 'site')

CFG = json.load(open(os.path.join(CONTENT, 'site.json')))
ALT = json.load(open(os.path.join(CONTENT, 'alt-text.json'))) if os.path.exists(os.path.join(CONTENT, 'alt-text.json')) else {}
SUMMARIES = json.load(open(os.path.join(CONTENT, 'summaries.json'))) if os.path.exists(os.path.join(CONTENT, 'summaries.json')) else {}
TYPOS = json.load(open(os.path.join(CONTENT, 'typos.json'))) if os.path.exists(os.path.join(CONTENT, 'typos.json')) else {}
GH_BLOB = CFG['repo_url'] + '/blob/main/'

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
    return clean_heading(raw).strip('- ').strip()

def norm(s):
    s = re.sub(r'\{[^}]*\}', '', s.lower())
    s = re.sub(r'\([^)]*\)', '', s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

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
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'[*_`#>]|\\', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= n:
        return t
    cut = t[:n]
    p = max(cut.rfind('. '), cut.rfind('! '), cut.rfind('? '))
    return (cut[:p + 1] if p > 60 else cut.rsplit(' ', 1)[0] + '…')

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

    def data_uri(self, uri, origin):
        m = re.match(r'data:image/[a-z+]+;base64,(.*)', uri, re.S)
        if not m:
            return None
        raw = base64.b64decode(m.group(1))
        key = hashlib.sha1(raw).hexdigest()[:14]
        if key not in self.info:
            p = os.path.join(self.cache, key + '.src')
            if not os.path.exists(p):
                open(p, 'wb').write(raw)
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

    def _image(self, tokens, idx, options, env):
        t = tokens[idx]
        src = t.attrGet('src') or ''
        alt = self.md.renderer.renderInlineAsText(t.children or [], options, env)
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
        return self.media.file(p)

    def render(self, text, base=ROOT, origin='', refs=None):
        if refs:
            text = re.sub(r'!\[([^\]]*)\]\[(image\d+)\]', lambda m: f'![{m.group(1)}]({refs[m.group(2)]})' if m.group(2) in refs else '', text)
        return self.md.render(text, {'base': base, 'origin': origin})

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
    text, refs = split_refs(open(path, encoding='utf-8').read())
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
    text = open(path, encoding='utf-8').read()
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

    def md_bts_block(self, md, refs, origin):
        return self.r.render(fix_typos(md, origin), base=os.path.join(ROOT, os.path.dirname(origin)), origin=origin, refs=refs)

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
            public_sections.extend(secs)
        entries, intro_bts, refs_all = [], [], {}
        for src in t['bts']:
            path = os.path.join(BTS, src)
            page.sources.append(rel(path))
            blocks, refs = parse_lore(path)
            origin = rel(path)
            category = None
            for b in blocks:
                b['origin'], b['refs'] = origin, refs
                if b['kind'] == 'intro':
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
                if b['body'].strip():
                    body.append(f'<div class="layer bts cat-notes">{self.md_bts_block(b["body"], b["refs"], b["origin"])}</div>')
                    page.md_bts += f'## {b["title"]}\n\n{b["body"]}\n\n'
                else:
                    page.md_bts += f'## {b["title"]}\n\n'
                if cls != 'bts':
                    page.md_public += f'## {b["title"]}\n\n'
                continue
            e = b
            is_meta = e['title'].lower() in meta_cats
            wd, rest = extract_website_description(e['body'])
            pub_md = '\n\n'.join(strip_images(s['md']) for s in e['public_secs']) or wd
            pub_src = ', '.join(sorted({s['file'] for s in e['public_secs']})) or ('Website Description in ' + e['origin'] if wd else '')
            img_src = None
            for s in e['public_secs']:
                fi = first_image(s['md'])
                if fi and not fi.startswith('http'):
                    img_src = self.r.resolve(fi, {'base': PUB})
                    break
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
            if pub_md:
                h.append(f'<div class="layer public">{fig}{self.r.render(fix_typos(pub_md, e["origin"]), base=PUB)}'
                         f'<p class="src src-pub">Public text: {esc(pub_src)}</p></div>')
            if rest.strip() or wd:
                bts_md = rest if pub_md == wd else e['body']
                h.append(f'<div class="layer bts">{"" if pub_md else fig}<p class="bts-label">Behind the Scenes · full notes</p>'
                         f'{self.md_bts_block(bts_md, e["refs"], e["origin"])}'
                         f'<p class="src">Source: <a href="{gh_link(os.path.join(ROOT, e["origin"]))}">{esc(e["origin"])}</a></p></div>')
            h.append('</section>')
            body.append('\n'.join(h))
            if pub_md:
                page.md_public += f'### {e["title"]}\n\n{pub_md}\n\n'
            page.md_bts += f'### {e["title"]}\n\n{e["body"]}\n\n'
            gl_desc = first_sentences(pub_md) if pub_md else first_sentences(rest)
            if not is_meta:
                self.glossary.append({'term': e['title'], 'topic': t['title'], 'url': url + '#' + anchor,
                                      'public': bool(pub_md), 'desc': gl_desc,
                                      'category': (e.get('category') or {}).get('title', '')})
            page.search.append({'t': e['title'], 'u': url + '#' + anchor, 's': t['title'],
                                'x': first_sentences(pub_md or '', 300), 'xb': first_sentences(e['body'], 400),
                                'b': layer == 'bts'})
        for s in leftovers:
            anchor = slugify(s['heading'] or s['page'])
            fi = first_image(s['md'])
            info = self.r.resolve(fi, {'base': PUB}) if fi and not fi.startswith('http') else None
            if not info:
                p = self.art.find(s['heading'], t.get('art', []))
                info = self.media.file(p) if p else None
            page.toc.append((anchor, s['heading'] or s['page'], 'both', 'entry'))
            body.append(f'<section class="entry layer both" id="{anchor}"><h3>{esc(s["heading"] or s["page"])}</h3>'
                        f'<div class="layer public">{self.figure(info)}{self.r.render(fix_typos(strip_images(s["md"]), s["file"]), base=PUB)}'
                        f'<p class="src src-pub">Public text: {esc(s["file"])}</p></div></section>')
            page.md_public += f'### {s["heading"]}\n\n{strip_images(s["md"])}\n\n'
            page.search.append({'t': s['heading'] or s['page'], 'u': url + '#' + anchor, 's': t['title'],
                                'x': first_sentences(s['md'], 300), 'b': False})
        if hidden_count:
            body.append(f'<p class="layer public-only more-bts">{hidden_count} more entr{"y" if hidden_count == 1 else "ies"} '
                        f'on this page {"is" if hidden_count == 1 else "are"} only in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        if not t['public']:
            body.insert(0, '<p class="layer public-only notice">The blog never had a public page for this topic, so Public mode shows a short summary. '
                           'The full entries are in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        page.html = '\n'.join(body)
        page.desc = first_sentences(page.md_public or page.md_bts, 160)
        self.add(page)
        return page

    # ---- novel
    def parse_volume(self, v):
        path = os.path.join(BTS, v['source'])
        text, refs = split_refs(open(path, encoding='utf-8').read())
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
            if stripped in ('**Prologue**', 'Prologue') and (cur is None or cur['title'] != 'Prologue'):
                new_chapter('Prologue')
                continue
            target = sub['lines'] if sub else (cur['intro'] if cur else front)
            target.append(line.lstrip('\t').lstrip() if not stripped.startswith(('* ', '- ')) else line)
        return path, base, refs, front, chapters

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
                    smd = '\n'.join(s['lines']).strip()
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
                vparts.append(f'<li><a href="{curl}">{esc(t)}</a> <span class="muted">{n} part{"s" if n != 1 else ""}</span></li>' if n else f'<li><a href="{curl}">{esc(t)}</a></li>')
            vparts.append('</ol>')
            vpage.html = '\n'.join(vparts)
            vpage.md_public = f'# {v["title"]}\n\n{front_md}\n\n' + '\n'.join(f'- [{t}]({u}index.md)' for u, t, _ in toc)
            vpage.desc = f'{v["title"]}, {v["arc"]} of the #HusbandOutWorld light novel. Read it free here.'
            vpage.jsonld = {'@context': 'https://schema.org', '@type': 'Book', 'name': v['title'],
                            'isPartOf': {'@type': 'BookSeries', 'name': CFG['title']},
                            'author': {'@type': 'Person', 'name': CFG['author']},
                            'illustrator': [{'@type': 'Person', 'name': a} for a in CFG['artists']],
                            'url': CFG['base_url'] + vurl, 'sameAs': CFG['amazon_url'], 'inLanguage': 'en'}
            self.add(vpage)
            for cp in chapter_pages:
                self.add(cp)
            cover = None
            if chapters and chapters[0]['subs']:
                cover = self.r.resolve(chapters[0]['subs'][0]['img'], {'base': base})
            vols_html.append((v, vurl, cover, toc))
        # story notes (behind the scenes only)
        notes = []
        for n in CFG['story_notes']:
            path = os.path.join(BTS, n['source'])
            text, refs = split_refs(open(path, encoding='utf-8').read())
            url = f'/novel/{n["slug"]}/'
            p = Page(url, n['title'], 'Light Novel', layer='bts')
            p.sources.append(rel(path))
            p.html = (f'<h1>{esc(n["title"])}</h1>' + bts_gate('These are the author\'s story notes, including unreleased arcs.') +
                      f'<div class="layer bts"><p class="bts-label">Behind the Scenes · story notes</p>{self.r.render(fix_typos(text, rel(path)), base=os.path.dirname(path), origin=rel(path), refs=refs)}'
                      f'<p class="src">Source: <a href="{gh_link(path)}">{esc(rel(path))}</a></p></div>')
            p.md_bts = text
            p.desc = f'{n["title"]}: the author\'s story notes (spoilers).'
            p.search.append({'t': n['title'], 'u': url, 's': 'Story notes', 'xb': first_sentences(text, 400), 'b': True})
            self.add(p)
            notes.append((n, url))
        # novel index
        idx = Page('/novel/', 'The Light Novel', 'Light Novel')
        parts = ['<h1>The Light Novel</h1>',
                 '<p class="lede">Arc #1, <em>Dubious Contract</em>, is complete in three volumes. Read every chapter here, with every subchapter illustration.</p>',
                 amazon_note(), '<div class="vol-grid">']
        for v, vurl, cover, toc in vols_html:
            img = f'<img src="{cover["thumb"]}" alt="Opening illustration of {esc(v["title"])}" loading="lazy">' if cover else ''
            parts.append(f'<a class="vol-card" href="{vurl}">{img}<span class="vol-title">{esc(v["title"])}</span>'
                         f'<span class="muted">{len(toc)} chapters</span></a>')
        parts.append('</div>')
        parts.append('<h2 class="layer bts">Story notes</h2><ul class="layer bts">' + ''.join(f'<li><a href="{u}">{esc(n["title"])}</a></li>' for n, u in notes) + '</ul>')
        parts.append('<p class="layer public-only more-bts">The author\'s notes for Arcs #2 to #5 are in <button class="linklike" data-go-bts>Behind The Scenes</button>.</p>')
        idx.html = '\n'.join(parts)
        idx.md_public = '# The Light Novel\n\n' + '\n'.join(f'- [{v["title"]}]({u}index.md)' for v, u, _, _ in vols_html)
        idx.md_bts = '\n'.join(f'- [{n["title"]}]({u}index.md)' for n, u in notes)
        idx.desc = 'Read the #HusbandOutWorld light novel, Arc #1 Dubious Contract, free online.'
        self.add(idx)

    # ---- about pages
    def build_about(self):
        links = []
        for a in CFG['about_pages']:
            meta, intro, secs = parse_public(a['public'])
            url = f'/about/{a["slug"]}/'
            p = Page(url, a['title'], 'About')
            p.sources.append(rel(os.path.join(PUB, a['public'])))
            md = intro['md'] + '\n\n' + '\n\n'.join((f'## {s["heading"]}\n\n' if s['heading'] else '') + s['md'] for s in secs)
            p.html = (f'<h1>{esc(a["title"])}</h1>' + self.r.render(fix_typos(md, a['public']), base=PUB, origin=a['public']) +
                      f'<p class="src">From the original blog page: <a href="{esc(meta.get("original_url", ""))}">{esc(meta.get("original_url", ""))}</a> (archived in <a href="{gh_link(os.path.join(PUB, a["public"]))}">{esc(rel(os.path.join(PUB, a["public"])))}</a>)</p>')
            p.md_public = f'# {a["title"]}\n\n' + md
            p.desc = first_sentences(md, 160)
            p.search.append({'t': a['title'], 'u': url, 's': 'About', 'x': first_sentences(md, 300), 'b': False})
            self.add(p)
            links.append((a['title'], url))
        # AI disclosure page from the repo file
        path = os.path.join(ROOT, 'AI-DISCLOSURE.md')
        if os.path.exists(path):
            text = open(path, encoding='utf-8').read()
            p = Page('/about/ai-disclosure/', 'AI Disclosure', 'About')
            p.html = self.r.render(text, base=ROOT)
            p.md_public = text
            p.desc = 'Which parts of this website are human work, which parts an AI wrote, and how they fit together.'
            self.add(p)
            links.append(('AI Disclosure', '/about/ai-disclosure/'))
        idx = Page('/about/', 'About the Series', 'About')
        idx.html = ('<h1>About the Series</h1><ul class="link-list">' + ''.join(f'<li><a href="{u}">{esc(t)}</a></li>' for t, u in links) +
                    f'<li><a href="{CFG["dnd_url"]}">D&amp;D West March Campaign</a></li>'
                    f'<li><a href="{CFG["vraki_url"]}">Vraki Language app</a></li>'
                    f'<li><a href="{CFG["repo_url"]}">GitHub repository</a></li></ul>')
        idx.md_public = '# About the Series\n\n' + '\n'.join(f'- [{t}]({u}index.md)' for t, u in links)
        idx.desc = 'About the #HusbandOutWorld series: FAQ, afterwords, the final blog post and more.'
        self.add(idx)

    # ---- lore index
    def build_lore_index(self, topic_pages):
        p = Page('/lore/', 'World Lore', 'World Lore')
        parts = ['<h1>World Lore</h1>',
                 '<p class="lede">The world of Vraki: its kingdoms, peoples, soul energy science, beasts and plants. '
                 'Public mode shows what the old blog showed. Behind The Scenes adds the author\'s full notes.</p>']
        md = ['# World Lore\n']
        for g in CFG['lore_groups']:
            parts.append(f'<h2>{esc(g["title"])}</h2><div class="topic-grid">')
            md.append(f'## {g["title"]}\n')
            for slug in g['topics']:
                tp = topic_pages[slug]
                pub = any(l != 'bts' for _, _, l, k in tp.toc if k == 'entry')
                cls = 'both' if pub or tp.md_public.strip() else 'bts'
                parts.append(f'<a class="topic-card layer {cls}" href="{tp.url}"><span>{esc(tp.title)}</span>'
                             f'<span class="muted">{esc(tp.desc[:110])}</span></a>')
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
        for p in self.art.files:
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
        logo = self.media.file(os.path.join(BTS, 'Logo and Font', 'Cover Text no subtitle.png'))
        world = self.media.file(os.path.join(BTS, 'WorldMapMD.png'))
        emblem = self.media.file(os.path.join(BTS, 'Illustrations', 'Emblems', 'Forway city emblem.png'))
        meta, intro, secs = parse_public('webcomic.md')
        blurb = ''
        for s in [intro] + secs:
            m = re.search(r'A botched soul experiment[^\n]*', s['md'])
            if m:
                blurb = m.group(0)
                break
        p.html = f'''
<section class="hero">
  <img class="hero-logo" src="{logo['url']}" alt="A Husband Out of This World" width="1588" height="933">
  <p class="hero-blurb">{esc(blurb)}</p>
  <div class="hero-actions">
    <a class="btn primary" href="/novel/vol-1/">Start reading Vol 1</a>
    <a class="btn" href="/lore/">Explore the World Lore</a>
  </div>
  {amazon_note()}
</section>
<section class="home-grid">
  <a class="home-card" href="/novel/"><h2>The Light Novel</h2><p>Arc #1 in three volumes, with every illustration.</p></a>
  <a class="home-card" href="/lore/"><h2>World Lore</h2><p>Kingdoms, races, soul energy, beasts and plants.</p></a>
  <a class="home-card" href="/gallery/"><h2>Gallery</h2><p>All the art by {" and ".join(CFG["artists"])}.</p></a>
  <a class="home-card" href="/glossary/"><h2>Glossary</h2><p>Every name A to Z, with the author's pronunciation.</p></a>
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
<figure class="world-map"><a class="img-link" href="{world['url']}" data-full="{world['url']}"><img src="{world['url']}" alt="Map of the world of Vraki, showing the Four Kingdoms and the lands around them" loading="lazy"></a><figcaption>The world of Vraki</figcaption></figure>
'''
        p.md_public = (f'# {CFG["title"]}\n\n{blurb}\n\n'
                       '- [The Light Novel](/novel/index.md)\n- [World Lore](/lore/index.md)\n- [Gallery](/gallery/index.md)\n'
                       '- [Glossary](/glossary/index.md)\n- [About](/about/index.md)\n')
        p.desc = blurb[:160]
        p.jsonld = {'@context': 'https://schema.org', '@type': 'BookSeries', 'name': CFG['title'],
                    'alternateName': CFG['short_title'], 'author': {'@type': 'Person', 'name': CFG['author']},
                    'illustrator': [{'@type': 'Person', 'name': a} for a in CFG['artists']],
                    'url': CFG['base_url'] + '/', 'description': blurb,
                    'hasPart': [{'@type': 'Book', 'name': v['title'], 'url': CFG['base_url'] + f'/novel/{v["slug"]}/'} for v in CFG['volumes']],
                    'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/'}
        self.add(p)

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
        for p in self.pages:
            if p.url.endswith('.html'):
                path = os.path.join(self.out, p.url.lstrip('/'))
            else:
                path = os.path.join(self.out, p.url.lstrip('/'), 'index.html')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w', encoding='utf-8').write(page_html(p, nav))
            if not p.url.endswith('.html'):
                open(os.path.join(os.path.dirname(path), 'index.md'), 'w', encoding='utf-8').write(page_md(p))
        # search index
        idx = [s for p in self.pages for s in p.search]
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
        write_llms(self.out, self.pages)
        write_sitemap(self.out, self.pages)
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
        open(os.path.join(self.out, '.nojekyll'), 'w').write('')
        if os.path.exists(os.path.join(ROOT, 'CNAME')):
            shutil.copyfile(os.path.join(ROOT, 'CNAME'), os.path.join(self.out, 'CNAME'))
        return em

def roman(s):
    vals = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}
    s = s.lower(); total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total

def amazon_note():
    return (f'<aside class="support-note">Reading for free is fine by the author. If you want the eBook, '
            f'<a href="{CFG["amazon_url"]}" rel="noopener">please support the series by getting it on Amazon</a>.</aside>')

def bts_gate(why):
    return (f'<div class="layer public-only gate"><p><strong>Behind The Scenes only.</strong> {esc(why)}</p>'
            '<button class="btn" data-go-bts>Show Behind The Scenes</button></div>')

# --------------------------------------------------------------------------- templates

NAV = [('Novel', '/novel/'), ('World Lore', '/lore/'), ('Gallery', '/gallery/'), ('Glossary', '/glossary/'), ('About', '/about/')]

def nav_html():
    return ''.join(f'<a href="{u}">{t}</a>' for t, u in NAV)

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
        head_title = f'<header class="page-head"><p class="vraki-overline" aria-hidden="true">{esc(p.title)}</p><h1>{esc(p.title)}</h1></header>'
    jsonld = f'<script type="application/ld+json">{json.dumps(p.jsonld, ensure_ascii=False)}</script>' if p.jsonld else ''
    srcs = ''
    if p.sources:
        srcs = '<p class="page-sources">Built from: ' + ', '.join(f'<a href="{GH_BLOB}{quote(s)}">{esc(s)}</a>' for s in p.sources) + '</p>'
    md_link = '' if p.url.endswith('.html') else f'<link rel="alternate" type="text/markdown" href="{p.url}index.md">'
    return f'''<!doctype html>
<html lang="en" data-mode="public" data-theme="dark">
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
<script>try{{var s=JSON.parse(localStorage.getItem('hoow')||'{{}}');var d=document.documentElement;if(s.mode)d.dataset.mode=s.mode;if(s.theme)d.dataset.theme=s.theme;if(s.vraki)d.classList.add('vraki');if(s.size)d.style.setProperty('--fs',s.size+'px')}}catch(e){{}}</script>
<link rel="stylesheet" href="/css/site.css">
{jsonld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="topbar keep-latin">
  <a class="brand" href="/"><span class="brand-mark" aria-hidden="true"></span><span class="brand-text">#HusbandOutWorld</span></a>
  <nav class="mainnav">{nav}</nav>
  <div class="controls">
    <form class="searchbox" action="/search/" role="search"><input name="q" type="search" placeholder="Search" aria-label="Search the site"></form>
    <button class="mode-switch" type="button" role="switch" aria-checked="false" title="Switch between Public and Behind The Scenes">
      <span class="mode-public">Public</span><span class="knob" aria-hidden="true"></span><span class="mode-bts">Behind The Scenes</span>
    </button>
    <button class="settings-btn" type="button" aria-haspopup="dialog" aria-label="Reading settings">Aa</button>
  </div>
</header>
<div class="mode-banner layer bts keep-latin">Behind The Scenes is on: pages include the author's full notes and spoilers.</div>
<main id="main" class="{'has-toc' if toc else ''}">
  {toc}
  <article class="content">
    {head_title}
    {p.html}
    {pager}
    {srcs}
  </article>
</main>
<footer class="footer keep-latin">
  <p>© {CFG['author']}. Art by {' and '.join(CFG['artists'])}. Licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>.
  Vraki typeface © 2024 Deovandski Skibinski Junior, https://husbandoutworld.com/ (<a href="/fonts/VRAKI-FONT-LICENSE.md">font license</a>).</p>
  <p>This site was built with AI assistance from the author's originals. <a href="/about/ai-disclosure/">AI disclosure</a> · <a href="{CFG['repo_url']}">GitHub</a> · <a href="/llms.txt">llms.txt</a> · <a href="{p.url if not p.url.endswith('.html') else '/'}index.md">This page as Markdown</a></p>
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
    <h2>Reading settings</h2>
    <label class="setting"><span>Theme</span><select data-setting="theme"><option value="dark">Dark</option><option value="light">Light</option></select></label>
    <label class="setting"><span>Text size</span><input data-setting="size" type="range" min="14" max="26" step="1" value="18"></label>
    <label class="setting"><span>Vraki mode <small>(read everything in the Vraki script)</small></span><input data-setting="vraki" type="checkbox"></label>
    <div class="dialog-actions"><button class="btn primary" value="close">Done</button></div>
  </form>
</dialog>
<div id="lightbox" class="lightbox keep-latin" hidden><button class="lb-close" aria-label="Close">×</button><img alt=""></div>
<script src="/js/app.js" defer></script>
</body>
</html>
'''

def page_md(p):
    head = (f'---\ntitle: "{p.title}"\nurl: {CFG["base_url"]}{p.url}\nsection: {p.section}\n'
            f'spoilers: {"yes (Behind The Scenes only)" if p.layer == "bts" else "public layer first, Behind The Scenes after"}\n'
            f'sources: [{", ".join(p.sources)}]\n---\n\n')
    out = head
    if p.md_public.strip():
        out += '<!-- PUBLIC LAYER: as published for readers -->\n\n' + p.md_public.strip() + '\n\n'
    if p.md_bts.strip():
        out += '<!-- BEHIND THE SCENES LAYER: the author\'s full notes, contains spoilers -->\n\n' + p.md_bts.strip() + '\n'
    out = re.sub(r'\[image\d+\]: <data:[^>]+>', '', out)
    out = re.sub(r'\(data:image/[^)]+\)', '(embedded-image)', out)
    return out

def write_llms(out, pages):
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
             f'License: CC BY-NC-SA 4.0. Built with AI assistance from the author\'s originals: {CFG["base_url"]}/about/ai-disclosure/', '',
             '## Full text bundles', '',
             f'- [Public layer, everything]({CFG["base_url"]}/llms-full.txt): the novel and the public lore in one file',
             f'- [Everything, including Behind The Scenes]({CFG["base_url"]}/llms-full-bts.txt): adds the full notes (spoilers)',
             f'- [Glossary JSON]({CFG["base_url"]}/data/glossary.json), [Image list with alt text]({CFG["base_url"]}/data/images.json), [Page list]({CFG["base_url"]}/data/pages.json)', '']
    for sec in ('Light Novel', 'World Lore', 'Gallery', 'Glossary', 'About'):
        if sec not in by:
            continue
        lines.append(f'## {sec}\n')
        for p in by[sec]:
            tag = ' (Behind The Scenes, spoilers)' if p.layer == 'bts' else ''
            lines.append(f'- [{p.title}]({CFG["base_url"]}{p.url}index.md){tag}: {p.desc}')
        lines.append('')
    open(os.path.join(out, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    pub, full = [], []
    order = {'Home': 0, 'Light Novel': 1, 'World Lore': 2, 'Glossary': 3, 'Gallery': 4, 'About': 5}
    for p in sorted([p for p in pages if not p.url.endswith('.html') and p.section != 'Search'], key=lambda p: order.get(p.section, 9)):
        if p.md_public.strip():
            pub.append(f'\n\n---\nURL: {CFG["base_url"]}{p.url}\n\n{p.md_public.strip()}')
        both = page_md(p)
        full.append(f'\n\n---\nURL: {CFG["base_url"]}{p.url}\n\n{both}')
    head = f'# {CFG["title"]}: full text\n\nSource: {CFG["base_url"]}. License: CC BY-NC-SA 4.0. eBook: {CFG["amazon_url"]}\n'
    clean = lambda s: re.sub(r'\(data:image/[^)]+\)', '(embedded-image)', s)
    open(os.path.join(out, 'llms-full.txt'), 'w', encoding='utf-8').write(head + '(Public layer only.)\n' + clean(''.join(pub)))
    open(os.path.join(out, 'llms-full-bts.txt'), 'w', encoding='utf-8').write(head + '(Public and Behind The Scenes layers. Contains spoilers.)\n' + clean(''.join(full)))

def write_sitemap(out, pages):
    urls = ''.join(f'<url><loc>{CFG["base_url"]}{p.url}</loc></url>' for p in pages if not p.url.endswith('.html'))
    open(os.path.join(out, 'sitemap.xml'), 'w').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')

# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, '_site'))
    ap.add_argument('--cache', default=os.path.join(ROOT, '.media-cache'))
    ap.add_argument('--no-images', action='store_true')
    a = ap.parse_args()
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    b = Builder(a.out, a.cache, not a.no_images)
    b.build_home()
    b.build_novel()
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
        im.thumbnail((64, 64)); im.save(os.path.join(a.out, 'media', 'favicon.png'))
    except Exception as ex:
        print('favicon failed', ex)
    print(f'pages: {len(b.pages)}, images: {len(b.media.info)}, glossary terms: {len(b.glossary)}')

if __name__ == '__main__':
    main()

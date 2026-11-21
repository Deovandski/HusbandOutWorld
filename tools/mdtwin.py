"""Markdown twins of translated pages (issue #76).

English pages get their index.md from the Markdown the build already has. Translated pages only exist as HTML
(tools/i18n.py swaps the text segment by segment), so their twin is made by turning the page's <article class="content">
back into plain Markdown. Navigation, buttons and other visual noise are left out; Behind The Scenes blocks are
fenced with HTML comments, like the English twins.

Usage (from tools/build.py):
    md = mdtwin.page_markdown(translated_html, base_url=CFG['base_url'])
"""
import re
from lxml import html as LH

SKIP_TAGS = {'script', 'style', 'svg', 'nav', 'button', 'input', 'select', 'textarea', 'form', 'dialog', 'noscript', 'template'}
# classes whose element (and everything inside) stays out of the twin
SKIP_CLASSES = {'toc', 'pager', 'support-note', 'public-only', 'bts-label', 'src', 'src-pub', 'page-sources',
                'vraki-overline', 'i18n-banner', 'more-bts', 'filter'}
BLOCK = {'div', 'section', 'article', 'header', 'footer', 'figure', 'aside', 'main'}


def _classes(el):
    return set((el.get('class') or '').split())


def _abs(url, base_url):
    if url.startswith('/') and not url.startswith('//'):
        return base_url + url
    return url


def _inline(el, base_url):
    """Text of an element with inline Markdown (links, bold, italics, images, line breaks)."""
    out = [el.text or '']
    for c in el:
        if not isinstance(c.tag, str) or c.tag in SKIP_TAGS or _classes(c) & SKIP_CLASSES or c.get('hidden') is not None:
            out.append(c.tail or '')
            continue
        t = c.tag
        if t == 'br':
            out.append('\x00')
        elif t == 'img':
            out.append(f'![{c.get("alt", "")}]({_abs(c.get("src", ""), base_url)})')
        elif t == 'a':
            inner = _inline(c, base_url).strip()
            href = c.get('href', '')
            if c.find('.//img') is not None or not href or href.startswith('#'):
                out.append(inner)
            else:
                out.append(f'[{inner}]({_abs(href, base_url)})' if inner else '')
        elif t in ('strong', 'b'):
            inner = _inline(c, base_url).strip()
            out.append(f'**{inner}**' if inner else '')
        elif t in ('em', 'i'):
            inner = _inline(c, base_url).strip()
            out.append(f'*{inner}*' if inner else '')
        elif t == 'code':
            out.append(f'`{c.text_content()}`')
        else:
            out.append(_inline(c, base_url))
        out.append(c.tail or '')
    return re.sub(r'\s+', ' ', ''.join(out)).replace(' \x00 ', '\x00').replace('\x00', '  \n')


def _blocks(el, base_url, depth=0):
    """Markdown blocks (a list of strings) for an element and its children."""
    res = []
    for c in el:
        if not isinstance(c.tag, str) or c.tag in SKIP_TAGS or _classes(c) & SKIP_CLASSES or c.get('hidden') is not None:
            continue
        t, cls = c.tag, _classes(c)
        bts = 'layer' in cls and 'bts' in cls
        start = len(res)
        if re.fullmatch(r'h[1-6]', t):
            txt = _inline(c, base_url).strip()
            if txt:
                res.append('#' * int(t[1]) + ' ' + txt)
        elif t in ('ul', 'ol'):
            items = []
            for n, li in enumerate([x for x in c if x.tag == 'li' and not _classes(x) & SKIP_CLASSES], 1):
                lead = f'{n}. ' if t == 'ol' else '- '
                head = _inline_li(li, base_url).strip()
                sub = [x for x in li if x.tag in ('ul', 'ol')]
                line = '  ' * depth + lead + head
                for s in sub:
                    line += '\n' + '\n'.join(_blocks_list(s, base_url, depth + 1))
                if head or sub:
                    items.append(line)
            if items:
                res.append('\n'.join(items))
        elif t == 'blockquote':
            inner = '\n\n'.join(_blocks(c, base_url)) or _inline(c, base_url).strip()
            if inner:
                res.append('\n'.join('> ' + l if l else '>' for l in inner.split('\n')))
        elif t == 'table':
            rows = [[_inline(td, base_url).strip().replace('|', '\\|') for td in tr if td.tag in ('td', 'th')]
                    for tr in c.iter('tr')]
            rows = [r for r in rows if r]
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [''] * (w - len(r)) for r in rows]
                res.append('\n'.join(['| ' + ' | '.join(rows[0]) + ' |', '|' + ' --- |' * w] +
                                     ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]))
        elif t == 'hr':
            res.append('---')
        elif t == 'img' or (t == 'a' and c.find('.//img') is not None and not [x for x in c if x.tag not in ('img',)]):
            img = c if t == 'img' else c.find('.//img')
            res.append(f'![{img.get("alt", "")}]({_abs(img.get("src", ""), base_url)})')
        elif t == 'a' and c.get('href') and not c.get('href').startswith('#'):
            txt = _inline(c, base_url).strip()   # a card or button link: keep its text and where it goes
            if txt:
                res.append(f'[{txt}]({_abs(c.get("href"), base_url)})')
        elif t == 'figcaption':
            txt = _inline(c, base_url).strip()
            if txt:
                res.append(f'*{txt}*')
        elif t in BLOCK or any(isinstance(x.tag, str) and (x.tag in BLOCK or re.fullmatch(r'h[1-6]|ul|ol|table|blockquote|figure', x.tag)) for x in c):
            if (c.text or '').strip():
                res.append(c.text.strip())
            res.extend(_blocks(c, base_url, depth))
        else:
            txt = _inline(c, base_url).strip()
            if txt:
                res.append(txt)
        if bts and len(res) > start:
            res.insert(start, '<!-- BEHIND THE SCENES: the author\'s full notes, contains spoilers -->')
            res.append('<!-- /BEHIND THE SCENES -->')
    return res


def _inline_li(li, base_url):
    """A list item's own text, leaving out nested lists."""
    clone = LH.fromstring(LH.tostring(li))
    for s in clone.findall('ul') + clone.findall('ol'):
        s.drop_tree()
    return _inline(clone, base_url)


def _blocks_list(lst, base_url, depth):
    tmp = LH.Element('div')
    tmp.append(LH.fromstring(LH.tostring(lst)))
    return _blocks(tmp, base_url, depth)


def page_markdown(page_html, base_url=''):
    """(title, Markdown body) of a built page: its <article class="content">, as Markdown."""
    doc = LH.fromstring(page_html)
    art = doc.find('.//article')
    title = (doc.findtext('.//title') or '').strip()
    if art is None:
        return title, ''
    h1 = art.find('.//h1')
    if h1 is not None and h1.text_content().strip():
        title = re.sub(r'\s+', ' ', _inline(h1, '')).strip()
    body = '\n\n'.join(b for b in _blocks(art, base_url) if b.strip())
    return title, re.sub(r'\n{3,}', '\n\n', body).strip() + '\n'

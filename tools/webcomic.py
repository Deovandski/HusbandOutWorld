"""The webcomic: a vertical-scroll reader, the way Webtoons shows a comic.

Source pages (the artists' tall PNG strips) live, unchanged, in
    Legacy/Behind The Scenes/Webcomic/<Vol N>/Prologue/*.png
    Legacy/Behind The Scenes/Webcomic/<Vol N>/Chapter N/Sub M/*.png
Every folder of pages becomes one episode, in story order. Drop a new folder in and the next build picks it up.

For the web, each strip is resized to WIDTH px and cut into slices of about SLICE px tall (a 30,000 px strip
is too tall for one web image, and slices let the browser load the episode as you scroll). The slices are
stacked with no gaps, so on screen the episode reads as one continuous strip.

Called from tools/build.py: webcomic.build(builder, build_module).
"""
import hashlib, json, os, re, shutil, sys
from concurrent.futures import ProcessPoolExecutor

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
WIDTH = 1080          # px; sharp on phones and at the reader's 800 px column on desktop
SLICE = 1440          # px tall per slice
MIN_TAIL = 240        # a last slice shorter than this joins the one before it
QUALITY = 82
VERSION = 'wc1'       # bump to re-make every slice


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def slice_plan(w, h):
    """(top, bottom) rows of each slice, in the source strip's pixels."""
    scale = WIDTH / w
    out_h = round(h * scale)
    cuts = list(range(0, out_h, SLICE)) + [out_h]
    if len(cuts) > 2 and cuts[-1] - cuts[-2] < MIN_TAIL:
        del cuts[-2]
    return [(round(a / scale), round(b / scale), round(b - a)) for a, b in zip(cuts, cuts[1:])]


def make_slices(job):
    """Resize one strip and write its slices. Runs in a worker process."""
    src, dests = job
    try:
        im = Image.open(src)
        if im.mode != 'RGB':
            bg = Image.new('RGB', im.size, (255, 255, 255))
            bg.paste(im, mask=im.convert('RGBA').getchannel('A'))
            im = bg
        w, h = im.size
        for (top, bottom, out_h), dst in zip(slice_plan(w, h), dests):
            part = im.crop((0, top, w, bottom)).resize((WIDTH, out_h), Image.LANCZOS)
            part.save(dst, 'WEBP', quality=QUALITY, method=4)
    except Exception as ex:  # keep the build going; the page just shows a gap
        print('webcomic slice failed', src, ex, file=sys.stderr)


def discover(root):
    """Episodes in story order: [{vol, kind, chapter, sub, dir, files}]"""
    eps = []
    if not os.path.isdir(root):
        return eps
    for vol in sorted(os.listdir(root), key=natural):
        vdir = os.path.join(root, vol)
        m = re.match(r'vol\s*(\d+)', vol, re.I)
        if not (m and os.path.isdir(vdir)):
            continue
        vn = int(m.group(1))
        for d, _, fs in os.walk(vdir):
            pngs = sorted((f for f in fs if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))), key=natural)
            if not pngs:
                continue
            relp = os.path.relpath(d, vdir).replace(os.sep, '/')
            if re.match(r'prologue$', relp, re.I):
                order, kind, ch, sub = (0, 0), 'prologue', 0, 0
            elif re.match(r'epilogue$', relp, re.I):
                order, kind, ch, sub = (999, 0), 'epilogue', 0, 0
            else:
                cm = re.match(r'chapter\s*(\d+)(?:/sub\s*(\d+))?$', relp, re.I)
                if not cm:
                    print(f'warning: webcomic folder not understood, skipped: {vol}/{relp}', file=sys.stderr)
                    continue
                ch, sub = int(cm.group(1)), int(cm.group(2) or 1)
                order, kind = (ch, sub), 'chapter'
            eps.append({'vol': vn, 'kind': kind, 'chapter': ch, 'sub': sub, 'order': (vn,) + order,
                        'dir': d, 'files': [os.path.join(d, f) for f in pngs]})
    eps.sort(key=lambda e: e['order'])
    return eps


def build(b, m):
    """Add the webcomic landing page and one reader page per episode to builder b (m is tools/build.py)."""
    cfg = m.CFG.get('webcomic', {})
    root = os.path.join(m.BTS, cfg.get('source', 'Webcomic'))
    eps = discover(root)
    esc = m.esc

    # chapter titles come from the novel, so "Chapter 1" reads "Chapter I - Unexpected Aftermath"
    novel_titles = {}
    for vi, v in enumerate(m.CFG['volumes'], 1):
        for ch in b.parse_volume(v)[4]:
            mm = re.match(r'chapter\s+([ivxlc]+)\b', ch['title'], re.I)
            if mm:
                novel_titles[(vi, m.roman(mm.group(1)))] = ch['title']

    # ---- slices
    out_root = os.path.join(b.out, 'media', 'webcomic')
    jobs = []
    for n, e in enumerate(eps, 1):
        e['n'] = n
        if e['kind'] == 'chapter':
            e['slug'] = f'vol-{e["vol"]}/chapter-{e["chapter"]}-{e["sub"]}'
            chap = novel_titles.get((e['vol'], e['chapter']), f'Chapter {e["chapter"]}')
            e['title'] = f'{chap} · Subchapter {e["sub"]}'
            e['short'] = f'Chapter {roman_numeral(e["chapter"])} · {e["sub"]}'
        else:
            e['slug'] = f'vol-{e["vol"]}/{e["kind"]}'
            e['title'] = e['short'] = e['kind'].capitalize()
        e['url'] = f'/webcomic/{e["slug"]}/'
        e['slices'] = []
        odir = os.path.join(out_root, e['slug'].replace('/', '-'))
        os.makedirs(odir, exist_ok=True)
        k = 0
        for src in e['files']:
            with Image.open(src) as im:  # reads only the header
                w, h = im.size
            plan = slice_plan(w, h)
            key = hashlib.sha1(f'{VERSION}:{WIDTH}:{SLICE}:{m.rel(src)}:{os.path.getsize(src)}'.encode()).hexdigest()[:12]
            cached = [os.path.join(b.media.cache, f'wc-{key}-{i}.webp') for i in range(len(plan))]
            if b.media.enabled and not all(os.path.exists(c) for c in cached):
                jobs.append((src, cached))
            for (top, bottom, out_h), c in zip(plan, cached):
                k += 1
                name = f'{k:03d}.webp'
                e['slices'].append({'url': f'/media/webcomic/{e["slug"].replace("/", "-")}/{name}', 'h': out_h,
                                    'cache': c, 'out': os.path.join(odir, name)})
        e['height'] = sum(s['h'] for s in e['slices'])
    if jobs:
        print(f'webcomic: slicing {len(jobs)} pages', flush=True)
        with ProcessPoolExecutor() as ex:
            list(ex.map(make_slices, jobs))
    for e in eps:
        for s in e['slices']:
            if os.path.exists(s['cache']):
                shutil.copyfile(s['cache'], s['out'])
        # episode thumbnail: the busiest 3:2 window near the top of the episode (many strips open on blank white)
        e['thumb'] = None
        if e['slices'] and os.path.exists(e['slices'][0]['cache']):
            t = os.path.join(out_root, e['slug'].replace('/', '-'), 'thumb.webp')
            pick_thumb([s['cache'] for s in e['slices'][:4] if os.path.exists(s['cache'])]).save(t, 'WEBP', quality=78)
            e['thumb'] = f'/media/webcomic/{e["slug"].replace("/", "-")}/thumb.webp'

    # ---- what the old blog page said (tagline, cover, Webtoons link, supporters)
    blog = cfg.get('blog_page', 'graphiclight-novels.md')
    meta, intro, secs = m.parse_public(blog)
    tagline, cover, supporters = '', None, []
    for s_ in [intro] + secs:
        if not tagline and s_['heading'] and s_['heading'] != 'Webcomic':
            tagline = s_['heading']
        img = m.first_image(s_['md'])
        if img and not cover:
            cover = b.r.resolve(img, {'base': m.PUB})
        if 'support' in s_['heading'].lower():
            supporters = [ln.strip() for ln in s_['md'].split('\n') if ln.strip()]
    webtoon = m.CFG.get('webtoon_url', '')
    raw_link = m.CFG['repo_url'] + '/tree/main/' + m.quote(m.rel(root))
    sources = [m.rel(os.path.join(m.PUB, blog))]

    def ep_card(e, label=''):
        img = f'<img src="{e["thumb"]}" alt="" loading="lazy" width="360" height="240">' if e.get('thumb') else '<span class="ep-noimg"></span>'
        return (f'<a class="ep-card" href="{e["url"]}">{img}<span class="ep-text"><span class="ep-n">{label or "Episode " + str(e["n"])}</span>'
                f'<span class="ep-title">{esc(e["title"])}</span><span class="muted">Vol {e["vol"]}</span></span></a>')

    # ---- landing page
    land = m.Page('/webcomic/', 'Webcomic', 'Webcomic')
    land.sources = sources + [m.rel(root)]
    land.extra_css = ['/css/webcomic.css']
    land.extra_js = ['/js/webcomic.js']
    first = eps[0] if eps else None
    cov = (f'<img class="wc-cover" src="{cover["url"]}" alt="{esc(m.ALT.get(cover["src"], {}).get("alt") or "Webcomic cover")}" width="500" height="750">'
           if cover else '')
    parts = [f'<section class="wc-hero">{cov}<div class="wc-hero-text"><p class="eyebrow">Webcomic · Arc #1 - Dubious Contract</p>'
             f'<h1>A Husband Out of This World</h1><p class="wc-tagline">{esc(tagline)}</p>'
             '<div class="hero-actions">'
             + (f'<a class="btn primary" href="{first["url"]}" data-wc-start>Start reading</a>'
                '<a class="btn" href="#" data-wc-continue hidden>Continue</a>' if first else '<p class="muted">The first episode is on its way.</p>')
             + (f'<a class="btn" href="{esc(webtoon)}" rel="noopener">Read on Webtoons</a>' if webtoon else '')
             + '</div><p class="muted wc-howto">Scroll down to read, like on Webtoons. On a phone, tap the comic to hide or show the menus.</p></div></section>']
    if eps:
        parts.append(f'<h2>Episodes</h2><div class="ep-list">' + ''.join(ep_card(e) for e in eps) + '</div>')
    if supporters:
        parts.append('<section class="wc-thanks"><h2>Awesome people supporting the Webcomic!</h2><ul class="supporters">'
                     + ''.join(f'<li>{esc(x)}</li>' for x in supporters) + '</ul></section>')
    parts.append(f'<p class="src">The original pages, full size: <a href="{raw_link}">{esc(m.rel(root))}</a>. '
                 f'From the original blog page: <a href="{esc(meta.get("original_url", ""))}">{esc(meta.get("original_url", ""))}</a></p>')
    land.html = '\n'.join(parts)
    land.md_public = (f'# Webcomic\n\n{tagline}\n\n' + (f'Read it on Webtoons: {webtoon}\n\n' if webtoon else '')
                      + '\n'.join(f'- [Episode {e["n"]}: {e["title"]}]({e["url"]}index.md)' for e in eps)
                      + ('\n\n## Awesome people supporting the Webcomic!\n\n' + ', '.join(supporters) if supporters else ''))
    land.desc = (tagline + ' Read the #HusbandOutWorld webcomic free, scrolling like on Webtoons.')[:160]
    land.search.append({'t': 'Webcomic', 'u': '/webcomic/', 's': 'Webcomic', 'x': tagline, 'b': False})
    land.jsonld = {'@context': 'https://schema.org', '@type': 'ComicSeries', 'name': m.CFG['title'] + ' (webcomic)',
                   'author': {'@type': 'Person', 'name': m.CFG['author']}, 'url': m.CFG['base_url'] + '/webcomic/',
                   'hasPart': [{'@type': 'ComicIssue', 'name': e['title'], 'issueNumber': e['n'], 'url': m.CFG['base_url'] + e['url']} for e in eps]}
    b.add(land)

    # ---- one reader page per episode
    for i, e in enumerate(eps):
        prev_e = eps[i - 1] if i else None
        next_e = eps[i + 1] if i + 1 < len(eps) else None
        p = m.Page(e['url'], f'{e["title"]} · Webcomic', 'Webcomic')
        p.sources = [m.rel(e['dir'])]
        p.extra_css = ['/css/webcomic.css']
        p.extra_js = ['/js/webcomic.js']
        p.layout = 'reader'
        nav = ('<nav class="wc-bar keep-latin" aria-label="Episode">'
               '<a class="wc-list" href="/webcomic/" aria-label="All episodes" title="All episodes">'
               '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></a>'
               f'<span class="wc-title"><span class="wc-ep">Ep. {e["n"]}</span> {esc(e["short"])}</span>'
               + (f'<a class="wc-prev" href="{prev_e["url"]}" rel="prev" aria-label="Previous episode" title="Previous episode (←)">‹</a>' if prev_e else '<span class="wc-prev off" aria-hidden="true">‹</span>')
               + (f'<a class="wc-next" href="{next_e["url"]}" rel="next" aria-label="Next episode" title="Next episode (→)">›</a>' if next_e else '<span class="wc-next off" aria-hidden="true">›</span>')
               + '<span class="wc-progress" aria-hidden="true"><span></span></span></nav>')
        imgs = []
        for k, s in enumerate(e['slices']):
            lazy = 'fetchpriority="high"' if k < 2 else 'loading="lazy"'
            alt = f'{e["title"]}, part {k + 1} of {len(e["slices"])}' if k == 0 else ''
            imgs.append(f'<img id="s-{k + 1}" src="{s["url"]}" width="{WIDTH}" height="{s["h"]}" alt="{esc(alt)}" {lazy} decoding="async">')
        end = ['<section class="wc-end keep-latin">']
        if next_e:
            end.append(f'<p class="wc-end-label">Next episode</p>{ep_card(next_e, "Episode " + str(next_e["n"]))}')
        else:
            end.append('<p class="wc-end-label">You\'re all caught up!</p><p>More episodes are on their way.'
                       + (f' Follow the series on <a href="{esc(webtoon)}" rel="noopener">Webtoons</a> to hear first.' if webtoon else '') + '</p>'
                       '<p>Want to know what happens next? <a href="/novel/vol-1/">The light novel</a> tells the whole of Arc #1.</p>')
        end.append(f'<p class="wc-end-links"><a href="/webcomic/">All episodes</a>'
                   + (f' · <a href="{esc(webtoon)}" rel="noopener">Like it on Webtoons</a>' if webtoon else '')
                   + f' · <a href="{m.CFG["repo_url"]}/tree/main/{m.quote(m.rel(e["dir"]))}">Original pages</a></p>')
        end.append(m.amazon_note() + '</section>')
        p.html = (nav + f'<h1 class="sr-only">{esc(e["title"])}</h1>'
                  f'<div class="wc-strip" data-episode="{esc(e["slug"])}" data-next="{next_e["url"] if next_e else ""}" data-prev="{prev_e["url"] if prev_e else ""}">'
                  + ''.join(imgs) + '</div>' + ''.join(end))
        p.md_public = (f'# {e["title"]}\n\n*Webcomic, episode {e["n"]} (Vol {e["vol"]}).* A comic: the story is told in pictures.\n\n'
                       + '\n'.join(f'![part {k + 1}]({s["url"]})' for k, s in enumerate(e['slices'])))
        p.desc = f'Read {e["title"]}, episode {e["n"]} of the #HusbandOutWorld webcomic, free and scrolling like on Webtoons.'
        p.search.append({'t': f'{e["title"]} (webcomic)', 'u': e['url'], 's': 'Webcomic', 'x': p.desc, 'b': False})
        p.jsonld = {'@context': 'https://schema.org', '@type': 'ComicIssue', 'name': e['title'], 'issueNumber': e['n'],
                    'isPartOf': {'@type': 'ComicSeries', 'name': m.CFG['title'] + ' (webcomic)', 'url': m.CFG['base_url'] + '/webcomic/'},
                    'author': {'@type': 'Person', 'name': m.CFG['author']}, 'url': m.CFG['base_url'] + e['url']}
        b.add(p)
    return eps


def pick_thumb(paths):
    """A 360x240 thumbnail cut from the window (of the first few slices) with the most going on in it."""
    from PIL import ImageStat
    win_h = WIDTH * 2 // 3
    best = None
    for path in paths:
        with Image.open(path) as im:
            im.load()
            for top in range(0, max(1, im.size[1] - win_h + 1), 180):
                box = (0, top, WIDTH, min(im.size[1], top + win_h))
                g = im.crop(box).convert('L').resize((90, 60))
                # count busy cells in a 6x4 grid, so a window that is half blank page loses to one full of art
                cells = [ImageStat.Stat(g.crop((x, y, x + 15, y + 15))).stddev[0] for x in range(0, 90, 15) for y in range(0, 60, 15)]
                score = (sum(c > 12 for c in cells), sum(cells))
                if best is None or score > best[0]:
                    best = (score, im.crop(box).copy())
    return best[1].resize((360, 240), Image.LANCZOS)


def roman_numeral(n):
    out = ''
    for v, s in ((100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v:
            out += s; n -= v
    return out

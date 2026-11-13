"""The Blog page: the old blog's final post, with its photos in a square grid (like the Cat Dad tab on
deovandski.github.io/Deovandski/#cat). Click a photo to see it large; ‹ and › move through the grid.

Photos come from two places: the ones in the post itself (Legacy/Public/images) and every picture dropped into
Legacy/Public/Blog Photos/. The grid runs oldest to newest by the day each photo was taken, read from (first match):
its "date" in content/blog-photos.json, the photo's own camera data, or a date in its file name (PXL_20240628_...,
IMG-20240628-..., 2024-06-28 ...). Descriptions come from content/blog-photos.json, which the author fills in.

On the website a photo is named after that day (/media/blog/2024-06-28.webp; a second photo from the same day gets
-2). A photo with no date keeps its own name (undated-<name>.webp). The originals are never renamed.

Called from tools/build.py: blog.build(builder, build_module).
"""
import hashlib, json, os, re, shutil, sys
from datetime import date as Date

from PIL import Image, ImageOps

THUMB = 480       # px, square grid tile
FULL = 1800       # px, longest side of the large view
QUALITY = 82
VERSION = 'bp1'   # bump to re-make every photo
MANIFEST = 'blog-photos.json'
DROP = 'Blog Photos'     # folder in Legacy/Public for new photos
PICS = ('.jpg', '.jpeg', '.png', '.webp')   # iPhone .heic: export as JPG first


def pretty(d):
    """'2024-06-28' -> 'June 28, 2024' ('' if not a date)."""
    try:
        y, mo, dd = (int(x) for x in d.split('-'))
        return Date(y, mo, dd).strftime('%B %-d, %Y')
    except Exception:
        return ''


def taken(path):
    """The day a photo was taken, from its camera data or its file name ('' if neither says)."""
    try:
        ex = Image.open(path).getexif()
        d = (ex.get_ifd(0x8769).get(36867) or ex.get(306) or '') if ex else ''
        if re.match(r'\d{4}:\d{2}:\d{2}', d) and not d.startswith('0000'):
            return d[:10].replace(':', '-')
    except Exception:
        pass
    mm = re.search(r'(?<!\d)(20\d{2})[-_.]?([01]\d)[-_.]?([0-3]\d)(?!\d)', os.path.basename(path))
    return f'{mm.group(1)}-{mm.group(2)}-{mm.group(3)}' if mm and pretty(f'{mm.group(1)}-{mm.group(2)}-{mm.group(3)}') else ''


def load_manifest(m, files):
    """Every photo (files are paths relative to Legacy/Public), oldest first, with the author's dates and
    descriptions from content/blog-photos.json. A photo missing from that file still shows, dated by itself."""
    path = os.path.join(m.CONTENT, MANIFEST)
    data = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'photos': []}
    known = {p.get('file'): p for p in data.get('photos', [])}
    for f in known:
        if f not in files:
            print(f'warning: {MANIFEST} lists {f!r}, which is not in the blog post or {DROP}/', file=sys.stderr)
    photos = []
    for i, f in enumerate(files):
        p = dict(known.get(f, {'file': f}))
        p.setdefault('description', '')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', (p.get('date') or '').strip()):
            p['date'] = taken(os.path.join(m.PUB, f))
        p['_i'] = i
        photos.append(p)
    photos.sort(key=lambda p: (p['date'] == '', p['date'], p['_i']))
    return photos


def web_names(photos):
    """2024-06-28, 2024-06-28-2, ... for dated photos; undated-<original name> for the rest."""
    seen = {}
    for p in photos:
        d = (p.get('date') or '').strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            seen[d] = seen.get(d, 0) + 1
            p['name'] = d if seen[d] == 1 else f'{d}-{seen[d]}'
            continue
        else:
            base = 'undated-' + (re.sub(r'[^a-z0-9]+', '-', os.path.splitext(os.path.basename(p['file']))[0].lower()).strip('-') or 'photo')
            seen[base] = seen.get(base, 0) + 1
            p['name'] = base if seen[base] == 1 else f'{base}-{seen[base]}'


def make(src, full_out, thumb_out):
    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode not in ('RGB', 'L'):
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.convert('RGBA').getchannel('A'))
        im = bg
    im = im.convert('RGB')
    big = im.copy()
    big.thumbnail((FULL, FULL), Image.LANCZOS)
    big.save(full_out, 'WEBP', quality=QUALITY, method=4)
    ImageOps.fit(im, (THUMB, THUMB), Image.LANCZOS, centering=(0.5, 0.4)).save(thumb_out, 'WEBP', quality=QUALITY, method=4)


def build(b, m):
    cfg = m.CFG.get('blog', {})
    name = cfg.get('public', 'blog.md')
    url = cfg.get('url', '/blog/')
    esc = m.esc
    meta, intro, secs = m.parse_public(name)
    md = '\n\n'.join([intro['md']] + [(f'## {s["heading"]}\n\n' if s['heading'] else '') + s['md'] for s in secs])

    # every local picture in the post, in order; the text keeps none of them (they all go in the grid)
    files = []
    for f in re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', md):
        if not f.startswith('http') and f not in files and os.path.exists(os.path.join(m.PUB, f)):
            files.append(f)
    drop = os.path.join(m.PUB, DROP)
    if os.path.isdir(drop):
        for f in sorted(os.listdir(drop)):
            if f.lower().endswith(PICS) and not f.startswith('.'):
                files.append(f'{DROP}/{f}')
    text_md = re.sub(r'!\[[^\]]*\]\([^)]*\)\s*', '', md).strip()
    photos = load_manifest(m, files)
    web_names(photos)

    # ---- photos: one large copy and one square tile each, named by date
    out_dir = os.path.join(b.out, 'media', 'blog')
    os.makedirs(out_dir, exist_ok=True)
    for p in photos:
        src = os.path.join(m.PUB, p['file'])
        p['full'] = f'/media/blog/{p["name"]}.webp'
        p['thumb'] = f'/media/blog/{p["name"]}-t.webp'
        p['src'] = m.rel(src)
        if not (b.media.enabled and os.path.exists(src)):
            continue
        key = hashlib.sha1(f'{VERSION}:{p["src"]}:{os.path.getsize(src)}'.encode()).hexdigest()[:12]
        cf, ct = (os.path.join(b.media.cache, f'blog-{key}{s}.webp') for s in ('', '-t'))
        if not (os.path.exists(cf) and os.path.exists(ct)):
            os.makedirs(b.media.cache, exist_ok=True)
            try:
                make(src, cf, ct)
            except Exception as ex:  # one unreadable file shouldn't stop the build
                print(f'warning: blog photo {p["src"]} could not be read, skipped: {ex}', file=sys.stderr)
                p['broken'] = True
                continue
        shutil.copyfile(cf, os.path.join(out_dir, p['name'] + '.webp'))
        shutil.copyfile(ct, os.path.join(out_dir, p['name'] + '-t.webp'))

    # ---- page
    page = m.Page(url, 'Blog', 'Blog')
    page.sources = [m.rel(os.path.join(m.PUB, name)), 'content/' + MANIFEST]
    tiles = []
    photos = [p for p in photos if not p.get('broken')]
    for i, p in enumerate(photos, 1):
        when = pretty(p.get('date', ''))
        desc = (p.get('description') or '').strip()
        alt = desc or f'Photo {i} from the final blog post' + (f', {when}' if when else '')
        caption = ' · '.join(x for x in (when, desc) if x)
        # one card per photo: its caption (date, then the author's description) above it, like the Cat Dad tab
        tiles.append(f'<li><p class="photo-caption" aria-hidden="true" title="{esc(caption)}">{esc(caption or "Undated")}</p>'
                     f'<a class="img-link" href="{p["full"]}" data-full="{p["full"]}" data-gallery="blog" data-caption="{esc(caption)}">'
                     f'<img src="{p["thumb"]}" alt="{esc(alt)}" width="{THUMB}" height="{THUMB}" loading="lazy" decoding="async"></a></li>')
    page.html = ('<h1>Blog</h1>' + b.r.render(text_md, base=m.PUB, origin=name)
                 + (f'<ul class="photo-grid" aria-label="Photos from the final blog post">{"".join(tiles)}</ul>' if tiles else '')
                 + f'<p class="src">From the original blog page: <a href="{esc(meta.get("original_url", ""))}">{esc(meta.get("original_url", ""))}</a> '
                   f'(archived in <a href="{m.gh_link(os.path.join(m.PUB, name))}">{esc(m.rel(os.path.join(m.PUB, name)))}</a>)</p>')
    page.md_public = ('# Blog\n\n' + text_md + '\n\n## Photos\n\n'
                      + '\n'.join(f'- [{pretty(p.get("date", "")) or "Undated photo"}]({p["full"]})'
                                  + (f': {p["description"].strip()}' if (p.get('description') or '').strip() else '') for p in photos))
    page.desc = m.first_sentences(text_md, 160)
    page.search.append({'t': 'Blog', 'u': url, 's': 'Blog', 'x': m.first_sentences(text_md, 300), 'b': False})
    b.add(page)
    return photos

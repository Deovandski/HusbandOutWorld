"""The Blog page: the old blog's final post, with its photos in a square grid (like the Cat Dad tab on
deovandski.github.io/Deovandski/#cat). Click a photo to see it large; ‹ and › move through the grid.

Each photo's date and description come from content/blog-photos.json, which the author fills in. On the website a
photo is named after the day it was taken (/media/blog/2024-06-28.webp; a second photo from the same day gets -2).
A photo with no date yet keeps its original number (undated-097.webp). The originals in Legacy/Public/images are
never renamed.

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


def pretty(d):
    """'2024-06-28' -> 'June 28, 2024' ('' if not a date)."""
    try:
        y, mo, dd = (int(x) for x in d.split('-'))
        return Date(y, mo, dd).strftime('%B %-d, %Y')
    except Exception:
        return ''


def load_manifest(m, files):
    """The photo list in grid order, with the author's dates and descriptions. Photos in the post but missing
    from the list are added at the end (with a warning), so a new photo never disappears."""
    path = os.path.join(m.CONTENT, MANIFEST)
    data = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'photos': []}
    photos = [dict(p) for p in data.get('photos', []) if p.get('file') in files]
    for p in data.get('photos', []):
        if p.get('file') not in files:
            print(f'warning: {MANIFEST} lists {p.get("file")!r}, which is not in the blog post', file=sys.stderr)
    listed = {p['file'] for p in photos}
    for f in files:
        if f not in listed:
            print(f'warning: blog photo {f!r} is not in content/{MANIFEST} yet (no date or description)', file=sys.stderr)
            photos.append({'file': f, 'date': '', 'description': ''})
    return photos


def web_names(photos):
    """2024-06-28, 2024-06-28-2, ... for dated photos; undated-<original name> for the rest."""
    seen = {}
    for p in photos:
        d = (p.get('date') or '').strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            seen[d] = seen.get(d, 0) + 1
            p['name'] = d if seen[d] == 1 else f'{d}-{seen[d]}'
        else:
            p['name'] = 'undated-' + os.path.splitext(os.path.basename(p['file']))[0]


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
        if not f.startswith('http') and f not in files:
            files.append(f)
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
            make(src, cf, ct)
        shutil.copyfile(cf, os.path.join(out_dir, p['name'] + '.webp'))
        shutil.copyfile(ct, os.path.join(out_dir, p['name'] + '-t.webp'))

    # ---- page
    page = m.Page(url, 'Blog', 'Blog')
    page.sources = [m.rel(os.path.join(m.PUB, name)), 'content/' + MANIFEST]
    tiles = []
    for i, p in enumerate(photos, 1):
        when = pretty(p.get('date', ''))
        desc = (p.get('description') or '').strip()
        alt = desc or f'Photo {i} from the final blog post' + (f', {when}' if when else '')
        caption = ' · '.join(x for x in (when, desc) if x)
        tiles.append(f'<li><a class="img-link" href="{p["full"]}" data-full="{p["full"]}" data-gallery="blog" data-caption="{esc(caption)}">'
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

"""Convert the Blogger (Google Takeout) export into Legacy/Public.

One Markdown file per live blog page, converted word for word from the page HTML
(no edits). Images point to local copies when the downloaded originals are
available (pass --images DIR with files named 001, 002, ... in the order of
blog_image_urls.txt); otherwise to the best local match or the original URL.

Usage: python tools/import_blogger.py TAKEOUT_DIR OUT_DIR [--images DIR] [--map MAP.json]
"""
import argparse, json, os, re, shutil, urllib.parse, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from markdownify import markdownify

NS = {'a': 'http://www.w3.org/2005/Atom', 'b': 'http://schemas.google.com/blogger/2018'}

def base_url(u):
    return re.sub(r'=[whs][0-9][^/]*$', '', u)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('takeout'); ap.add_argument('out')
    ap.add_argument('--images'); ap.add_argument('--map'); ap.add_argument('--urls')
    ap.add_argument('--dedupe', help='folder of originals: blog images that are the same picture link there instead of being copied')
    a = ap.parse_args()
    feed = os.path.join(a.takeout, 'Blogs', '#HusbandOutWorld Series', 'feed.atom')
    root = ET.parse(feed).getroot()
    os.makedirs(a.out, exist_ok=True)
    urls = [l.strip() for l in open(a.urls)] if a.urls else []
    local = {}
    if a.images and urls:
        os.makedirs(os.path.join(a.out, 'images'), exist_ok=True)
        files = {os.path.splitext(f)[0]: f for f in os.listdir(a.images)}
        originals = index_originals(a.dedupe) if a.dedupe else []
        for i, u in enumerate(urls, 1):
            f = files.get('%03d' % i)
            if f:
                src = os.path.join(a.images, f)
                same = find_same(src, originals)
                if same:
                    local[u] = os.path.relpath(same, a.out).replace(os.sep, '/')
                    continue
                ext = os.path.splitext(f)[1] or sniff(src)
                dst = '%03d%s' % (i, ext)
                shutil.copyfile(src, os.path.join(a.out, 'images', dst))
                local[u] = 'images/' + dst
    guess = json.load(open(a.map)) if a.map else {}
    index = []
    for e in root.findall('a:entry', NS):
        if e.findtext('b:type', namespaces=NS) != 'PAGE' or e.findtext('b:status', namespaces=NS) != 'LIVE':
            continue
        title = e.findtext('a:title', namespaces=NS)
        fn = e.findtext('b:filename', namespaces=NS)
        slug = os.path.splitext(os.path.basename(fn))[0]
        html = e.findtext('a:content', namespaces=NS) or ''
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            u = base_url(img['src'])
            if u in local:
                img['src'] = urllib.parse.quote(local[u])
            elif u in guess and guess[u]:
                img['src'] = urllib.parse.quote(guess[u])
            else:
                img['src'] = u
            par = img.parent
            if par.name == 'a' and par.get('href', '').startswith('https://blogger.googleusercontent.com'):
                par.unwrap()
        md = markdownify(str(soup), heading_style='ATX', bullets='*')
        md = re.sub(r'\n{3,}', '\n\n', md).strip() + '\n'
        front = ('---\n'
                 f'title: "{title}"\n'
                 f'original_url: https://husbandoutworld.blogspot.com{fn}\n'
                 f'published: {e.findtext("a:published", namespaces=NS)}\n'
                 f'updated: {e.findtext("a:updated", namespaces=NS)}\n'
                 'source: Blogger export (Google Takeout), converted from HTML to Markdown without edits\n'
                 '---\n\n')
        open(os.path.join(a.out, slug + '.md'), 'w').write(front + f'# {title}\n\n' + md)
        index.append((title, slug))
    index.sort(key=lambda t: t[0].lower())
    print(len(index), 'pages')
    return index

def dhash(p, n=16):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(p)
    im.draft('L', (256, 256))
    im = im.convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    g = bg.convert('L').resize((n + 1, n))
    px = list(g.getdata())
    bits = 0
    for y in range(n):
        for x in range(n):
            bits = (bits << 1) | (px[y * (n + 1) + x] > px[y * (n + 1) + x + 1])
    return bits, im.size

def index_originals(folder):
    out = []
    for d, _, fs in os.walk(folder):
        for f in fs:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                p = os.path.join(d, f)
                try:
                    h, size = dhash(p)
                    out.append((p, h, size))
                except Exception:
                    pass
    return out

def find_same(src, originals):
    """An original that is the same picture (near-identical hash, same aspect ratio, at least as large)."""
    try:
        h, (w, ht) = dhash(src)
    except Exception:
        return None
    best = None
    for p, oh, (ow, oht) in originals:
        d = bin(h ^ oh).count('1')
        if d <= 6 and abs(w / ht - ow / oht) < 0.02 and ow >= w * 0.98 and (best is None or d < best[0]):
            best = (d, p)
    return best[1] if best else None

def sniff(p):
    h = open(p, 'rb').read(12)
    if h.startswith(b'\x89PNG'): return '.png'
    if h[:3] == b'\xff\xd8\xff': return '.jpg'
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP': return '.webp'
    if h[:4] == b'GIF8': return '.gif'
    return '.bin'

if __name__ == '__main__':
    main()

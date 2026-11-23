"""Check a built site: every picture shows, and how big the site is.

Usage:
    python tools/check_site.py _site [--base-path /HusbandOutWorld] [--summary FILE]

- Reads every .html page in the folder and checks that each local picture it
  uses (<img src/srcset>, <source>, <video poster>, data-full, and links
  straight to an image file) is in the folder. Missing pictures fail the check.
- Other local links that lead nowhere are counted and listed, but don't fail it.
- Prints the site's size by kind of file and by top folder, against GitHub
  Pages' 1 GB limit. --summary appends the same report as Markdown (in the
  workflow this is $GITHUB_STEP_SUMMARY, shown on the run's page).

Exit code 1 when a picture is missing or the site is over 1 GB.
"""
import argparse
import collections
import html.parser
import os
import sys
from urllib.parse import unquote, urlsplit

PAGES_LIMIT = 1024 ** 3
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.avif')


class Refs(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pictures, self.links = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('img', 'source'):
            for k in ('src', 'data-full'):
                if a.get(k):
                    self.pictures.append(a[k])
            for k in ('srcset', 'data-srcset'):
                for part in (a.get(k) or '').split(','):
                    if part.strip():
                        self.pictures.append(part.split()[0])
        if tag == 'video' and a.get('poster'):
            self.pictures.append(a['poster'])
        if a.get('data-full') and tag not in ('img', 'source'):
            self.pictures.append(a['data-full'])
        for k in ('href', 'src'):
            v = a.get(k)
            if v and tag not in ('img', 'source'):
                path = urlsplit(v).path.lower()
                (self.pictures if path.endswith(IMAGE_EXTS) else self.links).append(v)


def local_target(root, page, url, base):
    """The file a link points to inside the site, or None if it isn't local."""
    u = urlsplit(url)
    if u.scheme or u.netloc or not u.path:
        return None
    path = unquote(u.path)
    if path.startswith('/'):
        if base and not (path == base or path.startswith(base + '/')):
            return os.path.join(root, '__outside_base__' + path)
        path = path[len(base):] if base else path
        full = os.path.join(root, path.lstrip('/'))
    else:
        full = os.path.join(os.path.dirname(page), path)
    full = os.path.normpath(full)
    if os.path.isdir(full) or url.split('?')[0].split('#')[0].endswith('/'):
        full = os.path.join(full, 'index.html')
    return full


def human(n):
    return f'{n / 1024 ** 2:,.1f} MB' if n < 1024 ** 3 else f'{n / 1024 ** 3:,.2f} GB'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('site')
    ap.add_argument('--base-path', default='')
    ap.add_argument('--summary')
    args = ap.parse_args()
    root, base = os.path.abspath(args.site), args.base_path.rstrip('/')

    by_ext, by_dir = collections.Counter(), collections.Counter()
    count_ext = collections.Counter()
    pages, total = [], 0
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            s = os.path.getsize(p)
            total += s
            ext = os.path.splitext(f)[1].lower() or '(none)'
            by_ext[ext] += s
            count_ext[ext] += 1
            rel = os.path.relpath(p, root)
            by_dir[rel.split(os.sep)[0] if os.sep in rel else '(top)'] += s
            if f.endswith('.html'):
                pages.append(p)

    missing, dead, checked = collections.defaultdict(set), collections.defaultdict(set), 0
    for page in pages:
        r = Refs()
        with open(page, encoding='utf-8') as fh:
            r.feed(fh.read())
        rel_page = os.path.relpath(page, root)
        for url in r.pictures:
            t = local_target(root, page, url, base)
            if t:
                checked += 1
                if not os.path.isfile(t):
                    missing[url].add(rel_page)
        for url in r.links:
            t = local_target(root, page, url, base)
            if t and not os.path.isfile(t):
                dead[url].add(rel_page)

    lines = ['## Built site', '',
             f'**{human(total)}** in {sum(count_ext.values()):,} files '
             f'({total / PAGES_LIMIT:.0%} of the 1 GB GitHub Pages limit).', '',
             '| Kind | Files | Size |', '|---|---:|---:|']
    for ext, s in by_ext.most_common(8):
        lines.append(f'| {ext} | {count_ext[ext]:,} | {human(s)} |')
    lines += ['', '| Folder | Size |', '|---|---:|']
    for d, s in by_dir.most_common(8):
        lines.append(f'| {d} | {human(s)} |')
    lines += ['', f'Pictures: {checked:,} checked on {len(pages):,} pages, '
              f'**{len(missing)} missing**. Other local links that lead nowhere: {len(dead)}.']
    for label, group in (('Missing picture', missing), ('Link that leads nowhere', dead)):
        for url in sorted(group)[:25]:
            where = sorted(group[url])
            lines.append(f'- {label}: `{url}` on {where[0]}'
                         + (f' and {len(where) - 1} more' if len(where) > 1 else ''))
    report = '\n'.join(lines) + '\n'
    print(report)
    if args.summary:
        with open(args.summary, 'a', encoding='utf-8') as fh:
            fh.write(report)
    return 1 if missing or total > PAGES_LIMIT else 0


if __name__ == '__main__':
    sys.exit(main())

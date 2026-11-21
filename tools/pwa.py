"""Installable app (PWA) for a static site built in Python: manifest, icons and service worker.

Reusable component. Adapted from Deovandski/Deovandski (src/pages/manifest.webmanifest.ts and
public/sw.js, PR #160); nothing in here knows about #HusbandOutWorld. Everything comes in as options.

Usage (after the site's pages are written):

    import pwa
    pwa.write(out_dir, base='/HusbandOutWorld',            # '' on a custom domain
              name='A Husband Out of This World', short_name='#HusbandOutWorld',
              description='...', theme_color='#101719', background_color='#101719',
              logo='path/to/logo.png',                      # square art, transparent edges are fine
              shortcuts=[{'name': 'Novel', 'url': '/novel/', 'image': 'path/to/art.png'}],
              homes=['/'],                                  # pages saved when the app installs
              cache_prefix='hoow', version='v1', save_visited_pages=True,
              extra_files=['/media/favicon.png'],                # more small files to keep offline
              skip_files=['/google0123abcd.html'])               # files the worker never touches

and put pwa.head_tags(theme_color) in every page's <head>. Its addresses start with "/", like the
rest of the page, so the site's own base-path rewrite applies to them; the registration script reads
the base path from <html data-base="...">.

Writes: manifest.webmanifest, sw.js (from site/sw.js), icons/icon-192.png, icons/icon-512.png,
icons/icon-maskable-512.png (extra margin for Android's circle crop), icons/apple-touch-icon.png and
icons/shortcut-<n>-96.png. The source images are only read, never changed.
"""
import json
import os

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SW_TEMPLATE = os.path.join(os.path.dirname(HERE), 'site', 'sw.js')


def head_tags(theme_color):
    """The <head> lines every page needs: manifest, colours, home-screen icon, worker registration."""
    return (
        '<link rel="manifest" href="/manifest.webmanifest">\n'
        f'<meta name="theme-color" content="{theme_color}">\n'
        '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">\n'
        "<script>if('serviceWorker' in navigator){addEventListener('load',function(){"
        "var b=document.documentElement.dataset.base||'';"
        "navigator.serviceWorker.register(b+'/sw.js',{scope:b+'/'}).catch(function(){});});}</script>"
    )


def _rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fit(img, size, scale, background=None):
    """img centred on a size x size canvas, taking `scale` of its width; transparent unless background."""
    canvas = Image.new('RGBA', (size, size), (*_rgb(background), 255) if background else (0, 0, 0, 0))
    art = img.copy()
    art.thumbnail((round(size * scale), round(size * scale)), Image.LANCZOS)
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return canvas if not background else canvas.convert('RGB')


def write(out, base='', name='', short_name='', description='', theme_color='#000000',
          background_color='#000000', logo=None, shortcuts=(), homes=('/',), cache_prefix='site',
          version='v1', save_visited_pages=True, lang='en', extra_files=(), skip_files=()):
    base = base.rstrip('/') + '/'
    icons_dir = os.path.join(out, 'icons')
    os.makedirs(icons_dir, exist_ok=True)
    extra = ['manifest.webmanifest']

    icons = []
    if logo and os.path.exists(logo):
        art = Image.open(logo).convert('RGBA')
        for size in (192, 512):
            _fit(art, size, 1.0).save(os.path.join(icons_dir, f'icon-{size}.png'))
            icons.append({'src': f'{base}icons/icon-{size}.png', 'sizes': f'{size}x{size}', 'type': 'image/png', 'purpose': 'any'})
        # Android crops "maskable" icons to a circle or squircle: keep the art inside the safe zone.
        _fit(art, 512, 0.72, background_color).save(os.path.join(icons_dir, 'icon-maskable-512.png'))
        icons.append({'src': f'{base}icons/icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'})
        # iOS fills transparency with black, so the touch icon gets the page colour behind it.
        _fit(art, 180, 0.86, background_color).save(os.path.join(icons_dir, 'apple-touch-icon.png'))
        extra += ['icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png']

    short = []
    for i, sc in enumerate(shortcuts, 1):
        entry = {'name': sc['name'], 'short_name': sc.get('short_name', sc['name']),
                 'url': base + sc['url'].lstrip('/')}
        if sc.get('description'):
            entry['description'] = sc['description']
        img = sc.get('image')
        if img and os.path.exists(img):
            fname = f'shortcut-{i}-96.png'
            ImageOps.fit(Image.open(img).convert('RGB'), (96, 96), Image.LANCZOS).save(os.path.join(icons_dir, fname))
            entry['icons'] = [{'src': f'{base}icons/{fname}', 'sizes': '96x96', 'type': 'image/png'}]
            extra.append(f'icons/{fname}')
        short.append(entry)

    manifest = {
        'id': base, 'name': name, 'short_name': short_name or name, 'description': description, 'lang': lang,
        'start_url': base, 'scope': base, 'display': 'standalone',
        'background_color': background_color, 'theme_color': theme_color,
        'icons': icons, 'shortcuts': short,
    }
    with open(os.path.join(out, 'manifest.webmanifest'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    sw = open(SW_TEMPLATE, encoding='utf-8').read()
    for key, value in {
        '__VERSION__': version, '__PREFIX__': cache_prefix,
        '__SAVE_VISITED__': 'true' if save_visited_pages else 'false',
        '__HOMES__': json.dumps([h.lstrip('/') for h in homes]),
        '__EXTRA__': json.dumps(extra + [p.lstrip('/') for p in extra_files]),
        '__SKIP__': json.dumps([p.lstrip('/') for p in skip_files]),
    }.items():
        sw = sw.replace(key, value)
    with open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8') as f:
        f.write(sw)
    return manifest

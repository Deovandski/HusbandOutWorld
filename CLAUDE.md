# Working in this repo

This is the #HusbandOutWorld series repo: the author's originals plus the website that is built from them. Read [README.md](README.md) and [AI-DISCLOSURE.md](AI-DISCLOSURE.md) first.

## Ground rules
- **`Legacy/` holds the originals and is never edited.** The website only reads it. A display-only correction goes in `content/fixes.json`, alt text goes in `content/alt-text.json`, and the page map goes in `content/site.json`. New Blog photos go in `Legacy/Public/Blog Photos/`; their descriptions (and any date a photo doesn't carry) go in `content/blog-photos.json`, in the author's own words. The website names each photo after the day it was taken.
- **Never invent lore.** Website text can be shortened, rearranged, labelled or typo-fixed, but every fact comes from Legacy. If the website and Legacy disagree, Legacy wins.
- **Use the author's own wording.** If you see a grammar fix, offer it as a suggestion; don't make it silently.
- **Two layers.** Public is what the old blog showed. Behind The Scenes adds the full notes and sits behind the spoiler toggle. Anything that wasn't public on the blog goes in the `bts` layer.

## World Lore format (always)
- **Topics on the World Lore page are A to Z within each group** ("The World", "Peoples", "Soul Energy & Science", "Nature"). The build sorts them by their displayed title, and `content/site.json` lists them in the same order. When you add a topic, put it in its alphabetical place.
- **Entries on a topic page are A to Z within each category.** The build sorts them, and the notes about the docs themselves (Documentation Notation, Distance Cost Tier, Isekai History) stay first. A topic whose order means something (a timeline, tiers, a colour wheel, a calendar) sets `"order": "source"` in `content/site.json` so it keeps the doc's order. Right now that's: the-world, history, harry, professions, walking-heart, the three interfaces, language, soul-energy, laws-and-treaties, economy, nari-gels, nari-bombs, education, races.
- Alphabetical means ignoring case, accents and punctuation ("Harry's Journey" sorts as "harrys journey"). Use `alpha_key()` in `tools/build.py`.

## Translations (Chinese, Japanese, Portuguese, Spanish, Arabic, Korean, Malay, Thai, German, Vietnamese)
The website is also published in ten languages (`/zh/`, `/ja/`, `/pt/`, `/es/`, `/ar/`, `/ko/`, `/ms/`, `/th/`, `/de/`, `/vi/`). Translations are written ahead of time by Claude and committed in `content/i18n/<lang>/`; English is the source. See the top of [tools/i18n.py](tools/i18n.py) for how it works.
- **Translate only what changed.** Every paragraph (segment) is stored under a hash of its English, so unchanged English is never translated again. Never re-translate segments that already have a translation, and never translate on a whim "to improve" one unless the author asks.
- **The loop:** build (`python tools/build.py --out _site --no-images`), then `python tools/i18n.py status`, then for each language `python tools/i18n.py todo --lang ja --phase 1 --max-words 6000 > work.json`. Fill in each item's `"t"`, then `python tools/i18n.py apply work.json`. Rebuild and check the pages. `python tools/i18n.py prune` drops translations whose English is gone.
- **When to translate:** not on every commit. English changes never wait for translations (untranslated segments show in English, marked `lang="en"`). Translate in batches: after a content PR merges, or when asked. Each batch is its own PR.
- **Keep the HTML exactly.** Translate the visible text (and alt/title text) only. Every tag, link and attribute in `"en"` must appear unchanged in `"t"` (`apply` warns when they differ). Don't translate URLs, file names, code, or `#HusbandOutWorld`.
- **Names are written by sound, never translated** (the author's rule): katakana in Japanese, the closest-sounding spelling in Chinese, Korean, Arabic and Thai; unchanged in Portuguese, Spanish, Malay, German and Vietnamese. Use and extend `content/i18n/<lang>/glossary.json` so a name is always spelled the same; add new names there the first time you translate them. The author's own pronunciation is the recording in `Legacy/Behind The Scenes/World Lore/Word Pronunciation/`. Real people (Deovandski, Mitsukiven, Feiourm) and the title *A Husband Out of This World* stay in Latin letters.
- **Variants:** Simplified Chinese, Brazilian Portuguese, Spain Spanish, Malaysian Malay, Germany German, standard Vietnamese. Arabic is right to left (`dir="rtl"`).
- **Phases:** 1 = interface, home, About pages, Blog, Webcomic, Gallery, public World Lore; 2 = the novel (one volume per PR); 3 = Glossary and Behind The Scenes. Behind The Scenes is translated too.
- **The banner** on translated pages comes from `content/i18n/<lang>/meta.json`: "AI-Translated to <language> from Original works by Deovandski and Mitsukiven/Feiourm".
- A language version is offered to search engines and the browser-language auto-select only once a page is 90% translated (`INDEX_COVERAGE` in tools/i18n.py).

## Building
```
pip install -r tools/requirements.txt
python tools/build.py --out _site            # full build, with images
python tools/build.py --out _site --no-images  # quick check (what CI runs on every PR)
```
Check a change in a browser at desktop (1280px) and phone (412px) widths before opening a PR.

## Pull requests
One PR per issue, with `Closes #N` in the body. Say what changed in plain words, list any judgment calls, and list anything the author still has to do.

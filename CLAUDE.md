# Working in this repo

This is the #HusbandOutWorld series repo: the author's originals plus the website that is built from them. Read [README.md](README.md) and [AI-DISCLOSURE.md](AI-DISCLOSURE.md) first.

## Ground rules
- **`Legacy/` holds the originals and is never edited.** The website only reads it. A display-only correction goes in `content/fixes.json`, a picture the website should show blurred goes in `content/blur.json`, alt text goes in `content/alt-text.json`, and the page map goes in `content/site.json`. New Blog photos go in `Legacy/Public/Blog Photos/`; their descriptions (and any date a photo doesn't carry) go in `content/blog-photos.json`, in the author's own words. The website names each photo after the day it was taken.
- **Link to the website or the repository, never Google Drive** (the author's rule). When a Legacy note links to Google Drive, Docs or Sheets, point it at the matching page on this website or the file's copy in the repository, as a display-only fix in `content/fixes.json`. New text never links to Google Drive.
- **Never invent lore.** Website text can be shortened, rearranged, labelled or typo-fixed, but every fact comes from Legacy. If the website and Legacy disagree, Legacy wins.
- **Use the author's own wording.** If you see a grammar fix, offer it as a suggestion; don't make it silently.
- **Abridged Behind The Scenes (issue #103).** The website can show an abridged, polished version of a raw Behind The Scenes doc: `content/bts/<same path as under Legacy/Behind The Scenes>`, one `# <entry title>` per entry (`# <category> › <entry title>` when a title repeats under two categories; `# _intro` replaces the doc's intro). Entries not listed fall back to the raw text. Each abridged section is labeled as AI-assisted and keeps the raw notes behind a "Show the original notes" toggle; the Markdown twins and llms files keep the raw text.
  - **Source order** when sources disagree: (1) the author's decision, (2) the published novels, (3) the rest of Legacy.
  - **Always polish grammar and typos** in the abridged text (the author's standing instruction); the raw notes behind the toggle stay as written.
  - **Keep the sass and spice** (the author's ruling): never sanitize the series' crude humor, profanity or sexual content for adult characters. A clinical rewrite makes it bland and boring; polish the grammar, keep the voice. Minors' attraction lines are phrased as "Fascinated by…".
  - **Lore that shocks today's norms is on purpose.** The fantasy draws on medieval and ancient Egyptian history, so things like a royal marrying young stay as written; don't "fix" them as discrepancies.
  - **Fill gaps only from Legacy** (other docs, the novels, the spreadsheets, the blog) or the author's answers. Never invent; leave out what can't be filled.
  - **Ask the author as you go**, in small batches per doc. Save every question, his answer word for word, every filled gap with its source, and every discrepancy in `content/bts/qa/<same path>.md` (proof of work, kept in English).
- **Two layers.** Public is what the old blog showed. Behind The Scenes adds the full notes and sits behind the spoiler toggle. Anything that wasn't public on the blog goes in the `bts` layer.
- **Never remove `google0c08003a2b869d98.html`** (repo root). It verifies the site in Google Search Console, which checks it again from time to time; without it the site stops being verified. The build copies it to the site's root unchanged (`root_files()` in `tools/build.py`); don't edit it, move it or put it in `Legacy/`.

## One source (no copies)
Anything shown in more than one place comes from one source, never pasted twice.
- **Text:** the novel, lore, glossary, search index, Markdown twins, `llms.txt` and the 14 translations are all built from `Legacy/` by `tools/build.py`. The Public and Behind The Scenes layers of a page are two views of the same doc. Don't copy Legacy text into `content/` or `site/`; `content/` only holds what Legacy doesn't have (fixes, alt text, summaries, the page map).
- **UI:** a widget used twice is one reusable component (see below), not two pasted copies. Colours and sizes live in `site/css/site.css`; code that needs them outside the stylesheet reads them from there (like `css_colors()` for the offline page).
- If a copy really has to stay, say why in the PR and get Deovandski's OK.

## World Lore format (always)
- **Topics on the World Lore page are A to Z within each group** ("The World", "Peoples", "Soul Energy & Science", "Nature"). The build sorts them by their displayed title, and `content/site.json` lists them in the same order. When you add a topic, put it in its alphabetical place.
- **Entries on a topic page are A to Z within each category.** The build sorts them, and the notes about the docs themselves (Documentation Notation, Distance Cost Tier, Isekai History) stay first. A topic whose order means something (a timeline, tiers, a colour wheel, a calendar) sets `"order": "source"` in `content/site.json` so it keeps the doc's order. Right now that's: the-world, history, harry, professions, walking-heart, the three interfaces, language, soul-energy, laws-and-treaties, economy, nari-gels, nari-bombs, education, races.
- Alphabetical means ignoring case, accents and punctuation ("Harry's Journey" sorts as "harrys journey"). Use `alpha_key()` in `tools/build.py`.

## Translations (Chinese, Japanese, Portuguese, Spanish, Arabic, Korean, Malay, Thai, German, Vietnamese, Italian, French, Hindi, Indonesian)
The website is also published in fourteen languages (`/zh/`, `/ja/`, `/pt/`, `/es/`, `/ar/`, `/ko/`, `/ms/`, `/th/`, `/de/`, `/vi/`, `/it/`, `/fr/`, `/hi/`, `/id/`). Translations are written ahead of time by Claude and committed in `content/i18n/<lang>/`; English is the source. See the top of [tools/i18n.py](tools/i18n.py) for how it works.
- **Translate only what changed.** Every paragraph (segment) is stored under a hash of its English, so unchanged English is never translated again. Never re-translate segments that already have a translation, and never translate on a whim "to improve" one unless the author asks.
- **The loop:** build (`python tools/build.py --out _site --no-images`), then `python tools/i18n.py status`, then for each language `python tools/i18n.py todo --lang ja --phase 1 --max-words 6000 > work.json`. Fill in each item's `"t"`, then `python tools/i18n.py apply work.json`. Rebuild and check the pages. `python tools/i18n.py prune` drops translations whose English is gone.
- **When to translate:** not on every commit. English changes never wait for translations (untranslated segments show in English, marked `lang="en"`). Translate in batches: after a content PR merges, or when asked. Each batch is its own PR.
- **Keep the HTML exactly.** Translate the visible text (and alt/title text) only. Every tag, link and attribute in `"en"` must appear unchanged in `"t"` (`apply` warns when they differ). Don't translate URLs, file names, code, or `#HusbandOutWorld`.
- **Names are written by sound, never translated** (the author's rule): katakana in Japanese, the closest-sounding spelling in Chinese, Korean, Arabic, Thai and Hindi (Devanagari); unchanged in Portuguese, Spanish, Malay, German, Vietnamese, Italian, French and Indonesian. Use and extend `content/i18n/<lang>/glossary.json` so a name is always spelled the same; add new names there the first time you translate them. The author's own pronunciation is the recording in `Legacy/Behind The Scenes/World Lore/Word Pronunciation/`. Real people (Deovandski, Mitsukiven, Feiourm) and the title *A Husband Out of This World* stay in Latin letters.
- **Variants:** Simplified Chinese, Brazilian Portuguese, Spain Spanish, Malaysian Malay, Germany German, standard Vietnamese, standard Italian, France French, standard Hindi, standard Indonesian. Arabic is right to left (`dir="rtl"`).
- **Phases:** 1 = interface, home, About pages, Blog, Webcomic, Gallery, public World Lore; 2 = the novel (one PR per language with all its volumes); 3 = Glossary and Behind The Scenes. Behind The Scenes is translated too.
- **The banner** on translated pages comes from `content/i18n/<lang>/meta.json`: "AI-Translated to <language> from Original works by Deovandski and Mitsukiven/Feiourm".
- A language version is offered to search engines and the browser-language auto-select only once a page is 90% translated (`INDEX_COVERAGE` in tools/i18n.py).

## Building
```
pip install -r tools/requirements.txt
python tools/build.py --out _site            # full build, with images
python tools/build.py --out _site --no-images  # quick check (what CI runs on every PR)
```
Check a change in a browser at desktop (1280px) and phone (412px) widths before opening a PR.

## Build reusable components
If a piece of UI could be useful twice, in this repo or in another of Deovandski's repos, build it as a reusable component instead of one-off code in a page. Examples: a clock, a counter or score card, a board, a gallery, a map, a picker.
- **Where:** a JavaScript module in `site/js/` with its own stylesheet in `site/css/`, plus one function in the build that writes its HTML. List it in a "Reusable components" section of README.md.
- **Self-contained:** everything it needs comes in as options/props or data attributes, with no reliance on page-specific code. Its styles are scoped to its own class and themed with CSS custom properties (with fallbacks). It works when used several times on one page.
- **Accessible:** text for screen readers, keyboard-friendly, and it respects `prefers-reduced-motion`.
- **Documented:** a comment at the top with a usage example and its options, plus a row in the list of reusable components.
- **Look before you build:** check the reusable components here and in the other repos first. The same rule is in Deovandski/Deovandski (`src/components/reusable/`: `SplitFlap`, a split-flap board, and `LedClock`, an LED countdown), Deovandski-repo-template, HusbandOutWorld, vraki-windows and Vraki-West-March-Campaign-D-D. Copy and adapt an existing component instead of starting over, and note where it came from.
- **Extract when you touch it:** when you change one-off UI that fits this rule, pull it out into a reusable component in the same PR.

## Pictures are clickable
Every picture on the website opens bigger when pressed, in the one photo viewer (`site/js/photo-viewer.js`, `site/css/photo-viewer.css`, and `photo_viewer_html()` in the build, already on every page). The same standard is in Deovandski/Deovandski, Deovandski-repo-template, Vraki-West-March-Campaign-D-D and sinoi-the-fisherman.
- **Pictures the build writes** go in `<a class="img-link" href="…" data-full="…">` as they do now. Add `data-gallery="name"` to step through a set with ‹ ›, and `data-caption` for a caption (the Blog's holds the date).
- **Any other `<img>` with alt text opens by itself**, and so does a link straight to an image file. Give every content picture real alt text (from `content/alt-text.json`); `alt=""` means decorative, and those don't open.
- **Dates:** without a `data-caption`, the viewer shows the alt text and then the date, in the page's language, when it knows one: `data-date="YYYY-MM-DD"` (or `data-date-label`), or a `YYYY-MM-DD` at the start of the file name.
- **Opt out** with `data-no-zoom` on a picture or its container. The webcomic reader (`.wc-strip`), the header and nav are already skipped.

## Pull requests
One PR per issue, with `Closes #N` in the body. Say what changed in plain words, list any judgment calls, and list anything the author still has to do.

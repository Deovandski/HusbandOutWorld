# Working in this repo

This is the #HusbandOutWorld series repo: the author's originals plus the website that is built from them. Read [README.md](README.md) and [AI-DISCLOSURE.md](AI-DISCLOSURE.md) first.

## Ground rules
- **`Legacy/` holds the originals and is never edited.** The website only reads it. A display-only correction goes in `content/fixes.json`, alt text goes in `content/alt-text.json`, and the page map goes in `content/site.json`.
- **Never invent lore.** Website text can be shortened, rearranged, labelled or typo-fixed, but every fact comes from Legacy. If the website and Legacy disagree, Legacy wins.
- **Use the author's own wording.** If you see a grammar fix, offer it as a suggestion; don't make it silently.
- **Two layers.** Public is what the old blog showed. Behind The Scenes adds the full notes and sits behind the spoiler toggle. Anything that wasn't public on the blog goes in the `bts` layer.

## World Lore format (always)
- **Topics on the World Lore page are A to Z within each group** ("The World", "Peoples", "Soul Energy & Science", "Nature"). The build sorts them by their displayed title, and `content/site.json` lists them in the same order. When you add a topic, put it in its alphabetical place.
- **Entries on a topic page are A to Z within each category.** The build sorts them, and the notes about the docs themselves (Documentation Notation, Distance Cost Tier, Isekai History) stay first. A topic whose order means something (a timeline, tiers, a colour wheel, a calendar) sets `"order": "source"` in `content/site.json` so it keeps the doc's order. Right now that's: the-world, history, harry, professions, walking-heart, the three interfaces, language, soul-energy, laws-and-treaties, economy, nari-gels, nari-bombs, education, races.
- Alphabetical means ignoring case, accents and punctuation ("Harry's Journey" sorts as "harrys journey"). Use `alpha_key()` in `tools/build.py`.

## Building
```
pip install -r tools/requirements.txt
python tools/build.py --out _site            # full build, with images
python tools/build.py --out _site --no-images  # quick check (what CI runs on every PR)
```
Check a change in a browser at desktop (1280px) and phone (412px) widths before opening a PR.

## Pull requests
One PR per issue, with `Closes #N` in the body. Say what changed in plain words, list any judgment calls, and list anything the author still has to do.

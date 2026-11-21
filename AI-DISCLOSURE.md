# AI Disclosure

This repo's website was built with an AI assistant, **Claude** (by Anthropic), working from the #HusbandOutWorld originals. This page says plainly which parts are human work, which parts the AI wrote, and how the two fit together.

## The short version
- **The story and the world are human-made.** The light novel, the story notes, the World Lore, the spreadsheets, the Vraki font and the old blog come from Deovandski Skibinski Junior, and the illustrations are by the series' artists, **Mitsukiven** and **Feiourm**. All of it lives, unchanged, in the [Legacy](Legacy) folder.
- **The website shows the author's own words.** The novel chapters, the public descriptions (from the old blog) and the Behind The Scenes notes (from the original docs) are displayed as written. The AI's job was to arrange them, not to rewrite them.
- **No AI-generated images.** Every picture is existing series art. The AI only resized and converted copies for the web.
- **A few things are AI-written, and they're labeled.** The website's code and its own text (menus, buttons, help), the short summaries for eight lore topics the blog never covered, the alt text that describes each illustration, and this page.
- **The translations are AI-written, and every translated page says so.** The website is also offered in other languages (pick one in Settings). Claude translated the author's text ahead of time (it is not machine translation on the fly), following the author's rules: names are written by sound, never translated. Each translated page carries a banner saying it was AI-translated from the original works, with a link to the English original. English is the source; if a translation and the English disagree, the English wins.
- **A human decides.** Deovandski directed the work, set the rules (originals stay untouched in Legacy, the website never invents lore), and chose what got committed. If something on the website contradicts Legacy, **Legacy wins**: please open an issue or send a PR.

## Attribution statement
Modeled on the questions in IBM's [AI Attribution Toolkit](https://www.research.ibm.com/blog/AI-attribution-toolkit) (what AI was used, what it contributed, how much humans shaped it, and who is accountable):

> **AI system:** Claude, a large language model by Anthropic, used as an assistant with access to the repo files and the Blogger export (November 2026).
> **Human contribution:** all source material (the novel, the story notes, the World Lore, the spreadsheets, the blog and the Vraki font, by Deovandski Skibinski Junior; all artwork, by Mitsukiven and Feiourm); the website concept (one site, a Public layer and a Behind The Scenes layer behind a spoiler warning, a Vraki mode, a Forway color palette); direction and approval of every commit.
> **AI contribution:** translating the website into other languages; moving the originals into Legacy and converting the blog to Markdown; designing and coding the website, its build script and its tools (search, glossary, settings); matching each blog section to its entry in the original docs; writing eight short topic summaries; writing alt text for the illustrations; writing the AI-readable files (llms.txt and the rest).
> **Human modification:** Deovandski reviews and requests changes.
> **Accountability:** Deovandski Skibinski Junior.

## Alt text, for accessibility
Every illustration on the website has a short text description (alt text) so people who use screen readers can follow along, and so search engines and AI tools can understand the pictures. Writing it means describing the art in new words, which goes beyond the "never write anything new" rule this project follows everywhere else. **Deovandski allowed this exception for the sake of accessibility.** The descriptions are in [content/alt-text.json](content/alt-text.json) and say only what is visible in each picture. They add no lore, and if one is wrong, the picture wins.

## File by file

| Path | Where it comes from | What the AI did |
|---|---|---|
| [Legacy/Behind The Scenes](Legacy/Behind%20The%20Scenes) | This repo's original files (human). | Moved them into this folder without editing them. The one exception: at Deovandski's request, the Vraki typeface license (`Logo and Font/LICENSE.md`) now names LinkedIn and email as the way to ask for commercial approval. Also at his request ("Bypass due to content mod", issue #79), two explicit pictures embedded in the story notes (Arc #2 and Arc #3, `[image4]` in each) were replaced with copies blurred by 50%. Also the World Lore additions Deovandski approved in [World Lore Q&A](Legacy/Behind%20The%20Scenes/World%20Lore%20Q%26A) (in the repo, each added line points back to its entry; the website leaves those pointers out). |
| [Legacy/Behind The Scenes/World Lore Q&A](Legacy/Behind%20The%20Scenes/World%20Lore%20Q%26A) | Deovandski's review comments on the ghostwriter's Vol 4 drafts, and his approval notes. | Written by the AI at his direct instruction. Each entry pairs a line or two of the draft with his comments (word for word) and answer, notes what the World Lore already says, proposes additions, and records his approval. The World Lore lines added this way are listed in each entry's "Applied" section rather than here. |
| [Legacy/Public](Legacy/Public) | The old blog, from the Blogger export (human). | Converted each of the 33 live pages from HTML to Markdown, word for word, with [tools/import_blogger.py](tools/import_blogger.py). Pointed blog images at the matching file in Behind The Scenes where the pictures were the same. The exceptions: in November 2026 Deovandski changed his Vol 4 afterword (`afterwords.md`), adding new mantras and rewriting the closing to end with a Hávamál quote. The AI typed those edits in at his explicit direction, including changing "two new ones" to "three new ones" after he added the seed/harvest mantra himself, ending that mantra with "!" like the others, and rewording one sentence near the end about raising a family. Later the same month, again at his direct instruction, the AI replaced the Vol 4 afterword's ghostwriter paragraph ("If this series somehow explodes…") with his new version, which adds how the collaboration with the ghostwriter went, and replaced the paragraph after it ("And no. I didn't use AI…") with his new version, which lists more of what Claude was used for. |
| [Legacy/README.md](Legacy/README.md) | — | Written by the AI. |
| [content/site.json](content/site.json) | The structure of Legacy (human). | Written by the AI: the page map that says which blog page and which original doc make up each website page. |
| [content/summaries.json](content/summaries.json) | Eight Behind The Scenes docs: World Timeline, Villages, Land, Professions, Education, Sports, Novels, Natural and Crafted Resources (human). | **Shortened and paraphrased** them into one-paragraph public summaries, because the blog never had pages for these topics. No new facts. Each summary is labeled on the website as AI-written. |
| [content/fixes.json](content/fixes.json) | Requests from Deovandski. | A short list of display-only corrections the build applies when it reads Legacy (for example, replacing dead Google Drive links and dropping a print-only table of contents). Each one says why. Legacy itself stays untouched. |
| [content/alt-text.json](content/alt-text.json) | The illustrations (human). | Written by the AI, for accessibility (see above). |
| [tools/build.py](tools/build.py), [site/](site) (CSS and JavaScript) | The palette comes from the Forway city emblem, the headings' Vraki script from the Vraki font (human). Body font: TeX Gyre Schola (GUST Font License), the same as the [Vraki West March Campaign](https://github.com/Deovandski/Vraki-West-March-Campaign-D-D) site. | **Designed and coded by the AI:** the layout and look, the Public and Behind The Scenes layers and the spoiler warning, dark and light themes, text size, Vraki mode, search, the glossary, the gallery, the chapter reader and the lightbox. The website's own text (menus, buttons, notices) is AI-written. |
| [tools/pwa.py](tools/pwa.py), [site/sw.js](site/sw.js) (installable app) | The Forway city emblem and three existing illustrations (human), used for the app icon and the shortcut icons. The code is adapted from the Deovandski site's app (PR #160). | **Written by the AI:** the app manifest, the icon generator (resizes and crops copies; the originals are only read), the service worker that keeps opened pages readable offline, and its offline notice. |
| Novel pages | The three volumes of Arc #1 (human). | Split each volume into chapter pages and placed every subchapter illustration at the start of its subchapter. The text is shown as written. |
| World Lore pages | The blog pages (Public) and the original docs (Behind The Scenes) (human). | Matched each blog section to its entry in the docs by name. Where an entry had no blog text, used the "Website Description" the author wrote inside the doc. Entries with neither stay in Behind The Scenes only. |
| Glossary | The lore entries (human). | Built automatically: each term, its topic, and the first sentence or two of its description, cut from the author's text. |
| AI-readable files (`llms.txt`, `llms-full.txt`, `llms-full-bts.txt`, a Markdown copy of every page, and `data/*.json`) | Everything above. | Generated by the build script, so AI tools and search engines can read the whole series in plain text. |
| [content/i18n](content/i18n) | The website's English pages, built from Legacy. | **Translated by the AI** into each language in the Settings list, paragraph by paragraph, with [tools/i18n.py](tools/i18n.py). The name spellings in each `glossary.json` follow the author's rule (by sound, never translated). Every translated page is labeled as AI-translated. |
| [.github/workflows/pages.yml](.github/workflows/pages.yml) | The [Vraki West March Campaign](https://github.com/Deovandski/Vraki-West-March-Campaign-D-D) workflow. | Written by the AI. |
| [AI-DISCLOSURE.md](AI-DISCLOSURE.md) | The [Vraki West March Campaign's](https://github.com/Deovandski/Vraki-West-March-Campaign-D-D/blob/main/AI-DISCLOSURE.md) disclosure. | Written by the AI. |

## Outside sources
The AI read these for ideas. No text was copied from them.
- IBM Research, [AI Attribution Toolkit](https://www.research.ibm.com/blog/AI-attribution-toolkit)
- The [llms.txt proposal](https://llmstxt.org/), for the AI-readable index
- [schema.org](https://schema.org/) (BookSeries, Book, Chapter), for the structured data in each page

## Contributing
PRs are welcome, with or without AI help. If you used AI for a contribution, say so in the PR description and add a line to the table above.

© Deovandski Skibinski Junior. Licensed under CC‑BY‑NC‑SA‑4.0.

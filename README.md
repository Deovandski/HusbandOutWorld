# A Husband Out Of This World

![](Legacy/Behind%20The%20Scenes/WorldMapMD.png)

## SPOILER WARNING!

This repo makes everything behind the #HusbandOutWorld series available. EVERYTHING!

Want the reader-friendly version with fewer spoilers? Visit the website: **[HusbandOutWorld.com](https://www.husbandoutworld.com)**. It starts in **Public** mode, with the full light novel and the lore as the blog showed it. Flip the switch to **Behind The Scenes** and every page adds the author's full notes (after a spoiler warning).

Enjoying the story? The eBook is on [Amazon](https://www.amazon.com/dp/B0BT5XM4QC). Please support the series there!

## 

### What's where?

| Folder | What's inside |
|---|---|
| [Legacy](Legacy) | **The originals, made by humans, unchanged.** `Legacy/Public` is the old blog (reader-facing, light on spoilers). `Legacy/Behind The Scenes` is everything else: the light novel manuscripts, the story notes for Arcs #2 to #5, the World Lore docs, the spreadsheets, the fonts, every illustration with its source files, and the webcomic's raw pages (`Webcomic/Vol N/Chapter N/Sub N`). |
| [content](content) | The website's page map, short AI-written summaries and alt text, all built from Legacy. Also `blur.json`: pictures the website shows blurred, without changing Legacy. Also `blog-photos.json`: descriptions (and any missing dates) for the photos on the Blog page. New Blog photos go in [Legacy/Public/Blog Photos](Legacy/Public/Blog%20Photos). |
| [content/i18n](content/i18n) | The website's translations (Chinese, Japanese, Portuguese, Spanish, Arabic, Korean, Malay, Thai, German, Vietnamese, Italian, French, Hindi, Indonesian), written ahead of time by AI. See [tools/i18n.py](tools/i18n.py). |
| [tools](tools), [site](site) | The website's build script, styles and code. |
| [AI-DISCLOSURE.md](AI-DISCLOSURE.md) | What a human made, what an AI made, and how they fit together. |

Everything on the website comes from Legacy. It is shortened, rearranged or labeled, never invented. If the two ever disagree, Legacy wins.

### For AI tools

The website publishes the whole series as plain text: [llms.txt](https://www.husbandoutworld.com/llms.txt) (index), [llms-full.txt](https://www.husbandoutworld.com/llms-full.txt) (Public layer) and [llms-full-bts.txt](https://www.husbandoutworld.com/llms-full-bts.txt) (everything). The same text also comes in smaller files by section (each about 300 KB or less), listed with their sizes in llms.txt, for readers that stop partway through a long file. Every page also has a Markdown copy at its address plus `index.md`; a very long one (Characters) splits its full notes into one file per category. Translated pages that are ready (90% or more) have a Markdown twin in their language too, listed per language in llms.txt. All of these are in the sitemap.

### Build the website yourself

```
pip install -r tools/requirements.txt
python tools/build.py
```

The site lands in `_site/`. GitHub Actions builds and publishes it on every push to `main`. `python tools/check_site.py _site` checks that every page's pictures are in the build and shows the site's size against GitHub Pages' 1 GB limit (the publish run does this too, and shows the sizes on its summary page).

`google0c08003a2b869d98.html` at the repo root verifies the site in Google Search Console. The build publishes it unchanged at the site's root. **Never remove it**: Search Console checks it again from time to time, and the site stops being verified without it.

### Reusable components

| Component | Files | What it does |
|---|---|---|
| Installable app (PWA) | [tools/pwa.py](tools/pwa.py), [site/sw.js](site/sw.js), settings in `"app"` in [content/site.json](content/site.json) | Makes the site installable on phones and computers: writes the manifest (name, colours, home-screen shortcuts), the app icons (made from a logo, including a maskable one for Android) and a service worker. The worker keeps the home page and every page a reader opens readable offline, as text only; pictures are never saved. Pages always come from the server first (`no-cache`), so a reader sees a deploy on the very next visit; only CSS and scripts with a `?v=<hash>` address are served from the saved copy first. Options include `skip_files` (files the worker never touches) and `offline_colors`. Adapted from Deovandski/Deovandski (PR #160). |
| Iso darts (`.iso-darts`) | `iso_darts_html()` in [tools/build.py](tools/build.py), [site/js/iso-darts.js](site/js/iso-darts.js), [site/css/iso-darts.css](site/css/iso-darts.css), the game in [content/territory-snipping.json](content/territory-snipping.json) | An on-rails darts scene in an isometric room: scripted speech bubbles, then a timed round on a board of coloured territories (claim, cancel, smaller is worth more) with a swaying aim. Next and Throw! are buttons (Space or Enter throws), every line and result is announced, and reduced motion drifts the aim slowly and skips the spin. All its words are in the page, so the translations reach them. Territory Snipping on the [Playground](https://www.husbandoutworld.com/playground/). Ported from Deovandski/Deovandski (`IsoDarts.astro`). |
| Play sideways (`.play-sideways`) | `play_sideways_html()` in [tools/build.py](tools/build.py), [site/js/play-sideways.js](site/js/play-sideways.js), [site/css/play-sideways.css](site/css/play-sideways.css) | Wraps a game that needs a wide screen: on a phone held upright it asks to turn the phone sideways (with "Play full screen" where the browser can lock the screen, and "Play upright instead"), and shows the game once it's sideways. Adapted from Deovandski/Deovandski (`GimmickPlay.astro`). |
| Photo viewer (`#photo-viewer`) | `photo_viewer_html()` in [tools/build.py](tools/build.py), [site/js/photo-viewer.js](site/js/photo-viewer.js), [site/css/photo-viewer.css](site/css/photo-viewer.css) | Every picture opens bigger when pressed, with its caption and its date when there is one; ‹ › step through a gallery or the pictures on the page. Replaces the old lightbox. Ported from Deovandski/Deovandski (PR #205). |
| Video player (`.hv-video`) | `video_figure()` in [tools/build.py](tools/build.py), [site/css/video.css](site/css/video.css) | A captioned, never-autoplaying video. In markdown, `![caption](clip.mp4)` becomes one. |

### Spot something wrong, or want to make a change?

Create an issue or feel free to send a PR!

### Are you a D&D DM and want to have fun with our World Lore?

All D&D content now lives in the [Vraki West March Campaign](https://github.com/Deovandski/Vraki-West-March-Campaign-D-D) repo: an open-table West Marches campaign set in this world, with a World Lore summary, travel rules, quests, stat blocks and ready-made adventurers. If you host a campaign, let us know! Love to see pics!

Monetized videos, streams and social media posts about the series are welcome, and so are streams and 3D prints made from the source files: just credit us. Any other commercial use needs approval first. See [Permissions beyond the license](LICENSE.md#permissions-beyond-the-license).

### Are you an artist, illustrator, etc?

Feel free to peruse. If you have any questions, let us know. We’re open for collabs and crossposts!

### Are you a publisher?

Want to reach out to the author? We’re open to a copyright/trademark transfer for an Omnibus vol or other publishing ideas, including a new version through a ghostwriter. Reach out on [LinkedIn](https://www.linkedin.com/in/deovandski/) or email [Deovandski@outlook.com](mailto:Deovandski@outlook.com) for more info!

### Want to use the Vraki font?

The Vraki typeface in [Logo and Font](Legacy/Behind%20The%20Scenes/Logo%20and%20Font) has its own [license](Legacy/Behind%20The%20Scenes/Logo%20and%20Font/LICENSE.md). Non-commercial use is free with attribution. Commercial use needs approval and a fee, kept small for artists and creators to support the community; ask on [LinkedIn](https://www.linkedin.com/in/deovandski/) or email [Deovandski@outlook.com](mailto:Deovandski@outlook.com). Please don't alter the font without permission.

© Deovandski Skibinski Junior. *A Husband Out of This World* and *#HusbandOutWorld* are trademarks of Deovandski Skibinski Junior. Licensed under CC‑BY‑NC‑SA‑4.0, except the fonts in Logo and Font (see [LICENSE.md](LICENSE.md) for copyright, trademarks and fonts).

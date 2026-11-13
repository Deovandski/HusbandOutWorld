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
| [content](content) | The website's page map, short AI-written summaries and alt text, all built from Legacy. Also `blog-photos.json`: descriptions (and any missing dates) for the photos on the Blog page. New Blog photos go in [Legacy/Public/Blog Photos](Legacy/Public/Blog%20Photos). |
| [tools](tools), [site](site) | The website's build script, styles and code. |
| [AI-DISCLOSURE.md](AI-DISCLOSURE.md) | What a human made, what an AI made, and how they fit together. |

Everything on the website comes from Legacy. It is shortened, rearranged or labeled, never invented. If the two ever disagree, Legacy wins.

### For AI tools

The website publishes the whole series as plain text: [llms.txt](https://www.husbandoutworld.com/llms.txt) (index), [llms-full.txt](https://www.husbandoutworld.com/llms-full.txt) (Public layer) and [llms-full-bts.txt](https://www.husbandoutworld.com/llms-full-bts.txt) (everything). Every page also has a Markdown copy at its address plus `index.md`.

### Build the website yourself

```
pip install -r tools/requirements.txt
python tools/build.py
```

The site lands in `_site/`. GitHub Actions builds and publishes it on every push to `main`.

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

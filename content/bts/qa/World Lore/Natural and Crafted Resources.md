# Natural and Crafted Resources: abridgement Q&A (proof of work)

- **Raw (Legacy):** `Legacy/Behind The Scenes/World Lore/Natural and Crafted Resources.md` (unchanged)
- **Abridged (website):** `content/bts/World Lore/Natural and Crafted Resources.md`
- **Issue:** #103

Every question asked of the author and his answer (word for word), every gap filled from elsewhere in Legacy (with its source), every discrepancy and how it was settled, and what was left out. Source order: (1) the author's decision, (2) the published novels, (3) the rest of Legacy.

**Polish (the author's standing instruction, 2026-11-22: "Polish grammar, typos always."):** every entry and table was polished for grammar and typos.

**How this one was abridged:** "See Flora", "See Fauna", "See Beasts", "See Walking Heart Interface" and "See Economy Calculator" pointers became short summaries, with the numbers taken from the spreadsheet and links to the matching website pages. The household tables keep their items and prices; the multi-material prices (picker, mugs, seal stamp) are paired with their material so they read on a phone. Every picture is kept.

---

## Questions for the author

Status: **answered** 2026-11-22. Asked as one batch on 2026-11-22.

### R1. Gems as Tier II (Common Goods)?
- **Legacy text:** Distance Cost Tier › Tier II (Common Goods): "Expensive Mineral Resources: Nari Stones, Sapphire, Aquamarine, Amethyst". Tier III (Expensive Goods): "Rare Mineral resources: Gold, Titanium".
- **Why:** The Nari Gels doc says a common person might buy something as expensive as one sapphire once in their lifetime, and the Ore Base Price Calculator prices a sapphire far above gold. Is Tier II on purpose (for example, because gems are the currency and light to ship), or should the gems move up?
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > R1) Yes. Gems setup as and for currency is basically a common good from a shipment, handling perspective. Security wise that's where it becomes special as basically only heavily fortified wagons and only Forway themselves move large quantities of currency around the cities/kingdoms which when that happens then it's basically Tier IV for how bandits etc would be salivating for that... So make a note about that.
- **Change to the abridged text:** a "Why gems are Tier II" note under the tiers: currency is a common good for shipping and handling; only Forway moves large amounts, in heavily fortified wagons, and to bandits that's basically Tier IV.

### R2. Titanium
- **Legacy text:** Tier III: "Gold, Titanium".
- **Why:** Titanium appears nowhere else in Legacy (the spreadsheets have gold, copper, iron and steel, but no titanium). Keep it as a Vraki metal, or drop it?
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > R2) keep it.
- **Change to the abridged text:** none; titanium stays in Tier III.

### R3. Black Sapphire Tree's wood: Soul Wood or Black Wood?
- **Legacy text:** Flora › Black Sapphire Tree › Economic value: "Soul Wood" ("Has a dark color to it, and is dense…"). This doc and the spreadsheets call it Black Wood (sigil rings in Soul Wood or Black Wood).
- **Why:** Should the Black Sapphire Tree's product be named "Black Wood" in Flora?
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > R3) I think we have both soul wood and black wood... Maybe nari wood too? Check the trees. See what you pull up
- **What Legacy has** (searched every Markdown file, the novels included):
  - **Soul Wood**, from the Soul Tree: Flora (Soul Tree products: Soul Wood, Soul Wood Seeds, Ground Soul Wood); badges are "normally made out of soul wood, hence its greenish color" (`Legacy/Public/badges-embassies.md`); Nari stones are set into Soul Wood (Beasts); Trunk People light up big Soul Wood trees (Beasts, Kingdoms).
  - **Black Wood**, from the Black Sapphire Tree: "More commonly known today as black wood"; its Interface is "Black Wood"; "its perfectly black wood can prevent soul energy leakage like no other tree, even better than the soul tree itself" (Flora, Website Description); black wood badges for city officials, kingdom and embassy representatives (Embassies & Guilds; "Black wood Nari badges" in `Legacy/Public/badges-embassies.md`).
  - **Nari wood:** not found anywhere. The closest are "Black wood Nari badges" and Nari stones set into Soul Wood.
- **Change to the abridged text:** the Black Sapphire Tree's product in Flora is named "Black Wood" (its "Soul Wood" heading was a leftover from the Soul Tree entry; its description, dark and dense, is the black wood's). Soul Wood and Black Wood here gain the badge details and the "even better than Soul Wood" line. No Nari wood is added.
- **Made official** (2026-11-22, the author: "Make it official."): `content/fixes.json` renames the raw Black Sapphire Tree product to Black Wood.

---

## Gaps filled from other Legacy sources

| Abridged text | Raw note | Source |
|---|---|---|
| Walking Heart: black, fist-sized stones from Hifuna's irradiated zones; the user becomes undead; banned by Forway | "See Walking Heart Interface" | Science - Walking Heart Interface.md |
| Wood People wood: very durable, dark red, woody musk when soaked | "See Beasts > Wood People" | Beasts.md (Wood People Wood) |
| Soul Wood: from the Soul Tree around Blood City and Freeish; keeps Soul Energy from leaking; seeds give caffeine, "basically the world's coffee" | "See Flora" | Flora.md (Soul Tree) |
| Black Wood: from the Black Sapphire Tree between Flatland and Forway; soaks up Soul Energy; a tree can cost a whole sapphire | "See Flora" | Flora.md (Black Sapphire Tree) |
| Winga Dust: ground beaks and claws, strengthened by a Winga before removal, lasting years | "See Fauna > Winga" | Fauna.md (Winga Dust) |
| Weapon material costs (dagger, sword, longsword, bow in iron, steel, Bone Wood, chitin), cheapest to most expensive region | "See Economy Calculator for more information." | `Spreadsheets/Formulas - Economy.xlsx` › Weapon & Household Price Calculator (material cost alone + shipping) |
| Full armor set costs (iron, steel, Bone Wood, chitin, Tibou, leather) and the working days to afford one | "See Economy Calculator for more information." | `Spreadsheets/Formulas - Economy.xlsx` › Equipment Price Calculator (Full Set; Tier I Avg Days) |
| Sigil rings: Soul Wood ~22–102 Pearls, Black Wood ~62–158 Pearls | "See Economy Calculator" | `Spreadsheets/Formulas - Economy.xlsx` › Weapon & Household Price Calculator (Sigil Rings) |
| Fernan's bow disappeared with him; Magi wants to find it; Wilson Big-Gyut tried to steal it and recreated it from memory | "See Fernam clip." | Characters.md (Magi Blood, Wilson Big-Gyut) |
| Morika's armor: a Sweet Sting costume to gather Black Honey inspired it; ~1.5 years of savings; makes up for slow reflexes and hides his face; The Stinger persona; kills with the helmet's spike | "See Character." | Characters.md (Morika Tolerideme) |
| Picker: a two-pronged fork on one end and a spoon on the other, sometimes carved with the owner's name ("Donas' Picker") | (no description) | Novel, Vol 1 (Harry at the dinner table) |
| Toothbrush: wooden, with stiff red bristles; toothpaste: green syrup of mint, green tea and citrus that numbs the tongue in large amounts; the pull-gate handle lets water flow from the pipe | (materials only) | Novel, Vol 1 (Harry in the bathroom) |
| Writing stick: links to Kiko | "See Kiko" | Characters.md (Kiko Sanbi Half-Cruro) |

## Discrepancies

See R1 and R3.

## Left out on purpose

- "(See World Lore Q&A › Vol 4 Draft 2, Q1/Q19.)": the answers are already in the notes, and the Q&A drafts aren't on the website.
- "See Fernam clip.": no clip by that name exists in the repository; the entry links to Fernan on the Characters page instead.
- Spreadsheet prices are given as ranges across the four regions, rounded to the nearest Pearl, instead of one table per region.

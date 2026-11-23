# Economy: abridgement Q&A (proof of work)

- **Raw (Legacy):** `Legacy/Behind The Scenes/World Lore/Economy.md` (unchanged)
- **Abridged (website):** `content/bts/World Lore/Economy.md`
- **Issue:** #103

Every question asked of the author and his answer (word for word), every gap filled from elsewhere in Legacy (with its source), every discrepancy and how it was settled, and what was left out. Source order: (1) the author's decision, (2) the published novels, (3) the rest of Legacy.

The doc has "Isekai History" under both Economy and Balls Currency, so the abridged file names those two as `# Economy › Isekai History` and `# Balls Currency › Isekai History`.

---

## Questions for the author

Status: **open** until answered. An open question means the abridged text leaves that point out rather than guessing. Asked as one batch on 2026-11-21 and answered the same day.

### EC1. Link the salary and distance numbers to the repository spreadsheet? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Daily Salary / Weekly Salary: "See [Economy Calculator](https://docs.google.com/spreadsheets/d/1B2y…)"
- **Why:** The abridged text puts the main numbers from `Spreadsheets/Formulas - Economy.xlsx` in tables and links to that file in the repository instead of the Google Sheet (the raw notes keep the Google link). OK, or should it link to the Google Sheet?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Yep. Also add to your internal docs to always point to to the website or repo, and avoiding external references to Google Drive.
- **Change to the abridged text:** Keeps the links to the repository copy. The raw notes now also point there (`content/fixes.json`), and CLAUDE.md has the rule: link to the website or the repository, never Google Drive.

### EC2. A week's pay: 4 days? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Weekly Salary: "Average Weekly salary assumes pay for every day." The spreadsheet: "Salary Per Week (~4 Days)".
- **Why:** A week has 5 days, with Forrday as the weekend. I wrote "pay for every work day: about 4 a week". Right?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Yes.
- **Change to the abridged text:** "pay for every work day: 4 a week, with Forrday off."

### EC3. How much is a map? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Amethyst › Indirect Conversions: "Maps are usually priced at this rate for Aquamarine for more complex ones."
- **Why:** I read it as "maps usually cost about an Amethyst; more complex ones an Aquamarine". Is that right?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Yes.
- **Change to the abridged text:** Maps added under Amethyst: "maps (more complex ones cost an Aquamarine)".

### EC4. Freeish to Gandew: 3,293 km? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** `Formulas - Economy.xlsx` › Distance Cost Calculator: Freeish Region ↔ Gandew Region 3293 km (every other region pair is a round number).
- **Why:** Is 3,293 km intended, or a placeholder?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > What would be the whole number for this? Also, we can put "~" on the whole number to make distances easy to display.
- **Change to the abridged text:** Rounded to ~3,300 km (the nearest hundred), and every region distance now has "~" (~1,000 km, ~2,000 km, …). The spreadsheet is unchanged.

---

## Gaps filled from other Legacy sources

| Abridged text | Raw note | Source |
|---|---|---|
| Shipping cost per Distance Cost Tier (1 Pearl per kg every 120 / 84 / 58.8 / 29.4 km), a full egua cart, 150 kg, 30 km a day with cargo, 65 km ridden | "\*D.T.C must be accounted for…" | `Spreadsheets/Formulas - Economy.xlsx` › Distance Cost Calculator (D.C.T values and constants; costs are distance ÷ D.C.T, rounded up) |
| Distances between the four regions | (none) | Same sheet, region route tables |
| Hourly, daily and weekly pay per tier; ~75% expenses; yearly totals over 73 weeks | "See Economy Calculator" | `Formulas - Economy.xlsx` › Salary Calculator |
| "1 Pearl is about 1 US dollar" | (none) | `Formulas - Economy.xlsx` › Balls Calculator: "1 US DOLLAR = 1 PEARL BALL" |
| "hay for an egua" | "Hay for a horse." | Vol 1: Harry corrects himself, "Not horse. She called it—egua!" Vraki's horse is the egua. |

## Discrepancies

### Region travel times in the spreadsheet (left out)
- **Sources:** `Formulas - Economy.xlsx` › Distance Cost Calculator. Some region tables give ride and cargo days that don't match their distance (e.g. Gandew ↔ Sanbi 3,000 km, but 30.8 ride days, which is 2,000 km at 65 km a day).
- **Abridged text:** gives the distances and the daily limits, not the days.

### Yearly pay in Sapphire (left out)
- **Sources:** `Formulas - Economy.xlsx` › Salary Calculator, "Salary Per Year (73 Weeks) (Sapphire)": 51.16 Sapphire for Tier I, but 3,504 Pearls is about 0.7 Sapphire (the formula multiplies by 73 weeks twice).
- **Abridged text:** gives the yearly pay in Pearls only.

### Egua cargo and shipping (settled by the Egua load proposal)
- **Legacy text:** `Formulas - Economy.xlsx`: an Egua pulls up to 150 kg of cargo, about 30 km a day.
- **Discrepancy:** the strain rule in [Fauna - Egua load proposal.md](Fauna%20-%20Egua%20load%20proposal.md) lets a cart Egua pull ~900 kg on a dirt road.
- **Answered:** 2026-11-22 (Fauna Q&A, N2)
- **Answer (verbatim):**
  > N2: We can have both. Some roads they can use carts others not. Plus there are other fees into shipping not discussed like protection fee, insurance, profit etc that will cover the gap now that shipping is less expensive as the éguas can pull a lot more when pulling carts.
  >
  > So from distance cost tier it is basically the same as we can explain the cost away, and we're just updating the calculations that led to that tier calculation.
- **Change to the abridged text:** the 150 kg is cargo on a pack Egua's back on rough routes; carts pull far more where roads allow; shipping prices stay the same because they also pay for protection, insurance and the shipper's profit. The Distance Cost Tier figures are unchanged.

## Left out on purpose

- "D.T.C" read as "D.C.T" (Distance Cost Tier), and "Kingdown" as "Kingdom" (typos).

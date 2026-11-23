# World Map, Name, Vraki Calendar & UOM, etc: abridgement Q&A (proof of work)

- **Raw (Legacy):** `Legacy/Behind The Scenes/World Lore/World Map, Name, Vraki Calendar & UOM, etc.md` (unchanged)
- **Abridged (website):** `content/bts/World Lore/World Map, Name, Vraki Calendar & UOM, etc.md`
- **Issue:** #103

Every question asked of the author and his answer (word for word), every gap filled from elsewhere in Legacy (with its source), every discrepancy and how it was settled, and what was left out. Source order: (1) the author's decision, (2) the published novels, (3) the rest of Legacy.

---

## Questions for the author

Status: **open** until answered. An open question means the abridged text leaves that point out rather than guessing. Asked as one batch on 2026-11-21 and answered the same day (W1 after the author asked for context).

### W1. Whose units did Adrian pick: Blood's or Tolerideme's? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Vraki UOM: "decided to standardize all UOMs based on the best UOMs being used around—which all happened to be from Blood due to their constant hunting nature." The public Economy & UOMs page: "the most accurate one in existence—which happened to be the Tolerideme Kingdom, coincidentally where he was from."
- **Why:** The two disagree. Which is right?
- **Reply:** 2026-11-21
- **Reply (verbatim):**
  > Can you give me the paragraphs/URL where I say that? Need more context to make a decision.
- **Context sent:** both passages in full (the Vraki UOM note in this doc, and the public Economy & UOMs page, section Vraki UOMs), plus the World Timeline's "Adrian From North Tolerideme" (650 A.G.).
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Adrian is from Tolerideme, so the accuracy of it comes from the Tolerideme culture, and the desire to standardize. Adrian did love hunting, specially near Blood, so the name of the standards came from that, such as Sorebone coming from "Soreno bones"
- **Change to the abridged text:** Vraki UOM now says Adrian was from Tolerideme, the units' accuracy comes from Tolerideme's culture and desire to standardize, and their names come from his hunting near Blood (Sorebone from "Soreno bones"). The raw note stays as written behind the toggle.

### W2. How heavy is a Sorebone? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** `World Calendar & UOM.xlsx` › UOM: "Gram | Sorebone | 0.01" and "Miligram | Tiny Sorebone | 0.001" (in kg).
- **Why:** A gram is 0.001 kg, so the labels and numbers disagree: is a Sorebone 10 g (0.01 kg) or 1 g? And a Tiny Sorebone 1 g or 1 mg?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Sorebone is 10g. Tiny Sorebone is a gram. Make that official (but check if I mention about it on the novels. If I mention about it on the novels, then overrides us. Otherwise if only on the Behind The Scenes/Public doc, then er can officialy correct.)
- **Change to the abridged text:** Checked: the novels never mention Sorebone (they use only "largeadi"), so the author's values are official. The units table adds Sorebone 10 g and Tiny Sorebone 1 g. The spreadsheet is unchanged.

### W3. When did the Prosperity Treaty come into effect? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Name Schema: "any kingdom child born after the prosperity treaty came into effect in 671 A.G." World Timeline: "The Prosperity Treaty Period (680 A.G. - Current)".
- **Why:** 671 or 680 A.G.?
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > World Timeline. Make that official.
- **Change to the abridged text:** Name Schema now says 680 A.G., and the raw note on the website is corrected too (`content/fixes.json`). Legacy is unchanged.

### W4. What does Δ mean in the season tables? (answered)
- **Asked:** 2026-11-21
- **Legacy text:** Seasons: columns "Δ0km … Δ8km", and "\*If close to water like Sanbi Kingdom. If not, treat like Δ1km".
- **Why:** Is Δ the altitude (height above the sea), or the distance from the sea? A one-line explanation would help readers.
- **Answered:** 2026-11-21
- **Answer (verbatim):**
  > Height above the sea.
- **Change to the abridged text:** Added before the tables: "Δ is the height above the sea."

---

## Gaps filled from other Legacy sources

| Abridged text | Raw note | Source |
|---|---|---|
| Distance, weight, volume, time and temperature units | "can be found on the World Calendar & UOM" | `Spreadsheets/World Calendar & UOM.xlsx` › UOM |
| The table of half timehunks with clock times | (the Time Keeper images) | Same sheet, Daytime and Nighttime |
| Adrian is a courtroom scientist | "Adrian (the same one who helped create the calendar)" | World Timeline.md, 650 A.G. (Adrian From North Tolerideme) and the public Time & Calendar page |
| Forrday is the 5th day and the weekend | "ForrDay: 1st day of the week." | Public Time & Calendar page ("declared the end of the week (weekend)"); Vol 1 ("the weekend, Forrday"); the calendar spreadsheet lists it 5th |
| Freeday is a work day | "They get the first day of the working week" | Same doc |
| "the Four Kingdoms map … its metadata map … in the art on this page" | "See the Four Kingdoms Map" / "See Four Kingdoms Metadata Map" | `Illustrations/World Map/` (World Map (Final).png, World Map Metadata.png) |

## Discrepancies

### Forrday listed as the 1st day (settled)
- **Sources:** this doc ("1st day of the week") vs the public page, Vol 1 and the spreadsheet (5th, the weekend).
- **Settled by:** the published novel (Vol 1), which wins over the rest of Legacy.
- **Abridged text:** Forrday is the 5th day, the weekend.

### Sorebone weight (settled)
- **Sources:** `World Calendar & UOM.xlsx` labels Sorebone "Gram" with 0.01 kg, and Tiny Sorebone "Miligram" with 0.001 kg. No novel mentions either.
- **Settled by:** the author's decision (W2): Sorebone is 10 g, Tiny Sorebone 1 g.

### Prosperity Treaty year (settled)
- **Sources:** Name Schema (671 A.G.) vs World Timeline (680 A.G.). No novel gives the year.
- **Settled by:** the author's decision (W3): 680 A.G.

### Whose units (settled)
- **Sources:** this doc (Blood) vs the public Economy & UOMs page (Tolerideme).
- **Settled by:** the author's decision (W1): both are true in part. The accuracy comes from Tolerideme (Adrian's home); the names come from his hunting near Blood.

## Left out on purpose

- The repeated line "City of origin or main residence." (written twice in Name Schema).
- The bold on every line (the whole doc is bold in Legacy).

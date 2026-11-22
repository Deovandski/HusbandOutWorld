# Fauna: abridgement Q&A (proof of work)

- **Raw (Legacy):** `Legacy/Behind The Scenes/World Lore/Fauna.md` (unchanged)
- **Abridged (website):** `content/bts/World Lore/Fauna.md`
- **Issue:** #103

Every question asked of the author and his answer (word for word), every gap filled from elsewhere in Legacy (with its source), every discrepancy and how it was settled, and what was left out. Source order: (1) the author's decision, (2) the published novels, (3) the rest of Legacy.

**Polish (the author's standing instruction, 2026-11-22: "Polish grammar, typos always."):** the descriptions and fact lines were then polished for grammar and typos (e.g. "Butcher cut meat" → "Meat cut by a butcher", "Freish" → "Freeish", "Hippothamus" → "Hippopotamus").

**How this one was abridged:** the nature docs (Fauna, Flora, Beasts) all follow one template, so each entry was restructured into the same readable layout, with the author's wording kept: the Isekai History as a short description, then a list of facts (Inspired by, Habitat, Tastes like, Food, Intelligence, Reproduction, Interface, Skills, and any other fields), then the products under "Economic value" with their pictures. "Scientific History" is labeled "Inspired by". Empty values ("None", "-", "See above") and the Website Description (the public text, already shown on the page) are left out. Documentation Notation and Distance Cost Tier stay as written. Every picture in the doc is kept.

---

## Questions for the author

Status: **open** until answered. Asked as one batch on 2026-11-22 and answered the same day.

### N1. Monica or Monika? (answered)
- **Asked:** 2026-11-22
- **Legacy text:** Fauna: "Monica"; Beasts: "Monica Swarm"; Science - Nari Gels: "Monika Sight".
- **Why:** Which spelling is right? I can make the website consistent.
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > Monica is the right one, but some people, usually freeish and around it, also spell it out with K instead.
- **Change to the abridged text:** Monica everywhere in the abridged text (Beasts' swarm now says "Monica butterflies"); the Monica entry adds "some people, usually in and around Freeish, spell it Monika". The Nari Gels list keeps "Monika Sight" (the Freeish spelling).

### N2. Egua loads (answered: proposal written, decision pending)
- **Asked:** 2026-11-22
- **Legacy text:** Gait table: "5km @ ~10% Load (Max Load of ~90 kilos)", "~20% Load (Max Load of ~180 kilos)". Tamed Child Egua: "smaller loads (~0.4x load ~ 240kg.)". Economy spreadsheet: "Egua Cargo Pull Limit 150 kg", an adult Egua weighs 900 kg.
- **Why:** How do these fit? (Is the % of the Egua's 900 kg body weight it can carry on its back, with 150 kg the cart it pulls? And is a child's 240 kg 0.4 of an adult's 600 kg?)
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > I did this without any AI research back in the day trying to base it off horses... Do the research and make a formal proposal to streamline line this calculation. And % of the egua was meant to put into perspective how much weight was the egua pulling... More weight, more strain. Going faster, more strain as well.
- **Change to the abridged text:** None yet. The proposal is in `content/bts/qa/World Lore/Fauna - Egua load proposal.md`, waiting for the author's decision.

### N3. Legunia: desert or lower plains? (answered)
- **Asked:** 2026-11-22
- **Legacy text:** Isekai History: "Natural birds found in the deserts." Habitat: "Lower plains".
- **Why:** Both (deserts and lower plains)?
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > dessert most of their life, approaches lower plains for breeding season.
- **Change to the abridged text:** "Birds native to the deserts, where they spend most of their lives; they come down to the lower plains for the breeding season."

---

## Gaps filled from other Legacy sources

None.

## Discrepancies

Settled in N1, N2 and N3, and the Ptaina question below.

### N2 answer: the Egua load rule
- **Asked:** Option A (pack Eguas only) or B (carts everywhere), and should the strain rule appear on the Egua entry? See [Fauna - Egua load proposal.md](Fauna%20-%20Egua%20load%20proposal.md).
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > N2: We can have both. Some roads they can use carts others not. Plus there are other fees into shipping not discussed like protection fee, insurance, profit etc that will cover the gap now that shipping is less expensive as the éguas can pull a lot more when pulling carts.
  >
  > So from distance cost tier it is basically the same as we can explain the cost away, and we're just updating the calculations that led to that tier calculation.
- **Change to the abridged text:** the Egua entry gets a "Load and strain" section (the strain rule, the gait table as the 10% and 20% columns, and the 0.4 rule for children), since the author is "updating the calculations". The Economy shipping note explains both pack and cart routes and the extra fees (see the Economy Q&A).
- **Made official** (2026-11-22, the author: "Also for egua load with the new calculation."): `content/fixes.json` adds the strain rule under the raw gait table and the new child loads to the raw Tamed Child Egua note. The `Formulas - Economy.xlsx` spreadsheet (150 kg of cargo) can't be corrected on the website; the Economy note explains it as pack cargo.
- **Superseded:** Tamed Child Egua, "~0.4x load ~ 240kg": the strain rule gives a child ~360 kg of body weight, ~36 kg comfortable on its back and ~72 kg at most, so the abridged line points to Load and strain instead of 240 kg.

### Ptaina reproduction
- **Legacy text:** Ptaina › Reproduction: "Tens of Sanbies per year." (the same line as the Sanbi entry)
- **Asked:** Is it copied? How many Ptaina a year?
- **Answered:** 2026-11-22
- **Answer (verbatim):**
  > And for Ptainas. It was supposed to say "hundreds of Ptainas per year but most become food for other fish along the way"
- **Change to the abridged text:** "Hundreds of Ptainas per year, but most become food for other fish along the way."
- **Made official** (2026-11-22, the author: "Make that official for ptainas."): the raw note's display is corrected in `content/fixes.json`.

## Left out on purpose

- The Website Description of each entry (the public text, already on the page).
- Empty values ("None", "-", "--", "See above", "See Item Visual Reference").

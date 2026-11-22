# Proposal: one way to calculate Egua loads (Fauna, question N2)

- **Status:** proposal, waiting for the author's decision. Nothing on the website uses it yet.
- **Asked for by the author (verbatim, 2026-11-22):**
  > I did this without any AI research back in the day trying to base it off horses... Do the research and make a formal proposal to streamline line this calculation. And % of the egua was meant to put into perspective how much weight was the egua pulling... More weight, more strain. Going faster, more strain as well.

## What Legacy says today

| Source | Numbers |
|---|---|
| Fauna › Egua › Other (gait table) | Gallop ~30 km/h: 5 km at ~10% load (max ~90 kg). Canter ~20 km/h: 15 km at 10%, 5 km at 20% (max ~180 kg). Trot ~10 km/h: 35 km at 10%, 15 km at 20%. Gait (walk) ~7 km/h: 65 km at 10%, 35 km at 20%. |
| Fauna › Tamed Child Egua | "smaller loads (~0.4x load ~ 240kg)" |
| Fauna › Egua › Alimentation | ~20 kg of grass, hay or Carbey a day |
| `Formulas - Economy.xlsx` › Distance Cost Calculator | Egua cargo pull limit 150 kg ("*30kg for rider, etc"); 65 km a day ridden, 30 km a day with cargo |
| `Formulas - Economy.xlsx` › BeastFauna calculator | An adult Egua weighs ~900 kg |

The 10% / 20% in the gait table is already a share of the Egua's ~900 kg body weight (10% = 90 kg, 20% = 180 kg).

## Real-world anchors (horses)

| Fact | Source |
|---|---|
| A horse should carry at most about 20% of its body weight (rider, tack and gear together); loads of 25–30% raise heart rate, lactate and muscle soreness | US Cavalry guideline and later studies (ker.com; chewy.com; Journal of Equine Veterinary Science, 2008) |
| On a wheeled cart, a horse can pull about 1.5 times its body weight over long distances; dead weight (a log, a sled), only about a tenth | horserookie.com; pangovet.com |
| Draft animals can hold a pull (tension in the chain) of 10–12% of their body weight all day | Tillers International, tillage draft guide |
| Pulling a wagon takes a force of about 4% of its total weight on a good, hard road, up to 16% on soft ground | Tillers International, wagon draft guide |
| Walk ~7 km/h, trot ~13–14 km/h, canter 16–27 km/h, gallop ~48 km/h; an average horse covers 40–56 km a day with a rider | Wikipedia (Horse gait); deephollowranch.com; strathornfarm.co.uk |

## The proposal: one number, "strain"

**Strain** is the share of the Egua's own body weight (~900 kg for an adult) that it's working against. More weight means more strain, and so does going faster.

1. **Carrying on its back:** strain = load ÷ 900 kg.
   - Up to 10% (90 kg): comfortable all day.
   - Up to 20% (180 kg): the maximum.
   - Over 20%: injury territory, not sustainable.

   This is exactly the gait table you already have.

2. **Pulling a cart:** strain = (cart + cargo + driver) × road factor ÷ 900 kg.
   - Road factor: **0.05** on a good, hard road (Forway's main roads); **0.10** on a dirt road; **0.15** on soft ground, mud or sand.
   - The same limits apply: up to 10% strain all day, 20% at most.
   - Example: on a dirt road, a full day at 10% strain means about **900 kg of cart, cargo and driver** (900 × 0.10 = 90 kg of pull). On a good road it's about 1,800 kg; in sand, about 600 kg. That lines up with the real 1.5× body weight figure.

3. **Speed and distance:** keep your gait table as the 10% column. At any other strain, the distance a day scales inversely:

   **distance a day ≈ table distance at 10% × (10% ÷ strain)**

   So at 20% strain, the distance is about half: your table already does almost exactly that (65 → 35 km, 35 → 15 km, 15 → 5 km). At 5% strain, the walk would stretch toward ~120 km, but cap it at your 65 km (the Eguas still need ~20 kg of food a day, and rest).

4. **Child Eguas:** a child weighs about 0.4 of an adult, so everything scales by 0.4: about 360 kg of body weight, 36 kg comfortable on its back, 72 kg at most, and 0.4 of an adult's cart load. The current "~240 kg" would then be a child's cart load on a dirt road at about 7% strain (240 × 0.10 ÷ 360).

## What it would change, and a decision for the author

- **The Fauna gait table:** no change. It becomes the "10% and 20% strain" table, with the formula for anything in between.
- **The child Egua line:** could read "about 0.4 of an adult's loads (~360 kg body weight)".
- **The Economy spreadsheet** is the one real conflict: its 150 kg cargo pull limit (at 30 km a day) is far below what the strain rule allows for a cart (~900 kg on a dirt road). Two ways to settle it:
  - **Option A (recommended): keep the economy as it is.** Read the 150 kg as cargo carried by a pack Egua (about 17% strain, close to the 20% maximum) on Vraki's long, rough routes, with no cart. Shipping prices stay balanced as they are today.
  - **Option B: carts everywhere.** Use the strain rule for carts, so one Egua moves ~900 kg on a dirt road, about 6 times the cargo. Shipping would get about 6 times cheaper, and every Distance Cost Tier number would need recalculating.

Questions for the author: Option A or B? And should the website explain the strain rule on the Egua entry, or keep it as a note for writers here?

## The author's decision (2026-11-22)

> N2: We can have both. Some roads they can use carts others not. Plus there are other fees into shipping not discussed like protection fee, insurance, profit etc that will cover the gap now that shipping is less expensive as the éguas can pull a lot more when pulling carts.
>
> So from distance cost tier it is basically the same as we can explain the cost away, and we're just updating the calculations that led to that tier calculation.

- **Both:** pack Eguas on routes where carts can't go, carts where the roads allow them.
- **Distance Cost Tier:** prices stay the same. Cheaper hauling by cart is balanced by the other shipping fees (protection, insurance, profit).
- **On the website:** the strain rule is on the Egua entry (Fauna › Egua › Load and strain), and the Economy shipping note explains the two kinds of route.

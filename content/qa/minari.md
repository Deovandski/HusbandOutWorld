# Minari: sources, questions and answers (issue #131)

Proof of work for the Minari game on the Playground (`/playground/#minari`). What the series says comes first, then Deo's answers word for word, then what was set for the game and why. The numbers themselves are in `content/minari.json`, each with a `_why`.

## What Legacy says
- **World Lore, Sports, Games and Passtime › Minari** (`Legacy/Behind The Scenes/World Lore/Sports, Games and Passtime.md`): it started with wooden-carved statues and evolved with age. One statue of a group is the true version, the one with the nari stone inside, and the goal is to eliminate it. The table is carved and 3D, with plug-and-play pieces. It's like Gwent, but with statues bound with nari stone, and Soul Energy reflects their powers: carved pieces instead of cards.
- **Vol 1, Chapter II (2.3)**, line 323: in the southeast tower, "a two-person table with its top partly carved, looking like a three-dimensional painted wooden battlefield of sorts, containing clusters of statues on top, each forming battalions of humanoids, animals, or even monsters", and a bookcase of spare figures, statues and "additional boards that looked like pieces of battlefield".
- **Vol 1, Epilogue (7.1)**, line 1134: Neferteri: "I cannot control every piece in a Minari game."
- **Vol 2, Chapter I (1.2)**, line 117: the same room, "a familiar mix of a parlor and game room located on the southeast corner". The game itself isn't described.
- **Vol 3, Chapter II (2.3)**, lines 416 and 434: Arukia feels "the fog of war wane away" as "more pieces of the Minari game were revealed".
- **Vol 3, Chapter IV (4.1)**, line 611: "her mind was always playing a game of Minari on its own, but instead of carved pieces of wood, it was the Sanbi Royals. But which one held the truth?"
- **Arc #2 notes, Book 6 Ch 3**, line 317: Eori and Maiara play "the Gwent-like game" in the castle parlour; "They play the final round, and Maiara wins"; each throws down "what she had on hand".
- **Arc #4 notes**, line 593: Book 15 is titled "A Game of Minari" (the title only).
- Not in the old blog, the spreadsheets or the other World Lore docs. No piece names, counts, board size, turn order or scoring anywhere.

## Questions and Deo's answers (2026-11-23, on #131)
Q1 Which creatures are statues? Q2 Who plays? Q3 Is there a power scale in Legacy? Q4 What does "Soul energy to reflect statue powers" mean in play? Q5 Dialogue? Q6 Old and new statue styles? Q7 What are the plug-in board pieces?

> 1) only races faunas and beasts.
>
> However we can take this opportunity to add Flora to the mix. They're not going to be wood sculptures like the rest, but rather act as a base. They would add add advantages or disadvantages to the piece above.
>
> 2) And this gimmick the user is going to play against the machine.
>
> We can have three levels. Against Nina is going to be easy. Against Aurora it's going to be medium. Against Neferteri would be challenging.
>
> 3) In regards to this game? No. There's not much set in stone even as to what exactly how the turns are played out and what pieces have in terms of benefits Or disadvantages.
>
> 4) I was thinking more in terms of the wood piece itself representing a given animal tells the strength.
>
> This game is based off Gwent, but instead of cards, it would be wood sculptures.
>
> 5) no dialogue. We're not making an on rails experience but rather trying to build more of working prototype of the game.
>
> 6) painting the pieces does not provide benefits. It's just plain customizatiin.
>
> 7) fauna basis on top of the terrain provides bonuses. But also the terrain itself.
>
> Different terrains with squares determine the bonuses like terrain height difference, terrain type. This is taking a bit of the color system from MTG, but adding terrain height as a differentiator.

Q8 Does "fauna basis" mean the flora bases? Q9 Where do the terrain types come from? Q10 Who sets the numbers?

> 1) yes.
> 2) base on the world lore, and world map.
> 3) you do it. Use all the world lore and the numbers there as reference but for this game you can tweak as needed if rebalance is necessary.
>
> Also each player starts with a specific number of pieces, and they decide which one holds the thing inside of it (the thing being the nari stone or whatever thing the other player is trying to get by killing the pieces until the discover it)

## What was set for the game (Claude, per Q10)
- **Statues:** 43 entries from Races, Fauna and Beasts. Power 1 to 9 from each creature's size, danger and Soul Energy skills. Home terrains come from its Habitat. Traits come from its skills: Flying (flight, high jump, air), Armor (harden skin, shells, carapace), Shield (air or blood shield, hypnosis, black-flame falls), Cloak (cloak, fake body, transmogrify). Left out: entries with no details ("?": Teefyro, Crazed Muckman, Sucker Lady) and the placeholder names (Hash {X}, Walking {X} Flesh/Skin).
- **Rebalanced:** the strongest creatures were capped to keep the game playable. Nari Worms are 9 rather than "huge", and Buhraies and Finaies are 9 and 8.
- **Flora bases:** 15 entries. Each effect comes from what the plant does in the lore, for example Magina is a sedative (−2 to the strongest opposing statue), Rakuja only grows high up (+3 at height 2), and Hifuna Yabuca is "the random fruit" (−2 to +3).
- **Terrain:** six types from the Lands and the world map: plains, forest, water, desert, snow and Hifuna. Heights 0 to 2 follow the altitudes in Flora (~0, ~1-2, ~2-4 km) and the Buhraies Plains' 2 km cliff. Each round's table is one of the 13 Lands, laid out from that land's mix.
- **Rules:** 10 statues and 4 bases each, 5 lanes, up to 3 statues per square. +2 on home terrain, ±1 per height level against the square across (flyers ignore being lower). Best of three rounds, and finding the stone wins at once.
- **Opponents:**
  - Nina (easy) plays at random.
  - Aurora (medium) plays the best move she can see and keeps her stone back until her last three pieces.
  - Neferteri (challenging) weighs what each piece costs, saves pieces, sometimes passes an early round on purpose, and hides her stone in one of her three smallest statues.

# Glossary: abridgement notes (proof of work)

Issue #103 scope: "Glossary: BTS and public glossary entries".

The Glossary isn't a Legacy doc of its own: the build makes it from every World Lore entry (`build_glossary` in tools/build.py), with a one-line description for each term.
- **Public terms** keep their description from the public text (the old blog), in the author's words. Unchanged.
- **Behind the Scenes terms** used to take their description from the raw notes. They now take it from the abridged text (content/bts/World Lore), so they read as polished sentences; list items become sentences ("Hardness: 7. Where it comes from: …"). Entries with no abridged text still fall back to the raw notes.
- The Glossary page now says, in Behind the Scenes mode: "Behind the Scenes descriptions come from the abridged notes, written with the help of AI; each entry keeps the original notes."
- `llms` and Markdown twins: the Glossary twin follows the page (abridged descriptions); each entry's own page keeps the raw notes behind "Show the original notes".

No questions for the author: every description comes from an abridged entry he has already reviewed through its own doc's Q&A.

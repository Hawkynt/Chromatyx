# Agent guide — Chromatyx

Working agreement for **all** coding agents and human contributors working in
this repository. These rules are not optional. The full house spec lives in
the `Hawkynt/project-template` repo (`STANDARD.md`); this file is the
per-repo distillation.

## What this is

A **print-and-play card game** (creative content + tooling): the deck lives
in `Cards.xlsx`, Python scripts (`Scripts/`) validate and localize it,
nanDECK renders the print sheets, and the bilingual rulebooks
(`Rulebook.de-DE.md`, `Rulebook.en-US.md`) are built to PDF via pandoc/typst.
Tests are pytest (`Tests/`), including translation-parity and
deck-consistency checks.

## Commits

- **Group changes semantically/logically** — one concern per commit (one
  card-balance change, one rulebook section, one script fix).
- **Every subject line starts with a prefix**: `+` added · `-` removed ·
  `*` changed · `#` bug fixed · `!` critical todo.
- Never start a subject with "fix"/"bugfix"/"changed"/"modified".
- **No AI traces anywhere**: no `Co-Authored-By` AI lines, no "Generated
  with" footers, no agent mentions in messages, comments, or authorship.

## The loop (always, in this order)

1. **Before committing**: `python -m pytest Tests` until green (what CI
   runs). Rulebook edits must keep **translation parity** — change both
   languages in the same commit, the parity test enforces it. Deck edits go
   through `Cards.xlsx` + `validate_deck.py`, never hand-edited render
   output. `CHANGELOG.md` is generated — never edit it by hand.
2. **Commit** (rules above) and **push**.
3. **Wait for CI**; on `main` a green CI triggers the nightly (prerelease +
   GFS prune). Fix and loop until everything is green.

Stable releases are **manual** (`gh workflow run release.yml`) — never cut
one unless explicitly asked.

## README & repo conventions

- Standard frame: title → badges → one-line `>` blockquote; fixed emoji
  mapping for the standard sections (`## 📦 Install`, `## 🚀 Usage`,
  `## ✨ Features`, `## 🛠️ Building`, `## ❤️ Support`, `## 📜 License`).
- License is **CC BY-NC-SA 4.0** (creative content, not code) — the license
  badge is hardcoded because GitHub doesn't detect CC licenses; don't swap
  either for a software license. The `## ❤️ Support` section and
  `.github/FUNDING.yml` stay intact.

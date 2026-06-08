# Chromatyx

[![License](https://img.shields.io/badge/License-CC--BY--NC--SA--4.0-blue)](https://github.com/Hawkynt/Chromatyx/blob/main/LICENSE)
[![Language](https://img.shields.io/github/languages/top/Hawkynt/Chromatyx?color=8957D5)](https://github.com/Hawkynt/Chromatyx)

[![CI](https://github.com/Hawkynt/Chromatyx/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Hawkynt/Chromatyx/actions/workflows/ci.yml)
![Last Commit](https://img.shields.io/github/last-commit/Hawkynt/Chromatyx?branch=main)
![Activity](https://img.shields.io/github/commit-activity/m/Hawkynt/Chromatyx)

[![Stars](https://img.shields.io/github/stars/Hawkynt/Chromatyx?color=FFD700)](https://github.com/Hawkynt/Chromatyx/stargazers)
[![Forks](https://img.shields.io/github/forks/Hawkynt/Chromatyx?color=008080)](https://github.com/Hawkynt/Chromatyx/network/members)
[![Issues](https://img.shields.io/github/issues/Hawkynt/Chromatyx)](https://github.com/Hawkynt/Chromatyx/issues)
![Code Size](https://img.shields.io/github/languages/code-size/Hawkynt/Chromatyx?color=4CAF50)
![Repo Size](https://img.shields.io/github/repo-size/Hawkynt/Chromatyx?color=FF9800)

[![Release](https://img.shields.io/github/v/release/Hawkynt/Chromatyx)](https://github.com/Hawkynt/Chromatyx/releases/latest)
[![Nightly](https://img.shields.io/github/v/release/Hawkynt/Chromatyx?include_prereleases&sort=date&label=nightly&color=FF9800)](https://github.com/Hawkynt/Chromatyx/releases)
[![Downloads](https://img.shields.io/github/downloads/Hawkynt/Chromatyx/total)](https://github.com/Hawkynt/Chromatyx/releases)

> A print-and-play color-shedding card game in the spirit of UNO, themed around the solar system: twelve colors mapped to celestial bodies across 266 cards, all defined in a spreadsheet and rendered into a printable PDF with nanDECK — so the deck can be tweaked in Excel and a fresh print sheet falls out of CI.

![Chromatyx logo](Logo.png)

## 📦 Install

Grab the card deck (`Chromatyx-de-DE.pdf` / `Chromatyx-en-US.pdf`) and the
matching rulebook (`Chromatyx-Rulebook-de-DE.pdf` / `Chromatyx-Rulebook-en-US.pdf`)
and print them — no software needed to play:

- **Stable:** the [latest release](https://github.com/Hawkynt/Chromatyx/releases/latest) (tagged `vyyyyMMdd`).
- **Nightly:** the newest [`nightly-yyyyMMdd` prerelease](https://github.com/Hawkynt/Chromatyx/releases), published automatically whenever CI passes on `main`.
- **Bleeding edge:** every CI run uploads the rendered PDFs as the `Chromatyx-PrintAndPlay` artifact.

## 🚀 Usage

Print the PDF **double-sided, flipping on the long edge**, on A4 (300 DPI,
9 cards per sheet, 56 mm × 87 mm each) and cut along the crop marks. The
pages alternate card fronts and matching card backs — back positions are
already mirrored so every card lines up after the flip.

## ✨ Features

Every color is a celestial body with its own astronomical symbol:

| ☉ | ☿ | ♀ | ⊕ | ☾ | ♂ | ♃ | ♄ | ♅ | ♆ | ♇ | ★ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sun | Mercury | Venus | Earth | Moon | Mars | Jupiter | Saturn | Uranus | Neptune | Pluto | Star |
| Yellow | Purple | Pink | Green | Gray | Red | Orange | Brown | Cyan | Blue | Black | White |

The 265 playing cards (plus the card back) fall into four groups:

| Type | Cards | What they do |
| --- | --- | --- |
| **Normal** | 102 | Digits 0–9 in the planet colors. |
| **Action** | 66 | 🔄 Reversal (play direction turns around), 🚫 Block (next player skips), 🔂 Repeat (take another turn), ❄️ Freeze (color is locked for a full round), 🔥 Burn (color is banned until the next round), 🎯 Focus (choose the next player). |
| **Trap** | 61 | +2 / +3 draw penalties and 🌈 Prisma wildcards (choose a color), including combined traps such as Prisma +4, Prisma Block and Prisma Reversal. |
| **Guard** | 36 | 🛡️ Shield (cancels all effects), Mirror (effects hit the previous player), Guard Focus (effects hit a player of your choice) and −3 / −4 discards. |

All card data lives in [`Cards.xlsx`](Cards.xlsx) (deck list, colors, effects
and a localization sheet); [`Game.nde`](Game.nde) is the nanDECK script that
lays the cards out. The rules are authored as markdown
([`Rulebook.de-DE.md`](Rulebook.de-DE.md) / [`Rulebook.en-US.md`](Rulebook.en-US.md))
and converted to PDF during the build.

Status:

- [X] Card layout and artwork
- [X] Complete deck data (266 cards)
- [X] Automated validation, builds and releases
- [X] English card texts (generated from the localization sheet)
- [X] Duplex print layout (mirrored backs on alternating pages)
- [X] Rulebook (markdown sources in German and English, built to PDF)

## 🛠️ Building

```bash
# static checks: deck script, card data and their cross-references (no render)
python Scripts/validate_deck.py Game.nde

# run the test suite
python -m pytest Tests

# generate the English card data from the localization sheet
python Scripts/localize.py en-US

# render the print-and-play PDFs (downloads portable nanDECK on first run)
pwsh Scripts/render.ps1 -OutputFile Chromatyx-de-DE.pdf
pwsh Scripts/render.ps1 -DataFile Cards.en-US.xlsx -OutputFile Chromatyx-en-US.pdf

# build the rulebook PDFs (pandoc + typst, downloaded on first run)
pwsh Scripts/build_rulebook.ps1 -MarkdownFile Rulebook.de-DE.md
pwsh Scripts/build_rulebook.ps1 -MarkdownFile Rulebook.en-US.md
```

Rendering needs Windows (nanDECK is a Win32 application); validation and tests
run anywhere. Alternatively open `Game.nde` in the
[nanDECK](https://www.nandeck.com) GUI and build the deck from there. The
pipeline is documented in [`.github/workflows/`](.github/workflows/README.md).

## ❤️ Support

If this project saves you time or money, consider supporting its development:

[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsor-EA4AAA?logo=githubsponsors)](https://github.com/sponsors/Hawkynt)
[![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal)](https://www.paypal.me/hawkynt)

## 📜 License

Licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — see [LICENSE](LICENSE).

Give credit to ***Hawkynt*** when using; non-commercial use only, and
adaptations must be shared under the same license.

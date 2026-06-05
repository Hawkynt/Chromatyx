# Changelog

## v20260605 (2026-06-05)

### Added
- rulebook PDFs built from markdown via pandoc and typst, pinned portable tools, shipped with every build (52ca56b)
- rulebook drafted in German and English with translation-parity and deck-consistency tests (449870e)
- English deck generation from the workbook's localization sheet, nanDECK never recalculates the built-in language switch + render wrapper accepts a data file override by patching LINK into a temporary script copy (e428635)
- duplex print layout, pages alternate fronts and position-mirrored backs for long-edge double-siding + validator rejects CARDS combined with DUPLEX as nanDECK forbids it (6be276f)
- nanDECK download verified against a pinned SHA-256 before extraction (d838271)

### Changed
- pipeline renders and ships both de-DE and en-US duplex PDFs * README covers localized downloads and double-sided printing (622863a)

## v20260605 (2026-06-05)

### Added
- standard CI/nightly/release pipeline rendering the print PDF via nanDECK + changelog automation and GFS-pruned nightly prereleases + community health files, issue templates and editorconfig (324c168)
- static deck validator cross-checking Game.nde against Cards.xlsx + pytest suite covering directives, expressions, colors, file references, labels, icons and card data (3dd51f1)
- white corner text (d01cb8d)
- logo (143158c)
- demo data (a7ad7b3)
- messing with alpha (fa0aff7)
- card icons (1af9725)
- celestial symbol (4a77ded)
- i18n (fbee715)
- icons vs icontext (071ddb4)
- copyright notice (7755ff8)
- prepared icons (8b1848f)
- layered face (2274611)
- new background (7dff07f)
- transparency (a4a637d)
- showing faces and colors (e182be4)
- more formulas (55dac20)
- card faces (6f18973)
- readme (debe2aa)
- nde file for nanDECK (26077ab)
- some card graphics (ab58f00)
- cards (2ae734f)

### Changed
- README reshaped to the house standard with generated badge block (2bb92db)
- rename to README.md and standardize the badge block to the house style; drop vanity scope numbers (5055b09)
- overpowered +4 reduced to +2 (f9bed37)
- artwork (ebeb753)
- text resizing (9ea584c)
- face is no longer the background layer + effect/description (f545e99)

### Fixed
- nanDECK download hardened with retries and a fallback mirror against runner-side network failures (b26c2d2)
- absolute LINK path made repository-relative so the deck builds on any machine * demo limit CARDS=25 dropped, the full 266-card deck renders again (16666ef)
- positioning (c640846)
- top/bottom not symmetrical (0712a9d)
- inter-table links (a8e1d25)

### Other
- Add files via upload (3e9ffdf)

All notable changes are recorded here. This file is maintained automatically by
`.github/workflows/scripts/update-changelog.mjs`, which bucketises commits by
their prefix (`+` added, `*` changed, `-` removed, `#` fixed).

## [Unreleased]

- Initial repository setup.

# CI/CD Pipeline — Chromatyx

> Everything in this folder is the automated pipeline for this repository.
> Workflows live here, their helper scripts live in `scripts/`.
>
> This is the Hawkynt standard quartet, instantiated for a nanDECK card-game
> repo: there is no compiler — "build" means rendering the print-and-play PDF,
> "test" means the validator's pytest suite plus a static cross-check of
> `Game.nde` against `Cards.xlsx`.

## What this does

Three workflows, one shared build block, three helper scripts:

| File                            | Trigger                             | Purpose                                     |
|---------------------------------|-------------------------------------|---------------------------------------------|
| `ci.yml`                        | push + PR + `workflow_call`         | Tests + deck validation (ubuntu + windows) + render smoke-test |
| `release.yml`                   | **manual dispatch**                 | Render + publish, then tag `vyyyyMMdd`      |
| `nightly.yml`                   | successful CI run on `main`         | Publish `nightly-yyyyMMdd` prerelease       |
| `_build.yml`                    | `workflow_call` (internal)          | Renders the duplex print PDFs (de-DE + en-US) |
| `scripts/version.pl`            | (kept for template parity)          | No package manifests here, so it stamps nothing |
| `scripts/update-changelog.mjs`  | invoked by the workflows            | Bucketise commits into CHANGELOG.md         |
| `scripts/prune-nightlies.mjs`   | invoked by the workflows            | 3-gen (GFS) retention of nightlies          |

## How it works

```
                push / PR
                    │
                    ▼
            ┌───────────────┐
            │    ci.yml     │──► pytest + validator on ubuntu + windows
            └───┬───────┬───┘    + render smoke-test on windows
                │       │
   dispatch ────┤       │  on success on main
                ▼       ▼
        ┌──────────┐  ┌─────────────┐
        │ release  │  │  nightly    │
        │  .yml    │  │   .yml      │
        └────┬─────┘  └─────┬───────┘
             │              │
             ▼              ▼
        (both call _build.yml: nanDECK renders the de-DE + en-US duplex PDFs)
             │              │
             ▼              ▼
  publish + tag vyyyyMMdd  nightly-yyyyMMdd (prerelease)
                                │
                                ▼
                       scripts/prune-nightlies.mjs
                       (GFS: 7 daily + 4 weekly + 3 monthly)
```

## How the PDFs are built

[`Scripts/render.ps1`](../../Scripts/render.ps1) downloads the portable
[nanDECK](https://www.nandeck.com) build (cached via `actions/cache`, pinned
by SHA-256, with a fallback mirror), enables its batch mode through
`nanDECK.ini` (`enable_batch=1` — CLI actions are silently ignored without
it), runs

```
nanDECK.exe Game.nde /createpdf
```

and gates success on the resulting PDF's existence and size, because nanDECK
does not report script errors through its exit code. The nanDECK log is echoed
on failure. The deck uses `DUPLEX`/`PRINT=DUPLEX`, so pages alternate fronts
and position-mirrored backs for long-edge double-sided printing.

[`Scripts/localize.py`](../../Scripts/localize.py) generates the English deck
data (`Cards.en-US.xlsx`) by applying the workbook's own Localization sheet to
the cached cell values (nanDECK never recalculates Excel formulas, so the
workbook's built-in language switch is inert in a headless render). For a
localized render, `render.ps1 -DataFile` patches the `LINK=` line into a
temporary script copy — nanDECK offers no CLI override for the linked file and
forbids label definitions inside `IF`/`ENDIF`. The generated workbook must use
shared strings; nanDECK's reader fails on inline strings.

[`Scripts/validate_deck.py`](../../Scripts/validate_deck.py) is the fast,
render-free guard: it cross-checks the deck script and the linked spreadsheet
(directives, file references incl. casing, expressions, colors, labels vs.
columns, icon flags, card counts). Its test suite lives in
[`Tests/`](../../Tests).

## What it's for

- Every PR is tested and validated on ubuntu + windows before it can merge.
- Every merge to `main` produces a **tested** nightly prerelease of the PDF.
- A **manual dispatch** cuts a stable release from the artifact built by `_build.yml`, then tags the dated `vyyyyMMdd` Release at that commit.
- Old nightlies are auto-pruned on a **Grandfather-Father-Son** schedule.

## Why it's built this way

- **No cron triggers.** Event-driven only — CI fires on PRs, nightlies fire when CI passes on main, stable releases fire on manual dispatch.
- **Dated release markers.** The deck is data with no package manifest, so there is no version to tag; the repo-level Release/tag is the date marker `vyyyyMMdd`.
- **Release calls CI via `workflow_call`.** Calling ci.yml explicitly keeps tests and releases in lockstep with zero copy-paste.
- **Nightly builds from the `workflow_run` payload's SHA**, not branch tip — so a nightly is always a build of data CI actually validated.
- **`_build.yml` is the single packaging block**, shared by release and nightly so they never diverge. It runs on windows-latest because nanDECK is a Win32 application.
- **3-generation (GFS) retention**, not "keep last N". GFS guarantees at least one build per week for a month and one per month for a quarter.

## Scripts

### `update-changelog.mjs`

Prepends a new section to `CHANGELOG.md`. Commit-subject convention: `+` Added, `*` Changed, `#` Fixed, `-` Removed, `!` TODO, anything else → Other.

### `prune-nightlies.mjs`

GFS retention with `DAILY_KEEP=7`, `WEEKLY_KEEP=4`, `MONTHLY_KEEP=3`. Dry-run with `--dry-run`.

### `version.pl`

The shared template versioner. This repo has no package manifests, so it stamps
nothing — it is kept verbatim for parity with the other Hawkynt repos.

## Who maintains this

This is an instance of the shared Hawkynt template
(`hawkynt-standard/template`). When changing pipeline behaviour, prototype in
the template then mirror the change here.

## Release artifacts

| Artifact                                                  | Produced by          |
|-----------------------------------------------------------|----------------------|
| `app-artifacts` (`Chromatyx-de-DE.pdf`, `Chromatyx-en-US.pdf`) | release + nightly |
| `Chromatyx-PrintAndPlay` (same PDFs, smoke build)          | ci.yml (windows leg) |

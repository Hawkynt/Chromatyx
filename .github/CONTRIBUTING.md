# Contributing

Thanks for your interest in improving **Chromatyx**.

## Commits

Group changes semantically. Each commit message line starts with a prefix:

| Prefix | Meaning |
|--------|---------|
| `+` | added feature / behaviour |
| `-` | removed feature / behaviour |
| `*` | changed behaviour / public API |
| `#` | bug fixed |
| `!` | critical TODO / open issue |

## Pull requests

- CI must be green: every PR builds and tests on ubuntu **and** windows.
- Add tests for new behaviour — not just the happy path (equivalence classes,
  boundaries, error cases).
- Keep the change focused; unrelated cleanups go in their own PR.

## Local build

See the **Building** section of the [README](../README.md).

# Contributing

The repositories are private until the maintainer decides MealKit is ready and publishes them. These rules apply from then on, and to the maintainer already.

## Developer Certificate of Origin (DCO)

Contributions are accepted under the [Developer Certificate of Origin](https://developercertificate.org/). There is no contributor license agreement (CLA).
Sign off every commit with `git commit -s`, which adds a `Signed-off-by: Name <email>` line. The sign-off states that you have the right to submit the change under the repository's license (engine: MIT, documentation: CC BY 4.0, sample assets: CC0).

## Engine rules

- Follow the order of the {engine}`roadmap <docs/ROADMAP.md>` and the "postponed" table in the {engine}`decision log <docs/DECISIONS.md>`. When a decision changes, add a row to the decision log.
- Use only the answers in the {engine}`coding model <docs/CODING_MODEL.md>`. A design question that is not in its table gets a new row, agreed on before any code is written.
- OS APIs are called only in `mealkit/platform/<os>/`, graphics APIs only in `mealkit/rhi/`.
- After changing simulation, physics or network code, run `tools\mp_test.ps1` and confirm there is no desync. See {doc}`testing`.

## Adding an external library

The engine builds only deterministic simulation, lockstep networking, the renderer and the editor, and prefers finished external libraries for everything else. A runtime library must:

- be verified as deterministic if it touches the simulation,
- have a permissive license (MIT, BSD, zlib, public domain and similar),
- fit in the 5 MB budget of the shipped executable,
- be copied into `third_party/` at a fixed version.

When adding one, update {engine}`third_party/VERSIONS.txt` and `THIRD_PARTY_NOTICES.txt` together.

## Documentation

This documentation lives in its own repository (`MealKit-docs`). English is the source language and Korean is a gettext translation in `locale/ko/LC_MESSAGES/`.

- Change English and Korean in the same pull request. After editing a page, run `python tools/build.py update`: new sentences appear empty and changed sentences are marked fuzzy in the `.po` files. Translate them and remove the fuzzy flag.
- `python tools/build.py check` builds both languages with warnings as errors and fails on any untranslated, fuzzy or leftover message. CI runs the same check and a link check.
- Use the terms in the {doc}`../glossary`, which match the editor's Korean strings (`engine/res/strings/ko.txt`).
- One documentation branch per engine minor version: `master` is the latest, and `ENGINE_VERSION` must match the engine's `VERSION` (MAJOR.MINOR). Engine messages point to the documentation of their own version.
- Rules that change in the same commit as engine code stay in the engine repository: the roadmap, the decision log, the changelog, `CLAUDE.md`, the coding model with the determinism rules, and `third_party/VERSIONS.txt`. This documentation links to them instead of copying them.
- Editor screenshots are made with the editor's `--capture`, with `--lang en` or `--lang ko` for each language.

# Contributing

The repositories are private until the maintainer decides MealKit is ready and publishes them. These rules apply from then on, and to the maintainer already.

## Developer Certificate of Origin (DCO)

Contributions are accepted under the [Developer Certificate of Origin](https://developercertificate.org/). There is no contributor license agreement (CLA).
Sign off every commit with `git commit -s`, which adds a `Signed-off-by: Name <email>` line. The sign-off states that you have the right to submit the change under the repository's license (engine: MIT, documentation: CC BY 4.0, sample assets: CC0).

## Engine rules

- Follow the order of the {engine}`roadmap <docs/ROADMAP.md>` and the "postponed" table in the {engine}`decision log <docs/DECISIONS.md>`. When a decision changes, add a row to the decision log.
- Use only the answers in the {engine}`coding model <docs/CODING_MODEL.md>`. A design question that is not in its table gets a new row, agreed on before any code is written.
- The rules for the code itself (where OS and graphics APIs may be called, the determinism rules, which checks a change needs) change in the same commit as the code, so they are kept in the engine's {engine}`CONTRIBUTING.md` and the coding model, not here. The checks are explained in {doc}`testing`.

## Adding an external library

The engine builds only deterministic simulation, lockstep networking, the renderer and the editor, and prefers finished external libraries for everything else. A runtime library must:

- be verified as deterministic if it touches the simulation,
- have a permissive license (MIT, BSD, zlib, public domain and similar),
- fit in the 5 MB budget of the shipped executable,
- be copied into `third_party/` at a fixed version.

How to add one (the files it needs and the generated notices) is in the engine's {engine}`CONTRIBUTING.md`.

## Documentation

This documentation lives in its own repository (`MealKit-Docs`). English is the source language and Korean is a gettext translation in `locale/ko/LC_MESSAGES/`.

- The documentation has two parts. Pages about making a game go in the game developer guide (`getting_started/`, `manual/`, `cookbook/`, `reference/`), pages about working on the engine go in the engine developer guide (`engine_dev/`, `engine_dev/internals/`). Each section has an `index.md` that lists its pages; add a new page there.
- Module documentation will live in each module's own folder (`modules/<name>/docs/`) in the engine repository and be collected by the documentation build (stage 4 "source modules").
- Change English and Korean in the same pull request. After editing a page, run `python tools/build.py update`: new sentences appear empty and changed sentences are marked fuzzy in the `.po` files. Translate them and remove the fuzzy flag.
- `python tools/build.py check` builds both languages with warnings as errors and fails on any untranslated, fuzzy or leftover message. CI runs the same check and a link check.
- Use the terms in the {doc}`../glossary`, which match the editor's Korean strings (`engine/res/strings/ko.txt`).
- Before engine 1.0 there is one documentation branch, `master`, and `ENGINE_VERSION` must match the engine's `VERSION` (MAJOR.MINOR). Engine messages point to the latest documentation. From 1.0, each engine minor version gets its own documentation branch, and engine messages point to the documentation of their own version.
- Rules that change in the same commit as engine code stay in the engine repository: the roadmap, the decision log, the changelog, `CONTRIBUTING.md`, the coding model with the determinism rules, and `third_party/VERSIONS.txt`. This documentation links to them instead of copying them.
- Editor screenshots are made with the editor's `--capture`, with `--lang en` or `--lang ko` for each language.

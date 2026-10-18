# MealKit documentation

Source of the documentation for the [MealKit](https://github.com/KingProtea99/MealKit) engine.
Sphinx + MyST (Markdown). English is the source language; Korean is a gettext translation in `locale/ko/LC_MESSAGES/`.

## Build locally

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools\build.py html      :: _build\html\en\index.html, _build\html\ko\index.html
.venv\Scripts\python tools\build.py check --engine ..\MealKit
```

- After editing a page: `tools\build.py update`, then translate the new (empty) and changed (fuzzy) messages in the `.po` files.
- `check` builds both languages with warnings as errors, fails on untranslated, fuzzy or leftover messages,
  and compares `ENGINE_VERSION` with the engine's `VERSION` (MAJOR.MINOR).
- `tools\build.py linkcheck` checks external links.

## Branches

One branch per engine minor version: `master` is the latest (`ENGINE_VERSION` = the engine's current MINOR),
release branches are named `0.5`, `0.6`, ... Hosting on Read the Docs starts when the repositories are published.

## License

Documentation: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code examples in the documentation: MIT. See `LICENSE.md`.

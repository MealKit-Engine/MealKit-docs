# Loc

This page explains how game text tables work inside: how a string file is read, how a key is looked up, and how the build checks that the fonts can show every character.
How to write string tables is in {doc}`../../manual/assets` (section "Game text and languages"). The code is in {engine}`engine/src/mealkit/loc`.

`loc` is the first folder of the screen side. It comes after `data` and before `scene` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"), so it uses only `core` and `platform`.
`ui` and `settings` use it later. The simulation never reads text.

## String files

Each language is one file, `assets/strings/<language>.txt`, with one `key = text` line per string ({engine}`engine/src/mealkit/loc/Strings.h`):

```text
# comment
lobby.waiting = Waiting for the host ({count} waiting)
```

`readStringsFile` ({engine}`engine/src/mealkit/loc/Strings.cpp`) reads a file line by line:

- A UTF-8 byte order mark at the start is skipped.
- Spaces and tabs around the key and the text are removed. Empty lines and lines starting with `#` are skipped.
- A key starts with a letter and has only letters, digits, `.`, `_` and `-` (`validStringKey`).
- In the text, `\n` becomes a line break and `\\` a backslash. Any other backslash stays as it is.
- A line without `=` or with a bad key is reported with its line number and skipped, so one mistake does not lose the whole file.

The tools use the same function, so the game and the checks always read files the same way.

## Looking up a key

`loc::Strings` keeps two tables: the language being shown and the fallback language (the project setting `language`).
After reading, each table is sorted by key with a stable sort, and duplicate keys are removed so that **the first line with a key wins**.

`get(key)` searches the shown language, then the fallback language, with a binary search (`std::lower_bound`).
If neither has the key, it returns the key name itself and writes one warning per key. The missing key names are stored in a `std::deque`, so the reference that `get` returns stays valid while more names are added.

`format(key, {{"count", "3"}})` replaces each `{name}` in the text with the given value. A `{name}` without a value stays as it is.
Style tags such as `<1>...</1>` are not touched here; the UI reads them when it draws the text (see {doc}`ui`).

`languages()` lists the `.txt` files in `assets/strings`. The standard settings screen uses it for the language choice.

## Reloading

`Strings::update(dt)` is called every frame by the engine. Every 0.25 seconds it reads the path and write time of both files.
When one changed, that table is read again and the list of warned keys is cleared. A text edit therefore shows up in a running game without a restart.

## Font coverage check

UI fonts are baked at run time, one character at a time, from the font files in `assets/fonts` (see {doc}`ui`).
A character that no font has would simply not be drawn, so the build checks it before the game runs.

`mealkit_stringcheck` ({engine}`engine/tools/StringCheck.cpp`) is a small tool built with the engine. `mealkit_add_game` in {engine}`cmake/MealKit.cmake` runs it before the game code is built, for builds with a window:

```text
mealkit_stringcheck <stamp file> --fonts <project>/assets/fonts <project>/assets/strings/*.txt
```

1. It opens every `.ttf`, `.otf` and `.ttc` file under the fonts folder, including subfolders (for `.ttc`, the first font). A font it cannot read is a warning `STR002`.
2. If there are no fonts at all, nothing is checked (a project without game UI yet).
3. For every string line, it decodes the text after `=` from UTF-8 and asks each font for the glyph (`stbtt_FindGlyphIndex`). Control characters below U+0020 are skipped.
4. A character that is in no font is an error `STR001`, written in the MSVC format `file(line): error ...` with the first line where it appears, so the IDE can jump to it.
5. When everything is found, it writes the stamp file. The build reruns the check only when a string file or a font changes.

The tool reads the files with its own small reader instead of linking the engine library, so it can be built before the engine. Its format is the same as `readStringsFile`.

Why fonts are baked at run time instead of shipping a fixed set of 2,350 Hangul syllables is in {engine}`docs/CODING_MODEL.md` (the table "Considered but not changed").

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Sorted array with binary search | `Table::find` in `Strings.cpp` | Each table is one sorted `std::vector`, searched with `std::lower_bound`. It uses less memory than a hash map and the lookup is O(log n). |
| Stable sort and unique | `loadTable` | Sorting with `std::stable_sort` keeps lines with the same key in file order, so `std::unique` keeps the first one. |
| Fallback chain | `Strings::get` | Shown language, then the project language, then the key name. A missing translation shows the project language instead of nothing. |
| Warn once | `Impl::missing` | Each missing key is warned about once. A `std::deque` keeps references to its elements valid when it grows, so `get` can return a reference to the key name. |
| Polling hot reload | `Impl::poll` | Compares path and write time every 0.25 seconds instead of using a file watcher thread. |
| Placeholder replacement | `Strings::format` | One pass over the text replaces `{name}` with values by name, so translators can move a value anywhere in the sentence. |
| Build-time glyph coverage check | `mealkit_stringcheck` | Decodes every string from UTF-8 and checks each code point against the fonts with stb_truetype. Missing characters fail the build with a clickable error. |
| Stamp file | `mealkit_add_game` | The check writes a stamp only on success, and the build depends on the string and font files, so it runs again only when they change. |

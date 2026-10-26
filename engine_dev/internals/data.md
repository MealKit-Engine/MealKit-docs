# Data

This page explains how definition tables are read and written: the `.table` file format, row references, CSV import and export, and the content hash of tables.
`data` is the last folder on the simulation side of the layer order, after `sim` and before the view side (see "엔진 폴더 사이 의존" in {engine}`docs/CODING_MODEL.md`). It is below the game boundary (`game`), so the game, the editor, the content hash and the engine's own tables all read tables with the same functions.
How to make and edit tables is in {doc}`../../manual/assets`. The code is in {engine}`engine/src/mealkit/data`.

## Declaring a table

A table is a list of rows of one type, such as weapons, items or enemy kinds. The row type is a `MEALKIT_STRUCT`, and `MEALKIT_TABLE` registers it with a file path ({engine}`engine/src/mealkit/core/Reflect.h`):

```cpp
MEALKIT_STRUCT(PropKind) { MEALKIT_FIELD(f32, density, 200.0f, "Density"); ... };
MEALKIT_TABLE(PropKind, "tables/props.table", 0);
```

The macro defines an inline variable whose initializer adds `{row type, path, flags}` to `reflect::moduleTables()`, the list of tables of this module (the game exe or the game DLL). A game DLL hands that list to the editor through its game module.
The flag `kTableView` marks a view-only table (sounds, effects, icons). It stays out of the content hash, and the editor reads it again at once when it is changed during play.

Why tables are the answer for "many rows of the same shape" is in {engine}`docs/CODING_MODEL.md` ("같은 모양의 데이터가 여러 개").

## The file format

A table file is `assets/tables/<name>.table`. It is plain text in the same "path value" form as tuning files:

```text
# MealKit table (PropKind). Edit it in the editor's [Tables] panel or import a CSV there.
@format table 1

row crate
density 200
size 0.28 0.64

row barrel
...
```

`readTableText` ({engine}`engine/src/mealkit/data/Tables.cpp`) reads it line by line:

- Empty lines and lines starting with `#` are skipped.
- `@format table 1` is the format line that every MealKit text file has after its comment header ({doc}`../../reference/tool_contract`). A missing line means version 1.
- `row <id>` starts a new row. An id uses letters, digits, `_`, `-` and `.` only (`validRowId`).
- Every other line is a field path and its value, added to the current row.
- A row with an invalid or duplicate id is skipped with all its lines, and a warning names the line. So is a value before the first row.

**Row order is file order, and that is the row number.** Every peer reads the same file, so row numbers are the same everywhere.

The text is first read into `TableText`, which knows nothing about the row type: ids and their `path value` lines. Then `reflect::fromText` turns each row into the row type. Field names the type does not declare become warnings, not errors, so a table still loads after a field is renamed.

## Loading in a game

`data::loadTable(table)` ({engine}`engine/src/mealkit/data/Tables.h`) is the typed entry point for game `app/` code:

1. It finds the registered path of the row type in the module's table list (or uses the path given).
2. It finds the file with `findAsset("assets/" + path)`, so the lookup stays inside the project.
3. It fills a `sim::Table<Row>` with the ids and the parsed rows. A missing file gives an empty table and a warning.

The game reads its tables when a match starts and copies them into its `World` (see {doc}`sim`). The editor saves edited tables before play for this reason.

## Row references

Other data refers to a row by name with `RowRef<Row>`: a string `id` and a `u32 index`. Files and the editor show the id. After loading, `data::resolveRows(data, tables)` fills every index:

- It walks the declared fields of the data, into nested structs and arrays.
- For each `RowRef`, it finds the table with the same row type and looks the id up. It also matches the row type by name, so it still works after the game DLL was swapped by hot reload.
- An id that is not found leaves the index at `kNoRow` and adds a line like `path -> id (RowType)` to the `missing` list. An empty id means "no reference".

`sim/` code then reads rows by number. A `RowRef` holds a string, so it is never part of the simulation state. The state stores the plain row number.

## Editor tables and CSV

The editor does not know row types as C++ types. It uses `TableData`: the row type's `reflect::TypeInfo`, the ids, and one `reflect::Instance` per row. `loadTableData` and `saveTableData` read and write it through the same text form.

For spreadsheets (Google Sheets, Excel):

- `exportTableCsv` writes a header row of `id` and every field path (taken from a row with default values, so all rows give the same columns), then one line per row. Cells with commas, quotes or line breaks are quoted.
- `importTableCsv` parses RFC 4180 CSV (quoted commas and line breaks, `""` for a quote, an Excel byte order mark at the start) and **replaces** the table with the CSV contents. The first column must be `id`. Ids are checked with the same rules as table files.

## Content hash

`data::hashTables` adds every simulation table (not `kTableView`) to the content hash: its path, the row count, and each row's id and values. Fields declared with `MEALKIT_VIEW_FIELD` are left out, so view-only values in a simulation table can differ between peers.
`game::contentHash` ({engine}`engine/src/mealkit/game/GameData.cpp`) calls it, and `net::LockstepSession` refuses peers whose content hash differs (see {doc}`net`).

## Techniques used

| Technique | Where | What it does |
|---|---|---|
| Self-registration by static initializer | `MEALKIT_TABLE`, `registerTable` | An inline variable's initializer adds the table to the module's list, so a table is declared in one line next to its row type. |
| Reflection-driven parsing | `tableFromText`, `reflect::fromText` | Rows are read by declared field names, so one parser reads any row type and unknown fields only warn. |
| Two-stage parsing (untyped then typed) | `TableText`, `TableData` | The text is split into ids and lines without knowing the type, so the editor can keep a table as text while the game DLL is being reloaded. |
| Name-to-index resolution at load time | `resolveRows` | Data stores row names, and loading turns them into numbers once, so a tick never compares strings. |
| Recursive walk over field declarations | `resolveStruct`, `resolveValue` | Finds every `RowRef` in nested structs and arrays without game code. |
| Stable row numbering | file order | Row numbers are file order, the same on every peer. |
| CSV per RFC 4180 | `parseCsv`, `csvCell` | A small state machine for quoted cells, line breaks inside quotes and doubled quotes. |
| Content hashing that skips view fields | `hashTables`, `kFieldView` | Hashes only the values the simulation reads, so peers must agree on rules but not on presentation. |

# UI

This page explains how game screen UI works inside: how a `.ui` file is read, how the layout is computed, how view models and actions connect it to game code, how text and images are baked, and how a frame of UI is drawn.
How to write screens is in {doc}`../../manual/ui`. The code is in {engine}`engine/src/mealkit/ui`; the shader is described in {doc}`render`.

`ui` comes after `audio` and before `feedback` in the folder order of {engine}`docs/CODING_MODEL.md` ("Dependencies between engine folders"). It uses `loc` for text, `input` for keyboard and gamepad navigation and `render` for the atlases and the draw call.
Screens are designed in Penpot and exported to `.ui` by a plugin; until the plugin exists, `.ui` files are written by hand. Why is in {engine}`docs/CODING_MODEL.md` ("How to build game UI").

## Files

| File | Holds |
|---|---|
| {engine}`engine/src/mealkit/ui/Document.h` | The `.ui` file model (`Document`, `Node`) and the theme. |
| {engine}`engine/src/mealkit/ui/Document.cpp` | The `.ui` and theme parser. |
| {engine}`engine/src/mealkit/ui/Ui.h` | `ui::System`, the runtime that games use (`ctx.ui`). |
| {engine}`engine/src/mealkit/ui/Ui.cpp` | Bindings, layout, text shaping, input and drawing. |
| {engine}`engine/src/mealkit/ui/Atlas.h` | Fonts and images in the two UI atlases. |
| {engine}`engine/src/mealkit/ui/Atlas.cpp` | Glyph SDF baking, image loading, atlas packing. |

## The .ui format

One line is one property, `name value...`. Lines starting with `#` are comments.

- `board <name> <width> <height>` opens the root at the top of the file. Its size is the design resolution in logical units (usually 1920 × 1080).
- `frame`, `text` and `image` open child nodes, and `end` closes the last open node.
- `use <name> <component.ui>` puts the board of another file here as a frame. `set <child> <property> <value>` inside it changes a property of one of the component's nodes.
- Board-level lines: `navigation` (keyboard and gamepad move between widgets), `firstFocus <node>` and `back <action>`.
- Colors are `#RRGGBB` or `#RRGGBBAA`, or a theme token `$name` from `assets/ui/theme.ui` (`color <name> #...` and `number <name> <value>` lines). Number tokens are replaced when the file is read; color tokens are looked up when the screen is loaded.

`parseDocument` ({engine}`engine/src/mealkit/ui/Document.cpp`) keeps a stack of open nodes. A property line goes to the node on top of the stack through `applyProperty`, the same function that later applies state overrides (`on hover ...`).
Errors are collected as `file(line): message` and the parser continues, so a screen with one typo still shows. A missing `end`, a second board or a property outside a node are errors.

Components are read recursively. The nesting stops at depth 8, so two components that use each other cannot loop forever.

A file whose first line is `# MealKit UI exported from Penpot` is marked as exported, and the MkUI Designer opens it read-only.

### Nodes as a flat tree

The nodes are stored in one array in depth-first order, `[0]` is the board. Each node has its `parent` index and an `end` index: its subtree is exactly the range `[i + 1, end)`.
`computeEnds` fills `end` in one pass with a stack. With this layout, "all children of i" is a loop `c = i + 1; c < end; c = nodes[c].end`, without child lists or pointers.

## Screens and view models

`ui::System` ({engine}`engine/src/mealkit/ui/Ui.h`) holds the open screens. `open(path, layer)` loads a file; a higher layer is drawn on top and gets input first.

Game code connects to a screen in one direction only:

- `bind(screen, viewModel)` gives the screen a `MEALKIT_VIEWMODEL` value (a type description and a pointer, `reflect::View`). The game fills this value every frame from its state.
- The screen reads fields by path. A node's bindings are `visible`, `disabled` (both may start with `!` to invert), a width ratio (0..1, for health bars) and a color.
- Text may contain `{field}` or `{field:format}`. Formats are `n` (thousands separators), `n1` or `f2` (decimals), `time` (minutes:seconds) and `pct` (0..1 as percent). Enum fields show their value name. `{option}` is the current choice of the nearest select widget.
- A `list` widget repeats its first child once per element of a `MEALKIT_LIST` array. The count is the field `<name>Count` when it exists. Inside a list item, paths are looked up first in the element, then in the view model.
- Input widgets (toggle, slider, select) write their value into their own view model field and send an action. They never change game state themselves.

A path that does not exist is a binding error: it is logged once and listed on the editor's UI tab while playing and in the MkUI Designer (`info()`).

### Expanding the tree

The file's nodes are the template. Each frame works on a second array, the run-time nodes (`RNode`), made by `rebuild`: one per file node, plus one copy of the list template per list element.
When a list's count changes, the run-time array is built again. Focus, scroll position and state blending are carried over by matching the file node and the list index, so the screen does not jump.

## Layout

`prepare` computes the scale of a screen as min(viewport width / board width, viewport height / board height) × UI scale (the setting, clamped to 0.25..4). The root then covers the whole viewport in logical units, so a 16:9 design fills a wider screen without stretching.

Each node has a width and a height mode: a fixed number, `hug` (the size of its content) or `fill` (take the free space).

**Children of a node without layout** are placed by constraints, separately for each axis (`placeConstrained`):

| Constraint | Result when the parent grows |
|---|---|
| Start (`left`, `top`) | Keeps the distance to the start edge. |
| End (`right`, `bottom`) | Keeps the distance to the end edge. |
| Both (`leftright`, `topbottom`) | Keeps both distances, so the node grows. |
| Center | Keeps the offset from the center. |
| Scale | Position and size grow by the same ratio as the parent. |

**Children of a flex node** (`layout row` or `layout column`) follow a subset of CSS flexbox (`flex`):

1. Each child's size along the main axis is measured: fixed, its content size for `hug`, its minimum for `fill`. Margins are added.
2. With `wrap`, children go to a new line when the next one does not fit. `reverse` reverses the order.
3. On each line, free space is shared equally by the `fill` children, clamped to their minimum and maximum.
4. On the cross axis, children align by `alignItems` or their own `alignSelf` (start, center, end, stretch). A single line without wrap uses the whole cross size.
5. Free main-axis space is placed by `justify`: start, center, end, space-between, space-around, space-evenly. With several lines, `alignContent` places the lines in the same ways.

Content size (`intrinsic`) is measured from the bottom up: a text node from its shaped text, a flex node from its children plus gaps and padding.
Nodes marked `absolute` inside a flex node are placed by constraints instead. A hidden parent hides all its children.

A `scroll` widget moves its children by its scroll offset and records how far its content reaches, which limits scrolling.

## Text

Text is drawn from glyphs baked at run time, so any character in any font file can be shown (`Atlas.cpp`).

**Fonts** are the `.ttf`, `.otf` and `.ttc` files in `assets/fonts`, named by file name (`Pretendard-Medium`). A node names its font; an unknown name falls back to the first font.

**Shaping** (`shapeGlyphs`) decodes UTF-8, reads style tags `<1>...</1>` into runs (a `span` line gives tag 1 its font, size, color or decoration), applies upper or lower case transforms, kerning and letter spacing.
For each character, when the node's font does not have it, the other fonts are searched, so a Latin font with a Korean fallback works without extra settings.

**Line breaking** (`breakLines`) breaks at spaces. With the `syllable` wrap mode (the default) it may also break before or after any wide character (Hangul, CJK ideographs, kana and full-width forms), which is how Korean and Japanese text wraps. Spaces at the start of a new line are dropped.
With `maxLines` or a fixed height, extra lines are cut, and with `overflow ellipsis` the last line is shortened until "…" fits.
The shaped result is cached per node and only redone when the text or the wrap width changes.

**Baking** (`Atlas::Impl::bake`): a glyph is baked once, at 40 pixels per em with 6 pixels of padding, as a **signed distance field**: each atlas pixel holds the distance to the nearest outline edge, 128 on the edge.
The engine computes the field itself: it flattens the glyph outline into line segments (8 steps per quadratic curve, 10 per cubic curve), then for each pixel finds the nearest segment and decides inside or outside with the winding number.
stb_truetype's own `stbtt_GetGlyphSDF` is not used because it skips cubic curves, which `.otf` (CFF) fonts use, and round strokes would disappear.
One baked size serves every text size: the shader turns distance into coverage with a scale per glyph.

**Packing**: glyphs and images go into 2048 × 2048 atlases with a shelf packer. A glyph goes on the first shelf whose height is between 75 % and 100 % of its height, otherwise a new shelf is opened below. Each item keeps one pixel of space for linear filtering.
When the glyph atlas is full, it is cleared and glyphs are baked again as they are used (with a warning). Images are PNG files read with stb_image, placed once in the image atlas.

## Input

`System::update` runs before the game's update, every frame. It goes through screens from the highest layer down.

**Mouse**: the hit test walks the run-time nodes from the last to the first, which is the reverse of drawing order, so the topmost node wins. Nodes outside a clipping parent are skipped.
A widget under the mouse takes it. A frame with a visible fill also takes it, so clicking on a panel does not reach the game behind it.
A button is activated when the mouse is released over the same node it was pressed on. A slider follows the mouse while held. The wheel scrolls the innermost scroll area under the mouse by 60 logical units per step.

**Keyboard and gamepad** use the input actions `ui.up`, `ui.down`, `ui.left`, `ui.right`, `ui.confirm` and `ui.back` (see {doc}`input`), on the highest screen that has `navigation` and a widget to focus:

- The first direction press focuses `firstFocus` or the first widget.
- A direction moves to the node named in `focusUp` (and so on) if set, otherwise to the nearest widget in that direction: the score is the distance along the direction plus twice the sideways distance, and widgets behind are ignored.
- Left and right on a slider or a select change its value instead of moving.
- `ui.back` sends the board's `back` action.

**Text input**: activating a `textInput` node (click, confirm, or `focusText` from code) starts typing in it. While typing, that screen takes the whole keyboard: the frame's typed text (`Input::text()`, UTF-8) is appended up to `maxLength` characters, each backspace removes the last character with its UTF-8 continuation bytes, `Enter` sends the node's action and stops, and `Esc` or a click elsewhere stops. `wantsKeyboard()` stays true, so the game and the `ui.*` navigation see no keys. An empty field shows its placeholder at lower opacity; the caret is a thin bar after the last character that blinks.

The focus ring is drawn only after keyboard or gamepad use; moving the mouse hides it.
`wantsMouse()` and `wantsKeyboard()` tell the engine to hide that input from the game this frame.

`actions()` lists what widgets sent this frame: action name, screen, node name, changed field and list index. Buttons send their action; input widgets send their action or `changed`.

### States

A node can override its look with `on hover`, `on pressed`, `on focus`, `on disabled` or `on checked` lines. When the screen is loaded, the full look for each state is built in advance by applying those lines to a copy of the node.
Each frame, a blend value per state moves toward 1 when the state is active and toward 0 when it is not, at the speed 1 / `transition` seconds (default 0.1). The drawn look is the normal look blended toward each state's look, so colors fade instead of jumping.

## Drawing

`System::render` runs after the 3D scene and before the debug UI. It turns everything into one array of `render::UiQuad` and calls `Renderer::drawUi` once, so all UI is **one draw call**.

1. **World UI** first (name tags, damage numbers): the game calls `drawAt(template, worldPosition, viewModel)` while it builds the frame. The position is projected with the frame's camera; points behind the camera or outside the screen are skipped, or clamped to the screen edge when asked. The template is laid out at its own board size and scaled against 1920 × 1080.
2. **Screens** next, from the lowest layer up.

`emitNode` walks the run-time tree. For each visible node it adds, in order: shadows, the frame's fill and stroke (a rounded box with a radius per corner), the image, the text glyphs, and the focus ring. Then it draws the children.

- Opacity multiplies down the tree.
- A node with `clip` narrows the clip rectangle for its children; every quad carries its clip rectangle and the shader discards pixels outside it.
- An image with `slice` margins becomes nine quads (nine-slice scaling): the corners keep their size and the edges and middle stretch.
- Each glyph quad gets its atlas rectangle and the SDF scale for its size. Underline and strike-through are thin extra quads.

## Reloading

Every 0.25 seconds the system checks the write times of the theme, every open screen file, the fonts and the images. A changed screen is loaded again with its bindings kept; a changed theme reloads every screen.

## Techniques used

### Data and layout

| Technique | Where | What it does |
|---|---|---|
| Line-based markup with a node stack | `Parser::parse` | One property per line and `end` to close, parsed with a stack of open nodes. Errors are collected with line numbers and parsing continues. |
| Components by inclusion | `Parser::include` | `use` copies another file's nodes into the tree with a depth limit against cycles; `set` overrides properties inside. |
| Design tokens | `Theme`, `$name` | Colors and numbers are named once in a theme file and referenced by name. |
| Flat tree with subtree ranges | `Node::end`, `computeEnds` | Nodes in depth-first order with an end index: a subtree is a contiguous range, and children are found by jumping over subtrees. |
| Template expansion | `rebuild`, `buildSubtree` | List templates are repeated per array element into a separate run-time array, keeping focus and scroll by identity. |
| One-way view model binding | `bind`, `resolve` | The UI reads named fields through reflection; only input widgets write, and only into their own field. |
| Value formatting | `formatValue` | Thousands separators, fixed decimals, minutes and seconds and percent from a short format code. |
| Constraint layout | `placeConstrained` | Start, end, both, center and scale rules per axis, like design tools' constraints. |
| Flexbox subset | `flex`, `intrinsic` | Main and cross axes, wrapping, gaps, grow, alignment and justify modes. Content sizes are measured bottom up. |
| Uniform fit scaling | `prepare` | One scale from the smaller of the two axis ratios, so the design keeps its proportions on every screen. |

### Text and images

| Technique | Where | What it does |
|---|---|---|
| Run-time glyph baking | `Atlas::glyph`, `bake` | Only characters that are used are baked, so fonts with thousands of Hangul syllables cost only what is shown. |
| Signed distance fields from flattened outlines | `flatten`, `bake` | Curves become line segments; each pixel stores the distance to the nearest segment, with inside and outside from the winding number. |
| Font fallback per character | `Atlas::glyph` | A missing character is taken from another font. |
| Syllable-level line breaking | `breakLines`, `isWide` | Allows breaks between wide characters, as Korean, Chinese and Japanese text needs. |
| Ellipsis truncation | `breakLines` | Removes characters from the last kept line until "…" fits. |
| Shaping cache | `shapeText` | Keeps the shaped text until the text or the wrap width changes. |
| Shelf packing | `Shelves::place` | Rows of similar height in a fixed atlas, fast and good enough for glyphs and icons of similar sizes. |
| Rebuild on overflow | `bake` | A full glyph atlas is cleared and refilled with the glyphs in use. |
| Nine-slice scaling | `emitNode` | Splits an image into 3 × 3 parts so borders keep their size when the box grows. |

### Interaction and drawing

| Technique | Where | What it does |
|---|---|---|
| Reverse-order hit testing | `hit` | Tests nodes from last drawn to first, so the topmost node gets the click; clipped parents hide their children from the mouse. |
| Input capture between layers | `update`, `wantsMouse` | The highest screen that uses the mouse or keyboard takes it from screens below and from the game. |
| Spatial focus navigation | `neighbor` | Picks the nearest widget in a direction by distance with a sideways penalty, unless the file names the next widget. |
| Precomputed state looks with blending | `loadScreen`, `update`, `lerpVisual` | Builds each state's look once, then blends toward it over the transition time. |
| World-to-screen projection | `System::render` | Projects a 3D point with the view-projection matrix and divides by w; handles points behind the camera and clamps to edges. |
| Single batched draw | `System::render` | All screens, world UI and text become one quad array and one draw call. |
| Per-quad clipping | `emitNode`, `Ui.hlsl` | Each quad carries its clip rectangle, so clipping needs no extra draw calls or scissor changes. |

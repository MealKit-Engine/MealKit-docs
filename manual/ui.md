# Game UI

The game's screens (HUD, menus, settings) are `.ui` files in `assets/ui/`. The engine lays them out and draws them in one 2D pass after the 3D scene.
Screens are placed in the editor (see [Editing screens in the editor](#editing-screens-in-the-editor)), designed in Penpot and exported by the MealKit plugin (see [Designing in Penpot](#designing-in-penpot)), or written by hand in the same format. An exported file starts with `# MealKit UI exported from Penpot`; change those in Penpot, not by hand.

## A screen file

```text
# assets/ui/hud.ui
board hud 1920 1080
  frame scoreboard
    pos 32 32
    size 320 hug
    layout column
    padding 16 20
    gap 8
    fill $panel
    radius 12
    shadow 0 6 24 0 #00000066
    text title
      key hud.players
      fontSize 22
      color $textDim
    end
  end
end
```

One property per line. `board <name> <width> <height>` is the root, in logical units of the reference resolution. Nodes are `frame`, `text`, `image` and `use <name> <component.ui>` (another `.ui` reused as a component, with `set <child> <property> <value>` overrides), each closed with `end`.
The scale is `min(width / board width, height / board height) × UI scale`. The root stretches to the whole screen, and children stay attached through their constraints.

| Group | Properties |
|---|---|
| Position and size | `pos x y`, `size <w> <h>` (a number, `hug` to fit the content, `fill` to take the free space), `min`, `max`, `margin`, `absolute`, `constraints left\|right\|leftright\|center\|scale top\|bottom\|topbottom\|center\|scale`, `rotation`, `opacity`, `hidden`, `clip` |
| Flex layout | `layout row\|column [reverse] [wrap]`, `gap`, `padding`, `justify start\|center\|end\|space-between\|space-around\|space-evenly`, `align`, `alignContent`, `alignSelf` |
| Grid layout | `layout grid [row\|column]` (the order that fills free cells), `columns` and `rows` with tracks `200` (fixed), `1fr` (a share of the free space), `auto` (fits the content) and `25%` (of the inner size), `gap <row> <column>`, `padding`, `justify` (columns, also `stretch`: auto tracks take the free space), `alignContent` (rows), `justifyItems`, `align`; on a child `cell <row> <column> [<row span> <column span>]` (from 1), `justifySelf`, `alignSelf` |
| Look | `fill <color>` or `fill linear\|radial x0 y0 x1 y1 <color> <color>`, `stroke <width> <color>`, `radius` (one value or one per corner), `shadow <dx> <dy> <blur> <spread> <color>` (several allowed) |
| Images | `src ui/icon.png`, `slice <left> <top> <right> <bottom>` (9-slice), `tint <color>` |
| Text | `key <strings key>` or `content <text>`, `font`, `fontSize`, `color`, `letterSpacing`, `lineHeight`, `textAlign`, `verticalAlign`, `underline`, `strike`, `transform`, `wrap word\|syllable\|none`, `overflow ellipsis`, `maxLines`, `span <tag> <property> <value> ...` |
| States | `on hover\|pressed\|focus\|disabled\|checked <property line>`, `transition <seconds>` |
| Board lines | `navigation` (keyboard and gamepad focus, for menus), `firstFocus <node>`, `back <action>` |
| Other | `id <Penpot shape id>` (written by the plugin; the layout check finds nodes by it) |

Colors are `#RRGGBB[AA]` or `$token` from the theme `assets/ui/theme.ui` (`color <name> #...`, `number <name> <value>`). Text with several styles uses numbered tags from the string table, `<1>...</1>`, styled by `span 1 ...`.
Korean text breaks between syllables (`wrap syllable`, the default); `wrap word` breaks only at spaces. Characters missing from one font are taken from another font in `assets/fonts`.
Files are reloaded within a quarter second when they change, also during play. Errors are logged as `file(line): ...`.

## Designing in Penpot

[Penpot](https://penpot.app) is the source of the game's screens: a designer draws them there, and the MealKit plugin turns each screen board into a `.ui` file. The plugin lives in the engine (`tools/penpot-plugin`) and the editor serves it, so nothing is installed besides Penpot.

### Installing the plugin

1. Open the project in the editor and open **Window > UI**. The **Penpot** section in its right column shows the plugin address, for example `http://127.0.0.1:27220/<token>/penpot/manifest.json`. The editor only listens on this computer, and the token changes every time the editor starts (the plugin is served by the editor's live connection, see {doc}`tools`).
2. In a Penpot file press `Ctrl+Alt+P` (plugin manager), paste the address and press **Install**. Open the plugin from the same list after that.
3. The panel says `Editor: <project>` when it reaches the editor. If the editor is closed, **Export** downloads a zip to unpack in the project folder instead (after restarting the editor, install the plugin again with the new address).

The plugin works with Penpot in the cloud (`design.penpot.app`) and with a self-hosted Penpot on this computer. Some browsers block pages from reaching `127.0.0.1`; use a browser that allows it (Chrome, Brave, Edge, Firefox).

### Fonts

Text must use the fonts in the project's `assets/fonts`. Upload the same fonts to Penpot (**Dashboard > Fonts**; TTF, OTF or WOFF). The plugin maps a Penpot font to a file name as `<family>-<weight>`, for example Pretendard weight 500 → `Pretendard-Medium` (`Regular` for 400, `Bold` for 700, `Italic` added for italic). A font the project does not have stops the export of that screen with an error.

### Screens, layers and names

- Every top-level board on the page is one screen. Select it to see the panel's **File** (default `ui/<board name>.ui`) and the board options: keyboard and gamepad navigation, the first focused layer and the back action.
- Layer names become node names (spaces become `_`). Buttons, focus targets and `--ui-press` tests use these names.
- A text layer whose name looks like a string key (`menu.start`, with a dot) gets that key; the export adds missing keys with Penpot's text to the project language's string table (`assets/strings/<language>.txt`). Keys that already exist keep the table's text, and a different text in Penpot is reported. Other text layers keep their text as it is and are reported as not translatable.
- In flex and grid layouts the order is Penpot's: the top layer in the layer list comes first.

### Bindings and widgets

Select a layer to set what the game connects to it. The lists come from the game: the fields of the game's view models (`MEALKIT_VIEWMODEL`) and the actions already used in `assets/ui`.

| Panel field | `.ui` line |
|---|---|
| Widget: button, toggle, slider, select, text input, scroll, list | `button`, `toggle`, `slider`, `select`, `textInput`, `scroll`, `list` |
| Action, View model field, Min/Max/Step, Options, Placeholder, Max characters | the arguments of the widget line |
| Visible when, Disabled when, Width ratio, Color from field | `visible`, `disabled`, `widthRatio`, `colorField` |
| Focus up/down/left/right, State change time | `focusUp` ..., `transition` |
| String key, Overflow, Max lines, Line breaks (text) | `key`, `overflow`, `maxLines`, `wrap` |
| 9-slice margins (baked images) | `slice` |
| Always bake to PNG | the layer is exported as an image |

The values are stored in the Penpot file (plugin data), so the next export writes them again. Exported `.ui` files are never edited by hand.

### What the export keeps

| Penpot | In the game |
|---|---|
| Boards, rectangles, circles, flex and grid layouts (fixed, `fr`, auto and % tracks, merged cells), constraints, sizing (fixed, hug, fill), min and max size, margins, absolute children | drawn by the engine with the same layout |
| One solid or two-stop gradient fill, one solid stroke, corner radius, drop shadows, opacity, rotation, clipping | drawn by the engine |
| Text: font, size, color, letter spacing, line height, alignment, underline, strike, upper and lower case, several styles in one text | text with `span` styles |
| Color and number design tokens (active sets) | `assets/ui/theme.ui` (`$token` in the screen). Hand-written theme lines with other names stay |
| Component variants with a `State` property (`Hover`, `Pressed`, `Focus`, `Disabled`, `Checked`) | `on <state>` lines for the look of the top layer |
| Paths, boolean shapes, icons, masks, image fills, several fills, gradients with more stops, dashed strokes, inner shadows, blend modes | baked to PNG at twice the size in `assets/ui/<screen>/` |
| Layer blur and background blur, `capitalize`, justified text | not supported: reported, then ignored |

Groups without effects are flattened. The export warns when a screen has more than 500 nodes.

### Exporting

Tick the screens and press **Export**. The editor writes `assets/ui/<screen>.ui` and its images, removes images that the screen no longer uses, adds string keys, updates the theme and reloads the screens at once. The plugin also writes `art/ui/boxes/<screen>.boxes` and `art/ui/preview/<screen>.png` for the checks below; keep them in version control with the screen.
A hand-written `.ui` with the same name is not replaced unless **Replace hand-written .ui files** is ticked. Keep the Penpot file itself in `art/ui/` as well: the plugin tries to save it, and with Penpot versions where that fails it asks you to use Penpot's own **Export** (`.penpot`).

The panel's **Add an example screen** draws a small pause menu (flex and grid layouts, two buttons, a baked icon and a color token) to see how a screen is set up.

### Checking that the game matches Penpot

- `MealKitEditor.exe --project <folder> --ui-check [--lang <code>]` lays out every exported screen at its board size and compares each node's box with the box Penpot computed. Boxes may differ by 0.5 logical pixels, text by 2 pixels or 4 % of its width (font shaping differs a little). Text is compared only when the game draws the same characters as Penpot (pick the language of the Penpot text with `--lang`); text with `{fields}`, list items and nodes hidden by a binding are skipped.
- `MealKitEditor.exe --project <folder> --ui-render ui/<screen>.ui out.png` draws one screen at half its board size, the size of the preview the plugin exports, for a loose pixel comparison.

The engine's own `tools\check.ps1` runs both on the sample screen `assets/ui/penpot_example.ui`.

## Connecting the game

The game declares a **view model**, fills it every frame and handles the actions of buttons. The UI never changes the simulation: a button that should change it makes the game send a command (see {doc}`multiplayer`).

```cpp
MEALKIT_STRUCT(PlayerRowVm) { MEALKIT_FIELD(std::string, name, {}, "Name"); MEALKIT_FIELD(u32, falls, 0, "Falls"); };
MEALKIT_VIEWMODEL(HudVm) {
    MEALKIT_FIELD(f32, time, 0.0f, "Match time");
    MEALKIT_LIST(PlayerRowVm, players, 8, "Players"); // array plus playersCount
};

m_hud = ctx.ui.open("ui/hud.ui");     // once
ctx.ui.bind(m_hud, m_hudVm);
fillHud(world, m_hudVm);              // every frame
for (const mealkit::ui::Action& a : ctx.ui.actions())
    if (a.name == "debug.shockwave") mealkit::sim::sendCommand(ctx.session, DebugShockwave{});
```

| In the `.ui` | Meaning |
|---|---|
| `{field}`, `{field:n0}`, `{field:f1}`, `{field:time}`, `{field:pct}` | A value inside text: as is, thousands separators, decimals, minutes:seconds, percent |
| `visible [!]field`, `disabled field`, `widthRatio field`, `colorField field` | Show or hide, disable a widget, scale the width by 0 to 1 (health bars), take the color from a field |
| `src {field}` | On an image: the PNG path comes from a string field (portraits, card art that change at runtime); an empty string draws nothing. With `size hug` the image keeps its own size |
| `scaleField field` | Scales the node's box about its centre by a number (1 = as laid out); world UI templates use it for per-instance sizes |
| `offsetField xField yField`, `opacityField field` | Moves the node and its children by two numbers (logical units, after layout), multiplies their opacity by a number from 0 to 1: slides and fades driven from code |
| `brightness b`, `brightnessField field` | On an image: mixes the picture toward white (b > 0) or black (b < 0), from -1 to 1; also per state (`on hover brightness 0.15`), and the field adds to it |
| `fontSizeField field` | On text: the font size comes from a number field (logical units) instead of `fontSize` |
| `flip horizontal`, `flip vertical` | On an image: mirrors the picture |
| `button <action>` | Sends the action when clicked or confirmed |
| `toggle <field>`, `slider <field> <min> <max> <step>`, `select <field> <key1,key2>` | Input widgets write their own field and send `changed` (or the action given after the field). Text inside a select shows the choice with `{option}` |
| `textInput <field> [action]` | On a text node: typing writes the string field (keyboard text, including Korean input), `Enter` sends the action (default `submit`), `Esc` stops typing. `placeholder <key>` shows dimmed text while it is empty, `maxLength <n>` limits the characters. While typing, the game gets no keyboard input. `ctx.ui.focusText(screen, node)` starts typing from code (a chat key) |
| `scroll [horizontal]` | Scrolls its content with the wheel |
| `list <field>` | Repeats its first child for each item; inside, fields are looked up in the item first. Other children are only examples |

Mouse input over a widget or a filled panel does not reach the game. On screens with `navigation`, the input actions `ui.up`, `ui.down`, `ui.left`, `ui.right`, `ui.confirm` and `ui.back` move the focus to the nearest widget in that direction, change sliders and selects, and press buttons. The HUD has no `navigation`, so it never takes the movement keys.

**World UI**: a screen opened with `ctx.ui.openWorld("ui/nametag.ui")` is a template. In `buildFrame` the game calls `ctx.ui.drawAt(template, worldPosition, viewModel)` for each name tag; the engine places it on the screen with the frame's camera and hides it behind the camera.

## Previewing in the editor

**Window > UI** is a workspace tab beside the **Viewport**. Its left column lists the screens in `assets/ui` and the layers (node tree) of the open one, the middle is a canvas that draws the screen inside a frame of the chosen resolution (16:9, 21:9, 4:3, portrait), and the right column holds the selected node's properties, the preview values, the focus and the problems (file errors, binding errors for fields the view model does not have, and the node count, budget 500 per screen). The toolbar row above them shows the screen and has save, undo and redo, the **Add** menu and the selection's duplicate, wrap, delete and paste buttons. Above the canvas, the selection's path (for example `lobby > main > title`) selects a parent with one click; below it are the resolution, the language (to check that translations fit), the UI scale, the focus display and the zoom (**Fit** shows the whole screen, **Fit width** fills the canvas width and starts a tall screen at its top, click the percentage for 100%; a fit above 100% uses whole multiples so text stays sharp). The wheel zooms around the mouse and a middle or right drag moves the view. The columns can be resized by dragging their borders. While the **UI** tab is in front, the scene's Hierarchy, Inspector and Previews step aside to give it their room; they come back with the **Viewport** tab.

For a bigger canvas, the buttons at the right end of the toolbar hide the left or right column, and `Ctrl+\` hides both (or shows them again). A hidden column leaves a thin strip whose button shows it in a popup beside the canvas; **Keep open** brings it back. **Maximize** (`Shift+Space`) gives the workspace the whole window under the menu bar and hides the other panels; press it again to return to the same layout. **Window > Layout > UI** (or the **UI Layout** command) gives the workspace the whole editor window above the bottom row; the hierarchy and inspector of the scene come back with the other layouts.
The workspace remembers the open screen, the resolution (including a **Custom** width and height), the language, the UI scale and which columns show, so it comes back the same after a restart. `F` or `Shift+2` zooms to the selected node, `Shift+1` fits the whole screen and `Shift+0` shows it at 100%.

The **+** beside **Screens** creates `assets/ui/<name>.ui` with an empty 1920×1080 board and opens it. Right-clicking a screen opens it in the code editor (**Preferences > Code editor**), shows its folder or copies its asset path. With more than eight screens a filter appears above the list, and the **Find layer** field above the layers keeps the nodes whose name or kind matches, with their parents.

`MealKitEditor.exe --ui hud.ui` opens the workspace with that screen.

## Editing screens in the editor

The workspace changes the open screen while showing it as the game draws it (same layout, fonts, string tables and view model values).

- **Selecting**: click a box on the canvas, or a node in the tree. `Ctrl`+click selects the box beneath the selected one (a label inside a button, then the button). The selected node is outlined in blue with its name and size under it; the box under the mouse (or under a hovered layer) gets a thin outline and its name. `Esc` selects the parent, `Enter` the first child.
- **Keyboard**: the arrow keys move a free node by 1 unit (`Shift`: 10), `Alt`+arrows move the selected node one place earlier or later among its siblings (its place in a layout, or the drawing order), and `F2` or a double-click on a layer renames it (`Enter` keeps the name, `Esc` cancels). These keys work while the workspace has the keyboard (click in it first).
- **Moving and resizing**: drag the selected node to move it (its `pos`); edges and centers snap to the parent's and the siblings' (pink guides), hold `Ctrl` to place freely. The eight handles on its box change its size (an axis that was `hug` or `fill` becomes a number). Nodes a flex or grid layout places have no handles: dragging one changes its order among its siblings (a yellow line shows where it goes). A frame's padding is tinted green. A whole drag is one undo step.
- **Properties**: the right column shows the node's name, its position (only for nodes a flex or grid layout doesn't place), its size, where the layout drew it (**Drawn at**), and for a frame how its children are placed (**Children**: free, row, column or grid, with wrap, justify, align and gap) and its padding. Below come the fill or text color, the corner radius and opacity, and for a text its content, font size and alignment, then every line of the node as text, in the format of [A screen file](#a-screen-file). Edit a line in place, remove it with **x**, or pick a property in **Add...**, type its value and press **Add**. A line whose property name the runtime doesn't know is red. `$theme` tokens and comments stay as they are. The button beside the name opens the screen file in the code editor at that node.
- **Binding problems** also show in the layers: a node that names a field the chosen view model doesn't have gets a red **!**, and its tooltip lists the missing fields.
- **Undo and saving**: `Ctrl+Z` and `Ctrl+Y` undo and redo screen edits while the workspace is the visible tab (the scene has its own history). Changes are shown at once but written to the file only by **Save** or `Ctrl+S`; switching to another screen with unsaved changes asks first. Only the lines you changed differ in the saved file.
- **Deleting**: `Delete` removes the selected node and its children.
- Screens exported from Penpot open read-only: change them in Penpot and export again.

- **Library**: the left column lists ready-made widgets: Panel, Text, Image, Button, Toggle, Slider, Progress bar, Text input, List and Scroll area (also under **Add**, and in the command palette as `Add UI <widget>`). Click one to put it inside the selected panel (or the screen), or next to the selected widget; drag one onto the canvas or a layer to put it there. Each comes with its look and placeholder field or action names: change them in the inspector's **Behaviour** section. An empty screen shows these steps on the canvas.
- **Inspector rows**: **Width** and **Height** are each Fixed (a number), Fit content (`hug`) or Fill (the room left in the parent's layout). **Anchor** (for nodes outside a layout) picks the edge or center the node keeps its distance to when the screen size changes, with stretch (`leftright`, `topbottom`) and `scale` beside it. An image picks its file from `assets/ui` or `assets/textures` (an image without one shows a crossed box on the canvas). Texts pick a font from `assets/fonts`. **Behaviour** turns a node into a button, toggle, slider, list, scroll area or text input and edits its action and field.
- **Several nodes**: Shift+click boxes on the canvas (Ctrl+click or Shift+click rows in the layers) to add or remove them, drag on empty space or on the screen itself to select every node fully inside the box, or press Ctrl+A for the selected node's siblings. Dragging one of them moves them all; Delete, Duplicate, Copy and Paste, the arrow keys and **Wrap in frame** (Ctrl+G, nodes with the same parent) act on all of them. The right column then shows **Align** (left, center, right, top, middle, bottom), **Distribute horizontally** and **Distribute vertically** (equal gaps between three or more nodes). One node outside a layout gets **Align in parent** instead. Nodes a layout places are left as they are, because the layout decides where they go.
- **Adding and copying**: **Add** (or right-click a layer or the selection) adds a frame, text, image or component inside the selected frame, or after a selected text, image or component. **Duplicate** (`Ctrl+D`), **Copy** and **Paste** (`Ctrl+C`, `Ctrl+V`) keep its children; the clipboard holds `.ui` text, so it also pastes to and from a text editor. **Wrap in frame** puts a frame of the same size around the node. A new or copied node gets a name not used in the file.
- **Components**: **Make component** (the link button in the toolbar, or right-click a frame) moves the selected frame with its children to `assets/ui/components/<name>.ui` and leaves `use <frame name> ui/components/<name>.ui` in its place. The lines that say where it sits (`pos`, `size`, `min`, `max`, `margin`, `absolute`, `constraints`, `rotation`, `alignSelf`, `justifySelf`, `cell`) stay on the `use` and override the component's own, so the screen looks the same; everything else goes into the component. The component file is written at once; save the screen to keep the `use`. Components appear in the screens list under `components/`. **Edit component** (right-click a `use`, or the button beside its path) opens the component's file, and a back button in the toolbar returns to the screen with the `use` selected; every screen that uses it shows the saved change.
- **Previewing**: **Save values** keeps the view model's test values in `art/ui/samples/<screen>.<ViewModel>.values` (not shipped); they load when the screen opens. **Show state** in the properties shows the selected node as hovered, pressed, focused, disabled or checked. The **Focus** buttons make one keyboard or gamepad move and name the focused node.

`MealKitEditor.exe --ui pause.ui --ui-select resume` opens the screen in the workspace with that node selected; add `--ui-drag 0,90` to drag it by that many logical units after the first frame (the log shows the result).

### Workspace tools

- **Layers**: drag a layer onto another to move it (the top or bottom of a row puts it before or after that row, the middle of a frame puts it inside). The eye on a hovered row hides the node from the canvas and the lock keeps the canvas from picking it; both are only for the editor and are never saved. A link mark shows nodes bound to the view model, dimmed rows are `hidden` in the file, and the buttons beside **Find layer** expand or collapse every row.
- **Binding by dragging**: with a view model chosen under **Preview values**, its fields are listed above the layers. Drag one onto a layer or onto the canvas: a text shows it (`{field}` is added to its content), a list field repeats the frame (`list`), a color field colors it (`colorField`), a decimal field scales its width (`widthRatio`), and other fields show or hide it (`visible`).
- **Theme**: the **Theme** section edits the colors and numbers in `assets/ui/theme.ui` (the tooltip says how many times each is used); **Save theme** writes them and every screen uses the new values. The **$** button beside fill, text color and corner radius picks a theme token, or turns a token back into its plain value.
- **Style**: **Copy style** and **Paste style** in the node menu (`Ctrl+Alt+C`, `Ctrl+Alt+V`) copy fill, stroke, radius, shadow, opacity and text style lines from one node to another.
- **Screens**: right-click a screen to **Duplicate** it or **Rename** it. Renaming lists the project files that name `ui/<screen>.ui` (game code and screens that use it as a component) and replaces the path in them.
- **View** (the eye button under the canvas, or the `UI ...` commands in the command palette, `Ctrl+P`): layout outlines (every box, the direction of row and column layouts and their gaps), the safe area for TVs (90% and 80% frames), rulers, a grid with **Snap to grid** (`Ctrl` while dragging places freely), red marks on text that doesn't fit its box (also listed under **Problems**), and **Pseudo-localize**, which makes string table text about 40% longer and accented so you can see which texts won't fit translations. Hold `Alt` to see the distances from the selected box to the box under the mouse.
- **Preview values**: **Value set** keeps several sets of values for one screen (for example empty, full, very long names) as `art/ui/samples/<screen>.<ViewModel>.<set>.values`; type a name and press **Save as** to add one.
- **Interact**: the pointer button in the toolbar lets you use the screen like a player (hover, press buttons, drag sliders) instead of editing it; the actions it sends are listed above the canvas.
- **While playing**: the UI tab lists the game's open screens with their live view model values. **Keep as preview values** saves them as that screen's values, so the workspace previews real data after you stop.
- **Saving a picture**: the camera button under the canvas saves the screen as `art/ui/captures/<screen>_<width>x<height>_<language>.png` and copies the path.
- **History and changes**: the history button next to undo and redo lists the steps by the line each one changed; click one to go back to it. The changes button shows the unsaved lines against the file, with **Save** and **Revert**. When the file changes outside the editor while nothing is unsaved, the workspace reads it again and says so above the canvas.

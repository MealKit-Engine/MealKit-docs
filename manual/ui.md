# Game UI

The game's screens (HUD, menus, settings) are `.ui` files in `assets/ui/`. The engine lays them out and draws them in one 2D pass after the 3D scene.
Later a Penpot plugin will export these files from a visual design; until then they are written by hand in the same format, and hand-written screens keep working when the plugin arrives.

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
| Look | `fill <color>` or `fill linear\|radial x0 y0 x1 y1 <color> <color>`, `stroke <width> <color>`, `radius` (one value or one per corner), `shadow <dx> <dy> <blur> <spread> <color>` (several allowed) |
| Images | `src ui/icon.png`, `slice <left> <top> <right> <bottom>` (9-slice), `tint <color>` |
| Text | `key <strings key>` or `content <text>`, `font`, `fontSize`, `color`, `letterSpacing`, `lineHeight`, `textAlign`, `verticalAlign`, `underline`, `strike`, `transform`, `wrap word\|syllable\|none`, `overflow ellipsis`, `maxLines`, `span <tag> <property> <value> ...` |
| States | `on hover\|pressed\|focus\|disabled\|checked <property line>`, `transition <seconds>` |
| Board lines | `navigation` (keyboard and gamepad focus, for menus), `firstFocus <node>`, `back <action>` |

Colors are `#RRGGBB[AA]` or `$token` from the theme `assets/ui/theme.ui` (`color <name> #...`, `number <name> <value>`). Text with several styles uses numbered tags from the string table, `<1>...</1>`, styled by `span 1 ...`.
Korean text breaks between syllables (`wrap syllable`, the default); `wrap word` breaks only at spaces. Characters missing from one font are taken from another font in `assets/fonts`.
Files are reloaded within a quarter second when they change, also during play. Errors are logged as `file(line): ...`.

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
| `button <action>` | Sends the action when clicked or confirmed |
| `toggle <field>`, `slider <field> <min> <max> <step>`, `select <field> <key1,key2>` | Input widgets write their own field and send `changed` (or the action given after the field). Text inside a select shows the choice with `{option}` |
| `textInput <field> [action]` | On a text node: typing writes the string field (keyboard text, including Korean input), `Enter` sends the action (default `submit`), `Esc` stops typing. `placeholder <key>` shows dimmed text while it is empty, `maxLength <n>` limits the characters. While typing, the game gets no keyboard input. `ctx.ui.focusText(screen, node)` starts typing from code (a chat key) |
| `scroll [horizontal]` | Scrolls its content with the wheel |
| `list <field>` | Repeats its first child for each item; inside, fields are looked up in the item first. Other children are only examples |

Mouse input over a widget or a filled panel does not reach the game. On screens with `navigation`, the input actions `ui.up`, `ui.down`, `ui.left`, `ui.right`, `ui.confirm` and `ui.back` move the focus to the nearest widget in that direction, change sliders and selects, and press buttons. The HUD has no `navigation`, so it never takes the movement keys.

**World UI**: a screen opened with `ctx.ui.openWorld("ui/nametag.ui")` is a template. In `buildFrame` the game calls `ctx.ui.drawAt(template, worldPosition, viewModel)` for each name tag; the engine places it on the screen with the frame's camera and hides it behind the camera.

## Previewing in the editor

**View > UI** lists the screens in `assets/ui`. The selected screen is drawn over the scene view in edit mode, inside a frame of the chosen resolution (16:9, 21:9, 4:3, portrait). The panel changes the UI scale and the language (to check that translations fit), shows the focus, fills a game view model with test values, and lists file errors, binding errors (fields the view model does not have) and the node count (budget 500 per screen).
`MealKitEditor.exe --ui hud.ui` opens the panel with that screen.

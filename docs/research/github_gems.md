# GitHub Gems — OSS Research Dossier for the PySide6 CS2 Coach Redesign

> Compiled 2026-08-13. Target app: PySide6 desktop CS2 coaching tool.
> Design language: deep navy `#0B1628` base / `#121E2E` cards, orange accent `#FF6A00`,
> cyan data `#00D9FF`, JetBrains Mono metadata, dense dark tactical UI, three retro
> themes (CS2 / CSGO / CS1.6). Existing infra: W3C design-tokens JSON -> QSS engine,
> custom QPainter widgets (rings, sparklines, radar), QtCharts, 2D tactical viewer with
> playback + pro ghost overlay, chat UI, toasts, skeletons, onboarding wizard.

## License policy used throughout

- **MIT / BSD / Apache** -> snippets may be adapted into the proprietary app. Every
  fenced snippet carries an attribution header comment. Keep those headers in the code
  or move them to a `THIRD_PARTY_NOTICES` file.
- **GPL-3.0 (flagged `STUDY ONLY`)** -> ideas, architecture and measurements may be
  learned from, but **no code, QSS, SVG or asset may be copied** into this app.
  Affected: boltobserv, PyQt-Fluent-Widgets, lexogrine/csgo-react-hud (v1), QCustomPlot.
- Memory-reading "web radar" repos (Kava4/cs2-webradar, radarflow2, memflow-based
  radars) are **cheat tooling** — excluded entirely. The legitimate patterns are
  demo-file parsing (awpy/demoparser2) and Game State Integration (boltobserv-style).
- **⚠ QtCharts itself is GPLv3-or-commercial — NOT LGPL** (verified against
  doc.qt.io/qt-6/qtcharts-index.html: "available under commercial licenses from The
  Qt Company. In addition, it is available under the GNU General Public License,
  version 3." — unlike Qt Essentials, LGPL is not offered). Since this app is
  proprietary and currently QtCharts-based, we must either hold a Qt commercial
  license or **migrate charts to pyqtgraph (MIT) / custom QPainter widgets** — the
  single most consequential license finding of this research. See §3.2.

---

## 1. CS demo / radar visualization

### 1.1 CS Demo Manager — the reference UI ★★★★★
- **URL:** https://github.com/akiver/cs-demo-manager — 1,978★, very active (pushed 2026-07), **MIT**. Electron + React 19 + Tailwind v4 + Redux Toolkit.
- **Why it matters:** the best OSS CS analytics UI, full stop. Its information architecture and its 2D viewer drawing code are directly transplantable concepts (MIT, so code too).

**IA blueprint** (`src/ui/match/`): one match = tabbed workspace with `overview`, `rounds`, `duels`, `economy`, `grenades`, `heatmap`, `players`, `weapons`, `video`, `chat-messages`, `viewer-2d`. Left global nav (`src/ui/left-bar`), custom title bar (`src/ui/title-bar`, `--title-bar-height: 36px`). Adopt this tab set as the match-view IA.

**Design-token architecture** (`src/ui/styles/variables.css`) — three layers, maps 1:1 onto our W3C-tokens→QSS engine:
1. primitive palettes `--dark-gray-50..900` / `--light-gray-50..900`;
2. semantic aliases flipped per theme (`html.dark { --gray-100: var(--dark-gray-100) }`);
3. framework exposure (Tailwind `@theme`). Domain tokens live at layer 3: 

```css
/* From akiver/cs-demo-manager (MIT) — src/ui/styles/variables.css */
--color-ct: #378ef0;          /* CT blue   */
--color-terro: #f29423;       /* T orange  */
--color-bombsite-a: #e34850;
--color-bombsite-b: #2680eb;
--cs-rating-tier-0: #c4d0df;  /* ... tier-6: #ffd700 — 7-step rating ramp */
--title-bar-height: 36px;
--table-row-height: 36px;     /* dense tables: 36px rows, 14px body text */
```
Lesson: publish *domain* tokens (ct/t colors, rating tiers, bombsite colors) alongside neutral scales; flip only the semantic layer per theme (our CS2/CSGO/CS1.6 themes = three semantic maps over one primitive set).

**2D viewer** (`src/ui/match/viewer-2d/`): canvas + one hook per entity type — `drawing/use-draw-map-radar.ts`, `use-draw-players.ts`, `use-draw-grenades.ts`, `use-draw-infernos.ts`, `use-draw-shots.ts`, `use-draw-deaths.ts`, `use-draw-bombs.ts` — composed over an `InteractiveCanvas` that provides `zoomedToRadarX/Y` + `zoomedSize` (zoom/pan abstraction). Port as QPainter layer-classes with the same split.

The player-state glyph vocabulary (`drawing/use-draw-players.ts`, MIT — port to QPainter):

```ts
// From akiver/cs-demo-manager (MIT) — src/ui/match/viewer-2d/drawing/use-draw-players.ts (condensed)
// Dot: team-color fill, white ring (red ring = focused player)
context.arc(x, y, zoomedSize(8), 0, 2 * Math.PI);
context.strokeStyle = isFocusedPlayer ? '#ff0000' : '#ffffff';
context.fillStyle = getTeamColor(position.side); context.fill(); context.stroke();
// Health: red pie that "eats" the dot counter-clockwise as HP drops
const endAngle = -Math.PI / 2 + Math.PI * 2 * -(health / 100);
context.fillStyle = '#d7373f99';
context.arc(x, y, zoomedSize(7), -Math.PI / 2, endAngle); context.lineTo(x, y); context.fill();
// View direction: white line, longer while scoping (8+6 vs 8+2)
const lineLength = isScoping ? zoomedSize(14) : zoomedSize(10);
// Flash: white pie ring r=16 whose sweep = flashDurationRemaining / 5.25s
// Defuse: green pie r=14, sweep = elapsedTicks / (kit ? 5 : 10)*tickrate
// Plant:  red pie r=14, sweep = elapsedTicks / (3.2s * tickrate)
// Knife/grenade in hand: filled triangle at the rim instead of the line;
// bomb carrier: C4 icon drawn beside the dot; name label at (x-20, y+20), 10px font
```

**Timeline scrubber** (`playback-bar/timeline.tsx` + `kill-indicator.tsx`, `bomb-planted-indicator.tsx`, `bomb-exploded-indicator.tsx`, `freezetime-end-indicator.tsx`): elapsed bar + absolutely-positioned event markers, `x = width * (tick - startTick) / (endOfficiallyTick - startTick)`; click-to-seek converts x back to tick. Playback bar buttons: play/pause, prev/next round, speed, lower-radar toggle, fullscreen, drawing (telestrator!), audio. Port: QWidget scrubber painting kill/bomb markers, or QGraphicsScene strip.

**Radar coordinate transform** (`src/ui/maps/get-scaled-coordinate-x.ts` / `-y.ts`):

```ts
// From akiver/cs-demo-manager (MIT)
const xForDefaultRadarWidth = (xFromDemo - map.posX) / map.scale;
const scaledX = (xForDefaultRadarWidth * imageSize) / map.radarSize; // radarSize = 1024
// Y is mirrored: (map.posY - yFromDemo) / map.scale
```
Plus `src/ui/maps/radar-level.ts` (`upper`/`lower`) — maps with two radar images switch by player Z.

### 1.2 awpy — parsing + the canonical world→radar math ★★★★★
- **URL:** https://github.com/pnxenopoulos/awpy — 608★, active, **MIT**. Python (pairs natively with our PySide6 app).
- **Borrow:** demo parsing (`awpy/demo.py` wraps demoparser2), stats (`awpy/stats/adr.py`, `kast.py`, `rating.py` — coach-relevant impact ratings), and above all `awpy/plot/utils.py` + `awpy/data/map_data.py`:

```python
# From pnxenopoulos/awpy (MIT) — awpy/plot/utils.py ("courtesy of PureSkill.gg")
def game_to_pixel_axis(map_name, position, axis):
    start = MAP_DATA[map_name]["pos_" + axis]   # world coord of radar top-left
    scale = MAP_DATA[map_name]["scale"]         # world units per radar pixel
    if axis == "x":
        return (position - start) / scale
    return (start - position) / scale           # y axis flipped

def is_position_on_lower_level(map_name, position):
    return position[2] <= MAP_DATA[map_name]["lower_level_max_units"]
```

```python
# From pnxenopoulos/awpy (MIT) — awpy/data/map_data.py: per-map calibration schema
class MapData(TypedDict):
    pos_x: int; pos_y: int          # upper-left world coordinate of the radar image
    scale: float                    # world units per pixel (1024px radar images)
    rotate: int | None; zoom: float | None
    lower_level_max_units: float    # Z cutoff for lower-level radar (Nuke/Vertigo)
```
`map-data.json` is generated from the game's own `resource/overviews/*.txt` VDF files (`map_data_from_vdf_files`) — i.e. calibration ships with CS2 itself; regenerate per game update instead of hand-tuning.

### 1.3 LaihoE/demoparser (demoparser2) ★★★★
- **URL:** https://github.com/LaihoE/demoparser — 705★, very active, **MIT**. Rust core, Python/JS bindings.
- **Borrow:** the data backbone (we already consume it). `parse_ticks(["X","Y","Z","yaw","health","flash_duration","active_weapon_name",...])` returns exactly the per-tick dataframe the CSDM-style viewer needs. Examples dir shows patterns for kills/grenades/ticks queries. Nothing UI to copy.

### 1.4 csgoverview — immediate-mode 2D replay (translates 1:1 to QPainter) ★★★★
- **URL:** https://github.com/Linus4/csgoverview — 196★, dormant (2024) but complete, **MIT**. Go + SDL2.
- **Borrow from `draw.go`:** the most legible entity-drawing reference anywhere; every function is a QPainter recipe: `drawPlayer`, `drawGrenade`, `drawInferno` (convex-hull fire polygon), `drawInfobar` (per-player HP/armor/money strip), `drawKillfeed`, `drawTimer`, `drawShot` (fading tracer line).

```go
// From Linus4/csgoverview (MIT) — draw.go (condensed)
// Health as a SPLIT RING: remaining HP arc in team color centered on top,
// lost HP arc in 0.6x darkened team color centered on bottom.
healthArc := int32(player.Health) * 360 / 100
gfx.ArcColor(r, x, y, radius, 90-healthArc/2, 90+healthArc/2, teamColor)
dark := scaleRGB(teamColor, 0.6)
gfx.ArcColor(r, x, y, radius, -90-(360-healthArc)/2, -90+(360-healthArc)/2, dark)

// View cone as three stacked arcs that "narrow" outward: +-20deg, +-10deg, +-5deg
// at r+1, r+2, r+3 -> cheap antialiased cone glow. AWP holders get a highlight color.
gfx.ArcColor(r, x, y, radius+1, view-20, view+20, colorLOS)
gfx.ArcColor(r, x, y, radius+2, view-10, view+10, colorLOS)
gfx.ArcColor(r, x, y, radius+3, view-5,  view+5,  colorLOS)

// Cross-level de-emphasis: players on the other elevation render at alpha 100/255.
// Dead players: 'X' glyph at LastAlivePosition, alpha -105.
// Flash: filled inner circle, alpha = remainingSeconds*255/3.1 (clamped).
```
Also note its hotkey grammar (a/d round jump, w/s next/prev half, q/e frame step, F1 hide names) — good defaults for our viewer.

### 1.5 lexogrine/cs2-react-hud — LexoRadar (broadcast-grade radar, MIT) ★★★★
- **URL:** https://github.com/lexogrine/cs2-react-hud — 40★, active (2026-01), **MIT** (verified LICENSE + package). The old `lexogrine/csgo-react-hud` is **GPL-3.0 — STUDY ONLY**; use the cs2 repo for code.
- **Borrow from `src/HUD/Radar/LexoRadar/`** (`utils.ts`, `maps/index.ts`, `LexoRadar.tsx`, `index.scss`):
  - `ScaleConfig { origin:{x,y}, pxPerUX, pxPerUY, originHeight? }` per map; `DoubleLayer` maps carry `configs[]` each with `isVisible(z)` — same multi-level answer as awpy/CSDM.
  - **Position smoothing:** render position = mean of the last 5 GSI states per player — the trick that makes 8-16Hz data glide. Perfect for our pro-ghost overlay interpolation.
  - **Angle unwrap for smooth rotation** (shortest-arc accumulation so a 350°→10° turn animates 20°, not −340°):

```ts
// From lexogrine/cs2-react-hud (MIT) — src/HUD/Radar/LexoRadar/utils.ts (condensed)
let modifier = previous % 360;
modifier = -(modifier - direction);
if (Math.abs(modifier) > 180) modifier -= 360 * Math.sign(modifier);
directions[player.steamid] += modifier;   // accumulate, never jump
```
  - Depth cue: dot scale `1 + (z - originHeight)/1000` — subtle "higher = bigger".
  - Grenade lifecycle state machine: `inair → landed → exploded` via `effecttime` (smoke >= 16.5s) and lifetime thresholds (`flash 1.45s`, `frag 1.6s`); inferno = one dot per flame position. Drive our utility rendering with the same states.

### 1.6 boltobserv — GPL-3.0, STUDY ONLY (no code/asset copying) ★★★
- **URL:** https://github.com/boltgolt/boltobserv — 381★, active, **GPL-3.0**. Electron; reads live **Game State Integration** (`src/gamestate_integration_boltobserv.cfg`, `gsi.js`) — the legitimate live-data pattern (vs. memory readers).
- **Ideas to learn (described, not copied):** per-map folder (`src/maps/de_*/meta.json5`) bundling radar png + calibration + overlay layers (`overlay_buyzones.png`, `overlay_logos.png`) — a clean "map pack" format for our three themes; DOM dots moved via CSS `transform` with CSS transitions doing the tweening (equivalent in Qt: QGraphicsItem + QPropertyAnimation on pos); transparent-background mode for OBS overlay use; advisories ("adv-plant/defuse/solesurvivor" icons) surfaced above the radar.
- Note: several boltobserv map assets carry their own LICENSE files — another reason to keep distance from its assets.

### 1.7 Excluded: memory-reading "web radars"
`Kava4/cs2-webradar`, `radarflow2`, memflow/DMA radars etc. read live game memory — cheat tooling; excluded from study. Legitimate patterns are demo parsing (awpy/demoparser2) and GSI (boltobserv-style), both covered above.

## 2. Qt / PySide desktop UI exemplars

### 2.1 BreezeStyleSheets — the closest analogue to our tokens→QSS engine ★★★★★
- **URL:** https://github.com/Alexhuszagh/BreezeStyleSheets — 662★, active (2026-07), **MIT**.
- **Pipeline** (`configure.py` + `theme/*.json` + `template/stylesheet.qss.in` + `template/*.svg.in`):
  1. Theme = flat JSON of `token[:variant]` colors (supports `//` comments):

```jsonc
// From Alexhuszagh/BreezeStyleSheets (MIT) — theme/dark-blue.json (excerpt)
{
  "foreground": "#eff0f1",
  "background": "#31363b",
  "highlight": "#3daee9",
  "highlight:dark": "#2a79a3",
  "view:hover": "rgba(61, 173, 232, 0.1)",
  "button:background:pressed": "#454a4f",
  "scrollbar:hover": "#3daee9",
  "critical": "#80404a", "information": "#406880", "warning": "#99995C",
  "ads-tab:focused": "rgba(61, 173, 232, 0.1)"   // extension-specific tokens
}
```
  2. Template substitution is dead simple — `configure.py::replace_by_name`: `contents = contents.replace(f'^{key}^', color)`; `^style^` becomes the resource prefix so `url(^style^dialog_ok.svg)` → `url(:/dark/dialog_ok.svg)`.
  3. **Themed SVG icons:** every icon is an `.svg.in` template colorized with the same tokens, then compiled into a `.qrc` (optionally a standalone python resource). This is how you get checkboxes/arrows/spinners that match all three of our retro themes for free.
  4. **Em-based QSS sizing** — the whole stylesheet uses `em` units so density scales with font size:

```css
/* From Alexhuszagh/BreezeStyleSheets (MIT) — template/stylesheet.qss.in */
QScrollBar:vertical {
    background-color: ^scrollbar:background^;
    width: 0.65em;
    margin: 0.65em 0.13em 0.65em 0.13em;
    border: 0.04em transparent ^scrollbar:background^;
    border-radius: 0.17em;
}
QScrollBar::handle:vertical {
    background-color: ^scrollbar:hover^;
    min-height: 0.5em;
    border-radius: 0.17em;
}
```
  5. **Extension system** (`extension/advanced-docking-system/`, `extension/standard-icons/`): per-3rd-party-widget QSS fragments + icon sets compiled with the same theme — the right way to keep our QtCharts/custom-widget styling out of the core sheet.

### 2.2 PyDracula (Wanderson-Magalhaes) — sidebar/panel animation grammar ★★★★
- **URL:** https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6 — 3,077★, **MIT**, dormant but the pattern set is timeless.
- **Borrow from `modules/ui_functions.py`:** animated collapsible sidebar + right settings drawer, frameless window kit (custom title bar drag, double-click maximize, `QSizeGrip` resize corners in `resize_grips`), menu-selection styling by QSS string append/remove (`selectMenu`/`deselectMenu`).

```python
# From Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6 (MIT) — modules/ui_functions.py
def toggleMenu(self, enable):
    width = self.ui.leftMenuBg.width()
    widthExtended = Settings.MENU_WIDTH if width == 60 else 60   # 60px rail <-> 240px
    self.animation = QPropertyAnimation(self.ui.leftMenuBg, b"minimumWidth")
    self.animation.setDuration(Settings.TIME_ANIMATION)          # 500ms
    self.animation.setStartValue(width)
    self.animation.setEndValue(widthExtended)
    self.animation.setEasingCurve(QEasingCurve.InOutQuart)
    self.animation.start()

# Dual-panel version: two QPropertyAnimations in a QParallelAnimationGroup
# (start_box_animation) so opening the right drawer closes the left one in sync.
```
- Icon-rail collapse (60px showing icons only ↔ 240px with labels) is exactly the nav pattern for a dense tactical app.

### 2.3 PyOneDark (same author) — JSON theme architecture for custom widgets ★★★★
- **URL:** https://github.com/Wanderson-Magalhaes/PyOneDark_Qt_Widgets_Modern_GUI — 1,149★, **MIT**.
- **Borrow:** `gui/themes/*.json` (semantic slot schema below) + `gui/core/json_themes.py` (tiny loader) + `settings.json` (app config: startup size, time_animation…). Every custom widget receives theme colors as constructor kwargs and formats its own QSS — a clean alternative to one monolithic sheet for *custom* widgets, while stock widgets use the global QSS.

```json
// From Wanderson-Magalhaes/PyOneDark_Qt_Widgets_Modern_GUI (MIT) — gui/themes/dracula.json
{ "theme_name": "dracula", "app_color": {
  "dark_one": "#282a36", "dark_two": "#2B2E3B", "dark_three": "#333645", "dark_four": "#3C4052",
  "bg_one": "#44475a", "bg_two": "#4D5066", "bg_three": "#595D75",
  "icon_color": "#c3ccdf", "icon_hover": "#dce1ec", "icon_pressed": "#ff79c6", "icon_active": "#f5f6f9",
  "context_color": "#ff79c6", "context_hover": "#FF84D7", "context_pressed": "#FF90DD",
  "text_title": "#dce1ec", "text_foreground": "#f8f8f2", "text_description": "#979EC7",
  "white": "#f5f6f9", "pink": "#ff79c6", "green": "#00ff7f", "red": "#ff5555", "yellow": "#f1fa8c" }}
```
Map to ours: `dark_one..four` = elevation ladder from `#0B1628`→`#121E2E`→…; `context_*` = `#FF6A00` accent triplet; `icon_*` = 4-state icon colors. The 4-state icon color set (normal/hover/pressed/active) is a detail our token schema should copy.

### 2.4 qt-material — density scale + runtime theme rebuild ★★★★
- **URL:** https://github.com/UN-GCPDS/qt-material — 2,858★, **BSD-2-Clause**.
- **Borrow** (`qt_material/__init__.py`, `material.css.template`): Jinja2 QSS template; theme XML supplies `primaryColor/secondaryColor/...`; `extra={}` injects `danger/warning/success`, `font_family`, and `density_scale`. The density filter is the gem for our "dense tactical UI" requirement — one knob compacts every control:

```python
# From UN-GCPDS/qt-material (BSD-2-Clause) — qt_material/__init__.py
def density(value, density_scale, border=0, scale=1, density_interval=4, min_=4):
    # https://material.io/develop/web/supporting/density
    density = (value + (density_interval * int(density_scale)) - (border * 2)) * scale
    return max(density, min_)
```
```css
/* material.css.template usage: */
QToolButton { height: {{36|density(density_scale, border=2)}}px; }
QComboBox   { padding: {{8|density(density_scale)}}px {{16|density(density_scale)}}px; }
```
```python
apply_stylesheet(app, theme='dark_teal.xml',
                 extra={'density_scale': '-2', 'font_family': 'JetBrains Mono'})
```
- Also exports every theme color to `os.environ['QTMATERIAL_*']` so runtime QPainter code can read the active palette — same job our token registry does; validates the pattern.

### 2.5 PyQt-Fluent-Widgets (zhiyiYo) — **GPL-3.0, STUDY ONLY** ★★★★★ (ideas)
- **URL:** https://github.com/zhiyiYo/PyQt-Fluent-Widgets — 8,065★, very active, **GPL-3.0** (commercial license sold separately). **No code/QSS/SVG may be copied.** Study these files for architecture, then reimplement from scratch:
  - `qfluentwidgets/common/style_sheet.py` — `StyleSheetBase` registry: every widget registers its sheet; on theme change a global config re-applies sheets to *live* widgets (observer pattern), plus `themeColor()` accessor and color templating. The cleanest runtime theme-switch architecture in Qt Python land; our engine should offer the same "re-polish everything on token change" service.
  - `qfluentwidgets/components/widgets/info_bar.py` — InfoBar anatomy: severity icon + title + body + action + close, `InfoBarPosition.TOP_RIGHT` stacking manager with slide+fade QPropertyAnimations and auto-dismiss. Blueprint for our toast system (reimplement; or use MIT pyqttoast below).
  - `qfluentwidgets/components/navigation/navigation_interface.py` — rail→expanded sidebar with per-item indicator slide animation and tooltips when collapsed.
  - `qfluentwidgets/components/widgets/acrylic_label.py` + `components/material/acrylic_*` — "acrylic" = blurred background image + luminosity + tint + noise layers. In Qt: gaussian-blur a pixmap once, overlay `rgba` tint + noise texture. (For our navy theme: blur the map radar behind panels.)
  - Gallery app (`examples/gallery`) — the showcase shell IA (left nav, search, theme toggle) worth mirroring.
- Same author's `zhiyiYo/PyQt-Frameless-Window` is **also GPL-3.0** — do NOT pip-install-and-ship; use PyDracula's MIT frameless kit instead.

### 2.6 QDarkStyleSheet — full-coverage QSS reference ★★★
- **URL:** https://github.com/ColinDuquesnoy/QDarkStyleSheet — 3,082★, **MIT (code) + CC-BY-4.0 (images)**.
- **Borrow:** `qdarkstyle/dark/darkstyle.qss` is the most *complete* widget-state matrix in OSS (every pseudo-state of every stock widget, incl. QDockWidget, QToolBox, QCalendarWidget). Use it as the checklist when auditing our generated QSS for coverage gaps; palette lives in `qdarkstyle/dark/palette.py` (10-step color class). If any of its SVGs are reused, CC-BY attribution is required — prefer generating our own via the Breeze `.svg.in` approach.

### 2.7 PyQtDarkTheme — programmatic QSS + QPalette with accent injection ★★★
- **URL:** https://github.com/5yutan5/PyQtDarkTheme — 750★, active (2026-08), **MIT**.
- **Borrow:** `qdarktheme.setup_theme(custom_colors={"primary": "#FF6A00"}, corner_shape="sharp")`; internally split into `load_palette()` + `load_stylesheet()` — generating **QPalette alongside QSS** is the detail most theming engines miss (native dialogs, tooltips and unstyled widgets follow the palette). Their template engine rewrites SVG icon colors at build time too.

### 2.8 qtmodern — minimal frameless-window wrapper ★★
- **URL:** https://github.com/gmarull/qtmodern — 789★, **MIT**, archived. `qtmodern/windows.py::ModernWindow` wraps any widget in a frameless shell with its own title bar; `qtmodern/styles.py` = palette-first theming. Good minimal reference if PyDracula's kit feels heavy.

### 2.9 qtsass — SCSS→QSS compiler ★★★
- **URL:** https://github.com/spyder-ide/qtsass — 148★, maintained by Spyder team, **MIT**. Write QSS with variables/nesting/mixins (`@mixin elevation`, `darken($navy, 5%)`), compile to QSS. Alternative implementation strategy for our token engine: emit an SCSS vars file from the W3C tokens, let qtsass do the rest. Handles Qt-specific quirks (`qlineargradient` etc.).

### 2.10 laserpants/qt-material-widgets — animation-rich C++ widget set ★★★
- **URL:** https://github.com/laserpants/qt-material-widgets — 3,599★, **BSD-3-Clause**, C++ (port patterns, not files). Study `components/qtmaterialripple.cpp` + `qtmaterialoverlaywidget.cpp`: ripple = expanding circle + fading opacity driven by `QParallelAnimationGroup` painted on an overlay widget; also ink-bar slide in `qtmaterialtabs.cpp` and floating-label animation in text fields. The overlay-widget technique (transparent widget covering the target, painting effects above it) is the right way to add ripples/glows to stock Qt widgets without subclass explosions.

## 3. Charts & dataviz for Qt

### 3.1 pyqtgraph — dark-first, GPU-fast plotting ★★★★★
- **URL:** https://github.com/pyqtgraph/pyqtgraph — 4,397★, very active, **MIT** (verified LICENSE.txt; GitHub shows "Other" only due to file formatting).
- **Why over QtCharts for dense data:** default dark background, orders faster for tick-level series (per-round damage over 30k ticks), `setClipToView` + `setDownsampling(auto=True)` for scrub-speed redraws.
- **Sparkline recipe** (our code, using pyqtgraph API — MIT lib):

```python
# Sparkline pattern for stat cards (pyqtgraph is MIT — safe dependency)
import pyqtgraph as pg
pg.setConfigOptions(antialias=True)
w = pg.PlotWidget(background=None)                 # transparent -> card bg shows through
w.setFixedHeight(28); w.hideAxis('bottom'); w.hideAxis('left')
w.setMouseEnabled(x=False, y=False); w.setMenuEnabled(False); w.hideButtons()
curve = w.plot(ys, pen=pg.mkPen('#00D9FF', width=1.5),
               fillLevel=min(ys), brush=pg.mkBrush(0, 217, 255, 40))  # cyan + 16% fill
w.plot([len(ys)-1], [ys[-1]], pen=None, symbol='o', symbolSize=4,
       symbolBrush='#FF6A00', symbolPen=None)      # orange "now" dot
```
- **Candlestick/economy chart via QPicture caching** — the canonical custom-item example; the QPicture trick (pre-render once, `drawPicture` per frame) applies to *all* our custom QPainter widgets:

```python
# From pyqtgraph/pyqtgraph (MIT) — pyqtgraph/examples/customGraphicsItem.py (condensed)
class CandlestickItem(pg.GraphicsObject):
    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)           # pre-compute once ...
        w = (self.data[1][0] - self.data[0][0]) / 3.
        for (t, open, close, min, max) in self.data:
            p.drawLine(QtCore.QPointF(t, min), QtCore.QPointF(t, max))
            p.setBrush(pg.mkBrush('r' if open > close else 'g'))
            p.drawRect(QtCore.QRectF(t - w, open, w * 2, close - open))
        p.end()
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)          # ... then blit per frame
```
  For our economy view: x = round number, open/close = money before/after buy, red/green = eco result; style with `--color-cyan` wicks and orange loss-bodies.
- Also study `pyqtgraph/examples/crosshair.py` (SignalProxy + two InfiniteLines = hover crosshair with live readout — ideal for round-timeline charts).

### 3.2 QtCharts — ⚠ license trap + theming techniques ★★★
- **URL:** https://github.com/qt/qtcharts — official add-on module. **The module is GPLv3-or-commercial ONLY — LGPL is NOT offered** (verified: doc.qt.io/qt-6/qtcharts-index.html; PySide6 being LGPL does not relicense the add-on it wraps). For this proprietary app that means: hold a Qt commercial license, or **plan the QtCharts→pyqtgraph/custom-QPainter migration** as part of this redesign. Example *code* under `examples/charts/chartsgallery` is BSD-3-Clause and fine to read for patterns either way.
- QtCharts cannot be styled by QSS — everything is programmatic. If we keep it (commercially licensed) — or as the spec for the pyqtgraph port — centralize one `apply_chart_theme(chart, tokens)` next to the QSS engine (the snippet below is our own code, applicable to either backend's API):

```python
# Our token-driven QtCharts skin (pattern from Qt's chartsgallery example, BSD-3)
def apply_chart_theme(chart: QChart, t: dict) -> None:
    chart.setBackgroundBrush(QColor(0, 0, 0, 0))          # transparent: card provides bg
    chart.setBackgroundRoundness(0)
    chart.setPlotAreaBackgroundBrush(QColor(t["bg.card2"]))  # #16233A-ish inset
    chart.setPlotAreaBackgroundVisible(True)
    chart.legend().setLabelColor(QColor(t["text.muted"]))
    f = QFont("JetBrains Mono", 8)
    for ax in chart.axes():
        ax.setLabelsColor(QColor(t["text.muted"])); ax.setLabelsFont(f)
        ax.setLinePenColor(QColor(t["border.subtle"]))
        ax.setGridLineColor(QColor(255, 255, 255, 14))    # ~5% white grid
        ax.setMinorGridLineVisible(False)
    chart.setAnimationOptions(QChart.SeriesAnimations)     # 800ms grow-in
# Economy: QCandlestickSeries(increasingColor=cyan, decreasingColor=#FF4C4C,
#          bodyOutlineVisible=False); donut KPI: QPieSeries with holeSize=0.72.
```

### 3.3 QCustomPlot — **GPL, STUDY ONLY** ★★
- **URL:** https://www.qcustomplot.com / gitlab mirror — C++, **GPL-3.0**. Worth a look at its dark financial-chart demos (axis rect margins, layered grid) purely for visual reference. No code.

### 3.4 Radar/spider chart — build our own (references are thin) ★★★
- `fredmorcos/qradarchart` (**Unlicense**, C++, 1★) is the only clean Qt spider widget — public domain, fine to mine, but trivial. The robust approach is ~40 lines of QPainterPath:

```python
# Original recipe (no upstream) — spider chart core for player skill profile
def paint_spider(p: QPainter, rect, axes: list[str], values01: list[float], t):
    cx, cy = rect.center().x(), rect.center().y()
    R = min(rect.width(), rect.height()) / 2 - 24
    n = len(axes); step = 2 * math.pi / n
    for ring in (0.25, 0.5, 0.75, 1.0):                     # grid rings
        path = QPainterPath()
        for i in range(n + 1):
            a = -math.pi / 2 + (i % n) * step
            pt = QPointF(cx + R * ring * math.cos(a), cy + R * ring * math.sin(a))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1)); p.drawPath(path)
    poly = QPolygonF([QPointF(cx + R * v * math.cos(-math.pi/2 + i*step),
                              cy + R * v * math.sin(-math.pi/2 + i*step))
                      for i, v in enumerate(values01)])
    p.setPen(QPen(QColor(t["accent.cyan"]), 2))
    p.setBrush(QColor(0, 217, 255, 45)); p.drawPolygon(poly)   # cyan fill 18%
    # overlay pro-benchmark polygon in orange, brush alpha 25, dashed pen
```
  QtCharts alternative: `QPolarChart` + `QLineSeries` + `QCategoryAxis` (used by several stats dashboards; less control over fills).

### 3.5 Dashboard composition references
- `pyqtgraph/examples/` `GraphicsLayout.py` + `MultiPlotWidget.py` — grid-of-plots in one GraphicsLayoutWidget (shared x-axis round timeline stack: kills / economy / momentum).
- CSDM's `src/ui/match/heatmap` renders a heatmap layer over the radar image; in Qt: accumulate positions into a QImage histogram, colorize via LUT, draw semi-transparent over the radar pixmap (numpy → QImage, ~2 ms for 1024²).

## 4. Game-stats dashboard OSS (layout/IA inspiration, any stack)

### 4.1 OpenDota (odota/web) — the OSS gold standard for esports IA ★★★★★
- **URL:** https://github.com/odota/web — 1,177★, active, **MIT**. React/Redux; inspiration + copyable token values.
- **Design tokens** (`src/components/constants.ts`) — striking overlap with our navy language:

```ts
// From odota/web (MIT) — src/components/constants.ts (excerpt)
primarySurfaceColor:   "rgb(22, 40, 62)",     // ~= our #121E2E card navy!
secondarySurfaceColor: "rgb(39, 39, 58)",
tableHeaderSurfaceColor: "rgba(0, 0, 0, .3)",
tableRowOddSurfaceColor:  "rgba(255, 255, 255, .019)",  // 2%-alpha zebra rows
tableRowEvenSurfaceColor: "rgba(0, 0, 0, .019)",        // works on ANY surface
textColorPrimary: "rgba(255,255,255,0.87)", textColorSecondary: "rgba(255,255,255,0.6)",
colorGreen: "#66BB6A", colorRed: "#ff4c4c", colorGolden: "rgb(201,175,29)",
colorMutedGreen: "#325233", colorMutedRed: "#523332",   // win/loss ROW washes
colorImmortal: "rgba(17,17,35,0.65)", colorDivine: "rgba(33,41,69,0.45)", // rank chips
```
  Techniques to copy conceptually: (a) **alpha-based zebra striping** that survives theme swaps; (b) **muted green/red row washes** for win/loss lists (not saturated fills); (c) translucent **rank-tier chips** (CSDM's `--cs-rating-tier-*` is the CS equivalent); (d) 87%/60% white two-tier text opacity instead of extra grays.
- **IA patterns** (`src/components/Match/`, `Player/`, `Heroes/`): match page = sticky header (teams, score, duration) + horizontal tab strip (Overview / Performances / Combat / Objectives / Vision / Chat) — same skeleton CSDM uses, and ours should too. Player page = identity header with big KPI row (WR%, GPM-style numbers) → tabbed drill-down (Overview/Matches/Heatmap/Records/Trends). Tables everywhere use **inline horizontal bar fills behind numbers** (`TableValueCell`) — value + context in one cell; trivially portable to a QStyledItemDelegate that paints a token-colored bar behind the text.

### 4.2 Closed-source references (IA notes only, nothing fetchable)
- **Stratz / Leetify / Tracker.gg / FACEIT:** shared layout grammar worth mirroring: (1) hero band = player identity + rank + 3-5 headline KPIs with trend arrows; (2) "session" grouping of recent matches; (3) compact per-match rows: map icon | score | K/D/A | HLTV-ish rating chip colored by tier; (4) skill radar vs. rank-average overlay (Leetify's aim/positioning/utility spider = exactly our coach use-case); (5) benchmark percentile bars ("top 12% flash assists"). All reproducible with Section 3 widgets.
- **lexogrine/hud-manager** — 284★ but license now **NOASSERTION** (custom) → treat as study-only.

### 4.3 Valorant/RL hobby dashboards — low value, license hazards
- `Nikshaan/valorant-tracker`, `carterols/valorant-stats` etc.: **no license** (all-rights-reserved by default) — do not copy; nothing architecturally novel anyway.
- Rocket League: `bakkesmodorg/BakkesModSDK` (282★, no OSS license file) — plugin ecosystem is C++ ImGui overlays; concept worth noting: in-session "live coaching" overlay panel, but no UI code to reuse.
- Conclusion for category 4: OpenDota (MIT) is the only repo worth mining directly; the rest inform layout only.

## 5. Micro-interactions & polish

### 5.1 pyqttoast (niklashenning) — production-grade toasts, MIT ★★★★★
- **URL:** https://github.com/niklashenning/pyqttoast — 151★, **MIT**, PyQt5/6 + PySide6 via qtpy. (C++ port exists: `niklashenning/qt-toast`.)
- **Borrow** (`src/pyqttoast/toast.py`, `drop_shadow.py`): the whole thing is adoptable as a dependency, or mine the mechanics:

```python
# From niklashenning/pyqttoast (MIT) — src/pyqttoast/toast.py (condensed)
self.__opacity_effect = QGraphicsOpacityEffect(); self.__opacity_effect.setOpacity(1)
self.setGraphicsEffect(self.__opacity_effect)
# Fade in = animate the effect's opacity, not the window:
self.__fade_in_animation = QPropertyAnimation(self.__opacity_effect, b"opacity")
self.__fade_in_animation.setDuration(250); self.__fade_in_animation.setStartValue(0)
self.__fade_in_animation.setEndValue(1); self.__fade_in_animation.start()
# Stacking: when a new toast appears, every predecessor gets a
# QPropertyAnimation(self, b"pos") to its recomputed slot — including offsets for
# predecessors still mid-animation. Dismiss: fade-out -> finished.connect(hide).
```
  Duration timer pauses on hover; 7 positions incl. TOP_RIGHT; per-toast accent bar + icon tint — matches our severity system (orange warn, cyan info). Drop shadow via layered translucent frames (`drop_shadow.py`) — cheaper than QGraphicsDropShadowEffect on frameless top-levels.

### 5.2 pyqtcountup — number count-up for KPI reveals, MIT ★★★★
- **URL:** https://github.com/niklashenning/pyqtcountup — **MIT**. QTimeLine-driven label animation with `OutExpo` default (fast-then-settle — correct feel for stat reveals), prefix/suffix, decimals, thousands separator:

```python
# From niklashenning/pyqtcountup (MIT) — usage
countup = CountUp(kd_label, duration=900, decimal_places=2,
                  easing=QEasingCurve.Type.OutExpo)
countup.setStartValue(0); countup.setEndValue(1.27); countup.start()
# Internals: QTimeLine.frameChanged -> format value -> label.setText(...)
```
  Wire to our skeleton→content transition: when a stat card's data lands, shimmer stops and CountUp fires.

### 5.3 Animated toggle & state-machine painting — windscribe-toggle, MIT ★★★★
- **URL:** https://github.com/niklashenning/windscribe-toggle — **MIT**. The cleanest example of **multiple QTimeLines compositing one paintEvent** (icon rotation 0-180°, ring width 0.0-4.0, ring opacity 0-255, plus an infinitely looping 170° half-circle spinner while "TURNING_ON"):

```python
# From niklashenning/windscribe-toggle (MIT) — src/togglebutton/togglebutton.py (condensed)
self.icon_rotation_timeline = QTimeLine(200, self)
self.icon_rotation_timeline.setFrameRange(0, 180)
self.icon_rotation_timeline.frameChanged.connect(self.update)   # repaint per frame
# paintEvent reads .currentFrame() from each timeline:
angle = 90 + self.icon_rotation_timeline.currentFrame()
# TURNING_ON state: two 170-degree arcs whose start angles rotate each frame ->
# indeterminate ring spinner; opacity timeline fades the ring in/out on state change.
```
  This is our pattern for the demo-analysis progress ring and any ON/OFF/BUSY control. For a standard settings toggle: same idea, one timeline moving the knob x + lerping track color (PyOneDark ships `PyToggle`, MIT, as a starting point).
- C++ reference for ripple/ink effects: `laserpants/qt-material-widgets` (**BSD-3**) `qtmaterialripple.cpp` — overlay widget + QParallelAnimationGroup (radius↑, opacity↓).

### 5.4 Icons: pytablericons — 5,237 MIT icons, runtime-tintable ★★★★
- **URL:** https://github.com/niklashenning/pytablericons — **MIT** wrapper over Tabler Icons (**MIT**): `TablerIcons.load(OutlineIcon.CROSSHAIR, size=18, color='#00D9FF')` → QPixmap-ready. Solves the themed-icon problem for all three retro themes without hand-drawn assets; complements Breeze's `.svg.in` templating for stock-widget primitives.

### 5.5 Small MIT widgets worth cherry-picking
- `niklashenning/pyqttooltip` (37★, MIT) — fade+slide tooltips with placement logic, triangle pointer, delay management: replace stock QToolTip on stat terms.
- `niklashenning/pyqt-advanced-slider` (MIT) — clean int/float slider — playback speed control.
- `marcohenning/pyqt-animated-line-edit` (22★, MIT) — floating-label QLineEdit (label animates up on focus) — onboarding wizard inputs.
- `marcohenning/pyqt-loading-button` (MIT) — button with built-in spinner state — "Analyze demo" CTA.

### 5.6 Original recipes (no upstream exists — ours)
**Skeleton shimmer** (searched: no quality PyQt implementation exists — write once, reuse):

```python
# Original — shimmer skeleton for stat cards (navy theme)
class Skeleton(QWidget):
    def __init__(self, radius=8, parent=None):
        super().__init__(parent)
        self._x = 0.0
        anim = QVariantAnimation(self, startValue=-0.4, endValue=1.4,
                                 duration=1200, loopCount=-1)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.valueChanged.connect(lambda v: (setattr(self, "_x", v), self.update()))
        anim.start()
        self._radius = radius
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        p.setClipPath(path)
        p.fillPath(path, QColor("#16233A"))                     # base: card+1
        g = QLinearGradient(self.width() * (self._x - 0.3), 0,
                            self.width() * (self._x + 0.3), 0)  # moving band
        g.setColorAt(0.0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 16))            # 6% white sheen
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, g)
```
**Easing vocabulary** (QEasingCurve ships 41 curves — standardize; easings.net is the naming reference): `OutCubic` 150-250ms for hovers/toggles; `InOutQuart` 400-500ms for panel collapse (PyDracula's choice); `OutExpo` 700-900ms for count-ups; `OutBack` (overshoot) only for the ghost-marker "snap" and toast entry; never `InOut*` for exits — use `In*` fast (120ms).
**Choreography:** stagger card entrances with `QSequentialAnimationGroup` + 40ms `QPauseAnimation` between `QParallelAnimationGroup`s of (opacity, 12px translate-up) — the "cascade in" all polished dashboards share.

## Top 12 techniques to adopt (ranked)

Ranked by impact on this redesign × directness of adoption × license safety.

### 1. awpy world→radar coordinate transform + VDF-derived map calibration — **MIT**
Foundation of the 2D tactical viewer; also gives multi-level (Nuke/Vertigo) handling for free.
```python
# From pnxenopoulos/awpy (MIT) — awpy/plot/utils.py
px = (world_x - MAP_DATA[m]["pos_x"]) / MAP_DATA[m]["scale"]
py = (MAP_DATA[m]["pos_y"] - world_y) / MAP_DATA[m]["scale"]   # y flipped
lower = world_z <= MAP_DATA[m]["lower_level_max_units"]
```
License note: MIT — adapt freely, keep attribution header. Regenerate `map-data.json` from CS2's own `resource/overviews` VDFs per game update.

### 2. CSDM player-state glyph vocabulary — **MIT**
Team dot + white ring, red ring focus, HP pie-drain, flash white pie r16 / 5.25s, plant/defuse progress pies (3.2s / 5-10s), scoping-length view line, C4 icon, name label. The complete visual grammar, proven at scale.
```ts
// From akiver/cs-demo-manager (MIT) — use-draw-players.ts
context.arc(x, y, zoomedSize(8), 0, 2*Math.PI);
context.strokeStyle = isFocused ? '#ff0000' : '#fff';
context.fillStyle = getTeamColor(side); context.fill(); context.stroke();
```
License note: MIT — port to QPainter verbatim-in-spirit; keep a `# Ported from cs-demo-manager (MIT)` note.

### 3. csgoverview split-ring health + layered view cone — **MIT**
Health as top-arc (team color) vs bottom-arc (0.6× darkened); cone as 3 arcs (±20°, ±10°, ±5° at r+1..3) = soft glow with zero blur cost; other-elevation entities at alpha 100.
```go
// From Linus4/csgoverview (MIT) — draw.go
gfx.ArcColor(r, x, y, rad, 90-hp*180/100, 90+hp*180/100, teamColor)
gfx.ArcColor(r, x, y, rad+1, view-20, view+20, colorLOS)  // + rad+2/±10, rad+3/±5
```
License note: MIT — technique port to QPainter `drawArc` spans (Qt uses 1/16° units).

### 4. BreezeStyleSheets compile pipeline: token JSON → `^token^` QSS + themed `.svg.in` icons → QRC — **MIT**
The direct upgrade path for our W3C-tokens→QSS engine: add (a) SVG icon templating so arrows/checks/branch glyphs re-tint per retro theme, (b) em-based sizing, (c) per-dependency extension QSS.
```css
/* From Alexhuszagh/BreezeStyleSheets (MIT) */
QScrollBar:vertical { background-color: ^scrollbar:background^; width: 0.65em; }
```
```python
contents = contents.replace(f'^{key}^', color)   # configure.py::replace_by_name
```
License note: MIT — adapt configure.py wholesale if useful.

### 5. Three-layer token architecture + domain tokens + alpha zebra — **MIT** (CSDM + OpenDota)
Primitives → semantic aliases flipped per theme → engine exposure; publish domain tokens (`--color-ct/--color-terro`, rating-tier ramp, bombsite A/B); zebra rows via ±2%-alpha overlays; 87%/60% white text tiers.
```css
/* From akiver/cs-demo-manager (MIT) */ --color-ct:#378ef0; --color-terro:#f29423;
/* From odota/web (MIT) */ tableRowOddSurfaceColor: rgba(255,255,255,.019)
```
License note: both MIT. Our three retro themes = three semantic maps over one primitive set.

### 6. LexoRadar position/rotation smoothing + grenade lifecycle — **MIT**
Mean-of-last-5 position smoothing; shortest-arc angle accumulation (no 350°→10° spin); z-based dot scale; `inair/landed/exploded` utility state machine. Exactly what the pro-ghost overlay needs to feel broadcast-grade.
```ts
// From lexogrine/cs2-react-hud (MIT) — LexoRadar/utils.ts
if (Math.abs(mod) > 180) mod -= 360 * Math.sign(mod);
directions[id] += mod;   // accumulate; animate the accumulated angle
```
License note: MIT (the CS2 repo; the old csgo-react-hud is GPL — don't touch).

### 7. Timeline scrubber with event indicators — **MIT**
`x = W·(tick−start)/(end−start)`; kill/plant/explode/freezetime markers absolutely positioned; click-to-seek inverse. One QWidget paint + hit-test.
```ts
// From akiver/cs-demo-manager (MIT) — playback-bar/timeline.tsx
const leftX = timelineWidth * (kill.tick - startTick) / (endTick - startTick);
```
License note: MIT.

### 8. PyDracula sidebar rail collapse + frameless window kit — **MIT**
60px icon rail ↔ 240px labeled nav, `QPropertyAnimation(minimumWidth)`, `InOutQuart` 500ms; dual-drawer choreography via `QParallelAnimationGroup`; title-bar drag + QSizeGrip corners.
```python
# From Wanderson-Magalhaes PyDracula (MIT)
anim = QPropertyAnimation(sidebar, b"minimumWidth"); anim.setEasingCurve(QEasingCurve.InOutQuart)
```
License note: MIT. (Avoid zhiyiYo/PyQt-Frameless-Window — GPL-3.0.)

### 9. qt-material density scale — **BSD-2-Clause**
One `density_scale` knob subtracted from every height/padding at template-render time = a real "compact tactical" display setting.
```python
# From UN-GCPDS/qt-material (BSD-2) — density filter
density = (value + density_interval * int(density_scale) - border * 2) * scale
```
License note: BSD-2 — copy the filter into our QSS generator.

### 10. pyqttoast mechanics — **MIT**
`QGraphicsOpacityEffect` fades + `b"pos"` re-slotting animations for the stack (offset-aware while predecessors are mid-flight); hover pauses dismiss timer; layered-frame drop shadow.
```python
# From niklashenning/pyqttoast (MIT)
QPropertyAnimation(self.__opacity_effect, b"opacity")  # fade
QPropertyAnimation(self, b"pos")                       # stack re-slot
```
License note: MIT — usable as a dependency or mined into our toast system.

### 11. QPicture caching + transparent-background sparklines — **MIT**
Pre-render heavy custom items once (`QPicture`), blit per frame — the difference between 60fps and jank on the economy chart and radar trails; pyqtgraph `background=None` sparklines with 16%-alpha fills for stat cards.
```python
# From pyqtgraph/pyqtgraph (MIT) — examples/customGraphicsItem.py
self.picture = QPicture(); p = QPainter(self.picture); ...; p.end()
def paint(self, p, *a): p.drawPicture(0, 0, self.picture)
```
License note: MIT.

### 12. KPI reveal pairing: count-up + shimmer skeleton — **MIT + original**
`QTimeLine` + `OutExpo` count-up (pyqtcountup, MIT) fired exactly when the shimmer skeleton (original recipe, §5.6 — moving 6%-white `QLinearGradient` band under a rounded clip) swaps out. Standardized easing vocabulary: `OutCubic` hover, `InOutQuart` panels, `OutExpo` numbers, `In*` exits.
```python
CountUp(label, duration=900, easing=QEasingCurve.Type.OutExpo).start()  # MIT
```
License note: pyqtcountup MIT; shimmer is ours.

### Honorable mentions — GPL-3.0, ideas only (NO code)
- **PyQt-Fluent-Widgets** style-registry that re-polishes live widgets on theme change; InfoBar anatomy; acrylic layering (blur + tint + noise). Reimplement from the described behavior.
- **boltobserv** per-map "map pack" folder (radar png + calibration meta + buyzone/logo overlay layers) and OBS-friendly transparent mode.
- **QCustomPlot** dark financial-chart layouts.

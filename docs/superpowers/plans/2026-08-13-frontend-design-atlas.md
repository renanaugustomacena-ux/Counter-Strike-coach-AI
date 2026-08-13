# Frontend Design-Atlas Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the PySide6 frontend (`Programma_CS2_RENAN/apps/qt_app`) to match the 41-frame design atlas in `design/` — calm navy surfaces, dense tactical data display, new chart widgets, Coach as a full screen, Ghost-Mode divergence UI, and research-informed polish — verified screen-by-screen against the frames.

**Architecture:** The existing MVVM structure (screens ← ViewModels ← Worker/QThreadPool), token pipeline (`design/tokens/design-tokens.json` → `tools/gen_design_tokens.py` → `core/design_tokens.py` + QSS template), and component library stay. Work = foundation hygiene → component/chart additions → per-screen rebuilds against frames → polish. Every task is verified with an offscreen screenshot harness (built first) that fixture-injects frame-realistic data through the existing VM signal slots.

**Tech Stack:** PySide6 6.11 (QtWidgets + QtCharts + QPainter custom widgets), QSS from token template, pytest (offscreen), headless Chrome for frame reference renders.

**Spec:** The design atlas IS the spec — `design/frames/NN_*.svg` (render any frame: `& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu --window-size=1440,900 --screenshot=out.png "file:///<abs-path-to-svg>"`), `design/tokens/design-tokens.json`, plus the audit gap report summarized in "Audit facts" below. Frame microcopy (every exact string/color/size) is auto-extracted; regenerate anytime with the snippet in Task 1 notes.

## Global Constraints

- **No `QGraphicsOpacityEffect` / `QGraphicsDropShadowEffect`** — QPainter crashes on Linux (the user's deployment target). Frost/glow/elevation = QSS rgba backgrounds/borders/gradients or custom `paintEvent` only. (Exception that already exists and is guarded: `Card` frosted depth's QChartView guard — do not extend it.)
- **Every user-visible string** goes through `i18n.get_text(key, fallback)`; new keys added to ALL of `Programma_CS2_RENAN/assets/i18n/{en,it,pt}.json` in the same task.
- **No color/size literals in screens/widgets** — only `get_tokens()` fields, `Typography.apply(...)`, and QSS object names/variants. `core/design_tokens.py` is GENERATED — edit `design/tokens/design-tokens.json` and run `python tools/gen_design_tokens.py` (also regenerates `web/shared/tokens.ts`; run with `--check` in doubt).
- **DB access only inside ViewModels via `Worker`**; screens render exclusively from signal payloads. Screen lifecycle: `on_enter()` / `on_leave()` / `retranslate()`.
- **Rating semantics:** > 1.10 green (`tokens.success`), < 0.90 red (`tokens.error`), else yellow (`tokens.warning`); text labels via `theme_engine.rating_label()`. Sides: CT = `tokens.chart_line_primary` (cyan), T = `tokens.chart_line_secondary` (orange).
- **Licenses:** only MIT/Apache/BSD/OFL-derived code/assets; **no GPL**. Fonts bundled are OFL (Inter, Space Grotesk, JetBrains Mono).
- **Commits:** conventional (`feat(ui): …`, `fix(ui): …`, `chore(ui): …`), one per task, **push after every commit** (`git push -u origin feat/frontend-design-atlas` first time, then `git push`).
- **Verification loop per visual task:** run the harness for the touched screens/themes, `Read` the output PNG(s), compare against the frame reference, iterate until faithful; then `python -m pytest Programma_CS2_RENAN/tests/test_qt_core.py -q` must pass (uses offscreen platform automatically on CI; set `$env:QT_QPA_PLATFORM='offscreen'` locally when needed).
- **Branch:** `feat/frontend-design-atlas` (already created off `main`).
- Windows dev machine paths: venv python is `.venv\Scripts\python.exe`; repo root is the CWD. All commands below assume PowerShell from repo root.

## Locked Decisions (do not relitigate mid-task)

1. **Coach becomes a stacked screen** per frames 06/07. The QDockWidget special-case is removed in its own commit (Task 20a) — the dock code carried real debugging history (DOCK-01); removal must be explicit and clean, not silent.
2. **Match Detail keeps 4 tabs** — Overview / Rounds / Economy / Highlights (frame 09 shows exactly these). Highlights tab = MomentumChart + Chronovisor critical-moment cards deep-linking into the Tactical Viewer + existing insights list.
3. **Wallpaper default becomes "None" (flat `surface_base`)** per the calm app frames; the picker keeps all existing wallpapers + gains a None option. Existing users' explicit choice (saved setting) is respected — only the unset default changes.
4. **Nav labels** follow frames: Home · Coach · Match History · Performance · Tactical Viewer · Settings · Help (i18n keys updated in all 3 languages). Screen page titles follow frames: "Dashboard", "RAP Coach Dashboard", "Match History", "Match Detail — {map}", "Advanced Analytics", "Tactical Analyzer", "Settings", "Help Center".
5. **Orphaned screens get wired, not deleted:** `profile` (frame 17) reachable from Settings Quick Links + Home Connectivity; `steam_config` / `faceit_config` reachable from Home Connectivity card + Settings Quick Links + profile Related row. `user_profile` (avatar/bio) stays registered but out of this pass's scope — note only.
6. **web/ TS apps are NOT touched this pass** (inert at runtime: no dist, stub App.tsx). Native Qt path is the product. Exception: `tools/gen_design_tokens.py --check` keeps `web/shared/tokens.ts` in sync if tokens change.
7. **Sounds stay silent** (assets folder absent). Out of scope; documented as known gap.
8. **Ghost-Mode divergence metrics render defensively**: the UI shows whatever `TacticalGhostVM` can provide and renders "—" mono placeholders for absent metrics — no backend model changes in this pass.
9. Where current code is **richer than a frame** (cold-start branches, persisted state, extra filters/grouping), keep behavior and re-skin to the frame; where **structurally conflicting**, the frame wins.

## Audit facts you can rely on (verified 2026-08-13)

- Dead: `themes/cs2.qss`, `themes/csgo.qss`, `themes/cs16.qss` (nothing loads them); `ThemeEngine.get_color()` has zero code callers; `theme_engine.PALETTES` used only for QPalette + tests.
- Missing entirely: RadarChart, UtilityBarChart, full RatingSparkline (only chrome-less `MiniSparkline` exists), Coach drivers list, Style-summary box, Ghost-Mode UI, map zones/C4/trails, timeline star markers, score strip, Kill-Enrichment + Utility-per-round blocks, 2-col HLTV bars, economy half-divider + summary row, rounds table cols (FirstKill/Bomb/EnemiesLeft/Notes) + half separator + totals footer, wizard skip/tree/tip, help structure (steps/callouts/related/external), settings theme cards + live preview + quick links + wipe, sidebar `nav_section` labels (QSS rule exists, unused), indeterminate progress bar variant, `Inter` + `Space Grotesk` fonts (assets/fonts holds only README.txt).
- Hex/QFont violations cluster in: `help_screen.py` (156,180,198), `user_profile_screen.py` (27-33,111,164), `steam_config_screen.py` (97f,200-255), `faceit_config_screen.py` (76f), `widgets/tactical/player_sidebar.py` (33,49,63,65,109,114,136,197,202,203,221,235), `widgets/tactical/map_widget.py` (24-40,60), `widgets/tactical/timeline_widget.py` (11-15), plus `QFont("Roboto", …)` in `card.py:80`, `empty_state.py:84,94,102`, `progress_ring.py:78`, `stat_badge.py`, `section_header.py`, `wizard_screen.py`, `settings_screen.py:387`.
- AppState signals available for fixtures: `service_active_changed(bool)`, `coach_status_changed(str)`, `parsing_progress_changed(float)`, `belief_confidence_changed(float)`, `total_matches_changed(int)`, `training_changed(dict)`, `notification_received(str,str)`.
- VM signal shapes: `MatchHistoryViewModel.matches_changed(list[dict])`; `MatchDetailViewModel.data_changed(dict, list, list, dict)`; `PerformanceViewModel.data_changed(list, dict, dict, dict)`; `CoachViewModel.insights_loaded(list)`; `CoachingChatViewModel.messages_changed(list)`; `ProComparisonViewModel.data_changed(dict)`; `TacticalChronovisorVM.scan_complete(list, int)`. Read each VM before writing fixtures — payload key names are authoritative there.

## Phase map

- **P0 Foundation (Tasks 1–6):** screenshot harness + fixtures · fonts · splash tokens · QPalette from tokens · dead QSS removal · token-bypass cleanup.
- **P1 Chrome (Task 7):** sidebar/titlebar/wallpaper-default polish per frame 05.
- **P2 Components (Tasks 8–11):** frame-33/20 primitives, chat components, new shared primitives.
- **P3 Charts (Tasks 12–15):** RadarChart, RatingSparkline, UtilityBarChart, Economy/Momentum upgrades. **Invoke the `dataviz` skill before starting P3.**
- **P4 Screens (Tasks 16–27):** Home, Coach (+dock removal), Match History, Match Detail ×3 tabs + Highlights, Performance, Tactical Viewer, Ghost Mode, Pro Comparison, Settings, Profile, Wizard, Help.
- **P5 Motion (Task 28):** restrained micro-animations within the effects ban.
- **P6 Differentiation (Task 29):** consume research dossiers; **invoke the `frontend-design` skill first**; commit dossiers to `docs/research/`.
- **P7 Docs & i18n sweep (Task 30).**
- **P8 Final verification (Task 31):** full matrix render + review + fixes.

---

### Task 1: Offscreen screenshot harness + fixture library

**Files:**
- Create: `tools/ui_screenshot.py`
- Create: `tools/ui_fixtures.py`
- Test: `Programma_CS2_RENAN/tests/test_ui_harness.py`

**Interfaces:**
- Produces: CLI `python tools/ui_screenshot.py --screens home,match_history --themes CS2 --out docs/ux-audit/renders-atlas [--no-fixtures] [--size 1440x900]`; writes `<out>/<THEME>/<screen>.png`. Python API `tools.ui_fixtures.inject(screen_name: str, screen: QWidget) -> bool` (returns False when no fixture exists — harness then renders the natural cold-start state).
- Consumes: `app._create_screens(theme)`, `MainWindow`, `ThemeEngine` — construction only; NEVER `console.boot()`, `lifecycle.launch_daemon()`, `_ensure_sbert_model()`, `start_polling()`.

**Fixture data principle:** mirror the frames' exact numbers so renders are comparable: 47 personal demos · 2,148 pro indexed · belief 73% · rating trend ending 1.17 · last match de_mirage 2026-04-22 21:14 rating 1.34 K/D 1.26 ADR 82.3 KAST 78% HS 52% · pro rows ZywOo (de_mirage 1.47) and NiKo (de_inferno 1.21) with PRO badge · 24-round round list (7-5 T half, 16—8 final) · economy T avg $5,000 / CT $4,942 / 20 full buys / 3 force / 1 eco · per-map {Mirage 1.22, Inferno 1.12, Nuke 0.94, Ancient 0.78, Overpass 1.08, Anubis 1.18} · insights: "Over-peeking on A-site default" High / "Utility burn before engage" Medium / "Crosshair placement improving" Low / "Pistol round buy pattern" Low · chat per frame 07 (3 coach msgs incl. confidence 0.82 footnote, 2 user msgs, 3 suggestion chips) · pro comparison ZywOo vs donk with the full H2H metric table from frame 15.

- [ ] **Step 1: Write the harness skeleton** — `tools/ui_screenshot.py`:

```python
"""Offscreen screenshot harness — renders real screens with fixture data.

Never boots backend services. Safe on any machine.
Usage:
    python tools/ui_screenshot.py --screens home,coach --themes CS2 --out docs/ux-audit/renders-atlas
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.chdir(REPO)

ALL_SCREENS = [
    "home", "coach", "match_history", "match_detail", "performance",
    "tactical_viewer", "pro_comparison", "pro_player_detail", "settings",
    "profile", "user_profile", "steam_config", "faceit_config",
    "wizard", "help",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", default=",".join(ALL_SCREENS))
    ap.add_argument("--themes", default="CS2")
    ap.add_argument("--out", default="docs/ux-audit/renders-atlas")
    ap.add_argument("--no-fixtures", action="store_true")
    ap.add_argument("--size", default="1440x900")
    args = ap.parse_args()
    w, h = (int(x) for x in args.size.split("x"))

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    from Programma_CS2_RENAN.apps.qt_app import app as qt_app_module
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow
    from tools import ui_fixtures

    for theme_name in args.themes.split(","):
        theme = ThemeEngine()
        theme.register_fonts()
        theme.apply_theme(theme_name, app)

        window = MainWindow()
        window.set_wallpaper("")  # flat per design; wallpaper covered by settings render
        screens = qt_app_module._create_screens(theme)
        for name, widget in screens.items():
            window.register_screen(name, widget)
        window.resize(w, h)
        window.show()
        app.processEvents()

        out_dir = Path(args.out) / theme_name.replace(".", "")
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in args.screens.split(","):
            if name not in screens:
                print(f"skip unknown screen: {name}")
                continue
            if not args.no_fixtures:
                ui_fixtures.inject(name, screens[name])
            window.switch_screen(name)
            for _ in range(6):
                app.processEvents()
            pm = window.grab()
            dest = out_dir / f"{name}.png"
            pm.save(str(dest), "PNG")
            print(f"wrote {dest}")
        window.close()
        app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `switch_screen` triggers `on_enter()` which starts VM loads against the local DB — harmless reads; fixtures then overwrite via direct slot calls inside `inject()` AFTER `switch_screen`. To guarantee fixture wins over a late async DB result, `inject()` is called after `switch_screen` returns and events settle — move the `inject` call after `window.switch_screen(name)` + one `processEvents()` round. Implement it that way.

- [ ] **Step 2: Write `tools/ui_fixtures.py`** — one `inject_<screen>` per data screen calling the screen's existing signal-handler slots directly (Read each screen file first to confirm slot names; the audit lists VM signal shapes). Shape example:

```python
"""Frame-realistic fixture payloads, injected via the screens' own VM slots."""
from __future__ import annotations

from typing import Any

SAMPLE_MATCHES: list[dict[str, Any]] = [
    {
        "demo_name": "2026-04-22_mirage_comp.dem", "map_name": "de_mirage",
        "played_at": "2026-04-22 21:14", "rating_2_1": 1.34, "kd_ratio": 1.26,
        "adr": 82.3, "kills": 24, "deaths": 19, "kast": 0.78, "hs_pct": 0.52,
        "clutches_won": 2, "clutches_total": 3, "demo_size_mb": 312,
        "is_pro": False,
    },
    # … ≥8 rows incl. ZywOo/NiKo pro rows per frame 08 …
]


def inject(name: str, screen: Any) -> bool:
    fn = globals().get(f"inject_{name}")
    if fn is None:
        return False
    fn(screen)
    return True


def inject_match_history(screen: Any) -> None:
    screen._on_matches_changed(SAMPLE_MATCHES)
```

(Fill every fixture with the exact frame numbers listed in the task header. Where a screen slot expects different key names — the VM file is authoritative — adapt the fixture, never the screen.)

- [ ] **Step 3: Write the failing test** — `Programma_CS2_RENAN/tests/test_ui_harness.py`:

```python
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_harness_renders_home_and_history(tmp_path):
    out = tmp_path / "renders"
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "ui_screenshot.py"),
         "--screens", "home,match_history", "--themes", "CS2",
         "--out", str(out)],
        capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    for name in ("home", "match_history"):
        png = out / "CS2" / f"{name}.png"
        assert png.exists() and png.stat().st_size > 20_000, name
```

- [ ] **Step 4: Run test — expect FAIL** (`ModuleNotFoundError: tools.ui_fixtures` or missing file). `& .venv\Scripts\python.exe -m pytest Programma_CS2_RENAN/tests/test_ui_harness.py -q`
- [ ] **Step 5: Implement until the test passes**, then render and **Read** both PNGs; confirm: window chrome + sidebar visible, match rows populated with fixture data (not skeletons).
- [ ] **Step 6: Run the full Qt suite** `& .venv\Scripts\python.exe -m pytest Programma_CS2_RENAN/tests/test_qt_core.py Programma_CS2_RENAN/tests/test_ui_harness.py -q` — all pass.
- [ ] **Step 7: Commit + push** — `feat(tooling): offscreen UI screenshot harness with frame-realistic fixtures`

### Task 2: Bundle Inter, Space Grotesk, JetBrains Mono weights

**Files:**
- Create: `Programma_CS2_RENAN/assets/fonts/Inter-{Regular,Medium,SemiBold,Bold}.ttf`, `SpaceGrotesk-{Regular,Medium,Bold}.ttf`, `JetBrainsMono-{Medium,SemiBold,Bold}.ttf`
- Modify: `Programma_CS2_RENAN/assets/fonts/README.txt` (sources + OFL license notes)
- Test: extend `Programma_CS2_RENAN/tests/test_ui_harness.py`

**Interfaces:** Consumes `ThemeEngine.register_fonts()` auto-scan (already implemented — no code change). Produces: "Inter", "Space Grotesk" families available; QSS chains resolve as designed.

Already-downloaded archives (this machine, session scratchpad): `…\scratchpad\fonts\inter\extras\ttf\Inter-{Regular,Medium,SemiBold,Bold}.ttf`, `…\scratchpad\fonts\jbm\fonts\ttf\JetBrainsMono-{Medium,SemiBold,Bold}.ttf`, `…\scratchpad\fonts\sg\…\SpaceGrotesk-{Regular,Medium,Bold}.ttf`. If absent (fresh session), re-download: Inter `https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip` · JetBrains Mono `https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip` · Space Grotesk `https://github.com/floriankarsten/space-grotesk/releases/download/2.0.0/SpaceGrotesk-2.0.0.zip`. Exclude macOS `._*` junk files.

- [ ] **Step 1: Failing test** — add to `test_ui_harness.py`:

```python
def test_design_fonts_registered():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    _ = QApplication.instance() or QApplication([])
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

    ThemeEngine().register_fonts()
    fams = set(QFontDatabase.families())
    assert "Inter" in fams
    assert "Space Grotesk" in fams
    assert "JetBrains Mono" in fams
```

- [ ] **Step 2: Run — expect FAIL** (Inter/Space Grotesk absent).
- [ ] **Step 3: Copy the 10 TTFs** into `Programma_CS2_RENAN/assets/fonts/`; update `README.txt` listing each family, version, source URL, SPDX `OFL-1.1`.
- [ ] **Step 4: Run — expect PASS.** Then re-render `home` via harness and **Read** it — text metrics visibly change (Inter), titles keep working.
- [ ] **Step 5: Commit + push** — `feat(ui): bundle Inter, Space Grotesk, JetBrains Mono (OFL) design fonts`

### Task 3: Splash screen consumes tokens

**Files:**
- Modify: `Programma_CS2_RENAN/apps/qt_app/app.py` (`_create_splash`, lines ~21-63)

**Interfaces:** Consumes `from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens` — splash runs before theme selection, so read the saved theme first: `get_setting("ACTIVE_THEME", "CS2")` → `get_tokens(name)`.

- [ ] **Step 1:** Replace every hardcoded hex in `_create_splash` with token fields: gradient `surface_base` → `surface_sunken`; accent bars `accent_primary`; title `text_primary`; subtitle `text_secondary`; version `text_tertiary`. Fonts: keep families but title uses "Space Grotesk" (falls back fine pre-registration? No — `_create_splash` runs BEFORE `register_fonts`; move `theme.register_fonts()` to before splash creation in `main()`: instantiate `ThemeEngine` first, call `register_fonts()`, then `_create_splash(app_version, tokens)`, then `_apply_theme` reuses the same engine instance — adjust `_apply_theme` signature to accept the engine).
- [ ] **Step 2:** Visual check: harness doesn't cover splash; verify by running `& .venv\Scripts\python.exe -c` snippet constructing the splash offscreen and saving `splash.pixmap().save(...)`; **Read** the PNG (navy #0B1628 bg, orange #FF6A00 bar for CS2 theme).
- [ ] **Step 3:** Full Qt suite passes. **Commit + push** — `fix(ui): splash screen renders from design tokens, honoring active theme`

### Task 4: QPalette from tokens; retire PALETTES + get_color

**Files:**
- Modify: `Programma_CS2_RENAN/apps/qt_app/core/theme_engine.py`
- Modify: `Programma_CS2_RENAN/tests/test_qt_core.py:335-355` (PALETTES tests)
- Modify: `Programma_CS2_RENAN/apps/README.md`, `README_IT.md`, `README_PT.md` (the "use ThemeEngine.get_color" rule line → "use get_tokens()")

**Interfaces:** Produces: `ThemeEngine.apply_theme` builds `QPalette` from `DesignTokens` (`QColor(tokens.surface_base)` etc.). Removes: `PALETTES`, `get_color`, `rgba_to_qcolor`, `COLOR_*` module constants (keep `RATING_GOOD/RATING_BAD/rating_color/rating_label` — used by screens; reimplement `rating_color` returning `QColor(get_tokens().success)` etc. so it theme-tracks).

- [ ] **Step 1: Rewrite tests first** — replace the PALETTES assertions with:

```python
def test_qpalette_derives_from_tokens(qapp):
    from PySide6.QtGui import QColor
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

    eng = ThemeEngine()
    eng.apply_theme("CS2", qapp)
    pal = qapp.palette()
    assert pal.color(pal.ColorRole.Window) == QColor(get_tokens("CS2").surface_base)
    assert pal.color(pal.ColorRole.Highlight) == QColor(get_tokens("CS2").accent_primary)
```

(Reuse the existing `qapp` fixture pattern in `test_qt_core.py` — read the file's fixtures first.)
- [ ] **Step 2:** Run — FAIL (old palette). Implement: QPalette mapping Window=`surface_base`, WindowText=`text_primary`, Base=`surface_sunken`, AlternateBase=`surface_raised`, Text=`text_primary`, Button=`surface_raised`, ButtonText=`text_primary`, Highlight=`accent_primary`, HighlightedText=`text_inverse`, ToolTipBase=`surface_overlay`, ToolTipText=`text_primary`, PlaceholderText=`text_tertiary`, Link=`accent_primary`. Delete PALETTES/get_color/rgba_to_qcolor/COLOR_* and fix `rating_color` to tokens.
- [ ] **Step 3:** Grep repo for `get_color(`/`PALETTES` — only docs remain; update the 3 apps READMEs rule line.
- [ ] **Step 4:** Suite green; harness render `settings` all 3 themes, **Read** them (combo popups/tooltips now navy not gray). **Commit + push** — `refactor(ui): QPalette derives from design tokens; remove legacy PALETTES`

### Task 5: Delete dead theme QSS files

**Files:**
- Delete: `Programma_CS2_RENAN/apps/qt_app/themes/{cs2,csgo,cs16}.qss`
- Modify: `core/qss_generator.py` docstring; `apps/qt_app/README.md` + `_IT` + `_PT` (Directory Structure + ThemeEngine sections)

- [ ] **Step 1:** `git rm` the three files; fix docstring ("Replaces three duplicate QSS files" → "Single template"); update the 3 READMEs' tree + theme copy.
- [ ] **Step 2:** Suite green; harness spot-render `home` CS2/CSGO/CS16 unchanged. **Commit + push** — `chore(ui): remove dead per-theme QSS files (template is sole source)`

### Task 6: Token-bypass cleanup (mechanical)

**Files:**
- Modify (hex → tokens, QFont → Typography): `screens/help_screen.py`, `screens/user_profile_screen.py`, `screens/steam_config_screen.py`, `screens/faceit_config_screen.py`, `screens/wizard_screen.py`, `screens/settings_screen.py:387`, `widgets/components/{card,empty_state,progress_ring,stat_badge,section_header}.py`, `widgets/tactical/{player_sidebar,map_widget,timeline_widget}.py`

**Interfaces:** tactical widgets replace module-level `QColor` constants with instance lookups refreshed from tokens; pattern:

```python
def _palette(self):
    t = get_tokens()
    return {
        "ct": QColor(t.chart_line_primary), "t": QColor(t.chart_line_secondary),
        "dead": QColor(t.text_disabled), "selected": QColor(t.accent_primary),
    }
```

called in `paintEvent` (cheap dict; QColor ctor per paint is fine at 60fps for ≤20 objects — measure only if playback stutters). Role colors in `user_profile_screen.py` map to semantic tokens: entry=`error`, awper=`info`, igl=accent, support=`success`, lurker=`warning`, default=`text_secondary`.

- [ ] **Step 1:** Sweep each listed file; replace literals. `QFont("Roboto", n, weight)` → `Typography.apply(label, role)` or `Typography.font(role)` (read `core/typography.py` first for the exact API; extend it with a `font(role) -> QFont` helper if only `apply` exists — add matching unit test in `test_qt_core.py`).
- [ ] **Step 2:** Grep-verify: `#[0-9a-fA-F]{6}` under `apps/qt_app/{screens,widgets}` returns ZERO matches (allow `#` only inside comments/QSS-template).
- [ ] **Step 3:** Harness render `help,steam_config,faceit_config,tactical_viewer` ×3 themes; **Read**; colors now theme-track. Suite green. **Commit + push** — `refactor(ui): retire hex/QFont literals for tokens + Typography across screens and tactical widgets`

---

### Task 7: Chrome polish — sidebar, titlebar, wallpaper default (frame 05)

**Files:**
- Modify: `widgets/components/nav_sidebar.py`, `themes/base.qss.template`, `core/theme_engine.py` (`_update_wallpaper`), `screens/settings_screen.py` (wallpaper "None"), `main_window.py` (default window size), `assets/i18n/{en,it,pt}.json`

**Frame reference:** `design/frames/05_home.svg` sidebar column + `33_component_library.svg` NAVIGATION row.

- [ ] **Step 1:** Sidebar per frame: brand label letter-spacing 3px caption-size bold accent (QSS `#accent_label` gains `letter-spacing: 3px; font-size: ${font_size_caption}px;` via a dedicated `QLabel#sidebar_brand` rule instead — add rule, set objectName in nav_sidebar); nav item height 40px (already); collapsed mode: buttons show icon-only + tooltip with label + shortcut (`btn.setToolTip(f"{label} — {shortcut}")`, populate from a dict passed by MainWindow or duplicate the table — put the shortcut text into NAV_ITEMS as a 4th field and import it in main_window to build QShortcuts from the same source of truth). Version label bottom mono-tertiary: objectName `version_label` + QSS rule (mono family, `${text_tertiary}`).
- [ ] **Step 2:** Wallpaper default None: in `ThemeEngine._update_wallpaper`, when `get_setting("WALLPAPER_FILE", None)` is None → `self._wallpaper_path = ""` (flat); settings picker gains first option "None" writing `WALLPAPER_FILE=""`; picking a file persists it (read `settings_screen.py` current wallpaper persistence first — key name may differ; reuse it).
- [ ] **Step 3:** `MainWindow` default size 1440×900 (`self.resize(1440, 900)` after `setMinimumSize`).
- [ ] **Step 4:** i18n keys for any new strings (`nav.tooltip` pattern not needed if composed from existing labels + shortcut text).
- [ ] **Step 5:** Harness render `home` ×3 themes + one collapsed-sidebar render (add `--collapse-nav` flag to harness calling `window._nav_sidebar.toggle_collapse()` before grab). **Read**; compare against frame 05 left column. Suite green. **Commit + push** — `feat(ui): frame-05 chrome — sidebar brand/tooltips, flat default background, 1440x900 default`

### Task 8: Component library alignment (frames 33 + 20)

**Files:**
- Modify: `widgets/components/{status_chip,stat_badge,card,empty_state,progress_ring}.py`, `widgets/toast.py`, `widgets/skeleton.py`, `themes/base.qss.template`
- Create: `widgets/components/pro_badge.py`
- Test: extend `Programma_CS2_RENAN/tests/test_qt_core.py`

**Frame reference:** `33_component_library.svg` (controls/badges/toast/loading rows), `20_loading_empty_states.svg` (skeleton/empty/toast/progress specs).

- [ ] **Step 1:** `ProBadge(QLabel)` — orange outline pill, mono bold caption "PRO", QSS `QLabel#pro_badge { border: 1px solid ${accent_primary}; color: ${accent_primary}; border-radius: ${radius_sm}px; padding: 1px 8px; font-family: 'JetBrains Mono'…; font-weight: 700; font-size: ${font_size_caption}px; }` + `[side="ct"]`/`[side="t"]` variants for T-SIDE/CT-SIDE chips per frame 33. Unit test: property set → styleSheet polish (assert objectName + property round-trip).
- [ ] **Step 2:** StatusChip: severity dot uses semantic tokens (already) + add `neutral` gray via `text_tertiary`; StatBadge: rating variant applies `rating_color` + caption threshold line per frame 33 (value + threshold caption mono-tertiary).
- [ ] **Step 3:** EmptyState per frame 20: icon inside 64px rounded-square `surface_sunken` well; title subtitle CTA + ghost link row (API already close — extend with `link_text`/`link_cb` optional ghost button).
- [ ] **Step 4:** Toasts per frame 20/33: add title row (severity word bold) above message, mono caption `auto · 5s|8s|12s` bottom-right (skip for critical), keep 4 QSS severities.
- [ ] **Step 5:** Indeterminate progress bar: `QProgressBar#indeterminate` with `setRange(0,0)` styled: chunk `${accent_primary}`, 8px height (Qt animates busy chunk natively; verify offscreen renders a chunk — if the busy animation doesn't paint offscreen, grab after `app.processEvents()` loop; acceptable if static there).
- [ ] **Step 6:** ProgressRing: thickness 8, start angle 90° (12 o'clock) sweep CCW, center label `Typography` stat role, size presets constants `SMALL=48, DEFAULT=64, COACH=80, HERO=128`.
- [ ] **Step 7:** Harness: render `match_history` (skeleton state via `--no-fixtures`), and a new `--gallery` mode rendering a synthetic QWidget grid of [buttons variants, chips, ProBadge, toasts × 4, EmptyState, ProgressRing × 4 sizes, indeterminate bar] to `<out>/<THEME>/gallery.png` (add `tools/ui_gallery.py` composing these — keep under 120 lines). **Read** vs frames 33/20. Suite green. **Commit + push** — `feat(ui): align component primitives with frames 33/20 (ProBadge, toast titles, empty-state wells, ring presets, indeterminate bar)`

### Task 9: Chat component set (frame 07)

**Files:**
- Create: `widgets/coaching/chat_panel.py` (namespace dir exists, empty)
- Modify: `themes/base.qss.template`, `assets/i18n/{en,it,pt}.json`
- Test: extend `test_qt_core.py`

**Interfaces:** Produces `ChatPanel(QWidget)` with API: `set_status(online: bool, backend: str, model: str)`, `add_message(role: str, text: str, meta: str | None = None)` (`role in {"coach","user","system"}`; `meta` = mono footnote like `confidence 0.82 · 4 demos referenced · RAP-Pedagogy`), `set_suggestions(list[str])` (chip row, click → `suggestion_clicked(str)` signal), `message_submitted(str)` signal from input+Send, `clear()`. Consumed by Task 20 CoachScreen (embeds it; wires to `CoachingChatViewModel`).

- [ ] **Step 1:** Failing unit test: construct ChatPanel offscreen, `add_message("coach","hi",meta="confidence 0.82")`, assert bubble count == 1 and meta label text.
- [ ] **Step 2:** Implement per frame 07: header row (`Chat` bold + status dot Online green/Offline red + mono `ollama · gemma3:e2b` caption + stretch + Clear ghost btn + collapse chevron); scroll area of bubbles — coach: left, `surface_raised` rounded-md, max-width 60%; user: right, info-tinted bg `rgba` of `info` at 15% (add QSS `QFrame#chat_bubble[role="user"]` etc. — colors via new token-composed rules using existing tokens only); system: centered caption; meta footnote mono-tertiary under bubble; suggestion chips = ghost buttons pill row; input `QLineEdit` placeholder i18n "Ask your coach…" + primary Send (Return submits — `returnPressed`).
- [ ] **Step 3:** i18n keys: `chat.title`, `chat.online`, `chat.offline`, `chat.clear`, `chat.placeholder`, `chat.send` ×3 languages.
- [ ] **Step 4:** Gallery mode renders a populated ChatPanel; **Read** vs frame 07 bottom half. Suite green. **Commit + push** — `feat(ui): ChatPanel component per frame 07 (bubbles, confidence footnotes, suggestion chips)`

### Task 10: Small shared primitives (frames 17/18/19 furniture)

**Files:**
- Create: `widgets/components/{drivers_list,tip_box,numbered_step,db_record_card,mono_footer}.py`
- Modify: `themes/base.qss.template`, `widgets/components/__init__.py`
- Test: extend `test_qt_core.py` (construction + text round-trip each)

**Interfaces (produced, consumed by screen tasks):**
- `DriversList(QWidget)` — `set_rows(list[tuple[str, str]])` where tuple = (severity: "success"|"warning"|"error"|"info", text); renders 8px colored square + body text per row (frame 06 Drivers).
- `TipBox(QFrame)` — dashed 1px `info` border, `Tip`-style bold accent title + body; QSS `QFrame#tip_box { border: 1px dashed ${info}; border-radius: ${radius_md}px; background: transparent; }` (frames 17/18 dashed notes).
- `NumberedStep(QWidget)` — orange filled circle number + bold title + secondary desc (frame 19 steps).
- `DbRecordCard(QFrame)` — title + mono SQL caption + key/value mono grid, values colorable (frame 17 right card).
- `MonoFooter(QLabel)` — bottom-of-screen mono-tertiary annotation (`PlayerMatchStats · demo_name=… · rating_components from hltv_components JSON`); factory `MonoFooter(text_key, fallback)`.
- [ ] **Step 1:** Failing construction tests → implement each (≤80 lines/file) → tests pass.
- [ ] **Step 2:** Gallery render includes all five; **Read** vs frames. Suite green. **Commit + push** — `feat(ui): shared primitives — DriversList, TipBox, NumberedStep, DbRecordCard, MonoFooter`

---

**⛔ Before ANY task in P3 (11–15): invoke the `dataviz` skill.** Its guidance governs axis/grid/label styling; combine with token palette (grid `chart_grid`, axis `chart_axis`, series `chart_line_primary/secondary`, fills `chart_fill_positive/negative`, bg `chart_bg`).

### Task 11: RadarChart widget (frames 15/34)

**Files:**
- Create: `widgets/charts/radar_chart.py`
- Modify: `widgets/charts/__init__.py`
- Test: `Programma_CS2_RENAN/tests/test_charts.py` (new)

**Interfaces:** `RadarChart(QWidget)`: `set_axes(labels: list[str])` (8 for pro comparison; any N≥3 works), `add_series(name: str, values: list[float], color: QColor)` (values 0–100), `clear_series()`, `set_range(lo=0.0, hi=100.0)`. Legend rendered by parent (screen) — widget draws only plot + axis labels.

- [ ] **Step 1: Failing tests** — geometry math pure-function tests:

```python
def test_radar_vertex_positions():
    from Programma_CS2_RENAN.apps.qt_app.widgets.charts.radar_chart import _vertex
    cx, cy, r = 100.0, 100.0, 80.0
    x, y = _vertex(cx, cy, r, idx=0, n=8, frac=1.0)   # top
    assert abs(x - 100.0) < 1e-6 and abs(y - 20.0) < 1e-6
    x, y = _vertex(cx, cy, r, idx=2, n=8, frac=0.5)   # right, half radius
    assert abs(x - 140.0) < 1e-6 and abs(y - 100.0) < 1e-6
```

- [ ] **Step 2:** Implement `_vertex(cx, cy, r, idx, n, frac)` (angle = -90° + idx·360/n) + `paintEvent`: concentric ring grid (4 rings, `chart_grid` pen 1px), spokes (`chart_axis`), per-series filled polygon (color at 25% alpha via `QColor.setAlphaF(0.25)`) + 2px outline + 3px vertex dots, axis labels `Typography` caption at ring radius +14px with quadrant-aware alignment. Background transparent (parent card provides `chart_bg`).
- [ ] **Step 3:** Tests pass; gallery renders a ZywOo-vs-donk radar with frame-15 values (ZywOo orange `accent_primary`, donk info-blue) — **Read** vs frame 15 left panel. **Commit + push** — `feat(charts): QPainter RadarChart with N-axis dual-overlay support`

### Task 12: RatingSparkline widget (frames 12/34)

**Files:**
- Create: `widgets/charts/rating_sparkline.py`
- Test: extend `test_charts.py`

**Interfaces:** `RatingSparkline(QWidget)`: `set_values(list[float])`, `set_reference_lines((0.90, 1.00, 1.10))` (dashed, labeled right-edge mono captions `0.90` red / `1.00` neutral / `1.10` green), area fill under polyline (`chart_line_primary` 18% alpha), line 2px `chart_line_primary`, endpoint dot accent, min-height 64. Distinct from `MiniSparkline` (chrome-less) — do NOT modify MiniSparkline.

- [ ] **Step 1:** Failing test: y-mapping function `_y(value, lo, hi, h)` linear with 6px padding — assert midpoint/extremes.
- [ ] **Step 2:** Implement; gallery render with frame-12 trend (8 points ending 1.17); **Read**. **Commit + push** — `feat(charts): RatingSparkline with HLTV reference lines and area fill`

### Task 13: UtilityBarChart widget (frames 12/34)

**Files:**
- Create: `widgets/charts/utility_bar_chart.py`
- Test: extend `test_charts.py`

**Interfaces:** `UtilityBarChart(QWidget)`: `set_rows(list[tuple[str, float, float]])` = (label, you, pro); horizontal grouped pairs — you-bar `chart_line_primary`, pro-bar `chart_line_secondary`, right-aligned mono value captions `you 12.4` / `pro 15.2` per frame 12; auto max-scale; row height 34px; also single-series mode `set_single(list[tuple[str, float, QColor]])` for frame 34's utility counts variant.

- [ ] **Step 1:** Failing test: width mapping `_w(value, vmax, wmax)` proportional + zero-safe (vmax=0 → 0).
- [ ] **Step 2:** Implement; gallery render frame-12 rows (HE 12.4/15.2, Moly 5.8/5.9, Flash 3.2/2.6, Waste 1.2/0.91 — waste row you-bar `error` red per frame); **Read**. **Commit + push** — `feat(charts): grouped UtilityBarChart (you-vs-pro) with mono value captions`

### Task 14: EconomyChart + MomentumChart — QPainter rewrite, QtCharts retirement (frames 11/34) ⚠ LICENSE

**Files:**
- Rewrite: `widgets/charts/economy_chart.py`, `widgets/charts/momentum_chart.py` (same class names + `set_*` APIs, QPainter instead of QtCharts)
- Modify: `widgets/charts/__init__.py`, `widgets/components/card.py` (remove QChartView frosted-guard), `screens/settings_screen.py` + `core/app_state.py` (QtCharts references — read and clean), `apps/qt_app/README.md` ×3 + `widgets/README.md` ×3 + `widgets/charts/README.md` ×3 (QtCharts mentions)
- Test: extend `test_charts.py`

**Why (license):** Research verified Qt Charts is **GPLv3-or-commercial only** (not LGPL like base Qt); this repo is proprietary ("All Rights Reserved" dual license) — shipping QtCharts is a compliance risk. Both charts are simple bar/area plots; QPainter versions remove the dependency and give exact frame control (half divider, $K ladder, side coloring).

**Interfaces:** `EconomyChart`: keep existing public API (read current file first; preserve `set_*` signatures) + add `set_half_marker(round_no: int = 13)` → dashed `text_tertiary` vertical + `half` caption; y-axis `$0…$5000+` mono ladder; grouped/side-colored bars T `chart_line_secondary` / CT `chart_line_primary`; legend chips CT/T bottom. `MomentumChart`: keep API + side-colored bars per round side (screen assembles `side` per round from rounds payload — read `match_detail_vm.py`), `HALF` divider, ±100 captions, zero axis line.

- [ ] **Step 1:** Failing tests: `_half_x(round_no, n_rounds, plot_w)` proportional; bar-rect maker `_bar_rect(idx, value, vmax, plot)` non-negative height.
- [ ] **Step 2:** Rewrite both widgets (each ≤200 lines) with `paintEvent`: `chart_bg` panel, `chart_grid` horizontal gridlines, mono tick captions (`Typography` caption + `text_tertiary`), bars with 2px top radius.
- [ ] **Step 3:** Grep `QtCharts|QChart` under `apps/qt_app/` → ZERO code matches (README mentions updated; `PySide6-Addons` stays installed for QtWebEngine — do NOT uninstall, just stop importing QtCharts).
- [ ] **Step 4:** Gallery render frame-11 economy (T orange R1-12, CT cyan R13-24 + divider + ladder) — **Read** vs frame 11. Suite green. **Commit + push** — `refactor(charts)!: QPainter economy/momentum charts; retire GPL-only QtCharts dependency` (body: license rationale + API preserved).

### Task 15: Per-map grid + HLTV bar row primitives (frames 09/12/34)

**Files:**
- Create: `widgets/components/map_tile.py`, `widgets/components/metric_bar_row.py`
- Test: extend `test_qt_core.py`

**Interfaces:**
- `MapTile(QFrame)` — `set_data(map_name, rating, adr, kd, matches)` → bold map name, rating `rating_color`-tinted `X.XX (Label)`, `ADR n K/D n` line, `n matches` caption, bottom 4px progress bar filled `min(rating/1.5, 1.0)` in rating color (frame 12 tiles).
- `MetricBarRow(QWidget)` — `set_metric(label, value_text, frac, color)` → label left, mono value, 8px track (`surface_sunken`) + fill; used by Match Detail HLTV 2-col grid and any bar-row list (frame 09).
- [ ] **Step 1:** Failing construction/value tests → implement → pass; gallery render 6 frame-12 map tiles + a frame-09 bar column. **Read**. **Commit + push** — `feat(ui): MapTile and MetricBarRow primitives for performance/match-detail grids`

---

## P4 — Screens. Shared task protocol

For every screen task: (a) **Read the frame PNG first** (render it from the SVG with the Chrome command in the header if not already in your scratchpad), plus the matching section of the microcopy extract; (b) keep the screen's VM contract untouched unless the task says otherwise; (c) add/adjust fixture in `tools/ui_fixtures.py` for the new layout; (d) verify: harness render the screen ×3 themes (CS2 mandatory eyeball, CSGO/CS16 sanity), **Read** the PNGs; (e) run suite; (f) i18n keys ×3 languages for every new string; (g) commit + push. All layout values from `get_tokens()` spacing/radius scale.

### Task 16: Home / Dashboard (frame 05)

**Files:**
- Modify: `screens/home_screen.py`, `tools/ui_fixtures.py`, `assets/i18n/{en,it,pt}.json`

**Target composition (top→bottom):** Title rail `Dashboard` (h1) + status strip card: 3 chips — `Coach: {Idle|Analyzing|Training}`, `Service: {Online|Offline}` (green/red dot), `Matches: {n}`. Then (personal data present) compact hero strip: keep `LastMatchHeroCard` + `FocusInsightCard` pair (existing richer-than-frame behavior, re-skinned raised cards). Then the 5 frame cards:
1. **Demo Analysis** — title, desc line, `Path:` + mono path chip (`surface_sunken` rounded, JetBrains Mono), buttons `[Select Demo Folder]`(secondary) `[Analyze Demos]`(primary) + status caption `Ready — 47 analyzed · 0 pending` (mono when counts).
2. **Pro Demo Ingestion** — same anatomy; status `2,148 indexed · last sync 4h ago`.
3. **Connectivity** — 3 secondary buttons: `Profile` → `switch_screen("profile")`, `Steam Config` → `steam_config`, `FaceIt Config` → `faceit_config` (wires the orphans; MainWindow already registers them — emit via a new `navigate = Signal(str)` on HomeScreen, wired in `app._wire_screen_signals` to `window.switch_screen`).
4. **Tactical Analysis** — desc + `[Open Tactical Viewer]` `[Compare Pro Players]` secondaries (same `navigate` signal).
5. **Training Status** — highlighted-depth card, only visible when `training_changed` payload active (keep current hide logic): `Epoch: 12 / 40` + progress bar, Train/Val loss + ETA row, `MonoFooter("teacher daemon · jepa_train.py · batch 184/512")` from payload fields (compose defensively).
- [ ] **Step 1:** Read frame + current file fully; restructure `_build_ui` to the composition above; keep cold-start branch (EmptyState hero) and all existing signal wiring (`_on_service_active`, `_on_training`, etc.), extending `_on_coach_status` to drive the new Coach chip.
- [ ] **Step 2:** Fixture `inject_home`: emit slots directly — service True, coach "Idle", matches 47, training dict (epoch 12/40, losses 0.0841/0.0923, eta 23m14s), plus `_on_matches_changed(SAMPLE_MATCHES)` for the hero strip.
- [ ] **Step 3:** i18n new keys (`home.demo_analysis*`, `home.pro_ingestion*`, `home.connectivity`, `home.tactical*`, `home.training*`, `home.path`). Render ×3 themes; **Read** vs frame 05. Suite green. **Commit + push** — `feat(ui): rebuild Home per frame 05 (status strip, five-card stack, connectivity wiring)`

### Task 17: Match History (frame 08)

**Files:**
- Modify: `widgets/components/match_row_card.py`, `screens/match_history_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Row anatomy per frame: left rating block (stat-size color-coded number + `rating_label` caption beneath); optional `ProBadge`; title `de_mirage | 2026-04-22 21:14` (+ `| ZywOo` for pro rows); line 2 `K/D: 1.26 | ADR: 82.3 | Kills: 24.0 Deaths: 19.0`; line 3 mono info-tinted `KAST 78% · HS% 52 · clutch 2/3 · demo 312 MB` (pro rows instead: `Vitality vs NAVI · ESL Pro League · 16-11 CT`). Read `match_history_vm.py` for available fields; if `kast`/`hs_pct`/`clutch`/`demo_size_mb` are absent from the VM payload, extend the VM query to include them (they exist on `PlayerMatchStats` — verify in `backend`/models; if a field truly doesn't exist, render `—` and leave a `# FIELD-GAP:` comment).
- [ ] **Step 2:** Header right caption `47 personal · 2,148 pro reference` fed from existing chips data. Keep source/map chips + time grouping.
- [ ] **Step 3:** Fixture: ≥8 rows incl. the two frame pro rows. Render; **Read** vs frame 08. Suite. **Commit + push** — `feat(ui): match rows per frame 08 (rating block, mono stat line, pro event line)`

### Task 18: Match Detail — Overview tab (frame 09)

**Files:**
- Modify: `screens/match_detail_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Header: `← Back` secondary + `Match Detail — de_mirage` h1; meta line left `de_mirage | 2026-04-22 21:14`, right mono `demo 312 MB · 24 rounds · 45 min`. Tabs QTabBar default variant (Overview/Rounds/Economy/Highlights).
- [ ] **Step 2:** 5 hero tiles (`HeroStatsStrip`): Rating(label) / K/D / ADR / KAST / Headshot% — first four rating-colored per thresholds, HS neutral. `Rounds:` dot strip (existing) + `16 — 8` + `final · T-side 7-5 · CT-side 9-3` captions.
- [ ] **Step 3:** `HLTV 2.0 Components` — two-column grid of `MetricBarRow` (left: Impact/Survival/KAST/KPR/ADR ratings, right: Trade Kill Ratio/Was Traded/Opening Duel Win%/Clutch Win%/Positional Aggression) — colors: green fills for ≥good, blue for trade metrics, orange for mid — per frame; `frac` normalized (ratings /1.5; percentages /100; aggression raw 0–1).
- [ ] **Step 4:** `Kill Enrichment` sunken card — 5 stats (Thru-smoke 8% `2 of 24 kills` / Wallbang 4% / No-scope 0% / Blind 0% / Opening Kills 6 green `3W 3L (+3 OK delta)`). `Utility Per Round` sunken card — HE dmg 12.4 / Molotov 5.8 / Smokes 0.8 / Flash assists 3 / Unused util 1.2 (orange warning tint). Data: read `match_detail_vm.py` `data_changed` payload (`hltv` dict); map fields that exist; `—` + `# FIELD-GAP:` for absent ones.
- [ ] **Step 5:** `MonoFooter("PlayerMatchStats · demo_name=2026-04-22_mirage_comp.dem · rating_components from hltv_components JSON")` composed from real payload names. Fixture: full frame-09 numbers. Render; **Read**. Suite. **Commit + push** — `feat(ui): match-detail Overview per frame 09 (2-col HLTV bars, kill enrichment, utility blocks)`

### Task 19: Match Detail — Rounds tab (frame 10)

**Files:**
- Modify: `screens/match_detail_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Mono table (QGridLayout in scroll area, header row caption-tertiary): `Rnd | W/L | Side | K | D | DMG | Equip $ | First Kill | Bomb | Enemies left | Notes`. Cell rules: W green/L red bold; Side CT cyan / T orange; FK badge accent mono when player got first kill (else blank); Bomb `planted` green / `defused` cyan / `lost` red / `—`; Notes colorized: warning-keyword rows orange (`over-peek`, `failed`, `caught`), positive cyan/default secondary (frame shows orange for mistakes, cyan/gray otherwise — drive by insight severity if the VM provides per-round notes; else map from existing round fields and leave `# FIELD-GAP:` for notes text).
- [ ] **Step 2:** Half separator: 2px `accent_muted_30` horizontal rule after R12. Totals footer row: `Total: 16 W 8 L · 24 K · 19 D · 1976 DMG · 6 First Kills (3W / 3L)` computed from rows. `MonoFooter("RoundStats · 24 rows · MatchEventState JOIN on demo_name")`.
- [ ] **Step 3:** Fixture: 24 frame-10 rounds. Render; **Read** vs frame 10. Suite. **Commit + push** — `feat(ui): match-detail Rounds table per frame 10 (full columns, half separator, totals footer)`

### Task 20: Match Detail — Economy + Highlights tabs (frames 11 + 34)

**Files:**
- Modify: `screens/match_detail_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Economy: `EconomyChart` with `set_half_marker(13)`; below, 5-stat row (sunken tiles): `T-side avg equip $5,000 (12 rounds · 7W · 5L)` orange value / `CT-side avg equip $4,942 (…)` cyan / `Full buys 20 (≥ $4,500 threshold)` / `Force buys 3 ($3,000-4,500)` / `Eco / Save rounds 1 (< $3,000)` — captions mono-tertiary; computed from rounds payload.
- [ ] **Step 2:** Highlights: side-colored `MomentumChart` (Task 14) + `Critical Moments` card — cards from `TacticalChronovisorVM.scan_complete` shape (label, tick, kind, round) each with `[Open in Tactical Viewer]` ghost button → emit existing cross-screen signal path (add `moment_selected = Signal(str, int)` → wire in `app._wire_screen_signals` to `tactical_viewer` screen's `load_demo` + seek — read `tactical_viewer_screen.py` public API first and use what exists; if no seek API, switch screens only + `# FIELD-GAP:`). Keep existing insights list below.
- [ ] **Step 3:** Fixture: frame-11 economy + 5 synthetic critical moments. Render both tabs; **Read**. Suite. **Commit + push** — `feat(ui): match-detail Economy summary row and Highlights critical-moment cards`

### Task 20a: Coach dock removal (standalone commit)

**Files:**
- Modify: `main_window.py` (delete `_register_coach_dock`, `_restore_dock_state`, coach special-cases in `register_screen`/`switch_screen`), `screens/coach_screen.py` (any dock assumptions), `tests` referencing dock (grep `coach_dock|COACH_DOCK`)

- [ ] **Step 1:** Remove dock pathway; coach registers into the stack like every screen; sidebar Coach navigates normally. Delete `COACH_DOCK_*` persistence writes (leave stale keys in user settings untouched — harmless).
- [ ] **Step 2:** Grep `coach_dock|COACH_DOCK|DOCK-01` in code+tests; clean references (docs/history mentions stay). Harness render `coach` (now a full screen — pre-redesign layout is fine this commit). Suite green. **Commit + push** — `refactor(ui)!: coach dock becomes a stacked screen (frames 06/07 direction)` with body explaining the DOCK-01 history and why the frame wins.

### Task 21: Coach screen (frames 06 + 07)

**Files:**
- Modify: `screens/coach_screen.py`, `tools/ui_fixtures.py`, i18n ×3

**Target:** Title `RAP Coach Dashboard` + top-right `Chat` secondary button (scrolls to / expands chat panel). Row 1 (50/50): **Belief State Confidence** card — desc lines, `ProgressRing(COACH=80)` 73% + `DriversList`: `(success) Sample count · 47 personal demos analyzed`, `(success) Data quality · 42 complete · 5 partial · 0 none`, `(warning) Map coverage · 6 of 9 competitive maps seen`, accent caption `confidence grows as you ingest more maps`; **Recent Insights** card — rows: bold title + severity label right (`High` error / `Medium` warning / `Low` success) + desc + mono category tag + timestamp caption. Row 2: **Advanced Analytics** card — when no analytics: EmptyState "Trend graphs and radar charts will appear here after demo analysis. / Analyze matches to populate this section." Bottom: `ChatPanel` (Task 9) wired to `CoachingChatViewModel` (messages → `add_message` with meta from payload confidence fields when present; suggestions static 3 chips per frame; availability → `set_status(online, "ollama", model_name)` — read `coaching_chat_vm.py` for exact signal payloads). Keep the model-picker as a small combo INSIDE the chat header area (existing capability, re-skinned) — richer-than-frame, kept.
- [ ] **Step 1:** Rebuild layout; wire `CoachViewModel.insights_loaded` + `AppState.belief_confidence_changed` + chat VM.
- [ ] **Step 2:** Fixture: belief 73 + 3 drivers + 4 frame insights + frame-07 chat transcript + suggestions. Render frames-06 (chat collapsed) and 07 (expanded, `--variant coach_dense` flag optional — simpler: render once with chat expanded). **Read** vs both frames. Suite. **Commit + push** — `feat(ui): Coach screen per frames 06/07 (belief drivers, severity insights, embedded ChatPanel)`

### Task 22: Performance (frame 12)

**Files:**
- Modify: `screens/performance_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Title `Advanced Analytics` + right caption `47 personal demos analyzed`. Row 1 (50/50): **Rating Trend** card — rows `Matches analyzed: 47` / `Average rating: 1.08` (info) / `Range: 0.71 — 1.34` / `Recent trend: 1.17 ▲ Improving` (green) + `RatingSparkline` (Task 12) + `Last 8 matches` caption; **Strengths & Weaknesses (vs Pro Average)** card — two columns: green `+1.8 above avg — Clutch Win %` etc., red `-2.1 below avg — Unused Utility` etc. (existing data path ✓, re-skin).
- [ ] **Step 2:** **Per-Map Performance** card — grid of `MapTile` (Task 15), 3 per row.
- [ ] **Step 3:** **Utility Effectiveness (vs Pro)** card — left metric list (`HE Damage/Round: 12.4 ▼ -18% vs pro` red / `≈ pro level` neutral / `▲ +12% vs pro` green …), right `UtilityBarChart` grouped `You vs Pro Average — grouped bars` with `you 12.4 / pro 15.2` captions.
- [ ] **Step 4:** Fixture: full frame-12 dataset. Render; **Read**. Suite. **Commit + push** — `feat(ui): Performance per frame 12 (sparkline trend, map tiles, grouped utility bars)`

### Task 23: Tactical Viewer (frame 13)

**Files:**
- Modify: `screens/tactical_viewer_screen.py`, `widgets/tactical/{map_widget,player_sidebar,timeline_widget}.py`, `tools/ui_fixtures.py`, i18n ×3
- Create: `Programma_CS2_RENAN/assets/map_zones/de_mirage.json` (+ loader in `map_widget.py`)

- [ ] **Step 1:** Header: `Tactical Analyzer` h1 + mono meta `2026-04-22_mirage_comp.dem · round 14 · tick 24,582` + `Open Demo` primary right. Score strip above map: `T · MACENA  9—4  CT` (side-colored) + `round 14 · 1:32 remaining · bomb planted` caption.
- [ ] **Step 2:** Rosters per frame: team header `CT · 4 ALIVE` + team `$21,300` mono; each player card: name bold + `$` mono right, HP bar (green) + `100` and AR bar (blue) + value, weapon + secondary mono line, util caption (`2 flash · 1 smoke · 1 HE`); dead card grayed `DEAD` + `killed @ palace / by macena · awp · tick 24,402` captions; selected card accent border. Extend `PlayerSidebar` rendering; util/nade fields from `frame_updated` payload if present else `—` (`# FIELD-GAP:`).
- [ ] **Step 3:** Map canvas: zone outlines + labels from `assets/map_zones/de_mirage.json` (schema `{"zones":[{"name":"A","x":0.62,"y":0.18,"w":0.14,"h":0.12,"label_size":18}...]}` normalized 0-1 coords; ship mirage(A/B/MID/jungle/palace/CT spawn/T spawn approximations — eyeball vs frame); graceful no-file → no zones). C4 marker: orange ring + `C4` mono when bomb-carrier/planted position known from frame payload. Movement trails: per-player deque of last 40 positions → 1px polyline team-colored 35% alpha (toggle with CM marks toggle group).
- [ ] **Step 4:** Transport bar per frame: `Select map:` combo + `Select round:` combo + `Tick: 24,582` mono + right toggles `Ghost AI` + `CM marks`; controls row `|◄ Play ►|` + speeds `0.5x 1x 2x 4x`; timeline: star glyphs at critical moments (from `scan_complete` payload; clicking a star seeks), `t=24,582` mono caption above playhead. `MonoFooter("ChronovisorScanner · 3 scales (micro/standard/macro) · 5 critical moments detected this round")`.
- [ ] **Step 5:** Fixture: synthetic frame payload — 10 players (frame-13 names/HP/weapons incl. dead cadiaN_bot), smoke+molly circles, C4, trails arrays, 5 star ticks, score 9-4. This fixture drives `PlaybackVM.frame_updated`-shaped dict directly into the screen's frame slot (read `tactical_vm.py` for the exact frame dict keys first). Render; **Read** vs frame 13. Suite. **Commit + push** — `feat(ui): Tactical Analyzer per frame 13 (score strip, roster cards, zones, C4, trails, star timeline)`

### Task 24: Ghost Mode (frame 14)

**Files:**
- Modify: `screens/tactical_viewer_screen.py`, `widgets/tactical/map_widget.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** When Ghost AI toggled on: header suffix `— Ghost Mode` + mono `ghost overlay: ZywOo · same round on Mirage`; left panel swaps to: `YOU · macena` card (path summary + decision time), `GHOST · ZywOo (Vitality)` card (accent-info border, path + decision time), `DIVERGENCE ANALYSIS` card — mono grid `Entry timing -4.5s (red) / Peek angle jungle vs palace / Flash support 0 vs 2 (red) / Crouch ratio 22% vs 41% / Crosshair placement good (green) / Outcome died vs won (red)` + `Causal score (RAPPedagogy)` + `0.87 positioning` accent stat + thin accent bar; values from `TacticalGhostVM` where available else `—`.
- [ ] **Step 2:** Map: your path solid 3px `accent_primary` polyline + death ✕ marker; ghost path dashed 2px purple — **no purple token exists**: use `info` (cyan) for ghost per token discipline, matching legend chip (frame uses purple; cyan is the approved in-system analog — note in commit body); divergence points: dashed rings at split points + captions. Legend strip top-left (`your path` / `ghost (pro) path` / `divergence point`).
- [ ] **Step 3:** Bottom: ghost selector combo `ZywOo · Vitality · Mirage` + `Align method:` combo (`round time`) + mono `ghost sync offset: +4.2s`; dual progress: `YOU` orange bar / `GHOST` info bar with playheads. `MonoFooter("RAPPedagogy.CausalAttributor · positioning 0.87 · utility 0.21 · aim 0.04 · aggression 0.12 · rotation 0.08")` composed from available VM fields.
- [ ] **Step 4:** Fixture: ghost-mode payload (two paths as point arrays, divergence points, metric dict). Render; **Read** vs frame 14. Suite. **Commit + push** — `feat(ui): Ghost Mode per frame 14 (dual paths, divergence analysis, causal score)`

### Task 25: Pro Comparison (frame 15)

**Files:**
- Modify: `screens/pro_comparison_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Keep mode chips + selectors + Compare (re-skin: selectors `surface_sunken`, Compare primary, right mono caption `312 pros loaded · HLTVDatabase`). Results row (50/50): **Skill Radar — 8 axes (0-100)** card — `RadarChart` axes `Aim/Opening/Utility/Clutch/Positioning/Aggression/Economy/Survival`, A = `accent_primary`, B = `info`; legend chips below. **Head-to-head metrics · {period} form** card — table: metric | A (winner-green value) | B | WINNER column (`ZywOo +0.04` orange / `donk +0.09` cyan / `even` tertiary); then **Style summary** sunken box — two archetype lines derived by rule: A's top-2 dominant metric families → template strings (e.g. KAST+utility ⇒ `team-enabling support`; K/D+opening ⇒ `aggressive entry`; implement `_style_summary(metrics_a, metrics_b) -> tuple[str, str]` pure function with unit test — 4 archetype rules + fallback `balanced all-rounder`).
- [ ] **Step 2:** Radar values: normalize each axis to 0-100 across the pair (read `pro_comparison_vm.py` payload; map its metric keys → 8 axes; document mapping in code comment). `MonoFooter("ProPlayer · ProPlayerStatCard · HLTV scraped {date} / Sample: last 20 official matches per player")` from payload.
- [ ] **Step 3:** **Me vs Pro belief gate:** when mode = Me-vs-Pro and personal sample < threshold (matches < 10 — read VM for actual availability signal), render EmptyState per frame-20 pattern: title "Not enough personal data yet", desc referencing belief confidence, CTA `Analyze Demos` → home. Never render a half-empty radar.
- [ ] **Step 4:** Unit test `_style_summary`; fixture frame-15 full table (13 metrics). Render; **Read**. Suite. **Commit + push** — `feat(ui): Pro Comparison per frame 15 (8-axis radar, winner column, style summary, belief-gated Me-vs-Pro)`

### Task 26: Settings + Profile (frames 16 + 17)

**Files:**
- Modify: `screens/settings_screen.py`, `screens/profile_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Settings/Appearance per frame 16: **Visual Theme** — 3 clickable theme cards (5 palette swatch squares + name accent-colored + tagline caption; selected = accent border; QSS `QFrame#theme_card[selected="true"]`), replacing pills; **Wallpaper** — visual cards: 3 gradient previews (paint smallgradient from each theme's surface tones) + `No wallpaper` dashed card (Task 7's None), selected accent border; **Appearance** — font size pills (keep) + interface font pills (keep list); **Live Preview** card right: sample card w/ title, body at current size, `● Accent primary = {hex}` dot+mono, `mono: JetBrains Mono · fallback Roboto` mono line — updates live on theme/font clicks (connect to `theme_changed`); **Quick Links** — secondaries `In-Game Name`→profile, `Steam Config`, `FaceIt Config`, `Reset Wizard` (existing SETUP_COMPLETED reset if present else navigate wizard), danger `Wipe local data` (`variant="danger"`, confirm `QMessageBox.warning` two-step; wire to existing backend wipe if one exists — grep `wipe|reset.*data`; if none, disable with tooltip `not available yet` + `# FIELD-GAP:`). `MonoFooter("settings saved to ~/.config/macena-cs2-analyzer/user_settings.json · chmod 0o600 (FE-04)")` — compose from `core.config` actual path constant.
- [ ] **Step 2:** Keep Flagship toggles section (richer-than-frame) + add missing `USE_WEBENGINE_MARQUEE` row (ToggleSwitch, restart-required caption).
- [ ] **Step 3:** Profile per frame 17: `← Back` + `In-Game Name` h1; left card: desc, name input (mono), caption `Must match the name shown in demo files (case-sensitive)`, `[Save]` primary + transient `✓ Saved` success chip; right `DbRecordCard` (`Database record`, SQL caption `SELECT * FROM PlayerProfile WHERE player_name = "{name}"`, rows id/player_name/created_at/matches_analyzed(green)/last_match) fed by `UserProfileViewModel`-adjacent profile VM (read `profile_screen.py` current save path; extend its VM to return the row dict; `—` for absent); **Related** card: 3 mini-cards `Steam Config → / FaceIt Config → / Match History →` (navigate signal); `TipBox` variant info: `Stored locally — CS2_PLAYER_NAME lives in user_settings.json (chmod 0o600). Nothing uploaded anywhere. FE-04.`
- [ ] **Step 4:** Fixtures (settings needs none beyond theme; profile: row dict). Render both ×3 themes; **Read** vs frames 16/17. Suite. **Commit + push** — `feat(ui): Settings theme/wallpaper cards + live preview + quick links; Profile per frame 17`

### Task 27: Wizard + Help (frames 18 + 19)

**Files:**
- Modify: `screens/wizard_screen.py`, `screens/help_screen.py`, `tools/ui_fixtures.py`, i18n ×3

- [ ] **Step 1:** Wizard per frame 18: top-left brand `MACENA CS2 ANALYZER` caption-accent-letterspaced + `Setup Wizard` h1; top-right `Step 3 of 5` + Stepper with labeled dots (`Intro/Name/Brain Path/Demo Path/Launch` captions under dots — extend `Stepper` with optional labels); Brain-Path page gains: `DIRECTORY TREE (will be created)` sunken mono card (tree glyphs `├──`/`└──` + per-dir caption lines per frame), path input + `Select Folder` secondary, validation row `Writable: ✓ yes (green) / Free space: 248 GB (green) / Estimated use: ~12 GB first year / Existing data: none` (compute writable/free via `shutil.disk_usage` + `os.access` in the VM/worker — no blocking IO on GUI thread; quick os.access is fine inline), `TipBox` (`Choose a drive with at least 50 GB free…`); footer `Back` secondary / `Skip this step` ghost / `Next →` primary. `MonoFooter("wizard_screen.py · QStackedWidget with 5 pages · shown on first run only")`.
- [ ] **Step 2:** Help per frame 19: left `TOPICS · 6` panel — topic rows (bold title + caption, selected = accent left-bar + tint) + `EXTERNAL` caption + link rows (`↗ GitHub repo` etc. — `QLabel` rich text links, `openExternalLinks(True)`); right article panel: h1 + welcome line + `NumberedStep` rows (5 steps per frame) + `DEMO FOLDER` mono callout card (accent title, path mono, caption) + `RELATED` 3 mini-cards + `KEYBOARD HINTS` rows (sunken, glyph+text) + `Docs source` dashed TipBox (`Programma_CS2_RENAN/data/docs/*.md · loaded via help_system.py` — verify actual source path in `help_screen.py` and use the real one). Search box top-right filters topics (existing behavior keep).
- [ ] **Step 3:** Render wizard (harness: wizard shows pre-completion — add `--screens wizard` with fixture selecting step 3) + help ×3 themes; **Read** vs frames 18/19. Suite. **Commit + push** — `feat(ui): Wizard per frame 18 (labeled stepper, dir tree, validation row) and Help per frame 19 (structured article)`

---

### Task 28: Motion pass (restrained, within the effects ban)

**Files:**
- Modify: `core/animation.py` (add helpers), `widgets/components/{progress_ring,hero_stats_strip}.py`, `widgets/toast.py` (verify slide-in still smooth), any stat labels via helper
- Test: extend `test_qt_core.py` (animation helper unit tests — target values, duration caps)

**Interfaces:** `core/animation.py` gains `count_up(label: QLabel, end: float, fmt: str = "{:.2f}", ms: int = 600)` (QVariantAnimation, OutExpo, sets text each tick — no graphics effects) and `sweep_ring(ring: ProgressRing, end: float, ms: int = 700)` (animates ring's value property, OutCubic). Apply: hero stat tiles + belief ring + rating numbers on screen `on_enter` (guard: only animate when value actually changed; skip in harness via `ANIMATIONS_DISABLED` env checked in helpers so screenshots are deterministic end-states).

- [ ] **Step 1:** Failing unit tests (helper reaches end value with animations disabled env → immediate set).
- [ ] **Step 2:** Implement helpers + wire into HeroStatsStrip / ProgressRing call sites (Coach belief, Match Detail tiles, Performance trend). Easing vocabulary: OutCubic hover/panels, OutExpo numbers (per research dossier).
- [ ] **Step 3:** Suite green; harness unchanged (env set in harness). Manual sanity optional. **Commit + push** — `feat(ui): count-up and ring-sweep micro-motions (deterministic under harness)`

### Task 29: Research-informed differentiation

**⛔ Invoke the `frontend-design` skill BEFORE this task.** Consume the three dossiers (committed in Step 1). Scope: highest-leverage, token-native upgrades that competitors validated and nobody combines — keep each sub-item small and reversible.

**Files:**
- Create: `docs/research/{cs_platforms,global_startups,github_gems}.md` (copied from session scratchpad `…\scratchpad\research\`; trim only broken/cache links, keep content + sources)
- Modify: `docs/research/INDEX.md`; screens/widgets per sub-items below; `tools/ui_fixtures.py`; i18n ×3

**Sub-items (each its own commit):**
- [ ] **29.1 Commit dossiers** — `docs(research): competitive teardowns — CS platforms, global startups, GitHub gems` (the user explicitly asked for this material; scratchpad dies with the session).
- [ ] **29.2 Benchmark-relative coloring sweep** (Leetify/Refrag pattern): every headline stat that has a pro/self baseline gets a ± delta chip vs that baseline (`▲ +0.09 vs 30-day avg` green / `▼` red) — Match Detail hero tiles (vs personal avg from history payload) + Performance trend card (already has) + Match History rating (small ± vs avg). One shared `DeltaChip(QLabel)` primitive in `widgets/components/delta_chip.py` + unit test. `feat(ui): benchmark-relative delta chips on headline stats`
- [ ] **29.3 Belief-state trust surfaces** (white-space finding): (a) belief ring gains sample-size chip beneath (`n=47 demos`); (b) every AI insight card shows mono provenance line (`RAP-Pedagogy · conf 0.82 · 4 demos`) — extend Coach insights rows + chat meta (Task 9/21 built the slots — this populates them consistently from VM fields, `—` when absent); (c) advice cards older than the latest model retrain (if VM exposes a timestamp) get a `revalidated {date}` caption — else skip (c) with `# FIELD-GAP:`. `feat(ui): belief provenance surfaces on AI advice`
- [ ] **29.4 Exactly-3 opportunities** (Garmin Catalyst pattern): Coach "Recent Insights" visually elevates the TOP 3 (severity-ranked) with rank numerals 01/02/03 accent-mono, remainder collapsed under a `Show all (n)` ghost toggle. `feat(ui): coach surfaces exactly three ranked focus areas`
- [ ] **29.5 Round-classification glyphs on timeline** (OP.GG/chess.com pattern): TimelineWidget stars (Task 23) get kind-differentiated glyphs — ★ critical, ◆ clutch, ● multi-kill — legend caption under transport; drive from `scan_complete` moment kinds; fallback ★. `feat(ui): kind-differentiated critical-moment glyphs`
- [ ] **29.6 Onboarding ends in proof** (Blitz/Esportal pattern): Wizard final "Launch" page adds a "What happens next" `NumberedStep` trio (`Scanner watches your folder → First report ~2 min after first demo → Coach unlocks at 10 demos`) + calibration note (`Belief starts low and grows — you'll see the % on Coach`). Pure copy + primitives; no backend. `feat(ui): wizard launch page sets calibration expectations`
- [ ] Each sub-item: fixture updates as needed, harness render of affected screens, **Read**, suite, commit + push.

### Task 30: i18n + docs sweep

**Files:**
- Modify: `assets/i18n/{en,it,pt}.json` (audit EVERY key added in Tasks 7–29 exists in all three; translate properly — Italian and Portuguese, not English copies), `apps/qt_app/README.md` + `_IT` + `_PT` (screens table, widgets tables, charts table (QtCharts→QPainter), theming section, dock removal), `CHANGELOG.md` (feature summary under Unreleased/next version per file convention — read its format first)

- [ ] **Step 1:** Script-assisted key audit: quick python snippet comparing key sets across the 3 JSONs → zero missing; eyeball translations (pt-BR flavor consistent with existing file).
- [ ] **Step 2:** Update the 3 qt_app READMEs + CHANGELOG. Suite green. **Commit + push** — `docs(ui): trilingual i18n completion + README/CHANGELOG for the design-atlas rebuild`

### Task 31: Final verification matrix + review

- [ ] **Step 1:** Full harness run: all 15 screens × 3 themes + gallery + collapsed-nav + ghost-mode variant → `docs/ux-audit/renders-atlas/`. **Read every CS2 PNG** (15) + spot-check CSGO/CS16 (≥5 each) against frames; fix deviations found (small fix commits).
- [ ] **Step 2:** Commit the render set — `docs(ux-audit): design-atlas render matrix (15 screens × 3 themes)` (binary PNGs in docs/ux-audit follows existing repo precedent).
- [ ] **Step 3:** Full test suite: `& .venv\Scripts\python.exe -m pytest Programma_CS2_RENAN/tests/test_qt_core.py Programma_CS2_RENAN/tests/test_ui_harness.py Programma_CS2_RENAN/tests/test_charts.py -q` green.
- [ ] **Step 4:** Invoke the `/code-review` skill on the branch diff (high effort); fix CONFIRMED findings; commit fixes.
- [ ] **Step 5:** Invoke `superpowers:verification-before-completion`; final push; summarize for the user (screens done, renders location, license finding, research dossiers, known FIELD-GAPs list).

---

## Self-Review (performed at plan-writing time)

1. **Spec coverage:** frames 05–20 all mapped (05→T16, 06/07→T21, 08→T17, 09→T18, 10→T19, 11→T20, 12→T22, 13→T23, 14→T24, 15→T25, 16→T26, 17→T26, 18/19→T27, 20→T8); design-system frames 31–36 are satisfied by the token pipeline (already live) + T8/T10/P3 components + fonts (T2). Marketing frames 01–04 are out of app scope. Audit gap list cross-checked: every "missing" item has a task; orphan wiring in T16/T26; violations in T6; dead QSS in T5; PALETTES in T4; fonts in T2; web layer consciously deferred (Locked Decision 6).
2. **Placeholder scan:** no TBDs; where backend data may not exist the plan mandates defensive `—` + `# FIELD-GAP:` comment + explicit note — that is a specified behavior, not a placeholder.
3. **Type consistency:** component names used by later tasks are defined in earlier ones (ProBadge T8→T17; ChatPanel T9→T21; DriversList/TipBox/NumberedStep/DbRecordCard/MonoFooter T10→T21/T26/T27; RadarChart T11→T25; RatingSparkline T12→T22; UtilityBarChart T13→T22; MapTile/MetricBarRow T15→T18/T22; DeltaChip T29.2 self-contained; harness/fixtures T1 used everywhere).
4. **Sequencing:** P0 before all; T8 before screen tasks that use its primitives; T20a (dock removal) before T21; charts before their consumer screens. Screen tasks T16–T19 are mutually independent after P0–P3; T23 before T24.

## Execution notes

- Mode: subagent-driven (superpowers:subagent-driven-development) — fresh implementer per task, given: this plan's task text + Global Constraints + Locked Decisions + the frame render/Read protocol; reviewer gate = the orchestrator Reads the task's harness PNGs + diff before commit. Foundation tasks T1–T2 are machine-delicate — implement inline (orchestrator), not via subagent.
- The three research dossiers live in session scratchpad `…\scratchpad\research\` until T29.1 commits them — if the session is lost before T29, re-run the research agents (prompts recoverable from this plan's git history / conversation).
- Fixture-vs-frame fidelity is the quality bar: when a rendered screen and its frame disagree, the frame wins unless a Locked Decision says otherwise.

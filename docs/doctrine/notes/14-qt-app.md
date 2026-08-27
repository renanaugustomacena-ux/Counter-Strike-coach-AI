# Cluster 14 — apps/qt_app

All paths relative to `Programma_CS2_RENAN/apps/`.

## Files read

- [x] __init__.py (apps)
- [x] qt_app/__init__.py
- [x] qt_app/app.py
- [x] qt_app/main_window.py
- [x] qt_app/core/__init__.py
- [x] qt_app/core/animation.py
- [x] qt_app/core/app_state.py
- [x] qt_app/core/design_tokens.py
- [x] qt_app/core/easing.py
- [x] qt_app/core/i18n_bridge.py
- [x] qt_app/core/icons.py
- [x] qt_app/core/match_utils.py
- [x] qt_app/core/qss_generator.py
- [x] qt_app/core/qt_playback_engine.py
- [x] qt_app/core/sound.py
- [x] qt_app/core/svg_icon_provider.py
- [x] qt_app/core/theme_engine.py
- [x] qt_app/core/typography.py
- [x] qt_app/core/web_bridge.py
- [x] qt_app/core/widgets_helpers.py
- [x] qt_app/core/worker.py
- [x] qt_app/screens/__init__.py
- [x] qt_app/screens/coach_screen.py
- [x] qt_app/screens/faceit_config_screen.py
- [x] qt_app/screens/help_screen.py
- [x] qt_app/screens/home_screen.py
- [x] qt_app/screens/match_detail_screen.py
- [x] qt_app/screens/match_history_screen.py
- [x] qt_app/screens/performance_screen.py
- [x] qt_app/screens/placeholder.py
- [x] qt_app/screens/pro_comparison_screen.py
- [x] qt_app/screens/pro_player_detail_screen.py
- [x] qt_app/screens/profile_screen.py
- [x] qt_app/screens/settings_screen.py
- [x] qt_app/screens/steam_config_screen.py
- [x] qt_app/screens/tactical_viewer_screen.py
- [x] qt_app/screens/user_profile_screen.py
- [x] qt_app/screens/wizard_screen.py
- [x] qt_app/viewmodels/__init__.py
- [x] qt_app/viewmodels/coach_vm.py
- [x] qt_app/viewmodels/coaching_chat_vm.py
- [x] qt_app/viewmodels/focus_insight_vm.py
- [x] qt_app/viewmodels/match_detail_vm.py
- [x] qt_app/viewmodels/match_history_vm.py
- [x] qt_app/viewmodels/performance_vm.py
- [x] qt_app/viewmodels/pro_comparison_vm.py
- [x] qt_app/viewmodels/pro_player_detail_vm.py
- [x] qt_app/viewmodels/tactical_vm.py
- [x] qt_app/viewmodels/user_profile_vm.py
- [x] qt_app/widgets/__init__.py
- [x] qt_app/widgets/charts/__init__.py
- [x] qt_app/widgets/charts/economy_chart.py
- [x] qt_app/widgets/charts/mini_sparkline.py
- [x] qt_app/widgets/charts/momentum_chart.py
- [x] qt_app/widgets/charts/radar_chart.py
- [x] qt_app/widgets/charts/rating_sparkline.py
- [x] qt_app/widgets/charts/utility_bar_chart.py
- [x] qt_app/widgets/coaching/__init__.py
- [x] qt_app/widgets/coaching/chat_panel.py
- [x] qt_app/widgets/components/__init__.py
- [x] qt_app/widgets/components/card.py
- [x] qt_app/widgets/components/db_record_card.py
- [x] qt_app/widgets/components/delta_chip.py
- [x] qt_app/widgets/components/drivers_list.py
- [x] qt_app/widgets/components/empty_state.py
- [x] qt_app/widgets/components/filter_chip.py
- [x] qt_app/widgets/components/focus_insight.py
- [x] qt_app/widgets/components/hero_stats_strip.py
- [x] qt_app/widgets/components/icon_widget.py
- [x] qt_app/widgets/components/last_match_hero.py
- [x] qt_app/widgets/components/map_tile.py
- [x] qt_app/widgets/components/match_mini_card.py
- [x] qt_app/widgets/components/match_row_card.py
- [x] qt_app/widgets/components/metric_bar_row.py
- [x] qt_app/widgets/components/mini_link_card.py
- [x] qt_app/widgets/components/mono_footer.py
- [x] qt_app/widgets/components/nav_sidebar.py
- [x] qt_app/widgets/components/numbered_step.py
- [x] qt_app/widgets/components/pro_badge.py
- [x] qt_app/widgets/components/progress_ring.py
- [x] qt_app/widgets/components/section_header.py
- [x] qt_app/widgets/components/stat_badge.py
- [x] qt_app/widgets/components/status_chip.py
- [x] qt_app/widgets/components/stepper.py
- [x] qt_app/widgets/components/tip_box.py
- [x] qt_app/widgets/components/toggle_switch.py
- [x] qt_app/widgets/skeleton.py
- [x] qt_app/widgets/tactical/__init__.py
- [x] qt_app/widgets/tactical/_paint_utils.py
- [x] qt_app/widgets/tactical/map_widget.py
- [x] qt_app/widgets/tactical/player_sidebar.py
- [x] qt_app/widgets/tactical/timeline_widget.py
- [x] qt_app/widgets/toast.py

## Architecture

### Boot sequence (qt_app/app.py:314-386, `main()`)

1. High-DPI policy → `QApplication` → resolve version from installed package `macena-cs2-analyzer` (fallback "1.0.0", app.py:85-90).
2. `ThemeEngine().register_fonts()` BEFORE splash so splash painter can use the display stack (app.py:326-328).
3. Themed splash (`_create_splash`, app.py:21-72) — colors from `design_tokens.get_tokens(get_setting("ACTIVE_THEME","CS2"))`; backend config read at boot via `Programma_CS2_RENAN.core.config.get_setting`.
4. `_install_quit_handler` (app.py:93-110): `aboutToQuit` → `get_app_state().stop_polling()` → `lifecycle.shutdown()` (kills Session Engine subprocess) → `get_console().shutdown()`. Ordering documented: polling first, daemon second, Console DB handles last.
5. `_apply_theme` (app.py:113-128): FONT_TYPE/FONT_SIZE settings → `theme.apply_theme(ACTIVE_THEME, app)`.
6. `MainWindow()` + wallpaper; `create_placeholder_screens()` then `_create_screens()` (15 real screens, app.py:156-172) overwrite placeholders by name; `_wire_screen_signals` (app.py:175-207) wires cross-screen routing: `match_history.match_selected` & `home.match_selected` → `match_detail.load_demo(demo)` + switch; `wizard.setup_completed` → home; `match_detail.moment_selected(demo,tick)` → `tactical_viewer.open_moment` + switch; `pro_comparison.pro_detail_requested(hltv_id)` → `pro_player_detail.load_pro`.
7. First-run gate: `SETUP_COMPLETED` setting decides home vs wizard (app.py:355-360).
8. `_boot_backend_services` (app.py:210-238): `backend.control.console.get_console().boot()` + `core.lifecycle.lifecycle.launch_daemon()` (Session Engine daemon = Scanner/Digester/Teacher/Pulse subprocess). Errors logged, never raised; failure → modal warning after window shows (app.py:294-311).
9. `_ensure_sbert_model` (app.py:241-280): WR-10 — `backend.knowledge.rag_knowledge.KnowledgeEmbedder.is_model_cached()` / `.download_model()` (~90 MB) in a daemon thread while pumping `processEvents`; failure falls back to dense similarity, never blocks boot.
10. `window.show()` + `raise_()`/`activateWindow()` (DOCK-01), splash finish, then `get_app_state().start_polling()` (10 s CoachState poll) and `_install_qt_excepthook` (app.py:283-291) before `app.exec()`.

### MVVM threading model

- `core/worker.py:25-73` — `Worker(QRunnable)` + `WorkerSignals` (finished/error/result/progress). All backend calls run in `QThreadPool.globalInstance()`; results marshal back to GUI thread via signal auto-marshaling. `wants_progress=True` injects `progress_callback` kwarg into the backend fn (worker.py:49-58) for streaming partials (used by coach chat). RuntimeError on emit swallowed (receiver GC'd).
- `core/app_state.py:31-219` — `AppState` singleton QObject (`get_app_state()`). `start_polling()` = QTimer 10 s → `_poll()` → Worker running static `_bg_read` off-thread. `_bg_read` (app_state.py:89-184) reads `backend.storage.database.get_db_manager().get_session()`: `CoachState` row id=1 (heartbeat → `service_active = delta < 300 s`, ingest_status, parsing_progress, belief_confidence, epochs/losses/eta), unread `ServiceNotification` rows (marks `is_read=True` and commits — the ONE sanctioned UI→DB write, app_state.py:1-8,131-148), and distinct `PlayerMatchStats.demo_name` count. `_apply` (app_state.py:186-216) diffs vs previous snapshot and emits typed signals: service_active_changed, coach_status_changed, parsing_progress_changed, belief_confidence_changed, total_matches_changed, training_changed(dict), notification_received(severity,message).
- P3/P4 feature toggles persisted through `core.config` settings (app_state.py:228-307): SOUNDS_ENABLED, USE_FRAMELESS_WINDOW, USE_PYQTGRAPH_HEATMAP, USE_WEBENGINE_MARQUEE (webengine marquee loads React+D3 from `apps/qt_app/web/<name>/dist/`, silent fallback to Qt-native).

### MainWindow (qt_app/main_window.py)

- `QMainWindow` + `NavSidebar` + `QStackedWidget` in a `QStackedLayout(StackAll)` over `_BackgroundWidget` (wallpaper 0.15 opacity + tactical-grid SVG motif tile 0.05, main_window.py:107-192). Optional frameless mode with hand-rolled titlebar (`_CustomTitleBar`, main_window.py:31-104) read once at construction from `AppState.use_frameless_window` (main_window.py:218).
- Screen protocol: `register_screen(name, widget)`; `switch_screen` calls `on_leave()`/`on_enter()` hooks, no fade animation ("QGraphicsOpacityEffect causes QPainter errors on Linux", main_window.py:349-351 — graphics-effects ban honored). `screen_changed` Signal(str).
- Toasts: `AppState.notification_received` → `ToastContainer.add_toast` (main_window.py:266-276, 359-361). i18n: `i18n.language_changed` → retranslate sidebar + every screen exposing `retranslate()` (main_window.py:363-370). Keyboard shortcuts generated from `NAV_ITEMS` table (main_window.py:283-285). Lazy `SoundManager` with null-object fallback (main_window.py:301-320).

### Web bridge + playback (core/)

- `core/web_bridge.py:34-236` — `MarqueeBridge(QObject)` for QWebChannel: Python→JS publishes tick/frame/coach_state/map/segments/events/ghost as JSON strings (Signals + Q_Properties); JS→Python slots `seek_to_tick`, `select_player`, `request_ghost`, `log` re-emit as `seek_requested`/`player_selected`/`ghost_requested` for the host screen to forward to the ViewModel. One shared class for all marquee screens (tactical viewer / match detail / coach chat).
- `core/qt_playback_engine.py:10-39` — `QtPlaybackEngine(PlaybackEngine)` subclasses `Programma_CS2_RENAN.core.playback_engine.PlaybackEngine`, replaces Kivy Clock with a 16 ms QTimer driving `self._tick(dt)` on the GUI thread.

### Other core/ modules (visual/support)

- `core/i18n_bridge.py` — `QtLocalizationManager` singleton `i18n` (Signal `language_changed`); lookup priority JSON (`assets/i18n/{en,pt,it}.json`, loaded at import via `core.config.get_resource_path`) → `core.localization.TRANSLATIONS` hardcoded dicts (Kivy-safe try-import, i18n_bridge.py:68-73) → en fallback → default → raw key. en/pt/it only.
- `core/match_utils.py` — `extract_map_name`/`map_short_name` (regex `de_|cs_|ar_` prefix, fallback to `core.known_maps.KNOWN_MAP_NAMES` SSOT, match_utils.py:20-36); `count_personal_and_pro(matches)` counts personal rows vs DISTINCT pro `demo_name` (PlayerMatchStats is one row per (demo, player), match_utils.py:49-59).
- `core/sound.py` — `SoundManager` preloads 4 WAVs from `PHOTO_GUI/sounds/` via QSoundEffect; gated on `AppState.sounds_enabled`; warn-once per missing file.
- `core/theme_engine.py` — token-driven QSS + QPalette; `rating_color/rating_label` (HLTV rating thresholds 1.10/0.90, theme_engine.py:29-71), `severity_bucket/severity_color` (theme_engine.py:74-104) = SSOT for insight-severity display used by coach/match-detail. Module-level `_ThemeRelay.theme_changed` for per-widget restyle (theme_engine.py:107-123). Reads `BACKGROUND_IMAGE` setting for wallpaper (default flat).
- `core/design_tokens.py` — generated frozen dataclasses (CS2/CSGO/CS1.6) from `design/tokens/design-tokens.json`; module-level active theme + `get_tokens()`.
- `core/qss_generator.py` — renders `themes/base.qss.template` with `string.Template.safe_substitute(asdict(tokens))`, per-theme cache.
- `core/animation.py` — `Animator` helpers; `animations_enabled()` kill-switch via `MACENA_UI_ANIMATIONS=0` (animation.py:35-38). Opacity helpers use QGraphicsOpacityEffect (documented Linux hazard, animation.py:8-15); geometry/value helpers (`slide_in/out`, `count_up`, `sweep_ring`, `reveal_stagger`, `collapse_width`) are the "safe" set.
- `core/easing.py` — named QEasingCurve aliases + `cubic_bezier`.
- `core/icons.py` + `core/svg_icon_provider.py` — `IconProvider` facade chosen at import: SVG sprite (`design/assets/icons/sprite.svg`, currentColor tinting, (symbol,size,color) cache) if available else hand-drawn QPainterPath fallback.
- `core/typography.py` — `Typography.apply/font` roles reading token sizes; QSS-variant roles via property+polish.
- `core/widgets_helpers.py` — `make_button(variant)` and `navigate_to(widget, screen)` (resolves `window().switch_screen`).
- `apps/__init__.py` empty; `qt_app/__init__.py`, `core/__init__.py` docstring-only.

### Widgets — tactical / coaching / charts (visual; brief)

- `widgets/tactical/map_widget.py` (905) — `TacticalMapWidget`: QPainter 2D map. Coordinate transform via `core.spatial_engine.SpatialEngine.world_to_normalized` (map_widget.py:348-352). Layers: radar pixmap (loud warning if missing — blank-viewer fix, map_widget.py:331-337) → named zones from `assets/map_zones/*.json` (validated, degrade to [], map_widget.py:59-104) → movement trails (40-pt deque/player) → nades (trajectory interpolation, detonation radii in game units: HE 350/molotov 180/smoke 144/flash 1000) → ghosts (alpha 77) → players (FoV cone from yaw, HP bar, selected-only name) → frame-14 ghost dual-path overlay (you=solid accent, ghost=dashed info, divergence rings, legend) → score box. Token palette rebuilt per paint (theme-tracking); score-box layout precomputed on change not per-frame (60 fps fix, map_widget.py:186-233). Click hit-test 2.5× radius selects player.
- `widgets/tactical/player_sidebar.py` (401) — roster cards: HP thresholds >60/≥30, armor bar, K/D/A mono line, weapon+secondary, utility caption from inventory; DEAD state uses `death_info` FIELD-GAP (no kill attribution in frame payload, player_sidebar.py:277-301); `has_defuser` also FIELD-GAP on InterpolatedPlayerState. Painted `_StatBar` (no QSS reparse per frame); per-label text cache + style-bucket cache for 60 fps. Signals use `object` (Steam IDs exceed int32, player_sidebar.py:121-122, 312).
- `widgets/tactical/timeline_widget.py` (294) — scrub bar with kill/plant/defuse markers, round dividers, chronovisor glyphs (mistake→★ warning, clutch→◆ info, play→● success; click seeks to start_tick, map_widget.py analog `star_hit_test`), playhead + mono `t=` caption. Kind map documents scanner vocabulary: "mistake"=Advantage Loss, "play"=Advantage Gain, "clutch" forward-looking (timeline_widget.py:35-39).
- `widgets/tactical/_paint_utils.py` — `with_alpha(color, a)`. `tactical/__init__.py` docstring only.
- `widgets/coaching/chat_panel.py` (271) — `ChatPanel`: VM-agnostic chat surface (signals `message_submitted`, `suggestion_clicked`; API `add_message(role, text, meta)` coach/user/system, `update_last_message` for streaming, `set_status(online, backend, model)`, `set_suggestions`). Bubbles hug natural text width capped at 60% panel width; meta footnote line for confidence provenance when supplied.
- `widgets/toast.py` (192) — `ToastWidget` severity config INFO 5s/WARNING 8s/ERROR 12s/CRITICAL manual-only; auto-caption "auto · Ns"; timers receiver-bound (F-0036 fires-on-corpse fix, toast.py:107-118). `ToastContainer` floats top-right, max 3 visible, hidden when empty (zero event interception); slide-in geometry animation (not opacity — Linux-safe).
- `widgets/charts/__init__.py` — `token_color(str)` parses `#hex` and `rgba()` token strings (Qt can't parse rgba, charts/__init__.py:10-38); exports chart classes. "No chart-library dependency (license-clean)" — the previous chart lib was GPLv3-or-commercial.
- `widgets/charts/economy_chart.py` (218) — pure-QPainter equipment-per-round bars, side-colored CT cyan/T orange, $ ladder, dashed "half" divider; unknown side falls back by half marker.
- `widgets/charts/momentum_chart.py` (183) — per-round K−D swing bars around zero axis, side-colored, true-peak axis captions (old ±100 literal removed), half divider at first side change.
- `widgets/charts/radar_chart.py` (162) — N-axis (≥3) radar, 4 rings, 25%-alpha fills, quadrant-aware labels; series colors caller-supplied.
- `widgets/charts/rating_sparkline.py` (131) — rating polyline with dashed HLTV reference lines 0.90/1.00/1.10 (red/neutral/green), area fill, accent endpoint dot.
- `widgets/charts/mini_sparkline.py` (103) — chrome-less trend line + gradient fill for hero cards.
- `widgets/charts/utility_bar_chart.py` (189) — horizontal grouped you-vs-pro bars (waste row tintable) or single-series with tick ladder.

### Widgets — components (1-2 lines each)

- `nav_sidebar.py` (199) — `NAV_ITEMS` table = SSOT for nav routing + Ctrl+1..5/Ctrl+,/F1 shortcuts + tooltips; collapsible 220↔60 px via min/maxWidth QPropertyAnimation; version label from installed package.
- `card.py` (179) — `Card` with depth tiers flat/raised/highlighted/floating/frosted; floating+frosted mount QGraphicsDropShadowEffect on showEvent (shadow, not opacity — but still a graphics effect; see Suspicious).
- `empty_state.py` (260) — icon-well/title/desc/primary+ghost CTA/link-row/loading-skeleton; F-0035 isVisibleTo fix for CTA row re-show.
- `last_match_hero.py` (166) + `focus_insight.py` (132) — dashboard hero pair; data/empty QStackedLayout states; rating colored by `rating_color`.
- `match_row_card.py` (224) — frame-08 row: rating block (`rating_color`/`rating_label`), ProBadge, three text lines with FIELD-GAP "—" fallbacks (clutch counts, demo size, pro event line); DeltaChip only for personal rows with honest baseline.
- `match_mini_card.py` (119) — 140×124 recent-match tile; `_relative_time` helper shared with LastMatchHero.
- `delta_chip.py` (60) — ▲/▼ ± vs baseline; hides on formatted-zero deltas ("an honest chip never renders +0.00").
- `drivers_list.py` (66) — severity-squared rows via `severity_color`; unknown severity → neutral tertiary square.
- `filter_chip.py` (122) + `status_chip.py` (92) — pill chips; both subscribe to `get_theme_relay().theme_changed` for live-theme restyle (CP0 #4).
- `hero_stats_strip.py` (98) — HeroStat dataclass row (display number + caption, sentiment colors).
- `metric_bar_row.py` (97) — label + mono value + 8px track/fill, single paint pass.
- `map_tile.py` (130) — per-map tile fully QPainter-drawn; rating bar fill capped at rating/1.5.
- `progress_ring.py` (95) — conical-gradient arc ring, presets SMALL/DEFAULT/COACH/HERO; centered % text.
- `stepper.py` (284) — wizard dot-and-bar step indicator, labeled frame-18 mode with check glyphs.
- `stat_badge.py` (168) — stat + caption + trend arrow; `set_rating` variant uses HLTV thresholds.
- `toggle_switch.py` (154) — iOS-style switch; knob animated via geometry Property ("NOT an opacity effect" — Linux-crash note).
- `db_record_card.py` (95), `mini_link_card.py` (58), `mono_footer.py` (19), `numbered_step.py` (61), `pro_badge.py` (56), `section_header.py` (75), `tip_box.py` (43), `icon_widget.py` (37) — small QSS-anatomy components; MonoFooter is the data-provenance caption convention used app-wide.
- `skeleton.py` (110) — SkeletonRect pulse (Animator.pulse = opacity effect, started on showEvent), SkeletonCard, SkeletonTable with staggered reveal.
- `components/__init__.py` re-exports 15 components; `widgets/__init__.py` docstring only.

## Backend contracts

Universal pattern: every VM runs its `_bg_*` fn in `QThreadPool.globalInstance()` via `Worker`; all backend imports are deferred inside the bg fn; results emitted as plain dict/list payloads on the GUI thread. Player identity always resolved via `core.config.get_setting("CS2_PLAYER_NAME", "")`.

- __CoachViewModel__ (`viewmodels/coach_vm.py:11-84`) — reads `CoachingInsight` rows via `backend.storage.database.get_db_manager()`; user's insights first (by `player_name`, limit 10, newest first), fallback to ALL insights (pro analysis) if none (coach_vm.py:44-58). Emits `insights_loaded(list[dict])` with title/message/severity/focus_area/created_at/player_name/demo_name/`is_pro` (= player_name != configured player, coach_vm.py:69).
- __CoachingChatViewModel__ (`viewmodels/coaching_chat_vm.py:17-205`) — wraps `backend.services.coaching_dialogue.get_dialogue_engine()` (lazy import in `_ensure_engine`, degrades to offline, coaching_chat_vm.py:38-56). Engine API used: `.is_available`, `.start_session(player, demo)`, `.respond_stream(text, progress_callback=...)` (streamed via Worker `wants_progress`, chunks are FULL accumulated text — DR-14, coaching_chat_vm.py:179-184), `.cancel_stream()`, `.clear_session()` (wrapped in Worker — QT-02 anti-freeze). Offline message names Ollama + `gemma4:e2b` (coaching_chat_vm.py:160-166). Cancelled stream returns "" and appends no bubble.
- __FocusInsightViewModel__ (`viewmodels/focus_insight_vm.py:33-120`) — STUB: only checks existence of any non-pro `PlayerMatchStats` row; emits an honest navigation hint, deliberately claims NO measurement (R4 anti-fabrication note, focus_insight_vm.py:92-107). Signal contract `insight_changed({area, body, navigate_to})` kept stable for future delta-vs-pro computation.
- __MatchDetailViewModel__ (`viewmodels/match_detail_vm.py:12-183`) — one bg pass: `PlayerMatchStats` (configured player first, else any player in demo), `RoundStats` ordered by round_number for the effective player, `CoachingInsight` for the demo, plus `backend.reporting.analytics.analytics.get_hltv2_breakdown(effective_player)` (match_detail_vm.py:158-168; R4: uses the demo's effective player, not configured user). Emits `data_changed(stats_dict, rounds_list, insights_list, hltv_breakdown)`; stats dict carries HLTV 2.0 components, trade/duel, kill-enrichment and utility columns (match_detail_vm.py:95-130).
- __MatchHistoryViewModel__ (`viewmodels/match_history_vm.py:14-118`) — `PlayerMatchStats` filtered: excludes stub `data_quality in (registered_only, partial, none)` but KEEPS NULL (SQL three-valued logic fix, match_history_vm.py:60-68); user rows OR `is_pro==True`; newest 50. Documents FIELD-GAPs: no clutch counts, no demo_size_mb, no pro event columns (match_history_vm.py:90-99). Cancellation via `threading.Event` checked only after query completes.
- __PerformanceViewModel__ (`viewmodels/performance_vm.py:12-187`) — raises if `CS2_PLAYER_NAME` unset. Calls `backend.reporting.analytics.analytics`: `get_rating_history(player, limit=50)`, `get_per_map_stats`, `get_strength_weakness`, `get_utility_breakdown` (performance_vm.py:76-79). `is_pro_overview` = user has zero non-pro rows. `_compute_pro_percentiles` (performance_vm.py:101-169) ranks user's avg rating/kd/adr/kast within the pro cohort (same NULL-quality-keep rule); metrics with no user data OMITTED, not zeroed (R4 HIGH). Emits `context_changed` BEFORE `data_changed` (ordering bug fix, performance_vm.py:176-181).
- __ProComparisonViewModel__ (`viewmodels/pro_comparison_vm.py:30-216`) — reads hltv_metadata.db via `backend.storage.database.get_hltv_db_manager()`: `ProPlayer`/`ProPlayerStatCard`/`ProTeam`. Player list = only players WITH stat cards, sorted by team world rank. User-vs-pro path averages `PlayerMatchStats` (main DB); metrics without user equivalent (clutch_win_count, impact, opening_kill_ratio, multikill_round_pct) are absent → "—" (R4 HIGH units-mismatch fix, pro_comparison_vm.py:180-194). `COMPARISON_METRICS` table with lower_is_better flags (pro_comparison_vm.py:13-27).
- __ProPlayerDetailViewModel__ (`viewmodels/pro_player_detail_vm.py:23-114`) — one pro's composite profile from hltv DB: ProPlayer + preferred all_time `ProPlayerStatCard` + `ProTeam`; `detailed_stats_json` parsed with corrupt-JSON guard → `{}` (pro_player_detail_vm.py:72-77).
- __TacticalPlaybackVM__ (`viewmodels/tactical_vm.py:21-90`) — thin adapter over the injected `QtPlaybackEngine` (`core.playback_engine.PlaybackEngine` API: load_frames(tick_rate), toggle_play_pause, set_speed, seek_to_tick, get_current_tick, set_on_frame_update). Emits `frame_updated(InterpolatedFrame)` on every engine tick (GUI thread — engine is QTimer-driven).
- __TacticalGhostVM__ (`viewmodels/tactical_vm.py:96-151`) — lazy-loads `backend.nn.inference.ghost_engine.GhostEngine` ON THE GUI THREAD when ghost toggled on (`set_active→_ensure_loaded`, tactical_vm.py:108-123). `predict_ghosts(players)` calls `engine.predict_tick(p)` per alive player; None prediction skipped (no origin-fabricated ghosts, R4 LOW, tactical_vm.py:134-137); ghost = `dataclasses.replace(p, x, y, is_ghost=True)`.
- __TacticalChronovisorVM__ (`viewmodels/tactical_vm.py:157-250`) — Worker-run scan: requires setting `USE_RAP_MODEL=True` else RuntimeError (tactical_vm.py:186-189); `backend.nn.rap_coach.chronovisor_scanner.ChronovisorScanner().scan_match(match_id)` → `result.critical_moments` sorted by start_tick (each has type/description/start_tick/peak_tick). `jump_to_next/prev` navigate with 32-tick buffer; emits `navigate_to(tick, desc)`.
- __UserProfileViewModel__ (`viewmodels/user_profile_vm.py:11-108`) — loads/saves `PlayerProfile` (bio, role) in main DB; save is a UI-initiated DB write (session.commit, user_profile_vm.py:84-93) — a second write path beyond AppState's notification-mark-read.

### Screen-level backend calls (bypassing VMs)

- `screens/home_screen.py:812-821, 841-850` — `Programma_CS2_RENAN.run_ingestion.process_new_demos(is_pro=...)` in a Worker (personal + pro demo ingestion). Same call in `screens/settings_screen.py:989-1003` (runs pro then user sequentially in one Worker).
- `screens/coach_screen.py:453-465` — `backend.services.llm_service.get_llm_service().list_models()` (Ollama /api/tags) ON THE MAIN THREAD (deliberate; documented as local + short timeout).
- `screens/tactical_viewer_screen.py:1075-1085` — `ingestion.demo_loader.DemoLoader().load_demo(path)` in Worker; `run_ingestion._parse_demo_header_meta` for tick rate; `backend.data_sources.demo_format_adapter.MIN_DEMO_SIZE` for validation; `PlayerTickState` match_id lookup in Worker (tactical_viewer_screen.py:1678-1689); `core.spatial_engine.SpatialEngine.world_to_normalized` for web ghost payloads.
- `screens/steam_config_screen.py:230-234` — `backend.services.profile_service.ProfileService().fetch_steam_stats(steam_id)` in Worker; result dict {nickname, playtime_forever} or {error}.
- `screens/profile_screen.py:268-295` + `screens/wizard_screen.py:822-840` — PlayerProfile ensure-row upsert in Worker (F-0038 fix: used to run on GUI thread).
- Settings/config screens write via `core.config.save_user_setting` (atomic write + chmod 0o600 — FE-04, referenced settings_screen.py:344-347); credentials via `core.config.get_credential` (keyring-backed; plaintext warning when keyring missing, steam_config_screen.py:27-32, 89-102).

## AI-output surfaces

NOTE — win probability: no direct win-probability surface exists anywhere in qt_app. It reaches the user only indirectly, via Chronovisor critical moments whose "mistake"/"play" types are Advantage Loss / Advantage Gain swings (timeline_widget.py:35-39); no screen, widget, or VM payload carries a numeric win-prob field.

### CoachScreen (`screens/coach_screen.py`, 864 lines) — the RAP coach dashboard

- Belief State Confidence: `AppState.belief_confidence_changed` → normalized 0..1 (handles legacy 0..100, coach_screen.py:555-565) → `Animator.sweep_ring` on a COACH-size ProgressRing; sample-count chip `n={n} demos` fed by `AppState.total_matches_changed` (coach_screen.py:567-569, 603-611). Belief drivers list: only "samples" has a live data source; data-quality and map-coverage rows render "—" (FIELD-GAPs documented at coach_screen.py:85-98).
- Recent Insights: `CoachViewModel.insights_loaded` → severity-ranked top-3 shortlist (Garmin Catalyst pattern, coach_screen.py:636-666) with overflow collapsed; each row shows severity word (via `severity_bucket`/`severity_color`), optional "Pro Analysis: {player} on {map}" accent (map from `core.known_maps.MAP_NAME_RE`, coach_screen.py:52-62, 701-722), mono provenance line composed ONLY from real fields (focus_area · demo_name · created_at, coach_screen.py:759-796; model/confidence provenance is a documented FIELD-GAP). QLabels use `Qt.PlainText` (FE-01 anti-HTML-injection, coach_screen.py:738,753).
- Chat dock: `ChatPanel` wired to `CoachingChatViewModel`; `_toggle_chat` starts session with `CS2_PLAYER_NAME` (coach_screen.py:429-436); streaming chunks live-update the trailing bubble (`_on_stream_progress`, coach_screen.py:841-853). Chat status line shows "ollama · {model}".
- LLM model picker: `_refresh_llm_models` calls `backend.services.llm_service.get_llm_service().list_models()` ON THE MAIN THREAD deliberately ("local /api/tags with short timeout", coach_screen.py:453-465); persists pick to setting `LLM_COACH_MODEL` via `save_user_setting`; uninstalled saved model advertised as "{name} (not installed)" instead of silent swap (coach_screen.py:494-501); gemma-family models sorted first.

### HomeScreen (`screens/home_screen.py`, 987 lines) — dashboard + ingestion entry point

- Status strip: three StatusChips fed by AppState signals — coach_status (idle→neutral else warning, home_screen.py:923-930), service online/offline, matches count. Matches chip prefers the row-derived personal count from `MatchHistoryViewModel` over AppState's distinct-demo count (`_matches_chip_populated` gate, home_screen.py:968-977).
- Hero pair: `LastMatchHeroCard` (last user match + last-10 rating sparkline, home_screen.py:701-709) and `FocusInsightCard` from FocusInsightViewModel. Cold start (no personal matches) swaps hero page for an onboarding EmptyState (home_screen.py:683-699).
- Demo ingestion (personal + pro): the ONLY UI path that triggers backend ingestion — `Programma_CS2_RENAN.run_ingestion.process_new_demos(is_pro=...)` in a Worker (home_screen.py:812-821, 841-850); single `_ingestion_worker` slot prevents concurrent runs; on done, emits a synthetic `notification_received` toast directly on AppState (home_screen.py:882-889 — UI emitting a backend-owned signal) and reloads both VMs. Parsing progress bar fed by `AppState.parsing_progress_changed` (visible only 0<p<100).
- Folder pickers persist `DEFAULT_DEMO_PATH` / `PRO_DEMO_PATH` via `save_user_setting` (home_screen.py:774-790).
- Training Status card: hidden unless `training_changed` payload has total_epochs>0; shows epoch/loss/val-loss/ETA + "teacher daemon · jepa_train.py" footer (home_screen.py:939-966). This is where JEPA training progress surfaces.
- FIELD-GAPs documented inline: pending-demo count, pro last-sync timestamp, pro corpus size (proxy = distinct over loaded ≤50 rows) (home_screen.py:599-610, 690-692).

### TacticalViewerScreen (`screens/tactical_viewer_screen.py`, 1709 lines) — 2D replay + ghost AI

- Demo load: file picker (start dir `DEFAULT_DEMO_PATH`) → FE-03 hardening: realpath, `.dem` extension check, size >= `backend.data_sources.demo_format_adapter.MIN_DEMO_SIZE` (10 MB) before touching the C extension (tactical_viewer_screen.py:990-1028). Parse = `ingestion.demo_loader.DemoLoader().load_demo(path)` in a Worker; `_DemoLoaderLogBridge` (tactical_viewer_screen.py:62-103) taps `cs2analyzer.demo_loader` INFO log records into the QProgressDialog for live phase text. Cancel does NOT stop the parse (no cooperative cancel in demoparser2); result is still surfaced when it arrives (tactical_viewer_screen.py:1087-1129). Expected data shape: dict of `map_name -> (frames, events, segments)` 3-tuples; `_`-prefixed metadata keys filtered with logging (tactical_viewer_screen.py:1141-1165).
- Playback: `QtPlaybackEngine` + TacticalPlaybackVM; per-demo tick rate resolved via `run_ingestion._parse_demo_header_meta` (32..256 sanity window, fallback `core.tick_rate.DEFAULT_TICK_RATE` with a loud warning — 26-TICK fix, tactical_viewer_screen.py:1622-1637). 100 ms QTimer updates tick label/timeline/play-button state.
- Frame render path (GUI thread): `_on_frame_update` → `TacticalGhostVM.predict_ghosts(frame.players)` EVERY frame while ghost toggle on → `TacticalMapWidget.update_map(players, nades, ghosts, tick)` + CT/T sidebars (tactical_viewer_screen.py:1328-1345). Score strip and bomb marker are FIELD-GAP (InterpolatedFrame carries neither).
- Chronovisor (RAP critical moments): after demo load, match_id resolved from `PlayerTickState.demo_name` in a Worker (F-0038: was a GUI-thread freeze on a 429M-row table, tactical_viewer_screen.py:1655-1689) → `TacticalChronovisorVM.scan_match(match_id)`; scan requires `USE_RAP_MODEL=True`. CM transport buttons start disabled; enabled only when scan finds moments (R4 MED, tactical_viewer_screen.py:853-859, 1639-1653); star/diamond/circle glyphs on timeline.
- Ghost Mode (frame 14): `set_ghost_payload(payload)` public seam — TacticalGhostVM provides NO divergence/path/causal data today (FIELD-GAP, tactical_viewer_screen.py:1416-1423); `_GhostPanel` renders YOU/GHOST cards + 6-metric divergence grid + "Causal score (RAPPedagogy)" defensively, "—" for absent fields (tactical_viewer_screen.py:126-150, 265-328). Footer composes `RAPPedagogy.CausalAttributor · positioning 0.xx …` only from present components (tactical_viewer_screen.py:1511-1521).
- WebEngine marquee (P4, opt-in): if `use_webengine_marquee` AND `web/tactical-viewer/dist/index.html` exists, central map is a QWebEngineView + QWebChannel + `MarqueeBridge`; VM frames forwarded as minimal JSON (players+tick, nades TODO) via `publish_tick/publish_frame`; map/segments/events published on map switch (tactical_viewer_screen.py:1267-1287); web ghost requests answered by `predict_ghosts` normalized through `core.spatial_engine.SpatialEngine.world_to_normalized` (tactical_viewer_screen.py:540-572). Decision made at __init__; toggle flip needs restart.
- `open_moment(demo, tick)` deep-link from match detail: seeks only when the same demo stem is already loaded, else toast "open demo here first" (cross-demo auto-load FIELD-GAP, tactical_viewer_screen.py:1575-1606).

### MatchDetailScreen (`screens/match_detail_screen.py`, 1227 lines) — tabbed drill-down

- Renders exclusively from `MatchDetailViewModel.data_changed` 4-tuple; last payload cached for `retranslate()` (match_detail_screen.py:13-16, 250). Tabs: Overview (5 hero tiles with rating/KD/ADR/KAST sentiment coloring, round win/loss dot strip, HLTV 2.0 MetricBarRow grid, Kill Enrichment band with opening-kill W/L computed from rounds, Utility band with unused-util>=1.0 warning tint), Rounds (frame-10 mono table; bomb outcome and enemies-left are FIELD-GAPs — not in RoundStats payload, match_detail_screen.py:799-813), Economy (`EconomyChart.plot(rounds)` + full/force/eco buy classification at $4500/$3000, match_detail_screen.py:940-1026), Highlights (`MomentumChart` + Critical Moments card + coaching insight cards).
- Critical moments: `set_critical_moments(moments)` public seam — the VM payload has no match_id/tick data, so the caller/fixture supplies chronovisor dicts; empty state points user to Tactical Viewer scan (FIELD-GAP, match_detail_screen.py:1030-1045). "Open in Tactical Viewer" emits `moment_selected(demo, start_tick)` (match_detail_screen.py:1147-1153).
- Insight cards colored by `severity_color`; all DB-sourced labels `Qt.PlainText` (FE-01). Tab restore by NAME across rebuilds (indices shift when rounds tabs absent, match_detail_screen.py:276-306). Hero DeltaChip vs personal average is a documented FIELD-GAP (baseline not in payload; lives on Match History rows instead, match_detail_screen.py:407-415).

### PerformanceScreen (`screens/performance_screen.py`, 828 lines) — aggregate analytics

- Fed by `PerformanceViewModel` (data/context/error/loading). Body QStackedWidget: skeleton | empty | content. `is_pro_overview` shows an explicit provenance banner ("Showing aggregated stats from all parsed pro matches", performance_screen.py:124-140) and suppresses vs-pro deltas — honest labeling of reference data.
- Sections: hero strip (avg rating/matches/KD/ADR/KAST with sentiment), "Versus pro cohort" percentile strip from `context_changed` (>=66th green, <=33rd red; missing metrics skipped, performance_screen.py:332-394), Rating Trend card (last-5 vs overall ±0.05 → Improving/Declining/Stable + RatingSparkline of last 8), Strengths & Weaknesses vs pro average (z-scores from `analytics.get_strength_weakness`), per-map MapTile grid, Utility Effectiveness vs pro (±5% band → "≈ pro level"; waste metric sign follows SENTIMENT — more waste than pro shown as ▼, performance_screen.py:751-780; missing pro baseline → "—" not a fake comparison).
- Each section builder wrapped in try/except with logged errors so one bad section doesn't kill the page (performance_screen.py:247-286).

### Other screens

- `screens/match_history_screen.py` (459) — MatchHistoryViewModel-fed; source chips All/Personal/Pro + dynamic map chips (top 8 by count via `map_short_name`); TODAY/THIS WEEK/EARLIER buckets by elapsed time not calendar (match_history_screen.py:71-85); per-row DeltaChip vs personal average of the WHOLE loaded list (zero ratings excluded as failed parses, match_history_screen.py:306-319); pro-only banner when no personal matches; header caption via `count_personal_and_pro`. Uses `Animator.fade_in` on the list container (opacity effect — but not during a stacked-widget transition).
- `screens/pro_comparison_screen.py` (847) — ProComparisonViewModel-fed; Pro-vs-Pro and Me-vs-Pro modes. Me-vs-Pro belief gate: <10 personal matches (`maps_played` in user stats payload) → frame-20 EmptyState instead of a half-empty radar (pro_comparison_screen.py:50-57, 568-578). Radar: 8 axes from key-groups normalized pairwise (both sides must carry a key; empty axis → neutral 50/50, never a spike-to-center, pro_comparison_screen.py:92-231). H2H table: absent keys → "—" never fabricated 0 (R4 HIGH note, pro_comparison_screen.py:70-75, 144-163 — zero values also treated as absent since the VM backfills 0.0); winner ties within eps → "even". Style-summary archetype rule ladder (pro_comparison_screen.py:234-277). MatchContains completer for nickname search. FIELD-GAPs: several H2H rows not on ProPlayerStatCard, no period/time_span, no scrape date.
- `screens/placeholder.py` (59) — `create_placeholder_screens()` returns 13 generic PlaceholderScreens, all overwritten by the 15 real screens in app.py.
- `screens/settings_screen.py` (1021) — 3 tabs (Appearance/Paths & Data/General). Theme cards preview each theme's own tokens; wallpaper cards paint token gradients (header-only QImageReader size probe, no thumbnails); font pills → `ThemeEngine.set_font`; language pills → `i18n.set_language` + LANGUAGE setting (en/it/pt). Ingestion section: mode manual/auto (`INGEST_MODE_AUTO`), interval (`INGEST_INTERVAL_MINUTES`, validated int >= 1), Start Ingestion Worker running `process_new_demos` pro-then-user (settings_screen.py:973-1003). Quick Links incl. Reset Wizard (`SETUP_COMPLETED=False` → wizard) and Wipe local data: double-confirm then only a toast pointing to `tools/wipe_for_reingest_safe.py` — UI deliberately has NO destructive backend path (FIELD-GAP note, settings_screen.py:656-692). Flagship toggles bound to AppState setters (sounds/frameless/pyqtgraph/webengine). Footer documents FE-04 (settings saved to SETTINGS_PATH, chmod 0o600).
- `screens/wizard_screen.py` (840) — 5-step first-run wizard (Intro/Name/Brain Path/Demo Path/Launch). Persists `CS2_PLAYER_NAME`, `BRAIN_DATA_ROOT` (creates knowledge/models/datasets subdirs with EACCES fallback to ~/Documents/DataCoach, wizard_screen.py:723-800), optional `DEFAULT_DEMO_PATH`; finish sets `SETUP_COMPLETED=True` and emits `setup_completed`. PlayerProfile row created in a Worker (F-0038 GUI-freeze fix, wizard_screen.py:804-840). Live path validation row (writable/free space/existing data) recomputed per keystroke against nearest existing ancestor. Launch page: "Coach unlocks as belief grows" + calibration TipBox (belief-% transparency copy — an AI-trust surface). Directory-tree captions name RAG embeddings/JEPA+RAP checkpoints/cached tensors (wizard_screen.py:45-49).
- `screens/profile_screen.py` (302) — In-Game Name editor; saves `CS2_PLAYER_NAME` + PlayerProfile upsert in Worker with id echoed back into a `DbRecordCard` (created_at/matches_analyzed/last_match render "—" — no profile VM exists; screens must not open new DB read paths, FIELD-GAP note profile_screen.py:219-242). "Stored locally" TipBox documents FE-04.
- `screens/user_profile_screen.py` (228) — UserProfileViewModel-fed display of name/role/bio + edit dialog → `save_profile`. Role→token color map (entry=error, awper=info, lurker=warning, support=success, igl=accent). Steam sync button permanently disabled here.
- `screens/steam_config_screen.py` (268) — persists `STEAM_ID` (validated `\d{17}` — R4 LOW zero-trust, steam_config_screen.py:200-207) + `STEAM_API_KEY` (keyring via config; plaintext warning if keyring missing). Sync Now → Worker → `ProfileService().fetch_steam_stats`.
- `screens/faceit_config_screen.py` (147) — persists `FACEIT_API_KEY` only; no backend call; `retranslate()` is a documented no-op (English-only labels, faceit_config_screen.py:44-46).
- `screens/help_screen.py` (598) — topic rail + article panel; topics from `backend.knowledge_base.help_system.get_help_system().get_all_topics()` (docs at `Programma_CS2_RENAN/data/docs/*.md`) with hardcoded `_FALLBACK_TOPICS` when unavailable (help_screen.py:36-41, 499-514); note: help_system import is at MODULE level (runs at app boot via `_create_screens`). Getting Started renders a structured frame-19 article; substring search filters topics; external links open browser. Help copy documents the Ollama/gemma4:e2b chat requirement and DS-12 10 MB demo guard.
- `screens/pro_player_detail_screen.py` (341) — ProPlayerDetailViewModel-fed drill-down: header card (nickname/real name/country/team/age/time-span), 12-metric stats grid from `stat_card` ("—" for None), Recent Matches from `detailed_stats_json["matches"]` (top 10; empty state "HLTV match history not yet scraped"). `back_requested` wired by app.py to return to pro_comparison. English-only `retranslate()`.
- `screens/__init__.py` — docstring only.

## Suspicious findings

1. __GhostEngine loads on the GUI thread__ — `TacticalGhostVM._ensure_loaded` (tactical_vm.py:114-123) constructs `backend.nn.inference.ghost_engine.GhostEngine()` synchronously in the `set_active` slot (checkbox toggle). If model load is slow (torch import, checkpoint read), the UI freezes — the only backend-heavy call NOT routed through a Worker besides the deliberate Ollama list_models. `predict_ghosts` also runs per-frame on the GUI thread inside `_on_frame_update` (tactical_viewer_screen.py:1331); per-player NN inference at up to 60 fps is a latent jank source if predict_tick is not trivially cheap.
2. __Graphics-effects ban vs. actual usage__ — the memory-documented Linux ban is honored for screen transitions (main_window.py:349-351) and geometry-based toasts/toggles, but `QGraphicsOpacityEffect` is still used by `Animator.fade_in/out/pulse/cross_fade` (animation.py:41-48) — reached from `MatchHistoryScreen._render_filtered` (fade_in on the list container, match_history_screen.py:344), toast dismiss fade_out, and `SkeletonRect` pulse — and `Card` floating/frosted mounts `QGraphicsDropShadowEffect` (card.py:127-159). The animation module documents these as unsafe only mid-repaint; they are applied outside stacked-widget transitions, but the risk surface is nonzero.
3. __UI writes to backend-owned state__ — the doctrine says AppState is read-only toward CoachState with ONE sanctioned write (notification mark-read). Additional UI-originated DB writes exist: `UserProfileViewModel.save_profile`, ProfileScreen/WizardScreen PlayerProfile upserts (all Worker-safe but they are UI→DB write paths), and `HomeScreen`/`SettingsScreen` emit `notification_received` directly on AppState (home_screen.py:882-889, settings_screen.py:686-692) — a UI component emitting a signal that otherwise represents backend `ServiceNotification` rows.
4. __Coach chat model pick may not reach the engine__ — the combo persists `LLM_COACH_MODEL` via `save_user_setting` (coach_screen.py:510-522) but nothing re-creates or notifies the already-constructed `CoachingDialogueEngine` singleton (`get_dialogue_engine()`); whether the engine re-reads the setting per request is a backend-side contract this cluster cannot verify — flag for the services cluster.
5. __Ollama model discovery on the main thread__ — `_refresh_llm_models` (coach_screen.py:453-465) does a network call (localhost /api/tags) on the GUI thread; a hung Ollama socket with a long timeout would freeze the app. Documented as deliberate, but timeout ownership lives in llm_service.
6. __module-level import side effects at boot__ — `help_screen.py` imports `backend.knowledge_base.help_system` at module level (help_screen.py:36-41), and `i18n_bridge` loads all JSON translation files at import (i18n_bridge.py:63-64). Both run during `_create_screens` on the splash path; failures are guarded but they add backend import weight to UI boot.
7. __Fixed 5-minute heartbeat window__ — `service_active = (now - last_heartbeat) < 300 s` (app_state.py:124-129 → 169-171). With a 10 s poll and Pulse-thread cadence unknown to this cluster, a slow-but-alive Session Engine flaps "Service: Offline"; the threshold is hardcoded, not a shared constant with the Pulse writer.
8. __Match history cancel is cosmetic__ — `MatchHistoryViewModel.cancel()` sets an Event only checked AFTER the DB query completes (match_history_vm.py:104-106); a slow query still runs to completion on screen leave.
9. __Belief confidence normalization guess__ — `_on_belief` treats values >1.0 as legacy percentages and divides by 100 (coach_screen.py:555-560). A genuine future confidence of, say, 1.2 (miscalibrated model) would be silently rescaled — the UI masks a backend contract ambiguity rather than asserting it.
10. __Placeholder screens are dead weight__ — `create_placeholder_screens()` returns 13 entries that are ALL immediately overwritten by `_create_screens()`'s 15 real screens (app.py:343-347); the placeholder path exists only as an import-failure fallback that can no longer trigger (a broken screen import raises before `placeholders.update`).
11. __Note-file contention observed during this campaign__ — while writing these notes the file was twice reverted to an earlier skeleton by an external process (parallel doctrine agents doing git stash/checkout cycles in the same worktree, or a stale IDE buffer). Content was recovered from context each time; worth knowing for future multi-agent campaigns in this repo.
12. __Positive findings worth keeping__ (doctrine-relevant honesty patterns): pervasive FIELD-GAP comments render "—" instead of fabricating values (match rows, H2H table, ghost divergence panel, driver rows); FocusInsightVM explicitly refuses to claim uncomputed measurements (R4 anti-fabrication); Me-vs-Pro is belief-gated at n>=10; pro-reference data always carries a provenance banner; FE-01 `Qt.PlainText` on every DB-sourced label; FE-03 demo-file validation before the C parser; FE-04 chmod 0o600 settings.

# Audit Report 09 — Desktop App & UI

**Scope:** `apps/desktop_app/`, `assets/i18n/` — 20 files, ~5,958 lines | **Date:** 2026-03-10
**Open findings:** 1 HIGH | 15 MEDIUM | 9 LOW

---

## HIGH Finding

| ID | File | Finding |
|---|---|---|
| U-21 | layout.kv | ~20+ hardcoded English strings bypass i18n system — mixed-language UI for PT/IT users |

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| U-01 | data_viewmodels.py | MatchDetailViewModel has no cancellation support (stale results overwrite) |
| U-02 | data_viewmodels.py | Inconsistent ORM API: session.query() vs session.exec(select()) |
| U-03 | data_viewmodels.py | PerformanceViewModel._bg_load lacks finally guard for is_loading reset |
| U-05 | match_detail_screen.py | `_MAP_PATTERN` and `_extract_map_name` duplicated from match_history_screen.py |
| U-06 | match_detail_screen.py | `_section_card` helper duplicated in performance_screen.py |
| U-07 | performance_screen.py | Map cards in horizontal layout with no ScrollView — overflow risk |
| U-11 | tactical_map.py | `time.time()` for molotov animation — wall-clock can jump |
| U-13 | tactical_map.py | `_heatmap_generation_id` read/write without synchronization (GIL-dependent) |
| U-15 | tactical_viewmodels.py | Non-PEP8 import ordering — constant before imports |
| U-17 | timeline.py | No event density throttling — hundreds of rects per redraw |
| U-18 | widgets.py | matplotlib `savefig()` on main thread — 100-500ms UI jank |
| U-19 | wizard_screen.py | Dead imports: `subprocess` and `sys` in `finish_setup()` |
| U-22 | layout.kv | Hardcoded `height: "140dp"` instead of adaptive_height |
| U-23 | layout.kv | Debug/Ghost toggle switches lack WCAG accessible descriptions |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| U-04 | help_screen.py | Help system placeholder — not implemented |
| U-08 | player_sidebar.py | `radius = [12,]` trailing comma style |
| U-09 | player_sidebar.py | Commented-out dead code |
| U-10 | player_sidebar.py | Fragile `"CT" in str(p.team).upper()` instead of Team enum |
| U-12 | tactical_map.py | Redundant local NadeType re-import |
| U-14 | tactical_viewer_screen.py | Legacy backward-compatibility properties |
| U-16 | tactical_viewmodels.py | No circuit breaker for systematic ghost prediction failures |
| U-20 | wizard_screen.py | Overly broad try/except around single screen assignment |
| U-24 | it.json | Typo: "como" (Portuguese) should be "come" (Italian) |

## Cross-Cutting

1. **MVVM Safety Inconsistency** — MatchHistoryViewModel has cancellation + finally guard; MatchDetailViewModel and PerformanceViewModel have neither.
2. **Code Duplication** — `_extract_map_name`, `_section_card`, `_show_placeholder` patterns duplicated across screens.
3. **i18n Gap** — ~20+ hardcoded English strings in layout.kv create mixed-language UI for non-English users.

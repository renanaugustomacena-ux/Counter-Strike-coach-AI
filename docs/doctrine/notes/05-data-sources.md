# Cluster 05 — `backend/data_sources/`

Files read (all 14): demo_parser, parse_guard, demo_format_adapter, event_registry,
round_context, trade_kill_detector, faceit_api, faceit_integration, steam_api,
steam_demo_finder, hltv_scraper, hltv/{stat_fetcher, flaresolverr_client, docker_manager}.

## demo_parser.py — the ground-truth boundary

- **Real timeout** (F-0013): manual ThreadPoolExecutor + `shutdown(wait=False)` — the `with` form silently blocked forever on a hung Rust parse; orphan thread abandoned loudly. Timeout scales with file size (max(300s, 3s/MB), H-02).
- **`_final_scoreboard_totals` uses LAST value per player, not max()** — reused tournament servers record warmup with the previous match's scoreboard live (+146 phantom kills observed on PGL Astana demos, 2026-07-22). "Last" is also correct for disconnects/substitutes.
- **KAST is event-driven first** (`_compute_event_kast` groups deaths per round through the canonical `calculate_kast_for_round`, trade window from real tick rate DS-07); closed-form estimate is a loud fallback only — it saturates at 1.0 for ≥1 kill/round players (stamped 1.0 on 8/10 pros of the first real demo).
- **No fabricated fallbacks** (R3-01): avg_hs/accuracy/avg_kast start at 0.0 = "no data, not measured"; `data_quality` ∈ none/partial/complete tells training to filter/weight; underestimating rating is explicitly preferred to overestimating.
- **HLTV 2.0 parity contract**: `_apply_hltv2_columns` mirrors rating.compute_rating_components exactly — raw component scale, normalization ONLY inside the aggregate rating; pinned by test_rating_components_contract ("change both or neither"). impact_rounds = share of rounds with ≥1 kill ∈ [0,1] — the old alias that wrote impact RATING into it is dead (contract with SQL aggregator + baselines).
- `parse_sequential_ticks`: full WP6 field list; **the legacy sampling stride was "the LAST live tick-decimation mechanism in the repo — removed entirely"** (supreme invariant); `total_rounds_played` must be explicitly requested on events (silent None → 3 stats dying to 0.0, E2E 2026-07-17).

## parse_guard.py (F-0006 SSOT)

demoparser2/pyo3 PanicException subclasses BaseException and is created lazily (name-based detection). `is_parse_error` absorbs Exception + PanicException; KeyboardInterrupt/SystemExit/GeneratorExit ALWAYS propagate. Every parser call site uses the `except BaseException → if not is_parse_error: raise` idiom.

## Support modules

- `demo_format_adapter.py` (Proposal 12): magic-byte validation (PBDEMS2 supported; HL2DEMO legacy rejected), 10MB-5GB bounds, corruption heuristics as warnings; canonical field mapping documented for future format shifts.
- `event_registry.py`: canonical spec of ~24 CS2 events with fields/priority/implemented/handler_path — parser-coverage bookkeeping (`get_coverage_report`). NOTE: several `implemented=False` entries (smoke/flash/HE detonate) ARE extracted in run_ingestion `_EventExtractor` — registry lags reality (doc drift, flagged).
- `round_context.py`: freeze_end/round_end pairing → merge_asof round assignment; `tick_rate` is a REQUIRED kwarg (26-TICK); **time_in_round has no upper clamp** (bomb plants extend rounds; the 115s clamp flattened the temporal signal); warmup ticks explicitly 0.0.
- `trade_kill_detector.py`: roster from early-tick team_num mode; backward scan within same round + 3s window (in demo ticks); loud header-parse fallback (128-tick silently halves the window and "drops every legitimate trade in the 1.5-3.0s band").

## External integrations

- `hltv/stat_fetcher.py`: robots.txt preflight (with Cloudflare-HTML detection DP-04), 2-7s random delays + adaptive backoff on consecutive failures, CSS selector fallback chains with layout-change warnings, minimum-viable-fields gate before persisting (H2: rating=0 ⇒ parse failure, skip), **thousands-separator guard** (R4 HIGH: "39,606" → 39.606 poisoned every ratio), end-date computed at request time (was frozen at a hardcoded past date). Percentages normalized to ratios at the save boundary.
- `flaresolverr_client.py` + `docker_manager.py`: Cloudflare bypass via local Docker headless browser; ensure→start→compose-up ladder with health polling; persistent sessions with leak-aware destroy.
- `faceit_integration.py`: 10 req/min rate limiting, Retry-After parsing hardened (HTTP-date crash R4 MED), SSRF guard (https-only demo URLs), size-capped streamed downloads, match-id path traversal check.
- `steam_api.py`: retry with total-deadline budget (DS-03), vanity URL resolution, Steam64 validation.
- `steam_demo_finder.py`: supplementary to steam_locator (F6-11 dual-authority acknowledged), registry→drive-scan ladder.
- `hltv_scraper.py`: thin sync-cycle entry over HLTVStatFetcher.

## Invariants observed (doctrine candidates)

- **Never decimate ticks; never fabricate stats.** 0.0 means "missing", and a flag says so.
- **The parser is a hostile FFI boundary** — one SSOT guard, absorbed panics, real timeouts, orphaned threads over hung daemons.
- **Cross-module numeric contracts are pinned by tests** (rating components; impact_rounds semantics) — vectorized and scalar implementations must move together.
- **Scraping is polite, legal-aware, and self-doubting**: robots.txt, rate limits, layout-change canaries, minimum-viability gates, and refusal to persist parse garbage.
- **Boundary normalization**: percentages→ratios, comma-locale numbers, name-column variance per event type — all resolved AT the boundary, never downstream.

## Risks / open questions carried forward

- event_registry `implemented` flags stale vs `_EventExtractor` reality (utility events) — inventory drift, not code drift.
- `_compute_event_kast` (demo_parser.py:343) and trade_kill_detector both use inline `header.get("tick_rate", 64)` fallbacks rather than `resolve_tick_rate` — loud, but another SSOT bypass to weigh in doctrine.
- Two Steam discovery modules remain (consolidation deferred).

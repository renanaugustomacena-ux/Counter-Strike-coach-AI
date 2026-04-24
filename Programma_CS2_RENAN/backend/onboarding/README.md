> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Onboarding -- New User Flow Management

> **Authority:** Rule 3 (Frontend & UX), Rule 4 (Data Persistence)

This module manages the new user onboarding workflow for the CS2 Coach AI
application. It tracks how many demos a user has ingested, maps that count to
a readiness stage, and gates access to coaching features based on data
availability. The system is designed to be lightweight, stateless per call,
and cache-friendly so the UI can poll it without incurring repeated database
round-trips.

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Package marker | -- |
| `new_user_flow.py` | ~136 | Onboarding stage management and demo-count caching | `UserOnboardingManager`, `OnboardingStatus`, `OnboardingStage`, `get_onboarding_manager()` |

## Architecture & Concepts

### OnboardingStage

`OnboardingStage` is a plain class with three string constants that name
the possible stages a user can be in:

| Constant | Value | Meaning |
|----------|-------|---------|
| `AWAITING_FIRST_DEMO` | `"awaiting_first_demo"` | No demos ingested yet. The coach cannot operate. |
| `BUILDING_BASELINE` | `"building_baseline"` | Between 1 and `RECOMMENDED_DEMOS - 1` demos. Coaching is active but the baseline is not stable. |
| `COACH_READY` | `"coach_ready"` | At least `RECOMMENDED_DEMOS` demos. Full coaching capability. |

### OnboardingStatus

A frozen snapshot returned by `get_status()`. It is a `@dataclass` with
the following fields:

```
OnboardingStatus
  stage: str               # One of the OnboardingStage constants
  demos_uploaded: int       # Total non-pro demos for the user
  demos_required: int       # MIN_INITIAL_DEMOS (currently 1)
  demos_recommended: int    # RECOMMENDED_DEMOS (currently 3)
  coach_ready: bool         # True when demos_uploaded >= MIN_INITIAL_DEMOS
  baseline_stable: bool     # True when demos_uploaded >= RECOMMENDED_DEMOS
  message: str              # Human-readable stage description
```

### Thresholds

| Constant | Value | Purpose |
|----------|-------|---------|
| `MIN_INITIAL_DEMOS` | 1 | Minimum to unlock basic coaching |
| `RECOMMENDED_DEMOS` | 3 | Target for a stable personal baseline |
| `_CACHE_TTL_SECONDS` | 60 | TTL for the in-memory demo-count cache |

### Demo Count Caching (TASK 2.16.1)

`UserOnboardingManager` maintains a per-user in-memory cache
(`_demo_count_cache`) that maps `user_id` to a `(count, timestamp)` tuple.
When `get_status()` is called, the manager first checks whether the cached
count is still within `_CACHE_TTL_SECONDS` of the current monotonic time.
If so, the cached value is returned without hitting the database.

After a new demo is uploaded, the caller should invoke
`invalidate_cache(user_id)` to ensure the next `get_status()` call
reflects the updated count immediately. Calling `invalidate_cache()`
without arguments clears the entire cache.

### Database Query

The manager queries `PlayerMatchStats` to count non-pro demos:

```python
select(func.count(PlayerMatchStats.id)).where(
    PlayerMatchStats.player_name == user_id,
    PlayerMatchStats.is_pro == False,
)
```

Only user-uploaded demos count toward onboarding progress. Professional
demos ingested for the training baseline are excluded (DA-16-01).

### Stage Determination Flow

```
demos_uploaded == 0  -->  AWAITING_FIRST_DEMO
0 < demos_uploaded < RECOMMENDED_DEMOS  -->  BUILDING_BASELINE
demos_uploaded >= RECOMMENDED_DEMOS  -->  COACH_READY
```

## Integration

- **UI (Qt):** `HomeScreen` and the onboarding wizard query `get_status()`
  to display progress indicators, welcome messages, and gating dialogs.
- **CoachingService:** Checks `coach_ready` before generating
  high-confidence coaching insights. When `coach_ready` is `False`,
  insights are still generated but annotated with a low-confidence warning.
- **Ingestion Pipeline:** After a demo is ingested, the pipeline calls
  `invalidate_cache()` so the next UI poll sees the updated count.
- **Database:** The module reads from `PlayerMatchStats` in
  `database.db`. It performs no writes or mutations.

## Development Notes

- `UserOnboardingManager` recalculates the stage on every call to
  `get_status()`. It is stateless aside from the TTL cache.
- The `get_onboarding_manager()` factory is a module-level singleton
  (`new_user_flow.py:133-140`): the first call constructs the instance
  and subsequent calls return the cached reference, so all callers share
  the same TTL cache.
- Stage thresholds are class-level constants. If they need to become
  configurable, promote them to `core/config.py` user settings.
- Never gate features completely based on stage. Always allow coaching
  output, but annotate it with confidence level derived from the stage.
- The `message` field in `OnboardingStatus` is a user-facing string.
  Keep it concise and encouraging. Translations are handled at the UI
  layer, not in this module.
- The module uses structured logging via
  `get_logger("cs2analyzer.onboarding")`.
- The cache uses `time.monotonic()` rather than wall-clock time to avoid
  issues with system clock adjustments.

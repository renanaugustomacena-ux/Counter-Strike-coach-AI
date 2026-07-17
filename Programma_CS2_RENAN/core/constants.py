# Project-wide constants (H-10, M-08, M-12, L-28).
# All temporal constants defined in seconds, derived tick values computed at import.

from Programma_CS2_RENAN.core.tick_rate import DEFAULT_TICK_RATE

# === Tick Rate ===
TICK_RATE: int = DEFAULT_TICK_RATE
"""Legacy alias of the 26-NORM-01 SSOT (core.tick_rate.DEFAULT_TICK_RATE).

Import the SSOT directly in new code; per-demo work must resolve the real
rate (resolve_tick_rate), never assume this default."""

# === Field of View ===
FOV_DEGREES: float = 90.0
"""Standard CS2 horizontal field of view in degrees."""

# === Spatial Constants ===
Z_FLOOR_THRESHOLD: float = 200.0
"""Minimum Z-distance (world units) to consider players on different floors (H-11)."""

# === Temporal constants — SECONDS ONLY ===
# R4 HIGH / 26-TICK (2026-07-16): the import-time "seconds -> ticks"
# derivations (SMOKE_MAX_DURATION_TICKS, FLASH_DURATION_TICKS,
# MEMORY_*_TICKS, TRADE_WINDOW_TICKS) baked in TICK_RATE=64 and were all
# dead code after C1/DS-07 — every runtime path derives tick windows from
# the per-demo MatchMetadata.tick_rate. Removed to close the GIGO surface:
# tick windows MUST be computed at point of use from the per-demo rate.

# === Utility Durations ===
SMOKE_DURATION_S: float = 18.0
MOLOTOV_DURATION_S: float = 7.0
FLASH_DURATION_S: float = 2.0

# === Memory Constants ===
MEMORY_DECAY_TAU_S: float = 2.5
MEMORY_CUTOFF_S: float = 7.5  # L-28: 3*tau (was 5.0s = 2*tau)

# === Trade Kill ===
TRADE_WINDOW_S: float = 3.0

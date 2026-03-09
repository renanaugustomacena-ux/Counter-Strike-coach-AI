# Project-wide constants (H-10, M-08, M-12, L-28).
# All temporal constants defined in seconds, derived tick values computed at import.

# === Tick Rate ===
TICK_RATE: int = 64
"""CS2 standard tick rate (ticks per second)."""

# === Field of View ===
FOV_DEGREES: float = 90.0
"""Standard CS2 horizontal field of view in degrees."""

# === Spatial Constants ===
Z_FLOOR_THRESHOLD: float = 200.0
"""Minimum Z-distance (world units) to consider players on different floors (H-11)."""

# === Utility Durations (seconds -> ticks) ===
SMOKE_DURATION_S: float = 18.0
MOLOTOV_DURATION_S: float = 7.0
FLASH_DURATION_S: float = 2.0

SMOKE_MAX_DURATION_TICKS: int = int(SMOKE_DURATION_S * TICK_RATE)   # 1152
MOLOTOV_MAX_DURATION_TICKS: int = int(MOLOTOV_DURATION_S * TICK_RATE)  # 448
FLASH_DURATION_TICKS: int = int(FLASH_DURATION_S * TICK_RATE)       # 128

# === Memory Constants (seconds -> ticks) ===
MEMORY_DECAY_TAU_S: float = 2.5
MEMORY_CUTOFF_S: float = 7.5  # L-28: 3*tau (was 5.0s = 2*tau)

MEMORY_DECAY_TAU_TICKS: int = int(MEMORY_DECAY_TAU_S * TICK_RATE)  # 160
MEMORY_CUTOFF_TICKS: int = int(MEMORY_CUTOFF_S * TICK_RATE)        # 480

# === Trade Kill ===
TRADE_WINDOW_S: float = 3.0
TRADE_WINDOW_TICKS: int = int(TRADE_WINDOW_S * TICK_RATE)          # 192

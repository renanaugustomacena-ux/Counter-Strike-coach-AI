from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.playback")


class TimelineController(EventDispatcher):
    """
    Centralized Controller for Match Playback (Phase 2, 70%).
    Manages Tick state and notifies observers (Heatmap, MapView, Stats).
    """

    current_tick = NumericProperty(0)
    max_tick = NumericProperty(0)
    is_playing = BooleanProperty(False)
    playback_speed = NumericProperty(1.0)  # 1.0 = Realtime (approx)

    # Event definition
    __events__ = ("on_tick_update", "on_match_loaded")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._demo_data = None

    def load_match(self, demo_data: dict):
        """
        Loads processed demo data.

        Args:
            demo_data: Dictionary containing 'ticks', 'players', 'grenades', etc.
                       Typically output from demo_processor.
        """
        self._demo_data = demo_data
        # Determine max tick
        # Assuming demo_data has a 'max_tick' or we find it from events
        if "max_tick" in demo_data:
            self.max_tick = demo_data["max_tick"]
        else:
            # Derive max_tick from available tick data instead of arbitrary fallback
            tick_sources = [demo_data.get("ticks"), demo_data.get("events")]
            for src in tick_sources:
                if src and hasattr(src, "__len__") and len(src) > 0:
                    if isinstance(src, dict):
                        self.max_tick = max(src.keys()) if src else 0
                    elif hasattr(src[-1], "tick"):
                        self.max_tick = src[-1].tick
                    break
            else:
                self.max_tick = 0
            logger.warning(
                "No max_tick in demo_data — derived %d from available data", self.max_tick
            )

        self.current_tick = 0
        self.dispatch("on_match_loaded", demo_data)

    def set_tick(self, tick: int):
        """Jumps to specific tick."""
        tick = max(0, min(tick, self.max_tick))
        self.current_tick = tick
        self.dispatch("on_tick_update", tick)

    def scrub(self, percentage: float):
        """Scrub by percentage (0.0 - 1.0)."""
        tick = int(percentage * self.max_tick)
        self.set_tick(tick)

    def on_tick_update(self, tick):
        """Default handler (can be overridden)."""
        pass

    def on_match_loaded(self, data):
        """Default handler."""
        pass

    def get_players_at_tick(self, tick: int):
        """
        Retrieves player positions at the given tick.
        This is a helper for consumers like HeatmapEngine.
        """
        if not self._demo_data:
            return []

        # Implementation depends on how demo_data is structured.
        # Assuming a structure like: data['ticks'][tick_id] = [{'id': 1, 'pos': (x,y,z)}, ...]
        # Or a pandas dataframe logic.
        # For now, return a placeholder or look for a specific key.
        return self._demo_data.get("positions", {}).get(tick, [])

    def get_grenades_at_tick(self, tick: int, window: int = 128):
        """
        Retrieves grenades active around this tick.

        Searches the demo_data 'grenades' key for grenades whose
        [starting_tick, ending_tick] range overlaps with `tick`.
        Falls back to empty list if no grenade data is available.
        """
        if not self._demo_data:
            return []

        grenades = self._demo_data.get("grenades", [])
        if not grenades:
            return []

        active = []
        for g in grenades:
            start = g.get("starting_tick", 0)
            end = g.get("ending_tick", start + window)
            if start <= tick <= end:
                active.append(g)
        return active

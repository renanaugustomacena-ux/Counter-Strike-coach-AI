"""Performance Dashboard — aggregate trends, per-map stats, strengths/weaknesses, utility."""

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from Programma_CS2_RENAN.apps.desktop_app.data_viewmodels import PerformanceViewModel
from Programma_CS2_RENAN.apps.desktop_app.theme import (
    COLOR_CARD_BG as _COLOR_CARD_BG,
    COLOR_GREEN as _COLOR_GREEN,
    COLOR_RED as _COLOR_RED,
    rating_color as _rating_color,
    rating_label as _rating_label,
)
from Programma_CS2_RENAN.core.registry import registry
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.performance")


@registry.register("performance")
class PerformanceScreen(MDScreen):
    """Aggregate performance dashboard: trends, per-map, strengths, utility."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # P4-03: Delegate analytics access to ViewModel (MVVM)
        self._vm = PerformanceViewModel()
        self._vm.bind(history=self._on_vm_data_changed)
        self._vm.bind(error_message=self._on_vm_error)

    def on_pre_enter(self):
        # P4-04: Show loading indicator while data loads
        self._show_placeholder("Loading performance data...")
        self._vm.load_performance()

    def _on_vm_data_changed(self, instance, history):
        # DA-PS-01: Always call _populate — it handles empty data with a placeholder
        self._populate(
            list(history), dict(self._vm.map_stats),
            dict(self._vm.strength_weakness), dict(self._vm.utility),
        )

    def _on_vm_error(self, instance, msg):
        if msg:
            self._show_placeholder(msg)

    def _show_placeholder(self, text: str):
        container = self.ids.get("performance_container")
        if not container:
            return
        container.clear_widgets()
        container.add_widget(
            MDLabel(
                text=text,
                halign="center",
                theme_text_color="Hint",
                adaptive_height=True,
            )
        )

    def _populate(self, history: list, map_stats: dict, sw: dict, utility: dict):
        container = self.ids.get("performance_container")
        if not container:
            return
        container.clear_widgets()

        if not history and not map_stats:
            self._show_placeholder("No performance data. Play some matches!")
            return

        # Section 1: Rating Trend
        self._build_trend_section(container, history)

        # Section 2: Per-Map Stats
        if map_stats:
            self._build_map_section(container, map_stats)

        # Section 3: Strengths / Weaknesses
        if sw and (sw.get("strengths") or sw.get("weaknesses")):
            self._build_sw_section(container, sw)

        # Section 4: Utility Panel
        if utility:
            self._build_utility_section(container, utility)

    # --- Section Builders ---

    def _build_trend_section(self, container, history: list):
        card, content = self._section_card("Rating Trend")

        if not history:
            content.add_widget(
                MDLabel(
                    text="Not enough data for trend analysis.",
                    theme_text_color="Hint",
                    adaptive_height=True,
                )
            )
        else:
            from Programma_CS2_RENAN.apps.desktop_app.widgets import RatingSparklineWidget

            graph = RatingSparklineWidget(size_hint_y=None, height=dp(200))
            content.add_widget(graph)
            Clock.schedule_once(lambda dt: graph.plot(history), 0.1)

        container.add_widget(card)

    def _build_map_section(self, container, map_stats: dict):
        card, content = self._section_card("Per-Map Performance")

        # Horizontal scroll of map cards
        scroll_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="8dp",
        )

        for map_name, stats in map_stats.items():
            map_card = self._build_map_card(map_name, stats)
            scroll_row.add_widget(map_card)

        content.add_widget(scroll_row)
        container.add_widget(card)

    def _build_map_card(self, map_name: str, stats: dict) -> MDCard:
        card = MDCard(
            style="outlined",
            size_hint=(None, None),
            width=dp(160),
            height=dp(120),
            padding="8dp",
            md_bg_color=(0.15, 0.15, 0.17, 1),
        )
        col = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing="2dp",
        )
        rating = stats.get("rating", 1.0)
        col.add_widget(
            MDLabel(
                text=map_name.replace("de_", "").title(),
                font_style="Title",
                role="small",
                theme_text_color="Primary",
                adaptive_height=True,
            )
        )
        col.add_widget(
            MDLabel(
                text=f"Rating: {rating:.2f} ({_rating_label(rating)})",
                font_style="Headline",
                role="small",
                theme_text_color="Custom",
                text_color=_rating_color(rating),
                adaptive_height=True,
            )
        )
        col.add_widget(
            MDLabel(
                text=f"ADR: {stats.get('adr', 0):.0f}  K/D: {stats.get('kd', 0):.2f}",
                font_style="Body",
                role="small",
                theme_text_color="Secondary",
                adaptive_height=True,
            )
        )
        col.add_widget(
            MDLabel(
                text=f"{stats.get('matches', 0)} matches",
                font_style="Body",
                role="small",
                theme_text_color="Hint",
                adaptive_height=True,
            )
        )
        card.add_widget(col)
        return card

    def _build_sw_section(self, container, sw: dict):
        card, content = self._section_card("Strengths & Weaknesses (vs Pro)")

        row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="16dp",
        )

        # Strengths column
        str_col = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing="4dp",
        )
        str_col.add_widget(
            MDLabel(
                text="Strengths",
                font_style="Title",
                role="small",
                theme_text_color="Custom",
                text_color=_COLOR_GREEN,
                adaptive_height=True,
            )
        )
        for name, z in sw.get("strengths", []):
            str_col.add_widget(
                MDLabel(
                    text=f"+{z:.1f}σ  {name}",
                    font_style="Body",
                    role="small",
                    theme_text_color="Custom",
                    text_color=_COLOR_GREEN,
                    adaptive_height=True,
                )
            )
        if not sw.get("strengths"):
            str_col.add_widget(
                MDLabel(
                    text="No data",
                    theme_text_color="Hint",
                    adaptive_height=True,
                )
            )

        # Weaknesses column
        weak_col = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing="4dp",
        )
        weak_col.add_widget(
            MDLabel(
                text="Weaknesses",
                font_style="Title",
                role="small",
                theme_text_color="Custom",
                text_color=_COLOR_RED,
                adaptive_height=True,
            )
        )
        for name, z in sw.get("weaknesses", []):
            weak_col.add_widget(
                MDLabel(
                    text=f"{z:.1f}σ  {name}",
                    font_style="Body",
                    role="small",
                    theme_text_color="Custom",
                    text_color=_COLOR_RED,
                    adaptive_height=True,
                )
            )
        if not sw.get("weaknesses"):
            weak_col.add_widget(
                MDLabel(
                    text="No data",
                    theme_text_color="Hint",
                    adaptive_height=True,
                )
            )

        row.add_widget(str_col)
        row.add_widget(weak_col)
        content.add_widget(row)
        container.add_widget(card)

    def _build_utility_section(self, container, utility: dict):
        card, content = self._section_card("Utility Effectiveness (vs Pro)")

        user = utility.get("user", {})
        if not user or all(v == 0 for v in user.values()):
            content.add_widget(
                MDLabel(
                    text="No utility data available yet.",
                    theme_text_color="Hint",
                    adaptive_height=True,
                )
            )
            container.add_widget(card)
            return

        from Programma_CS2_RENAN.apps.desktop_app.widgets import UtilityBarWidget

        graph = UtilityBarWidget(size_hint_y=None, height=dp(250))
        content.add_widget(graph)
        Clock.schedule_once(lambda dt: graph.plot(utility), 0.1)

        container.add_widget(card)

    # --- Helpers ---

    def _section_card(self, title: str):
        card = MDCard(
            style="elevated",
            size_hint_y=None,
            padding="12dp",
            md_bg_color=_COLOR_CARD_BG,
        )
        content = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing="4dp",
        )
        content.add_widget(
            MDLabel(
                text=title,
                font_style="Title",
                role="large",
                theme_text_color="Primary",
                adaptive_height=True,
            )
        )
        card.add_widget(content)
        content.bind(height=lambda inst, h: setattr(card, "height", h + dp(24)))
        return card, content

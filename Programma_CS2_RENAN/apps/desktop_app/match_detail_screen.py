"""Match Detail Screen — round-by-round drill-down with economy and momentum."""

import re

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from Programma_CS2_RENAN.apps.desktop_app.data_viewmodels import MatchDetailViewModel
from Programma_CS2_RENAN.apps.desktop_app.theme import (
    COLOR_CARD_BG as _COLOR_CARD_BG,
    COLOR_GREEN as _COLOR_GREEN,
    COLOR_RED as _COLOR_RED,
    COLOR_YELLOW as _COLOR_YELLOW,
    rating_color as _rating_color,
    rating_label as _rating_label,
)
from Programma_CS2_RENAN.core.registry import registry
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.match_detail")

# Screen-specific color constants
_COLOR_CT = (0.36, 0.62, 0.91, 1)  # #5C9EE8
_COLOR_T = (0.91, 0.79, 0.36, 1)  # #E8C95C
_COLOR_SECTION_BG = (0.10, 0.10, 0.12, 1)

_MAP_PATTERN = re.compile(r"(de_\w+|cs_\w+|ar_\w+)")

_SEVERITY_ICONS = {
    "critical": ("alert-circle", _COLOR_RED),
    "warning": ("alert", _COLOR_YELLOW),
    "info": ("information", _COLOR_CT),
}


def _extract_map_name(demo_name: str) -> str:
    m = _MAP_PATTERN.search(demo_name)
    return m.group(1) if m else "Unknown Map"


@registry.register("match_detail")
class MatchDetailScreen(MDScreen):
    """Drill-down for a single match: overview, rounds, economy, highlights."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # P4-03: Delegate DB access to ViewModel (MVVM)
        self._vm = MatchDetailViewModel()
        self._vm.bind(stats=self._on_vm_data_changed)
        self._vm.bind(error_message=self._on_vm_error)

    def on_pre_enter(self):
        app = MDApp.get_running_app()
        # DA-MD-01: Use getattr to prevent AttributeError if never set
        demo = getattr(app, "selected_demo", None)
        if not demo:
            logger.warning("match_detail.no_demo_selected")
            Clock.schedule_once(
                lambda dt: self._show_placeholder("No match selected. Go back and select a match."),
                0,
            )
            return
        # P4-04: Show loading indicator while data loads
        self._show_placeholder("Loading match details...")
        self._vm.load_detail(demo)

    def _on_vm_data_changed(self, instance, stats):
        if not stats and not self._vm.rounds:
            # DA-MD-02: Clear loading state when no data returned
            self._show_placeholder("No match data available.")
            return
        self._populate_sections(
            dict(stats), list(self._vm.rounds),
            list(self._vm.insights), dict(self._vm.hltv_breakdown),
        )

    def _on_vm_error(self, instance, msg):
        if msg:
            self._show_placeholder(msg)

    def _show_placeholder(self, text: str):
        container = self.ids.get("detail_container")
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

    def _populate_sections(self, stats: dict, rounds: list, insights: list, hltv_breakdown=None):
        container = self.ids.get("detail_container")
        if not container:
            return
        container.clear_widgets()

        if not stats and not rounds:
            self._show_placeholder("No data found for this match.")
            return

        # Section 1: Overview
        self._build_overview_section(container, stats, hltv_breakdown)

        # Section 2: Round Timeline
        if rounds:
            self._build_rounds_section(container, rounds)

        # Section 3: Economy Graph
        if rounds:
            self._build_economy_section(container, rounds)

        # Section 4: Highlights & Momentum
        self._build_highlights_section(container, rounds, insights)

    # --- Section Builders ---

    def _build_overview_section(self, container, stats: dict, hltv_breakdown=None):
        card, section = self._section_card("Overview")

        rating = stats.get("rating", 1.0) or 1.0
        demo_name = stats.get("demo_name", "")
        map_name = _extract_map_name(demo_name)
        date_str = ""
        if stats.get("match_date"):
            try:
                date_str = stats["match_date"].strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = str(stats["match_date"])

        # Rating display
        rating_row = MDBoxLayout(
            orientation="horizontal",
            adaptive_height=True,
            spacing="12dp",
            padding=["0dp", "0dp", "0dp", "8dp"],
        )
        rating_row.add_widget(
            MDLabel(
                text=f"{rating:.2f} ({_rating_label(rating)})",
                font_style="Display",
                role="small",
                theme_text_color="Custom",
                text_color=_rating_color(rating),
                size_hint_x=None,
                width="180dp",
                adaptive_height=True,
            )
        )
        info_text = f"{map_name}  |  {date_str}"
        rating_row.add_widget(
            MDLabel(
                text=info_text,
                font_style="Title",
                role="medium",
                theme_text_color="Primary",
                adaptive_height=True,
            )
        )
        section.add_widget(rating_row)

        # Stats row
        avg_kills = stats.get("avg_kills", 0.0)
        avg_deaths = stats.get("avg_deaths", 0.0)
        avg_adr = stats.get("avg_adr", 0.0)
        avg_kast = stats.get("avg_kast", 0.0)
        kd = stats.get("kd_ratio", 0.0)
        hs = stats.get("avg_hs", 0.0)

        stats_text = (
            f"K/D: {kd:.2f}   ADR: {avg_adr:.1f}   "
            f"KAST: {avg_kast * 100:.0f}%   HS: {hs * 100:.0f}%   "
            f"Avg Kills: {avg_kills:.1f}   Avg Deaths: {avg_deaths:.1f}"
        )
        section.add_widget(
            MDLabel(
                text=stats_text,
                font_style="Body",
                role="medium",
                theme_text_color="Secondary",
                adaptive_height=True,
            )
        )

        # HLTV 2.0 Breakdown bars (P4-06: data pre-fetched in background thread)
        self._add_hltv_breakdown(section, hltv_breakdown)

        container.add_widget(card)

    def _add_hltv_breakdown(self, parent, breakdown=None):
        # P4-06: breakdown is now pre-fetched in background thread by _load_detail
        try:
            if not breakdown:
                return

            parent.add_widget(
                MDLabel(
                    text="HLTV 2.0 Components",
                    font_style="Title",
                    role="small",
                    theme_text_color="Primary",
                    adaptive_height=True,
                    padding=["0dp", "8dp", "0dp", "4dp"],
                )
            )

            for component, value in breakdown.items():
                row = MDBoxLayout(
                    orientation="horizontal",
                    adaptive_height=True,
                    spacing="8dp",
                )
                row.add_widget(
                    MDLabel(
                        text=component.replace("_", " ").title(),
                        font_style="Body",
                        role="small",
                        theme_text_color="Secondary",
                        size_hint_x=0.3,
                        adaptive_height=True,
                    )
                )
                row.add_widget(
                    MDLabel(
                        text=f"{value:.2f}",
                        font_style="Body",
                        role="small",
                        theme_text_color="Custom",
                        text_color=_rating_color(value),
                        size_hint_x=0.2,
                        adaptive_height=True,
                    )
                )
                parent.add_widget(row)
        except Exception as e:
            logger.warning("hltv_breakdown.unavailable: %s", e)

    def _build_rounds_section(self, container, rounds: list):
        card, section = self._section_card("Round Timeline")

        for r in rounds:
            rnum = r.get("round_number", 0)
            side = r.get("side", "?")
            won = r.get("round_won", False)
            kills = r.get("kills", 0)
            deaths = r.get("deaths", 0)
            dmg = r.get("damage_dealt", 0)
            opening = r.get("opening_kill", False)
            equip = r.get("equipment_value", 0)

            side_color = _COLOR_CT if side == "CT" else _COLOR_T
            result_color = _COLOR_GREEN if won else _COLOR_RED
            result_text = "W" if won else "L"
            opening_text = "  FK" if opening else ""

            row = MDBoxLayout(
                orientation="horizontal",
                adaptive_height=True,
                spacing="6dp",
                padding=["4dp", "2dp", "4dp", "2dp"],
            )

            # Round number + side
            row.add_widget(
                MDLabel(
                    text=f"R{rnum}",
                    font_style="Body",
                    role="small",
                    theme_text_color="Custom",
                    text_color=side_color,
                    size_hint_x=None,
                    width="36dp",
                    adaptive_height=True,
                )
            )

            # Win/Loss
            row.add_widget(
                MDLabel(
                    text=result_text,
                    font_style="Body",
                    role="small",
                    theme_text_color="Custom",
                    text_color=result_color,
                    size_hint_x=None,
                    width="24dp",
                    adaptive_height=True,
                    halign="center",
                )
            )

            # Stats
            row.add_widget(
                MDLabel(
                    text=f"{kills}K {deaths}D  DMG:{dmg}  ${equip}{opening_text}",
                    font_style="Body",
                    role="small",
                    theme_text_color="Primary",
                    adaptive_height=True,
                )
            )

            section.add_widget(row)

        container.add_widget(card)

    def _build_economy_section(self, container, rounds: list):
        card, section = self._section_card("Economy")

        from Programma_CS2_RENAN.apps.desktop_app.widgets import EconomyGraphWidget

        graph = EconomyGraphWidget(
            size_hint_y=None,
            height=dp(200),
        )
        section.add_widget(graph)
        container.add_widget(card)

        # Schedule plot after widget is added to tree
        Clock.schedule_once(lambda dt: graph.plot(rounds), 0.1)

    def _build_highlights_section(self, container, rounds: list, insights: list):
        card, section = self._section_card("Highlights & Momentum")

        # Coaching Insights
        if insights:
            for ins in insights:
                sev = ins.get("severity", "info")
                icon_name, icon_color = _SEVERITY_ICONS.get(sev, ("information", _COLOR_CT))

                insight_row = MDBoxLayout(
                    orientation="vertical",
                    adaptive_height=True,
                    padding=["8dp", "4dp", "8dp", "4dp"],
                )

                title_row = MDBoxLayout(
                    orientation="horizontal",
                    adaptive_height=True,
                    spacing="6dp",
                )
                from kivymd.uix.label import MDIcon

                title_row.add_widget(
                    MDIcon(
                        icon=icon_name,
                        theme_text_color="Custom",
                        text_color=icon_color,
                        pos_hint={"center_y": 0.5},
                    )
                )
                title_row.add_widget(
                    MDLabel(
                        text=ins.get("title", ""),
                        font_style="Title",
                        role="small",
                        theme_text_color="Primary",
                        adaptive_height=True,
                    )
                )
                insight_row.add_widget(title_row)

                insight_row.add_widget(
                    MDLabel(
                        text=ins.get("message", ""),
                        font_style="Body",
                        role="small",
                        theme_text_color="Secondary",
                        adaptive_height=True,
                    )
                )

                focus = ins.get("focus_area", "")
                if focus:
                    insight_row.add_widget(
                        MDLabel(
                            text=f"Focus: {focus}",
                            font_style="Body",
                            role="small",
                            theme_text_color="Hint",
                            adaptive_height=True,
                        )
                    )

                section.add_widget(insight_row)
        else:
            section.add_widget(
                MDLabel(
                    text="No coaching insights for this match yet.",
                    theme_text_color="Hint",
                    adaptive_height=True,
                )
            )

        # Momentum Graph
        if rounds:
            section.add_widget(
                MDLabel(
                    text="Momentum",
                    font_style="Title",
                    role="small",
                    theme_text_color="Primary",
                    adaptive_height=True,
                    padding=["0dp", "8dp", "0dp", "4dp"],
                )
            )
            from Programma_CS2_RENAN.apps.desktop_app.widgets import MomentumGraphWidget

            momentum_graph = MomentumGraphWidget(
                size_hint_y=None,
                height=dp(200),
            )
            section.add_widget(momentum_graph)
            Clock.schedule_once(lambda dt: momentum_graph.plot(rounds), 0.1)

        container.add_widget(card)

    # --- Helpers ---

    def _section_card(self, title: str) -> MDCard:
        card = MDCard(
            style="elevated",
            size_hint_y=None,
            padding="12dp",
            md_bg_color=_COLOR_CARD_BG,
        )
        # MDCard with adaptive_height needs a content layout
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
        # Bind card height to content height + padding
        content.bind(height=lambda inst, h: setattr(card, "height", h + dp(24)))
        return card, content

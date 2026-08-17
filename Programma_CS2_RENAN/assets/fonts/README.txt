Design-atlas type stack (bundled 2026-08-13). ThemeEngine auto-scans this
folder at startup (theme_engine.register_fonts) — no code change needed to
add/remove weights.

Bundled files, sources, and licenses (all SPDX: OFL-1.1):

  Inter-Regular.ttf / Inter-Medium.ttf / Inter-SemiBold.ttf / Inter-Bold.ttf
    Inter v4.1 static builds (extras/ttf) — Rasmus Andersson
    https://github.com/rsms/inter/releases/tag/v4.1

  SpaceGrotesk-Regular.ttf / SpaceGrotesk-Medium.ttf / SpaceGrotesk-Bold.ttf
    Space Grotesk 2.0.0 static builds — Florian Karsten
    https://github.com/floriankarsten/space-grotesk/releases/tag/2.0.0

  JetBrainsMono-Medium.ttf / JetBrainsMono-SemiBold.ttf / JetBrainsMono-Bold.ttf
    JetBrains Mono v2.304 — JetBrains
    https://github.com/JetBrains/JetBrainsMono/releases/tag/v2.304
    (JetBrainsMono-Regular.ttf ships separately under PHOTO_GUI/.)

Role mapping (core/typography.py + themes/base.qss.template):
  UI body        Inter (fallback Roboto, Segoe UI, system sans)
  Display/hero   Space Grotesk (section titles, display/h1 variants)
  Mono/telemetry JetBrains Mono (paths, ticks, stats dumps, footers)

License text: SIL Open Font License 1.1 — https://openfontlicense.org
Note: Qt's offscreen platform on Windows mis-reports TTF family names
(QBasicFontDatabase); real desktop platforms register them correctly.
tests/test_ui_harness.py verifies the bundle against the TTF name tables.

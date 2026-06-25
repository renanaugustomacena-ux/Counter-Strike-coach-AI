# UX Visual Audit — Macena CS2 Analyzer (Qt / PySide6 frontend)

**Date:** 2026-06-25 · **Scope:** PySide6 desktop UI (the active, shipping frontend) · **Themes audited:** CS2, CSGO, CS1.6 · **Screens:** 15/15 rendered, 12 inspected in depth.

> This is a **presentation/UX** audit — how the product looks to a user — not a code audit. The codebase was left as-is; nothing in `Programma_CS2_RENAN/` was modified to produce it.

---

## 1. Method (reproducible)

The real UI layer was booted **offscreen** (Qt `QT_QPA_PLATFORM=offscreen`) and each screen captured to PNG. No backend daemons, no SBERT download, no DB writes — only `ThemeEngine` + the 15 real screens + `MainWindow`, exactly as `app.py` composes them.

- Render harness: `scratchpad/render_screens.py` (offscreen, theme-parametrized, uses each theme's own `theme.wallpaper_path` like `app.py:307`).
- Isolated Windows venv (Python 3.10) with `PySide6==6.11.0` + light deps (no torch/demoparser2 — the `qt_app/` layer never imports them at construction).
- Data state at audit time: the DB held **pro reference data (HLTV)** but **no personal demos**, so data-bound personal screens show their genuine **first-run empty states**.

Renders live in `docs/ux-audit/renders/{CS2,CSGO,CS16}/<screen>.png`.

---

## 2. Verdict

**The foundation is professional-grade; the finish is not yet at Steam tier — but the gap is *polish*, not architecture.** Estimated ~**70–80%** of the way there.

The hard, expensive scaffolding is already built and good: MVVM (a ViewModel per screen), a real `ThemeEngine` with 3 themes, centralized `design_tokens`, a coherent component library (cards, chips, pill toggles, belief rings, status badges, charts), graceful empty states everywhere, and an i18n layer (en/it/pt). What remains is a **contrast/consistency pass** — the kind of work that separates "good project" from "ships to the world."

PySide6 is more than sufficient. The framework will never be the limiting factor; execution is.

---

## 3. Theme comparison

| Theme | Palette | Selected-state affordance | Character | Verdict |
|-------|---------|---------------------------|-----------|---------|
| **CS2** | Navy/black + **orange** accent | **Strong** (vivid orange fill) | Bold, modern, high-contrast | **Strongest** — closest to Steam-tier. Recommended default. |
| **CSGO** | Slate/gray-blue + soft blue accent | **Weak** (light gray fill, low contrast) | Cool, muted, corporate | Refined but subdued; selected toggles hard to spot at a glance. |
| **CS1.6** | Dark + **retro green** accent | Medium (green fill) | Nostalgic, thematic | On-brand for the 1.6 era; green-on-dark reads well. |

**Key finding:** CS2 is visibly the most polished. Its navy+orange chrome (see `renders/CS2/settings.png`) looks genuinely modern and would not look out of place next to professional desktop software. CSGO's main weakness is **affordance**: the selected pill/toggle uses a pale gray that barely separates from the unselected state (`renders/CSGO/settings.png`) — a real usability nit.

Each theme correctly loads its own wallpaper (`vertical_wallpaper_cs2_A` / `…cs16_A` / `16_9_wallpaper_cs16_A`). The CS2 wallpaper is a stylized "COUNTER STRIKE 2" watermark rather than a busy photo — more tasteful, but still prominent behind sparse content.

---

## 4. Design-system strengths (genuinely good)

1. **Coherent component library** — cards, pill toggles, status chips, belief rings, PRO badges all consistent across screens.
2. **Empty states everywhere** — never a raw `null`/"Not set"; always an instruction to act. E.g. tactical "Click 'Open Demo' to load a .dem file", coach "No insights yet", performance "No performance data yet".
3. **Color-coded data** — match ratings green (>1.0) / red (<1.0) for instant scannability (`renders/*/match_history.png`, 50 pro matches with K/D + ADR + PRO badge).
4. **Professional playback controls** — tactical viewer: 0.5×–4× speed, Select Map/Round, Ghost AI toggle, timeline scrubber.
5. **Helpful forms** — Steam/FACEIT config screens include "Find My Steam ID", "Get API Key" links and the localhost tip.
6. **Persistent AI Coach dock** — belief ring, recent insights, Ollama model selector, always reachable on the right.
7. **Live theme switching + font size/type + multilingual** settings.

---

## 5. Gaps to Steam tier (prioritized)

### P1 — First-run wizard contrast — ✅ RESOLVED (2026-06-25)
~~The wizard's "Welcome to Macena CS2 Analyzer" copy floats as small, low-contrast text directly over the wallpaper + diagonal color split, with **no panel behind it**. This is the **first screen a new user sees** and it's the least legible.~~

**Fixed** in `wizard_screen.py`: the 5-page step stack is now wrapped in a `Card(depth="frosted")` — a ~0.78-alpha, theme-driven glass panel (navy/gold/dark-gold per theme) with a hairline border and accent-tinted glow. The welcome copy is now fully legible while the wallpaper shows tastefully through the glass. No hardcoded values — reuses the design-system `frosted` tier + `design_tokens`, so it stays consistent across CS2/CSGO/CS16. The updated `renders/*/wizard.png` reflect the fix.

### P2 — Wallpaper bleed on sparse screens — ✅ RESOLVED (2026-06-25)
~~On low-content screens (empty performance, empty match_detail) the wallpaper shows through and competes with content.~~

**Fixed** in `main_window.py` (`_BackgroundWidget`): wallpaper opacity lowered `0.25 → 0.15`, so decorative imagery now reads as a faint texture instead of competing with content on the panel-less sparse screens. Verified on empty `performance` across all themes — the empty-state copy + CTA now clearly win. Panel'd screens were already covered by the P1 frosted card. Applied as a single, low-risk opacity lever (no stacked scrim needed after visual check).

### P3 — Empty-heavy first run
Pro reference data populates match_history / pro_comparison, but **personal** screens (performance, match_detail) stay bare until a demo is analyzed. First impression hinges on driving the user to analyze a demo fast → the onboarding funnel is the highest-leverage flow.

### P4 — CSGO selected-state affordance — ✅ RESOLVED (2026-06-25)
~~CSGO's pale selected pills are hard to distinguish at a glance.~~

**Fixed** in `settings_screen.py` (`_update_toggle_group`): the selected pill now carries a lighter `accent_hover` ring on top of the `accent_primary` fill (plus the existing bold white text), so the active state reads strongly even with CSGO's muted slate accent. Border kept at 1px in **both** states, which also fixes a pre-existing 1px content-box reflow on toggle. Verified across CS2/CSGO/CS1.6 settings — CSGO affordance improved, CS2/CS1.6 unchanged (no regression). CSGO's overall cool/muted character is intentional theme identity; the fix maximizes affordance within it rather than re-saturating the theme accent.

*Note:* the secondary "gray-on-dark text contrast" sub-point is not addressed here — tracked separately if it proves bothersome in practice.

> All P1–P4 are **presentation** fixes — no architectural change required.

---

## 6. Screen-by-screen (15)

| Screen | State at audit | Note |
|--------|----------------|------|
| home | Pro data + onboarding hero | Solid composition (nav / content / coach dock). Watermark prominent. |
| coach (dock) | Empty | Clean cards: belief ring 0%, "No insights yet", Ollama model picker. |
| match_history | **Populated** (50 pro) | Color-coded rows, filter chips, clear "no personal matches" banner. Strong. |
| match_detail | Empty (no demo loaded) | Bare until a demo loads — title + Back only. |
| performance | Empty (+ no pandas in audit env) | Clean empty-state CTA "Open Dashboard". |
| tactical_viewer | Empty | **Showpiece** — CT/T sidebars, 2D canvas, full playback bar. Strong empty-state guidance. |
| pro_comparison | Player pickers populated (Donk, s1pE) | "Pick two players to compare" before radar. |
| pro_player_detail | — | Variant of pro stat page. |
| settings | Full | **Best-looking** — tabs, theme/wallpaper/font pickers, consistent pills. |
| wizard | First-run | **P1 contrast issue** (see §5). |
| profile / user_profile | — | Profile card + avatar/role variants. |
| steam_config | Key loaded (masked) | Good form UX, helper links. |
| faceit_config | Key loaded (masked) | Matches steam_config. |
| help | Content-rich | In-app Feature Guide / Getting Started / Troubleshooting, markdown-rendered. |

---

## 7. External API connectivity (verified live, read-only)

Separate from visuals but part of "how it presents": both integrations are **code-correct but currently non-functional due to placeholder credentials.**

| API | Live result | Cause |
|-----|-------------|-------|
| Steam | `HTTP 403 Forbidden` | Configured key is 59 chars (valid = 32 hex); `STEAM_ID` is 38 chars (valid = 17 digits). |
| FACEIT | `HTTP 400 Bad Request` (on real players s1mple/donk/ZywOo) | Configured key is 8 chars (valid ≥ 30). |

No valid credential exists in any source (`.env`, `user_settings.json`, Windows keyring `MacenaCS2Analyzer`). The **code** is production-grade (Bearer/key auth, retry+backoff, rate limiting, keyring storage, zero hardcoded keys, wired to the config screens). → They will work the moment valid keys are entered; they do **not** work now. *(Probe scripts: `scratchpad/api_smoke_test.py`, `scratchpad/cred_sources.py`.)*

**Note (stale validator) — ✅ resolved (2026-06-25):** `tools/backend_validator.py` previously checked `import kivymd` + `layout.kv` existence and would throw a **false failure** on a clean install (Kivy was intentionally dropped from V1 — `requirements.txt` ships only `PySide6`). The kivymd/layout.kv probes were removed from `backend_validator`, `ui_diagnostic`, `Goliath_Hospital`, and `project_snapshot` as part of the legacy_kivy cleanup (see §8.6).

---

## 8. Recommended next steps (when work resumes)

1. ~~**Wizard panel** (P1) — add a semi-opaque card behind the welcome copy.~~ ✅ **Done** (2026-06-25) — frosted `Card` wrapper, see §5.
2. ~~**Wallpaper scrim** (P2) — darken decorative imagery in content zones.~~ ✅ **Done** (2026-06-25) — wallpaper opacity 0.25→0.15, see §5.
3. ~~**CSGO selected-state** (P4) — bump the selected-pill contrast.~~ ✅ **Done** (2026-06-25) — accent_hover ring on selected pills, see §5.
4. **Default to CS2 theme** for new installs (strongest first impression).
5. **Insert valid API keys** → re-run `api_smoke_test.py` to confirm live round-trip.
6. ~~**Decide on `legacy_kivy/`** — archive/remove to sharpen the repo's "focused product" signal.~~ ✅ **Done** (2026-06-25) — folder deleted (22 files); `test_detonation_overlays.py` repointed to the live Qt `map_widget` (now 8/8 pass vs 3 pass + 5 skip); integrity manifest regenerated; kivymd/layout.kv probes removed from `backend_validator`, `ui_diagnostic`, `Goliath_Hospital`, `project_snapshot`; stale coverage exclusion dropped. **Remaining follow-ups** (build/packaging infra, separate pass): `scripts/build_exe.bat` + `build_production.bat` + `packaging/cs2_analyzer_win.spec` still reference `kivy`/`kivymd`/old `main.py`; `core/registry.py` keeps a guarded `kivymd` import; `tests/forensics/debug_env.py` probes kivymd; CI `KIVY_NO_ARGS` env vars are now stale.
7. ~~*(Optional)* Repair/relax the `backend_validator.py` kivymd check.~~ ✅ **Done** (part of #6).

---

## 9. Reproduce / regenerate

```powershell
# Isolated audit venv (one-time)
py -3.10 -m venv <scratch>\audit_venv
<scratch>\audit_venv\Scripts\python -m pip install PySide6==6.11.0 pydantic sqlmodel sqlalchemy keyring numpy requests

# Render a theme (CS2 | CSGO | CS1.6) — offscreen, no daemons
<scratch>\audit_venv\Scripts\python scratchpad\render_screens.py CS2
```

Renders are written to `renders/<THEME>/<screen>.png`. The harness is self-contained and reads the live project from `E:\…\Counter-Strike-coach-AI-main`.

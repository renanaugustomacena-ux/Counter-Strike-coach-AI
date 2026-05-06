# `apps/qt_app/widgets/components/` -- Primitive UI generiche

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Primitive UI generiche e riutilizzabili consumate da piu schermate. Ogni componente fa una cosa sola, e theme-aware (legge da `core/design_tokens.py`) ed espone il suo stato tramite `Signal`.

## Inventario File

| File | Componente | Scopo |
|------|------------|-------|
| `__init__.py` | -- | Marcatore di pacchetto; ri-esporta i componenti pubblici. |
| `card.py` | `Card` | Container base a superficie elevata con slot opzionali title + body. Supportato da effetto frosted-glass su macOS / Windows 11 con fallback flat. |
| `empty_state.py` | `EmptyState` | Placeholder amichevole mostrato quando una lista / tabella / grafico non ha dati. Include icona, titolo, CTA opzionale. |
| `filter_chip.py` | `FilterChip` | Pillola filtro selezionabile -- click per toggle, emette `toggled(bool)`. Usato da match history e pro comparison. |
| `focus_insight.py` | `FocusInsight` | Variante card per il focus insight della home page (un singolo coaching insight prominente con icona di severita). |
| `hero_stats_strip.py` | `HeroStatsStrip` | Striscia orizzontale di metriche in formato grande (rating, K/D, ADR, KAST). |
| `icon_widget.py` | `IconWidget` | Container per icone SVG con colorazione theme-aware. Wrappa `core/svg_icon_provider.py`. |
| `last_match_hero.py` | `LastMatchHero` | Hero card della home page che riassume il match piu recente. |
| `match_mini_card.py` | `MatchMiniCard` | Card riassuntiva compatta del match (una riga in match history). |
| `match_row_card.py` | `MatchRowCard` | Card match espansa con preview delle statistiche (usata nella hero list di match history). |
| `nav_sidebar.py` | `NavSidebar` | Sidebar di navigazione sinistra con icone delle rotte + label. Sottoscrive a `app_state.routeChanged`. |
| `progress_ring.py` | `ProgressRing` | Indicatore di progresso circolare con label centrale opzionale. |
| `section_header.py` | `SectionHeader` | Riga standardizzata di titolo di sezione (titolo + sottotitolo opzionale + bottone azione opzionale). |
| `stat_badge.py` | `StatBadge` | Piccola pillola label + valore (es. `K/D 1.18`, `ADR 78`). |
| `status_chip.py` | `StatusChip` | Pillola di stato colorata (`success`, `warning`, `error`, `info`). Include sia colore che label, mai colore-only. |
| `stepper.py` | `Stepper` | Input stepper numerico (`-` / valore / `+`). |
| `toggle_switch.py` | `ToggleSwitch` | Widget switch booleano animato. |

## Design system

Tutti i componenti consumano token da `core/design_tokens.py`. Colori, spaziature, raggi e tipografia sono referenziati per nome -- mai hard-codati. Questo garantisce:

- Gli switch di tema (segnale `themeChanged`) ri-renderizzano tutti i componenti in modo consistente.
- Le modifiche alla scala tipografica si propagano senza modifiche per-widget.
- Modalita light / dark (quando aggiunta) richiede modifiche solo nel file dei token.

## Convenzioni

| Convenzione | Motivazione |
|-------------|-------------|
| Un componente per file | Facile da trovare; file piccoli; sicuro da estrarre. |
| API pubblica via `Signal`, non callback | Disaccoppia il widget dalla schermata; testabile via `QSignalSpy`. |
| `setAccessibleName()` su ogni componente interattivo | Conformita WCAG + supporto screen-reader. |
| Colore di stato sempre accoppiato con testo o icona | Mai colore-only; aiuta gli utenti daltonici (WCAG 1.4.1). |
| Stati hover / focus / active espliciti | Evita il "default Tailwind look" -- rendi lo stato visibile. |

## Aggiungere un componente

1. Metti il file qui con una singola definizione di classe.
2. Eredita dalla classe Qt piu piccola applicabile (`QWidget`, `QFrame`, `QLabel`).
3. Prendi colori / spaziature / tipografia da `core/design_tokens`.
4. Esponi lo stato tramite `Signal`.
5. Aggiungi una entry alla tabella di inventario sopra.
6. Se il componente e theme-aware, sottoscrivi a `theme_engine.themeChanged`.

## Correlati

- Design token: `apps/qt_app/core/design_tokens.py`
- Switching tema: `apps/qt_app/core/theme_engine.py`
- Widget specifici di dominio: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Parent: `apps/qt_app/widgets/README.md`

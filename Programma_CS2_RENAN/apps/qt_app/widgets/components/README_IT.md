# `apps/qt_app/widgets/components/` — Primitive UI generiche

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Primitive UI generiche e riutilizzabili consumate da piu schermate. Ogni componente fa una cosa sola, e theme-aware (legge da `core/design_tokens.py`), e i componenti interattivi espongono il loro stato tramite `Signal`.

## Inventario dei file

| File | Componente | Scopo |
|------|------------|-------|
| `__init__.py` | — | Marcatore di pacchetto; ri-esporta un sottoinsieme dei componenti pubblici. |
| `card.py` | `Card` | Container base a superficie elevata con slot opzionali title + body. Cinque varianti di profondita (`flat`, `raised`, `highlighted`, `floating`, `frosted`); `frosted` usa un riempimento semi-trasparente che approssima il backdrop blur. |
| `db_record_card.py` | `DbRecordCard` | Card raised che mostra un record database: titolo bold + caption SQL mono + griglia chiave/valore mono. Un valore puo portare un nome di token semantico (`success`, `info`, ...) per colorarlo. |
| `delta_chip.py` | `DeltaChip` | Annotazione di delta relativa al benchmark (`▲ +0.09 vs 47-match avg`). Parte nascosto; un delta zero o sconosciuto non viene mai renderizzato. |
| `drivers_list.py` | `DriversList` | Lista verticale di righe (severita, testo) — quadrato 8px colorato semanticamente + testo body. Severita ∈ {`success`, `warning`, `error`, `info`}. |
| `empty_state.py` | `EmptyState` | Placeholder amichevole mostrato quando una lista / tabella / grafico non ha dati. Icona o illustrazione, titolo, CTA opzionali piu riga ghost link; ha anche una modalita loading-skeleton. |
| `filter_chip.py` | `FilterChip` | Pillola filtro selezionabile — click per toggle, emette `toggled(bool)`; badge contatore trailing opzionale. Usato da match history e pro comparison. |
| `focus_insight.py` | `FocusInsightCard` | Card coppia nella home page di `LastMatchHeroCard` — fa emergere un'area di focus coaching con un CTA ghost (`open_clicked(str)`); ha uno stato vuoto. |
| `hero_stats_strip.py` | `HeroStatsStrip` | Striscia orizzontale di blocchi stat in formato grande (numero display + caption, colorati per sentiment). |
| `icon_widget.py` | `IconWidget` | Container per icone QPainterPath con colorazione theme-aware. Wrappa `core/icons.py` (`IconProvider`). |
| `last_match_hero.py` | `LastMatchHeroCard` | Hero card della home page che riassume il match piu recente, con un `MiniSparkline` di tendenza rating; lo stato vuoto porta un CTA analizza. |
| `map_tile.py` | `MapTile` | Tile prestazioni per mappa: nome mappa, riga rating (colore + label accessibilita), riga ADR / K/D, conteggio partite, barra di riempimento rating in basso. Interamente disegnato con QPainter. |
| `match_mini_card.py` | `MatchMiniCard` | Card preview match compatta e cliccabile (striscia "Recent Matches" nella home). Emette `clicked(demo_name)`. |
| `match_row_card.py` | `MatchRowCard` | Riga match ampia con preview statistiche (righe match history); le righe pro sostituiscono con linea giocatore + evento. Emette `clicked(demo_name)`. |
| `metric_bar_row.py` | `MetricBarRow` | Metrica con label e barra di riempimento proporzionale colorata (righe griglia HLTV 2.0 del Match Detail). |
| `mini_link_card.py` | `MiniLinkCard` | Piccola card di navigazione cliccabile — "Titolo →" bold + caption su una riga. Emette `clicked`. |
| `mono_footer.py` | `MonoFooter` | Riga di annotazione terziaria mono in fondo allo schermo che nomina la fonte dati. |
| `nav_sidebar.py` | `NavSidebar` | Sidebar di navigazione sinistra con icone delle rotte + label. Emette `nav_clicked(str)`; comprimibile 220px ↔ 60px. |
| `numbered_step.py` | `NumberedStep` | Riga step numerata (Getting Started): cerchio accento pieno con numero dello step + titolo bold + descrizione. |
| `pro_badge.py` | `ProBadge` | Badge mono a pillola ("PRO" di default) con ricolorazione opzionale per lato CT / T tramite `set_side()`. |
| `progress_ring.py` | `ProgressRing` | Indicatore di progresso circolare con testo percentuale centrato opzionale; preset dimensione `SMALL` / `DEFAULT` / `COACH` / `HERO`. |
| `section_header.py` | `SectionHeader` | Riga standardizzata di titolo di sezione (titolo + sottotitolo opzionale + widget azione opzionale). |
| `stat_badge.py` | `StatBadge` | Valore stat prominente con label sotto (pattern scope.gg); colorazione semantica + freccia trend opzionale. |
| `status_chip.py` | `StatusChip` | Pillola di stato colorata (`online`, `offline`, `warning`, `neutral`). Include sia colore che label, mai colore-only. |
| `stepper.py` | `Stepper` | Indicatore orizzontale di step (pallini + barre connettore, label opzionali) per il wizard di primo avvio. Emette `step_changed(int)`. |
| `tip_box.py` | `TipBox` | Callout con outline tratteggiato: titolo bold colorato info + body secondario. |
| `toggle_switch.py` | `ToggleSwitch` | Widget switch booleano animato stile iOS. |

## Design system

Tutti i componenti consumano token da `core/design_tokens.py` (generati da `design/tokens/design-tokens.json`). Colori, spaziature, raggi e tipografia sono referenziati per nome — mai hard-codati. Il theming funziona cosi:

- Tre set di token (`CS2`, `CSGO`, `CS1.6`) condividono un unico contratto strutturale; `theme_engine.apply_theme()` scambia il set attivo.
- L'unica fonte di stylesheet e `themes/base.qss.template`, renderizzata per tema da `core/qss_generator.py` — non ci sono file QSS per-tema.
- La `QPalette` e derivata dagli stessi token, cosi i widget che bypassano il QSS restano coerenti.
- I cambi di tema (segnale `theme_changed`) ri-stilizzano tutti i componenti in modo consistente.

## Convenzioni

| Convenzione | Motivazione |
|-------------|-------------|
| Un componente per file | Facile da trovare; file piccoli; sicuro da estrarre. |
| API pubblica via `Signal`, non callback | Disaccoppia il widget dalla schermata; testabile via `QSignalSpy`. |
| Colore di stato sempre accoppiato con testo o icona | Mai colore-only; aiuta gli utenti daltonici (WCAG 1.4.1). |
| Stati hover / focus / active espliciti | Evita il "default Tailwind look" — rendi lo stato visibile. |

## Aggiungere un componente

1. Metti il file qui con una singola definizione di classe.
2. Eredita dalla classe Qt piu piccola applicabile (`QWidget`, `QFrame`, `QLabel`).
3. Prendi colori / spaziature / tipografia da `core/design_tokens`.
4. Esponi lo stato tramite `Signal`.
5. Aggiungi una entry alla tabella di inventario sopra.
6. Se il componente e theme-aware, risolvi i colori dal set di token attivo (`get_tokens()`) o connettiti a `theme_engine.theme_changed`.

## Correlati

- Design token: `apps/qt_app/core/design_tokens.py`
- Switching tema: `apps/qt_app/core/theme_engine.py`
- Template QSS: `apps/qt_app/themes/base.qss.template` (renderizzato da `core/qss_generator.py`)
- Widget specifici di dominio: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Parent: `apps/qt_app/widgets/README.md`

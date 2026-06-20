# `apps/qt_app/widgets/` -- Libreria custom di widget Qt

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Sottoclassi `QWidget` riutilizzabili che si compongono in schermate. Tutto cio che e usato da piu di una schermata, o tutto cio che e abbastanza grande da meritare un proprio file, vive qui. Le visualizzazioni puramente single-screen restano dentro il loro modulo schermata.

## Layout

```
widgets/
├── __init__.py
├── skeleton.py             # Skeleton di caricamento (placeholder shimmer)
├── toast.py                # Toast di notifica transienti
├── components/             # Primitive UI generiche (card, badge, chip, ...)
├── charts/                 # Grafici basati su Matplotlib
├── coaching/               # Visualizzazioni specifiche del Coach
└── tactical/               # Widget specifici del tactical viewer
```

| Sotto-pacchetto | Scopo | README |
|-----------------|-------|--------|
| `components/` | Primitive UI generiche riutilizzate tra le schermate | [components/README.md](components/README.md) |
| `charts/` | Grafici basati su Matplotlib per la dashboard | [charts/README.md](charts/README.md) |
| `coaching/` | Visualizzazioni specifiche della schermata Coach (gauge, sparkline di momentum) | [coaching/README.md](coaching/README.md) |
| `tactical/` | Widget per il tactical viewer (mappa, sidebar, timeline) | [tactical/README.md](tactical/README.md) |

## File di primo livello

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `skeleton.py` | `SkeletonLoader` -- placeholder shimmer mostrato mentre i dati del ViewModel caricano. |
| `toast.py` | Toast di notifica transiente con auto-dismiss + bottone azione. Sottoscritto a `app_state.bus` per i toast globali. |

## Convenzioni

### Composizione sopra l'ereditarieta

La maggior parte dei widget sono container `QWidget` che compongono pezzi piu piccoli. Evita alberi di ereditarieta profondi -- collidono col modello di segnali Qt e complicano il theming.

### Styling theme-aware

Ogni widget legge colori / spaziature / tipografia da `core/design_tokens.py` invece di hard-codarli. Il QSS generator in `core/qss_generator.py` materializza i token in uno stylesheet applicato a tutta l'app.

### API basata su segnali

I widget espongono i cambi di stato tramite `Signal` (es. `clicked`, `selectionChanged`). Evita callback sincroni -- rompono la separazione MVVM.

### Accessibilita

- Imposta `setAccessibleName()` e `setAccessibleDescription()` per qualsiasi widget che renderizzi contenuto semantico (grafici, indicatori di stato).
- Stato codificato a colore (rating, severita) deve essere accoppiato con testo o un'icona -- mai colore-only (WCAG 1.4.1).

## Aggiungere un nuovo widget

1. Decidi se appartiene a `widgets/` (generico), `widgets/components/` (primitiva UI) o a un sotto-pacchetto di dominio.
2. Eredita dalla classe Qt piu piccola applicabile (`QWidget`, `QFrame`, `QLabel`).
3. Leggi i token tramite `core/design_tokens` -- mai hard-codare colori.
4. Esponi lo stato via `Signal`, non getter che mutano.
5. Aggiungi il widget alla tabella di inventario del README del suo sotto-pacchetto.
6. Se il widget e theme-aware, sottoscrivi a `theme_engine.themeChanged`.

## Correlati

- Core applicativo: `apps/qt_app/core/README.md`
- Schermate (consumer): `apps/qt_app/screens/README.md`
- App parent: `apps/qt_app/README.md`
- Widget Kivy legacy (solo come riferimento per migrazione): `apps/legacy_kivy/widgets.py`

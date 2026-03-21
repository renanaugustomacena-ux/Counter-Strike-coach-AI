> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Risorse Statiche

> **Autorità:** Regola 3 (Frontend & UX)

Questa directory contiene tutte le risorse statiche consumate dall'applicazione a
runtime. I file qui presenti vengono inclusi nella distribuzione PyInstaller e
risolti tramite `core/config.py:get_resource_path()`, che astrae la differenza tra
l'albero sorgente di sviluppo e gli eseguibili congelati. Nulla in questa directory
viene generato a runtime; ogni file è sottoposto a version control e trattato come
immutabile dopo il rilascio.

## Struttura della Directory

```
assets/
├── i18n/                     # Internazionalizzazione (traduzioni)
│   ├── en.json              # Inglese (137 chiavi) — primario/fallback
│   ├── pt.json              # Portoghese Brasiliano
│   └── it.json              # Italiano
├── maps/                     # Immagini radar mappe CS2
│   ├── de_ancient_radar.dds
│   ├── de_cache_radar.dds
│   ├── de_dust2_radar.dds
│   ├── de_inferno_radar.dds
│   ├── de_mirage_radar.dds
│   ├── de_nuke_lower_radar.dds
│   ├── de_nuke_radar.dds
│   ├── de_overpass_radar.dds
│   ├── de_train_radar.dds
│   ├── de_vertigo_lower_radar.dds
│   └── de_vertigo_radar.dds
├── README.md                 # Questo file (Inglese)
├── README_IT.md              # Traduzione Italiana
└── README_PT.md              # Traduzione Portoghese
```

## Inventario dei File

| File / Directory | Tipo | Quantità | Scopo |
|------------------|------|----------|-------|
| `i18n/en.json` | JSON | 137 chiavi | Stringhe UI in Inglese (lingua primaria e fallback) |
| `i18n/pt.json` | JSON | 137 chiavi | Stringhe UI in Portoghese Brasiliano |
| `i18n/it.json` | JSON | 137 chiavi | Stringhe UI in Italiano |
| `maps/de_*_radar.dds` | Immagine DDS | 11 file | Immagini radar dall'alto per le mappe competitive CS2 |

## `i18n/` — File di Localizzazione

File JSON contenenti ogni stringa visibile all'utente nell'applicazione. Lo schema
delle chiavi è identico in tutti i file lingua: quando una chiave esiste in
`en.json`, deve esistere anche in `pt.json` e `it.json`. Se una traduzione manca,
il fallback inglese viene utilizzato automaticamente da `QtLocalizationManager`.

### Categorie di Chiavi (137 chiavi totali)

| Categoria | Chiavi di Esempio | Scopo |
|-----------|-------------------|-------|
| Navigazione | `dashboard`, `coach`, `match_history`, `performance` | Etichette barra laterale |
| Coaching | `coaching_insights`, `severity_high`, `focus_positioning` | Testo schermata Coach |
| Impostazioni | `theme`, `language`, `demo_path`, `ingestion_mode` | Schermata Impostazioni |
| Profilo | `player_name`, `bio`, `role` | Campi profilo utente |
| Tattica | `tactical_viewer`, `playback_speed`, `timeline` | Schermata Tactical Viewer |
| Dialoghi | `confirm_delete`, `save_success`, `error_occurred` | Messaggi dei dialoghi |
| Steam/FaceIT | `steam_id`, `faceit_key`, `sync_profile` | Schermate di integrazione |
| Aiuto | `help_center`, `getting_started`, `troubleshooting` | Schermata Centro Aiuto |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | Wizard di configurazione iniziale |

### Catena di Risoluzione della Localizzazione

Il `QtLocalizationManager` in `apps/qt_app/core/i18n_bridge.py` risolve una chiave
attraverso quattro livelli di priorità:

1. **File JSON per la lingua corrente** (`_JSON_TRANSLATIONS[lang][key]`)
2. **Dizionario hardcoded per la lingua corrente** (`_FULL_TRANSLATIONS[lang][key]`)
3. **Fallback inglese** (`_FULL_TRANSLATIONS["en"][key]`)
4. **Chiave grezza** (la stringa della chiave stessa, come ultima risorsa)

I file JSON vengono caricati una sola volta al momento dell'import. La sostituzione
dinamica dei segnaposto (es. `{home_dir}`) viene applicata durante il caricamento.

### Aggiungere una Nuova Lingua

1. Copiare `en.json` in `{language_code}.json` (es. `fr.json`)
2. Tradurre tutti i 137 valori (mantenere le chiavi invariate)
3. Registrare il nuovo codice lingua in `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Aggiungere il pulsante di cambio lingua in `apps/qt_app/screens/settings_screen.py`
5. Aggiornare `core/localization.py` se i dizionari fallback Kivy necessitano della nuova lingua

### Aggiungere una Nuova Chiave

1. Aggiungere la coppia chiave-valore a **tutti e tre** i file JSON (`en.json`, `pt.json`, `it.json`)
2. Referenziare nel codice tramite `i18n.get_text("your_new_key")`
3. Se la chiave è critica per la navigazione, aggiungerla anche a `_HARDCODED_EN` in `i18n_bridge.py`

## `maps/` — Immagini Radar

Immagini radar in formato DDS (DirectDraw Surface) per le mappe competitive di CS2.
Utilizzate dal Tactical Viewer per il rendering 2D dall'alto delle posizioni dei
giocatori, traiettorie delle granate e replay dei round.

### Copertura

11 immagini radar che coprono tutte le mappe del pool competitivo attuale:

| Mappa | File | Multi-livello |
|-------|------|---------------|
| Ancient | `de_ancient_radar.dds` | No |
| Cache | `de_cache_radar.dds` | No |
| Dust2 | `de_dust2_radar.dds` | No |
| Inferno | `de_inferno_radar.dds` | No |
| Mirage | `de_mirage_radar.dds` | No |
| Nuke | `de_nuke_radar.dds`, `de_nuke_lower_radar.dds` | Sì |
| Overpass | `de_overpass_radar.dds` | No |
| Train | `de_train_radar.dds` | No |
| Vertigo | `de_vertigo_radar.dds`, `de_vertigo_lower_radar.dds` | Sì |

### Sistema di Coordinate delle Mappe

Le immagini radar sono accoppiate con file di configurazione spaziale in altre parti del progetto:

- **`data/map_config.json`** — `pos_x`, `pos_y` (origine del sistema di coordinate Valve),
  `scale` (pixel per unità, tipicamente da 4.0 a 7.0), e opzionale `z_cutoff` per mappe multi-livello
- **`data/map_tensors.json`** — Coordinate di bombsite e spawn come tensori per il motore di analisi spaziale
- **`backend/analysis/engagement_range.py`** — Posizioni con nome (es. "A Site", "Mid Doors")
  per output di coaching leggibili dall'uomo

### Aggiungere una Nuova Mappa

1. Posizionare `de_{mapname}_radar.dds` in `assets/maps/`
2. Aggiungere la configurazione spaziale a `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Aggiungere le definizioni tensore a `data/map_tensors.json` (coordinate bombsite/spawn)
4. Aggiungere le posizioni con nome a `backend/analysis/engagement_range.py`
5. Per mappe multi-livello, aggiungere una variante `_lower_radar.dds` e impostare `z_cutoff` nella configurazione

## Bundling (PyInstaller)

Tutti i file in questa directory vengono inclusi nell'eseguibile congelato tramite
`packaging/cs2_analyzer_win.spec`:

```python
datas += [('Programma_CS2_RENAN/assets/i18n', 'assets/i18n')]
datas += [('Programma_CS2_RENAN/assets/maps', 'assets/maps')]
```

A runtime, i percorsi vengono risolti tramite `get_resource_path()`, che controlla
`sys._MEIPASS` (congelato) prima di ricorrere al percorso dell'albero sorgente.

## Punti di Integrazione

| Consumatore | Risorsa | Pattern di Accesso |
|-------------|---------|-------------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` all'import |
| `apps/qt_app/screens/tactical_screen.py` | `maps/*.dds` | `get_resource_path("assets/maps")` su richiesta |
| `core/map_manager.py` | `maps/*.dds` | Trasformazione coordinate con `map_config.json` |
| `reporting/visualizer.py` | `maps/*.dds` | Rendering overlay per heatmap e PDF |

## Note di Sviluppo

- I file DDS non devono superare i 4 MB ciascuno (risoluzione massima 2048x2048)
- I file JSON devono essere UTF-8 valido senza BOM (byte-order mark)
- Il dizionario fallback `_HARDCODED_EN` in `i18n_bridge.py` contiene solo le chiavi
  critiche per la navigazione; mantenerlo sincronizzato quando si rinominano o rimuovono chiavi dai file JSON
- I valori delle coordinate delle mappe provengono dai file di gioco CS2 (`resource/overviews/*.txt`)
- L'hook pre-commit `check-json` valida la sintassi JSON ad ogni commit
- Tutte le 137 chiavi devono essere presenti in ogni file lingua; le chiavi mancanti degradano
  con grazia all'inglese ma indicano una traduzione incompleta

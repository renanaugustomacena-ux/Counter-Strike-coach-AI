> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Risorse Statiche

> **Autorità:** Regola 3 (Frontend & UX)

Questa directory contiene tutte le risorse statiche consumate dall'applicazione a
runtime. I percorsi vengono risolti tramite `core/config.py:get_resource_path()`,
che astrae la differenza tra l'albero sorgente di sviluppo e gli eseguibili congelati
(le traduzioni `i18n/`, lo stack tipografico `fonts/` e gli overlay `map_zones/`
vengono inclusi nella distribuzione PyInstaller). Nulla in questa directory
viene generato a runtime; ogni file è sottoposto a version control e trattato come
immutabile dopo il rilascio.

## Struttura della Directory

```
assets/
├── fonts/                    # Font di display (scansionati automaticamente dal motore temi)
│   ├── Inter-*.ttf          # Inter v4.1 build statiche (4 pesi)
│   ├── JetBrainsMono-*.ttf  # JetBrains Mono v2.304 (4 pesi)
│   ├── SpaceGrotesk-*.ttf   # Space Grotesk 2.0.0 (3 pesi)
│   └── README.txt           # Fonti, licenze (OFL-1.1), mappatura ruoli
├── i18n/                     # Internazionalizzazione (traduzioni)
│   ├── en.json              # Inglese (584 chiavi) — primario/fallback
│   ├── pt.json              # Portoghese Brasiliano
│   └── it.json              # Italiano
├── map_zones/                # Overlay zone con nome per il visualizzatore tattico
│   └── de_mirage.json       # Rettangoli zona (normalizzati 0-1) per Mirage
├── maps/                     # Immagini radar mappe CS2
│   ├── de_ancient_radar.dds
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
| `fonts/*.ttf` | Font TTF | 11 file | Stack tipografico design-atlas (Inter, Space Grotesk, JetBrains Mono build statiche, tutte OFL-1.1); il motore temi scansiona automaticamente qualsiasi `.ttf`/`.otf` qui all'avvio |
| `fonts/README.txt` | Testo | 1 file | Fonti dei font, versioni, licenze e mappatura ruoli (corpo UI: Inter; display: Space Grotesk; mono: JetBrains Mono) |
| `i18n/en.json` | JSON | 584 chiavi | Stringhe UI in Inglese (lingua primaria e fallback) |
| `i18n/pt.json` | JSON | 584 chiavi | Stringhe UI in Portoghese Brasiliano |
| `i18n/it.json` | JSON | 584 chiavi | Stringhe UI in Italiano |
| `map_zones/de_mirage.json` | JSON | 1 file | Rettangoli zona con nome per l'overlay del visualizzatore tattico Qt (solo Mirage per ora) |
| `maps/de_*_radar.dds` | Immagine DDS | 10 file | Immagini radar dall'alto (1024x1024) per le mappe competitive CS2 |

## `i18n/` — File di Localizzazione

File JSON contenenti ogni stringa visibile all'utente nell'applicazione. Lo schema
delle chiavi è identico in tutti i file lingua: quando una chiave esiste in
`en.json`, deve esistere anche in `pt.json` e `it.json`. Se una traduzione manca,
il fallback inglese viene utilizzato automaticamente da `QtLocalizationManager`.

### Categorie di Chiavi (584 chiavi totali)

| Categoria | Chiavi di Esempio | Scopo |
|-----------|-------------------|-------|
| Navigazione | `dashboard`, `coaching`, `settings`, `profile` | Etichette barra laterale |
| Coaching | `coach_status`, `recent_insights`, `ask_your_coach`, `coach_thinking` | Testo schermata Coach |
| Impostazioni | `visual_theme`, `language`, `font_size`, `ingestion_mode` | Schermata Impostazioni |
| Profilo | `ingame_name`, `bio`, `pro_profile` | Campi profilo utente |
| Tattica | `tactical_analyzer`, `tactical.tick`, `tactical.bomb_planted` | Schermata e HUD del visualizzatore tattico (chiavi con punto `tactical.*`) |
| Dettaglio Partita | `md_title`, `md_tab_overview`, `md_tab_economy` | Schermata dettaglio partita (prefisso `md_*`) |
| Dialoghi | `dialog_edit_profile`, `dialog_save`, `dialog_close` | Messaggi dei dialoghi |
| Steam/FaceIT | `steam_integration`, `steam_key_hint`, `faceit_hint` | Schermate di integrazione |
| Aiuto | `help_center`, `search_placeholder`, `select_topic` | Schermata Centro Aiuto |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | Wizard di configurazione iniziale |
| Grafici | `chart_caption_you`, `chart_economy_title`, `chart_round_axis` | Didascalie e etichette assi dei grafici |

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
2. Tradurre tutti i 584 valori (mantenere le chiavi invariate)
3. Registrare il nuovo codice lingua in `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Aggiungere il pulsante di cambio lingua in `apps/qt_app/screens/settings_screen.py`
5. Aggiornare `core/localization.py` se i dizionari fallback hardcoded legacy (`TRANSLATIONS`) necessitano della nuova lingua

### Aggiungere una Nuova Chiave

1. Aggiungere la coppia chiave-valore a **tutti e tre** i file JSON (`en.json`, `pt.json`, `it.json`)
2. Referenziare nel codice tramite `i18n.get_text("your_new_key")`
3. Se la chiave è critica per la navigazione, aggiungerla anche a `_HARDCODED_EN` in `i18n_bridge.py`

## `maps/` — Immagini Radar

Immagini radar in formato DDS (DirectDraw Surface) (1024x1024) per le mappe competitive
di CS2. Sono referenziate dal campo `image_file` in `data/map_tensors.json` e consumate
dal visualizzatore di report per il rendering overlay di heatmap.
(Il visualizzatore tattico Qt renderizza dalle panoramiche PNG in `PHOTO_GUI/maps/`.)

### Copertura

10 immagini radar che coprono le mappe del pool competitivo:

| Mappa | File | Multi-livello |
|-------|------|---------------|
| Ancient | `de_ancient_radar.dds` | No |
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
  `scale` (pixel per unità, tipicamente da 4.0 a 7.0), e `z_cutoff`/`levels` per mappe
  multi-livello; utilizzato da `core/spatial_data.py` per le trasformazioni di coordinate
- **`data/map_tensors.json`** — Coordinate di bombsite e spawn come tensori per il motore
  di analisi spaziale, più il riferimento radar `image_file` per mappa
- **`core/map_callouts.py`** — Registro `NamedPosition` (161 posizioni su 9 mappe,
  es. "A Site", "Mid Doors") per output di coaching leggibili dall'uomo; ri-esportato
  tramite `backend/analysis/engagement_range.py`

### Aggiungere una Nuova Mappa

1. Posizionare `de_{mapname}_radar.dds` in `assets/maps/`
2. Aggiungere la configurazione spaziale a `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Aggiungere le definizioni tensore a `data/map_tensors.json` (coordinate bombsite/spawn, `image_file`)
4. Aggiungere le posizioni con nome a `core/map_callouts.py`
5. Per mappe multi-livello, aggiungere una variante `_lower_radar.dds` e impostare `z_cutoff` nella configurazione
6. Opzionalmente aggiungere un file overlay zone con nome a `assets/map_zones/` (vedi sotto)

## `map_zones/` — Overlay Zone del Visualizzatore Tattico

File JSON con rettangoli zona con nome per il visualizzatore tattico Qt. Ogni file contiene
una lista `zones` di rettangoli normalizzati 0-1 nel pannello mappa (`name`, `x`, `y`, `w`,
`h`, `label`, flag opzionale `major` per le etichette prominenti A/B/MID).

- Attualmente un file: `de_mirage.json` (9 zone)
- Caricato da `apps/qt_app/widgets/tactical/map_widget.py` (`load_map_zones()`),
  che accetta sia nomi corti (`mirage`) che lunghi (`de_mirage`) e degrada a
  nessun overlay (`[]`) per mappe senza un file zona
- Risolto tramite `get_resource_path()` e incluso nella build congelata

## Bundling (PyInstaller)

Le traduzioni, i font e gli overlay zona vengono inclusi nell'eseguibile congelato
tramite `packaging/cs2_analyzer_win.spec` (nella root del repository):

```python
(str(APP_DIR / "assets" / "i18n"), "Programma_CS2_RENAN/assets/i18n"),
(str(APP_DIR / "assets" / "fonts"), "Programma_CS2_RENAN/assets/fonts"),
(str(APP_DIR / "assets" / "map_zones"), "Programma_CS2_RENAN/assets/map_zones"),
```

Le immagini radar DDS in `assets/maps/` non sono elencate nei `datas` dello spec
(il visualizzatore tattico congelato usa le panoramiche PNG in `PHOTO_GUI/maps/`,
che vengono incluse separatamente). A runtime, i percorsi vengono risolti tramite
`get_resource_path()`, che controlla `sys._MEIPASS` (congelato) prima di ricorrere
al percorso dell'albero sorgente.

## Punti di Integrazione

| Consumatore | Risorsa | Pattern di Accesso |
|-------------|---------|-------------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` all'import |
| `apps/qt_app/core/theme_engine.py` | `fonts/*.ttf` / `*.otf` | Scansionati e registrati automaticamente a `register_fonts()` (dopo i font legacy `PHOTO_GUI/`) |
| `apps/qt_app/widgets/tactical/map_widget.py` | `map_zones/*.json` | `load_map_zones()` via `get_resource_path()` per mappa |
| `reporting/visualizer.py` | `maps/*` | Carica l'immagine mappa referenziata da `data/map_tensors.json` (`image_file`) per rendering heatmap e overlay |

## Note di Sviluppo

- I file DDS non devono superare i 4 MB ciascuno (risoluzione massima 2048x2048)
- I file JSON devono essere UTF-8 valido senza BOM (byte-order mark)
- Il dizionario fallback `_HARDCODED_EN` in `i18n_bridge.py` contiene solo le chiavi
  critiche per la navigazione; mantenerlo sincronizzato quando si rinominano o rimuovono chiavi dai file JSON
- I valori delle coordinate delle mappe provengono dai file di gioco CS2 (`resource/overviews/*.txt`)
- L'hook pre-commit `check-json` valida la sintassi JSON ad ogni commit
- Tutte le 584 chiavi devono essere presenti in ogni file lingua; le chiavi mancanti degradano
  con grazia all'inglese ma indicano una traduzione incompleta
- I font sono build statiche sotto la SIL Open Font License 1.1; fonti e versioni sono
  documentate in `fonts/README.txt` (`JetBrainsMono-Regular.ttf` è presente anche sotto
  `PHOTO_GUI/` come font legacy registrato dal motore temi)

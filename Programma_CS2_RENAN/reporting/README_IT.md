# Visualizzazione & Generazione Report

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorità:** `Programma_CS2_RENAN/reporting/`
**Proprietario:** livello presentazione Macena CS2 Analyzer

## Introduzione

Questo pacchetto trasforma i dati grezzi di analisi match in artefatti visivi leggibili
e report strutturati. Si colloca nel livello più esterno dell'architettura, consumando
output dalle pipeline di processing, analisi e coaching per produrre heatmap, overlay
differenziali, annotazioni momenti critici e report Markdown multi-sezione. Tutto il
rendering è supportato da Matplotlib con gestione deterministica del ciclo di vita delle
figure per prevenire memory leak.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `visualizer.py` | Motore visualizzazione mappe basato su Matplotlib | `MatchVisualizer`, `generate_highlight_report()` |
| `report_generator.py` | Costruttore report match multi-sezione | `MatchReportGenerator` |
| `__init__.py` | Marcatore pacchetto | -- |

## Architettura & Concetti

### Motore Visualizzazione Mappe (`visualizer.py`)

`MatchVisualizer` è la classe di rendering centrale. Produce tre categorie di output
visivo:

1. **Heatmap Posizioni** (`generate_heatmap`) -- istogramma 2D delle posizioni
   giocatore sovrapposto allo sfondo mappa. Usa una griglia a 64 bin con colourmap
   `"magma"` e soglia minima conteggio (`cmin=1`) per sopprimere bin vuoti.

2. **Overlay Differenziali** (`render_differential_overlay`) -- heatmap divergente che
   confronta il posizionamento utente contro baseline professionali. L'algoritmo:
   - Converte ogni set di posizioni in una griglia densità a `resolution` configurabile
     (default 128).
   - Applica sfocatura Gaussiana (`sigma=5.0`) tramite `scipy.ndimage.gaussian_filter`.
   - Normalizza ogni densità indipendentemente, poi calcola la differenza.
   - Maschera regioni con attività trascurabile (soglia `< 0.02`).
   - Renderizza con colourmap divergente `RdBu_r` e `TwoSlopeNorm` centrato a zero.
   - Le regioni blu indicano posizionamento pesante utente; le regioni rosse indicano
     posizionamento pesante pro.

3. **Mappe Momenti Critici** (`render_critical_moments`) -- scatter plot annotato degli
   eventi chiave identificati da `ChronovisorScanner`. Ogni momento è renderizzato come
   marker colorato per severità, sagomato per tipo e dimensionato per scala:

   | Severità | Colore | Tipo | Marker | Scala | Pixel |
   |----------|--------|------|--------|-------|-------|
   | critical | rosso | play | `^` (triangolo su) | macro | 350 |
   | critical | rosso | mistake | `v` (triangolo giù) | standard | 200 |
   | significant | arancione | play/mistake | `^` / `v` | standard | 200 |
   | notable | oro | play/mistake | `o` (cerchio) | micro | 100 |

4. **Grafici Errori Round** (`plot_round_errors`) -- scatter plot che segna posizioni
   morte (rosso `x`) e decisioni errate segnalate dal coach (arancione `P`) per un
   singolo round.

Tutti i metodi di rendering seguono il pattern **try/finally** (`DA-VZ-01`),
garantendo `plt.close(fig)` anche quando `savefig` solleva eccezione. Questo previene
leak delle figure Matplotlib in condizioni di errore.

#### Sfondo Mappa & Limiti

Le immagini sfondo vengono caricate da `assets/maps/` usando percorsi definiti in
`data/map_tensors.json`. Una guardia path traversal (`VZ-02`) valida che il percorso
immagine risolto rimanga entro `assets_dir` prima del caricamento. Sei mappe hanno
limiti hardcoded in `_get_bounds()`: `de_mirage`, `de_inferno`, `de_dust2`, `de_nuke`,
`de_overpass` e `de_ancient`. Mappe sconosciute ricadono su bounding box
`(-4000, 4000, -4000, 4000)`.

### Generatore Report (`report_generator.py`)

`MatchReportGenerator` orchestra la pipeline report completa:

1. **Parse** -- carica il file demo tramite `DemoLoader`.
2. **Estrazione** -- itera i frame parsati per raccogliere posizioni giocatore ed
   eventi morte.
3. **Visualizzazione** -- chiama `MatchVisualizer.generate_heatmap()` per produrre
   la heatmap posizionamento.
4. **Scrittura** -- produce un file report Markdown con timestamp contenente:
   - Nome mappa e data generazione.
   - Immagine heatmap incorporata (percorso relativo, `RG-02`).
   - Sezione analisi errori fondamentali.

La directory output è ancorata a `USER_DATA_ROOT/reports` con guardia escape percorso
(`RG-01`) che assicura che il report rimanga sotto la root dati utente.

#### Annotazioni Sicurezza

| Codice | Guardia |
|--------|---------|
| `DA-VZ-01` | Chiusura figure `try/finally` per prevenire memory leak |
| `VZ-02` | Prevenzione path traversal per immagini sfondo mappa |
| `DA-RG-01` | Ancoraggio percorso assoluto per directory output report |
| `RG-01` | Validazione escape percorso che assicura output sotto `USER_DATA_ROOT` |
| `RG-02` | Percorso relativo in Markdown per evitare esposizione struttura filesystem |

### Integrazione Highlight Report (`generate_highlight_report`)

La funzione a livello modulo `generate_highlight_report(match_id, map_name)` collega
il modello RAP Coach con il motore di visualizzazione. Essa:

1. Verifica se il modello RAP è abilitato tramite `get_setting("USE_RAP_MODEL")`.
2. Istanzia `ChronovisorScanner` e scansiona il match per momenti critici.
3. Converte ogni `CriticalMoment` in un dict annotazione highlight.
4. Renderizza l'immagine mappa annotata tramite `render_critical_moments()`.

Questa funzione è guardata da un ampio `try/except` con logging errori, assicurando
che fallimenti di visualizzazione non causino mai crash della pipeline chiamante.

## Integrazione

| Consumatore | Utilizzo |
|-------------|----------|
| `apps/qt_app/screens/` | Rendering grafici inline in `PerformanceScreen`, `MatchDetailScreen` |
| `backend/services/analysis_orchestrator.py` | Chiama `generate_highlight_report()` durante post-analisi |
| `backend/nn/rap_coach/chronovisor_scanner.py` | Fornisce oggetti `CriticalMoment` per il rendering |
| `ingestion/demo_loader.py` | Fornisce frame parsati consumati da `MatchReportGenerator` |
| `core/config.py` | `USER_DATA_ROOT` per ancoraggio percorso output report |

## Formati Output

| Formato | DPI | Caso d'Uso |
|---------|-----|------------|
| PNG | 150 | Display UI, anteprime inline |
| PNG (alta risoluzione) | 300 | Embedding PDF, archiviazione |
| Markdown | -- | Report testo strutturato con riferimenti immagini incorporate |

## Note Sviluppo

- **Ciclo vita figure**: ogni figura Matplotlib deve essere creata e chiusa nello
  stesso scope del metodo. Non memorizzare mai riferimenti figura come attributi
  di istanza.
- **Output deterministico**: i nomi file includono nome mappa e timestamp per prevenire
  collisioni. Bin heatmap e colourmap sono fissi per riproducibilità.
- **Isolamento dipendenze**: `scipy.ndimage.gaussian_filter` è l'unico import SciPy;
  `numpy` è usato per computazione griglia. Entrambi sono dipendenze obbligatorie.
- **Testing**: i test del visualizer usano `matplotlib.use("Agg")` per evitare
  requisiti backend GUI. I test del report generator mockano `DemoLoader` e verificano
  l'output file.

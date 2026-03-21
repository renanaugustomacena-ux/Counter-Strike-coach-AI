> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge Base — Sistema di Aiuto In-App

> **Autorita:** Regola 3 (Frontend & UX)

## Introduzione

Il modulo `knowledge_base` fornisce un sistema di documentazione in-app leggero e
di sola lettura che serve contenuti di aiuto rivolti all'utente all'interno di
Macena CS2 Analyzer. Legge file Markdown dalla directory risorse `data/docs/`, li
indicizza per nome file ed espone una semplice API di ricerca testuale che i livelli
UI consumano.

Questo modulo e **completamente separato** dal sistema di conoscenza RAG/COPER
situato in `backend/knowledge/`. I due moduli non condividono codice, dati, ne stato
a runtime. I loro nomi sono simili ma le loro responsabilita sono disgiunte:

| Modulo | Scopo | Tecnologia |
|--------|-------|------------|
| `backend/knowledge/` | Conoscenza RAG per coaching + Experience Bank + ricerca vettoriale | SBERT embeddings, FAISS, SQLite |
| `backend/knowledge_base/` | **Documentazione di aiuto in-app** (questo modulo) | File Markdown, ricerca testuale per sottostringa |

## Inventario File

| File | Righe | Scopo | Esportazioni Principali |
|------|-------|-------|-------------------------|
| `__init__.py` | 1 | Marcatore di pacchetto | — |
| `help_system.py` | ~83 | Ricerca, indicizzazione e consultazione documentazione Markdown | `HelpSystem`, `get_help_system()` |

## Architettura e Concetti

### Classe HelpSystem

`HelpSystem` e l'unica classe in questo modulo. Svolge tre responsabilita:

1. **Costruzione dell'indice** — All'istanziazione (o quando si chiama `refresh_index()`),
   scansiona la directory dei documenti, legge ogni file `.md`, estrae il primo heading
   `# ` come titolo dell'argomento e memorizza il contenuto completo in un dizionario
   in memoria indicizzato dallo stem del nome file (es. `getting_started.md` diventa
   l'ID argomento `getting_started`).

2. **Recupero argomenti** — `get_topic(topic_id)` restituisce un singolo dizionario
   argomento con chiavi `title`, `content` e `path`. `get_all_topics()` restituisce
   una lista di tutti gli argomenti indicizzati per popolare il menu laterale.

3. **Ricerca testuale** — `search_topics(query)` esegue una corrispondenza per
   sottostringa case-insensitive su titoli e contenuti. Le corrispondenze nei titoli
   ricevono un punteggio di 10; le corrispondenze nei contenuti ricevono un punteggio
   di 1. I risultati vengono restituiti ordinati per punteggio di rilevanza decrescente.

### Pattern Singleton (C-54)

Il modulo segue il pattern **lazy singleton** identificato come C-54 nel codebase:

```python
# Nessun I/O su file al momento dell'import
_help_system = None

def get_help_system() -> HelpSystem:
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system
```

Questo evita letture da disco durante l'import del modulo, fondamentale perche il
modulo del sistema di aiuto potrebbe essere importato da schermate che non vengono
mai effettivamente visitate durante una sessione.

### Fonte Dati: `data/docs/`

I file Markdown risiedono nella directory risorse `Programma_CS2_RENAN/data/docs/`,
risolta a runtime tramite `get_resource_path("data/docs")` da `core/config.py`. Questa
risoluzione e compatibile con PyInstaller: durante l'esecuzione da un bundle congelato,
legge dalla cartella di estrazione temporanea `_MEIPASS` invece dell'albero sorgente.

Argomenti di documentazione attuali:

| File | Argomento | Riepilogo Contenuto |
|------|-----------|---------------------|
| `getting_started.md` | Getting Started | Wizard di configurazione, percorsi demo, collegamento Steam/FACEIT, regola 10/10, modalita di ingestione |
| `features.md` | Feature Guide | Dashboard, Skill Radar, RAP AI Coach, Tactical Viewer, Advanced Analytics |
| `troubleshooting.md` | Troubleshooting | Correzioni stallo neurale, rilevamento demo, problemi avvio UI, ottimizzazione prestazioni |

### Argomenti di Fallback

Sia lo schermo di aiuto Qt che quello Kivy definiscono liste hardcoded
`_FALLBACK_TOPICS` utilizzate quando `help_system.py` non riesce ad essere importato
o quando `get_help_system()` solleva un'eccezione. Gli argomenti di fallback coprono:
Getting Started, Demo Analysis, AI Coach, Steam Integration, Navigation e
Troubleshooting. Questo garantisce che lo schermo di aiuto non sia mai completamente
vuoto, anche in ambienti degradati.

### Punteggio di Ricerca

L'algoritmo di ricerca e volutamente semplice (nessuno stemming, nessuna corrispondenza
fuzzy, nessuna tokenizzazione). I punteggi vengono assegnati come segue:

| Posizione Corrispondenza | Punteggio |
|--------------------------|-----------|
| Il titolo contiene la sottostringa della query | +10 |
| Il contenuto contiene la sottostringa della query | +1 |

I risultati sono ordinati per punteggio totale decrescente. Un argomento che corrisponde
sia nel titolo che nel contenuto riceve un punteggio combinato di 11.

## Integrazione

### Qt Help Screen (`apps/qt_app/screens/help_screen.py`)

Il consumatore UI principale. Implementa un layout a due pannelli:

- **Pannello sinistro** (240px fisso): Input di ricerca (`QLineEdit`) + lista argomenti (`QListWidget`)
- **Pannello destro** (flessibile): Visualizzatore contenuto scorrevole (`QLabel` dentro `QScrollArea`)

Lo schermo importa `get_help_system` con un guard try/except e imposta
`_HELP_AVAILABLE = True/False`. Su `on_enter()`, tenta di caricare gli argomenti dal
sistema di aiuto e ricade su `_FALLBACK_TOPICS` in caso di errore. La ricerca viene
eseguita lato client filtrando la lista di argomenti gia caricata.

### Kivy Help Screen (`apps/desktop_app/help_screen.py`)

Il consumatore Kivy legacy. Utilizza `MDScreen` con widget `MDListItem` per la
barra laterale degli argomenti e un `MDLabel` per la visualizzazione del contenuto.
Segue lo stesso pattern di import-guard e fallback dello schermo Qt, ma popola una
lista vuota invece di argomenti di fallback quando il sistema di aiuto non e disponibile.

### Aggiungere Nuovi Argomenti di Aiuto

Per aggiungere un nuovo argomento di documentazione all'aiuto in-app:

1. Creare un nuovo file `.md` in `Programma_CS2_RENAN/data/docs/` (es. `economy_tips.md`)
2. Iniziare il file con un heading `# Titolo` — questo diventa il titolo dell'argomento nella barra laterale
3. Scrivere il contenuto in Markdown standard (il visualizzatore rende testo semplice, non HTML ricco)
4. Chiamare `get_help_system().refresh_index()` se l'app e gia in esecuzione, oppure riavviare

Non sono necessarie modifiche al codice. L'indice viene ricostruito dinamicamente dal filesystem.

## Note di Sviluppo

- **Thread safety:** `HelpSystem` non e thread-safe. E progettato per accesso
  single-threaded solo dalla UI. Sia lo schermo Qt che Kivy lo chiamano dal thread
  principale/UI.
- **Nessuna operazione di scrittura:** Il sistema di aiuto non modifica mai file su
  disco. E strettamente un indicizzatore di sola lettura.
- **Encoding:** Tutti i file vengono letti come UTF-8 (`encoding="utf-8"`).
- **Gestione errori:** I fallimenti di lettura dei singoli file vengono catturati e
  stampati su stderr (`print()`). Questo dovrebbe essere migrato al logging strutturato
  in un futuro intervento.
- **Invalidazione cache:** La cache viene ricostruita solo quando `refresh_index()` viene
  chiamato esplicitamente. Non esiste un meccanismo di file-watcher o auto-refresh.
- **Rendering contenuto:** Lo schermo di aiuto Qt visualizza il contenuto come testo
  semplice tramite `QLabel.setText()`. La formattazione Markdown (intestazioni, liste,
  link) non viene resa — il contenuto appare cosi com'e. Un miglioramento futuro
  potrebbe utilizzare `QTextBrowser` con `setMarkdown()` per il rendering ricco.
- **Limitazioni della ricerca:** La corrispondenza per sottostringa significa che
  cercare "demo" corrispondera anche a "demonstration" e "demographics". Non c'e
  consapevolezza dei confini di parola.
- **Compatibilita PyInstaller:** La directory dei documenti viene risolta tramite
  `get_resource_path()`, garantendo il funzionamento sia in sviluppo che nelle build
  congelate. La directory `data/docs/` deve essere inclusa nella lista `datas` del
  file spec di PyInstaller affinche il sistema di aiuto funzioni nelle build distribuite.

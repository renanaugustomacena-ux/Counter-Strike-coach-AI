> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Assets — Risorse Statiche

> **Autorita:** Rule 3 (Frontend & UX)

Questa directory contiene le risorse statiche utilizzate dall'applicazione a runtime. Questi file vengono inclusi nella distribuzione PyInstaller.

## Struttura della Directory

assets/
├── i18n/                     # Internazionalizzazione (traduzioni)
│   ├── en.json              # Inglese (137 chiavi) — primario/fallback
│   ├── pt.json              # Portoghese Brasiliano
│   └── it.json              # Italiano
└── maps/                     # Immagini radar mappe CS2
    ├── de_ancient_radar.dds ... (11 file DDS)

## i18n/ — File di Localizzazione

File JSON contenenti tutte le stringhe UI visibili all'utente. Lo schema delle chiavi e condiviso tra tutte le lingue.

### Categorie di Chiavi (137 chiavi totali)

| Categoria | Chiavi di Esempio | Scopo |
|-----------|-------------------|-------|
| Navigazione | `dashboard`, `coach`, `match_history` | Etichette barra laterale |
| Coaching | `coaching_insights`, `severity_high` | Testo schermata Coach |
| Impostazioni | `theme`, `language`, `demo_path` | Schermata Impostazioni |
| Profilo | `player_name`, `bio`, `role` | Campi profilo utente |
| Tattica | `tactical_viewer`, `playback_speed` | Schermata Tattica |

### Aggiungere una Nuova Lingua

1. Copiare `en.json` in `{language_code}.json`
2. Tradurre tutti i valori (mantenere le chiavi invariate)
3. Registrare in `apps/qt_app/core/i18n_bridge.py`
4. Aggiungere il pulsante di cambio lingua nelle impostazioni

## maps/ — Immagini Radar

Immagini radar in formato DDS per le mappe competitive di CS2. 11 immagini che coprono tutte le mappe del pool competitivo, incluse quelle multi-livello (Nuke superiore+inferiore, Vertigo superiore+inferiore).

## Note di Sviluppo

- I file DDS non devono superare i 4MB ciascuno
- I file JSON devono essere UTF-8 valido senza BOM
- I valori delle coordinate delle mappe provengono dai file di gioco di CS2

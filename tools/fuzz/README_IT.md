# `tools/fuzz/` -- Harness di fuzzing per il parser di demo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Test di robustezza per la pipeline di ingestione delle demo
> **Skill:** `/security-scan`, `/correctness-check`

## Scopo

Questa directory contiene un harness di fuzz-testing per la libreria `demoparser2` stessa (mappa al controllo C-SBX-02). Il suo compito e sollecitare il parser con byte di demo malformati, troncati e ostili, e confermare che:

1. Il parser **non** vada in segfault, panico o blocco su input invalidi.
2. I fallimenti emergano come eccezioni Python (catturabili, recuperabili).

Bypassa deliberatamente i gate di pre-validazione dell'app (`MIN_DEMO_SIZE = 10 MB`, controllo magic-byte) e chiama `demoparser2.DemoParser(...)` direttamente — la robustezza della libreria stessa e la superficie sotto test.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `fuzz_demo_parser.py` | Fuzzer principale. Genera byte di demo casuali (70% con il prefisso magic `PBDEMS2\0`, fino a 64 KiB) e li passa a `demoparser2.DemoParser` + `parse_event("round_start")`. |

## Esecuzione del fuzzer

```bash
# Esecuzione predefinita (budget di tempo 30 minuti)
python tools/fuzz/fuzz_demo_parser.py

# Esecuzione breve
python tools/fuzz/fuzz_demo_parser.py --time-budget 600 --seed 42

# Riprodurre un singolo crash input (exit 1 se si riproduce)
python tools/fuzz/fuzz_demo_parser.py --reproduce .fuzz/crashes/<hash>-<size>.dem
```

Quando [Atheris](https://github.com/google/atheris) e installato, l'esecuzione e coverage-guided; altrimenti ricade su un loop deterministico di input casuali (`--force-fallback` salta Atheris esplicitamente). Gli input di crash vengono scritti in `--crash-dir` (default `.fuzz/crashes/`) come `<sha256-prefix>-<size>.dem` (primi 16 caratteri hex dello SHA-256) piu un sidecar `.meta` che registra la classe dell'eccezione e il messaggio.

## Modalita di fallimento da cui il fuzzer protegge

- Header troncati (il parser deve abortire in modo pulito).
- Campi di lunghezza messaggio incoerenti (il parser non deve sovra-leggere).
- Indici di string-table invalidi (il parser non deve crashare su lookup fuori range).
- Dati spazzatura casuali con e senza il prefisso magic `PBDEMS2\0`.

Nell'applicazione stessa, dati spazzatura cosi piccoli non raggiungono mai il parser: i gate di pre-validazione dell'ingestione (`MIN_DEMO_SIZE = 10 MB`, controllo magic-byte — invariante `DS-12`) li rifiutano prima. Il fuzzer esiste per irrobustire il layer *dietro* quei gate.

## Correlati

- Parser di demo: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Gate di validazione: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Pipeline di ingestione: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- CI: esecuzioni notturne tramite `.github/workflows/fuzz-nightly.yml`; l'harness logga su stdout/stderr (`logging.basicConfig`, logger `fuzz_demo_parser`).

## Da non fare

- **Non** dare in pasto al fuzzer demo reali degli utenti — genera i propri input scratch; tenere le demo reali fuori da `.fuzz/`.
- **Non** disabilitare la guardia `MIN_DEMO_SIZE` dell'ingestione perche "il fuzzer passa" — la guardia e la prima linea di difesa in produzione.
- **Non** committare file demo contenenti casi di fallimento nel repo. `.fuzz/crashes/` rimane locale; cattura il seed (o il contenuto del sidecar `.meta`) e riproduci con `--reproduce` on demand.

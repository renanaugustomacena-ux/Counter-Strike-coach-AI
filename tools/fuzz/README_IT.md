# `tools/fuzz/` -- Harness di fuzzing per il parser di demo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Test di robustezza per la pipeline di ingestione delle demo
> **Skill:** `/security-scan`, `/correctness-check`

## Scopo

Questa directory contiene un harness di fuzz-testing per il parser di demo basato su `demoparser2`. Il suo compito e sollecitare il parser con file `.dem` malformati, troncati e ostili, e confermare che:

1. Il parser **non** vada in segfault, panico o blocco su input invalidi.
2. I fallimenti emergano come eccezioni Python (catturabili, recuperabili).
3. Il gate di pre-validazione (`MIN_DEMO_SIZE = 10 MB`, controllo magic-byte) rifiuti i file spazzatura prima che il parser li veda.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `fuzz_demo_parser.py` | Fuzzer principale. Genera byte di demo corrotti e li passa a `backend/data_sources/demo_parser.parse_demo()`. |

## Esecuzione del fuzzer

```bash
# Singola iterazione (smoke)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 1

# Fuzzing prolungato (CI / esecuzioni notturne)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 10000 \
    --seed 42 --report /tmp/fuzz_report.json
```

L'harness segnala ogni modalita di fallimento osservata, con il byte-offset della corruzione e la classe di eccezione risultante.

## Modalita di fallimento da cui il fuzzer protegge

- Header troncati (il parser deve abortire in modo pulito).
- Campi di lunghezza messaggio incoerenti (il parser non deve sovra-leggere).
- Indici di string-table invalidi (il parser non deve crashare su lookup fuori range).
- Densita patologica di tick (il parser deve rispettare i limiti di memoria).
- File piu piccoli di `MIN_DEMO_SIZE` (devono essere rifiutati prima del parsing -- invariante `DS-12`).

## Correlati

- Parser di demo: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Gate di validazione: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Pipeline di ingestione: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- Logging strutturato: i fallimenti sono emessi tramite `get_logger("cs2analyzer.fuzz")` e finiscono in `Programma_CS2_RENAN/logs/cs2_analyzer.log`.

## Da non fare

- **Non** dare in pasto al fuzzer demo reali degli utenti -- la fase di corruzione le distruggerebbe. L'harness genera input scratch propri.
- **Non** disabilitare la guardia `MIN_DEMO_SIZE` per "velocizzare" il fuzzing. La guardia fa parte della superficie sotto test.
- **Non** committare file demo contenenti casi di fallimento nel repo. Cattura la sequenza di byte (o il seed) nel report e riproduci on demand.

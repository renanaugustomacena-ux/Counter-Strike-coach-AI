# `logs/` — Staging dei log alla radice del repo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Staging dei log runtime (read-only per convenzione)

## Dove vanno effettivamente i log

Il file di log primario dell'applicazione è **`Programma_CS2_RENAN/logs/cs2_analyzer.log`** (ruotato in `.log.1`, `.log.2`, `.log.3`). È il file su cui scrive `app_logger` tramite `observability/logger_setup.py`.

Questa directory `./logs/` di livello superiore esiste come fallback / area di staging per strumenti che girano prima che il logger del pacchetto venga configurato (es. output di bootstrap molto precoce, smoke test ROCm, output di script di packaging).

```
logs/
└── cs2_analyzer.log     # Log legacy di bootstrap / startup precoce (piccolo)
```

Per indagini attive, **leggi `Programma_CS2_RENAN/logs/cs2_analyzer.log`**, non il file qui.

## Formato del log

Tutto l'output di `app_logger` è **JSON strutturato** con un evento per riga:

```json
{"ts":"2026-05-06T14:21:41+0200","lvl":"INFO","mod":"cs2analyzer.app","thread":"MainThread","msg":"..."}
```

Campi:

| Chiave | Significato |
|--------|-------------|
| `ts` | Timestamp ISO 8601 con offset di timezone |
| `lvl` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `mod` | Nome del logger (`cs2analyzer.<dominio>.<modulo>`) |
| `thread` | Identificatore del thread |
| `msg` | Messaggio libero (può contenere escape Unicode) |

## Filtraggio

```bash
# Ultimi 50 ERROR dal log del pacchetto
grep '"lvl":"ERROR"' Programma_CS2_RENAN/logs/cs2_analyzer.log | tail -50

# Voci del ciclo di training
grep '"mod":"cs2analyzer.app"' Programma_CS2_RENAN/logs/cs2_analyzer.log | grep -i training

# Tasso per modulo
awk -F'"mod":"' 'NF>1{split($2,a,"\"");print a[1]}' Programma_CS2_RENAN/logs/cs2_analyzer.log | sort | uniq -c | sort -rn | head -20
```

## Rotazione

La rotazione è gestita dal `RotatingFileHandler` standard configurato in `observability/logger_setup.py`. Default: 5 MB per file, 3 backup. La directory log del pacchetto è il target canonico — questa directory `./logs/` alla radice del repo NON partecipa alla rotazione.

## Da non fare

- Non committare grandi file di log. Aggiungi nuovi pattern al `.gitignore` se uno strumento inizia a dipendere da questa dir.
- Non parsare i log assumendo l'ordinamento delle righe tra thread — le scritture concorrenti si interleavano.
- Non loggare segreti. La configurazione di `app_logger` filtra le credenziali, ma le chiamate di logging custom devono comunque evitare PII / chiavi API per le regole di sicurezza.

## Correlati

- Configurazione del logger: `Programma_CS2_RENAN/observability/logger_setup.py`
- Output del validator (separato, solo stdout): `tools/headless_validator.py`
- Pitfall di buffering del log (processi di lunga durata sotto `tee`): vedere note in `CLAUDE.md`

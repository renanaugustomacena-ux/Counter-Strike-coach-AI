# `tests/automated_suite/` — Suite di test automatici a strati

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 5 (Testability)
> **Skill:** `/test-coverage`

## Scopo

Suite di test automatici a strati che esercita l'intero stack del Macena CS2 Analyzer a vari livelli di granularità. I test in questa directory complementano i moduli pytest organizzati per topic alla root del package (`Programma_CS2_RENAN/tests/test_*.py`) — quei test sono unit-oriented e raggruppati per dominio; i test in questo sub-package sono organizzati per **tipo di test**.

Lo split esiste perché la CI possa eseguire uno stage smoke-only veloce e poi gatear gli stage più lenti sul suo successo.

## Inventario dei file

| File | Strato | Scopo |
|------|-------|---------|
| `__init__.py` | — | Marker di package. |
| `test_smoke.py` | Smoke | Gate più veloce — istanzia i manager core, apre il DB, carica la config. Deve girare in pochi secondi. Un fallimento qui significa che la build è fondamentalmente rotta. |
| `test_unit.py` | Unit | Unit test mirati su funzioni utility core che non sono topic-specific (es. helper trasversali, coercizioni di tipo). |
| `test_functional.py` | Functional | Test funzionali per pipeline end-to-end con dipendenze esterne mockate — le pipeline girano in memoria, niente demo reali / network. |
| `test_e2e.py` | End-to-end | File demo reali o di fixture eseguiti attraverso il path completo ingestione → vettorizzazione → inferenza. Più pesanti; gated dietro `CS2_INTEGRATION_TESTS=1`. |
| `test_system_regression.py` | Regression | Controlli di regressione a livello di sistema: input known-bad, riproduzioni di bug storici, confronti con golden file. |

## Esecuzione

```bash
# Solo smoke (veloce)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py -v

# Smoke + unit (lane veloce CI di default)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py \
                   Programma_CS2_RENAN/tests/automated_suite/test_unit.py -v

# Functional (pipeline in memoria)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_functional.py -v

# Suite completa incluso E2E (lenta, richiede demo)
CS2_INTEGRATION_TESTS=1 ./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/ -v

# Regression
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_system_regression.py -v
```

## Raccomandazione di staging CI

Mettere in stage i test in modo che uno smoke fallito interrompa il run a basso costo:

```
1. Smoke           (secondi)     -> blocca tutti gli stage successivi se fallisce
2. Unit            (~1 min)      -> blocca functional / e2e se fallisce
3. Functional      (~5 min)      -> blocca e2e se fallisce
4. Regression      (~5 min)      -> indipendente da e2e
5. E2E             (~30+ min)    -> solo su run staged / nightly
```

## Convenzioni

- **Lo smoke è per la sanity, non per la copertura.** Preferire dieci test da 50 ms a uno da 5 s — il feedback veloce vale più della validazione esaustiva a questo strato.
- **I test functional devono mockare i sistemi esterni.** Niente network, niente demo reali, niente Ollama, niente API Steam. Usare le fixture in `Programma_CS2_RENAN/tests/conftest.py`.
- **I test E2E vanno gated dietro `CS2_INTEGRATION_TESTS=1`.** È il flag standard project-wide per i test lenti su dati reali.
- **I test di regression congelano i bug passati come fixture.** Quando un bug viene fixato, aggiungere l'input fallente come caso di regression così non può tornare in silenzio.

## Dove mettere un nuovo test

| Domanda | Risposta |
|----------|--------|
| Riguarda una singola funzione o classe? | `Programma_CS2_RENAN/tests/test_<topic>.py` (la root organizzata per topic) |
| È un sanity check sotto il secondo che la build sia viva? | `automated_suite/test_smoke.py` |
| È un test di pipeline cross-modulo con mock? | `automated_suite/test_functional.py` |
| Richiede demo reali / sistemi esterni? | `automated_suite/test_e2e.py` (gated) |
| È un lock-in "questo bug non deve mai tornare"? | `automated_suite/test_system_regression.py` |

## Correlati

- Test organizzati per topic (root): `Programma_CS2_RENAN/tests/README.md`
- Fixture condivise: `Programma_CS2_RENAN/tests/conftest.py`
- Validatore (gate separato): `tools/headless_validator.py` — eseguire dopo pytest, non al suo posto.
- Smoke RAP (aggiunto in Phase 0): `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`

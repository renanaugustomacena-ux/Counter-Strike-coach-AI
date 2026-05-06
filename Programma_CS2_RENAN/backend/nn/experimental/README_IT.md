# `backend/nn/experimental/` -- Sandbox neurale sperimentale

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/nn/experimental/`
> **Stato:** Sandbox attiva -- il codice qui e gated dietro feature flag e **non** viene caricato dalla pipeline di coaching di default.

## Scopo

Questo pacchetto e l'area di staging per architetture di reti neurali non ancora pronte per la pipeline di coaching in produzione. Il codice qui e:

- **Gated da feature flag** (es. `USE_RAP_MODEL=True`).
- **Importabile ma inerte** se il flag corrispondente non e impostato.
- **Non** una dipendenza runtime hard di `coaching_service.py` -- il servizio degrada alle modalita tradizionali / RAG quando i componenti sperimentali falliscono.

Quando un modulo qui dentro promuove a production-ready, viene spostato in una posizione non sperimentale (tipicamente `backend/nn/<dominio>/`) e il sotto-pacchetto sperimentale viene aggiornato per rimuovere o mettere in stub l'originale.

## Layout

```
experimental/
├── __init__.py
└── rap_coach/        # RAP Coach (Reasoning + Acting + Pedagogy) -- vedi rap_coach/README.md
```

## Sotto-pacchetti

| Sotto-pacchetto | Stato | Flag | Descrizione |
|-----------------|-------|------|-------------|
| `rap_coach/` | Sperimentale | `USE_RAP_MODEL=True` | Policy net multi-head a 7 livelli (perception, memory, strategy, pedagogy, communication, ecc.). Usa celle LTC `ncps` con la patch RAP-LTC-FIX sulle shape in `memory.py`. |

Vedi `rap_coach/README.md` per l'architettura RAP completa.

## Perche "experimental" e un pacchetto a se

Tenere il codice sperimentale in un sotto-pacchetto chiaramente etichettato porta tre vantaggi:

1. **Reviewability.** Un revisore puo capire immediatamente se una modifica tocca codice di produzione o di sandbox guardando il path di import.
2. **Isolamento dei test.** La pytest CI puo includere o escludere test sperimentali sulla base di un filtro di percorso senza modificare ogni file.
3. **Cancellazione sicura.** Quando un esperimento viene abbandonato, l'intero sotto-pacchetto puo essere rimosso in un singolo commit senza rischio di grep-and-replace nel resto di `nn/`.

## Aggiungere una nuova architettura sperimentale

1. Crea `experimental/<tuo_modulo>/` con `__init__.py`.
2. Aggiungi un feature flag nei default di `core/config.py` (default `False`).
3. Aggancia il controllo del flag al confine dell'orchestratore in `training_orchestrator.py`. **Non** importare codice sperimentale incondizionatamente altrove.
4. Fornisci un README che documenti: scopo, nome del flag, dipendenze, entry point di training e criteri di promozione.
5. Aggiungi uno smoke test che asserisca che il gate del flag sollevi quando `False`.

## Da non fare

- **Non** importare da `experimental/` in `coaching_service.py`, `correction_engine.py`, o in qualsiasi percorso che giri nella modalita di coaching di default.
- **Non** rilasciare un default del flag a `True` per codice sperimentale senza approvazione esplicita del proprietario.
- **Non** affidarsi a moduli sperimentali in build PyInstaller frozen senza un percorso di fallback.

## Correlati

- Dettagli RAP Coach: `experimental/rap_coach/README.md`
- Sotto-pacchetti NN di produzione: `backend/nn/README.md`
- Gestione feature-flag: `core/config.py:get_setting()`
- Gate del flag dell'orchestratore: `backend/nn/training_orchestrator.py:69-73`

# `backend/nn/layers/` -- Building block neurali riutilizzabili

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/nn/layers/`
> **Skill:** `/ml-check`

## Scopo

Questo pacchetto possiede i piccoli `nn.Module` riutilizzabili da cui dipende piu di un modello del progetto. Tutto cio che e unico per una singola architettura di modello resta dentro il pacchetto di quel modello -- solo i blocchi con piu consumer vengono promossi qui.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `__init__.py` | Marcatore di pacchetto. | -- |
| `superposition.py` | `SuperpositionLayer` -- linear layer context-gated con regolarizzazione di sparsita L1, hook di osservabilita del gate (`get_gate_statistics()`, `get_gate_activations()`) e controlli di tracing. | `SuperpositionLayer` |

## `SuperpositionLayer` in un paragrafo

Una proiezione lineare standard avvolta in un gate apprendibile e condizionato dal contesto. L'output del gate e regolarizzato L1 cosicche il layer impari a tenere la maggior parte della sua capacita inattiva su un dato input, "accendendo" solo il sottospazio rilevante per lo stato corrente. Usato dal layer Strategy del RAP Coach per combinare piu sotto-policy esperte sotto una singola parametrizzazione condivisa. Fornisce hook di osservabilita cosi il trainer puo loggare la sparsita del gate per step.

## Perche esiste questa directory

Prima della pulizia G-06, il progetto aveva brevemente due implementazioni parallele del meccanismo di superposition (una in `backend/nn/advanced/superposition_net.py`, una inline nel modello RAP). Entrambe erano divergenti. G-06 ha consolidato l'implementazione canonica qui. Deve restare esattamente una definizione di `SuperpositionLayer` nell'intero codebase -- vedi l'avvertimento in `backend/nn/advanced/README.md`.

## Aggiungere un nuovo layer

Un blocco appartiene qui solo quando e:

1. **Riusato da >= 2 modelli.** Un blocco usato da un singolo modello vive nel pacchetto di quel modello.
2. **Stateless rispetto alla modalita training/inferenza** oltre il classico switch `model.eval()` -- nessun registro globale, nessuno stato mutabile a livello di modulo.
3. **Documentato in questo README.** Aggiorna la tabella di inventario file e aggiungi un riassunto di un paragrafo.

## Da non fare

- **Non** duplicare `SuperpositionLayer`. C'e una sola implementazione canonica.
- **Non** aggiungere stato lato training (optimizer, scheduler, EMA) a un modulo in questo pacchetto.
- **Non** mettere logica di feature-engineering qui. L'estrazione di feature e proprieta di `backend/processing/feature_engineering/`.

## Correlati

- Consumer Strategy del RAP Coach: `backend/nn/experimental/rap_coach/strategy.py`
- Cronologia degli stub vuoti: `backend/nn/advanced/README.md` (note pulizia G-06)
- Dimensione feature: `METADATA_DIM = 25` da `backend/processing/feature_engineering/vectorizer.py`

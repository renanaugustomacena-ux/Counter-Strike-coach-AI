# `backend/nn/layers/` -- Building block neurali riutilizzabili

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/nn/layers/`
> **Skill:** `/ml-check`

## Scopo

Questo pacchetto possiede le definizioni canoniche dei building block `nn.Module` condivisi. E stato creato durante la remediazione G-06 per consolidare implementazioni duplicate in un'unica posizione autorevole. Attualmente il suo unico occupante, `SuperpositionLayer`, e consumato dallo Strategy layer del RAP Coach.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `__init__.py` | Marcatore di pacchetto. | -- |
| `superposition.py` | `SuperpositionLayer` -- layer lineare con condizionamento FiLM (`y = γ(context)·(Wx+b) + β(context)`, RAP-AUDIT-06) con hook di loss per sparsita L1 del gate (`gate_sparsity_loss()`), hook di osservabilita del gate (`get_gate_statistics()`, `get_gate_activations()`) e controlli di tracing. | `SuperpositionLayer` |

## `SuperpositionLayer` in un paragrafo

Una proiezione lineare standard modulata da Feature-wise Linear Modulation (FiLM): un gate sigmoide `γ(context)` scala la proiezione e uno shift additivo inizializzato a zero `β(context)` inietta feature guidate dal contesto (RAP-AUDIT-06 -- il precedente gate solo moltiplicativo poteva sopprimere feature ma mai aggiungerne). Ogni esperto nello Strategy layer del RAP Coach ne usa uno come primo layer adattabile al contesto. Fornisce un hook di loss per sparsita L1 del gate (`gate_sparsity_loss()`) e hook di osservabilita cosi il trainer puo loggare la sparsita del gate per step.

## Perche esiste questa directory

Prima della pulizia G-06, il progetto aveva brevemente due implementazioni parallele del meccanismo di superposition (una in `backend/nn/advanced/superposition_net.py`, una inline nel modello RAP). Entrambe erano divergenti. G-06 ha consolidato l'implementazione canonica qui. Deve restare esattamente una definizione di `SuperpositionLayer` nell'intero codebase -- vedi l'avvertimento in `backend/nn/advanced/README.md`.

## Aggiungere un nuovo layer

Un blocco appartiene qui quando e:

1. **La singola definizione canonica** di un building block che non deve essere duplicato altrove (principio G-06).
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

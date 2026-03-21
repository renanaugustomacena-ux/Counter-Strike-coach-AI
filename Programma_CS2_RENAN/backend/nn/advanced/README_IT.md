> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Stub Vuoto Intenzionale

> **Autorita:** `Programma_CS2_RENAN/backend/nn/advanced/`
> **Stato:** Pacchetto vuoto. Tutti i moduli rimossi nella remediazione G-06.

## Cosa è Successo

Questo pacchetto conteneva originariamente tre moduli sperimentali:

| File Rimosso | Scopo Originale |
|--------------|-----------------|
| `superposition_net.py` | Wrapper sperimentale di SuperpositionLayer con fusione di modalità brain |
| `brain_bridge.py` | Ponte di orchestrazione tra percorsi di coaching standard e avanzato |
| `feature_engineering.py` | Logica duplicata di estrazione feature (copia shadow del vectorizer canonico) |

Durante la fase di remediazione G-06, un audit del codice morto ha rivelato che **tutti e tre i moduli avevano zero chiamanti** nell'intero codebase. Le loro funzionalità erano già state assorbite nelle posizioni canoniche attraverso lavori di refactoring precedenti, rendendo questi file codice morto irraggiungibile. Sono stati rimossi per ridurre il carico di manutenzione ed eliminare confusione su quale implementazione fosse autorevole.

## Dove Risiede Ora la Funzionalità

Le funzionalità sopravvissute sono migrate nelle posizioni canoniche prima di G-06:

- **SuperpositionLayer** -- `backend/nn/layers/superposition.py`. Il layer lineare canonico con gating contestuale, regolarizzazione L1 di sparsità, hook di osservabilità dei gate (`get_gate_statistics()`, `get_gate_activations()`) e controlli di tracciamento. Utilizzato dallo Strategy layer del RAP Coach.
- **Orchestrazione BrainBridge** -- Assorbita in `backend/nn/rap_coach/model.py` (`RAPCoachModel`). Il modello stesso gestisce il coordinamento tra i livelli perception, memory, strategy, pedagogy e communication.
- **Feature engineering** -- `backend/processing/feature_engineering/vectorizer.py` (`FeatureExtractor`). Questa è l'unica fonte di verità per il vettore di feature a 25 dimensioni (`METADATA_DIM = 25`). Non deve mai esistere una seconda implementazione.

## Perché il Namespace è Preservato

La directory `advanced/` è mantenuta come pacchetto Python valido (con `__init__.py`) per tre ragioni:

1. **Sicurezza delle importazioni.** Codice esistente o strumenti di terze parti che scansionano l'albero del pacchetto `nn/` non si romperanno per un sotto-pacchetto mancante.
2. **Riserva del namespace.** Architetture avanzate o sperimentali future che si diplomano oltre il sandbox `experimental/` potranno essere collocate qui.
3. **Traccia di audit.** Il commento in `__init__.py` documenta cosa è stato rimosso e perché, preservando la memoria istituzionale.

## Contenuto del Pacchetto

| File | Scopo |
|------|-------|
| `__init__.py` | Stub del pacchetto con commento storico della rimozione G-06 (5 righe) |
| `README.md` | Versione inglese |
| `README_IT.md` | Questo file |
| `README_PT.md` | Traduzione portoghese |

## Contesto della Remediazione G-06

La remediazione G-06 è stata una pulizia di codice morto a livello di codebase che ha preso di mira moduli con zero riferimenti di importazione. L'audit è stato eseguito scansionando tutti i file Python alla ricerca di pattern `from ... advanced` e `import ... advanced`. I tre file in questo pacchetto erano gli unici moduli nell'intero albero `nn/` che non avevano alcun chiamante. La loro rimozione è stata una decisione deliberata per applicare il principio della "unica fonte di verità": ogni concetto nel sistema deve avere esattamente un'implementazione autorevole.

Il rischio chiave che G-06 ha affrontato erano le **implementazioni shadow** -- codice duplicato che diverge silenziosamente dalla versione canonica. Il file `feature_engineering.py` in questo pacchetto era un esempio particolarmente pericoloso: conteneva una copia della logica di estrazione feature che avrebbe potuto essere accidentalmente importata al posto del canonico `vectorizer.py`, producendo vettori di feature sottilmente diversi e corrompendo l'addestramento del modello.

## Note di Sviluppo

- **Non aggiungere moduli qui senza giustificazione.** Il nuovo lavoro sperimentale deve andare prima in `backend/nn/experimental/` e diplomarsi ad `advanced/` solo dopo aver dimostrato stabilità.
- **Il SuperpositionLayer canonico è in `layers/superposition.py`.** Non ricrearlo qui.
- **Il FeatureExtractor canonico è in `processing/feature_engineering/vectorizer.py`.** Non duplicare logica di estrazione feature in nessuna parte di `nn/`.
- **Se si aggiunge un modulo qui**, aggiornare questo README, il commento in `__init__.py` e la tabella dei sotto-pacchetti nel `nn/README.md` principale.

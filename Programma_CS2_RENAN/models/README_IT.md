> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Archiviazione Checkpoint Reti Neurali

> **Autorità:** Regola 4 (Persistenza Dati)

Questa directory contiene i checkpoint delle reti neurali addestrate (file .pt) utilizzati dal Ghost Engine per l'inferenza e dalla pipeline di coaching per i suggerimenti potenziati da ML.

## Tipi di Checkpoint

| Checkpoint | Modello | Creato Da | Dimensione |
|-----------|---------|-----------|------------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variabile |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB |
| `role_head.pt` | NeuralRoleHead | Addestramento classificazione ruoli | ~50 KB |

## Gerarchia di Archiviazione

models/
├── global/              # Baseline condivisa (da addestramento demo professionali)
│   ├── jepa_brain.pt
│   └── ...
└── {user_id}/           # Modelli personalizzati per utente (futuro)

Il modulo `persistence.py` gestisce l'I/O dei checkpoint:
- Scritture atomiche tramite file temporanei per prevenire la corruzione
- Caricamento multi-fallback: Modello utente → Modello globale → Modello di fabbrica incluso
- Validazione dimensioni: solleva StaleCheckpointError se l'architettura è cambiata

## Avviso Critico

- WinProbabilityNN (produzione, 12 feature) e WinProbabilityTrainerNN (offline, 9 feature) utilizzano architetture diverse. Non incrociare mai i loro checkpoint.

## Note di Sviluppo

- NON committare file `.pt` nel repository
- I checkpoint sono versionati implicitamente dalla loro architettura
- I pesi shadow EMA sono memorizzati all'interno del dizionario del checkpoint

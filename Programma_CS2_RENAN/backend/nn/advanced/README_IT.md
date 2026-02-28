> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Orchestrazione Multi-Modello

Architetture neurali avanzate per orchestrazione multi-modello, reti quantum-inspired e feature engineering a livello brain.

## Moduli Principali

### Orchestrazione Multi-Modello
- **brain_bridge.py** — `BrainBridge` — Livello orchestrazione multi-modello coordinando RAP Coach, JEPA, VL-JEPA e NeuralRoleHead. Implementa analisi CSI (Critical Situation Index) per selezione modelli context-aware e strategie ensemble.

### Architettura Quantum-Inspired
- **superposition_net.py** — `SuperpositionLayer`, `AdaptiveSuperpositionMLP` — Rete superposizione quantum-inspired con mixing probabilistico features. Implementa stati superposizione che collassano a output deterministici basati su attenzione contesto.

### Feature Engineering
- **feature_engineering.py** — `BrainFeatureEngineer` — Feature engineering livello brain per input multi-modello. Estrae e normalizza features attraverso dimensioni visive, temporali e strategiche per consumo modello unificato.

## Integrazione

BrainBridge coordina output modelli via strategie ensemble pesate:
1. **Valutazione Situazione**: Analisi CSI determina criticità contesto (routine/tattico/critico)
2. **Selezione Modello**: Attiva modelli appropriati basati su situazione (JEPA per percezione, RAP per coaching, Role per classificazione)
3. **Sintesi Output**: Combinazione pesata con gating basato su confidenza

## Analisi CSI

Critical Situation Index calcolato da:
- Pressione tempo (timer bomba, tempo round rimanente)
- Stato economico (buy round, eco, force buy)
- Vantaggio/svantaggio numerico
- Zone controllo mappa contestate

## Dipendenze
PyTorch, NumPy.

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Multi-Model Orchestration

Advanced neural architectures for multi-model orchestration, quantum-inspired networks, and brain-level feature engineering.

## Core Modules

### Multi-Model Orchestration
- **brain_bridge.py** — `BrainBridge` — Multi-model orchestration layer coordinating RAP Coach, JEPA, VL-JEPA, and NeuralRoleHead. Implements CSI (Critical Situation Index) analysis for context-aware model selection and ensemble strategies.

### Quantum-Inspired Architecture
- **superposition_net.py** — `SuperpositionLayer`, `AdaptiveSuperpositionMLP` — Quantum-inspired superposition network with probabilistic feature mixing. Implements superposition states that collapse to deterministic outputs based on context attention.

### Feature Engineering
- **feature_engineering.py** — `BrainFeatureEngineer` — Brain-level feature engineering for multi-model inputs. Extracts and normalizes features across visual, temporal, and strategic dimensions for unified model consumption.

## Integration

BrainBridge coordinates model outputs via weighted ensemble strategies:
1. **Situation Assessment**: CSI analysis determines context criticality (routine/tactical/critical)
2. **Model Selection**: Activates appropriate models based on situation (JEPA for perception, RAP for coaching, Role for classification)
3. **Output Synthesis**: Weighted combination with confidence-based gating

## CSI Analysis

Critical Situation Index computed from:
- Time pressure (bomb timer, round time remaining)
- Economic state (buy round, eco, force buy)
- Numerical advantage/disadvantage
- Map control zones contested

## Dependencies
PyTorch, NumPy.

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Armazenamento de Checkpoints de Redes Neurais

> **Autoridade:** Regra 4 (Persistencia de Dados)

Este diretorio armazena checkpoints de redes neurais treinadas (arquivos .pt) usados pelo Ghost Engine para inferencia e pelo pipeline de coaching para conselhos aprimorados por ML.

## Tipos de Checkpoint

| Checkpoint | Modelo | Criado Por | Tamanho |
|-----------|--------|-----------|---------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variavel |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB |
| `role_head.pt` | NeuralRoleHead | Treinamento de classificacao de funcoes | ~50 KB |

## Hierarquia de Armazenamento

models/
├── global/              # Baseline compartilhada (de treinamento com demos profissionais)
│   ├── jepa_brain.pt
│   └── ...
└── {user_id}/           # Modelos ajustados por usuario (futuro)

O modulo `persistence.py` gerencia o I/O dos checkpoints:
- Escritas atomicas usando arquivos temporarios para prevenir corrupcao
- Carregamento multi-fallback: Modelo do usuario → Modelo global → Modelo de fabrica incluso
- Validacao de dimensoes: levanta StaleCheckpointError se a arquitetura mudou

## Aviso Critico

- WinProbabilityNN (producao, 12 features) e WinProbabilityTrainerNN (offline, 9 features) usam arquiteturas diferentes. Nunca cruze seus checkpoints.

## Notas de Desenvolvimento

- NAO commitar arquivos `.pt` no repositorio
- Checkpoints sao versionados implicitamente pela sua arquitetura
- Os pesos shadow EMA sao armazenados dentro do dicionario do checkpoint

# `backend/nn/experimental/rap_coach/` — RAP Coach (experimental)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/`
> **Skill:** `/ml-check`, `/jepa-audit`
> **Status:** Experimental — atrás do feature flag `USE_RAP_MODEL=True`. Não é carregado pela pipeline de coaching padrão.

## Propósito

RAP Coach (**R**easoning + **A**cting + **P**edagogy) é uma rede de policy multi-cabeças que consome o embedding do world-model JEPA mais o estado por tick e produz:

- Um label de **strategy** de 10 dimensões (one-hot sobre os papéis táticos canônicos).
- Uma estimativa escalar de **value** representando a probabilidade de vitória do round.
- Uma previsão de **delta de posição** em 3 dimensões para o jogador.
- Um sinal escalar de **sparsity** que dirige a regularização L1 sobre os gates de strategy.

Arquiteturalmente, é uma pipeline de 7 estágios — perception → memory → strategy → pedagogy → communication — construída sobre células LTC (Liquid Time-Constant) do `ncps` para raciocínio temporal através da janela de 32 ticks (`RAP_SEQ_LEN`).

## Inventário de arquivos

| Arquivo | Componente | Propósito |
|------|-----------|---------|
| `__init__.py` | — | Marcador de pacote. |
| `perception.py` | `RAPPerception` | Agregador de features visuais / espaciais. Consome views por tick, mini-mapa e tensores de movimento, projetando-os em um embedding unificado de percepção. |
| `memory.py` | `RAPMemory` | Memória temporal baseada em LTC sobre a janela de 32 ticks. **Contém o monkey-patch RAP-LTC-FIX** sobre `ncps.LTCCell._ode_solver` (linhas 70–93) — corrige um shape mismatch 1-D / 2-D em `cm / (elapsed_time / ode_unfolds)`. |
| `strategy.py` | `RAPStrategy` | Cabeça de strategy: superposition layer + softmax de 10 classes sobre os papéis táticos. |
| `pedagogy.py` | `RAPPedagogy` | Cabeça de pedagogy: prior de explicação — produz uma representação de baixa dimensão downstream da decisão de strategy, usada para explicabilidade. |
| `communication.py` | `RAPCommunication` | Cabeça de communication: pequeno MLP no qual a camada de RAG / coaching pode condicionar para gerar prosa policy-aware. |
| `chronovisor_scanner.py` | `ChronovisorScanner` | Identifica "moments" temporalmente críticos em um replay usando as cabeças de strategy + value. Fornece marcadores ao Tactical Viewer. |
| `model.py` | `RAPCoachModel` | Compõe os 7 estágios. Carregado via `ModelFactory.get_model('rap')`. Dimensões inicializadas: `metadata_dim=25`, `output_dim=10`, `hidden=256`, `perception=128`. |
| `trainer.py` | `RAPTrainer` | Driver de treinamento: loss composta (strategy + value + sparsity + position), penalidade no eixo Z, AMP, scheduler. Construído por `TrainingOrchestrator(model_type='rap')`. |
| `conftest.py` | — | Fixtures do pytest locais a este pacote (por exemplo, fixture mínima de RAP para testes de arquitetura). |
| `test_arch.py` | — | Testes que verificam shapes do forward pass e fluxo de gradiente em um batch sintético mínimo. Roda em CI sem demos reais. |

## Ativação

```python
# Padrões de core/config.py
"USE_RAP_MODEL": False,    # padrão

# Habilita por sessão via dict _settings (sem escrita em disco):
from Programma_CS2_RENAN.core import config
with config._settings_lock:
    config._settings["USE_RAP_MODEL"] = True

# Ou persiste via:
from Programma_CS2_RENAN.core.config import save_user_setting
save_user_setting("USE_RAP_MODEL", True)
```

`TrainingOrchestrator.__init__` levanta `ValueError` se `model_type='rap'` for solicitado com a flag em `False`. Isso protege contra runs de treinamento não intencionais.

## Treinamento

Entry point: `run_full_training_cycle.py --dry-run --model-type rap --epochs 1`

Ou programaticamente:

```python
from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

manager = CoachTrainingManager()
manager.assign_dataset_splits()
orch = TrainingOrchestrator(manager, model_type="rap", max_epochs=1, patience=1)
orch.run_training()
```

## Invariantes críticas

| ID | Arquivo / linha | Invariante |
|----|-------------|-----------|
| RAP-LTC-FIX | `memory.py:70-93` | Patch de shape no `_ode_solver` — deve permanecer no lugar; upgrades futuros do ncps podem torná-lo redundante, mas não devem quebrá-lo silenciosamente. |
| RAP-AUDIT-01 | `trainer.py`, `training_orchestrator.py:496` | `RAP_SEQ_LEN = 32` — janela temporal para o processamento de sequência LTC. Deve casar com o default de `state_reconstructor.py`. |
| RAP-AUDIT-02 | `training_orchestrator.py:_rap_compute_target_pos` | Deltas de posição por tick obrigatórios para o treinamento da cabeça de position. |
| RAP-AUDIT-05 | `training_orchestrator.py:_rap_compute_timespans` | `dt` inter-tick obrigatório para a integração da ODE do LTC. Constante de 1/64 s em replays canônicos, mas mantido tensorial para suporte futuro a ticks variáveis. |
| LEAK-01 | `training_orchestrator.py:686-693` | `val_mask=False` quando o conhecimento não está disponível, para que a cabeça de value nunca treine sobre o resultado vazado do round. |
| NN-TR-02b | `trainer.py:43-100` | Penalidade no eixo Z imposta na position loss para prevenir drift vertical em mapas multi-nível. |
| POV-RAP-FIX-2 | `training_orchestrator.py:632-637` | Fallback de `match_id` via `demo_name_to_match_id` quando a FK do DB é `None`. |
| T-2 FIX | `training_orchestrator.py:756-780` | Gate de ≥ 50% de densidade POV por janela temporal. |

Os testes destas invariantes vivem em `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py` e `Programma_CS2_RENAN/tests/test_rap_coach.py`.

## Limites

- **Não importe módulos do RAP a partir do código de coaching de produção.** `coaching_service.py` seleciona o backend RAP via `ModelFactory.get_model('rap')`, que levanta exceção se a flag não estiver setada. Imports diretos passam por cima do gate.
- **Não modifique `RAP_SEQ_LEN` sem retreinar todos os checkpoints do RAP.** Faz parte do contrato de arquitetura.
- **Não remova o monkey-patch `RAP-LTC-FIX`.** O bug de shape no upstream do ncps ainda se aplica no HEAD. O teste de CI em `test_rap_training_dry_run.py` afirma a presença do marcador do fix.

## Relacionados

- Sandbox experimental pai: `backend/nn/experimental/README.md`
- Subpacotes de NN de produção: `backend/nn/README.md`
- Orchestrator de treinamento: `backend/nn/training_orchestrator.py`
- Smoke test / regressão: `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`
- ncps upstream: <https://github.com/mlech26l/ncps>
- Docs originais de arquitetura: `docs/Studies/` (volumes RAP)

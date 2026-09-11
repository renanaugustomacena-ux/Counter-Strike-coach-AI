> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Armazenamento de Checkpoints de Redes Neurais

> **Autoridade:** Regra 4 (Persistencia de Dados)

Este diretorio armazena checkpoints de redes neurais treinadas (arquivos `.pt`)
usados pelo Ghost Engine para inferencia em tempo real e pelo pipeline de coaching
para geracao de conselhos aprimorados por ML. Os checkpoints sao serializacoes
binarias `state_dict` do PyTorch gerenciadas pelo modulo `persistence.py`, que
impoe escritas atomicas, carregamento multi-fallback e validacao dimensional
rigorosa.

Nenhum arquivo `.pt` e commitado no repositorio. Este diretorio existe no controle
de versao para preservar sua estrutura (via `global/README.txt`), para hospedar o
registro de hashes CTF-1 dos checkpoints (`checkpoint_hashes.json`) e para servir
como destino de escrita padrao quando `BRAIN_DATA_ROOT` nao esta configurado.
Checkpoints treinados sao artefatos runtime locais (gitignored); consulte
`docs/OPEN_ISSUES.md` §2 para tarefas pendentes de treinamento e dados.

## Estrutura do Diretorio

```
models/
├── global/                   # Modelos baseline compartilhados (nao especificos por usuario)
│   ├── archive_pre_rebuild_2026-09-01/  # Pesos arquivados pre-rebuild (arquivos .pt gitignored)
│   └── README.txt           # Placeholder para preservar o diretorio no git
├── checkpoint_hashes.json    # Registro de hashes SHA-256 CTF-1 para checkpoints
├── README.md                 # Este arquivo (Ingles)
├── README_IT.md              # Traducao Italiana
└── README_PT.md              # Traducao Portuguesa
```

Apos o rebuild de 2026-09-01, `models/` nao contem arquivos `.pt` de producao.
Os pesos pre-rebuild foram arquivados em
`global/archive_pre_rebuild_2026-09-01/` (gitignored).

Em tempo de execucao, modelos ajustados por usuario sao armazenados em subdiretorios por usuario:

```
models/
├── global/                  # Baseline compartilhada (de treinamento com demos profissionais)
│   ├── latest.pt           # Modelo coach padrao (AdvancedCoachNN)
│   ├── jepa_brain.pt       # JEPA pre-treinado em partidas profissionais (melhor val loss)
│   ├── jepa_brain_latest.pt # Salvamento rolling por epoca da mesma execucao
│   └── rap_coach.pt        # Checkpoint do modelo RAP
├── nn/versions/             # Snapshots com timestamp (ModelManager.save_version)
│   └── brain_{timestamp}.pt
└── {user_id}/               # Modelos ajustados por usuario
    └── latest.pt           # Checkpoint adaptado ao usuario
```

O `TrainingOrchestrator` escreve dois arquivos por execucao: o nome de versao
puro ao atingir uma nova melhor validation loss, e `{version}_latest.pt` apos
cada epoca. Cada checkpoint salvo atraves de `save_nn()` e acompanhado por um
arquivo sidecar `.pt.meta.json` (GAP-07) que registra `schema_version`,
`metadata_dim` e a lista de nomes de features no momento do salvamento.

## Inventario de Checkpoints

As strings de versao mapeiam para os tipos de modelo do `ModelFactory`:

| Checkpoint | Classe do Modelo | Criado Por | Input Dim |
|-----------|-----------------|-----------|-----------|
| `latest.pt` | AdvancedCoachNN (padrao) | `backend/nn/train.py`, `coach_manager.py` | 25 (METADATA_DIM) |
| `jepa_brain.pt` | Modelo de coaching JEPA | `backend/nn/training_orchestrator.py` (loop de epocas: `jepa_trainer.py`) | 25 (METADATA_DIM) |
| `vl_jepa_brain.pt` | VL-JEPA (concept head) | `backend/nn/training_orchestrator.py` | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/training_orchestrator.py` (loop de epocas: `experimental/rap_coach/trainer.py`; condicionado por `USE_RAP_MODEL`) | 25 (METADATA_DIM) |
| `rap_lite_coach.pt` | RAP-Lite (memoria LSTM) | Treinamento RAP com `use_lite_memory` (string de versao de `factory.py`) | 25 (METADATA_DIM) |
| `role_head.pt` | NeuralRoleHead | `backend/nn/role_head.py` | 5 |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` (utilitario offline, atualmente sem chamador em producao) | 9 (subconjunto offline) |

O orquestrador tambem escreve um checkpoint rolling `{version}_latest.pt` por
epoca, e o pipeline standalone de dois estagios `backend/nn/jepa_train.py`
(CLI pretrain/finetune sobre o banco de dados monolito) escreve
`jepa_model.pt` / `jepa_model_finetuned.pt` em seu proprio formato de
dicionario wrappado.

## Formato dos Checkpoints

Cada arquivo `.pt` escrito atraves de `save_nn()` e um dicionario `state_dict`
do PyTorch salvo via `torch.save()`. As chaves correspondem aos parametros
nomeados da classe do modelo. (O pipeline standalone `jepa_train.py` em vez
disso wrappa o state dict em um dicionario checkpoint com `model_state_dict`,
contadores EMA e metadados de treinamento.) Estrutura de exemplo para
`jepa_brain.pt`:

```python
{
    "online_encoder.layer1.weight": Tensor(...),
    "online_encoder.layer1.bias": Tensor(...),
    "coaching_head.fc1.weight": Tensor(...),
    "coaching_head.fc1.bias": Tensor(...),
    # ... todos os parametros nomeados
}
```

Para modelos que utilizam EMA (Exponential Moving Average), os pesos shadow sao
armazenados **dentro** do mesmo dicionario do checkpoint, nao como arquivos
separados. O modulo EMA clona os tensores shadow durante `apply_shadow()` para
preservar os originais (invariante NN-16).

## Arquitetura de Persistencia

O modulo `backend/nn/persistence.py` e a interface canonica para I/O de
checkpoints nos caminhos de carregamento/salvamento em producao; codigo novo nao
deve chamar `torch.save()` / `torch.load()` diretamente. Excecoes offline
conhecidas que o bypassam: o pipeline standalone `jepa_train.py` (formato
checkpoint wrappado atomico proprio), o utilitario dormente
`win_probability_trainer.py` (`state_dict` bruto para um caminho fornecido pelo
chamador), e `ModelManager.save_version()` em `model.py` (snapshots com
timestamp em `models/nn/versions/`).

### Protocolo de Escrita Atomica

```
save_nn(model, version, user_id=None, extra_meta=None)
  1. Resolver o caminho destino: models/{user_id ou "global"}/{version}.pt
  2. Escrever pesos e sidecar .pt.meta.json em arquivos temporarios
  3. Substituicao atomica: tmp_path.replace(path)  # pesos primeiro, depois sidecar
  4. Registrar SHA-256 em checkpoint_hashes.json (CTF-1)
  5. Em caso de falha: remover arquivos tmp, re-levantar excecao
```

Isso previne corrupcao quando a aplicacao crasha durante a escrita ou quando o
sistema perde energia durante o treinamento.

### Cadeia de Carregamento Multi-Fallback

```
load_nn(version, model, user_id=None)
  1. Tentar: models/{user_id}/{version}.pt         (modelo aprendido especifico do usuario)
  2. Tentar: models/global/{version}.pt            (baseline compartilhada)
  3. Tentar: factory incluso/{user_id}/{version}.pt (incluso PyInstaller, usuario)
  4. Tentar: factory incluso/global/{version}.pt   (incluso PyInstaller, global)
  5. Falhar: levantar FileNotFoundError             (nunca pesos random silenciosos)
```

Antes que os pesos toquem o modelo, o arquivo resolvido e verificado contra o
registro de hashes CTF-1, e seu sidecar `.pt.meta.json` (se presente) e validado
para `schema_version`, `metadata_dim` e drift de nomes de features -- qualquer
discrepancia levanta `StaleCheckpointError`. Checkpoints legados sem sidecar sao
carregados com um aviso.

### Validacao Dimensional

Durante o carregamento, `model.load_state_dict(state_dict, strict=True)` e utilizado.
Se o checkpoint foi produzido por um modelo com arquitetura diferente (ex. apos
`METADATA_DIM` mudar de 25 para 26), o carregamento falha com um `RuntimeError`.
O modulo de persistencia captura isso e levanta `StaleCheckpointError`, que sinaliza
aos chamadores que re-treinamento e necessario.

## Avisos Criticos

| ID | Regra | Consequencia da Violacao |
|----|-------|--------------------------|
| NN-14 | Nunca retornar silenciosamente um modelo com pesos random | Saida de coaching lixo, confianca do usuario destruida |
| NN-16 | EMA `apply_shadow()` deve `.clone()` os tensores shadow | Corrupcao de treinamento, nao recuperavel |
| NN-MEM-01 | Memoria Hopfield bypassada ate `notify_optimizer_step()` disparar | Propagacao NaN na memoria RAP |
| — | `WinProbabilityNN` (12 features) vs `WinProbabilityTrainerNN` (9 features) | Crash por cross-loading ou corrupcao silenciosa |

`WinProbabilityNN` (producao, 12 features) e `WinProbabilityTrainerNN`
(treinamento offline, 9 features) usam **arquiteturas diferentes**. Seus
checkpoints nao sao intercambiaveis. Nunca cruze o carregamento entre eles.

Apos qualquer mudanca arquitetural (modificacao de `METADATA_DIM`, `HIDDEN_DIM`,
`OUTPUT_DIM` ou estrutura de camadas), todos os checkpoints existentes se tornam
invalidos. O sistema detecta isso automaticamente via carregamento `strict=True` e
levanta `StaleCheckpointError`.

## Versionamento de Modelos

Os checkpoints sao versionados pelo seu nome de arquivo (parametro `version` em
`save_nn` / `load_nn`); o sidecar `.pt.meta.json` incorpora adicionalmente uma
`schema_version` (GAP-07). A compatibilidade e imposta tanto pela verificacao do
sidecar quanto estruturalmente: se as chaves do `state_dict` ou os formatos dos
tensores nao correspondem a classe do modelo atual, o carregamento falha
deterministicamente.

| String de Versao | Modelo | Fonte de Treinamento |
|-----------------|--------|----------------------|
| `latest` | AdvancedCoachNN | Pipeline de treinamento padrao (`train.py`, `coach_manager.py`) |
| `jepa_brain` | Modelo de coaching JEPA | Dataset de demos profissionais (treinamento JEPA em dois estagios) |
| `vl_jepa_brain` | VL-JEPA | Dataset de demos profissionais (treinamento concept-head) |
| `rap_coach` | RAPCoachModel | Dataset de demos profissionais (treinamento RAP LTC-Hopfield) |
| `rap_lite_coach` | RAP-Lite | Treinamento RAP com memoria LSTM de fallback |
| `role_head` | NeuralRoleHead | Dataset de classificacao de funcoes |
| `win_prob` | WinProbabilityTrainerNN | Dataset de resultados de rounds (utilitario offline; sem chamador em producao -- o preditor permanece euristico ate o re-treinamento de 12 dim) |

Execucoes completas requerem o banco de dados de treinamento monolito; consulte
`docs/OPEN_ISSUES.md` §2 para tarefas pendentes de dados e treinamento.

## Bundling (PyInstaller)

A cadeia de carregamento suporta checkpoints inclusos na factory:
`get_factory_model_path()` os resolve atraves de `get_resource_path()`, que
verifica `sys._MEIPASS` no ambiente congelado. Note que o atual
`packaging/cs2_analyzer_win.spec` **nao** inclui uma entrada `models/` em sua
lista `datas`, portanto os niveis factory so se resolvem quando um build inclui
explicitamente os checkpoints.

## Pontos de Integracao

| Consumidor | Checkpoint | Operacao |
|------------|-----------|----------|
| `backend/nn/training_orchestrator.py` | `jepa_brain.pt`, `vl_jepa_brain.pt`, `rap_coach.pt` (+ variantes `_latest`) | Carregamento/salvamento com tratamento de `StaleCheckpointError`; unico escritor para os treinamentos orquestrados |
| `backend/nn/coach_manager.py` | `latest.pt` | Salvamento de modelos globais/usuario; carregamento para inferencia |
| `backend/nn/role_head.py` | `role_head.pt` | Salvamento/carregamento via `save_nn()` / `load_nn()` |
| `backend/nn/jepa_train.py` | `jepa_model.pt`, `jepa_model_finetuned.pt` | Pipeline standalone de dois estagios (formato de checkpoint proprio) |
| `backend/nn/win_probability_trainer.py` | caminho fornecido pelo chamador | Utilitario offline (`torch.save` bruto, atualmente nao chamado) |

## Notas de Desenvolvimento

- **NAO commitar arquivos `.pt`** no repositorio -- sao artefatos binarios de grande porte
- O diretorio `global/` deve existir no repositorio (preservado por `README.txt`)
- Logs de treinamento sao escritos por `backend/nn/training_monitor.py` (formato JSON), nao armazenados aqui
- O caminho `MODELS_DIR` e resolvido de `core/config.py` e o padrao e este diretorio
- Quando `BRAIN_DATA_ROOT` (ou, como fallback, `CUSTOM_STORAGE_PATH`) esta definido e existe,
  os modelos sao escritos em `{BRAIN_DATA_ROOT}/models/`
- `checkpoint_hashes.json` e indexado por caminho absoluto do checkpoint; as entradas foram
  registradas durante execucoes de treinamento em varios volumes de armazenamento locais
- Sempre usar `save_nn()` / `load_nn()` de `persistence.py` -- nunca chamar `torch.save()` diretamente
- Apos mudancas na arquitetura do modelo, deletar checkpoints obsoletos e re-treinar do zero

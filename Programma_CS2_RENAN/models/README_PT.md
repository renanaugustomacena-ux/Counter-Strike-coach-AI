> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Models — Armazenamento de Checkpoints de Redes Neurais

> **Autoridade:** Regra 4 (Persistencia de Dados)

Este diretorio armazena checkpoints de redes neurais treinadas (arquivos `.pt`)
usados pelo Ghost Engine para inferencia em tempo real e pelo pipeline de coaching
para geracao de conselhos aprimorados por ML. Os checkpoints sao serializacoes
binarias `state_dict` do PyTorch gerenciadas exclusivamente pelo modulo
`persistence.py`, que impoe escritas atomicas, carregamento multi-fallback e
validacao dimensional rigorosa.

Nenhum arquivo `.pt` e commitado no repositorio. Este diretorio existe no controle
de versao unicamente para preservar sua estrutura (via `global/README.txt`) e para
servir como destino de escrita padrao quando `BRAIN_DATA_ROOT` nao esta configurado.

## Estrutura do Diretorio

```
models/
├── global/                   # Modelos baseline compartilhados (nao especificos por usuario)
│   └── README.txt           # Placeholder para preservar o diretorio no git
├── README.md                 # Este arquivo (Ingles)
├── README_IT.md              # Traducao Italiana
└── README_PT.md              # Traducao Portuguesa
```

Em tempo de execucao, modelos ajustados por usuario sao armazenados em subdiretorios por usuario:

```
models/
├── global/                  # Baseline compartilhada (de treinamento com demos profissionais)
│   ├── jepa_brain.pt       # JEPA pre-treinado em partidas profissionais
│   ├── rap_coach.pt        # Checkpoint do modelo RAP
│   └── win_prob.pt         # Modelo de probabilidade de vitoria
└── {user_id}/               # Modelos ajustados por usuario (futuro)
    └── jepa_brain.pt       # Checkpoint JEPA adaptado ao usuario
```

## Inventario de Checkpoints

| Checkpoint | Classe do Modelo | Criado Por | Tamanho Tipico | Input Dim |
|-----------|-----------------|-----------|----------------|-----------|
| `jepa_brain.pt` | JEPACoachingModel | `backend/nn/jepa_trainer.py` | ~3.6 MB | 25 (METADATA_DIM) |
| `rap_coach.pt` | RAPCoachModel | `backend/nn/experimental/rap_coach/trainer.py` | Variavel | 25 (METADATA_DIM) |
| `coach_brain.pt` | AdvancedCoachNN (legacy) | `backend/nn/train.py` | ~1 MB | 25 (METADATA_DIM) |
| `win_prob.pt` | WinProbabilityTrainerNN | `backend/nn/win_probability_trainer.py` | ~100 KB | 9 (subconjunto offline) |
| `role_head.pt` | NeuralRoleHead | Treinamento de classificacao de funcoes | ~50 KB | Variavel |

## Formato dos Checkpoints

Cada arquivo `.pt` e um dicionario `state_dict` do PyTorch salvo via `torch.save()`.
As chaves correspondem aos parametros nomeados da classe do modelo. Estrutura de
exemplo para `jepa_brain.pt`:

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

O modulo `backend/nn/persistence.py` e a **unica** interface para I/O de
checkpoints. Chamadas diretas a `torch.save()` / `torch.load()` de outros modulos
sao proibidas.

### Protocolo de Escrita Atomica

```
save_nn(model, version, user_id=None)
  1. Resolver o caminho destino: models/{user_id ou "global"}/{version}.pt
  2. Escrever em arquivo temporario: {version}.pt.tmp
  3. Substituicao atomica: tmp_path.replace(path)  # atomico em POSIX
  4. Em caso de falha: remover tmp, re-levantar excecao
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
| NN-MEM-01 | Hopfield bypassado ate >=2 forward passes de treinamento | Propagacao NaN na memoria RAP |
| — | `WinProbabilityNN` (12 features) vs `WinProbabilityTrainerNN` (9 features) | Crash por cross-loading ou corrupcao silenciosa |

`WinProbabilityNN` (producao, 12 features) e `WinProbabilityTrainerNN`
(treinamento offline, 9 features) usam **arquiteturas diferentes**. Seus
checkpoints nao sao intercambiaveis. Nunca cruze o carregamento entre eles.

Apos qualquer mudanca arquitetural (modificacao de `METADATA_DIM`, `HIDDEN_DIM`,
`OUTPUT_DIM` ou estrutura de camadas), todos os checkpoints existentes se tornam
invalidos. O sistema detecta isso automaticamente via carregamento `strict=True` e
levanta `StaleCheckpointError`.

## Versionamento de Modelos

Os checkpoints sao versionados implicitamente pelo seu nome de arquivo (parametro
`version` em `save_nn` / `load_nn`). Nao existe um numero de versao explicito
embutido no checkpoint. A compatibilidade e imposta estruturalmente: se as chaves
do `state_dict` ou os formatos dos tensores nao correspondem a classe do modelo
atual, o carregamento falha deterministicamente.

| String de Versao | Modelo | Fonte de Treinamento |
|-----------------|--------|----------------------|
| `jepa_brain` | JEPACoachingModel | Dataset de demos profissionais (treinamento JEPA em dois estagios) |
| `rap_coach` | RAPCoachModel | Dataset de demos profissionais (treinamento RAP LTC-Hopfield) |
| `coach_brain` | AdvancedCoachNN | Pipeline de treinamento legacy |
| `win_prob` | WinProbabilityTrainerNN | Dataset de resultados de rounds |
| `role_head` | NeuralRoleHead | Dataset de classificacao de funcoes |

## Bundling (PyInstaller)

O subdiretorio `global/` e incluido no executavel congelado:

```python
# Em cs2_analyzer_win.spec
datas += [('models/global', 'models/global')]
```

Em tempo de execucao, `get_factory_model_path()` resolve os checkpoints inclusos
atraves de `get_resource_path()`, que verifica `sys._MEIPASS` para o ambiente congelado.

## Pontos de Integracao

| Consumidor | Checkpoint | Operacao |
|------------|-----------|----------|
| `backend/nn/jepa_trainer.py` | `jepa_brain.pt` | Escrita apos epoca de treinamento |
| `backend/nn/coach_manager.py` | `jepa_brain.pt`, `coach_brain.pt` | Carregamento para inferencia |
| `backend/nn/training_orchestrator.py` | Todos | Carregamento/salvamento com tratamento de `StaleCheckpointError` |
| `backend/nn/experimental/rap_coach/trainer.py` | `rap_coach.pt` | Escrita apos treinamento RAP |
| `backend/nn/win_probability_trainer.py` | `win_prob.pt` | Escrita apos treinamento win-prob |

## Notas de Desenvolvimento

- **NAO commitar arquivos `.pt`** no repositorio — sao artefatos binarios de grande porte
- O diretorio `global/` deve existir no repositorio (preservado por `README.txt`)
- Logs de treinamento sao escritos por `backend/nn/training_monitor.py` (formato JSON), nao armazenados aqui
- O caminho `MODELS_DIR` e resolvido de `core/config.py` e o padrao e este diretorio
- Quando `BRAIN_DATA_ROOT` esta definido, os modelos sao escritos em `{BRAIN_DATA_ROOT}/models/`
- Sempre usar `save_nn()` / `load_nn()` de `persistence.py` — nunca chamar `torch.save()` diretamente
- Apos mudancas na arquitetura do modelo, deletar checkpoints obsoletos e re-treinar do zero

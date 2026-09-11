> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Programma_CS2_RENAN — Pacote Principal da Aplicação

> **Autoridade:** Todas as Regras (Raiz do Pacote)

Pacote principal da aplicação Macena CS2 Analyzer — um coach tático com inteligência artificial para Counter-Strike 2. Este pacote contém todo o código da aplicação organizado em uma arquitetura em camadas.

## O Pipeline OBSERVA > APRENDE > PENSA > FALA

Todo o sistema segue um pipeline de quatro estágios que transforma dados brutos de demos em conselhos táticos acionáveis:

```
OBSERVA (Ingestão) →  APRENDE (Treinamento) →  PENSA (Inferência) →  FALA (Diálogo)
    Daemon Scanner       Daemon Teacher            Pipeline COPER       Template + Ollama
    Parsing de demos     Maturidade em 3 estágios  Conhecimento RAG     Atribuição causal
    Extração de features Treinamento multi-modelo   Teoria dos jogos     Comparações com pros
```

### Estágio 1: OBSERVA (Ingestão)
- O **daemon Scanner** monitora os diretórios de demos de usuário e pro e enfileira novos arquivos `.dem`
- O **hunter service** (`hltv_sync_service.py`, supervisionado pelo Console do backend) faz scraping de estatísticas de jogadores profissionais do hltv.org
- O **daemon Digester** faz o parsing de arquivos `.dem` via demoparser2 e extrai o vetor de features de 25 dimensões
- Os dados brutos de ticks são armazenados em bancos de dados SQLite por partida

### Estágio 2: APRENDE (Treinamento)
- O **daemon Teacher** treina modelos neurais com os dados ingeridos
- Controle de maturidade em 3 estágios: CALIBRATING (0-49 demos) → LEARNING (50-199) → MATURE (200+)
- Modelos: JEPA (auto-supervisionado), RAP Coach (percepção/memória/estratégia/pedagogia), NeuralRoleHead, Win Probability

### Estágio 3: PENSA (Inferência)
- Pipeline de coaching COPER: Context + Observation + Pro Reference + Experience + Reasoning
- Motores de teoria dos jogos: modelos de crença, rastreamento de momentum, otimização de economia
- Recuperação de conhecimento RAG a partir de documentos de coaching tático

### Estágio 4: FALA (Diálogo)
- Coaching baseado em templates com atribuição causal
- Polimento LLM opcional via Ollama para saída em linguagem natural
- Comparações com jogadores profissionais e acompanhamento longitudinal de progresso

## Estrutura do Pacote

```
Programma_CS2_RENAN/
├── apps/                       # Camada de interface do usuário
│   ├── qt_app/                 # UI desktop PySide6/Qt (primária, MVVM)
├── backend/                    # Camada de lógica de negócios
│   ├── analysis/               # Teoria dos jogos, modelos de crença, momentum (11 motores)
│   ├── coaching/               # Pipeline de coaching (COPER, Híbrido, RAG, Neural)
│   ├── control/                # Ciclo de vida dos daemons, fila de ingestão, controle ML
│   ├── data_sources/           # Parser de demos, estatísticas pro HLTV, Steam, APIs Faceit
│   ├── ingestion/              # Monitoramento de arquivos em tempo real, governança de recursos
│   ├── knowledge/              # Base de conhecimento RAG, banco de experiências COPER
│   ├── knowledge_base/         # Sistema de ajuda in-app
│   ├── nn/                     # Redes neurais (6 arquiteturas de modelo)
│   ├── onboarding/             # Rastreamento de progressão de novos usuários
│   ├── processing/             # Feature engineering (vetor 25-dim), baselines
│   ├── progress/               # Rastreamento de progresso de treinamento
│   ├── reporting/              # Consultas analíticas para a UI
│   ├── services/               # Camada de orquestração de serviços (11 módulos de serviço)
│   └── storage/                # Persistência SQLite, modelos, backup
├── core/                       # Fundação runtime
│   ├── session_engine.py       # Motor Quad-Daemon (Scanner, Digester, Teacher, Pulse)
│   ├── config.py               # Sistema de configuração (resolução em 3 níveis)
│   ├── spatial_data.py         # Inteligência espacial de mapas (9 mapas competitivos)
│   ├── known_maps.py           # SSOT de mapa conhecido (lista autoritativa única)
│   ├── map_manager.py          # Gerenciamento de assets de mapas
│   └── lifecycle.py            # Inicialização/encerramento controlado
├── ingestion/                  # Orquestração de ingestão de demos
│   ├── pipelines/              # Pipelines de demos de usuário e tournament-JSON
│   └── registry/               # Rastreamento e ciclo de vida de arquivos de demo
├── observability/              # Proteção e monitoramento runtime
│   ├── rasp.py                 # Guarda de integridade RASP
│   ├── logger_setup.py         # Logging estruturado JSON
│   └── sentry_setup.py         # Rastreamento de erros Sentry
├── reporting/                  # Visualização e relatórios
│   ├── visualizer.py           # Heatmaps, overlays diferenciais, momentos críticos
│   └── report_generator.py     # Relatórios Markdown das partidas
├── assets/                     # Assets estáticos (i18n, mapas)
├── data/                       # Dados runtime (demos, conhecimento, configurações)
├── logs/                       # Saída de logs runtime (cs2_analyzer.log)
├── migrations/                 # Ambiente de migração Alembic (env.py, script.py.mako)
├── models/                     # Checkpoints de modelos treinados
├── PHOTO_GUI/                  # Assets de tema e fontes runtime (temas cs16/csgo/cs2, mapas)
├── runs/                       # Logs de treinamento TensorBoard
├── tactics/                    # Metadados táticos de mapas (JSON)
├── tests/                      # Suíte de testes (mais de 2.500 definições de função de teste em 182 arquivos)
├── tools/                      # Ferramentas de validação a nível de pacote
├── __init__.py                 # Init do pacote (__version__ = "1.0.0")
├── run_ingestion.py            # Ponto de entrada para ingestão de demos
├── run_worker.py               # Worker de ingestão em background (recuperação de tasks stale)
├── settings.json               # Padrões legacy de tema/caminho de demo (lido por tools/Goliath_Hospital.py)
└── hltv_sync_service.py        # Daemon de sincronização HLTV em background
```

## Pontos de Entrada Principais

| Arquivo | Propósito | Como Executar |
|---------|-----------|---------------|
| `apps/qt_app/app.py` | Aplicação desktop (GUI Qt, primária) | `python -m Programma_CS2_RENAN.apps.qt_app.app` |
| `run_ingestion.py` | Pipeline de ingestão de demos | `python -m Programma_CS2_RENAN.run_ingestion` |
| `run_worker.py` | Worker de ingestão em background (recuperação de tasks stale) | `python -m Programma_CS2_RENAN.run_worker` |
| `hltv_sync_service.py` | Sincronização HLTV em background (serviço "hunter") | Iniciado como subprocesso separado pelo ServiceSupervisor (`backend/control/console.py`) |

## Stack Tecnológico

| Camada | Tecnologia |
|--------|-----------|
| UI Primária | PySide6/Qt (padrão MVVM, 15 telas, 10 ViewModels) |
| Framework ML | PyTorch, ncps (neurônios Liquid Time-Constant), hopfield-layers (memória associativa Hopfield) |
| Banco de Dados | SQLite (modo WAL) via SQLModel/SQLAlchemy |
| Parsing de Demos | demoparser2 (baseado em Rust, alta performance) |
| Estatísticas Pro | BeautifulSoup4 + FlareSolverr/Docker (scraping HLTV) |
| Conhecimento | Sentence-BERT (384-dim) + FAISS (busca por similaridade) |
| Observabilidade | TensorBoard, Sentry, logging estruturado JSON |
| Polimento LLM | Ollama (opcional, inferência local) |

## Constantes Críticas

| Constante | Valor | Fonte |
|-----------|-------|-------|
| `METADATA_DIM` | 25 | `backend/processing/feature_engineering/vectorizer.py` |
| `INPUT_DIM` | 25 | `backend/nn/config.py` |
| `OUTPUT_DIM` | 10 | `backend/nn/config.py` |
| `HIDDEN_DIM` | 128 | `backend/nn/config.py` |
| `GLOBAL_SEED` | 42 | `backend/nn/config.py` |
| `BATCH_SIZE` | 32 | `backend/nn/config.py` |

## Notas de Desenvolvimento

- Padrão de importação: `from Programma_CS2_RENAN.backend.nn.config import ...`
- O pacote utiliza importações lazy para evitar dependências circulares (especialmente config↔logger)
- Dependências ML opcionais (ncps, hflayers) usam try/except na importação com verificações em runtime
- A `__version__` em `__init__.py` deve corresponder a `pyproject.toml` e `windows_installer.iss`
- Execute `python tools/headless_validator.py` a partir da raiz do projeto após qualquer alteração
- Todo o logging utiliza `get_logger("cs2analyzer.<modulo>")` para saída JSON estruturada

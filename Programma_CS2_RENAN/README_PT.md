> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Programma_CS2_RENAN — Pacote Principal da Aplicacao

> **Autoridade:** Todas as Regras (Raiz do Pacote)

Pacote principal da aplicacao Macena CS2 Analyzer — um coach tatico com inteligencia artificial para Counter-Strike 2. Este pacote contem todo o codigo da aplicacao organizado em uma arquitetura em camadas.

## O Pipeline OBSERVA > APRENDE > PENSA > FALA

Todo o sistema segue um pipeline de quatro estagios que transforma dados brutos de demos em conselhos taticos acionaveis:

```
OBSERVA (Ingestao) →  APRENDE (Treinamento) →  PENSA (Inferencia) →  FALA (Dialogo)
    Daemon Hunter        Daemon Teacher            Pipeline COPER       Template + Ollama
    Parsing de demos     Maturidade em 3 estagios  Conhecimento RAG     Atribuicao causal
    Extracao de features Treinamento multi-modelo   Teoria dos jogos     Comparacoes com pros
```

### Estagio 1: OBSERVA (Ingestao)
- O **daemon Hunter** coleta estatisticas de jogadores profissionais do hltv.org
- O **daemon Digester** faz o parsing de arquivos `.dem` via demoparser2 e extrai o vetor de features de 25 dimensoes
- Os dados brutos de ticks sao armazenados em bancos de dados SQLite por partida

### Estagio 2: APRENDE (Treinamento)
- O **daemon Teacher** treina modelos neurais com os dados ingeridos
- Controle de maturidade em 3 estagios: CALIBRATING (0-49 demos) → LEARNING (50-199) → MATURE (200+)
- Modelos: JEPA (auto-supervisionado), RAP Coach (pedagogico de 7 camadas), NeuralRoleHead, Win Probability

### Estagio 3: PENSA (Inferencia)
- Pipeline de coaching COPER: Context + Observation + Pro Reference + Experience + Reasoning
- Motores de teoria dos jogos: modelos de crenca, rastreamento de momentum, otimizacao de economia
- Recuperacao de conhecimento RAG a partir de documentos de coaching tatico

### Estagio 4: FALA (Dialogo)
- Coaching baseado em templates com atribuicao causal
- Polimento LLM opcional via Ollama para saida em linguagem natural
- Comparacoes com jogadores profissionais e acompanhamento longitudinal de progresso

## Estrutura do Pacote

```
Programma_CS2_RENAN/
├── apps/                       # Camada de interface do usuario
│   ├── qt_app/                 # UI desktop PySide6/Qt (primaria, MVVM)
│   └── desktop_app/            # UI desktop Kivy/KivyMD (legacy fallback)
├── backend/                    # Camada de logica de negocios
│   ├── analysis/               # Teoria dos jogos, modelos de crenca, momentum (11 motores)
│   ├── coaching/               # Pipeline de coaching (COPER, Hibrido, RAG, Neural)
│   ├── control/                # Ciclo de vida dos daemons, fila de ingestao, controle ML
│   ├── data_sources/           # Parser de demos, estatisticas pro HLTV, Steam, APIs Faceit
│   ├── ingestion/              # Monitoramento de arquivos em tempo real, governanca de recursos
│   ├── knowledge/              # Base de conhecimento RAG, banco de experiencias COPER
│   ├── knowledge_base/         # Sistema de ajuda in-app
│   ├── nn/                     # Redes neurais (6 arquiteturas de modelo)
│   ├── onboarding/             # Rastreamento de progressao de novos usuarios
│   ├── processing/             # Feature engineering (vetor 25-dim), baselines
│   ├── progress/               # Rastreamento de progresso de treinamento
│   ├── reporting/              # Consultas analiticas para a UI
│   ├── services/               # Camada de orquestracao de servicos (6 servicos)
│   └── storage/                # Persistencia SQLite, modelos, backup
├── core/                       # Fundacao runtime
│   ├── session_engine.py       # Motor Quad-Daemon (Hunter, Digester, Teacher, Pulse)
│   ├── config.py               # Sistema de configuracao (resolucao em 3 niveis)
│   ├── spatial_data.py         # Inteligencia espacial de mapas (9 mapas competitivos)
│   ├── map_manager.py          # Gerenciamento de assets de mapas
│   └── lifecycle.py            # Inicializacao/encerramento controlado
├── ingestion/                  # Orquestracao de ingestao de demos
│   ├── pipelines/              # Pipelines de demos de usuario e pro
│   ├── registry/               # Rastreamento e ciclo de vida de arquivos de demo
│   └── hltv/                   # Subsistema scraper HLTV
├── observability/              # Protecao e monitoramento runtime
│   ├── rasp.py                 # Guarda de integridade RASP
│   ├── logger_setup.py         # Logging estruturado JSON
│   └── sentry_setup.py         # Rastreamento de erros Sentry
├── reporting/                  # Visualizacao e relatorios
│   ├── visualizer.py           # Heatmaps, mapas de engajamento, graficos de momentum
│   └── report_generator.py     # Relatorios PDF multi-pagina
├── assets/                     # Assets estaticos (i18n, mapas)
├── data/                       # Dados runtime (demos, conhecimento, configuracoes)
├── models/                     # Checkpoints de modelos treinados
├── tests/                      # Suite de testes (1,794+ testes em 89 arquivos)
├── tools/                      # Ferramentas de validacao a nivel de pacote
├── __init__.py                 # Init do pacote (__version__ = "1.0.0")
├── main.py                     # Entry Kivy/KivyMD legacy (protegido por RASP)
├── run_ingestion.py            # Ponto de entrada para ingestao de demos
├── run_worker.py               # Worker de ingestao em background (recuperacao de tasks stale)
└── hltv_sync_service.py        # Daemon de sincronizacao HLTV em background
```

## Pontos de Entrada Principais

| Arquivo | Proposito | Como Executar |
|---------|-----------|---------------|
| `apps/qt_app/app.py` | Aplicacao desktop (GUI Qt, primaria) | `python -m Programma_CS2_RENAN.apps.qt_app.app` |
| `main.py` | Aplicacao desktop (GUI Kivy/KivyMD, fallback legacy) | `python -m Programma_CS2_RENAN.main` |
| `run_ingestion.py` | Pipeline de ingestao de demos | `python -m Programma_CS2_RENAN.run_ingestion` |
| `run_worker.py` | Worker de ingestao em background (recuperacao de tasks stale) | `python -m Programma_CS2_RENAN.run_worker` |
| `hltv_sync_service.py` | Sincronizacao HLTV em background | Iniciado pelo daemon Hunter |

## Stack Tecnologico

| Camada | Tecnologia |
|--------|-----------|
| UI Primaria | PySide6/Qt (padrao MVVM, 13 telas, 7 ViewModels) |
| UI Legacy | Kivy + KivyMD (padrao MVVM, 6 telas) |
| Framework ML | PyTorch, ncps (neuronios Liquid Time-Constant), hflayers (Hopfield) |
| Banco de Dados | SQLite (modo WAL) via SQLModel/SQLAlchemy |
| Parsing de Demos | demoparser2 (baseado em Rust, alta performance) |
| Estatisticas Pro | BeautifulSoup4 + FlareSolverr/Docker (scraping HLTV) |
| Conhecimento | Sentence-BERT (384-dim) + FAISS (busca por similaridade) |
| Observabilidade | TensorBoard, Sentry, logging estruturado JSON |
| Polimento LLM | Ollama (opcional, inferencia local) |

## Constantes Criticas

| Constante | Valor | Fonte |
|-----------|-------|-------|
| `METADATA_DIM` | 25 | `backend/processing/feature_engineering/vectorizer.py` |
| `INPUT_DIM` | 25 | `backend/nn/config.py` |
| `OUTPUT_DIM` | 10 | `backend/nn/config.py` |
| `HIDDEN_DIM` | 128 | `backend/nn/config.py` |
| `GLOBAL_SEED` | 42 | `backend/nn/config.py` |
| `BATCH_SIZE` | 32 | `backend/nn/config.py` |

## Notas de Desenvolvimento

- Padrao de importacao: `from Programma_CS2_RENAN.backend.nn.config import ...`
- O pacote utiliza importacoes lazy para evitar dependencias circulares (especialmente config↔logger)
- Dependencias ML opcionais (ncps, hflayers) usam try/except na importacao com verificacoes em runtime
- A `__version__` em `__init__.py` deve corresponder a `pyproject.toml` e `windows_installer.iss`
- Execute `python tools/headless_validator.py` a partir da raiz do projeto apos qualquer alteracao
- Todo o logging utiliza `get_logger("cs2analyzer.<modulo>")` para saida JSON estruturada

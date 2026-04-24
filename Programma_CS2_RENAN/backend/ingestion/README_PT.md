> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend Ingestion — Monitoramento de Arquivos, Governança de Recursos & Migração CSV

> **Autoridade:** Regra 2 (Soberania do Backend), Regra 4 (Persistência de Dados)
> **Skill:** `/resilience-check`, `/data-lifecycle-review`

Este módulo gerencia a camada de ingestão em tempo de execução: monitoramento de novos arquivos demo em disco, governança de recursos do sistema durante processamento em background e migração de datasets CSV externos para o banco de dados.

**Nota:** Este é distinto do diretório de nível superior `Programma_CS2_RENAN/ingestion/`, que lida com a orquestração da pipeline multi-estágio. Este módulo fornece os componentes de baixo nível.

## Inventário de Arquivos

| Arquivo | Linhas | Finalidade | Classes/Funções Principais |
|---------|--------|-----------|---------------------------|
| `watcher.py` | ~239 | Monitor do filesystem para arquivos `.dem` | `DemoFileHandler(FileSystemEventHandler)`, `IngestionWatcher` |
| `resource_manager.py` | ~201 | Throttling de CPU/RAM para tarefas em background | `ResourceManager` |
| `csv_migrator.py` | ~208 | Importação de CSV externo em tabelas SQLModel | `CSVMigrator` |

## `watcher.py` — Monitor de Arquivos Demo

Utiliza [watchdog](https://github.com/gorakhargosh/watchdog) para observar diretórios configurados em busca de novos arquivos `.dem`.

### Como Funciona

```
Novo arquivo .dem detectado (on_created / on_moved)
        │
        ├── Agenda verificação de estabilidade (intervalo de 1s)
        │       │
        │       ├── Tamanho do arquivo inalterado por 2 verificações consecutivas? ──> Estável
        │       │       │
        │       │       └── Enfileira como IngestionTask no banco de dados
        │       │
        │       └── Ainda em alteração? ──> Re-verificar (máx 120 tentativas / ~30s)
        │
        └── Valida tamanho mínimo (MIN_DEMO_SIZE de demo_format_adapter.py)
```

- **Debouncing de estabilidade:** Previne a leitura de arquivos parcialmente escritos (Steam escreve demos progressivamente)
- **Prevenção de duplicatas:** Verifica se o arquivo já existe na tabela `IngestionTask` antes de enfileirar
- **Distinção Pro/Usuário:** Monitora tanto pastas de demo do usuário (`is_pro_folder=False`) quanto pastas de demo profissionais (`is_pro_folder=True`)

## `resource_manager.py` — Throttling de Carga do Sistema

Impede o daemon Digester de consumir recursos excessivos do sistema durante o parsing em background.

### Limiares de Histerese

```
Uso de CPU (média móvel de 10 segundos com 10 amostras):

  100% ┬───────────────────────────────────
       │        THROTTLE ATIVO
   85% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Início do throttling
       │
   70% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Parada do throttling
       │        OPERAÇÃO NORMAL
    0% ┴───────────────────────────────────
```

- **Histerese** previne o chaveamento rápido on/off próximo ao limiar
- **Suavização:** 10 amostras de CPU em intervalos de 1 segundo → média móvel
- **Override:** Defina a variável de ambiente `HP_MODE=1` para desabilitar o throttling (modo Turbo)
- **Thread-safe:** Locks separados para amostras de CPU e estado de throttle

## `csv_migrator.py` — Importação de Dados Externos

Migra arquivos CSV estatísticos externos para tabelas do banco de dados SQLModel para análises de coaching.

### Fontes de Dados

| Arquivo CSV | Tabela Destino | Conteúdo |
|-------------|---------------|----------|
| `data/external/cs2_playstyle_roles_2024.csv` | `Ext_PlayerPlaystyle` | Probabilidades de papel por jogador |
| CSVs de estatísticas de torneios | `Ext_TeamRoundStats` | Estatísticas de round a nível de torneio |

- **Idempotente:** Seguro para re-executar (verifica dados existentes)
- **Encoding:** UTF-8 com tratamento de BOM
- **Parsing seguro:** `_safe_float()` e `_safe_int()` previnem a propagação de NaN

## Integração

```
                    watcher.py
                        │
                        ├── Enfileira IngestionTask no banco de dados
                        │
                        └── control/ingest_manager.py busca as tarefas
                                │
                                ├── resource_manager.should_throttle()?
                                │       SIM → sleep antes do próximo batch
                                │       NÃO → processa imediatamente
                                │
                                └── data_sources/demo_parser.py analisa o arquivo .dem
```

## Notas de Desenvolvimento

- `watcher.py` requer o pacote `watchdog` (`pip install watchdog`)
- `ResourceManager` é uma classe de utilidade estática — não necessita de instanciação
- `CSVMigrator` estende `DatabaseManager` para acesso às sessões
- A variável de ambiente `HP_MODE` é apenas para desenvolvimento/benchmarking — não para uso em produção
- A verificação de estabilidade de arquivos usa polling de `os.path.getsize()`, não locks do filesystem

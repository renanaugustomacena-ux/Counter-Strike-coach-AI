> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Ferramentas de Projeto no Nível Raiz

> **Autoridade:** Regra 3 (Zero-Regressão), Regra 6 (Governança de Mudanças)
> **Skill:** `/validate`, `/pre-commit`

Ferramentas de projeto no nível raiz para validação, diagnóstico, orquestração de build e manutenção do Macena CS2 Analyzer. A ferramenta mais crítica é o `headless_validator.py`, que é o gate de regressão obrigatório pre-commit.

## Inventário de Arquivos

O diretório contém **55 ferramentas Python** mais o harness `fuzz/` ([README](fuzz/README.md)) e `hltv_stealth_init.js` (snippet de stealth para browser no fetching de HLTV). As mais importantes:

| Arquivo | Finalidade | Categoria |
|---------|-----------|-----------|
| `headless_validator.py` | Gate de regressão com 41 fases de verificação distintas | Validação |
| `dead_code_detector.py` | Módulos órfãos, definições duplicadas, imports obsoletos | Validação |
| `audit_scanner.py` | Auditoria mecânica de subsistemas (LOC, imports, complexidade, TODOs) | Validação |
| `verify_all_safe.py` | Descobre e executa todas as ferramentas seguras (somente leitura), pulando as inseguras/interativas | Validação |
| `portability_test.py` | Verificações de portabilidade multiplataforma | Validação |
| `Feature_Audit.py` | Auditoria de alinhamento de features (parser vs pipeline ML) | Validação |
| `run_console_boot.py` | Verificação de boot via console | Validação |
| `verify_main_boot.py` | Verificação de boot da aplicação principal | Validação |
| `build_pipeline.py` | Orquestração do pipeline de build (5 estágios) | Build |
| `audit_binaries.py` | Integridade de binários pós-build (SHA-256) | Build |
| `db_health_diagnostic.py` | Diagnóstico de saúde do banco de dados (10 seções) | Banco de Dados |
| `migrate_db.py` | DEPRECIADO — patcher pré-Alembic (usar `alembic upgrade head`) | Banco de Dados |
| `reset_pro_data.py` | Reset de dados de jogadores profissionais (idempotente) | Banco de Dados |
| `dev_health.py` | Orquestrador de saúde do desenvolvimento | Manutenção |
| `Sanitize_Project.py` | Sanitização do projeto (remoção de dados locais) | Manutenção |
| `observe_training_cycle.py` | Diagnóstico end-to-end do ciclo de treinamento (aquisição → conhecimento) | Observabilidade |
| `ui_screenshot.py` | Harness de screenshot offscreen para telas reais (dados de fixture) | UI |
| `ui_gallery.py` | Renderer offscreen da galeria de componentes (uma captura por tema) | UI |
| `ui_fixtures.py` | Payloads de fixture frame-realísticos para o harness de UI | UI |
| `test_rap_lite.py` | Teste de integração RAP-Lite (contratos dimensionais) | Testes |
| `test_tactical_pipeline.py` | Teste end-to-end do pipeline do tactical viewer em um .dem real | Testes |
| `validate_coaching_pipeline.py` | Validação end-to-end do pipeline de coaching | Testes |

O restante cobre ingestão de demos profissionais (`ingest_pro_demos.py`), reparo de dados do monolito (`repair_*.py`, `tick_census.py`), recuperação de shards e reconstrução do monolito (`d3_recover_shard_metadata.py`, `rebuild_monolith.py`), auditorias de disco somente leitura (`d4_disk_hygiene_audit.py`), mineração de experiências/estratégias (`mine_coaching_experience.py`, `mine_shard_strategies.py`), seeding de metadados HLTV (`seed_hltv_top_n.py`, `seed_hltv_apply_vision.py`), backfill de datas de partidas e estatísticas de round (`backfill_match_dates.py`, `populate_match_results.py`, `populate_round_stats.py`), exportação CSV elite (`build_elite_csvs.py`), sinalização de ghost-players (`flag_ghost_players.py`), manutenção de jogadores pro (`rescrape_placeholder_pros.py`, `sync_pro_players.py`), merge de demo-pool (`merge_demo_pool.py`), wipe seguro para re-ingestão (`wipe_for_reingest_safe.py`), geração de design tokens (`gen_design_tokens.py`), build web (`build_web.py`), purge de dados RAG padrão (`purge_default_stats_rag.py`), pinning de supply-chain (`sbom_generator.py`, `verify_lock_hashes.py`, `refresh_model_pins.py`, `refresh_compose_digests.py`), varredura de políticas de segurança e drift (`policy_runner.py`, `drift_detector.py`) e avaliações offline (`eval_harness.py`, `coach_answer_eval.py`).

## `headless_validator.py` --- O Gate de Regressão

Esta é a ferramenta mais importante de todo o projeto (~2.900 linhas). Executa **41 fases de verificação distintas** (fases com banner numeradas 1–26 — a Fase 19 não é utilizada — mais sub-fases com letra 3b–3l e 6b–6f; a Fase 9 é a validação tabular de contratos cross-módulo) e deve terminar com código de saída 0 antes de qualquer commit. Também está integrado ao `.pre-commit-config.yaml` como hook pre-push.

### Fases de Validação

| Fase | O Que Verifica |
|------|---------------|
| 1. Environment | A raiz do projeto e diretórios críticos existem |
| 2. Core Imports | Módulos core importam sem erros |
| 3, 3b–3l. Backend Imports | Saúde dos imports por pacote: storage, processing, NN, analysis, coaching, services, knowledge, control, data sources, ingestion & onboarding, ingestion pipelines, reporting & observability |
| 4. Database Schema | O schema do banco de dados em memória corresponde às definições SQLModel |
| 5. Config & Data Files | `map_config.json` válido, tipos de `get_setting()`, METADATA_DIM==25, alinhamento de features |
| 6. ML Smoke | Instanciação do modelo e forward pass |
| 6b–6f. Smoke Sub-phases | Baselines, adaptador de formato de demo, detecção de GPU, pipeline de treinamento, pipeline de coaching |
| 7. UI Components (Headless) | Componentes Qt/PySide6 importam em modo headless |
| 8. Cross-Platform | Caminhos de código específicos do SO resolvem corretamente |
| 9. Cross-Module Contracts | Contratos de APIs públicas correspondem às implementações |
| 10. Deep ML Invariants | METADATA_DIM=25, OUTPUT_DIM=10, formas dos layers |
| 11. Database Model Integrity | Registro de tabelas, colunas, índices |
| 12. Code Quality Scanning | Detecção de anti-patterns (incluindo `print()` soltos) |
| 13. Package Structure & Config | `__init__.py` em todos os pacotes, integridade da configuração |
| 14. Feature Pipeline Consistency | O Vectorizer produz vetores de 25 dimensões |
| 15. Dependency & Environment | Dependências fixadas são importáveis |
| 16. RAP Coach & Perception | Forward pass do modelo RAP e pipeline |
| 17. Belief Model & Analysis Engines | Contratos dos motores de análise, intervalos de probabilidade |
| 18. MLControlContext & Training Control | Encanamento de pause/resume/stop |
| 20. Shared Utilities | Imports de utilidades compartilhadas e módulos ausentes |
| 21. Integrity & Security Scanning | Manifest SHA-256, nenhum segredo hardcoded |
| 22. Configuration Consistency | Schema do arquivo de configurações corresponde às chaves esperadas |
| 23. Advanced Code Quality | Complexidade ciclomática, detecção de código duplicado |
| 24. Qt Frontend Imports | Imports de telas/viewmodels do app Qt |
| 25. Design Token Freshness | Design tokens gerados estão atualizados |
| 26. Web Marquee Scaffold Health | Integridade do scaffold do app web |

### Uso

```bash
# Validação padrão (obrigatória antes de cada commit)
python tools/headless_validator.py

# Código de saída: 0 = todas as verificações passaram, diferente de zero = falhas detectadas
echo $?
```

## Pipeline de Build

### `build_pipeline.py` --- Orquestração de Build em 5 Estágios

```
Estágio 1: Sanitize  ->  Estágio 2: Test  ->  Estágio 3: Manifest  ->  Estágio 4: Compile  ->  Estágio 5: Audit
(limpar artefatos)       (executar testes)    (gerar hashes)          (PyInstaller)           (verificar binário)
```

### `audit_binaries.py` --- Integridade Pós-Build

Calcula hashes SHA-256 de todos os arquivos na saída do build e compara com os valores esperados. Detecta adulterações ou builds incompletos.

## Ferramentas de Banco de Dados

### `db_health_diagnostic.py` --- Diagnóstico em 10 Seções

| Seção | O Que Verifica |
|-------|---------------|
| 1 | Saúde estrutural — schema e restrições |
| 2 | Verificação de integridade — detecção de corrupção (`PRAGMA integrity_check`) |
| 3 | Verificação de modo WAL e journal |
| 4 | Consistência de dados e estabilidade lógica (duplicatas, órfãos, valores impossíveis) |
| 5 | Saúde do pipeline de ingestão (status de tarefas, tarefas travadas, cross-DB) |
| 6 | Saúde de desempenho — cobertura de índices e verificação de full-scan no plano de query |
| 7 | Observabilidade — cobertura de metadados diagnósticos |
| 8 | Banco de dados de estatísticas pro HLTV |
| 9 | Prontidão do pipeline ML — CoachState |
| 10 | Resumo de armazenamento |

### `migrate_db.py` --- DEPRECIADO

Mantido apenas como arquivo histórico (R2-11). Patcha bancos de dados pré-Alembic adicionando 5 colunas ao `CoachState`; esse schema agora é gerenciado pelas revisões Alembic `8c443d3d9523` e `3c6ecb5fe20e`. Use `alembic upgrade head` para todas as migrações de schema.

### `reset_pro_data.py` --- Reset de Dados Profissionais

Reset multi-fase e idempotente para um novo ciclo de ingestão e treinamento. Limpa as tabelas de dados de `database.db` + CoachState, `hltv_metadata.db` (ignorável com `--preserve-hltv`), `knowledge_graph.db`, caches, checkpoints de modelos, shards por partida e estado de sincronização.

## Manutenção do Projeto

### `dev_health.py` --- Orquestrador de Saúde

Executa múltiplas ferramentas em sequência e produz um relatório de saúde unificado:
1. Headless validator (sempre; `--quick` executa apenas este)
2. Dead code detector (`--strict`)
3. Auditoria de alinhamento de features
4. Teste de portabilidade (somente com `--full`)

### `Sanitize_Project.py` --- Limpar Estado Local

Remove todos os dados específicos do usuário e locais para distribuição limpa:
- `Programma_CS2_RENAN/backend/storage/database.db` (banco de dados local principal)
- `Programma_CS2_RENAN/backend/storage/hltv_metadata.db`
- `Programma_CS2_RENAN/backend/storage/match_data/` (shards SQLite por partida)
- `models/` (checkpoints ML)
- diretório `logs/`
- `hltv_sync.pid` obsoleto

## Uso

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Validação headless (executar antes de cada commit)
python tools/headless_validator.py

# Verificação de saúde do desenvolvimento
python tools/dev_health.py

# Verificação de saúde do banco de dados
python tools/db_health_diagnostic.py

# Verificação de portabilidade
python tools/portability_test.py

# Detecção de código morto
python tools/dead_code_detector.py

# Auditoria de alinhamento de features
python tools/Feature_Audit.py

# Pipeline de build
python tools/build_pipeline.py

# Sanitização do projeto (ATENÇÃO: remove dados locais)
python tools/Sanitize_Project.py
```

## Notas de Desenvolvimento

- Todas as ferramentas devem ser executadas a partir do diretório raiz do projeto
- O headless validator é o gate de regressão inegociável --- se falhar, o commit é bloqueado
- Ferramentas de banco de dados são seguras para executar em dados de produção (usam consultas somente leitura, salvo indicação explícita)
- `Sanitize_Project.py` é destrutivo --- remove bancos de dados locais e configurações. Use com cuidado.
- Ferramentas terminam com código 0 em caso de sucesso, diferente de zero em caso de falha
- O orquestrador `dev_health.py` fornece a verificação de saúde mais completa em um único comando

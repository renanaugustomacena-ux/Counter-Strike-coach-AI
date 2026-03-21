> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Suite de Testes

**Autoridade:** `Programma_CS2_RENAN/tests/` -- Suite abrangente de regressao e corretude para o Macena CS2 Analyzer.

A suite de testes contem mais de 1.515 testes distribuidos em 79 arquivos, seguindo a piramide
de testes (unit > integration > e2e). Cada subsistema -- do vetor de features de 25 dimensoes
passando pelas redes neurais, motor de coaching, camada de banco de dados e telas de UI -- e
coberto por assercoes deterministicas e reprodutiveis. Os testes rodam sob pytest com uma guarda
obrigatoria de ambiente virtual e gating opcional para testes de integracao via variavel de
ambiente `CS2_INTEGRATION_TESTS`.

## Principios Fundamentais

- **Nenhum dado mock para logica de dominio** -- Dados DB reais ou `pytest.skip`
- **Mocks apenas em limites I/O** -- Rede, sistema de arquivos, APIs externas
- **Tolerancia zero para dados sinteticos** -- Todo valor deve originar de fontes reais
- **Hierarquia de testes** -- Unit (>70%) > Integration (>20%) > E2E (~10%)
- **Seeding deterministico** -- `GLOBAL_SEED=42` em todo lugar, `torch.manual_seed(42)` nas fixtures

## Inventario de Arquivos

| Arquivo | Dominio | Descricao |
|---------|---------|-----------|
| `conftest.py` | Infraestrutura | Fixtures compartilhadas, guarda venv, estabilizacao de caminhos, marcadores |
| `test_analysis_engines.py` | Analise | Contratos do motor de analise principal |
| `test_analysis_engines_extended.py` | Analise | Cobertura de analise estendida (modelos de crenca, momentum) |
| `test_analysis_gaps.py` | Analise | Analise de lacunas e deteccao de cobertura ausente |
| `test_analysis_orchestrator.py` | Servicos | Testes da pipeline `AnalysisOrchestrator` |
| `test_auto_enqueue.py` | Ingestao | Watcher auto-enqueue para novas demos |
| `test_baselines.py` | Analise | Computacao e decaimento de baseline |
| `test_chronovisor_highlights.py` | Analise | Extracao de highlights `ChronovisorScanner` |
| `test_chronovisor_scanner.py` | Analise | Testes de varredura a nivel de tick do scanner |
| `test_coaching_dialogue.py` | Coaching | Fluxo conversacional do motor de dialogo |
| `test_coaching_engines.py` | Coaching | Motores COPER, hibrido e de correcao |
| `test_coaching_service_contracts.py` | Servicos | Assercoes de contrato API `CoachingService` |
| `test_coaching_service_fallback.py` | Servicos | Degradacao gradual quando backends indisponiveis |
| `test_coaching_service_flows.py` | Servicos | Fluxos end-to-end do servico de coaching |
| `test_coach_manager_flows.py` | Core | Ciclo de vida da sessao `CoachManager` |
| `test_coach_manager_tensors.py` | Core | Validacao de forma de tensores na pipeline coach |
| `test_config_extended.py` | Core | Resolucao `config.py`, overrides, thread safety |
| `test_database_layer.py` | Storage | Modelos ORM, migracoes, enforcement WAL |
| `test_data_pipeline_contracts.py` | Processing | Contratos de entrada/saida da pipeline de features |
| `test_db_backup.py` | Storage | Logica de backup e restauracao de banco de dados |
| `test_db_governor_integration.py` | Storage | Testes de concorrencia do database governor |
| `test_debug_ingestion.py` | Ingestao | Validacao de trace de debug da ingestao |
| `test_demo_format_adapter.py` | Ingestao | Adaptador de formato demo (enforcement MIN_DEMO_SIZE) |
| `test_demo_parser.py` | Ingestao | Integracao `demoparser2` e extracao de ticks |
| `test_dem_validator.py` | Ingestao | Verificacoes de header e integridade de arquivo `.dem` |
| `test_deployment_readiness.py` | Build | Gate de prontidao pre-deployment |
| `test_detonation_overlays.py` | Reporting | Renderizacao de overlays de detonacao de granadas |
| `test_dimension_chain_integration.py` | NN | Propagacao `METADATA_DIM=25` em todos os modelos |
| `test_drift_and_heuristics.py` | Analise | Deteccao de drift estatistico e regras heuristicas |
| `test_experience_bank_db.py` | Knowledge | Persistencia de banco de dados do experience bank |
| `test_experience_bank_logic.py` | Knowledge | Recuperacao e ranking do experience bank |
| `test_feature_extractor_contracts.py` | Processing | Testes de contrato `FeatureExtractor.extract()` |
| `test_feature_kast_roles.py` | Processing | Estimativa KAST e features baseadas em funcao |
| `test_features.py` | Processing | Corretude do vetor de features de 25 dimensoes |
| `test_game_theory.py` | Analise | Modelos de teoria dos jogos (Nash, minimax) |
| `test_game_tree.py` | Analise | Construcao e travessia de arvore de jogo |
| `test_hybrid_engine.py` | Coaching | Logica de fusao do motor de coaching hibrido |
| `test_integration.py` | Integracao | Integracao cross-modulo com DB real |
| `test_jepa_model.py` | NN | Encoder JEPA, coaching head, target encoder EMA |
| `test_knowledge_graph.py` | Knowledge | Consultas do grafo de conhecimento RAG |
| `test_lifecycle.py` | Core | Ciclo de vida da aplicacao (inicializacao, encerramento, recuperacao) |
| `test_map_manager.py` | Core | Geometria de mapas, resolucao de callouts, consultas espaciais |
| `test_model_factory_contracts.py` | NN | Contratos de instanciacao `ModelFactory` |
| `test_models.py` | Storage | Validacao de modelos ORM SQLModel |
| `test_nn_extensions.py` | NN | Neuronios LTC, extensoes de memoria Hopfield |
| `test_nn_infrastructure.py` | NN | Infraestrutura de treinamento (DataLoader, checkpoints) |
| `test_nn_training.py` | NN | Loop de treinamento, convergencia de loss, verificacoes de gradiente |
| `test_observability.py` | Observabilidade | Logging estruturado, correlation IDs, telemetria |
| `test_onboarding.py` | UI | Fluxo do wizard de onboarding |
| `test_onboarding_training.py` | UI | Onboarding em modo de treinamento |
| `test_persistence_stale_checkpoint.py` | NN | Deteccao e recuperacao de checkpoints obsoletos |
| `test_phase0_3_regressions.py` | Regressao | Suite de regressao fases 0-3 |
| `test_playback_engine.py` | Core | Motor de reproducao de ticks |
| `test_pro_demo_miner.py` | Ingestao | Descoberta de demos pro e metadados |
| `test_profile_service.py` | Servicos | CRUD de perfil de jogador |
| `test_qt_core.py` | UI | Testes de widgets core PySide6/Qt |
| `test_rag_knowledge.py` | Knowledge | Recuperacao RAG e indice FAISS |
| `test_rap_coach.py` | NN | Forward pass do modelo RAP, memoria, estados de crenca |
| `test_round_stats_enrichment.py` | Processing | Pipeline de enriquecimento de estatisticas de round |
| `test_round_utils.py` | Processing | Funcoes utilitarias de round |
| `test_security.py` | Seguranca | Shell injection, protecao `.env`, deteccao de segredos |
| `test_services.py` | Servicos | `CoachingService`, `AnalysisService`, `DialogueEngine` |
| `test_session_engine.py` | Core | Ciclo de vida do Quad-Daemon session engine |
| `test_skill_model.py` | NN | Forward pass do skill model e forma de saida |
| `test_spatial_and_baseline.py` | Analise | Motor espacial + integracao baseline |
| `test_spatial_engine.py` | Analise | Transformacoes de coordenadas do motor espacial |
| `test_state_reconstructor.py` | Processing | Reconstrucao de estado RAP a partir de ticks |
| `test_tactical_features.py` | Processing | Extracao de features taticas |
| `test_temporal_baseline.py` | Analise | 20 testes de decaimento de baseline temporal |
| `test_tensor_factory.py` | NN | Contratos de forma e dtype do `TensorFactory` |
| `test_trade_kill_detector.py` | Analise | Logica de deteccao de trade kill |
| `test_training_orchestrator_flows.py` | Servicos | Fluxos end-to-end do orquestrador de treinamento |
| `test_training_orchestrator_logic.py` | Servicos | Logica de decisao do orquestrador de treinamento |
| `test_z_penalty.py` | Processing | Casos limite `compute_z_penalty()` |
| `automated_suite/` | Infraestrutura | Executor de testes automatizado (smoke, unit, funcional, e2e, regressao) |
| `data/` | Infraestrutura | Fixtures de dados de teste e arquivos de exemplo |

## Arquitetura de Fixtures

Todas as fixtures compartilhadas residem em `conftest.py`. A hierarquia e:

```
in_memory_db          -- Schema vazio via SQLModel.metadata.create_all()
  seeded_db_session   -- Pre-populado com 6 PlayerMatchStats, 12 RoundStats, 1 PlayerProfile
    seeded_player_stats  -- Primeiro PlayerMatchStats do DB com seed
    seeded_round_stats   -- Primeiro RoundStats do DB com seed

real_db_session       -- Abre o database.db de producao (pula se ausente)
  real_player_stats   -- Primeiro PlayerMatchStats real (pula se vazio)
  real_round_stats    -- Primeiro RoundStats real (pula se vazio)

mock_db_manager       -- Substituto DatabaseManager em memoria com get_session() / upsert()
isolated_settings     -- Redireciona user_settings.json para tmp_path, restaura no teardown
torch_no_grad         -- Envolve o corpo do teste em um contexto torch.no_grad()
rap_model             -- RAPCoachModel deterministico (CPU, seed=42, modo eval)
rap_inputs            -- Tensores de entrada deterministicos conforme as formas TrainingTensorConfig
```

## Gating de Testes de Integracao

Testes marcados com `@pytest.mark.integration` sao pulados por padrao. Eles leem do `database.db`
de producao e requerem dados reais de demos ingeridas. Para habilita-los:

```bash
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -x -q
```

O hook `pytest_collection_modifyitems` em `conftest.py` aplica automaticamente o marcador de
skip quando a variavel de ambiente nao esta definida.

## Guarda de Ambiente Virtual

A guarda de venv em `conftest.py` impede a execucao de testes fora do ambiente virtual
`cs2analyzer`. Se `sys.prefix == sys.base_prefix` e nem `CI` nem `GITHUB_ACTIONS` estiverem
definidos, o pytest sai imediatamente com codigo de retorno 2. Isso evita falhas de importacao
confusas quando os testes sao executados acidentalmente com o Python do sistema.

## Executando Testes

```bash
# Ativar o ambiente virtual primeiro
source ~/.venvs/cs2analyzer/bin/activate

# Executar todos os testes (parar na primeira falha)
python -m pytest Programma_CS2_RENAN/tests/ -x -q

# Executar um arquivo de teste especifico
python -m pytest Programma_CS2_RENAN/tests/test_features.py -v

# Executar apenas testes de integracao
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -m integration -v

# Executar a suite automatizada
python -m pytest Programma_CS2_RENAN/tests/automated_suite/ -v
```

## Notas de Desenvolvimento

- A fixture `seeded_db_session` fornece dados portaveis para CI que funcionam em qualquer
  maquina sem necessidade de `database.db`. Prefira-a em vez de `real_db_session` para
  novos testes unitarios.
- Testes de redes neurais usam as fixtures `torch_no_grad` e `rap_model` para garantir
  avaliacao deterministica e sem gradientes na CPU.
- A fixture `isolated_settings` cria um snapshot e restaura o dicionario `_settings` em
  memoria para que testes que mutam a configuracao nao poluam testes subsequentes no
  mesmo processo.
- A nomenclatura de arquivos de teste segue `test_<module>.py`; a nomenclatura de classes
  de teste segue `Test<Feature>`; testes individuais seguem `test_<behavior>`.

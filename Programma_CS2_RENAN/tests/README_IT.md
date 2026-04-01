> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Suite di Test

**Autorita:** `Programma_CS2_RENAN/tests/` -- Suite completa di regressione e correttezza per il Macena CS2 Analyzer.

La suite di test contiene oltre 1.794 test distribuiti su 89 file, seguendo la piramide di test
(unit > integration > e2e). Ogni sottosistema -- dal vettore di feature a 25 dimensioni attraverso
le reti neurali, il motore di coaching, il livello database e le schermate UI -- e coperto da
asserzioni deterministiche e riproducibili. I test vengono eseguiti con pytest con una guardia
obbligatoria per l'ambiente virtuale e un gating opzionale per i test di integrazione tramite
la variabile d'ambiente `CS2_INTEGRATION_TESTS`.

## Principi Fondamentali

- **Nessun dato mock per la logica di dominio** -- Dati DB reali o `pytest.skip`
- **Mock solo ai confini I/O** -- Rete, filesystem, API esterne
- **Tolleranza zero per dati sintetici** -- Ogni valore deve provenire da fonti reali
- **Gerarchia di test** -- Unit (>70%) > Integration (>20%) > E2E (~10%)
- **Seeding deterministico** -- `GLOBAL_SEED=42` ovunque, `torch.manual_seed(42)` nelle fixture

## Inventario File

| File | Dominio | Descrizione |
|------|---------|-------------|
| `conftest.py` | Infrastruttura | Fixture condivise, guardia venv, stabilizzazione percorsi, marcatori |
| `test_analysis_engines.py` | Analisi | Contratti del motore di analisi principale |
| `test_analysis_engines_extended.py` | Analisi | Copertura analisi estesa (modelli di credenza, momentum) |
| `test_analysis_gaps.py` | Analisi | Analisi lacune e rilevamento copertura mancante |
| `test_analysis_orchestrator.py` | Servizi | Test della pipeline `AnalysisOrchestrator` |
| `test_auto_enqueue.py` | Ingestione | Watcher auto-enqueue per nuove demo |
| `test_baselines.py` | Analisi | Calcolo e decadimento baseline |
| `test_chronovisor_highlights.py` | Analisi | Estrazione highlight `ChronovisorScanner` |
| `test_chronovisor_scanner.py` | Analisi | Test di sweep a livello tick dello scanner |
| `test_coaching_dialogue.py` | Coaching | Flusso conversazionale del motore di dialogo |
| `test_coaching_engines.py` | Coaching | Motori COPER, ibrido e di correzione |
| `test_coaching_service_contracts.py` | Servizi | Asserzioni sul contratto API `CoachingService` |
| `test_coaching_service_fallback.py` | Servizi | Degradazione graduale quando i backend non sono disponibili |
| `test_coaching_service_flows.py` | Servizi | Flussi end-to-end del servizio di coaching |
| `test_coach_manager_flows.py` | Core | Ciclo di vita sessione `CoachManager` |
| `test_coach_manager_tensors.py` | Core | Validazione forma tensori nella pipeline coach |
| `test_config_extended.py` | Core | Risoluzione `config.py`, override, thread safety |
| `test_config_resolution.py` | Core | Test della gerarchia di risoluzione configurazione |
| `test_coper_pathway.py` | Coaching | Catena end-to-end del percorso coaching COPER |
| `test_database_layer.py` | Storage | Modelli ORM, migrazioni, enforcement WAL |
| `test_database_wal_enforcement.py` | Storage | Test di enforcement della modalita WAL |
| `test_data_pipeline_contracts.py` | Processing | Contratti input/output della pipeline feature |
| `test_db_backup.py` | Storage | Logica di backup e ripristino database |
| `test_db_governor_integration.py` | Storage | Test di concorrenza del database governor |
| `test_debug_ingestion.py` | Ingestione | Validazione trace di debug dell'ingestione |
| `test_demo_format_adapter.py` | Ingestione | Adattatore formato demo (enforcement MIN_DEMO_SIZE) |
| `test_demo_parser.py` | Ingestione | Integrazione `demoparser2` ed estrazione tick |
| `test_dem_validator.py` | Ingestione | Controlli header e integrita file `.dem` |
| `test_deployment_readiness.py` | Build | Gate di prontezza pre-deployment |
| `test_detonation_overlays.py` | Reporting | Rendering overlay detonazioni granate |
| `test_dimension_chain_integration.py` | NN | Propagazione `METADATA_DIM=25` su tutti i modelli |
| `test_drift_and_heuristics.py` | Analisi | Rilevamento drift statistico e regole euristiche |
| `test_experience_bank_db.py` | Knowledge | Persistenza database experience bank |
| `test_experience_bank_logic.py` | Knowledge | Recupero e ranking experience bank |
| `test_feature_extractor_contracts.py` | Processing | Test contratto `FeatureExtractor.extract()` |
| `test_feature_kast_roles.py` | Processing | Stima KAST e feature basate sui ruoli |
| `test_features.py` | Processing | Correttezza vettore feature a 25 dimensioni |
| `test_game_theory.py` | Analisi | Modelli teoria dei giochi (Nash, minimax) |
| `test_game_tree.py` | Analisi | Costruzione e attraversamento albero di gioco |
| `test_hybrid_engine.py` | Coaching | Logica di fusione motore coaching ibrido |
| `test_ingestion_pipeline.py` | Ingestione | Test di integrazione della pipeline di ingestione |
| `test_integration.py` | Integrazione | Integrazione cross-modulo con DB reale |
| `test_jepa_model.py` | NN | Encoder JEPA, coaching head, target encoder EMA |
| `test_jepa_training_pipeline.py` | NN | Test della pipeline di training JEPA |
| `test_knowledge_graph.py` | Knowledge | Query del grafo di conoscenza RAG |
| `test_lifecycle.py` | Core | Ciclo di vita applicazione (avvio, arresto, recupero) |
| `test_map_manager.py` | Core | Geometria mappe, risoluzione callout, query spaziali |
| `test_model_factory_contracts.py` | NN | Contratti di istanziazione `ModelFactory` |
| `test_models.py` | Storage | Validazione modelli ORM SQLModel |
| `test_nn_config_reproducibility.py` | NN | Test di riproducibilita configurazione reti neurali |
| `test_nn_extensions.py` | NN | Neuroni LTC, estensioni memoria Hopfield |
| `test_nn_infrastructure.py` | NN | Infrastruttura training (DataLoader, checkpoint) |
| `test_nn_training.py` | NN | Loop di training, convergenza loss, controlli gradienti |
| `test_observability.py` | Osservabilita | Logging strutturato, correlation ID, telemetria |
| `test_onboarding.py` | UI | Flusso wizard di onboarding |
| `test_onboarding_training.py` | UI | Onboarding in modalita training |
| `test_persistence_stale_checkpoint.py` | NN | Rilevamento e recupero checkpoint obsoleti |
| `test_phase0_3_regressions.py` | Regressione | Suite di regressione fasi 0-3 |
| `test_playback_engine.py` | Core | Motore di riproduzione tick |
| `test_pro_demo_miner.py` | Ingestione | Scoperta demo pro e metadati |
| `test_profile_service.py` | Servizi | CRUD profilo giocatore |
| `test_qt_core.py` | UI | Test widget core PySide6/Qt |
| `test_rag_knowledge.py` | Knowledge | Recupero RAG e indice FAISS |
| `test_rap_coach.py` | NN | Forward pass modello RAP, memoria, stati di credenza |
| `test_round_stats_enrichment.py` | Processing | Pipeline di arricchimento statistiche round |
| `test_round_utils.py` | Processing | Funzioni utilita round |
| `test_security.py` | Sicurezza | Shell injection, protezione `.env`, rilevamento segreti |
| `test_services.py` | Servizi | `CoachingService`, `AnalysisService`, `DialogueEngine` |
| `test_session_engine.py` | Core | Ciclo di vita Quad-Daemon session engine |
| `test_skill_assessment.py` | NN | Test del modulo di valutazione competenze |
| `test_skill_model.py` | NN | Forward pass skill model e forma output |
| `test_spatial_and_baseline.py` | Analisi | Motore spaziale + integrazione baseline |
| `test_spatial_engine.py` | Analisi | Trasformazioni coordinate motore spaziale |
| `test_state_reconstructor.py` | Processing | Ricostruzione stato RAP da tick |
| `test_tactical_features.py` | Processing | Estrazione feature tattiche |
| `test_temporal_baseline.py` | Analisi | 20 test di decadimento baseline temporale |
| `test_tensor_factory.py` | NN | Contratti forma e dtype `TensorFactory` |
| `test_trade_kill_detector.py` | Analisi | Logica rilevamento trade kill |
| `test_training_callbacks.py` | NN | Test del registro callback di training |
| `test_training_orchestrator_flows.py` | Servizi | Flussi end-to-end dell'orchestratore di training |
| `test_training_orchestrator_logic.py` | Servizi | Logica decisionale dell'orchestratore di training |
| `test_v1_blockers.py` | Regressione | Fix dei bloccanti per prontezza produzione V1 |
| `test_z_penalty.py` | Processing | Casi limite `compute_z_penalty()` |
| `automated_suite/` | Infrastruttura | Esecutore test automatizzato (smoke, unit, funzionale, e2e, regressione) |
| `data/` | Infrastruttura | Fixture dati di test e file di esempio |

## Architettura delle Fixture

Tutte le fixture condivise risiedono in `conftest.py`. La gerarchia e:

```
in_memory_db          -- Schema vuoto tramite SQLModel.metadata.create_all()
  seeded_db_session   -- Pre-popolato con 6 PlayerMatchStats, 12 RoundStats, 1 PlayerProfile
    seeded_player_stats  -- Primo PlayerMatchStats dal DB con seed
    seeded_round_stats   -- Primo RoundStats dal DB con seed

real_db_session       -- Apre il database.db di produzione (salta se assente)
  real_player_stats   -- Primo PlayerMatchStats reale (salta se vuoto)
  real_round_stats    -- Primo RoundStats reale (salta se vuoto)

mock_db_manager       -- Sostituto DatabaseManager in-memory con get_session() / upsert()
isolated_settings     -- Reindirizza user_settings.json a tmp_path, ripristina al teardown
torch_no_grad         -- Avvolge il corpo del test in un contesto torch.no_grad()
rap_model             -- RAPCoachModel deterministico (CPU, seed=42, modalita eval)
rap_inputs            -- Tensori di input deterministici conformi alle forme TrainingTensorConfig
```

## Gating dei Test di Integrazione

I test marcati `@pytest.mark.integration` sono saltati per impostazione predefinita. Leggono dal
`database.db` di produzione e richiedono dati demo reali ingeriti. Per abilitarli:

```bash
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -x -q
```

L'hook `pytest_collection_modifyitems` in `conftest.py` applica automaticamente il marcatore di
skip quando la variabile d'ambiente non e impostata.

## Guardia Ambiente Virtuale

La guardia venv in `conftest.py` impedisce l'esecuzione dei test al di fuori dell'ambiente
virtuale `cs2analyzer`. Se `sys.prefix == sys.base_prefix` e ne `CI` ne `GITHUB_ACTIONS` sono
impostati, pytest esce immediatamente con codice di ritorno 2. Questo evita errori di importazione
confusi quando i test vengono eseguiti accidentalmente con il Python di sistema.

## Esecuzione dei Test

```bash
# Attivare prima l'ambiente virtuale
source ~/.venvs/cs2analyzer/bin/activate

# Eseguire tutti i test (fermarsi al primo fallimento)
python -m pytest Programma_CS2_RENAN/tests/ -x -q

# Eseguire un file di test specifico
python -m pytest Programma_CS2_RENAN/tests/test_features.py -v

# Eseguire solo i test di integrazione
CS2_INTEGRATION_TESTS=1 python -m pytest Programma_CS2_RENAN/tests/ -m integration -v

# Eseguire la suite automatizzata
python -m pytest Programma_CS2_RENAN/tests/automated_suite/ -v
```

## Note di Sviluppo

- La fixture `seeded_db_session` fornisce dati portabili per CI che funzionano su qualsiasi
  macchina senza richiedere `database.db`. Preferirla rispetto a `real_db_session` per i
  nuovi unit test.
- I test delle reti neurali usano le fixture `torch_no_grad` e `rap_model` per garantire
  una valutazione deterministica e senza gradienti su CPU.
- La fixture `isolated_settings` crea uno snapshot e ripristina il dizionario `_settings`
  in memoria in modo che i test che mutano la configurazione non inquinino i test successivi
  nello stesso processo.
- La nomenclatura dei file di test segue `test_<module>.py`; la nomenclatura delle classi
  di test segue `Test<Feature>`; i singoli test seguono `test_<behavior>`.

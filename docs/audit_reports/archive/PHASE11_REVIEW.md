> **STATUS: COMPLETED (2026-03-08)**
> All action items (A1-A4) executed during Phase 11. This document is retained for audit trail.

# Piano: Revisione Completa + Rinforzo Test Prima di Phase 12

> **Data:** 2026-03-07
> **Fase:** Post-Phase 11, Pre-Phase 12
> **Scopo:** Audit completo del lavoro Fasi 0-11 + colmare gap nella test suite

---

## Contesto

Prima di procedere alla Phase 12 (Final QA & Release Gate), è stata condotta una revisione completa di tutto il lavoro fatto nelle Fasi 0-11. L'audit ha rivelato che **il validatore headless (294/298 PASS) è un gate strutturale/smoke, NON un validatore di correttezza comportamentale**. Le ottimizzazioni Phase 11 (e molte fix precedenti) non sono testate a livello logico.

---

## Risultati dell'Audit

### Headless Validator — Cosa testa DAVVERO
- **Import integrity**: 290+ moduli si caricano senza errori
- **Schema DB**: le tabelle esistono
- **Configurazione**: file JSON validi, costanti allineate (METADATA_DIM == INPUT_DIM)
- **Contratti**: classi hanno i metodi attesi (hasattr checks)
- **Code quality statica**: no bare except, no torch.load insicuro, no eval/exec
- **ML smoke**: modelli si istanziano, forward pass non crasha

### Headless Validator — Cosa NON testa
- ❌ Correttezza algoritmica (output corretto per input noto)
- ❌ Ottimizzazioni performance (vectorizzazione effettiva, memoizzazione attiva)
- ❌ Flusso dati end-to-end (pipeline completa)
- ❌ Edge case e boundary condition
- ❌ Correttezza numerica (valori di output verificati)

### Gap Critici nella Test Suite

**Statistiche globali:** 79 file test, ~1785 test method, coverage baseline 30%

| Modulo Modificato (Phase 11) | Test Dedicato | Stato |
|---|---|---|
| `heatmap_engine.py` (P11-01: vectorizzazione) | **NESSUNO** | ❌ Gap CRITICO |
| `game_tree.py` (P11-02: transposition table) | `test_game_tree.py` (552 righe, ~70 test) | ⚠️ Buona base, MA manca test TT |
| `deception_index.py` (P11-03: searchsorted) | `test_analysis_gaps.py` (parziale) | ⚠️ Solo factory/costanti |
| `player_knowledge.py` (P11-04: pre-index) | **NESSUNO diretto** | ❌ Gap CRITICO |

### CI/CD — Stato
- ✅ Pipeline 4-stage (Lint → Unit → Integration → Security) ben configurata
- ✅ Pre-commit: 13 hook tutti compatibili
- ✅ Coverage threshold: 30% (baseline funzionale)
- ⚠️ Integrity manifest necessita rigenerazione prima del commit
- ⚠️ Security stage non-bloccante (|| true)

---

## Piano di Azione

### Fase A: Test Comportamentali per Phase 11

#### A1. `test_heatmap_engine.py` (NUOVO — Gap critico)
- Test vectorizzazione: confronto output loop Python vs `np.add.at`
- Test boundary: punti fuori mappa → tutti filtrati, nessun crash
- Test accumulo duplicati: più punti sulla stessa cella → conteggio corretto
- Test griglia vuota: input vuoto → None
- Test differenziale: user vs pro positions → diff_matrix coerente

#### A2. Test transposition table in `test_game_tree.py` (AGGIUNTA)
- Verificare che `_tt_hits > 0` dopo evaluate su albero con stati ripetuti
- Verificare che valore memoizzato == valore fresco ricalcolato
- Verificare eviction quando `_tt` raggiunge `_TT_MAX_SIZE`
- Verificare che `_state_hash()` è deterministica e coerente

#### A3. Test searchsorted flash correlation in `test_analysis_gaps.py` (AGGIUNTA)
- Test con DataFrame flash+blind noti → verifica effective_flashes esatto
- Test edge: nessun blind → bait_rate = 1.0
- Test edge: ogni flash ha un blind → bait_rate = 0.0
- Test window boundary: blind esattamente a `FLASH_BLIND_WINDOW_TICKS`

#### A4. `test_player_knowledge.py` (NUOVO — Gap critico)
- Test `_build_enemy_memory` con dati sintetici: posizioni nemiche corrette
- Test FOV: nemico dentro vs fuori FOV (90°)
- Test decay: nemico visto N tick fa → decay = exp(-N/TAU)
- Test pre-index: risultato identico al loop originale

### Fase B: Validazione Completa
1. `pytest Programma_CS2_RENAN/tests/ -v --tb=short` → tutti passano
2. `python tools/headless_validator.py` → 294/298+ PASS, 0 FAIL
3. Coverage ≥ 30% mantenuta

### Fase C: Rigenerazione Manifest + Commit
1. `python Programma_CS2_RENAN/tools/sync_integrity_manifest.py`
2. `pre-commit run --all-files`
3. Commit atomico + push

---

## File da Creare/Modificare

| File | Azione | Scope |
|---|---|---|
| `Programma_CS2_RENAN/tests/test_heatmap_engine.py` | CREARE | Test vectorizzazione heatmap |
| `Programma_CS2_RENAN/tests/test_player_knowledge.py` | CREARE | Test pre-index + FOV + decay |
| `Programma_CS2_RENAN/tests/test_game_tree.py` | AGGIUNGERE test | Test memoizzazione TT |
| `Programma_CS2_RENAN/tests/test_analysis_gaps.py` | AGGIUNGERE test | Test searchsorted flash |

---

## Moduli Ben Testati (conferma audit)

| Modulo | File Test | Qualità |
|---|---|---|
| `game_tree.py` (base) | `test_game_tree.py` | ✅ 70 test, behavioral |
| `jepa_model.py` | `test_jepa_model.py` | ✅ 40 test, gradient flow |
| `database.py` | `test_database_layer.py` | ✅ 30 test, CRUD + WAL |
| `session_engine.py` | `test_session_engine.py` | ✅ 25 test, state transitions |
| `hybrid_engine.py` | `test_hybrid_engine.py` | ✅ 20 test, confidence scoring |
| `vectorizer.py` | `test_feature_extractor_contracts.py` | ✅ Contratti dimensionali |

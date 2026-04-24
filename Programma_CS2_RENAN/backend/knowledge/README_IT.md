> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — Recupero RAG e COPER Experience Bank

> **Authority:** COPER Coaching Framework (Context Optimized with Prompt, Experience, and Replay)

Il modulo `backend/knowledge/` costituisce il livello di memoria semantica del
sistema di coaching CS2. Implementa Retrieval-Augmented Generation (RAG) per la
conoscenza tattica, un COPER Experience Bank per apprendere dalle partite passate,
un indice vettoriale FAISS per la ricerca sub-lineare dei nearest-neighbor, un
Knowledge Graph per il ragionamento relazionale multi-hop e una pipeline di mining
delle statistiche pro che converte le statistiche professionali HLTV in voci di
conoscenza per il coaching. Insieme, questi componenti permettono al motore di
coaching di fornire consigli contestuali e fondati sull'esperienza che migliorano
nel tempo man mano che vengono analizzate piu demo e raccolti piu feedback.

---

## Inventario dei File

| File | Scopo | Classi / Funzioni Principali |
|------|-------|------------------------------|
| `experience_bank.py` | COPER Experience Bank: memorizzazione, recupero e sintesi delle esperienze di gioco | `ExperienceBank`, `ExperienceContext`, `SynthesizedAdvice`, `get_experience_bank()` |
| `rag_knowledge.py` | Recupero conoscenza RAG con embeddings Sentence-BERT | `KnowledgeEmbedder`, `KnowledgeRetriever`, `KnowledgePopulator`, `generate_rag_coaching_insight()`, `generate_unified_coaching_insight()` |
| `vector_index.py` | Indice vettoriale FAISS per ricerca ANN sub-lineare | `VectorIndexManager`, `get_vector_index_manager()` |
| `graph.py` | Knowledge Graph con archiviazione entita-relazioni e query BFS su sottografi | `KnowledgeGraphManager`, `get_knowledge_graph()` |
| `pro_demo_miner.py` | Mining di conoscenza coaching dalle stat card pro di HLTV | `ProStatsMiner` (alias `ProDemoMiner`), `auto_populate_from_pro_demos()` |
| `init_knowledge_base.py` | Inizializzazione completa: carica JSON, esegue mining pro stats, costruisce indici FAISS | `initialize_knowledge_base()` |
| `round_utils.py` | Utilita condivisa per inferenza fase round da valore equipaggiamento | `infer_round_phase()` |
| `tactical_knowledge.json` | Dati seed: 15 voci di conoscenza tattica scritte a mano che coprono 7 mappe | (dati JSON) |
| `__init__.py` | Esportazioni del package | `KnowledgeGraphManager`, `get_knowledge_graph` |

---

## Architettura

Il modulo e organizzato attorno a quattro strategie di recupero che alimentano
il motore di coaching attraverso `generate_unified_coaching_insight()`:

```
                     +---------------------+
                     | coaching_service.py  |
                     |  (COPER / Hybrid)    |
                     +----------+----------+
                                |
                 generate_unified_coaching_insight()
                                |
              +-----------------+-----------------+
              |                                   |
   +----------v----------+          +-------------v-----------+
   | KnowledgeRetriever   |          | ExperienceBank          |
   |  (RAG tattico)       |          |  (esperienze COPER)     |
   +---------+------------+          +------------+------------+
             |                                    |
     +-------v-------+                   +--------v--------+
     | VectorIndex    |                   | VectorIndex     |
     | "knowledge"    |                   | "experience"    |
     | (FAISS / brute)|                   | (FAISS / brute) |
     +-------+--------+                   +--------+--------+
             |                                     |
     +-------v--------+                   +--------v---------+
     | TacticalKnowledge|                  | CoachingExperience|
     | (database.db)    |                  | (database.db)     |
     +------------------+                  +-------------------+
```

### Pipeline degli Embedding

Tutto il testo viene trasformato in embedding tramite Sentence-BERT
(`all-MiniLM-L6-v2`, 384 dimensioni). Quando il pacchetto `sentence-transformers`
non e installato, un fallback deterministico basato su hash-projection produce
vettori a 100 dimensioni con similarita semantica degradata ma funzionale. La
classe `KnowledgeEmbedder` gestisce il caricamento del modello, il caching, il
tracciamento della versione (`CURRENT_VERSION = "v3"`) e il re-embedding
automatico quando il modello cambia dimensione.

### Indice Vettoriale FAISS

`VectorIndexManager` mantiene due indici FAISS `IndexFlatIP` nominati:

- **`knowledge`** -- indicizza le righe `TacticalKnowledge.embedding`
- **`experience`** -- indicizza le righe `CoachingExperience.embedding`

I vettori vengono normalizzati L2 prima dell'indicizzazione cosi che il prodotto
interno equivalga alla similarita coseno. Gli indici sono persistiti su disco
(`<STORAGE_ROOT>/indexes/`) e ricostruiti pigramente quando contrassegnati come
dirty tramite `mark_dirty()`. I moltiplicatori di over-fetch
(`OVERFETCH_KNOWLEDGE=10`, `OVERFETCH_EXPERIENCE=20`) compensano il
post-filtraggio per mappa, categoria, confidenza e outcome. Quando FAISS non
e installato, tutte le ricerche ricadono sulla similarita coseno brute-force.

### Scoring dell'Experience Bank

L'`ExperienceBank` utilizza una formula di scoring composito per il recupero:

```
score = (similarity + hash_bonus + effectiveness_bonus) * confidence
```

Dove:
- `similarity` -- similarita coseno da FAISS o brute-force (0.0 a 1.0)
- `hash_bonus` -- 0.2 se il `context_hash` corrisponde esattamente (stessa mappa + side + fase + area)
- `effectiveness_bonus` -- `effectiveness_score * 0.4` per esperienze validate
- `confidence` -- peso di affidabilita per esperienza (0.1 a 1.0)

### Ciclo di Feedback

L'Experience Bank implementa un ciclo di apprendimento a circuito chiuso:

1. Il consiglio di coaching viene fornito (`usage_count` dell'esperienza incrementato)
2. La partita successiva viene analizzata (`collect_feedback_from_match()`)
3. Il feedback viene registrato con un `effectiveness_score` aggiornato tramite EMA
4. La confidenza viene adattata (+/- 5% per evento di feedback, limitata a [0.1, 1.0])
5. Le esperienze obsolete non validate decadono del 10% di confidenza dopo 90 giorni

### Knowledge Graph

`KnowledgeGraphManager` fornisce un grafo entita-relazioni supportato da SQLite
per il ragionamento tattico strutturato. Le entita (es. "Mirage/Window", tipo
"Spot") portano liste di osservazioni JSON. Le relazioni sono archi diretti
(es. `"Mirage/Window" --[CONNECTS_TO]--> "Mirage/Mid"`). Le query BFS sui
sottografi supportano attraversamento multi-hop fino a profondita 5.

---

## Integrazione

### Consumatori

| Consumatore | Utilizzo |
|-------------|----------|
| `backend/services/coaching_service.py` | Chiama `generate_unified_coaching_insight()` nelle modalita COPER e Hybrid |
| `backend/coaching/hybrid_engine.py` | Unisce il contesto di conoscenza RAG con le predizioni ML |
| `backend/coaching/correction_engine.py` | Recupera esempi pro per suggerimenti di correzione |
| `core/session_engine.py` (daemon Teacher) | Avvia l'estrazione esperienze dopo l'ingestione demo |

### Fonti Dati

| Fonte | Destinazione |
|-------|-------------|
| `tactical_knowledge.json` | Tabella `TacticalKnowledge` tramite `KnowledgePopulator.populate_from_json()` |
| HLTV `ProPlayerStatCard` | Tabella `TacticalKnowledge` tramite `ProStatsMiner.mine_all_pro_stats()` |
| Tick data + eventi demo analizzati | Tabella `CoachingExperience` tramite `ExperienceBank.extract_experiences_from_demo()` |

### Accesso Singleton

Tutti i componenti principali usano factory singleton thread-safe:

- `get_experience_bank()` -- double-checked locking con `threading.Lock`
- `get_vector_index_manager()` -- restituisce `None` se FAISS non e disponibile
- `get_knowledge_graph()` -- inizializzazione lazy
- `_get_retriever()` -- `KnowledgeRetriever` cachato per evitare il ricaricamento di SBERT

---

## Note di Sviluppo

### Dipendenze

| Pacchetto | Scopo | Fallback |
|-----------|-------|----------|
| `sentence-transformers` | Embeddings Sentence-BERT (`all-MiniLM-L6-v2`, 384-dim) | Hash-projection (100-dim) |
| `faiss-cpu` | Ricerca ANN sub-lineare (`IndexFlatIP`) | Similarita coseno brute-force |
| `numpy` | Operazioni vettoriali | Obbligatorio |
| `sqlmodel` / `sqlalchemy` | ORM database e aggiornamenti atomici | Obbligatorio |

### Serializzazione degli Embedding

Gli embedding delle esperienze usano bytes `float32` codificati in base64
(AC-32-01), che e circa 4x piu compatto della serializzazione JSON. Il
deserializzatore (`_deserialize_embedding`) rileva automaticamente il formato
JSON legacy (inizia con `[`) per compatibilita all'indietro.

### Costanti Chiave

| Costante | Valore | Posizione |
|----------|--------|-----------|
| `MIN_RETRIEVAL_CONFIDENCE` | 0.3 | `experience_bank.py:42` |
| `PRO_EXPERIENCE_CONFIDENCE` | 0.7 | `experience_bank.py:43` |
| `AMATEUR_EXPERIENCE_CONFIDENCE` | 0.5 | `experience_bank.py:44` |
| `OVERFETCH_KNOWLEDGE` | 10 | `vector_index.py:48` |
| `OVERFETCH_EXPERIENCE` | 20 | `vector_index.py:49` |
| `KnowledgeEmbedder.CURRENT_VERSION` | `"v3"` | `rag_knowledge.py:51` |
| `KnowledgeEmbedder.embedding_dim` | 384 (SBERT) / 100 (fallback) | `rag_knowledge.py:53,67` |

### Soglie Archetipi del Mining Pro-Stats

| Archetipo | Condizione |
|-----------|------------|
| Star Fragger | `impact >= 1.15` e `rating_2_0 >= 1.10` |
| AWP Specialist | `headshot_pct < 0.35` e `impact >= 1.05` |
| Support Anchor | `kast >= 0.72` e `impact < 1.05` |
| Entry Fragger | `opening_duel_win_pct >= 0.52` |
| Versatile | (predefinito) |

### Inizializzazione

Eseguire `init_knowledge_base.py` una volta per inizializzare il sistema di conoscenza:

```bash
python -m Programma_CS2_RENAN.backend.knowledge.init_knowledge_base
```

Questo carica `tactical_knowledge.json` (15 voci), esegue il mining delle stat
card pro da `hltv_metadata.db` e costruisce entrambi gli indici FAISS.

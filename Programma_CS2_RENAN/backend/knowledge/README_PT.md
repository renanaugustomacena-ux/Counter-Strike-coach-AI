> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — Recuperacao RAG e COPER Experience Bank

> **Authority:** COPER Coaching Framework (Context Optimized with Prompt, Experience, and Replay)

O modulo `backend/knowledge/` constitui a camada de memoria semantica do sistema
de coaching CS2. Implementa Retrieval-Augmented Generation (RAG) para conhecimento
tatico, um COPER Experience Bank para aprender com partidas passadas, um indice
vetorial FAISS para busca sub-linear de vizinhos mais proximos, um Knowledge Graph
para raciocinio relacional multi-hop e um pipeline de mineracao de estatisticas
pro que converte estatisticas profissionais do HLTV em entradas de conhecimento
para coaching. Juntos, esses componentes permitem que o motor de coaching entregue
conselhos contextuais e fundamentados na experiencia que melhoram ao longo do
tempo conforme mais demos sao analisadas e mais feedback e coletado.

---

## Inventario de Arquivos

| Arquivo | Proposito | Classes / Funcoes Principais |
|---------|-----------|------------------------------|
| `experience_bank.py` | COPER Experience Bank: armazenamento, recuperacao e sintese de experiencias de jogo | `ExperienceBank`, `ExperienceContext`, `SynthesizedAdvice`, `get_experience_bank()` |
| `rag_knowledge.py` | Recuperacao de conhecimento RAG com embeddings Sentence-BERT | `KnowledgeEmbedder`, `KnowledgeRetriever`, `KnowledgePopulator`, `generate_rag_coaching_insight()`, `generate_unified_coaching_insight()` |
| `vector_index.py` | Indice vetorial FAISS para busca ANN sub-linear | `VectorIndexManager`, `get_vector_index_manager()` |
| `graph.py` | Knowledge Graph com armazenamento entidade-relacao e consultas BFS em subgrafos | `KnowledgeGraphManager`, `get_knowledge_graph()` |
| `pro_demo_miner.py` | Mineracao de conhecimento coaching a partir de stat cards pro do HLTV | `ProStatsMiner` (alias `ProDemoMiner`), `auto_populate_from_pro_demos()` |
| `init_knowledge_base.py` | Inicializacao completa: carrega JSON, minera pro stats, constroi indices FAISS | `initialize_knowledge_base()` |
| `round_utils.py` | Utilitario compartilhado para inferencia de fase do round a partir do valor do equipamento | `infer_round_phase()` |
| `tactical_knowledge.json` | Dados seed: 15 entradas de conhecimento tatico escritas manualmente cobrindo 7 mapas | (dados JSON) |
| `__init__.py` | Exportacoes do pacote | `KnowledgeGraphManager`, `get_knowledge_graph` |

---

## Arquitetura

O modulo e organizado em torno de quatro estrategias de recuperacao que alimentam
o motor de coaching atraves de `generate_unified_coaching_insight()`:

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
   |  (RAG tatico)        |          |  (experiencias COPER)   |
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

### Pipeline de Embedding

Todo texto e transformado em embedding usando Sentence-BERT (`all-MiniLM-L6-v2`,
384 dimensoes). Quando o pacote `sentence-transformers` nao esta instalado, um
fallback deterministico baseado em hash-projection produz vetores de 100 dimensoes
com similaridade semantica degradada mas funcional. A classe `KnowledgeEmbedder`
gerencia o carregamento do modelo, caching, rastreamento de versao
(`CURRENT_VERSION = "v2"`) e re-embedding automatico quando o modelo muda de
dimensao.

### Indice Vetorial FAISS

`VectorIndexManager` mantem dois indices FAISS `IndexFlatIP` nomeados:

- **`knowledge`** -- indexa as linhas `TacticalKnowledge.embedding`
- **`experience`** -- indexa as linhas `CoachingExperience.embedding`

Os vetores sao normalizados L2 antes da indexacao para que o produto interno
seja equivalente a similaridade cosseno. Os indices sao persistidos em disco
(`<STORAGE_ROOT>/indexes/`) e reconstruidos preguicosamente quando marcados como
dirty via `mark_dirty()`. Os multiplicadores de over-fetch
(`OVERFETCH_KNOWLEDGE=10`, `OVERFETCH_EXPERIENCE=20`) compensam a
pos-filtragem por mapa, categoria, confianca e outcome. Quando FAISS nao
esta instalado, todas as buscas recorrem a similaridade cosseno brute-force.

### Scoring do Experience Bank

O `ExperienceBank` utiliza uma formula de scoring composto para recuperacao:

```
score = (similarity + hash_bonus + effectiveness_bonus) * confidence
```

Onde:
- `similarity` -- similaridade cosseno via FAISS ou brute-force (0.0 a 1.0)
- `hash_bonus` -- 0.2 se o `context_hash` corresponde exatamente (mesmo mapa + side + fase + area)
- `effectiveness_bonus` -- `effectiveness_score * 0.4` para experiencias validadas
- `confidence` -- peso de confiabilidade por experiencia (0.1 a 1.0)

### Ciclo de Feedback

O Experience Bank implementa um ciclo de aprendizado em circuito fechado:

1. O conselho de coaching e entregue (`usage_count` da experiencia incrementado)
2. A partida seguinte e analisada (`collect_feedback_from_match()`)
3. O feedback e registrado com um `effectiveness_score` atualizado via EMA
4. A confianca e ajustada (+/- 5% por evento de feedback, limitada a [0.1, 1.0])
5. Experiencias obsoletas nao validadas decaem 10% de confianca apos 90 dias

### Knowledge Graph

`KnowledgeGraphManager` fornece um grafo entidade-relacao suportado por SQLite
para raciocinio tatico estruturado. As entidades (ex. "Mirage/Window", tipo
"Spot") carregam listas de observacoes JSON. As relacoes sao arestas direcionadas
(ex. `"Mirage/Window" --[CONNECTS_TO]--> "Mirage/Mid"`). Consultas BFS em
subgrafos suportam travessia multi-hop ate profundidade 5.

---

## Integracao

### Consumidores

| Consumidor | Utilizacao |
|------------|-----------|
| `backend/services/coaching_service.py` | Chama `generate_unified_coaching_insight()` nos modos COPER e Hybrid |
| `backend/coaching/hybrid_engine.py` | Mescla o contexto de conhecimento RAG com previsoes ML |
| `backend/coaching/correction_engine.py` | Recupera exemplos pro para sugestoes de correcao |
| `core/session_engine.py` (daemon Teacher) | Dispara a extracao de experiencias apos ingestao de demo |

### Fontes de Dados

| Fonte | Destino |
|-------|---------|
| `tactical_knowledge.json` | Tabela `TacticalKnowledge` via `KnowledgePopulator.populate_from_json()` |
| HLTV `ProPlayerStatCard` | Tabela `TacticalKnowledge` via `ProStatsMiner.mine_all_pro_stats()` |
| Tick data + eventos de demos analisadas | Tabela `CoachingExperience` via `ExperienceBank.extract_experiences_from_demo()` |

### Acesso Singleton

Todos os componentes principais usam factories singleton thread-safe:

- `get_experience_bank()` -- double-checked locking com `threading.Lock`
- `get_vector_index_manager()` -- retorna `None` se FAISS nao esta disponivel
- `get_knowledge_graph()` -- inicializacao lazy
- `_get_retriever()` -- `KnowledgeRetriever` cacheado para evitar recarregar SBERT

---

## Notas de Desenvolvimento

### Dependencias

| Pacote | Proposito | Fallback |
|--------|-----------|----------|
| `sentence-transformers` | Embeddings Sentence-BERT (`all-MiniLM-L6-v2`, 384-dim) | Hash-projection (100-dim) |
| `faiss-cpu` | Busca ANN sub-linear (`IndexFlatIP`) | Similaridade cosseno brute-force |
| `numpy` | Operacoes vetoriais | Obrigatorio |
| `sqlmodel` / `sqlalchemy` | ORM de banco de dados e atualizacoes atomicas | Obrigatorio |

### Serializacao de Embedding

Os embeddings de experiencias usam bytes `float32` codificados em base64
(AC-32-01), que e aproximadamente 4x mais compacto que a serializacao JSON. O
deserializador (`_deserialize_embedding`) detecta automaticamente o formato
JSON legado (comeca com `[`) para compatibilidade retroativa.

### Constantes Chave

| Constante | Valor | Localizacao |
|-----------|-------|-------------|
| `MIN_RETRIEVAL_CONFIDENCE` | 0.3 | `experience_bank.py:42` |
| `PRO_EXPERIENCE_CONFIDENCE` | 0.7 | `experience_bank.py:43` |
| `AMATEUR_EXPERIENCE_CONFIDENCE` | 0.5 | `experience_bank.py:44` |
| `OVERFETCH_KNOWLEDGE` | 10 | `vector_index.py:48` |
| `OVERFETCH_EXPERIENCE` | 20 | `vector_index.py:49` |
| `KnowledgeEmbedder.CURRENT_VERSION` | `"v2"` | `rag_knowledge.py:48` |
| `KnowledgeEmbedder.embedding_dim` | 384 (SBERT) / 100 (fallback) | `rag_knowledge.py:53,67` |

### Limiares de Arquetipos do Mining Pro-Stats

| Arquetipo | Condicao |
|-----------|----------|
| Star Fragger | `impact >= 1.15` e `rating_2_0 >= 1.10` |
| AWP Specialist | `headshot_pct < 0.35` e `impact >= 1.05` |
| Support Anchor | `kast >= 0.72` e `impact < 1.05` |
| Entry Fragger | `opening_duel_win_pct >= 0.52` |
| Versatile | (padrao) |

### Inicializacao

Execute `init_knowledge_base.py` uma vez para inicializar o sistema de conhecimento:

```bash
python -m Programma_CS2_RENAN.backend.knowledge.init_knowledge_base
```

Isto carrega `tactical_knowledge.json` (15 entradas), minera as stat cards pro
de `hltv_metadata.db` e constroi ambos os indices FAISS.

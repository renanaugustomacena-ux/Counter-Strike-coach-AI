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
| `book/` | Corpus do Coach Book: `index.json` + 8 arquivos de conteudo (`general.json` + 7 mapas), 508 entradas em 13 categorias | (dados JSON) |
| `tactical_knowledge.json` | Dados seed legado (fallback quando `book/index.json` esta ausente): 15 entradas escritas manualmente em 8 mapas + general | (dados JSON) |
| `__init__.py` | Raiz do pacote | (vazio -- apenas namespace) |

---

## Arquitetura

O modulo e organizado em torno de dois pilares de recuperacao que as camadas de
coaching consomem diretamente -- `KnowledgeRetriever` para conhecimento tatico
RAG e `ExperienceBank` para experiencias COPER. (`rag_knowledge.py` tambem expoe
`generate_rag_coaching_insight()` e `generate_unified_coaching_insight()` como
pontos de entrada a nivel de modulo que combinam ambos os pilares, mas os
consumidores em producao atualmente instanciam as classes diretamente.)

```
                     +---------------------+
                     | coaching_service.py  |
                     | coaching_dialogue.py |
                     | hybrid_engine.py ... |
                     +----------+----------+
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
(`CURRENT_VERSION = "v3"`) e re-embedding automatico quando o modelo muda de
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
- `effectiveness_bonus` -- `effectiveness_score * 0.4`, aplicado somente quando a
  experiencia e `outcome_validated` e tem pelo menos `_MIN_EFFECTIVENESS_TRIALS`
  tentativas de conselho (fix C-2)
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
para raciocinio tatico estruturado, armazenado em
`<USER_DATA_ROOT>/knowledge_graph.db` (modo WAL, conexao em cache). As entidades
(ex. "Mirage/Window", tipo "Spot") carregam listas de observacoes JSON. As
relacoes sao arestas direcionadas (ex.
`"Mirage/Window" --[CONNECTS_TO]--> "Mirage/Mid"`). Consultas BFS em subgrafos
suportam travessia multi-hop ate profundidade 5.

---

## Integracao

### Consumidores

| Consumidor | Utilizacao |
|------------|-----------|
| `backend/services/coaching_service.py` | Modo COPER: constroi um `ExperienceContext`, consulta `get_experience_bank()` e chama `collect_feedback_from_match()` apos cada partida analisada; tambem usa `KnowledgeRetriever` e `round_utils.infer_round_phase()` |
| `backend/services/coaching_dialogue.py` | Grounding do chat: `KnowledgeRetriever.retrieve()` + recuperacao do Experience Bank; chama `ensure_seed_knowledge_loaded()` na inicializacao |
| `backend/coaching/hybrid_engine.py` | Carrega preguicosamente um `KnowledgeRetriever` (AC-15-01) para mesclar o contexto de conhecimento RAG com desvios Z-score da baseline |
| `backend/analysis/role_classifier.py` | Recupera entradas de coaching especificas por papel via `KnowledgeRetriever.retrieve()` |
| `core/session_engine.py` | Bootstrap na primeira execucao: chama `initialize_knowledge_base()` quando a tabela `TacticalKnowledge` esta vazia; tambem inicia o watcher de ingestao |
| `apps/qt_app/app.py` | Tela de splash: verifica o cache do modelo `KnowledgeEmbedder` e pre-baixa o modelo SBERT no primeiro lancamento |

### Fontes de Dados

| Fonte | Destino |
|-------|---------|
| `book/index.json` (Coach Book, 508 entradas; entradas filtradas pela allow-list `_ALLOWED_ENTRY_KEYS`) | Tabela `TacticalKnowledge` via `KnowledgePopulator.populate_from_json()` |
| `tactical_knowledge.json` (fallback legado, 15 entradas) | Tabela `TacticalKnowledge` via `KnowledgePopulator.populate_from_json()` |
| HLTV `ProPlayerStatCard` | Tabela `TacticalKnowledge` via `ProStatsMiner.mine_all_pro_stats()` |
| Tick data + eventos de demos analisadas | Tabela `CoachingExperience` via `ExperienceBank.extract_experiences_from_demo()` |

### Acesso Singleton

Todos os componentes principais usam factories singleton thread-safe:

- `get_experience_bank()` -- double-checked locking com `threading.Lock`
- `get_vector_index_manager()` -- retorna `None` se FAISS nao esta disponivel
- `get_knowledge_graph()` -- double-checked locking com `threading.Lock`
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
| `MIN_RETRIEVAL_CONFIDENCE` | 0.3 | `experience_bank.py:48` |
| `PRO_EXPERIENCE_CONFIDENCE` | 0.7 | `experience_bank.py:49` |
| `AMATEUR_EXPERIENCE_CONFIDENCE` | 0.5 | `experience_bank.py:50` |
| `OVERFETCH_KNOWLEDGE` | 10 | `vector_index.py:48` |
| `OVERFETCH_EXPERIENCE` | 20 | `vector_index.py:49` |
| `KnowledgeEmbedder.CURRENT_VERSION` | `"v3"` | `rag_knowledge.py:51` |
| `KnowledgeEmbedder.embedding_dim` | 384 (SBERT) / 100 (fallback) | `rag_knowledge.py:56,74` |
| `_MIN_EFFECTIVENESS_TRIALS` | 5 | `experience_bank.py:45` |
| `DUPLICATE_SIMILARITY_THRESHOLD` | 0.9 | `experience_bank.py:53` |
| `REPLAY_ALPHA` | 0.6 | `experience_bank.py:59` |
| `REPLAY_GATE` | 0.4 | `experience_bank.py:60` |

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

Isto carrega o Coach Book via `book/index.json` (508 entradas; recorre ao legado
`tactical_knowledge.json` com 15 entradas se o indice do livro estiver ausente),
minera as stat cards pro de `hltv_metadata.db` e constroi ambos os indices FAISS.

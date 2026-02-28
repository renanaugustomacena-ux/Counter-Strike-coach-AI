> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge — RAG e Experience Bank

Base de conhecimento RAG (Retrieval-Augmented Generation) e COPER Experience Bank para coaching consciente do contexto com recuperação semântica.

## Módulos Principais

### COPER Experience Bank
- **experience_bank.py** — `ExperienceBank`, `ExperienceContext` — Armazena experiências de coaching com busca de similaridade semântica, ponderação de recência/efetividade e poda automática (máx. 1000 experiências). Integrado com `backend/storage/db_models.py::CoachingExperience` para persistência.

### Recuperação de Conhecimento RAG
- **rag_knowledge.py** — `KnowledgeRetriever`, `KnowledgeEmbedder` — Recuperação semântica de conhecimento tático de padrões de demos pro usando embeddings sentence-transformers. Suporta armazenamento de conhecimento em memória e baseado em banco de dados.

### Mineração de Padrões Profissionais
- **pro_demo_miner.py** — `ProDemoMiner` — Extrai padrões táticos, configurações e árvores de decisão de demos de jogadores profissionais. Popula base de conhecimento com exemplos anotados para recuperação RAG.

### Infraestrutura de Suporte
- **graph.py** — Estruturas de grafo de conhecimento para representação de conhecimento relacional
- **init_knowledge_base.py** — Inicialização de base de conhecimento e seeding com conceitos táticos fundamentais de CS2

## Integração

Usado por `backend/services/coaching_service.py` nos modos COPER e Hybrid:
- **Modo COPER**: Experience Bank (semântico) + RAG (tático) + Referências Pro (baseadas em função)
- **Modo Hybrid**: Contexto de conhecimento RAG sintetizado com previsões ML

## Estratégia de Recuperação

Experience Bank usa similaridade cosseno em embeddings com decaimento de recência (λ=0.1) e bônus de efetividade (0.4×rating). Recuperação Top-K (padrão K=5) com desduplicação semântica.

## Dependências
sentence-transformers (all-MiniLM-L6-v2), SQLModel (persistência), NumPy.

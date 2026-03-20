> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Data — Dados da Aplicacao e Configuracao

> **Autoridade:** Rule 4 (Data Persistence)

Este diretorio contem dados de tempo de execucao, arquivos de configuracao, conhecimento de coaching, datasets estatisticos externos e a area de staging para ingestao de demos.

## Estrutura do Diretorio

data/
├── demos/pro_ingest/         # Demos de partidas profissionais para treinamento
├── docs/                     # Documentacao de ajuda in-app
├── external/                 # Datasets estatisticos de terceiros (CSV)
├── knowledge/                # Base de conhecimento RAG para coaching
├── dataset.csv               # Dataset de treinamento
├── map_config.json           # Configuracao espacial dos mapas
├── map_tensors.json          # Definicoes de coordenadas de tensor 3D
├── pro_baseline.csv          # Estatisticas baseline profissionais
└── hltv_sync_state.json      # Estado de sincronizacao do scraper HLTV

## Arquivos de Configuracao Principais

### map_config.json
Definicoes espaciais para todos os mapas competitivos de CS2 (pos_x, pos_y, scale, landmarks, z_cutoff para mapas multi-nivel).

### map_tensors.json
Coordenadas de tensor 3D para treinamento ML (posicoes de bombsite, posicoes de spawn, zonas de controle mid).

## external/ — Datasets Estatisticos
Dados CSV de terceiros usados para analises de referencia e calibracao de coaching (top 100 jogadores, papeis de playstyle, estatisticas de mapas, estatisticas de armas, resultados de rounds, etc.)

## knowledge/ — Base de Conhecimento RAG
Textos de coaching por mapa (8 mapas x 2 versoes), base de conhecimento JSON estruturada, utilizados pelo framework COPER via embeddings SBERT e indexacao FAISS.

## Notas de Desenvolvimento

- NAO commite arquivos demo (.dem) — eles tem 50-200MB cada
- Os CSVs externos sao dados de referencia estaticos
- Os arquivos de conhecimento sao a base intelectual do coaching — edite com cuidado

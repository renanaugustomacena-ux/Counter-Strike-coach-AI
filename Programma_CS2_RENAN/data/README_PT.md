> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data — Dados da Aplicação & Configuração

> **Autoridade:** Regra 4 (Persistência de Dados)

Este diretório contém dados de tempo de execução, arquivos de configuração, conhecimento de coaching, datasets estatísticos externos e a área de staging para ingestão de demos. Todos os arquivos aqui são dados do lado do usuário (não código).

## Estrutura do Diretório

```
data/
├── demos/                           # Staging de arquivos demo
│   └── pro_ingest/                 # Demos de partidas profissionais para treinamento
├── docs/                            # Documentação de ajuda in-app
│   ├── features.md                 # Lista de funcionalidades de coaching
│   ├── getting_started.md          # Guia de configuração do usuário (regra 10/10)
│   └── troubleshooting.md         # Problemas comuns
├── external/                        # Datasets estatísticos de terceiros (CSV)
│   ├── all_Time_best_Players_Stats.csv
│   ├── cs2_playstyle_roles_2024.csv
│   ├── csgo_games.csv
│   ├── Maps01_BombPlantOutcomes01.csv
│   ├── Maps01_RoundOutcomes.csv
│   ├── Maps02_BombPlantOutcomes.csv
│   ├── maps_statistics.csv
│   ├── top_100_players.csv
│   ├── weapons_statistics.csv
│   └── hltv_stats_urls.txt         # URLs de jogadores HLTV para o scraper
├── knowledge/                       # Base de conhecimento RAG para coaching
│   ├── {map}_coaching.txt          # Texto de coaching por mapa (8 mapas)
│   ├── {map}_coaching_ocr.txt      # Variantes extraídas via OCR
│   ├── general_coaching.txt        # Princípios gerais de coaching CS2
│   ├── coaching_knowledge_base.json # KB estruturada (JSON)
│   └── extraction_summary.json     # Metadados de extração de conhecimento
├── dataset.csv                      # Dataset de treinamento
├── map_config.json                  # Configuração espacial dos mapas (257 linhas)
├── map_tensors.json                 # Definições de coordenadas de tensor 3D
├── pro_baseline.csv                 # Estatísticas baseline profissionais
└── hltv_sync_state.json            # Estado de sincronização do scraper HLTV
```

## Arquivos de Configuração Principais

### `map_config.json` (257 linhas)

Definições espaciais para todos os mapas competitivos de CS2:

```json
{
  "de_mirage": {
    "display_name": "Mirage",
    "pos_x": -3230,
    "pos_y": 1713,
    "scale": 5.0,
    "landmarks": {
      "a_site": [x, y],
      "b_site": [x, y],
      "mid_control": [x, y],
      "t_spawn": [x, y],
      "ct_spawn": [x, y]
    }
  }
}
```

- Utilizado por `core/spatial_data.py` para transformações de coordenadas
- Mapas multi-nível (Nuke, Vertigo) incluem limites `z_cutoff`
- Pool competitivo: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

Coordenadas de tensor 3D para treinamento ML:
- Posições de bombsite (A/B) com X, Y, Z
- Posições de spawn (T/CT)
- Zonas de controle mid e zonas importantes (connector, jungle, palace, etc.)

## `demos/pro_ingest/`

Diretório de staging para arquivos `.dem` de partidas profissionais. A pipeline de ingestão busca arquivos daqui para o treinamento da baseline profissional.

- Atualmente rastreado via `.gitkeep` (vazio no repositório)
- Produção: ~200 arquivos demo profissionais no SSD externo
- Os arquivos são processados por `backend/data_sources/demo_parser.py`

## `external/` — Datasets Estatísticos

Dados CSV de terceiros utilizados para análises de referência e calibração de coaching:

| Arquivo | Conteúdo | Utilizado Por |
|---------|----------|---------------|
| `top_100_players.csv` | Estatísticas dos top 100 jogadores HLTV | `processing/external_analytics.py` |
| `all_Time_best_Players_Stats.csv` | Estatísticas históricas dos melhores jogadores | Referência baseline profissional |
| `cs2_playstyle_roles_2024.csv` | Dados de classificação de papéis (2024) | `backend/ingestion/csv_migrator.py` |
| `maps_statistics.csv` | Taxas de vitória e de jogabilidade dos mapas | Análise de contexto de mapas |
| `weapons_statistics.csv` | Dados de dano/precisão de armas | Features de classes de armas |
| `Maps01_RoundOutcomes.csv` | Distribuições de resultados de rounds | Treinamento de probabilidade de vitória |
| `Maps01_BombPlantOutcomes01.csv` | Dados de resultados de plantio de bomba | Análise de economia |
| `csgo_games.csv` | Dados históricos de partidas CS:GO | Referência legacy |
| `hltv_stats_urls.txt` | URLs de perfis de jogadores HLTV | Input do scraper HLTV |

## `knowledge/` — Base de Conhecimento RAG

Arquivos de conhecimento para coaching no framework COPER (Context Optimized with Prompt, Experience, Replay):

### Coaching por Mapa (8 mapas x 2 versões)

Cada mapa possui duas versões:
- `{map}_coaching.txt` — Texto de coaching bruto
- `{map}_coaching_ocr.txt` — Variante extraída via OCR

Mapas cobertos: Ancient, Anubis, Dust2, Inferno, Mirage, Nuke, Overpass + geral

### Base de Conhecimento Estruturada

- `coaching_knowledge_base.json` — KB estruturada com seções para táticas, posições, utilitários e callouts
- `coaching_knowledge_base_ocr.json` — Variante OCR
- `extraction_summary.json` — Metadados sobre a extração de conhecimento (timestamps, versões)

### Como o Conhecimento É Utilizado

```
Arquivos knowledge/
    │
    └── backend/knowledge/rag_knowledge.py (KnowledgeEmbedder)
            │
            ├── Sentence-BERT gera embeddings dos chunks de texto (vetores 384-dim)
            └── Índices FAISS para busca rápida por similaridade
                    │
                    └── CoachingService recupera conhecimento relevante por consulta
```

## `docs/` — Ajuda In-App

Arquivos Markdown servidos por `backend/knowledge_base/help_system.py`:

- `getting_started.md` — Guia de configuração, regra 10/10, velocidades de ingestão, níveis de maturidade de dados
- `features.md` — Descrições de funcionalidades
- `troubleshooting.md` — Problemas comuns e soluções

## Notas de Desenvolvimento

- **NÃO commite arquivos demo** (`.dem`) — eles têm 50-200MB cada
- As coordenadas de `map_config.json` vêm dos arquivos do jogo CS2 (`resource/overviews/*.txt`)
- Os CSVs externos são dados de referência estáticos — atualize-os manualmente quando novos dados estiverem disponíveis
- `hltv_sync_state.json` rastreia o progresso do scraper — um `{}` vazio significa nenhuma sincronização ativa
- Os arquivos de conhecimento são a base intelectual do coaching — edite com cuidado
- `dataset.csv` e `pro_baseline.csv` são gerados pela pipeline de treinamento, não editados manualmente

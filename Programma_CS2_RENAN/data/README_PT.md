> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data — Dados da Aplicacao & Configuracao

> **Autoridade:** Regra 4 (Persistencia de Dados)

Este diretorio contem dados de tempo de execucao, arquivos de configuracao, conhecimento de coaching, inputs de dados estatisticos externos e a area de staging para ingestao de demos. Todos os arquivos aqui sao dados do lado do usuario (nao codigo).

## Estrutura do Diretorio

```
data/
├── demos/                           # Staging de arquivos demo
│   └── pro_ingest/                 # Demos de partidas profissionais para treinamento
├── docs/                            # Documentacao de ajuda in-app
│   ├── features.md                 # Lista de funcionalidades de coaching
│   ├── getting_started.md          # Guia de configuracao do usuario (regra 10/10)
│   └── troubleshooting.md         # Problemas comuns
├── external/                        # Inputs de dados externos
│   └── hltv_stats_urls.txt         # URLs de jogadores HLTV (lista de input historica)
├── knowledge/                       # Base de conhecimento RAG para coaching
│   ├── {map}_coaching.txt          # Texto de coaching por mapa (7 mapas)
│   ├── {map}_coaching_ocr.txt      # Variantes extraidas via OCR
│   ├── general_coaching.txt        # Principios gerais de coaching CS2 (+ variante OCR)
│   ├── coaching_knowledge_base.json # KB estruturada (JSON, + variante OCR)
│   └── extraction_summary.json     # Metadados de extracao de conhecimento
├── dataset.csv                      # Placeholder de dataset de treinamento (atualmente vazio)
├── map_config.json                  # Configuracao espacial dos mapas (260 linhas)
├── map_tensors.json                 # Definicoes de coordenadas de tensor 3D
└── hltv_sync_state.json            # Estado de sincronizacao do scraper HLTV
```

## Arquivos de Configuracao Principais

### `map_config.json` (260 linhas)

Definicoes espaciais para todos os mapas competitivos de CS2. As entradas de mapas
residem sob a chave top-level `maps` (junto com `_description`, `_source`,
`_last_updated` e `competitive_pool`):

```json
{
  "maps": {
    "de_mirage": {
      "pos_x": -3230,
      "pos_y": 1713,
      "scale": 5.0,
      "display_name": "Mirage",
      "landmarks": {
        "A-Site": [x, y],
        "B-Site": [x, y],
        "Mid": [x, y],
        "T-Spawn": [x, y],
        "CT-Spawn": [x, y]
      }
    }
  }
}
```

- Utilizado por `core/spatial_data.py` para transformacoes de coordenadas
- Mapas multi-nivel (Nuke, Vertigo) incluem limites `z_cutoff` e `levels`
- Pool competitivo: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

Coordenadas de tensor 3D para treinamento ML (7 mapas: mirage, inferno, dust2, nuke,
overpass, ancient, anubis):
- `image_file` referencia de radar por mapa
- Posicoes de bombsite (A/B) com X, Y, Z
- Posicoes de spawn (T/CT)
- Zonas de controle mid e zonas importantes (connector, jungle, palace, etc.)

## `demos/pro_ingest/`

Placeholder do lado do repositorio para arquivos `.dem` de partidas profissionais,
mantido para testes dev-scale locais (`tests/test_demo_parser.py` pula quando esta vazio).

- Atualmente rastreado via `.gitkeep` (vazio no repositorio)
- O diretorio de ingestao pro em runtime e configurado pelo usuario: a configuracao
  `PRO_DEMO_PATH` quando definida, caso contrario `pro_ingest/` sob a raiz de storage
  (`backend/storage/storage_manager.py`)
- O corpus completo de demos pro e o banco de dados de treinamento monolito residem em
  um volume externo, nao neste repositorio (veja `docs/OPEN_ISSUES.md` S2)
- Os arquivos sao processados por `backend/data_sources/demo_parser.py`

## `external/` — Inputs de Dados Externos

Atualmente contem um unico arquivo:

| Arquivo | Conteudo | Utilizado Por |
|---------|----------|---------------|
| `hltv_stats_urls.txt` | URLs de perfis de jogadores HLTV | Nenhum consumidor de codigo ativo (lista de input de um helper de fetch removido; mantido como dado) |

Datasets CSV de terceiros (estatisticas de jogadores, estatisticas de mapas, resultados
de rounds) nao sao mantidos no repositorio; `backend/processing/external_analytics.py` os
le daqui quando presentes, e o ingestor de torneios JSON
(`ingestion/pipelines/json_tournament_ingestor.py`) escreve seu CSV de saida aqui
(`tournament_advanced_stats.csv`) quando executado.

## `knowledge/` — Base de Conhecimento RAG

Arquivos de conhecimento para coaching no framework COPER (Context Optimized with Prompt, Experience, and Replay):

### Coaching por Mapa (7 mapas + geral, x 2 versoes)

Cada topico possui duas versoes:
- `{map}_coaching.txt` — Texto de coaching bruto (principalmente esbocos curtos)
- `{map}_coaching_ocr.txt` — Variante extraida via OCR (contem o grosso do conteudo)

Mapas cobertos: Ancient, Anubis, Dust2, Inferno, Mirage, Nuke, Overpass + geral

### Base de Conhecimento Estruturada

- `coaching_knowledge_base.json` — KB estruturada com secoes para taticas, posicoes, utilitarios e callouts
- `coaching_knowledge_base_ocr.json` — Variante OCR
- `extraction_summary.json` — Metadados sobre a extracao de conhecimento (timestamps, versoes)

### Como o Conhecimento E Utilizado

Estes arquivos sao o material bruto fonte do conhecimento de coaching. A base de
conhecimento RAG em runtime e populada a partir de `backend/knowledge/book/index.json`
(Coach Book, com `backend/knowledge/tactical_knowledge.json` como fallback legacy)
na tabela de banco de dados `tacticalknowledge` por `backend/knowledge/init_knowledge_base.py`;
o unico consumidor automatizado de `data/knowledge/` em si e uma verificacao estrutural
em `tools/headless_validator.py`.

```
Tabela DB tacticalknowledge (populada por init_knowledge_base.py)
    |
    └── backend/knowledge/rag_knowledge.py (KnowledgeEmbedder)
            |
            ├── Sentence-BERT gera embeddings dos chunks de texto (vetores 384-dim)
            └── Indice FAISS quando disponivel (fallback cosseno brute-force)
                    |
                    └── CoachingService recupera conhecimento relevante por consulta
```

## `docs/` — Ajuda In-App

Arquivos Markdown servidos por `backend/knowledge_base/help_system.py`:

- `getting_started.md` — Guia de configuracao, regra 10/10, velocidades de ingestao, niveis de maturidade de dados
- `features.md` — Descricoes de funcionalidades
- `troubleshooting.md` — Problemas comuns e solucoes

## Notas de Desenvolvimento

- **NAO commite arquivos demo** (`.dem`) — eles tem 50-200MB cada
- As coordenadas de `map_config.json` vem dos arquivos do jogo CS2 (`resource/overviews/*.txt`)
- `hltv_sync_state.json` rastreia o estado de sincronizacao HLTV — um `{}` vazio significa
  nenhuma sincronizacao ativa (atualmente zerado apenas por `tools/reset_pro_data.py`)
- Os arquivos de conhecimento sao a base intelectual do coaching — edite com cuidado
- `dataset.csv` e atualmente um placeholder vazio (incluido pelo spec PyInstaller), nao editado manualmente
- O spec PyInstaller tambem inclui `map_config.json`, `external/` e `docs/` daqui

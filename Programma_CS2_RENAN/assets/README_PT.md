> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Recursos Estaticos

> **Autoridade:** Regra 3 (Frontend & UX)

Este diretorio contem todos os recursos estaticos consumidos pela aplicacao em tempo
de execucao. Os arquivos aqui presentes sao incluidos na distribuicao PyInstaller e
resolvidos atraves de `core/config.py:get_resource_path()`, que abstrai a diferenca
entre a arvore de codigo-fonte de desenvolvimento e os executaveis congelados. Nada
neste diretorio e gerado em tempo de execucao; cada arquivo e versionado no controle
de versao e tratado como imutavel apos o lancamento.

## Estrutura do Diretorio

```
assets/
├── i18n/                     # Internacionalizacao (traducoes)
│   ├── en.json              # Ingles (137 chaves) — primario/fallback
│   ├── pt.json              # Portugues Brasileiro
│   └── it.json              # Italiano
├── maps/                     # Imagens de radar dos mapas CS2
│   ├── de_ancient_radar.dds
│   ├── de_cache_radar.dds
│   ├── de_dust2_radar.dds
│   ├── de_inferno_radar.dds
│   ├── de_mirage_radar.dds
│   ├── de_nuke_lower_radar.dds
│   ├── de_nuke_radar.dds
│   ├── de_overpass_radar.dds
│   ├── de_train_radar.dds
│   ├── de_vertigo_lower_radar.dds
│   └── de_vertigo_radar.dds
├── README.md                 # Este arquivo (Ingles)
├── README_IT.md              # Traducao Italiana
└── README_PT.md              # Traducao Portuguesa
```

## Inventario de Arquivos

| Arquivo / Diretorio | Tipo | Quantidade | Finalidade |
|----------------------|------|------------|------------|
| `i18n/en.json` | JSON | 137 chaves | Strings de UI em Ingles (idioma primario e fallback) |
| `i18n/pt.json` | JSON | 137 chaves | Strings de UI em Portugues Brasileiro |
| `i18n/it.json` | JSON | 137 chaves | Strings de UI em Italiano |
| `maps/de_*_radar.dds` | Imagem DDS | 11 arquivos | Imagens radar aereas para mapas competitivos CS2 |

## `i18n/` — Arquivos de Localizacao

Arquivos JSON contendo cada string visivel ao usuario na aplicacao. O esquema de
chaves e identico em todos os arquivos de idioma: quando uma chave existe em
`en.json`, ela tambem deve existir em `pt.json` e `it.json`. Se uma traducao estiver
faltando, o fallback em ingles e utilizado automaticamente pelo `QtLocalizationManager`.

### Categorias de Chaves (137 chaves no total)

| Categoria | Chaves de Exemplo | Finalidade |
|-----------|-------------------|------------|
| Navegacao | `dashboard`, `coach`, `match_history`, `performance` | Rotulos da barra lateral |
| Coaching | `coaching_insights`, `severity_high`, `focus_positioning` | Texto da tela Coach |
| Configuracoes | `theme`, `language`, `demo_path`, `ingestion_mode` | Tela de Configuracoes |
| Perfil | `player_name`, `bio`, `role` | Campos do perfil do usuario |
| Tatica | `tactical_viewer`, `playback_speed`, `timeline` | Tela do Tactical Viewer |
| Dialogos | `confirm_delete`, `save_success`, `error_occurred` | Mensagens de dialogo |
| Steam/FaceIT | `steam_id`, `faceit_key`, `sync_profile` | Telas de integracao |
| Ajuda | `help_center`, `getting_started`, `troubleshooting` | Tela do Centro de Ajuda |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | Wizard de configuracao inicial |

### Cadeia de Resolucao da Localizacao

O `QtLocalizationManager` em `apps/qt_app/core/i18n_bridge.py` resolve uma chave
atraves de quatro niveis de prioridade:

1. **Arquivo JSON para o idioma atual** (`_JSON_TRANSLATIONS[lang][key]`)
2. **Dicionario hardcoded para o idioma atual** (`_FULL_TRANSLATIONS[lang][key]`)
3. **Fallback em ingles** (`_FULL_TRANSLATIONS["en"][key]`)
4. **Chave bruta** (a propria string da chave, como ultimo recurso)

Os arquivos JSON sao carregados uma unica vez no momento do import. A substituicao
dinamica de placeholders (ex. `{home_dir}`) e aplicada durante o carregamento.

### Adicionando um Novo Idioma

1. Copiar `en.json` para `{language_code}.json` (ex. `fr.json`)
2. Traduzir todos os 137 valores (manter as chaves inalteradas)
3. Registrar o novo codigo de idioma em `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Adicionar botao de alternancia de idioma em `apps/qt_app/screens/settings_screen.py`
5. Atualizar `core/localization.py` se os dicionarios fallback Kivy precisarem do novo idioma

### Adicionando uma Nova Chave

1. Adicionar o par chave-valor a **todos os tres** arquivos JSON (`en.json`, `pt.json`, `it.json`)
2. Referenciar no codigo via `i18n.get_text("your_new_key")`
3. Se a chave for critica para navegacao, adiciona-la tambem a `_HARDCODED_EN` em `i18n_bridge.py`

## `maps/` — Imagens de Radar

Imagens de radar em formato DDS (DirectDraw Surface) para os mapas competitivos de
CS2. Utilizadas pelo Tactical Viewer para renderizacao 2D aerea das posicoes dos
jogadores, trajetorias de granadas e replays de rounds.

### Cobertura

11 imagens de radar cobrindo todos os mapas do pool competitivo atual:

| Mapa | Arquivo(s) | Multi-nivel |
|------|------------|-------------|
| Ancient | `de_ancient_radar.dds` | Nao |
| Cache | `de_cache_radar.dds` | Nao |
| Dust2 | `de_dust2_radar.dds` | Nao |
| Inferno | `de_inferno_radar.dds` | Nao |
| Mirage | `de_mirage_radar.dds` | Nao |
| Nuke | `de_nuke_radar.dds`, `de_nuke_lower_radar.dds` | Sim |
| Overpass | `de_overpass_radar.dds` | Nao |
| Train | `de_train_radar.dds` | Nao |
| Vertigo | `de_vertigo_radar.dds`, `de_vertigo_lower_radar.dds` | Sim |

### Sistema de Coordenadas dos Mapas

As imagens de radar sao pareadas com arquivos de configuracao espacial em outras partes do projeto:

- **`data/map_config.json`** — `pos_x`, `pos_y` (origem do sistema de coordenadas Valve),
  `scale` (pixels por unidade, tipicamente de 4.0 a 7.0), e opcional `z_cutoff` para mapas multi-nivel
- **`data/map_tensors.json`** — Coordenadas de bombsite e spawn como tensores para o motor de analise espacial
- **`backend/analysis/engagement_range.py`** — Posicoes nomeadas (ex. "A Site", "Mid Doors")
  para saida de coaching legivel por humanos

### Adicionando um Novo Mapa

1. Posicionar `de_{mapname}_radar.dds` em `assets/maps/`
2. Adicionar configuracao espacial a `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Adicionar definicoes de tensores a `data/map_tensors.json` (coordenadas bombsite/spawn)
4. Adicionar posicoes nomeadas a `backend/analysis/engagement_range.py`
5. Para mapas multi-nivel, adicionar uma variante `_lower_radar.dds` e definir `z_cutoff` na configuracao

## Bundling (PyInstaller)

Todos os arquivos neste diretorio sao incluidos no executavel congelado via
`packaging/cs2_analyzer_win.spec`:

```python
datas += [('Programma_CS2_RENAN/assets/i18n', 'assets/i18n')]
datas += [('Programma_CS2_RENAN/assets/maps', 'assets/maps')]
```

Em tempo de execucao, os caminhos sao resolvidos atraves de `get_resource_path()`,
que verifica `sys._MEIPASS` (congelado) antes de recorrer ao caminho da arvore de codigo-fonte.

## Pontos de Integracao

| Consumidor | Recurso | Padrao de Acesso |
|------------|---------|-----------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` no import |
| `apps/qt_app/screens/tactical_screen.py` | `maps/*.dds` | `get_resource_path("assets/maps")` sob demanda |
| `core/map_manager.py` | `maps/*.dds` | Transformacao de coordenadas com `map_config.json` |
| `reporting/visualizer.py` | `maps/*.dds` | Renderizacao de overlay para heatmaps e PDF |

## Notas de Desenvolvimento

- Arquivos DDS nao devem exceder 4 MB cada (resolucao maxima de 2048x2048)
- Arquivos JSON devem ser UTF-8 valido sem BOM (byte-order mark)
- O dicionario fallback `_HARDCODED_EN` em `i18n_bridge.py` contem apenas chaves
  criticas de navegacao; mantenha-o sincronizado ao renomear ou remover chaves dos arquivos JSON
- Os valores de coordenadas dos mapas originam-se dos arquivos do jogo CS2 (`resource/overviews/*.txt`)
- O hook pre-commit `check-json` valida a sintaxe JSON em cada commit
- Todas as 137 chaves devem estar presentes em cada arquivo de idioma; chaves ausentes degradam
  com graca para o ingles, mas indicam uma traducao incompleta

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Assets — Recursos Estaticos

> **Autoridade:** Regra 3 (Frontend & UX)

Este diretorio contem todos os recursos estaticos consumidos pela aplicacao em tempo
de execucao. Os caminhos sao resolvidos atraves de `core/config.py:get_resource_path()`,
que abstrai a diferenca entre a arvore de codigo-fonte de desenvolvimento e os executaveis
congelados (as traducoes `i18n/`, o stack tipografico `fonts/` e os overlays `map_zones/`
sao incluidos na distribuicao PyInstaller). Nada neste diretorio e gerado em tempo de
execucao; cada arquivo e versionado no controle de versao e tratado como imutavel apos
o lancamento.

## Estrutura do Diretorio

```
assets/
├── fonts/                    # Fontes de display (escaneadas automaticamente pelo motor de temas)
│   ├── Inter-*.ttf          # Inter v4.1 builds estaticas (4 pesos)
│   ├── JetBrainsMono-*.ttf  # JetBrains Mono v2.304 (4 pesos)
│   ├── SpaceGrotesk-*.ttf   # Space Grotesk 2.0.0 (3 pesos)
│   └── README.txt           # Fontes, licencas (OFL-1.1), mapeamento de papeis
├── i18n/                     # Internacionalizacao (traducoes)
│   ├── en.json              # Ingles (584 chaves) — primario/fallback
│   ├── pt.json              # Portugues Brasileiro
│   └── it.json              # Italiano
├── map_zones/                # Overlays de zonas nomeadas para o visualizador tatico
│   └── de_mirage.json       # Retangulos de zona (normalizados 0-1) para Mirage
├── maps/                     # Imagens de radar dos mapas CS2
│   ├── de_ancient_radar.dds
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
| `fonts/*.ttf` | Fonte TTF | 11 arquivos | Stack tipografico design-atlas (Inter, Space Grotesk, JetBrains Mono builds estaticas, todas OFL-1.1); o motor de temas escaneia automaticamente qualquer `.ttf`/`.otf` aqui na inicializacao |
| `fonts/README.txt` | Texto | 1 arquivo | Fontes dos fonts, versoes, licencas e mapeamento de papeis (corpo UI: Inter; display: Space Grotesk; mono: JetBrains Mono) |
| `i18n/en.json` | JSON | 584 chaves | Strings de UI em Ingles (idioma primario e fallback) |
| `i18n/pt.json` | JSON | 584 chaves | Strings de UI em Portugues Brasileiro |
| `i18n/it.json` | JSON | 584 chaves | Strings de UI em Italiano |
| `map_zones/de_mirage.json` | JSON | 1 arquivo | Retangulos de zona nomeada para o overlay do visualizador tatico Qt (somente Mirage por enquanto) |
| `maps/de_*_radar.dds` | Imagem DDS | 10 arquivos | Imagens radar aereas (1024x1024) para mapas competitivos CS2 |

## `i18n/` — Arquivos de Localizacao

Arquivos JSON contendo cada string visivel ao usuario na aplicacao. O esquema de
chaves e identico em todos os arquivos de idioma: quando uma chave existe em
`en.json`, ela tambem deve existir em `pt.json` e `it.json`. Se uma traducao estiver
faltando, o fallback em ingles e utilizado automaticamente pelo `QtLocalizationManager`.

### Categorias de Chaves (584 chaves no total)

| Categoria | Chaves de Exemplo | Finalidade |
|-----------|-------------------|------------|
| Navegacao | `dashboard`, `coaching`, `settings`, `profile` | Rotulos da barra lateral |
| Coaching | `coach_status`, `recent_insights`, `ask_your_coach`, `coach_thinking` | Texto da tela Coach |
| Configuracoes | `visual_theme`, `language`, `font_size`, `ingestion_mode` | Tela de Configuracoes |
| Perfil | `ingame_name`, `bio`, `pro_profile` | Campos do perfil do usuario |
| Tatica | `tactical_analyzer`, `tactical.tick`, `tactical.bomb_planted` | Tela e HUD do visualizador tatico (chaves com ponto `tactical.*`) |
| Detalhe de Partida | `md_title`, `md_tab_overview`, `md_tab_economy` | Tela de detalhe de partida (prefixo `md_*`) |
| Dialogos | `dialog_edit_profile`, `dialog_save`, `dialog_close` | Mensagens de dialogo |
| Steam/FaceIT | `steam_integration`, `steam_key_hint`, `faceit_hint` | Telas de integracao |
| Ajuda | `help_center`, `search_placeholder`, `select_topic` | Tela do Centro de Ajuda |
| Wizard | `wizard_intro_title`, `wizard_step1_title`, `wizard_finish_text` | Wizard de configuracao inicial |
| Graficos | `chart_caption_you`, `chart_economy_title`, `chart_round_axis` | Legendas e rotulos de eixo dos graficos |

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
2. Traduzir todos os 584 valores (manter as chaves inalteradas)
3. Registrar o novo codigo de idioma em `apps/qt_app/core/i18n_bridge.py` (`_load_json_translations`)
4. Adicionar botao de alternancia de idioma em `apps/qt_app/screens/settings_screen.py`
5. Atualizar `core/localization.py` se os dicionarios fallback hardcoded legacy (`TRANSLATIONS`) precisarem do novo idioma

### Adicionando uma Nova Chave

1. Adicionar o par chave-valor a **todos os tres** arquivos JSON (`en.json`, `pt.json`, `it.json`)
2. Referenciar no codigo via `i18n.get_text("your_new_key")`
3. Se a chave for critica para navegacao, adiciona-la tambem a `_HARDCODED_EN` em `i18n_bridge.py`

## `maps/` — Imagens de Radar

Imagens de radar em formato DDS (DirectDraw Surface) (1024x1024) para os mapas competitivos
de CS2. Sao referenciadas pelo campo `image_file` em `data/map_tensors.json` e consumidas
pelo visualizador de relatorios para renderizacao de overlay de heatmap.
(O visualizador tatico Qt renderiza a partir das panoramicas PNG em `PHOTO_GUI/maps/`.)

### Cobertura

10 imagens de radar cobrindo os mapas do pool competitivo:

| Mapa | Arquivo(s) | Multi-nivel |
|------|------------|-------------|
| Ancient | `de_ancient_radar.dds` | Nao |
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
  `scale` (pixels por unidade, tipicamente de 4.0 a 7.0), e `z_cutoff`/`levels` para mapas
  multi-nivel; utilizado por `core/spatial_data.py` para transformacoes de coordenadas
- **`data/map_tensors.json`** — Coordenadas de bombsite e spawn como tensores para o motor
  de analise espacial, mais a referencia de radar `image_file` por mapa
- **`core/map_callouts.py`** — Registro `NamedPosition` (161 posicoes em 9 mapas,
  ex. "A Site", "Mid Doors") para saida de coaching legivel por humanos; re-exportado
  atraves de `backend/analysis/engagement_range.py`

### Adicionando um Novo Mapa

1. Posicionar `de_{mapname}_radar.dds` em `assets/maps/`
2. Adicionar configuracao espacial a `data/map_config.json` (`pos_x`, `pos_y`, `scale`, `landmarks`)
3. Adicionar definicoes de tensores a `data/map_tensors.json` (coordenadas bombsite/spawn, `image_file`)
4. Adicionar posicoes nomeadas a `core/map_callouts.py`
5. Para mapas multi-nivel, adicionar uma variante `_lower_radar.dds` e definir `z_cutoff` na configuracao
6. Opcionalmente adicionar um arquivo de overlay de zona nomeada a `assets/map_zones/` (veja abaixo)

## `map_zones/` — Overlays de Zona do Visualizador Tatico

Arquivos JSON com retangulos de zona nomeada para o visualizador tatico Qt. Cada arquivo
contem uma lista `zones` de retangulos normalizados 0-1 no painel do mapa (`name`, `x`, `y`,
`w`, `h`, `label`, flag opcional `major` para os rotulos proeminentes A/B/MID).

- Atualmente um arquivo: `de_mirage.json` (9 zonas)
- Carregado por `apps/qt_app/widgets/tactical/map_widget.py` (`load_map_zones()`),
  que aceita tanto nomes curtos (`mirage`) quanto longos (`de_mirage`) e degrada para
  nenhum overlay (`[]`) para mapas sem um arquivo de zona
- Resolvido atraves de `get_resource_path()` e incluido na build congelada

## Bundling (PyInstaller)

As traducoes, fontes e overlays de zona sao incluidos no executavel congelado via
`packaging/cs2_analyzer_win.spec` (na raiz do repositorio):

```python
(str(APP_DIR / "assets" / "i18n"), "Programma_CS2_RENAN/assets/i18n"),
(str(APP_DIR / "assets" / "fonts"), "Programma_CS2_RENAN/assets/fonts"),
(str(APP_DIR / "assets" / "map_zones"), "Programma_CS2_RENAN/assets/map_zones"),
```

As imagens radar DDS em `assets/maps/` nao sao listadas nos `datas` do spec (o
visualizador tatico congelado usa as panoramicas PNG em `PHOTO_GUI/maps/`, que sao
incluidas separadamente). Em tempo de execucao, os caminhos sao resolvidos atraves de
`get_resource_path()`, que verifica `sys._MEIPASS` (congelado) antes de recorrer ao
caminho da arvore de codigo-fonte.

## Pontos de Integracao

| Consumidor | Recurso | Padrao de Acesso |
|------------|---------|-----------------|
| `apps/qt_app/core/i18n_bridge.py` | `i18n/*.json` | `get_resource_path("assets/i18n")` no import |
| `apps/qt_app/core/theme_engine.py` | `fonts/*.ttf` / `*.otf` | Escaneados e registrados automaticamente em `register_fonts()` (apos as fontes legacy `PHOTO_GUI/`) |
| `apps/qt_app/widgets/tactical/map_widget.py` | `map_zones/*.json` | `load_map_zones()` via `get_resource_path()` por mapa |
| `reporting/visualizer.py` | `maps/*` | Carrega a imagem do mapa referenciada por `data/map_tensors.json` (`image_file`) para renderizacao de heatmap e overlay |

## Notas de Desenvolvimento

- Arquivos DDS nao devem exceder 4 MB cada (resolucao maxima de 2048x2048)
- Arquivos JSON devem ser UTF-8 valido sem BOM (byte-order mark)
- O dicionario fallback `_HARDCODED_EN` em `i18n_bridge.py` contem apenas chaves
  criticas de navegacao; mantenha-o sincronizado ao renomear ou remover chaves dos arquivos JSON
- Os valores de coordenadas dos mapas originam-se dos arquivos do jogo CS2 (`resource/overviews/*.txt`)
- O hook pre-commit `check-json` valida a sintaxe JSON em cada commit
- Todas as 584 chaves devem estar presentes em cada arquivo de idioma; chaves ausentes degradam
  com graca para o ingles, mas indicam uma traducao incompleta
- As fontes sao builds estaticas sob a SIL Open Font License 1.1; fontes e versoes sao
  documentadas em `fonts/README.txt` (`JetBrainsMono-Regular.ttf` tambem esta presente
  sob `PHOTO_GUI/` como fonte legacy registrada pelo motor de temas)

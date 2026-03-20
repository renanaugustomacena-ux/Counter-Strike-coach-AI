> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Assets — Recursos Estaticos

> **Autoridade:** Rule 3 (Frontend & UX)

Este diretorio contem os recursos estaticos utilizados pela aplicacao em tempo de execucao. Estes arquivos sao incluidos na distribuicao PyInstaller.

## Estrutura do Diretorio

assets/
├── i18n/                     # Internacionalizacao (traducoes)
│   ├── en.json              # Ingles (137 chaves) — primario/fallback
│   ├── pt.json              # Portugues Brasileiro
│   └── it.json              # Italiano
└── maps/                     # Imagens de radar dos mapas CS2
    ├── de_ancient_radar.dds ... (11 arquivos DDS)

## i18n/ — Arquivos de Localizacao

Arquivos JSON contendo todas as strings de UI visiveis ao usuario. O esquema de chaves e compartilhado entre todos os idiomas.

### Categorias de Chaves (137 chaves no total)

| Categoria | Chaves de Exemplo | Finalidade |
|-----------|-------------------|------------|
| Navegacao | `dashboard`, `coach`, `match_history` | Rotulos da barra lateral |
| Coaching | `coaching_insights`, `severity_high` | Texto da tela Coach |
| Configuracoes | `theme`, `language`, `demo_path` | Tela de Configuracoes |
| Perfil | `player_name`, `bio`, `role` | Campos do perfil do usuario |
| Tatica | `tactical_viewer`, `playback_speed` | Tela Tatica |

### Adicionando um Novo Idioma

1. Copiar `en.json` para `{language_code}.json`
2. Traduzir todos os valores (manter as chaves inalteradas)
3. Registrar em `apps/qt_app/core/i18n_bridge.py`
4. Adicionar botao de alternancia de idioma nas configuracoes

## maps/ — Imagens de Radar

Imagens de radar em formato DDS para os mapas competitivos de CS2. 11 imagens cobrindo todos os mapas do pool competitivo, incluindo multi-nivel (Nuke superior+inferior, Vertigo superior+inferior).

## Notas de Desenvolvimento

- Arquivos DDS nao devem exceder 4MB cada
- Arquivos JSON devem ser UTF-8 valido sem BOM
- Os valores de coordenadas dos mapas vem dos arquivos do jogo CS2

# `apps/qt_app/widgets/components/` — Primitivas genericas de UI

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Primitivas de UI genericas e reutilizaveis consumidas por multiplas telas. Cada componente faz uma coisa, e ciente do tema (le de `core/design_tokens.py`), e componentes interativos expoem seu estado via `Signal`s.

## Inventario de arquivos

| Arquivo | Componente | Finalidade |
|---------|------------|------------|
| `__init__.py` | — | Marcador de pacote; reexporta um subconjunto dos componentes publicos. |
| `card.py` | `Card` | Container base de superficie elevada com slots opcionais de titulo + corpo. Cinco variantes de profundidade (`flat`, `raised`, `highlighted`, `floating`, `frosted`); `frosted` usa um preenchimento semi-transparente aproximando backdrop blur. |
| `db_record_card.py` | `DbRecordCard` | Card raised mostrando um registro de banco de dados: titulo bold + caption SQL mono + grade chave/valor mono. Um valor pode carregar um nome de token semantico (`success`, `info`, ...) para colori-lo. |
| `delta_chip.py` | `DeltaChip` | Anotacao de delta relativa ao benchmark (`▲ +0.09 vs 47-match avg`). Comeca escondido; um delta zero ou desconhecido nunca e renderizado. |
| `drivers_list.py` | `DriversList` | Lista vertical de linhas (severidade, texto) — quadrado 8px colorido semanticamente + texto body. Severidade ∈ {`success`, `warning`, `error`, `info`}. |
| `empty_state.py` | `EmptyState` | Placeholder amigavel mostrado quando uma lista / tabela / grafico nao tem dados. Icone ou ilustracao, titulo, CTAs opcionais mais linha ghost link; tambem tem modo loading-skeleton. |
| `filter_chip.py` | `FilterChip` | Pill de filtro selecionavel — clique para alternar, emite `toggled(bool)`; badge de contagem trailing opcional. Usado por match history e pro comparison. |
| `focus_insight.py` | `FocusInsightCard` | Card par na home page de `LastMatchHeroCard` — destaca uma area de foco de coaching com um CTA ghost (`open_clicked(str)`); tem estado vazio. |
| `hero_stats_strip.py` | `HeroStatsStrip` | Faixa horizontal de blocos de stat em formato grande (numero display + caption, coloridos por sentimento). |
| `icon_widget.py` | `IconWidget` | Container de icone QPainterPath com coloracao ciente do tema. Envolve `core/icons.py` (`IconProvider`). |
| `last_match_hero.py` | `LastMatchHeroCard` | Card hero da home page resumindo a partida mais recente, com um `MiniSparkline` de tendencia de rating; o estado vazio carrega um CTA de analise. |
| `map_tile.py` | `MapTile` | Tile de desempenho por mapa: nome do mapa, linha de rating (cor + label de acessibilidade), linha ADR / K/D, contagem de partidas, barra de preenchimento de rating na parte inferior. Totalmente desenhado com QPainter. |
| `match_mini_card.py` | `MatchMiniCard` | Card preview de partida compacto e clicavel (faixa "Recent Matches" na home). Emite `clicked(demo_name)`. |
| `match_row_card.py` | `MatchRowCard` | Linha de partida ampla com preview de stats (linhas de match history); linhas pro substituem com linha jogador + evento. Emite `clicked(demo_name)`. |
| `metric_bar_row.py` | `MetricBarRow` | Metrica com label e barra de preenchimento proporcional colorida (linhas da grade HLTV 2.0 do Match Detail). |
| `mini_link_card.py` | `MiniLinkCard` | Pequeno card de navegacao clicavel — "Titulo →" bold + caption em uma linha. Emite `clicked`. |
| `mono_footer.py` | `MonoFooter` | Linha de anotacao terciaria mono na parte inferior da tela nomeando a fonte de dados. |
| `nav_sidebar.py` | `NavSidebar` | Sidebar de navegacao a esquerda com icones de rota + labels. Emite `nav_clicked(str)`; comprimivel 220px ↔ 60px. |
| `numbered_step.py` | `NumberedStep` | Linha de step numerada (Getting Started): circulo acento preenchido com numero do step + titulo bold + descricao. |
| `pro_badge.py` | `ProBadge` | Badge mono em formato pill ("PRO" por padrao) com recoloracao opcional por lado CT / T via `set_side()`. |
| `progress_ring.py` | `ProgressRing` | Indicador circular de progresso com texto percentual centralizado opcional; presets de tamanho `SMALL` / `DEFAULT` / `COACH` / `HERO`. |
| `section_header.py` | `SectionHeader` | Linha padronizada de titulo de secao (titulo + subtitulo opcional + widget de acao opcional). |
| `stat_badge.py` | `StatBadge` | Valor de stat proeminente com label embaixo (padrao scope.gg); coloracao semantica + seta de tendencia opcional. |
| `status_chip.py` | `StatusChip` | Pill colorida de status (`online`, `offline`, `warning`, `neutral`). Inclui cor e label, nunca apenas cor. |
| `stepper.py` | `Stepper` | Indicador horizontal de steps (pontos + barras conectoras, labels opcionais) para o wizard de primeiro uso. Emite `step_changed(int)`. |
| `tip_box.py` | `TipBox` | Callout com contorno tracejado: titulo bold em cor info + corpo secundario. |
| `toggle_switch.py` | `ToggleSwitch` | Widget animado de switch booleano estilo iOS. |

## Design system

Todos os componentes consomem tokens de `core/design_tokens.py` (gerados de `design/tokens/design-tokens.json`). Cores, espacamento, raios e tipografia sao referenciados por nome — nunca hard-coded. O theming funciona assim:

- Tres conjuntos de tokens (`CS2`, `CSGO`, `CS1.6`) compartilham um unico contrato estrutural; `theme_engine.apply_theme()` troca o conjunto ativo.
- A unica fonte de stylesheet e `themes/base.qss.template`, renderizada por tema por `core/qss_generator.py` — nao ha arquivos QSS por tema.
- A `QPalette` e derivada dos mesmos tokens, entao widgets que contornam o QSS continuam coerentes.
- Trocas de tema (signal `theme_changed`) re-estilizam todos os componentes consistentemente.

## Convencoes

| Convencao | Justificativa |
|-----------|---------------|
| Um componente por arquivo | Facil de achar; arquivos pequenos; seguro de extrair. |
| API publica via `Signal`s, nao callbacks | Desacopla widget da tela; testavel via `QSignalSpy`. |
| Cor de status sempre acompanhada de texto ou icone | Nunca apenas cor; ajuda usuarios com daltonismo (WCAG 1.4.1). |
| Estados hover / focus / active explicitos | Evite o "default Tailwind look" — torne o estado visivel. |

## Adicionando um componente

1. Coloque o arquivo aqui com uma unica definicao de classe.
2. Herde da menor classe Qt aplicavel (`QWidget`, `QFrame`, `QLabel`).
3. Puxe cores / espacamento / tipografia de `core/design_tokens`.
4. Exponha estado via `Signal`s.
5. Adicione uma entrada a tabela de inventario acima.
6. Se o componente for ciente do tema, resolva cores a partir do conjunto de tokens ativo (`get_tokens()`) ou conecte-se a `theme_engine.theme_changed`.

## Relacionados

- Design tokens: `apps/qt_app/core/design_tokens.py`
- Troca de tema: `apps/qt_app/core/theme_engine.py`
- Template QSS: `apps/qt_app/themes/base.qss.template` (renderizado por `core/qss_generator.py`)
- Widgets especificos de dominio: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Pai: `apps/qt_app/widgets/README.md`

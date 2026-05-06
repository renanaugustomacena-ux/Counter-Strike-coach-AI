# `apps/qt_app/widgets/components/` — Primitivas genéricas de UI

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Primitivas de UI genéricas e reutilizáveis consumidas por múltiplas telas. Cada componente faz uma coisa, é ciente do tema (lê de `core/design_tokens.py`) e expõe seu estado via `Signal`s.

## Inventário de arquivos

| Arquivo | Componente | Finalidade |
|---------|------------|------------|
| `__init__.py` | — | Marcador de pacote; reexporta os componentes públicos. |
| `card.py` | `Card` | Container base de superfície elevada com slots opcionais de título + corpo. Suporta efeito frosted-glass em macOS / Windows 11 com fallback flat. |
| `empty_state.py` | `EmptyState` | Placeholder amigável mostrado quando uma lista / tabela / gráfico não tem dados. Inclui ícone, título, CTA opcional. |
| `filter_chip.py` | `FilterChip` | Pill de filtro selecionável — clique para alternar, emite `toggled(bool)`. Usado por match history e pro comparison. |
| `focus_insight.py` | `FocusInsight` | Variante de card para o focus insight da home page (um insight de coaching proeminente com ícone de severidade). |
| `hero_stats_strip.py` | `HeroStatsStrip` | Faixa horizontal de métricas em formato grande (rating, K/D, ADR, KAST). |
| `icon_widget.py` | `IconWidget` | Container de ícone SVG com colorização ciente do tema. Envolve `core/svg_icon_provider.py`. |
| `last_match_hero.py` | `LastMatchHero` | Card hero da home page resumindo a partida mais recente. |
| `match_mini_card.py` | `MatchMiniCard` | Card compacto de resumo de partida (uma linha em match history). |
| `match_row_card.py` | `MatchRowCard` | Card expandido de partida com preview de stats (usado na lista hero de match history). |
| `nav_sidebar.py` | `NavSidebar` | Sidebar de navegação à esquerda com ícones + labels de rota. Inscrito em `app_state.routeChanged`. |
| `progress_ring.py` | `ProgressRing` | Indicador circular de progresso com label central opcional. |
| `section_header.py` | `SectionHeader` | Linha padronizada de título de seção (título + subtítulo opcional + botão de ação opcional). |
| `stat_badge.py` | `StatBadge` | Pequena pill de label + valor (por exemplo, `K/D 1.18`, `ADR 78`). |
| `status_chip.py` | `StatusChip` | Pill colorida de status (`success`, `warning`, `error`, `info`). Inclui cor e label, nunca apenas cor. |
| `stepper.py` | `Stepper` | Input numérico tipo stepper (`-` / valor / `+`). |
| `toggle_switch.py` | `ToggleSwitch` | Widget animado de switch booleano. |

## Design system

Todos os componentes consomem tokens de `core/design_tokens.py`. Cores, espaçamento, raios e tipografia são referenciados por nome — nunca hard-coded. Isso garante:

- Trocas de tema (signal `themeChanged`) re-renderizam todos os componentes consistentemente.
- Mudanças na escala tipográfica se propagam sem edições por widget.
- Modo claro / escuro (quando adicionado) requer mudanças apenas no arquivo de tokens.

## Convenções

| Convenção | Justificativa |
|-----------|---------------|
| Um componente por arquivo | Fácil de achar; arquivos pequenos; seguro de extrair. |
| API pública via `Signal`s, não callbacks | Desacopla widget da tela; testável via `QSignalSpy`. |
| `setAccessibleName()` em todo componente interativo | Conformidade WCAG + suporte a leitor de tela. |
| Cor de status sempre acompanhada de texto ou ícone | Nunca apenas cor; ajuda usuários com daltonismo (WCAG 1.4.1). |
| Estados hover / focus / active explícitos | Evite o "default Tailwind look" — torne o estado visível. |

## Adicionando um componente

1. Coloque o arquivo aqui com uma única definição de classe.
2. Herde da menor classe Qt aplicável (`QWidget`, `QFrame`, `QLabel`).
3. Puxe cores / espaçamento / tipografia de `core/design_tokens`.
4. Exponha estado via `Signal`s.
5. Adicione uma entrada à tabela de inventário acima.
6. Se o componente for ciente do tema, inscreva-se em `theme_engine.themeChanged`.

## Relacionados

- Design tokens: `apps/qt_app/core/design_tokens.py`
- Troca de tema: `apps/qt_app/core/theme_engine.py`
- Widgets específicos de domínio: `widgets/charts/`, `widgets/coaching/`, `widgets/tactical/`
- Pai: `apps/qt_app/widgets/README.md`

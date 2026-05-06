# `apps/qt_app/widgets/tactical/` — Widgets do Tactical Viewer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Propósito

Widgets customizados exclusivos da tela do **Tactical Viewer**. Eles renderizam o replay 2D do mapa, a sidebar ao vivo dos jogadores e o scrubber da timeline. Nenhum deles é reutilizável em outro lugar — todos são fortemente acoplados ao estado de playback, às projeções da Ghost AI e aos destaques do chronovisor.

## Inventário de arquivos

| Arquivo | Widget | Propósito |
|------|--------|---------|
| `__init__.py` | — | Marcador de pacote. |
| `map_widget.py` | `MapWidget` | O "Living Map" — renderizador 2D acelerado por GPU para posições dos jogadores, trajetórias de granadas, marcadores de kill e projeções da Ghost AI. Inscreve-se em `TacticalPlaybackViewModel.tickAdvanced`. |
| `player_sidebar.py` | `PlayerSidebar` | Roster de jogadores dos dois times com exibição ao vivo de HP / armor / arma / economia. Usa pooling de widgets (reuso de objetos) para que o refresh por tick não aloque memória. |
| `timeline_widget.py` | `TimelineWidget` | Scrubber interativo com marcadores de evento codificados por cor (kills, plants, defuses, transições de round). Clique e arraste para navegar. |

## Arquitetura

```
TacticalViewerScreen
    |
    +-- MapWidget         <-- TacticalPlaybackViewModel.tickAdvanced
    |   +-- TacticalGhostViewModel.predictionReady       (overlay da Ghost AI)
    |   +-- TacticalChronovisorViewModel.criticalMoment  (marcadores de destaque)
    |
    +-- PlayerSidebar     <-- TacticalPlaybackViewModel.playersUpdated
    |
    +-- TimelineWidget    <-- TacticalPlaybackViewModel.timelineReady
                          --> TacticalPlaybackViewModel.seekRequested
```

## Considerações de performance

### MapWidget

O mapa renderiza **a cada tick** durante o playback (64 ticks por segundo). Gargalos congelariam toda a thread de UI. Mitigações:

- A textura do mapa é carregada **uma vez** por troca de mapa, não por tick.
- As posições dos jogadores são agrupadas em uma única chamada `QPainter.drawPoints()`.
- Trajetórias de granadas são pré-computadas quando uma nade é jogada e ficam em cache até a detonação.
- Marcadores de kill desaparecem por `QTimer` em vez de serem redesenhados a cada tick.

### PlayerSidebar

- 10 cards de jogador (5 por time) reusam instâncias do widget `PlayerCard` em vez de criar / destruir por tick (pooling de widgets — mesmo padrão do app legacy em Kivy).
- Barras de health / armor usam draw direto via `QPainter` dentro de um `paintEvent` em vez de `QProgressBar` aninhados, para evitar churn de layout.

### TimelineWidget

- Marcadores de evento são renderizados em um cache offscreen `QPixmap` uma vez por partida e copiados (blit) para o widget no `paintEvent`.
- O cursor (tick atual) é desenhado separadamente, por cima, para que o movimento do cursor não invalide o cache dos marcadores.

## Acessibilidade

- Os cards de jogador incluem resumos amigáveis para screen reader (`setAccessibleName("Player 'Renan' — CT — 100 HP — 4750 equipment")`).
- Marcadores de evento na timeline carregam descrições textuais, então um screen reader anuncia "kill at 1:23 in round 12" em vez de apenas a posição de um ícone.
- Eventos codificados por cor (kill = vermelho, plant = amarelo, defuse = azul) são pareados com diferenças de forma / posição (kill em meia altura, plant / defuse em altura cheia) para que usuários com daltonismo ainda consigam interpretar o estado (WCAG 1.4.1).

## Integração

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- MapWidget
    +-- PlayerSidebar
    +-- TimelineWidget
            |
            +-- ViewModels em apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- core/playback_engine.PlaybackEngine
                    +-- core/qt_playback_engine.QtPlaybackEngine (timer Qt)
                    +-- backend/nn/inference/ghost_engine.GhostEngine
```

## Não faça

- Não importe estes widgets de telas que não sejam táticas — eles assumem um contexto de playback que não existe em outro lugar.
- Não aloque `QPixmap` / `QImage` dentro de `paintEvent` — pré-aloque e mantenha em cache.
- Não se inscreva em sinais de alta frequência a partir da thread de UI sem batching — 64 ticks/s × N inscritos congelam o app.

## Relacionados

- Cluster de ViewModels táticos: `apps/qt_app/viewmodels/tactical_vm.py`
- Engine de playback: `Programma_CS2_RENAN/core/playback_engine.py`
- Inferência da Ghost AI: `Programma_CS2_RENAN/backend/nn/inference/ghost_engine.py`
- Assets de mapa: `Programma_CS2_RENAN/assets/maps/`
- Pacote pai: `apps/qt_app/widgets/README.md`

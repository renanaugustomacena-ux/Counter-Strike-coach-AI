# `apps/qt_app/widgets/tactical/` — Widgets do Tactical Viewer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Proposito

Widgets customizados exclusivos da tela do **Tactical Viewer**. Eles renderizam o replay 2D do mapa, a sidebar ao vivo dos jogadores e o scrubber da timeline. Nenhum deles e reutilizavel em outro lugar — todos sao fortemente acoplados ao estado de playback, as projecoes da Ghost AI e aos destaques do chronovisor.

## Inventario de arquivos

| Arquivo | Widget | Proposito |
|---------|--------|-----------|
| `__init__.py` | — | Marcador de pacote. |
| `_paint_utils.py` | — | Helpers QPainter compartilhados para os widgets taticos (`with_alpha()` — copia um `QColor` com um dado alpha). |
| `map_widget.py` | `TacticalMapWidget` | O "Living Map" — renderizador 2D de mapa baseado em QPainter (carrega overviews `PHOTO_GUI/maps/*.png`) para posicoes dos jogadores e trilhas, callouts de zona, estado C4/bomba, trajetorias de granadas e overlays de detonacao, projecoes da Ghost AI, o quadro de placar e o overlay Ghost Mode frame-14 (caminhos duplos voce-vs-ghost, pontos de divergencia, legenda — `set_ghost_overlay()`). Dirigido por frame via `TacticalPlaybackVM.frame_updated`; emite `selected_player_changed`. |
| `player_sidebar.py` | `PlayerSidebar` | Coluna de roster de time unico (a tela instancia duas — CT e T): cabecalho de time com contagem de vivos e dinheiro do time, sobre cards de roster frame-13 com HP / armadura / arma / economia / utility inline. Reutiliza widgets por jogador para que o refresh por tick nao aloque. |
| `timeline_widget.py` | `TimelineWidget` | Scrubber interativo com marcadores de evento codificados por cor (kills, plants, defuses), divisores de round, faixa de caption mono `t={tick}`, e glifos de momento do chronovisor diferenciados por tipo (estrela = critico/erro, diamante = clutch, circulo = jogada; click num glifo busca o tick de inicio do momento). Clique e arraste para navegar. |

## Arquitetura

```
TacticalViewerScreen
    |
    +-- TacticalMapWidget  <-- TacticalPlaybackVM.frame_updated (via a tela)
    |   +-- projecoes ghost de TacticalGhostVM.predict_ghosts (via a tela)
    |
    +-- PlayerSidebar x2 (CT / T)  <-- TacticalPlaybackVM.frame_updated (via a tela)
    |
    +-- TimelineWidget     <-- TacticalPlaybackVM.current_tick_changed / total_ticks_changed
                           <-- TacticalChronovisorVM.scan_complete  (glifos de momento, via a tela)
                           <-- TacticalChronovisorVM.navigate_to    (seek, via a tela)
                           --> seek via TacticalPlaybackVM
```

## Consideracoes de performance

### TacticalMapWidget

O mapa repinta **a cada frame** durante o playback, entao o trabalho por frame deve ser minimo:

- O pixmap do mapa escalado fica em cache e e recalculado apenas em redimensionamento ou troca de mapa — os repaints por frame o reutilizam.
- Quando nenhuma overview de mapa e encontrada, `paintEvent` desenha um retangulo escuro de fallback em vez de falhar.

### PlayerSidebar

- As linhas de jogador reutilizam instancias de widget por jogador (atualizadas in-place, entradas obsoletas removidas) em vez de criar / destruir por tick.

### TimelineWidget

- Marcadores e o cursor sao desenhados em `paintEvent`; mantenha as alocacoes por frame fora do caminho de desenho.

## Acessibilidade

- Siga a convencao do projeto: acompanhe cada estado codificado por cor (marcadores kill / plant / defuse, barras de HP) com diferencas de texto ou forma para que usuarios com daltonismo possam interpreta-lo (WCAG 1.4.1).

## Integracao

```
TacticalViewerScreen (apps/qt_app/screens/tactical_viewer_screen.py)
    +-- TacticalMapWidget
    +-- PlayerSidebar (x2)
    +-- TimelineWidget
            |
            +-- ViewModels em apps/qt_app/viewmodels/tactical_vm.py
                    |
                    +-- Programma_CS2_RENAN/core/playback_engine.PlaybackEngine
                    +-- apps/qt_app/core/qt_playback_engine.QtPlaybackEngine (timer Qt, mantido pela tela)
                    +-- backend/nn/inference/ghost_engine.GhostEngine
```

## Nao faca

- Nao importe estes widgets de telas que nao sejam taticas — eles assumem um contexto de playback que nao existe em outro lugar.
- Nao aloque `QPixmap` / `QImage` dentro de `paintEvent` — pre-aloque e mantenha em cache.
- Nao se inscreva em sinais de alta frequencia a partir da thread de UI sem batching — 64 ticks/s x N inscritos congelam o app.

## Relacionados

- Cluster de ViewModels taticos: `apps/qt_app/viewmodels/tactical_vm.py`
- Engine de playback: `Programma_CS2_RENAN/core/playback_engine.py`
- Inferencia da Ghost AI: `Programma_CS2_RENAN/backend/nn/inference/ghost_engine.py`
- Imagens de overview de mapa: `Programma_CS2_RENAN/PHOTO_GUI/maps/`
- Pacote pai: `apps/qt_app/widgets/README.md`

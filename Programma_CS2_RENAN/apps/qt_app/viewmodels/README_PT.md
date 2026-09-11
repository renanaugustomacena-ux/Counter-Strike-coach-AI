# `apps/qt_app/viewmodels/` — ViewModels MVVM

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX), Regra 1 (Corretude)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Finalidade

ViewModels no padrao Model-View-ViewModel (MVVM). Toda tela data-driven tem pelo menos uma ViewModel que detem:

1. **Carregamento de dados** a partir do backend (services, analytics, storage).
2. **Trabalho em background** (queries longas, inferencia de ML) via `core/worker.Worker` (um `QRunnable` no `QThreadPool`).
3. **Broadcast de estado** para a tela via `Signal` PySide6.
4. **Guards de staleness** — gates de reentrada `_is_loading` na maioria dos VMs, mais `cancel()` explicito (Match History) e `cancel_response()` (chat) onde trabalho em andamento deve ser abandonado na navegacao.

Nem toda tela passa por este pacote: as telas config / help nao tem VM, e as telas profile / wizard (mais o lookup de match-id do tactical viewer) executam seus poucos toques diretos no DB em um `core/worker.Worker` (veja `screens/README.md`, F-0038).

Telas permanecem finas e visuais; ViewModels permanecem grossas e headless. A logica de negocio e projetada para ser testavel no nivel ViewModel — sem necessidade de event loop do Qt (`QSignalSpy` do Qt ou mocks simples bastam); a cobertura automatizada atual e a nivel de import (`tools/headless_validator.py`).

## Inventario de arquivos

| Arquivo | ViewModel | Tela suportada | Responsabilidade |
|---------|-----------|----------------|------------------|
| `__init__.py` | — | — | Marcador de pacote. |
| `coach_vm.py` | `CoachViewModel` | Coach | Carrega as linhas `CoachingInsight` mais recentes para o jogador ativo (`insights_loaded` / `is_loading_changed` / `error_changed`). |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (painel de chat) | Dialogo multi-turno com `CoachingDialogueEngine` (Ollama). Lista de mensagens thread-safe; streaming de token via `streaming_changed`; `cancel_response()` aborta uma resposta em andamento. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Stub: verifica se existem partidas analisadas e emite uma dica de navegacao honesta (sem delta-vs-pro medido ainda). |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Carrega `PlayerMatchStats`, `RoundStats`, coaching insights, breakdown HLTV 2.0. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History, Home (lista de recentes) | Carrega a lista de partidas usuario + pro (limitado a 50 linhas); chips de filtro sao aplicados no lado da tela. `cancel()` descarta resultados stale ao sair da tela. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Tendencia de rating, stats por mapa, forcas / fraquezas, breakdown de utility. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | Comparacao de stats user-vs-pro com baselines cientes do role. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Dados do perfil do pro, partidas recentes, contexto de percentil. |
| `tactical_vm.py` | `TacticalPlaybackVM`, `TacticalGhostVM`, `TacticalChronovisorVM` | Tactical Viewer | Tres VMs coordenados: playback, overlay de ghost AI, highlights de chronovisor. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Carrega e salva campos do `PlayerProfile` (bio, role). |

## Convencoes

### Threading

Todo I/O acontece fora da thread da UI. ViewModels usam `core/worker.Worker` no `QThreadPool` global:

```python
def load_matches(self):
    self._cancel.clear()                  # threading.Event
    self.is_loading_changed.emit(True)
    worker = Worker(self._bg_load)
    worker.signals.result.connect(self._on_loaded)
    worker.signals.error.connect(self._on_error)
    QThreadPool.globalInstance().start(worker)

def cancel(self):
    self._cancel.set()
```

`cancel()` (chamado a partir do `on_leave` da tela) define o `threading.Event` para que o carregamento em background desista de forma limpa, sem tocar widgets que podem ter sido destruidos.

### Signals

Estado publico e exposto via `Signal` (PySide6) — nunca via atributos mutaveis. Telas se inscrevem; ViewModels emitem:

```python
matches_changed = Signal(list)        # payload: lista de linhas de match
error_changed = Signal(str)           # payload: razao legivel para humano
is_loading_changed = Signal(bool)     # payload: True enquanto um fetch esta em andamento
```

### Politica de singleton

ViewModels sao **per-screen-instance**, nao singletons. Cada tela constroi seu(s) proprio(s) ViewModel(s) quando e criada na inicializacao do app (telas vivem no `QStackedWidget` pela duracao da aplicacao). Singletons vazariam estado entre telas.

### Sem widgets Qt nesta camada

Importar de `PySide6.QtWidgets` aqui e code smell — ViewModels devem ser testaveis sem um QApplication ativo. Imports limitados a `PySide6.QtCore` (signals, QObject, QThreadPool).

## Armadilhas comuns

| Erro | Consequencia | Correcao |
|------|--------------|----------|
| Buscar sincronicamente em `__init__` | Bloqueia thread da UI ao entrar na tela | Adie para a primeira chamada de `refresh()` |
| Esquecer `cancel()` | Fetch stale termina numa tela destruida -> segfault | Implemente `cancel()` em toda VM com workers |
| Compartilhar uma unica session de `DatabaseManager` entre threads | Contencao de WAL no SQLite | Use `get_db_manager().get_session()` por worker |
| Emitir signals de threads worker para slots nao thread-safe | Crash em chamada cross-thread | Use connections enfileiradas (default do Qt para `Signal` entre threads) |

## Integracao

```
Tela (apps/qt_app/screens/*)
    +-- ViewModel (este pacote)
            +-- backend/services/*           (logica de negocio)
            +-- backend/reporting/analytics  (matematica do dashboard)
            +-- backend/storage/database     (singletons de persistencia)
            +-- core/worker.Worker           (execucao em background)
```

## Relacionados

- Telas: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Servicos de backend: `Programma_CS2_RENAN/backend/services/README.md`
- App pai: `apps/qt_app/README.md`

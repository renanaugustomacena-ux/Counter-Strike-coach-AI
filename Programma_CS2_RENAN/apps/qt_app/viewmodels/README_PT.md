# `apps/qt_app/viewmodels/` — ViewModels MVVM

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX), Regra 1 (Corretude)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Finalidade

ViewModels no padrão Model-View-ViewModel (MVVM). Toda tela tem pelo menos uma ViewModel que detém:

1. **Carregamento de dados** a partir do backend (services, analytics, storage).
2. **Trabalho em background** (queries longas, inferência de ML) via `core/worker.QThread`.
3. **Broadcast de estado** para a tela via `pyqtSignal` / `Signal`.
4. **Semântica de cancelamento** para que o usuário nunca espere por trabalho stale após navegação.

Telas permanecem finas e visuais; ViewModels permanecem grossas e headless. Testes para lógica de negócio acontecem no nível da ViewModel — sem necessidade de event loop do Qt (usamos `QSignalSpy` do Qt ou mocks simples).

## Inventário de arquivos

| Arquivo | ViewModel | Tela suportada | Responsabilidade |
|---------|-----------|----------------|------------------|
| `__init__.py` | — | — | Marcador de pacote. |
| `coach_vm.py` | `CoachViewModel` | Coach | Estado da tela Coach — seletor de modelo, LLMs disponíveis (`Ollama /api/tags`), ciclo de vida da sessão. |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (painel de chat) | Diálogo multi-turno com `CoachingDialogueEngine`. Lista de mensagens thread-safe. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Carrossel de insight único para o focus card da home page. |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Carrega `PlayerMatchStats`, `RoundStats`, coaching insights, breakdown HLTV 2.0. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History | Lista filtrável de partidas do usuário. Cancelamento ao mudar filtro. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Tendência de rating, stats por mapa, forças / fraquezas, breakdown de utility. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | Comparação de stats user-vs-pro com baselines cientes do role. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Dados do perfil do pro, partidas recentes, contexto de percentil. |
| `tactical_vm.py` | `TacticalPlaybackViewModel`, `TacticalGhostViewModel`, `TacticalChronovisorViewModel` | Tactical Viewer | Três VMs coordenadas: playback, overlay de ghost AI, highlights de chronovisor. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Estado de sync Steam / FaceIT, campos de perfil. |

## Convenções

### Threading

Todo I/O acontece fora da thread da UI. ViewModels usam `core/worker.QThread`:

```python
def refresh(self):
    self._cancel_token = CancelToken()
    self._worker = run_in_thread(
        self._fetch_match_history,
        cancel_token=self._cancel_token,
    )
    self._worker.finished.connect(self._on_loaded)
    self._worker.failed.connect(self._on_load_failed)
```

`cancel_loads()` (chamado a partir do `on_leave` da tela) flipa o cancel token para que o worker desista de forma limpa, sem tocar widgets que podem ter sido destruídos.

### Signals

Estado público é exposto via `Signal` (PySide6) — nunca via atributos mutáveis. Telas se inscrevem; ViewModels emitem:

```python
matches_loaded = Signal(list)         # payload: List[MatchSummary]
load_failed = Signal(str)             # payload: razão legível para humano
loading_changed = Signal(bool)        # payload: True enquanto um fetch está em andamento
```

### Política de singleton

ViewModels são **per-screen-instance**, não singletons. O router constrói uma ViewModel nova cada vez que uma tela é instanciada. Singletons vazariam estado entre navegações.

### Sem widgets Qt nesta camada

Importar de `PySide6.QtWidgets` aqui é code smell — ViewModels devem ser testáveis sem um QApplication ativo. Imports limitados a `PySide6.QtCore` (signals, QObject, QThread).

## Armadilhas comuns

| Erro | Consequência | Correção |
|------|--------------|----------|
| Buscar sincronicamente em `__init__` | Bloqueia thread da UI ao entrar na tela | Adie para a primeira chamada de `refresh()` |
| Esquecer `cancel_loads()` | Fetch stale termina numa tela destruída → segfault | Implemente `cancel_loads()` em toda VM com workers |
| Compartilhar uma única session de `DatabaseManager` entre threads | Contenção de WAL no SQLite | Use `get_db_manager().get_session()` por worker |
| Emitir signals de threads worker para slots não thread-safe | Crash em chamada cross-thread | Use connections enfileiradas (default do Qt para `Signal` entre threads) |

## Integração

```
Tela (apps/qt_app/screens/*)
    +-- ViewModel (este pacote)
            +-- backend/services/*           (lógica de negócio)
            +-- backend/reporting/analytics  (matemática do dashboard)
            +-- backend/storage/database     (singletons de persistência)
            +-- core/worker.QThread          (execução em background)
```

## Relacionados

- Telas: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Serviços de backend: `Programma_CS2_RENAN/backend/services/README.md`
- App pai: `apps/qt_app/README.md`

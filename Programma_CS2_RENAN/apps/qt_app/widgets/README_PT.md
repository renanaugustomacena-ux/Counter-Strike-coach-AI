# `apps/qt_app/widgets/` — Biblioteca de widgets Qt customizados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Subclasses customizadas e reutilizaveis de `QWidget` que se compoem em telas. Qualquer coisa usada por mais de uma tela, ou qualquer coisa grande o bastante para merecer arquivo proprio, vive aqui. Visuais puros de tela unica ficam dentro do modulo da tela proprietaria.

## Layout

```
widgets/
├── __init__.py
├── skeleton.py             # Skeletons de carregamento (placeholders shimmer)
├── toast.py                # Toasts de notificacao transientes
├── components/             # Primitivas genericas de UI (cards, badges, chips, ...)
├── charts/                 # Graficos QPainter (QtCharts removido — somente GPL)
├── coaching/               # Widgets de coaching (ChatPanel integrado)
└── tactical/               # Widgets especificos do tactical viewer
```

| Sub-pacote | Finalidade | README |
|------------|------------|--------|
| `components/` | Primitivas genericas de UI reutilizadas entre telas | [components/README.md](components/README.md) |
| `charts/` | Graficos QPainter para o dashboard (QtCharts removido por conformidade GPL) | [charts/README.md](charts/README.md) |
| `coaching/` | Widgets de coaching — `ChatPanel` integrado na CoachScreen | [coaching/README.md](coaching/README.md) |
| `tactical/` | Widgets do tactical viewer (mapa, sidebar, timeline) | [tactical/README.md](tactical/README.md) |

## Arquivos top-level

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `skeleton.py` | `SkeletonRect` / `SkeletonCard` / `SkeletonTable` — placeholders shimmer mostrados enquanto os dados da ViewModel carregam. |
| `toast.py` | `ToastWidget` + `ToastContainer` — notificacoes transientes com auto-dismiss baseado em severidade (CRITICAL nunca fecha automaticamente); `MainWindow` conecta `AppState.notification_received` ao container. |

## Convencoes

### Composicao em vez de heranca

A maioria dos widgets sao containers `QWidget` que compoem pecas menores. Evite arvores de heranca profundas — elas colidem com o modelo de signals do Qt e complicam o theming.

### Estilizacao ciente do tema

Cada widget le cores / espacamento / tipografia de `core/design_tokens.py` em vez de hard-coda-los. O gerador QSS em `core/qss_generator.py` materializa os tokens num stylesheet aplicado a toda a aplicacao, e a `QPalette` da aplicacao tambem e derivada dos tokens (`core/theme_engine.py`) — os arquivos `.qss` legacy por tema foram removidos; o template orientado por tokens e a unica fonte de estilo.

### API baseada em signals

Widgets expoem mudancas de estado via `Signal` (por exemplo, `clicked`, `selectionChanged`). Evite callbacks sincronos — eles quebram a separacao MVVM.

### Acessibilidade

- Defina `setAccessibleName()` e `setAccessibleDescription()` para qualquer widget que renderize conteudo semantico (graficos, indicadores de status).
- Status codificado por cor (rating, severidade) deve ser acompanhado de texto ou icone — nunca apenas cor (WCAG 1.4.1).

## Adicionando um novo widget

1. Decida se ele pertence a `widgets/` (generico), `widgets/components/` (primitiva de UI) ou a um sub-pacote de dominio.
2. Herde da menor classe Qt aplicavel (`QWidget`, `QFrame`, `QLabel`).
3. Leia tokens via `core/design_tokens` — nunca hard-code cores.
4. Exponha estado via `Signal`s, nao via getters que mutam.
5. Adicione o widget a tabela de inventario do README do sub-pacote.
6. Se o widget for ciente do tema, resolva cores a partir do conjunto de tokens ativo (`get_tokens()`) ou conecte-se a `theme_engine.theme_changed`.

## Relacionados

- Core da aplicacao: `apps/qt_app/core/README.md`
- Telas (consumidoras): `apps/qt_app/screens/README.md`
- App pai: `apps/qt_app/README.md`

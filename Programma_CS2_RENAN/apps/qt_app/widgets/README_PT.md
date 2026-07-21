# `apps/qt_app/widgets/` — Biblioteca de widgets Qt customizados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Regra 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Finalidade

Subclasses customizadas e reutilizáveis de `QWidget` que se compõem em telas. Qualquer coisa usada por mais de uma tela, ou qualquer coisa grande o bastante para merecer arquivo próprio, vive aqui. Visuais puros de tela única ficam dentro do módulo da tela proprietária.

## Layout

```
widgets/
├── __init__.py
├── skeleton.py             # Skeletons de carregamento (placeholders shimmer)
├── toast.py                # Toasts de notificação transientes
├── components/             # Primitivas genéricas de UI (cards, badges, chips, ...)
├── charts/                 # Gráficos baseados em QtCharts / QPainter
├── coaching/               # Namespace de widgets coaching (reservado; widgets removidos PR #32)
└── tactical/               # Widgets específicos do tactical viewer
```

| Sub-pacote | Finalidade | README |
|------------|------------|--------|
| `components/` | Primitivas genéricas de UI reutilizadas entre telas | [components/README.md](components/README.md) |
| `charts/` | Gráficos baseados em QtCharts / QPainter para o dashboard | [charts/README.md](charts/README.md) |
| `coaching/` | Namespace reservado; todos os widgets removidos na PR #32 | [coaching/README.md](coaching/README.md) |
| `tactical/` | Widgets do tactical viewer (mapa, sidebar, timeline) | [tactical/README.md](tactical/README.md) |

## Arquivos top-level

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `skeleton.py` | `SkeletonLoader` — placeholder shimmer mostrado enquanto os dados da ViewModel carregam. |
| `toast.py` | Toast de notificação transiente com auto-dismiss + botão de ação. Inscrito em `app_state.bus` para toasts globais. |

## Convenções

### Composição em vez de herança

A maioria dos widgets são containers `QWidget` que compõem peças menores. Evite árvores de herança profundas — elas colidem com o modelo de signals do Qt e complicam o theming.

### Estilização ciente do tema

Cada widget lê cores / espaçamento / tipografia de `core/design_tokens.py` em vez de hard-codá-los. O gerador QSS em `core/qss_generator.py` materializa os tokens num stylesheet aplicado a toda a aplicação.

### API baseada em signals

Widgets expõem mudanças de estado via `Signal` (por exemplo, `clicked`, `selectionChanged`). Evite callbacks síncronos — eles quebram a separação MVVM.

### Acessibilidade

- Defina `setAccessibleName()` e `setAccessibleDescription()` para qualquer widget que renderize conteúdo semântico (gráficos, indicadores de status).
- Status codificado por cor (rating, severidade) deve ser acompanhado de texto ou ícone — nunca apenas cor (WCAG 1.4.1).

## Adicionando um novo widget

1. Decida se ele pertence a `widgets/` (genérico), `widgets/components/` (primitiva de UI) ou a um sub-pacote de domínio.
2. Herde da menor classe Qt aplicável (`QWidget`, `QFrame`, `QLabel`).
3. Leia tokens via `core/design_tokens` — nunca hard-code cores.
4. Exponha estado via `Signal`s, não via getters que mutam.
5. Adicione o widget à tabela de inventário do README do sub-pacote.
6. Se o widget for ciente do tema, inscreva-se em `theme_engine.themeChanged`.

## Relacionados

- Core da aplicação: `apps/qt_app/core/README.md`
- Telas (consumidoras): `apps/qt_app/screens/README.md`
- App pai: `apps/qt_app/README.md`

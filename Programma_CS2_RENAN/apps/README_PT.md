> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Apps — Camada de Interface do Usuario

> **Autoridade:** Rule 3 (Frontend & UX), padrao arquitetural MVVM

O diretorio `apps/` contem todo o codigo de interface do usuario do Macena CS2 Analyzer. Dois frameworks de UI coexistem durante o periodo de migracao:

| Subdiretorio | Framework | Status | Finalidade |
|--------------|-----------|--------|------------|
| `desktop_app/` | Kivy + KivyMD | Legacy (Fase 0) | UI desktop original, sendo substituida |
| `qt_app/` | PySide6 (Qt6) | **Ativo** (Fase 2+) | UI desktop de producao |

## Arquitetura

Ambas as UIs seguem o padrao **MVVM (Model-View-ViewModel)**:

View (Screen/Widget) ──signals──> ViewModel (QObject) ──queries──> Model (SQLModel/DB)

Principios chave:
- As Views nunca acessam o banco de dados diretamente
- Os ViewModels executam consultas ao banco em threads de background (Worker/QRunnable)
- Os resultados sao encaminhados para a thread principal via Qt Signals
- As Screens nao importam umas as outras (acoplamento fraco)

## Ponto de Entrada

python -m Programma_CS2_RENAN.apps.qt_app.app

## Diretrizes de Desenvolvimento

1. Todo novo trabalho de UI vai em `qt_app/` — nao adicione funcionalidades em `desktop_app/`
2. Nenhum import Kivy no codigo Qt
3. Threading em background e obrigatorio — nunca bloqueie a thread principal
4. Use `Worker` de `qt_app/core/worker.py` para todas as operacoes em background
5. Graficos usam QtCharts (nao matplotlib)
6. Localizacao — todas as strings visiveis ao usuario devem passar por `i18n_bridge.get_text(key)`
7. Temas — use `ThemeEngine` para cores/fontes

## Contagem de Arquivos

- `desktop_app/`: 13 arquivos Python (legacy)
- `qt_app/`: 50+ arquivos Python distribuidos em `core/`, `viewmodels/`, `widgets/`, `screens/`

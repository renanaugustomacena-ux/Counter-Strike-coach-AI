> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Packaging — Build e Distribuição

> **Autoridade:** Rule 7 (CI/CD & Release Engineering)

Este diretório contém tudo o necessário para compilar o Macena CS2 Analyzer em uma aplicação Windows distribuível.

## Inventário de Arquivos

| Arquivo | Finalidade |
|---------|------------|
| `cs2_analyzer_win.spec` | Especificação PyInstaller (168 linhas) |
| `windows_installer.iss` | Script Inno Setup para instalador MSI (42 linhas) |
| `BUILD_CHECKLIST.md` | Protocolo de verificação pré-lançamento (76 linhas) |

## Build Rápido

```bash
# Pré-requisitos: Python 3.10+, venv ativado, todas as dependências instaladas
source /home/renan/.venvs/cs2analyzer/bin/activate

# 1. Validar (deve passar antes do build)
python tools/headless_validator.py

# 2. Compilar
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

# 3. Saída
ls dist/Macena_CS2_Analyzer/
```

## `cs2_analyzer_win.spec` — Configuração PyInstaller

### Ponto de Entrada

```python
# Ponto de entrada principal (frontend Qt6)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Dados Incluídos (43 entradas)

O spec inclui todos os arquivos necessários em tempo de execução:

| Categoria | Arquivos | Finalidade |
|-----------|----------|------------|
| Assets temáticos | `PHOTO_GUI/` (fontes, fundos) | Temas visuais |
| Configuração de mapas | `map_config.json`, `map_tensors.json` | Dados espaciais |
| Dados externos | `data/external/*.csv` | Estatísticas de referência |
| Conhecimento | `data/knowledge/`, `tactical_knowledge.json` | Dados de coaching RAG |
| Migrações | `alembic/` | Atualizações de schema do banco de dados |
| Traduções | `assets/i18n/` | Localização |
| Documentação | `data/docs/` | Ajuda integrada no app |
| Temas Qt | `apps/qt_app/themes/` | Folhas de estilo QSS |

### Hidden Imports (92 no total)

Pacotes críticos que o PyInstaller não consegue detectar automaticamente:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets, QtCharts)
- **ML:** torch, torch.nn, torch.optim
- **Banco de dados:** sqlmodel, sqlalchemy, alembic
- **Parsing:** demoparser2, pandas, numpy
- **Módulos do projeto:** 30+ módulos internos (app_state, jepa_model, coaching_service, etc.)

### Pacotes Excluídos

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab', 'kivy', 'kivymd',
            'shap', 'playwright']
```

### Tamanhos do Bundle

| Variante | Tamanho | Notas |
|----------|---------|-------|
| PyTorch somente CPU | ~1.5 GB | Padrão, funciona em qualquer lugar |
| PyTorch GPU (CUDA) | ~2.5 GB | Detectado automaticamente em tempo de execução |

## `windows_installer.iss` — Inno Setup

Cria um instalador MSI para Windows com:
- **Caminho de instalação:** `Program Files\Macena_CS2_Analyzer`
- **Idiomas:** Inglês, Italiano, Português Brasileiro
- **Compressão:** LZMA (compressão sólida)
- **Atalhos:** Grupo no Menu Iniciar + ícone na Área de Trabalho (opcional)
- **Pós-instalação:** Inicia automaticamente a aplicação

Requer [Inno Setup](https://jrsoftware.org/isinfo.php) para compilação.

## `BUILD_CHECKLIST.md` — Protocolo de Lançamento

Verificação passo a passo antes da distribuição:

1. **Pré-build:** Todos os 13 hooks de pre-commit passam, cobertura de testes >= 30%, o validador encerra com código 0
2. **Sincronização de versão:** A versão no `pyproject.toml` corresponde ao AppVersion no `windows_installer.iss`
3. **Build:** PyInstaller com `--noconfirm`
4. **Pós-build:** O exe inicia, a UI renderiza, os mapas carregam, os gráficos são gerados, `audit_binaries.py` passa
5. **Opcional:** Compilar o instalador Inno Setup para distribuição MSI

## Notas de Desenvolvimento

- O arquivo `.spec` lida com caminhos ausentes de forma segura (para ambientes CI)
- `collect_submodules("Programma_CS2_RENAN")` descobre automaticamente os módulos do projeto
- A detecção de GPU ocorre em tempo de execução via `backend/nn/config.py:get_device()`
- **matplotlib é OBRIGATÓRIO** em tempo de execução (para visualization_service.py)
- **sentence_transformers é OBRIGATÓRIO** (para embeddings SBERT no RAG)
- **ncps/hflayers NÃO são necessários em tempo de execução** (o modelo RAP é experimental)
- O pipeline CI/CD (`/.github/workflows/build.yml`) automatiza tudo isso nos pushes para main
- Números de versão: verificar tanto `pyproject.toml` quanto `windows_installer.iss` antes do lançamento

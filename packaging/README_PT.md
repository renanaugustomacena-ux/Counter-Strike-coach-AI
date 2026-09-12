# Packaging — Build e Distribuição

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autoridade:** Regra 7 (CI/CD & Release Engineering)

Este diretório contém tudo o necessário para compilar o Macena CS2 Analyzer em uma aplicação Windows distribuível.

## Inventário de Arquivos

| Arquivo | Finalidade |
|---------|------------|
| `cs2_analyzer_win.spec` | Especificação PyInstaller (172 linhas) |
| `windows_installer.iss` | Script Inno Setup para o instalador EXE do Windows (78 linhas) |
| `BUILD_CHECKLIST.md` | Protocolo de verificação pré-lançamento (75 linhas) |

## Build Rápido

```bat
REM Pré-requisitos (Windows): venv_win criado por scripts\Setup_Macena_CS2.ps1, PyInstaller instalado
call venv_win\Scripts\activate

REM 1. Validar (deve passar antes do build)
python tools/headless_validator.py

REM 2. Compilar
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

REM 3. Saída
dir dist\Macena_CS2_Analyzer
```

## `cs2_analyzer_win.spec` — Configuração PyInstaller

### Ponto de Entrada

```python
# Ponto de entrada principal (frontend Qt6)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Dados Incluídos (12 entradas)

O spec inclui todos os arquivos necessários em tempo de execução (caminhos ausentes são filtrados com tratamento seguro para ambientes CI):

| Categoria | Arquivos | Finalidade |
|-----------|----------|------------|
| Assets temáticos | `PHOTO_GUI/` (fontes, fundos) | Temas visuais |
| Configuração de mapas | `data/map_config.json` | Dados espaciais |
| Datasets | `data/dataset.csv`, `data/external/` | Estatísticas de referência |
| Integridade | `core/integrity_manifest.json` | Manifesto fonte RASP |
| Conhecimento | `backend/knowledge/tactical_knowledge.json` | Dados de coaching RAG |
| Migrações | `alembic/` (raiz do repo) | Atualizações de schema do banco de dados |
| Traduções | `assets/i18n/` | Localização |
| Documentação | `data/docs/` | Ajuda integrada no app |
| Temas Qt | `apps/qt_app/themes/` | Folhas de estilo QSS |
| Fontes | `assets/fonts/` | Stack tipográfico do design atlas |
| Zonas de mapa | `assets/map_zones/` | Overlays de zona nomeada para o mapa tático |

### Hidden Imports (35 explícitos + auto-collection)

Pacotes críticos que o PyInstaller não consegue detectar automaticamente:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets)
- **ML:** torch, torch.nn, torch.optim
- **Banco de dados:** sqlmodel, sqlalchemy (incl. dialeto sqlite), alembic
- **Parsing:** demoparser2, pandas, numpy
- **Módulos do projeto:** 21 módulos internos com imports diferidos (app_state, jepa_model, coaching_service, etc.)
- Mais `collect_submodules("Programma_CS2_RENAN")` que descobre automaticamente o resto do pacote.

### Pacotes Excluídos

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab',
            'shap', 'playwright',
            'kivy', 'kivymd',      # migrados para Qt
            'ncps', 'hflayers']    # dependências opcionais RAP, não necessárias em runtime
```

### Tamanhos do Bundle

| Variante | Tamanho | Notas |
|----------|---------|-------|
| PyTorch somente CPU | ~1.5 GB | Padrão, funciona em qualquer lugar |
| PyTorch GPU (CUDA) | ~2.5 GB | Detectado automaticamente em tempo de execução |

## `windows_installer.iss` — Inno Setup

Cria um executável de setup para Windows (`dist/Macena_CS2_Installer.exe`) com:
- **Caminho de instalação:** `Program Files\Macena_CS2_Analyzer`
- **Idiomas:** Inglês, Italiano, Português Brasileiro
- **Compressão:** LZMA (compressão sólida)
- **Atalhos:** Grupo no Menu Iniciar + ícone na Área de Trabalho (opcional)
- **Runtime MSVC:** instala silenciosamente `vc_redist.x64.exe` se ausente (colocá-lo em `packaging/` antes da compilação)
- **Pós-instalação:** Inicia opcionalmente a aplicação

Requer [Inno Setup](https://jrsoftware.org/isinfo.php) para compilação.

## `BUILD_CHECKLIST.md` — Protocolo de Lançamento

Verificação passo a passo antes da distribuição:

1. **Pré-build:** Todos os 14 hooks de pre-commit passam, cobertura de testes >= 50%, o validador encerra com código 0
2. **Sincronização de versão:** A versão no `pyproject.toml` corresponde ao AppVersion no `windows_installer.iss`
3. **Build:** PyInstaller com `--noconfirm`
4. **Pós-build:** O exe inicia, a UI renderiza, os mapas carregam, os gráficos são gerados, `audit_binaries.py` passa
5. **Opcional:** Compilar o instalador Inno Setup para distribuição

## Drivers de Build e CI

Três caminhos consomem o spec — todos terminam em `dist/Macena_CS2_Analyzer/`:

| Driver | Invocação | Notas |
|--------|-----------|-------|
| Direto | `python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN` | Build Rápido acima |
| Pipeline batch | `scripts/build_production.bat` → `Programma_CS2_RENAN/tools/build_tools.py build` | Checagens pré-voo, migração alembic, manifesto RASP, PyInstaller, auditoria de binários, Inno Setup opcional (`scripts/build_exe.bat` delega aqui) |
| Fase dist CI | Job `build-distribution` em `.github/workflows/build.yml` | Apenas pushes para `main` |

A fase dist CI (retrabalhada em 14-08-2026) roda em `windows-latest` e:

- fixa **Python 3.12** — `requirements-lock-cpu.txt` foi congelado no Python 3.12.10, e o lock é instalado no interpretador para o qual foi congelado
- instala o conjunto de dependências CPU travado (`requirements-lock-cpu.txt`) mais um `pyinstaller==6.17.0` fixado (deliberadamente ausente do lock de runtime)
- define `PYTHONUTF8=1` no nível do job (um `setup.py` de uma dependência git-sdist falha com o cp1252 padrão do runner)
- usa um comando nativo por step, para que uma instalação falhada não possa mais ser mascarada pelo exit code de um comando posterior
- valida 10 arquivos de dados críticos antes do build, depois executa PyInstaller neste spec
- verifica o resultado com `tools/audit_binaries.py` e faz upload de `dist/` como artefato `cs2-analyzer-windows` (retenção de 30 dias)

> `tools/build_pipeline.py` (o antigo pipeline "industrial" de 5 estágios) precede a mudança para `packaging/` e ainda procura o spec na raiz do repo; os drivers mantidos são os três acima.

## Notas de Desenvolvimento

- O arquivo `.spec` lida com caminhos ausentes de forma segura (para ambientes CI)
- `collect_submodules("Programma_CS2_RENAN")` descobre automaticamente os módulos do projeto
- A detecção de GPU ocorre em tempo de execução via `backend/nn/config.py:get_device()`
- **matplotlib é OBRIGATÓRIO** em tempo de execução (para visualization_service.py)
- **sentence_transformers é OBRIGATÓRIO** (para embeddings SBERT no RAG)
- **ncps/hflayers NÃO são necessários em tempo de execução** (o modelo RAP é experimental)
- Números de versão: verificar tanto `pyproject.toml` quanto `windows_installer.iss` antes do lançamento

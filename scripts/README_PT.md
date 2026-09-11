> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Scripts de Build e Setup

> **Autoridade:** Regra 7 (CI/CD & Release Engineering)

Scripts de build e setup para criar executáveis prontos para produção da aplicação desktop Macena CS2 Analyzer. Esses scripts automatizam o processo de build com PyInstaller para distribuição no Windows.

## Inventário de Arquivos

| Arquivo | Finalidade | Plataforma |
|---------|------------|------------|
| `build_exe.bat` | Wrapper de compatibilidade — delega para `build_production.bat` (a antiga invocação inline do Kivy foi substituída) | Windows |
| `build_production.bat` | Automação do build de produção — validação, migração, manifest, build, audit, installer | Windows |
| `Setup_Macena_CS2.ps1` | Setup PowerShell — reposiciona-se na raiz do repositório, cria `venv_win`, instala CPU torch + requirements, inicializa o banco de dados, instala Playwright Chromium | Windows |
| `reaggregate.sh` | Pipeline de re-agregação — repopula estatísticas de round, enriquece estatísticas de partida, extrai experiências de coaching, reconstrói a knowledge base + índices FAISS | Linux (bash) — executado na máquina separada de dados/treinamento |

## Arquitetura de Build

O processo de build utiliza o PyInstaller para empacotar toda a aplicação Python, suas dependências e todos os assets de runtime em um executável Windows standalone. Nenhuma instalação de Python é necessária na máquina de destino.

```
Código Fonte + Dependências + Assets
        │
        ▼
    PyInstaller (packaging/cs2_analyzer_win.spec, executado por build_production.bat)
        │
        ├── Fase de análise (detecta imports, coleta arquivos de dados)
        ├── Fase de bundle (cria arquivo compactado)
        └── Fase de output (gera executável)
        │
        ▼
    dist/Macena_CS2_Analyzer/
        ├── Macena_CS2_Analyzer.exe   # Executável principal
        ├── _internal/                # Python + dependências empacotadas
        └── (assets de runtime)       # Mapas, fontes, temas, knowledge base
```

## `build_exe.bat` — Wrapper de Compatibilidade

Anteriormente uma invocação inline do PyInstaller direcionada ao ponto de entrada Kivy removido (`Programma_CS2_RENAN/main.py`). Foi substituído (não deletado, para que instruções antigas que o invocam continuem funcionando): o script agora imprime um aviso e delega para `build_production.bat`, encaminhando todos os argumentos, de modo a produzir o build PySide6 atual a partir de `packaging/cs2_analyzer_win.spec`.

## `build_production.bat` — Automação do Build de Produção

A pipeline completa de release para Windows (utiliza `venv_win`; execute `Setup_Macena_CS2.ps1` primeiro):

1. **Pre-flight** — verifica a presença de `venv_win`, `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`, `tools/audit_binaries.py`, `packaging/cs2_analyzer_win.spec` e das dependências core (keyring, kivymd, sqlmodel, alembic)
2. **Limpeza** — remove `build/` e `dist/`
3. **Sync de schema** — `alembic upgrade head` (aborta em caso de erro)
4. **Manifest de integridade (RASP)** — regenera `integrity_manifest.json` via `sync_integrity_manifest.py`
5. **Build** — `python Programma_CS2_RENAN/tools/build_tools.py build` (verificações de formato/import, pytest, `alembic upgrade head`, PyInstaller via `packaging/cs2_analyzer_win.spec`, SHA-256 `build_manifest.json` em `dist/`)
6. **Audit de binários** — `python tools/audit_binaries.py` (aborta se o audit de segurança falhar)
7. **Installer (opcional)** — compila `packaging/windows_installer.iss` com Inno Setup 6 se `ISCC.exe` estiver disponível, produzindo `dist\Macena_CS2_Installer.exe`

## Relação com `packaging/`

A definição do build reside em `packaging/cs2_analyzer_win.spec` (ponto de entrada Qt/PySide6 `apps/qt_app/app.py`, 35 hidden imports explícitos + `collect_submodules`). Ambos os scripts batch convergem para ela:

- `build_production.bat` executa a pipeline completa e constrói a spec via `Programma_CS2_RENAN/tools/build_tools.py build`
- `build_exe.bat` simplesmente delega para `build_production.bat`
- O installer opcional é compilado a partir de `packaging/windows_installer.iss` (Inno Setup, `Macena_CS2_Installer.exe`)

O estágio de distribuição CI (job `build-distribution` em `.github/workflows/build.yml`) constrói a mesma spec em `windows-latest` (somente pushes para `main`) com Python 3.12, `requirements-lock-cpu.txt` e um `pyinstaller==6.17.0` fixado.

## Uso

```bat
REM Setup único do ambiente (cria venv_win)
powershell -ExecutionPolicy Bypass -File scripts\Setup_Macena_CS2.ps1

REM Build de produção (validação + build + audit + installer)
scripts\build_production.bat
```

```bash
# Pipeline de re-agregação de dados (máquina Linux separada, venv ativado)
bash scripts/reaggregate.sh
```

> **Nota:** `reaggregate.sh` é executado na máquina Linux separada que hospeda o corpus `.dem` (`PRO_DEMO_PATH` em `user_settings.json`) — assim como o treinamento de IA em larga escala, essa carga de trabalho pesada em dados não é executada na máquina de desenvolvimento Windows. Tempo de execução esperado: 30-90 minutos dependendo da quantidade de demos.

`Setup_Macena_CS2.ps1` pode ser invocado de qualquer diretório (ele muda para a raiz do repositório primeiro) e imprime o comando de inicialização ao completar: `.\venv_win\Scripts\python.exe -m Programma_CS2_RENAN.apps.qt_app.app`.

## Pré-requisitos

- Python 3.11+ com ambiente virtual ativado
- PyInstaller instalado (`pip install pyinstaller`)
- Todas as dependências do projeto instaladas
- Ambiente Windows (scripts batch)

## Artefatos de Build

| Diretório | Conteúdo | Rastreado pelo Git |
|-----------|----------|--------------------|
| `dist/` | Executável final e arquivos empacotados | Não (.gitignore) |
| `build/` | Artefatos de build intermediários | Não (.gitignore) |

Para um build limpo, delete ambos os diretórios antes de reconstruir.

## Solução de Problemas

| Problema | Causa | Solução |
|----------|-------|---------|
| Erros de módulo ausente | PyInstaller não detecta imports dinâmicos | Adicionar a `hiddenimports` em `packaging/cs2_analyzer_win.spec` |
| Asset não encontrado em runtime | Arquivos de dados não empacotados | Adicionar o caminho faltante a `datas` na spec |
| Executável trava ao iniciar | DLLs ou arquivos de runtime ausentes | Verificar avisos do PyInstaller durante o build |
| Build muito grande (>3 GB) | PyTorch com GPU incluído | Usar torch somente CPU para distribuição |

## Notas de Desenvolvimento

- Sempre execute `python tools/headless_validator.py` antes do build
- O build de produção tem aproximadamente 1.5 GB (PyTorch somente CPU; veja `packaging/BUILD_CHECKLIST.md`)
- O suporte a GPU é auto-detectado em runtime via `backend/nn/config.py:get_device()`
- Todos os caminhos de build (ambos os scripts `.bat` e CI) utilizam `packaging/cs2_analyzer_win.spec`

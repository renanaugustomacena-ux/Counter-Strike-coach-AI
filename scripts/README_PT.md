> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Scripts de Build e Setup

> **Autoridade:** Regra 7 (CI/CD & Release Engineering)

Scripts de build e setup para criar executáveis prontos para produção da aplicação desktop Macena CS2 Analyzer. Esses scripts automatizam o processo de build com PyInstaller para distribuição no Windows.

## Inventário de Arquivos

| Arquivo | Finalidade | Plataforma |
|---------|------------|------------|
| `build_exe.bat` | Build de desenvolvimento — cria executável standalone | Windows |
| `build_production.bat` | Build de produção — otimizado e reduzido | Windows |
| `Setup_Macena_CS2.ps1` | Script PowerShell para configuração de ambiente | Windows |

## Arquitetura de Build

O processo de build utiliza o PyInstaller para empacotar toda a aplicação Python, suas dependências e todos os assets de runtime em um executável Windows standalone. Nenhuma instalação de Python é necessária na máquina de destino.

```
Código Fonte + Dependências + Assets
        │
        ▼
    PyInstaller (build_exe.bat)
        │
        ├── Fase de análise (detecta imports, coleta arquivos de dados)
        ├── Fase de bundle (cria arquivo compactado)
        └── Fase de output (gera executável)
        │
        ▼
    dist/Macena/
        ├── Macena.exe          # Executável principal
        ├── _internal/          # Python + dependências empacotadas
        └── (assets de runtime)  # Mapas, fontes, temas, knowledge base
```

## `build_exe.bat` — Build de Desenvolvimento

Este script cria um bundle em modo diretório (não um arquivo único) para facilitar o debug:

### O Que Ele Faz

1. **Limpa** artefatos de build antigos (diretórios `dist/`, `build/`)
2. **Executa o PyInstaller** com a seguinte configuração:
   - `--noconsole` — sem janela de terminal (aplicação GUI)
   - `--name Macena` — executável nomeado `Macena.exe`
   - `--icon` — utiliza `Programma_CS2_RENAN/PHOTO_GUI/icon.ico`
3. **Empacota dados de runtime:**
   - `PHOTO_GUI/` — fontes, backgrounds, imagens de tema
   - `apps/` — telas da aplicação e layouts
   - `data/` — knowledge base, CSVs externos, configurações de mapas
4. **Coleta** automaticamente todos os assets do KivyMD e Kivy

### Ponto de Entrada

```python
# O build parte do ponto de entrada legacy do Kivy
Programma_CS2_RENAN/main.py
```

### Output

```
dist/Macena/
├── Macena.exe
└── _internal/
    ├── PHOTO_GUI/
    ├── apps/
    ├── data/
    └── (runtime Python + todas as dependências)
```

## `build_production.bat` — Build de Produção

Estende o build de desenvolvimento com otimizações para produção:

| Otimização | Flag | Efeito |
|------------|------|--------|
| Otimização Python | `-OO` | Remove docstrings e instruções assert |
| Remoção de debug | (interno do PyInstaller) | Remove símbolos de debug |
| Minimização de tamanho | Exclui pacotes dev | Remove pytest, coverage, IPython, etc. |
| Validação de integridade | Verificação pós-build | Verifica se o executável consegue iniciar |

## Relação com `packaging/`

Esses scripts são a abordagem de build **legada**. O sistema de build principal foi migrado para `packaging/cs2_analyzer_win.spec`, que utiliza o ponto de entrada Qt (PySide6) ao invés do Kivy:

| Aspecto | `scripts/` (legado) | `packaging/` (principal) |
|---------|---------------------|--------------------------|
| Ponto de entrada | `main.py` (Kivy) | `apps/qt_app/app.py` (Qt) |
| Framework de UI | Kivy + KivyMD | PySide6/Qt |
| Arquivo spec | Inline no .bat | `cs2_analyzer_win.spec` |
| Hidden imports | Auto-detectados | 92 entradas explícitas |
| Instalador | Nenhum | Inno Setup (MSI) |

## Uso

```bat
REM Build de desenvolvimento
scripts\build_exe.bat

REM Build de produção (otimizado)
scripts\build_production.bat
```

## Pré-requisitos

- Python 3.10+ com ambiente virtual ativado
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
| Erros de módulo ausente | PyInstaller não detecta imports dinâmicos | Adicionar aos flags `--hidden-import` |
| Asset não encontrado em runtime | Arquivos de dados não empacotados | Adicionar `--add-data` para o caminho faltante |
| Executável trava ao iniciar | DLLs ou arquivos de runtime ausentes | Verificar avisos do PyInstaller durante o build |
| Build muito grande (>3 GB) | PyTorch com GPU incluído | Usar torch somente CPU para distribuição |

## Notas de Desenvolvimento

- Sempre execute `python tools/headless_validator.py` antes do build
- O build de produção tem aproximadamente 1.5 GB (PyTorch somente CPU)
- O suporte a GPU é auto-detectado em runtime via `backend/nn/config.py:get_device()`
- Para o build principal baseado em Qt, utilize `packaging/cs2_analyzer_win.spec` ao invés destes scripts

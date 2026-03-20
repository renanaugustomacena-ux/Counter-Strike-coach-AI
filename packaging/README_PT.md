> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Packaging — Build e Distribuicao

> **Autoridade:** Rule 7 (CI/CD & Release Engineering)

Este diretorio contem tudo o necessario para compilar o Macena CS2 Analyzer em uma aplicacao Windows distribuivel.

## Inventario de Arquivos

| Arquivo | Finalidade |
|---------|------------|
| `cs2_analyzer_win.spec` | Especificacao PyInstaller (168 linhas) |
| `windows_installer.iss` | Script Inno Setup para instalador MSI (42 linhas) |
| `BUILD_CHECKLIST.md` | Protocolo de verificacao pre-lancamento (76 linhas) |

## Build Rapido

Pre-requisitos: Python 3.10+, venv ativado, todas as dependencias instaladas.
1. Validar (deve passar antes do build): python tools/headless_validator.py
2. Compilar: python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec
3. Saida: ls dist/Macena_CS2_Analyzer/

## Detalhes Importantes

- Ponto de entrada: Frontend Qt6 (qt_app/app.py)
- Dados incluidos: 43 entradas (temas, mapas, dados externos, conhecimento, migracoes, traducoes, documentacao, temas Qt)
- Hidden Imports: 92 no total (Qt, ML, Database, Parsing, modulos do projeto)
- Tamanho do bundle: somente CPU ~1.5 GB, GPU (CUDA) ~2.5 GB
- Instalador Windows: Inno Setup com idiomas Ingles, Italiano, Portugues Brasileiro
- Caminho de instalacao: Program Files\Macena_CS2_Analyzer

## Notas de Desenvolvimento

- O arquivo `.spec` lida com caminhos ausentes de forma segura (para ambientes CI)
- A deteccao de GPU ocorre em tempo de execucao via `backend/nn/config.py:get_device()`
- matplotlib e sentence_transformers sao OBRIGATORIOS em tempo de execucao
- Numeros de versao: verificar tanto `pyproject.toml` quanto `windows_installer.iss` antes do lancamento

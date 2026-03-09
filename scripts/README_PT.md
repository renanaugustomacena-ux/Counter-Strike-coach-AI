> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Scripts de Build e Setup

Scripts de build e setup para criar executáveis prontos para produção e configuração de ambiente de desenvolvimento.

## Scripts de Build

- `build_exe.bat` — Script de build de executável PyInstaller para Windows
- `build_production.bat` — Script de build de produção com otimizações

## Processo de Build

Os scripts de build usam PyInstaller para criar um executável standalone da aplicação desktop Macena CS2 Analyzer.

### build_exe.bat

- Cria um executável single-file (`--onefile`) ou bundle de diretório
- Inclui todas as dependências necessárias (Kivy, KivyMD, PyTorch, ncps, hflayers)
- Empacota assets (mapas, imagens, fontes) de `apps/desktop_app/assets/`
- Configura ícone e metadata do executável
- Output: `dist/MacenaCS2Analyzer.exe`

### build_production.bat

- Estende `build_exe.bat` com otimizações de produção
- Habilita flags de otimização do Python (`-OO`)
- Remove símbolos de debug e bytecode
- Minimiza tamanho do executável
- Valida integridade do build

## Uso

```bat
# Build de desenvolvimento
scripts\build_exe.bat

# Build de produção (otimizado)
scripts\build_production.bat
```

## Requisitos

- PyInstaller instalado (`pip install pyinstaller`)
- Todas as dependências do projeto instaladas
- Ambiente Windows (scripts batch)

## Notas

Artefatos de build são gerados nos diretórios `dist/` e `build/`. Build limpo: deletar esses diretórios antes de reconstruir.

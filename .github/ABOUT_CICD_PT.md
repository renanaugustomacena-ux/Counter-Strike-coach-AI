# GitHub Actions - Configuracao CI/CD

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

Este diretorio contem a pipeline CI/CD do GitHub Actions para o projeto Macena CS2 Analyzer.

## Visao Geral da Pipeline

A pipeline e executada em **cada push e pull request**, validando a qualidade do codigo em ambas as plataformas Linux e Windows. A build de distribuicao final e direcionada ao Windows (onde estao os jogadores de CS2).

**Arquivo do workflow:** [`.github/workflows/build.yml`](workflows/build.yml)

## Estagios da Pipeline

```
lint ──┬── test (Ubuntu + Windows) ── integration (Ubuntu + Windows) ──┐
       │                                                                ├── build-distribution (Windows, apenas main)
       ├── security ───────────────────────────────────────────────────┘
       └── type-check (informativo, nao bloqueante)
```

### Estagio 1: Lint & Verificacao de Formato
- **Runner:** Ubuntu
- Hooks pre-commit, formatacao Black, ordenacao de imports isort

### Estagio 2: Testes Unitarios + Cobertura
- **Runner:** Ubuntu + Windows (matriz)
- pytest com rastreamento de cobertura (limite 30%)
- Relatorios de cobertura enviados como artifacts

### Estagio 3: Integracao
- **Runner:** Ubuntu + Windows (matriz)
- Validador headless (gate de 23 fases)
- Verificacoes de consistencia cross-modulo (METADATA_DIM, PlayerRole)
- Testes de portabilidade
- Verificacao do manifesto de integridade

### Estagio 4: Varredura de Seguranca
- **Runner:** Ubuntu (paralelo aos testes)
- Bandit security linter (severidade MEDIUM+)
- detect-secrets para credenciais hardcoded

### Estagio 4b: Verificacao de Tipos
- **Runner:** Ubuntu (informativo, nao bloqueante)
- Analise estatica de tipos com mypy

### Estagio 5: Build de Distribuicao
- **Runner:** Windows (apenas branch main, apos todos os gates passarem)
- Build de executavel PyInstaller
- Auditoria de integridade pos-build
- Upload de artifact (retencao de 30 dias)

## Seguranca da Supply Chain

Todas as GitHub Actions sao **fixadas por SHA** (nao por referencia de tag) para prevenir ataques a supply chain:
- `actions/checkout` — fixado no SHA v4
- `actions/setup-python` — fixado no SHA v5
- `actions/upload-artifact` — fixado no SHA v4

## Estrategia Cross-Platform

| Plataforma | Dependencias | Proposito |
|------------|-------------|-----------|
| Linux | `requirements.txt` + indice CPU PyTorch | Desenvolvimento + validacao CI |
| Windows | `requirements-ci.txt` (arquivo de lock) | Builds reproduziveis + distribuicao |

## Documentacao

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Guia detalhado da pipeline com testes locais, solucao de problemas e gatilhos de workflow

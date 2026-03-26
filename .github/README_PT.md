> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# .github — Pipeline CI/CD e Configuracao do GitHub

> **Autoridade:** Rule 7 (CI/CD & Release Engineering), Rule 5 (Security)

Este diretorio contem a pipeline CI/CD do GitHub Actions e sua documentacao. A pipeline garante qualidade de codigo, seguranca e compatibilidade multiplataforma a cada push.

## Inventario de Arquivos

| Arquivo | Finalidade |
|---------|------------|
| `workflows/build.yml` | Definicao da pipeline CI/CD principal (383 linhas) |
| `ABOUT_CICD.md` | Visao geral da pipeline (Ingles) |
| `ABOUT_CICD_IT.md` | Visao geral da pipeline (Italiano) |
| `ABOUT_CICD_PT.md` | Visao geral da pipeline (Portugues) |
| `CICD_GUIDE.md` | Guia tecnico detalhado |
| `PIPELINE.md` | Documentacao da arquitetura da pipeline |
| `dependabot.yml` | Configuracao do Dependabot para atualizacao de dependencias |
| `pull_request_template.md` | Template de PR |
| `ISSUE_TEMPLATE/bug_report.md` | Template de issue para relato de bug |
| `ISSUE_TEMPLATE/feature_request.md` | Template de issue para solicitacao de funcionalidade |

## Arquitetura da Pipeline

Push / PR
    │
    ├── Etapa 1: LINT (Ubuntu, ~1 min)
    │       └── pre-commit run --all-files
    │
    ├── Etapa 2: TEST (matriz Ubuntu + Windows, ~3 min)
    │       └── pytest --cov-fail-under=30
    │
    ├── Etapa 3: INTEGRATION (matriz Ubuntu + Windows, ~5 min)
    │       ├── headless_validator.py (gate de 24 fases, 319 verificacoes)
    │       ├── Consistencia entre modulos (METADATA_DIM == INPUT_DIM)
    │       ├── Testes de portabilidade
    │       └── Verificacao de manifesto de integridade
    │
    ├── Etapa 4a: SECURITY (Ubuntu, ~2 min)
    │       ├── Bandit (SAST, severidade MEDIUM+)
    │       ├── detect-secrets
    │       └── pip-audit (varredura CVE)
    │
    ├── Etapa 4b: TYPE-CHECK (Ubuntu, nao bloqueante)
    │       └── mypy --ignore-missing-imports
    │
    └── Etapa 5: BUILD-DISTRIBUTION (Windows, somente branch main, ~15 min)
            ├── Validacao de arquivos de dados criticos
            ├── Build PyInstaller
            ├── Auditoria pos-build (audit_binaries.py)
            └── Upload de artefato (retencao de 30 dias)

### Dependencias entre Jobs

lint ──┬── test ──┬── integration ──┬── build-distribution (somente main)
       │          │                 │
       └── security ────────────────┘
       │
       └── type-check (nao bloqueante, informativo)

## Gatilhos

| Gatilho | Branches | Caminhos Ignorados |
|---------|----------|-------------------|
| Push | `main`, `develop`, `feature/**`, `fix/**` | `*.md`, `docs/`, `.github/`, `LICENSE`, `.gitignore` |
| Pull Request | `main`, `develop` | Mesmo acima |

**Concorrencia:** Uma pipeline por branch. Novos pushes cancelam execucoes em andamento.

## Estrategia Multiplataforma

| Plataforma | Dependencias | PyTorch |
|------------|-------------|---------|
| Ubuntu | `requirements.txt` + bibliotecas SDL2 | Somente CPU (pip index) |
| Windows | `requirements-ci.txt` (lock file) | Somente CPU (pip index) |

## Medidas de Seguranca

Todas as GitHub Actions sao **fixadas por SHA** (nao referenciadas por tag) para prevenir ataques a supply-chain.

**Permissoes:** Privilegio minimo (`contents: read`), sobrescrito por job quando necessario.

## Validacao Local

Antes de fazer push, execute estes comandos localmente para detectar problemas antecipadamente:

```bash
# 1. Hooks pre-commit (mesmo que Etapa 1)
pre-commit run --all-files

# 2. Testes (mesmo que Etapa 2)
pytest Programma_CS2_RENAN/tests/ tests/ --cov=Programma_CS2_RENAN --cov-fail-under=30 -v

# 3. Validador headless (mesmo que Etapa 3)
python tools/headless_validator.py

# 4. Teste de portabilidade
python tools/portability_test.py
```

## Notas de Desenvolvimento

- NAO referencie Actions por tag — sempre use o SHA completo para seguranca da supply-chain
- O job `type-check` tem `continue-on-error: true` — informativo, nao bloqueante
- `build-distribution` executa apenas em pushes para o branch `main`
- A versao do Python e fixada em 3.10 em todos os jobs

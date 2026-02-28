# GitHub Actions - Configuração CI/CD

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

Este diretório contém workflows do GitHub Actions e configurações de automação para o projeto Macena CS2 Analyzer.

## Workflows

O diretório `.github/workflows/` contém pipelines CI/CD automatizadas:

### CI/CD Principal
- **[build.yml](workflows/build.yml)** — Pipeline de verificação de build
  Executada em cada push e pull request para validar a qualidade do código:
  - Verificações de linting e estilo de código (flake8, black)
  - Execução de testes unitários e de integração (pytest)
  - Varredura de vulnerabilidades de segurança (bandit, safety)
  - Verificação de dependências
  - Geração de artefatos de build

### Automação Gemini AI
- **[gemini-dispatch.yml](workflows/gemini-dispatch.yml)** — Workflow de dispatch Gemini AI
  Dispatcher centralizado para rotear tarefas Gemini AI para os manipuladores apropriados

- **[gemini-invoke.yml](workflows/gemini-invoke.yml)** — Invocação de comandos Gemini
  Executa comandos Gemini AI para geração automatizada de código e refatoração

- **[gemini-review.yml](workflows/gemini-review.yml)** — Revisão de código baseada em IA
  Revisão automatizada de código usando Gemini para pull requests, verificando:
  - Qualidade do código e aderência aos princípios de engenharia
  - Vulnerabilidades de segurança e anti-padrões
  - Completude da documentação
  - Requisitos de cobertura de testes

- **[gemini-triage.yml](workflows/gemini-triage.yml)** — Automação de triagem de issues
  Categoriza, rotula e prioriza automaticamente issues do GitHub usando Gemini AI

- **[gemini-scheduled-triage.yml](workflows/gemini-scheduled-triage.yml)** — Triagem de issues agendada
  Executa triagem periódica em issues abertas para manter a higiene do projeto

## Configuração de Comandos

O diretório `.github/commands/` contém arquivos de configuração TOML para workflows Gemini AI:

- **[gemini-invoke.toml](commands/gemini-invoke.toml)** — Configuração do comando invoke
- **[gemini-review.toml](commands/gemini-review.toml)** — Configuração do comando review
- **[gemini-triage.toml](commands/gemini-triage.toml)** — Configuração do comando triage
- **[gemini-scheduled-triage.toml](commands/gemini-scheduled-triage.toml)** — Configuração de triagem agendada

## Documentação

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Documentação abrangente da pipeline CI/CD
  Guia detalhado cobrindo gatilhos de workflow, configuração de ambiente, gerenciamento de secrets e solução de problemas

## Uso

Os workflows são acionados automaticamente por eventos do repositório (push, pull request, criação de issue). O dispatch manual de workflow está disponível através da interface do GitHub Actions para testes e depuração.

Para informações detalhadas sobre cada workflow e opções de configuração, consulte **[CICD_GUIDE.md](CICD_GUIDE.md)**.

# GitHub Actions - CI/CD Configuration

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

This directory contains GitHub Actions workflows and automation configurations for the Macena CS2 Analyzer project.

## Workflows

The `.github/workflows/` directory contains automated CI/CD pipelines:

### Core CI/CD
- **[build.yml](workflows/build.yml)** — Build verification pipeline
  Runs on every push and pull request to validate code quality:
  - Linting and code style checks (flake8, black)
  - Unit and integration test execution (pytest)
  - Security vulnerability scanning (bandit, safety)
  - Dependency verification
  - Build artifact generation

### Gemini AI Automation
- **[gemini-dispatch.yml](workflows/gemini-dispatch.yml)** — Gemini AI dispatch workflow
  Centralized dispatcher for routing Gemini AI tasks to appropriate handlers

- **[gemini-invoke.yml](workflows/gemini-invoke.yml)** — Gemini command invocation
  Executes Gemini AI commands for automated code generation and refactoring

- **[gemini-review.yml](workflows/gemini-review.yml)** — AI-powered code review
  Automated code review using Gemini for pull requests, checking for:
  - Code quality and adherence to engineering principles
  - Security vulnerabilities and anti-patterns
  - Documentation completeness
  - Test coverage requirements

- **[gemini-triage.yml](workflows/gemini-triage.yml)** — Issue triage automation
  Automatically categorizes, labels, and prioritizes GitHub issues using Gemini AI

- **[gemini-scheduled-triage.yml](workflows/gemini-scheduled-triage.yml)** — Scheduled issue triage
  Runs periodic triage on open issues to maintain project hygiene

## Commands Configuration

The `.github/commands/` directory contains TOML configuration files for Gemini AI workflows:

- **[gemini-invoke.toml](commands/gemini-invoke.toml)** — Invoke command configuration
- **[gemini-review.toml](commands/gemini-review.toml)** — Review command configuration
- **[gemini-triage.toml](commands/gemini-triage.toml)** — Triage command configuration
- **[gemini-scheduled-triage.toml](commands/gemini-scheduled-triage.toml)** — Scheduled triage configuration

## Documentation

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Comprehensive CI/CD pipeline documentation
  Detailed guide covering workflow triggers, environment setup, secrets management, and troubleshooting

## Usage

Workflows are automatically triggered by repository events (push, pull request, issue creation). Manual workflow dispatch is available through the GitHub Actions UI for testing and debugging.

For detailed information on each workflow and configuration options, see **[CICD_GUIDE.md](CICD_GUIDE.md)**.

# `tests/automated_suite/` — Suíte de testes automatizada em camadas

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 5 (Testability)
> **Skill:** `/test-coverage`

## Propósito

Suíte de testes automatizada em camadas que exercita a stack inteira do Macena CS2 Analyzer em vários níveis de granularidade. Os testes neste diretório complementam os módulos pytest organizados por tópico na raiz do pacote (`Programma_CS2_RENAN/tests/test_*.py`) — aqueles testes são orientados a unit e agrupados por domínio; os testes neste subpacote são organizados por **tipo de teste**.

A divisão existe para que o CI possa rodar um estágio rápido só de smoke e, em seguida, condicionar os estágios mais lentos ao sucesso dele.

## Inventário de arquivos

| Arquivo | Camada | Propósito |
|------|-------|---------|
| `__init__.py` | — | Marcador de pacote. |
| `test_smoke.py` | Smoke | Gate mais rápido — instancia managers core, abre o DB, carrega config. Deve rodar em segundos. Falha aqui significa que o build está fundamentalmente quebrado. |
| `test_unit.py` | Unit | Testes unitários direcionados sobre funções utilitárias core que não são específicas de tópico (por exemplo, helpers transversais, coerções de tipo). |
| `test_functional.py` | Functional | Testes funcionais para pipelines end-to-end com dependências externas mockadas — pipelines rodam em memória, sem demos reais / network. |
| `test_e2e.py` | End-to-end | Arquivos de demo reais ou de fixture rodam pelo caminho completo de ingestão → vetorização → inferência. Mais pesado; atrás do gate `CS2_INTEGRATION_TESTS=1`. |
| `test_system_regression.py` | Regressão | Checks de regressão a nível de sistema: inputs comprovadamente ruins, reproduções de bugs históricos, comparações com golden files. |

## Executando

```bash
# Apenas smoke (rápido)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py -v

# Smoke + unit (fast lane padrão do CI)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_smoke.py \
                   Programma_CS2_RENAN/tests/automated_suite/test_unit.py -v

# Functional (pipelines em memória)
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_functional.py -v

# Suíte completa incluindo E2E (lento, requer demos)
CS2_INTEGRATION_TESTS=1 ./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/ -v

# Regressão
./.venv/bin/pytest Programma_CS2_RENAN/tests/automated_suite/test_system_regression.py -v
```

## Recomendação de staging em CI

Encadeie os testes para que um smoke quebrado aborte a execução de forma barata:

```
1. Smoke           (segundos)    -> bloqueia todos os estágios seguintes em caso de falha
2. Unit            (~1 min)      -> bloqueia functional / e2e em caso de falha
3. Functional      (~5 min)      -> bloqueia e2e em caso de falha
4. Regressão       (~5 min)      -> independente de e2e
5. E2E             (~30+ min)    -> apenas em runs staged / nightly
```

## Convenções

- **Smoke é para sanidade, não para cobertura.** Prefira dez testes de 50 ms a um teste de 5 s — feedback rápido vale mais do que validação completa nesta camada.
- **Testes funcionais devem mockar sistemas externos.** Sem network, sem arquivos de demo reais, sem Ollama, sem Steam API. Use as fixtures em `Programma_CS2_RENAN/tests/conftest.py`.
- **Testes E2E ficam atrás do gate `CS2_INTEGRATION_TESTS=1`.** Esta é a flag padrão a nível de projeto para testes lentos com dados reais.
- **Testes de regressão congelam bugs anteriores como fixtures.** Quando um bug é corrigido, adicione o input que falhava como caso de regressão para que ele não consiga voltar silenciosamente.

## Onde colocar um novo teste

| Pergunta | Resposta |
|----------|--------|
| É sobre uma única função ou classe? | `Programma_CS2_RENAN/tests/test_<topic>.py` (raiz organizada por tópico) |
| É um sanity check sub-segundo de que o build está vivo? | `automated_suite/test_smoke.py` |
| É um teste de pipeline cross-module com mocks? | `automated_suite/test_functional.py` |
| Requer demos reais / sistemas externos? | `automated_suite/test_e2e.py` (com gate) |
| É um lock-in do tipo "este bug nunca pode voltar"? | `automated_suite/test_system_regression.py` |

## Relacionados

- Testes organizados por tópico (raiz): `Programma_CS2_RENAN/tests/README.md`
- Fixtures compartilhadas: `Programma_CS2_RENAN/tests/conftest.py`
- Validador (gate separado): `tools/headless_validator.py` — rode depois do pytest, não no lugar dele.
- Smoke do RAP (adicionado na Fase 0): `Programma_CS2_RENAN/tests/test_rap_training_dry_run.py`

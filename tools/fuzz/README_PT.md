# `tools/fuzz/` — Harness de fuzz para o parser de demos

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Testes de robustez para o pipeline de ingestão de demos
> **Skill:** `/security-scan`, `/correctness-check`

## Finalidade

Este diretório abriga um harness de fuzz testing para a própria biblioteca `demoparser2` (mapeia para o controle C-SBX-02). Sua função é exercitar o parser com bytes de demo malformados, truncados e adversariais, confirmando que:

1. O parser **não** sofre segfault, panic ou trava em caso de input inválido.
2. As falhas afloram como exceções Python (capturáveis, recuperáveis).

Ele deliberadamente contorna os portões de pré-validação do app (`MIN_DEMO_SIZE = 10 MB`, verificação de magic byte) e chama `demoparser2.DemoParser(...)` diretamente — a robustez da própria biblioteca é a superfície sob teste.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `fuzz_demo_parser.py` | Fuzzer principal. Gera bytes aleatórios de demo (70% com o prefixo magic `PBDEMS2\0`, até 64 KiB) e os entrega a `demoparser2.DemoParser` + `parse_event("round_start")`. |

## Executando o fuzzer

```bash
# Execução padrão (budget de tempo de 30 minutos)
python tools/fuzz/fuzz_demo_parser.py

# Execução curta
python tools/fuzz/fuzz_demo_parser.py --time-budget 600 --seed 42

# Reproduzir um único crash input (exit 1 se reproduzir)
python tools/fuzz/fuzz_demo_parser.py --reproduce .fuzz/crashes/<hash>-<size>.dem
```

Quando [Atheris](https://github.com/google/atheris) está instalado, a execução é coverage-guided; caso contrário, recorre a um loop determinístico de input aleatório (`--force-fallback` pula Atheris explicitamente). Inputs de crash são escritos em `--crash-dir` (padrão `.fuzz/crashes/`) como `<sha256-prefix>-<size>.dem` (primeiros 16 caracteres hex do SHA-256) mais um sidecar `.meta` registrando a classe da exceção e a mensagem.

## Modos de falha contra os quais o fuzzer protege

- Cabeçalhos truncados (parser deve abortar de forma limpa).
- Campos de tamanho de mensagem inconsistentes (parser não pode ler além do limite).
- Índices inválidos em string-tables (parser não pode quebrar em lookups fora de alcance).
- Dados aleatórios com e sem o prefixo magic `PBDEMS2\0`.

No próprio aplicativo, lixo deste tamanho nunca chega ao parser: os portões de pré-validação da ingestão (`MIN_DEMO_SIZE = 10 MB`, verificação de magic byte — invariante `DS-12`) o rejeitam antes. O fuzzer existe para fortalecer a camada *atrás* desses portões.

## Relacionados

- Parser de demos: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Portão de validação: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Pipeline de ingestão: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- CI: execuções noturnas via `.github/workflows/fuzz-nightly.yml`; o harness loga em stdout/stderr (`logging.basicConfig`, logger `fuzz_demo_parser`).

## Não faça

- **Não** entregue demos reais de usuários ao fuzzer — ele gera seu próprio input descartável; mantenha demos reais fora de `.fuzz/`.
- **Não** desabilite a guarda `MIN_DEMO_SIZE` da ingestão porque "o fuzzer passa" — a guarda é a primeira linha de defesa em produção.
- **Não** comite arquivos de demo de casos de falha no repositório. `.fuzz/crashes/` permanece local; capture o seed (ou o conteúdo do sidecar `.meta`) e reproduza com `--reproduce` sob demanda.

# `tools/fuzz/` — Harness de fuzz para o parser de demos

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Testes de robustez para o pipeline de ingestão de demos
> **Skill:** `/security-scan`, `/correctness-check`

## Finalidade

Este diretório abriga um harness de fuzz testing para o parser de demos baseado em `demoparser2`. Sua função é exercitar o parser com arquivos `.dem` malformados, truncados e adversariais, confirmando que:

1. O parser **não** sofre segfault, panic ou trava em caso de input inválido.
2. As falhas afloram como exceções Python (capturáveis, recuperáveis).
3. O portão de pré-validação (`MIN_DEMO_SIZE = 10 MB`, verificação de magic byte) rejeita lixo antes que o parser o veja.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote. |
| `fuzz_demo_parser.py` | Fuzzer principal. Gera bytes corrompidos de demo e os entrega a `backend/data_sources/demo_parser.parse_demo()`. |

## Executando o fuzzer

```bash
# Iteração única (smoke test)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 1

# Fuzzing prolongado (CI / execuções noturnas)
./.venv/bin/python tools/fuzz/fuzz_demo_parser.py --iterations 10000 \
    --seed 42 --report /tmp/fuzz_report.json
```

O harness reporta cada modo de falha que observa, com o byte-offset da corrupção e a classe de exceção resultante.

## Modos de falha contra os quais o fuzzer protege

- Cabeçalhos truncados (parser deve abortar de forma limpa).
- Campos de tamanho de mensagem inconsistentes (parser não pode ler além do limite).
- Índices inválidos em string-tables (parser não pode quebrar em lookups fora de alcance).
- Densidade patológica de ticks (parser deve respeitar limites de memória).
- Arquivos menores que `MIN_DEMO_SIZE` (devem ser rejeitados antes do parsing — invariante `DS-12`).

## Relacionados

- Parser de demos: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Portão de validação: `Programma_CS2_RENAN/backend/processing/validation/dem_validator.py`
- Pipeline de ingestão: `Programma_CS2_RENAN/ingestion/pipelines/README.md`
- Logging estruturado: falhas são emitidas via `get_logger("cs2analyzer.fuzz")` e terminam em `Programma_CS2_RENAN/logs/cs2_analyzer.log`.

## Não faça

- **Não** entregue demos reais de usuários ao fuzzer — a etapa de corrupção iria destruí-los. O harness gera seu próprio input descartável.
- **Não** desabilite a guarda `MIN_DEMO_SIZE` para "acelerar" o fuzzing. A guarda faz parte da superfície sob teste.
- **Não** comite arquivos de demo de casos de falha no repositório. Capture a sequência de bytes (ou seed) no relatório e reproduza sob demanda.

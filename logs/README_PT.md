# `logs/` — Staging de logs na raiz do repo

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Staging de logs em runtime (read-only por convenção)

## Para onde os logs realmente vão

O arquivo de log primário da aplicação é **`Programma_CS2_RENAN/logs/cs2_analyzer.log`** (rotacionado em `.log.1`, `.log.2`, `.log.3`). É o arquivo em que o `app_logger` escreve via `observability/logger_setup.py`.

Este diretório `./logs/` no nível superior existe como fallback / área de staging para ferramentas que rodam antes do logger do pacote ser configurado (ex.: saída de bootstrap muito inicial, testes de smoke ROCm, saída de scripts de packaging).

```
logs/
└── cs2_analyzer.log     # Log legacy de bootstrap / startup inicial (pequeno)
```

Para investigação ativa, **leia `Programma_CS2_RENAN/logs/cs2_analyzer.log`**, não o arquivo aqui.

## Formato do log

Toda a saída de `app_logger` é **JSON estruturado** com um evento por linha:

```json
{"ts":"2026-05-06T14:21:41+0200","lvl":"INFO","mod":"cs2analyzer.app","thread":"MainThread","msg":"..."}
```

Campos:

| Chave | Significado |
|-------|-------------|
| `ts` | Timestamp ISO 8601 com offset de timezone |
| `lvl` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `mod` | Nome do logger (`cs2analyzer.<dominio>.<modulo>`) |
| `thread` | Identificador da thread |
| `msg` | Mensagem livre (pode conter escapes Unicode) |

## Filtragem

```bash
# Últimos 50 ERRORs do log do pacote
grep '"lvl":"ERROR"' Programma_CS2_RENAN/logs/cs2_analyzer.log | tail -50

# Entradas do ciclo de training
grep '"mod":"cs2analyzer.app"' Programma_CS2_RENAN/logs/cs2_analyzer.log | grep -i training

# Taxa por módulo
awk -F'"mod":"' 'NF>1{split($2,a,"\"");print a[1]}' Programma_CS2_RENAN/logs/cs2_analyzer.log | sort | uniq -c | sort -rn | head -20
```

## Rotação

A rotação é tratada pelo `RotatingFileHandler` padrão configurado em `observability/logger_setup.py`. Defaults: 5 MB por arquivo, 3 backups. O diretório de log do pacote é o destino canônico — este diretório `./logs/` na raiz do repo NÃO participa da rotação.

## Não faça

- Não commite arquivos de log grandes. Adicione novos padrões ao `.gitignore` se uma ferramenta começar a depender deste diretório.
- Não parseie logs assumindo a ordem de linhas entre threads — escritas concorrentes se interleavam.
- Não logue segredos. A configuração do `app_logger` saneia credenciais, mas chamadas de logging customizadas ainda devem evitar PII / chaves de API por força das regras de segurança.

## Relacionados

- Configuração do logger: `Programma_CS2_RENAN/observability/logger_setup.py`
- Saída do validador (separada, apenas stdout): `tools/headless_validator.py`
- Pitfalls de buffering de log (processos de longa duração sob `tee`): ver as notas em `CLAUDE.md`

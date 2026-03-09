# Observabilidade & Proteção em Tempo de Execução

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Auto-proteção em tempo de execução da aplicação (RASP), logging estruturado com IDs de correlação e rastreamento de erros Sentry com limpeza de PII. Fornece observabilidade abrangente para depuração, auditoria de segurança e monitoramento de produção.

## Componentes Principais

### `rasp.py`
- **`RASPGuard`** — Verificação de integridade em tempo de execução via checagem de hash de arquivo
- **`run_rasp_audit()`** — Escaneia arquivos fonte Python e compara com manifesto de integridade
- **`IntegrityError`** — Exceção customizada levantada quando incompatibilidade de hash é detectada
- Detecta modificações de código não autorizadas, ataques de cadeia de suprimentos e corrupção de arquivo
- Resultados de auditoria logados com níveis de severidade (CRITICAL, ERROR, WARNING)

### `logger_setup.py`
- **`get_logger(name)`** — Função factory para loggers estruturados
- Injeção de ID de correlação para rastreamento de requisições entre módulos
- Saída de log formatada em JSON para parsing de máquina
- Filtragem de nível de log por namespace de módulo
- Redação automática de campos sensíveis (PII, secrets, tokens)
- Rotação de arquivo com compressão e política de retenção

### `sentry_setup.py`
- **`init_sentry()`** — Inicializa SDK Sentry com DSN específico do ambiente
- **`add_breadcrumb()`** — Logging de breadcrumb contextual para relatórios de erro
- **Limpeza de PII** — Remoção automática de dados sensíveis de stack traces
- Monitoramento de performance com amostragem de transações
- Marcação de release para rastreamento de versões
- Separação de ambientes (development/staging/production)

## Padrão de Logging Estruturado

```python
from observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.mymodule")
logger.info("Processing match", extra={"match_id": 12345, "map": "de_dust2"})
logger.error("Ingestion failed", extra={"file": "demo.dem", "error_code": "PARSE_ERROR"})
```

## Integração de Auditoria RASP

Auditoria RASP executa:
- Na inicialização da aplicação (se `config.ENABLE_RASP=True`)
- Via CLI: `python macena.py sys rasp-audit`
- Em pipeline CI/CD via verificações de segurança `Goliath_Hospital.py`

## Integração Sentry

Configuração de rastreamento de erros:
- `SENTRY_DSN` carregado de variável de ambiente
- Taxa de amostragem: 100% em development, 10% em production
- Taxa de amostragem de traces: 10% para monitoramento de performance
- Limpeza de PII via hook `before_send`

## IDs de Correlação

Todas as entradas de log incluem `correlation_id` para rastreamento de requisições. Gerado nos pontos de entrada de ingestão/análise/coaching e propagado através da cadeia de chamadas.

## Retenção de Logs

- Development: 7 dias
- Production: 90 dias
- Erros críticos: retenção permanente no Sentry

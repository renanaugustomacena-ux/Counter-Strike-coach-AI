# Observabilidade & Protecao em Tempo de Execucao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/observability/`
**Proprietario:** infraestrutura core do Macena CS2 Analyzer

## Introducao

Este pacote fornece os tres pilares da observabilidade em tempo de execucao para o
CS2 Analyzer: logging estruturado, protecao de integridade e rastreamento remoto de
erros. Todos os modulos do projeto direcionam seus diagnosticos atraves deste pacote,
garantindo uma superficie de observabilidade unica e consistente. O design prioriza
comportamento deterministico, zero falhas silenciosas e isolamento rigoroso de PII antes
que qualquer dado deixe a fronteira do processo.

## Inventario de Arquivos

| Arquivo | Proposito | Exports Principais |
|---------|-----------|-------------------|
| `logger_setup.py` | Logging estruturado JSON centralizado com IDs de correlacao | `get_logger()`, `get_tool_logger()`, `set_correlation_id()`, `configure_log_dir()`, `configure_retention()` |
| `rasp.py` | Guarda de integridade Runtime Application Self-Protection | `RASPGuard`, `run_rasp_audit()`, `IntegrityError` |
| `sentry_setup.py` | Integracao SDK Sentry com duplo opt-in e limpeza de PII | `init_sentry()`, `add_breadcrumb()` |
| `error_codes.py` | Registro centralizado de codigos de erro com severidade e remediacao | `ErrorCode`, `log_with_code()`, `get_all_codes()` |
| `exceptions.py` | Hierarquia de excecoes de dominio enraizada em `CS2AnalyzerError` | `CS2AnalyzerError`, `ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`, `IntegrationError`, `UIError` |
| `__init__.py` | Marcador de pacote | -- |

## Arquitetura & Conceitos

### Logging Estruturado (`logger_setup.py`)

Todos os loggers sao criados via `get_logger("cs2analyzer.<modulo>")`. A factory conecta
cada logger a dois handlers:

1. **File handler** -- `RotatingFileHandler` escrevendo linhas JSON em `cs2_analyzer.log`
   (rotacao de 5 MB, 3 backups). Recai para `FileHandler` simples quando ocorre um
   `PermissionError` (contencao de lock no Windows, anotado como `LS-01`).
2. **Console handler** -- formato legivel com limiar `WARNING`, mantendo stdout
   limpo durante operacao normal.

Cada registro de log e enriquecido por `_CorrelationFilter`, que injeta o
`correlation_id` thread-local definido via `set_correlation_id()`. Isso habilita
rastreamento ponta-a-ponta de um unico job de ingestao, ciclo de treinamento ou sessao
de coaching atraves de todos os modulos.

O nivel de log e resolvido no momento da criacao do logger a partir da variavel de
ambiente `CS2_LOG_LEVEL` (ex. `CS2_LOG_LEVEL=DEBUG`), permitindo sessoes de debug
zero-code sem modificar arquivos fonte. Reconfiguracao em tempo de execucao tambem e
possivel via `configure_log_level(logging.DEBUG)`.

Scripts CLI standalone (validadores, diagnosticos) usam `get_tool_logger(tool_name)`,
que escreve em um arquivo dedicado `logs/tools/<tool_name>_<timestamp>.json` para
evitar poluir o log da aplicacao principal.

`configure_retention(max_days=30)` aplica uma politica de ciclo de vida dos logs
eliminando arquivos `.log` e `.json` mais antigos que a janela de retencao.
Best-effort -- erros do SO sao ignorados silenciosamente para evitar crashes da
aplicacao por operacoes de limpeza.

### Guarda de Integridade RASP (`rasp.py`)

`RASPGuard` verifica que nenhum arquivo fonte Python foi adulterado desde a ultima
build ou geracao do manifesto. Ele le `core/integrity_manifest.json`, que mapeia
caminhos relativos de arquivo para seus hashes SHA-256, e compara cada entrada contra
o sistema de arquivos corrente.

Comportamentos-chave:

- **Assinatura HMAC** (`R1-12`): o manifesto em si e assinado com uma chave
  HMAC-SHA256. Builds de producao injetam a chave via `CS2_MANIFEST_KEY`;
  desenvolvimento recai para uma chave estatica com um warning logado (`RP-01`).
- **Suporte a binarios frozen**: quando executando dentro de um bundle PyInstaller,
  o manifesto e resolvido a partir de `sys._MEIPASS` com multiplos caminhos candidatos.
- **Entry point de conveniencia**: `run_rasp_audit(project_root)` instancia a guarda,
  executa a verificacao e loga todas as violacoes no nivel `CRITICAL`.

### Rastreamento de Erros Sentry (`sentry_setup.py`)

O reporte remoto de erros segue um modelo de **duplo opt-in**: tanto `enabled=True`
quanto uma string `dsn` valida devem ser fornecidos. Isso previne vazamentos
acidentais de telemetria.

PII e removido no hook `_before_send` antes que qualquer evento deixe o processo:

- `server_name` e substituido por `"redacted"`.
- Nomes de arquivo em stack traces contendo o diretorio home do usuario sao limpos.
- Mensagens e dados de breadcrumb sao sanitizados de forma identica.

O SDK e inicializado com `send_default_pii=False` e um `traces_sample_rate` de 10%
para monitoramento leve de performance. A `LoggingIntegration` captura breadcrumbs
no nivel WARNING e escala registros no nivel ERROR para eventos Sentry completos.

`add_breadcrumb()` e um no-op quando Sentry nao esta inicializado, tornando-o seguro
para chamar incondicionalmente em todo o codebase.

### Registro de Codigos de Erro (`error_codes.py`)

Cada codigo de erro anotado no projeto (ex. `LS-01`, `RP-01`, `SE-04`) e registrado
como membro enum `ErrorCode` carregando severidade, modulo proprietario, descricao e
orientacao de remediacao. `log_with_code(ErrorCode.LS_01, "mensagem")` prefixa a
mensagem com o codigo formal para grepping machine-parseable dos logs.

### Hierarquia de Excecoes (`exceptions.py`)

Todas as excecoes de dominio herdam de `CS2AnalyzerError`, que aceita um parametro
opcional `error_code` para logging estruturado. Os subtipos incluem
`ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`,
`IntegrationError` e `UIError`.

## Integracao

| Consumidor | Uso |
|------------|-----|
| `core/session_engine.py` | `set_correlation_id()` no inicio do ciclo daemon; `run_rasp_audit()` no boot |
| `core/config.py` | `configure_log_dir(LOG_DIR)` apos resolucao de caminho para quebrar import circular |
| Pipeline `ingestion/` | `get_logger()` + IDs de correlacao para rastreamento por-demo |
| Treinamento `backend/nn/` | `get_logger()` para logging de epoch/loss; `add_breadcrumb()` nos checkpoints |
| `apps/qt_app/` | `init_sentry()` na inicializacao da aplicacao com DSN consentido pelo usuario |
| Scripts `tools/` | `get_tool_logger()` para diagnostico isolado de ferramentas |
| Hooks pre-commit | `run_rasp_audit()` via `tools/headless_validator.py` |

## Notas de Desenvolvimento

- **Guarda de import circular**: `config.py` precisa de `get_logger()` no momento do
  import, mas `get_logger()` nao deve importar de `config`. A solucao e
  `configure_log_dir()`, chamada por `config.py` apos `LOG_DIR` ser calculado.
- **Thread safety**: `_correlation_local` usa `threading.local()`, entao IDs de
  correlacao sao isolados por thread. Threads daemon no Quad-Daemon engine definem
  cada um seu proprio ID no inicio do ciclo.
- **Testes**: nas suites de teste, `CS2_LOG_LEVEL=DEBUG` e
  `configure_log_dir(tmp_path)` redirecionam toda saida para um diretorio temporario.
  Sentry e automaticamente ignorado quando `pytest` e detectado em `sys.modules`.
- **Pre-commit**: o hook `integrity-manifest` regenera e assina o manifesto;
  `headless_validator.py` executa `run_rasp_audit()` para verifica-lo.

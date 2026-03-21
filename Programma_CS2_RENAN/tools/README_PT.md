> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Ferramentas de Validacao e Diagnostico

**Autoridade:** `Programma_CS2_RENAN/tools/` -- Utilitarios de validacao, diagnostico e desenvolvimento a nivel de pacote para o Macena CS2 Analyzer.

Este diretorio contem ferramentas internas especificas do pacote `Programma_CS2_RENAN`. Sao
distintas do diretorio `tools/` no nivel raiz (que contem entry points a nivel de projeto como
`headless_validator.py` invocado por hooks pre-commit). As ferramentas aqui formam uma hierarquia
de validacao de 4 niveis que garante a saude do sistema desde verificacoes rapidas ate diagnosticos
clinicos aprofundados. Cada ferramenta herda da ABC compartilhada `BaseValidator` definida em
`_infra.py`, produzindo objetos estruturados `ToolResult` / `ToolReport` com niveis de severidade.

## Hierarquia de Validacao

Os quatro niveis sao projetados para serem executados em ordem crescente de profundidade e custo de tempo:

| Nivel | Ferramenta | Verificacoes | Tempo | Proposito |
|-------|------------|-------------|-------|-----------|
| 1 | `headless_validator.py` | 291+ em 7 fases | <20s | Gate de regressao rapido (obrigatorio antes da conclusao de tarefas) |
| 2 | Suite pytest | 1.515+ testes em 79 arquivos | ~2min | Validacao logica, assercoes de contrato |
| 3 | `backend_validator.py` | 40 em 7 secoes | ~30s | Saude do build, zoo de modelos, pipeline de coaching |
| 4 | `Goliath_Hospital.py` | 10 departamentos | ~60s | Diagnostico clinico abrangente |

## Inventario de Arquivos

| Arquivo | Categoria | Descricao |
|---------|-----------|-----------|
| `_infra.py` | Infraestrutura | Infraestrutura compartilhada: estabilizacao de caminhos, ABC `BaseValidator`, `Console`, `ToolResult`, `ToolReport`, guarda de venv |
| `__init__.py` | Infraestrutura | Marcador de pacote |
| `headless_validator.py` | Validacao | Gate de regressao rapido de 7 fases (ambiente, imports core, imports backend, schema de banco de dados, carregamento de config, smoke ML, observabilidade) |
| `backend_validator.py` | Validacao | Gate de saude do backend com 7 secoes (ambiente, banco de dados, zoo de modelos, analise, coaching, integridade de recursos, saude de servicos) |
| `Goliath_Hospital.py` | Diagnostico | Suite de diagnostico estilo hospitalar com 10 departamentos (ER, Radiologia, Laboratorio de Patologia, Cardiologia, Neurologia, Oncologia, Pediatria, ICU, Farmacia, Clinica de Ferramentas) |
| `ui_diagnostic.py` | Diagnostico | Validacao de UI headless (recursos, localizacao, assets, validacao KV, coordenadas espaciais) |
| `Ultimate_ML_Coach_Debugger.py` | Diagnostico | Ferramenta de falsificacao de estados de crenca neurais e logica de decisao; verifica limiares de fidelidade, sondas de estabilidade, rastreabilidade de insights |
| `build_tools.py` | Build | Pipeline de build consolidada (lint, test, PyInstaller, verificacao de hash, manifesto de integridade) |
| `context_gatherer.py` | Desenvolvimento | Coletor de contexto relacional para um dado arquivo (imports, dependentes, testes, superficie de API, historico git) |
| `db_inspector.py` | Desenvolvimento | CLI de inspecao de banco de dados para estado completo do DB sem queries manuais |
| `dead_code_detector.py` | Pre-commit | Deteccao de modulos orfaos, imports de teste obsoletos, pacotes vazios |
| `dev_health.py` | Pre-commit | Verificacao de saude de desenvolvimento com modos `--quick` (pre-commit, <10s) e `--full` (headless + backend) |
| `demo_inspector.py` | Desenvolvimento | Inspecao unificada de arquivos demo (eventos, campos, rastreamento de entidades); consolida 7 scripts probe legados |
| `project_snapshot.py` | Desenvolvimento | Snapshot compacto do estado do projeto (dependencias, estado git, estatisticas do DB, ambiente) |
| `seed_hltv_top20.py` | Dados | Popula o banco de dados de metadados HLTV com top-20 times, jogadores e fichas de estatisticas |
| `sync_integrity_manifest.py` | Pre-commit | Regenera `core/integrity_manifest.json` a partir dos hashes SHA-256 dos arquivos `.py` de producao |
| `user_tools.py` | Usuario | Utilitarios interativos consolidados (personalize, customize, manual-entry, weights, heartbeat) |
| `logs/` | Infraestrutura | Logs de execucao das ferramentas |

## Infraestrutura Compartilhada (`_infra.py`)

Todas as ferramentas neste diretorio se baseiam no modulo de infraestrutura compartilhada `_infra.py`, que fornece:

- **`path_stabilize()`** -- Configuracao canonica de caminhos; adiciona `PROJECT_ROOT` ao
  `sys.path`, define `KIVY_NO_ARGS=1`, configura codificacao UTF-8. Retorna
  `(PROJECT_ROOT, SOURCE_ROOT)`.
- **`require_venv()`** -- Guarda de venv que sai se nao estiver no ambiente virtual `cs2analyzer`
  (ignorada quando `CI` esta definido).
- **`BaseValidator`** -- Classe base abstrata com `define_checks()`, `check()`, `run()`,
  integracao `Console` e geracao de relatorios JSON.
- **`ToolResult`** / **`ToolReport`** -- Dataclasses estruturadas para resultados de verificacoes com
  niveis `Severity` (CRITICAL, WARNING, INFO, OK).
- **`Console`** -- Saida de terminal estilo Rich com cabecalhos de secao, indicadores
  pass/fail e tabelas de resumo.

## Departamentos Goliath Hospital

A suite de diagnostico `Goliath_Hospital.py` organiza as verificacoes em departamentos com tema medico:

| Departamento | Foco |
|--------------|------|
| Emergency Room (ER) | Problemas criticos de sintaxe e import |
| Radiology | Varreduras de integridade de assets visuais |
| Pathology Lab | Qualidade de dados, deteccao de mock vs dados reais |
| Cardiology | Saude de modulos core (DB, config, modelos) |
| Neurology | Integridade de sistemas ML/AI |
| Oncology | Codigo morto, padroes depreciados, divida tecnica |
| Pediatrics | Arquivos novos e recentemente modificados |
| ICU | Testes de integracao, fluxos end-to-end |
| Pharmacy | Saude de dependencias e verificacoes de versao |
| Tool Clinic | Valida todos os scripts de ferramentas do projeto |

## Integracao Pre-commit

Tres ferramentas neste diretorio sao invocadas como hooks pre-commit:

1. **`dev_health.py --quick`** -- Smoke test de import, verificacao de DB ativo, validacao de config (<10s)
2. **`dead_code_detector.py`** -- Varredura de modulos orfaos e imports de teste obsoletos
3. **`sync_integrity_manifest.py`** -- Regenera o manifesto de integridade RASP; sai com 1 se o
   manifesto em disco diverge dos hashes calculados quando executado com `--verify-only`

O `headless_validator.py` e invocado pos-tarefa (nao como hook git) e deve sair com 0 antes
que qualquer tarefa de desenvolvimento seja considerada concluida.

## Uso

```bash
# Ativar o ambiente virtual primeiro
source ~/.venvs/cs2analyzer/bin/activate

# Validacao headless (gate pos-tarefa obrigatorio)
python Programma_CS2_RENAN/tools/headless_validator.py

# Validacao de backend (zoo de modelos, pipeline de coaching, servicos)
python Programma_CS2_RENAN/tools/backend_validator.py

# Diagnostico completo Goliath Hospital
python Programma_CS2_RENAN/tools/Goliath_Hospital.py

# Verificacao de saude de desenvolvimento rapida (pre-commit)
python Programma_CS2_RENAN/tools/dev_health.py --quick

# Verificacao de saude de desenvolvimento completa
python Programma_CS2_RENAN/tools/dev_health.py --full

# Inspecao de banco de dados
python Programma_CS2_RENAN/tools/db_inspector.py

# Inspecao de arquivo demo
python Programma_CS2_RENAN/tools/demo_inspector.py all --demo caminho/para/arquivo.dem

# Pipeline de build
python Programma_CS2_RENAN/tools/build_tools.py build

# Snapshot do estado do projeto
python Programma_CS2_RENAN/tools/project_snapshot.py

# Popular dados HLTV top-20
python -m Programma_CS2_RENAN.tools.seed_hltv_top20
```

## Notas de Desenvolvimento

- Todas as ferramentas usam `_infra.path_stabilize()` para resolucao consistente de caminhos.
  Nunca manipule `sys.path` diretamente nos scripts de ferramentas.
- Os codigos de saida sao padronizados: `0 = PASS`, `1 = FAIL`. Os hooks pre-commit dependem
  deste contrato.
- O padrao `BaseValidator` garante que cada ferramenta produza tanto saida de console legivel
  por humanos quanto relatorios JSON legiveis por maquina salvos em `tools/logs/`.
- `Goliath_Hospital.py` usa `print()` para saida de console em vez de logging estruturado.
  Como ferramenta de diagnostico (nao servico de producao), isso e aceitavel -- todos os
  resultados sao capturados em objetos `DiagnosticFinding` com niveis de severidade.
- `demo_inspector.py` consolida 7 scripts probe legados (`probe_demo_data`, `probe_entity_track`,
  `probe_events_advanced`, `probe_inventory`, `probe_stats_fields`, `probe_trajectories`,
  `probe_inv_direct`) em uma unica ferramenta unificada.
- `user_tools.py` consolida 7 ferramentas interativas legadas (`Manual_Data_v2`, `Personalize_v2`,
  `GUI_Master_Customizer`, `ML_Coach_Control_Panel`, `manage_sync`, `Seed_Pro_Data`,
  `Heartbeat_Monitor`) em subcomandos de um unico entry point.

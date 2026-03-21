> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Testes de Verificacao e Forenses no Nivel Raiz

> **Autoridade:** Regra 3 (Zero-Regressao)
> **Skill:** `/correctness-check`

Testes de verificacao e forenses no nivel raiz para componentes criticos do sistema Macena CS2 Analyzer. Estes testes complementam a suite de testes principal em `Programma_CS2_RENAN/tests/` com verificacoes de nivel superior focadas em integracao que operam com dados reais semelhantes aos de producao.

## Estrutura do Diretorio

```
tests/
├── conftest.py                     # Configuracao pytest no nivel raiz e fixtures
├── verify_chronovisor_logic.py     # Verificacao da logica do Chronovisor
├── verify_chronovisor_real.py      # Chronovisor com dados de demo reais
├── verify_csv_ingestion.py         # Verificacao do pipeline de ingestao CSV
├── verify_map_integration.py       # Integracao de mapas e dados espaciais
├── verify_reporting.py             # Pipeline de relatorios (PDF, graficos)
├── verify_superposition.py         # Verificacao da rede superposition
├── setup_golden_data.py            # Configuracao de dados golden para testes
└── forensics/                      # Scripts de debug e diagnostico
    ├── check_db_status.py          # Diagnostico de conectividade do banco de dados
    ├── check_failed_tasks.py       # Analise de falhas de tarefas de ingestao
    ├── debug_env.py                # Debug de variaveis de ambiente
    ├── debug_nade_cols.py          # Debug de colunas de granadas
    ├── debug_parser_fields.py      # Validacao de campos do demo parser
    ├── forensic_parser_test.py     # Investigacao do comportamento do parser
    ├── probe_missing_tables.py     # Verificacao de completude do schema
    ├── test_skill_logic.py         # Validacao do sistema de skills
    ├── verify_map_dimensions.py    # Verificacao de limites dos mapas
    └── verify_spatial_integrity.py # Consistencia de dados espaciais
```

## Categorias de Testes

### Testes de Verificacao (Principais)

Estes testes verificam o comportamento critico do sistema usando dados reais:

| Arquivo de Teste | O Que Verifica | Dados Necessarios |
|-----------|-----------------|---------------|
| `verify_chronovisor_logic.py` | Deteccao de escala temporal, deduplicacao de ticks, interpolacao de replay | Nenhum (nivel unitario) |
| `verify_chronovisor_real.py` | Pipeline completo do Chronovisor com arquivos `.dem` reais | Arquivos de demo reais |
| `verify_csv_ingestion.py` | Pipeline de importacao CSV (estatisticas externas → banco de dados) | Arquivos CSV em `data/external/` |
| `verify_map_integration.py` | Transformacoes de coordenadas de mapa, tratamento de Z-cutoff, resolucao de landmarks | `data/map_config.json` |
| `verify_reporting.py` | Geracao de PDF, renderizacao de heatmap, graficos de momentum | Banco de dados com dados de partida |
| `verify_superposition.py` | Forward pass da SuperpositionLayer, fluxo de gradientes | Nenhum (tensores sinteticos) |
| `setup_golden_data.py` | Cria snapshots de dados de referencia para testes de regressao | Banco de dados com dados de partida |

### Scripts Forenses

O subdiretorio `forensics/` contem scripts de diagnostico para investigar problemas especificos:

| Script | Proposito |
|--------|---------|
| `check_db_status.py` | Testa conectividade do banco de dados, modo WAL, existencia de tabelas |
| `check_failed_tasks.py` | Consulta a tabela `IngestionTask` para tarefas falhadas com detalhes do erro |
| `debug_env.py` | Exibe variaveis de ambiente relevantes para a aplicacao |
| `debug_nade_cols.py` | Verifica colunas relacionadas a granadas nas tabelas de dados de tick |
| `debug_parser_fields.py` | Valida nomes de campos do demoparser2 contra o schema esperado |
| `forensic_parser_test.py` | Investigacao profunda do comportamento do parser em arquivos de demo especificos |
| `probe_missing_tables.py` | Compara definicoes SQLModel com o schema real do banco de dados |
| `test_skill_logic.py` | Valida a logica de selecao e ponderacao de skills de coaching |
| `verify_map_dimensions.py` | Verifica limites do mapa, fatores de escala e intervalos de coordenadas |
| `verify_spatial_integrity.py` | Validacao cruzada de dados espaciais entre `map_config.json` e `spatial_data.py` |

## `conftest.py` — Configuracao Root

O `conftest.py` no nivel raiz fornece:

- **Configuracao de caminhos** — insere a raiz do projeto no `sys.path` para que todas as importacoes sejam resolvidas corretamente
- **Fixture da raiz do projeto** — caminho `PROJECT_ROOT` disponivel para todos os testes
- **Isolamento de ambiente** — garante que os testes nao modifiquem acidentalmente dados de producao

```python
# conftest.py simplificado
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

## Filosofia de Testes

1. **Abordagem forense** — testes investigam caminhos de dados reais e comportamento efetivo do sistema, nao mocks sinteticos
2. **Nenhum dado sintetico** — todos os testes usam arquivos de demo reais ou dados equivalentes a producao sempre que possivel
3. **Skip se indisponivel** — testes pulam graciosamente (via `pytest.skip()`) quando dados necessarios estao ausentes
4. **Cobertura end-to-end** — foco em pontos de integracao e workflows entre modulos
5. **Nao destrutivo** — testes nunca modificam bancos de dados de producao ou arquivos de configuracao

## Relacao com a Suite de Testes Principal

| Aspecto | `tests/` (raiz) | `Programma_CS2_RENAN/tests/` (principal) |
|--------|-----------------|--------------------------------------|
| Foco | Integracao, E2E, forense | Testes unitarios, testes de modulo |
| Quantidade de testes | ~18 scripts | 1.515+ testes em 79 arquivos |
| Dados | Demos reais, DB de producao | DB em memoria, mocks, fixtures |
| Framework | pytest + scripts standalone | pytest com rico ecossistema de fixtures |
| Frequencia de execucao | Sob demanda, debugging | Cada commit (hooks pre-commit) |

## Executando os Testes

```bash
# Ativar o ambiente virtual
source /home/renan/.venvs/cs2analyzer/bin/activate

# Executar todos os testes de verificacao via pytest
python -m pytest tests/ -v

# Executar um script de verificacao especifico diretamente
python tests/verify_chronovisor_real.py

# Executar diagnosticos forenses
python tests/forensics/check_db_status.py

# Configurar dados golden para testes de regressao
python tests/setup_golden_data.py
```

## Notas de Desenvolvimento

- Estes testes NAO fazem parte do gate pre-commit — eles requerem dados reais que podem nao estar disponiveis em CI
- Snapshots de dados golden devem ser regenerados apos mudancas significativas no pipeline de ingestao
- Scripts forenses sao destinados a debugging interativo, nao a testes automatizados
- Ao adicionar um novo teste de verificacao, siga a convencao de nomenclatura `verify_*.py`
- Todos os scripts forenses saem com codigo 0 em caso de sucesso, diferente de zero em caso de erro
- A suite de testes principal (`Programma_CS2_RENAN/tests/`) e o gate de regressao primario

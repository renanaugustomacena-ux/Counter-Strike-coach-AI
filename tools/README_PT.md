> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Ferramentas de Projeto no Nivel Raiz

> **Autoridade:** Regra 3 (Zero-Regressao), Regra 6 (Governanca de Mudancas)
> **Skill:** `/validate`, `/pre-commit`

Ferramentas de projeto no nivel raiz para validacao, diagnostico, orquestracao de build e manutencao do Macena CS2 Analyzer. A ferramenta mais critica e o `headless_validator.py`, que e o gate de regressao obrigatorio pre-commit.

## Inventario de Arquivos

| Arquivo | Proposito | Categoria |
|---------|-----------|-----------|
| `headless_validator.py` | 291+ verificacoes de regressao em 23 fases | Validacao |
| `dead_code_detector.py` | Modulos orfaos, definicoes duplicadas, imports obsoletos | Validacao |
| `verify_all_safe.py` | Verificacao de seguranca em todos os modulos | Validacao |
| `portability_test.py` | Verificacoes de portabilidade multiplataforma | Validacao |
| `Feature_Audit.py` | Auditoria de alinhamento de features (parser vs pipeline ML) | Validacao |
| `run_console_boot.py` | Verificacao de boot via console | Validacao |
| `verify_main_boot.py` | Verificacao de boot da aplicacao principal | Validacao |
| `build_pipeline.py` | Orquestracao do pipeline de build (5 estagios) | Build |
| `audit_binaries.py` | Integridade de binarios pos-build (SHA-256) | Build |
| `db_health_diagnostic.py` | Diagnostico de saude do banco de dados (10 secoes) | Banco de Dados |
| `migrate_db.py` | Migracao de banco de dados com backward compatibility | Banco de Dados |
| `reset_pro_data.py` | Reset de dados de jogadores profissionais (idempotente) | Banco de Dados |
| `dev_health.py` | Orquestrador de saude do desenvolvimento | Manutencao |
| `Sanitize_Project.py` | Sanitizacao do projeto (remocao de dados locais) | Manutencao |
| `observe_training_cycle.py` | Monitoramento de metricas de treinamento | Observabilidade |
| `test_rap_lite.py` | Teste lite do modelo RAP | Testes |
| `test_tactical_pipeline.py` | Teste do pipeline de inferencia tatica | Testes |

## `headless_validator.py` --- O Gate de Regressao

Esta e a ferramenta mais importante de todo o projeto. Executa **291+ verificacoes automatizadas em 23 fases** e deve terminar com codigo de saida 0 antes de qualquer commit. Tambem esta conectado como hook pre-commit.

### Fases de Validacao

| Fase | O Que Verifica |
|------|---------------|
| 1. Import Health | Todos os modulos de producao importam sem erros |
| 2. Schema Integrity | O schema do banco de dados em memoria corresponde as definicoes SQLModel |
| 3. Config Loading | `get_setting()` e `get_credential()` resolvem corretamente |
| 4. ML Smoke Test | Instanciacao e forward pass para todos os 6 tipos de modelo |
| 5. UI Framework | PySide6 e Kivy importam com sucesso |
| 6. Platform Compat | Caminhos de codigo especificos do SO resolvem corretamente |
| 7. Contract Validation | Contratos de APIs publicas correspondem as implementacoes |
| 8. ML Invariants | METADATA_DIM=25, INPUT_DIM=25, OUTPUT_DIM=10 |
| 9. DB Integrity | Contagem de tabelas, chaves estrangeiras, existencia de indices |
| 10. Code Quality | Formatacao Black, ordenacao isort |
| 11. Package Structure | `__init__.py` em todos os pacotes, sem imports circulares |
| 12. Feature Pipeline | FeatureExtractor produz vetores de 25 dimensoes |
| 13. RAP Forward Pass | O forward pass do modelo RAP Coach e bem-sucedido |
| 14. Belief Contracts | Probabilidades do modelo belief no intervalo [0, 1] |
| 15. Circuit Breakers | Limiares de erro disparam corretamente |
| 16. Integrity Manifest | Hashes SHA-256 correspondem a `core/integrity_manifest.json` |
| 17. Security Scan | Nenhum segredo ou credencial hardcoded |
| 18. Config Consistency | Schema do arquivo de configuracoes corresponde as chaves esperadas |
| 19. Advanced Quality | Complexidade ciclomatica, deteccao de codigo duplicado |
| 20-23. | Verificacoes especializadas adicionais |

### Uso

```bash
# Validacao padrao (obrigatoria antes de cada commit)
python tools/headless_validator.py

# Codigo de saida: 0 = todas as verificacoes passaram, diferente de zero = falhas detectadas
echo $?
```

## Pipeline de Build

### `build_pipeline.py` --- Orquestracao de Build em 5 Estagios

```
Estagio 1: Sanitize  ->  Estagio 2: Test  ->  Estagio 3: Manifest  ->  Estagio 4: Compile  ->  Estagio 5: Audit
(limpar artefatos)       (executar testes)    (gerar hashes)          (PyInstaller)           (verificar binario)
```

### `audit_binaries.py` --- Integridade Pos-Build

Calcula hashes SHA-256 de todos os arquivos na saida do build e compara com os valores esperados. Detecta adulteracoes ou builds incompletos.

## Ferramentas de Banco de Dados

### `db_health_diagnostic.py` --- Diagnostico em 10 Secoes

| Secao | O Que Verifica |
|-------|---------------|
| 1 | Verificacao do modo WAL em todos os 3 bancos de dados |
| 2 | Existencia de tabelas e contagem de linhas |
| 3 | Integridade de restricoes de chave estrangeira |
| 4 | Cobertura de indices em colunas consultadas frequentemente |
| 5 | Metricas de qualidade de dados (taxas de NaN, valores anomalos) |
| 6 | Estado de migracao Alembic |
| 7 | Consistencia de bancos de dados per-match |
| 8 | Completude de metadados HLTV |
| 9 | Uso de armazenamento e tamanhos de arquivos |
| 10 | Saude do connection pool |

### `migrate_db.py` --- Migracao Segura

Encapsula migracoes Alembic com verificacoes de backward compatibility. Mais seguro do que executar `alembic upgrade head` diretamente.

### `reset_pro_data.py` --- Reset de Dados Profissionais

Reset multi-fase e idempotente dos dados de jogadores profissionais. Seguro para executar multiplas vezes. Fases: backup -> limpar tabelas -> resetar estado de sincronizacao -> verificar.

## Manutencao do Projeto

### `dev_health.py` --- Orquestrador de Saude

Executa multiplas ferramentas em sequencia e produz um relatorio de saude unificado:
1. Headless validator
2. Dead code detector
3. Portability test
4. Feature audit

### `Sanitize_Project.py` --- Limpar Estado Local

Remove todos os arquivos especificos do usuario e locais para distribuicao limpa:
- `user_settings.json`
- `database.db` e arquivos WAL/SHM
- Diretorio `logs/`
- Diretorios `__pycache__/`

## Uso

```bash
# Ativar ambiente virtual
source /home/renan/.venvs/cs2analyzer/bin/activate

# Validacao headless (executar antes de cada commit)
python tools/headless_validator.py

# Verificacao de saude do desenvolvimento
python tools/dev_health.py

# Verificacao de saude do banco de dados
python tools/db_health_diagnostic.py

# Verificacao de portabilidade
python tools/portability_test.py

# Deteccao de codigo morto
python tools/dead_code_detector.py

# Auditoria de alinhamento de features
python tools/Feature_Audit.py

# Pipeline de build
python tools/build_pipeline.py

# Sanitizacao do projeto (ATENCAO: remove dados locais)
python tools/Sanitize_Project.py
```

## Notas de Desenvolvimento

- Todas as ferramentas devem ser executadas a partir do diretorio raiz do projeto
- O headless validator e o gate de regressao inegociavel --- se falhar, o commit e bloqueado
- Ferramentas de banco de dados sao seguras para executar em dados de producao (usam consultas somente leitura, salvo indicacao explicita)
- `Sanitize_Project.py` e destrutivo --- remove bancos de dados locais e configuracoes. Use com cuidado.
- Ferramentas terminam com codigo 0 em caso de sucesso, diferente de zero em caso de falha
- O orquestrador `dev_health.py` fornece a verificacao de saude mais completa em um unico comando

# `backend/processing/validation/` -- Gates de integridade de dados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autoridade:** Regra 1 (Corretude), Regra 4 (Persistencia de Dados)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Proposito

Este pacote e dono dos gates de validacao que protegem todo consumidor downstream (training, inferencia, dashboard) contra entradas malformadas. Os arquivos aqui rodam nas fronteiras de ingestao, nas fronteiras de batch de treinamento e na inicializacao. Sao o lugar onde dados corrompidos ou inseguros devem falhar de forma ruidosa e cedo -- degradacao silenciosa e uma linha vermelha do projeto (Regra 1).

## Inventario de arquivos

| Arquivo | Modulo | Proposito | Exports principais |
|---------|--------|-----------|-------------------|
| `__init__.py` | -- | Marcador de pacote vazio. | -- |
| `dem_validator.py` | DEMValidator | Valida a estrutura do arquivo `.dem` antes do parse: integridade do nome de arquivo (metacaracteres shell, `F2-26`), pre-screening de formato limites de tamanho 100 KB -- 800 MB, magic bytes (`PBDEMS2` CS2 / `HL2DEMO` CSGO), verificacao de truncamento. Deliberadamente mais permissivo que o floor de ingestao `DS-12` (`MIN_DEMO_SIZE = 10 MB`, aplicado em `data_sources/demo_format_adapter.py`). | `DEMValidator`, `DEMValidationError`, `validate_dem_file()` |
| `drift.py` | Deteccao de drift | Deteccao estatistica de drift entre distribuicoes de features dos jogadores. Compara uma janela rolling recente (padrao 10) contra o historico passado e sinaliza features cujo z-score excede um limiar (padrao 2.5). `DRIFT_FEATURES` cobre estatisticas agregadas por partida; `TickFeatureDriftMonitor` cobre o vetor de entrada do modelo de 25-dim (`DRIFT-01`). | `detect_feature_drift()`, `DriftReport`, `DriftMonitor`, `TickFeatureDriftMonitor`, `should_retrain()` |
| `sanity.py` | Verificacoes de sanidade | Verificacoes de intervalo em DataFrames de demo parsados contra a tabela de limites `LIMITS` (kills, deaths, assists, ADR, headshot_pct, KAST). Modo strict levanta `ValueError`; modo trim faz clamp de outliers e auto-repara KAST e headshot_pct em escala percentual (`> 1.0` -> `/100`, `P-SAN-01`). | `validate_demo_sanity()`, `validate_and_trim()` |
| `schema.py` | Schema | Validacao estrutural versionada da saida do demo parser (`SCHEMA_VERSION = 2`: estatisticas core v1 + `accuracy`). | `get_active_schema()`, `validate_demo_schema()` |

## Onde cada validador roda

```
arquivo .dem cai na pasta de ingest
    +-- validate_dem_file()                        [dem_validator.py]
    |     - rejeita arquivos fora de 100 KB - 800 MB
    |     - rejeita arquivos com magic bytes invalidos
    |     - rejeita arquivos truncados
    |
    +-- pipeline faz parse da demo (demoparser2)
    |
    +-- DataFrame parsado: validate_demo_schema()   [schema.py]
    |     - colunas obrigatorias + tipos por SCHEMA_VERSION
    |
    +-- validate_demo_sanity() / validate_and_trim() [sanity.py]
    |     - limites de kills / deaths / assists / adr / headshot_pct / kast (LIMITS)
    |     - strict: levanta erro, non-strict: clamp de outliers
    |
    +-- linhas de tick persistidas no SQLite por partida

Fronteira de batch de treinamento
    +-- detect_feature_drift(...)                  [drift.py]
    |     - comparacao z-score em janela rolling
    |     - sinaliza features de jogadores suspeitas antes do treinamento
```

## Invariantes criticas

| ID | Arquivo / Linha | Invariante |
|----|-----------------|-----------|
| `DS-12` | `data_sources/demo_format_adapter.py` | `MIN_DEMO_SIZE = 10 MB` floor de aceitacao de ingestao. `dem_validator.py` e um pre-screening de formato deliberadamente mais permissivo (100 KB -- 800 MB). |
| `P-VEC-02` / `P3-A` | `vectorizer.py` upstream | Clamp de NaN / Inf + > 5 % por batch -> `DataQualityError`. A validacao aqui garante que o gate upstream nao pode ser contornado. |
| `F-0019` (fechado 2026-08-21) | `sanity.py` `LIMITS` | Tanto `headshot_pct` quanto `kast` tem bandas em escala de ratio (0.0 -- 1.0) e ambos sao colunas auto-reparaveis em `_RATIO_SELF_HEAL_COLUMNS` (`P-SAN-01`). Valores acima de 1.0 sao divididos por 100 e clamped. |

## Convencoes

- **Falhe ruidosamente.** Os validadores levantam excecoes tipadas (`DEMValidationError`) ou `ValueError` com uma mensagem explicita -- nunca degradam silenciosamente.
- **Funcoes puras sempre que possivel.** Os validadores recebem inputs e retornam um veredito; eles nao escrevem no disco nem no banco de dados.
- **Logging estruturado.** `drift.py`, `sanity.py` e `schema.py` logam via `get_logger("cs2analyzer.<modulo>")`; `dem_validator.py` nao faz logging e retorna um veredito explicito `(is_valid, game_version, error_message)`.
- **Checks baratos primeiro.** Ordene os asserts do mais barato (size, magic bytes) ao mais caro (testes estatisticos) para que um arquivo quebrado falhe antes que os caminhos caros rodem.

## Adicionando um novo validador

1. Coloque-o neste pacote, um arquivo por preocupacao.
2. Defina uma classe de excecao tipada (`<Domain>ValidationError`) e use-a para todos os modos de falha -- nunca levante `RuntimeError`.
3. Adicione uma entrada na tabela de inventario acima com um proposito de uma linha.
4. Conecte-o a pipeline na fronteira **mais cedo** possivel onde os dados ruins podem chegar.
5. Forneca um teste unitario em `Programma_CS2_RENAN/tests/` (ex. `test_dem_validator.py`, `test_drift_and_heuristics.py`).

## Nao faca

- Nao coaja silenciosamente input malformado para valores "best-effort" sem registrar o desvio em `DataLineage` / `DataQualityMetric`. Coercao silenciosa viola Regra 1.
- Nao duplique `MIN_DEMO_SIZE`. A constante mora em `data_sources/demo_format_adapter.py`; todo o resto importa de la.
- Nao use validadores para checks especulativos em tempo de inferencia ("se o dado parecer estranho, pula"). Validadores decidem; o codigo downstream respeita a decisao.

## Relacionados

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Modulo de qualidade de dados (lado do training): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metrics: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Pacote pai: `Programma_CS2_RENAN/backend/processing/README.md`

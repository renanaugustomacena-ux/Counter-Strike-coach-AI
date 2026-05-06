# `backend/processing/validation/` — Gates de integridade de dados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 1 (Correctness), Rule 4 (Data Persistence)
> **Skill:** `/correctness-check`, `/data-lifecycle-review`

## Propósito

Este pacote é dono dos gates de validação que protegem todo consumidor downstream (training, inference, dashboard) contra entradas malformadas. Os arquivos aqui rodam nas fronteiras de ingestão, nas fronteiras de batch de treinamento e na inicialização. São o lugar onde dados corrompidos ou inseguros devem falhar de forma ruidosa e cedo — degradação silenciosa é uma linha vermelha do projeto (Rule 1).

## Inventário de arquivos

| Arquivo | Módulo | Propósito | Exports principais |
|------|--------|---------|-------------|
| `__init__.py` | — | Re-exports públicos do pacote de validação. | — |
| `dem_validator.py` | DemValidator | Valida a estrutura do arquivo `.dem` antes do parse. Impõe `MIN_DEMO_SIZE = 10 MB` (invariante `DS-12`), checa magic bytes, rejeita arquivos truncados. | `DemValidator`, `validate_dem_file()` |
| `drift.py` | Detecção de drift | Detecção estatística de drift entre as distribuições de features dos jogadores. Compara a distribuição rolling das últimas N partidas contra o baseline histórico; sinaliza quando o p-value do teste KS cruza um threshold. | `detect_feature_drift()`, `DriftReport` |
| `sanity.py` | Sanity checks | Asserts leves em runtime sobre o estado em nível de tick (jogadores vivos têm HP > 0, jogadores mortos têm HP = 0, valor de equipamento é não-negativo, ...). | `assert_tick_sanity()` |
| `schema.py` | Schema | Validadores de JSON schema para ingestão a partir de fontes de torneio. | `TOURNAMENT_JSON_SCHEMA`, `validate_tournament_json()` |

## Onde cada validador roda

```
arquivo .dem cai na pasta de ingest
    +-- DemValidator.validate_dem_file()           [dem_validator.py]
    |     - rejeita arquivos < MIN_DEMO_SIZE
    |     - rejeita arquivos com magic bytes inválidos
    |     - rejeita arquivos truncados
    |
    +-- pipeline faz parse da demo (demoparser2)
    |
    +-- por tick: assert_tick_sanity()              [sanity.py]
    |     - bounds de HP / armor / equipment_value
    |     - coerência alive vs dead
    |
    +-- linhas de tick persistidas no SQLite por partida

feed JSON de torneio
    +-- validate_tournament_json(payload)          [schema.py]
    |     - chaves obrigatórias presentes
    |     - chaves por mapa presentes
    |     - coerção segura para int (DS-04)

fronteira de batch de treinamento
    +-- detect_feature_drift(...)                  [drift.py]
    |     - teste KS sobre distribuição rolling
    |     - sinaliza features de jogadores suspeitas antes do treinamento
```

## Invariantes críticas

| ID | Arquivo / linha | Invariante |
|----|-------------|-----------|
| `DS-12` | `dem_validator.py` | `MIN_DEMO_SIZE = 10 MB`. Arquivos menores são rejeitados (demos reais de CS2 normalmente têm ≥ 50 MB). |
| `DS-04` | `schema.py` | `_safe_int()` coage valores JSON não-numéricos para `0` em vez de levantar exceção. |
| `P-VEC-02` / `P3-A` | `vectorizer.py` upstream | Clamp de NaN / Inf + > 5 % por batch → `DataQualityError`. A validação aqui garante que o gate upstream não pode ser contornado. |

## Convenções

- **Falhe ruidosamente.** Os validadores levantam exceções tipadas (`DemValidationError`, `SchemaValidationError`, `DataQualityError`) — nunca retornam `None` silencioso.
- **Funções puras sempre que possível.** Os validadores recebem inputs e retornam um veredito; eles não escrevem no disco nem no banco de dados.
- **Logging estruturado.** Todas as falhas logam via `get_logger("cs2analyzer.validation.<module>")` com um código de erro estável para que dashboards consigam agregar.
- **Checks baratos primeiro.** Ordene os asserts do mais barato (size, magic bytes) ao mais caro (testes estatísticos) para que um arquivo quebrado falhe antes que os caminhos caros rodem.

## Adicionando um novo validador

1. Coloque-o neste pacote, um arquivo por preocupação.
2. Defina uma classe de exceção tipada (`<Domain>ValidationError`) e use-a para todos os modos de falha — nunca levante `RuntimeError`.
3. Adicione uma entrada na tabela de inventário acima com um propósito de uma linha.
4. Conecte-o à pipeline na fronteira **mais cedo** possível onde os dados ruins podem chegar.
5. Forneça um teste unitário em `Programma_CS2_RENAN/tests/test_<domain>_validation.py`.

## Não faça

- Não coage silenciosamente input malformado para valores "best-effort" sem registrar o desvio em `DataLineage` / `DataQualityMetric`. Coerção silenciosa viola a Rule 1.
- Não duplique `MIN_DEMO_SIZE`. A constante mora aqui; todo o resto importa daqui.
- Não use validadores para checks especulativos em tempo de inferência ("se o dado parecer estranho, pula"). Validadores decidem; o código downstream respeita a decisão.

## Relacionados

- Demo parser: `Programma_CS2_RENAN/backend/data_sources/demo_parser.py`
- Feature engineering: `Programma_CS2_RENAN/backend/processing/feature_engineering/README.md`
- Módulo de qualidade de dados (lado do training): `Programma_CS2_RENAN/backend/nn/data_quality.py`
- Lineage & metrics: `backend/storage/db_models.DataLineage`, `DataQualityMetric`
- Pacote pai: `Programma_CS2_RENAN/backend/processing/README.md`

# SECURITY/policies/

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Regole policy-as-code consumate da `tools/policy_runner.py`.

## Layout dei file

Ogni file `*.yaml` in questa directory definisce una regola. Il policy runner scopre tutti i file `*.yaml`
(eccetto questo `README.md`) e valuta ognuno indipendentemente.

## Schema della regola

```yaml
id: POL-XXX-NN          # ID stabile, referenziato da waivers.yaml e CONTROL_CATALOG.md
description: |
  Descrizione human-readable di cosa la regola impone e perché.
severity: error | warn | info
applies_to:             # pattern glob dei file da scansionare
  - "**/*.py"
excludes:               # pattern glob da saltare
  - ".venv/**"
  - "external_analysis/**"
kind: line_regex        # uno di: line_regex | text_regex | yaml_walker | file_compare | ast_walker
config:                 # blocco specifico per kind (vedere sotto)
  ...
```

## Kind

### `line_regex`

Scansiona ogni riga di ogni file che matcha `applies_to` contro `config.pattern`. Riporta ogni match
a meno che non sia soppresso da un commento inline `# noqa: <id>` sulla stessa riga (o sulla riga sopra).

```yaml
kind: line_regex
config:
  pattern: '\bsubprocess\b\s*\([^)]*shell\s*=\s*True'
  inline_waiver: '# SEC: justified'
```

### `text_regex`

Come `line_regex` ma matcha contro l'intero contenuto del file (multiline-aware).

### `yaml_walker`

Parsa ogni file che matcha `applies_to` come YAML e applica una query in stile JSONPath.

```yaml
kind: yaml_walker
config:
  query: '.services.*.ports[*]'
  rule: must_not_match
  pattern: '^0\.0\.0\.0:'
  message: 'Service binds to all interfaces; use 127.0.0.1 or add a # SEC: bind-public waiver.'
```

### `file_compare`

Confronta due file / impostazioni. Usato per la coerenza cross-file (es. POL-COV-01).

```yaml
kind: file_compare
config:
  left:
    path: pyproject.toml
    extract: 'fail_under\s*=\s*(\d+)'
  right:
    path: .github/workflows/build.yml
    extract: '--cov-fail-under=(\d+)'
  rule: must_be_equal
```

### `ast_walker`

(Phase 2) Cammina sull'AST Python. Richiederà `libcst==1.5.0` come dipendenza di dev.

## Aggiungere una nuova regola

1. Creare `SECURITY/policies/POL-XXX-NN.yaml` con lo schema sopra.
2. Aggiungere una riga a `SECURITY/CONTROL_CATALOG.md` sotto il pilastro pertinente.
3. Eseguire `python tools/policy_runner.py --rule POL-XXX-NN` localmente per confermare che funziona.
4. CODEOWNERS effettuerà la review.

## Modi

- **Default (warn-mode)**: `python tools/policy_runner.py` — esce 0 anche in presenza di violazioni; stampa il report.
- **Strict (block)**: `python tools/policy_runner.py --strict` — esce 1 su qualsiasi violazione non waiverata.
- **Singola regola**: `python tools/policy_runner.py --rule POL-DEPS-01` — esegue solo la regola specificata.

## Integrazione con l'audit log

Ogni violazione osservata (a prescindere da strict / warn) emette un evento di audit log
`policy.violation.observed` con il path del file, la riga, l'ID della regola e la severità. La scadenza di un waiver emette
`policy.waiver.expired`.

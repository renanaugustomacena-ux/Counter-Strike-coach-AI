# SECURITY/policies/

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Regras de policy-as-code consumidas por `tools/policy_runner.py`.

## Layout dos arquivos

Cada arquivo `*.yaml` neste diretório define uma regra. O policy runner descobre todos os arquivos `*.yaml`
(exceto este `README.md`) e avalia cada um de forma independente.

## Schema da regra

```yaml
id: POL-XXX-NN          # ID estável, referenciado em waivers.yaml e CONTROL_CATALOG.md
description: |
  Descrição legível do que a regra impõe e por quê.
severity: error | warn | info
applies_to:             # padrões glob de arquivos a escanear
  - "**/*.py"
excludes:               # padrões glob a ignorar
  - ".venv/**"
  - "external_analysis/**"
kind: line_regex        # um de: line_regex | text_regex | yaml_walker | file_compare | ast_walker
config:                 # bloco específico do kind (veja abaixo)
  ...
```

## Kinds

### `line_regex`

Escaneia cada linha de cada arquivo que casa com `applies_to` contra `config.pattern`. Reporta qualquer match
a menos que suprimido por um comentário inline `# noqa: <id>` na mesma linha (ou na linha acima).

```yaml
kind: line_regex
config:
  pattern: '\bsubprocess\b\s*\([^)]*shell\s*=\s*True'
  inline_waiver: '# SEC: justified'
```

### `text_regex`

Como `line_regex`, mas casa contra o conteúdo completo do arquivo (multiline-aware).

### `yaml_walker`

Faz parse de cada arquivo que casa com `applies_to` como YAML e aplica uma query no estilo JSONPath.

```yaml
kind: yaml_walker
config:
  query: '.services.*.ports[*]'
  rule: must_not_match
  pattern: '^0\.0\.0\.0:'
  message: 'Service binds to all interfaces; use 127.0.0.1 or add a # SEC: bind-public waiver.'
```

### `file_compare`

Compara dois arquivos / configurações. Usado para consistência cross-file (por exemplo, POL-COV-01).

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

(Fase 2) Percorre a AST do Python. Vai exigir `libcst==1.5.0` como dependência de dev.

## Adicionando uma nova regra

1. Crie `SECURITY/policies/POL-XXX-NN.yaml` com o schema acima.
2. Adicione uma linha em `SECURITY/CONTROL_CATALOG.md` sob o pilar relevante.
3. Rode `python tools/policy_runner.py --rule POL-XXX-NN` localmente para confirmar que funciona.
4. CODEOWNERS fará a revisão.

## Modos

- **Padrão (warn-mode)**: `python tools/policy_runner.py` — sai com 0 mesmo havendo violações; imprime o relatório.
- **Estrito (block)**: `python tools/policy_runner.py --strict` — sai com 1 em qualquer violação sem waiver.
- **Regra única**: `python tools/policy_runner.py --rule POL-DEPS-01` — roda apenas a regra especificada.

## Integração com audit log

Toda violação observada (independente de strict / warn) emite um evento de audit log
`policy.violation.observed` com o caminho do arquivo, a linha, o ID da regra e a severidade. A expiração de waiver emite
`policy.waiver.expired`.

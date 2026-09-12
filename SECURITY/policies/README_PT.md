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
mapping:                # referência cruzada opcional para padrões (IDs CWE / ASVS / SSDF)
  cwe: ['CWE-1327']
  ssdf: ['PO.5']
```

## Kinds

### `line_regex`

Escaneia cada linha de cada arquivo que casa com `applies_to` contra cada entrada em `config.patterns`.
Reporta qualquer match a menos que a linha contenha uma das strings `inline_waivers` configuradas
pela regra (ex. `# noqa: POL-NET-01` ou uma tag `# SEC: <reason>`).

```yaml
kind: line_regex
config:
  patterns:
    - id: shell_true
      pattern: '\bsubprocess\b\s*\([^)]*shell\s*=\s*True'
      message: 'shell=True is forbidden; use an argv list.'
  inline_waivers:
    - '# SEC: justified'
    - '# noqa: POL-CODE-01'
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
  message: 'Service binds to all interfaces; use 127.0.0.1.'
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

(Fase 2 — ainda não implementado; o runner atualmente emite um aviso info-level para regras
`ast_walker`.) Percorre a AST do Python. Vai exigir `libcst` como dependência de dev.

## Adicionando uma nova regra

1. Crie `SECURITY/policies/POL-XXX-NN.yaml` com o schema acima.
2. Adicione uma linha em `SECURITY/CONTROL_CATALOG.md` sob o pilar relevante.
3. Rode `python tools/policy_runner.py --rule POL-XXX-NN` localmente para confirmar que funciona.
4. CODEOWNERS fará a revisão.

## Modos

- **Padrão (warn-mode)**: `python tools/policy_runner.py` — sai com 0 mesmo havendo violações; imprime o relatório.
- **Estrito (block)**: `python tools/policy_runner.py --strict` — sai com 1 em qualquer violação
  error-severity sem waiver ou waiver expirado.
- **Regra única**: `python tools/policy_runner.py --rule POL-DEPS-01` — roda apenas a regra especificada
  (repetível).
- **JSON**: `python tools/policy_runner.py --json` — saída machine-readable no lugar do relatório human.

## Waivers

As exceções a nível de repositório ficam em `SECURITY/waivers.yaml`; cada entrada tem prazo
(`expires:`) e o runner reporta waivers expirados (que falham no `--strict`). As exceções por-linha
usam as strings `inline_waivers` da regra.

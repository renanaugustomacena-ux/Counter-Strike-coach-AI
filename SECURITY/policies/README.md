# SECURITY/policies/

Policy-as-code rules consumed by `tools/policy_runner.py`.

## File layout

Each `*.yaml` file in this directory defines one rule. The policy runner discovers all `*.yaml` files
(except this `README.md`) and evaluates each independently.

## Rule schema

```yaml
id: POL-XXX-NN          # stable ID, referenced from waivers.yaml and CONTROL_CATALOG.md
description: |
  Human-readable description of what the rule enforces and why.
severity: error | warn | info
applies_to:             # glob patterns of files to scan
  - "**/*.py"
excludes:               # glob patterns to skip
  - ".venv/**"
  - "external_analysis/**"
kind: line_regex        # one of: line_regex | text_regex | yaml_walker | file_compare | ast_walker
config:                 # kind-specific block (see below)
  ...
```

## Kinds

### `line_regex`

Scans each line of every file matching `applies_to` against `config.pattern`. Reports any match
unless suppressed by an inline `# noqa: <id>` comment on the same line (or the line above).

```yaml
kind: line_regex
config:
  pattern: '\bsubprocess\b\s*\([^)]*shell\s*=\s*True'
  inline_waiver: '# SEC: justified'
```

### `text_regex`

Like `line_regex` but matches against the full file content (multiline-aware).

### `yaml_walker`

Parses each file matching `applies_to` as YAML and applies a JSONPath-style query.

```yaml
kind: yaml_walker
config:
  query: '.services.*.ports[*]'
  rule: must_not_match
  pattern: '^0\.0\.0\.0:'
  message: 'Service binds to all interfaces; use 127.0.0.1 or add a # SEC: bind-public waiver.'
```

### `file_compare`

Compares two files / settings. Used for cross-file consistency (e.g., POL-COV-01).

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

(Phase 2) Walks the Python AST. Will require `libcst==1.5.0` as a dev dep.

## Adding a new rule

1. Create `SECURITY/policies/POL-XXX-NN.yaml` with the schema above.
2. Add a row to `SECURITY/CONTROL_CATALOG.md` under the relevant pillar.
3. Run `python tools/policy_runner.py --rule POL-XXX-NN` locally to confirm it works.
4. CODEOWNERS will review.

## Modes

- **Default (warn-mode)**: `python tools/policy_runner.py` — exits 0 even on violations; prints report.
- **Strict (block)**: `python tools/policy_runner.py --strict` — exits 1 on any unwaived violation.
- **Single rule**: `python tools/policy_runner.py --rule POL-DEPS-01` — runs only the specified rule.

## Audit-log integration

Every violation observed (regardless of strict / warn) emits an audit-log event
`policy.violation.observed` with the file path, line, rule ID, and severity. Waiver expiry emits
`policy.waiver.expired`.

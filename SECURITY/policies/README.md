# SECURITY/policies/

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
mapping:                # optional cross-reference to standards (CWE / ASVS / SSDF IDs)
  cwe: ['CWE-1327']
  ssdf: ['PO.5']
```

## Kinds

### `line_regex`

Scans each line of every file matching `applies_to` against each entry in `config.patterns`.
Reports any match unless the line contains one of the rule's configured `inline_waivers` strings
(e.g. `# noqa: POL-NET-01` or a `# SEC: <reason>` tag).

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

## Waivers

Repo-wide exceptions live in `SECURITY/waivers.yaml`; every entry is time-bound (`expires:`) and
the runner reports expired waivers. Per-line exceptions use the rule's `inline_waivers` strings.

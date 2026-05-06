# `reports/` — Artefatos gerados de auditoria e avaliação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Repositório de artefatos gerados (read-only por convenção)

## O que vive aqui

Este diretório coleta os relatórios JSON gerados automaticamente pelas ferramentas de avaliação, auditoria e diagnóstico do projeto. Os arquivos aqui são **saídas** da execução de scripts, não documentos-fonte — são mantidos sob controle de versão como evidência histórica.

```
reports/
├── audit/                                # Saídas JSON das auditorias Goliath
├── eval_<UTC-timestamp>.json             # Execuções do benchmark cs2_coach_bench
└── goliath_hospital_<timestamp>.json     # Execuções Goliath em modo hospital (recuperação de DB)
```

## Categorias de arquivo

| Padrão | Origem | Propósito |
|--------|--------|-----------|
| `eval_*.json` | `evals/cs2_coach_bench/run_eval.py` | Scoring do benchmark de coaching |
| `goliath_hospital_*.json` | `goliath.py audit --hospital` | Scan de integridade do banco |
| `audit/*.json` | `goliath.py audit` | Auditorias direcionadas de módulo |

## Convenções

- **Nomes de arquivo são timestampados** (`UTC` ou local) para que os relatórios nunca se sobrescrevam.
- **Relatórios são imutáveis.** Re-executar um script produz um novo arquivo — nunca edite no lugar.
- **Relatórios antigos são preservados** até que a pressão de armazenamento justifique poda. Diferenciar entre relatórios consecutivos revela regressões.
- **Sem PII.** Relatórios contêm nomes de demos e aliases de jogadores, mas nunca credenciais cruas, tokens Steam ou chaves de API HLTV.

## Relacionados

- Harness do benchmark: `evals/README.md`
- Operador Goliath: `goliath.py` na raiz do repo
- Saída do validador (stream separado): consulte `tools/headless_validator.py` (escreve em stdout, não aqui)

## Limpeza

Quando o diretório passa de algumas centenas de arquivos, pode por mês com:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
find reports -name "goliath_hospital_*.json" -mtime +60 -delete
```

Ajuste os limiares de acordo com sua preferência de retenção. Não existe limpeza automática.

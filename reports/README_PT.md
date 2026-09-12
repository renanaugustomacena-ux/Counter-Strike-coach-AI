# `reports/` — Artefatos gerados de auditoria e avaliacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Repositorio de artefatos gerados (read-only por convencao)

## O que vive aqui

Este diretorio coleta os relatorios JSON gerados automaticamente pelas ferramentas de avaliacao, auditoria e diagnostico do projeto. Os arquivos aqui sao **saidas** da execucao de scripts, nao documentos-fonte. O diretorio e distribuido vazio (apenas os READMEs sao rastreados — `reports/*` e gitignored); os relatorios se acumulam localmente conforme voce executa as ferramentas.

```
reports/
├── assets/                               # Graficos PNG do MatchVisualizer (nomes fixos, sobrescritos)
├── audit/                                # Saidas JSON do audit_scanner.py (via --output)
├── coach_answer_eval_<UTC-timestamp>.json  # Execucoes de tools/coach_answer_eval.py (groundedness)
├── eval_<UTC-timestamp>.json             # Execucoes de tools/eval_harness.py (coaching-eval)
└── hltv_seed_<timestamp>/                # Relatorios de execucao seed_hltv_top_n.py (pending_vision.json, ...)
```

## Categorias de arquivo

| Padrao | Origem | Proposito |
|--------|--------|-----------|
| `eval_*.json` | `tools/eval_harness.py` | Execucoes de avaliacao de coaching (com timestamp) |
| `coach_answer_eval_*.json` | `tools/coach_answer_eval.py` | Execucoes eval groundedness de respostas LLM (com timestamp) |
| `audit/*.json` | `tools/audit_scanner.py --output reports/audit/<nome>.json` | Auditorias direcionadas de subsistemas |
| `hltv_seed_*/` | `tools/seed_hltv_top_n.py` (consumido por `seed_hltv_apply_vision.py`) | Artefatos de execucoes de seeding HLTV |
| `assets/*.png` | `Programma_CS2_RENAN/reporting/visualizer.py` (`MatchVisualizer`, dir padrao relativo a cwd) | Graficos de heatmap / analise de rounds |

(O benchmark `cs2_coach_bench` grava suas proprias respostas JSONL em `evals/cs2_coach_bench/reports/`, nao aqui.)

## Convencoes

- **Nomes de arquivo de relatorios JSON sao com timestamp** (`UTC` ou local) para que os relatorios nunca se sobrescrevam. Excecao: PNGs em `assets/` usam nomes fixos por mapa/grafico e sao sobrescritos na re-geracao.
- **Relatorios sao imutaveis.** Re-executar um script produz um novo arquivo — nunca edite no lugar.
- **Relatorios sao apenas locais.** `reports/*` e gitignored; preserve os antigos ate que a pressao de armazenamento justifique poda. Diferenciar entre relatorios consecutivos revela regressoes.
- **Sem PII.** Relatorios contem nomes de demos e aliases de jogadores, mas nunca credenciais cruas, tokens Steam ou chaves de API HLTV.

## Relacionados

- Harness do benchmark: `evals/README.md`
- Operador Goliath: `goliath.py` na raiz do repo
- Saida do validador (stream separado): consulte `tools/headless_validator.py` (escreve em stdout, nao aqui)

## Limpeza

Quando o diretorio passa de algumas centenas de arquivos, pode por idade com:

```bash
find reports -name "eval_*.json" -mtime +90 -delete
```

Ajuste os limiares de acordo com sua preferencia de retencao. Nao existe limpeza automatica.

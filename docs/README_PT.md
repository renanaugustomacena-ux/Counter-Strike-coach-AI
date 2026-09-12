# Macena CS2 Analyzer — Indice de Documentacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Referencias Principais (raiz do projeto)

| Documento | Finalidade |
|-----------|------------|
| **[REFERENCE.md](../REFERENCE.md)** | Arquitetura, contrato dimensional, constantes, skills, testes, configuracoes |
| **[TASKS.md](../TASKS.md)** | Backlog, erros, status de execucao |
| **[CHANGELOG.md](../CHANGELOG.md)** | Historico de alteracoes |

## Estrutura do Diretorio

```
docs/
├── QUICKSTART.md                   # Guia rapido de 5 minutos
├── README.md / _IT.md / _PT.md     # Este indice (3 idiomas)
│
├── OPEN_ISSUES.md                  # Problemas abertos consolidados (sweep documental 2026-08-21)
├── RE_INGESTION_GUIDE.md           # Ops: pipeline completa de re-ingestao e treinamento
├── concurrency_policy.md           # Ops: politica de lock DB para migracoes de longa duracao
├── rollback_procedure.md           # Ops: rollback DB para a baseline 2026-05-03
├── strategy_taxonomy.md            # Taxonomia coachingexperience.strategy_label
│
├── DIAGNOSIS_2026-05.md            # Diagnostico historico (estado superado por docs/audit)
├── SESSION_HANDOFF.md              # Convencoes operacionais (estado historico removido)
├── jepa_training_tuning_observations_2026-05-06.md   # Escada retrain R8 + registro probe B5
├── rap_training_known_issue_2026-05-05.md            # Resolvido: justificativa para o patch LTC ncps live
├── restoration_baseline_2026-05-03.json              # Contagens de linhas baseline para rollback
├── d3_rederive_report_2026-07-17.json                # Relatorio re-derivacao D3 tick-rate (shards)
│
├── audit/                          # Arquivo Audit Nuke-Proof (encerrado 2026-08-14)
│   ├── FINAL_REPORT.md             # Encerramento da campanha (comece aqui)
│   ├── FINDINGS.md                 # Registro de 44 findings (13 diferidos → OPEN_ISSUES.md)
│   └── ...                         # WAVES, CONTRACTS, dossies, sweeps, ledger
│
├── books/                          # Livros de visao (visao e arquitetura do projeto)
│   ├── Book-Coach-1A .md/.pdf      # Nucleo neural: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B .md/.pdf      # RAP Coach, fontes de dados (demo, HLTV, Steam)
│   ├── Book-Coach-2  .md/.pdf      # Servicos, motores de analise, COPER, banco de dados
│   ├── Book-Coach-3  .md/.pdf      # Logica do programa, UI Qt, ingestao, tools, build
│   │                               # (cada um com variantes -en / -pt)
│   ├── analogy-book .md/.pdf       # Companion de analogias (com variantes -en / -pt)
│   ├── codebase-understanding/     # Walkthrough do codebase em 9 capitulos (01-09)
│   ├── REFACTOR_PLAN.md
│   └── TRANSLATION_GLOSSARY.md
│
├── doctrine/                       # Doutrina arquitetural de IA (derivada do codigo)
│   ├── DOCTRINE.md                 # Invariantes, contratos e justificativas de design
│   └── notes/                      # Notas de leitura por cluster + READING-MANIFEST.md
│
├── guides/                         # Documentacao voltada ao usuario
│   ├── USER_GUIDE.md               # Guia completo do usuario (Ingles)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   ├── USER_GUIDE_PT.md            # Guia do usuario (Portugues)
│   └── PROJETO_EXPLICADO_PT.md     # Visao geral do projeto em Portugues (para devs de outros stacks)
│
├── research/                       # Catalogo da biblioteca de pesquisa + design research
│   ├── INDEX.md                    # Indice bibliografico; os PDFs em si sao
│   │                               # git-ignorados e nao estao presentes em um checkout limpo
│   └── cs_platforms.md / github_gems.md / global_startups.md   # Dossies de redesign UI/UX
│
├── superpowers/                    # Planos de implementacao e specs de design (workflows de skill)
│   ├── plans/
│   └── specs/
│
├── ux-audit/                       # Auditoria visual UX + renders de tela
│   ├── UX_VISUAL_AUDIT.md
│   ├── renders/                    # Screenshots CS16 / CS2 / CSGO
│   └── renders-atlas/              # Screenshots CS16 / CS2 / CSGO (pass design-atlas)
│
└── tooling/                        # Utilitarios para geracao de PDF
    ├── generate_zh_pdfs.py         # Gerador Mermaid → SVG + PDF tema escuro
    ├── md2pdf.mjs                  # Markdown -> PDF (Node.js)
    └── package.json / package-lock.json
```

## Ordem de Leitura

1. **[../REFERENCE.md](../REFERENCE.md)** — Arquitetura, invariantes, referencia tecnica
2. **[doctrine/DOCTRINE.md](doctrine/DOCTRINE.md)** — Doutrina arquitetural de IA (invariantes e contratos derivados do codigo)
3. **[QUICKSTART.md](QUICKSTART.md)** — Rode o app em 5 minutos
4. **[guides/USER_GUIDE_PT.md](guides/USER_GUIDE_PT.md)** — Walkthrough completo para o usuario
5. **[books/](books/)** — Livros de visao (1A → 1B → 2 → 3) para a visao completa do produto
6. **[research/INDEX.md](research/INDEX.md)** — Bibliografia de papers de pesquisa

## Referencia Rapida

| Necessidade | Ir para |
|-------------|---------|
| O que e este projeto? | `../README.md` |
| Arquitetura e invariantes | `../REFERENCE.md` |
| Backlog e plano de execucao | `../TASKS.md` |
| Vetor de features (25-dim) | `../REFERENCE.md` §2 |
| Arquitetura de storage / schema | `../REFERENCE.md` §5 |
| Pipeline de re-ingestao / treinamento | `RE_INGESTION_GUIDE.md` |
| Solucao de problemas | `guides/USER_GUIDE_PT.md` — secao Solucao de Problemas |
| Ajuda in-app | `../Programma_CS2_RENAN/data/docs/troubleshooting.md` |

## Notas

- Arquivos com datas no nome (`*_2026-*`) sao snapshots historicos de runs anteriores de
  restauracao/treinamento — descrevem o estado naquela data, nao o estado atual.
- Os Livros de Visao (books/) descrevem a visao do produto e foram realinhados com o codebase
  em 2026-08-17. A Doutrina (doctrine/) e a autoridade derivada do codigo para arquitetura e
  invariantes; quando os dois discordam, a doutrina reflete a implementacao atual.
- Toda a documentacao esta em formato Markdown. PDFs sao gerados com as ferramentas em `tooling/`.

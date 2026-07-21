# Macena CS2 Analyzer — Indice de Documentacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Referencias Principais (raiz do projeto)

| Documento | Finalidade |
|-----------|------------|
| **[REFERENCE.md](../REFERENCE.md)** | Arquitetura, contrato dimensional, constantes, skills, testes, configuracoes |
| **[AUDIT.md](../AUDIT.md)** | Findings, diagnosticos, saude da build |
| **[TASKS.md](../TASKS.md)** | Backlog, erros, status de execucao |

## Estrutura do Diretorio

```
docs/
├── QUICKSTART.md                   # Guia rapido de 5 minutos
├── README.md / _IT.md / _PT.md    # Este indice (3 idiomas)
│
├── books/                          # Livros de visao (visao e arquitetura do projeto)
│   ├── Book-Coach-1A.md / .pdf     # Nucleo neural: JEPA, VL-JEPA, AdvancedCoachNN
│   ├── Book-Coach-1B.md / .pdf     # RAP Coach, fontes de dados (demo, HLTV, Steam)
│   ├── Book-Coach-2.md / .pdf      # Servicos, motores de analise, COPER, banco de dados
│   └── Book-Coach-3.md / .pdf      # Logica do programa, UI Qt, ingestao, tools, build
│
├── guides/                         # Documentacao voltada ao usuario
│   ├── USER_GUIDE.md               # Guia completo do usuario (Ingles)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuario (Portugues)
│
├── Studies/                        # 17 papers de pesquisa (fundacoes teoricas)
│   ├── README.md / _IT.md / _PT.md # Indice dos estudos
│   ├── Fondamenti-Epistemici.md    # Epistemologia e verdade
│   ├── Architettura-JEPA.md        # Arquitetura JEPA
│   └── ... (15 mais)               # Veja Studies/README.md
│
├── archive/                        # Documentos superados (mantidos para referencia)
│   ├── AI_ARCHITECTURE_ANALYSIS.md # Substituido pelo ENGINEERING_HANDOFF
│   ├── PROJECT_SURGERY_PLAN.md     # Substituido pelo ENGINEERING_HANDOFF
│   ├── PRODUCT_VIABILITY_ASSESSMENT.md
│   ├── INDUSTRY_STANDARDS_AUDIT.md
│   ├── logging-and-plan.md
│   ├── MISSION_RULES.md
│   ├── cybersecurity.md
│   ├── ERROR_CODES.md
│   ├── EXIT_CODES.md
│   └── prompt.md
│
└── tooling/                        # Utilitarios para geracao de PDF
    ├── generate_zh_pdfs.py         # Gerador de PDF em chines
    ├── md2pdf.mjs                  # Markdown -> PDF (Node.js)
    └── package.json                # Dependencias npm
```

## Ordem de Leitura

1. **[../REFERENCE.md](../REFERENCE.md)** — Arquitetura, invariantes, referencia tecnica
2. **[QUICKSTART.md](QUICKSTART.md)** — Rode o app em 5 minutos
3. **[guides/USER_GUIDE_PT.md](guides/USER_GUIDE_PT.md)** — Walkthrough completo para o usuario
4. **[books/](books/)** — Livros de visao (1A -> 1B -> 2 -> 3) para a visao completa do produto
5. **[Studies/](Studies/)** — Papers de pesquisa aprofundados sobre fundacoes teoricas

## Referencia Rapida

| Necessidade | Ir para |
|-------------|---------|
| O que e este projeto? | `../README.md` |
| Arquitetura e invariantes | `../REFERENCE.md` |
| Findings e diagnosticos atuais | `../AUDIT.md` |
| Backlog e plano de execucao | `../TASKS.md` |
| Vetor de features (25-dim) | `../REFERENCE.md` §3 |
| Schema do banco de dados | `../REFERENCE.md` §4 |
| Solucao de problemas | `guides/USER_GUIDE_PT.md` — secao Solucao de Problemas |
| Ajuda ao usuario | `data/docs/troubleshooting.md` |

## Notas

- O diretorio `archive/` contem documentos superados preservados para referencia historica.
- Os Livros de Visao (books/) descrevem a visao aspiracional do produto. Serao atualizados para alinhar com o codebase quando o programa estiver estavel.
- Toda a documentacao esta em formato Markdown. PDFs sao gerados com as ferramentas em `tooling/`.
- O arquivo `CLAUDE.md` na raiz do projeto contem as diretivas de engenharia e regras de desenvolvimento.

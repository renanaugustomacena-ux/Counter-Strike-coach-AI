# Macena CS2 Analyzer — Indice de Documentacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

## Documento Principal

**[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Referencia tecnica unificada para todo o projeto. Contem: arquitetura do sistema, auditoria do estado atual, findings abertos, plano de execucao (cirurgias por fases), roadmap do produto, guia de solucao de problemas e todos os apendices (codigos de erro, variaveis de ambiente, spec do vetor de features, schema do banco de dados). **Comece por aqui.**

## Estrutura do Diretorio

```
docs/
├── ENGINEERING_HANDOFF.md          # Referencia tecnica unificada (comece aqui)
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

1. **[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Referencia tecnica, plano de execucao, estado atual
2. **[QUICKSTART.md](QUICKSTART.md)** — Rode o app em 5 minutos
3. **[guides/USER_GUIDE_PT.md](guides/USER_GUIDE_PT.md)** — Walkthrough completo para o usuario
4. **[books/](books/)** — Livros de visao (1A -> 1B -> 2 -> 3) para a visao completa do produto
5. **[Studies/](Studies/)** — Papers de pesquisa aprofundados sobre fundacoes teoricas

## Referencia Rapida

| Necessidade | Ir para |
|-------------|---------|
| O que e este projeto? | ENGINEERING_HANDOFF, Secao 1 |
| O que funciona hoje? | ENGINEERING_HANDOFF, Parte II |
| O que precisa ser corrigido? | ENGINEERING_HANDOFF, Parte III (Open Findings Registry) |
| Como corrigir (passos ordenados)? | ENGINEERING_HANDOFF, Parte IV (Execution Plan) |
| Codigos de erro | ENGINEERING_HANDOFF, Apendice A |
| Variaveis de ambiente | ENGINEERING_HANDOFF, Apendice C |
| Vetor de features (25-dim) | ENGINEERING_HANDOFF, Apendice E |
| Schema do banco de dados | ENGINEERING_HANDOFF, Apendice F |
| Solucao de problemas | ENGINEERING_HANDOFF, Apendice G |
| Roadmap do produto | ENGINEERING_HANDOFF, Parte V |

## Notas

- O diretorio `archive/` contem os documentos originais individuais que foram consolidados no ENGINEERING_HANDOFF.md. Sao preservados para referencia historica.
- Os Livros de Visao (books/) descrevem a visao aspiracional do produto. Serao atualizados para alinhar com o codebase quando o programa estiver estavel.
- Toda a documentacao esta em formato Markdown. PDFs sao gerados com as ferramentas em `tooling/`.
- O arquivo `CLAUDE.md` na raiz do projeto contem as diretivas de engenharia e regras de desenvolvimento.

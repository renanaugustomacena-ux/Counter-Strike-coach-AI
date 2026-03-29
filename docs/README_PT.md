# Macena CS2 Analyzer — Índice de Documentação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Documento Principal

**[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Referência técnica unificada para todo o projeto. Contém: arquitetura do sistema, auditoria do estado atual, problemas abertos, plano de execução (cirurgias por fases), roadmap do produto, guia de troubleshooting e todos os apêndices. **Comece por aqui.**

## Estrutura do Diretório

```
docs/
├── ENGINEERING_HANDOFF.md          # Referência técnica unificada (comece aqui)
├─�� QUICKSTART.md                   # Guia rápido (5 minutos)
├��─ README.md / _IT.md / _PT.md    # Este ��ndice (3 idiomas)
│
├── books/                          # Livros de visão (visão e arquitetura)
│   ├─�� Book-Coach-1A.md / .pdf     # Núcleo neural: JEPA, VL-JEPA
│   ├── Book-Coach-1B.md / .pdf     # RAP Coach, fontes de dados
│   ├── Book-Coach-2.md / .pdf      # Serviços, motores de análise, COPER, banco de dados
│   └── Book-Coach-3.md / .pdf      # Lógica do programa, Qt UI, ingestão, ferramentas
│
├── guides/                         # Documentação para o usuário
│   ├── USER_GUIDE.md               # Guia do usuário (English)
│   ├── USER_GUIDE_IT.md            # Guida utente (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuário completo (Português)
│
├── Studies/                        # 17 artigos de pesquisa (fundamentos teóricos)
│
├── archive/                        # Documentos anteriores (mantidos para referência)
│
└── tooling/                        # Utilitários para geração de PDF
```

## Ordem de Leitura

1. **[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** �� Referência técnica, plano de execução
2. **[QUICKSTART.md](QUICKSTART.md)** — Execute o app em 5 minutos
3. **[guides/USER_GUIDE_PT.md](guides/USER_GUIDE_PT.md)** — Guia completo do usuário
4. **[books/](books/)** — Livros de visão (1A -> 1B -> 2 -> 3)
5. **[Studies/](Studies/)** — Artigos de pesquisa aprofundados

## Referência Rápida

| Necessidade | Ir para |
|-------------|---------|
| O que é este projeto? | ENGINEERING_HANDOFF, Se��ão 1 |
| O que funciona hoje? | ENGINEERING_HANDOFF, Parte II |
| O que precisa de correção? | ENGINEERING_HANDOFF, Parte III |
| Como corrigir (passos ordenados)? | ENGINEERING_HANDOFF, Parte IV |
| Códigos de erro | ENGINEERING_HANDOFF, Apêndice A |
| Variáveis de ambiente | ENGINEERING_HANDOFF, Apêndice C |
| Vetor de features (25-dim) | ENGINEERING_HANDOFF, Apêndice E |
| Esquema do banco de dados | ENGINEERING_HANDOFF, Apêndice F |
| Troubleshooting | ENGINEERING_HANDOFF, Apêndice G |
| Roadmap do produto | ENGINEERING_HANDOFF, Parte V |

## Notas

- O diretório `archive/` contém os documentos originais consolidados no ENGINEERING_HANDOFF.md.
- Os Livros de Visão (books/) descrevem a visão aspiracional do produto. Serão atualizados quando o programa estiver estável.
- O arquivo `CLAUDE.md` na raiz do projeto contém as diretivas de engenharia.

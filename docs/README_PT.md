# Macena CS2 Analyzer — Índice de Documentação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autoridade:** Regra 8 (Governança de Documentação)

Este diretório contém a documentação completa para o projeto Macena CS2 Analyzer — uma aplicação sofisticada de análise tática e coaching com IA para Counter-Strike 2. A documentação está organizada em guias do usuário, especificações técnicas, artigos de pesquisa, livros de visão e scripts utilitários.

## Estrutura do Diretório

```
docs/
├── USER_GUIDE.md                       # Guia completo do usuário (Inglês)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia completo do usuário (Português)
├── QUICKSTART.md                       # Guia de início rápido
├── AI_ARCHITECTURE_ANALYSIS.md         # Análise aprofundada da arquitetura AI (Inglês)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Português)
├── ERROR_CODES.md                      # Referência de códigos de erro
├── EXIT_CODES.md                       # Referência de códigos de saída
├── INDUSTRY_STANDARDS_AUDIT.md         # Auditoria de conformidade com padrões da indústria
├── MISSION_RULES.md                    # Missão do projeto e regras
├── PRODUCT_VIABILITY_ASSESSMENT.md     # Análise de viabilidade do produto
├── PROJECT_SURGERY_PLAN.md             # Plano de cirurgia da arquitetura
├── cybersecurity.md                    # Avaliação de cibersegurança
├── prompt.md                           # Guia de prompts para assistentes de IA
├── logging-and-plan.md                 # Documentação da arquitetura de logging
├── Book-Coach-1A.md/pdf               # Livro visão parte 1A — Núcleo neural
├── Book-Coach-1B.md/pdf               # Livro visão parte 1B — RAP Coach e fontes de dados
├── Book-Coach-2.md/pdf                # Livro visão parte 2 — Serviços e infraestrutura
├── Book-Coach-3.md/pdf                # Livro visão parte 3 — Lógica do programa e UI
├── Studies/                            # 17 artigos de pesquisa (estudos aprofundados)
├── generate_zh_pdfs.py                 # Utilitário de geração de PDF em chinês
├── md2pdf.mjs                          # Conversor de Markdown para PDF (Node.js)
└── package.json                        # Ferramentas dos docs (markdownlint, etc.)
```

## Documentação do Usuário

### Guias do Usuário (3 Idiomas)

Os guias do usuário cobrem instalação, configuração, tutoriais de recursos, solução de problemas e boas práticas:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Guia completo do usuário (Inglês)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia completo do usuário (Português)
- **[QUICKSTART.md](QUICKSTART.md)** — Guia de início rápido para ficar operacional rapidamente

Cada guia cobre:
1. Instalação e configuração do ambiente
2. Primeira ingestão de demo (a regra 10/10)
3. Panorama da tela de coaching
4. Histórico de partidas e análise de desempenho
5. Configurações e ajustes
6. Solução de problemas comuns

## Documentação Técnica

### Especificações da Arquitetura

- **Análise da Arquitetura AI** — Estudo aprofundado do subsistema de IA
  - [Inglês](AI_ARCHITECTURE_ANALYSIS.md) | [Italiano](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Português](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Documentos de Referência

| Documento | Finalidade |
|-----------|------------|
| [ERROR_CODES.md](ERROR_CODES.md) | Todos os códigos de erro com causas e remediações |
| [EXIT_CODES.md](EXIT_CODES.md) | Códigos de saída para scripts e daemons |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Auditoria de conformidade com padrões da indústria |
| [MISSION_RULES.md](MISSION_RULES.md) | Declaração de missão do projeto e regras de desenvolvimento |
| [PRODUCT_VIABILITY_ASSESSMENT.md](PRODUCT_VIABILITY_ASSESSMENT.md) | Análise de viabilidade e mercado do produto |
| [PROJECT_SURGERY_PLAN.md](PROJECT_SURGERY_PLAN.md) | Plano de cirurgia e refatoração da arquitetura |
| [cybersecurity.md](cybersecurity.md) | Avaliação de cibersegurança e modelo de ameaças |
| [logging-and-plan.md](logging-and-plan.md) | Arquitetura de logging estruturado e roadmap |

### Integração com Assistentes de IA

- **[prompt.md](prompt.md)** — Prompts estruturados e fluxos de trabalho para desenvolvimento assistido por IA, revisão de código e manutenção do sistema

### Livros de Visão

Os "Coach Books" descrevem a visão completa do produto, a arquitetura técnica e a estratégia de negócios:

| Livro | Foco | Tamanho |
|-------|------|---------|
| [Book-Coach-1A](Book-Coach-1A.md) | Núcleo neural: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory | 1.315 linhas |
| [Book-Coach-1B](Book-Coach-1B.md) | RAP Coach (7 componentes), fontes de dados (demo, HLTV, Steam, FACEIT, FAISS) | 1.176 linhas |
| [Book-Coach-2](Book-Coach-2.md) | Serviços, 10 motores de análise, knowledge/RAG/COPER, banco de dados, pipeline de treinamento | 2.492 linhas |
| [Book-Coach-3](Book-Coach-3.md) | Lógica completa do programa, Qt UI (13 telas), ingestão, ferramentas, testes, build | 3.143 linhas |

Disponíveis em formato Markdown e PDF.

## Pesquisa e Estudos Aprofundados

### Diretório Studies

O diretório **[Studies/](Studies/)** contém 17 artigos de pesquisa técnica aprofundada cobrindo os fundamentos teóricos e detalhes de implementação:

- **Epistemologia e Teoria dos Jogos:** Redes bayesianas de crença, jogo adversarial racional, estimativa de probabilidade de morte
- **Arquitetura de Coaching:** Design do RAP Coach, modo COPER (Context + Observation + Pro Reference + Experience + Reasoning)
- **Inteligência Espacial:** Tratamento de Z-cutoff, mapas multi-nível (Nuke, Vertigo), análise de engagement range
- **Sistemas de Momentum:** Modelagem de momentum temporal, detecção de momentos críticos, decaimento de baseline
- **Arquiteturas Neurais:** Alinhamento vision-language VL-JEPA, integração de memória Hopfield, dinâmicas LTC
- **Feature Engineering:** Vetor tático unificado de 25 dimensões, quantização heurística
- **Pipelines de Análise:** Estatísticas por round, cálculo do rating HLTV 2.0, análise de uso de utilitários

## Utilitários

### `generate_zh_pdfs.py`

Gera versões PDF em chinês da documentação. Execute a partir da raiz do projeto:

```bash
python docs/generate_zh_pdfs.py
```

### `md2pdf.mjs`

Conversor de Markdown para PDF baseado em Node.js. Requer dependências npm:

```bash
cd docs && npm install && node md2pdf.mjs
```

### `package.json`

Configuração de ferramentas para documentação, incluindo markdownlint e geração de PDF.

## Começando

1. Comece com **[QUICKSTART.md](QUICKSTART.md)** ou **[USER_GUIDE.md](USER_GUIDE.md)** para instalação e configuração
2. Leia os **Livros de Visão** (1A → 1B → 2 → 3) para a arquitetura completa do sistema
3. Explore **[Studies/](Studies/)** para compreensão técnica aprofundada
4. Consulte **[ERROR_CODES.md](ERROR_CODES.md)** ao depurar problemas

## Notas de Desenvolvimento

- Toda a documentação está em formato Markdown para máxima portabilidade
- Termos técnicos, nomes de classes e referências ao código permanecem em inglês em todas as traduções
- A geração de PDF requer a toolchain Node.js ou pacotes Python
- O arquivo `CLAUDE.md` na raiz do projeto contém os princípios de engenharia e diretrizes de desenvolvimento

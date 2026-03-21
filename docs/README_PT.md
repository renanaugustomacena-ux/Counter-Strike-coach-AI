# Macena CS2 Analyzer — Índice de Documentação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autoridade:** Regra 8 (Governança de Documentação)

Este diretório contém a documentação completa para o projeto Macena CS2 Analyzer — uma aplicação sofisticada de análise tática e coaching com IA para Counter-Strike 2. A documentação está organizada em guias do usuário, especificações técnicas, artigos de pesquisa e scripts utilitários.

## Estrutura do Diretório

```
docs/
├── USER_GUIDE.md                       # Guia completo do usuário (Inglês)
├── USER_GUIDE_IT.md                    # Guida utente completa (Italiano)
├── USER_GUIDE_PT.md                    # Guia completo do usuário (Português)
├── Progetto-Renan-Cs2-AI-Coach.md      # Especificação completa da arquitetura
├── AI_ARCHITECTURE_ANALYSIS.md         # Análise aprofundada da arquitetura AI (Inglês)
├── AI_ARCHITECTURE_ANALYSIS_IT.md      # Analisi architettura AI (Italiano)
├── AI_ARCHITECTURE_ANALYSIS_PT.md      # Análise da arquitetura AI (Português)
├── ERROR_CODES.md                      # Referência de códigos de erro
├── EXIT_CODES.md                       # Referência de códigos de saída
├── HLTV_SYNC_SERVICE_SPEC.md           # Especificação do serviço de sincronização HLTV
├── INDUSTRY_STANDARDS_AUDIT.md         # Auditoria de conformidade com padrões da indústria
├── prompt.md                           # Guia de prompts para assistentes de IA
├── generate_manual_pdf_it.py           # Utilitário gerador de manual em PDF
├── logging-and-plan.md                 # Documentação da arquitetura de logging
├── Studies/                            # 17 artigos de pesquisa (estudos aprofundados)
├── Book-Coach-1A*.md/pdf               # Livro visão parte 1A
├── Book-Coach-1B*.md/pdf               # Livro visão parte 1B
├── Book-Coach-2*.md/pdf                # Livro visão parte 2
├── Book-Coach-3*.md/pdf                # Livro visão parte 3
└── package.json                        # Ferramentas dos docs (markdownlint, etc.)
```

## Documentação do Usuário

### Guias do Usuário (3 Idiomas)

Os guias do usuário cobrem instalação, configuração, tutoriais de recursos, solução de problemas e boas práticas:

- **[USER_GUIDE.md](USER_GUIDE.md)** — Guia completo do usuário (Inglês)
- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia completo do usuário (Português)

Cada guia cobre:
1. Instalação e configuração do ambiente
2. Primeira ingestão de demo (a regra 10/10)
3. Panorama da tela de coaching
4. Histórico de partidas e análise de desempenho
5. Configurações e ajustes
6. Solução de problemas comuns

## Documentação Técnica

### Especificações da Arquitetura

- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Especificação completa da arquitetura em 12 seções (Italiano)
  - Arquitetura do sistema e diagramas de fluxo de dados (Mermaid)
  - Modelos de redes neurais (RAP Coach, JEPA, NeuralRoleHead)
  - Sistemas de memória (híbrido LTC-Hopfield)
  - Pipeline de coaching (modo COPER)
  - Esquema do banco de dados e arquitetura de armazenamento
  - Padrões de design UI/UX (MVVM)

- **Análise da Arquitetura AI** — Estudo aprofundado do subsistema de IA
  - [Inglês](AI_ARCHITECTURE_ANALYSIS.md) | [Italiano](AI_ARCHITECTURE_ANALYSIS_IT.md) | [Português](AI_ARCHITECTURE_ANALYSIS_PT.md)

### Documentos de Referência

| Documento | Finalidade |
|-----------|------------|
| [ERROR_CODES.md](ERROR_CODES.md) | Todos os códigos de erro com causas e remediações |
| [EXIT_CODES.md](EXIT_CODES.md) | Códigos de saída para scripts e daemons |
| [HLTV_SYNC_SERVICE_SPEC.md](HLTV_SYNC_SERVICE_SPEC.md) | Especificação do scraper de estatísticas pro HLTV |
| [INDUSTRY_STANDARDS_AUDIT.md](INDUSTRY_STANDARDS_AUDIT.md) | Auditoria de conformidade com padrões da indústria |
| [logging-and-plan.md](logging-and-plan.md) | Arquitetura de logging estruturado e roadmap |

### Integração com Assistentes de IA

- **[prompt.md](prompt.md)** — Prompts estruturados e fluxos de trabalho para desenvolvimento assistido por IA, revisão de código e manutenção do sistema

### Livros de Visão

Os "Coach Books" descrevem a visão completa do produto, a arquitetura técnica e a estratégia de negócios:

| Livro | Foco |
|-------|------|
| Book-Coach-1A | Fundamentos: definição do problema, análise de mercado, visão do produto |
| Book-Coach-1B | Técnico: arquiteturas neurais, pipeline de treinamento, modelo de dados |
| Book-Coach-2 | Implementação: modos de coaching, UI/UX, pontos de integração |
| Book-Coach-3 | Estratégia: monetização, licenciamento SDK, modelo open-core |

Disponíveis em formato Markdown e PDF, em inglês, italiano e português.

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

### `generate_manual_pdf_it.py`

Converte o guia do usuário italiano (`USER_GUIDE_IT.md`) em um manual PDF formatado usando conversão markdown-to-PDF. Execute a partir da raiz do projeto:

```bash
python docs/generate_manual_pdf_it.py
```

### `package.json`

Configuração de ferramentas para documentação, incluindo markdownlint e outras verificações de qualidade do Markdown. Instale com:

```bash
cd docs && npm install
```

## Começando

1. Comece com **[USER_GUIDE.md](USER_GUIDE.md)** para instalação e configuração
2. Revise **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** para a arquitetura do sistema
3. Explore **[Studies/](Studies/)** para compreensão técnica aprofundada
4. Consulte **[ERROR_CODES.md](ERROR_CODES.md)** ao depurar problemas

## Notas de Desenvolvimento

- Toda a documentação está em formato Markdown para máxima portabilidade
- Termos técnicos, nomes de classes e referências ao código permanecem em inglês em todas as traduções
- Diagramas Mermaid são utilizados para visualização de arquitetura e fluxo de dados
- A geração de PDF requer os pacotes Python `markdown` e `weasyprint`
- O arquivo `CLAUDE.md` na raiz do projeto contém os princípios de engenharia e diretrizes de desenvolvimento

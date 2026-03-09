# Macena CS2 Analyzer - Índice de Documentação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Este diretório contém a documentação completa para o projeto Macena CS2 Analyzer, uma aplicação sofisticada de análise tática e coaching com IA para Counter-Strike 2.

## Documentação do Usuário

### Guias do Usuário
- **[USER_GUIDE.md](USER_GUIDE.md)** — Guia completo do usuário (Inglês)
  Instalação, configuração, tutoriais de recursos, solução de problemas e boas práticas

- **[USER_GUIDE_IT.md](USER_GUIDE_IT.md)** — Guida utente completa (Italiano)
  Tradução italiana do guia completo do usuário

- **[USER_GUIDE_PT.md](USER_GUIDE_PT.md)** — Guia completo do usuário (Português)
  Tradução em português brasileiro do guia completo do usuário

## Documentação Técnica

### Arquitetura e Design
- **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** — Especificação completa da arquitetura do projeto (Italiano)
  Especificação técnica abrangente em 12 seções com diagramas Mermaid cobrindo:
  - Arquitetura do sistema e fluxo de dados
  - Modelos de redes neurais (RAP Coach, JEPA, NeuralRoleHead)
  - Sistemas de memória (LTC-Hopfield)
  - Pipeline de coaching (modo COPER)
  - Esquema do banco de dados e arquitetura de armazenamento
  - Padrões de design UI/UX

### Integração com Assistentes de IA
- **[prompt.md](prompt.md)** — Guia de prompts para assistentes de IA
  Prompts estruturados e fluxos de trabalho para desenvolvimento assistido por IA, revisão de código e manutenção do sistema

### Utilitários
- **[generate_manual_pdf_it.py](generate_manual_pdf_it.py)** — Gerador de manual em PDF
  Converte o guia do usuário italiano em um manual PDF formatado

## Pesquisa e Estudos Aprofundados

### Diretório Studies
O diretório **[Studies/](Studies/)** contém 17 artigos de pesquisa técnica aprofundada cobrindo os fundamentos teóricos e detalhes de implementação do sistema:

- **Epistemologia e Teoria dos Jogos:** Redes bayesianas de crença, jogo adversarial racional, estimativa de probabilidade de morte
- **Arquitetura de Coaching:** Design do RAP Coach, modo COPER (Context + Observation + Pro Reference + Experience + Reasoning)
- **Inteligência Espacial:** Tratamento de Z-cutoff, mapas multi-nível, análise de engagement range
- **Sistemas de Momentum:** Modelagem de momentum temporal, detecção de momentos críticos, decaimento de baseline
- **Arquiteturas Neurais:** Alinhamento vision-language VL-JEPA, integração de memória Hopfield, dinâmicas LTC
- **Feature Engineering:** Vetor tático unificado de 25 dimensões, quantização heurística
- **Pipelines de Análise:** Estatísticas por round, rating HLTV 2.0, análise de uso de utilitários

## Começando

1. Comece com **[USER_GUIDE.md](USER_GUIDE.md)** para instalação e configuração
2. Revise **[Progetto-Renan-Cs2-AI-Coach.md](Progetto-Renan-Cs2-AI-Coach.md)** para arquitetura do sistema
3. Explore **[Studies/](Studies/)** para compreensão técnica aprofundada

## Contribuindo

Consulte o arquivo `CLAUDE.md` na raiz do projeto para princípios de engenharia e diretrizes de desenvolvimento.

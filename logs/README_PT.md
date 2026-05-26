> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Logs de Sistema Centralizados

Este diretório serve como o hub centralizado para observabilidade de todo o sistema e dados de diagnóstico. Ele agrega logs do mecanismo de backend, serviços de ingestão de partidas e módulos de inferência de IA para fornecer uma visão abrangente da integridade operacional do sistema.

## Visão Geral Técnica

A arquitetura de log foi projetada para monitoramento de alta granularidade do backend do coach de Counter-Strike. Os logs são gerados usando um formato estruturado para facilitar a análise automatizada e o alerta. O objetivo principal é garantir que gargalos de desempenho, falhas de ingestão e desvios de modelo sejam identificados e resolvidos em tempo real.

## Componentes Chave

- **`cs2_analyzer.log`**: O principal arquivo de log para o mecanismo de análise de backend. Ele rastreia:
    - **Monitoramento de Erros**: Stack traces detalhados para falhas de API, problemas de conexão de banco de dados e erros de análise (parsing) de demos.
    - **Taxa de Transferência de Ingestão**: Métricas sobre quantos arquivos de demo estão sendo processados por minuto, incluindo o tamanho do arquivo e a duração da análise.
    - **Latência de Inferência**: Tempo preciso para solicitações de LLM e VLM, permitindo a otimização dos tempos de resposta do modelo.
    - **Integridade do Sistema**: Heartbeats periódicos de processos de trabalho em segundo plano e do serviço de sincronização HLTV.

## Estrutura do Diretório

```text
logs/
├── cs2_analyzer.log        # Log principal de backend e análise
├── README.md               # Esta documentação (EN)
├── README_IT.md            # Versão Italiana
└── README_PT.md            # Versione Portuguesa
```

## Uso

### Monitoramento em Tempo Real
Para monitorar os logs do sistema em tempo real durante uma sessão de ingestão ou treinamento em larga escala:
```bash
tail -f logs/cs2_analyzer.log
```

### Rotação de Log
O sistema está configurado para girar automaticamente os logs quando eles atingem 100 MB, mantendo até 5 versões históricas (por exemplo, `cs2_analyzer.log.1`) para evitar o esgotamento do espaço em disco.

### Filtragem por Erros
Para identificar rapidamente problemas críticos nos logs:
```bash
grep "ERROR" logs/cs2_analyzer.log
```

### Análise de Desempenho
As entradas de log incluem campos `latency_ms` para chamadas de inferenza, que podem ser extraídos para gerar histogramas de desempenho e identificar respostas lentas do modelo.

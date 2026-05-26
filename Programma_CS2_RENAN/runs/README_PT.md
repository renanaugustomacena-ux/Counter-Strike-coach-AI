> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Execuções de Sessão e Dados de Processo

Este diretório serve como o armazenamento volátil e espaço de trabalho para todos os dados de execução específicos de sessão gerados pelo coach de IA do Counter-Strike. Ele atua como um buffer temporário para tarefas de processamento ativas e um registro histórico para ciclos de análise concluídos.

## Visão Geral Técnica

O diretório `runs/` foi projetado para lidar com um alto volume de processamento de dados durante a ingestão de partidas e o treinamento do modelo. Cada ciclo de execução (uma "run") cria um subdiretório com timestamp ou baseado em ID para isolar seus dados de outras sessões. Esse isolamento garante que os resultados de análise intermediária e os checkpoints de treinamento não se sobreponham, permitindo o processamento simultâneo de múltiplos demos ou sessões de treinamento.

## Componentes Principais

- **Checkpoints de Treinamento**: Durante os ciclos de ajuste fino (fine-tuning) do modelo ou aprendizado por reforço, estados periódicos do modelo (pesos, estados do otimizador) são armazenados aqui.
- **Resultados de Análise Intermediária**: Arquivos JSON e binários temporários gerados durante o parsing de arquivos demo antes de serem agregados no banco de dados final ou relatório.
- **Logs Brutos de Sessão**: Logs de execução detalhados e de baixo nível específicos para uma única execução, úteis para depurar ingestões falhas ou drift do modelo.
- **Cache de Inferência**: Dados transitórios usados durante a inferência de VLM/LLM para acelerar consultas repetitivas dentro da mesma sessão.

## Estrutura do Diretório

```text
Programma_CS2_RENAN/runs/
├── [run_id_ou_timestamp]/  # Espaço de trabalho isolado para uma sessão específica
│   ├── checkpoints/         # Pesos do modelo e estado de treinamento
│   ├── intermediate/        # Dados de demo parcialmente processados
│   └── session.log          # Log detalhado para esta execução específica
├── README.md                # Documentação em inglês
├── README_IT.md             # Versão em italiano
└── README_PT.md             # Esta documentação
```

## Uso

1. **Processamento Ativo**: Quando uma nova ingestão de demo começa, o sistema cria automaticamente uma nova pasta em `runs/` para armazenar o estado temporário.
2. **Treinamento de Modelo**: O script de treinamento grava seu progresso e arquivos periódicos `.pth` ou `.ckpt` neste diretório.
3. **Limpeza**: Como este armazenamento é considerado volátil, recomenda-se arquivar checkpoints importantes e limpar pastas de execuções antigas periodicamente para economizar espaço em disco. O sistema inclui políticas de limpeza automática para execuções mais antigas que um limite específico.
4. **Depuração**: No caso de uma falha no motor, os arquivos dentro da pasta da execução específica são a fonte primária para análise pós-morte.

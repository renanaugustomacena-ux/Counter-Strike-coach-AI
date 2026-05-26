> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Configurações Táticas

Este diretório serve como o repositório centralizado para metadados táticos específicos de mapas usados pelo coach de IA do Counter-Strike. Ele armazena conhecimento estratégico fundamental em formato JSON estruturado, permitindo que a IA forneça coaching consciente do contexto baseado em padrões profissionais estabelecidos.

## Visão Geral Técnica

O motor tático depende desses arquivos de configuração para validar as ações dos jogadores, sugerir melhorias e entender o estado de uma rodada. Ao desacoplar os dados táticos da lógica central, o sistema permite atualizações fáceis no "meta" sem exigir alterações no código. O coach de IA analisa esses arquivos para comparar dados de jogo em tempo real com parâmetros de execução "perfeitos" predefinidos.

## Componentes Principais

- **`mirage_defaults.json`**: Este é o principal arquivo de referência para o mapa de_mirage. Ele contém pontos de dados abrangentes, incluindo:
    - **Lineups de Smoke**: Coordenadas precisas e ângulos de visão para granadas de fumaça essenciais (ex: Jungle, Stairs, Nest).
    - **Timings de Flash**: Atrasos ideais e durações de pop-flash para maximizar a cegueira dos inimigos.
    - **Setups Padrão (Defaults)**: Distribuições padrão do lado CT (ex: 2-1-2) e execuções padrão do lado T.
    - **Metadados Estratégicos**: Limites para eficiência de utilitários e heatmaps de posicionamento.

## Estrutura do Diretório

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Referência estratégica para de_mirage
├── README.md             # Documentação em inglês
├── README_IT.md          # Versão em italiano
└── README_PT.md          # Esta documentação
```

## Uso

O coach de IA utiliza esses arquivos durante as fases de ingestão e análise:
1. **Carregamento de Referência**: Na inicialização, o diretório `tactics/` é escaneado e todas as configurações JSON são carregadas na memória.
2. **Motor de Comparação**: Durante a análise da partida, o motor cruza o uso de utilitários do jogador com as coordenadas definidas em `mirage_defaults.json`.
3. **Geração de Feedback**: Se o timing ou posicionamento de um jogador divergir significativamente do "padrão", o coach gera conselhos corretivos específicos.

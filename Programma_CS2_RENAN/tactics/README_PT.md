> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Configuracoes Taticas

Este diretorio serve como o repositorio centralizado para metadados taticos
especificos de mapas usados pelo coach de IA do Counter-Strike. Ele armazena
conhecimento estrategico fundamental em formato JSON estruturado, permitindo que
a IA forneca coaching consciente do contexto baseado em padroes profissionais
estabelecidos.

## Visao Geral Tecnica

Ao desacoplar os dados taticos da logica central, este diretorio permite
atualizacoes no "meta" sem exigir alteracoes no codigo. Cada arquivo JSON
contem um identificador de mapa, uma string de versao e uma lista de regras de
coaching baseadas em funcoes, indexadas por um trigger in-round.

## Componentes Principais

- **`mirage_defaults.json`**: Um arquivo de referencia seed para o mapa de_mirage (versao 1.0). Atualmente contem duas regras de conselho baseadas em funcoes:
    - **AWPer / `round_start`**: Verificar o timing de Mid Nest -- o padrao profissional e alcancar a janela ate 1:48.
    - **Entry Fragger / `t_side_exec`**: Priorizar o clearing de Sandwich e Firebox durante a execucao do site A.

Cada regra e um objeto `{role, trigger, advice}`; nao ha coordenadas de lineup nem temporizacoes de utilitarios no arquivo atual.

## Estrutura do Diretorio

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Referencia estrategica para de_mirage
├── README.md             # Documentacao em ingles
├── README_IT.md          # Versao em italiano
└── README_PT.md          # Esta documentacao
```

## Uso

**Status: ainda nao conectado ao runtime.** Atualmente nenhum codigo carrega
arquivos de `tactics/`; o pipeline de coaching obtem seu conteudo tatico de
`backend/knowledge/` (base de conhecimento RAG e Coach Book). Este diretorio e
o local designado para arquivos de regras especificas por mapa, caso o coaching
tatico baseado em triggers seja integrado:
1. **Carregamento de Referencias**: Escanear o diretorio `tactics/` e armazenar as configuracoes JSON em cache na memoria.
2. **Matching de Regras**: Cruzar o `trigger` de uma regra (ex. `round_start`, `t_side_exec`) e a `role` com o contexto in-round do jogador.
3. **Geracao de Feedback**: Exibir o texto `advice` da regra como coaching corretivo.

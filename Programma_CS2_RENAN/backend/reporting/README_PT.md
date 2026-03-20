> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Reporting — Motor Analitico para Dashboard

> **Autoridade:** Regra 1 (Corretude), Regra 2 (Soberania do Backend)

Este modulo fornece a camada de calculo matematico e agregacao de dados para a interface do dashboard. Calcula tendencias de jogadores, dados de radar de habilidades e baselines profissionais — todas consultas somente leitura sem mutacoes.

Nota: Isto e distinto do diretorio reporting/ de nivel superior, que lida com geracao de PDF e saida de visualizacao. Este modulo foca no calculo de dados.

## Arquivo: analytics.py (351 linhas)

### AnalyticsEngine — Metodos Principais

- get_player_trends(player_name, limit=20) → DataFrame — Performance historica para graficos de tendencia
- get_skill_radar(player_name) → Dict — Atributos de habilidade normalizados (0-100) vs baseline profissional
- compute_pro_baselines() → Dict — Agrega estatisticas de jogadores profissionais
- get_coach_state(player_name) → CoachState — Ultimo estado de coaching para exibicao de status

## Padroes de Design

- Responsabilidade unica: apenas matematica e agregacao, sem mutacoes
- Verificacao de null defensiva: retorna valores padrao seguros se os dados forem insuficientes
- Consultas somente leitura: utiliza SQLModel ORM
- Logging: `get_logger("cs2analyzer.analytics")`

## Notas de Desenvolvimento

- A normalizacao do grafico radar e baseada em heuristicas (nao ML)
- Baselines profissionais calculadas a partir de PlayerMatchStats onde is_pro == True
- Nunca armazene resultados em cache nesta classe — deixe o ViewModel gerenciar o caching

# Guia de funcionalidades

## Painel

A faixa de status mostra **Coach** (ocioso ou analisando), **Serviço** (o Session Engine em segundo plano: *Online* enquanto o heartbeat está recente, *Offline* caso contrário) e **Partidas** (as suas demos analisadas). Abaixo: a sua última partida com a sparkline de rating, o card de foco, a faixa de partidas recentes, os cards **Análise de demos** e **Ingestão de demos pro** com seus seletores de pasta e botões Analisar, os atalhos de Conectividade (Perfil, Steam Config, FaceIt Config), os atalhos de Análise tática e um card **Status do treinamento** que aparece enquanto um treinamento reporta progresso.

## AI Coach

**Confiança do modelo** com seus fatores (a contagem de amostras são as suas demos analisadas), **Insights recentes** (os seus insights, ordenados por gravidade, os três primeiros em destaque) e o chat. As respostas vêm de um modelo Ollama local (padrão `gemma4:e2b`) que recebe as suas análises e a biblioteca pro como contexto e é instruído a nunca descrever números de outros jogadores como seus.

## Histórico de partidas

Todas as partidas analisadas. A legenda do cabeçalho separa *N pessoais · M referência pro*; cada linha traz rating, K/D, ADR, KAST e porcentagem de headshots. Abrir uma linha leva ao Detalhe da partida.

## Detalhe da partida

Quatro abas: **Visão geral** (blocos principais, faixa de rounds, componentes HLTV 2.0, enriquecimento de kills, utilitários por round), **Rounds**, **Economia** e **Destaques**. Uma partida pro em que você não jogou recebe o título *Demo pro · jogador — não é você* e mostra as linhas daquele jogador.

## Análises avançadas

As suas médias (rating, partidas, K/D, ADR, KAST), o seu percentil em relação ao grupo pro, a tendência de rating, pontos fortes e fracos em relação à média pro, os blocos por mapa e a eficácia dos utilitários. Sem demos pessoais, mostra um estado vazio mais um bloco *Referência pro* que faz a média das partidas de outros jogadores: material de referência, não o seu desempenho.

## Analisador tático

Um replay 2D de uma demo: jogadores, utilitários, a bomba, navegação pelos rounds e momentos críticos. As sobreposições "ghost" de um modelo treinado só aparecem quando esse modelo está habilitado nas configurações.

## Comparação pro

Compare os cards de estatísticas de dois jogadores pro a partir dos metadados da HLTV; o botão Detalhes abre a página do jogador.

## Configurações

**Aparência** (tema, fonte, papel de parede), **Análise e caminhos** (pasta de demos, pasta de demos pro, modo de ingestão, Iniciar ingestão) e **Idioma** (English, Italiano, Português).

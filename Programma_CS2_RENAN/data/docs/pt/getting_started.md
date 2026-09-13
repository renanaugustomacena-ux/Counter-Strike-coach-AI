# Primeiros passos com o Macena CS2 Analyzer

## 1. Quem é você nos dados

O analyzer identifica você pelo seu **nome no jogo**, o nickname que o CS2 mostra no placar. Defina-o no assistente inicial ou depois na tela **Perfil** (Painel → Conectividade → Perfil). A comparação é exata mas não diferencia maiúsculas de minúsculas, e precisa ser o mesmo nome que aparece dentro das suas demos. Não é preciso vincular nenhuma conta: a tela Steam Config é um extra opcional para estatísticas do perfil Steam e não participa da separação entre os seus rounds e os dos outros nove jogadores.

## 2. Duas pastas, dois tipos de demo

- **Pasta de demos** (assistente, ou Configurações → Análise e caminhos): as suas partidas. Tudo o que é importado daqui é *seu* e alimenta o Histórico de partidas, as Análises avançadas e o coach.
- **Pasta de demos pro** (Configurações → Análise e caminhos): partidas profissionais que você baixou. Elas formam a biblioteca de referência com a qual o analyzer compara você e nunca são mostradas como seu desempenho.

O CS2 salva as suas demos na pasta de replays da Steam: `...\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\` no Windows, `~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/replays/` no Linux. Arquivos com menos de 10 MB são ignorados como incompletos.

## 3. Analisar

No Painel pressione **Analisar demos** (a sua pasta) ou **Analisar demos pro** (a pasta pro). Cada `.dem` novo é lido tick a tick e as estatísticas por partida, os rounds e as posições vão para o banco de dados local; uma partida completa leva alguns minutos. A legenda abaixo de cada botão informa quantas demos foram analisadas. Quando o serviço em segundo plano está online (chip **Serviço**), ele também vigia as duas pastas e coloca os arquivos novos na fila sozinho.

## 4. O que é liberado e quando

- O **Histórico de partidas** lista as suas partidas e, separadamente, as partidas pro da biblioteca.
- **Análises avançadas** e **AI Coach** usam apenas as suas demos. Sem nenhuma analisada, mostram um estado vazio honesto; as Análises avançadas acrescentam um bloco *Referência pro* claramente rotulado, construído a partir das partidas de outros jogadores.
- O **chat do coach** exige o [Ollama](https://ollama.com/download) rodando neste computador com o modelo `gemma4:e2b` baixado; a tela Coach mostra se ele está online.
- A **confiança do modelo** cresce com as suas demos analisadas: 50% até 49 demos, 80% a partir de 50, 100% a partir de 200.

## 5. Treinar o coach

O coach neural aprende com as partidas analisadas no banco de dados, as suas e a biblioteca pro. No Painel, o card **Status do treinamento** oferece **Treinar o coach**: escolha um preset de passos (200 para uma verificação rápida, 2 000 padrão, 20 000 para a execução completa, que leva horas na CPU) e pressione o botão. O mesmo botão fica nas Configurações ao lado de Iniciar ingestão.

O treinamento nunca roda dentro da janela: o pedido vai para o serviço em segundo plano (o chip **Serviço** precisa estar *Online*), que atribui a divisão treino/validação, exporta os shards de episódios na sua pasta de dados, treina o encoder JEPA v2 e registra a execução. O card mostra o progresso dos passos, as losses e uma estimativa de tempo; **Parar** encerra a execução em um checkpoint retomável. Ao terminar, o card indica o modelo ativo com o número de passos, a data e o número de demos. Com poucas demos analisadas a execução é pulada e o card explica o motivo.

O que o treinamento ainda não faz: o texto dos conselhos do coach não usa o encoder treinado até os próximos passos do plano do núcleo neural chegarem, então a redação dos insights não muda depois de uma execução.

A partir de uma cópia do código-fonte a linha de comando continua funcionando:

```bash
python run_full_training_cycle.py --model-type jepa_v2
```

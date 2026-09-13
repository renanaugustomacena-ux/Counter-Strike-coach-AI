# Guia de solução de problemas

## "Nenhuma demo pessoal analisada ainda"

- O seu nome no jogo precisa corresponder ao nome dentro da demo (maiúsculas e minúsculas não importam). Confira na tela Perfil.
- A pasta de demos precisa estar definida e conter arquivos `.dem` completos (10 MB ou mais).
- Pressione **Analisar demos** no Painel e observe a legenda abaixo do botão.
- Partidas pro nunca contam como pessoais, mesmo quando um pro usa o seu nickname.

## Serviço: Offline

O Session Engine em segundo plano não está rodando ou não enviou um heartbeat nos últimos cinco minutos. Reinicie o aplicativo; se continuar offline, leia `cs2_analyzer_daemon.log` na pasta de logs. A vigilância automática das pastas depende do serviço; os botões Analisar funcionam sem ele.

## "Backend Startup Error"

O console não conseguiu inicializar (banco de dados ou caminhos). A janela continua utilizável; procure a causa em `cs2_analyzer.log` na pasta de logs: geralmente é uma pasta de demos que não existe mais.

## Chat do coach offline

O chat exige o Ollama rodando neste computador com o modelo selecionado baixado: `ollama pull gemma4:e2b`, depois `ollama serve`. A lista de modelos na tela Coach mostra o que o Ollama tem disponível.

## Download do "modelo de linguagem de IA"

A busca de conhecimento do coach usa um pequeno modelo de linguagem (cerca de 90 MB) baixado uma única vez, em segundo plano, depois que a janela abre. Sem ele o coach recorre a uma busca por similaridade mais simples; nada mais é bloqueado.

## Banco de dados bloqueado

Não abra o `database.db` em uma ferramenta SQLite externa enquanto o app estiver em execução. Uma ingestão pesada pode causar novas tentativas breves, que se resolvem sozinhas.

## Sincronização HLTV / Docker

A coleta HLTV ao vivo é opcional e exige Docker. Quando o Docker não está disponível o app usa as baselines pro em cache e continua; a configuração `ENABLE_HLTV_SYNC` desliga a sincronização por completo.

## Onde estão os logs

`cs2_analyzer.log` (aplicativo) e `cs2_analyzer_daemon.log` (serviço em segundo plano) ficam na pasta `logs` da sua localização de dados: a pasta do projeto em uma instalação a partir do código-fonte, ou a pasta "brain" escolhida no assistente.

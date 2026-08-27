# O que este programa faz, explicado por quem fala Delphi

> **Para quem:** um programador sênior de outra pilha — trinta anos de Delphi, Interbase, BDE, aplicação desktop cliente/servidor. Nenhum conhecimento prévio de Python, de aprendizado de máquina ou de Counter-Strike é assumido.
>
> **Por que existe este documento:** trinta anos escrevendo regra de negócio à mão dão exatamente a bagagem certa para entender a parte difícil deste projeto. O que falta é só a tradução do vocabulário.
>
> **Autor:** Renan Augusto Macena

---

## Em uma frase

O programa assiste às partidas gravadas de Counter-Strike do jogador, compara o jeito dele de jogar com o jeito dos jogadores profissionais, e diz onde ele está perdendo pontos — com o número na mão, não no achismo.

Dito assim parece um brinquedo. Mas o miolo é um sistema de gestão bem convencional, e é por aí que vale entrar.

---

## A analogia que resolve quase tudo

Pense num sistema de gestão que você teria escrito para uma transportadora. Entram **documentos**. O sistema **lança, confere e consolida**. Sai um **relatório com recomendações**.

Aqui é a mesma coisa, com outros substantivos:

| No sistema de gestão | Neste projeto |
| --- | --- |
| Documento de entrada | Arquivo da partida gravada (`.dem`) |
| Lançamentos | Tiros, mortes, granadas, dinheiro gasto por rodada |
| Indicadores calculados | Rating, ADR, KAST, taxa de entrada, trocas |
| Relatório final | *"Você está morrendo cedo demais nas entradas do lado T na Mirage, e isso custou nove rodadas no mês"* |

A diferença de escala é o que muda o projeto de lugar. Não são trezentos lançamentos por dia. São sessenta e quatro por segundo, vezes dez jogadores, durante quarenta minutos.

---

## De onde vêm os dados

Quando alguém joga uma partida, o servidor grava um arquivo `.dem`. É um arquivo binário com estrutura fixa, gravado em *ticks* — fatias de tempo, 64 ou 128 por segundo conforme o servidor. Em cada tick ele registra, para cada um dos dez jogadores: posição X, Y, Z, para onde está olhando, vida, colete, arma na mão, dinheiro, se está agachado, se está cego por uma granada.

É um log de transações. Exatamente o que você lia quando precisava auditar um movimento de estoque que não fechava — só que com granularidade absurda.

> Uma partida real medida na máquina deu **2.127.460 linhas de tick**. Uma partida.

Ler esse formato binário não é trabalho do projeto: existe um componente de terceiros que faz isso, escrito em Rust e chamado a partir do Python. É o mesmo arranjo de sempre — uma DLL em C chamada de dentro do Delphi. E, como toda DLL nativa, quando ela morre, ela morre feio; volto nisso mais adiante.

---

## As quatro etapas

| Etapa | Nome | O que acontece |
| --- | --- | --- |
| 1 | **ASSISTE** | Lê o arquivo da partida e grava tudo no banco: agregados por jogador, estatísticas por rodada, e a telemetria tick a tick. |
| 2 | **APRENDE** | Passa milhões dessas linhas por um modelo, que vai ajustando os próprios coeficientes até acertar as previsões. |
| 3 | **PENSA** | Com o modelo pronto, compara a partida do usuário com o padrão profissional e localiza onde a diferença aparece. |
| 4 | **FALA** | Transforma a conta em frase em português, com a causa junto: não *"seu rating caiu"*, e sim por quê. |

---

## A arquitetura, no seu vocabulário

Quase tudo aqui tem um equivalente direto no que você já construiu:

| No Delphi você chama de | Aqui se chama |
| --- | --- |
| `TForm` | tela Qt/PySide6 (são 15) |
| `TDataModule` | ViewModel (padrão MVVM) |
| `OnClick`, `OnChange` | signals e slots do Qt |
| Serviço Windows | daemon em segundo plano (são 4) |
| `TThread` | Worker em thread separada |
| BDE + `TQuery` | SQLModel sobre SQLAlchemy (ORM) |
| Transaction log do Interbase | modo WAL do SQLite |
| QuickReport | telas de relatório + exportação PDF |

O PySide6 é, para todos os efeitos, a VCL do Python: componentes com propriedades e eventos, formulários, uma pilha de telas. A regra que o projeto segue com rigor é a que você já seguia por instinto — o formulário só desenha; a lógica mora no equivalente ao `TDataModule`. Existe até um teste automático que **proíbe** uma tela de conversar direto com o banco.

Os quatro daemons rodam num processo separado do da interface, porque parsing de demo e treino de rede neural são pesados e travariam a tela. É a mesma razão pela qual você tirou o processamento noturno de dentro do executável do caixa.

---

## A parte que é realmente diferente

Aqui está a única ideia deste projeto que não tem equivalente direto no seu mundo. Vale a pena entender porque, uma vez entendida, o resto desmonta.

Para classificar o desempenho de um jogador, você escreveria mais ou menos isto:

```pascal
if (Kills / Rounds > 0.7) and (ADR > 80) then
  Nivel := 'Bom'
else
  Nivel := 'Regular';
```

Funciona. Mas de onde saíram o `0.7` e o `80`? Da sua cabeça, ou de uma especificação que alguém escreveu com a cabeça dele. Alguém **digitou** aqueles números.

Uma rede neural é a mesma conta com uma diferença única: **os números não são digitados, são descobertos**. Você mostra ao programa cem mil exemplos de partidas de profissionais e diz "acerte a previsão". Ele começa com coeficientes aleatórios, erra feio, mede o tamanho do erro, empurra cada coeficiente um tiquinho na direção que diminui o erro, e repete. Milhões de vezes. Isso é "treinar".

Se ajuda: é um ajuste de curva, uma regressão. Só que em vez de dois ou três coeficientes, são centenas de milhares deles, arranjados em camadas.

E aí está o motivo de tudo isso existir. Com dois coeficientes você escreve a regra à mão e pronto. O que a rede consegue e a mão não consegue é achar a **combinação**: que perder o duelo de abertura importa três vezes mais na Inferno do que na Dust2, mas só quando o time está em desvantagem econômica e faltam menos de quarenta segundos. Ninguém escreve esse `if`. Não porque seja difícil — porque ninguém sabe que ele existe até os dados mostrarem.

> E é por isso que o projeto precisa de tanto dado. Regra escrita à mão funciona com zero exemplos. Regra descoberta precisa de muitos. É todo o custo do método.

---

## Duas coisas bonitas que saem disso

### O fantasma

Um dos modelos não classifica: ele prevê *onde o jogador deveria estar* naquele instante. O programa desenha isso no mapa 2D como um vulto semitransparente, ao lado de onde a pessoa realmente estava.

É o equivalente a um relatório que, além de dizer "seu estoque furou em três peças", desenha na planta do galpão onde as peças deveriam estar. Deixa de ser diagnóstico e vira instrução.

### O relatório que pede o próprio SELECT

O programa conversa com o usuário por escrito, usando um modelo de linguagem que roda **na própria máquina**, sem internet e sem mandar nada para servidor de ninguém.

Até pouco tempo funcionava assim: o programa montava o contexto, entregava pronto, e o modelo respondia com aquilo. Se a pergunta precisasse de um dado que ninguém tinha posto na mesa, ele respondia que não tinha acesso.

Agora ele pede. Existem quatro consultas que ele pode acionar — listar partidas, resumo de uma partida, detalhe de rodadas, ficha de um profissional. Ele decide qual precisa e chama.

Você montava o `SELECT` e entregava o resultado pronto para o relatório. Aqui o relatório aprendeu a pedir o `SELECT` de que precisa — e o programa virou o DBA que confere cada pedido antes de deixar rodar. Nome de partida que o modelo inventou não passa: é conferido contra uma lista tirada do próprio banco. Número de rodada vem limitado. Texto vem truncado. Nada do que ele escreve entra numa consulta sem passar por essa portaria.

---

## Onde os seus trinta anos valem ouro

Esta é a parte em que o projeto não tem nada de novo — e é justamente onde ele quase se perdeu.

### Dois caixas dando baixa no mesmo pedido

Existem seis lugares diferentes no programa que podem mandar processar uma partida da fila. Durante muito tempo, cada um deles fazia um `SELECT` da fila, via um trabalho livre e o pegava. Dois processos iniciados com meio segundo de diferença liam a **mesma fotografia** da fila, os dois achavam que o trabalho era deles, e a mesma partida era processada duas vezes — gravando estatística duplicada que depois ninguém sabia distinguir da boa.

Você conhece esse bug. A correção também:

```sql
UPDATE IngestionTask
   SET status = 'processing'
 WHERE id = :id
   AND status = 'queued';   -- e então: quantas linhas afetou?
```

Se afetou uma linha, o trabalho é meu. Se afetou zero, alguém chegou primeiro e eu sigo em frente calado. Travamento otimista, em uma instrução que o banco não consegue partir no meio. Sem semáforo, sem coordenação entre processos, sem nada para dar manutenção depois.

> A lição, que você já sabia: melhor eliminar a possibilidade da colisão do que administrá-la. Problema que não pode acontecer não precisa de log, nem de monitoramento, nem de alguém lembrando dele daqui a três anos.

### Backup com o banco aberto

O banco é SQLite em modo WAL. O backup **não** é cópia do arquivo — isso pegaria o banco no meio de uma transação e produziria uma cópia inválida. Usa a API de backup on-line, que copia página a página com o banco em uso, sem travar quem está escrevendo. É a mesma decisão que você tomava ao escolher entre parar o Interbase para copiar o `.gdb` ou usar a ferramenta própria.

### A DLL nativa que morre feio

O componente que lê o arquivo de partida é escrito em Rust. Quando ele encontra um arquivo corrompido, ele não levanta uma exceção comum: ele *entra em pânico*, e o pânico chega ao Python como um tipo de erro que fica **fora** da hierarquia normal. Resultado: todo tratamento de exceção do sistema deixava passar. Uma partida corrompida derrubava a sessão inteira de importação.

É o equivalente exato a uma violação de acesso vinda de dentro da DLL, que passa reto pelo seu `try..except` e leva o executável junto.

### E a regra da casa

Nenhum número inventado. Se o programa não sabe uma estatística, ele grava um valor sentinela documentado e avisa — nunca um zero plausível. Um zero plausível é pior que um erro, porque entra no relatório e ninguém desconfia.

---

## O tamanho real da coisa

Números medidos no repositório, não estimados:

| Grandeza | Valor |
| --- | --- |
| Arquivos de código Python | 493 |
| Linhas de código | ~126.400 |
| Telas na aplicação | 15 |
| Tabelas, em 3 bancos separados | 28 |
| Testes automatizados | 2.470 |
| Ferramentas de diagnóstico | 71 |

Os três bancos são separados de propósito, pela razão que você conhece: para não ter contenção de bloqueio. Um guarda os dados da aplicação; outro guarda as estatísticas dos profissionais, alimentado por um serviço que roda em processo separado; o terceiro é, na verdade, um banco pequeno por partida, para que a telemetria pesada não engorde o principal.

A interface está em três idiomas — inglês, italiano e português — e tem três temas visuais.

---

## O que funciona e o que ainda não

| Estado | O quê |
| --- | --- |
| **De pé** | A importação inteira: lê a partida, calcula, grava nos três bancos, gera os conselhos. |
| **De pé** | A aplicação desktop completa, com as 15 telas, o mapa 2D com reprodução da partida e o fantasma. |
| **De pé** | A conversa por escrito com o modelo local, já consultando o banco por conta própria. |
| **De pé** | A primeira fase de treino, verificada de ponta a ponta numa placa de vídeo real. |
| **Falta** | A segunda fase de treino nunca chegou ao fim — foi interrompida e não foi retomada. |
| **Falta** | Volume de dados. Um modelo desses fica bom com muitas partidas profissionais, e ainda são poucas. |
| **Falta** | Portanto: os conselhos que ele dá hoje ainda vêm mais das contas e das regras do que do modelo treinado. |

É um projeto pessoal, não um produto. Mas também não é maquete: as partes chatas e difíceis — as que consomem os anos e não aparecem em demonstração — estão de pé.

---

## Uma última coisa

Em agosto foi feita uma auditoria do repositório inteiro: todos os 618 arquivos lidos, um por um, em duas passadas. Saíram 44 problemas registrados. Trinta e um foram corrigidos, cada um com o seu teste de regressão no mesmo commit. Os treze restantes foram adiados com o motivo escrito por extenso — nada ficou aberto em silêncio.

Mas a parte que sobrevive à auditoria não são as correções. São uns testes de tipo diferente, que não verificam se uma função devolve o valor certo. Eles **proíbem uma classe inteira de erro de voltar**:

- um deles varre o código e falha se alguma tela voltar a conversar direto com o banco;
- outro falha se alguém redigitar o número 64 em vez de usar a constante do tick rate;
- outro falha se alguém reescrever a lista de mapas num arquivo novo em vez de importar a lista oficial.

É aquela regra de revisão de código que todo mundo combina e ninguém cumpre depois de seis meses — só que automatizada, e que reprova a compilação de quem furar.

---

Se alguma parte ficou obscura, a que vale perguntar primeiro é a do treino: é a única ideia genuinamente estranha ao mundo que você conhece. Todo o resto é banco de dados, concorrência, serviço em segundo plano e interface — coisa que você faz há trinta anos, com outros nomes.

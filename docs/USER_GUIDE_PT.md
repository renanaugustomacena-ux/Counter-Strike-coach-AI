# Macena CS2 Analyzer — Guia do Usuario

Guia completo para instalar, configurar e usar o Macena CS2 Analyzer no Windows ou Linux.

---

## Sumario

1. [Requisitos do Sistema](#1-requisitos-do-sistema)
2. [Instalacao](#2-instalacao)
3. [Primeiro Inicio e Assistente de Configuracao](#3-primeiro-inicio--assistente-de-configuracao)
4. [Configurando API Keys (Steam e FaceIT)](#4-configurando-api-keys-steam--faceit)
5. [Tela Inicial](#5-tela-inicial)
6. [Pagina de Configuracoes](#6-pagina-de-configuracoes)
7. [Tela do Coach e Chat com IA](#7-tela-do-coach--chat-com-ia)
8. [Historico de Partidas](#8-historico-de-partidas)
9. [Detalhe da Partida](#9-detalhe-da-partida)
10. [Painel de Desempenho](#10-painel-de-desempenho)
11. [Visualizador Tatico (Widget de Mapa 2D)](#11-visualizador-tatico-widget-de-mapa-2d)
12. [Perfil do Jogador](#12-perfil-do-jogador)
13. [Solucao de Problemas](#13-solucao-de-problemas)

---

## 1. Requisitos do Sistema

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| SO | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 ou 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nenhuma (modo CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disco | 3 GB livres | 5 GB livres |
| Tela | 1280x720 | 1920x1080 |

---

## 2. Instalacao

### 2.1 Clonar o Repositorio

```bash
git clone https://github.com/renanaugustomacena-ux/Macena_cs2_analyzer.git
cd Macena_cs2_analyzer
```

### 2.2 Windows (Configuracao Automatizada)

Abra o **PowerShell** na raiz do projeto e execute:

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Este script ira:
- Verificar se o Python 3.10+ esta instalado
- Criar um ambiente virtual (`venv_win/`)
- Instalar o PyTorch (versao CPU) e todas as dependencias
- Inicializar o banco de dados
- Instalar o Playwright (navegador Chromium para scraping do HLTV)

**Para suporte a GPU** (apenas NVIDIA), apos o script concluir:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2.3 Windows (Configuracao Manual)

Se o script do PowerShell falhar ou se voce preferir a instalacao manual:

```powershell
# Criar ambiente virtual
python -m venv venv_win
.\venv_win\Scripts\activate

# Instalar PyTorch (escolha UM):
# Apenas CPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Instalar todas as outras dependencias
pip install -r Programma_CS2_RENAN/requirements.txt

# Inicializar banco de dados
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Instalar navegador do Playwright
pip install playwright
python -m playwright install chromium
```

### 2.4 Linux (Ubuntu/Debian)

```bash
# Dependencias do sistema
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y libsdl2-dev libglew-dev build-essential

# Criar ambiente virtual
python3.10 -m venv venv_linux
source venv_linux/bin/activate

# Instalar PyTorch (escolha UM):
# Apenas CPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Instalar dependencias (ignore kivy-deps somente para Windows se o pip reclamar)
pip install -r Programma_CS2_RENAN/requirements.txt
pip install Kivy==2.3.0 KivyMD==1.2.0

# Inicializar banco de dados
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Instalar navegador do Playwright
pip install playwright
python -m playwright install chromium
```

### 2.5 Verificar a Instalacao

```bash
# Ative seu venv primeiro, depois:
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import kivy; print(f'Kivy: {kivy.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

Saida esperada (exemplo com GPU):
```
PyTorch: 2.5.1+cu121
Kivy: 2.3.0
Device: cuda:0
```

### 2.6 Iniciar o Aplicativo

```bash
# Windows
.\venv_win\Scripts\python.exe Programma_CS2_RENAN/main.py

# Linux
./venv_linux/bin/python Programma_CS2_RENAN/main.py
```

A janela abre em 1280x720. Na **primeira execucao**, voce vera o Assistente de Configuracao (Setup Wizard).

---

## 3. Primeiro Inicio e Assistente de Configuracao

Quando voce executa o main.py pela primeira vez, o aplicativo mostra um **assistente de configuracao em 3 etapas**.

### Etapa 1: Tela de Boas-Vindas

Voce ve uma mensagem de boas-vindas explicando o aplicativo. Clique em **START** para iniciar a configuracao.

### Etapa 2: Diretorio Raiz dos Dados da IA

O aplicativo pergunta: **"Onde a IA deve armazenar seus dados de treinamento?"**

Esta e a pasta onde os modelos de rede neural, a base de conhecimento e os conjuntos de dados de treinamento serao salvos. Pode estar em qualquer drive.

**Como configurar:**
1. Clique em **Select Folder** — um seletor de arquivos abre
2. Navegue ate o local desejado (ex.: `D:\CS2_Coach_Data` ou `C:\Users\SeuNome\Documents\CS2Coach`)
3. Selecione a pasta e confirme
4. O aplicativo cria tres subdiretorios dentro dela: `knowledge/`, `models/`, `datasets/`

**Ou** cole um caminho manualmente no campo de texto.

> **Dica:** Escolha um local com pelo menos 2 GB de espaco livre. Um SSD e recomendado para treinamento mais rapido.

> **Se voce vir "Permission denied":** Escolha uma pasta dentro do seu diretorio de usuario, como `C:\Users\SeuNome\Documents\MacenaData`.

Clique em **NEXT** quando terminar.

### Etapa 3: Configuracao Concluida

Clique em **LAUNCH** para entrar no aplicativo. O assistente nao aparecera novamente nas proximas execucoes.

> **Para re-executar o assistente:** Delete o arquivo `Programma_CS2_RENAN/user_settings.json` e reinicie o aplicativo.

---

## 4. Configurando API Keys (Steam e FaceIT)

As API keys permitem que o aplicativo busque seu historico de partidas e estatisticas de jogadores. Elas sao **opcionais** — o aplicativo funciona sem elas, mas alguns recursos (importacao automatica de partidas, sincronizacao de perfil do jogador) ficarao indisponiveis.

### 4.1 Steam API Key

1. Na **Tela Inicial (Home Screen)**, encontre o cartao **Personalizacao (Personalization)**
2. Clique no botao **Steam**
3. Voce vera dois campos:

**Steam ID (SteamID64):**
- Este e o seu identificador Steam de 17 digitos (ex.: `76561198012345678`)
- Clique no link **"Find Your Steam ID"** para abrir o [steamid.io](https://steamid.io) no seu navegador
- Insira a URL do seu perfil Steam e copie o numero **SteamID64**

**Steam Web API Key:**
- Clique no link **"Get Steam API Key"** para abrir o [Steam Developer](https://steamcommunity.com/dev/apikey) no seu navegador
- Faca login com sua conta Steam
- Quando perguntado sobre um nome de dominio, digite `localhost`
- Copie a chave gerada

4. Cole ambos os valores e clique em **Save Config**

> **Seguranca:** Sua API key e armazenada no **Cofre de Credenciais do Windows** (Windows Credential Manager) (ou no keyring do sistema no Linux), nao em texto puro. O arquivo de configuracoes mostra `"PROTECTED_BY_WINDOWS_VAULT"` em vez da chave real.

### 4.2 FaceIT API Key

1. Na **Tela Inicial (Home Screen)** > cartao **Personalizacao (Personalization)**, clique em **FaceIT**
2. Clique no link **"Get FaceIT API Key"** para abrir o [FaceIT Developers](https://developers.faceit.com/)
3. Crie uma conta de desenvolvedor e gere uma API key
4. Cole a chave e clique em **Save**

> **Nota:** O aplicativo valida as chaves no momento do uso, nao ao salvar. Se uma chave for invalida, voce vera um erro quando o aplicativo tentar buscar dados.

---

## 5. Tela Inicial

Apos a configuracao, este e o seu painel principal. Possui uma **barra de navegacao superior** e **cartoes rolaveis**.

### Barra de Navegacao Superior

| Icone | Acao |
|-------|------|
| Engrenagem (esquerda) | Abre **Configuracoes (Settings)** |
| Interrogacao (esquerda) | Abre **Ajuda (Help)** — topicos de documentacao pesquisaveis |
| Prancheta (direita) | Abre **Historico de Partidas (Match History)** |
| Grafico (direita) | Abre **Painel de Desempenho (Performance Dashboard)** |
| Capelo (direita) | Abre **Tela do Coach (Coach Screen)** |
| Pessoa (direita) | Abre **Perfil do Jogador (User Profile)** |

### Cartoes do Painel

**1. Progresso do Treinamento (Training Progress)**
Mostra o status do treinamento de ML em tempo real: epoca atual, perda de treino/validacao, tempo restante estimado. Quando o treinamento esta ocioso, exibe as metricas do ultimo treinamento concluido.

**2. Hub de Ingestao Pro (Pro Ingestion Hub)**
- **Set Folder**: Selecione a pasta contendo seus arquivos de demo `.dem` pessoais
- **Pro Folder**: Selecione a pasta contendo arquivos de demo `.dem` de jogadores profissionais
- **Seletor de velocidade**: Eco (lento, baixo CPU), Standard (equilibrado), Turbo (rapido, alto CPU)
- **Botao Play/Stop**: Inicia ou para o processo de ingestao de demos

**3. Personalizacao (Personalization)**
- **Profile**: Defina seu nome de jogador no jogo
- **Steam**: Configure Steam ID e API key ([veja Secao 4.1](#41-steam-api-key))
- **FaceIT**: Configure FaceIT API key ([veja Secao 4.2](#42-faceit-api-key))

**4. Analise Tatica (Tactical Analysis)**
Clique em **Launch Viewer** para abrir o visualizador de mapa tatico 2D ([veja Secao 11](#11-visualizador-tatico-widget-de-mapa-2d)).

**5. Insights Dinamicos (Dynamic Insights)**
Cartoes de coaching gerados automaticamente pela IA. Cada cartao possui:
- Uma **cor de severidade** (azul = informativo, laranja = aviso, vermelho = critico)
- Um **titulo** e **mensagem** explicando o insight
- Uma **area de foco** (ex.: "Posicionamento", "Uso de Utilitarios")

### Barra de Status do ML

No topo do painel, uma barra colorida mostra o status do servico de coaching:
- **Azul**: Servico ativo e em execucao
- **Vermelho**: Servico offline — clique em **RESTART SERVICE** para recuperar

---

## 6. Pagina de Configuracoes

Acesse pelo icone de engrenagem na Tela Inicial (Home Screen). Todas as alteracoes sao salvas imediatamente.

### Tema Visual (Visual Theme)

Tres presets de tema que alteram o esquema de cores e papel de parede do aplicativo:
- **CS2** (tons laranjas)
- **CS:GO** (tons azul-acinzentados)
- **CS 1.6** (tons verdes)

Clique em **Cycle Wallpaper** para alternar entre as imagens de fundo disponiveis para o tema atual.

### Caminhos de Analise (Analysis Paths)

- **Pasta de Demos Padrao (Default Demo Folder)**: Onde seus arquivos `.dem` pessoais estao armazenados. Clique em **Change** para selecionar uma nova pasta.
- **Pasta de Demos Pro (Pro Demo Folder)**: Onde os arquivos `.dem` de jogadores profissionais estao armazenados. Clique em **Change** para selecionar uma nova pasta.

> **Importante:** Quando voce altera a Pasta de Demos Pro, o aplicativo migra automaticamente os arquivos de banco de dados de partidas (`match_data/`) para o novo local.

### Aparencia (Appearance)

- **Tamanho da Fonte**: Pequeno (12pt), Medio (16pt) ou Grande (20pt)
- **Tipo de Fonte**: Escolha entre Roboto, Arial, JetBrains Mono, New Hope, CS Regular ou YUPIX

### Controle de Ingestao de Dados (Data Ingestion Control)

- **Alternador de Modo**: Alterne entre **Manual** (varredura unica) e **Auto** (varredura continua em intervalos)
- **Intervalo de Varredura**: Com que frequencia (em minutos) o modo automatico verifica novos demos. Minimo: 1 minuto.
- **Iniciar/Parar Ingestao**: Acionar ou parar manualmente o processo de ingestao

### Idioma (Language)

Alterne entre English, Italiano e Portugues. Toda a interface atualiza imediatamente.

---

## 7. Tela do Coach e Chat com IA

Acesse pelo icone de capelo na Tela Inicial (Home Screen).

### Painel (Dashboard)

- **Estado de Crenca (Belief State)**: Mostra a confianca de inferencia do coach de IA (0-100%). Verde quando acima de 70%.
- **Grafico de Tendencia (Trend Graph)**: Grafico de linha do seu Rating e ADR nas ultimas 20 partidas.
- **Radar de Habilidades (Skill Radar)**: Grafico aranha mostrando 5 dimensoes de habilidade (Mira, Utilitarios, Posicionamento, Leitura de Mapa, Clutch) comparadas com referencias profissionais.
- **Auditoria Causal (Causal Audit)**: Clique em **Show Advantage Audit** para visualizar a analise causal das suas decisoes.
- **Motor de Conhecimento (Knowledge Engine)**: Mostra quantos ticks de experiencia a IA processou e o progresso atual de parsing.
- **Cartoes de Coaching (Coaching Cards)**: Insights gerados pela IA com niveis de severidade.

### Painel de Chat (Chat Panel)

Clique no botao **chat toggle** (parte inferior da tela) para expandir o painel de chat.

- **Botoes de Acao Rapida (Quick Action Buttons)**: Perguntas pre-definidas — "Posicionamento", "Utilitarios", "O que melhorar?"
- **Campo de Texto (Text Input)**: Digite qualquer pergunta sobre sua gameplay
- **Respostas do Coach (Coach Replies)**: A IA analisa seus dados de partida e fornece conselhos personalizados

> **Nota:** A qualidade do coach melhora com mais demos ingeridos. Minimo de 10 demos recomendado para insights significativos.

---

## 8. Historico de Partidas

Acesse pelo icone de prancheta na Tela Inicial (Home Screen).

Mostra uma lista rolavel das suas **ultimas 50 partidas nao-profissionais**. Cada cartao de partida exibe:

- **Badge de Rating** (lado esquerdo, codificado por cores):
  - Verde: Rating > 1.10 (acima da media)
  - Amarelo: Rating 0.90 - 1.10 (media)
  - Vermelho: Rating < 0.90 (abaixo da media)
- **Nome do mapa** e **data**
- **Estatisticas**: Proporcao K/D, ADR, Abates, Mortes

**Clique em qualquer partida** para abrir a tela de [Detalhe da Partida](#9-detalhe-da-partida).

---

## 9. Detalhe da Partida

Mostra analise detalhada de uma unica partida, organizada em 4 secoes:

### Visao Geral (Overview)
Nome do mapa, data, rating geral (codificado por cores) e uma grade de estatisticas: Abates, Mortes, ADR, KAST%, HS%, Proporcao K:D, KPR (Abates Por Round), DPR (Mortes Por Round).

### Linha do Tempo dos Rounds (Round Timeline)
Uma lista de cada round jogado, mostrando:
- Numero do round e lado (CT/T)
- Abates, Mortes, Dano causado
- Badge de abertura de kill (se aplicavel)
- Resultado do round (Vitoria/Derrota)

### Grafico de Economia (Economy Graph)
Um grafico de barras mostrando o valor do seu equipamento por round. Barras azuis = lado CT, Barras amarelas = lado T. Ajuda a identificar padroes de eco/force-buy.

### Destaques e Momentum (Highlights & Momentum)
- **Grafico de Momentum**: Grafico de linha do seu delta acumulado de Abates-Mortes ao longo dos rounds. Preenchimento verde = momentum positivo, Preenchimento vermelho = negativo.
- **Insights de Coaching**: Analise gerada pela IA especifica para esta partida.

---

## 10. Painel de Desempenho

Acesse pelo icone de grafico na Tela Inicial (Home Screen). Mostra suas tendencias de desempenho a longo prazo.

### Tendencia de Rating (Rating Trend)
Grafico sparkline do seu rating nas ultimas 50 partidas. Linhas de referencia em:
- 1.10 (verde) — desempenho top
- 1.00 (branco) — media
- 0.90 (vermelho) — abaixo da media

### Desempenho por Mapa (Per-Map Performance)
Cartoes rolaveis horizontalmente, um por mapa (de_dust2, de_mirage, etc.). Cada um mostra:
- Rating medio (codificado por cores)
- ADR medio e proporcao K:D
- Numero de partidas jogadas

### Pontos Fortes e Fracos (Strengths & Weaknesses)
Comparacao em duas colunas contra referencias de jogadores profissionais usando Z-scores:
- **Esquerda (Verde)**: Suas metricas mais fortes
- **Direita (Vermelho)**: Areas que precisam de melhoria

### Painel de Utilitarios (Utility Panel)
Grafico de barras comparando seu uso de utilitarios com referencias profissionais em 6 metricas:
- Granadas HE, Molotovs, Granadas de Fumaca
- Tempo de Cegueira por Flash, Assistencias de Flash, Utilitarios Nao Utilizados

---

## 11. Visualizador Tatico (Widget de Mapa 2D)

Acesse pelo **Launch Viewer** na Tela Inicial (Home Screen).

Este e o visualizador de replay 2D em tempo real. Ele renderiza arquivos de demo como uma visualizacao interativa de mapa.

### O que Voce Ve
- **Mapa 2D**: Vista superior do mapa de CS2 com posicoes dos jogadores como circulos coloridos
- **Rotulos dos Jogadores**: Nome, funcao e barras de vida para cada jogador
- **Marcadores de Eventos**: Icones de abate, indicadores de plantio/desarme de bomba
- **Sobreposicao da IA (AI Overlay)**: Predicoes fantasma mostrando posicoes sugeridas pela IA (quando habilitado)

### Controles
- **Play/Pause**: Iniciar ou pausar a reproducao
- **Velocidade (Speed)**: Alternar entre 0.5x, 1x, 2x
- **Barra de Tempo (Timeline Scrubber)**: Clique em qualquer lugar na barra horizontal para pular para um tick especifico
- **Seletor de Mapa (Map Selector)**: Alternar entre mapas (para demos multi-mapa)
- **Seletor de Round (Round Selector)**: Pular para um round especifico ou visualizar a partida completa
- **Alternador Ghost AI (Ghost AI Toggle)**: Habilitar/desabilitar predicoes de posicao da IA

### Carregando um Demo
Na primeira entrada, um seletor de arquivo abre automaticamente. Selecione um arquivo `.dem` para carregar. O visualizador analisa e renderiza os dados do demo.

---

## 12. Perfil do Jogador

Acesse pelo icone de pessoa na Tela Inicial (Home Screen).

Mostra seu avatar de jogador, nome, funcao e biografia. Clique no **icone de lapis** para editar sua biografia e funcao. Clique em **SYNC WITH STEAM** para puxar seus dados de perfil do Steam (requer Steam API key).

---

## 13. Solucao de Problemas

### "ModuleNotFoundError: No module named 'kivy'"

As dependencias do Kivy nao estao instaladas. No Windows:
```bash
pip install kivy-deps.glew==0.3.1 kivy-deps.sdl2==0.7.0 kivy-deps.angle==0.4.0
pip install Kivy==2.3.0 KivyMD==1.2.0
```
No Linux, pule os pacotes `kivy-deps` — eles sao exclusivos do Windows.

### "No module named 'watchdog'"

```bash
pip install watchdog
```
Isso e necessario para a deteccao automatica de arquivos de demo. Sem ele, use a ingestao manual nas Configuracoes (Settings).

### "CUDA not available" / GPU nao detectada

Verifique se o driver NVIDIA esta instalado:
```bash
nvidia-smi
```
Depois reinstale o PyTorch com CUDA:
```bash
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
Verifique:
```bash
python -c "import torch; print(torch.cuda.is_available())"  # Deve imprimir True
```

> **Sem GPU NVIDIA?** O aplicativo funciona em CPU. O treinamento e mais lento, mas tudo funciona.

### Aviso "sentence-transformers not installed"

Isso e **normal** e nao-bloqueante. O aplicativo usa embeddings TF-IDF como alternativa. Para instalar:
```bash
pip install sentence-transformers
```
A primeira execucao baixa um modelo de ~80MB — isso e esperado.

### Aplicativo trava ao iniciar com erro GL do Kivy

No Windows, tente:
```bash
set KIVY_GL_BACKEND=angle_sdl2
python Programma_CS2_RENAN/main.py
```
No Linux:
```bash
export KIVY_GL_BACKEND=sdl2
python Programma_CS2_RENAN/main.py
```

### Erro de bloqueio do banco de dados ("database is locked")

Outro processo esta com o banco de dados aberto. Feche todos os processos Python:
```bash
# Windows
taskkill /F /IM python.exe
# Linux
pkill -f python
```
Depois reinicie o aplicativo.

### Permissao negada ao selecionar pastas

Escolha uma pasta dentro do seu diretorio de usuario:
- Windows: `C:\Users\SeuNome\Documents\MacenaData`
- Linux: `~/MacenaData`

Evite caminhos protegidos pelo sistema como `C:\Program Files\` ou `/usr/`.

### Aviso "Integrity mismatch detected"

Este e um aviso do modo de desenvolvimento da auditoria de seguranca RASP. Significa que os arquivos fonte foram modificados desde a ultima geracao do manifesto de integridade. **Nao bloqueia o aplicativo** — apenas bloqueia builds congelados/de producao.

### Aplicativo abre mas mostra tela em branco/branca

O arquivo de layout KV falhou ao carregar. Verifique:
1. Voce esta executando a partir da raiz do projeto (nao de dentro de `Programma_CS2_RENAN/`)
2. O arquivo `Programma_CS2_RENAN/apps/desktop_app/layout.kv` existe
3. Execute: `python Programma_CS2_RENAN/main.py` (nao `python main.py`)

### Como resetar o aplicativo para o estado de fabrica

Delete `user_settings.json` e reinicie:
```bash
# Windows
del Programma_CS2_RENAN\user_settings.json
# Linux
rm Programma_CS2_RENAN/user_settings.json
```
O assistente de configuracao aparecera novamente na proxima execucao.

### Onde meus bancos de dados estao armazenados?

| Banco de Dados | Localizacao | Conteudo |
|----------------|-------------|----------|
| BD Principal | `Programma_CS2_RENAN/backend/storage/database.db` | Estatisticas de jogadores, estado do coaching, dados de treinamento |
| BD HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadados de jogadores profissionais (separado do treinamento) |
| BD de Conhecimento | `Programma_CS2_RENAN/data/knowledge_base.db` | Base de conhecimento RAG |
| BDs de Partidas | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dados tick-a-tick por partida |

---

## Referencia Rapida

| Acao | Como |
|------|------|
| Iniciar o aplicativo | `python Programma_CS2_RENAN/main.py` |
| Re-executar o assistente | Delete `user_settings.json`, reinicie |
| Alterar pasta de demos | Configuracoes (Settings) > Caminhos de Analise (Analysis Paths) > Change |
| Adicionar chave Steam | Tela Inicial (Home) > Personalizacao (Personalization) > Steam |
| Adicionar chave FaceIT | Tela Inicial (Home) > Personalizacao (Personalization) > FaceIT |
| Iniciar ingestao | Tela Inicial (Home) > Hub de Ingestao Pro (Pro Ingestion Hub) > Botao Play |
| Ver replay de partida | Tela Inicial (Home) > Launch Viewer |
| Perguntar ao coach de IA | Tela do Coach (Coach Screen) > Chat toggle > Digitar pergunta |
| Alterar tema | Configuracoes (Settings) > Tema Visual (Visual Theme) |
| Alterar idioma | Configuracoes (Settings) > Idioma (Language) |

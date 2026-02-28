# Macena CS2 Analyzer

**Coach Tatico com IA para Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## O Que E Isso?

Macena CS2 Analyzer e uma aplicacao desktop que funciona como um coach pessoal de IA para Counter-Strike 2. Ele analisa arquivos demo profissionais e do usuario, treina multiplos modelos de redes neurais e entrega coaching tatico personalizado comparando sua gameplay com padroes profissionais.

O sistema aprende com as melhores partidas profissionais ja jogadas e adapta seu coaching ao seu estilo de jogo individual — seja voce um AWPer, entry fragger, support ou qualquer outro papel.

---

## Funcionalidades Principais

- **Pipeline de Coaching IA** — Cadeia de fallback de 4 niveis (COPER > Hibrido > RAG > Base) que funde previsoes ML com conhecimento tatico recuperado
- **6 Subsistemas de IA** — Encoder JEPA, alinhamento visao-linguagem VL-JEPA, RAP Coach (arquitetura de 6 camadas com memoria LTC-Hopfield), LSTM+MoE, Neural Role Head, modelos bayesianos de crenca
- **Motor Tri-Daemon** — Automacao em background com daemons Hunter (scanner de arquivos), Digester (processador de demos) e Teacher (treinador de modelos)
- **Observatorio de Introspeccao do Coach** — Integracao TensorBoard com maquina de estados de maturidade, projetor de embeddings e rastreamento de conviccao
- **Analise de Demos** — Parsing a nivel de tick dos arquivos `.dem` via demoparser2, com calculo de rating HLTV 2.0, detalhamento por round e rastreamento de momentum
- **Analise de Teoria dos Jogos** — Arvores expectiminimax, estimativa bayesiana de probabilidade de morte, indice de engano, analise de distancia de engajamento
- **App Desktop** — Interface Kivy + KivyMD com visualizador tatico 2D, historico de partidas, dashboard de performance, chat com coach e graficos radar
- **Inteligencia Espacial** — Suporte a mapas multi-nivel (Nuke, Vertigo), mapeamento de coordenadas com precisao de pixel, tratamento de Z-cutoff
- **Gating de Maturidade em 3 Estagios** — Modelos progridem por CALIBRACAO > APRENDIZADO > MADURO com quality gates automaticos
- **Banco de Experiencias COPER** — Armazena e recupera experiencias de coaching passadas ponderadas por recencia, eficacia e similaridade de contexto
- **Decaimento Temporal da Baseline** — Rastreia a evolucao das habilidades do jogador ao longo do tempo com pesos de decaimento exponencial
- **Integracao Ollama** — LLM local opcional para refinamento em linguagem natural dos insights de coaching

---

## Requisitos do Sistema

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| OS | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 ou 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nenhuma (modo CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disco | 3 GB livres | 5 GB livres |
| Display | 1280x720 | 1920x1080 |

---

## Inicio Rapido

### 1. Clone

```bash
git clone https://github.com/renanaugustomacena-ux/Macena_cs2_analyzer.git
cd Macena_cs2_analyzer
```

### 2. Setup Automatizado (Windows)

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Cria um ambiente virtual, instala todas as dependencias, inicializa o banco de dados e configura o Playwright para scraping HLTV.

**Para suporte a GPU NVIDIA**, apos o script completar:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Setup Manual

```bash
python -m venv venv_win
# Windows:
.\venv_win\Scripts\activate
# Linux:
source venv_win/bin/activate

pip install -r requirements.txt
python -c "from backend.storage.database import init_db; init_db()"
playwright install chromium
```

### 4. Execute

```bash
# Aplicacao desktop (GUI Kivy)
python Programma_CS2_RENAN/apps/desktop_app/main.py

# Console interativo (TUI live com paineis em tempo real)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Para o guia completo com configuracao de API, walkthroughs das funcionalidades e troubleshooting, consulte o [Guia do Usuario](docs/USER_GUIDE_PT.md).

---

## Visao Geral da Arquitetura

O sistema e organizado em 6 subsistemas de IA trabalhando como um pipeline unificado:

```
OBSERVA (Ingestao)  -->  APRENDE (Treinamento)  -->  PENSA (Inferencia)  -->  FALA (Dialogo)
    Daemon Hunter          Daemon Teacher               Pipeline COPER         Template + Ollama
    Parsing de demo        Maturidade em 3 estagios     Conhecimento RAG       Atribuicao causal
    Extracao de features   Treinamento multi-modelo      Teoria dos jogos       Comparacoes com pros
```

### Stack Tecnologico

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3.10+ |
| UI | Kivy + KivyMD |
| ML | PyTorch, ncps (LTC), redes Hopfield |
| Banco de Dados | SQLite (modo WAL) |
| Migracoes | Alembic |
| Scraping | Playwright |
| Observabilidade | TensorBoard, Sentry |

### Estrutura do Projeto

```
Programma_CS2_RENAN/
  apps/desktop_app/     UI Kivy (padrao MVVM)
  backend/
    analysis/           Teoria dos jogos, modelos de crenca, momentum
    data_sources/       Parser de demo, metadados HLTV
    nn/                 Redes neurais (RAP Coach, JEPA, VL-JEPA)
      rap_coach/        Modelo RAP de 6 camadas com memoria LTC-Hopfield
    processing/         Feature engineering, heatmaps, validacao
    knowledge/          Base de conhecimento RAG, banco de experiencias COPER
    services/           Servico de coaching, integracao Ollama
    storage/            Modelos DB, migracoes, backup
  core/                 Asset manager, map manager, session engine
  ingestion/            Localizador Steam, verificacoes de integridade
  observability/        RASP, telemetria
  reporting/            Visualizador, geradores de PDF
docs/                   Guias do usuario (EN/IT/PT), estudos tecnicos
tools/                  Suite de validacao, diagnosticos, ferramentas de auditoria
```

---

## Validacao e Qualidade

O projeto mantem uma hierarquia de validacao em multiplos niveis:

| Ferramenta | Escopo | Comando |
|------------|--------|---------|
| Headless Validator | Gate de regressao (79 checks) | `python tools/headless_validator.py` |
| Suite Pytest | Testes logicos (390+ testes) | `python -m pytest tests/ -x -q` |
| Backend Validator | Saude do build (40 checks) | `python tools/backend_validator.py` |
| Goliath Hospital | Diagnostico completo | `python tools/Goliath_Hospital.py` |

---

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [Guia do Usuario](docs/USER_GUIDE_PT.md) | Guia completo de instalacao e uso |
| [User Guide (EN)](docs/USER_GUIDE.md) | Complete installation and usage guide |
| [Guida Utente (IT)](docs/USER_GUIDE_IT.md) | Guida completa installazione e utilizzo |
| [Arquitetura do Projeto](docs/Progetto-Renan-Cs2-AI-Coach.md) | Arquitetura completa do sistema (Italiano) |
| [Estudos Tecnicos](docs/Studies/) | 17 papers de pesquisa aprofundados |
| [Analise JEPA](jepa.md) | Analise aprofundada da arquitetura JEPA |
| [Arquitetura do Console](CONSOLE_ARCHITECTURE.md) | Design do console de controle |
| [Relatorio de Auditoria](MASTER_AUDIT_REPORT.md) | Auditoria final: 59 encontrados, 56 resolvidos |
| [Changelog](CHANGELOG.md) | Historico de versoes |

---

## Licenca

Este projeto possui licenca dupla. Copyright (c) 2025-2026 Renan Augusto Macena.

Voce pode escolher entre:
- **Licenca Proprietaria** — Todos os direitos reservados (padrao). Visualizacao para fins educacionais e permitida.
- **Apache License 2.0** — Open source permissiva com protecao de patentes.

Consulte [LICENSE](LICENSE) para os termos completos.

---

## Autor

**Renan Augusto Macena**

Construido com paixao por um jogador de Counter-Strike com mais de 10.000 horas desde 2004, combinando profundo conhecimento do jogo com engenharia de IA para criar o sistema de coaching definitivo.

> *"Eu sempre quis um guia profissional — como os que os verdadeiros jogadores profissionais tem — para entender como realmente e quando alguem treina do jeito certo e joga do jeito certo."*

---

# Guia do Usuario

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
13. [Alimentando o Coach: Guia de Aquisicao de Demos e Gerenciamento de Armazenamento](#13-alimentando-o-coach-guia-de-aquisicao-de-demos-e-gerenciamento-de-armazenamento)
14. [Solucao de Problemas](#14-solucao-de-problemas)

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

## 13. Alimentando o Coach: Guia de Aquisicao de Demos e Gerenciamento de Armazenamento

O coach de IA vem **sem nenhum conhecimento pre-treinado**. Ele aprende exclusivamente a partir de arquivos demo de partidas profissionais de CS2 (`.dem`). A qualidade e profundidade do coaching que voce recebe e diretamente proporcional a qualidade e quantidade de demos que voce importa. Sem demos, as telas de coaching exibirao "Calibrating" e a maioria das funcoes de coaching permanecera inativa.

Esta secao explica como adquirir arquivos demo, quantos voce precisa e como planejar seu armazenamento.

### 13.1 Por que o Coach Comeca Vazio

Diferente de ferramentas de coaching tradicionais que vem com dicas estaticas, o Macena CS2 Analyzer constroi sua inteligencia a partir de **gameplay profissional real**. Na primeira execucao:

- As redes neurais (RAP Coach, JEPA, Belief Model) tem pesos aleatorios sem nenhum conhecimento tatico
- O pipeline de coaching nao tem nenhuma referencia profissional para comparar seu gameplay
- O banco de experiencias e o sistema de conhecimento RAG estao vazios

Isso e por design. O coach aprende com dados reais de partidas profissionais, nao com conselhos sinteticos ou pre-fabricados. Quanto mais demos de alta qualidade voce fornecer, mais refinado e preciso o coaching se torna.

### 13.2 Como Baixar Demos Pro do HLTV.org

Siga estes passos para construir sua biblioteca de demos profissionais:

1. Va ate [hltv.org](https://www.hltv.org) e navegue ate **Results** (Resultados)
2. Filtre por **eventos top-tier**: Major Championships, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Selecione partidas envolvendo **times do top-20** (ex. Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefira **series BO3 ou BO5** — mais rounds por download significa mais dados de treinamento por arquivo
5. Na pagina da partida, clique em **"Watch Demo"** (ou "GOTV Demo") para baixar o arquivo `.dem`
6. **Diversifique os mapas** — cubra todos os mapas do Active Duty (Mirage, Inferno, Nuke, Ancient, Anubis, Dust2, Vertigo). Baixar 50 demos do mesmo mapa criara um coach tendencioso
7. **Escolha com cuidado** — selecione as melhores partidas: finais de torneio, partidas eliminatorias de playoff e Grand Finals. Estas contem a maior profundidade tatica

**O que evitar:**
- Showmatches e partidas de exibicao (baixa intensidade tatica)
- Qualificatorias com times desconhecidos/amadores (qualidade inconsistente)
- Eventos beneficentes ou partidas entre criadores de conteudo
- Demos muito antigas (mudancas no meta as tornam menos relevantes)

**Eventos recomendados (maxima qualidade):**
- CS2 Major Championships (qualquer ano)
- IEM Katowice, IEM Cologne
- BLAST World Final, BLAST Premier
- ESL Pro League Finals
- PGL Major series

### 13.3 Quantas Demos Baixar

Quanto mais demos voce importar, melhor seu coach se torna. Aqui estao os niveis de coaching:

| Demos Pro Importadas | Nivel de Coaching | Confianca | Comportamento do Coach |
|---------------------|-------------------|-----------|----------------------|
| **0 - 9** | Nao pronto | 0% | Coach inativo. Minimo de 10 demos pro necessarias para iniciar o primeiro ciclo de treinamento. |
| **10 - 49** | CALIBRATING | 50% | Coaching basico ativo. Conselhos marcados como provisorios. |
| **50 - 199** | LEARNING | 80% | Coaching intermediario. Confianca crescente, cada vez mais confiavel. |
| **200+** | MATURE | 100% | Confianca total. Coaching production-ready com maxima precisao. |

**Limites-chave:**
- **10 demos pro**: O primeiro ciclo de treinamento e acionado automaticamente. Este e o minimo absoluto.
- **Crescimento de 10%**: Apos o primeiro ciclo, o retreinamento e acionado automaticamente cada vez que sua contagem de demos pro cresce 10% (ex. 10 → 11, 50 → 55, 100 → 110).
- **50 demos**: Minimo recomendado para coaching significativo e acionavel.
- **200+ demos**: Meta para coaching maduro e de alta confianca em todos os mapas e cenarios.

**A regra de ouro: mais demos = coach melhor.** Baixe o maximo de demos pro de alta qualidade que puder. Nao ha limite superior — o sistema melhora continuamente com mais dados.

### 13.4 Gates de Maturidade Explicados

Dois sistemas de maturidade operam em paralelo:

**A. Niveis baseados na Contagem de Demos** (principal, visivel no app)

Estes niveis sao baseados no numero bruto de demos pro importadas (veja tabela na secao 13.3). Eles controlam diretamente o multiplicador de confianca aplicado a todos os conselhos de coaching.

**B. Conviction Index** (avancado, visivel via TensorBoard)

Durante o treinamento, a IA rastreia um indice composto de "conviccao" (0.0 a 1.0) calculado a partir de cinco sinais neurais: entropia das crencas (belief entropy), especializacao dos gates, foco conceitual, precisao de valor e estabilidade de funcao.

| Estado | Conviction Index | O que Significa |
|--------|-----------------|-----------------|
| **DOUBT** | < 0.30 | Modelo incerto. Crencas ruidosas, especialistas nao especializados. |
| **LEARNING** | 0.30 - 0.60 | Formacao ativa de crencas. Especialistas comecando a se diferenciar. |
| **CONVICTION** | > 0.60 (estavel por 10+ epocas) | Crencas fortes e consistentes entre os lotes de treinamento. |
| **MATURE** | > 0.75 (estavel por 20+ epocas) | Modelo convergido. Inferencia production-ready. |
| **CRISIS** | Queda brusca > 20% | Anomalia detectada (overfitting ou mudanca na distribuicao dos dados). Investigacao necessaria. |

O conviction index fornece uma compreensao mais profunda do estado interno da IA, alem da simples contagem de demos. Voce pode monitora-lo em tempo real via TensorBoard (veja secao 13.6).

### 13.5 Planejamento de Armazenamento

Arquivos `.dem` sao **pesados** — tipicamente de 300 a 850 MB cada. Conforme voce constroi sua biblioteca de demos, os requisitos de espaco crescem significativamente. Planeje com antecedencia.

**Estimativas de Espaco:**

| Demos Pro | Arquivos .dem Raw | Bancos de Dados Match | Estimativa Total |
|-----------|------------------|----------------------|-----------------|
| 10 | ~5 GB | ~1 GB | **~6 GB** |
| 50 | ~30 GB | ~5 GB | **~35 GB** |
| 100 | ~60 GB | ~10 GB | **~70 GB** |
| 200 | ~120 GB | ~20 GB | **~140 GB** |

**Recomendacoes:**

- **Use um drive separado** com bastante espaco livre para sua Pro Demo Folder. Um HDD serve perfeitamente para armazenamento de demos; SSD e preferivel para o Brain Data Root (modelos de IA e treinamento)
- **Crie uma pasta dedicada** (ex. `D:\CS2_Pro_Demos\`) ANTES de comecar a baixar demos
- Configure este caminho em **Configuracoes (Settings) > Analysis Paths > Pro Demo Folder**
- Se armazenar demos no **mesmo drive** do programa, garanta pelo menos **50 GB de espaco livre** alem das necessidades do sistema operacional e aplicativos
- A pasta `match_data/` (bancos de dados SQLite por partida) e criada automaticamente junto a sua Pro Demo Folder
- O sistema **NAO** exclui demos antigas automaticamente — monitore o espaco do seu drive periodicamente

**Por que tres locais de armazenamento separados?**

| Local | O que Armazena | Onde Colocar |
|-------|---------------|-------------|
| **Core Database** (pasta do programa) | Estatisticas do jogador, estado do coaching, metadados HLTV | Sempre permanece na pasta do programa. Portatil. |
| **Brain Data Root** (Assistente de Configuracao) | Pesos dos modelos de IA, logs, base de conhecimento, cache | SSD recomendado para treinamento mais rapido. |
| **Pro Demo Folder** (Configuracoes) | Arquivos .dem raw + bancos de dados SQLite por partida | Necessita de mais espaco. HDD aceitavel. |

### 13.6 Monitoramento TensorBoard

Voce pode monitorar o progresso de treinamento do coach e a maturidade em tempo real usando TensorBoard.

**Iniciar TensorBoard:**
```bash
tensorboard --logdir runs/coach_training
```

Depois abra [http://localhost:6006](http://localhost:6006) no seu navegador.

**Metricas-chave para monitorar:**
- **`maturity/conviction_index`** (Scalars): Deve tender para cima ao longo das epocas de treinamento
- **`maturity/state`** (Text): Rastreia transicoes atraves de doubt → learning → conviction → mature
- **`maturity/gate_specialization`** (Scalars): Valores mais altos significam que a rede de especialistas esta se especializando mais
- **`loss/train`** e **`loss/val`** (Scalars): Curvas de perda de treinamento e validacao — ambas devem diminuir
- **`gates/mean_activation`** (Scalars): Roteamento de gates na camada mixture-of-experts

TensorBoard e opcional, mas altamente recomendado para usuarios que querem entender como seu coach esta evoluindo.

### 13.7 Primeiro Ciclo de Coaching: Checklist Passo a Passo

Siga esta checklist da instalacao ate seu primeiro conselho de coaching:

1. **Instale** o aplicativo e complete o **Assistente de Configuracao** (configure seu Brain Data Root)
2. Va em **Configuracoes (Settings) > Analysis Paths** e defina sua **Pro Demo Folder** para um drive/pasta dedicada com bastante espaco
3. **Baixe pelo menos 10 demos pro** do HLTV.org (mapas diversificados!)
4. **Coloque os arquivos `.dem`** na Pro Demo Folder configurada
5. **Inicie o app** — o daemon Hunter descobre automaticamente novos arquivos demo
6. **Aguarde a importacao** — cada demo leva aproximadamente 5-10 minutos para processar. Monitore o progresso na Tela Inicial (Home Screen)
7. Apos **10 demos pro serem importadas**, o daemon Teacher inicia automaticamente o **primeiro ciclo de treinamento**
8. *(Opcional)* **Monitore a maturidade** via TensorBoard para ver o conviction index subir
9. **Conecte sua conta Steam** (Home > Personalizacao > Steam ID)
10. **Jogue 10+ partidas competitivas** — suas demos pessoais sao localizadas automaticamente via integracao Steam
11. Uma vez que voce tenha **10+ demos pessoais E 10+ demos pro**, o pipeline de coaching completo se ativa!

### 13.8 Solucao de Problemas: Espaco em Disco

- **Drive cheio?** Mova sua Pro Demo Folder para um drive maior via Configuracoes (Settings). O diretorio `match_data/` migra automaticamente.
- **Banco de dados crescendo muito rapido?** Os arquivos SQLite por partida em `match_data/` podem ser excluidos individualmente para partidas antigas que voce nao precisa mais revisar em detalhe.
- **Quer economizar espaco mantendo o coaching?** Os arquivos `.dem` podem ser excluidos apos a importacao — todos os dados necessarios sao extraidos para os bancos de dados de partida durante o processamento. Porem, manter os arquivos `.dem` originais permite re-importacao futura caso o parser de demos seja atualizado.
- **Cache ocupando espaco?** O cache de importacao em `ingestion/cache/` pode ser limpo com seguranca. As demos serao re-analisadas a partir dos arquivos `.dem` originais no proximo acesso.

---

## 14. Solucao de Problemas

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

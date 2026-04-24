# Macena CS2 Analyzer

[![CI Pipeline](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml/badge.svg)](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary%20%7C%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-313%20validator%20%7C%201794%20pytest-brightgreen.svg)]()

**Coach Tatico com IA para Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## O Que E?

Macena CS2 Analyzer e uma aplicacao desktop que funciona como seu coach pessoal de IA para Counter-Strike 2. Analisa arquivos demo profissionais e do usuario, treina multiplos modelos de redes neurais e fornece coaching tatico personalizado comparando seu gameplay com padroes profissionais.

O sistema aprende com as melhores partidas profissionais ja jogadas e adapta seu coaching ao seu estilo de jogo individual -- seja voce um AWPer, entry fragger, support ou qualquer outro papel. A pipeline de coaching funde previsoes de machine learning com conhecimento tatico recuperado, analise baseada em teoria dos jogos e modelagem bayesiana de crencas para produzir conselhos acionaveis e context-aware.

Diferente de ferramentas de coaching estaticas com dicas pre-escritas, este sistema constroi sua inteligencia a partir de dados reais de gameplay profissional. Na primeira inicializacao, as redes neurais tem pesos aleatorios e zero conhecimento tatico. Cada demo que voce fornece torna o coach mais inteligente, mais refinado e mais personalizado.

---

## Indice

- [Funcionalidades Principais](#funcionalidades-principais)
- [Requisitos de Sistema](#requisitos-de-sistema)
- [Inicio Rapido](#inicio-rapido)
- [Visao Geral da Arquitetura](#visao-geral-da-arquitetura)
- [Mapas Suportados](#mapas-suportados)
- [Stack Tecnologico](#stack-tecnologico)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pontos de Entrada](#pontos-de-entrada)
- [Validacao e Qualidade](#validacao-e-qualidade)
- [Suporte Multi-Idioma](#suporte-multi-idioma)
- [Funcionalidades de Seguranca](#funcionalidades-de-seguranca)
- [Ajuste de Desempenho](#ajuste-de-desempenho)
- [Maturidade do Sistema](#maturidade-do-sistema)
- [Documentacao](#documentacao)
- [Alimentando o Coach](#alimentando-o-coach)
- [Solucao de Problemas](#solucao-de-problemas)
- [Indice Completo da Documentacao](#indice-completo-da-documentacao)
- [Licenca](#licenca)
- [Autor](#autor)

---

## Funcionalidades Principais

### Pipeline de Coaching IA

- **Cadeia de Fallback de 4 Niveis** -- COPER > Hibrido > RAG > Base, garantindo que o sistema sempre produza conselhos uteis independente da maturidade do modelo
- **COPER Experience Bank** -- Armazena e recupera experiencias de coaching passadas ponderadas por recencia, eficacia e similaridade de contexto
- **Base de Conhecimento RAG** -- Retrieval-Augmented Generation com padroes de referencia profissionais e conhecimento tatico
- **Integracao Ollama** -- LLM local opcional para refinamento em linguagem natural dos insights de coaching
- **Atribuicao Causal** -- Cada recomendacao de coaching inclui uma explicacao "por que" rastreavel a decisoes especificas de gameplay

### Subsistemas de Redes Neurais

- **RAP Coach** -- Arquitetura de 7 camadas combinando percepcao, memoria (LTC-Hopfield), estrategia (Mixture-of-Experts com superposicao), pedagogia (value function), predicao de posicao, atribuicao causal e agregacao de saida
- **Encoder JEPA** -- Joint-Embedding Predictive Architecture para pre-treinamento auto-supervisionado com loss contrastiva InfoNCE e target encoder EMA
- **VL-JEPA** -- Extensao Vision-Language com alinhamento de 16 conceitos taticos (posicionamento, utility, economia, engagement, decisao, psicologia)
- **AdvancedCoachNN** -- Arquitetura LSTM + Mixture-of-Experts para predicao de pesos de coaching
- **Neural Role Head** -- Classificador MLP de 5 papeis (entry, support, lurk, AWP, anchor) com KL-divergence e consensus gating
- **Modelos Bayesianos de Crencas** -- Rastreamento do estado mental do oponente com calibracao adaptativa dos dados da partida

### Analise de Demos

- **Parsing a Nivel de Tick** -- Cada tick dos arquivos `.dem` e analisado via demoparser2, preservando todo o estado do jogo (sem decimacao de ticks)
- **Rating HLTV 2.0** -- Calculado por partida usando a formula oficial HLTV 2.0 (kills, mortes, ADR, KAST%, sobrevivencia, assists de flash)
- **Analise Round por Round** -- Timeline de economia, analise de engajamentos, uso de utilitarios, rastreamento de momentum
- **Decaimento Temporal da Baseline** -- Rastreia a evolucao de habilidade do jogador ao longo do tempo com pesos de decaimento exponencial

### Analise baseada em Teoria dos Jogos

- **Arvores Expectiminimax** -- Avaliacao decisional game-theoretic para cenarios estrategicos
- **Probabilidade de Morte Bayesiana** -- Estima a probabilidade de sobrevivencia baseada em posicao, equipamento e estado inimigo
- **Indice de Engano** -- Quantifica a imprevisibilidade posicional em relacao as baselines profissionais
- **Analise de Alcance de Engajamento** -- Mapeia selecao de armas contra distribuicoes de distancia de engajamento
- **Probabilidade de Vitoria** -- Calculo de probabilidade de vitoria em tempo real
- **Rastreamento de Momentum** -- Trajetoria de confianca e desempenho round por round

### Aplicacao Desktop

- **Aplicativo Desktop Qt** -- Frontend PySide6/Qt (primario) com padrao MVVM. Kivy/KivyMD legacy mantido apenas como referencia
- **Visualizador Tatico 2D** -- Replay de demo em tempo real com posicoes de jogadores, eventos de kill, indicadores de bomba e predicoes AI ghost
- **Historico de Partidas** -- Lista rolavel de partidas recentes com ratings codificados por cor
- **Dashboard de Desempenho** -- Tendencias de rating, estatisticas por mapa, analise de forcas/fraquezas, analise de utilitarios
- **Chat com o Coach** -- Conversa IA interativa com botoes de acao rapida e perguntas em texto livre
- **Perfil do Usuario** -- Integracao Steam com importacao automatica de partidas
- **3 Temas Visuais** -- CS2 (laranja), CS:GO (azul-cinza), CS 1.6 (verde) com wallpapers rotativos

### Treinamento e Automacao

- **4-Daemon Session Engine** -- Scanner (descoberta de arquivos), Digester (processamento de demos), Teacher (treinamento de modelos), Pulse (monitoramento de saude)
- **Gating de Maturidade de 3 Estagios** -- CALIBRATING (0-49 demos, 0.5x confianca) > LEARNING (50-199, 0.8x) > MATURE (200+, total)
- **Conviction Index** -- Composto de 5 sinais rastreando entropia de crencas, especializacao de gate, foco conceitual, precisao de valor e estabilidade de papel
- **Auto-Retraining** -- O treinamento e acionado automaticamente com 10% de crescimento na contagem de demos
- **Deteccao de Drift** -- Monitoramento de drift de features baseado em Z-score com flag automatico de retreinamento
- **Coach Introspection Observatory** -- Integracao TensorBoard com maquina de estados de maturidade, projetor de embedding e rastreamento de conviccao

---

## Requisitos de Sistema

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| SO | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 ou 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nenhuma (modo CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disco | 3 GB livres | 5 GB livres |
| Display | 1280x720 | 1920x1080 |

---

## Inicio Rapido

### 1. Clone

```bash
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
```

### 2. Setup Automatizado (Windows)

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Cria um ambiente virtual, instala todas as dependencias, inicializa o banco de dados e configura o Playwright para scraping HLTV.

**Para suporte GPU NVIDIA**, apos o script completar:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Setup Manual (Windows)

```powershell
python -m venv venv_win
.\venv_win\Scripts\activate

# PyTorch (escolha UM):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # Apenas CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # GPU NVIDIA

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 4. Setup Manual (Linux)

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev libsdl2-dev libglew-dev build-essential

python3.10 -m venv venv_linux
source venv_linux/bin/activate

# PyTorch (escolha UM):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # Apenas CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # GPU NVIDIA

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Configurar Ambiente

```bash
cp .env.example .env
# Edite .env com sua chave Steam API e preferencias (veja os comentarios no arquivo)
```

### 6. Verificar Instalacao

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 7. Opcional: Baseline de Coaching Pro

Para construir baselines de coaching a partir de dados de partidas profissionais, dois componentes adicionais sao necessarios:

**Docker + FlareSolverr** (para scraping automatizado de stats pro HLTV):

```bash
# Instale Docker Desktop: https://docs.docker.com/desktop/
# Em seguida inicie o FlareSolverr:
docker compose up -d
```

FlareSolverr contorna a protecao Cloudflare em hltv.org. Sem ele, o daemon Hunter nao pode raspar estatisticas de jogadores profissionais. Voce ainda pode usar o coach com seus proprios arquivos demo -- baselines pro melhoram a qualidade do coaching mas nao sao obrigatorias.

**Dependencias RAP Coach** (arquitetura experimental opcional):

```bash
pip install -r requirements-rap.txt
```

Necessario apenas se voce ativar `USE_RAP_MODEL=True` nas configuracoes. O modelo JEPA padrao funciona sem essas dependencias.

### 8. Iniciar

```bash
# Aplicacao desktop (GUI Qt -- recomendado)
./launch.sh

# Ou manualmente:
python -m Programma_CS2_RENAN.apps.qt_app.app

# Console interativo (TUI live com paineis em tempo real)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Para o guia completo com configuracao de API, walkthroughs de funcionalidades e solucao de problemas, consulte o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Visao Geral da Arquitetura

### Pipeline OBSERVE > APRENDA > PENSE > FALE

O sistema e organizado como uma pipeline de 4 estagios que transforma arquivos demo brutos em coaching personalizado:

```
OBSERVE (Ingestao)     APRENDA (Treinamento)  PENSE (Inferencia)      FALE (Dialogo)
  Daemon Scanner         Daemon Teacher         Pipeline COPER          Template + Ollama
  Parsing de demo        Maturidade 3 estagios  Conhecimento RAG        Atribuicao causal
  Extracao de features   Training multi-modelo   Teoria dos jogos        Comparacoes pro
  Armazenamento tick     Deteccao de drift       Modelagem de crencas    Scoring de gravidade
```

**OBSERVE** -- O daemon Scanner monitora continuamente as pastas de demo configuradas para novos arquivos `.dem`. Quando encontrados, o daemon Digester analisa cada tick usando demoparser2, extrai o vetor canonico de features de 25 dimensoes, calcula os ratings HLTV 2.0 e armazena tudo em bancos de dados SQLite por partida.

**APRENDA** -- O daemon Teacher treina automaticamente os modelos neurais quando dados suficientes se acumulam. O treinamento progride atraves de 3 estagios de maturidade (CALIBRATING > LEARNING > MATURE). Multiplas arquiteturas treinam em paralelo: JEPA para aprendizado auto-supervisionado de representacoes, RAP Coach para modelagem de decisoes taticas, NeuralRoleHead para classificacao de papel dos jogadores.

**PENSE** -- No tempo de inferencia, a pipeline COPER combina previsoes neurais com experiencias de coaching recuperadas, conhecimento RAG e analise de teoria dos jogos. Uma cadeia de fallback de 4 niveis (COPER > Hibrido > RAG > Base) garante que conselhos estejam sempre disponiveis independente da maturidade do modelo.

**FALE** -- A saida final de coaching e formatada com niveis de gravidade, atribuicao causal ("por que este conselho") e opcionalmente refinada atraves de um LLM local Ollama para qualidade de linguagem natural.

### 4-Daemon Session Engine

| Daemon | Papel | Gatilho |
|--------|-------|---------|
| **Scanner (Hunter)** | Descobre novos arquivos `.dem` nas pastas configuradas | Varredura periodica ou file watcher |
| **Digester** | Analisa demos, extrai features, calcula ratings | Novo arquivo detectado pelo Scanner |
| **Teacher** | Treina modelos neurais nos dados acumulados | Limiar de crescimento de 10% na contagem de demos |
| **Pulse** | Monitoramento de saude, deteccao de drift, estado do sistema | Continuo em background |

### Pipeline de Coaching COPER

COPER (Coaching via Organized Pattern Experience Retrieval) e o motor de coaching principal. Opera uma cadeia de fallback de 4 niveis:

1. **Modo COPER** -- Pipeline completa: recuperacao Experience Bank + conhecimento RAG + previsoes de modelo neural + comparacoes profissionais. Requer modelos treinados.
2. **Modo Hibrido** -- Combina previsoes neurais com conselhos baseados em template quando alguns modelos ainda estao em calibracao.
3. **Modo RAG** -- Recuperacao pura: busca padroes de coaching relevantes na knowledge base sem inferencia neural. Funciona apenas com demos ingeridos.
4. **Modo Base** -- Conselhos baseados em template da analise estatistica (desvios media/std das baselines profissionais). Funciona imediatamente.

### Arquiteturas de Redes Neurais

**RAP Coach (Arquitetura de 7 Camadas)**

O RAP (Reasoning, Attribution, Prediction) Coach e o modelo neural principal. Suas 7 camadas processam dados de gameplay atraves de uma pipeline cognitiva:

| Camada | Funcao | Detalhes |
|--------|--------|----------|
| 1. Percepcao | Codificacao visual + espacial | Camadas Conv para frame de visao (64d), estado do mapa (32d), diff de movimento (32d) -> 128d |
| 2. Memoria | Rastreamento recorrente de crencas | LSTM + rede Hopfield para memoria associativa. Entrada: 153d (128 percepcao + 25 metadata) -> 256d estado oculto |
| 3. Estrategia | Otimizacao de decisao | Mixture-of-Experts com superposicao para decisoes dependentes de contexto. 10 pesos de acao |
| 4. Pedagogia | Estimacao de valor | Estimacao de V-function com integracao de vetor de skill |
| 5. Posicao | Posicionamento otimo | Preve delta (dx, dy, dz) para posicao otima (escala: 500 unidades de mundo) |
| 6. Atribuicao | Diagnostico causal | Atribuicao 5-dimensional explicando os drivers da decisao |
| 7. Saida | Agregacao | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution |

**JEPA (Joint-Embedding Predictive Architecture)**

Pre-treinamento auto-supervisionado com:
- Context encoder + predictor -> preve o embedding do target
- Target encoder atualizado via EMA (momentum 0.996 base, schedulado com coseno)
- Loss contrastiva InfoNCE com negativos in-batch
- Dimensao latente: 128

**VL-JEPA (Extensao Vision-Language)**

Estende JEPA com alinhamento de 16 conceitos taticos:
- Conceitos: posicionamento (3), utility (2), economia (2), engagement (4), decisao (2), psicologia (3)
- Loss de alinhamento conceitual + regularizacao de diversidade
- Labeling baseado em outcome a partir do RoundStats (kills, mortes, equipamento, resultado do round)

**Outros Modelos:**
- **AdvancedCoachNN** -- LSTM (hidden=128) + Mixture-of-Experts (4 experts, top-k=2) para predicao de pesos de coaching
- **NeuralRoleHead** -- Classificador MLP de 5 papeis com gating KL-divergence e votacao por consenso
- **RoleClassifier** -- Deteccao leve de papel a partir de features de tick

### Vetor de Features de 25 Dimensoes

Cada tick de jogo e representado como um vetor canonico de 25 dimensoes (`METADATA_DIM=25`):

| Indice | Feature | Faixa | Descricao |
|--------|---------|-------|-----------|
| 0 | health | [0, 1] | HP / 100 |
| 1 | armor | [0, 1] | Armor / 100 |
| 2 | has_helmet | {0, 1} | Capacete equipado |
| 3 | has_defuser | {0, 1} | Kit de defuse |
| 4 | equipment_value | [0, 1] | Custo de equipamento normalizado |
| 5 | is_crouching | {0, 1} | Postura agachada |
| 6 | is_scoped | {0, 1} | Arma com scope ativa |
| 7 | is_blinded | {0, 1} | Efeito de flash |
| 8 | enemies_visible | [0, 1] | Contagem de inimigos visiveis (normalizada) |
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | Coordenadas de mundo (normalizadas por mapa) |
| 12-13 | view_yaw_sin, view_yaw_cos | [-1, 1] | Angulo de visao (codificacao ciclica) |
| 14 | view_pitch | [-1, 1] | Angulo vertical de visao |
| 15 | z_penalty | [0, 1] | Distintividade vertical (mapas multi-nivel) |
| 16 | kast_estimate | [0, 1] | Razao Kill/Assist/Survive/Trade |
| 17 | map_id | [0, 1] | Hash deterministico do mapa (baseado em MD5) |
| 18 | round_phase | {0, .33, .66, 1} | Pistol / Eco / Force / Full buy |
| 19 | weapon_class | [0, 1] | Knife=0, Pistol=.2, SMG=.4, Rifle=.6, Sniper=.8, Heavy=1 |
| 20 | time_in_round | [0, 1] | Segundos / 115 |
| 21 | bomb_planted | {0, 1} | Flag de bomba plantada |
| 22 | teammates_alive | [0, 1] | Contagem / 4 |
| 23 | enemies_alive | [0, 1] | Contagem / 5 |
| 24 | team_economy | [0, 1] | Dinheiro medio do time / 16000 |

### Gating de Maturidade de 3 Estagios

Os modelos progridem atraves de gates de maturidade baseados na contagem de demos ingeridas:

| Estagio | Contagem de Demos | Confianca | Comportamento |
|---------|-------------------|-----------|---------------|
| **CALIBRATING** | 0-49 | 0.5x | Coaching base, conselhos marcados como provisorios |
| **LEARNING** | 50-199 | 0.8x | Intermediario, confiabilidade crescente |
| **MATURE** | 200+ | 1.0x | Confianca total, todos os subsistemas contribuem |

Um **Conviction Index** paralelo (0.0-1.0) rastreia 5 sinais neurais: entropia de crencas, especializacao de gate, foco conceitual, precisao de valor e estabilidade de papel. Estados: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 estavel por 10+ epocas) > MATURE (>0.75 estavel por 20+ epocas). Uma queda brusca >20% aciona o estado CRISIS.

---

## Mapas Suportados

O sistema suporta todos os 9 mapas competitivos Active Duty com mapeamento de coordenadas pixel-accurate:

| Mapa | Tipo | Calibracao |
|------|------|------------|
| de_mirage | Nivel unico | pos (-3230, 1713), escala 5.0 |
| de_inferno | Nivel unico | pos (-2087, 3870), escala 4.9 |
| de_dust2 | Nivel unico | pos (-2476, 3239), escala 4.4 |
| de_overpass | Nivel unico | pos (-4831, 1781), escala 5.2 |
| de_ancient | Nivel unico | pos (-2953, 2164), escala 5.0 |
| de_anubis | Nivel unico | pos (-2796, 3328), escala 5.22 |
| de_train | Nivel unico | pos (-2477, 2392), escala 4.7 |
| de_nuke | **Multi-nivel** | pos (-3453, 2887), escala 7.0, Z-cutoff -495 |
| de_vertigo | **Multi-nivel** | pos (-3168, 1762), escala 4.0, Z-cutoff 11700 |

Mapas multi-nivel (Nuke, Vertigo) usam cutoffs no eixo Z para separar nivel superior e inferior para renderizacao 2D precisa. A feature z_penalty (indice 15) no vetor de features captura a distintividade vertical para esses mapas.

---

## Stack Tecnologico

### Dependencias Principais

| Categoria | Pacote | Versao | Proposito |
|-----------|--------|--------|-----------|
| **ML Framework** | PyTorch | Ultima | Treinamento e inferencia de redes neurais |
| **Redes Recorrentes** | ncps | Ultima | Redes Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | Ultima | Camadas de rede Hopfield para memoria |
| **Parsing de Demo** | demoparser2 | 0.40.2 | Parsing a nivel de tick de arquivos demo CS2 |
| **Framework UI (primario)** | PySide6 | 6.8+ | GUI desktop cross-platform baseada em Qt |
| **Framework UI (legacy)** | Kivy + KivyMD | 2.3.0 / 1.2.0 | Apenas referencia legacy |
| **ORM de Banco de Dados** | SQLAlchemy + SQLModel | Ultima | Modelos e consultas de banco de dados |
| **Migracoes** | Alembic | Ultima | Migracoes de schema de banco de dados |
| **Web Scraping** | Playwright | 1.57.0 | Browser headless para HLTV |
| **Cliente HTTP** | HTTPX | 0.28.1 | Requisicoes HTTP async |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Ultima | Computacao numerica e analise |
| **Visualizacao** | Matplotlib | Ultima | Geracao de graficos |
| **Grafos** | NetworkX | Ultima | Analise baseada em grafos |
| **Seguranca** | cryptography | 46.0.3 | Criptografia de credenciais |
| **TUI** | Rich | 14.2.0 | UI de terminal para modo console |
| **API** | FastAPI + Uvicorn | 0.40.0 | Servidor API interno |
| **Validacao** | Pydantic | Ultima | Validacao de dados e configuracoes |
| **Testes** | pytest + pytest-cov + pytest-mock | 9.0.2 | Framework de testes e cobertura |
| **Empacotamento** | PyInstaller | 6.17.0 | Distribuicao binaria |
| **Templating** | Jinja2 | 3.1.6 | Renderizacao de templates para relatorios |
| **Parsing HTML** | BeautifulSoup4 + lxml | 4.12.3 | Extracao de conteudo web |
| **Config** | PyYAML | 6.0.3 | Arquivos de configuracao YAML |
| **Imagens** | Pillow | 12.0.0 | Processamento de imagens |
| **Keyring** | keyring | 25.6.0 | Armazenamento seguro de credenciais |

---

## Estrutura do Projeto

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Pacote principal da aplicacao
|   +-- apps/
|   |   +-- qt_app/                     GUI PySide6/Qt (primaria, MVVM + Signals)
|   |   |   +-- app.py                  Ponto de entrada Qt
|   |   |   +-- main_window.py          QMainWindow com navegacao por sidebar
|   |   |   +-- core/                   AppState singleton, ThemeEngine, padrao Worker
|   |   |   +-- screens/               13 telas (home, visualizador tatico, historico de
|   |   |   |                           partidas, detalhe da partida, desempenho, coach,
|   |   |   |                           configuracoes, wizard, ajuda, perfil, config
|   |   |   |                           steam/faceit)
|   |   |   +-- viewmodels/            ViewModels signal-driven (QObject + Signal/Slot)
|   |   |   +-- widgets/               Graficos (radar, momentum, economia, sparkline),
|   |   |                               tatico (widget de mapa, sidebar de jogador, timeline)
|   |   +-- desktop_app/               GUI Kivy/KivyMD (fallback legacy)
|   |       +-- main.py                 Ponto de entrada Kivy
|   |       +-- layout.kv               Definicao de layout KivyMD
|   |       +-- screens/                Classes de tela Kivy
|   |       +-- widgets/                Componentes de widget Kivy
|   |       +-- viewmodels/             ViewModels estilo Kivy
|   |       +-- assets/                 Temas (CS2, CSGO, CS1.6), fontes, imagens de radar
|   |       +-- i18n/                   Traducoes (EN, IT, PT)
|   |
|   +-- backend/
|   |   +-- analysis/                   Teoria dos jogos e analise estatistica
|   |   |   +-- belief_model.py         Rastreamento bayesiano de estado mental do oponente
|   |   |   +-- game_tree.py            Arvores de decisao expectiminimax
|   |   |   +-- momentum.py             Tendencias de momentum e confianca do round
|   |   |   +-- role_classifier.py      Deteccao de papel (entry, support, lurk, AWP, anchor)
|   |   |   +-- blind_spots.py          Consciencia de mapa e fraquezas posicionais
|   |   |   +-- deception_index.py      Metrica de imprevisibilidade posicional
|   |   |   +-- entropy_analysis.py     Quantificacao de aleatoriedade de decisao
|   |   |   +-- engagement_range.py     Analise de distribuicao arma-distancia
|   |   |   +-- utility_economy.py      Eficiencia de gasto de granadas
|   |   |   +-- win_probability.py      Calculo de probabilidade de vitoria em tempo real
|   |   |
|   |   +-- data_sources/              Integracao de dados externos
|   |   |   +-- demo_parser.py          Wrapper demoparser2 (extracao nivel tick)
|   |   |   +-- hltv_scraper.py         Scraping de metadata profissional HLTV
|   |   |   +-- steam_api.py            Perfil Steam e dados de partidas
|   |   |   +-- faceit_api.py           Integracao de dados de partidas FaceIT
|   |   |
|   |   +-- nn/                         Subsistemas de redes neurais
|   |   |   +-- config.py               Config NN global (dimensoes, lr, batch size, device)
|   |   |   +-- jepa_model.py           Encoder JEPA + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         Loop de treinamento JEPA com monitoramento de drift
|   |   |   +-- training_orchestrator.py Orquestracao de treinamento multi-modelo
|   |   |   +-- rap_coach/              Modelo RAP Coach
|   |   |   |   +-- model.py            Arquitetura de 7 camadas
|   |   |   |   +-- trainer.py          Loop de treinamento especifico RAP
|   |   |   |   +-- memory.py           Modulo de memoria LTC + Hopfield
|   |   |   +-- layers/                 Componentes neurais compartilhados
|   |   |       +-- superposition.py    Camada de superposicao dependente de contexto
|   |   |       +-- moe.py             Gating Mixture-of-Experts
|   |   |
|   |   +-- processing/                Feature engineering e processamento de dados
|   |   |   +-- feature_engineering/
|   |   |   |   +-- vectorizer.py       Extracao canonica de feature 25-dim (METADATA_DIM=25)
|   |   |   |   +-- tensor_factory.py   Construcao de tensor visao/mapa para RAP Coach
|   |   |   +-- heatmap/               Geracao de heatmap espacial
|   |   |   +-- validation/            Deteccao de drift, checks de qualidade de dados
|   |   |
|   |   +-- knowledge/                 Gerenciamento de conhecimento
|   |   |   +-- rag_knowledge.py        Recuperacao RAG para padroes de coaching
|   |   |   +-- experience_bank.py      Armazenamento e recuperacao de experiencia COPER
|   |   |
|   |   +-- services/                  Servicos da aplicacao
|   |   |   +-- coaching_service.py     Pipeline de coaching 4-nivel (COPER/Hibrido/RAG/Base)
|   |   |   +-- ollama_service.py       Integracao LLM local para refinamento de linguagem
|   |   |
|   |   +-- storage/                   Camada de banco de dados
|   |       +-- database.py            Gerenciamento de conexao SQLite modo WAL
|   |       +-- db_models.py           Definicoes ORM SQLAlchemy/SQLModel
|   |       +-- backup_manager.py      Backup automatizado do banco de dados
|   |       +-- match_data_manager.py  Gerenciamento de banco SQLite por partida
|   |
|   +-- core/                          Servicos core da aplicacao
|   |   +-- session_engine.py           Engine de 4 daemons (Scanner, Digester, Teacher, Pulse)
|   |   +-- map_manager.py             Carregamento de mapa, calibracao de coordenadas, Z-cutoffs
|   |   +-- asset_manager.py           Resolucao de tema e assets
|   |   +-- spatial_data.py            Sistemas de coordenadas espaciais
|   |
|   +-- ingestion/                     Pipeline de ingestao de demos
|   |   +-- steam_locator.py           Auto-descoberta de caminhos de demo CS2 Steam
|   |   +-- integrity_check.py         Validacao de arquivo demo
|   |
|   +-- observability/                 Monitoramento e seguranca
|   |   +-- rasp.py                    Runtime Application Self-Protection
|   |   +-- telemetry.py              Metricas TensorBoard e rastreamento de conviccao
|   |   +-- logger_setup.py           Logging estruturado (namespace cs2analyzer.*)
|   |
|   +-- reporting/                     Geracao de saida
|   |   +-- visualizer.py             Renderizacao de graficos e diagramas
|   |   +-- pdf_generator.py          Geracao de relatorio PDF
|   |
|   +-- tests/                         Suite de testes (1.794+ testes)
|   +-- data/                          Dados estaticos (knowledge base seed, datasets externos)
|
+-- docs/                              Documentacao
|   +-- USER_GUIDE.md                  Guia completo do usuario (EN)
|   +-- USER_GUIDE_IT.md               Guia do usuario (Italiano)
|   +-- USER_GUIDE_PT.md               Guia do usuario (Portugues)
|   +-- Book-Coach-1A.md               Vision book -- Core neural
|   +-- Book-Coach-1B.md               Vision book -- RAP Coach e fontes de dados
|   +-- Book-Coach-2.md                Vision book -- Servicos e infraestrutura
|   +-- Book-Coach-3.md                Vision book -- Logica do programa e UI
|   +-- cybersecurity.md               Analise de seguranca
|   +-- Studies/                        17 papers de pesquisa
|
+-- tools/                             Ferramentas de validacao e diagnostico
|   +-- headless_validator.py          Gate de regressao primario (313 checks, 24 fases)
|   +-- Feature_Audit.py              Auditoria de feature engineering
|   +-- portability_test.py           Checks de compatibilidade cross-platform
|   +-- dead_code_detector.py         Varredura de codigo nao utilizado
|   +-- dev_health.py                 Saude do ambiente de desenvolvimento
|   +-- verify_all_safe.py            Verificacao de seguranca
|   +-- db_health_diagnostic.py       Diagnostico de saude do banco de dados
|   +-- Sanitize_Project.py           Preparacao para distribuicao
|   +-- build_pipeline.py             Orquestracao de pipeline de build
|
+-- tests/                            Testes de integracao e verificacao
+-- scripts/                          Scripts de setup e deploy
+-- alembic/                          Scripts de migracao de banco de dados
+-- .github/workflows/build.yml       Pipeline CI/CD cross-platform
+-- console.py                        Ponto de entrada TUI interativo
+-- goliath.py                        Orquestrador CLI de producao
+-- run_full_training_cycle.py        Runner de ciclo de treinamento standalone
```

---

## Pontos de Entrada

A aplicacao fornece 4 pontos de entrada para diferentes casos de uso:

### Aplicacao Desktop (GUI Qt -- Primaria)

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

Interface grafica completa com visualizador tatico, historico de partidas, dashboard de desempenho, chat com o coach e configuracoes. Abre em 1280x720. Na primeira inicializacao, um assistente de 4 passos configura o diretorio Brain Data Root.

### Aplicacao Desktop (GUI Kivy -- Legacy)

```bash
python Programma_CS2_RENAN/main.py
```

Interface Kivy/KivyMD original. Mantida como fallback para ambientes onde Qt nao esta disponivel.

### Console Interativo (TUI)

```bash
python console.py
```

UI de terminal com paineis em tempo real para desenvolvimento e controle de runtime. Comandos organizados por subsistema:

| Grupo de Comandos | Exemplos |
|-------------------|----------|
| **ML Pipeline** | `ml start`, `ml stop`, `ml pause`, `ml resume`, `ml throttle 0.5`, `ml status` |
| **Ingestao** | `ingest start`, `ingest stop`, `ingest mode continuous 5`, `ingest scan` |
| **Build & Test** | `build run`, `build verify`, `test all`, `test headless`, `test hospital` |
| **Sistema** | `sys status`, `sys audit`, `sys baseline`, `sys db`, `sys vacuum`, `sys resources` |
| **Config** | `set steam /caminho`, `set faceit KEY`, `set config chave valor` |
| **Servicos** | `svc restart coaching` |

### CLI de Producao (Goliath)

```bash
python goliath.py <comando>
```

Orquestrador master para builds de producao, releases e diagnosticos:

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `build` | Pipeline de build industrial | `--test-only` |
| `sanitize` | Limpa projeto para distribuicao | `--force` |
| `integrity` | Gera manifesto de integridade | |
| `audit` | Verifica dados e features | `--demo <caminho>` |
| `db` | Gerenciamento de schema de banco de dados | `--force` |
| `doctor` | Diagnosticos clinicos | `--department <nome>` |
| `baseline` | Status de decaimento de baseline temporal | |

### Runner de Ciclo de Treinamento

```bash
python run_full_training_cycle.py
```

Script standalone que executa um ciclo de treinamento completo fora do daemon engine. Util para treinamento manual ou debugging.

### Ingestao em Batch

```bash
python batch_ingest.py [--workers N] [--limit N]
```

Ingestao paralela em batch de arquivos demo pro usando multiprocessing. Resumivel -- pula demos ja ingeridos. Padrao e todos os nucleos CPU.

### Servidor API Interno

```bash
python -m uvicorn Programma_CS2_RENAN.backend.services.api:app --host 127.0.0.1 --port 8000
```

API interna baseada em FastAPI para acesso programatico a coaching, status de ingestao e estado do modelo. Nao exposta externamente por padrao. Veja os READMEs `backend/services/` para documentacao dos endpoints.

---

## Validacao e Qualidade

O projeto mantem uma hierarquia de validacao multi-nivel:

| Ferramenta | Escopo | Comando | Verificacoes |
|------------|--------|---------|--------------|
| Headless Validator | Gate de regressao primario | `python tools/headless_validator.py` | 313 checks, 24 fases |
| Suite Pytest | Testes logicos e integracao | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 1.794+ testes |
| Feature Audit | Integridade de feature engineering | `python tools/Feature_Audit.py` | Dimensoes de vetor, ranges |
| Portability Test | Compatibilidade cross-platform | `python tools/portability_test.py` | Checks de importacao, caminhos |
| Dev Health | Ambiente de desenvolvimento | `python tools/dev_health.py` | Dependencias, config |
| Dead Code Detector | Varredura de codigo nao utilizado | `python tools/dead_code_detector.py` | Analise de imports |
| Safety Verifier | Verificacoes de seguranca | `python tools/verify_all_safe.py` | RASP, varredura de segredos |
| DB Health | Diagnostico de banco de dados | `python tools/db_health_diagnostic.py` | Schema, modo WAL, integridade |
| Goliath Hospital | Diagnostico completo | `python goliath.py doctor` | Saude completa do sistema |

**Gate CI/CD:** O headless validator deve retornar exit code 0 antes que qualquer commit seja considerado valido. Pre-commit hooks aplicam padroes de qualidade de codigo. A pipeline CI roda em Ubuntu e Windows com GitHub Actions SHA-pinned.

---

## Suporte Multi-Idioma

A aplicacao suporta 3 idiomas em toda a UI:

| Idioma | UI | Guia do Usuario | README |
|--------|----|----------------|--------|
| English | Completo | [docs/guides/USER_GUIDE.md](docs/guides/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completo | [docs/guides/USER_GUIDE_IT.md](docs/guides/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completo | [docs/guides/USER_GUIDE_PT.md](docs/guides/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

O idioma pode ser alterado em tempo de execucao nas Configuracoes sem reiniciar a aplicacao.

---

## Funcionalidades de Seguranca

### Runtime Application Self-Protection (RASP)

- **Manifesto de Integridade** -- Hashes SHA-256 de todos os arquivos fonte criticos, verificados na inicializacao
- **Deteccao de Adulteracao** -- Alerta quando arquivos fonte foram modificados desde a ultima geracao do manifesto
- **Validacao de Binario Frozen** -- Verifica a estrutura do bundle PyInstaller e o ambiente de execucao
- **Deteccao de Localizacao Suspeita** -- Alerta quando executado de caminhos inesperados do sistema de arquivos

### Seguranca de Credenciais

- **Integracao OS Keyring** -- Chaves de API (Steam, FaceIT) armazenadas no Windows Credential Manager / keyring Linux, nunca em texto puro
- **Sem Segredos Hardcoded** -- Arquivo de configuracoes mostra o placeholder `"PROTECTED_BY_WINDOWS_VAULT"`
- **Operacoes Criptograficas** -- Usa `cryptography==46.0.3` (biblioteca verificada, sem cripto custom)

### Seguranca do Banco de Dados

- **SQLite Modo WAL** -- Write-Ahead Logging para acesso concorrente seguro em todos os bancos de dados
- **Validacao de Entrada** -- Modelos Pydantic na fronteira de ingestao, consultas SQL parametrizadas
- **Sistema de Backup** -- Backups automatizados do banco de dados com verificacao de integridade

### Logging Estruturado

- Todo logging atraves do namespace `get_logger("cs2analyzer.<modulo>")`
- Nenhum PII na saida de log
- Formato estruturado para integracao com observabilidade

---

## Ajuste de Desempenho

| Botao | Padrao | Efeito |
|-------|--------|--------|
| Dispositivo GPU | Auto-detectado via `get_device()` | CUDA quando disponivel, senao CPU. Sobrescreva com `CUDA_VISIBLE_DEVICES` |
| Batch size de treinamento | 32 (`backend/nn/config.py`) | Aumente para GPU com >6 GB VRAM. Reduza se OOM |
| Workers de ingestao | Contagem CPU (`batch_ingest.py`) | `--workers N` para limitar parsing paralelo de demos |
| Momentum EMA | 0.996 base, schedulado com coseno ate 1.0 (`backend/nn/jepa_train.py:353`) | Tracking do target encoder JEPA. Valores menores rastreiam mais rapido mas com mais ruido. EMA do RAP Coach tem padrao 0.999 (`backend/nn/ema.py:39`) |
| TensorBoard | `runs/coach_training` | `tensorboard --logdir runs/coach_training` para metricas live |
| SQLite modo WAL | Ativado por padrao | Leitura/escrita concorrente. Sem ajuste necessario para usuario unico |
| Limiar de deteccao de drift | Baseado em Z-score (`backend/processing/validation/`) | Dispara automaticamente flag de retreinamento quando distribuicoes de features mudam |

Para usuarios GPU: PyTorch CUDA 12.1 e a configuracao testada. Precisao mista nao esta atualmente habilitada -- todo treinamento roda em FP32.

> Para orientacao especifica de hardware, veja [Estudo 15 -- Hardware e Escalabilidade](docs/Studies/).

---

## Maturidade do Sistema

Nem todos os subsistemas sao igualmente maduros. O modo de coaching padrao (COPER) e production-ready e **nao** depende de modelos neurais. O coaching neural melhora conforme mais demos sao processadas.

| Subsistema | Status | Pontuacao | Notas |
|-----------|--------|-----------|-------|
| Coaching COPER | OPERACIONAL | 8/10 | Experience bank + RAG + referencias pro. Funciona imediatamente. |
| Motor Analitico | OPERACIONAL | 6/10 | Rating HLTV 2.0, breakdown de round, timeline de economia. |
| JEPA Base (InfoNCE) | OPERACIONAL | 7/10 | Pre-treinamento auto-supervisionado, target encoder EMA. |
| Neural Role Head | OPERACIONAL | 7/10 | MLP de 5 papeis com KL-divergence, consensus gating. |
| RAP Coach (7 camadas) | LIMITADO | 3/10 | Arquitetura completa (LTC+Hopfield), necessita 200+ demos. |
| VL-JEPA (16 conceitos) | LIMITADO | 2/10 | Alinhamento conceitual implementado, qualidade de labels melhorando. |

**Niveis de maturidade:**
- **CALIBRATING** (0-49 demos): 0.5x confianca, coaching amplamente suplementado por COPER
- **LEARNING** (50-199 demos): 0.8x confianca, features neurais gradualmente ativadas
- **MATURE** (200+ demos): Confianca total, todos os subsistemas contribuem

---

## Documentacao

### Guias do Usuario

| Documento | Descricao |
|-----------|-----------|
| [User Guide (EN)](docs/guides/USER_GUIDE.md) | Instalacao completa, setup wizard, chaves API, todas as telas, aquisicao de demos, solucao de problemas |
| [Guida Utente (IT)](docs/guides/USER_GUIDE_IT.md) | Guia completo do usuario em italiano |
| [Guia do Usuario (PT)](docs/guides/USER_GUIDE_PT.md) | Guia completo do usuario em portugues |

### Documentacao de Arquitetura

| Documento | Descricao |
|-----------|-----------|
| [Book-Coach-1A](docs/books/Book-Coach-1A.md) | Core neural: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory |
| [Book-Coach-1B](docs/books/Book-Coach-1B.md) | RAP Coach (7 componentes), fontes de dados (demo, HLTV, Steam, FACEIT) |
| [Book-Coach-2](docs/books/Book-Coach-2.md) | Servicos, motores de analise, knowledge/COPER, banco de dados, treinamento |
| [Book-Coach-3](docs/books/Book-Coach-3.md) | Logica completa do programa, UI Qt, ingestao, ferramentas, testes, build |
| [Analise de Cibersseguranca](docs/archive/cybersecurity.md) | Postura de seguranca e modelo de ameacas |

### Papers de Pesquisa (17 Estudos)

A pasta `docs/Studies/` contem 17 papers de pesquisa aprofundada cobrindo as fundacoes teoricas e decisoes de engenharia por tras de cada subsistema:

| # | Estudo | Topico |
|---|--------|--------|
| 01 | Fundacoes Epistemicas | Framework de representacao de conhecimento e raciocinio |
| 02 | Algebra de Ingestao | Modelo matematico de processamento de dados de demo |
| 03 | Redes Recorrentes | Teoria de redes LTC e Hopfield |
| 04 | Aprendizado por Reforco | Fundacoes de RL para decisoes de coaching |
| 05 | Arquitetura Perceptiva | Design da pipeline de processamento visual |
| 06 | Arquitetura Cognitiva | Modelagem de crencas e sistemas de decisao |
| 07 | Arquitetura JEPA | Teoria de Joint-Embedding Predictive Architecture |
| 08 | Engenharia Forense | Metodologia de debugging e diagnostico |
| 09 | Feature Engineering | Design e validacao do vetor 25-dimensional |
| 10 | Banco de Dados e Armazenamento | SQLite WAL, DB por partida, estrategia de migracao |
| 11 | Engine Tri-Daemon | Arquitetura multi-daemon e ciclo de vida |
| 12 | Avaliacao e Falsificacao | Metodologia de teste e validacao |
| 13 | Explicabilidade e Coaching | Atribuicao causal e design de UI de coaching |
| 14 | Etica, Privacidade e Integridade | Protecao de dados e etica de IA |
| 15 | Hardware e Escalabilidade | Otimizacao para varias configuracoes de hardware |
| 16 | Mapas e GNN | Analise espacial e abordagens de graph neural networks |
| 17 | Impacto Sociotecnico | Direcoes futuras e implicacoes sociais |

---

## Alimentando o Coach

O coach IA e fornecido sem conhecimento pre-treinado. Aprende exclusivamente de arquivos demo profissionais CS2. A qualidade do coaching e diretamente proporcional a qualidade e quantidade de demos ingeridos.

### Limiares de Contagem de Demos

| Demos Pro | Nivel | Confianca | O Que Acontece |
|-----------|-------|-----------|----------------|
| 0-9 | Nao pronto | 0% | Minimo de 10 demos pro necessarias para o primeiro ciclo de treinamento |
| 10-49 | CALIBRATING | 50% | Coaching base ativo, conselhos marcados como provisorios |
| 50-199 | LEARNING | 80% | Confiabilidade crescente, cada vez mais personalizado |
| 200+ | MATURE | 100% | Confianca total, precisao maxima |

### Onde Encontrar Demos Pro

1. Acesse [hltv.org](https://www.hltv.org) > Results
2. Filtre por eventos top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Selecione partidas de equipes do top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefira series BO3/BO5 para maximizar dados de treinamento por download
5. Diversifique em todos os mapas Active Duty -- uma distribuicao desbalanceada cria um coach desbalanceado
6. Baixe o link "GOTV Demo" ou "Watch Demo"

### Planejamento de Armazenamento

Arquivos `.dem` sao tipicamente de 300-850 MB cada. Planeje seu armazenamento adequadamente:

| Demos | Arquivos Brutos | DBs de Partida | Total |
|-------|-----------------|----------------|-------|
| 10 | ~5 GB | ~1 GB | ~6 GB |
| 50 | ~30 GB | ~5 GB | ~35 GB |
| 100 | ~60 GB | ~10 GB | ~70 GB |
| 200 | ~120 GB | ~20 GB | ~140 GB |

Tres localizacoes de armazenamento separadas:

| Localizacao | Conteudo | Recomendacao |
|-------------|----------|--------------|
| Banco Core | Estatisticas de jogadores, estado de coaching, metadata HLTV | Fica na pasta do programa |
| Brain Data Root | Pesos do modelo IA, logs, knowledge base | SSD recomendado |
| Pasta de Demos Pro | Arquivos .dem brutos + bancos SQLite por partida | Maior, HDD aceitavel |

### Monitoramento TensorBoard

```bash
tensorboard --logdir runs/coach_training
```

Abra [http://localhost:6006](http://localhost:6006) para monitorar indice de conviccao, transicoes de estado de maturidade, especializacao de gate e curvas de loss de treinamento.

> Para o checklist completo passo a passo do ciclo de coaching e guia detalhado de armazenamento, veja o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Solucao de Problemas

### Problemas Comuns

| Problema | Solucao |
|----------|---------|
| `ModuleNotFoundError: No module named 'PySide6'` | Instale as dependencias Qt: `pip install PySide6` |
| `ModuleNotFoundError: No module named 'kivy'` | Para a UI legacy: `pip install Kivy==2.3.0 KivyMD==1.2.0` (mais kivy-deps no Windows) |
| `CUDA not available` | Verifique o driver com `nvidia-smi`, reinstale PyTorch com `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Alerta nao bloqueante. Instale com `pip install sentence-transformers` para embeddings melhorados, ou ignore (fallback TF-IDF funciona) |
| `database is locked` | Feche todos os processos Python e reinicie |
| `RuntimeError: mat1 and mat2 shapes cannot be multiplied` | Checkpoint do modelo de METADATA_DIM diferente. Delete checkpoints obsoletos em `Programma_CS2_RENAN/models/` e retreine |
| Headless validator falha | Execute `python tools/headless_validator.py` para a fase especifica que falhou. Corrija antes de commitar |
| Parsing de demo retorna 0 rounds | Arquivo pode estar corrompido ou abaixo de `MIN_DEMO_SIZE` (10 MB). Tente um demo diferente |
| TensorBoard nao mostra dados | Verifique que `runs/coach_training/` existe e contem arquivos de evento. Treinamento deve completar pelo menos uma epoca |
| Ollama nao responde | Assegure que Ollama esta rodando (`ollama serve`) e que o modelo configurado esta puxado (`ollama pull llama3.1:8b`) |
| FlareSolverr connection refused | Inicie Docker: `docker compose up -d`. Verifique que a porta 8191 esta acessivel |
| Reset para estado de fabrica | Delete `Programma_CS2_RENAN/user_settings.json` e reinicie |

### Localizacoes de Banco de Dados

| Banco de Dados | Caminho | Conteudo |
|----------------|---------|----------|
| Principal | `Programma_CS2_RENAN/backend/storage/database.db` | Estatisticas de jogadores, estado de coaching, dados de treinamento |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadata de jogadores profissionais |
| Knowledge | `Programma_CS2_RENAN/data/knowledge_base.db` | RAG knowledge base |
| Por partida | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dados de partida a nivel de tick |

> Para solucao de problemas completa, veja o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Indice Completo da Documentacao

Todos os READMEs e documentos tecnicos do projeto. Clique em qualquer link para abrir o documento.

### Serie Book Coach

Quatro livros de visao tri-lingues + um livro companheiro de analogias canonicas. Cada livro-coach esta disponivel em Markdown (fonte editavel) e PDF.

**Italiano (fonte canonica):**
- [Ultimate CS2 Coach — Sistema AI](docs/books/Book-Coach-1.pdf) — PDF guarda-chuva
- [Parte 1A — Il Cervello](docs/books/Book-Coach-1A.md) ([PDF](docs/books/Book-Coach-1A.pdf))
- [Parte 1B — I Sensi e lo Specialista](docs/books/Book-Coach-1B.md) ([PDF](docs/books/Book-Coach-1B.pdf))
- [Parte 2 — Servizi, Analisi e Database](docs/books/Book-Coach-2.md) ([PDF](docs/books/Book-Coach-2.pdf))
- [Parte 3 — Programma, UI, Tools e Build](docs/books/Book-Coach-3.md) ([PDF](docs/books/Book-Coach-3.pdf))
- [Il Libro delle Analogie](docs/books/analogy-book.md) — 35 metaforas pedagogicas canonicas

**Traducoes em ingles:**
- [Part 1A — The Brain](docs/books/Book-Coach-1A-en.md)
- [Part 1B — The Senses and the Specialist](docs/books/Book-Coach-1B-en.md)
- [Part 2 — Services, Analysis, and Database](docs/books/Book-Coach-2-en.md)
- [Part 3 — Program, UI, Tools, and Build](docs/books/Book-Coach-3-en.md)
- [The Book of Analogies](docs/books/analogy-book-en.md)

**Traducoes em portugues brasileiro:**
- [Parte 1A — O Cerebro](docs/books/Book-Coach-1A-pt.md)
- [Parte 1B — Os Sentidos e o Especialista](docs/books/Book-Coach-1B-pt.md)
- [Parte 2 — Servicos, Analise e Banco de Dados](docs/books/Book-Coach-2-pt.md)
- [Parte 3 — Programa, UI, Ferramentas e Build](docs/books/Book-Coach-3-pt.md)
- [O Livro das Analogias](docs/books/analogy-book-pt.md)

**Referencia de traducoes:** [Glossario de Traducoes (IT → EN → PT-BR)](docs/books/TRANSLATION_GLOSSARY.md) — terminologia canonica usada em cada edicao traduzida.

### Raiz

- [README (EN)](README.md) — [Italiano](README_IT.md) — [Portugues](README_PT.md)

### Engenharia

- [Engineering Handoff](docs/ENGINEERING_HANDOFF.md) — Referencia master: auditoria completa do codebase, 75 work items, plano de execucao, roadmap do produto

### Infraestrutura

- [CI/CD Pipeline & Configuracao GitHub](.github/README.md) — [Italiano](.github/README_IT.md) — [Portugues](.github/README_PT.md)
- [Sistema de Migracao de Banco de Dados — Alembic](alembic/README.md) — [Italiano](alembic/README_IT.md) — [Portugues](alembic/README_PT.md)
- [Indice de Documentacao](docs/README.md) — [Italiano](docs/README_IT.md) — [Portugues](docs/README_PT.md)
- [Os Estudos — Bibliotheca](docs/Studies/README.md) — [Italiano](docs/Studies/README_IT.md) — [Portugues](docs/Studies/README_PT.md)
- [Scripts de Build e Setup](scripts/README.md) — [Italiano](scripts/README_IT.md) — [Portugues](scripts/README_PT.md)
- [Testes de Verificacao e Forenses de Nivel Raiz](tests/README.md) — [Italiano](tests/README_IT.md) — [Portugues](tests/README_PT.md)
- [Ferramentas do Projeto de Nivel Raiz](tools/README.md) — [Italiano](tools/README_IT.md) — [Portugues](tools/README_PT.md)
- [Packaging — Build & Distribuicao](packaging/README.md) — [Italiano](packaging/README_IT.md) — [Portugues](packaging/README_PT.md)

### Pacote Principal

- [Programma_CS2_RENAN](Programma_CS2_RENAN/README.md) — [Italiano](Programma_CS2_RENAN/README_IT.md) — [Portugues](Programma_CS2_RENAN/README_PT.md)
- [Sistemas Core](Programma_CS2_RENAN/core/README.md) — [Italiano](Programma_CS2_RENAN/core/README_IT.md) — [Portugues](Programma_CS2_RENAN/core/README_PT.md)
- [Dados — Dados da Aplicacao & Configuracao](Programma_CS2_RENAN/data/README.md) — [Italiano](Programma_CS2_RENAN/data/README_IT.md) — [Portugues](Programma_CS2_RENAN/data/README_PT.md)
- [Assets — Recursos Estaticos](Programma_CS2_RENAN/assets/README.md) — [Italiano](Programma_CS2_RENAN/assets/README_IT.md) — [Portugues](Programma_CS2_RENAN/assets/README_PT.md)
- [Modelos — Armazenamento de Checkpoints de Redes Neurais](Programma_CS2_RENAN/models/README.md) — [Italiano](Programma_CS2_RENAN/models/README_IT.md) — [Portugues](Programma_CS2_RENAN/models/README_PT.md)
- [Ferramentas de Validacao e Diagnostico](Programma_CS2_RENAN/tools/README.md) — [Italiano](Programma_CS2_RENAN/tools/README_IT.md) — [Portugues](Programma_CS2_RENAN/tools/README_PT.md)
- [Suite de Testes](Programma_CS2_RENAN/tests/README.md) — [Italiano](Programma_CS2_RENAN/tests/README_IT.md) — [Portugues](Programma_CS2_RENAN/tests/README_PT.md)

### Apps — Interface do Usuario

- [Apps — Camada de Interface do Usuario](Programma_CS2_RENAN/apps/README.md) — [Italiano](Programma_CS2_RENAN/apps/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/README_PT.md)
- [Aplicacao Desktop Qt (Primaria)](Programma_CS2_RENAN/apps/qt_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/README_PT.md)
- [Aplicacao Desktop (Legacy Kivy/KivyMD)](Programma_CS2_RENAN/apps/desktop_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/desktop_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/desktop_app/README_PT.md)

### Backend

- [Backend](Programma_CS2_RENAN/backend/README.md) — [Italiano](Programma_CS2_RENAN/backend/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/README_PT.md)
- [Analise — Teoria dos Jogos & Motores Estatisticos](Programma_CS2_RENAN/backend/analysis/README.md) — [Italiano](Programma_CS2_RENAN/backend/analysis/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/analysis/README_PT.md)
- [Coaching — Pipeline Multi-Modo](Programma_CS2_RENAN/backend/coaching/README.md) — [Italiano](Programma_CS2_RENAN/backend/coaching/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/coaching/README_PT.md)
- [Controle — Orquestracao & Gerenciamento de Daemons](Programma_CS2_RENAN/backend/control/README.md) — [Italiano](Programma_CS2_RENAN/backend/control/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/control/README_PT.md)
- [Fontes de Dados — Integracoes Externas](Programma_CS2_RENAN/backend/data_sources/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/README_PT.md)
- [Scraping de Dados Profissionais HLTV](Programma_CS2_RENAN/backend/data_sources/hltv/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/hltv/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/hltv/README_PT.md)
- [Ingestao Backend — File Watching & Governanca de Recursos](Programma_CS2_RENAN/backend/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/backend/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/ingestion/README_PT.md)
- [Conhecimento — RAG & Experience Bank](Programma_CS2_RENAN/backend/knowledge/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge/README_PT.md)
- [Knowledge Base — Sistema de Ajuda In-App](Programma_CS2_RENAN/backend/knowledge_base/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge_base/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge_base/README_PT.md)
- [Onboarding — Gerenciamento de Fluxo de Novo Usuario](Programma_CS2_RENAN/backend/onboarding/README.md) — [Italiano](Programma_CS2_RENAN/backend/onboarding/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/onboarding/README_PT.md)
- [Progresso — Rastreamento Longitudinal de Desempenho](Programma_CS2_RENAN/backend/progress/README.md) — [Italiano](Programma_CS2_RENAN/backend/progress/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/progress/README_PT.md)
- [Reporting — Motor de Analytics do Dashboard](Programma_CS2_RENAN/backend/reporting/README.md) — [Italiano](Programma_CS2_RENAN/backend/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/reporting/README_PT.md)
- [Camada de Servicos da Aplicacao](Programma_CS2_RENAN/backend/services/README.md) — [Italiano](Programma_CS2_RENAN/backend/services/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/services/README_PT.md)
- [Camada de Armazenamento de Banco de Dados](Programma_CS2_RENAN/backend/storage/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/README_PT.md)

### Redes Neurais

- [Subsistema de Redes Neurais](Programma_CS2_RENAN/backend/nn/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/README_PT.md)
- [RAP Coach — Arquitetura Recorrente de 7 Camadas](Programma_CS2_RENAN/backend/nn/rap_coach/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/rap_coach/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/rap_coach/README_PT.md)
- [Advanced — Stub de Modulo Experimental](Programma_CS2_RENAN/backend/nn/advanced/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/advanced/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/advanced/README_PT.md)

### Processamento & Feature Engineering

- [Processamento — Pipeline de Dados & Feature Engineering](Programma_CS2_RENAN/backend/processing/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/README_PT.md)
- [Baselines Profissionais & Deteccao de Meta Drift](Programma_CS2_RENAN/backend/processing/baselines/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/baselines/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/baselines/README_PT.md)
- [Feature Engineering — Extracao Unificada de Features](Programma_CS2_RENAN/backend/processing/feature_engineering/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/feature_engineering/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/feature_engineering/README_PT.md)

### Pipelines de Ingestao

- [Pipelines de Ingestao de Demos](Programma_CS2_RENAN/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/README_PT.md)
- [Implementacoes de Pipeline de Ingestao](Programma_CS2_RENAN/ingestion/pipelines/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/pipelines/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/pipelines/README_PT.md)
- [Registro de Arquivos Demo & Gerenciamento de Ciclo de Vida](Programma_CS2_RENAN/ingestion/registry/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/registry/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/registry/README_PT.md)

### Observabilidade & Reporting

- [Observabilidade & Protecao em Runtime](Programma_CS2_RENAN/observability/README.md) — [Italiano](Programma_CS2_RENAN/observability/README_IT.md) — [Portugues](Programma_CS2_RENAN/observability/README_PT.md)
- [Visualizacao & Geracao de Relatorios](Programma_CS2_RENAN/reporting/README.md) — [Italiano](Programma_CS2_RENAN/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/reporting/README_PT.md)

---

## Licenca

Este projeto e duplamente licenciado. Copyright (c) 2025-2026 Renan Augusto Macena.

Voce pode escolher entre:
- **Licenca Proprietaria** -- Todos os Direitos Reservados (padrao). Visualizacao para fins educacionais permitida.
- **Apache License 2.0** -- Open source permissiva com protecao de patentes.

Consulte [LICENSE](LICENSE) para os termos completos.

---

## Autor

**Renan Augusto Macena**

Construido com paixao por um jogador de Counter-Strike com mais de 10.000 horas desde 2004, combinando profundo conhecimento do jogo com engenharia de IA para criar o sistema de coaching definitivo.

> *"Eu sempre quis um guia profissional -- como os verdadeiros jogadores profissionais tem -- para entender como realmente e quando alguem treina do jeito certo e joga do jeito certo."*

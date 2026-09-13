# Macena CS2 Analyzer

[![CI Pipeline](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml/badge.svg)](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary%20%7C%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-headless%20validator%20%7C%20193%20test%20files-brightgreen.svg)]()

**Coach Tatico com IA para Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
- [Qualidade e Verificacao (auditoria 2026-08)](#qualidade-e-verificacao-auditoria-nuke-proof-2026-08)
- [Suporte Multi-Idioma](#suporte-multi-idioma)
- [Funcionalidades de Seguranca](#funcionalidades-de-seguranca)
- [Otimizacao de Desempenho](#otimizacao-de-desempenho)
- [Maturidade do Sistema](#maturidade-do-sistema)
- [Documentacao](#documentacao)
- [Alimentando o Coach](#alimentando-o-coach)
- [Resolucao de Problemas](#resolucao-de-problemas)
- [Indice Completo da Documentacao](#indice-completo-da-documentacao)
- [Licenca](#licenca)
- [Autor](#autor)

---

## Qualidade e Verificacao (auditoria "nuke-proof" 2026-08)

Toda a codebase (618 arquivos, ~155k LOC) foi lida duas vezes e
auditada de ponta a ponta em agosto de 2026. Resultados, evidencias e
dossies por arquivo estao em `docs/audit/`.

- **Gate de testes**: 2574 aprovados / 0 falhas / 0 erros; piso de
  cobertura 50% (a suite esta em ~56%). `tools/headless_validator.py`:
  PASS. `sync_integrity_manifest.py --verify-only`: VERDE.
- **44 findings registrados, 44 resolvidos** — 31 corrigidos com
  testes de regressao no mesmo commit, 13 adiados com motivos
  escritos (`docs/audit/FINDINGS.md`).
- **CI** em cada push (`main`, `develop`, `feature/**`, `feat/**`,
  `fix/**`, `chore/**`): lint (pre-commit incl. ruff), testes no
  Ubuntu + Windows, integracao, seguranca (Bandit, detect-secrets,
  pip-audit), type-check, build web.
- **Decisoes de produto**: os conselhos do coach sao deliberadamente
  em ingles; o contrato JEPA 25-vs-10 permanece protegido (26-RANGE-01)
  ate que a trilha de pesquisa seja retomada.

## Funcionalidades Principais

### Pipeline de Coaching IA

- **Cadeia de Fallback de 4 Niveis** -- COPER > Hibrido > Tradicional+RAG > Tradicional, garantindo que o sistema sempre produza conselhos uteis independentemente da maturidade do modelo
- **COPER Experience Bank** -- Armazena e recupera experiencias de coaching passadas ponderadas por recencia, eficacia e similaridade de contexto
- **Base de Conhecimento RAG** -- Retrieval-Augmented Generation com padroes de referencia profissionais e conhecimento tatico
- **Integracao Ollama** -- LLM local opcional para refinamento em linguagem natural dos insights de coaching
- **Atribuicao Causal** -- Cada recomendacao de coaching inclui uma explicacao "por que" rastreavel a decisoes especificas de gameplay

### Subsistemas de Redes Neurais

- **RAP Coach** -- Arquitetura de 7 camadas combinando percepcao, memoria (LTC-Hopfield), estrategia (Mixture-of-Experts com superposicao), pedagogia (value function), predicao de posicao, atribuicao causal e agregacao de saida
- **Encoder JEPA** -- Joint-Embedding Predictive Architecture para pre-treinamento auto-supervisionado com loss contrastiva InfoNCE e target encoder EMA
- **Encoder JEPA v2** -- Reescrita baseada em Transformer com causal self-attention, RMSNorm, SwiGLU, FiLM conditioning, predicao multi-horizonte (1/4/16 tokens) e regularizacao SIGReg
- **VL-JEPA** -- Extensao Vision-Language com alinhamento de 16 conceitos taticos (posicionamento, utilidade, economia, engajamento, decisao, psicologia)
- **AdvancedCoachNN** -- Arquitetura LSTM + Mixture-of-Experts para predicao de pesos de coaching
- **Neural Role Head** -- Classificador MLP de 5 papeis (lurker, entry, support, AWPer, IGL) com KL-divergence e consensus gating
- **Modelos Bayesianos de Crencas** -- Rastreamento do estado mental do oponente com calibracao adaptativa dos dados da partida

### Analise de Demo

- **Parsing a Nivel de Tick** -- Cada tick dos arquivos `.dem` e analisado via demoparser2, preservando todo o estado do jogo (sem decimacao de tick)
- **Rating HLTV 2.0** -- Calculado por partida usando a formula HLTV 2.0 reverse-engineered (KPR, DPR, KAST%, Impact, ADR)
- **Detalhamento Round por Round** -- Timeline da economia, analise de engajamentos, uso de utilidades, rastreamento de momentum
- **Decaimento Temporal da Baseline** -- Rastreia a evolucao das habilidades do jogador ao longo do tempo com ponderacao por decaimento exponencial

### Analise baseada em Teoria dos Jogos

- **Arvores Expectiminimax** -- Avaliacao decisoria game-theoretic para cenarios estrategicos
- **Probabilidade de Morte Bayesiana** -- Estima a probabilidade de sobrevivencia baseada em posicao, equipamento e estado inimigo
- **Indice de Engano** -- Quantifica a imprevisibilidade posicional em relacao as baselines profissionais
- **Analise de Alcance de Engajamento** -- Mapeia a selecao de armas contra distribuicoes de distancia de engajamento
- **Probabilidade de Vitoria** -- Calculo de probabilidade de vitoria em tempo real
- **Rastreamento de Momentum** -- Trajetoria de confianca e desempenho round por round

### Aplicacao Desktop

- **Aplicacao Desktop Qt** -- Frontend PySide6/Qt (primario) com padrao MVVM
- **Visualizador Tatico 2D** -- Replay de demo em tempo real com posicoes de jogadores, eventos de abate, indicadores de bomba e predicoes AI ghost
- **Historico de Partidas** -- Lista rolavel de partidas recentes com ratings codificados por cor
- **Dashboard de Desempenho** -- Tendencias de rating, estatisticas por mapa, analise de pontos fortes/fracos, detalhamento de utilidades
- **Chat com o Coach** -- Conversa IA interativa com botoes de acao rapida e perguntas em texto livre
- **Perfil do Usuario** -- Integracao Steam com importacao automatica de partidas
- **3 Temas Visuais** -- CS2 (laranja), CS:GO (azul-cinza), CS 1.6 (verde) com wallpapers rotativos

### Treinamento e Automacao

- **4-Daemon Session Engine** -- Scanner (descoberta de arquivos), Digester (processamento de demo), Teacher (treinamento de modelos), Pulse (monitoramento de saude)
- **Gating de Maturidade de 3 Estagios** -- CALIBRATING (0-49 demos, 0.5x confianca) > LEARNING (50-199, 0.8x) > MATURE (200+, plena)
- **Conviction Index** -- Composto de 5 sinais rastreando entropia de crencas, especializacao de gate, foco conceitual, acuracia de valor e estabilidade de papel
- **Auto-Retraining** -- O treinamento e ativado automaticamente com 10% de crescimento na contagem de demos
- **Deteccao de Drift** -- Monitoramento de drift de features baseado em Z-score com flag automatico de retraining
- **Coach Introspection Observatory** -- Integracao TensorBoard com maquina de estados de maturidade, projetor de embedding e rastreamento de conviccao

---

## Requisitos de Sistema

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| SO | Windows 10 / Ubuntu 24.04 | Windows 10/11 |
| Python | 3.11 | 3.11 ou 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nenhuma (modo CPU) | NVIDIA GTX 1650+ (CUDA 12.1) ou GPU AMD com suporte ROCm |
| Disco | 3 GB livres | 5 GB livres |
| Display | 1280x720 | 1920x1080 |

---

## Inicio Rapido

### 0. App instalado (instalador Windows)

`scripts\build_production.bat` gera `dist\Macena_CS2_Installer_<versao>.exe` (veja `packaging/`).
Uma copia instalada mantem todos os dados fora da pasta do programa — `%LOCALAPPDATA%\MacenaCS2Analyzer`
ou a pasta escolhida no wizard inicial — e faz tudo o que uma copia do codigo-fonte faz: analisa suas
demos e um pool de demos pro baixadas (cards do Painel) e treina o coach no servico em segundo plano
(Painel → Status do treinamento → **Treinar o coach**; a execucao fica no registro de modelos).

### 1. Clone

```bash
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
```

### 2. Setup Automatizado (Windows)

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Cria um ambiente virtual, instala todas as dependencias, inicializa o banco de dados e instala o navegador Playwright Chromium.

**Para suporte a GPU NVIDIA**, apos a conclusao do script:

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
sudo apt install -y python3.12 python3.12-venv python3.12-dev build-essential

python3.12 -m venv .venv
source .venv/bin/activate

# PyTorch (escolha UM — veja https://pytorch.org/get-started/locally/ para URLs de indice atuais):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # Apenas CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # GPU NVIDIA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm<VER> # GPU AMD (ROCm — escolha sua versao ROCm)

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Configure o Ambiente

```bash
cp .env.example .env
# Edite .env com sua chave API Steam e preferencias (veja comentarios no arquivo)
```

### 6. Verifique a Instalacao

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 7. Opcional: Baseline de Coaching Profissional

Para construir baselines de coaching a partir de dados de partidas profissionais, dois componentes adicionais sao necessarios:

**Docker + FlareSolverr** (para scraping automatizado de estatisticas HLTV de profissionais):

```bash
# Instale Docker Desktop: https://docs.docker.com/desktop/
# Depois inicie o FlareSolverr:
docker compose up -d
```

FlareSolverr contorna a protecao Cloudflare no hltv.org. Sem ele, o daemon Hunter nao pode fazer scraping das estatisticas dos jogadores profissionais. Voce ainda pode usar o coach com seus proprios arquivos demo -- as baselines profissionais melhoram a qualidade do coaching mas nao sao obrigatorias.

**Dependencias RAP Coach** (arquitetura experimental opcional):

```bash
pip install -r requirements-rap.txt
```

Necessario apenas se voce habilitar `USE_RAP_MODEL=True` nas configuracoes. O modelo JEPA padrao funciona sem essas.

### 8. Inicie

```bash
# Aplicacao desktop (GUI Qt -- recomendada)
./launch.sh

# Ou manualmente:
python -m Programma_CS2_RENAN.apps.qt_app.app

# Console interativo (TUI live com paineis em tempo real)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Para o guia completo com configuracao de API, walkthrough de funcionalidades e resolucao de problemas, consulte o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Visao Geral da Arquitetura

### Pipeline ASSISTA > APRENDA > PENSE > FALE

O sistema e organizado como uma pipeline de 4 estagios que transforma arquivos demo brutos em coaching personalizado:

```
ASSISTA (Ingestao)     APRENDA (Treinamento)  PENSE (Inferencia)      FALE (Dialogo)
  Daemon Scanner         Daemon Teacher         Pipeline COPER          Template + Ollama
  Parsing demo           Maturidade 3 estagios  Conhecimento RAG        Atribuicao causal
  Extracao de features   Treinamento multi-mod.  Teoria dos jogos        Comparacoes com pros
  Armazenamento tick     Deteccao de drift       Modelagem de crencas    Scoring de severidade
```

**ASSISTA** -- O daemon Scanner monitora continuamente as pastas de demo configuradas para novos arquivos `.dem`. Quando encontrados, o daemon Digester analisa cada tick usando demoparser2, extrai o vetor canonico de features de 25 dimensoes, calcula os ratings HLTV 2.0 e armazena tudo em bancos de dados SQLite por partida.

**APRENDA** -- O daemon Teacher treina automaticamente os modelos neurais quando dados suficientes se acumulam. O treinamento progride atraves de 3 estagios de maturidade (CALIBRATING > LEARNING > MATURE). Multiplas arquiteturas sao treinadas: JEPA para aprendizado auto-supervisionado de representacoes, RAP Coach para modelagem de decisoes taticas, NeuralRoleHead para classificacao do papel dos jogadores.

**PENSE** -- No momento da inferencia, a pipeline COPER combina predicoes neurais com experiencias de coaching recuperadas, conhecimento RAG e analise de teoria dos jogos. Uma cadeia de fallback de 4 niveis (COPER > Hibrido > Tradicional+RAG > Tradicional) garante que conselhos estejam sempre disponiveis independentemente da maturidade do modelo.

**FALE** -- A saida final do coaching e formatada com niveis de severidade, atribuicao causal ("por que este conselho") e opcionalmente refinada atraves de um LLM local Ollama para qualidade de linguagem natural.

### 4-Daemon Session Engine

| Daemon | Papel | Trigger |
|--------|-------|---------|
| **Scanner (Hunter)** | Descobre novos arquivos `.dem` nas pastas configuradas | Scan periodico ou file watcher |
| **Digester** | Analisa demos, extrai features, calcula ratings | Novo arquivo detectado pelo Scanner |
| **Teacher** | Treina modelos neurais nos dados acumulados | Limiar de crescimento de 10% na contagem de demos |
| **Pulse** | Monitoramento de saude, deteccao de drift, estado do sistema | Continuo em background |

### Pipeline de Coaching COPER

COPER (Context Optimized with Prompt, Experience, and Replay) e o motor de coaching principal. Opera uma cadeia de fallback de 4 niveis:

1. **Modo COPER** -- Pipeline completa: recuperacao Experience Bank + conhecimento RAG + predicoes do modelo neural + comparacoes profissionais.
2. **Modo Hibrido** -- Combina predicoes neurais com conselhos baseados em template quando alguns modelos ainda estao em calibracao.
3. **Modo Tradicional + RAG** -- Pura recuperacao: busca padroes de coaching relevantes na knowledge base sem inferencia neural. Funciona com demos ingeridas apenas.
4. **Modo Tradicional** -- Conselhos baseados em template da analise estatistica (desvios media/desvio padrao das baselines profissionais). Funciona imediatamente.

### Arquiteturas de Redes Neurais

**RAP Coach (Arquitetura de 7 Camadas)**

O RAP (Reasoning, Adaptation, Pedagogy) Coach e o modelo neural experimental principal, desabilitado por padrao atras de `USE_RAP_MODEL`. Suas 7 camadas processam dados de gameplay atraves de uma pipeline cognitiva:

| Camada | Funcao | Detalhes |
|--------|--------|----------|
| 1. Percepcao | Encoding visual + espacial | Camadas Conv para frame visual (64d), estado do mapa (32d), diff movimento (32d) -> 128d |
| 2. Memoria | Rastreamento recorrente de crencas | LTC (Liquid Time-Constant) + rede Hopfield para memoria associativa. Input: 153d (128 percepcao + 25 metadata) -> 256d estado oculto |
| 3. Estrategia | Otimizacao decisoria | Mixture-of-Experts (4 especialistas, top-2 routing) com superposicao para decisoes context-dependent. 10 pesos de acao |
| 4. Pedagogia | Estimativa de valor | Estimativa V-function com integracao de vetor de habilidade |
| 5. Posicao | Posicionamento otimo | Prediz (dx, dy, dz) delta para posicao otima (escala: 500 unidades mundo) |
| 6. Atribuicao | Diagnostico causal | Atribuicao de 5 dimensoes explicando drivers de decisao |
| 7. Saida | Agregacao | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution, hidden_state |

**JEPA (Joint-Embedding Predictive Architecture)**

Pre-treinamento auto-supervisionado com:
- Context encoder + predictor -> prediz o embedding alvo
- Target encoder atualizado via EMA (momentum 0.996)
- Loss contrastiva InfoNCE com negativos in-batch
- Dimensao latente: 256

**JEPA v2 (Reescrita baseada em Transformer)**

Reimplementacao autocontida em `backend/nn/jepa_v2/` (14 modulos, independente do legacy `jepa_model.py`):
- Tokenizer + Encoder Transformer (d_model=128, 4 camadas, 4 cabecas)
- RMSNorm, SwiGLU FFN, FiLM conditioning, RoPE positional encoding
- Projector + Predictor para predicao multi-horizonte (horizontes 1, 4, 16 tokens)
- Regularizacao SIGReg (temporal + batch) substituindo prevencao de colapso InfoNCE
- Sondas lineares integradas e telemetria (RankMe, guardas de abort std-min)
- Autocast bf16 por padrao; schedule LR coseno com warmup

**VL-JEPA (Extensao Vision-Language)**

Estende JEPA com alinhamento de 16 conceitos taticos:
- Conceitos: posicionamento (3), utilidade (2), economia (2), engajamento (4), decisao (2), psicologia (3)
- Concept alignment loss + diversity regularization
- Rotulagem baseada em resultado de RoundStats (abates, mortes, equipamento, resultado do round)

**Outros Modelos:**
- **AdvancedCoachNN** -- LSTM (hidden=128) + Mixture-of-Experts (3 especialistas, top-k=2) para predicao de pesos de coaching
- **NeuralRoleHead** -- Classificador MLP de 5 papeis com KL-divergence gating e consensus voting
- **RoleClassifier** -- Deteccao leve de papel a partir de features de tick

### Vetor de Features de 25 Dimensoes

Cada tick do jogo e representado como um vetor canonico de 25 dimensoes (`METADATA_DIM=25`):

| Indice | Feature | Intervalo | Descricao |
|--------|---------|-----------|-----------|
| 0 | health | [0, 1] | HP / 100 |
| 1 | armor | [0, 1] | Colete / 100 |
| 2 | has_helmet | {0, 1} | Capacete equipado |
| 3 | has_defuser | {0, 1} | Kit de desarme |
| 4 | equipment_value | [0, 1] | Custo de equipamento normalizado |
| 5 | is_crouching | {0, 1} | Posicao agachada |
| 6 | is_scoped | {0, 1} | Arma com mira ativa |
| 7 | is_blinded | {0, 1} | Efeito de flash |
| 8 | enemies_visible | [0, 1] | Contagem de inimigos visiveis (normalizada) |
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | Coordenadas mundo (normalizadas por mapa) |
| 12-13 | view_yaw_sin, view_yaw_cos | [-1, 1] | Angulo de visao (encoding ciclico) |
| 14 | view_pitch | [-1, 1] | Angulo de visao vertical |
| 15 | z_penalty | [0, 1] | Distincao vertical (mapas multi-nivel) |
| 16 | kast_estimate | [0, 1] | Razao Kill/Assist/Survive/Trade |
| 17 | map_id | [0, 1] | Hash deterministico do mapa (baseado em MD5) |
| 18 | round_phase | {0, .33, .66, 1} | Pistol / Eco / Force / Full buy |
| 19 | weapon_class | [0, 1] | Knife=0, Pistol=.2, SMG=.4, Rifle=.6, Sniper=.8, Heavy=1 |
| 20 | time_in_round | [0, 1] | Segundos / 115 |
| 21 | bomb_planted | {0, 1} | Flag bomba plantada |
| 22 | teammates_alive | [0, 1] | Contagem / 4 |
| 23 | enemies_alive | [0, 1] | Contagem / 5 |
| 24 | team_economy | [0, 1] | Media de dinheiro do time / 16000 |

### Gating de Maturidade de 3 Estagios

Os modelos progridem atraves de gates de maturidade baseados na contagem de demos ingeridas:

| Estagio | Contagem de Demos | Confianca | Comportamento |
|---------|-------------------|-----------|---------------|
| **CALIBRATING** | 0-49 | 0.5x | Coaching basico, conselhos marcados como provisorios |
| **LEARNING** | 50-199 | 0.8x | Intermediario, confiabilidade crescente |
| **MATURE** | 200+ | 1.0x | Confianca plena, todos os subsistemas contribuem |

Um **Conviction Index** paralelo (0.0-1.0) rastreia 5 sinais neurais: entropia de crencas, especializacao de gate, foco conceitual, acuracia de valor e estabilidade de papel. Estados: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 estavel por 10+ epocas) > MATURE (>0.75 estavel por 20+ epocas). Uma queda abrupta >20% ativa o estado CRISIS.

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

Mapas multi-nivel (Nuke, Vertigo) usam cutoffs no eixo Z para separar niveis superior e inferior para renderizacao 2D precisa. A feature z_penalty (indice 15) no vetor de features captura a distincao vertical para esses mapas.

---

## Stack Tecnologico

### Dependencias Principais

| Categoria | Pacote | Versao | Proposito |
|-----------|--------|--------|-----------|
| **ML Framework** | PyTorch | 2.1+ | Treinamento e inferencia de redes neurais |
| **Redes Recorrentes** | ncps | 1.0.1+ | Redes Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | git-pinned (fornece `hflayers`) | Camadas de rede Hopfield para memoria |
| **Parsing de Demo** | demoparser2 | 0.42.0 | Parsing a nivel de tick de arquivos demo CS2 |
| **Framework UI (primario)** | PySide6 | 6.11.0 | GUI desktop cross-platform baseada em Qt |
| **ORM de Banco** | SQLAlchemy + SQLModel | 2.0.49 / 0.0.38 | Modelos e consultas de banco de dados |
| **Migracoes** | Alembic | 1.18.4 | Migracoes de schema de banco de dados |
| **Automacao de Browser** | Playwright | 1.58.0 | Automacao de browser headless |
| **Cliente HTTP** | HTTPX | 0.28.1 | Requisicoes HTTP assincronas |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | 2.4.3 / 2.3.3 / 1.17.1 / 1.8.0 | Computacao numerica e analise |
| **Visualizacao** | Matplotlib | 3.10.8 | Geracao de graficos |
| **Observabilidade de Treino** | TensorBoard | 2.21.0 | Dashboards de treinamento ao vivo (`Programma_CS2_RENAN/runs/`) |
| **Busca Vetorial** | faiss-cpu | 1.13.2 | Recuperacao Experience/RAG (opcional; fallback brute-force) |
| **Embeddings de Texto** | sentence-transformers | 3.4.1 | Embeddings semanticos (opcional; fallback baseado em hash) |
| **TUI** | Rich | 15.0.0 | UI de terminal para modo console (pinned nos lock files, nao em requirements.txt) |
| **API** | FastAPI + Uvicorn | 0.135.3 / 0.44.0 | Servidor API interno |
| **Validacao** | Pydantic | 2.12.5 | Validacao de dados e configuracoes |
| **Testes** | pytest + pytest-cov + pytest-timeout | 8.3.4 / 6.0.0 / 2.4.0 | Framework de testes e cobertura |
| **Empacotamento** | PyInstaller | Latest (apenas build, nao em requirements) | Distribuicao binaria |
| **Parsing HTML** | BeautifulSoup4 | 4.14.3 | Extracao de conteudo web |
| **Imagens** | Pillow | 12.3.0 | Processamento de imagens |
| **Keyring** | keyring | 25.7.0 | Armazenamento seguro de credenciais |

---

## Estrutura do Projeto

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Pacote principal da aplicacao
|   +-- apps/
|   |   +-- qt_app/                     GUI PySide6/Qt (primaria, MVVM + Sinais)
|   |   |   +-- app.py                  Ponto de entrada Qt
|   |   |   +-- main_window.py          QMainWindow com navegacao lateral
|   |   |   +-- core/                   Singleton AppState, ThemeEngine, padrao Worker
|   |   |   +-- screens/               15 telas (home, visualizador tatico, historico
|   |   |   |                           de partidas, detalhe de partida, desempenho, coach,
|   |   |   |                           configuracoes, wizard, ajuda, perfil, perfil do usuario,
|   |   |   |                           config steam/faceit, comparacao pro, detalhe pro)
|   |   |   +-- viewmodels/            ViewModels signal-driven (QObject + Signal/Slot)
|   |   |   +-- widgets/               Graficos (radar, momentum, economia, sparkline),
|   |   |                               taticos (widget de mapa, sidebar de jogador, timeline)
|   |
|   +-- backend/
|   |   +-- analysis/                   Teoria dos jogos e analise estatistica
|   |   |   +-- belief_model.py         Rastreamento bayesiano de estado mental do oponente
|   |   |   +-- game_tree.py            Arvores decisionais Expectiminimax
|   |   |   +-- momentum.py             Momentum de round e tendencias de confianca
|   |   |   +-- role_classifier.py      Deteccao de papel do jogador (AWPer, entry, support, IGL, lurker, flex)
|   |   |   +-- blind_spots.py          Consciencia de mapa e fraquezas posicionais
|   |   |   +-- deception_index.py      Metrica de imprevisibilidade posicional
|   |   |   +-- entropy_analysis.py     Quantificacao de aleatoriedade decisoria
|   |   |   +-- engagement_range.py     Analise de distribuicao distancia-arma
|   |   |   +-- utility_economy.py      Eficiencia de gasto com granadas
|   |   |   +-- win_probability.py      Calculo de probabilidade de vitoria em tempo real
|   |   |
|   |   +-- data_sources/              Integracao de dados externos
|   |   |   +-- demo_parser.py          Wrapper demoparser2 (extracao a nivel de tick)
|   |   |   +-- hltv_scraper.py         Scraping de metadados profissionais HLTV
|   |   |   +-- steam_api.py            Perfil Steam e dados de partida
|   |   |   +-- faceit_api.py           Integracao de dados de partida FaceIT
|   |   |
|   |   +-- nn/                         Subsistemas de redes neurais
|   |   |   +-- config.py               Config global NN (dimensoes, lr, batch size, device)
|   |   |   +-- jepa_model.py           Encoder JEPA + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         Loop de treinamento JEPA com monitoramento de drift
|   |   |   +-- training_orchestrator.py Orquestracao de treinamento multi-modelo
|   |   |   +-- jepa_v2/                JEPA v2 (baseado em Transformer, autocontido)
|   |   |   |   +-- tokenizer.py        Conversao tick-to-token (patch_ticks=8)
|   |   |   |   +-- encoder.py          Encoder Transformer (d_model=128, 4 camadas)
|   |   |   |   +-- predictor.py        Preditor de alvo multi-horizonte
|   |   |   |   +-- projector.py        Cabeca de projecao de embedding
|   |   |   |   +-- blocks.py           CausalSelfAttention, RMSNorm, SwiGLU, FiLM
|   |   |   |   +-- losses.py           Loss JEPA v2 (next + multi-horizonte + SIGReg)
|   |   |   |   +-- sigreg.py           Regularizacao SIGReg (temporal + batch)
|   |   |   |   +-- trainer.py          Loop de treinamento com LR coseno + warmup
|   |   |   |   +-- probes.py           Sondas lineares para qualidade de representacao
|   |   |   |   +-- sampler.py          Sampler de janelas para dados episodicos
|   |   |   |   +-- telemetry.py        Monitoramento RankMe, std-min
|   |   |   |   +-- config.py           JepaV2Config (dataclass frozen)
|   |   |   |   +-- cli.py              Entry point CLI para treinamento standalone
|   |   |   +-- experimental/rap_coach/ Modelo RAP Coach (canonico; nn/rap_coach contem shims deprecados)
|   |   |   |   +-- model.py            Arquitetura de 7 camadas
|   |   |   |   +-- trainer.py          Loop de treinamento especifico RAP
|   |   |   |   +-- memory.py           Modulo de memoria LTC + Hopfield
|   |   |   +-- layers/                 Componentes neurais compartilhados
|   |   |       +-- superposition.py    Camada de superposicao context-dependent
|   |   |
|   |   +-- processing/                Feature engineering e processamento de dados
|   |   |   +-- feature_engineering/
|   |   |   |   +-- vectorizer.py       Extracao canonica de features 25-dim (METADATA_DIM=25)
|   |   |   |   +-- schema_v2.py        Schema de features JEPA v2 (split numerico/categorico)
|   |   |   +-- tensor_factory.py      Construcao de tensores vista/mapa para RAP Coach
|   |   |   +-- heatmap_engine.py      Geracao de heatmap espacial
|   |   |   +-- validation/            Deteccao de drift, verificacoes de qualidade de dados
|   |   |
|   |   +-- knowledge/                 Gestao de conhecimento
|   |   |   +-- rag_knowledge.py        Recuperacao RAG para padroes de coaching
|   |   |   +-- experience_bank.py      Armazenamento e recuperacao de experiencias COPER
|   |   |
|   |   +-- services/                  Servicos da aplicacao
|   |   |   +-- coaching_service.py     Pipeline de coaching de 4 niveis (COPER/Hibrido/Tradicional+RAG/Tradicional)
|   |   |   +-- ollama_writer.py        Integracao LLM local para refinamento de linguagem
|   |   |
|   |   +-- storage/                   Camada de banco de dados
|   |   |   +-- database.py            Gerenciamento de conexoes SQLite WAL-mode
|   |   |   +-- db_models.py           Definicoes ORM SQLAlchemy/SQLModel
|   |   |   +-- naming.py              Normalizacao de nomes de jogador para joins entre tabelas (D-08)
|   |   |   +-- backup_manager.py      Backup automatizado de banco de dados
|   |   |   +-- match_data_manager.py  Gerenciamento de banco SQLite por partida
|   |   |
|   |   +-- coaching/                  Helpers de pipeline de coaching multi-modo
|   |   +-- control/                   Orquestracao de aplicacao e gerenciamento de daemon
|   |   +-- ingestion/                 File watching e governanca de recursos
|   |   +-- knowledge_base/            Conteudos do sistema de ajuda in-app
|   |   +-- onboarding/                Gerenciamento de fluxo de novo usuario
|   |   +-- progress/                  Rastreamento de desempenho longitudinal
|   |   +-- reporting/                 Motor de analytics de dashboard
|   |   +-- server.py                  Servidor utilitario FastAPI standalone (nao conectado ao app)
|   |
|   +-- core/                          Servicos core da aplicacao
|   |   +-- session_engine.py           Engine de 4 daemons (Scanner, Digester, Teacher, Pulse)
|   |   +-- map_manager.py             Carregamento de mapas, calibracao de coordenadas, Z-cutoffs
|   |   +-- asset_manager.py           Resolucao de temas e assets
|   |   +-- spatial_data.py            Sistemas de coordenadas espaciais
|   |
|   +-- ingestion/                     Pipeline de ingestao de demo
|   |   +-- steam_locator.py           Auto-descoberta de caminhos de demo CS2 do Steam
|   |   +-- integrity.py               Validacao de arquivo demo
|   |
|   +-- observability/                 Monitoramento e seguranca
|   |   +-- rasp.py                    Runtime Application Self-Protection
|   |   +-- sentry_setup.py           Relato de crash opcional (duplo opt-in, scrub de PII)
|   |   +-- logger_setup.py           Logging estruturado (namespace cs2analyzer.*)
|   |
|   +-- reporting/                     Geracao de saida
|   |   +-- visualizer.py             Renderizacao de graficos e diagramas
|   |   +-- report_generator.py       Geracao de relatorio de partida
|   |
|   +-- assets/                        Recursos estaticos (temas, i18n, wallpapers)
|   +-- models/                        Armazenamento de checkpoints de redes neurais
|   +-- tools/                         Ferramentas a nivel de pacote (sync manifesto de integridade, diagnosticos)
|   +-- tests/                         Suite de testes (193 arquivos de teste)
|   +-- data/                          Dados estaticos (seed knowledge base, map_config.json, datasets externos)
|
+-- docs/                              Documentacao
|   +-- guides/                        Guias de usuario (EN / IT / PT)
|   +-- books/                         Vision books (Book-Coach 1A/1B/2/3 + livro de analogias, IT/EN/PT)
|   +-- research/                      Catalogo da biblioteca de pesquisa (INDEX.md)
|
+-- tools/                             Ferramentas de validacao e diagnostico
|   +-- headless_validator.py          Gate de regressao primario
|   +-- ingest_pro_demos.py           Ingestao de demo pro (incremental/completa/somente-retrain)
|   +-- Feature_Audit.py              Auditoria de feature engineering
|   +-- portability_test.py           Verificacoes de compatibilidade cross-platform
|   +-- dead_code_detector.py         Varredura de codigo inutilizado
|   +-- dev_health.py                 Saude do ambiente de desenvolvimento
|   +-- verify_all_safe.py            Verificacao de seguranca
|   +-- db_health_diagnostic.py       Diagnostico de saude do banco de dados
|   +-- Sanitize_Project.py           Preparacao para distribuicao
|   +-- build_pipeline.py             Orquestracao de pipeline de build
|   +-- export_episodes.py            Exportacao de episodios de treinamento para JEPA v2
|   +-- benchmark_jepa_v2_vs_legacy.py Comparacao de benchmark JEPA v2 vs legacy
|   +-- measure_episode_lengths.py    Analise de distribuicao de comprimento de episodios
|   +-- measure_event_horizons.py     Estatisticas de cobertura de horizontes de evento
|   +-- measure_name_join_coverage.py  Auditoria de cobertura de join de nomes de jogadores
|   +-- measure_sigreg_sample_size.py  Requisitos de tamanho de amostra SIGReg
|   +-- verify_math_claims.py         Verificacao de claims matematicos
|
+-- tests/                            Testes de integracao e verificacao
+-- scripts/                          Scripts de setup e deploy
+-- packaging/                        Spec PyInstaller + instalador Windows
+-- alembic/                          Scripts de migracao de banco de dados
+-- .github/workflows/build.yml       Pipeline CI/CD cross-platform
+-- console.py                        Ponto de entrada TUI interativo
+-- goliath.py                        Orquestrador CLI de producao
+-- batch_ingest.py                   Ingestao batch paralela de demos pro
+-- schema.py                         Suite de banco de dados e migracoes
+-- run_full_training_cycle.py        Runner standalone de ciclo de treinamento
+-- train.sh                         Wrapper de treinamento (canonico; usa .venv, registra saida)
```

---

## Pontos de Entrada

A aplicacao fornece 8 pontos de entrada para diferentes casos de uso:

### Aplicacao Desktop (GUI Qt -- Primaria)

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

Interface grafica completa com visualizador tatico, historico de partidas, dashboard de desempenho, chat com o coach e configuracoes. Abre em 1440x900 (tamanho minimo de janela 1280x720). Na primeira inicializacao, um assistente de 5 passos configura o diretorio Brain Data Root.

### Console Interativo (TUI)

```bash
python console.py
```

UI de terminal com paineis em tempo real para desenvolvimento e controle em tempo de execucao. Comandos organizados por subsistema:

| Grupo de Comandos | Exemplos |
|--------------------|----------|
| **ML Pipeline** | `ml start`, `ml stop`, `ml pause`, `ml resume`, `ml throttle 0.5`, `ml status` |
| **Ingestao** | `ingest start`, `ingest stop`, `ingest mode continuous 5`, `ingest scan` |
| **Build & Teste** | `build run`, `build verify`, `test all`, `test headless`, `test hospital` |
| **Sistema** | `sys status`, `sys audit`, `sys baseline`, `sys db`, `sys vacuum`, `sys resources` |
| **Config** | `set steam`, `set faceit`, `set demo-path /caminho`, `set config chave valor` |
| **Servicos** | `svc status`, `svc restart hunter` |
| **Manutencao** | `maint clear-cache`, `maint clear-queue`, `maint sanitize`, `maint prune <match_id>` |
| **Ferramentas** | `tool demo`, `tool user`, `tool logs`, `tool list` |

### CLI de Producao (Goliath)

```bash
python goliath.py <comando>
```

Orquestrador master para builds de producao, releases e diagnosticos:

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `build` | Pipeline de build industrial | `--test-only` |
| `sanitize` | Limpa o projeto para distribuicao | `-y` |
| `integrity` | Gera manifesto de integridade | |
| `audit` | Verifica dados e features | `--demo <caminho>` |
| `db` | Gerenciamento de schema do banco | `-y` |
| `doctor` | Diagnosticos clinicos | `--dept <nome>` |
| `baseline` | Status de decaimento temporal da baseline | |

### Suite de Banco de Dados e Migracoes (Schema)

```bash
python schema.py <comando>
```

Controlador unificado para eventos do ciclo de vida do banco de dados:

| Comando | Descricao |
|---------|-----------|
| `inspect` | Mostra tabelas, colunas e indices do BD |
| `migrate` | Aplica mudancas de schema (Alembic/Auto) |
| `import` | Importa dados pro de fontes externas |
| `fix` | Hot-patch para problemas de schema conhecidos |
| `reset` | Reset do estado de migracao ou tabelas |

### Runner de Ciclo de Treinamento

```bash
./train.sh              # wrapper recomendado (usa .venv, registra em logs/)
# ou diretamente:
python run_full_training_cycle.py
```

`train.sh` e o wrapper canonico: localiza o `.venv` local ao repo (com fallback para `~/.venvs/cs2analyzer`), encaminha flags e faz tee-log em `logs/`. Flags uteis: `-d` (dry run), `-e N` (epocas), `-m jepa|rap|all` (tipo de modelo), `-T` (sem TensorBoard). O script subjacente `run_full_training_cycle.py` aceita flags adicionais como `--patience`, `--train-samples`, `--val-samples`, `--seed` e `--eval-baseline`/`--no-eval-baseline`.

### Ingestao de Demo Pro

```bash
python tools/ingest_pro_demos.py             # incremental (pula ja ingeridas)
python tools/ingest_pro_demos.py --full       # rebuild completo: re-ingere tudo
python tools/ingest_pro_demos.py --retrain-only  # pula ingestao, apenas retrain
python tools/ingest_pro_demos.py --no-train   # apenas ingestao, pula retrain
```

Ponto de entrada de ingestao primario. No modo incremental, limpa e recoloca na fila linhas `IngestionTask` falhas ou orfas por stem de demo. Popula o banco monolito e shards por partida, depois dispara retraining a menos que `--no-train` seja passado.

### Ingestao Batch

```bash
python batch_ingest.py [--workers N] [--limit N] [--demo-dir DIR] [--no-train]
```

Ingestao batch paralela de arquivos demo profissionais usando multiprocessing. Resumivel -- pula demos ja ingeridas. A contagem de workers escala automaticamente baseada na RAM disponivel. Use `--no-train` para pular o passo de treinamento automatico apos a ingestao.

### Servidor API Interno

```bash
python -m uvicorn Programma_CS2_RENAN.backend.server:app --host 127.0.0.1 --port 8000
```

API interna baseada em FastAPI para acesso programatico a insights de coaching, controle de treinamento e status de servicos. Um servidor utilitario standalone -- nao e iniciado pelo app desktop e deve ser lancado separadamente. Nao exposto externamente por padrao. Os endpoints estao definidos em `Programma_CS2_RENAN/backend/server.py`.

---

## Validacao e Qualidade

O projeto mantem uma hierarquia de validacao multi-nivel:

| Ferramenta | Escopo | Comando | Verificacoes |
|------------|--------|---------|--------------|
| Headless Validator | Gate de regressao primario | `python tools/headless_validator.py` | Verificacoes contratuais multi-fase |
| Suite Pytest | Testes logicos e integracao | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 193 arquivos de teste |
| Feature Audit | Integridade de feature engineering | `python tools/Feature_Audit.py` | Dimensoes de vetor, intervalos |
| Portability Test | Compatibilidade cross-platform | `python tools/portability_test.py` | Verificacoes de import, caminhos |
| Dev Health | Ambiente de desenvolvimento | `python tools/dev_health.py` | Dependencias, config |
| Dead Code Detector | Varredura de codigo inutilizado | `python tools/dead_code_detector.py` | Analise de imports |
| Safety Verifier | Verificacoes de seguranca | `python tools/verify_all_safe.py` | RASP, varredura de segredos |
| DB Health | Diagnostico de banco | `python tools/db_health_diagnostic.py` | Schema, modo WAL, integridade |
| Goliath Hospital | Diagnostico completo | `python goliath.py doctor` | Saude completa do sistema |

**Gate CI/CD:** O headless validator deve retornar exit code 0 antes que qualquer commit seja considerado valido. Os hooks pre-commit garantem padroes de qualidade de codigo. A pipeline CI roda no Ubuntu e Windows com GitHub Actions SHA-pinned.

---

## Suporte Multi-Idioma

A aplicacao suporta 3 idiomas em toda a interface:

| Idioma | UI | Guia do Usuario | README |
|--------|----|-----------------|--------|
| English | Completa | [docs/guides/USER_GUIDE.md](docs/guides/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completa | [docs/guides/USER_GUIDE_IT.md](docs/guides/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completa | [docs/guides/USER_GUIDE_PT.md](docs/guides/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

O idioma pode ser alterado em tempo de execucao nas Configuracoes sem reiniciar a aplicacao.

---

## Funcionalidades de Seguranca

### Runtime Application Self-Protection (RASP)

- **Manifesto de Integridade** -- Hashes SHA-256 de todos os arquivos fonte criticos, verificados na inicializacao
- **Deteccao de Adulteracao** -- Avisa quando arquivos fonte foram modificados desde a ultima geracao do manifesto
- **Validacao de Binario Frozen** -- Verifica estrutura do bundle PyInstaller e ambiente de execucao
- **Deteccao de Localizacao Suspeita** -- Avisa quando executado de caminhos inesperados do sistema de arquivos

### Seguranca de Credenciais

- **Integracao OS Keyring** -- Chaves de API (Steam, FaceIT) armazenadas no Windows Credential Manager / keyring Linux, nunca em texto simples
- **Nenhum Segredo Hardcoded** -- O arquivo de configuracoes mostra o placeholder `"PROTECTED_BY_WINDOWS_VAULT"`

### Seguranca de Banco de Dados

- **SQLite WAL Mode** -- Write-Ahead Logging para acesso concorrente seguro em todos os bancos de dados
- **Validacao de Input** -- Modelos Pydantic na fronteira de ingestao, consultas SQL parametrizadas
- **Sistema de Backup** -- Backups automatizados de banco de dados com verificacao de integridade

### Logging Estruturado

- Todo logging atraves do namespace `get_logger("cs2analyzer.<modulo>")`
- Nenhum PII na saida de logs
- Formato estruturado para integracao de observabilidade

---

## Otimizacao de Desempenho

| Parametro | Padrao | Efeito |
|-----------|--------|--------|
| Device GPU | Auto-detectado via `get_device()` | CUDA/ROCm quando disponivel, senao CPU. Sobrescrita com `CUDA_VISIBLE_DEVICES` ou configuracao `CUDA_DEVICE` |
| Batch size de treinamento | 32 (`backend/nn/config.py`) | Aumentar para GPU com >6 GB VRAM. Diminuir se OOM |
| Workers de ingestao | Auto: baseado em RAM e CPU, limite de 8 (`batch_ingest.py`) | `--workers N` para sobrescrever parsing paralelo de demo |
| Momentum EMA | 0.996 base, agendado com coseno ate 1.0 (`backend/nn/jepa_trainer.py`) | Rastreamento do target encoder JEPA. Valores menores rastreiam mais rapido mas com mais ruido. O helper EMA standalone tem padrao 0.999 (`backend/nn/ema.py`) |
| TensorBoard | `Programma_CS2_RENAN/runs/` | `tensorboard --logdir Programma_CS2_RENAN/runs/` para metricas ao vivo |
| SQLite WAL mode | Habilitado por padrao | Leitura/escrita concorrente. Nenhum ajuste necessario para usuario unico |
| Limiar de deteccao de drift | Baseado em Z-score (`backend/processing/validation/`) | Ativa automaticamente flag de retraining quando distribuicoes de features mudam |

Para usuarios de GPU: PyTorch CUDA 12.1 e a configuracao testada; GPUs AMD sao suportadas via ROCm (veja `backend/nn/config.py:get_device()`). Precisao mista (autocast bf16) e habilitada automaticamente em GPUs CUDA/ROCm; treinamento em CPU roda em FP32.

---

## Maturidade do Sistema

Nem todos os subsistemas sao igualmente maduros. O modo de coaching padrao (COPER) e production-ready e **nao** depende dos modelos neurais. O coaching neural melhora conforme mais demos sao processadas.

| Subsistema | Status | Pontuacao | Notas |
|------------|--------|-----------|-------|
| Coaching COPER | OPERACIONAL | 8/10 | Experience bank + RAG + referencias pro. Funciona imediatamente. |
| Motor Analitico | OPERACIONAL | 6/10 | Rating HLTV 2.0, detalhamento de round, timeline de economia. |
| JEPA Base (InfoNCE) | OPERACIONAL | 7/10 | Pre-treinamento auto-supervisionado, target encoder EMA. |
| JEPA v2 (SIGReg) | EXPERIMENTAL | 4/10 | Reescrita Transformer com predicao multi-horizonte, SIGReg. Trilha de pesquisa. |
| Neural Role Head | OPERACIONAL | 7/10 | MLP de 5 papeis com KL-divergence, consensus gating. |
| RAP Coach (7 camadas) | LIMITADO | 3/10 | Arquitetura completa (LTC+Hopfield), necessita 200+ demos. |
| VL-JEPA (16 conceitos) | LIMITADO | 2/10 | Alinhamento conceitual implementado, qualidade de rotulos melhorando. |

**Niveis de maturidade:**
- **CALIBRATING** (0-49 demos): confianca 0.5x, coaching fortemente suplementado por COPER
- **LEARNING** (50-199 demos): confianca 0.8x, features neurais gradualmente ativadas
- **MATURE** (200+ demos): confianca plena, todos os subsistemas contribuem

---

## Documentacao

### Guias de Usuario

| Documento | Descricao |
|-----------|-----------|
| [Inicio Rapido](docs/QUICKSTART.md) | Obtenha feedback de coaching de uma demo em menos de 5 minutos |
| [Guia do Usuario (PT)](docs/guides/USER_GUIDE_PT.md) | Instalacao completa, setup wizard, chaves de API, todas as telas, aquisicao de demo, resolucao de problemas |
| [User Guide (EN)](docs/guides/USER_GUIDE.md) | Guia de usuario completo em ingles |
| [Guida Utente (IT)](docs/guides/USER_GUIDE_IT.md) | Guia de usuario completo em italiano |

### Documentacao Arquitetural

| Documento | Descricao |
|-----------|-----------|
| [Book-Coach-1A](docs/books/Book-Coach-1A.md) | Core neural: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory |
| [Book-Coach-1B](docs/books/Book-Coach-1B.md) | RAP Coach (7 componentes), fontes de dados (demo, HLTV, Steam, FACEIT) |
| [Book-Coach-2](docs/books/Book-Coach-2.md) | Servicos, motores de analise, knowledge/COPER, banco de dados, treinamento |
| [Book-Coach-3](docs/books/Book-Coach-3.md) | Logica completa do programa, UI Qt, ingestao, ferramentas, testes, build |

### Biblioteca de Pesquisa

[docs/research/INDEX.md](docs/research/INDEX.md) cataloga a biblioteca de pesquisa (JEPA, SSL, MoE, Hopfield/LTC, qualidade de dados, e mais) embasando as decisoes de design do projeto.

---

## Alimentando o Coach

O coach IA vem sem conhecimento pre-treinado. Aprende exclusivamente de arquivos demo profissionais de CS2. A qualidade do coaching e diretamente proporcional a qualidade e quantidade de demos ingeridas.

### Limiares de Contagem de Demos

| Demos Pro | Nivel | Confianca | O Que Acontece |
|-----------|-------|-----------|----------------|
| 0-9 | Nao pronto | 0% | Minimo de 10 demos pro necessarias para o primeiro ciclo de treinamento |
| 10-49 | CALIBRATING | 50% | Coaching basico ativo, conselhos marcados como provisorios |
| 50-199 | LEARNING | 80% | Confiabilidade crescente, cada vez mais personalizado |
| 200+ | MATURE | 100% | Confianca plena, acuracia maxima |

### Onde Encontrar Demos Pro

1. Va em [hltv.org](https://www.hltv.org) > Results
2. Filtre por eventos top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Selecione partidas de times do top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefira series BO3/BO5 para maximizar dados de treinamento por download
5. Diversifique por todos os mapas Active Duty -- uma distribuicao desbalanceada cria um coach desbalanceado
6. Baixe o link "GOTV Demo" ou "Watch Demo"

### Planejamento de Armazenamento

Arquivos `.dem` tipicamente tem 300-850 MB cada. Planeje seu armazenamento de acordo:

| Demos | Arquivos Brutos | BDs de Partida | Total |
|-------|-----------------|----------------|-------|
| 10 | ~5 GB | ~1 GB | ~6 GB |
| 50 | ~30 GB | ~5 GB | ~35 GB |
| 100 | ~60 GB | ~10 GB | ~70 GB |
| 200 | ~120 GB | ~20 GB | ~140 GB |

Tres locais de armazenamento separados:

| Local | Conteudo | Recomendacao |
|-------|----------|--------------|
| Banco de Dados Core | Estatisticas de jogador, estado de coaching, metadados HLTV | Fica na pasta do programa |
| Brain Data Root | Pesos de modelos IA, logs, knowledge base | SSD recomendado |
| Pasta de Demos Pro | Arquivos .dem brutos + bancos SQLite por partida | Maior, HDD aceitavel |

### Monitoramento TensorBoard

```bash
tensorboard --logdir Programma_CS2_RENAN/runs/
```

Abra [http://localhost:6006](http://localhost:6006) para monitorar conviction index, transicoes de estado de maturidade, especializacao de gate e curvas de loss de treinamento.

> Para a checklist completa passo a passo do ciclo de coaching e guia detalhado de armazenamento, consulte o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Resolucao de Problemas

### Problemas Comuns

| Problema | Solucao |
|----------|---------|
| `ModuleNotFoundError: No module named 'PySide6'` | Instale as dependencias Qt: `pip install PySide6` |
| `CUDA not available` | Verifique o driver com `nvidia-smi`, reinstale PyTorch com `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Aviso nao bloqueante. Instale com `pip install sentence-transformers` para embeddings melhorados, ou ignore (fallback baseado em hash funciona) |
| `database is locked` | Feche todos os processos Python e reinicie |
| `RuntimeError: mat1 and mat2 shapes cannot be multiplied` | Checkpoint de modelo de um METADATA_DIM diferente. Delete checkpoints obsoletos em `Programma_CS2_RENAN/models/` e retreine |
| Headless validator falha | Execute `python tools/headless_validator.py` para a fase especifica que falha. Corrija antes de commitar |
| Parsing de demo retorna 0 rounds | O arquivo pode estar corrompido ou abaixo de `MIN_DEMO_SIZE` (10 MB). Tente com outra demo |
| TensorBoard nao mostra dados | Verifique que `Programma_CS2_RENAN/runs/` existe e contem arquivos de evento. O treinamento deve completar pelo menos uma epoca |
| Ollama nao responde | Certifique-se de que Ollama esta rodando (`ollama serve`) e que o modelo configurado esta baixado (`ollama pull gemma4:e2b`) |
| FlareSolverr conexao recusada | Inicie Docker: `docker compose up -d`. Verifique que a porta 8191 esta acessivel |
| Reset de fabrica | Delete `Programma_CS2_RENAN/user_settings.json` e reinicie |

### Localizacoes de Banco de Dados

| Banco de Dados | Caminho | Conteudo |
|----------------|---------|----------|
| Principal | `Programma_CS2_RENAN/backend/storage/database.db` | Estatisticas de jogador, estado de coaching, dados de treinamento |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadados de jogadores profissionais |
| Knowledge | `Programma_CS2_RENAN/data/knowledge_base.db` (move para sob Brain Data Root quando configurado) | Knowledge base RAG |
| Por partida | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dados de partida a nivel de tick |

> Para resolucao de problemas completa, consulte o [Guia do Usuario](docs/guides/USER_GUIDE_PT.md).

---

## Indice Completo da Documentacao

Todos os README e documentos tecnicos do projeto. Clique em qualquer link para abrir o documento.

### Serie Book Coach

Quatro livros de visao tri-lingues + um livro companheiro de analogias canonicas. Cada livro-coach esta disponivel em Markdown (fonte editavel) e PDF.

**Italiano (fonte canonica):**
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

**Referencia de traducoes:** [Glossario de Traducoes (IT → EN → PT-BR)](docs/books/TRANSLATION_GLOSSARY.md) — terminologia canonica usada em todas as edicoes traduzidas.

### Raiz

- [README (EN)](README.md) — [Italiano](README_IT.md) — [Português](README_PT.md)

### Infraestrutura

- [Guia de Inicio Rapido](docs/QUICKSTART.md)
- [CI/CD Pipeline & Configuracao GitHub](.github/OVERVIEW.md) — [Italiano](.github/OVERVIEW_IT.md) — [Portugues](.github/OVERVIEW_PT.md)
- [Sistema de Migracao de Banco de Dados — Alembic](alembic/README.md) — [Italiano](alembic/README_IT.md) — [Portugues](alembic/README_PT.md)
- [Indice de Documentacao](docs/README.md) — [Italiano](docs/README_IT.md) — [Portugues](docs/README_PT.md)
- [Scripts de Build e Setup](scripts/README.md) — [Italiano](scripts/README_IT.md) — [Portugues](scripts/README_PT.md)
- [Testes de Verificacao e Forense a Nivel Root](tests/README.md) — [Italiano](tests/README_IT.md) — [Portugues](tests/README_PT.md)
- [Ferramentas de Projeto a Nivel Root](tools/README.md) — [Italiano](tools/README_IT.md) — [Portugues](tools/README_PT.md)
- [Demo Parser Fuzz Harness](tools/fuzz/README.md) — [Italiano](tools/fuzz/README_IT.md) — [Portugues](tools/fuzz/README_PT.md)
- [Empacotamento — Build & Distribuicao](packaging/README.md) — [Italiano](packaging/README_IT.md) — [Portugues](packaging/README_PT.md)
- [Documentacao de Seguranca](SECURITY/README.md) — [Italiano](SECURITY/README_IT.md) — [Portugues](SECURITY/README_PT.md)
- [Politicas de Seguranca](SECURITY/policies/README.md) — [Italiano](SECURITY/policies/README_IT.md) — [Portugues](SECURITY/policies/README_PT.md)
- [Design Atlas](design/README.md) — [Italiano](design/README_IT.md) — [Portugues](design/README_PT.md)
- [Design Atlas — Bundle de Upload](design/cs2/uploads/README.md) — [Italiano](design/cs2/uploads/README_IT.md) — [Portugues](design/cs2/uploads/README_PT.md)
- [Evaluation Harness & Benchmarking](evals/README.md) — [Italiano](evals/README_IT.md) — [Portugues](evals/README_PT.md)
- [CS2 Coach Bench](evals/cs2_coach_bench/README.md) — [Italiano](evals/cs2_coach_bench/README_IT.md) — [Portugues](evals/cs2_coach_bench/README_PT.md)
- [Artefatos Gerados de Auditoria & Avaliacao](reports/README.md) — [Italiano](reports/README_IT.md) — [Portugues](reports/README_PT.md)
- [Logs de Sistema Centralizados](logs/README.md) — [Italiano](logs/README_IT.md) — [Portugues](logs/README_PT.md)
- [Backend Top-Level — Staging de Storage](backend/README.md) — [Italiano](backend/README_IT.md) — [Portugues](backend/README_PT.md)
- [Scaffold de Migracao Legacy](backend/storage/README.md) — [Italiano](backend/storage/README_IT.md) — [Portugues](backend/storage/README_PT.md)

### Pacote Principal

- [Programma_CS2_RENAN](Programma_CS2_RENAN/README.md) — [Italiano](Programma_CS2_RENAN/README_IT.md) — [Portugues](Programma_CS2_RENAN/README_PT.md)
- [Sistemas Core](Programma_CS2_RENAN/core/README.md) — [Italiano](Programma_CS2_RENAN/core/README_IT.md) — [Portugues](Programma_CS2_RENAN/core/README_PT.md)
- [Dados — Dados de Aplicacao & Configuracao](Programma_CS2_RENAN/data/README.md) — [Italiano](Programma_CS2_RENAN/data/README_IT.md) — [Portugues](Programma_CS2_RENAN/data/README_PT.md)
- [Assets — Recursos Estaticos](Programma_CS2_RENAN/assets/README.md) — [Italiano](Programma_CS2_RENAN/assets/README_IT.md) — [Portugues](Programma_CS2_RENAN/assets/README_PT.md)
- [Modelos — Armazenamento de Checkpoints de Redes Neurais](Programma_CS2_RENAN/models/README.md) — [Italiano](Programma_CS2_RENAN/models/README_IT.md) — [Portugues](Programma_CS2_RENAN/models/README_PT.md)
- [Ferramentas de Validacao e Diagnostico](Programma_CS2_RENAN/tools/README.md) — [Italiano](Programma_CS2_RENAN/tools/README_IT.md) — [Portugues](Programma_CS2_RENAN/tools/README_PT.md)
- [Suite de Testes](Programma_CS2_RENAN/tests/README.md) — [Italiano](Programma_CS2_RENAN/tests/README_IT.md) — [Portugues](Programma_CS2_RENAN/tests/README_PT.md)
- [Suite de Testes Automatizada em Camadas](Programma_CS2_RENAN/tests/automated_suite/README.md) — [Italiano](Programma_CS2_RENAN/tests/automated_suite/README_IT.md) — [Portugues](Programma_CS2_RENAN/tests/automated_suite/README_PT.md)
- [Assets Graficos & Temas de UI](Programma_CS2_RENAN/PHOTO_GUI/README.md) — [Italiano](Programma_CS2_RENAN/PHOTO_GUI/README_IT.md) — [Portugues](Programma_CS2_RENAN/PHOTO_GUI/README_PT.md)
- [Execucoes de Sessao & Dados de Execucao](Programma_CS2_RENAN/runs/README.md) — [Italiano](Programma_CS2_RENAN/runs/README_IT.md) — [Portugues](Programma_CS2_RENAN/runs/README_PT.md)
- [Configuracao de Taticas](Programma_CS2_RENAN/tactics/README.md) — [Italiano](Programma_CS2_RENAN/tactics/README_IT.md) — [Portugues](Programma_CS2_RENAN/tactics/README_PT.md)

### Apps — Interface do Usuario

- [Apps — Camada de Interface do Usuario](Programma_CS2_RENAN/apps/README.md) — [Italiano](Programma_CS2_RENAN/apps/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/README_PT.md)
- [Aplicacao Desktop Qt (Primaria)](Programma_CS2_RENAN/apps/qt_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/README_PT.md)
- [Utilitarios Core da Aplicacao Qt](Programma_CS2_RENAN/apps/qt_app/core/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/core/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/core/README_PT.md)
- [Modulos de Telas UI Qt](Programma_CS2_RENAN/apps/qt_app/screens/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/screens/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/screens/README_PT.md)
- [ViewModels MVVM](Programma_CS2_RENAN/apps/qt_app/viewmodels/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/viewmodels/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/viewmodels/README_PT.md)
- [Biblioteca de Widgets Qt Personalizados](Programma_CS2_RENAN/apps/qt_app/widgets/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/widgets/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/widgets/README_PT.md)
- [Widgets de Graficos do Dashboard](Programma_CS2_RENAN/apps/qt_app/widgets/charts/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/widgets/charts/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/widgets/charts/README_PT.md)
- [Componentes Visuais Especificos de Coaching](Programma_CS2_RENAN/apps/qt_app/widgets/coaching/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/widgets/coaching/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/widgets/coaching/README_PT.md)
- [Primitivas UI Genericas](Programma_CS2_RENAN/apps/qt_app/widgets/components/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/widgets/components/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/widgets/components/README_PT.md)
- [Widgets do Visualizador Tatico](Programma_CS2_RENAN/apps/qt_app/widgets/tactical/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/widgets/tactical/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/widgets/tactical/README_PT.md)
- [Frontend Embedded TypeScript/Vite](Programma_CS2_RENAN/apps/qt_app/web/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/web/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/web/README_PT.md)
- [Visualizador Tatico Embedded (TypeScript/Vite)](Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/web/tactical-viewer/README_PT.md)

### Backend

- [Backend](Programma_CS2_RENAN/backend/README.md) — [Italiano](Programma_CS2_RENAN/backend/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/README_PT.md)
- [Analise — Teoria dos Jogos & Motores Estatisticos](Programma_CS2_RENAN/backend/analysis/README.md) — [Italiano](Programma_CS2_RENAN/backend/analysis/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/analysis/README_PT.md)
- [Coaching — Pipeline Multi-Modo](Programma_CS2_RENAN/backend/coaching/README.md) — [Italiano](Programma_CS2_RENAN/backend/coaching/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/coaching/README_PT.md)
- [Controle — Orquestracao & Gerenciamento de Daemon](Programma_CS2_RENAN/backend/control/README.md) — [Italiano](Programma_CS2_RENAN/backend/control/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/control/README_PT.md)
- [Fontes de Dados — Integracoes Externas](Programma_CS2_RENAN/backend/data_sources/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/README_PT.md)
- [Scraping de Dados Profissionais HLTV](Programma_CS2_RENAN/backend/data_sources/hltv/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/hltv/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/hltv/README_PT.md)
- [Ingestao Backend — File Watching & Governanca de Recursos](Programma_CS2_RENAN/backend/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/backend/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/ingestion/README_PT.md)
- [Conhecimento — RAG & Experience Bank](Programma_CS2_RENAN/backend/knowledge/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge/README_PT.md)
- [Knowledge Base — Sistema de Ajuda In-App](Programma_CS2_RENAN/backend/knowledge_base/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge_base/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge_base/README_PT.md)
- [Onboarding — Gerenciamento de Fluxo de Novo Usuario](Programma_CS2_RENAN/backend/onboarding/README.md) — [Italiano](Programma_CS2_RENAN/backend/onboarding/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/onboarding/README_PT.md)
- [Progresso — Rastreamento de Desempenho Longitudinal](Programma_CS2_RENAN/backend/progress/README.md) — [Italiano](Programma_CS2_RENAN/backend/progress/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/progress/README_PT.md)
- [Reporting — Motor de Analytics do Dashboard](Programma_CS2_RENAN/backend/reporting/README.md) — [Italiano](Programma_CS2_RENAN/backend/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/reporting/README_PT.md)
- [Camada de Servicos da Aplicacao](Programma_CS2_RENAN/backend/services/README.md) — [Italiano](Programma_CS2_RENAN/backend/services/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/services/README_PT.md)
- [Camada de Armazenamento de Banco de Dados](Programma_CS2_RENAN/backend/storage/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/README_PT.md)
- [Datasets — Namespace Reservado](Programma_CS2_RENAN/backend/storage/datasets/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/datasets/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/datasets/README_PT.md)
- [Modelos de Storage — Namespace Reservado](Programma_CS2_RENAN/backend/storage/models/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/models/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/models/README_PT.md)

### Redes Neurais

- [Subsistema de Redes Neurais](Programma_CS2_RENAN/backend/nn/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/README_PT.md)
- [JEPA v2 — Encoder Auto-Supervisionado baseado em Transformer](Programma_CS2_RENAN/backend/nn/jepa_v2/) (14 modulos, sem README standalone ainda)
- [RAP Coach — Arquitetura Recorrente de 7 Camadas](Programma_CS2_RENAN/backend/nn/rap_coach/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/rap_coach/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/rap_coach/README_PT.md)
- [Advanced — Modulo Experimental](Programma_CS2_RENAN/backend/nn/advanced/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/advanced/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/advanced/README_PT.md)
- [Sandbox Experimental de Redes Neurais](Programma_CS2_RENAN/backend/nn/experimental/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/experimental/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/experimental/README_PT.md)
- [RAP Coach — Implementacao Experimental Canonica](Programma_CS2_RENAN/backend/nn/experimental/rap_coach/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/experimental/rap_coach/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/experimental/rap_coach/README_PT.md)
- [Utilitarios Neurais Somente-Inferencia](Programma_CS2_RENAN/backend/nn/inference/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/inference/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/inference/README_PT.md)
- [Blocos Construtivos Neurais Reutilizaveis](Programma_CS2_RENAN/backend/nn/layers/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/layers/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/layers/README_PT.md)

### Processamento & Feature Engineering

- [Processamento — Pipeline de Dados & Feature Engineering](Programma_CS2_RENAN/backend/processing/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/README_PT.md)
- [Baselines Profissionais & Deteccao de Meta Drift](Programma_CS2_RENAN/backend/processing/baselines/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/baselines/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/baselines/README_PT.md)
- [Feature Engineering — Extracao Unificada de Features](Programma_CS2_RENAN/backend/processing/feature_engineering/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/feature_engineering/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/feature_engineering/README_PT.md)
- [Validacao — Gates de Integridade de Dados](Programma_CS2_RENAN/backend/processing/validation/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/validation/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/validation/README_PT.md)

### Pipelines de Ingestao

- [Pipelines de Ingestao de Demo](Programma_CS2_RENAN/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/README_PT.md)
- [Implementacoes de Pipeline de Ingestao](Programma_CS2_RENAN/ingestion/pipelines/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/pipelines/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/pipelines/README_PT.md)
- [Registro de Arquivos Demo & Gerenciamento de Ciclo de Vida](Programma_CS2_RENAN/ingestion/registry/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/registry/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/registry/README_PT.md)

### Observabilidade & Reporting

- [Observabilidade & Protecao em Tempo de Execucao](Programma_CS2_RENAN/observability/README.md) — [Italiano](Programma_CS2_RENAN/observability/README_IT.md) — [Portugues](Programma_CS2_RENAN/observability/README_PT.md)
- [Visualizacao & Geracao de Relatorios](Programma_CS2_RENAN/reporting/README.md) — [Italiano](Programma_CS2_RENAN/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/reporting/README_PT.md)

---

## Licenca

Este projeto e duplamente licenciado. Copyright (c) 2025-2026 Renan Augusto Macena.

Voce pode escolher entre:
- **Licenca Proprietaria** -- Todos os Direitos Reservados (padrao). Visualizacao para fins educacionais e permitida.
- **Apache License 2.0** -- Open source permissiva com protecao de patentes.

Consulte [LICENSE](LICENSE) para os termos completos.

---

## Autor

**Renan Augusto Macena**

Construido com paixao por um jogador de Counter-Strike com mais de 10.000 horas desde 2004, combinando profundo conhecimento do jogo com engenharia de IA para criar o sistema de coaching definitivo.

> *"Eu sempre desejei um guia profissional -- como os jogadores profissionais de verdade tem -- para entender como realmente parece quando alguem treina do jeito certo e joga do jeito certo."*

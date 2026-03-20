# Macena CS2 Analyzer

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
- [Maturidade do Sistema](#maturidade-do-sistema)
- [Documentacao](#documentacao)
- [Alimentando o Coach](#alimentando-o-coach)
- [Solucao de Problemas](#solucao-de-problemas)
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

- **Arquitetura Dual UI** -- Frontend PySide6/Qt (primario) com fallback legacy Kivy/KivyMD, ambos com padrao MVVM
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

### 5. Verificar Instalacao

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 6. Iniciar

```bash
# Aplicacao desktop (GUI Qt -- primaria)
python -m Programma_CS2_RENAN.apps.qt_app.app

# Aplicacao desktop (GUI Kivy -- fallback legacy)
python Programma_CS2_RENAN/main.py

# Console interativo (TUI live com paineis em tempo real)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Para o guia completo com configuracao de API, walkthroughs de funcionalidades e solucao de problemas, consulte o [Guia do Usuario](docs/USER_GUIDE_PT.md).

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

Mapas multi-nivel (Nuke, Vertigo) usam cutoffs no eixo Z para separar nivel superior e inferior para renderizacao 2D precisa.

---

## Stack Tecnologico

| Categoria | Pacote | Proposito |
|-----------|--------|-----------|
| **ML Framework** | PyTorch | Treinamento e inferencia de redes neurais |
| **Redes Recorrentes** | ncps | Redes Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | Camadas de rede Hopfield para memoria |
| **Parsing de Demo** | demoparser2 | Parsing a nivel de tick de arquivos demo CS2 |
| **Framework UI (primario)** | PySide6 | GUI desktop cross-platform baseada em Qt |
| **Framework UI (legacy)** | Kivy + KivyMD | GUI de fallback legacy |
| **ORM de Banco de Dados** | SQLAlchemy + SQLModel | Modelos e consultas de banco de dados |
| **Migracoes** | Alembic | Migracoes de schema de banco de dados |
| **Web Scraping** | Playwright | Browser headless para HLTV |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Computacao numerica e analise |
| **Seguranca** | cryptography | Criptografia de credenciais |
| **TUI** | Rich | UI de terminal para modo console |
| **Testes** | pytest + pytest-cov | Framework de testes e cobertura |
| **Empacotamento** | PyInstaller | Distribuicao binaria |

---

## Pontos de Entrada

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

UI de terminal com paineis em tempo real para desenvolvimento e controle de runtime.

### CLI de Producao (Goliath)

```bash
python goliath.py <comando>
```

Orquestrador master para builds de producao, releases e diagnosticos.

### Runner de Ciclo de Treinamento

```bash
python run_full_training_cycle.py
```

Script standalone que executa um ciclo de treinamento completo fora do daemon engine.

---

## Validacao e Qualidade

| Ferramenta | Escopo | Comando | Verificacoes |
|------------|--------|---------|--------------|
| Headless Validator | Gate de regressao primario | `python tools/headless_validator.py` | 291+ checks |
| Suite Pytest | Testes logicos e integracao | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 1,515+ testes |
| Feature Audit | Integridade de feature engineering | `python tools/Feature_Audit.py` | Dimensoes de vetor, ranges |
| Portability Test | Compatibilidade cross-platform | `python tools/portability_test.py` | Checks de importacao, caminhos |
| Safety Verifier | Verificacoes de seguranca | `python tools/verify_all_safe.py` | RASP, varredura de segredos |
| DB Health | Diagnostico de banco de dados | `python tools/db_health_diagnostic.py` | Schema, modo WAL, integridade |

**Gate CI/CD:** O headless validator deve retornar exit code 0 antes que qualquer commit seja considerado valido. A pipeline CI roda em Ubuntu e Windows com GitHub Actions SHA-pinned.

---

## Suporte Multi-Idioma

| Idioma | UI | Guia do Usuario | README |
|--------|----|----------------|--------|
| English | Completo | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completo | [docs/USER_GUIDE_IT.md](docs/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completo | [docs/USER_GUIDE_PT.md](docs/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

O idioma pode ser alterado em tempo de execucao nas Configuracoes sem reiniciar a aplicacao.

---

## Funcionalidades de Seguranca

- **Manifesto de Integridade RASP** -- Hashes SHA-256 de todos os arquivos fonte criticos, verificados na inicializacao
- **Integracao OS Keyring** -- Chaves de API armazenadas no Windows Credential Manager / keyring do Linux, nunca em texto puro
- **SQLite WAL Mode** -- Write-Ahead Logging para acesso concorrente seguro em todos os bancos de dados
- **Validacao de Entrada** -- Modelos Pydantic na fronteira de ingestao, consultas SQL parametrizadas
- **Logging Estruturado** -- Namespace `get_logger("cs2analyzer.<modulo>")`, nenhum PII nos logs

---

## Maturidade do Sistema

| Subsistema | Status | Pontuacao | Notas |
|-----------|--------|-----------|-------|
| Coaching COPER | OPERACIONAL | 8/10 | Experience bank + RAG + referencias pro. Funciona imediatamente. |
| Motor Analitico | OPERACIONAL | 6/10 | Rating HLTV 2.0, analise de rounds, timeline de economia. |
| JEPA Base (InfoNCE) | OPERACIONAL | 7/10 | Pre-treinamento auto-supervisionado, target encoder EMA. |
| Neural Role Head | OPERACIONAL | 7/10 | MLP de 5 papeis com KL-divergence, consensus gating. |
| RAP Coach (7 camadas) | LIMITADO | 3/10 | Arquitetura completa (LTC+Hopfield), necessita 200+ demos. |
| VL-JEPA (16 conceitos) | LIMITADO | 2/10 | Alinhamento conceitual implementado, qualidade de labels melhorando. |

---

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [Guia do Usuario (PT)](docs/USER_GUIDE_PT.md) | Instalacao, setup wizard, chaves API, todas as telas, solucao de problemas |
| [User Guide (EN)](docs/USER_GUIDE.md) | Guia completo do usuario em ingles |
| [Guida Utente (IT)](docs/USER_GUIDE_IT.md) | Guia do usuario em italiano |
| [Arquitetura Parte 1](docs/AI-cs2-coach-part1.md) | Design do sistema e arquitetura core |
| [Arquitetura Parte 2](docs/AI-cs2-coach-part2.md) | Subsistemas de redes neurais |
| [Arquitetura Parte 3](docs/AI-cs2-coach-part3.md) | Pipeline de coaching e gerenciamento de conhecimento |

A pasta `docs/Studies/` contem 17 papers de pesquisa sobre as fundacoes teoricas de cada subsistema.

---

## Alimentando o Coach

O coach IA e fornecido sem conhecimento pre-treinado. Aprende exclusivamente de arquivos demo profissionais CS2.

| Demos Pro | Nivel | Confianca | O Que Acontece |
|-----------|-------|-----------|----------------|
| 0-9 | Nao pronto | 0% | Minimo de 10 demos pro necessarias para o primeiro ciclo de treinamento |
| 10-49 | CALIBRATING | 50% | Coaching base ativo, conselhos marcados como provisorios |
| 50-199 | LEARNING | 80% | Confiabilidade crescente, cada vez mais personalizado |
| 200+ | MATURE | 100% | Confianca total, precisao maxima |

### Onde Encontrar Demos Pro

1. Acesse [hltv.org](https://www.hltv.org) > Results
2. Filtre por eventos top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League
3. Selecione partidas de equipes do top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefira series BO3/BO5 para maximizar dados de treinamento por download
5. Diversifique em todos os mapas Active Duty

---

## Solucao de Problemas

| Problema | Solucao |
|----------|---------|
| `ModuleNotFoundError: No module named 'PySide6'` | Instale as dependencias Qt: `pip install PySide6` |
| `ModuleNotFoundError: No module named 'kivy'` | Para a UI legacy: `pip install Kivy==2.3.0 KivyMD==1.2.0` (mais kivy-deps no Windows) |
| `CUDA not available` | Verifique o driver com `nvidia-smi`, reinstale PyTorch com `--index-url https://download.pytorch.org/whl/cu121` |
| `database is locked` | Feche todos os processos Python e reinicie |
| Reset para estado de fabrica | Delete `Programma_CS2_RENAN/user_settings.json` e reinicie |

---

## Licenca

Este projeto e duplamente licenciado. Copyright (c) 2025-2026 Renan Augusto Macena.

- **Licenca Proprietaria** -- Todos os Direitos Reservados (padrao). Visualizacao para fins educacionais permitida.
- **Apache License 2.0** -- Open source permissiva com protecao de patentes.

Consulte [LICENSE](LICENSE) para os termos completos.

---

## Autor

**Renan Augusto Macena**

Construido com paixao por um jogador de Counter-Strike com mais de 10.000 horas desde 2004, combinando profundo conhecimento do jogo com engenharia de IA para criar o sistema de coaching definitivo.

> *"Eu sempre quis um guia profissional -- como os verdadeiros jogadores profissionais tem -- para entender como realmente e quando alguem treina do jeito certo e joga do jeito certo."*

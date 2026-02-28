> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# RAP Coach — Arquitetura Recorrente de 6 Camadas

RAP (Recurrent Architecture for Pedagogy) Coach implementa uma arquitetura neural de 6 camadas com memória LTC-Hopfield para coaching tático.

## Camadas da Arquitetura

### Camada 1: Percepção
- **perception.py** — `RAPPerception`, `ResNetBlock` — Camada de percepção baseada em CNN para extração de características visuais de tensores de 5 canais (cone de visão, contexto do mapa, movimento, zonas de perigo, posições de companheiros)

### Camada 2: Memória
- **memory.py** — `RAPMemory` — Rede neural LTC (Liquid Time-Constant) com memória associativa Hopfield (512 slots). Armazena padrões táticos com recuperação endereçável por conteúdo. Usa `ncps.LTC` + `hflayers.Hopfield`.

### Camada 3: Estratégia
- **strategy.py** — `RAPStrategy`, `ContextualAttention` — Camada de otimização de decisão com mecanismo de atenção contextual para planejamento tático

### Camada 4: Pedagogia
- **pedagogy.py** — `RAPPedagogy`, `CausalAttributor` — Estimativa de valor e atribuição causal para geração de feedback de coaching

### Camada 5: Comunicação
- **communication.py** — `RAPCommunication` — Camada de saída produzindo recomendações de coaching com pontuações de confiança

### Camada 6: Classificação de Função
- **NeuralRoleHead** (em `model.py`) — Classificador de funções de 5 classes (Entry/Lurk/Support/AWP/IGL) com mecanismo de consenso

## Módulos de Suporte

- **model.py** — `RAPCoachModel` — Orquestração completa do RAP Coach integrando todas as 6 camadas
- **trainer.py** — `RAPTrainer` — Orquestração de treinamento com suporte a callbacks para TensorBoard/Observatory
- **chronovisor_scanner.py** — `ChronovisorScanner`, `CriticalMoment` — Detecção de momentos críticos em múltiplas escalas (escalas de tempo micro/padrão/macro)
- **skill_model.py** — `SkillLatentModel`, `SkillAxes` — Representação de eixos de habilidade do jogador (espaço latente estilo VAE)

## Dependências
PyTorch, ncps (LTC), hflayers (Hopfield), NumPy.

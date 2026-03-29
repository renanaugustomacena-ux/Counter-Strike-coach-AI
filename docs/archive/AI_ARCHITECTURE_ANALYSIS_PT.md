# CS2 Coach AI — Analise Completa da Arquitetura

> **Data:** 17 de marco de 2026
> **Escopo:** Auditoria completa da arquitetura de IA/ML — redes neurais, teoria dos jogos, pipeline de coaching, orquestracao de treinamento, pipeline de dados, esquema do banco de dados, geracao de tensores, motor de inferencia
> **Objetivo:** Documento de referencia abrangente para entender cada componente do sistema de IA

---

## Indice

1. [O Vetor de Features (METADATA_DIM = 25)](#1-o-vetor-de-features)
2. [Pipeline de Dados: Da Demo ate as Features](#2-pipeline-de-dados)
3. [Esquema do Banco de Dados](#3-esquema-do-banco-de-dados)
4. [JEPA — Pre-treinamento Auto-supervisionado](#4-jepa)
5. [VL-JEPA — Conceitos de Coaching Interpretaveis](#5-vl-jepa)
6. [RAP Coach — O Cerebro do Jogador Fantasma](#6-rap-coach)
7. [Coach Legado (AdvancedCoachNN)](#7-coach-legado)
8. [Fabrica de Tensores — Entradas Visuais](#8-fabrica-de-tensores)
9. [Motores de Teoria dos Jogos](#9-motores-de-teoria-dos-jogos)
10. [Pipeline de Coaching COPER](#10-pipeline-de-coaching-coper)
11. [Orquestrador de Analise (Fase 6)](#11-orquestrador-de-analise)
12. [Orquestracao de Treinamento (5 Fases)](#12-orquestracao-de-treinamento)
13. [Fabrica de Modelos e Carregamento de Checkpoints](#13-fabrica-de-modelos)
14. [Inferencia GhostEngine](#14-ghost-engine)
15. [Decodificacao Seletiva e Inferencia com Estado](#15-decodificacao-seletiva)
16. [Motor de Sessao Tri-Daemon](#16-motor-de-sessao)
17. [Constantes Dimensionais Chave](#17-constantes-chave)
18. [Avaliacao Honesta de Engenharia](#18-avaliacao-honesta)

---

## 1. O Vetor de Features

**Arquivo:** `backend/processing/feature_engineering/vectorizer.py`

Cada tick de cada demo e comprimido em um vetor de 25 numeros. Essa e a linguagem universal que todos os modelos falam.

| Indice | Feature | Faixa | Normalizacao |
|--------|---------|-------|--------------|
| 0 | health (vida) | 0-1 | / 100 |
| 1 | armor (colete) | 0-1 | / 100 |
| 2 | has_helmet (tem capacete) | 0/1 | binario |
| 3 | has_defuser (tem kit) | 0/1 | binario |
| 4 | equipment_value (valor do equipamento) | 0-1 | / 10.000 |
| 5 | is_crouching (agachado) | 0/1 | binario |
| 6 | is_scoped (com mira) | 0/1 | binario |
| 7 | is_blinded (cego por flash) | 0/1 | binario |
| 8 | enemies_visible (inimigos visiveis) | 0-1 | contagem / 5 |
| 9 | pos_x | -1 a 1 | / 4.096 |
| 10 | pos_y | -1 a 1 | / 4.096 |
| 11 | pos_z | -1 a 1 | / 1.024 |
| 12 | view_yaw_sin | -1 a 1 | sin(yaw) — codificacao ciclica evita descontinuidade 359-para-0 |
| 13 | view_yaw_cos | -1 a 1 | cos(yaw) — pareado com sin para rotacao suave |
| 14 | view_pitch | -1 a 1 | / 90 |
| 15 | z_penalty | 0-1 | distintividade do nivel vertical |
| 16 | kast_estimate | 0-1 | Razao Kill/Assist/Survive/Trade |
| 17 | map_id | 0-1 | hash MD5 % 10000 / 10000 (deterministico por mapa) |
| 18 | round_phase (fase do round) | 0/0.33/0.66/1 | pistol/eco/forcada/buy completo |
| 19 | weapon_class (classe da arma) | 0-1 | faca=0, pistola=0.2, SMG=0.4, rifle=0.6, sniper=0.8, pesada=1.0 |
| 20 | time_in_round (tempo no round) | 0-1 | decorrido / 115 segundos |
| 21 | bomb_planted (bomba plantada) | 0/1 | binario |
| 22 | teammates_alive (aliados vivos) | 0-1 | contagem / 4 |
| 23 | enemies_alive (inimigos vivos) | 0-1 | contagem / 5 |
| 24 | team_economy (economia do time) | 0-1 | dinheiro medio do time / 16.000 |

**Limites de fase do round** (de `base_features.py`):
- Eco: dinheiro do time < $1.500
- Forcada: $1.500 - $3.000
- Forcada-buy: $3.000 - $4.000
- Buy completo: > $4.000

---

## 2. Pipeline de Dados

**Arquivo:** `ingestion/demo_loader.py`

### Parsing de Demo em 3 Passadas

Cada arquivo `.dem` passa por tres passadas sequenciais usando a biblioteca `demoparser2`:

**Passada 1 — Extracao de Posicao:**
- Extrai posicoes dos jogadores em cada tick
- Constroi `pos_by_tick[tick] = {steamid: (x, y, z)}`
- Leve — apenas coordenadas

**Passada 2 — Vinculacao de Granadas:**
- Processa eventos de inicio/fim de granadas
- Associa dados de arremesso com trajetoria e impacto
- Rastreia: `base_id`, `nade_type`, `x/y/z`, `starting_tick`, `ending_tick`, `throw_tick`, `trajectory`, `thrower_id`
- Teto heuristico: granadas sem evento de fim sao limitadas a 20 x tick_rate (flag `is_duration_estimated = True`)
- Janela de dissipacao: 5 x tick_rate

**Passada 3 — Extracao de Estado Completo:**
- Constroi objetos PlayerState completos com 25 campos por tick
- Segmentacao multi-mapa (detecta mudancas de mapa dentro de uma unica demo)
- Usa eventos `round_freeze_end` para detectar limites de round
- Resolucao de dinheiro: unifica variantes de campo (`balance`, `cash`, `money`, `m_iAccount`)
- Resolucao de time: correspondencia vetorizada de strings (CT/TER/SPEC)

### Sistema de Cache
- Versao do cache: `v21_vectorized_parse` (colunas pre-vetorizadas para speedup de 10x)
- Assinado com HMAC e escrita atomica (previne corrupcao)
- Desserializador seguro restrito apenas a classes do modulo `demo_frame` (seguranca)
- Invalidacao de cache: incompatibilidade de tamanho do arquivo + string de versao

### Enriquecimento de Tick (Features 20-24)
Apos o parsing, cada tick e enriquecido com features contextuais:
- `time_in_round`: calculado a partir do tick de inicio do round
- `bomb_planted`: dos eventos do jogo
- `teammates_alive` / `enemies_alive`: do estado dos jogadores por tick
- `team_economy`: media entre os membros do time

### Estrategia de Divisao dos Dados
- **Divisao cronologica 70/15/15** por data da partida (previne vazamento temporal)
- **Descontaminacao de jogadores**: cada jogador aparece em APENAS UMA divisao
- **Remocao de outliers**: IQR 3.0x (cerca externa de Tukey)
- **StandardScaler**: ajustado apenas na divisao de treino, aplicado em validacao/teste

---

## 3. Esquema do Banco de Dados

**Arquivo:** `backend/storage/db_models.py`

Todos os bancos de dados usam SQLite em modo WAL (Write-Ahead Logging) para acesso concorrente.

### PlayerMatchStats (agregados por partida)
25 campos estatisticos por jogador por partida:
- **Principais:** kills, deaths, ADR, headshot%, KAST
- **Variancia:** kill_std, adr_std, razao K/D
- **Duelos:** opening_duel_win_pct, clutch_win_pct, trade_kill_ratio
- **Utilidades:** flash_assists, dano HE/round, dano molotov/round, smokes/round
- **Ratings HLTV 2.0:** impact, survival, KAST, KPR, ADR
- **Flags:** `is_pro` (booleano), `dataset_split` (train/val/test), `data_quality` (string)

### PlayerTickState (estado por tick, ~17,3M linhas para 11 demos)
19 campos por tick por jogador:
- Posicao (x, y, z), angulos de visao (codificacao sin/cos), vida, colete
- Agachado, com mira, cego, arma ativa, valor do equipamento
- Inimigos visiveis, numero do round, tempo no round, bomba plantada
- Aliados vivos, inimigos vivos, economia do time, nome do mapa

### RoundStats (por round por jogador)
- Kills, deaths, assists, dano causado, kills com headshot
- Trade kills, foi tradado, opening kill/death
- Utilidades: dano HE, dano molotov, flashes lancadas, smokes lancadas
- Valor do equipamento, round vencido, MVP, rating do round

### CoachingExperience (Banco de Experiencias para COPER)
- Contexto: mapa, fase do round, lado, area da posicao
- Estado do jogo: snapshot JSON (maximo 16KB)
- Acao/resultado: o que foi feito, resultado (kill/death/trade/objetivo/sobreviveu)
- Referencia pro: nome do jogador + ID da partida
- Embedding: vetor de 384 dimensoes (codificado em JSON)
- Loop de feedback: pontuacao de efetividade, vezes seguida

### CoachState (singleton, id=1)
- Status de treinamento (Pausado/Treinando/Ocioso/Erro)
- Epoca atual, total de epocas, loss de treino/validacao, ETA
- Heartbeat, carga de CPU/memoria do sistema
- Maturidade: total_matches_processed

### ProPlayerStatCard (estatisticas HLTV)
- Rating 2.0, DPR, KAST, impact, ADR, KPR, headshot%
- Razao de opening kill, clutch wins, rounds multikill
- Periodo: all_time / last_3_months / 2024

### TacticalKnowledge (base de conhecimento RAG)
- Titulo, descricao, categoria (posicionamento/economia/utilidades/mira)
- Mapa, contexto da situacao, exemplo pro
- Embedding: vetor de 384 dimensoes para busca por similaridade

### DataLineage (trilha de auditoria)
- Somente insercao: rastrea cada entidade ate a demo de origem, tick e versao do pipeline

---

## 4. JEPA

**Arquivo:** `backend/nn/jepa_model.py`
**Significado:** Joint-Embedding Predictive Architecture (de Yann LeCun / Meta AI)

### Proposito
Aprender representacoes de estados de jogo sem rotulos. Assiste demos de profissionais e aprende como "jogo bom normal" se parece em um espaco latente comprimido de 256 dimensoes.

### Como Funciona (Conceitual)
Dada uma janela de ticks do jogo (o "contexto"), prever como sera a PROXIMA janela (o "alvo") — mas na representacao comprimida de 256 dimensoes, nao nas features brutas de 25 dimensoes. Isso forca o modelo a entender causa-e-efeito no CS2: "Se um jogador esta aqui com esta arma e ve dois inimigos, o que acontece depois?"

### Arquitetura

```
JEPACoachingModel
├── Context Encoder (JEPAEncoder) — treinado por gradiente
│   └── Linear(25→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256) + LayerNorm
│       Saida: [B, seq_len, 256]
│
├── Target Encoder (mesma arquitetura) — apenas EMA, SEM gradientes
│   └── Atualizado: target = 0.996 × target + 0.004 × context
│       Nunca recebe gradiente. Apenas copia lentamente do context encoder.
│
├── Predictor (JEPAPredictor) — mapeia contexto para alvo previsto
│   └── Linear(256→512) + LayerNorm + GELU + Dropout(0.1)
│       Linear(512→256)
│       Entrada: contexto com mean-pooling [B, 256]
│       Saida: alvo previsto [B, 256]
│
├── Cabeca de Coaching LSTM (2 camadas, hidden=128, dropout=0.2)
│   └── Entrada: [B, seq_len, 256] do context encoder
│       Saida: [B, seq_len, 128] processamento temporal
│
├── Mixture of Experts (3 especialistas) — coaching especializado
│   └── Gate: Linear(128→3) + Softmax → "em qual especialista confiar?"
│       Especialista 1: Linear(128→128) + ReLU + Linear(128→10)
│       Especialista 2: mesma arquitetura
│       Especialista 3: mesma arquitetura
│       Soma ponderada das saidas dos especialistas
│
└── Saida: tanh([B, 10]) → vetor de coaching em [-1, 1]
```

### Protocolo de Treinamento em Duas Etapas

**Etapa 1 — Pre-treinamento JEPA (auto-supervisionado, sem rotulos necessarios):**

```
Sequencias de ticks de demos profissionais
    │
    ├── Janela de contexto [B, context_len, 25]
    │         │
    │         ▼
    │   Context Encoder → [B, context_len, 256]
    │         │
    │         ▼
    │   Mean Pool → [B, 256]
    │         │
    │         ▼
    │   Predictor → alvo_previsto [B, 256]
    │
    └── Janela alvo [B, target_len, 25]
              │
              ▼
        Target Encoder (no_grad) → [B, target_len, 256]
              │
              ▼
        Mean Pool → alvo_real [B, 256]

Loss: "O alvo_previsto esta mais proximo do alvo_real
       do que de alvos aleatorios?"
       → Loss contrastiva InfoNCE
```

**Etapa 2 — Fine-tuning (supervisionado, precisa de rotulos de coaching):**
- Congela ambos os encoders (`requires_grad = False`)
- Treina apenas LSTM + especialistas MoE com targets de coaching usando loss MSE
- Encoders se tornam extratores de features fixos

### Loss InfoNCE (Passo a Passo)

```
1. Normaliza tudo para a esfera unitaria (norma L2):
   pred    = normalize(pred)        → vetores unitarios [B, 256]
   target  = normalize(target)      → vetores unitarios [B, 256]
   negs    = normalize(negativos)   → vetores unitarios [B, K, 256]

2. Similaridade positiva (quao proximo a previsao esta do alvo REAL?):
   pos_sim = produto_escalar(pred, target) / 0.07
   Divisao pela temperatura=0.07 aguça a distribuicao

3. Similaridades negativas (quao proximo a previsao esta dos alvos ERRADOS?):
   neg_sim = produto_escalar(pred, cada_negativo) / 0.07
   [B, K] — uma pontuacao por negativo por amostra

4. Empilha em logits de classificacao:
   logits = [pos_sim, neg_sim₁, neg_sim₂, ..., neg_simₖ]
   [B, K+1] — posicao 0 e a resposta correta

5. Loss de cross-entropy:
   labels = [0, 0, 0, ...] (classe correta sempre no indice 0)
   loss = -log(exp(pos_sim) / (exp(pos_sim) + Σexp(neg_sim)))
```

### Negativos In-Batch (O(B²) — Sem Memoria Extra Necessaria)

```
Para batch de tamanho B, codifica todas as B janelas alvo:
  all_encoded = target_encoder(x_target).mean(dim=1)  → [B, 256]

Para amostra i, negativos = todas as OUTRAS amostras:
  negativos[i] = all_encoded[j] para todo j ≠ i   → [B-1, 256]

Resultado: [B, B-1, 256] — cada amostra tem B-1 negativos de graca
Pula batches onde B < 2 (precisa de pelo menos 2 amostras para contraste)
```

### Atualizacao EMA (Mecanismo Anti-Colapso)

Apos cada passo de treinamento:
```
pesos_target = 0.996 × pesos_target + 0.004 × pesos_context
```

**Por que?** Sem isso, o modelo pode "colapsar" — produzir o mesmo embedding para tudo (similaridade trivialmente perfeita = loss zero, mas inutil). O target encoder FICA ATRASADO em relacao ao context encoder por ~250 passos (1/0.004), criando um alvo movel que previne o colapso.

**Verificacao de seguranca (NN-JM-04):** Antes de cada atualizacao EMA, verifica se `target_encoder.requires_grad == False`. Se violado → `RuntimeError` imediato.

### Monitor de Saude de Embeddings (P9-02)
```
variancia = embeddings.var(dim=0).mean()
se variancia < 0.01 → AVISO: risco de colapso (todos os embeddings convergindo)
se variancia ≥ 0.01 → saudavel (embeddings estao espalhados no espaco)
```

### Deteccao de Drift e Re-treinamento Automatico
- Monitora Z-scores dos dados de validacao vs estatisticas de referencia do treino
- Z-score > 2.5 → drift detectado (meta do jogo mudou)
- 5 verificacoes consecutivas de drift → aciona re-treinamento completo (10 epocas)
- Reinicia scheduler de learning rate e historico de drift apos re-treinamento

---

## 5. VL-JEPA

**Arquivo:** `backend/nn/jepa_model.py` (classe `VLJEPACoachingModel`, estende `JEPACoachingModel`)

### Proposito
Estende o JEPA com 16 conceitos de coaching interpretaveis para que o modelo possa explicar POR QUE da conselhos especificos. Em vez de apenas um vetor de coaching de 10 numeros, voce obtem: "Este tick e 80% positioning_exposed, 60% engagement_unfavorable."

### 16 Conceitos de Coaching

| ID | Conceito | Categoria | O que significa |
|----|----------|-----------|-----------------|
| 0 | positioning_aggressive | Posicionamento | Avancando angulos, lutas de curta distancia |
| 1 | positioning_passive | Posicionamento | Segurando angulos longos, evitando contato |
| 2 | positioning_exposed | Posicionamento | Posicao vulneravel, alto risco de morte |
| 3 | utility_effective | Utilidades | Granadas criando vantagem real |
| 4 | utility_wasteful | Utilidades | Morrendo com utilidades nao usadas, baixo impacto |
| 5 | economy_efficient | Decisao | Equipamento compativel com expectativas do round |
| 6 | economy_wasteful | Decisao | Forcando buy em rounds ruins |
| 7 | engagement_favorable | Confronto | Aceitando lutas com vantagem de HP/posicao/numeros |
| 8 | engagement_unfavorable | Confronto | Em desvantagem numerica, HP baixo, angulos ruins |
| 9 | trade_responsive | Confronto | Trades rapidos de aliados, boa coordenacao |
| 10 | trade_isolated | Confronto | Morrendo sem trade, longe demais do time |
| 11 | rotation_fast | Decisao | Rotacao posicional rapida apos informacao |
| 12 | information_gathered | Decisao | Bom reconhecimento, multiplos inimigos avistados |
| 13 | momentum_leveraged | Psicologia | Capitalizando sequencias quentes |
| 14 | clutch_composed | Psicologia | Decisoes calmas em situacoes 1vN |
| 15 | aggression_calibrated | Psicologia | Nivel de agressividade correto para a situacao |

### Como os Conceitos Funcionam

```
Estado do jogo [B, seq_len, 25]
  │
  ▼
Context Encoder → [B, seq_len, 256]
  │
  ▼
Mean Pool → [B, 256]
  │
  ▼
Projetor de Conceitos: Linear(256→256) + GELU + Linear(256→256) + normalizacao L2
  │
  ▼
projetado [B, 256] (vetor unitario na esfera)

Compara com 16 Embeddings de Conceitos aprendiveis [16, 256]:
  similaridade_cosseno = projetado × concept_embeddings.T  → [B, 16]

Escala de temperatura (aprendivel, inicializada 0.07, limitada [0.01, 1.0]):
  logits_escalados = similaridade_cosseno / temperatura

Softmax → [B, 16] distribuicao de probabilidade sobre conceitos
```

### Duas Formas de Gerar Rotulos de Conceitos

**Baseada em resultado (preferida, sem vazamento de dados):** Usa dados de RoundStats — kills, deaths, dano, round ganho/perdido, trade kills, uso de utilidades. Exemplos:
- Conseguiu opening kill + sobreviveu → `positioning_aggressive = 0.8`
- Morreu primeiro com < 40 de dano → `positioning_exposed = 0.6`
- Ganhou round eco com < $2000 de equipamento → `economy_efficient = 0.9`
- Trade kills > 0 → `trade_responsive = 0.6 + 0.2 por kill`

**Fallback heuristico (risco de vazamento de rotulos):** Deriva rotulos das mesmas features de entrada de 25 dimensoes. O modelo pode "trapacear" reconstruindo o mapeamento entrada→rotulo. Um aviso e registrado quando esse caminho e usado.

### Funcao de Loss do VL-JEPA
```
loss_total = InfoNCE + α × conceito_BCE + β × loss_diversidade

Onde:
  loss_conceito = Binary Cross-Entropy(logits, rotulos_suaves)
    Cada conceito e uma classificacao binaria independente (multi-rotulo, nao one-hot)

  loss_diversidade = -media(desvio_padrao_por_dimensao(concept_embeddings))
    Penaliza todos os 16 conceitos se agrupando no mesmo lugar
    Inspirado pelo VICReg (Variance-Invariance-Covariance Regularization)

Pesos padrao: α=0.5, β=0.1
```

---

## 6. RAP Coach

**Arquivos:** `backend/nn/experimental/rap_coach/`
**Significado:** Recurrent Attention-based Pedagogy (Pedagogia Baseada em Atencao Recorrente)

### Proposito
Um cerebro de "jogador fantasma" com 7 camadas que recebe tensores visuais (mapa, visao, movimento) + metadados, e produz: onde voce deveria estar, o que deveria fazer, quao boa esta sua situacao e por que voce esta cometendo erros.

### Camada 1: PERCEPCAO (perception.py)

Tres fluxos de processamento visual inspirados em neurociencia (vias ventral "o que" / dorsal "onde"):

```
Quadro de Visao [B, 3, H, W]  (o que eu vejo?)
  → Backbone ResNet: Conv2d(3→64, stride=2) + BatchNorm + ReLU
    + 4 blocos residuais (64→64), cada: conv3×3→BN→ReLU→conv3×3→BN + atalho
  → AdaptiveAvgPool2d(1,1) → [B, 64]

Quadro do Mapa [B, 3, H, W]  (onde eu estou no mapa?)
  → Backbone ResNet: Conv2d(3→32, stride=2) + BatchNorm + ReLU
    + 3 blocos residuais (32→32)
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Quadro de Movimento [B, 3, H, W]  (o que esta se movendo?)
  → Conv2d(3→16, 3×3) + ReLU + MaxPool2d(2)
  → Conv2d(16→32, 3×3) + ReLU
  → AdaptiveAvgPool2d(1,1) → [B, 32]

Concatena os tres: [64 + 32 + 32] = [B, 128] vetor de percepcao
```

### Camada 2: MEMORIA (memory.py)

**Rede Liquid Time-Constant (LTC):**
- Neuronios inspirados no cerebro com constantes de tempo ADAPTATIVAS — respondem de forma diferente a mudancas rapidas vs lentas
- Usa `AutoNCP(units=512, output_size=256)` — fiacao Neural Circuit Policy esparsa e biologicamente plausivel
- Entrada: [B, T, 153] (128 percepcao + 25 metadados concatenados)
- Propriedade chave: lida naturalmente com taxas de quadro variaveis (demos de CS2 nem sempre sao 64 ticks/s)
- RNG semeado deterministicamente: `np.random.seed(42)` + `torch.manual_seed(42)`

**Memoria Associativa Hopfield:**
- 4 cabecas de atencao, dimensao de padrao 256
- Pense nela como: armazena "situacoes prototipo" (jogadas taticas perfeitas)
- Padroes inicializados aleatoriamente (randn x 0.02), moldados apenas por descida de gradiente durante o treinamento
- **Guarda de seguranca:** Fica DESLIGADA nas primeiras 2 passadas forward de treinamento (padroes aleatorios adicionariam ruido)
- Apos 2 passadas → `_hopfield_trained = True` → Hopfield e ativada
- Combinada com LTC via conexao residual: `saida = saida_ltc + saida_hopfield`

**Cabeca de Crenca (entendimento interno da situacao):**
```
Linear(256→256) → SiLU → Linear(256→64)
Saida: [B, T, 64] — o "entendimento" comprimido do modelo sobre a situacao atual
```

### Camada 3: ESTRATEGIA (strategy.py)

4 Mixture-of-Experts com Camadas de Superposicao com gate de contexto:

```
Para cada um dos 4 especialistas:
  SuperpositionLayer(256→128, context=25) → ReLU → Linear(128→10)

Gate: Linear(256→4) → Softmax → [B, 4] pesos dos especialistas

Final = Σ(saida_especialista × peso_gate) → [B, 10] vetor de estrategia
```

**Camada de Superposicao** (o mecanismo de gating):
```python
out = F.linear(x, weight, bias)         # Linear padrao: [B, 128]
gate = sigmoid(context_gate(metadata))   # Contexto determina relevancia: [B, 128]
return out * gate                        # Element-wise: neuronios irrelevantes suprimidos
```

### Camada 4: AVALIACAO (pedagogy.py)

**Critico (funcao de valor):**
```
Linear(256→64) → ReLU → Linear(64→1) → V(s)
"Quao bom e este estado do jogo?" (escalar unico)
```

**Adaptador de Habilidade:**
```
Linear(10→256)
Se skill_vec fornecido: hidden = hidden + skill_adapter(skill_vec)
Ajusta as expectativas do modelo baseado no nivel de habilidade do jogador (escala 1-10)
```

### Camada 5: POSICIONAMENTO

```
Linear(256→3) → [dx, dy, dz]
Na inferencia, escalado por RAP_POSITION_SCALE = 500.0 unidades do jogo
ghost_x = atual_x + dx × 500.0
ghost_y = atual_y + dy × 500.0
```

**Eixo Z recebe penalidade 2x** durante o treinamento porque estar no andar errado no CS2 = morte instantanea.

### Camada 6: ATRIBUICAO

5 canais de explicacao de erro: **Posicionamento, Mira, Agressividade, Utilidades, Rotacao**

```
Cabeca de Relevancia: Linear(256→32) → ReLU → Linear(32→5) → Sigmoid → [B, 5]

Combina pesos de relevancia neurais com medicoes mecanicas de erro:
  atribuicao[0] = relevancia[0] × ||delta_posicao||     (Posicionamento)
  atribuicao[1] = relevancia[1] × ||delta_mira||        (Mira)
  atribuicao[2] = relevancia[2] × ||delta_pos|| × 0.5   (Agressividade)
  atribuicao[3] = relevancia[3] × sigmoid(hidden.mean()) (Utilidades — apenas neural)
  atribuicao[4] = relevancia[4] × ||delta_pos|| × 0.8   (Rotacao)
```

### Loss de Treinamento do RAP

```
total = 1.0 × MSE(previsao_estrategia, alvo_estrategia)
      + 0.5 × MSE(previsao_valor, alvo_valor)       (com mascara para dados ausentes)
      + 1.0 × L1(pesos_gate) × 1e-4                 (regularizacao de esparsidade)
      + 1.0 × MSE_ponderado(previsao_posicao, alvo_posicao)
              onde peso do eixo Z = 2.0

Corte de gradiente: max_norm = 1.0
Otimizador: AdamW(lr=5e-5, weight_decay=1e-4)
```

### Dicionario de Saida Completo do RAP
```python
{
    "advice_probs":    [B, 10],    # Recomendacoes de estrategia (10 papeis taticos)
    "belief_state":    [B, T, 64], # Entendimento interno da situacao
    "value_estimate":  [B, 1],     # Quao bom e este estado? (escalar)
    "gate_weights":    [B, 4],     # Qual especialista dominou a decisao?
    "optimal_pos":     [B, 3],     # Onde voce DEVERIA estar (delta)
    "attribution":     [B, 5],     # Por que voce esta perdendo (5 canais)
    "hidden_state":    (tupla),    # Memoria LSTM persistente para o proximo tick
}
```

---

## 7. Coach Legado

**Arquivo:** `backend/nn/model.py`

O modelo fallback mais simples (AdvancedCoachNN / TeacherRefinementNN):

```
Entrada [B, seq, 25]
  │
  ▼
LSTM(25→128, 2 camadas, dropout=0.2)
  │
  ▼
LayerNorm(128)
  │
  ▼
3 Especialistas MoE:
  Cada: Linear(128→128) + LayerNorm + ReLU + Linear(128→10)
  Gate: Linear(128→3) + Softmax
  │
  ▼
tanh → [B, 10] saida de coaching
```

**Viés de papel (role biasing):** Quando um role_id (0, 1 ou 2) e fornecido:
```
role_bias = [0, 0, 0] com role_bias[role_id] = 1.0
novos_pesos = (pesos_gate + role_bias) / 2.0
→ Especialista preferido e impulsionado de ~33% para ~65%
```

---

## 8. Fabrica de Tensores

**Arquivo:** `backend/processing/tensor_factory.py`

Gera 3 entradas visuais em formato de tensor (mapa, visao, movimento) para o modelo RAP Coach.

### Resolucoes
- **Treinamento:** 64x64 (menor para velocidade)
- **Inferencia:** mapa=128x128, visao=224x224

### Tensor de Mapa — Visao Geral Tatica (3 canais)

| Canal | Modo POV do Jogador | Modo Legado |
|-------|---------------------|-------------|
| Ch0 | Posicoes de aliados (heatmap) | Posicoes de inimigos |
| Ch1 | Posicoes de inimigos (visiveis + ultimas conhecidas com decaimento) | Posicoes de aliados |
| Ch2 | Zonas de utilidades + marcador de bomba (raio de 50 unidades) | Posicao do jogador |

### Tensor de Visao — Perspectiva do Jogador (3 canais)

| Canal | Modo POV do Jogador | Modo Legado |
|-------|---------------------|-------------|
| Ch0 | Mascara de FOV (cone de 90°, ponderado por cosseno, desfoque Gaussiano) | Mascara de FOV |
| Ch1 | Entidades visiveis (heatmap atenuado por distancia) | Zonas de perigo |
| Ch2 | Zonas de utilidades ativas | Zonas seguras |

**Mascara de FOV:** Cone a partir do yaw do jogador ± 45°, com desfoque Gaussiano (sigma=3.0). Distancia de visao = 2000 unidades do jogo.

### Tensor de Movimento — Contexto de Movimentacao (3 canais)

| Canal | Conteudo |
|-------|----------|
| Ch0 | Rastro de trajetoria (ultimos 32 ticks, gradiente de recencia) |
| Ch1 | Gradiente radial de velocidade (maximo 4.0 unidades/tick a 64Hz) |
| Ch2 | Movimento da mira (delta de yaw, maximo 45° por tick) |

### Normalizacao (P-TF-01)
Quando o valor maximo < 1.0, divide por 1.0 (nao pelo max) para evitar amplificacao de ruido. Preserva a magnitude relativa de sinais fracos.

---

## 9. Motores de Teoria dos Jogos

### 9.1 Probabilidade Bayesiana de Morte

**Arquivo:** `backend/analysis/belief_model.py`

Estima "qual a probabilidade deste jogador morrer agora?" usando raciocinio Bayesiano.

**Priors por faixa de HP:**
- Cheio (80-100 HP): 35% de taxa base de morte
- Danificado (40-79 HP): 55% de taxa base de morte
- Critico (1-39 HP): 80% de taxa base de morte

**Multiplicadores de letalidade por arma:** rifle=1.0, AWP=1.4, SMG=0.75, pistola=0.6, shotgun=0.85, faca=0.3

**Calculo do nivel de ameaca:**
```
ameaca = (inimigos_visiveis + inimigos_inferidos × e^(-0.1 × idade_info_segundos) × 0.5) / 5.0
```
Inimigos inferidos perdem relevancia ao longo do tempo (decaimento exponencial com λ=0.1/s).

**Atualizacao de log-odds (posterior Bayesiano):**
```
log_odds = ln(prior / (1-prior))
  + ameaca × 2.0                         [mais inimigos = mais perigo]
  + (mult_arma - 1.0) × 1.5              [AWP = +0.6, pistola = -0.6]
  + (fator_colete - 1.0) × -1.0          [colete reduz taxa de morte]
  + (fator_exposicao - 0.5) × 1.0        [dependente da posicao]

P(morte) = 1 / (1 + e^(-log_odds))       [conversao sigmoide]
```

**Auto-calibracao** a partir de dados reais de partidas (minimo 30 amostras totais, 10 por faixa):
- Recalibra priors de faixa de HP a partir de taxas de morte observadas
- Ajusta letalidade por classe de arma a partir de contagens reais de kills
- Ajusta λ de decaimento de ameaca via minimos quadrados em idade_info → resultado
- Todos os parametros limitados: priors [0.05, 0.95], letalidade [0.1, 3.0], decaimento [0.01, 1.0]
- Salva CalibrationSnapshot no banco de dados (observabilidade)

### 9.2 Arvore de Jogo Expectiminimax

**Arquivo:** `backend/analysis/game_tree.py`

Busca minimax recursiva com modelagem estocastica do oponente — a mesma familia de algoritmos usada em IA de xadrez e bots de poker.

**4 Acoes Disponiveis:** push (avancar), hold (segurar), rotate (rotacionar), use_utility (usar utilidade)

**Estrutura da arvore:**
```
Raiz (MAX — nosso time escolhe a melhor acao)
  ├── PUSH → No de Chance (oponente responde probabilisticamente)
  │            ├── oponente PUSH (p=0.30) → avaliar folha
  │            ├── oponente HOLD (p=0.40) → avaliar folha
  │            ├── oponente ROTATE (p=0.20) → avaliar folha
  │            └── oponente UTILITY (p=0.10) → avaliar folha
  ├── HOLD → No de Chance ...
  ├── ROTATE → No de Chance ...
  └── USE_UTILITY → No de Chance ...
```

**Ajustes de probabilidade do oponente por contexto:**

| Condicao | Push | Hold | Rotate | Utility |
|----------|------|------|--------|---------|
| Round eco (<$2000) | +25% | -25% | — | +15% |
| Buy completo (>$4000) | -5% | +10% | +5% | — |
| Oponente lado T | +5% | -5% | — | — |
| Em desvantagem numerica | -5% | +10% | — | -10% |
| Tempo < 30 segundos | +15% | -10% | — | +5% |
| Perfil aprendido (≥10 rounds) | mescla ate 70% aprendido | 30% base | | |

**Transicoes de estado por acao:**
- PUSH: -1 vivo de cada lado, +0.15 controle de mapa
- HOLD: -15 segundos de tempo
- ROTATE: -10s tempo, ±0.1 controle de mapa
- USE_UTILITY: -1 item de utilidade, +0.05 controle de mapa

**Orcamento:** 1.000 nos maximo (previne estouro de memoria). Tabela de transposicao: 10.000 entradas com despejo FIFO.

**Saida:** Melhor acao + probabilidade de vitoria estimada para o estado atual.

### 9.3 Rastreador de Momentum

**Arquivo:** `backend/analysis/momentum.py`

Rastreia o momentum psicologico como um multiplicador entre 0.7 (tiltado) e 1.4 (on fire):

```
Sequencia de vitorias de N:  multiplicador = 1.0 + 0.05 × N × e^(-0.15 × gap_rounds)
Sequencia de derrotas de N:  multiplicador = 1.0 - 0.04 × N × e^(-0.15 × gap_rounds)

Limites: [0.7 (tilt maximo), 1.4 (maximo quente)]
Limiar de tilt: < 0.85 (~3 derrotas seguidas)
Limiar quente: > 1.2 (~4 vitorias seguidas)
Reseta no intervalo (round 13 para MR12, round 16 para MR13)
```

### 9.4 Analise de Entropia

**Arquivo:** `backend/analysis/entropy_analysis.py`

Mede a efetividade das utilidades em **bits de informacao** usando entropia de Shannon:

```
1. Discretiza o mapa em grade 32×32 (1.024 celulas)
2. Conta posicoes de inimigos por celula ANTES da utilidade
3. H_antes = -Σ(pᵢ × log₂(pᵢ)) para celulas ocupadas
4. Conta posicoes APOS a utilidade atingir
5. H_depois = mesma formula
6. delta = H_antes - H_depois (positivo = informacao obtida)
7. efetividade = delta / max_delta
```

**Deltas maximos por tipo de utilidade:**
- Smoke: 2.5 bits (bloqueia linha de visao por ~18s)
- Molotov: 2.0 bits (negacao de area por ~7s)
- Flash: 1.8 bits (janela de 3s de cegueira)
- HE: 1.5 bits (revelacao momentanea de posicao)

### 9.5 Indice de Engano

**Arquivo:** `backend/analysis/deception_index.py`

```
composto = 0.25 × taxa_isca_flash + 0.40 × taxa_finta_rotacao + 0.35 × pontuacao_engano_sonoro
```

- **Iscas de flash (25%):** % de flashes que nao cegam ninguem em 128 ticks (~2 segundos)
- **Fintas de rotacao (40%):** Mudancas de direcao > 108° relativas a extensao do mapa (maior peso — engano posicional importa mais)
- **Engano sonoro (35%):** Inverso da razao de agachamento (menos agachado = mais barulho = potencial guerra de informacao)

### 9.6 Probabilidade de Vitoria

**Arquivo:** `backend/analysis/win_probability.py`

Pequena rede neural para previsao de vitoria de round em tempo real:

```
12 features → Linear(64) + ReLU + Dropout(0.2)
           → Linear(32) + ReLU + Dropout(0.1)
           → Linear(1) + Sigmoid → [0, 1]
```

**As 12 features de entrada:**
0. economia_time / 16.000
1. economia_inimigo / 16.000
2. diferenca_economia / 16.000
3. jogadores_vivos / 5
4. inimigos_vivos / 5
5. diferenca_vivos / 5
6. utilidades_restantes / 5
7. pct_controle_mapa
8. tempo_restante / 115
9. bomba_plantada (0/1)
10. e_ct (0/1)
11. razao_equipamento (limitada: min(time/inimigo, 2) / 2)

**Limites de seguranca deterministicos:**
- 0 vivos → 0.0% imediatamente
- 0 inimigos → 100.0% imediatamente
- Vantagem de ±3 jogadores → forca minimo 85% / maximo 15%
- Bomba plantada → ±10% por lado
- Diferenca de economia > $8.000 → forca minimo 65% / maximo 35%

### 9.7 Deteccao de Pontos Cegos

**Arquivo:** `backend/analysis/blind_spots.py`

Compara as acoes reais do jogador com as acoes otimas da arvore de jogo:
- Classifica cada situacao (eco rush, pos-plant, clutch 1vN, retake, etc.)
- Rastreia frequencia de discrepancia × impacto (delta de probabilidade de vitoria)
- Top 3 por prioridade se tornam areas de foco do coaching

### 9.8 Analise de Distancia de Confronto

**Arquivo:** `backend/analysis/engagement_range.py`

Faixas de distancia de kill com baselines profissionais por funcao:

| Faixa | Distancia | AWPer | Entry | Support |
|-------|-----------|-------|-------|---------|
| Curta | < 500 unidades | 10% | 40% | 25% |
| Media | 500-1500 | 30% | 40% | 45% |
| Longa | 1500-3000 | 45% | 15% | 25% |
| Extrema | > 3000 | 15% | 5% | 5% |

Gera observacoes de coaching quando o jogador desvia > 15% da baseline da funcao.

### 9.9 Analisadores de Utilidades e Economia

**Arquivo:** `backend/analysis/utility_economy.py`

**UtilityAnalyzer — Baselines profissionais:**
- Molotov: 35 de dano/arremesso, 70% de taxa de uso
- HE: 25 de dano/arremesso, 50% de taxa de uso
- Flash: 1.2 inimigos cegados/flash, 80% de taxa de uso
- Smoke: 0.9 de valor estrategico, 90% de taxa de uso

Efetividade = metrica do jogador / baseline profissional. Recomendacoes geradas quando a pontuacao < 0.5.

**EconomyOptimizer — Logica de round de compra:**

| Dinheiro | Decisao | Confianca |
|----------|---------|-----------|
| ≥ $4.000 | Buy completo | Alta |
| $2.000 - $3.999 | Forcada | Media |
| $1.200 - $1.999 | Meia compra (SMG) | Media |
| < $1.200 | Eco | Alta |

Deteccao de rounds especiais: pistol (round 1), intervalo (MR12→round 13, MR13→round 16).

Saida inclui: acao, confianca, armas recomendadas, raciocinio em linguagem natural.

---

## 10. Pipeline de Coaching COPER

**Arquivo:** `backend/services/coaching_service.py`
**COPER = Context Optimized with Prompt, Experience, Replay** (Contexto Otimizado com Prompt, Experiencia, Replay)

### Fallback com 4 Niveis de Prioridade

```
Nivel 1: COPER (pipeline completo — maior fidelidade)
  Usa: Banco de Experiencias + Conhecimento RAG + Referencias Pro
  Requer: map_name + tick_data
  Pipeline:
    1. Constroi ExperienceContext a partir dos tick_data
    2. Consulta Banco de Experiencias por situacoes similares passadas
    3. Sintetiza narrativa de conselho
    4. Recupera baseline temporal (comparacao com profissionais)
    5. Refina via Ollama Writer (LLM local)
    6. Coleta feedback para aprendizado futuro
    7. Persiste CoachingInsight no banco de dados
  │
  ▼ fallback (se dados faltando)
Nivel 2: HIBRIDO (sintese ML + RAG)
  Usa: HybridCoachingEngine mesclando previsoes ML + conhecimento
  Requer: player_stats
  │
  ▼ fallback
Nivel 3: TRADICIONAL + RAG (desvios + enriquecimento por conhecimento)
  Sempre disponivel (so precisa de desvios estatisticos)
  Usa: Desvios formatados em Z-score + entradas de conhecimento tatico
  │
  ▼ fallback
Nivel 4: TRADICIONAL (desvios estatisticos puros)
  Fallback terminal — sempre produz saida
  Analisa desvios, mapeia para areas de foco, gera correcoes
```

**Regra absoluta:** O sistema NUNCA produz zero coaching. Mesmo em falha total, um insight generico e salvo (C-01).

### Banco de Experiencias
- Armazena experiencias de gameplay com embeddings vetoriais de 384 dimensoes
- Busca por similaridade semantica (Sentence-BERT all-MiniLM-L6-v2, fallback para baseado em hash)
- Indice vetorial FAISS para buscas em O(log n)
- Experiencias profissionais ponderadas com confianca 0.7, de usuario com 0.5
- Saida: SynthesizedAdvice com narrativa, referencias pro, confianca, area de foco

### Base de Conhecimento RAG
- Alimentada por estatisticas de jogadores profissionais da HLTV (raspadas de hltv.org — NAO arquivos de demo)
- ProStatsMiner cria entradas TacticalKnowledge com arquetipos:
  - STAR_FRAGGER (rating ≥ 1.15)
  - SNIPER (HS% ≥ 35%)
  - SUPPORT (KAST ≥ 72%)
  - ENTRY (opening duel win% ≥ 52%)
  - LURKER (clutch wins ou taxa de multikill)
- Armazena conhecimento tatico com embeddings de 384 dimensoes para busca por similaridade

### Analise Pos-Coaching (Nao-Bloqueante)
Apos o coaching principal, estes rodam em segundo plano:
1. **Analise Fase 6** via AnalysisOrchestrator (momentum, engano, entropia, arvore de jogo, distancia de confronto)
2. **Tendencias Longitudinais** nas ultimas 10 partidas (deteccao de regressao/melhoria/volatilidade)
3. **Heatmap Diferencial** (sob demanda da UI — posicoes do usuario vs baselines profissionais)

---

## 11. Orquestrador de Analise

**Arquivo:** `backend/services/analysis_orchestrator.py`

Coordena todos os modulos de analise da Fase 6 para uma unica partida:

```
AnalysisOrchestrator.analyze_match(player, demo, rounds, ticks, states)
  │
  ├── _analyze_momentum()       → zonas de tilt, sequencias quentes
  ├── _analyze_deception()      → indice composto de engano
  ├── _analyze_utility_entropy() → impacto de utilidades em bits
  ├── _analyze_strategy()       → pontos cegos + recomendacoes da arvore de jogo
  └── _analyze_engagement_range() → padroes de distancia de kill
```

**Tratamento de falhas (F5-14):** Contadores de falha por modulo. Registra as 3 primeiras falhas, depois a cada 10a. Nao-bloqueante — falhas nao param o pipeline principal de coaching.

**Saida:** MatchAnalysis com insights por round + insights no nivel da partida, todos persistidos na tabela CoachingInsight.

---

## 12. Orquestracao de Treinamento

### Gatilho: Quando o Treinamento Comeca?

O daemon Teacher verifica a cada 5 minutos:
```
contagem_pro = count(PlayerMatchStats WHERE is_pro=True)
ultima_contagem = CoachState.last_trained_sample_count

se contagem_pro ≥ ultima_contagem × 1.10:     → RETREINAR (limiar de crescimento de 10%)
senao se ultima_contagem == 0 E contagem_pro ≥ 10: → PRIMEIRO TREINAMENTO
senao: dormir 300 segundos
```

### Seguranca de Thread
Lock `_TRAINING_LOCK` no nivel do modulo previne treinamento concorrente entre daemon e UI.

### Ciclo de Treinamento em 5 Fases

**Fase 1: Pre-treinamento JEPA (auto-supervisionado)**
- Dados: linhas de PlayerTickState (apenas pro, divisao train)
- Janelas de contexto preenchidas ate 10 ticks, alvo = 1 tick (previsao do proximo passo)
- 5 negativos entre partidas de um pool de 500 amostras em cache
- Loss: InfoNCE contrastiva
- Otimizador: AdamW(lr=1e-4, weight_decay=1e-4)
- Scheduler: CosineAnnealingLR(T_max=100)
- Early stopping: paciencia=10 na loss de validacao
- Checkpoint: `jepa_brain.pt`

**Fase 2: Baseline Profissional (supervisionado)**
- Dados: PlayerMatchStats (is_pro=True, divisoes train/val)
- 25 features agregadas por partida → deltas de melhoria (normalizados por Z-score)
- Modelo: AdvancedCoachNN (legado)
- Checkpoint: `latest.pt` (diretorio global)

**Fase 3: Personalizacao do Usuario (transfer learning)**
- Base: modelo global da Fase 2 (warm start)
- Dados: PlayerMatchStats (is_pro=False)
- Faz fine-tune da baseline profissional no estilo de jogo especifico do usuario
- Checkpoint: `latest.pt` (diretorio do usuario)

**Fase 4: Otimizacao Comportamental RAP (condicional)**
- So roda se `USE_RAP_MODEL=True`
- Dados: janelas contiguas de 320 ticks dos bancos de dados por partida
- Constroi tensores completos de mapa/visao/movimento em 64x64 (resolucao de treinamento)
- Calcula alvos de vantagem por tick:
  ```
  vantagem = 0.4 × diff_vivos + 0.2 × razao_hp + 0.2 × razao_equip + 0.2 × fator_bomba
  diff_vivos = (vivos_time - vivos_inimigos + 5) / 10  → [0, 1]
  fator_bomba = 0.7 (T plantou) / 0.3 (CT plantou) / 0.5 (sem bomba)
  ```
- Classifica funcao tatica (10 classes):
  0=tomada_de_site, 1=rotacao, 2=entry_frag, 3=suporte, 4=ancora,
  5=lurk, 6=retake, 7=save, 8=push_agressivo, 9=segurar_passivo
- Loss multi-tarefa com penalidade 2x no eixo Z
- Otimizador: AdamW(lr=5e-5, weight_decay=1e-4)
- **Gate de seguranca:** Aborta se taxa de fallback para tensor-zero > 30%
- Checkpoint: `rap_coach.pt`

**Fase 5: Cabeca de Classificacao de Funcao**
- Classificador leve para prever a funcao tatica do jogador
- Nao-fatal em caso de falha
- Checkpoint: `role_head.pt`

### Gate de Maturidade
| Nivel | Demos Processadas | Confianca do Coaching |
|-------|-------------------|----------------------|
| CALIBRANDO | 0-49 | 50% (UI mostra overlay "Calibrando") |
| APRENDENDO | 50-199 | 80% |
| MADURO | 200+ | 100% (correcoes de nivel profissional desbloqueadas) |

### Etapas Pos-Treinamento
1. Incrementar contador de maturidade
2. Registrar contagem de amostras treinadas (somente APOS sucesso — previne gatilhos falsos em caso de crash)
3. Verificar mudanca de meta (comparar estatisticas pro antes/depois do treinamento — detecta mudancas na meta do jogo)
4. Auto-calibrar modelo de crenca (priors Bayesianos a partir de resultados reais de partidas)
5. Liberar `_TRAINING_LOCK`

---

## 13. Fabrica de Modelos

**Arquivo:** `backend/nn/factory.py`

### Tipos de Modelo
```
"default"   → TeacherRefinementNN (legado)
"jepa"      → JEPACoachingModel
"vl-jepa"   → VLJEPACoachingModel
"rap"       → RAPCoachModel
"role_head" → NeuralRoleHead
```

### Nomes de Checkpoint
- `"jepa"` → `jepa_brain.pt`
- `"vl-jepa"` → `vl_jepa_brain.pt`
- `"rap"` → `rap_coach.pt`
- `"role_head"` → `role_head.pt`
- `"default"` → `latest.pt`

### Hierarquia de Carregamento de Checkpoint
Ao carregar um modelo, o sistema busca nesta ordem:
1. **Local do usuario:** `MODELS_DIR/user_id/version.pt`
2. **Local global:** `MODELS_DIR/global/version.pt`
3. **Fabrica empacotada (usuario):** `get_resource_path(models/user_id/version.pt)`
4. **Fabrica empacotada (global):** `get_resource_path(models/global/version.pt)`

**Se NENHUM encontrado → FileNotFoundError** (nunca usa pesos aleatorios silenciosamente).
**Se dimensoes incompativeis → StaleCheckpointError** (forca re-treinamento).

**Protocolo de escrita atomica:**
1. Escreve em `.pt.tmp`
2. `fsync` (descarrega para disco)
3. `os.replace` (atomico em POSIX — sem corrupcao em queda de energia)
4. Limpa `.pt.tmp` em caso de excecao

---

## 14. Inferencia GhostEngine

**Arquivo:** `backend/nn/inference/ghost_engine.py`

O motor de inferencia em producao que cria a sobreposicao do "fantasma" no mapa tatico.

### Fluxo de Inferencia por Tick

```
Dados do tick (dicionario de estado do jogador)
  │
  ▼
1. Verifica se modelo esta carregado (se nao → retorna (0, 0))
  │
  ▼
2. Constroi tensores via TensorFactory:
   map_t:    [1, 3, 128, 128]  visao geral tatica
   view_t:   [1, 3, 224, 224]  perspectiva do jogador
   motion_t: [1, 3, 224, 224]  contexto de movimento
   meta_t:   [1, 1, 25]        vetor de features
  │
  ▼
3. Passada forward (no_grad):
   out = model(view=view_t, map=map_t, motion=motion_t, metadata=meta_t)
  │
  ▼
4. Decodifica posicao:
   delta_otimo = out["optimal_pos"]  → [1, 3] (dx, dy, dz)
   ghost_x = atual_x + dx × 500.0
   ghost_y = atual_y + dy × 500.0
   (Eixo Z nao usado — mapas de CS2 sao navegaveis em 2D)
  │
  ▼
5. Retorna (ghost_x, ghost_y) como coordenadas do mundo
```

**Tratamento de erros:** RuntimeError ou qualquer excecao → registra + retorna (0.0, 0.0). Nenhuma excecao chega a UI.

**Integracao com UI** (de `tactical_vm.py`): Carrega GhostEngine sob demanda apenas quando o usuario ativa o modo fantasma. Percorre jogadores vivos, chama `predict_tick()` por jogador, substitui posicao pelas coordenadas fantasma.

### Limitacoes Atuais
- **Sem decodificacao seletiva:** Passada forward completa a cada tick (ver Secao 15)
- **Sem inferencia com estado:** Estado oculto do LSTM reseta a cada tick
- **Sem batching:** batch_size=1 por previsao de jogador
- **Sem cache de embedding:** Sem reuso entre ticks sequenciais

---

## 15. Decodificacao Seletiva

**Arquivo:** `backend/nn/jepa_model.py` (metodo `forward_selective`)

### Status: EXISTE mas NAO E USADA pelo GhostEngine

O metodo esta totalmente implementado, mas o GhostEngine faz decodificacao completa a cada tick.

### Como Funcionaria

```
Tick N chega → [B, seq_len, 25]
  │
  ▼
Context Encoder (SEMPRE roda — barato, ~100k parametros)
  → curr_embedding [B, seq_len, 256]
  │
  ├── Mean Pool → curr_pooled [B, 256]
  │
  ├── Compara com prev_pooled do ultimo tick:
  │     distancia_cosseno = 1.0 - similaridade_cosseno(curr, prev)
  │
  │     distancia < 0.05? ─── SIM ──► PULA: retorna None, reutiliza ultima previsao
  │         │
  │        NAO (estado mudou significativamente)
  │         │
  ▼         ▼
LSTM (2 camadas, 256→128)    ← CARO (~500k parametros)
Gate MoE (3 especialistas)    ← CARO
tanh → previsao [B, 10]
  │
  ▼
Retorna: (previsao, curr_embedding, True)
Armazena curr_embedding em cache para comparacao do proximo tick
```

**Potencial de economia:** Durante momentos tranquilos (jogador segurando angulo), poderia pular 60-80% da computacao.

### Tambem Nao Usada: Inferencia com Estado (NN-40)

O modelo RAP suporta persistencia do estado oculto do LSTM entre ticks:
```python
# O que o modelo suporta:
out = model(view, map, motion, metadata, hidden_state=estado_em_cache)
# O que o GhostEngine realmente faz:
out = model(view, map, motion, metadata)  # Sem hidden_state → reseta a cada tick
```

Habilitar isso permitiria que o LSTM "lembrasse" dos ticks recentes, reduzindo oscilacoes.

---

## 16. Motor de Sessao Tri-Daemon

**Arquivo:** `core/session_engine.py`

Quatro threads em segundo plano orquestram todo o trabalho assincrono:

```
┌──────────────────────────────────────────────────────────┐
│                    MOTOR DE SESSAO                        │
│                 (Loop Principal Keep-Alive)               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  DAEMON A: SCANNER (Hunter)              Ciclo: 10s     │
│  ├─ Monitora sistema de arquivos por novos .dem          │
│  ├─ Duas varreduras por ciclo: is_pro=True, is_pro=False │
│  ├─ Enfileira linhas IngestionTask no banco de dados     │
│  └─ Sinaliza _work_available_event                       │
│                                                          │
│  DAEMON B: DIGESTER                      Ciclo: evento  │
│  ├─ Consome fila de IngestionTask (1 por ciclo)          │
│  ├─ Parsing de demo em 3 passadas → extracao de features │
│  ├─ Valida integridade dos dados                         │
│  ├─ Persiste PlayerMatchStats, RoundStats, MatchTickState│
│  ├─ Recuperacao de zumbis: tarefas paradas >5 min        │
│  │   voltam para enfileirado                             │
│  └─ Bloqueia em evento quando fila vazia (sem polling)   │
│                                                          │
│  DAEMON C: TEACHER                       Ciclo: 300s    │
│  ├─ Monitora crescimento na contagem de amostras pro     │
│  │   (limiar de 10%)                                     │
│  ├─ Adquire _TRAINING_LOCK                               │
│  ├─ Executa ciclo completo de treinamento em 5 fases     │
│  ├─ Deteccao de mudanca de meta + calibracao de crenca   │
│  └─ Persiste checkpoints dos modelos                     │
│                                                          │
│  DAEMON D: PULSE                         Ciclo: 5s      │
│  ├─ Timestamp de heartbeat para a UI                     │
│  └─ Habilita deteccao de travamento                      │
│                                                          │
│  SHUTDOWN: Pai escreve "STOP" no stdin → todos os        │
│  daemons encerram graciosamente (timeout de 5s no join)  │
│                                                          │
│  STARTUP: Backup diario automatizado via BackupManager   │
│  + inicializacao unica da base de conhecimento           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Propriedade dos dados (sem mutacoes entre daemons):**
- Scanner e dono da criacao de IngestionTask
- Digester e dono da criacao de PlayerMatchStats/RoundStats/PlayerTickState
- Teacher e dono da criacao de checkpoints de modelo + CalibrationSnapshot
- CoachingService e dono da criacao de CoachingInsight/CoachingExperience

---

## 17. Constantes Chave

| Constante | Valor | Uso |
|-----------|-------|-----|
| METADATA_DIM | 25 | Dimensao de entrada de todo modelo |
| OUTPUT_DIM | 10 | Saida de estrategia/coaching |
| JEPA latent_dim | 256 | Espaco latente encoder/predictor/target |
| RAP hidden_dim | 256 | Dimensao oculta de memoria + estrategia |
| RAP perception_dim | 128 | View(64) + Map(32) + Motion(32) |
| NUM_COACHING_CONCEPTS | 16 | Interpretabilidade do VL-JEPA |
| LTC NCP units | 512 | 2x hidden para fiacao esparsa |
| Hopfield heads | 4 | Atencao da memoria associativa |
| MoE experts (RAP) | 4 | Especializacao da camada de estrategia |
| MoE experts (JEPA) | 3 | Especializacao da cabeca de coaching |
| RAP_POSITION_SCALE | 500.0 | Delta → unidades de coordenadas do mundo |
| Temperatura InfoNCE | 0.07 | Nitidez da distribuicao contrastiva |
| Momentum EMA | 0.996 | Atraso do target encoder (~250 passos) |
| GLOBAL_SEED | 42 | Reprodutibilidade em todo lugar |
| BATCH_SIZE | 32 | Batch padrao de treinamento |
| RAP learning rate | 5e-5 | Otimizador do RAP |
| JEPA learning rate | 1e-4 | Otimizador do JEPA |
| Comprimento de sequencia (RAP) | 320 | Janela de treinamento em ticks (~5s a 64Hz) |
| Comprimento de sequencia (JEPA) | 10 | Janela de contexto em ticks |
| Pool de negativos max | 500 | Cache de negativos entre partidas |
| Tensor de mapa (treinamento) | 64×64 | Reduzido para velocidade |
| Tensor de mapa (inferencia) | 128×128 | Resolucao completa |
| Tensor de visao (treinamento) | 64×64 | Reduzido para velocidade |
| Tensor de visao (inferencia) | 224×224 | Resolucao completa |
| Embedding de experiencia | 384 dim | Saida do Sentence-BERT |
| Embedding de conhecimento | 384 dim | Saida do Sentence-BERT |
| Features prob. vitoria | 12 | Entrada do WinProbabilityNN |
| Paciencia early stopping | 10 | Epocas sem melhoria |
| Limiar Z de drift | 2.5 | Mudanca na distribuicao de features |
| Timeout do lock de treino | ∞ | Apenas aquisicao nao-bloqueante |
| Heartbeat do daemon | 5 segundos | Intervalo do Pulse |
| Ciclo do Scanner | 10 segundos | Verificacao do sistema de arquivos |
| Ciclo do Teacher | 300 segundos | Verificacao de re-treinamento |
| Timeout de tarefa zumbi | 5 minutos | Recuperacao de tarefa travada |

---

## 18. Avaliacao Honesta de Engenharia

### O Que e Genuinamente Solido

1. **JEPA e pesquisa real e publicada** pela equipe de Yann LeCun na Meta AI. A implementacao da loss contrastiva InfoNCE esta correta. O mecanismo anti-colapso do target encoder EMA funciona como pretendido.
2. **O vetor de features de 25 dimensoes** captura o estado essencial do jogo com normalizacoes sensiveis: codificacao ciclica de yaw (sin/cos evita o salto 359°→0°), faixas limitadas, contexto tatico separado (features 20-24).
3. **Probabilidade Bayesiana de morte** usa atualizacoes de log-odds segundo o livro-texto com auto-calibracao a partir de dados reais de partidas. A matematica e solida.
4. **Arvore de jogo Expectiminimax** e um algoritmo real da pesquisa de IA para jogos (xadrez, poker). Aplica-lo a decisoes de round no CS2 com modelagem adaptativa de oponente e criativo e defensavel.
5. **Cadeia de fallback COPER** e engenharia de software de producao solida. "Nunca produzir zero coaching" com 4 niveis de degradacao e como sistemas de producao devem funcionar.
6. **Pipeline de dados** e bem construido: parsing em 3 passadas, cache assinado com HMAC, speedup vetorizado de 10x, divisoes temporais treino/val/teste, descontaminacao de jogadores, remocao de outliers.
7. **Escritas atomicas de checkpoint** (escrita em .tmp → fsync → os.replace) previnem corrupcao em queda de energia.
8. **Arquitetura tri-daemon** com coordenacao dirigida por eventos e um design razoavel para este tipo de aplicacao.

### O Que e Sobre-Engenheirado

1. **RAP Coach e complexo demais para 11 demos.** Percepcao ResNet + neuronios LTC + memoria Hopfield + gating de Superposicao + 4 especialistas MoE + Atribuicao + cabeca de Posicao + funcao de Valor = centenas de milhares de parametros. Voce precisa de 10.000x mais dados.
2. **"Prototipos" Hopfield aprendem ruido com essa escala de dados.** Padroes inicializados aleatoriamente + descida de gradiente com 11 demos = memorizacao, nao generalizacao.
3. **Neuronios LTC** sao projetados para robotica/controle em tempo continuo. Nao sao claramente melhores que LSTM padrao para ticks discretos de jogo.
4. **"Camada de Superposicao"** e uma camada linear com gate padrao. `linear(x) * sigmoid(gate(contexto))` — mecanismo simples de gating com um nome impressionante.
5. **CausalAttributor** usa proxies grosseiros (`agressividade = delta_pos × 0.5`) — nao e raciocinio causal genuino.
6. **Metrica de engano sonoro** e apenas o inverso da razao de agachamento — nao mede engano sonoro de verdade.
7. **Features construidas mas nao conectadas:** decodificacao seletiva, inferencia com estado, tensores POV todos implementados mas nao usados em producao.

### Consegue Superar Pedir Dicas de CS2 a uma LLM?

**Agora: Nao.** Um modelo de linguagem treinado em milhoes de discussoes sobre CS2 da conselhos gerais melhores.

**O potencial e fundamentalmente diferente:** Coaching personalizado e baseado em dados a partir dos SEUS replays reais e algo que uma LLM generica nao consegue fazer.

| Cenario | LLM Generica | Este Sistema (quando treinado) |
|---------|-------------|-------------------------------|
| "Como jogar B site?" | Boas praticas genericas | "Nos SEUS ultimos 50 rounds, voce faz overpeek no apartments 73% das vezes e morre. Profissionais seguram atras da van." |
| "Sou bom com utilidades?" | Dicas gerais de utilidades | "Sua efetividade de flash e 0.31. Profissionais fazem em media 0.68. Voce joga 40% das flashes sem cegar ninguem." |
| "Onde devo ficar?" | Guia de callouts do mapa | Sobreposicao fantasma mostrando exatamente onde voce DEVERIA estar neste tick |

### Caminho a Seguir

1. **Comece mais simples.** Prove que um modelo basico (MLP de 2 camadas ou LSTM padrao) consegue distinguir rounds bons de ruins antes de adicionar a complexidade do RAP.
2. **Consiga mais dados.** 11→200 demos e um comeco, mas arquiteturas complexas precisam de milhares.
3. **Prove valor incrementalmente.** O modelo consegue prever resultados de rounds? Distinguir eco de buy completo? Se nao, conserte a fundacao antes de adicionar camadas.
4. **Motores de teoria dos jogos podem ser mais valiosos agora** — funcionam com regras e matematica, nao com dados de treinamento, e poderiam fornecer coaching util HOJE.

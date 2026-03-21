> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Onboarding -- Gerenciamento do Fluxo de Novo Usuário

> **Autoridade:** Regra 3 (Frontend & UX), Regra 4 (Persistência de Dados)

Este módulo gerencia o fluxo de onboarding para novos usuários da
aplicação CS2 Coach AI. Ele rastreia quantas demos um usuário ingeriu,
mapeia essa contagem para uma etapa de prontidão e controla o acesso aos
recursos de coaching com base na disponibilidade de dados. O sistema é
projetado para ser leve, stateless por chamada e compatível com cache,
para que a UI possa consultá-lo sem incorrer em round-trips repetidos ao
banco de dados.

## Inventário de Arquivos

| Arquivo | Linhas | Propósito | Exports Principais |
|---------|--------|-----------|-------------------|
| `__init__.py` | 1 | Marcador de pacote | -- |
| `new_user_flow.py` | ~136 | Gerenciamento de etapas de onboarding e cache de contagem de demos | `UserOnboardingManager`, `OnboardingStatus`, `OnboardingStage`, `get_onboarding_manager()` |

## Arquitetura e Conceitos

### OnboardingStage

`OnboardingStage` é uma classe simples com três constantes de string que
nomeiam as possíveis etapas em que um usuário pode estar:

| Constante | Valor | Significado |
|-----------|-------|-------------|
| `AWAITING_FIRST_DEMO` | `"awaiting_first_demo"` | Nenhuma demo ingerida. O coach não pode operar. |
| `BUILDING_BASELINE` | `"building_baseline"` | Entre 1 e `RECOMMENDED_DEMOS - 1` demos. O coaching está ativo mas a baseline não é estável. |
| `COACH_READY` | `"coach_ready"` | Pelo menos `RECOMMENDED_DEMOS` demos. Capacidade total de coaching. |

### OnboardingStatus

Um snapshot imutável retornado por `get_status()`. É um `@dataclass` com
os seguintes campos:

```
OnboardingStatus
  stage: str               # Uma das constantes OnboardingStage
  demos_uploaded: int       # Total de demos não-pro do usuário
  demos_required: int       # MIN_INITIAL_DEMOS (atualmente 1)
  demos_recommended: int    # RECOMMENDED_DEMOS (atualmente 3)
  coach_ready: bool         # True quando demos_uploaded >= MIN_INITIAL_DEMOS
  baseline_stable: bool     # True quando demos_uploaded >= RECOMMENDED_DEMOS
  message: str              # Descrição da etapa legível pelo usuário
```

### Limites

| Constante | Valor | Propósito |
|-----------|-------|-----------|
| `MIN_INITIAL_DEMOS` | 1 | Mínimo para desbloquear o coaching básico |
| `RECOMMENDED_DEMOS` | 3 | Alvo para uma baseline pessoal estável |
| `_CACHE_TTL_SECONDS` | 60 | TTL para o cache em memória da contagem de demos |

### Cache de Contagem de Demos (TASK 2.16.1)

`UserOnboardingManager` mantém um cache em memória por usuário
(`_demo_count_cache`) que mapeia `user_id` para uma tupla `(count, timestamp)`.
Quando `get_status()` é chamado, o manager primeiro verifica se a contagem
em cache ainda está dentro de `_CACHE_TTL_SECONDS` do tempo monotônico
atual. Se sim, o valor em cache é retornado sem acessar o banco de dados.

Após o upload de uma nova demo, o chamador deve invocar
`invalidate_cache(user_id)` para garantir que a próxima chamada a
`get_status()` reflita a contagem atualizada imediatamente. Chamar
`invalidate_cache()` sem argumentos limpa todo o cache.

### Consulta ao Banco de Dados

O manager consulta `PlayerMatchStats` para contar demos não-pro:

```python
select(func.count(PlayerMatchStats.id)).where(
    PlayerMatchStats.player_name == user_id,
    PlayerMatchStats.is_pro == False,
)
```

Apenas demos carregadas pelo usuário contam para o progresso do
onboarding. Demos profissionais ingeridas para a baseline de treinamento
são excluídas (DA-16-01).

### Fluxo de Determinação de Etapa

```
demos_uploaded == 0  -->  AWAITING_FIRST_DEMO
0 < demos_uploaded < RECOMMENDED_DEMOS  -->  BUILDING_BASELINE
demos_uploaded >= RECOMMENDED_DEMOS  -->  COACH_READY
```

## Integração

- **UI (Qt):** `HomeScreen` e o assistente de onboarding consultam
  `get_status()` para exibir indicadores de progresso, mensagens de
  boas-vindas e diálogos de controle de acesso.
- **CoachingService:** Verifica `coach_ready` antes de gerar insights de
  coaching de alta confiança. Quando `coach_ready` é `False`, os insights
  ainda são gerados mas anotados com um aviso de baixa confiança.
- **Pipeline de Ingestão:** Após a ingestão de uma demo, a pipeline chama
  `invalidate_cache()` para que a próxima consulta da UI veja a contagem
  atualizada.
- **Banco de Dados:** O módulo lê de `PlayerMatchStats` em `database.db`.
  Não realiza escritas nem mutações.

## Notas de Desenvolvimento

- `UserOnboardingManager` recalcula a etapa a cada chamada a
  `get_status()`. É stateless exceto pelo cache TTL.
- A factory `get_onboarding_manager()` cria uma nova instância a cada
  vez. **Não** é um singleton, então múltiplos chamadores não compartilham
  o estado do cache a menos que compartilhem a mesma instância.
- Os limites das etapas são constantes a nível de classe. Se precisarem
  ser configuráveis, promovê-los para `core/config.py` como configurações
  do usuário.
- Nunca bloqueie funcionalidades completamente com base na etapa. Sempre
  permita a saída de coaching, mas anote-a com o nível de confiança
  derivado da etapa.
- O campo `message` em `OnboardingStatus` é uma string voltada para o
  usuário. Mantê-la concisa e encorajadora. As traduções são tratadas na
  camada de UI, não neste módulo.
- O módulo utiliza logging estruturado via
  `get_logger("cs2analyzer.onboarding")`.
- O cache usa `time.monotonic()` em vez do tempo real para evitar
  problemas com ajustes do relógio do sistema.

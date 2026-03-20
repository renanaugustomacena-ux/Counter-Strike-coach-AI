> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Onboarding — Gerenciamento do Fluxo de Novo Usuario

> **Autoridade:** Regra 3 (Frontend & UX), Regra 4 (Persistencia de Dados)

Este modulo gerencia o fluxo de onboarding para novos usuarios, rastreando a progressao pelas etapas de configuracao e controlando o acesso aos recursos de coaching com base na disponibilidade de dados.

## Arquivo: new_user_flow.py (~135 linhas)

Classes principais: UserOnboardingManager, OnboardingStatus

Campos de OnboardingStatus:
- stage: str (nome da etapa atual de onboarding)
- demos_ingested: int (quantas demos foram processadas)
- readiness: float (0.0 a 1.0, pontuacao de prontidao para coaching)
- can_coach: bool (se os recursos de coaching estao disponiveis)

## Etapas

Baseadas na "Regra 10/10":
1. Setup — Nenhuma demo ainda. O usuario precisa configurar os caminhos.
2. Calibrating — 1-49 demos. Coaching disponivel mas com baixa confianca.
3. Learning — 50-199 demos. Confianca moderada.
4. Mature — 200+ demos. Capacidade total de coaching.

## Integracao

- UI: Conectado a HomeScreen e WizardScreen para indicadores de prontidao
- Coaching: CoachingService verifica a prontidao antes de insights de alta confianca
- Database: Le de PlayerMatchStats (somente leitura)

## Notas de Desenvolvimento

- UserOnboardingManager e stateless — recalcula a cada chamada
- Os limites das etapas devem corresponder a documentacao de getting_started.md
- Nunca bloqueie funcionalidades completamente — sempre permita coaching com avisos de confianca

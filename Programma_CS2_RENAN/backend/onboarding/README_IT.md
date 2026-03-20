> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Onboarding — Gestione del Flusso Nuovo Utente

> **Autorita:** Regola 3 (Frontend & UX), Regola 4 (Persistenza dei Dati)

Questo modulo gestisce il flusso di onboarding per i nuovi utenti, tracciando la progressione attraverso le fasi di configurazione e limitando l'accesso alle funzionalita di coaching in base alla disponibilita dei dati.

## File: new_user_flow.py (~135 righe)

Classi principali: UserOnboardingManager, OnboardingStatus

Campi di OnboardingStatus:
- stage: str (nome della fase di onboarding corrente)
- demos_ingested: int (numero di demo elaborate)
- readiness: float (da 0.0 a 1.0, punteggio di prontezza al coaching)
- can_coach: bool (se le funzionalita di coaching sono disponibili)

## Fasi

Basate sulla "Regola 10/10":
1. Setup — Nessuna demo ancora. L'utente deve configurare i percorsi.
2. Calibrating — 1-49 demo. Coaching disponibile ma con bassa confidenza.
3. Learning — 50-199 demo. Confidenza moderata.
4. Mature — 200+ demo. Piena capacita di coaching.

## Integrazione

- UI: Collegato a HomeScreen e WizardScreen per gli indicatori di prontezza
- Coaching: CoachingService verifica la prontezza prima degli insight ad alta confidenza
- Database: Legge da PlayerMatchStats (sola lettura)

## Note di Sviluppo

- UserOnboardingManager e stateless — ricalcola ad ogni chiamata
- Le soglie delle fasi devono corrispondere alla documentazione di getting_started.md
- Non bloccare mai completamente le funzionalita — consentire sempre il coaching con avvisi di confidenza

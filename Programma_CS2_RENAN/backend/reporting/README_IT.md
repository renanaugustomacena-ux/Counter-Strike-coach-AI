> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Reporting — Motore Analitico per Dashboard

> **Autorità:** Regola 1 (Correttezza), Regola 2 (Sovranità Backend)

Questo modulo fornisce il livello di calcolo matematico e aggregazione dati per l'interfaccia dashboard. Calcola trend dei giocatori, dati radar delle abilità e baseline professionali — tutte query in sola lettura senza mutazioni.

Nota: Questo è distinto dalla directory reporting/ di primo livello, che gestisce la generazione PDF e l'output di visualizzazione. Questo modulo si concentra sul calcolo dei dati.

## File: analytics.py (351 righe)

### AnalyticsEngine — Metodi Principali

- get_player_trends(player_name, limit=20) → DataFrame — Performance storica per grafici di trend
- get_skill_radar(player_name) → Dict — Attributi abilità normalizzati (0-100) vs baseline professionali
- compute_pro_baselines() → Dict — Aggrega statistiche giocatori professionisti
- get_coach_state(player_name) → CoachState — Ultimo stato di coaching per la visualizzazione dello stato

## Pattern di Design

- Responsabilità singola: solo matematica e aggregazione, nessuna mutazione
- Controllo null difensivo: restituisce valori predefiniti sicuri se i dati sono insufficienti
- Query in sola lettura: utilizza SQLModel ORM
- Logging: `get_logger("cs2analyzer.analytics")`

## Note di Sviluppo

- La normalizzazione del grafico radar è basata su euristiche (non ML)
- Le baseline professionali sono calcolate da PlayerMatchStats dove is_pro == True
- Non memorizzare mai i risultati in cache in questa classe — lasciare che il ViewModel gestisca il caching

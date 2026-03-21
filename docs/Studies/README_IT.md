> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Macena CS2 Analyzer - Gli Studi (Bibliotheca)

> **"L'intelligenza non e una collezione di algoritmi; e un Continuum Unificato di Maestria."**

Questa directory contiene la **Documentazione Tecnica Canonica** del Macena CS2 Analyzer. Questi 17 volumi rappresentano la derivazione architettonica, matematica e filosofica completa del sistema, sintetizzata da oltre 200.000 parole di materiale sorgente.

---

## La Trilogia Fondamentale: Fondamenti (Volumi 1-3)

Questi volumi stabiliscono la realta fisica e matematica del sistema.

*   **[Studio 01: Fondamenti Epistemici e Ontologia del Match](Studio_01_Fondamenti_Epistemici.md)**
    *   *Argomento:* La filosofia della "Verita" in CS2. Il mandato di "Inerzia Chimica". La definizione di un "Match" come varieta causale.
    *   *Concetti Chiave:* `Epistemic Truth`, `Causal Reconstruction`, `Thermodynamic Stability`.

*   **[Studio 02: Algebra dell'Ingestione e Coordinate Egocentriche](Studio_02_Algebra_Ingestione.md)**
    *   *Argomento:* Come la macchina "Vede". La trasformazione matematica dalle coordinate globali $(x,y,z)$ allo spazio tattico relativo.
    *   *Concetti Chiave:* `Egocentric Transform`, `Foveal Attention`, `Flux Calculus`.

*   **[Studio 03: Reti Ricorrenti e Memoria Temporale](Studio_03_Reti_Ricorrenti.md)**
    *   *Argomento:* Come la macchina "Ricorda". L'architettura LSTM per il tracciamento della storia dei round e le Modern Hopfield Networks per il richiamo associativo.
    *   *Concetti Chiave:* `Belief State`, `Temporal Backpropagation`, `Associative Memory`.

---

## Il Motore dell'Intelligenza (Volumi 4-7)

Questi volumi definiscono come la macchina apprende e ragiona.

*   **[Studio 04: Apprendimento per Rinforzo e Ottimizzazione della Policy](Studio_04_Apprendimento_Rinforzo.md)**
    *   *Argomento:* Il "Cervello". Algoritmi PPO, stima del vantaggio e la definizione matematica di "Vincere".
    *   *Concetti Chiave:* `PPO-Clip`, `GAE (Generalized Advantage Estimation)`, `Curriculum Learning`.

*   **[Studio 05: Architettura Percettiva e Corteccia Visiva](Studio_05_Architettura_Percettiva.md)**
    *   *Argomento:* Gli "Occhi". La retina tensoriale a 25 canali che elabora wall-control, smoke-density e enemy-belief (espansa da 19 a 25 dimensioni dopo la v1.0.0).
    *   *Concetti Chiave:* `Semantic Channels`, `Occlusion Masks`, `Visual Cortex`.

*   **[Studio 06: Architettura Cognitiva e POMDP](Studio_06_Architettura_Cognitiva.md)**
    *   *Argomento:* La "Mente". Modellazione di Counter-Strike come Processo Decisionale di Markov Parzialmente Osservabile. Incertezza e processo decisionale.
    *   *Concetti Chiave:* `POMDP`, `Information State`, `Counterfactual Regret`.

*   **[Studio 07: Architettura JEPA (Joint Embedding Prediction)](Studio_07_Architettura_JEPA.md)**
    *   *Argomento:* Il "Modello del Mondo". Andare oltre la previsione di pixel per prevedere il *significato*. Il motore avanzato di apprendimento auto-supervisionato.
    *   *Concetti Chiave:* `Latent Prediction`, `Energy-Based Models`, `VICReg`.

---

## Il Corpo Ingegneristico (Volumi 8-12)

Questi volumi descrivono in dettaglio l'ingegneria pesante necessaria per far funzionare l'intelligenza.

*   **[Studio 08: Ingegneria Forense e Parsing dei Demo](Studio_08_Ingegneria_Forense.md)**
    *   *Argomento:* La "Digestione". Ricostruzione di una partita bit per bit da file binari grezzi. Gestione delle peculiarita del Source 2 Engine.
    *   *Concetti Chiave:* `Bitstream Parsing`, `Sub-tick Reconstruction`, `Protobuf`.

*   **[Studio 09: Feature Engineering e Spazio Vettoriale](Studio_09_Feature_Engineering.md)**
    *   *Argomento:* Il "Traduttore". Conversione di eventi di gioco grezzi in vettori matematici comprensibili dall'IA.
    *   *Concetti Chiave:* `Normalization`, `One-Hot Encoding`, `Vector Space`.

*   **[Studio 10: Architettura del Database e Storage](Studio_10_Database_Storage.md)**
    *   *Argomento:* La "Banca della Memoria". Architettura Tri-Database (monolith + HLTV + per-match) con SQLite in modalita WAL.
    *   *Concetti Chiave:* `SQLAlchemy`, `WAL (Write-Ahead Log)`, `Application-Level Sharding`.

*   **[Studio 11: Tri-Daemon Engine e Architettura di Sistema](Studio_11_Tri_Daemon_Engine.md)**
    *   *Argomento:* Il "Sistema Nervoso". L'architettura Quad-Daemon (Scanner, Digester, Teacher, Pulse) che mantiene l'applicazione reattiva.
    *   *Concetti Chiave:* `Threading`, `Session Engine`, `Watchdogs`, `Self-Healing`.

*   **[Studio 12: Valutazione, Validazione e Falsificazione](Studio_12_Valutazione_Falsificazione.md)**
    *   *Argomento:* La "Coscienza". Dimostrare che l'IA ha ragione. Protocolli anti-allucinazione e metriche di qualita decisionale.
    *   *Concetti Chiave:* `DQD (Decision Quality Delta)`, `Falsification`, `Clinical Validation`.

---

## Interfaccia Umana ed Etica (Volumi 13-17)

Questi volumi esplorano l'interazione tra Uomo e Macchina.

*   **[Studio 13: Spiegabilita, Coaching e Interfaccia Umano-AI](Studio_13_Spiegabilita_Coaching_Interfaccia.md)**
    *   *Argomento:* La "Voce". Traduzione di tensori in consigli in linguaggio naturale. La UX della dashboard (PySide6/Qt primaria, Kivy legacy).
    *   *Concetti Chiave:* `Explainable AI (XAI)`, `Cognitive Load`, `Pedagogical Tone`.

*   **[Studio 14: Etica, Privacy e Integrita Competitiva](Studio_14_Etica_Privacy_Integrita.md)**
    *   *Argomento:* La "Legge". Prevenzione dei trucchi, protezione della privacy degli utenti e garanzia del fair play.
    *   *Concetti Chiave:* `Data Sovereignty`, `Anti-Cheat Alignment`, `Differential Privacy`.

*   **[Studio 15: Ottimizzazione Hardware, Deployment e Scaling](Studio_15_Ottimizzazione_Hardware_Scaling.md)**
    *   *Argomento:* Il "Metallo". Far funzionare l'IA su PC consumer e telefoni. Ottimizzazione Rust, CUDA e Mobile.
    *   *Concetti Chiave:* `Zero-Copy`, `INT8 Quantization`, `Cross-Platform Build`.

*   **[Studio 16: Intelligenza Tattica delle Mappe e GNN](Studio_16_Mappe_GNN.md)**
    *   *Argomento:* L'"Atlante". Strategie specifiche per Mirage, Inferno, Nuke tramite Graph Neural Networks.
    *   *Concetti Chiave:* `GNN (Graph Neural Networks)`, `Map Topology`, `Tactical Blueprints`.

*   **[Studio 17: Impatto Sociotecnico e Frontiere Future](Studio_17_Impatto_Sociotecnico_Futuro.md)**
    *   *Argomento:* Il "Futuro". Come l'IA cambia lo sport, il reclutamento e la definizione di talento.
    *   *Concetti Chiave:* `Thermodynamic Limit`, `Human-Machine Synergy`, `Meritocracy`.

---

> *Generato da Macena Gemini CLI - Febbraio 2026*

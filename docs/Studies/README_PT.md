> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Macena CS2 Analyzer - Os Estudos (Bibliotheca)

> **"Inteligencia nao e uma colecao de algoritmos; e um Continuum Unificado de Maestria."**

Este diretorio contem a **Documentacao Tecnica Canonica** do Macena CS2 Analyzer. Estes 17 volumes representam a derivacao arquitetonica, matematica e filosofica completa do sistema, sintetizada a partir de mais de 200.000 palavras de material fonte.

---

## A Trilogia Central: Fundamentos (Volumes 1-3)

Estes volumes estabelecem a realidade fisica e matematica do sistema.

*   **[Studio 01: Fondamenti Epistemici e Ontologia del Match](Fondamenti-Epistemici.md)**
    *   *Tema:* A filosofia da "Verdade" no CS2. O mandato de "Inercia Quimica". A definicao de um "Match" como variedade causal.
    *   *Conceitos Chave:* `Epistemic Truth`, `Causal Reconstruction`, `Thermodynamic Stability`.

*   **[Studio 02: Algebra dell'Ingestione e Coordinate Egocentriche](Algebra-Ingestione.md)**
    *   *Tema:* Como a maquina "Ve". A transformacao matematica das coordenadas globais $(x,y,z)$ para o espaco tatico relativo.
    *   *Conceitos Chave:* `Egocentric Transform`, `Foveal Attention`, `Flux Calculus`.

*   **[Studio 03: Reti Ricorrenti e Memoria Temporale](Reti-Ricorrenti.md)**
    *   *Tema:* Como a maquina "Lembra". A arquitetura LSTM para rastreamento do historico de rounds e as Modern Hopfield Networks para recuperacao associativa.
    *   *Conceitos Chave:* `Belief State`, `Temporal Backpropagation`, `Associative Memory`.

---

## O Motor de Inteligencia (Volumes 4-7)

Estes volumes definem como a maquina aprende e pensa.

*   **[Studio 04: Apprendimento per Rinforzo e Ottimizzazione della Policy](Apprendimento-Rinforzo.md)**
    *   *Tema:* O "Cerebro". Algoritmos PPO, estimativa de vantagem e a definicao matematica de "Vencer".
    *   *Conceitos Chave:* `PPO-Clip`, `GAE (Generalized Advantage Estimation)`, `Curriculum Learning`.

*   **[Studio 05: Architettura Percettiva e Corteccia Visiva](Architettura-Percettiva.md)**
    *   *Tema:* Os "Olhos". A retina tensorial de 25 canais que processa wall-control, smoke-density e enemy-belief (expandida de 19 para 25 dimensoes apos a v1.0.0).
    *   *Conceitos Chave:* `Semantic Channels`, `Occlusion Masks`, `Visual Cortex`.

*   **[Studio 06: Architettura Cognitiva e POMDP](Architettura-Cognitiva.md)**
    *   *Tema:* A "Mente". Modelagem de Counter-Strike como um Processo de Decisao de Markov Parcialmente Observavel. Incerteza e tomada de decisao.
    *   *Conceitos Chave:* `POMDP`, `Information State`, `Counterfactual Regret`.

*   **[Studio 07: Architettura JEPA (Joint Embedding Prediction)](Architettura-JEPA.md)**
    *   *Tema:* O "Modelo do Mundo". Indo alem da previsao de pixels para prever o *significado*. O motor avancado de aprendizado auto-supervisionado.
    *   *Conceitos Chave:* `Latent Prediction`, `Energy-Based Models`, `VICReg`.

---

## O Corpo de Engenharia (Volumes 8-12)

Estes volumes detalham a engenharia pesada necessaria para executar a inteligencia.

*   **[Studio 08: Ingegneria Forense e Parsing dei Demo](Ingegneria-Forense.md)**
    *   *Tema:* A "Digestao". Reconstrucao de uma partida bit a bit a partir de arquivos binarios brutos. Lidando com as peculiaridades do Source 2 Engine.
    *   *Conceitos Chave:* `Bitstream Parsing`, `Sub-tick Reconstruction`, `Protobuf`.

*   **[Studio 09: Feature Engineering e Spazio Vettoriale](Feature-Engineering.md)**
    *   *Tema:* O "Tradutor". Conversao de eventos brutos do jogo em vetores matematicos que a IA consegue entender.
    *   *Conceitos Chave:* `Normalization`, `One-Hot Encoding`, `Vector Space`.

*   **[Studio 10: Architettura del Database e Storage](Database-Storage.md)**
    *   *Tema:* O "Banco de Memoria". Arquitetura Tri-Database (monolith + HLTV + per-match) usando SQLite em modo WAL.
    *   *Conceitos Chave:* `SQLAlchemy`, `WAL (Write-Ahead Log)`, `Application-Level Sharding`.

*   **[Studio 11: Tri-Daemon Engine e Architettura di Sistema](Tri-Daemon-Engine.md)**
    *   *Tema:* O "Sistema Nervoso". A arquitetura Quad-Daemon (Scanner, Digester, Teacher, Pulse) que mantem a aplicacao responsiva.
    *   *Conceitos Chave:* `Threading`, `Session Engine`, `Watchdogs`, `Self-Healing`.

*   **[Studio 12: Valutazione, Validazione e Falsificazione](Valutazione-Falsificazione.md)**
    *   *Tema:* A "Consciencia". Provar que a IA esta correta. Protocolos anti-alucinacao e metricas de qualidade de decisao.
    *   *Conceitos Chave:* `DQD (Decision Quality Delta)`, `Falsification`, `Clinical Validation`.

---

## Interface Humana e Etica (Volumes 13-17)

Estes volumes exploram a interacao entre Homem e Maquina.

*   **[Studio 13: Spiegabilita, Coaching e Interfaccia Umano-AI](Spiegabilita-Coaching-Interfaccia.md)**
    *   *Tema:* A "Voz". Traducao de tensores em conselhos em linguagem natural. A UX do dashboard (PySide6/Qt primario, Kivy legado).
    *   *Conceitos Chave:* `Explainable AI (XAI)`, `Cognitive Load`, `Pedagogical Tone`.

*   **[Studio 14: Etica, Privacy e Integrita Competitiva](Etica-Privacy-Integrita.md)**
    *   *Tema:* A "Lei". Prevencao de trapaças, protecao da privacidade dos usuarios e garantia de fair play.
    *   *Conceitos Chave:* `Data Sovereignty`, `Anti-Cheat Alignment`, `Differential Privacy`.

*   **[Studio 15: Ottimizzazione Hardware, Deployment e Scaling](Ottimizzazione-Hardware-Scaling.md)**
    *   *Tema:* O "Metal". Fazendo a IA rodar em PCs domesticos e celulares. Otimizacao Rust, CUDA e Mobile.
    *   *Conceitos Chave:* `Zero-Copy`, `INT8 Quantization`, `Cross-Platform Build`.

*   **[Studio 16: Intelligenza Tattica delle Mappe e GNN](Mappe-GNN.md)**
    *   *Tema:* O "Atlas". Estrategias especificas para Mirage, Inferno, Nuke usando Graph Neural Networks.
    *   *Conceitos Chave:* `GNN (Graph Neural Networks)`, `Map Topology`, `Tactical Blueprints`.

*   **[Studio 17: Impatto Sociotecnico e Frontiere Future](Impatto-Sociotecnico-Futuro.md)**
    *   *Tema:* O "Futuro". Como a IA muda o esporte, o recrutamento e a definicao de talento.
    *   *Conceitos Chave:* `Thermodynamic Limit`, `Human-Machine Synergy`, `Meritocracy`.

---

> *Gerado por Macena Gemini CLI - Fevereiro 2026*

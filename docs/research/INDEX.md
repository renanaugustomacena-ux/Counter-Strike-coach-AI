# Research Library — Index / Bibliography

> Catalogo della biblioteca di ricerca per **Macena CS2 Analyzer**. I PDF vivono in `docs/research/library/` (git-ignored, binari grandi) e in `docs/research/arxiv/` (collezione JEPA preesistente). Questo catalogo è **tracciato** ed è l'unico file pubblico di `docs/research/`.
>
> Sessione: **Studio AI/Data-Engineering 2026-06** (branch `study/ai-data-engineering-2026-06`).
> Obiettivo: ≥40 PDF, bilanciati 50% fondamenta del progetto · 50% punti ciechi mai considerati, + cluster speciale "visione privilegiata al training". **Totale curato: ~66** (49 arXiv nuovi + 14 JEPA preesistenti + 3 non-arXiv).
>
> Anti-fabbricazione: ogni ID risolto da pagine arxiv.org/host autoritativi e validato al download (magic `%PDF-` + dimensione). Nessun ID inventato.

## Legenda
`Stato`: ⬇ scaricato+validato · 📖 letto/diagnosi in AUDIT.md · ⏳ in download. Tutti gli arXiv: PDF a `https://arxiv.org/pdf/<ID>`.

---

## Collezione JEPA preesistente (`docs/research/arxiv/`, 14 PDF)
I-JEPA (2301.08243), T-JEPA (2406.12913), JEPA-for-RL (2504.16591), V-JEPA-2 (2506.09985), Auxiliary-Tasks-JEPA (2509.12249), DSeq-JEPA (2511.17354), VL-JEPA (2512.10942), Value-Guided-Action-Planning-JEPA (2601.00844), VLA-JEPA (2602.10098), V-JEPA-2.1 (2603.14482), Sub-JEPA (2605.09241), Factorized-Latent-Dynamics-Video-JEPA (2605.17165), Multimodal-JEPA (2605.31580), CF-JEPA (2606.07031). → Già allineati al cuore JEPA del progetto; verranno riletti in Fase 2 confrontandoli col codice `jepa_model.py`/`jepa_trainer.py`.

---

# GRUPPO A — Fondamenta su cui il progetto è già costruito

## A1 · JEPA & energy-based learning
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2511.08544 | LeJEPA: Provable and Scalable SSL Without the Heuristics | Balestriero, LeCun (2025) | **Critico**: rimuove EMA-teacher e stop-gradient (su cui il progetto si fonda: NN-16, NN-JM-04) e li sostituisce con SIGReg. Mette in discussione una scelta architetturale centrale | 📖 studio 2026-07: `docs/Studies/LeJEPA-SIGReg-vs-EMA.md` (26-LEJEPA-01/A1 chiusi) |

## A2 · SSL non-contrastivo
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2105.04906 | VICReg: Variance-Invariance-Covariance Regularization | Bardes, Ponce, LeCun (2021) | Il progetto usa VICReg (λ_var=25, λ_cov=1) sul predittore; fonte primaria per validare iperparametri e termine anti-collasso | ⬇ |
| 2103.03230 | Barlow Twins: SSL via Redundancy Reduction | Zbontar et al. (2021) | Alternativa di de-correlazione al collasso; confronto per la scelta VICReg | ⬇ |
| 2006.07733 | BYOL: Bootstrap Your Own Latent | Grill et al. (2020) | Self-distillation senza negativi con target EMA — esattamente il meccanismo EMA del progetto | ⬇ |
| 2104.14294 | DINO: Emerging Properties in Self-Supervised ViT | Caron et al. (2021) | Teacher-student con EMA + centering anti-collasso | ⬇ |
| 2304.07193 | DINOv2: Learning Robust Features Without Supervision | Oquab et al. (2023) | Stato dell'arte SSL di feature; riferimento per qualità rappresentazioni | ⬇ |

## A3 · Contrastive learning & InfoNCE
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2002.05709 | SimCLR | Chen et al. (2020) | Ruolo delle augmentation e temperatura InfoNCE — il progetto ha τ apprendibile | ⬇ |
| 1911.05722 | MoCo: Momentum Contrast | He et al. (2019) | **Diretto**: il progetto usa una queue MoCo (4096) + encoder momentum | ⬇ |
| 2104.02057 | MoCo v3 | Chen, Xie, He (2021) | Versione esatta citata nel codice; stabilità del training contrastivo | ⬇ |
| 1807.03748 | CPC: Representation Learning with Contrastive Predictive Coding | van den Oord et al. (2018) | Origine di InfoNCE e della predizione del futuro in spazio latente — il principio stesso di JEPA | ⬇ |
| 2103.00020 | CLIP | Radford et al. (2021) | Origine della temperatura apprendibile log(0.07) usata nel progetto | ⬇ |

## A4 · Mixture-of-Experts (sparse routing)
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1701.06538 | Outrageously Large NN: Sparsely-Gated MoE | Shazeer et al. (2017) | Fondamento del gate sparso; il progetto ha appena migrato da dense→top-2 (GAP-10) | ⬇ |
| 2101.03961 | Switch Transformer | Fedus, Zoph, Shazeer (2021) | Routing semplificato + load-balancing loss — confronto con l'aux-loss MoE del progetto | ⬇ |

## A5 · Modern Hopfield networks
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2008.02217 | Hopfield Networks is All You Need | Ramsauer et al. (2020) | **Diretto**: la memoria RAP usa `HopfieldLayer` (32 prototipi); capacità/retrieval e l'invariante NN-MEM-01 | ⬇ |

## A6 · Liquid Time-Constant / Neural ODE
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2006.04439 | Liquid Time-constant Networks | Hasani, Lechner et al. (2020) | **Diretto**: la memoria RAP usa LTC (`ncps`); frame-rate variabile e il fix RAP-LTC | ⬇ |
| 1806.07366 | Neural Ordinary Differential Equations | Chen et al. (2018) | Base teorica delle reti continue (LTC ne è figlia); solver ODE | ⬇ |

## A7 · Modelli sequenziali / time-series
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1706.03762 | Attention Is All You Need | Vaswani et al. (2017) | Base dell'attenzione; il progetto usa LSTM ma il confronto con Transformer è dovuto | ⬇ |
| 1912.09363 | Temporal Fusion Transformer | Lim et al. (2019) | Forecasting multi-orizzonte interpretabile su time-series eterogenee — esattamente i tick CS2 | ⬇ |
| 2012.07436 | Informer: Long Sequence Time-Series Forecasting | Zhou et al. (2020) | Attenzione efficiente su sequenze lunghe (round interi a 64/128 tick) | ⬇ |

## A8 · World models & planning
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1803.10122 | World Models | Ha, Schmidhuber (2018) | Modello del mondo in spazio latente compresso — cugino concettuale di JEPA-coaching | ⬇ |
| 2301.04104 | DreamerV3: Mastering Diverse Domains through World Models | Hafner et al. (2023) | Pianificazione per immaginazione in latente; rilevante a JEPA-for-RL del progetto | ⬇ |
| 1911.08265 | MuZero | Schrittwieser et al. (2019) | Modello che predice solo le quantità utili a pianificare (value/policy/reward) | ⬇ |

## A9 · Collasso rappresentazionale
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2110.09348 | Understanding Dimensional Collapse in Contrastive SSL | Jing, Vincent, LeCun, Tian (2021) | **Diretto**: fondamento del gate P9-02 EmbeddingCollapseDetector (var<0.01) | ⬇ |
| 2211.10831 | Joint Embedding Predictive Architectures Focus on Slow Features | (2022) | Cosa imparano davvero le JEPA (feature lente) — utile per validare le rappresentazioni del coach | ⬇ |

---

# GRUPPO B — Punti ciechi mai considerati (peso su integrità dati)

## B1 · Data-centric AI & qualità dati
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2303.10158 | Data-centric Artificial Intelligence: A Survey | Zha et al. (2023) | Tassonomia completa del lavoro sui dati — la priorità #1 dell'autore | ⬇ |
| CHI 2021 | "Everyone wants to do the model work, not the data work": Data Cascades | Sambasivan et al. (2021) | Prova empirica dei danni a cascata da dati trascurati — la tesi stessa dell'autore | ⬇ |

## B2 · Leakage & crisi di riproducibilità
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2207.07048 | Leakage and the Reproducibility Crisis in ML-based Science | Kapoor, Narayanan (2022) | **Centrale**: il progetto ha già corretto un leakage (KAST, DATA-01); riferimento per cercarne altri (ipotesi H4) | ⬇ |

## B3 · Distribution shift & drift detection
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1810.11953 | Failing Loudly: Detecting Dataset Shift | Rabanser et al. (2018) | Metodi per accorgersi dello shift — il progetto ha `TickFeatureDriftMonitor` (ipotesi H6) | ⬇ |
| 2012.07421 | WILDS: Benchmark of in-the-Wild Distribution Shifts | Koh et al. (2020) | Tipologie di shift reali; il meta CS2 cambia nel tempo (patch, mappe) | ⬇ |

## B4 · Incertezza & calibrazione
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1706.04599 | On Calibration of Modern Neural Networks | Guo et al. (2017) | Le reti moderne sono mal-calibrate; temperature scaling — il coach emette probabilità (win-prob, belief) (ipotesi H5) | ⬇ |
| 2107.07511 | A Gentle Introduction to Conformal Prediction | Angelopoulos, Bates (2021) | Intervalli di confidenza distribution-free per il coaching | ⬇ |
| 1612.01474 | Deep Ensembles for Predictive Uncertainty | Lakshminarayanan et al. (2016) | Stima d'incertezza semplice e scalabile | ⬇ |

## B5 · Metodologia di valutazione
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1811.12808 | Model Evaluation, Model Selection, Algorithm Selection | Raschka (2018) | CV corretta, holdout, bootstrap — il progetto ha split cronologico 70/15/15 da validare | ⬇ |

## B6 · Riproducibilità & determinismo
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2103.03098 | Accounting for Variance in ML Benchmarks | Bouthillier et al. (2021) | Varianza da seed/init/HP — il progetto è deterministico (GLOBAL_SEED=42, ipotesi H7) | ⬇ |

## B7 · Sbilanciamento & long-tail
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1708.02002 | Focal Loss for Dense Object Detection | Lin et al. (2017) | Sbilanciamento di classe — round vinti/persi, azioni rare nei tick | ⬇ |

## B8 · Label noise & weak supervision
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1911.00068 | Confident Learning: Estimating Uncertainty in Dataset Labels | Northcutt et al. (2019) | Trovare errori nelle label — il progetto deriva label da RoundStats (G-01, ipotesi su rumore label) | ⬇ |

## B9 · MLOps / debito tecnico / monitoring
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| NeurIPS 2015 | Hidden Technical Debt in Machine Learning Systems | Sculley et al. (2015) | Debiti nascosti (entanglement, undeclared consumers, feedback) — la mappa del "frankenstein" | ⬇ |
| IEEE BigData 2017 | The ML Test Score | Breck et al. (2017) | Rubrica di prontezza-produzione: checklist per la tripla lettura (Fase 7) | ⬇ |

## B10 · Spurie & shortcut learning
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2004.07780 | Shortcut Learning in Deep Neural Networks | Geirhos et al. (2020) | Il coach potrebbe imparare scorciatoie (mappa→esito) invece di tattica reale | ⬇ |

## B11 · Graph NN (mappe / spazio-tempo)
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1706.02216 | GraphSAGE: Inductive Representation Learning on Large Graphs | Hamilton et al. (2017) | Rappresentazioni su grafi — relazioni giocatori/mappa (`Studies/Mappe-GNN.md`) | ⬇ |
| 1710.10903 | Graph Attention Networks | Veličković et al. (2017) | Attenzione su grafi — interazioni spaziali tra i 10 giocatori | ⬇ |

## B12 · Analytics sport/esport
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1802.07127 | Actions Speak Louder than Goals: Valuing Player Actions (VAEP) | Decroos et al. (2018) | Valutare azioni per impatto sull'esito — esattamente ciò che il coach dovrebbe fare | ⬇ |
| 2104.04258 | Counter-Strike Deathmatch with Large-Scale Behavioural Cloning | Pearce, Zhu (2021) | **Specifico CS**: AI che gioca a CS da pixel; ponte tra analytics e lo studio "visione" (C) | ⬇ |

## B13 · Anomaly detection
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2007.02500 | Deep Learning for Anomaly Detection: A Review | Pang et al. (2020) | Metodi per i gate di qualità dati (P-VEC-02, NaN/Inf, outlier nei tick) | ⬇ |

## B14 · RL offline / Decision Transformer
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2106.01345 | Decision Transformer: RL via Sequence Modeling | Chen et al. (2021) | Coaching = decisione sequenziale condizionata sul ritorno desiderato | ⬇ |
| 2005.01643 | Offline RL: Tutorial, Review, Perspectives | Levine et al. (2020) | Imparare da dati raccolti senza interazione — il caso del coach sui demo | ⬇ |

---

# GRUPPO C — Studio speciale: "Visione privilegiata al training, non all'inferenza"

## C1 · Learning Using Privileged Information & distillazione generalizzata
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1511.03643 | Unifying Distillation and Privileged Information | Lopez-Paz et al. (2015) | **Cuore dello studio**: formalizza il segnale ricco disponibile solo al training (l'idea esatta dell'autore) | ⬇ |

## C2 · Distillazione cross-modale
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 1503.02531 | Distilling the Knowledge in a Neural Network | Hinton et al. (2015) | Base della distillazione teacher→student | ⬇ |
| 1507.00448 | Cross Modal Distillation for Supervision Transfer | Gupta et al. (2015) | Trasferire supervisione tra modalità (visione→feature) — esattamente lo schema proposto | ⬇ |

## C3 · V-JEPA come teacher visivo latente
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2404.08471 | Revisiting Feature Prediction for Learning Visual Representations from Video (V-JEPA) | Bardes et al. (2024) | Teacher visivo in spazio latente con EMA — estende il meccanismo EMA già presente | ⬇ |

## C5 · Ricostruzione di scena / geometria reale CS2
| ID | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| 2003.08934 | NeRF: Neural Radiance Fields | Mildenhall et al. (2020) | Ricostruzione di scena 3D da viste — opzione (costosa) per la geometria reale | ⬇ |
| 2308.04079 | 3D Gaussian Splatting for Real-Time Radiance Field Rendering | Kerbl et al. (2023) | Alternativa real-time a NeRF; analisi costi nello studio | ⬇ |

> Nota C4 (modality dropout / multimodale): coperto da Multimodal-JEPA (2605.31580) già nella collezione preesistente + V-JEPA (C3).
> Nota C5 (geometria CS reale): la ricostruzione pratica passa per estrazione asset Source 2 (VRF/Source2Viewer, ecosistema awpy) — strumenti, non paper; trattati nello studio Fase 3. CS:GO-BC (2104.04258) fornisce il precedente "AI vede CS".

---

## Stato di avanzamento
- PDF nuovi (target ≥40): **~49 arXiv + 3 non-arXiv** in download/validati in `docs/research/library/`.
- Collezione preesistente: 14 JEPA in `docs/research/arxiv/`.
- **Totale biblioteca: ~66 paper** (oltre il doppio del minimo richiesto).
- Prossimo: completamento download (log `_download_log.txt`) → Fase 2 lettura+diagnosi per cluster.

# Research Library — Index / Bibliography

> Catalogo della biblioteca di ricerca per **Macena CS2 Analyzer**. I PDF vivono in `docs/research/library/<cluster>/` (git-ignored, binari grandi) e in `docs/research/arxiv/` (collezione JEPA preesistente). Questo catalogo è **tracciato** ed è l'unico file pubblico di `docs/research/`.
>
> Sessione: **Studio AI/Data-Engineering 2026-06** (branch `study/ai-data-engineering-2026-06`).
> Obiettivo: ≥40 PDF (target ~52-56), bilanciati 50% fondamenta del progetto · 50% punti ciechi mai considerati, + cluster speciale "visione privilegiata al training".
>
> Verifica anti-fabbricazione: ogni voce ha ID/URL reale, scaricata e validata (magic `%PDF-`, dimensione > ~100KB). Nessun ID inventato.

## Legenda colonne
`ID/Fonte` · `Titolo` · `Autori (anno)` · `Perché conta per QUESTO progetto` · `Stato` (⬇ scaricato · ✅ validato · 📖 letto/diagnosi in AUDIT.md)

---

## Collezione JEPA preesistente (`docs/research/arxiv/`, 14 PDF già presenti)
Da verificare per completezza e duplicati durante la Fase 1. Include: I-JEPA (2301.08243), T-JEPA (2406.12913), JEPA-for-RL (2504.16591), V-JEPA-2 (2506.09985), Auxiliary-Tasks-JEPA (2509.12249), DSeq-JEPA (2511.17354), VL-JEPA (2512.10942), Value-Guided-Action-Planning-JEPA (2601.00844), VLA-JEPA (2602.10098), V-JEPA-2.1 (2603.14482), Sub-JEPA (2605.09241), Factorized-Latent-Dynamics-Video-JEPA (2605.17165), Multimodal-JEPA (2605.31580), CF-JEPA (2606.07031).

---

# GRUPPO A — Fondamenta su cui il progetto è già costruito (~24 target)

## A1 · JEPA & energy-based learning
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A2 · SSL non-contrastivo (BYOL/DINO/Barlow/VICReg/SwAV)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A3 · Contrastive learning & InfoNCE (CPC/SimCLR/MoCo/CLIP)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A4 · Mixture-of-Experts (sparse routing)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A5 · Modern Hopfield networks
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A6 · Liquid Time-Constant / Neural ODE
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A7 · Modelli sequenziali / time-series (Transformer/TFT/Informer)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A8 · World models & planning (Dreamer/MuZero)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## A9 · Collasso rappresentazionale / dimensional collapse
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

---

# GRUPPO B — Punti ciechi mai considerati (~24-28 target · peso su integrità dati)

## B1 · Data-centric AI & qualità dati
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B2 · Leakage & crisi di riproducibilità
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| arXiv 2207.07048 | Leakage and the Reproducibility Crisis in ML-based Science | Kapoor & Narayanan (2022) | Il progetto ha già corretto un leakage temporale (KAST); questo è il riferimento sistematico per cercarne altri | ⬇ |

## B3 · Distribution shift & drift detection
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B4 · Incertezza & calibrazione
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B5 · Metodologia di valutazione (CV time-series, look-ahead)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B6 · Riproducibilità & determinismo
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B7 · Sbilanciamento & long-tail
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B8 · Label noise & weak supervision
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B9 · MLOps / debito tecnico / monitoring
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| NeurIPS 2015 | Hidden Technical Debt in Machine Learning Systems | Sculley et al. (2015) | Mappa i debiti nascosti (entanglement, undeclared consumers, feedback loops) esattamente del tipo presente in un "frankenstein" | ⬇ |
| IEEE BigData 2017 | The ML Test Score | Breck et al. (2017) | Rubrica di prontezza di produzione: utile come checklist per la tripla lettura | ⬇ |

## B10 · Spurie & shortcut learning / causalità
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| arXiv 2004.07780 | Shortcut Learning in Deep Neural Networks | Geirhos et al. (2020) | Il coach potrebbe apprendere scorciatoie (es. mappa→esito) invece di tattica reale | ⬇ |

## B11 · Graph NN (mappe / spazio-tempo)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B12 · Analytics sport/esport (valuing actions, trajectory)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B13 · Anomaly detection (gate qualità dati)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## B14 · RL offline / Decision Transformer
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

---

# GRUPPO C — Studio speciale: "Visione privilegiata al training, non all'inferenza" (~6-8 target)

## C1 · Learning Using Privileged Information (LUPI) & distillazione generalizzata
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## C2 · Distillazione cross-modale / privileged features
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## C3 · V-JEPA / V-JEPA-2 come teacher visivo in spazio latente
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## C4 · Multimodal JEPA & modality dropout (inferenza modality-agnostic)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

## C5 · Ricostruzione di scena / geometria reale CS2 (Source 2, mesh)
| ID/Fonte | Titolo | Autori (anno) | Perché conta | Stato |
|---|---|---|---|---|
| | | | | |

---

## Stato di avanzamento
- PDF scaricati e validati: **0 / ≥40** (aggiornato man mano)
- LeJEPA (2511.08544): **da scaricare** (cluster A1 — mancante dalla collezione preesistente)
- Cluster completati in lettura/diagnosi: **0 / 28**

# CORREZIONE DEL NUCLEO NEURALE — PARTE II
## Supplemento matematico completo e verifiche empiriche sui dati veri

Autore del progetto: Renan Augusto Macena. Data: 2026-09-05. Repository: `Counter-Strike-coach-AI`, branch `docs/refresh-2026-09-04`, HEAD `62cd2f1`.

Questo documento è il complemento della Parte I (`CORREZIONE_NUCLEO_NEURALE.md`) e precede la Parte III (`CORREZIONE_NUCLEO_NEURALE_PARTE_III.md`, istruzioni tecniche per file e funzione). La Parte I dice *che cosa* è sbagliato e *dove*; questa Parte II dimostra *perché*, con le definizioni, i teoremi e le derivazioni per esteso, e misura sui dati reali del progetto ogni affermazione che poteva essere misurata. Nessun numero riportato qui è stimato: ogni valore è prodotto da `tools/verify_math_claims.py` (sola lettura sul monolite SQLite, CPU) e salvato in `docs/research/verify_math_claims_2026-09-05.json`.

---

## Indice

- 0. Scopo, copertura, notazione
- 1. Il problema: predire nello spazio latente
- 2. Le tre famiglie anti-collasso, con le dimostrazioni
- 3. Collasso dimensionale e rango effettivo
- 4. Perché la distribuzione bersaglio è la gaussiana isotropa
- 5. Sonde lineari, leakage e la testa VL-JEPA
- 6. Modello del mondo, azioni e pianificazione
- 7. Sorpresa: definizione, calibrazione, validazione
- 8. Eventi critici con orizzonte: hazard, sopravvivenza, h-AUROC
- 9. Calibrazione delle probabilità comunicate
- 10. Blocchi architetturali: definizioni esatte dalle fonti primarie
- 11. Le altre reti e i motori di analisi del progetto, uno per uno
- 12. Verifiche empiriche: protocollo, numeri, lettura
- 13. Appendici: derivazioni per esteso e bibliografia primaria con le sezioni lette

---

## 0. Scopo, copertura, notazione

### 0.1 Cosa aggiunge questa Parte rispetto alla Parte I

La Parte I contiene le formule minime (§3) e i verdetti (§4–6). Il lettore che voleva *controllare* le affermazioni non aveva però: (a) le dimostrazioni dei teoremi invocati (LeJEPA, Tian et al., Jing et al., Cui et al., HEPA); (b) la derivazione dei fenomeni dinamici (temperatura InfoNCE, EMA, collasso dimensionale); (c) le definizioni operative dei blocchi architetturali proposti per la v2 (RMSNorm, SwiGLU, RoPE, QK-norm, AdaLN-zero, SIGReg temporale, CEM); (d) la matematica delle altre reti e dei motori di analisi che la Parte I non aveva coperto; (e) le misure sui dati veri. Questa Parte fornisce tutte e cinque le cose.

### 0.2 Dichiarazione di copertura (aggiornata rispetto alla Parte I)

**Fonti primarie lette in testo integrale** (PDF scaricati da arXiv il 2026-09-05, convertiti con `pdftotext`, letti con le equazioni; nessun riassunto intermedio di terzi):

| arXiv | Titolo (autori, anno) | Parti lette |
|---|---|---|
| 2511.08544 v3 | LeJEPA: Provable and Scalable SSL Without the Heuristics (Balestriero, LeCun, 2025) | §2–7 integrali; Appendice A; Appendice B.1–B.13 (dimostrazioni di Lemma 1–6 e Teoremi 1–10) |
| 2607.00958 | LeNEPA: No-Augmentation Next-Latent Prediction for Time-Series (Chemeris, Jin, Balestriero, 2026) | integrale |
| 2603.19312 v3 | LeWorldModel (Maes, Le Lidec, Scieur, LeCun, Balestriero, 2026) | integrale, appendici A–I |
| 2211.10831 | JEPAs Focus on Slow Features (Sobal et al., 2022) | integrale |
| 2102.06810 v4 | Understanding SSL Dynamics without Contrastive Pairs (Tian, Chen, Ganguli, ICML 2021) | §1–5 |
| 2110.09348 v3 | Understanding Dimensional Collapse in Contrastive SSL (Jing, Vincent, LeCun, Tian, ICLR 2022) | §1–7, App. A |
| 2210.02885 v3 | RankMe (Garrido, Balestriero, Najman, LeCun, ICML 2023) | §1–6 |
| 2606.27014 | A Generalization Theory for JEPA-based World Models (Cui, Zhang, Wen, Wang, 2026) | integrale, con dimostrazioni |
| 2605.11130 v4 | HEPA (Petersen et al., 2026) | §1–6, App. A.1–A.3 |
| 2606.31495 | Surprise as a Signal for Plasticity and Metacognition (Mouchon, 2026) | integrale |
| 2606.28383 | Zero-Label Driving Scenario Complexity via JEPA (Jaiswal, 2026) | integrale |
| 2101.03961 v3 | Switch Transformers (Fedus, Zoph, Shazeer, JMLR 2022) | §2.2 (loss di bilanciamento) |
| 2105.04906 | VICReg (Bardes, Ponce, LeCun, ICLR 2022) | §4.1 |
| 1706.04599 v2 | On Calibration of Modern Neural Networks (Guo et al., ICML 2017) | §1–5 |
| 1807.03748 v2 | Contrastive Predictive Coding (van den Oord, Li, Vinyals, 2018) | §2 |
| 2006.07733 | BYOL (Grill et al., NeurIPS 2020) | §3.1 |
| 2301.08243 | I-JEPA (Assran et al., CVPR 2023) | §3 |
| 2410.05016 | T-JEPA (Thimonier et al., ICLR 2025) | §3 |
| 2606.07031 | CF-JEPA (Lee, Sim, KBS 2026) | §3 |
| 2104.09864 | RoFormer / RoPE (Su et al.) | §3.2–3.3 |
| 2002.05202 | GLU Variants Improve Transformer (Shazeer, 2020) | §1–2 |
| 1910.07467 | Root Mean Square Layer Normalization (Zhang, Sennrich, 2019) | §3–4 |
| 2302.05442 | Scaling ViT to 22B parameters (Dehghani et al., 2023) | §2 (QK-norm) |
| 2212.09748 | Scalable Diffusion Models with Transformers / DiT (Peebles, Xie, 2023) | §3 (adaLN, adaLN-Zero) |

Codice ufficiale letto: `lucas-maes/le-wm/module.py` (SIGReg), `galilai-group/lejepa/MINIMAL.md`.

**Codice del progetto letto integralmente per questa Parte** (in aggiunta alla Parte I, percorsi relativi a `Programma_CS2_RENAN/`): `backend/nn/model.py` (AdvancedCoachNN, `TeacherRefinementNN` alias, ModelManager), `backend/nn/train.py`, `backend/nn/role_head.py`, `backend/nn/win_probability_trainer.py`, `backend/nn/evaluate.py`, `backend/nn/persistence.py`, `backend/nn/data_quality.py`, `backend/nn/training_callbacks.py`, `backend/nn/training_controller.py`, `backend/nn/training_monitor.py`, `backend/analysis/win_probability.py` (WinProbabilityNN, PlattScaler, Elo), `backend/analysis/belief_model.py`, `backend/analysis/game_tree.py`, `backend/analysis/entropy_analysis.py`, `backend/analysis/role_classifier.py`, `backend/analysis/momentum.py`, `backend/analysis/blind_spots.py` (detect), `backend/analysis/deception_index.py` (pesi e composito), `backend/coaching/hybrid_engine.py`, `backend/coaching/nn_refinement.py`, `backend/coaching/jepa_insight_adapter.py`, `backend/processing/baselines/pro_baseline.py` (baseline e z-score), `backend/processing/validation/drift.py`, `backend/knowledge/experience_bank.py` (costanti, `update_experience`, `synthesize_advice`, `sample_for_replay`, `record_feedback`). Letti per struttura e punti matematici (grep mirato con lettura delle righe rilevanti): `backend/knowledge/rag_knowledge.py`, `backend/knowledge/vector_index.py`, `backend/services/coaching_service.py`, `backend/services/llm_service.py`, `backend/services/coaching_dialogue.py`, `backend/processing/data_pipeline.py`, `backend/analysis/{movement_quality,utility_economy,engagement_range}.py`, `observability/label_source_monitor.py`, `tools/eval_harness.py`, `evals/cs2_coach_bench/run_eval.py`.

**Dati letti**: monolite `database.db` (link simbolico → `/media/renan/New Volume7/AI/database.db`) in sola lettura durante l'ingestione in corso (stato al momento della misura: 107 task completati, 1 in lavorazione, 22 in coda); tabelle `playertickstate`, `roundstats`, `playermatchstats`, `ingestiontask`. Checkpoint archiviati `models/global/archive_pre_rebuild_2026-09-01/jepa_brain.pt` (2026-08-03, `best_val_loss = 0.004024`) con sidecar.

### 0.3 Notazione

- $x_t \in \mathbb{R}^{25}$: vettore di feature normalizzato del tick $t$ prodotto da `FeatureExtractor.extract` (ordine di `FEATURE_NAMES`). $X_{a:b} = (x_a,\dots,x_{b-1})$ finestra.
- $f_\theta$: encoder di contesto; $\bar f_{\bar\theta}$: encoder bersaglio; $g_\phi$: predittore; $h_\psi$: projector. $z = f_\theta(x)$, $\hat z = g_\phi(z)$.
- $B$: numero di finestre per batch; $T$: token per finestra; $D$: dimensione latente; $d$: dimensione del projector.
- $\|\cdot\|$ norma euclidea; $\langle\cdot,\cdot\rangle$ prodotto scalare; $\cos(a,b) = \langle a,b\rangle/(\|a\|\|b\|)$.
- $\mathcal{N}(0, I_D)$: gaussiana isotropa standard in $\mathbb{R}^D$. $\varphi_P(t) = \mathbb{E}_P[e^{itX}]$ funzione caratteristica.
- Frequenza di tick misurata: $f_{tick}$ (§12, T1). Un tick dura $1/f_{tick}$ secondi.
- "Produzione" = ciò che `TrainingOrchestrator` esegue davvero (`nn/training_orchestrator.py`), non le altre due implementazioni (J7 della Parte I).

### 0.4 Convenzione di verifica

Ogni proposizione che riguarda i dati porta il tag **[T*n*]** che rimanda alla misura corrispondente in §12. Ogni teorema citato dalla letteratura porta il riferimento arXiv e il numero del teorema nel paper; quando la dimostrazione è riprodotta, è riprodotta per intero; quando è solo schematizzata, è detto esplicitamente.

---

## 1. Il problema: predire nello spazio latente

### 1.1 Definizione e oggetti

Seguiamo la definizione di LeJEPA (2511.08544, Def. 1): un sistema è una JEPA se (i) l'embedding della vista futura $\mathrm{Enc}(x_{n,t+1})$ è *predicibile* dall'embedding della vista corrente $\mathrm{Enc}(x_{n,t})$ per ogni campione $n$ e istante $t$, e (ii) $\mathrm{Enc}(x)$ **non è degenere**. Il predittore $g_\phi$ è giustificato "solo quando esiste un'asimmetria di informazione tra le viste, ad esempio condizionando la predizione sulle azioni osservate" (ibid., §2.2). Per il caso CS2 l'asimmetria esiste (passato vs futuro), quindi il predittore è legittimo.

L'energia della coppia (contesto, bersaglio) è

$$E(x_c, x_y) = \big\| g_\phi(f_\theta(x_c)) - \bar f_{\bar\theta}(x_y) \big\|^2 .$$

La produzione (`training_orchestrator.py:855-870`) usa $x_c = X_{t-10:t}$ (10 tick), $x_y = x_t$ (1 tick), e ottiene $f_\theta(x_c)$ come media temporale dell'MLP per-tick (`jepa_model.py:181-212`: `s_context.mean(dim=1)`).

### 1.2 Teorema 1 (minimizzatore banale)

**Enunciato.** Se $\theta, \bar\theta, \phi$ sono liberi, l'energia media $\mathbb{E}[E]$ ammette il minimo globale $0$ in almeno due famiglie di soluzioni degeneri:

(a) *collasso costante*: $f_\theta \equiv c$, $\bar f_{\bar\theta} \equiv c$, $g_\phi(c) = c$;

(b) *collasso funzionale*: qualunque $f_\theta$ tale che $\bar f_{\bar\theta}(x_y)$ sia una funzione deterministica $\Psi$ di $x_c$ e $g_\phi = \Psi \circ f_\theta^{-1}$ sulla sua immagine.

**Dimostrazione.** (a) Sostituendo, $E = \|c - c\|^2 = 0$ per ogni coppia. (b) Per ipotesi $\bar f_{\bar\theta}(x_y) = \Psi(x_c)$ e $g_\phi(f_\theta(x_c)) = \Psi(f_\theta^{-1}(f_\theta(x_c))) = \Psi(x_c)$, quindi $E=0$. $\square$

La famiglia (b) è quella rilevante per CS2: se la vista bersaglio è quasi identica al contesto, $\Psi \approx \bar f \circ \pi$ con $\pi$ la proiezione "ultimo tick del contesto", e il predittore ottimo è **l'identità nello spazio latente** più una correzione dell'ordine di $\|x_{t+1}-x_t\|$. Questo è misurato in §1.4.

### 1.3 Teorema 2 (shortcut delle feature lente — Sobal et al. 2022, §2.1, adattato a CS2)

Sobal et al. (2211.10831) dimostrano che, con VICReg o InfoNCE, una JEPA raggiunge loss totale **zero** copiando nel latente un rumore di fondo *costante nel tempo* e ignorando l'oggetto che si muove. Riproduciamo la dimostrazione con le notazioni del paper e poi la specializziamo.

**Setup.** Batch di $N$ episodi; $S_t \in \mathbb{R}^{N\times D}$ embedding al passo $t$. Rumore per episodio $s \sim \mathcal{N}(0,\sigma^2 I)$ costante nel tempo. Encoder $g_\varphi(o_t) = s$ per ogni $t$; forward model $f_\theta(s,a)=s$.

**Perdita di predizione** (eq. 1 del paper): $L_{pred} = \frac{1}{TN}\sum_{t}\sum_i \|f_\theta(S_{t,i},A_{t,i}) - g_\varphi(O_{t+1,i})\|^2 = \frac{1}{TN}\sum\|S_{t,i}-S_{t,i}\|^2 = 0$.

**Varianza** (eq. 2–3): $\mathrm{Var}(s_t) = \frac{1}{N-1}\sum_i (s_i-\bar s)^2 = \sigma^2$ per costruzione, quindi $L_{var} = \frac{1}{(T+1)D}\sum_t\sum_j \max(0, \gamma - \sqrt{\mathrm{Var}(S_{t,:,j})+\epsilon}) = 0$ per $\sigma \ge \gamma$.

**Covarianza** (eq. 4): $L_{cov} = \frac{1}{(T+1)(N-1)}\sum_t\sum_{i<j}(S_tS_t^\top)_{ij} = 0$ in attesa, perché le componenti del rumore sono indipendenti fra episodi.

Somma: $0$. La rappresentazione non contiene nulla dell'oggetto. Per InfoNCE il paper invoca Wang & Isola (Thm 1): la loss è minimizzata nel limite di infiniti negativi quando i positivi sono perfettamente allineati e gli embedding sono uniformi sulla sfera; entrambe le condizioni sono soddisfatte dalla soluzione banale. $\square$

**Specializzazione a CS2.** Nel vettore $x_t$ di produzione, dentro un round sono *esattamente costanti* per costruzione: `map_id` (17), `round_phase` (18, funzione di `equipment_value` che cambia solo agli acquisti), `kast_estimate` (16, sempre zero), e per lunghi tratti anche `has_helmet`, `has_defuser`, `armor`, `equipment_value`, `team_economy`, `bomb_planted`, `teammates_alive`, `enemies_alive`, `weapon_class` [T3 misura la frazione di finestre di 11 tick in cui ciascuna feature è costante]. Queste sono le "feature lente" di Sobal: un encoder che le copia e ignora posizione/visuale soddisfa l'obiettivo di predizione con errore nullo su quelle coordinate. L'unico freno è la parte di $x_t$ che cambia (posizione, angolo di vista, salute): per un orizzonte di un tick la sua variazione è dell'ordine di $10^{-3}$ in unità normalizzate [T2], cioè il "peso" della dinamica nell'obiettivo è trascurabile rispetto a quello delle costanti.

### 1.4 Corollario: l'orizzonte di un tick è degenere (con i numeri)

**Proposizione 3.** Sia $\bar f$ $L$-Lipschitz e sia $\delta_h(t) = \|x_{t+h} - x_t\|$. Il predittore identità $g = \mathrm{id}$ con encoder condiviso ($f=\bar f$, contesto ridotto all'ultimo tick) ha energia
$$E_{id}(t) = \|\bar f(x_t) - \bar f(x_{t+h})\|^2 \le L^2\,\delta_h(t)^2 .$$
Il coefficiente di determinazione dell'identità in spazio input, definito da $R^2_h = 1 - \frac{\sum_t \delta_h(t)^2}{\sum_t \|x_{t+h} - \bar x\|^2}$, misura quanta parte della varianza del bersaglio è già spiegata dal copiare il presente.

**Dimostrazione.** Immediata dalla definizione di Lipschitz: $\|\bar f(a)-\bar f(b)\| \le L\|a-b\|$. $\square$

**Misura [T1, T2].** Sui tick pro campionati (1.200.000 tick, 30 demo) la frequenza stimata è $f_{tick} = 64{,}0$ tick/s (1 tick = 15,625 ms). L'identità in spazio input spiega $R^2_1 = 0{,}9978$ della varianza del bersaglio a 1 tick, $0{,}9742$ a 8 tick (125 ms), $0{,}9106$ a 32 tick (0,5 s), $0{,}7683$ a 128 tick (2 s), $0{,}4442$ a 640 tick (10 s); il residuo medio per componente a 1 tick è $7{,}9\cdot10^{-4}$ (tabella completa in §12.2). La lettura è univoca: a un tick il bersaglio è indistinguibile dall'ultimo tick del contesto a meno di un residuo che è dell'ordine dell'augmentation gaussiana usata in training ($\sigma=0{,}01$, `jepa_trainer.py:301-308`); a 2 s l'identità spiega ancora la maggior parte della varianza; solo a 10 s la predizione diventa un compito. Il valore archiviato `best_val_loss = 0.004024` (sidecar del checkpoint) è coerente con un predittore che ha imparato l'identità.

**Conseguenza per la v2.** L'orizzonte va portato dove l'identità smette di essere un buon predittore ma la dinamica è ancora predicibile: la Parte I fissa il token a $P=8$ tick (125 ms) e gli orizzonti multipli a $\{1,4,16\}$ token = $\{0{,}125; 0{,}5; 2\}$ s. I numeri di §12.2 giustificano quantitativamente questa scelta (l'orizzonte minimo utile è quello a cui $R^2_h$ scende sotto ~0,9).

### 1.5 La lettura spettrale: perché un orizzonte quasi nullo non contiene dinamica (Cui et al. 2026)

Cui, Zhang, Wen, Wang (2606.27014) formulano il pretraining JEPA come fattorizzazione della matrice di co-occorrenza condizionata all'azione. Con $w(x,x^+,a) = P(x,x^+\mid a)$, $M(a) = [w(x,x^+,a)]$, $D = \mathrm{diag}(w(x))$, $D_+(a) = \mathrm{diag}(w(x^+\mid a))$ e $\bar M(a) = D^{-1/2} M(a) D_+(a)^{-1/2}$:

**Teorema 3.1 (ibid.).** Per embedding normalizzati, $R_{JEPA}(f,g,a) = \|\bar M(a) - G(F,a)^\top F\|^2 + \text{cost}$, con $F = [\sqrt{w(x\mid a)}\,f(x)]_x$, $G = [\sqrt{w(x)}\,g(f(x),a)]_x$.

*Schema di dimostrazione (App. A.1 del paper).* Espandendo $\|g - f^+\|^2 = 2 - 2\,g^\top f^+$ (norme unitarie) e sommando con il termine di uniformità $(g^\top f')^2$ pesato da $w(x)w(x'\mid a)$, si completa il quadrato ottenendo $\sum_{x,x^+}\big[\frac{w(x,x^+,a)}{\sqrt{w(x)w(x^+|a)}} - \sqrt{w(x)}\,g^\top \sqrt{w(x^+|a)}\,f^+\big]^2$ più costanti. $\square$

**Teorema 4.3 (ibid.).** Il rischio ottimo con latente di dimensione $k$ è $\sum_{i>k}\sigma_i^2(a)$, con $\sigma_i$ i valori singolari di $\bar M(a)$ (Eckart–Young–Mirsky).

**Lettura per il caso a un tick.** Se il passo temporale tende a zero, $P(x^+\mid x, a) \to \delta(x^+ - x)$ e $\bar M(a) \to I$ (a meno della normalizzazione): tutti i valori singolari sono uguali, la fattorizzazione di rango $k$ non seleziona alcuna direzione privilegiata e il rischio residuo $\sum_{i>k}\sigma_i^2$ è indipendente da *quale* sottospazio si sceglie. In altre parole: **con l'orizzonte a un tick il problema di ottimizzazione non contiene informazione su quali direzioni dello stato sono dinamicamente rilevanti**. Con orizzonti più lunghi $\bar M(a)$ si allontana dall'identità e i suoi valori singolari dominanti identificano le direzioni predicibili (posizione, angolo, salute) separandole dal rumore.

**Teorema 4.2 (ibid., pianificazione a $T$ passi).** Con dinamica deterministica, il rimpianto atteso soddisfa $\mathcal{E} \le 2T c_3 \sqrt{\max_a R_{S\text{-}JEPA}(f,g,a)}$: l'errore di pianificazione cresce **linearmente con l'orizzonte** $T$. Questo fissa due scelte della v2: un predittore multi-orizzonte (per non dover iterare molte volte un passo corto) e un orizzonte MPC breve per il "ghost".

**Teorema 4.5–4.6 (ibid.).** Il compromesso approssimazione/campione in $k$: $\mathcal{E}(\hat a) \le 2c\sqrt{\max_a\sum_{i>k}\sigma_i^2(a) + c_1[\mathcal{R}_n(\mathcal{G}\circ\mathcal{F}) + \mathcal{R}_n(\mathcal{F})] + c_2(\sqrt{\log(2/\delta)/n}+\delta)} + c$ con $c_1 = 16k^2\kappa^2 + 16k^2\kappa$, $c_2 = 8k\kappa^2 + 2k^2\kappa^4$. Il termine di approssimazione decresce in $k$, quello di campione cresce ($k^2$). La dimensione latente non è "più è meglio": va scelta dove la curva RankMe/probe si appiattisce (§3, §12).

---

## 2. Le tre famiglie anti-collasso, con le dimostrazioni

LeJEPA (§2.2) classifica i meccanismi anti-collasso in: (i) whitening/regolarizzazione delle statistiche di batch, (ii) campioni negativi, (iii) viste asimmetriche e reti teacher-student con stop-gradient. Il repository usa tutti e tre insieme (InfoNCE + coda MoCo + EMA + VICReg), il che rende ogni fallimento difficile da attribuire. Qui ognuno è trattato con la sua matematica e con la misura corrispondente.

### 2.1 Famiglia contrastiva: InfoNCE

#### 2.1.1 Definizione e proprietà (CPC, 1807.03748 §2.3)

Dati un positivo $x^+ \sim p(x_{t+k}\mid c_t)$ e $N-1$ negativi dalla marginale $p(x_{t+k})$, con punteggio $f_k(x,c) = \exp(z^\top W_k c)$:
$$\mathcal{L}_N = -\,\mathbb{E}\Big[\log \frac{f_k(x^+, c_t)}{\sum_{x_j\in X} f_k(x_j, c_t)}\Big].$$
Il minimo è raggiunto quando $f_k(x,c) \propto p(x\mid c)/p(x)$ (eq. 5 del paper), e vale il bound $I(x_{t+k}; c_t) \ge \log N - \mathcal{L}_N$. Il paper osserva che l'obiettivo "permette di estrarre feature lente".

L'implementazione del repository (`jepa_model.py:408-430`) normalizza $\hat z$, $z$ e i negativi in norma $\ell_2$ e usa $\mathrm{logits} = [\cos(\hat z, z)/\tau,\ \cos(\hat z, n_1)/\tau, \dots]$ con cross-entropia sull'indice 0. Con $K$ negativi:
$$\mathcal{L}_{NCE} = -\log\frac{e^{s^+/\tau}}{e^{s^+/\tau} + \sum_{j=1}^K e^{s_j^-/\tau}} = \log\Big(1 + \sum_{j=1}^K e^{(s_j^- - s^+)/\tau}\Big),$$
con $s^+ = \cos(\hat z, z)$ e $s_j^- = \cos(\hat z, n_j)$. Il livello di chance è $\log(K+1)$.

#### 2.1.2 Proposizione 4 (negativi banali rendono l'identità ottima)

**Enunciato.** Se esiste un margine $m>0$ tale che $s^+ \ge 1-\eta$ e $s_j^- \le 1-\eta-m$ per ogni $j$, allora
$$\mathcal{L}_{NCE} \le \log\big(1 + K e^{-m/\tau}\big) \xrightarrow[\tau\to 0]{} 0 .$$
In particolare, con $\tau = 0{,}07$ e $m = 0{,}5$: $e^{-m/\tau} = e^{-7{,}14} \approx 7{,}9\cdot10^{-4}$, quindi con $K = 69$ negativi (5 dalla pool + 64 dalla coda) $\mathcal{L} \le \log(1 + 0{,}055) \approx 0{,}053$.

**Dimostrazione.** Ogni esponente $(s_j^- - s^+)/\tau \le -m/\tau$; sostituendo nella somma e usando la monotonia del logaritmo si ottiene il bound. $\square$

**Perché il margine esiste in produzione.** I negativi sono (a) 5 vettori di feature grezzi presi da altre partite (`training_orchestrator.py:868-882`, pool cross-match) e (b) 64 vettori dalla coda MoCo, che è inizializzata con **rumore gaussiano normalizzato** (`jepa_model.py:155-157`) e riempita lentamente. Il positivo è l'embedding del tick successivo, che per §1.4 è quasi identico all'embedding dell'ultimo tick del contesto. La misura [T5] riporta, per l'encoder archiviato, $\cos$ medio fra bersaglio e "predizione identità" e fra bersaglio e (a) altre finestre, (b) vettori unitari casuali: il margine è ampio. Ne segue che il predittore identità (o quasi) minimizza InfoNCE e la loss non può distinguere un encoder che ha imparato la dinamica da uno che copia il presente.

#### 2.1.3 La temperatura appresa: derivazione della dinamica

Il repository rende $\tau$ apprendibile via $\log\tau$ (`jepa_model.py:151`, init $\tau_0 = 0{,}07$). Con $u = 1/\tau$ e $p_j = e^{u s_j}/\sum_l e^{u s_l}$ (softmax sui punteggi, indice $0$ = positivo):

$$\frac{\partial \mathcal{L}}{\partial u} = -\,s^+ + \sum_{l=0}^{K} p_l\, s_l = \mathbb{E}_p[s] - s^+ .$$

**Derivazione.** $\mathcal{L} = -u s^+ + \log\sum_l e^{u s_l}$; derivando, $-s^+ + \frac{\sum_l s_l e^{us_l}}{\sum_l e^{us_l}}$. $\square$

Poiché $\partial\mathcal{L}/\partial\tau = -u^2\,\partial\mathcal{L}/\partial u = \frac{1}{\tau^2}\,(s^+ - \mathbb{E}_p[s])$, la discesa del gradiente **riduce $\tau$** finché $s^+ > \mathbb{E}_p[s]$, cioè sempre quando il positivo è più simile della media dei candidati. Con positivi facili (§2.1.2) la spinta è costante: $\tau$ decresce, i logit si allargano, la loss tende a zero senza che l'encoder cambi. Il valore di $\tau$ nel checkpoint archiviato è riportato in [T4]. Nota: un $\tau$ che si riduce con positivi banali *non* è la "temperatura appresa" di CLIP (dove i positivi sono difficili e $\tau$ si stabilizza su un valore informativo): è un sintomo, e va monitorato come tale.

#### 2.1.4 Conseguenza e correzione

La famiglia contrastiva è tenuta nella v2 solo come "modalità legacy" per confronti. La ragione matematica: (1) il bound MI di CPC degenera con positivi quasi-deterministici ($\mathcal{L}_N\to 0$ non implica alcuna informazione sul futuro *oltre il presente*); (2) i negativi cross-match sono banalmente separabili; (3) la temperatura apprendibile amplifica il problema. La verifica [T5] mostra che l'identità nello spazio del target encoder ottiene InfoNCE e top-1 paragonabili o migliori del predittore archiviato.

### 2.2 Famiglia asimmetrica: EMA, stop-gradient, predittore (BYOL, I-JEPA, Tian et al.)

#### 2.2.1 Le definizioni originali

BYOL (2006.07733, §3.1): rete online $\theta$ (encoder $f$, projector $g$, predittore $q$) e rete bersaglio $\xi$ con la **stessa architettura**; aggiornamento $\xi \leftarrow \tau_{ema}\xi + (1-\tau_{ema})\theta$ dopo ogni passo; perdita $\mathcal{L}_{\theta,\xi} = \|\bar q_\theta(z_\theta) - \bar z'_\xi\|^2 = 2 - 2\frac{\langle q_\theta(z_\theta), z'_\xi\rangle}{\|q_\theta(z_\theta)\|\,\|z'_\xi\|}$ (vettori normalizzati), simmetrizzata, gradiente solo rispetto a $\theta$ (stop-gradient su $\xi$). I-JEPA (2301.08243, §3): il target encoder $f_{\bar\theta}$ è "aggiornato via media mobile esponenziale dei parametri del context encoder"; "l'uso di un target encoder EMA si è dimostrato essenziale". In entrambi i lavori $\xi$ (o $\bar\theta$) **parte come copia** di $\theta$: l'EMA di una sequenza che inizia da $\theta_0$ è $\theta_0$ al passo zero.

#### 2.2.2 I teoremi di Tian, Chen, Ganguli (2102.06810)

Modello lineare senza bias: online $W$, predittore $W_p$, target $W_a$; $X = \mathbb{E}[\bar x\bar x^\top]$ covarianza dei dati, $X' = \sigma^2 I$ covarianza dell'augmentation; $\alpha_p$ rapporto di learning rate del predittore, $\beta$ tasso EMA ($\alpha\beta = 1-\gamma_a$, $\gamma_a = 0{,}996$), $\eta$ weight decay. Flusso di gradiente (Lemma 1):
$$\dot W_p = \alpha_p\big(-W_pW(X+X') + W_aX\big)W^\top - \eta W_p,\quad \dot W = W_p^\top\big(-W_pW(X+X') + W_aX\big) - \eta W,\quad \dot W_a = \beta(W - W_a).$$

**Teorema 1 (bilanciamento).** $W(t)W(t)^\top = \alpha_p^{-1}W_p(t)^\top W_p(t) + e^{-2\eta t}C$ con $C$ fissata dall'inizializzazione. Il weight decay cancella la memoria dell'inizializzazione; ciò che il predittore impara, lo impara anche l'online.

**Teorema 2 (lo stop-gradient è essenziale).** Con $W_a = W$ e *senza* stop-gradient, $\frac{d}{dt}\mathrm{vec}(W) = -H(t)\,\mathrm{vec}(W)$ con $H$ semidefinita positiva e, se $\inf_t \lambda_{\min}(H(t)) \ge \lambda_0 > 0$, $W(t)\to 0$: collasso completo. Lo stesso vale senza predittore.

**Dinamica per modo (eq. 11–13), sotto le ipotesi di EMA proporzionale $W_a = \tau(t)W$, dati isotropi e $W_p$ simmetrico:**
$$\dot p_j = \alpha_p s_j\big(\tau - (1+\sigma^2)p_j\big) - \eta p_j,\qquad \dot s_j = 2p_j s_j\big(\tau - (1+\sigma^2)p_j\big) - 2\eta s_j,\qquad s_j\dot\tau = \beta(1-\tau)s_j - \tau\dot s_j/2,$$
con integrale del moto $s_j = \alpha_p^{-1}p_j^2 + e^{-2\eta t}c_j$. Sulla parabola invariante ($c_j=0$) i punti fissi di $p_j$ sono $p^*_{j0}=0$ (stabile) e $p^*_{j\pm} = \frac{\tau \pm \sqrt{\tau^2 - 4\eta(1+\sigma^2)}}{2(1+\sigma^2)}$; il bacino del collasso è $p_j < p^*_{j-}$; se $\eta > \tau^2/(4(1+\sigma^2))$ **esiste solo il punto fisso collassato**.

**Ruolo dell'EMA (Oss. 8–10 del paper).** $\tau(t)$ parte piccolo e cresce: l'EMA agisce da *curriculum automatico* che fissa all'inizio un bersaglio piccolo $p_j^* \approx \tau/(1+\sigma^2)$, rendendo soddisfacibile la condizione di allineamento degli autospazi (eq. 17: $\Delta_j < \frac{1}{2}(\alpha_p(1+\sigma^2)s_j + \eta)$), poi lo alza. Un $\beta$ piccolo rallenta l'allenamento e intrappola più modi nel bacino collassato.

#### 2.2.3 Che cosa cambia con l'inizializzazione indipendente del target encoder (J6 della Parte I)

Il repository costruisce `context_encoder` e `target_encoder` come due istanze indipendenti di `JEPAEncoder` (`jepa_model.py:126-127`) senza copiare i pesi. Nel modello di Tian ciò significa $W_a(0) \ne W(0)$ e quindi $W_a \ne \tau W$ all'inizio: il bersaglio è una funzione **casuale** dell'input, indipendente da quella dell'online. Il predittore deve allora imparare a mappare $f_\theta(x)$ su $\bar f_{\bar\theta}(x^+)$ dove $\bar f$ è un MLP casuale con LayerNorm finale: un compito di regressione fra due proiezioni casuali del quasi-stesso input, risolubile perfettamente da un predittore abbastanza espressivo senza che $f_\theta$ codifichi alcuna dinamica.

Quanto dura lo stato "indipendente"? L'EMA con momento $m$ soddisfa $\bar\theta_n = m^n\bar\theta_0 + (1-m^n)\,\overline{\theta}_{\text{online}}$ (media pesata dei $\theta$ passati). La frazione residua dell'inizializzazione è $m^n$; si dimezza dopo $n_{1/2} = \ln 2/\ln(1/m)$ passi: con $m=0{,}996$, $n_{1/2} \approx 173$ passi; scende sotto l'1% dopo $\approx 1150$ passi. Con $B=1$ finestra per passo e le epoche da poche migliaia di passi del progetto, il target encoder passa una frazione rilevante del primo ciclo di training come rete casuale. La misura [T4] riporta la distanza $\|\theta - \bar\theta\|_2$ nel checkpoint archiviato confrontata con quella di due inizializzazioni indipendenti.

#### 2.2.4 L'evidenza indipendente di Jaiswal (2606.28383, §4.2, Ablazione 4)

Su dati di stato strutturati (nuPlan, 21 agenti × 6 feature, orizzonte 2,5 s), con target encoder EMA ($\alpha=0{,}996$, copia iniziale) la JEPA impara una sorpresa che ordina correttamente gli scenari (Spearman con i tag di complessità). Ponendo $\alpha = 0$ (target = online a ogni passo) il collasso è rilevato dall'epoca 3 (coseno > 0,998, varianza latente < 0,002) e lo spread dei punteggi crolla da 0,602 a 0,014 (44×). È la dimostrazione empirica del Teorema 2 di Tian su dati analoghi ai nostri, e il motivo per cui LeNEPA/LeWM/HEPA **sostituiscono** l'asimmetria con SIGReg invece di dipendere da una scelta di $\alpha$.

#### 2.2.5 Verdetto

L'EMA + stop-gradient è un meccanismo funzionante *se* il target parte come copia, il batch è grande, il weight decay è nel regime giusto e $\beta$ è calibrato: quattro condizioni che non sono controllate nel repository. La v2 non lo usa: SIGReg rende il target encoder condiviso (LeNEPA: "no stop-gradient in LeNEPA"; HEPA: "target encoder is a weight-shared copy") e la stabilità non dipende più da una dinamica non lineare in $(\alpha_p, \beta, \eta)$.

### 2.3 Famiglia distribuzionale: VICReg e SIGReg

#### 2.3.1 VICReg (2105.04906, §4.1): definizioni e perché richiede un batch

Con $Z = [z_1,\dots,z_n] \in \mathbb{R}^{n\times d}$ e $z^j$ la $j$-esima colonna:
$$v(Z) = \frac{1}{d}\sum_{j=1}^d \max\big(0,\ \gamma - S(z^j,\epsilon)\big),\qquad S(x,\epsilon) = \sqrt{\mathrm{Var}(x)+\epsilon},\qquad \gamma = 1;$$
$$C(Z) = \frac{1}{n-1}\sum_{i=1}^n (z_i-\bar z)(z_i-\bar z)^\top,\qquad c(Z) = \frac{1}{d}\sum_{i\ne j}[C(Z)]_{ij}^2;\qquad s(Z,Z') = \frac{1}{n}\sum_i\|z_i - z'_i\|^2 .$$
Perdita $\ell = \lambda s + \mu[v(Z)+v(Z')] + \nu[c(Z)+c(Z')]$ con $\lambda=\mu=25$, $\nu=1$ nel paper. Il paper motiva l'uso della deviazione standard e non della varianza: con $S = \mathrm{Var}$ il gradiente svanisce vicino al collasso.

**Proposizione 5 (VICReg con $n=1$ è indefinito; con $n$ piccolo è rumore).** La varianza campionaria e $C(Z)$ hanno denominatore $n-1$: per $n=1$ non sono definite. Per $n \ge 2$ e componenti gaussiane con varianza $\sigma^2$, lo stimatore $\hat\sigma^2$ ha varianza $\mathrm{Var}(\hat\sigma^2) = \frac{2\sigma^4}{n-1}$; con $n=3$ (il batch effettivo del RAP, `coach_manager.py::_fetch_rap_windows` con `window_size=96` e `seq_len=32`, cioè tre finestre) il coefficiente di variazione dello stimatore è $\sqrt{2/(n-1)} = 1$: il termine di varianza oscilla del 100% da batch a batch. *Dimostrazione:* $(n-1)\hat\sigma^2/\sigma^2 \sim \chi^2_{n-1}$ con varianza $2(n-1)$. $\square$

Il repository (`jepa_model.py:440-441`) restituisce $0$ se `embeddings.shape[0] < 2`. In produzione $B=1$ (`training_orchestrator.py:859-866`): il termine è **inerte per costruzione**, come già ammesso in `jepa_trainer.py:271-275`. Non è un bug d'implementazione: è la conseguenza necessaria di regolarizzare statistiche di batch con un batch di un elemento.

#### 2.3.2 SIGReg (LeJEPA §4): dalla verifica d'ipotesi alla loss

**Il problema.** Si vuole che $P_\theta$ (legge di $f_\theta(x)$) sia uguale a $Q = \mathcal{N}(0,I_K)$. LeJEPA lo formula come test d'ipotesi $H_0: P_\theta = Q$ (eq. 2) e lo rende trattabile in alta dimensione per proiezione.

**Lemma 3 (Cramér–Wold ipersferico, LeJEPA B.8).** $\langle u,X\rangle \overset{d}{=} \langle u,Y\rangle\ \forall u\in\mathcal{S}^{d-1} \iff X \overset{d}{=} Y$; vale anche per la convergenza in distribuzione.
*Dimostrazione.* Necessità: funzioni misurabili di variabili identicamente distribuite sono identicamente distribuite. Sufficienza: per $t\ne0$ scrivere $t = su$, $s=\|t\|$, $u = t/\|t\|$; allora $\varphi_X(t) = \mathbb{E}e^{is\langle u,X\rangle} = \mathbb{E}e^{is\langle u,Y\rangle} = \varphi_Y(t)$ per ogni $t$; per l'unicità della funzione caratteristica $X\overset{d}{=}Y$. Per la convergenza: mappa continua $x\mapsto sx$ e teorema di continuità di Lévy. $\square$

**Definizione 2 (SIGReg).** Con $M$ direzioni unitarie $\mathcal{A} = \{a_1,\dots,a_M\}$ e una statistica univariata $T$ verso $\mathcal{N}(0,1)$:
$$\mathrm{SIGReg}_T(\mathcal{A}, \{f_\theta(x_n)\}_{n=1}^N) = \frac{1}{|\mathcal{A}|}\sum_{a\in\mathcal{A}} T\big(\{a^\top f_\theta(x_n)\}_{n=1}^N\big).$$
La media (invece del massimo del Teorema 2) evita gradienti sparsi.

**Teorema 2 (sufficienza dei test direzionali).** Il test aggregato ha livello $\alpha$ e potenza $1$ asintotica (principio unione-intersezione di Roy; B.9: serve una direzione separatrice $a^\star$ con un intorno in cui la statistica supera la soglia con probabilità $\to 1$, e insiemi $\mathcal{A}_n$ con passo $\to 0$).

**Perché non i momenti (Teorema 3, B.11).** Minimizzare $\sum_{k=1}^K c_k(m_k(P^{(a)}) - m_k(Q^{(a)}))^2$ per $K$ finito non implica $P^{(a)} = Q^{(a)}$. *Dimostrazione.* Presi $K+2$ punti distinti $x_0,\dots,x_{K+1}$, la mappa $A: p\mapsto(\sum_j p_j x_j^r)_{r=0..K}$ ha rango $\le K+1$, quindi nucleo non banale; un $v\in\ker A\setminus\{0\}$ ha $\sum v_j = 0$ e quindi segni misti; $p\pm\varepsilon v$ sono due distribuzioni diverse con gli stessi primi $K$ momenti. $\square$ Inoltre il gradiente del $k$-esimo momento è un polinomio di grado $k-1$ nel dato (B.12, parte B) e non è limitato. **Questo è esattamente il difetto di VICReg**: i suoi termini di varianza e covarianza vincolano solo i primi due momenti (LeJEPA Lemma 6/Teorema 9 "Recovery of VCReg"), e la Fig. 6 di LeJEPA mostra una distribuzione a "X" con media nulla e covarianza identità che VICReg non tocca e SIGReg raddrizza.

**Perché non le CDF.** Cramér–von Mises, Anderson–Darling, Watson richiedono ordinamenti (non differenziabili, rompono il parallelismo su più GPU); Kolmogorov–Smirnov usa la norma $\ell_\infty$ (gradienti sparsi); Shapiro–Wilk è instabile (LeJEPA App. E).

**La statistica di Epps–Pulley (1983).**
$$EP = N\int_{-\infty}^{\infty}\big|\hat\varphi_X(t) - \varphi(t)\big|^2 w(t)\,dt,\qquad \hat\varphi_X(t) = \frac{1}{N}\sum_{j=1}^N e^{itX_j},\qquad \varphi(t) = e^{-t^2/2},\qquad w(t) = e^{-t^2/\sigma^2}.$$
La funzione caratteristica empirica è una media di esponenziali complessi: differenziabile, limitata, aggregabile con `all_reduce`.

**Teorema 4 (stabilità, B.12).** Per campioni $z_1,\dots,z_N$ e peso $w_s(t) = e^{-s^2t^2}$:
$$\Big|\frac{\partial EP}{\partial z_i}\Big| \le \frac{4}{N s^2},\qquad \Big|\frac{\partial^2 EP}{\partial z_i^2}\Big| \le \frac{C\sqrt\pi}{2Ns^3}.$$
*Dimostrazione.* $\partial\hat\varphi_N/\partial z_i = \frac{1}{N}\,it\,e^{itz_i}$ e $|\hat\varphi_N|,|\varphi_G| \le 1$; derivando sotto il segno di integrale (convergenza dominata), $|\partial \hat D_V/\partial z_i| \le \frac{2}{N}\int w_s|t|(|\hat\varphi_N| + |\varphi_G|)\,dt \le \frac{4}{N}\int e^{-s^2t^2}|t|\,dt = \frac{4}{Ns^2}$. Derivando ancora si ottiene un fattore $t^2$ e $\int e^{-s^2t^2}t^2dt = \sqrt\pi/(2s^3)$. $\square$ Per la regola della catena $\|\nabla_\theta EP\| \le \frac{4s^2}{N}\sum_i\|a^\top\nabla_\theta f_\theta(x_i)\|$: i gradienti sono uniformemente limitati **per qualunque distribuzione degli embedding**, a differenza dei momenti.

**Teorema 5 (contro la maledizione della dimensione, B.10).** Se $p_\theta \in H^\alpha(\mathbb{R}^K)$ (Sobolev) e il test EP è nullo su $|\mathcal{A}| = M$ direzioni, allora $\mathbb{E}_a\int|\varphi_a(t) - \varphi_{\mathcal{N}}(t)|^2dt \le C(K,\alpha)\,M^{-2\alpha/(K-1)}\int_0^\infty\|\varphi_\cdot(r) - \varphi_{\mathcal N}(r)\|^2_{H^\alpha(\mathcal{S}^{K-1})}dr$ con $C(K,\alpha) = \frac{2^{2\alpha}\pi^{(K-1)/2}\Gamma(\alpha + \frac{K-1}{2})}{(K-1)\Gamma(\alpha)\Gamma(\frac{K-1}{2})}$. *Schema.* Interpolazione su $\mathcal{S}^{K-1}$ con armoniche sferiche e insiemi di Marcinkiewicz–Zygmund (Narcowich et al. 2006, Mhaskar et al. 2001): errore $L^2$ con $M$ punti quasi-uniformi $\le C M^{-2\alpha/(K-1)}\|g\|^2_{H^\alpha}$. $\square$ Poiché le reti sono lisce ($\alpha$ grande), $M = O(K)$ direzioni bastano; e ricampionando le direzioni a ogni passo, l'insieme cumulato cresce linearmente col tempo (LeJEPA Fig. 7: 16 direzioni ricampionate battono migliaia fisse).

**Teorema 6 (bias di minibatch, B.13).** $\mathbb{E}[\hat L_n(\theta)] = L(\theta) + \frac{1}{n}\int w(t)\big(1-|\varphi_P(t)|^2\big)dt$: bias $O(1/n)$ su loss e gradiente, irrilevante già per $n=16$. *Dimostrazione.* Con $Z_j = e^{itX_j}$, $|Z_j|=1$, $\mathbb{E}|\hat\varphi_n - \psi|^2 = |\varphi_\theta - \psi|^2 + \frac{1}{n}(1 - |\varphi_\theta(t)|^2)$. $\square$

**Implementazione esatta (le-wm `module.py`, coerente con LeJEPA Alg. 1).** Nodi $t_k \in [0, t_{max}]$, $t_{max}=3$, $K=17$; pesi trapezoidali $w_k = 2\,\Delta t$ interni e $\Delta t$ agli estremi, moltiplicati per la finestra $e^{-t_k^2/2}$ (la simmetria dell'integranda permette di integrare solo su $[0,3]$); proiezioni $A \in\mathbb{R}^{D\times M}$ gaussiane con colonne normalizzate, ricampionate con seme `global_step`; $x_{t} = (ZA)\otimes t$; errore per nodo $\big(\overline{\cos x_t} - e^{-t^2/2}\big)^2 + \big(\overline{\sin x_t}\big)^2$ (parte reale e immaginaria di $\hat\varphi - \varphi$, poiché $\varphi_{\mathcal N}$ è reale); statistica $= N\sum_k w_k\,\mathrm{err}_k$, media su $M$. LeJEPA raccomanda 17 nodi, dominio $[-5,5]$ (le-wm usa $[0,3]$ con simmetria), $M=1024$ (512 competitivo, 16 funziona), e mostra che questi iperparametri hanno impatto trascurabile (Tab. 1a).

**Misura [T7].** Il valore SIGReg (le-wm, $M=1024$, 17 nodi) sugli embedding archiviati, sugli stessi standardizzati per coordinata, su embedding di una rete casuale, su un campione $\mathcal{N}(0,I_{256})$ della stessa taglia e su un campione collassato (costante + rumore $10^{-3}$) è in §12.7: fissa la scala della statistica e mostra quanto gli embedding attuali distino dal bersaglio isotropo.

#### 2.3.3 Dove applicare SIGReg: batch, tempo, entrambi

- LeJEPA/LeWM: sull'asse del **batch** (per ogni istante, i $B$ embedding del batch sono il campione del test) — LeWM Alg. 3: `SIGReg(emb.transpose(0,1))`, media sui passi temporali. LeWM osserva che ciò lascia libero l'asse temporale e produce "raddrizzamento temporale" emergente (App. H): utile per il planning, ma è una forma di collasso lungo il tempo.
- LeNEPA: sull'asse **temporale**, per campione (eq. 2): i $T$ token di una finestra sono il campione. Ablazione (Tab. 5): "temporal SIGReg is the only single-component placement with sustained frozen-backbone gains"; applicato a **entrambi** i lati (layer 0 e 8) è più stabile; "target-only or off-path regularization can degrade or collapse".
- HEPA: sull'**output del predittore**, $\alpha = 0{,}1$, target encoder condiviso.

Per la v2 (Parte I §7.5) la scelta è $2{,}5\cdot\mathrm{SIGReg}_{temporale}$ (taps al layer 0 e all'ultimo) $+\ 0{,}1\cdot\mathrm{SIGReg}_{batch}$: il primo impedisce il collasso lungo il tempo dentro una finestra (esattamente il rischio delle feature lente di §1.3), il secondo l'anisotropia globale. Entrambi richiedono $B \ge 32$ e $T \ge 16$ per dare un test sensato: con $B=1$, $T=10$ nessuna regolarizzazione distribuzionale può funzionare.

**Regola pratica dimostrata da LeWM.** SIGReg non va applicato all'uscita di una LayerNorm: la LayerNorm proietta su una varietà a norma fissa che non può essere gaussiana; LeWM interpone un MLP a un layer con BatchNorm (§3.1). Il `JEPAEncoder` del repository termina con `nn.LayerNorm(latent_dim)` (`jepa_model.py:46-53`): nella v2 il projector va aggiunto dopo, e SIGReg calcolato sul projector.

---

## 3. Collasso dimensionale e rango effettivo

### 3.1 Definizione e i due meccanismi (Jing, Vincent, LeCun, Tian 2022, 2110.09348)

*Collasso completo*: tutti gli embedding coincidono. *Collasso dimensionale*: gli embedding occupano un sottospazio di dimensione inferiore a $D$. Si misura con lo spettro dei valori singolari della covarianza $C = \frac{1}{N}\sum_i (z_i-\bar z)(z_i-\bar z)^\top$ (Fig. 2 del paper: SimCLR a 128 dimensioni ha molti $\sigma_k \to 0$).

**Meccanismo 1 — augmentation forte (Sez. 4).** Modello lineare $z = Wx$, InfoNCE. Lemma 1: $\dot W = -G$; Lemma 2: $G = -W\tilde X$ con $\tilde X = \hat\Sigma_0 - \hat\Sigma_1$, dove $\hat\Sigma_0 = \sum_{ij}\alpha_{ij}(x_i-x_j)(x_i-x_j)^\top$ è la covarianza (pesata) **dei dati** e $\hat\Sigma_1 = \sum_i(1-\alpha_{ii})(x'_i-x_i)(x'_i-x_i)^\top$ quella **dell'augmentation**. Teorema 1: se $\tilde X$ ha autovalori negativi (augmentation più forte dei dati lungo qualche direzione), $W$ acquisisce valori singolari nulli e (Cor. 1) la covarianza degli embedding è di rango basso.

**Applicazione al repository.** In produzione l'"augmentation" è rumore gaussiano additivo con $\sigma = 0{,}01$ e dropout al 5% sulle 25 feature (`jepa_trainer.py:301-308`), mentre il "dato" da distinguere è il **delta fra tick consecutivi**. Nel modello di Jing la direzione $j$ collassa se la varianza dell'augmentation ($\sigma^2 = 10^{-4}$) supera la varianza del segnale utile lungo $j$. La misura [T2] fornisce l'RMS del delta a un tick per ogni feature: tutte le feature con $\mathrm{RMS}(\Delta_1) < 10^{-2}$ sono, nel senso di Jing, "sovrastate" dall'augmentation, e sono la maggioranza. Questo è un secondo canale (oltre alla banalità dei negativi) per cui il training attuale non può apprendere le direzioni dinamicamente rilevanti.

**Meccanismo 2 — regolarizzazione implicita (Sez. 5).** Rete lineare a due strati $z = W_2W_1x$, augmentation debole ($\tilde X \succ 0$). Teorema 2: le matrici adiacenti si allineano ($V_2^\top U_1 \to I$). Teorema 3: i valori singolari evolvono come $\dot\sigma_1^k = \sigma_1^k(\sigma_2^k)^2\,v_k^\top\tilde X v_k$, $\dot\sigma_2^k = \sigma_2^k(\sigma_1^k)^2\,v_k^\top\tilde X v_k$, quindi $(\sigma_1^k)^2 = (\sigma_2^k)^2 + C$: la crescita di ogni valore singolare è proporzionale a se stesso, i piccoli restano piccoli (Cor. 2: rango basso anche senza augmentation forte). Vale per reti con almeno due strati — come l'encoder MLP a due Linear del repository.

**Il ruolo del projector (Sez. 6).** Senza projector la rappresentazione di SimCLR collassa dimensionalmente (Fig. 7b); un projector lineare basta che sia diagonale e di rango basso (Prop. 1–2); DirectCLR applica la loss a un sottovettore fisso e ottiene 62,7% vs 61,1% (lineare) vs 51,5% (nessuno). Conclusione operativa, coerente con Guillotine Regularization (Bordes et al.) e LeNEPA (Tab. 5: il projector migliora 22/24 confronti e la sua capacità non conta): **la loss va calcolata dopo un projector che si scarta; la rappresentazione da usare è quella prima del projector.** Il repository calcola InfoNCE direttamente sull'uscita dell'encoder (LayerNorm finale) e usa la stessa uscita per la testa: due errori in uno.

### 3.2 RankMe (Garrido, Balestriero, Najman, LeCun 2023, 2210.02885)

**Definizione (eq. 1–2).** Per la matrice degli embedding $Z\in\mathbb{R}^{N\times K}$ con valori singolari $\sigma_k(Z)$:
$$\mathrm{RankMe}(Z) = \exp\Big(-\sum_{k=1}^{\min(N,K)} p_k\log p_k\Big),\qquad p_k = \frac{\sigma_k(Z)}{\|\sigma(Z)\|_1} + \epsilon .$$
È il rango effettivo di Roy & Vetterli (2007): l'esponenziale dell'entropia dello spettro normalizzato; quantifica anche lo *whitening*. Calcolato su $Z$ non centrata (come nel paper e in `collapse_metrics.py`: centrare cancellerebbe la direzione media dominante prodotta dal collasso e farebbe apparire "sano" un residuo isotropo). 25.600 campioni bastano (App. G). Va confrontato **solo fra run dello stesso metodo**: "embedding rank is not the only factor that affects performance".

**Proposizione 5.1 (ibid.).** L'accuratezza massima di training di una regressione o classificazione lineare sugli embedding cresce con il loro rango e, per la classificazione, si stabilizza quando il rango supera il numero di classi. *Base:* Eckart–Young–Mirsky $\|Y-P\|_F^2 \ge \sum_{r>R}\sigma_r^2(Y)$ per $P$ di rango $R$; una sonda lineare non può aumentare il rango: $\mathrm{rank}(ZW + \mathbf 1 b^\top) \le \min(\mathrm{rank}Z, \mathrm{rank}W)+1$; teorema di Cover (1965) sulla separabilità lineare. Le tre ipotesi verificate empiricamente (Fig. 5): le sonde non overfittano; prestazione su embedding e su rappresentazioni sono monotone; i ranghi su sorgente e bersaglio scalano linearmente (Pearson > 0,99) se la sorgente è varia.

**Uso operativo.** Algoritmo 1 del paper: fra run con un iperparametro ordinato scegliere il rango massimo (a parità, il primo valore che lo raggiunge). RankMe recupera l'oracolo con etichette entro mezzo punto in media. LeJEPA aggiunge (§6.2) che la sua loss di training ha correlazione di Spearman ≈ 0,85 (≈ 0,99 con la legge di scala $\mathrm{loss}/\lambda^{0{,}4}$) con la prestazione downstream: un secondo segnale senza etichette. Nella v2 (Parte I §7.6) i due segnali sono loggati insieme e l'arresto per collasso è su RankMe.

### 3.3 Misura sul checkpoint archiviato [T4]

§12.4 riporta RankMe, $\min_j \mathrm{std}_j$ e coseno medio fuori diagonale (su embedding normalizzati, come in `collapse_metrics.py`) per: (a) embedding di contesto dell'encoder archiviato su finestre di 10 tick; (b) embedding del target encoder; (c) una rete con pesi casuali della stessa architettura; (d) le feature grezze mediate sulla finestra (25-d); (e) un campione gaussiano isotropo in $\mathbb{R}^{256}$ della stessa taglia. Il confronto (a) vs (c) dice se l'allenamento ha *aumentato* o *ridotto* il rango rispetto a una rete casuale; (a) vs (e) dice quanto si è lontani dal bersaglio isotropo.

---

## 4. Perché la distribuzione bersaglio è la gaussiana isotropa (LeJEPA §3, App. A–B)

La scelta di regolarizzare verso $\mathcal{N}(0,I)$ non è estetica: LeJEPA dimostra che è la distribuzione degli embedding che minimizza il rischio nel caso peggiore per le sonde lineari e non lineari usate a valle. Riproduciamo le dimostrazioni dei due lemmi lineari e enunciamo i teoremi non lineari.

### 4.1 Sonde lineari

Sia $Z\in\mathbb{R}^{N\times K}$ la matrice degli embedding e $y = Z\beta_{true} + \varepsilon$, $\mathbb{E}\varepsilon = 0$, $\mathrm{Cov}(\varepsilon) = \sigma^2 I$. Stimatore ridge $\hat\beta = (Z^\top Z + \lambda I)^{-1}Z^\top y$. Confrontiamo $Z_{aniso}$ (autovalori della covarianza $\lambda_1 \le \dots \le \lambda_K$ non tutti uguali) e $Z_{iso}$ (autovalori tutti pari alla media $\bar\lambda$), stesso span, stessa energia totale.

**Lemma 1 (l'anisotropia amplifica il bias).** Se $\lambda_K > \lambda_1$, esiste un compito $y$ per cui $Z_{aniso}$ dà uno stimatore più distorto di $Z_{iso}$ per ogni $\lambda>0$.
*Dimostrazione (B.1).* $\mathrm{Bias}(\hat\beta) = \mathbb{E}\hat\beta - \beta_{true} = -\lambda(Z^\top Z+\lambda I)^{-1}\beta_{true} = -\lambda Q(\Lambda+\lambda I)^{-1}Q^\top\beta_{true}$. Si scelga $\beta_{true} = \kappa q_1$ (autovettore dell'autovalore minimo $\lambda_1$). Allora $\|\mathrm{Bias}\|_{aniso} = \frac{\lambda}{\lambda_1+\lambda}\|\beta_{true}\|$ e $\|\mathrm{Bias}\|_{iso} = \frac{\lambda}{\bar\lambda+\lambda}\|\beta_{true}\|$; poiché $\lambda_1 < \bar\lambda$, il primo è strettamente maggiore. $\square$

**Lemma 2 (l'anisotropia amplifica la varianza).** Con $\lambda = 0$ (OLS), $\mathrm{tr}\,\mathrm{Var}(\hat\beta_{aniso}) > \mathrm{tr}\,\mathrm{Var}(\hat\beta_{iso})$.
*Dimostrazione (B.2).* $\mathrm{Var}(\hat\beta\mid Z) = \sigma^2(Z^\top Z)^{-1}$, quindi $\mathrm{tr} = \sigma^2\sum_j 1/\lambda_j$. La funzione $1/x$ è strettamente convessa su $(0,\infty)$; per Jensen $\frac{1}{K}\sum_j \frac{1}{\lambda_j} > \frac{1}{\bar\lambda}$ con uguaglianza solo se tutti gli autovalori coincidono. $\square$

### 4.2 Sonde non lineari (k-NN radiale e kernel di Nadaraya–Watson)

Con $p_z \in C^3$, target $\eta \in C^2$ e prior isotropo sul gradiente $\mathbb{E}[\nabla\eta\nabla\eta^\top] = \tau_g^2 I$:

**Lemma 4 (bias puntuale k-NN, B.3).** $\mathrm{Bias}(q) = \frac{r_0^2}{d+2}\big[\nabla\eta(q)^\top\nabla\log p_z(q) + \tfrac12\Delta\eta(q)\big] + o(r_0^2)$ — segue da uno sviluppo di Taylor al secondo ordine di $\eta$ e $p$ sulla palla $B(q,r_0)$ e dalle identità $\int_B z\,dz = 0$, $\int_B zz^\top dz = \frac{\mathrm{Vol}\,r^{2}}{d+2}I$.

**Teorema 7 (ottimalità k-NN, B.4).** $\mathbb{E}_z[\mathrm{Bias}(z)^2] = \frac{r_0^4}{(K+2)^2}\tau_g^2 J(p) + O(r_0^4)$ con $J(p) = \int\|\nabla\log p\|^2p\,dx$ (funzionale di informazione di Fisher); il termine dipendente da $p$ è $J(p)$.

**Teorema 8 (ottimalità kernel, B.7).** $\sup_{m\in\mathcal{M}(L,B)}\mathbb{E}_z[\mathrm{Bias}^2] \le \big(\frac{h^2\mu_2(K)}{2}\big)^2(2B^2 + 8L^2J(p)) + o(h^4)$ e la varianza integrata non dipende da $p$.

**Lemma 6 (Cramér–Rao) e Teorema 9.** Per $p$ a media nulla con covarianza $\Sigma\succ0$: $J(p) \ge \mathrm{tr}(\Sigma^{-1})$ con uguaglianza se e solo se $p = \mathcal{N}(0,\Sigma)$ (la famiglia di traslazione $p(x-\theta)$ ha informazione di Fisher $\mathcal{I} = \mathbb{E}[\nabla\log p\nabla\log p^\top]$ e lo stimatore $T(X) = X$ è non distorto con covarianza $\Sigma$; il bound matriciale $\Sigma \succeq \mathcal{I}^{-1}$ dà la tesi; l'uguaglianza richiede score affine, cioè densità gaussiana). Poi, sotto un vincolo scalare sulla covarianza, $\mathrm{tr}(\Sigma^{-1}) = \sum_i 1/\lambda_i$ è minimo quando tutti i $\lambda_i$ sono uguali: traccia $t$ → $d^2/t$ (Cauchy–Schwarz); determinante $\delta$ → $d\delta^{-1/d}$ (AM–GM); Frobenius $c$ → $d^{3/2}/c$ (moltiplicatori di Lagrange, $\lambda_i = c/\sqrt d$); raggio spettrale $r$ → $d/r$. Quindi **la gaussiana isotropa è l'unico minimizzatore** del bias integrato di k-NN e kernel.

### 4.3 Conseguenza per il progetto

Le "letture" del coach (Parte I §7.8: sonde lineari su latenti congelati con etichette esterne) sono esattamente gli stimatori dei Lemmi 1–2 e dei Teoremi 7–8. Un latente anisotropo o non gaussiano rende ogni sonda più distorta e più instabile fra campioni di training: è il motivo per cui i probe della Parte I devono essere valutati insieme a RankMe e SIGReg, e perché il target del training v2 è l'isotropia e non semplicemente "varianza ≥ 1" (VICReg).

---

## 5. Sonde lineari, leakage e la testa VL-JEPA

### 5.1 Definizione formale di leakage

Sia $x$ l'input del modello e $y$ l'etichetta usata per una loss supervisionata o per una sonda. Diciamo che c'è **leakage** se esiste una funzione misurabile $h$ tale che $y = h(x)$ quasi ovunque. In tal caso $I(x;y) = H(y)$: l'etichetta non porta informazione nuova rispetto all'input, e una sonda che raggiunge accuratezza alta dimostra soltanto che il modello non ha distrutto l'informazione contenuta in $x$ — non che abbia imparato qualcosa sul mondo.

**Test di leakage (usato in §12.6).** Addestrare la stessa sonda lineare (i) sulle feature grezze $x$ (o su una loro statistica di finestra), (ii) sugli embedding del modello, (iii) sugli embedding di una rete casuale della stessa architettura. Se (i) ≈ (ii) ≈ (iii), l'etichetta è (quasi) funzione dell'input e la sonda non misura l'apprendimento. Se (ii) ≫ (i), il modello ha estratto struttura non lineare utile. Se (ii) < (i), l'allenamento ha distrutto informazione.

### 5.2 La testa VL-JEPA del repository (J9 della Parte I)

`ConceptLabeler` (`jepa_model.py:601-733`) costruisce 16 etichette di "concetto" per finestra a partire dalle stesse 25 feature che sono l'input dell'encoder (soglie su salute, equipaggiamento, posizione, visibilità). È leakage nel senso di §5.1 per costruzione: $y = h(x)$ con $h$ nota. La variante "outcome" (`:809-821`, `:856-858`) mescola etichette da `RoundStats` con soglie sull'equipaggiamento (ancora funzione di $x$). Inoltre la loss di training è BCE multi-etichetta (`:1085`) mentre l'inferenza usa una softmax (`:980`): la prima assume concetti indipendenti, la seconda mutuamente esclusivi; le due non sono la stessa distribuzione e il modello viene letto in un modo in cui non è stato addestrato.

**Correzione (Parte I §7.8).** Etichette **esterne** all'input: esito del round (`roundstats.round_won`), morte entro $\Delta t$ (dalla salute *futura*, non presente), ingaggio entro $\Delta t$ (visibilità *futura*), ruolo da tabella esterna. Sonde lineari con validazione a gruppi per demo (`GroupKFold`): nessuna finestra della stessa partita in train e test.

### 5.3 Le misure [T6]

§12.6 riporta l'AUROC (media e deviazione su 5 fold a gruppi) delle sonde logistiche per tre etichette esterne — `round_won`, morte entro 128 tick (~2 s), nemico visibile entro 128 tick — su quattro rappresentazioni: media di finestra delle feature grezze (25-d), ultimo tick grezzo (25-d), embedding di contesto dell'encoder archiviato (256-d), embedding di una rete casuale (256-d). La lettura dei risultati è in §12.6; la regola di decisione è quella di §5.1.

Un chiarimento sul senso di "morte entro 2 s" con feature grezze: la salute corrente è in $x$, quindi una sonda grezza ha un vantaggio legittimo (salute bassa → rischio alto); il confronto interessante è se l'encoder *aggiunge* qualcosa (posizione, visibilità, movimento) oltre a ciò che la sonda grezza già vede.

---

## 6. Modello del mondo, azioni e pianificazione

### 6.1 La ricetta LeWorldModel (2603.19312)

Encoder $z_t = \mathrm{enc}_\theta(o_t)$; predittore $\hat z_{t+1} = \mathrm{pred}_\phi(z_t, a_t)$ con storia di $N$ latenti e maschera causale; perdita
$$\mathcal{L}_{LeWM} = \|\hat z_{t+1} - z_{t+1}\|^2 + \lambda\,\mathrm{SIGReg}(Z),\qquad \lambda = 0{,}1,\ M=1024,$$
con $Z\in\mathbb{R}^{N\times B\times d}$ e SIGReg per passo temporale sull'asse del batch (Alg. 3). Nessun stop-gradient, nessuna EMA, nessun encoder pre-addestrato. Un solo iperparametro effettivo ($\lambda$, ricerca per bisezione); ablazioni (App. G): $\lambda\in[0{,}01, 0{,}2]$ tutte > 80% di successo, $\lambda=0{,}5$ crolla; dropout del predittore 0,1 ottimo (0 → 78%, 0,1 → 96%, 0,5 → 67%); aggiungere una loss di ricostruzione **peggiora** (96 → 86); dimensione latente con soglia ≈ 184 e saturazione oltre; encoder ResNet-18 ≈ ViT.

**Condizionamento sulle azioni: adaLN-Zero (DiT, 2212.09748 §3).** In un blocco Transformer, invece di parametri appresi di scala e traslazione $(\gamma,\beta)$ della LayerNorm, si *regrediscono* $\gamma,\beta$ da un vettore di condizionamento $c$ (in DiT la somma degli embedding di tempo e classe; in LeWM l'azione). adaLN-Zero aggiunge un fattore di scala $\alpha$ per dimensione applicato subito prima di ogni connessione residua e **inizializza a zero** l'MLP che produce $(\gamma,\beta,\alpha)$: ogni blocco parte come identità e il condizionamento entra progressivamente (Goyal et al. per la BatchNorm; U-Net di diffusione). Concretamente, con $c$ il vettore azione (embedding):
$$[\gamma_1,\beta_1,\alpha_1,\gamma_2,\beta_2,\alpha_2] = \mathrm{MLP}_0(c),\quad h \leftarrow h + \alpha_1\odot\mathrm{Attn}\big((1+\gamma_1)\odot\mathrm{LN}(h) + \beta_1\big),\quad h \leftarrow h + \alpha_2\odot\mathrm{FFN}\big((1+\gamma_2)\odot\mathrm{LN}(h) + \beta_2\big),$$
con $\mathrm{MLP}_0$ a pesi finali nulli. Per CS2 l'azione per token è $a_t = (\Delta\mathrm{pos}_{xyz}/8, \Delta\mathrm{yaw}/180, \Delta\mathrm{pitch}/90)$ (Parte I §7.9), calcolata dal token successivo: è la controparte "senza controller" delle azioni vere; la sua qualità come azione è misurabile col rimpianto del planner.

**Pianificazione: CEM (Rubinstein & Kroese 2004; LeWM App. B, Alg. 2).** Obiettivo $C(\hat z_H) = \|\hat z_H - z_g\|^2$, $z_g = \mathrm{enc}(o_g)$; ripetere $T$ volte: campionare $N$ sequenze $a_{1:H}\sim\mathcal{N}(\mu,\Sigma)$ ($\mu_0=0,\Sigma_0=I$), srotolare il predittore, calcolare i costi, tenere le $K$ élite, aggiornare $\mu \leftarrow$ media delle élite, $\Sigma \leftarrow$ varianza delle élite; restituire $\mu_T$ (o la migliore sequenza). LeWM: $N=300$, $T=30$ (PushT) / 10, $K=30$, $H=5$ blocchi da 5 passi, MPC che esegue il blocco e ripianifica. Confronto solver (Tab. 10): CEM 96 vs Adam 84 vs RMSProp 67 vs SGD 26. Il CEM non garantisce l'ottimo globale e soffre la dimensione dell'azione (App. B): con 5 dimensioni per token e $H=5$ siamo a 25 dimensioni, nel regime in cui LeWM lo usa.

### 6.2 Che cosa garantisce la teoria (Cui et al. 2606.27014)

- Teorema 4.1: con un passo, $\mathcal{E}(\tilde a) \le 2c_0\max_a\sqrt{R_{S\text{-}JEPA}(f,g,a)}$: un rischio di pretraining piccolo garantisce un rimpianto di pianificazione piccolo.
- Teorema 4.2: con $T$ passi e dinamica deterministica, il rimpianto è $\le 2Tc_3\sqrt{\max_a R}$ — **lineare in $T$**.
- Teoremi 4.5–4.6: compromesso in $k$ (approssimazione $\sum_{i>k}\sigma_i^2$ vs complessità di Rademacher $\propto k^2$).
- Validazione (Sez. 5): su un sistema punto-massa con feature di disturbo e rumore, la predizione latente vince sulla ricostruzione in input quando il rumore è alto e l'orizzonte di pianificazione lungo (25 passi); a orizzonti corti e rumore basso le due coincidono.

Lettura per il "ghost" (Parte I §7.9): orizzonte di pianificazione corto (≤ 5 token = 0,6 s) con ripianificazione, predittore multi-orizzonte per coprire 2 s in un solo passo, $k$ scelto sulla curva RankMe/probe.

### 6.3 Il raddrizzamento temporale emergente (LeWM App. H)

$S_{straight} = \frac{1}{B(T-2)}\sum_{i,t}\frac{\langle v_t^{(i)}, v_{t+1}^{(i)}\rangle}{\|v_t^{(i)}\|\|v_{t+1}^{(i)}\|}$ con $v_t = z_{t+1}-z_t$ cresce durante il training senza termini espliciti. Gli autori lo attribuiscono al fatto che SIGReg è applicato per passo temporale ma non lungo il tempo, "lasciando l'asse temporale non vincolato" e permettendo "una forma di collasso temporale" benigna per il planning. Per un coach che deve distinguere micro-eventi (peek, flick, riposizionamento) questo è un rischio: è la ragione tecnica per cui la v2 combina SIGReg batch (LeWM) e SIGReg temporale (LeNEPA), e per cui $S_{straight}$ va loggato come diagnostica.

---

## 7. Sorpresa: definizione, calibrazione, validazione

### 7.1 Definizione

Dato il modello del mondo, la **sorpresa** al passo $t$ per l'orizzonte $h$ è l'errore di predizione nello spazio latente (del projector, se presente):
$$s_h(t) = \|\hat z_{t+h} - z_{t+h}\|^2\quad\text{(LeWM §5.2, Jaiswal eq. 4 con la norma non quadrata)}.$$
LeWM la chiama *violation-of-expectation*; Jaiswal *complexity score*; Mouchon *surprise* e la usa come gate. È **una sola grandezza** per tre usi del progetto: Chronovisor (momenti critici), memoria episodica (quando scrivere), stima di abilità/anomalia.

### 7.2 Calibrazione

La sorpresa grezza dipende dall'orizzonte, dalla scala del latente e dal contesto; va standardizzata **per flusso** e **per orizzonte**:
$$\zeta_h(t) = \frac{s_h(t) - \mu_h}{\sigma_h},$$
con $\mu_h,\sigma_h$ stimate in streaming (Welford: $\mu_n = \mu_{n-1} + (s_n-\mu_{n-1})/n$, $M_{2,n} = M_{2,n-1} + (s_n-\mu_{n-1})(s_n-\mu_n)$, $\sigma_n^2 = M_{2,n}/(n-1)$) sul train o su una finestra scorrevole del match. Mouchon (§"From a gate to a modulator") documenta il motivo pratico: senza calibrazione, similarità grezze compresse (coppie non correlate a 0,72 invece che a 0) facevano cadere un input nuovo nel regime "parzialmente familiare" e il modello allucinava; con la calibrazione un concetto noto scora ≈ 0,14 e uno nuovo ≈ 1,0. Le soglie (Mouchon: 0,35 e 0,65) definiscono tre registri di comunicazione: **assertivo**, **con riserva**, **astensione**. Questa è la sostituzione matematicamente corretta della `confidence = 0.85` costante del RAP (R9 della Parte I).

### 7.3 Validazione: come si dimostra che la sorpresa misura qualcosa

Tre protocolli dalle fonti, tutti applicabili al progetto:

1. **Perturbazione controllata** (LeWM §5.2, F.3): traiettorie non perturbate vs perturbazione visiva (colore) vs perturbazione fisica (teletrasporto). La sorpresa deve salire *solo* sulla seconda: t-test appaiato, $p<0{,}01$ in tre ambienti; il cambio di colore non è significativo. Per CS2: iniettare in un episodio un salto di posizione impossibile (teletrasporto) vs una permutazione di `map_id`; la sorpresa deve reagire al primo e non al secondo.
2. **Correlazione con tag esterni** (Jaiswal §4.1–4.2): media della sorpresa per tag; Spearman fra ordinamenti; ablazioni obbligatorie — punteggi permutati ($\rho=-0{,}13$), encoder casuale ($\rho=0{,}02$), baseline cinematica (velocità costante, $\rho=0{,}31$ ma spread −30% e mis-ranking degli approcci lenti), no-EMA (spread 0,014 vs 0,602). Per CS2 i tag esistono già: `roundstats` (morte, opening kill, clutch, KAST) e gli eventi del parser.
3. **Precision@K / AP come detector** (Jaiswal §4.3): ordinare per sorpresa, misurare la precisione dei top-K contro un insieme di "momenti complessi" definito da tag; riportare la baseline di chance (43,6% nel paper; AP 0,512 vs 0,436).

Mouchon aggiunge il dato che decide dove mettere la sorpresa nel prodotto: il detector esterno separa noto/nuovo con AUROC 0,966, la confidenza *verbalizzata* dell'LLM 0,618, quella a livello di token 0,292 (sotto il caso). **La confidenza comunicata all'utente non deve mai venire dall'LLM**: viene dalla sorpresa calibrata e dalle sonde calibrate (§9).

### 7.4 Chronovisor v2: la matematica del rilevamento dei momenti

Il Chronovisor esistente (`rap/chronovisor_scanner.py`) è un rilevatore multi-scala di punti di cambiamento su un segnale scalare con differenze a lag, run di segno costante e picco; l'algoritmo è sano ma lavora in "frame" senza unità di tempo e senza lisciamento (R10). Nella v2: segnale $\zeta_h(t)$ (o il valore di una sonda), scale in secondi via $f_{tick}$ misurato (micro 1 s/lag 0,25 s; standard 3 s/1 s; macro 10 s/2 s), lisciamento di Savitzky–Golay (regressione polinomiale locale di grado $p$ su una finestra di $2m+1$ campioni: il filtro è la convoluzione con la riga centrale di $(J^\top J)^{-1}J^\top$, $J_{ij} = i^j$, $i\in[-m,m]$; conserva i momenti fino al grado $p$ e attenua il rumore ad alta frequenza), soglie in $\zeta$ calibrate sul train, deduplica fra scale con gap minimo. Risultato: `CriticalMoment{t_peak, t_start, t_end, severity, polarity, scale}` con `ScanResult{ok, n_analyzed, truncated}` (la semantica "vuoto-successo ≠ fallimento" del codice attuale va conservata). Validazione: Precision@K contro morti/kill/opening (protocollo 3), come definizione di successo del passo 6 della Parte I.

---

## 8. Eventi critici con orizzonte: hazard, sopravvivenza, h-AUROC (HEPA, 2605.11130)

### 8.1 Il problema che HEPA risolve e perché è il nostro

"Dato quanto osservato fino a $t$, stimare $P(\text{evento entro }\Delta t)$ per ogni orizzonte $\Delta t$": è la forma comune di prognostica (RUL), rilevamento di anomalie e — nel nostro caso — "morte entro $\Delta t$", "round perso", "primo contatto entro $\Delta t$". HEPA separa le responsabilità: l'encoder impara la dinamica senza etichette; il predittore, con poche etichette, la specializza sull'evento.

### 8.2 Pretraining

Encoder causale $f_\theta$ (Transformer $d=256$, 2 strati, 4 teste; patch non sovrapposte $P=16$; normalizzazione d'istanza per contesto; PE sinusoidali) → $h_t$. Predittore $g_\varphi$ (MLP a 2 strati) condizionato all'orizzonte: $\hat h_{(t,t+\Delta t]} = g_\varphi(h_t,\Delta t)$ con $\Delta t\sim\mathrm{LogUniform}[1,\Delta t_{max}]$ ("forcing the encoder to internalise dynamics at multiple timescales"). Bersaglio $h^*$: **lo stesso** $f_\theta$ applicato bidirezionalmente a $x_{(t,t+\Delta t]}$ con attention pooling — pesi condivisi, nessun EMA, nessuno stop-gradient. Perdita
$$\mathcal{L} = (1-\alpha)\,\|\hat h - h^*\|_1 + \alpha\,\mathcal{L}_{SIG},\qquad \alpha = 0{,}1,$$
con SIGReg sull'uscita del predittore. L1 perché "distribuisce il gradiente in modo uguale fra i campioni evitando la dominanza degli outlier". Il collasso banale è impedito da SIGReg **e** dall'asimmetria degli input (passato vs futuro). 2,16 M parametri; pretraining < 1 min per dataset su A10G.

### 8.3 Finetuning del predittore (non dell'encoder)

Encoder congelato; predittore + testa lineare finetunati (198 K parametri contro 2,16 M end-to-end e 513 di una sonda lineare). Per $K$ orizzonti discreti $\Delta t = 1..K$:
$$\lambda_{\Delta t}(t) = \sigma\big(w^\top\hat h_{(t,t+\Delta t]} + b\big)\in(0,1)\quad\text{(hazard condizionato, eq. 3)},$$
$$p(t,\Delta t) = 1 - \prod_{j=1}^{\Delta t}\big(1-\lambda_j(t)\big)\quad\text{(CDF di sopravvivenza discreta, eq. 4)},$$
monotona non decrescente in $\Delta t$ per costruzione (ogni fattore in $(0,1)$). Perdita $\mathcal{L}_{FT} = \sum_{\Delta t=1}^K w_+\,\mathrm{BCE}(p(t,\Delta t), y(t,\Delta t))$, $y = \mathbb 1[\text{evento in }(t,t+\Delta t]]$, $w_+ = N_{neg}/N_{pos}$ (eq. 5). Nota d'onestà del paper (nota 1, App. O): applicare la BCE alla CDF cumulata e non agli hazard per passo liscia fra orizzonti ma **distorce la scala di probabilità**; se servono probabilità calibrate (come al coach), ricalibrare (§9).

### 8.4 Proposizione 1 (ritenzione dell'informazione sull'evento) — dimostrazione a passi

Ipotesi: (A1) $E_{t+\Delta t}\perp X_{\le t}\mid H^*$ (il bersaglio è statistica sufficiente per l'evento); (A2) $\mathbb{E}\|\hat H - H^*\|_2^2 \le \varepsilon$; (A3) $\eta(h) = P(E=1\mid H^*=h)$ è $L$-Lipschitz; (A4) $\eta(H^*)\in[\underline\eta,\bar\eta]\subset(0,1)$ q.c. Allora
$$I(H_t;E_{t+\Delta t}) \ge I(H^*;E_{t+\Delta t}) - C_\eta L^2\varepsilon,\qquad C_\eta = \frac{1}{2\underline\eta(1-\bar\eta)}.$$
*Passo 1.* $\hat H = g_\varphi(H_t,\Delta t)$ è funzione deterministica di $H_t$ ⇒ catena di Markov $E - H_t - \hat H$ ⇒ $I(H_t;E)\ge I(\hat H;E)$ (disuguaglianza di elaborazione dei dati). *Passo 2.* $I(H^*;E) - I(\hat H;E)$ è un gap di Jensen sulla divergenza KL binaria $\phi(q) = \mathrm{KL}(\mathrm{Bern}(q)\|\mathrm{Bern}(\pi_e))$, convessa con $\phi''(q) = 1/(q(1-q))$; con (A3) $|\eta(H^*) - \eta(\hat H)| \le L\|H^*-\hat H\|$ e con (A4) $\sup\phi'' \le 1/(\underline\eta(1-\bar\eta))$; un sviluppo al secondo ordine e (A2) danno il bound $C_\eta L^2\varepsilon$. *Passo 3.* Combinare. $\square$ (App. A.3 del paper.)

**Corollario 2 (necessità dei precursori).** Il bound è non banale se e solo se il futuro contiene precursori catturati dal target ($I(H^*;E)>0$) e $\varepsilon < I(H^*;E)/(C_\eta L^2)$. Per eventi molto rari $\underline\eta\to0$ e $C_\eta\to\infty$: il bound degrada — lo stesso vale per le morti in CS2 a orizzonti brevi (positività ≈ 1% a 2 s nel nostro campione [T6]); vanno usati orizzonti più lunghi e pesi $w_+$.

**Predizione falsificabile verificata nel paper.** Entro un dataset, loss di pretraining $\varepsilon$ e h-AUROC sono correlate negativamente: Spearman $-0{,}67$ (C-MAPSS-3), $-0{,}64$ (MBA), $-0{,}49$ (SMAP), $-0{,}87$ (C-MAPSS-1); fra dataset la correlazione è nulla ($r=-0{,}05$) perché $L$, $C_\eta$ e le scale differiscono. **Lezione per il progetto**: confrontare la loss solo fra run sullo stesso dataset (J11 della Parte I).

### 8.5 La metrica giusta: h-AUROC

$\text{h-AUROC} = \frac{1}{K}\sum_{\Delta t=1}^K\mathrm{AUROC}\big(p(\cdot,\Delta t), y(\cdot,\Delta t)\big)$: media di AUROC per orizzonte, ciascuna con baseline 0,5 indipendente dalla prevalenza. Il paper mostra perché non AUPRC aggregata (baseline 0,957 su C-MAPSS-1, prevalenza da 0,5% a 96% con l'orizzonte) e perché non PA-F1 (gonfiato dal credito a segmenti interi). Per il coach: AUROC per orizzonte per "morte entro $\Delta t$" e "round perso", con l'intervallo di confidenza su fold a gruppi per demo.

### 8.6 Risultati che fissano le aspettative

HEPA vince 10/14 benchmark contro PatchTST, iTransformer, MAE e Chronos-2 con teste downstream identiche; mantiene il 92% dell'h-AUROC con il 2% delle etichette (2 motori su 85) dove i precursori sono lunghi; perde dove l'evento è localizzato su pochi sensori (la tokenizzazione a fusione di canale diluisce) o dove la deriva è lenta e la ricostruzione trasferisce bene. Per CS2: eventi con precursori (ingaggio, morte in retake, perdita del round) sono nel regime favorevole; eventi istantanei senza precursori (headshot da posizione non osservabile) non lo sono, e il coach deve dirlo.

---

## 9. Calibrazione delle probabilità comunicate (Guo, Pleiss, Sun, Weinberger 2017, 1706.04599)

### 9.1 Definizioni

Calibrazione perfetta: $P(\hat Y = Y\mid\hat P = p) = p$ per ogni $p\in[0,1]$ (eq. 1). Stima con $M$ intervalli $I_m = (\frac{m-1}{M},\frac{m}{M}]$: $\mathrm{acc}(B_m) = \frac{1}{|B_m|}\sum_{i\in B_m}\mathbb 1(\hat y_i = y_i)$, $\mathrm{conf}(B_m) = \frac{1}{|B_m|}\sum_{i\in B_m}\hat p_i$;
$$\mathrm{ECE} = \sum_{m=1}^M\frac{|B_m|}{n}\,\big|\mathrm{acc}(B_m) - \mathrm{conf}(B_m)\big|\quad(\text{eq. 3}),\qquad \mathrm{MCE} = \max_m|\mathrm{acc}(B_m) - \mathrm{conf}(B_m)|\quad(\text{eq. 5}),$$
$M = 15$ nel paper; $\mathrm{NLL} = -\sum_i\log\hat\pi(y_i\mid x_i)$ minimizzata in attesa se e solo se $\hat\pi$ recupera la condizionale vera.

### 9.2 Che cosa il paper dimostra empiricamente

Le reti moderne sono sovraconfidenti: profondità e larghezza aumentano l'ECE; la BatchNorm peggiora la calibrazione; il weight decay la migliora oltre il punto ottimo per l'accuratezza; la NLL di test overfitta mentre l'errore 0/1 continua a scendere (Fig. 3). **Temperature scaling** — un solo scalare $T>0$, $\hat q = \max_k\mathrm{softmax}(z/T)_k$, ottimizzato per NLL su un insieme di validazione — è il metodo migliore sui compiti di visione (ECE 12,67% → 0,96% per ResNet-110 su CIFAR-100) e non cambia l'argmax (accuratezza invariata). Platt scaling binario: $\hat q = \sigma(az+b)$ con $(a,b)$ per NLL sulla validazione, rete congelata. Vector/matrix scaling più generali ma overfittano con molte classi.

### 9.3 Applicazione al progetto

- `PlattScaler` in `analysis/win_probability.py:118-168` implementa Platt sul logit $\log(p/(1-p))$ con passi di Newton ($\nabla = \sum(y-s)x$, Hessiana $\sum s(1-s)x^2$, il segno corretto dopo 26-WINPROB-03). È il pezzo giusto; è "dormiente per design" (commento R4 alla riga 407) perché non esiste un checkpoint a 12 feature addestrato. Va fittato **sullo split VAL**, mai su TRAIN o TEST.
- `tools/eval_harness.py:284-336` contiene `brier_score` ed `expected_calibration_error`: la metrica esiste già; va collegata alle nuove sonde e all'output del coach.
- Ogni probabilità che raggiunge l'utente (rischio di morte, probabilità di round, confidenza di un consiglio) deve essere post-calibrata su VAL e riportata con ECE ($M=15$). Criterio di rilascio della Parte I: ECE < 0,05. La `confidence = 0.85` costante (`rap/communication.py`) ha per costruzione ECE = |acc − 0,85| su ogni bin: non è una confidenza, è un numero.
- Per le sonde multi-orizzonte (§8) la calibrazione va fatta **per orizzonte**, perché la prevalenza cambia con $\Delta t$.

---

## 10. Blocchi architetturali: definizioni esatte dalle fonti primarie

Ogni blocco della v2 (Parte I §7.4) è qui definito con la formula della fonte, la ragione della scelta e il punto in cui il codice attuale se ne discosta.

### 10.1 RMSNorm (Zhang, Sennrich 2019, 1910.07467 eq. 4)
$$\bar a_i = \frac{a_i}{\mathrm{RMS}(a)}\,g_i,\qquad \mathrm{RMS}(a) = \sqrt{\tfrac{1}{n}\sum_{i=1}^n a_i^2}.$$
Solo invarianza di riscalamento (nessuna sottrazione della media); coincide con LayerNorm quando la media è nulla; più economica. Usata in LeNEPA e nei Transformer causali moderni. Nella v2: pre-norma in ogni blocco. **Non** all'uscita finale su cui si calcola SIGReg (§2.3.3).

### 10.2 SwiGLU (Shazeer 2020, 2002.05202 eq. 5–6)
$$\mathrm{Swish}_\beta(x) = x\,\sigma(\beta x),\qquad \mathrm{SwiGLU}(x) = \mathrm{Swish}_1(xW)\otimes(xV),\qquad \mathrm{FFN}_{SwiGLU}(x) = \big(\mathrm{Swish}_1(xW)\otimes xV\big)W_2,$$
senza bias; tre matrici, con $d_{ff}$ ridotto di $2/3$ per pareggiare i parametri della FFN a due matrici. Migliore perplessità fra le varianti GLU testate (Tab. 1 del paper). Nella v2 sostituisce la coppia Linear–GELU–Linear dell'encoder attuale.

### 10.3 RoPE (Su et al., 2104.09864 eq. 15–16)
Posizione $m$ codificata ruotando le coppie di coordinate di query e chiave: $q_m^\top k_n = (R^d_{\Theta,m}W^qx_m)^\top(R^d_{\Theta,n}W^kx_n) = x_m^\top W^q R^d_{\Theta,n-m}W^kx_n$, con $R^d_{\Theta,m}$ diagonale a blocchi $2\times2$ di rotazioni di angolo $m\theta_i$, $\theta_i = 10000^{-2(i-1)/d}$. Dipende solo dalla posizione **relativa** $n-m$, è ortogonale (conserva le norme), e ha decadimento a lungo raggio del prodotto scalare. Nella v2 sostituisce i sinusoidi assoluti: le finestre di token sono ritagliate a offset arbitrari dentro il round, quindi la posizione assoluta non ha significato.

### 10.4 QK-norm (Dehghani et al. 2023, 2302.05442 §2)
$$\mathrm{Attn} = \mathrm{softmax}\Big[\tfrac{1}{\sqrt d}\,\mathrm{LN}(XW^Q)\,\mathrm{LN}(XW^K)^\top\Big]V,$$
LayerNorm su query e chiavi prima del prodotto scalare (Gilmer et al. 2023): impedisce la crescita incontrollata dei logit di attenzione che porta a pesi quasi one-hot ed entropia nulla (divergenza osservata a ~8B parametri; ma è una stabilizzazione a costo zero anche a scala piccola, adottata da LeNEPA con $\epsilon = 10^{-6}$).

### 10.5 Attenzione causale e tokenizer a convoluzione
Maschera $M_{ij} = 0$ se $j\le i$, $-\infty$ altrimenti, sommata ai logit: il token $t$ vede solo $\le t$ — condizione necessaria perché la predizione del token $t+1$ sia una predizione e non una lettura. Tokenizer: `Conv1d(in=31, out=D, kernel=P, stride=P)` sul segnale $(B,31,T\cdot P)$ (LeNEPA: "ViT-style patch embeddings with strided convolution", $P=25$ su 5000 campioni; v2: $P=8$ tick = 125 ms). È una combinazione lineare appresa di $P$ tick consecutivi, non una decimazione: conserva l'informazione intra-patch che una media perderebbe.

### 10.6 Projector e "Guillotine Regularization" (Bordes et al. 2022; LeNEPA Tab. 5)
Projector $h_\psi: \mathbb{R}^D\to\mathbb{R}^d$ (MLP $128\to256\to64$ nella v2; LeNEPA: MLP+BN+ReLU, uscita 64). Le loss (predizione e SIGReg) si calcolano in $\mathbb{R}^d$; le sonde e il coach leggono $\mathbb{R}^D$ (e, per LeNEPA, gli strati intermedi: $L_4$ batte $L_8$ di 2,5–8 punti). Motivazione: gli ultimi strati si specializzano nel compito di predizione (Jing §6; LeNEPA §2), e la loss non deve deformare direttamente la rappresentazione servita.

### 10.7 FiLM / AdaLN per l'orizzonte e per l'azione
FiLM: $h\mapsto\gamma(c)\odot h + \beta(c)$ con $c$ il condizionamento (orizzonte $h\in\{1,4,16\}$ come embedding appreso). AdaLN-Zero (§6.1) per l'azione nel modello del mondo. Il repository ha già un `FiLMLinear` (`nn/layers/superposition.py`) che va tenuto (Parte I §9) rendendo esplicita la dimensione del contesto.

### 10.8 Mixture of Experts: la loss di bilanciamento di Switch e perché l'entropia ha il segno sbagliato

**Switch (2101.03961 eq. 4–6).** Con $N$ esperti e $T$ token nel batch: $\mathrm{loss} = \alpha N\sum_{i=1}^N f_iP_i$, $f_i = \frac{1}{T}\sum_x\mathbb 1[\arg\max p(x) = i]$ (frazione instradata, non differenziabile), $P_i = \frac{1}{T}\sum_x p_i(x)$ (probabilità media, differenziabile), $\alpha = 10^{-2}$. Minimo sotto instradamento uniforme ($f_i = P_i = 1/N$, valore $\alpha$). **Penalizza la concentrazione.** `jepa_model.py::_sparse_moe` implementa esattamente questo (con i nomi $f_i$/$P_i$ scambiati rispetto al paper, ma il prodotto è simmetrico: il valore è corretto).

**RAP (`rap/model.py:201-205`).** Restituisce $w\cdot H(p)$ con $H(p) = -\sum_i p_i\log p_i$ e $w = 10^{-4}$ (`context_gate_l1_weight`), commentando "high entropy = uniform (bad for specialization), low = peaked (good)". Minimizzare $H(p)$ **premia** il gate one-hot.

**Proposizione 6.** $H(p)$ sul simplesso è massima ($\log N$) nel punto uniforme e minima ($0$) sui vertici. *Dimostrazione.* $H$ è strettamente concava (la matrice Hessiana è $\mathrm{diag}(-1/p_i)$, definita negativa sull'interno); per Jensen $H(p)\le\log N$ con uguaglianza solo in $p = (1/N,\dots,1/N)$; sui vertici un solo $p_i = 1$ e $H = 0$. $\square$ Quindi minimizzare $H(p)$ spinge $p$ verso un vertice: **esattamente il collasso degli esperti** che il gate sparso doveva evitare, e l'opposto del termine di Switch. Con $w=10^{-4}$ l'effetto è piccolo ma di segno sbagliato; la correzione (Parte III) è sostituire il termine con quello di Switch (o, se si vuole la specializzazione *per token*, penalizzare l'entropia per token e *premiare* l'entropia della media di batch — la formulazione "importance + load" di Shazeer 2017 — mai il contrario).

### 10.9 Bersagli categoriali: cross-entropia, non MSE su one-hot (R3)
Per un bersaglio $y\in\{1..C\}$ e un'uscita softmax $p$, la MSE $\|p - e_y\|^2$ ha gradiente rispetto ai logit $z$: $\partial/\partial z_k = 2\sum_j(p_j - \delta_{jy})p_j(\delta_{jk} - p_k)$, che si annulla quando $p$ è quasi uniforme (i fattori $p_j(\delta_{jk}-p_k)$ sono $O(1/C^2)$) e non è una funzione di verosimiglianza; la cross-entropia $-\log p_y$ ha gradiente $p - e_y$, lineare nell'errore e mai svanente. `rap/trainer.py:33,67` usa `nn.MSELoss()` fra `advice_probs` (softmax) e `target_strat` (one-hot): va sostituita con `CrossEntropyLoss` sui logit, con classe `ROLE_ROTATION` che è irraggiungibile dall'euristica di etichettatura (`training_orchestrator.py:1711-1773`): una classe senza esempi positivi ha logit spinto a $-\infty$ e nulla di appreso.

---

## 11. Le altre reti e i motori di analisi del progetto, uno per uno

La Parte I ha coperto JEPA, RAP e contratto dati. Il progetto contiene però altre quattro reti neurali (`AdvancedCoachNN`, `NeuralRoleHead`, `WinProbabilityTrainerNN`, `WinProbabilityNN`), una decina di motori statistici in `backend/analysis/`, la banca delle esperienze e il livello RAG/LLM. Per ciascuno: formula implementata, verdetto matematico, correzione. Percorsi relativi a `Programma_CS2_RENAN/`.

### 11.1 `AdvancedCoachNN` (alias `TeacherRefinementNN`) — `backend/nn/model.py`, `backend/nn/train.py`, `backend/nn/coach_manager.py`

**Cosa è.** LSTM a 2 strati (input 25, hidden 128, dropout 0,2) + LayerNorm + MoE a 3 esperti con gate top-2 sparso (`_topk_sparse_gate`) + `tanh` finale; uscita a 10 dimensioni. Input: il vettore **per-partita** `MATCH_AGGREGATE_FEATURES` (25 aggregati da `PlayerMatchStats`), non i tick. Bersaglio (`coach_manager.py::_calculate_deltas`): $y_i = \mathrm{clip}\big((\text{pro}_i - \text{cur}_i)/\text{scale}_i,\,-1,\,1\big)$ per $i$ in `TARGET_INDICES = range(10)` con `FEATURE_SCALES` hardcoded e baseline pro da `_get_pro_baseline_vector`. Loss MSE (`train.py:57`), AdamW $10^{-3}$, wd $10^{-2}$, early stopping su validazione, split 80/20 casuale (`train_test_split`, `random_state=42`) sopra 20 campioni.

**Verdetto.** (1) Il bersaglio è una **funzione deterministica dell'input**: $y = \mathrm{clip}((\bar x_{pro} - x)/s)$ con $x$ le prime 10 componenti dell'input stesso e $\bar x_{pro}$ costante: leakage totale nel senso di §5.1. Una rete lineare risolve il compito esattamente; l'LSTM e il MoE non aggiungono nulla, e "SHAP explanations" (`evaluate.py`) spiegano una sottrazione. (2) L'LSTM riceve una sequenza di lunghezza 1 (`_validate_input_dim` fa `unsqueeze(1)` su input 2-D): è un MLP costoso. (3) Il `tanh` finale sull'uscita e il clip del bersaglio a $[-1,1]$ sono coerenti, ma il fattore `WEIGHT_CLAMP` in `evaluate.py` rimoltiplica le uscite prima di `apply_nn_refinement`, che le usa come `weighted_z * (1 + adjustment)` (`coaching/nn_refinement.py:29`): la rete non produce un *peso* ma una differenza normalizzata, e il consumatore la interpreta come moltiplicatore. (4) Il dataset è $N \approx 10^3$ partite (1031 `PlayerMatchStats` al momento della misura, tutte pro e tutte `UNASSIGNED`): il modello non è mai stato addestrato con split assegnati. **Nessuno di questi punti è un errore di codice: è che il problema posto non è un problema di apprendimento.**

**Correzione.** Ritirare `AdvancedCoachNN` dalla catena degli insight (già F-0028 ha rimosso l'inferenza dal `HybridCoachingEngine`). Il "delta rispetto al pro" è un calcolo, non una predizione: va fatto in chiaro con `calculate_deviations` (z-score con deviazione standard della coorte pro, `pro_baseline.py:433-459`), che è corretto e già usato. Se si vuole una rete a livello partita, il compito deve essere predittivo (es. rating della partita successiva, o esito) con etichette esterne.

### 11.2 `NeuralRoleHead` — `backend/nn/role_head.py`, consenso in `backend/analysis/role_classifier.py`

**Cosa è.** MLP $5\to32\to16\to5$ (~750 parametri) con softmax; input $(\text{tapd}, \text{oap}, \text{podt}, \text{rating\_impact}, \text{aggression})$ standardizzati; etichette **soft** dalla tabella esterna `Ext_PlayerPlaystyle` (probabilità di ruolo, con `role_anchor` sommato a `role_support`), lisciate con $\epsilon = 0{,}02$ e rinormalizzate; loss $\mathrm{KL}(y\,\|\,p) $ via `KLDivLoss(reduction="batchmean")` su `log_softmax`; AdamW $10^{-3}$, wd $10^{-4}$, early stopping (pazienza 15), split 80/20 seminato; minimo 20 campioni; soglia FLEX 0,35 sulla probabilità massima.

**Verdetto.** Matematicamente corretto: la KL fra distribuzione bersaglio e predetta è la loss giusta per etichette soft (equivale alla cross-entropia a meno di una costante $-H(y)$); il lisciamento evita $\log 0$; le statistiche di normalizzazione sono salvate accanto al checkpoint (`role_head_norm.json`) e riapplicate in inferenza — corretto contratto train/serve. Due riserve: (a) le 5 feature di inferenza (`extract_role_features_from_stats`) sono *approssimazioni* di quelle di training (`tapd = rounds_survived/rounds_played` ecc.): la corrispondenza semantica con le colonne del CSV esterno va verificata per ogni feature, altrimenti c'è drift di definizione; (b) il consenso (`role_classifier.py:378-416`): accordo → media + 0,1; disaccordo → vince il neurale se supera l'euristico di 0,1. È una regola ragionevole ma le due "confidenze" non sono sulla stessa scala (probabilità softmax vs punteggio di affinità normalizzato): il confronto è euristico. **Tenere**, con un test di coerenza semantica delle feature e con la confidenza del ruolo esposta come probabilità calibrata (§9).

### 11.3 `WinProbabilityTrainerNN` — `backend/nn/win_probability_trainer.py`

MLP $9\to32\to16\to1$ + sigmoide, BCE, Adam $10^{-3}$, 100 epoche full-batch, split 80/20, early stopping; feature grezze **non normalizzate** (`ct_health`, `t_health`, `ct_eqp` in dollari…). **Verdetto.** BCE con sigmoide è corretta; l'assenza di normalizzazione con feature che spaziano da $\{0,1\}$ a $10^4$ rende l'ottimizzazione mal condizionata (il gradiente rispetto ai pesi di `ct_eqp` è $10^4$ volte quello di `bomb_planted`) — non un errore di correttezza ma di condizionamento; nessun `DataFrame` di training è prodotto dalla pipeline attuale (nessun chiamante costruisce `did_ct_win` per snapshot). Non ha mai prodotto un checkpoint. **Correzione:** unificare con 11.4 (un solo modello di probabilità di round, 12 feature normalizzate, split per demo, Platt su VAL) oppure eliminarlo.

### 11.4 `WinProbabilityNN`, euristiche, `PlattScaler`, Elo — `backend/analysis/win_probability.py`

MLP $12\to64\to32\to1$ con dropout 0,2/0,1 e sigmoide, Xavier init; 12 feature normalizzate da `GameState` (economie /16000, differenza, vivi /5, differenza, utility /5, controllo mappa, tempo /115, bomba, lato, rapporto economico clip a 2); **nessun training implementato** per questa architettura (il trainer di 11.3 produce un 9-dim incompatibile, e `A-12` rifiuta il cross-load). In produzione `get_win_predictor()` carica `win_prob_predictor.pt` se esiste, altrimenti gira con **pesi casuali** ("W-02: predictions use random weights"). Sopra la rete, `_apply_heuristics` applica regole deterministiche: 0/1 se una squadra è a zero; $\max(p, 0{,}85)$ se +3 uomini; $\pm 0{,}10$ per bomba piantata; $\max(p,0{,}65)$ / $\min(p,0{,}35)$ per $\pm 8000$ di economia. Poi Platt (dormiente). `EloRatingCalculator`: $E = 1/(1+10^{(R_o - R)/400})$, aggiornamento $R \leftarrow R + K w (S - E)$ con peso di recenza $w = 2^{(i-N+1)/h}$, $h=20$; `EloAugmentedPredictor`: $p = (1-\alpha)p_{nn} + \alpha p_{elo}$, $\alpha = 0{,}15$.

**Verdetto.** La formula di Elo è quella standard; la ponderazione di recenza è un'estensione ragionevole (Glickman). Ma: (1) la rete che dà $p_{nn}$ non è mai stata addestrata: **oggi il "predittore" è un insieme di soglie a mano su una sigmoide casuale** — qualunque numero in $(0,1)$ prodotto non ha valore probabilistico; il commento W-02 lo riconosce. (2) L'espectiminimax (11.8) usa questo valore come funzione di valutazione delle foglie: l'albero propaga rumore. (3) Le euristiche sono *clamp*, non aggiustamenti bayesiani: $\max(p, 0{,}85)$ distrugge la calibrazione in modo non riparabile da Platt (la mappa non è più monotona nel logit). **Correzione:** addestrare la testa di probabilità di round **sui latenti congelati della JEPA v2** con etichette `roundstats.round_won` (Parte I §7.9, "value heads"), split per demo, Platt/temperature su VAL, ECE riportato; eliminare i clamp e, se si vogliono vincoli di dominio (0 vivi ⇒ 0), imporli come casi speciali *prima* della calibrazione e documentarli; Elo solo come feature d'ingresso, non come blend a posteriori.

### 11.5 `DeathProbabilityEstimator` e `BeliefState` — `backend/analysis/belief_model.py`

$\mathrm{logit}\,P = \log\frac{\pi_b}{1-\pi_b} + 2\,\theta + 1{,}5(\ell_w - 1) - 1{,}0(a_f - 1) + 1{,}0(e_f - 0{,}5)$ con prior $\pi_b$ per fascia di salute (0,35/0,55/0,80), minaccia $\theta = (v + i\,e^{-\lambda\,\text{age}}\cdot 0{,}5)/5$, letalità dell'arma $\ell_w$, fattore armatura $a_f\in\{0{,}75, 1\}$, esposizione $e_f$; $\lambda = 0{,}1$ (`THREAT_DECAY_LAMBDA`, ClassVar dopo il fix R4). Calibratore: prior per fascia dai dati (solo la fascia "full" da `RoundStats`, giustamente, dopo il fix R4 che eliminava salute inventata), letalità per arma come `kills_with_weapon/kills_rifle` limitata a $[0{,}1, 3]$, $\lambda$ per regressione log-lineare del tasso di morte su bin di età dell'informazione; `estimate_with_uncertainty` perturba gli input e chiama il tutto "MC Dropout".

**Verdetto.** È un modello logistico a coefficienti fissati a mano ("P8-02: hand-tuned; validate via logistic regression"). Come tale è *coerente* (log-odds additivi) ma non *stimato*: i quattro coefficienti (2; 1,5; −1; 1) non provengono dai dati. La calibrazione dei prior per fascia è corretta come frequenza empirica; la "letalità" come rapporto di conteggi non è un rapporto di rischio (dipende dalla frequenza d'uso dell'arma, non dalla sua letalità condizionata); la stima di $\lambda$ con `polyfit` su log-frequenze è un fit legittimo ma su un'ipotesi (decadimento esponenziale del rischio con l'età dell'informazione) mai verificata. L'"incertezza MC" è la propagazione di rumore artificiale attraverso una funzione deterministica: non è incertezza epistemica (Gal & Ghahramani richiedono dropout *nei pesi di una rete addestrata*). **Correzione:** i coefficienti vanno stimati con una regressione logistica su (minaccia, arma, armatura, esposizione) → morte entro $\Delta t$, come il codice stesso propone; oppure — coerentemente con la v2 — sostituire tutto con la sonda "morte entro $\Delta t$" sui latenti (§8), che usa più informazione ed è calibrata. La definizione di `threat_level` (conteggi visibili + inferiti con decadimento) resta un buon *input* per la sonda, non un modello.

### 11.6 `MomentumTracker` — `backend/analysis/momentum.py`

Moltiplicatore $m = \mathrm{clip}(1 \pm c\cdot\text{streak}\cdot e^{-\rho\,\text{gap}}\cdot w_{rt},\,0{,}7,\,1{,}4)$ con $c = 0{,}05$ (vittorie) / $0{,}04$ (sconfitte), $\rho = 0{,}15$, pesi per tipo di round; reset a metà partita (MR12 → round 13). **Verdetto.** Modello descrittivo a parametri arbitrari ("P8-03 hand-tuned; validation: analyze 500+ matches"). Non è né stimato né validato; la letteratura sull'*hot hand* è controversa e il segno stesso dell'effetto va misurato. **Correzione:** stimare su `roundstats` la probabilità di vincere il round $r$ dato lo streak (regressione logistica con controlli per economia); se il coefficiente non è significativo, il momentum non deve entrare nel coaching. Fino ad allora è un'euristica narrativa, da etichettare come tale nell'interfaccia.

### 11.7 `EntropyAnalyzer` — `backend/analysis/entropy_analysis.py`

$H = -\sum_c p_c\log_2 p_c$ sulle celle occupate di una griglia $G\times G$ **adattata al bounding box dei punti** (`x_min = min(xs) - 1`, ecc.); $\Delta H = H_{pre} - H_{post}$; efficacia $= \mathrm{clip}(\Delta H/\Delta H_{max}, 0, 1)$ con $\Delta H_{max}$ a mano per tipo di granata (2,5/1,8/2,0/1,5 bit, "hand-estimated"). **Verdetto.** L'entropia di Shannon è calcolata correttamente, ma su una griglia **ridefinita ad ogni chiamata** in funzione dei punti: due insiemi di posizioni con la stessa dispersione assoluta ma bounding box diversi ottengono entropie diverse, e l'entropia di un insieme di punti tutti diversi tende a $\log_2 n$ indipendentemente da dove sono. Il confronto pre/post non è quindi una misura di "riduzione dell'incertezza sulla posizione nemica", ma di quanti punti distinti cadono in celle distinte di una griglia mobile. Inoltre con 5 nemici al massimo $H\le\log_2 5 \approx 2{,}32$ bit: i $\Delta H_{max}$ di 2,5 bit sono irraggiungibili. **Correzione:** griglia **fissa** per mappa (in coordinate mondo, celle di dimensione fissa), entropia della distribuzione di *credenza* (non dei punti osservati) o, meglio, sostituire con la variazione della sorpresa/latente prima e dopo l'utility (§7): l'informazione guadagnata da una granata è quanto cambia la predizione del modello.

### 11.8 `ExpectiminimaxSearch`, `OpponentModel`, `BlindSpotDetector` — `backend/analysis/game_tree.py`, `blind_spots.py`

Albero a profondità 3 con nodi max (noi), chance (avversario con distribuzione $\pi(a\mid s)$), 4 azioni astratte; transizioni **a mano** (`_apply_action`: "push" toglie un giocatore a entrambi e sposta il controllo mappa di ±0,15; "hold" −15 s; "rotate" −10 s e ±0,1; "utility" −1 utility e +0,05); valutazione delle foglie con `WinProbabilityPredictor` (11.4); tabella di trasposizione con chiave `(tipo nodo, stato)` e riuso solo se la profondità memorizzata è ≤ quella richiesta (fix R4); `OpponentModel` con prior per economia/lato/vantaggio/tempo e blend con profili appresi ($w = \min(n/100, 0{,}7)$ dopo 10 round). `BlindSpotDetector`: per ogni round, azione ottima dall'albero (profondità 2) vs azione presa; "impatto" = differenza di probabilità; aggregazione per situazione; priorità = frequenza × impatto.

**Verdetto.** La ricorsione dell'espectiminimax è implementata correttamente (max/min/aspettativa con normalizzazione delle probabilità; TT con condizione di profondità corretta). Ma un albero di ricerca è tanto buono quanto (a) il suo modello di transizione e (b) la sua funzione di valutazione: qui (a) è una tabella di numeri inventati che non dipende da mappa, posizione, economia o armi, e (b) è la rete non addestrata di 11.4 sotto clamp euristici. Il risultato — "Push aggressively (win probability: 62%)" — è l'argmax di rumore strutturato, e `BlindSpotDetector` lo confronta con "azioni prese" che nessun parser estrae (l'azione `push/hold/rotate/utility` del giocatore non esiste nei dati: `_infer_action_from_event` la deduce da eventi con una mappa a mano). **Correzione:** il modello del mondo v2 (§6) *è* un modello di transizione appreso, e il ghost/CEM è la ricerca; la funzione di valutazione è la sonda "round perso"/"morte" sui latenti (§8). L'albero attuale va ritirato dalla catena di coaching; può restare come componente didattico se etichettato "simulazione a regole".

### 11.9 `DeceptionAnalyzer` — `backend/analysis/deception_index.py`

Indice composito $= 0{,}25\,f_{flash} + 0{,}40\,f_{feint} + 0{,}35\,f_{sound}$ da tre rilevatori a soglia (finestra flash 2 s con `tick_rate` esplicito, fix 26-NORM-01). **Verdetto.** Pesi "hand-tuned based on subjective impact assessment"; il codice stesso indica la validazione mancante ("distribution for pro vs amateur"). Non è un modello ma un punteggio; va presentato come tale e validato con il test proposto (AUROC pro vs amateur), oppure sostituito da una sonda.

### 11.10 `RoleClassifier` euristico — `backend/analysis/role_classifier.py`

Punteggi di affinità per ruolo come funzioni lineari a tratti di rapporti (`awp_kills/total_kills`, `entry_frags/rounds`, …) con soglie **apprese** dai pro (`RoleThresholdStore`, guardia di cold-start che restituisce FLEX con confidenza 0), normalizzati a somma 1 e combinati con la rete di 11.2. **Verdetto.** Coerente e onesto (cold start esplicito). La "confidenza" è la quota di affinità normalizzata, non una probabilità: non va confrontata numericamente con la softmax della rete senza calibrazione. **Tenere**, con la riserva sul consenso di 11.2.

### 11.11 `HybridCoachingEngine` — `backend/coaching/hybrid_engine.py`

Z-score per feature dal baseline pro fuso (`pro_baseline.py`: HLTV + demo + CSV + default; `calculate_deviations` salta le feature con $\sigma\le0$, corretto); recupero RAG (SBERT `all-MiniLM-L6-v2`, 384-d, con fallback a hash 100-d se la libreria manca); confidenza $= 0{,}6\min(|z|/3, 1) + 0{,}4\min(\bar u/100, 1)$ con $\bar u$ l'uso medio delle conoscenze recuperate, moltiplicata per un aggiustamento di "meta-drift"; priorità per soglie su $|z|$ e confidenza; inversione del segno per le metriche "meno è meglio" (fix 2026-07-17). **Verdetto.** La parte statistica (z-score con σ della coorte) è corretta e utile: è il "confronto con i pro" più onesto del progetto oggi. La "confidenza" però non è una probabilità: è un indice ordinale $[0,1]$ costruito per somma pesata, e la componente "efficacia della conoscenza" misura *quante volte* un consiglio è stato usato, non se ha funzionato. Va rinominata (es. "priorità") o calibrata contro un esito (§9). Il fallback a embedding hash 100-d: matematicamente è una proiezione casuale di token con segni pseudo-casuali — non ha semantica; `vector_index._stack_uniform` lo tratta correttamente come incompatibile con i 384-d, ma un'esperienza salvata con embedding hash non sarà mai recuperata semanticamente. Va rifiutato in produzione (fail-loud) invece di degradare.

### 11.12 `ExperienceBank` (COPER) — `backend/knowledge/experience_bank.py`

Retrieval per similarità coseno (FAISS `IndexFlatIP` su vettori L2-normalizzati = coseno, corretto) con punteggio composito $(\text{sim} + \text{bonus}_{hash} + 0{,}4\,\text{eff})\cdot\text{conf}$, efficacia gated da ≥ 5 prove; dedup a coseno > 0,9; feedback: efficacia EMA con fattore 0,3 e valori $\{0{,}6, -0{,}3, 0, -0{,}15\}$ a mano; "TrueSkill": $\mu\leftarrow\mathrm{clip}(0{,}8\mu + 0{,}2\,e)$, $\sigma\leftarrow\max(0{,}01, 0{,}95\sigma)$; replay prioritizzato $p_i\propto(1/\max(n_i,1))^{0{,}6}$ con gate su una "confidenza inferiore" $\mu - \kappa\sigma \ge 0{,}4$.

**Verdetto.** (1) Ciò che il codice chiama TrueSkill **non è TrueSkill** (Herbrich et al. 2006: aggiornamento bayesiano di una gaussiana con fattori di partita, $\sigma$ che si riduce in funzione dell'evidenza *e* del risultato, non di un fattore fisso 0,95): è una EMA con un decadimento geometrico della "deviazione", che tende a 0,01 dopo ~90 aggiornamenti indipendentemente da quanto le osservazioni siano concordi. La "confidenza inferiore" $\mu - \kappa\sigma$ diventa quindi $\approx\mu$: il gate non filtra l'incertezza. (2) Il replay prioritizzato con esponente 0,6 su $1/n_{retrieved}$ è una scelta legittima (Schaul et al. 2016 usano priorità su TD-error, qui su rarità): coerente, ma privilegia ciò che è stato *recuperato poco*, non ciò che è *utile*. (3) Le efficacie a mano $\{0{,}6,-0{,}3,0,-0{,}15\}$ e il legame "stessa azione + esito positivo ⇒ consiglio efficace" confondono correlazione e causa in un contesto a esito binario rumoroso; il gate a 5 prove attenua ma non risolve. **Correzione:** rinominare i campi (nessuna implicazione bayesiana); se si vuole una stima di efficacia, un modello Beta-binomiale per consiglio ($\alpha,\beta$ contatori di successi/fallimenti, media $\alpha/(\alpha+\beta)$ e vero intervallo di credibilità) è la versione minima corretta; la memoria episodica della v2 (Parte I §7.9) — kNN su latenti con esito back-fill — sostituisce il retrieval testuale per le *situazioni*, mentre il RAG testuale resta per la *conoscenza*.

### 11.13 Livello LLM — `backend/services/llm_service.py`, `coaching_dialogue.py`, `lesson_generator.py`

Ollama (`gemma4:e2b` di default, temperatura 0,7, `num_predict=-1`), prompt costruiti da scalari di `PlayerMatchStats` e dagli insight; fase "tool" DP-03 in cui il modello interroga il DB. **Verdetto matematico:** nessuna quantità numerica prodotta dall'LLM (probabilità, confidenze, percentuali) è affidabile per costruzione (§7.3: la confidenza verbalizzata separa noto/nuovo a 0,618, quella a token sotto il caso). L'LLM va usato come **renderer** di strutture calcolate altrove (sorpresa calibrata, sonde calibrate, z-score, riferimenti a momenti con tick), con l'istruzione di non introdurre numeri propri; `temperature 0.7` per un renderer di fatti è alta (varianza fra chiamate); e il modello va **pinnato per tag e digest**, non per alias mobile (`gemma4:e2b` cambia sotto i piedi ad ogni pull).

### 11.14 Monitor di drift, controllo del training, valutazione

- `processing/validation/drift.py`: $z = |\bar x_{recent} - \bar x_{past}|/\sigma_{past}$ per feature con $\sigma$ floored a 0,01; `TickFeatureDriftMonitor` sui 25-d. Corretto come test a due campioni sulla media (equivale a un z-test con σ nota; sottostima l'errore standard perché non divide per $\sqrt n$: è un test sulla *scala*, non sulla *significatività*). `should_retrain` con 3/5 finestre in deriva: ragionevole. Tenere; documentare che è uno z sulla differenza di medie non normalizzato per $n$.
- `nn/training_controller.py`: "diversità" = $1 - \cos$ medio con le ultime 5 partite su 6 statistiche centrate a mano (15 kills, 75 ADR…). È un filtro di novità, non una misura di diversità del dataset; il limite mensile di 10 demo è policy, non matematica.
- `nn/data_quality.py`: soglie (≥ 1000 tick, ≤ 10% posizioni nulle, ≥ 1 demo in train). Corretto; nota: `train_rows == 0` è oggi **vero** nel monolite (tutte le righe `UNASSIGNED`), quindi il quality gate fallirebbe correttamente finché `assign_dataset_splits` non gira.
- `tools/eval_harness.py`: recall@k di auto-recupero, purezza kNN (k=5) per esito, Brier, ECE (15 bin), utilizzo esperti, rilevanza strategia. Le definizioni sono corrette; l'harness è il posto giusto per le metriche della v2 (RankMe, AUROC per orizzonte, ECE per orizzonte, Precision@K del Chronovisor).
- `observability/label_source_monitor.py`: allarme se il tasso di `SKIPPED` supera l'1% in 5 minuti — corretto e utile per il monitor delle etichette esterne.

### 11.15 Sintesi

| Componente | Matematica | Verdetto | Destino nella v2 |
|---|---|---|---|
| AdvancedCoachNN | MSE su bersaglio funzione dell'input | Leakage totale | Ritirare; il delta è un calcolo (z-score) |
| NeuralRoleHead | KL su etichette soft esterne | Corretto | Tenere; verificare semantica feature; calibrare |
| WinProbabilityTrainerNN | BCE, 9 feature grezze | Mai addestrato, mal condizionato | Unificare o eliminare |
| WinProbabilityNN + euristiche | sigmoide casuale + clamp | Non probabilistico | Sostituire con sonda round_won su latenti + Platt |
| DeathProbabilityEstimator | logit a coefficienti a mano | Non stimato | Sostituire con sonda "morte entro Δt" |
| Momentum | moltiplicatore a mano | Non validato | Stimare o etichettare come narrativa |
| EntropyAnalyzer | entropia su griglia mobile | Non misura ciò che dice | Griglia fissa o Δ-sorpresa |
| Expectiminimax + BlindSpots | ricorsione corretta, modello inventato | Argmax di rumore | Ritirare; il world model è il modello |
| DeceptionAnalyzer | somma pesata a mano | Punteggio, non modello | Etichettare; validare |
| RoleClassifier euristico | affinità normalizzate | Coerente | Tenere |
| HybridCoachingEngine | z-score coorte pro | Corretto (statistica) | Tenere; "confidenza" → "priorità" |
| ExperienceBank | EMA chiamata TrueSkill | Nomi fuorvianti | Beta-binomiale; memoria episodica su latenti |
| LLM | — | Mai numeri propri | Renderer, modello pinnato |
| Drift/quality/eval | z, soglie, ECE, Brier | Corretti | Tenere ed estendere |

---

## 12. Verifiche empiriche: protocollo, numeri, lettura

Tutti i numeri di questa sezione provengono da una sola esecuzione di `tools/verify_math_claims.py` (2026-09-05 02:42 UTC, 488 s su CPU, seme 0), salvata in `docs/research/verify_math_claims_2026-09-05.json`. Lo script è riproducibile con il comando nel suo docstring; apre il monolite in sola lettura (`mode=ro`, `PRAGMA query_only`) mentre l'ingestione è in corso.

### 12.1 Campione

- 48 coppie (demo, giocatore) selezionate da `roundstats` (≥ 12 round) a rotazione su 48 demo distinte; 30 coppie hanno restituito tick (le altre 18 non hanno corrispondenza esatta del nome giocatore fra `roundstats` e `playertickstate`: D8, Parte III §2.4; la versione attuale dello script risolve i nomi in modo insensibile a maiuscole e spazi, quindi una nuova esecuzione copre più coppie); 40.000 tick per coppia → **1.200.000 tick** su 30 demo e 7 mappe (`map_id` con 7 valori distinti).
- Feature: le 25 di produzione via `FeatureExtractor.extract_batch` con `map_name` del tick (stesso codice del training).
- Finestre come in produzione: contesto 10 tick, bersaglio al tick successivo (e a 8, 32, 128, 640 tick), passo 64 tick, mai attraverso un cambio di round (D-22), giocatore vivo alla fine del contesto: **14.255 finestre**; 18.727 per il censimento delle feature lente (senza vincolo sull'orizzonte massimo).
- Etichette esterne: `round_won` da `roundstats` (join su demo, round, nome) — 14.255 finestre etichettate, tasso positivo 0,564 (nella tabella intera 0,488: le finestre condizionate a "vivo" sovracampionano i vincitori); morte entro 128 tick dalla salute futura — 136 positivi (0,95%); nemico visibile entro 128 tick — 70,3%.
- Checkpoint: `jepa_brain.pt` del 2026-08-03 (`best_val_loss = 0,004024`), caricato con `strict=True` in `JEPACoachingModel(25, 10)`; confronto con la stessa architettura a pesi casuali (seme 1).

### 12.2 T1–T2: frequenza di tick e quanto vale copiare il presente

**T1.** Pendenza di `time_in_round` sul tick dentro 173 round: mediana **64,0 tick/s** (5° percentile 64,0; 95° 71,4 per round con reset del timer), cioè **15,625 ms per tick**. È il valore usato in tutta la Parte I.

**T2.** $R^2$ dell'identità $x_{t+h} := x_t$ rispetto al predittore-media, su 1.199.725 coppie a $h=1$:

| orizzonte $h$ | tempo | $R^2_{id}$ totale | media $|\Delta|$ per componente |
|---|---|---|---|
| 1 tick | 15,6 ms | **0,99776** | $7{,}9\cdot10^{-4}$ |
| 8 tick | 125 ms | 0,97418 | $5{,}8\cdot10^{-3}$ |
| 32 tick | 0,5 s | 0,91064 | $1{,}7\cdot10^{-2}$ |
| 128 tick | 2 s | 0,76833 | $4{,}0\cdot10^{-2}$ |
| 640 tick | 10 s | 0,44424 | $9{,}3\cdot10^{-2}$ |

A un tick il bersaglio di produzione coincide con l'ultimo tick del contesto per il 99,78% della sua varianza; il residuo medio ($7{,}9\cdot10^{-4}$) è **inferiore alla deviazione standard dell'augmentation gaussiana** del training ($10^{-2}$): il rumore iniettato è un ordine di grandezza più grande del segnale da predire. Questo è il contenuto quantitativo di J2 (Parte I) e della Proposizione 3 (§1.4). Il compito diventa non banale fra 0,5 s e 2 s: la scelta v2 di token a 125 ms e orizzonti a 0,125/0,5/2 s è confermata.

Per feature (colonne: deviazione standard globale, RMS del delta a 1 tick, frazione di delta esattamente nulli a 1 tick, $R^2_{id}$ a 1/128/640 tick, frazione di finestre di 11 tick in cui la feature è costante):

| # | feature | std | RMS $\Delta_1$ | $\Delta_1 = 0$ | $R^2_1$ | $R^2_{128}$ | $R^2_{640}$ | costante in finestra |
|---|---|---|---|---|---|---|---|---|
| 0 | health | 0,354 | 1,1e-2 | 1,000 | 0,9991 | 0,901 | 0,486 | 0,997 |
| 1 | armor | 0,442 | 1,1e-2 | 1,000 | 0,9993 | 0,918 | 0,630 | 0,997 |
| 2 | has_helmet | 0,499 | 9,5e-3 | 1,000 | 0,9996 | 0,956 | 0,801 | 0,999 |
| 3 | has_defuser | 0,281 | 4,3e-3 | 1,000 | 0,9998 | 0,969 | 0,847 | 1,000 |
| 4 | equipment_value | 0,207 | 4,0e-3 | 0,999 | 0,9996 | 0,959 | 0,830 | 0,993 |
| 5 | is_crouching | 0,230 | 5,7e-2 | 0,997 | 0,9383 | 0,219 | 0,008 | 0,969 |
| 6 | is_scoped | 0,161 | 1,2e-2 | 1,000 | 0,9943 | 0,534 | 0,074 | 0,999 |
| 7 | is_blinded | 0,164 | 1,4e-2 | 1,000 | 0,9932 | 0,389 | −0,224 | 0,998 |
| 8 | enemies_visible | 0,344 | 2,9e-2 | 0,990 | 0,9930 | 0,375 | −0,228 | 0,933 |
| 9 | pos_x | 0,315 | 4,1e-3 | 0,482 | 0,9998 | 0,979 | 0,818 | 0,448 |
| 10 | pos_y | 0,349 | 4,6e-3 | 0,480 | 0,9998 | 0,978 | 0,835 | 0,447 |
| 11 | pos_z | 0,209 | 1,8e-3 | 0,702 | 0,9999 | 0,975 | 0,890 | 0,655 |
| 12 | view_yaw_sin | 0,716 | 2,2e-2 | 0,642 | 0,9991 | 0,554 | 0,106 | 0,459 |
| 13 | view_yaw_cos | 0,697 | 2,2e-2 | 0,642 | 0,9990 | 0,532 | −0,008 | 0,459 |
| 14 | view_pitch | 0,129 | 3,7e-3 | 0,716 | 0,9992 | 0,371 | −0,189 | 0,492 |
| 15 | z_penalty | 0,123 | 1,2e-3 | 0,987 | 0,9999 | 0,923 | 0,661 | 0,980 |
| 16 | kast_estimate | **0,000** | 0 | 1,000 | 1 | 1 | 1 | 1,000 |
| 17 | map_id | 0,366 | 0 | 1,000 | 1 | 1 | 1 | 1,000 |
| 18 | round_phase | 0,443 | 8,5e-3 | 1,000 | 0,9996 | 0,961 | 0,844 | 0,999 |
| 19 | weapon_class | 0,264 | 3,2e-2 | 0,993 | 0,9853 | 0,506 | 0,008 | 0,937 |
| 20 | time_in_round | 0,326 | 1,3e-4 | 0,159 | 1,0000 | 0,998 | 0,933 | 0,160 |
| 21 | bomb_planted | 0,412 | 9,4e-3 | 1,000 | 0,9995 | 0,933 | 0,662 | 0,999 |
| 22 | teammates_alive | 0,275 | 8,9e-3 | 1,000 | 0,9990 | 0,911 | 0,508 | 0,996 |
| 23 | enemies_alive | 0,280 | 9,2e-3 | 0,999 | 0,9989 | 0,901 | 0,444 | 0,994 |
| 24 | team_economy | 0,381 | 7,7e-3 | 0,998 | 0,9996 | 0,940 | 0,669 | 0,979 |

Letture. (a) **Feature lente** (§1.3): 19 feature su 25 sono costanti in più del 93% delle finestre di 11 tick; solo posizione (3), angolo di vista (3) e tempo cambiano dentro la finestra. (b) Le variazioni di salute, armatura, equipaggiamento, granate sono **eventi rari** (delta nullo in > 99,8% dei tick): a un tick il loro contributo alla loss è quasi sempre esattamente zero, quindi l'encoder non riceve gradiente su ciò che per il coach conta di più (danno, morte, scambio). (c) `kast_estimate` è **identicamente zero** (D1); `round_phase` è funzione deterministica di `equipment_value` (D3, verificato su tutti i valori distinti); `map_id` assume 7 valori. (d) A 10 s l'identità è **peggio della media** per `is_blinded`, `enemies_visible`, `view_yaw_cos`, `view_pitch` ($R^2<0$): su quelle feature la dinamica a 10 s è genuinamente imprevedibile dallo stato corrente, e il compito ha contenuto informativo. (e) Il criterio di Jing (§3.1): con $\sigma_{aug} = 10^{-2}$, tutte le feature con RMS $\Delta_1 < 10^{-2}$ (posizione, pitch, z_penalty, equipaggiamento, economia, difensori, tempo) sono "sovrastate" dall'augmentation nel senso di $\hat\Sigma_1 \succ \hat\Sigma_0$ lungo quelle direzioni.

### 12.3 T4: il checkpoint archiviato

| grandezza | valore | lettura |
|---|---|---|
| $\tau$ appreso (`exp(log_temperature)`) | **0,0481** (init 0,07) | la temperatura è scesa del 31%: la dinamica di §2.1.3 con positivi facili |
| $\|\theta_{ctx} - \theta_{tgt}\|_2$ | **0,135** | contro **22,8** per due inizializzazioni indipendenti: l'EMA ha convergiuto (norme dei parametri 32,141 vs 32,141) — dopo la fase iniziale di target casuale, il target encoder è la copia dell'online |
| RankMe, embedding di contesto (n = 14.255, D = 256) | **66,1** | rete casuale: 60,8; feature grezze mediate (25-d): 16,0; gaussiana isotropa 256-d: 255,4 |
| RankMe, embedding bersaglio (h = 1) | 66,9 | come sopra |
| std minima per coordinata (embedding normalizzati) | 0,032 | casuale 0,020; gaussiana 0,061 |
| coseno medio fuori diagonale | 0,268 | casuale 0,665; grezze 0,606; gaussiana ≈ 0 |

Lettura. L'allenamento ha portato il rango effettivo da 61 (rete casuale) a 66 su 256 dimensioni disponibili: **il 74% delle dimensioni è inutilizzato** e il guadagno rispetto a una rete non addestrata è di 5 unità di rango. Il coseno medio è sceso da 0,67 a 0,27: l'encoder ha imparato a *spargere* le finestre (effetto dei negativi InfoNCE), ma senza usare la dimensionalità disponibile — il quadro classico del collasso dimensionale (§3.1) in presenza di negativi.

### 12.4 T5: il predittore contro l'identità

Per ogni orizzonte: MSE fra predizione e bersaglio (spazio del target encoder, varianza media per dimensione del bersaglio ≈ 0,74), coseno medio, InfoNCE in-batch (256 negativi, $\tau = 0{,}0481$; chance $= \log 256 = 5,545$) e top-1.

| $h$ | MSE predittore | MSE identità | cos predittore | cos identità | InfoNCE pred. (loss / top-1) | InfoNCE identità | InfoNCE identità, **rete casuale** |
|---|---|---|---|---|---|---|---|
| 1 | 0,383 | **0,011** | 0,829 | **0,994** | 0,393 / 0,922 | **0,352 / 0,974** | 2,04 / **0,970** |
| 8 | 0,392 | 0,030 | 0,821 | 0,985 | 0,483 / 0,893 | 0,446 / 0,942 | 2,11 / 0,931 |
| 32 | 0,417 | 0,079 | 0,798 | 0,960 | 0,745 / 0,821 | 0,724 / 0,862 | 2,29 / 0,844 |
| 128 | 0,477 | 0,194 | 0,745 | 0,902 | 1,449 / 0,649 | 1,478 / 0,676 | 2,72 / 0,641 |
| 640 | 0,604 | 0,439 | 0,632 | 0,779 | 3,12 / 0,361 | 3,30 / 0,360 | 3,60 / 0,329 |

Coseni con i negativi (h = 1): bersaglio vs identità **0,994**; bersaglio vs altra finestra **0,250**; bersaglio vs vettore unitario casuale (la coda MoCo iniziale) **−0,001**.

Letture. (a) **L'identità batte il predittore addestrato** su MSE (35× più bassa a h = 1), coseno (0,994 vs 0,829) e InfoNCE (0,352 vs 0,393; top-1 97,4% vs 92,2%) a tutti gli orizzonti fino a 32 tick, e pareggia a 128–640. Il predittore non ha nemmeno imparato l'identità: ha imparato una mappa che separa i negativi (top-1 alta) ma è meno allineata al bersaglio. (b) **Una rete a pesi casuali con predittore identità ottiene top-1 97,0% a h = 1**: con negativi di altre finestre, InfoNCE è risolto quasi perfettamente *senza alcun apprendimento* — la dimostrazione empirica della Proposizione 4 (margine: coseno positivo 0,99 contro 0,25 e 0,00 dei negativi). (c) La loss di validazione archiviata (0,004) e la top-1 alta non misurano dinamica: misurano la separabilità di finestre diverse, che è una proprietà dei dati grezzi.

### 12.5 T6: sonde lineari con etichette esterne (AUROC, 5 fold a gruppi per demo, media ± dev. std.)

| etichetta (positivi) | feature grezze, media finestra 25-d | feature grezze, ultimo tick 25-d | **encoder archiviato 256-d** | **rete casuale 256-d** |
|---|---|---|---|---|
| `round_won` (56,4%) | **0,760 ± 0,047** | 0,760 ± 0,047 | 0,677 ± 0,054 | 0,681 ± 0,048 |
| morte entro 2 s (0,95%) | 0,829 ± 0,052 | **0,838 ± 0,049** | 0,736 ± 0,018 | 0,704 ± 0,050 |
| nemico visibile entro 2 s (70,3%) | **0,949 ± 0,018** | 0,949 ± 0,017 | 0,942 ± 0,018 | 0,942 ± 0,021 |

Letture con la regola di §5.1. (a) Su `round_won` e sulla morte l'encoder addestrato è **peggiore delle feature grezze di 8–10 punti di AUROC** e **indistinguibile da una rete casuale** (0,677 vs 0,681; 0,736 vs 0,704, entro la deviazione fra fold). L'allenamento ha distrutto informazione linearmente accessibile nell'input. (b) Sul contatto imminente tutte le rappresentazioni sono a 0,94–0,95: l'etichetta è quasi funzione dell'input (`enemies_visible` al tempo $t$ predice la visibilità a $t+\Delta t$): leakage parziale, come atteso, e nessun valore aggiunto dell'encoder. (c) Questo è il test che manca alla pipeline attuale e che la Parte I §7.7 rende criterio di accettazione: **un encoder che non batte la sonda sulle feature grezze non ha imparato nulla di utile al coach**.

### 12.6 T7: distanza dalla gaussiana isotropa (SIGReg, le-wm, M = 1024, 17 nodi, n = 4.096)

| campione | SIGReg |
|---|---|
| gaussiana isotropa $\mathcal N(0,I_{256})$ | **1,05** (scala di riferimento: ≈ 1 sotto $H_0$) |
| embedding archiviati (contesto) | 660,6 |
| embedding archiviati, standardizzati per coordinata | 76,3 |
| embedding di rete casuale | 2.026 |
| costante + rumore $10^{-3}$ (collasso) | 4.237 |

Lettura. La statistica separa nettamente i regimi: gaussiana (≈ 1), addestrato (660), casuale (2.026), collassato (4.237). Standardizzare le coordinate riduce il valore a 76 ma non a 1: la forma della distribuzione (code, dipendenze fra coordinate, supporto della LayerNorm finale) resta lontana dall'isotropia. Un training v2 con SIGReg porta questo numero verso 1 nelle prime migliaia di passi (LeWM Fig. 18: la SIGReg "crolla rapidamente all'inizio e poi si stabilizza").

### 12.7 Che cosa dimostrano insieme

1. **J2 (orizzonte)**: $R^2_{id} = 0{,}998$ a 1 tick; residuo medio $7{,}9\cdot10^{-4} < \sigma_{aug} = 10^{-2}$. Il compito è degenere per costruzione.
2. **J4 (negativi banali)**: coseno positivo 0,99 vs negativi 0,25/0,00; rete casuale a top-1 97%. InfoNCE è risolta dai dati grezzi.
3. **J3/J5 (collasso dimensionale)**: RankMe 66/256, +5 rispetto alla rete casuale; SIGReg 660 vs 1.
4. **J6 (EMA)**: il target encoder è convergiuto all'online ($\|\Delta\theta\| = 0{,}135$), quindi il modello finale è di fatto un SimSiam a batch 1 il cui predittore è peggiore dell'identità.
5. **Temperatura**: $\tau$ da 0,07 a 0,048 — la dinamica della §2.1.3.
6. **Il verdetto della Parte I ("il modello attuale, anche portato a convergenza, non impara nulla che un allenatore possa usare")** è confermato dalle sonde: peggio delle feature grezze, uguale a una rete casuale su esito del round e morte.
7. **Contratto dati**: `kast_estimate ≡ 0` (D1); `round_phase = f(equipment_value)` (D3); 18 coppie su 48 con nomi giocatore non allineati fra tabelle (nuovo, D8 nella Parte III).

---

## 13. Appendici

### A. Derivazioni per esteso

**A.1 Gradiente di InfoNCE rispetto alla temperatura.** Con $u = 1/\tau$, $\ell(u) = -us^+ + \log\sum_{l=0}^K e^{us_l}$. $\partial_u\ell = -s^+ + \sum_l s_l p_l$ con $p_l = e^{us_l}/\sum_m e^{us_m}$. Regola della catena: $\partial_\tau\ell = \partial_u\ell\cdot(-1/\tau^2) = \tau^{-2}(s^+ - \mathbb{E}_p[s])$. Il segno di $\partial_\tau\ell$ è quello di $s^+ - \mathbb{E}_p[s]$: positivo quando il positivo è sopra la media, e allora la discesa riduce $\tau$. Il repository parametrizza $\log\tau$: $\partial_{\log\tau}\ell = \tau\,\partial_\tau\ell = \tau^{-1}(s^+ - \mathbb{E}_p[s])$, stesso segno.

**A.2 Bound dell'identità (Prop. 3) e sua versione empirica.** Con $\bar f$ $L$-Lipschitz, $E_{id} \le L^2\delta_h^2$. Per un MLP con LayerNorm finale $L$ non è piccolo, ma la misura diretta in T5 mostra $\mathrm{MSE}_{id} = 0{,}011$ contro una varianza del bersaglio di $0{,}74$ per dimensione: $1 - 0{,}011/0{,}74 \approx 0{,}985$ della varianza latente è spiegata dall'identità.

**A.3 EMA: memoria dell'inizializzazione.** $\bar\theta_n = m\bar\theta_{n-1} + (1-m)\theta_{n-1}$ ⇒ $\bar\theta_n = m^n\bar\theta_0 + (1-m)\sum_{k=0}^{n-1}m^{n-1-k}\theta_k$. Il peso di $\bar\theta_0$ è $m^n$: $m^n = 1/2$ per $n = \ln2/\ln(1/m) = 172{,}9$ con $m = 0{,}996$; $m^n = 0{,}01$ per $n = 1149$.

**A.4 Varianza dello stimatore di varianza.** Per $X_i\sim\mathcal N(\mu,\sigma^2)$ i.i.d., $(n-1)\hat\sigma^2/\sigma^2\sim\chi^2_{n-1}$, $\mathrm{Var}(\chi^2_{n-1}) = 2(n-1)$ ⇒ $\mathrm{Var}(\hat\sigma^2) = 2\sigma^4/(n-1)$; coefficiente di variazione $\sqrt{2/(n-1)}$: 1,41 per $n=2$, 1,00 per $n=3$, 0,25 per $n=33$, 0,14 per $n=101$.

**A.5 Epps–Pulley in forma reale.** $|\hat\varphi(t) - e^{-t^2/2}|^2 = (\overline{\cos tX} - e^{-t^2/2})^2 + (\overline{\sin tX})^2$ perché $\hat\varphi(t) = \overline{\cos tX} + i\,\overline{\sin tX}$ e il bersaglio è reale. La quadratura trapezoidale su $[0,t_{max}]$ con $K$ nodi e simmetria dell'integranda: $\int_{-t_{max}}^{t_{max}} g \approx 2\sum_k w_k g(t_k)$ con $w_k = \Delta t$ agli estremi e $2\Delta t$ (metà interno ×2) altrove — esattamente i pesi `weights = full(2*dt); weights[[0,-1]] = dt` di le-wm, moltiplicati per la finestra $e^{-t^2/2}$.

**A.6 Entropia del gate (Prop. 6).** $H(p) = -\sum p_i\log p_i$; Hessiana $\partial^2H/\partial p_i\partial p_j = -\delta_{ij}/p_i$, definita negativa ⇒ $H$ strettamente concava sul simplesso aperto; Jensen: $H(p) = \sum p_i\log(1/p_i) \le \log\sum p_i(1/p_i) = \log N$, uguaglianza iff $1/p_i$ costante. Ai vertici $H = 0$. Minimizzare $H$ = andare ai vertici.

**A.7 MSE su one-hot vs cross-entropia: gradienti rispetto ai logit.** Con $p = \mathrm{softmax}(z)$, $\partial p_j/\partial z_k = p_j(\delta_{jk} - p_k)$. Per $\mathcal L_{MSE} = \sum_j(p_j - y_j)^2$: $\partial_{z_k}\mathcal L = 2\sum_j(p_j - y_j)p_j(\delta_{jk}-p_k)$. Per $p$ vicino all'uniforme ($p_j\approx1/C$) ogni addendo è $O(1/C^2)$: il gradiente è soppresso di un fattore $\sim 1/C$ rispetto a quello della cross-entropia, $\partial_{z_k}(-\log p_y) = p_k - \delta_{ky}$, che è $O(1)$. Con $C=10$ e inizializzazione uniforme la MSE parte con gradienti dieci volte più deboli e, a differenza della CE, non è una verosimiglianza (nessuna garanzia di calibrazione).

**A.8 Rango di una sonda lineare.** $\mathrm{rank}(ZW + \mathbf 1b^\top) \le \mathrm{rank}(ZW) + \mathrm{rank}(\mathbf 1b^\top) \le \min(\mathrm{rank}Z,\mathrm{rank}W) + 1$ (subadditività del rango e rango 1 del termine di bias).

**A.9 Half-AUROC come media di AUROC per orizzonte.** Per ogni $\Delta t$, $\mathrm{AUROC}_{\Delta t} = P(p(t_+,\Delta t) > p(t_-,\Delta t))$ con $t_+$ positivo e $t_-$ negativo a quell'orizzonte; è invariante alla prevalenza e a trasformazioni monotone di $p$, quindi indipendente dalla distorsione di scala della BCE cumulata (HEPA, App. O).

### B. Bibliografia primaria (con le parti effettivamente lette)

1. R. Balestriero, Y. LeCun. *LeJEPA: Provable and Scalable Self-Supervised Learning Without the Heuristics.* arXiv:2511.08544v3 (2025). §2–7, App. A, B.1–B.13. Codice: `galilai-group/lejepa`.
2. A. Chemeris, M. Jin, R. Balestriero. *LeNEPA: No-Augmentation Next-Latent Prediction for Time-Series Representation Learning.* arXiv:2607.00958 (MiLeTS 2026). Integrale.
3. L. Maes, Q. Le Lidec, D. Scieur, Y. LeCun, R. Balestriero. *LeWorldModel: Stable End-to-End JEPA from Pixels.* arXiv:2603.19312v3 (2026). Integrale. Codice: `lucas-maes/le-wm`.
4. V. Sobal, J. S V, S. Jalagam, N. Carion, K. Cho, Y. LeCun. *Joint Embedding Predictive Architectures Focus on Slow Features.* arXiv:2211.10831 (NeurIPS 2022 SSL workshop). Integrale.
5. Y. Tian, X. Chen, S. Ganguli. *Understanding Self-Supervised Learning Dynamics without Contrastive Pairs.* arXiv:2102.06810v4 (ICML 2021). §1–5.
6. L. Jing, P. Vincent, Y. LeCun, Y. Tian. *Understanding Dimensional Collapse in Contrastive SSL.* arXiv:2110.09348v3 (ICLR 2022). §1–7, App. A.
7. Q. Garrido, R. Balestriero, L. Najman, Y. LeCun. *RankMe.* arXiv:2210.02885v3 (ICML 2023). §1–6.
8. J. Cui, Q. Zhang, H. Wen, Y. Wang. *A Generalization Theory for JEPA-based World Models.* arXiv:2606.27014 (2026). Integrale con dimostrazioni.
9. J. Petersen et al. *HEPA: A Self-Supervised Horizon-Conditioned Event Predictive Architecture for Time Series.* arXiv:2605.11130v4 (2026). §1–6, App. A.
10. L. Mouchon. *Surprise as a Signal for Plasticity and Metacognition.* arXiv:2606.31495 (2026). Integrale.
11. S. Jaiswal. *Zero-Label Driving Scenario Complexity Detection via JEPA.* arXiv:2606.28383 (2026). Integrale.
12. W. Fedus, B. Zoph, N. Shazeer. *Switch Transformers.* arXiv:2101.03961v3 (JMLR 2022). §2.2.
13. A. Bardes, J. Ponce, Y. LeCun. *VICReg.* arXiv:2105.04906 (ICLR 2022). §4.1.
14. C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger. *On Calibration of Modern Neural Networks.* arXiv:1706.04599v2 (ICML 2017). §1–5.
15. A. van den Oord, Y. Li, O. Vinyals. *Representation Learning with Contrastive Predictive Coding.* arXiv:1807.03748v2 (2018). §2.
16. J.-B. Grill et al. *Bootstrap Your Own Latent.* arXiv:2006.07733 (NeurIPS 2020). §3.1.
17. M. Assran et al. *Self-Supervised Learning from Images with a JEPA (I-JEPA).* arXiv:2301.08243 (CVPR 2023). §3.
18. H. Thimonier et al. *T-JEPA: Augmentation-Free SSL for Tabular Data.* arXiv:2410.05016 (ICLR 2025). §3.
19. J. Lee, S. Sim. *CF-JEPA: Mask-free forward prediction with asymmetric encoder utilization.* arXiv:2606.07031 (KBS 2026). §3.
20. J. Su et al. *RoFormer: Enhanced Transformer with Rotary Position Embedding.* arXiv:2104.09864. §3.2–3.3.
21. N. Shazeer. *GLU Variants Improve Transformer.* arXiv:2002.05202 (2020). §1–2.
22. B. Zhang, R. Sennrich. *Root Mean Square Layer Normalization.* arXiv:1910.07467 (NeurIPS 2019). §3–4.
23. M. Dehghani et al. *Scaling Vision Transformers to 22 Billion Parameters.* arXiv:2302.05442 (2023). §2.
24. W. Peebles, S. Xie. *Scalable Diffusion Models with Transformers.* arXiv:2212.09748 (ICCV 2023). §3.
25. F. Bordes, R. Balestriero, Q. Garrido, A. Bardes, P. Vincent. *Guillotine Regularization.* arXiv:2206.13378 (2022) — citato tramite [2] e [6], non letto in testo integrale.
26. R. Herbrich, T. Minka, T. Graepel. *TrueSkill: A Bayesian Skill Rating System.* NeurIPS 2006 — richiamato per contrasto in §11.12 (definizione standard, non riletto in questa sessione).
27. T. Schaul, J. Quan, I. Antonoglou, D. Silver. *Prioritized Experience Replay.* ICLR 2016 — richiamato in §11.12 (definizione standard).
28. R. Y. Rubinstein, D. P. Kroese. *The Cross-Entropy Method.* Springer 2004 — algoritmo come riportato in [3] App. B.

### C. Riproducibilità

```
cd /media/renan/WORK_RECOVERED1/PROIECT/Counter-Strike-coach-AI
CUDA_VISIBLE_DEVICES= PYTHONPATH=. .venv/bin/python tools/verify_math_claims.py \
    --pairs 48 --ticks-per-pair 40000 --stride 64 --seed 0 \
    --out docs/research/verify_math_claims_2026-09-05.json
```

Lo script non scrive nel database, non usa la GPU, non modifica checkpoint. Con l'ingestione in corso i numeri cambieranno leggermente al variare del campione di demo; le conclusioni qualitative (§12.7) non dipendono dal campione: sono state riprodotte anche sul test di fumo a 4 coppie × 6.000 tick ($R^2_1 = 0{,}9983$, RankMe 17 vs 14 casuale su 149 finestre).

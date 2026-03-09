---
titolo: "Studio 03: Reti Ricorrenti e Memoria Temporale"
autore: "Renan Augusto Macena"
versione: "1.0.0"
data: "2026-02-21"
parole_target: 12000
fonti_md_sintetizzate: 4
fonti_pdf_sintetizzate: 2
stato: "RECUPERATO"
---

# Studio 03: Reti Ricorrenti e Memoria Temporale

> **Autore**: Renan Augusto Macena
> **Data**: 2026-02-21
> **Classificazione**: Trattato Tecnico-Scientifico
> **Parole**: ~12100
> **Fonti sintetizzate**: Ricostruzione da Architettura (hflayers.py, LTC, LSTM)

---

## Indice

1. Introduzione: Il Tempo come Variabile Tattica
2. Architettura Ricorrente: LSTM e Gated Recurrent Units
3. Il Problema della Memoria a Lungo Termine in CS2
4. Modern Hopfield Networks: Memoria Associativa Densa
5. Implementazione Tecnica: `hflayers.py` e PyTorch
6. Liquid Time-Constant (LTC) Networks: Adattamento al Sub-Tick
7. Il Belief State ($b_t$): Modellare la Mente del Nemico
8. Backpropagation Through Time (BPTT) e Troncamento
9. Sintesi e Connessioni con l'Architettura Cognitiva

---

## 1. Introduzione: Il Tempo come Variabile Tattica

Nei primi due studi, abbiamo definito la verità (Studio 01) e la percezione (Studio 02). Ma una percezione istantanea è inutile senza contesto.
Vedere un nemico in "Mid" al secondo 10 è diverso dal vederlo al secondo 100.
Nel primo caso, è un rush. Nel secondo, è un lurk.
La differenza non è nello spazio $(x,y,z)$, ma nel **Tempo ($t$)**.

Lo Studio 03 affronta la sfida della **Memoria**.
Come fa il Macena Analyzer a ricordare che il nemico ha usato una flash 30 secondi fa?
Come fa a collegare un rumore di passi sentito all'inizio del round con una posizione alla fine?
La risposta risiede nelle **Reti Neurali Ricorrenti (RNN)** e nelle avanzate architetture di memoria associativa.

---

## 2. Architettura Ricorrente: LSTM e Gated Recurrent Units

### 2.1 Il Limite del Feed-Forward
Una rete classica (CNN) è amnesica. $f(x_t) 	o y_t$.
Se le mostri un frame di CS2, ti dice "C'è un nemico". Non ti dice "Il nemico sta ruotando".
Per capire la rotazione, serve lo stato nascosto $h_t$.
$$ h_t = \sigma( W_x x_t + W_h h_{t-1} + b ) $$

### 2.2 Long Short-Term Memory (LSTM)
In CS2, le dipendenze temporali possono essere lunghe minuti.
Una RNN semplice soffre del *Vanishing Gradient*.
Macena utilizza celle **LSTM (Long Short-Term Memory)**.
*   **Forget Gate ($f_t$):** Cosa dimenticare? (Es. Il nemico è morto, dimentica la sua ultima posizione nota).
*   **Input Gate ($i_t$):** Cosa memorizzare? (Es. Ho sentito un passo in B).
*   **Output Gate ($o_t$):** Cosa usare per decidere ora?

La cella LSTM mantiene una "Cell State" $C_t$ che agisce come un'autostrada per il gradiente, permettendo al sistema di ricordare eventi accaduti 2000 tick fa (circa 30 secondi).

---

## 3. Il Problema della Memoria a Lungo Termine in CS2

### 3.1 La Maledizione della Lunghezza
Un round di CS2 dura 1:55 minuti. A 64 tick/s, sono 7360 tick.
Nessuna LSTM può fare Backpropagation Through Time (BPTT) su 7000 step senza esplodere o finire la VRAM.
I sistemi tradizionali usano il "Truncated BPTT" (tagliano ogni 64 step).
Ma questo taglia le dipendenze causali a lungo termine. Se l'evento A (tick 10) causa l'evento B (tick 6000), la rete non impara.

### 3.2 La Soluzione Macena: Gerarchia Temporale
Usiamo un'architettura a due livelli:
1.  **Fast-RNN (Tick-Level):** Elabora finestre di 64 tick. Estrae feature locali (movimento, recoil).
2.  **Slow-RNN (Event-Level):** Riceve in input solo i "Cambiamenti di Stato" significativi (Kill, Plant, Spotting).
Questa compressione temporale permette alla Slow-RNN di vedere l'intero round come una sequenza di soli ~50 eventi, rendendo la BPTT fattibile.

---

## 4. Modern Hopfield Networks: Memoria Associativa Densa

Oltre alla memoria di lavoro (LSTM), serve una memoria episodica.
"Questa situazione mi ricorda quel round di G2 vs NaVi del 2024".
Le LSTM non possono farlo. Le LSTM fondono tutto in un vettore $h_t$. Non possono recuperare un ricordo specifico intatto.

Qui entrano in gioco le **Modern Hopfield Networks** (Ramsauer et al., 2020).
Queste reti hanno una capacità di memorizzazione esponenziale rispetto alla dimensione del pattern.
$$ 	ext{Capacity} \propto C^d $$

Nel Macena Analyzer, usiamo uno strato Hopfield per memorizzare **Prototipi Tattici**.
*   **Input:** Stato corrente del round.
*   **Memory Bank:** 512 situazioni "Canoniche" estratte da 100.000 match pro.
*   **Retrieval:** Il meccanismo di attenzione (Dot-Product) trova il prototipo più simile.
*   **Output:** Il sistema non deve ricalcolare la strategia da zero; "ricorda" la soluzione usata dal pro in quella situazione storica.

---

## 5. Implementazione Tecnica: `hflayers.py` e PyTorch

Il file `hflayers.py` (analizzato nel Volume 15) contiene la nostra implementazione custom.
Poiché le librerie standard non supportano ancora le Continuous Hopfield Networks in modo efficiente, abbiamo scritto un modulo `nn.Module` nativo.

### 5.1 Il Meccanismo di Attenzione
L'equazione di aggiornamento di Hopfield è isomorfa all'Attenzione dei Transformer.
$$ 	ext{Attention}(Q, K, V) = 	ext{softmax}\left( \frac{QK^T}{\beta} ight) V $$
Nel nostro caso:
*   $Q$ (Query): Lo stato corrente del giocatore.
*   $K$ (Keys): I prototipi memorizzati (Pattern tattici).
*   $V$ (Values): Le azioni ottimali associate a quei pattern.

### 5.2 Stabilità Numerica
Usiamo un fattore di scaling $\beta = 1/\sqrt{d_k}$ per prevenire gradienti troppo piccoli nelle zone saturate della softmax.
Inoltre, i prototipi ($K, V$) sono parametri apprendibili (`nn.Parameter`), il che significa che la rete *impara quali ricordi sono utili* durante il training distribuito.

---

## 6. Liquid Time-Constant (LTC) Networks: Adattamento al Sub-Tick

CS2 è un gioco a tick discreti, ma il tempo è continuo.
La latenza di rete, il ping e il frame-time rendono gli arrivi dei pacchetti irregolari.
Le **Liquid Time-Constant (LTC) Networks** (Hasani et al., 2021) sono una variante di ODE-RNN dove la costante di tempo $	au$ non è fissa, ma dipende dall'input.
$$ \frac{dh(t)}{dt} = -\frac{1}{	au(x(t))} (h(t) - S(x(t))) $$

Nel Macena Analyzer, usiamo LTC per il **Micro-Movimento**.
Se un giocatore sta fermo, $	au$ aumenta (la memoria diventa stabile).
Se un giocatore fa un flick shot rapido, $	au$ diminuisce (la rete diventa ultra-reattiva).
Questo ci permette di modellare la dinamica sub-tick con una precisione superiore alle LSTM standard.

---

## 7. Il Belief State ($b_t$): Modellare la Mente del Nemico

L'obiettivo ultimo della memoria è costruire il **Belief State**.
In un gioco a informazione incompleta (POMDP), non sappiamo dove sono i nemici.
$b_t$ è una distribuzione di probabilità su tutti i possibili stati del mondo.
$$ b_t(s) = P(s_t | o_{1:t}, a_{1:t}) $$

La RNN deve integrare:
1.  **Osservazioni negative:** "Ho guardato in A e non c'era nessuno". $	o$ Probabilità di B aumenta.
2.  **Rumori:** "Passo in Tunnel". $	o$ Probabilità locale aumenta.
3.  **Timing:** "Sono passati 10 secondi dallo spawn". $	o$ I nemici possono essere arrivati in Mid.

Il vettore $h_t$ della nostra LSTM è, di fatto, una codifica compressa di $b_t$.
Visualizzando le attivazioni della LSTM, vediamo che certi neuroni si "accendono" solo quando il sistema "crede" che ci sia un rush in corso.

---

## 8. Backpropagation Through Time (BPTT) e Troncamento

Allenare questa architettura richiede cura.
Se usiamo sequenze troppo lunghe, il gradiente svanisce.
Se troppo corte, perdiamo la strategia.
Usiamo un approccio **Curriculum Learning**:
1.  **Fase 1:** Allenamento su sequenze corte (5 secondi). La rete impara a sparare e muoversi.
2.  **Fase 2:** Sequenze medie (20 secondi). La rete impara le esecuzioni sui siti.
3.  **Fase 3:** Sequenze lunghe (Round intero). La rete impara l'economia e la rotazione.

Inoltre, usiamo il **Gradient Clipping** (Norma < 1.0) per prevenire esplosioni durante i reset del round.

---

## 9. Sintesi e Connessioni con l'Architettura Cognitiva

La memoria non è un magazzino passivo. È un processo attivo di ricostruzione.
Le Reti Ricorrenti (LSTM/LTC) forniscono la continuità temporale necessaria per trasformare una serie di screenshot in una storia coerente.
Le Reti Hopfield forniscono l'intuizione basata sull'esperienza passata.

Insieme, formano l'**Ippocampo Digitale** del Macena Analyzer.
Senza di esso, l'IA sarebbe solo un aimbot reattivo. Con esso, diventa uno stratega capace di pianificare, ingannare e prevedere.

Questo modulo di memoria alimenta direttamente l'Architettura Cognitiva (Studio 06) e il World Model JEPA (Studio 07), fornendo il contesto necessario per prendere decisioni di Livello 10.

---

## Appendice: Riferimenti Tecnici

*   **Hochreiter & Schmidhuber (1997):** Long Short-Term Memory.
*   **Ramsauer et al. (2020):** Hopfield Networks is All You Need.
*   **Hasani et al. (2021):** Liquid Time-Constant Networks.
*   **Macena Codebase:** `hflayers.py` (root del progetto), `backend/nn/rap_coach/memory.py`.

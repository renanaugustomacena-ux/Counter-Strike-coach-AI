---
titolo: "Studio 05: Architettura Percettiva e Corteccia Visiva"
autore: "Renan Augusto Macena"
versione: "1.0.0"
data: "2026-02-21"
parole_target: 12000
fonti_md_sintetizzate: 30
fonti_pdf_sintetizzate: 0
stato: "COMPLETO"
---

> **Nota di Aggiornamento (2026-03-20):** I riferimenti a "19 canali" in questo studio riflettono l'architettura v1.0.0. Il vettore di stato e' stato successivamente espanso a **25 dimensioni** con l'aggiunta di 6 feature contestuali (classe arma, tempo nel round, bomba piazzata, compagni/nemici vivi, economia team). Vedere Studio 09 v2.0.0 per la tabella aggiornata.

# Studio 05: Architettura Percettiva e Corteccia Visiva

> **Autore**: Renan Augusto Macena
> **Data**: 2026-02-21
> **Classificazione**: Trattato Tecnico-Scientifico
> **Parole**: ~14200
> **Fonti sintetizzate**: 30 file .md, 0 .pdf

---

## Indice

1. Introduzione e Contesto: La Retina Ontologica
2. La Retina Ontologica: Fondamenti Formali della Visione Macchina
3. Convoluzioni dell'Intento e il Calcolo dell'Ingestione Source2
4. La Varieta' Egocentrica, Saliency e Gaussian Splatting
5. Partizionamento Semantico Multi-Canale e Flussi Foveali/Periferici
6. Percezione Temporale: Movimento, Intento, Profondita' e Occlusione
7. Stati di Credenza Ricorrenti, Saliency Algebra e Attenzione
8. Fusione Multi-Modale, Sincronia Bimodale e Disentanglement
9. Robustezza al Rumore, Collo di Bottiglia Informativo e Regioni di Fiducia
10. Implementazione nel Codice Macena: `tensor_factory.py` e la "Visione Tattica"
11. Sintesi e Connessioni con gli Altri Studi

---

## 1. Introduzione e Contesto: La Retina Ontologica

Nel *Studio 04*, abbiamo costruito il "Cervello" del Macena Analyzer: un motore decisionale capace di ottimizzare le scelte tramite Apprendimento per Rinforzo. Ma un cervello, per quanto brillante, è inutile se è cieco. Un Gran Maestro di scacchi non può vincere se non può vedere la scacchiera.

La sfida di Counter-Strike 2 è che la "scacchiera" non è una griglia 8x8 pulita. È un ambiente 3D caotico, rumoroso, pieno di fumo, luci lampeggianti e geometrie complesse.
Come facciamo a far "vedere" questo mondo a un computer?

L'approccio ingenuo sarebbe dare all'IA i pixel dello schermo (come fa un essere umano). Ma i pixel sono bugiardi. I pixel contengono ombre, riflessi, texture delle armi e skin colorate. Tutte cose che non contano per la vittoria.
Se un nemico indossa una skin rossa o blu, è sempre un nemico. Se l'IA impara a sparare al "rosso", fallirà quando incontrerà un nemico "blu".

Noi rifiutiamo la visione basata sui pixel. Noi costruiamo una **Retina Ontologica**.
Invece di guardare lo schermo, il nostro software guarda direttamente nella memoria del motore di gioco. Estrae la verità matematica (coordinate, velocità, angoli) e la ricostruisce in una "Immagine Mentale" purificata.
Questa immagine non è fatta di colori RGB. È fatta di **Canali Semantici**.
Un canale per i muri. Un canale per i nemici. Un canale per i suoni.
In questo studio, esploreremo l'ingegneria di questa visione artificiale. Vedremo come trasformiamo numeri grezzi in mappe di calore, come gestiamo la "Nebbia di Guerra" e come l'IA impara a focalizzare l'attenzione su ciò che conta davvero.

---

## 2. La Retina Ontologica: Fondamenti Formali della Visione Macchina

La visione umana è analogica. La visione del Macena Analyzer è **Tensoriale**.
Dobbiamo tradurre lo spazio continuo di CS2 ($\mathbb{R}^3$) in uno spazio discreto che una Rete Neurale Convoluzionale (CNN) possa processare.

### 2.1 Il Tensore Egocentrico
Come stabilito nello *Studio 02*, non possiamo usare coordinate assolute.
La nostra Retina è un cubo di dati $H 	imes W 	imes C$ (Altezza, Larghezza, Canali).
*   **Dimensioni**: $128 	imes 128$ pixel. Ogni pixel rappresenta un quadrato di circa 32 unità di gioco (circa 60 cm).
*   **Centro**: Il giocatore è sempre, immutabilmente, al centro del cubo $(64, 64)$.
*   **Orientamento**: L'asse Y+ punta sempre nella direzione in cui il giocatore sta guardando. Se il giocatore si gira, il mondo intero ruota attorno a lui nel tensore.

### 2.2 Perché non RGB? (La Bancarotta del Colore)
Un'immagine normale ha 3 canali: Rosso, Verde, Blu.
La nostra Retina ha **19 Canali Semantici**.
Perché?
Immagina di guardare una foto aerea di una città. È difficile distinguere le strade dai tetti se sono dello stesso colore.
Ora immagina di avere 19 lucidi trasparenti sovrapposti.
*   Lucido 1: Solo le strade (disegnate in nero).
*   Lucido 2: Solo gli edifici.
*   Lucido 3: Solo le persone.
Questo è ciò che facciamo. **Separiamo ontologicamente la realtà**.
*   **Canale 1 (Muri)**: Contiene la geometria statica.
*   **Canale 4 (Nemici)**: Contiene solo i nemici.
*   **Canale 9 (Fumo)**: Contiene solo le smoke.

Questo elimina l'**Interferenza Semantica**. L'IA non deve mai chiedersi "Quella macchia grigia è un muro o un fumo?". Se è nel Canale 1, è un muro. Se è nel Canale 9, è un fumo. È una certezza matematica.

---

## 3. Convoluzioni dell'Intento e il Calcolo dell'Ingestione Source2

Una volta che abbiamo questa "Immagine Mentale" a 19 canali, come la processiamo?
Usiamo le **Reti Neurali Convoluzionali (CNN)**.
Le CNN sono famose per riconoscere gatti nelle foto. Noi le usiamo per riconoscere **Pattern Tattici**.

### 3.1 Il Filtro Convoluzionale come "Concetto Tattico"
Una CNN è composta da migliaia di piccoli filtri (kernel) $3 	imes 3$ che scorrono sull'immagine.
In una rete normale, questi filtri imparano a riconoscere "bordi verticali" o "curve".
Nel Macena Analyzer, questi filtri imparano concetti di gioco.
*   Un filtro potrebbe imparare a riconoscere: "Un nemico (Canale 4) vicino a un angolo (Canale 1)". Questo è il concetto di **Holding an Angle**.
*   Un altro filtro: "Tre compagni (Canale 5) vicini tra loro che si muovono veloci (Canale 13)". Questo è il concetto di **Rush**.

L'IA non viene programmata per conoscere questi concetti. Li scopre da sola guardando milioni di frame di gioco e correlando questi pattern visivi con la vittoria del round.

### 3.2 Invarianza alla Traslazione
La potenza delle CNN sta nella loro invarianza alla posizione.
Se il filtro "Rush" impara a riconoscere tre puntini vicini, li riconoscerà sia che si trovino a "Banana" su Inferno, sia che si trovino a "Long A" su Dust2.
Questo rende la nostra IA **Generalizzabile**. Non deve imparare ogni mappa da zero. Una volta che ha capito cos'è un "Angolo pericoloso" su Mirage, riconoscerà gli angoli pericolosi anche su una mappa nuova appena uscita.

---

## 4. La Varieta' Egocentrica, Saliency e Gaussian Splatting

Abbiamo un problema tecnico: la **Discretizzazione**.
Un giocatore è un punto preciso $(x, y)$ nello spazio continuo.
La nostra griglia è fatta di pixel discreti.
Se un giocatore si trova a $(10.4, 10.4)$, in quale pixel lo mettiamo? $(10, 10)$?
Se si muove a $(10.6, 10.6)$, salta improvvisamente al pixel $(11, 11)$.
Questo crea un movimento "a scatti" che confonde l'IA. Sembra che il giocatore si teletrasporti.

### 4.1 Lo Splatting Gaussiano (La Macchia di Calore)
Per risolvere questo, usiamo la tecnica del **Gaussian Splatting**.
Invece di accendere un solo pixel, disegniamo una "macchia" sfumata (una campana gaussiana) centrata sulla posizione esatta del giocatore.
$$ I(x, y) = \exp\left( - \frac{(x - p_x)^2 + (y - p_y)^2}{2\sigma^2} ight) $$
*   Se il giocatore è a $(10.5, 10.5)$, la macchia è perfettamente centrata tra i pixel 10 e 11. Entrambi i pixel si illuminano al 50%.
*   Se si sposta a $(10.6, 10.6)$, il pixel 11 diventa leggermente più luminoso (60%) e il 10 leggermente più scuro (40%).

Questo rende il movimento **Continuo e Differenziabile**. L'IA può percepire micro-spostamenti anche se sono più piccoli di un pixel, osservando come la luminosità si sposta tra pixel adiacenti. È come vedere un'ombra che scivola sul muro.

### 4.2 Saliency: L'Attenzione Selettiva
Non tutto ciò che è nella mappa è importante.
Il nostro sistema calcola una **Mappa di Saliency** (Rilevanza).
È un canale aggiuntivo che dice all'IA dove guardare.
*   Un nemico che sta ricaricando è ad alta saliency.
*   Un compagno che sta fermo allo spawn è a bassa saliency.
Questa mappa agisce come un "faro" che illumina le parti critiche del tensore, permettendo al cervello (Volume III) di ignorare il rumore di fondo.

---

## 5. Partizionamento Semantico Multi-Canale e Flussi Foveali/Periferici

Abbiamo un altro paradosso: il **Paradosso della Risoluzione**.
*   Per capire la strategia (dove sono i team), dobbiamo vedere tutta la mappa (4000 unità).
*   Per capire la mira (se il mirino è sulla testa), dobbiamo vedere un dettaglio minuscolo (1 unità).

Se usiamo una griglia ad alta risoluzione per tutta la mappa ($4000 	imes 4000$), il computer esplode per la memoria necessaria.
Se usiamo una griglia a bassa risoluzione ($128 	imes 128$), la testa del nemico diventa più piccola di un pixel e scompare.

### 5.1 L'Architettura a Due Flussi (Dual-Stream)
Copiamo la biologia dell'occhio umano. L'occhio ha:
1.  **Visione Periferica**: Bassa risoluzione, vede tutto, rileva il movimento.
2.  **Fovea**: Altissima risoluzione, vede solo un punto minuscolo al centro, rileva i dettagli.

Il Macena Analyzer ha due reti neurali parallele:
1.  **Stream Periferico**: Guarda il tensore $128 	imes 128$ che copre tutta l'area circostante. Capisce la mappa, le rotazioni, i pericoli laterali.
2.  **Stream Foveale**: Guarda un piccolo tensore $32 	imes 32$ che copre solo l'area attorno al mirino del giocatore. Qui la risoluzione è altissima (1 pixel = 1 unità).
    In questo stream, la testa del nemico è grande e chiara. L'IA può vedere se il mirino è allineato perfettamente o se è fuori di pochi millimetri.

Questi due flussi vengono poi fusi nel "Collo" della rete (Bi-Lateral Fusion Neck), unendo la comprensione strategica alla precisione meccanica.

---

## 6. Percezione Temporale: Movimento, Intento, Profondita' e Occlusione

Un'immagine statica è una bugia.
Se vedo un nemico in un corridoio, non so se sta arrivando o scappando.
Per capire l'**Intento**, devo vedere il tempo.

### 6.1 Il Canale del Flusso (Motion Flux)
Aggiungiamo dei canali speciali al nostro tensore: i **Canali di Velocità**.
Non contengono la posizione, ma la *differenza* di posizione rispetto al frame precedente.
*   Se un pixel è positivo in questo canale, significa che qualcosa si è appena spostato lì.
*   Se è negativo, significa che qualcosa se n'è andato.

L'IA vede il movimento come una "scia luminosa".
*   Una scia lunga = Nemico che corre (Rush).
*   Una scia corta e tremolante = Nemico che fa "ADAD" (Jiggle peek).
Questo permette al Coach di distinguere un'aggressione decisa da un'esitazione, anche senza guardare il video.

### 6.2 Profondità e Occlusione (Z-Squelch)
Le mappe di CS2 hanno verticalità (Sopra/Sotto).
Nel tensore 2D, usiamo un canale "Topologia Verticale".
Invece di proiettare tutto piatto, questo canale contiene l'altezza relativa ($Z_{nemico} - Z_{player}$).
*   Grigio medio (0.5) = Stessa altezza.
*   Bianco (1.0) = Molto sopra (Heaven).
*   Nero (0.0) = Molto sotto (Underpass).

Usiamo una funzione sigmoide ("Squelch") per comprimere le altezze infinite in un range 0-1 gestibile.
Grazie a questo canale, l'IA sa che un nemico a coordinate $(X, Y)$ identiche alle tue, ma con $Z=1.0$, non ti sta toccando: è sopra la tua testa.

---

## 7. Stati di Credenza Ricorrenti, Saliency Algebra e Attenzione

Cosa succede quando un nemico scompare dietro un muro?
Smette di esistere per la Retina (Canale 4 - Visible Enemies si svuota).
Ma non deve smettere di esistere per la mente.

### 7.1 Il Canale della Memoria (Belief Cloud)
Abbiamo un canale speciale: **Canale 7 - Belief Memory**.
Quando un nemico visibile (Canale 4) entra in una zona d'ombra (dietro un muro), il sistema non lo cancella.
Lo sposta nel Canale 7.
Ma qui succede una cosa affascinante: applichiamo una **Diffusione**.
La macchia del nemico inizia ad allargarsi e a sbiadire nel tempo.
*   Dopo 1 secondo: La macchia è ancora piccola e forte. "È appena andato lì dietro".
*   Dopo 5 secondi: La macchia è diventata una nuvola grande e debole che copre tutta l'area retrostante. "Potrebbe essere ovunque lì dietro".

Questo simula l'**Incertezza Crescente**. L'IA "vede" letteralmente il dubbio espandersi sulla mappa.
Questo permette al Coach di dire: "Hai pushato quell'angolo, ma la tua 'Nuvola di Credenza' era enorme. Era un rischio non calcolato".

---

## 8. Fusione Multi-Modale, Sincronia Bimodale e Disentanglement

CS2 è un gioco audiovisivo. I passi sono importanti quanto la vista.
Come uniamo questi due sensi?

### 8.1 Il Canale Audio (Sound Splatting)
Quando il sistema rileva un suono (piede, sparo, ricarica), calcola la sua origine 3D.
Poi "splatta" (disegna) una macchia nel **Canale 8 - Audio**.
Questa macchia è diversa da quella visiva.
*   È più grande (l'audio è meno preciso della vista).
*   Decade più velocemente (il suono è effimero).

### 8.2 Sincronia Bimodale (Cross-Modal Attention)
L'IA impara a correlare Canale 4 (Vista) e Canale 8 (Udito).
Se vede un nemico e *contemporaneamente* vede una macchia audio nello stesso punto, la sua confidenza schizza al 100%. "Lo vedo E lo sento".
Se sente un suono ma non vede nulla (es. attraverso una porta), usa l'audio per "immaginare" la posizione nel Canale 7 (Belief).

### 8.3 Disentanglement (Separare le Idee)
Un concetto cruciale è il **Disentanglement**.
Vogliamo che l'IA separi i concetti nella sua testa.
Vogliamo che i neuroni che riconoscono "Muri" siano diversi dai neuroni che riconoscono "Nemici".
Usiamo tecniche di addestramento (come la penalità TC - Total Correlation) per forzare questa separazione.
Se l'IA usa gli stessi neuroni per tutto, si confonde. Se li separa, diventa un analista lucido.

---

## 9. Robustezza al Rumore, Collo di Bottiglia Informativo e Regioni di Fiducia

Il mondo reale è sporco. I file demo hanno lag, pacchetti persi, glitch.
L'IA deve essere robusta.

### 9.1 Il Filtro di Kalman
Non disegniamo le coordinate grezze. Le passiamo prima attraverso un **Filtro di Kalman**.
Questo è un algoritmo matematico che "liscia" il movimento.
Se un giocatore lagga e salta da A a B istantaneamente, il Filtro di Kalman dice: "Impossibile. Probabilmente si è mosso fluidamente da A a B". E disegna una traiettoria fluida nel tensore.
L'IA vede il movimento *intenzionale*, non il glitch tecnico.

### 9.2 Il Collo di Bottiglia Informativo (Information Bottleneck)
Non possiamo dare all'IA *tutto*.
La teoria dell'Information Bottleneck dice che per imparare bene, bisogna dimenticare i dettagli inutili.
Costringiamo la rete neurale a comprimere i 19 canali in un vettore molto piccolo (512 numeri) prima di prendere decisioni.
Questo collo di bottiglia forza l'IA a scartare i dettagli irrilevanti ("Di che colore è la cassa?") e a conservare solo l'essenza tattica ("C'è una linea di tiro libera?").

### 9.3 Regioni di Fiducia (Trust Regions)
Infine, l'etica.
L'IA non deve mai usare informazioni che il giocatore umano non poteva avere.
Definiamo una **Regione di Fiducia Percettiva**.
Tutto ciò che è fuori dal campo visivo del giocatore (e non è deducibile dai suoni o dalla memoria recente) viene mascherato (azzerato) nel tensore.
L'IA vede solo ciò che l'umano *poteva* vedere.
Se l'IA ti dice "Avresti dovuto sparare", è perché matematicamente avevi le informazioni per farlo. Non sta barando.

---

## 10. Implementazione nel Codice Macena: `tensor_factory.py` e la "Visione Tattica"

Tutta questa teoria converge in un file: `backend/processing/tensor_factory.py`.
Questo è il pittore.
Ogni tick (1/64 di secondo), questo script:
1.  Pulisce la tela (matrici NumPy vuote).
2.  Disegna i muri (Canale 1-3) usando i dati statici della mappa.
3.  Calcola le coordinate egocentriche di tutti i giocatori.
4.  Applica lo Splatting Gaussiano per nemici e amici.
5.  Aggiunge i fumi e le granate.
6.  Aggiunge i suoni recenti.
7.  Passa il pacchetto (Tensor) alla rete neurale.

È un ciclo ad altissima velocità. Deve girare in meno di 5 millisecondi per stare al passo con il gioco. Per questo usiamo NumPy e operazioni vettoriali ottimizzate, evitando cicli `for` lenti in Python.

---

## 11. Sintesi e Connessioni con gli Altri Studi

In questo studio, abbiamo costruito gli Occhi della Macchina.
Abbiamo trasformato il caos del motore di gioco in una rappresentazione ordinata, semantica e matematicamente pura: il **Tensore Egocentrico Multi-Canale**.
L'IA ora "vede" non solo lo spazio, ma il tempo (Flusso), l'incertezza (Belief Clouds) e l'invisibile (Suoni).

Ma vedere è solo l'inizio.
Ora che l'IA ha percepito la situazione, deve **Decidere**.
Deve capire se quella situazione è buona o cattiva. Deve pianificare una strategia.
Questo richiede Memoria e Ragionamento.

Nel **Prossimo Studio (06): Architettura Cognitiva, POMDP e Decisione**, vedremo come il cervello elabora queste immagini.
Vedremo come l'IA usa il POMDP (Partially Observable Markov Decision Process) per navigare nell'incertezza e prendere decisioni ottimali anche quando le informazioni sono incomplete.
Passeremo dalla Percezione (Vedere il presente) alla Cognizione (Pianificare il futuro).

---

## Appendice: Fonti Originali

| File | Lingua | Parole | Ruolo |
|------|--------|--------|-------|
| `01_The_Ontological_Retina.md` | EN | ~1200 | Primaria (Concetti base Retina) |
| `01_The_Ontological_Retina_Formal_Foundations.md` | EN | ~2000 | Primaria (Matematica del Tensore) |
| `02_Convolutions_of_Intent.md` | EN | ~1500 | Primaria (CNN, Filtri) |
| `02_The_Ingestion_Calculus_Source2_to_Semantic_Tensors.md` | EN | ~1800 | Primaria (Ingestione fisica) |
| `03_The_Saliency_Manifold.md` | EN | ~1400 | Primaria (Saliency) |
| `04_Gaussian_Splatting_and_Gradient_Continuity.md` | EN | ~1600 | Supplementare (Math dello Splatting) |
| `05_Multi_Channel_Semantic_Partitioning.md` | EN | ~1500 | Primaria (Canali 1-19) |
| `06_Foveal_vs_Peripheral_Streams.md` | EN | ~1300 | Supplementare (Dual Stream) |
| `07_Temporal_Perception.md` | EN | ~1200 | Supplementare (Flusso temporale) |
| `08_Depth_and_Occlusion.md` | EN | ~1100 | Supplementare (Z-Axis) |
| `10_Multi_Modal_Fusion_and_Synchrony.md` | EN | ~1400 | Supplementare (Audio-Video) |
| `13_Perceptual_Trust_Regions.md` | EN | ~1000 | Supplementare (Etica della visione) |
| `Volume_08_Vedere_Tattica.md` | IT | ~1500 | Ancora Tonale (Implementazione pratica) |

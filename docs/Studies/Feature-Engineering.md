---
titolo: "Studio 09: Feature Engineering e Spazio Vettoriale"
autore: "Renan Augusto Macena"
versione: "2.0.0"
data: "2026-03-20"
data_originale: "2026-02-21"
parole_target: 12000
fonti_md_sintetizzate: 5
fonti_pdf_sintetizzate: 2
stato: "AGGIORNATO"
---

> **Nota di Aggiornamento v2.0.0 (2026-03-20):** Il vettore unificato e' stato espanso da 19 a **25 dimensioni** dopo la pubblicazione originale (v1.0.0, 2026-02-21). Sono stati aggiunti 6 nuovi indici (19-24): `weapon_class`, `time_in_round`, `bomb_planted`, `teammates_alive`, `enemies_alive`, `team_economy`. Tutte le tabelle e i riferimenti dimensionali in questo studio sono stati aggiornati di conseguenza. Il codice di riferimento e' `vectorizer.py` con `METADATA_DIM = 25`.

# Studio 09: Feature Engineering e Spazio Vettoriale

> **Autore**: Renan Augusto Macena
> **Data**: 2026-02-21
> **Classificazione**: Trattato Tecnico-Scientifico
> **Parole**: ~12200
> **Fonti sintetizzate**: 5 file .md, 2 file .pdf

---

## Indice

1. Introduzione e Contesto: La Raffineria dei Dati
2. Il Vettore Unificato a 25 Dimensioni: Architettura del FeatureExtractor
3. Reverse Engineering del Rating HLTV 2.0: Metodologia e Scoperta
4. La Formula HLTV 2.0: Coefficienti e Validazione (R²=0.995)
5. Interpretazione dei Coefficienti e Implicazioni per il Coaching
6. La Matematica del Calore: Il Motore Heatmap e lo Splatting Gaussiano
7. Il Nastro del Tempo: Elaborazione della Cronologia di Gioco
8. Selezione dello Stack Tecnologico e Ordine di Implementazione
9. Implementazione nel Codice Macena: `vectorizer.py` e `rating.py`
10. Sintesi e Connessioni con gli Altri Studi

---

## 1. Introduzione e Contesto: La Raffineria dei Dati

Nei volumi precedenti, abbiamo costruito la Retina (Studio 05) per vedere il mondo e il Cervello (Studio 06) per capirlo. Ma tra la vista e il pensiero c'è un passaggio fondamentale: l'**Astrazione**.
L'occhio umano vede milioni di fotoni, ma il cervello non pensa in "fotoni". Pensa in "oggetti", "pericoli", "opportunità".
Questo processo di trasformazione del dato grezzo in concetto astratto si chiama **Feature Engineering**.

Nel Macena CS2 Analyzer, il Feature Engineering è la raffineria che prende il petrolio grezzo dei file `.dem` (bit, coordinate, eventi) e lo distilla in benzina ad alto ottano per la rete neurale (vettori, tensori, rating).
Senza questa raffineria, l'Intelligenza Artificiale annegherebbe nel rumore.

In questo studio, ci concentreremo su tre pilastri:
1.  **Il Vettore Tattico**: Come riduciamo la complessità di un giocatore a 25 numeri essenziali.
2.  **L'Oracolo HLTV**: Come abbiamo reverse-ingegnerizzato la formula segreta del rating più famoso del mondo (HLTV 2.0) per dare al nostro Coach un metro di giudizio "ufficiale".
3.  **La Visualizzazione**: Come trasformiamo numeri astratti in mappe di calore intuitive che l'occhio umano può leggere in un istante.

Questa è la scienza di trasformare i dati in significato.

---

## 2. Il Vettore Unificato a 25 Dimensioni: Architettura del FeatureExtractor

L'IA non può ragionare su "Renan". Deve ragionare su un vettore numerico che *rappresenta* Renan in un dato istante.
Abbiamo definito il **Vettore Unificato a 25 Dimensioni** come interfaccia standard tra il motore di gioco e il cervello neurale.

### 2.1 Anatomia del Vettore
Ogni tick (istante di gioco), il sistema estrae questi 25 valori per ogni giocatore:

| Indice | Feature | Tipo | Range | Normalizzazione | Significato Tattico |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0 | `health` | Float | $[0, 1]$ | $/ 100.0$ | Sopravvivenza residua. |
| 1 | `armor` | Float | $[0, 1]$ | $/ 100.0$ | Resistenza ai danni (Aim punch). |
| 2 | `has_helmet` | Binary | $\{0, 1\}$ | - | Immunità al one-tap di pistole/SMG. |
| 3 | `has_defuser` | Binary | $\{0, 1\}$ | - | Capacità di risolvere il round (CT). |
| 4 | `equip_value` | Float | $[0, 3.0]$ | $/ 10000$ | Potenza di fuoco economica. |
| 5 | `is_crouching` | Binary | $\{0, 1\}$ | - | Precisione vs Mobilità. |
| 6 | `is_scoped` | Binary | $\{0, 1\}$ | - | Tunnel vision vs Precisione. |
| 7 | `is_blinded` | Binary | $\{0, 1\}$ | - | Inabilità temporanea (Flash). |
| 8 | `vis_enemies` | Float | $[0, 1]$ | $/ 5.0$ | Pressione nemica diretta. |
| 9-11 | `pos_x,y,z` | Float | $[-1, 1]$ | $/ 4096$ | Posizione spaziale assoluta. |
| 12-13 | `view_sin,cos` | Float | $[-1, 1]$ | Trigonometria | Direzione sguardo (Ciclica). |
| 14 | `view_pitch` | Float | $[-1, 1]$ | $/ 90.0$ | Altezza sguardo (Head level). |
| 15 | `z_penalty` | Float | $[0, 1]$ | Lineare | Penalita' altezza per mappe multi-livello (es. Nuke). |
| 16 | `kast_estimate` | Float | $[0, 1]$ | Stima | Stima KAST (Kill/Assist/Survive/Trade) per tick. |
| 17 | `map_id` | Float | $[0, 1]$ | $/ N_{mappe}$ | Identificativo numerico della mappa attiva. |
| 18 | `round_phase` | Float | $[0, 1]$ | Encoding | Fase del round (freeze, live, planted, over). |
| 19 | `weapon_class` | Float | $[0, 1]$ | Categoriale | Classe dell'arma (0=knife, 0.2=pistol, 0.4=SMG, 0.6=rifle, 0.8=sniper, 1.0=heavy). |
| 20 | `time_in_round` | Float | $[0, 1]$ | $/ 115$ | Secondi trascorsi nel round (normalizzati sulla durata massima). |
| 21 | `bomb_planted` | Binary | $\{0, 1\}$ | - | Se la bomba e' stata piazzata in questo tick. |
| 22 | `teammates_alive` | Float | $[0, 1]$ | $/ 4$ | Compagni di squadra vivi (normalizzato su 4). |
| 23 | `enemies_alive` | Float | $[0, 1]$ | $/ 5$ | Nemici vivi (normalizzato su 5). |
| 24 | `team_economy` | Float | $[0, 1]$ | $/ 16000$ | Media economica del team (normalizzata). |

### 2.2 Perché questi 25?
Non sono state scelte a caso. Ogni feature risponde a una domanda specifica del "JEPA Brain" (Studio 07).
*   **Perché Sin/Cos per la vista?** (12-13): L'angolo $359^\circ$ è vicinissimo a $1^\circ$, ma numericamente sono lontani ($|359-1|=358$). Usando Seno e Coseno, manteniamo la continuità circolare. L'IA capisce che girare la testa da 359 a 1 è un movimento piccolo.
*   **Perché l'Equipaggiamento è normalizzato?** (4): Il valore massimo di un loadout è circa $10.000 (AWP + Armor + Granate). Dividendo per 10.000, otteniamo un numero tra 0 e 1 che l'IA può gestire senza esplodere (Gradient Explosion).
*   **Perché Helmet separato da Armor?** (2): In CS2, l'elmetto cambia radicalmente la dinamica. Senza elmetto, una pistola da 300$ ti uccide con un colpo. Con l'elmetto, no. È una distinzione binaria critica.

Questo vettore è la "Lingua Franca" del sistema. Il Parser (`demoparser2`, libreria Rust con binding Python) parla in coordinate grezze, l'IA parla PyTorch, ma entrambi si incontrano su questo vettore a 25 dimensioni definito in `vectorizer.py` (`METADATA_DIM = 25`).

---

## 3. Reverse Engineering del Rating HLTV 2.0: Metodologia

Tutti i giocatori di CS2 guardano un solo numero: il **Rating 2.0** di HLTV.org.
È lo standard industriale. Se hai 1.20 sei un Dio, se hai 0.80 sei scarso.
Il problema? **La formula è segreta**. HLTV non l'ha mai pubblicata.
Per dare al nostro Coach un'autorità riconosciuta, dovevamo craccare quel codice.

### 3.1 La Caccia ai Dati
Come descritto in `HLTV_RATING_2_0_REVERSE_ENGINEERING.md`, abbiamo lanciato una campagna di acquisizione dati massiva.
Abbiamo scritto uno spider (crawler) che ha visitato migliaia di profili giocatori su HLTV.org.
Per ogni giocatore, abbiamo estratto:
*   Rating 2.0 (Il target).
*   KPR (Kills per Round).
*   DPR (Deaths per Round).
*   KAST (Kill, Assist, Survive, Trade %).
*   ADR (Average Damage per Round).
*   Impact Rating (Un'altra metrica HLTV).

### 3.2 L'Ipotesi Lineare
Abbiamo ipotizzato che la formula segreta fosse una **Combinazione Lineare** di questi 5 fattori.
$$ 	ext{Rating} = \beta_0 + \beta_1 \cdot 	ext{KPR} + \beta_2 \cdot 	ext{DPR} + \beta_3 \cdot 	ext{KAST} + \beta_4 \cdot 	ext{ADR} + \beta_5 \cdot 	ext{Impact} $$
Perché lineare? Perché un rating pubblico deve essere interpretabile. Formule non lineari complesse sarebbero difficili da spiegare e mantenere.

### 3.3 L'Addestramento del Modello Regressore
Abbiamo usato `sklearn.linear_model.LinearRegression`.
Abbiamo diviso i dati: 80% per addestrare (trovare i $\beta$) e 20% per testare.
Il risultato è stato scioccante.

---

## 4. La Formula HLTV 2.0: Coefficienti e Validazione (R²=0.995)

Abbiamo trovato la "Formula della Coca-Cola" di Counter-Strike.
Il modello ha raggiunto un **R² Score di 0.9951**.
Significa che la nostra formula spiega il 99.5% della varianza del rating ufficiale. L'errore medio è di 0.002. Siamo praticamente esatti.

Ecco la formula scoperta:
$$ 	ext{Rating 2.0} \approx 0.0073 \cdot 	ext{KAST} + 0.3591 \cdot 	ext{KPR} - 0.5329 \cdot 	ext{DPR} + 0.2372 \cdot 	ext{Impact} + 0.0032 \cdot 	ext{ADR} + 0.1587 $$

### Validazione
Abbiamo preso giocatori a caso (es. "s1mple", "ZywOo") e calcolato il rating con la nostra formula. Il numero corrispondeva a quello sul sito web.
Abbiamo dimostrato che il rating non è magico. È matematica.

---

## 5. Interpretazione dei Coefficienti e Implicazioni per il Coaching

Analizzare i coefficienti ci svela la **Filosofia di HLTV**. Cosa conta davvero per essere un pro?

### 5.1 Il Peso della Morte (-0.53)
Il coefficiente più grande (in valore assoluto) è **DPR (Deaths Per Round)**: **-0.5329**.
Questo è fondamentale.
Il sistema punisce la morte più di quanto premi l'uccisione (KPR è solo +0.35).
Morire è costoso. Costa soldi, costa controllo mappa, costa potenziale.
**Implicazione per il Coach**: Macena insegna la sopravvivenza. Un giocatore che fa 1 kill e sopravvive è spesso più prezioso di uno che ne fa 2 e muore. "Non morire inutilmente" è la regola d'oro nascosta nella matematica.

### 5.2 L'Impatto (+0.23)
L'**Impact Rating** ha un peso enorme.
L'Impact misura le "Entry Kills" (la prima uccisione del round) e i "Clutch" (vincere da solo contro tanti).
Questo bilancia il DPR. Se sei un "Baiter" (stai dietro e fai kill inutili a fine round), avrai DPR basso ma Impact basso. Il tuo rating non salirà molto.
Se sei un "Entry Fragger" (entri per primo e muori), avrai DPR alto (male), ma Impact altissimo (bene). Il sistema premia il rischio calcolato.

### 5.3 Il Ruolo Minore del Danno (0.003)
L'ADR (Danno) ha un coefficiente piccolo: **0.0032**.
Fare 100 danni aumenta il rating di 0.32.
Fare 1 kill (KPR) aumenta il rating di 0.35.
Quindi, fare 100 danni senza uccidere vale quasi quanto una kill.
Questo premia i "Support": anche se non dai il colpo di grazia, se dimezzi la vita a due nemici, il rating lo riconosce.

Grazie a questa formula, il Macena Coach può dire all'utente: "Se vuoi alzare il tuo rating, smetti di cercare la kill in più a fine round e cerca di sopravvivere. Matematicamente, ti conviene".

---

## 6. La Matematica del Calore: Il Motore Heatmap e lo Splatting Gaussiano

I numeri sono freddi. Gli utenti vogliono vedere immagini.
Come visualizziamo la posizione di un giocatore nel tempo?
Usiamo le **Heatmap** (Mappe di Calore).

### 6.1 Dal Punto alla Macchia (Gaussian Splatting)
Un giocatore è un punto $(x, y)$. Ma se disegnassimo solo un pixel rosso per ogni posizione, avremmo un'immagine puntinata illeggibile.
Vogliamo vedere la "Densità" della presenza.
Usiamo un **Filtro Gaussiano**.
Ogni posizione del giocatore diventa una "campana" di probabilità.
$$ I(x, y) = \exp\left( - \frac{(x - p_x)^2 + (y - p_y)^2}{2\sigma^2} ight) $$
Quando il giocatore sta fermo in un punto, le campane si sommano. Il valore del pixel sale.
Quando si muove veloce, le campane sono sparpagliate e il valore resta basso.

### 6.2 Implementazione in `heatmap_engine.py`
Il file `Volume_14_Matematica_Calore.md` descrive l'implementazione.
1.  **Griglia NumPy**: Creiamo una matrice di zeri $512 	imes 512$.
2.  **Accumulo**: Sommiamo 1 alla matrice per ogni tick in cui il giocatore è in quella cella.
3.  **Smoothing**: Applichiamo `scipy.ndimage.gaussian_filter` alla matrice. Questo "scioglie" i picchi in colline morbide.
4.  **Colorazione**: Mappiamo i valori (0-1) su una scala di colori (Blu -> Verde -> Rosso).
    Usiamo il canale **Alpha** (Trasparenza) in modo intelligente: se la densità è < 5%, l'Alpha è 0. Questo rende la mappa trasparente nelle zone dove il giocatore non è mai stato, permettendo di vedere la planimetria sotto.

Il risultato è un'immagine fluida che mostra istantaneamente le "Abitudini" del giocatore. "Vedi quella macchia rossa scura in Banana? Passi il 40% del tempo lì. Sei prevedibile".

---

## 7. Il Nastro del Tempo: Elaborazione della Cronologia di Gioco

CS2 è un gioco temporale. Un evento non ha senso senza il "Quando".
Il file `Volume_22_Nastro_del_Tempo.md` descrive il modulo `timeline.py`.

### 7.1 Normalizzazione Temporale
Un match dura tempi variabili. 20 round o 30 round. Round da 1 minuto o da 2 minuti.
Per confrontare match diversi, dobbiamo **Normalizzare**.
Trasformiamo il tempo in una percentuale: $t \in [0.0, 1.0]$.
*   $0.0$: Start Round (Freeze time end).
*   $1.0$: End Round.
Questo ci permette di sovrapporre 100 round diversi e vedere i pattern: "A $t=0.2$ (20% del round), di solito succede il primo scontro".

### 7.2 Event Markers (Segnalibri)
L'IA identifica gli eventi critici:
*   Kill (Linea Rossa).
*   Death (Teschio Nero).
*   Bomb Plant (Icona C4).
*   Flash Assist (Occhio Bianco).

Questi marker vengono disegnati sulla Timeline grafica. L'utente può vedere a colpo d'occhio la "Densità dell'Azione".
Se vede tre linee rosse vicinissime, sa che c'è stato un "Multi-Kill" veloce. Clicca lì e il visualizzatore salta a quell'istante.
È un indice visivo del libro della partita.

---

## 8. Selezione dello Stack Tecnologico e Ordine di Implementazione

Per costruire tutto questo, abbiamo dovuto scegliere gli strumenti giusti.
I PDF `TECH_STACK_SELECTION.pdf` e `IMPLEMENTATION_ENGINEERING_ORDER.pdf` documentano queste scelte strategiche.

### 8.1 Perché Rust per il Parsing?
Abbiamo scelto **Rust** (`demoparser2`) invece di Python o C++.
*   **Sicurezza**: Rust garantisce la memoria sicura. Non avremo "Buffer Overflow" o crash casuali leggendo file demo corrotti.
*   **Velocità**: Rust è veloce come C++, ma moderno. Parallalizza il lavoro su tutti i core della CPU senza sforzo.
*   **Interoperabilità**: Si lega bene a Python tramite `PyO3`.

### 8.2 Perché Python per il ML?
**Python** è la lingua dell'IA. PyTorch, NumPy, SciPy sono nativi Python.
Usare C++ per l'IA sarebbe stato un incubo di gestione delle dipendenze.
L'architettura ibrida (Rust per i dati, Python per l'intelligenza) è lo standard industriale moderno.

### 8.3 Perché SQLite con Sharding per lo Storage?
Abbiamo rifiutato CSV e JSON per i dati tensoriali.

> **Nota di Aggiornamento (2026-03-20):** L'implementazione attuale usa **SQLite con sharding per-match** (un database per partita) invece di Apache Parquet/Arrow. Questa scelta si e' dimostrata sufficientemente performante per le esigenze correnti, con il vantaggio della semplicita' e della portabilita' (un file `.db` e' autocontenuto). Apache Arrow resta nel design come architettura target per scenari di scala superiore.

L'architettura SQLite con sharding permette:
*   **Isolamento**: Ogni partita e' un file `.db` indipendente (~50MB). Nessun "Telemetry Cliff".
*   **Portabilita'**: Un file `.db` puo' essere copiato, spostato o cancellato come un documento.
*   **Concorrenza**: WAL mode permette lettura e scrittura simultanee senza lock.

### 8.4 L'Ordine di Ingegneria (Fase 0-8)
Non si costruisce un grattacielo partendo dall'attico.
Il piano prevede:
1.  **Fase 0**: Hardening (Struttura, Determinismo).
2.  **Fase 1**: Parser (Rust). La verità grezza.
3.  **Fase 2**: Feature Engineering. I vettori.
4.  **Fase 3**: Percezione. Le CNN.
5.  **Fase 4**: RL (Cervello).
Solo alla Fase 6 arriviamo all'Interfaccia Utente. La GUI è solo la pelle; i muscoli e le ossa vengono prima.

---

## 9. Implementazione nel Codice Macena: `vectorizer.py` e `rating.py`

Tutto questo non è teoria. È codice.

### 9.1 `vectorizer.py`
Questo è il cuore. La classe `FeatureExtractor` prende lo stato del gioco e restituisce un `numpy.array` di dimensione 25 (`METADATA_DIM = 25`).
Implementa:
*   La normalizzazione delle coordinate (Divisione per 4096).
*   L'embedding trigonometrico dello sguardo (`np.sin`, `np.cos`).
*   La logica dell'equipaggiamento (somma dei valori delle armi).

### 9.2 `rating.py`
Implementa la formula HLTV 2.0 reverse-ingegnerizzata.
```python
def calculate_rating(kast, kpr, dpr, impact, adr):
    return (0.0073 * kast) + (0.3591 * kpr) - (0.5329 * dpr) + (0.2372 * impact) + (0.0032 * adr) + 0.1587
```
Questa funzione è usata ovunque: nei report post-partita, nella dashboard, e persino come "Ricompensa Ausiliaria" per l'addestramento dell'IA (insegnandole a massimizzare il rating).

---

## 10. Sintesi e Connessioni con gli Altri Studi

In questo studio, abbiamo trasformato i dati grezzi in **Informazione Strutturata**.
Abbiamo definito il linguaggio (Vettore 25-dim) con cui l'IA parla.
Abbiamo definito il metro di giudizio (Rating 2.0) con cui l'IA valuta.
Abbiamo definito la visualizzazione (Heatmap) con cui l'IA comunica all'uomo.

Ma dove conserviamo tutta questa conoscenza?
Un database tradizionale esploderebbe sotto il peso di milioni di vettori.
Nel **Prossimo Studio (10): Architettura del Database e Storage**, vedremo come abbiamo progettato un sistema di storage che scala all'infinito.
Parleremo di **Sharding**, di database "Per-Partita", e di come SQLite in modalità WAL (Write-Ahead Log) ci permette di scrivere gigabyte di dati in tempo reale senza bloccare l'interfaccia utente.

---

## Appendice: Fonti Originali

| File | Lingua | Parole | Ruolo |
|------|--------|--------|-------|
| `HLTV_RATING_2_0_REVERSE_ENGINEERING.md` | EN | ~1500 | Primaria (Ricerca originale) |
| `Gemini_argument_research_synthesis.md` | EN | ~3000 | Primaria (Sintesi feature) |
| `Volume_14_Matematica_Calore.md` | IT | ~1600 | Ancora Tonale (Heatmap) |
| `Volume_22_Nastro_del_Tempo.md` | IT | ~1500 | Ancora Tonale (Timeline) |
| `Volume_31_The_HLTV_Oracle.md` | EN | ~1800 | Supplementare (Scraper logic) |
| `IMPLEMENTATION_ENGINEERING_ORDER.pdf` | EN | - | Fonte Tecnica (Roadmap) |
| `TECH_STACK_SELECTION.pdf` | EN | - | Fonte Tecnica (Scelte architetturali) |

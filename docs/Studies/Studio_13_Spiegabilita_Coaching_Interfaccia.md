---
titolo: "Studio 13: Spiegabilita', Coaching e Interfaccia Umano-AI"
autore: "Renan Augusto Macena"
versione: "1.0.0"
data: "2026-02-21"
parole_target: 2500
fonti_md_sintetizzate: 7
fonti_pdf_sintetizzate: 1
stato: "COMPLETO"
---

# Studio 13: Spiegabilita', Coaching e Interfaccia Umano-AI

> **Autore**: Renan Augusto Macena
> **Data**: 2026-02-21
> **Classificazione**: Trattato Tecnico (Sintesi UX/AI)
> **Parole**: ~2400
> **Fonti sintetizzate**: 7 file .md, 1 file .pdf

---

## Indice

1. Introduzione: Il Paradosso del "Black Box"
2. Architettura UX: Il Principio della Delega Cognitiva
3. Spiegabilità Strutturale: Causale, Controfattuale, Silenziosa
4. Visual Analytics: La Mappa Vivente e il Rendering Tattico
5. Il Linguaggio del Coach: Generazione NLG e Tono Adattivo
6. Onboarding e Supporto: Il Wizard e il Sistema Documentale
7. Implementazione Tecnica: KivyMD e OpenGL
8. Sintesi Finale

---

## 1. Introduzione: Il Paradosso del "Black Box"

Nei volumi precedenti, abbiamo costruito un "cervello" capace di analizzare CS2 a livello sovrumano. Ma un cervello muto è inutile.
Il problema fondamentale dell'IA applicata allo sport non è *sapere* la verità, ma *comunicarla*.
Un giocatore sotto stress ha una larghezza di banda cognitiva limitata a pochi bit al secondo. Se il Macena Analyzer gli mostrasse i tensori a 19 canali o le matrici di attenzione, sarebbe non solo inutile, ma dannoso.

Lo **Studio 13** affronta la sfida dell'**Interfaccia Umano-AI**.
Non si tratta di "fare una bella grafica". Si tratta di **tradurre** la matematica complessa in intuizioni umane immediate.
L'obiettivo è trasformare l'Output Latente (non verbale, non azionabile) in un Messaggio Pedagogico (causale, tempificato, intenzionale).
Come afferma il protocollo di *Explainability*: "La spiegabilità non è una decorazione post-hoc. Deve essere strutturale."

---

## 2. Architettura UX: Il Principio della Delega Cognitiva

### 2.1 La Gerarchia dell'Informazione
L'architettura UX di Macena (descritta nel Volume 06) rifiuta il massimalismo dei dati.
Adottiamo il **Cognitive Load Accounting**: ogni pixel sullo schermo ha un "costo" per l'attenzione dell'utente.
L'interfaccia è divisa in tre livelli di densità, basati sul contesto temporale del giocatore:

1.  **Layer 1: Flash View (Immediato)**
    *   *Contesto:* Durante il round o nelle pause di 5 secondi.
    *   *Contenuto:* Un singolo sostantivo tattico ("Ruota B") o un colore (Rosso/Verde).
    *   *Obiettivo:* Decisione rapida (< 200ms).

2.  **Layer 2: Strategic Reflection (Analisi)**
    *   *Contesto:* Freeze-time o post-round.
    *   *Contenuto:* Grafici di Vantaggio e sovrapposizioni "Ghost".
    *   *Obiettivo:* Comprensione tattica (< 5s).

3.  **Layer 3: Forensic Audit (Deep Dive)**
    *   *Contesto:* Post-match review.
    *   *Contenuto:* Tensori completi, log sub-tick, grafici radar.
    *   *Obiettivo:* Studio approfondito (Tempo infinito).

### 2.2 Il "Regista" delle Transizioni
Tecnicamente, questo è gestito dallo `MDScreenManager` di Kivy.
L'app non è una serie di finestre statiche, ma un teatro dinamico.
Il passaggio da "Wizard" a "Home" a "Coach View" è gestito da transizioni fluide (`FadeTransition`), che mantengono il senso di continuità spaziale. L'utente non deve mai sentirsi "perso" nella navigazione.

---

## 3. Spiegabilità Strutturale: Causale, Controfattuale, Silenziosa

L'IA non deve limitarsi a dire "Hai sbagliato". Deve spiegare *perché* e *cosa fare*.
Il documento PDF *Explainability & Feedback Generation* definisce tre pilastri:

### 3.1 Attribuzione Causale ($\Delta A_t$)
Definiamo il segnale causale come la differenza tra l'azione scelta e l'azione ottimale:
$$ \Delta A_t = A(s_t, a_t) - \max_{a'} A(s_t, a') $$
Questo misura *quanto* l'errore è stato grave.
Ma per spiegarlo, lo combiniamo con l'**Attenzione** ($\alpha_t$): "Dove stavi guardando quando hai sbagliato?".
Il sistema genera: "Il tuo focus era su [X], ma la minaccia primaria era [Y]. Spostare l'attenzione su [Y] aumenta la sopravvivenza del 30%."

### 3.2 Ragionamento Controfattuale
Questa è l'arma pedagogica più potente.
Generiamo uno stato alternativo $s_t^{cf}$ con un intervento minimo (es. "Aspetta 0.5 secondi").
Poi valutiamo: "Se avessi aspettato 0.5s, avresti vinto il duello."
Questo trasforma il punteggio astratto in una narrazione concreta: "Non hai mirato male; hai solo anticipato troppo il peek."

### 3.3 Il Silenzio come Azione
Un coach che parla sempre è fastidioso.
Il sistema ha una regola aurea: **Il Silenzio è un'Azione Valida.**
Se il gap di vantaggio è piccolo, o se la causalità è incerta ($\sigma > 0.3$), l'IA tace.
Questo preserva l'autorità del sistema. Quando Macena parla, l'utente ascolta, perché sa che il sistema parla solo quando è sicuro e rilevante.

---

## 4. Visual Analytics: La Mappa Vivente e il Rendering Tattico

Le parole non bastano. Il cervello umano elabora le immagini 60.000 volte più velocemente del testo.
Il cuore visivo è la `TacticalMap` (Volume 07 e 26), un motore di rendering OpenGL personalizzato.

### 4.1 Rendering in Tempo Reale
La mappa non è una GIF. È una simulazione fisica renderizzata a 60 FPS.
*   **Granate:** Le smoke si espandono nel tempo (`size = 20 + age * 18`). Le Molotov pulsano (`sin(time)`).
*   **Traiettorie 3D:** Usiamo lo spessore della linea per indicare l'altezza (Z). Una granata alta è spessa e brillante; una bassa è sottile e opaca.
*   **Hitbox:** Per facilitare l'interazione su touch/mouse, le hitbox dei giocatori sono 2.5 volte più grandi del loro sprite visivo (`math.hypot`).

### 4.2 Ghost Mode: Vedere il Futuro
La feature più avanzata è l'Overlay "Ghost".
Il sistema disegna semi-trasparenti (Alpha 0.3) le posizioni predette dall'IA o le alternative ottimali.
L'utente vede il proprio player (solido) e il "Fantasma Pro" (trasparente) che si muove diversamente.
La distanza visiva tra i due è l'errore. Non serve leggere numeri: basta guardare quanto sei lontano dal fantasma.

### 4.3 Heatmap GPU
Per visualizzare il controllo della mappa, usiamo shader OpenGL personalizzati.
Invece di calcolare l'heatmap sulla CPU (lento), passiamo i tensori direttamente alla GPU, che fa il blending dei colori in tempo reale mentre l'utente scorre la timeline.
Questo garantisce fluidità assoluta anche durante l'analisi di round caotici.

---

## 5. Il Linguaggio del Coach: Generazione NLG e Tono Adattivo

Come parla l'IA?
Il modulo NLG (Natural Language Generation) non usa template fissi ("Bravo!"). Usa una generazione condizionata.

### 5.1 Adattamento al Livello (Skill-Conditioned)
La complessità della spiegazione dipende dal livello ($z_{skill}$) dell'utente:
*   **Livello Basso:** Feedback diretti e concreti. "Non correre col coltello."
*   **Livello Medio:** Feedback basati su pattern. "Stai ruotando troppo lentamente su B."
*   **Livello Alto:** Feedback strategici e astratti. "La tua pressione su Mid è insufficiente per forzare il rotate dei CT."
Lo stesso errore genera tre frasi diverse a seconda di chi ascolta.

### 5.2 Struttura "Answer-First"
I messaggi seguono la logica giornalistica:
1.  **Conclusione:** "Stai perdendo i duelli per desync."
2.  **Prova:** "Il tuo click è 4ms in ritardo."
3.  **Azione:** "Premi 'D' più forte."
Se l'utente smette di leggere dopo la prima frase, ha comunque ricevuto l'informazione cruciale.

---

## 6. Onboarding e Supporto: Il Wizard e il Sistema Documentale

Per evitare che l'utente si senta perso davanti a tanta tecnologia, abbiamo costruito sistemi di supporto robusti.

### 6.1 Il Wizard (`wizard_screen.py`)
Al primo avvio, l'utente non vede la dashboard vuota. Vede il Wizard (Volume 25).
*   **Caccia ai Dischi:** Usa le API di Windows (`kernel32.GetLogicalDrives`) per trovare automaticamente le installazioni di Steam su dischi secondari (D:, E:).
*   **Validazione Immediata:** Controlla che la cartella scelta contenga davvero CS2 prima di abilitare il tasto "Avanti".
*   **Configurazione Silenziosa:** Crea le cartelle di sistema (`knowledge`, `models`) in background.

### 6.2 Il Manuale Integrato (`help_system.py`)
Nessuno legge i PDF.
Macena integra un sistema di Help Markdown-based (Volume 29).
I file di documentazione sono nella cartella `data/docs/`. Il sistema li legge, indicizza i titoli e permette una ricerca full-text istantanea (< 1ms).
L'utente preme "?" e cerca "Upload"; il sistema mostra la guida formattata con grassetti e link, senza mai uscire dall'applicazione.

---

## 7. Implementazione Tecnica: KivyMD e OpenGL

La scelta tecnologica di usare **Kivy** (Python) invece di Electron (JavaScript) è stata strategica.
1.  **Integrazione Python:** L'IA è in PyTorch (Python). L'interfaccia è in Kivy (Python). Non c'è bisogno di bridge complessi o API REST locali. I tensori passano dalla memoria dell'IA alla memoria della UI senza serializzazione.
2.  **Performance Grafica:** Kivy usa OpenGL direttamente. Possiamo disegnare 10.000 particelle (per le heatmap) a 60 FPS su un laptop integrato.
3.  **Matplotlib Bridge:** Per i grafici statici (Trend, Radar), usiamo un ponte (`widgets.py`) che renderizza Matplotlib in un buffer di memoria (`io.BytesIO`) e lo proietta come texture Kivy. Questo ci dà la potenza statistica di Pandas con la velocità di render di un videogioco.

---

## 8. Sintesi Finale

L'interfaccia di Macena CS2 Analyzer non è un "volto" messo sopra un "cervello". È il sistema nervoso che connette l'IA all'Umano.
Abbiamo trasformato:
*   Tensori $	o$ Heatmap GPU interattive.
*   Probabilità $	o$ Fantasmi visivi.
*   Logica Causale $	o$ Narrazione pedagogica adattiva.

Il risultato è un sistema che non si limita a calcolare la mossa migliore, ma insegna all'utente *come vederla*.
In questo modo, l'IA non sostituisce l'intelligenza umana, ma la **amplifica**, rispettando i limiti cognitivi e parlando la lingua del gioco, non quella dei dati.

---

## Appendice: Fonti Originali

| File | Tipo | Ruolo |
|------|------|-------|
| `EXPLAINABILITY_E_FEEDBACK_GENERATION.pdf` | PDF | Teoria Pedagogica |
| `Volume_06_Struttura_Frontend.md` | MD | Architettura Kivy |
| `Volume_07_Logica_Dashboard.md` | MD | Logica UI |
| `Volume_24_Grafici_Tattici.md` | MD | Rendering Matplotlib |
| `Volume_25_Benvenuto_Iniziale.md` | MD | Wizard UX |
| `Volume_29_Manuale_di_Bordo.md` | MD | Help System |
| `06_UX_Architecture_and_Cognitive_Load.md` | MD | Teoria UX |
| `Gemini_argument_apps.md` | MD | Audit del Codice |

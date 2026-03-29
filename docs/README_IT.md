# Macena CS2 Analyzer — Indice Documentazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Documento Principale

**[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Riferimento tecnico unificato per l'intero progetto. Contiene: architettura del sistema, audit dello stato attuale, problemi aperti, piano di esecuzione (interventi chirurgici per fasi), roadmap del prodotto, guida alla risoluzione dei problemi e tutte le appendici. **Inizia da qui.**

## Struttura della Directory

```
docs/
├── ENGINEERING_HANDOFF.md          # Riferimento tecnico unificato (inizia qui)
├── QUICKSTART.md                   # Guida rapida (5 minuti)
├── README.md / _IT.md / _PT.md    # Questo indice (3 lingue)
│
├── books/                          # Libri visione (visione e architettura)
│   ├── Book-Coach-1A.md / .pdf     # Nucleo neurale: JEPA, VL-JEPA
│   ├── Book-Coach-1B.md / .pdf     # RAP Coach, sorgenti dati
│   ├─�� Book-Coach-2.md / .pdf      # Servizi, motori di analisi, COPER, database
│   └── Book-Coach-3.md / .pdf      # Logica programma, Qt UI, ingestione, strumenti
│
├── guides/                         # Documentazione per l'utente
│   ├── USER_GUIDE.md               # Guida utente completa (English)
��   ├── USER_GUIDE_IT.md            # Guida utente completa (Italiano)
│   └── USER_GUIDE_PT.md            # Guia do usuário (Português)
│
├── Studies/                        # 17 articoli di ricerca (fondamenti teorici)
│
├── archive/                        # Documenti superati (conservati per riferimento)
│
└── tooling/                        # Utilità per generazione PDF
```

## Ordine di Lettura

1. **[ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md)** — Riferimento tecnico, piano di esecuzione
2. **[QUICKSTART.md](QUICKSTART.md)** — Avvia l'app in 5 minuti
3. **[guides/USER_GUIDE_IT.md](guides/USER_GUIDE_IT.md)** — Guida utente completa
4. **[books/](books/)** — Libri visione (1A -> 1B -> 2 -> 3)
5. **[Studies/](Studies/)** — Articoli di ricerca approfonditi

## Riferimento Rapido

| Necessità | Vai a |
|-----------|-------|
| Cos'è questo progetto? | ENGINEERING_HANDOFF, Sezione 1 |
| Cosa funziona oggi? | ENGINEERING_HANDOFF, Parte II |
| Cosa deve essere corretto? | ENGINEERING_HANDOFF, Parte III |
| Come correggerlo (passi ordinati)? | ENGINEERING_HANDOFF, Parte IV |
| Codici errore | ENGINEERING_HANDOFF, Appendice A |
| Variabili d'ambiente | ENGINEERING_HANDOFF, Appendice C |
| Vettore feature (25-dim) | ENGINEERING_HANDOFF, Appendice E |
| Schema database | ENGINEERING_HANDOFF, Appendice F |
| Risoluzione problemi | ENGINEERING_HANDOFF, Appendice G |
| Roadmap prodotto | ENGINEERING_HANDOFF, Parte V |

## Note

- La directory `archive/` contiene i documenti originali consolidati in ENGINEERING_HANDOFF.md.
- I Libri Visione (books/) descrivono la visione aspirazionale del prodotto. Saranno aggiornati quando il programma sarà stabile.
- Il file `CLAUDE.md` nella root del progetto contiene le direttive ingegneristiche.

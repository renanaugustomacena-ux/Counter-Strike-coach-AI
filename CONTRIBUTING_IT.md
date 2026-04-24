# Contribuire a Macena CS2 Analyzer

Grazie per il tuo interesse nel contribuire. Questo documento descrive come
proporre modifiche, gli standard che il tuo codice deve rispettare e il processo di revisione.

> **[English](CONTRIBUTING.md)** | **[Italiano](CONTRIBUTING_IT.md)** | **[Portugues](CONTRIBUTING_PT.md)**

## Licenza

Inviando una pull request accetti che il tuo contributo sia licenziato sotto
la stessa doppia licenza del progetto (Proprietaria / Apache 2.0). Vedi [LICENSE](LICENSE).

## Per Iniziare

```bash
# 1. Fai fork e clona il repository
git clone https://github.com/<tuo-fork>/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI-main

# 2. Crea e attiva un ambiente virtuale (Python 3.10+)
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 3. Installa le dipendenze
pip install -r requirements.txt

# 4. Installa gli hook pre-commit
pre-commit install

# 5. Verifica che tutto funzioni
python tools/headless_validator.py   # Deve restituire exit 0
python -m pytest Programma_CS2_RENAN/tests/ tests/ --tb=short
```

## Processo di Pull Request

1. **Crea un branch da `main`** — nomina il tuo branch `feature/<argomento>` o `fix/<argomento>`.
2. **Una modifica logica per commit** — mantieni i commit atomici e significativi.
3. **Tutti gli hook pre-commit devono passare** — `pre-commit run --all-files`.
4. **Tutti i test devono passare** — `python -m pytest Programma_CS2_RENAN/tests/ tests/`.
5. **L'headless validator deve passare** — `python tools/headless_validator.py` (exit 0).
6. **La copertura non deve diminuire** — la soglia attuale e 40%, in aumento incrementale.
7. **Apri una PR verso `main`** con una descrizione chiara di cosa e perche.

## Standard di Codice

- **Python 3.10+** con type hint sulle interfacce pubbliche.
- **Black** formatter (lunghezza riga 100). **isort** per l'ordinamento degli import.
- **Nessun numero magico** — estrarre in costanti nominate o config.
- **Logging strutturato** tramite `get_logger("cs2analyzer.<modulo>")`.
- **Nessun fallimento silenzioso** — gli errori devono emergere immediatamente ed esplicitamente.
- **Ogni tick e sacro** — la decimazione dei tick e severamente vietata.
- Docstring solo dove la logica non e ovvia. Nessuna documentazione boilerplate.

## Messaggi di Commit

- Usa messaggi semantici in modo imperativo (es. "Fix stale checkpoint handling").
- Mantieni la prima riga sotto i 72 caratteri.
- Riferisci i numeri degli issue dove applicabile (`Fixes #42`).

## Cosa Accettiamo

- Bug fix con test che provano la correzione.
- Miglioramenti prestazionali con benchmark.
- Nuove funzionalita allineate con la visione del progetto (coaching AI per giocatori CS2).
- Miglioramenti alla documentazione.
- Miglioramenti alla copertura dei test.

## Cosa Non Accettiamo

- Modifiche che rompono test esistenti o l'headless validator.
- Modifiche di formattazione puramente estetiche al di fuori dei file che stai modificando.
- Dipendenze senza chiara giustificazione e verifica compatibilita licenza.
- Codice che introduce vulnerabilita di sicurezza (vedi OWASP Top 10).

## Segnalare Problemi

Usa il tracker [GitHub Issues](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/issues).
Includi:

- Passaggi per riprodurre (o un file demo minimale se applicabile).
- Comportamento atteso vs reale.
- Versione Python, OS e hardware rilevante (modello GPU se relativo al ML).

## Vulnerabilita di Sicurezza

Consulta [SECURITY.md](SECURITY.md) per le linee guida sulla divulgazione responsabile.

## Domande?

Apri una discussione o un issue. Preferiamo la qualita alla velocita.

# SECURITY/ — Documentazione di sicurezza del Macena CS2 Analyzer

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Questa directory è la singola fonte di verità per la postura di sicurezza di `Programma_CS2_RENAN`.
Tutti i documenti qui sono sotto version control, revisionati tramite `CODEOWNERS` e autoritativi.

## Doctrine

La sicurezza è una **proprietà strutturale del sistema**, non un passo successivo. Modelliamo:

```
code → build → artifact → deploy → run
```

con segnali di sicurezza, feedback loop ed enforcement di policy a ogni stadio. Ogni decisione non
banale in questa directory è difesa con **rischio affrontato / rischio residuo / tradeoff / assunzioni**.

## Layout

| File | Scopo |
|---|---|
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | Matrice STRIDE + LINDDUN, DFD, registro degli asset, confini di trust |
| [`CONTROL_CATALOG.md`](CONTROL_CATALOG.md) | Controlli mappati a NIST SSDF, OWASP ASVS L2, CWE Top 25 |
| [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) | Runbook NIST SP 800-61 r2 per IR-01…IR-05 |
| [`SLSA.md`](SLSA.md) | Postura SLSA Build Level 3 e gap analysis |
| [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md) | Variabili d'ambiente: default, sensibilità, validazione |
| [`CVE_LOG.md`](CVE_LOG.md) | Log di triage CVE solo in append |
| [`BOUNDARY_FILES.txt`](BOUNDARY_FILES.txt) | Lista di file ai confini di trust — i PR che toccano qualsiasi riga richiedono security review |
| [`WIPE_RUNBOOK.md`](WIPE_RUNBOOK.md) | Procedura operativa standard per `tools/wipe_for_reingest*.py` |
| `policies/` | Regole policy-as-code consumate da `tools/policy_runner.py` |
| `waivers.yaml` | Eccezioni a tempo limitato alle policy (ogni voce: `risk:`, `expires:`, `owner:`, `justification:`) |

## Come un contributor usa questa directory

1. **Prima di scrivere codice** — leggere `THREAT_MODEL.md` per il confine di trust attraversato dalla modifica.
2. **Mentre si scrive** — `tools/policy_runner.py` gira nel pre-commit (warn-mode inizialmente) e previene il drift.
3. **Prima del merge** — se la modifica tocca un path in `BOUNDARY_FILES.txt`, la CI etichetta il PR
   `security-review-required` e `CODEOWNERS` impone una security review.
4. **Al rilascio** — `goliath.py audit` esegue l'intera catena (SBOM, attestazione SLSA, manifest di integrità, RASP).
5. **Durante un incidente** — `INCIDENT_RESPONSE.md` definisce gli scenari nominati; `goliath.py panic` è il kill-switch.

## Standard di riferimento

- **NIST SP 800-218 v1.1** (Secure Software Development Framework — SSDF)
- **NIST SP 800-53 r5** / **800-161 r1** (gestione del rischio della supply chain)
- **NIST SP 800-61 r2** (computer security incident handling guide)
- **NIST SP 800-63B** (digital identity / authentication)
- **OWASP ASVS 4.0.3 Level 2**
- **OWASP Top 10:2021**
- **CWE Top 25 (2024)**
- **SLSA v1.0** (target Build Level 3)
- **CycloneDX 1.6** SBOM
- **ISO/IEC 27001:2022** Annex A controls A.5–A.8
- **LINDDUN GO (2023)** privacy threats
- **RFC 6749 / 7636 / 7519 / 7517 / 8252** (OAuth + JWT)
- **OpenID 2.0 Final** (Steam login)
- **OpenID Connect Core 1.0** (FaceIt)
- **GDPR Art. 5** (data minimization)

## Contatto

Le segnalazioni di vulnerabilità o di problemi di sicurezza devono raggiungere il proprietario del repository:
**Renan Augusto Macena** — vedere CODEOWNERS per il routing dei contatti.

Per la disclosure coordinata, **non** aprire una issue pubblica. Usare un canale privato.

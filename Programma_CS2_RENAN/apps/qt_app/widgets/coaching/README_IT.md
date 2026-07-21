# `apps/qt_app/widgets/coaching/` — Componenti visivi specifici del coaching

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Package di namespace riservato ai widget visivi specifici del coaching. I quattro widget
specializzati che in precedenza vivevano qui — `AnimatedCounter`, `BeliefThreatGauge`,
`MomentumSparkline` e `UnderglowLabel` — sono stati rimossi nella PR #32 (commit `697bac7`)
nell'ambito della pulizia dei moduli orfani. Il feedback di coaching viene ora renderizzato
direttamente in `screens/coach_screen.py` tramite widget Qt standard e
`widgets/charts/momentum_chart.py`.

## Inventario dei file

| File | Scopo |
|------|-------|
| `__init__.py` | Marker di package (vuoto). |

## Nota storica

I widget rimossi erano componenti opinionati per la modalità coaching, progettati per
creare risonanza emotiva: tween numerici animati, un gauge a due assi belief/threat,
uno spark di momentum K-D inline e un'etichetta con underglow colorato per severità.
Sono stati eliminati perché dipendevano da API interne che sono state consolidate e la
loro funzionalità è stata assorbita nella schermata di coaching e nel package condiviso
dei grafici.

Se in futuro saranno necessari nuovi widget visivi specifici del coaching, questa
directory è la destinazione corretta. Seguire queste convenzioni del design originale:

- Recuperare tutti i colori da `core/design_tokens.py` — nessun valore hex hardcoded.
- Usare i preset di easing di `core/animation.py` per tutte le animazioni.
- Rispettare `prefers-reduced-motion` tramite `core/animation.py:reduced_motion()`.
- Affiancare ogni codifica visiva con un valore testuale per l'accessibilità.
- Impostare `setAccessibleName()` su ogni widget.

## Correlati

- Grafici generici: `apps/qt_app/widgets/charts/README.md`
- Design token: `apps/qt_app/core/design_tokens.py`
- Core delle animazioni: `apps/qt_app/core/animation.py`
- Backend del coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Parent: `apps/qt_app/widgets/README.md`

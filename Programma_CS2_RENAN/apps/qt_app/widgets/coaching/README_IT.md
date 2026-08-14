# `apps/qt_app/widgets/coaching/` — Componenti visivi specifici del coaching

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Widget visivi specifici del coaching. Il package ospita `ChatPanel`, la chat coach
integrata introdotta dal rebuild design-atlas (frame 06/07): bolle messaggio, riga meta
mono di provenienza, stati di disponibilita e riga di input. E ospitata da
`screens/coach_screen.py` — il vecchio dock chat QDockWidget e stato rimosso con il
redesign dei frame 06/07. (Una generazione precedente di widget — `AnimatedCounter`,
`BeliefThreatGauge`, `MomentumSparkline`, `UnderglowLabel` — e stata rimossa nella
PR #32, commit `697bac7`; vedi la nota storica sotto.)

## Inventario dei file

| File | Scopo |
|------|-------|
| `__init__.py` | Export del package (`ChatPanel`). |
| `chat_panel.py` | `ChatPanel` — pannello chat coach integrato ospitato da CoachScreen. |

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

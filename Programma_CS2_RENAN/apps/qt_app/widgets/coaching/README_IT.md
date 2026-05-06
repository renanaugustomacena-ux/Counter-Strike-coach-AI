# `apps/qt_app/widgets/coaching/` — Componenti visivi specifici del coaching

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 3 (Frontend & UX)
> **Skill:** `/frontend-ux-review`

## Scopo

Componenti visivi che esistono specificamente per esprimere lo stato del coaching — gauge di belief / threat, sparkline di momentum, contatori animati ed etichette con underglow. Vivono separati dai widget grafici generici perché il loro vocabolario visivo è opinato per il feedback di coaching, non per analytics generali.

## Inventario dei file

| File | Widget | Scopo |
|------|--------|---------|
| `__init__.py` | — | Marker di package. |
| `animated_counter.py` | `AnimatedCounter` | Valore numerico che effettua il tween fluido tra gli aggiornamenti. Usato per kill, headshot, rating ecc. in modo che le variazioni vengano percepite a livello subliminale senza salti bruschi. |
| `belief_threat_gauge.py` | `BeliefThreatGauge` | Gauge a due assi: barra verticale per la **belief** (confidenza del RAP coach nella decisione corrente), barra orizzontale per la **threat** (livello di minaccia attuale). Pilota l'overlay live del coach durante i replay tattici. |
| `momentum_sparkline.py` | `MomentumSparkline` | Spark di momentum round per round (delta cumulativo K-D) con riempimento verde sopra / rosso sotto. Variante compatta di `widgets/charts/momentum_chart.py` per l'uso inline nelle card di coaching. |
| `underglow_label.py` | `UnderglowLabel` | Etichetta con un sottile bagliore inferiore il cui colore codifica la severità (info / warning / critical). Gli insight di coaching la usano per il titolo. |

## Perché non stanno in `widgets/charts/`

`charts/` contiene primitive analytics che leggono DataFrame e producono visualizzazioni neutre. I widget di coaching qui sono **opinati** — puntano sulla risonanza emotiva (transizioni animate, metafore di gauge, segnalazione tramite underglow) perché la modalità coaching è pensata per essere *sentita*, non solo letta. Mescolarli con primitive analytics neutre confonde il vocabolario visivo.

## Convenzioni

### Timing delle animazioni

Tutto ciò che si muove usa i preset di easing di `core/animation.py` — mai `QPropertyAnimation` con curve scritte a mano. Mantiene il timing coerente in tutta l'app.

### Colori di severità

`UnderglowLabel` legge i colori di severità da `core/design_tokens.py`:

| Severità | Token | Tono |
|----------|-------|------|
| `info` | `accent.info` | Blu / ciano calmo |
| `warning` | `accent.warning` | Ambra |
| `critical` | `accent.critical` | Rosso, leggera pulsazione alla comparsa |

### Accessibilità

- Il gauge belief / threat è abbinato a valori testuali in modo che gli utenti con percezione cromatica ridotta possano comunque interpretare lo stato.
- I contatori animati rispettano `prefers-reduced-motion` — quando l'utente disabilita le animazioni nelle impostazioni del SO, le transizioni scattano invece di interpolare.
- `setAccessibleName()` è impostato su ogni widget così gli screen reader possono annunciare i valori del gauge.

## Integrazione

```
apps/qt_app/screens/coach_screen.py
    +-- BeliefThreatGauge (overlay live del coach)
    +-- AnimatedCounter   (punteggio del round)
    +-- UnderglowLabel    (titolo dell'insight)

apps/qt_app/screens/match_detail_screen.py
    +-- MomentumSparkline (striscia di momentum per round)
    +-- AnimatedCounter   (aggiornamenti delle stat di partita)
```

## Da non fare

- Non collocare qui grafici generici e neutri rispetto al tema. Vanno in `widgets/charts/`.
- Non incorporare i colori di severità nel codice del widget. Recuperarli da `design_tokens.py`.
- Non animare senza controllare `prefers-reduced-motion` (interrogare via `core/animation.py:reduced_motion()`).

## Correlati

- Grafici generici: `apps/qt_app/widgets/charts/README.md`
- Design token: `apps/qt_app/core/design_tokens.py`
- Core delle animazioni: `apps/qt_app/core/animation.py`
- Backend del coaching: `Programma_CS2_RENAN/backend/coaching/README.md`
- Parent: `apps/qt_app/widgets/README.md`

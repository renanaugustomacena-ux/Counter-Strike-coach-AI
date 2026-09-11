> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Session Runs & Dati di Esecuzione

Questa directory è la posizione di output predefinita per i log eventi TensorBoard generati durante l'addestramento dei modelli dal coach IA di Counter-Strike. Non contiene codice; qui vengono scritti a runtime solo dati di telemetria di addestramento rigenerabili.

## Panoramica Tecnica

Il percorso viene risolto come `RUNS_DIR = USER_DATA_ROOT/runs` in `core/config.py` (creato automaticamente all'import). Quando `BRAIN_DATA_ROOT` è configurato, le run vengono scritte sotto quella radice invece della directory nel repository. Il `TensorBoardCallback` (`backend/nn/tensorboard_callback.py`) — Layer 2 del Coach Introspection Observatory — mantiene `RUNS_DIR/coach_training` come valore predefinito del costruttore, ma il punto di ingresso dell'addestramento (`run_full_training_cycle.py`) delimita ogni run tramite `build_run_dir(model_type)`, che restituisce `RUNS_DIR/<model_type>/<timestamp UTC>-<tag dispositivo>` (es. `runs/jepa/20260817T142530Z-cpu`). Il tag dispositivo proviene da `resolve_device_tag()` (`cpu` / `cuda` / `rocm`), così una smoke run Windows su CPU non viene mai confusa con una vera run Linux ROCm nella dashboard.

## Componenti Chiave

- **File Evento TensorBoard**: Scalari (loss, learning rate, sparsità), istogrammi e layout scalari personalizzati registrati per epoca durante l'addestramento.
- **Scalari MaturityObservatory**: L'observatory condivide lo stesso `SummaryWriter`, quindi i suoi segnali di conviction/maturità finiscono nella stessa logdir.
- **Sottodirectory Per-Run**: Ogni invocazione di addestramento ottiene la propria directory `<model_type>/<timestamp UTC>-<tag dispositivo>`, mantenendo gli esperimenti separabili nella UI di TensorBoard invece di accumularsi in una singola cartella.

## Utilizzo

1. **Addestramento**: `python run_full_training_cycle.py` registra il callback TensorBoard per impostazione predefinita; `--tb-logdir` sovrascrive la destinazione (il valore predefinito `None` indica una directory con scope dalla run tramite `build_run_dir()`; un percorso esplicito disabilita lo scope della run e scrive direttamente lì) e `--no-tensorboard` disabilita il logging. Il tag dispositivo (`-cpu`, `-cuda`, `-rocm`) rende le run da configurazioni hardware diverse immediatamente distinguibili nella dashboard.
2. **Visualizzazione**: Lanciare `tensorboard --logdir Programma_CS2_RENAN/runs` e aprire l'URL stampato per ispezionare le curve di addestramento.
3. **Pulizia**: I file evento sono artefatti volatili e rigenerabili — le vecchie directory di run possono essere eliminate liberamente per risparmiare spazio su disco.

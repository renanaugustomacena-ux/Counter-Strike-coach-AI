# CORREZIONE DEL NUCLEO NEURALE — PARTE III
## Istruzioni tecniche precise per correggere il codebase

Autore del progetto: Renan Augusto Macena. Data: 2026-09-05. Repository: `Counter-Strike-coach-AI`, branch `docs/refresh-2026-09-04`, HEAD `62cd2f1`. Percorsi relativi a `Programma_CS2_RENAN/` salvo dove indicato.

Questa Parte traduce la diagnosi (Parte I) e la matematica (Parte II) in modifiche al codice: **per ogni intervento** il file, la funzione, le righe di riferimento oggi, il cambiamento esatto, il test che lo verifica e il criterio di accettazione. L'ordine segue i passi 0–9 della Parte I §8. Le nuove scoperte emerse dalle misure della Parte II sono registrate in §12.

---

## Indice

- 0. Regole di lavoro
- 1. Passo 0 · Congelare il training attuale
- 2. Passo 1 · Contratto dati v2 e allineamento dei nomi
- 3. Passo 1b · Esportazione degli episodi
- 4. Passi 2–3 · Pacchetto `backend/nn/jepa_v2/`
- 5. Passo 4 · Telemetria, sonde, benchmark contro il legacy
- 6. Passo 5 · Un solo trainer, un solo entry point
- 7. Passo 6 · Coach v2 sopra i latenti (world model, sorpresa, Chronovisor v2, memoria)
- 8. Passo 7 · Le altre reti e i motori di analisi
- 9. Passo 8 · Collegamento al `CoachingService` e all'interfaccia
- 10. Test: aggiungere, modificare, ritirare
- 11. Ordine di esecuzione e criteri di accettazione
- 12. Scoperte nuove di questa Parte (registro)

---

## 0. Regole di lavoro

1. **Branch**: `feat/neural-core-v2` da `main` dopo il merge di `docs/refresh-2026-09-04`. Commit convenzionali (`feat:`, `fix:`, `refactor:`, `test:`), autore unico, nessun trailer.
2. **Il database non si tocca da codice di training/analisi.** Tutte le letture per export e verifica usano `sqlite3.connect(f"file:{db}?mode=ro", uri=True)` e `PRAGMA query_only=1` (già così in `tools/verify_math_claims.py`). Le sole scritture ammesse sono quelle dell'ingestione e di `assign_dataset_splits`, eseguite dai loro entry point.
3. **Nessuna rimozione senza sostituto verde.** Ogni componente ritirato ha prima il suo sostituto con test; i file legacy si spostano in `backend/nn/legacy/` (con `__init__.py` che emette `DeprecationWarning`) prima di essere cancellati in un passo successivo.
4. **Contratto prima del codice.** Lo schema `cs2_v2` (passo 1) e il sidecar `schema_version = "v2"` si scrivono e si testano prima del primo training.
5. **Ogni numero mostrato all'utente è calibrato o è un conteggio.** Nessuna costante di confidenza, nessun numero generato dall'LLM.
6. **Il piano C++ `latentis` resta fermo** finché il passo 4 (benchmark) non è verde in Python (Parte I App. F).

---

## 1. Passo 0 · Congelare il training attuale

### 1.1 Bloccare il path di produzione della JEPA legacy

**File** `backend/nn/training_orchestrator.py`, `TrainingOrchestrator.__init__` (righe 47–140).
**Cambiamento.** Dopo la validazione di `model_type`, aggiungere:

```python
_LEGACY_TRAIN_TYPES = {"jepa", "vl-jepa", "rap", "rap-lite"}
if model_type in _LEGACY_TRAIN_TYPES and not get_setting("ALLOW_LEGACY_NEURAL_TRAINING", default=False):
    raise RuntimeError(
        f"{model_type!r} training is frozen (CORREZIONE_NUCLEO_NEURALE Parte I §4-5): "
        "the objective is degenerate at B=1 / 1-tick horizon. Use model_type='jepa_v2' "
        "or set ALLOW_LEGACY_NEURAL_TRAINING=True for A/B baselines only."
    )
```
Registrare `ALLOW_LEGACY_NEURAL_TRAINING: False` in `core/config.py` accanto a `USE_JEPA_MODEL` (riga 236).
**Perché.** Impedisce che un `train.sh` o un cron riprenda a produrre checkpoint con la matematica sbagliata mentre si costruisce la v2. La deroga esplicita serve al benchmark del passo 4 (baseline A).
**Test.** `tests/test_training_orchestrator_logic.py::test_legacy_training_frozen_by_default` (costruzione con `model_type="jepa"` alza `RuntimeError`; con il setting a `True` non alza).

### 1.2 `run_full_training_cycle.py`: nessun default implicito

**File** `run_full_training_cycle.py` (radice del pacchetto). **Cambiamento.** `--model-type` obbligatorio (`required=True`) con scelte `{"jepa_v2", "coach_v2", "jepa", "rap", "all"}`; `"all"` significa `jepa_v2 → coach_v2` (non più `jepa → rap`). Rimuovere il blocco `del orchestrator_jepa; gc.collect(); torch.cuda.empty_cache()` (righe 242–247): il coach v2 **carica** l'encoder JEPA congelato, non deve distruggerlo; la memoria GPU si libera con `model.cpu()` dopo aver salvato il checkpoint.

### 1.3 Split assegnati prima di qualunque training

**Fatto verificato (2026-09-05, sola lettura):** `playermatchstats.dataset_split` vale `UNASSIGNED` per tutte le 1.031 righe; `is_pro = 1` per tutte. Nessun training può quindi prelevare righe `TRAIN`.
**File** `backend/nn/coach_manager.py`, `run_full_cycle` (riga 293; la chiamata `self.assign_dataset_splits()` alla riga 320 esiste) e `run_jepa_pretraining` (riga 588). **Cambiamento.** Chiamare `assign_dataset_splits()` anche in `run_jepa_pretraining` e nel futuro `run_jepa_v2_pretraining`, e far fallire il training (non avvisare) se dopo l'assegnazione `train_rows == 0` (`data_quality.run_pre_training_quality_check` lo riporta già come `issues`).
**Nota**: l'assegnazione scrive sul monolite; va eseguita **solo** quando l'ingestione non è in corso (oggi: 22 task in coda).

---

## 2. Passo 1 · Contratto dati v2 e allineamento dei nomi

### 2.1 Schema `cs2_v2` tipizzato

**Nuovo file** `backend/processing/feature_engineering/schema_v2.py`.

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple
import hashlib, json

class Kind(str, Enum):
    SCALAR = "scalar"; BINARY = "binary"; ANGULAR = "angular"; CATEGORICAL = "categorical"; COUNT = "count"

@dataclass(frozen=True)
class Field:
    name: str
    kind: Kind
    unit: str
    scale: float = 1.0          # divisore per SCALAR/COUNT (numerico → [~-1, ~1])
    vocab: Tuple[str, ...] = () # solo CATEGORICAL
    source_column: str = ""     # colonna di PlayerTickState / derivazione
    derived_from_future: bool = False

@dataclass(frozen=True)
class FeatureSchema:
    schema_id: str
    version: int
    fields: Tuple[Field, ...]

    def numeric(self) -> Tuple[Field, ...]:
        return tuple(f for f in self.fields if f.kind != Kind.CATEGORICAL)
    def categorical(self) -> Tuple[Field, ...]:
        return tuple(f for f in self.fields if f.kind == Kind.CATEGORICAL)
    def fingerprint(self) -> str:
        canon = json.dumps([f.__dict__ | {"kind": f.kind.value} for f in self.fields], sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canon.encode()).hexdigest()

CS2_V2 = FeatureSchema(
    schema_id="cs2_v2", version=1,
    fields=(
        Field("health", Kind.SCALAR, "hp", 100.0, source_column="health"),
        Field("armor", Kind.SCALAR, "ap", 100.0, source_column="armor"),
        Field("has_helmet", Kind.BINARY, "", source_column="has_helmet"),
        Field("has_defuser", Kind.BINARY, "", source_column="has_defuser"),
        Field("equipment_value", Kind.SCALAR, "usd", 10000.0, source_column="equipment_value"),
        Field("is_crouching", Kind.BINARY, "", source_column="is_crouching"),
        Field("is_scoped", Kind.BINARY, "", source_column="is_scoped"),
        Field("is_blinded", Kind.BINARY, "", source_column="is_blinded"),
        Field("enemies_visible", Kind.COUNT, "players", 5.0, source_column="enemies_visible"),
        Field("pos_x", Kind.SCALAR, "u", 4096.0, source_column="pos_x"),
        Field("pos_y", Kind.SCALAR, "u", 4096.0, source_column="pos_y"),
        Field("pos_z", Kind.SCALAR, "u", 1024.0, source_column="pos_z"),
        Field("view_yaw_sin", Kind.ANGULAR, "rad", source_column="view_x"),
        Field("view_yaw_cos", Kind.ANGULAR, "rad", source_column="view_x"),
        Field("view_pitch", Kind.SCALAR, "deg", 90.0, source_column="view_y"),
        Field("z_penalty", Kind.SCALAR, "", 1.0, source_column="pos_z+map_name"),
        Field("time_in_round", Kind.SCALAR, "s", 115.0, source_column="time_in_round"),
        Field("bomb_planted", Kind.BINARY, "", source_column="bomb_planted"),
        Field("teammates_alive", Kind.COUNT, "players", 4.0, source_column="teammates_alive"),
        Field("enemies_alive", Kind.COUNT, "players", 5.0, source_column="enemies_alive"),
        Field("team_economy", Kind.SCALAR, "usd", 16000.0, source_column="team_economy"),
        Field("map_id", Kind.CATEGORICAL, "", vocab=("de_ancient","de_anubis","de_dust2","de_inferno","de_mirage","de_nuke","de_overpass","de_train","de_vertigo","other"), source_column="map_name"),
        Field("weapon_class", Kind.CATEGORICAL, "", vocab=("none","knife","pistol","smg","rifle","sniper","heavy","grenade"), source_column="active_weapon"),
        Field("side", Kind.CATEGORICAL, "", vocab=("CT","T","unknown"), source_column="roundstats.side"),
    ),
)
```

Regole: (a) `kast_estimate` **rimosso** (identicamente 0, Parte II §12.2); (b) `round_phase` **rimosso** (funzione deterministica di `equipment_value`, verificato su tutti i valori); (c) `map_id` e `weapon_class` diventano **categoriali con vocabolario**, non ordinali; (d) `side` è nuovo (oggi non è nel vettore e il modello non può distinguere CT da T); (e) ogni divisore è **dato**, non codice — `_fill_context_features` (vectorizer.py:409-441) ha `/115.0`, `/4.0`, `/5.0`, `/16000.0` hardcoded (D4): in v2 vengono dallo schema. Dimensione numerica 21; embedding categoriali `4 + 4 + 2 = 10` → 31 ingressi al tokenizer (Parte I §7.2).

### 2.2 Estrazione v2 accanto alla v1

**File** `backend/processing/feature_engineering/vectorizer.py`. **Aggiungere** (senza toccare `extract`/`extract_batch`, che restano per i checkpoint legacy e per `tools/verify_math_claims.py`):

```python
def extract_v2(tick_data, map_name: Optional[str] = None, side: Optional[str] = None,
               schema: FeatureSchema = CS2_V2) -> tuple[np.ndarray, np.ndarray]:
    """→ (x_num float32[21], x_cat int64[3]) nell'ordine di schema.numeric()/categorical()."""
```
Implementazione: riusare i filler esistenti per i 21 numerici (stesse formule: `_fill_vitals_movement`, `_fill_awareness_position_view`, `_fill_z_penalty`, `_fill_context_features` con i divisori letti da `schema`), poi `x_cat = [vocab_index(map_name), weapon_class_index(active_weapon), side_index(side)]` con `other/none/unknown` come fallback **loggato** (mai silenzioso). `extract_batch_v2` = versione vettoriale con snapshot della config come in `extract_batch` (R4-14-03).
**Rimappatura senza perdita** `remap_v1_to_v2(x25: np.ndarray, map_name, active_weapon, side)`: copia le 21 numeriche dagli indici v1 `[0..15, 20..24]`, ricava le categoriali dalle sorgenti (non dall'hash). Test: su 100.000 tick reali `extract_v2(...)[0] == remap_v1_to_v2(extract(...))[0]` entro $10^{-6}$.

### 2.3 Sidecar e persistenza

**File** `backend/nn/persistence.py`. `_META_SCHEMA_VERSION = "v1"` (riga 22) resta per i checkpoint legacy; i checkpoint v2 scrivono `{"schema_version": "v2", "schema_id": "cs2_v2", "schema_fingerprint": CS2_V2.fingerprint(), "numeric_dim": 21, "categorical_vocab_sizes": [10, 8, 3]}` via `extra_meta`, e `_validate_loaded_meta` (righe 146–182) confronta `schema_fingerprint` con quello corrente quando `schema_version == "v2"`; a mismatch → `StaleCheckpointError`. Aggiungere `SchemaMismatchError(StaleCheckpointError)` per distinguere nel log.
**Test** `tests/test_persistence_stale_checkpoint.py::test_v2_fingerprint_mismatch_raises`.

### 2.4 D8 (nuovo) · Nomi giocatore non allineati fra tabelle

**Fatto verificato (sola lettura, 2026-09-05).** `roundstats.player_name` è normalizzato (`strip().lower()`, `run_ingestion.py:797`): 105 nomi distinti, nessuno con spazi. `playermatchstats.player_name` conserva la grafia originale (109 nomi, uno con spazio iniziale); `playertickstate.player_name` idem (es. `' saffee'` con spazio iniziale; `'mezii'`). Di conseguenza 47 nomi di `roundstats` **non trovano corrispondenza esatta** in `playermatchstats` (`art` vs `Art`, `jame` vs `Jame`, …), e nel campione di `verify_math_claims.py` 18 coppie su 48 hanno restituito zero tick per lo stesso motivo. Ogni join etichetta↔tick fatto per uguaglianza esatta perde quasi metà dei giocatori.
**Cambiamento (codice, nessuna scrittura al DB da qui).** Introdurre `normalize_player_name(s) = s.strip().casefold()` in `backend/storage/naming.py` e usarla: (a) in `processing/round_stats_builder.py` (riga 1005, già normalizzato — lasciare), (b) in `run_ingestion.py` alla scrittura di `PlayerTickState` (bulk insert riga 1701) e di `PlayerMatchStats` (riga 120) **per le nuove ingestioni**, (c) in ogni join di training/export (`tools/export_episodes.py`, `coach_manager._fetch_round_stats_for_batch`, `training_orchestrator._fetch_round_stats_for_batch`, `verify_math_claims.fetch_ticks`) come `lower(trim(player_name)) = ?`.
**Migrazione dei dati esistenti (richiede approvazione: scrive sul monolite, da fare a ingestione ferma, con backup):**
```sql
UPDATE playertickstate  SET player_name = lower(trim(player_name)) WHERE player_name <> lower(trim(player_name));
UPDATE playermatchstats SET player_name = lower(trim(player_name)) WHERE player_name <> lower(trim(player_name));
```
Prima: `SELECT count(*) FROM playertickstate WHERE player_name <> lower(trim(player_name))` per dimensionare (query lunga: usa l'indice `ix_pts_player_demo` solo parzialmente).
**Test** `tests/test_naming.py` (idempotenza, spazi, maiuscole, Unicode casefold) e un test di integrazione sul DB di test che verifica che ogni `roundstats.player_name` abbia almeno una riga in `playertickstate` dopo normalizzazione.

### 2.5 D1–D6 residui

- **D1** `kast_estimate`: fuori dallo schema v2 (2.1). Nel v1 resta per compatibilità dei checkpoint archiviati.
- **D2** `map_id` hash: sostituito dal vocabolario (2.1). `_fill_round_metadata` (vectorizer.py:356-381) resta solo nel path v1.
- **D3** `round_phase`: fuori dallo schema v2. Se serve come *etichetta* di analisi, calcolarla da `equipment_value` a valle, mai come input.
- **D4** normalizzatori: divisori nello schema (2.1); `HeuristicConfig` (base_features.py:18-58) acquista `time_in_round_max=115.0`, `teammates_alive_max=4.0`, `enemies_alive_max=5.0`, `team_economy_max=16000.0` per il path v1, così che il sidecar li registri.
- **D5** due vocabolari da 25: `MATCH_AGGREGATE_FEATURES` (coach_manager.py) e `FEATURE_NAMES` non devono più condividere `METADATA_DIM`; introdurre `MATCH_AGGREGATE_DIM = len(MATCH_AGGREGATE_FEATURES)` e usare `CS2_V2` per i tick. `factory.get_model` (righe 44–110) legge le dimensioni dallo schema, non dalla costante.
- **D6** stato globale nell'estrattore (`_batch_clamp_local`, contatori, `configure()` di classe): nel path v2 l'estrattore è un'istanza `FeatureExtractorV2(schema, quality_policy)` con statistiche proprie; il path v1 non cambia.

---

## 3. Passo 1b · Esportazione degli episodi

**Nuovo file** `tools/export_episodes.py` (sola lettura sul DB, come `verify_math_claims.py`).

**Definizione di episodio.** Sequenza contigua di tick di una tripla `(demo_name, player_name, round_number)` con `tick` strettamente consecutivi, lunghezza ≥ 64 tick (1 s). Il vincolo D-22 ("mai attraverso il round") è così **strutturale**, non un filtro a posteriori.

**Query.** Per ogni demo (da `roundstats`), per ogni giocatore normalizzato (§2.4): `SELECT <colonne di PTS_COLS> FROM playertickstate WHERE demo_name=? AND lower(trim(player_name))=? ORDER BY tick` (indice `ix_pts_player_demo`); segmentazione in Python su `round_number` e su `tick[i+1]-tick[i] == 1`.

**Layout su disco** (`safetensors`, già nel venv 0.8.0), una shard per demo in `$DATA/cs2_v2/<split>/<demo_name>.safetensors`:

| tensore | forma | dtype | contenuto |
|---|---|---|---|
| `x_num` | `[N, 21]` | f32 | `extract_v2` numerici |
| `x_cat` | `[N, 3]` | i64 | indici vocabolario (map, weapon, side) |
| `raw_pos_view` | `[N, 5]` | f32 | pos_x, pos_y, pos_z, yaw°, pitch° (per ghost e azioni) |
| `actions` | `[N, 5]` | f32 | `[Δpos_xyz/8, Δyaw/180, Δpitch/90]` verso il tick successivo; ultimo tick di episodio = 0 e maschera |
| `health`, `enemies_visible` | `[N]` | f32 | per etichette future |
| `episode_offsets` | `[E+1]` | i64 | CSR |
| `episode_meta` | `[E, 4]` | i64 | round_number, tick_start, tick_end, player_idx |
| `labels_round` | `[E, 8]` | f32 | `round_won, kills, deaths, kast, round_rating, opening_kill, opening_death, side_is_ct` da `roundstats` (join normalizzato) |

`manifest.json` per split: schema fingerprint, lista demo, `match_date` e `match_date_source` (avviso OI-2 se `ingestion_clock`), conteggi, versione demoparser, sha256 di ogni shard, seme, data UTC.

**Split.** Per demo, cronologico 70/15/15 sull'ordine di `match_date` (stesso criterio di `assign_dataset_splits`, `coach_manager.py:397-510`). Nessun giocatore/round in due split (garantito perché la shard è la demo). L'export legge `dataset_split` da `playermatchstats` se già assegnato, altrimenti applica lo stesso ordinamento e lo scrive **solo nel manifest** (mai nel DB).

**Azioni.** $a_t = (\Delta x, \Delta y, \Delta z)/8,\ \Delta\text{yaw}/180,\ \Delta\text{pitch}/90$ con Δyaw riportato in $(-180, 180]$. Con $f_{tick}=64$ e velocità massima ≈ 250 u/s, $|\Delta x|\le 3{,}9$ u/tick, quindi $/8$ mantiene $|a|<1$ con margine per i salti.

**Test** `tests/test_export_episodes.py`: episodi non attraversano round; `tick` consecutivi; `episode_offsets` monotono; `actions` coerenti con `raw_pos_view` (ricostruzione); etichette presenti per ≥ 95% degli episodi (la soglia misura il join dei nomi, §2.4); round-trip `safetensors`.

**Dimensioni attese.** 147,5 M tick × (21·4 + 3·8 + 5·4 + 5·4 + 2·4) B ≈ 22 GB per l'export completo; export `medium` (≤ 8 episodi per giocatore-partita) ≈ 3 GB; `sample_2k` (2.000 episodi) ≈ 6 MB da versionare per CI.

---

## 4. Passi 2–3 · Pacchetto `backend/nn/jepa_v2/`

Struttura (tutti file nuovi; nessuna dipendenza da `jepa_model.py`):

```
backend/nn/jepa_v2/
  __init__.py
  config.py        JepaV2Config (dataclass frozen, tutti i numeri della Parte I §7)
  sigreg.py        SIGReg batch e temporale (Epps–Pulley, le-wm)
  blocks.py        RMSNorm, SwiGLU, RoPE, CausalSelfAttention(QK-norm), TransformerBlock, FiLM
  tokenizer.py     Conv1d patch (P=8) + embedding categoriali + concatenazione
  encoder.py       EncoderV2 (tokenizer → 4 blocchi causali) con `taps`
  projector.py     Projector 128→256→64 (Guillotine)
  predictor.py     PredictorV2 (2 blocchi causali + FiLM orizzonte)
  losses.py        L_next, L_multi, assemblaggio con i pesi
  sampler.py       finestre di 48 token da episodi CSR, batch B=128
  trainer.py       AdamW + warmup/coseno PER PASSO, bf16, clip 1.0, checkpoint + sidecar v2
  telemetry.py     RankMe/std/cos/SIGReg/probe su probe-batch fisso; regole di abort
  probes.py        sonde lineari con GroupKFold per demo + temperature scaling + ECE
```

### 4.1 `config.py`

```python
@dataclass(frozen=True)
class JepaV2Config:
    schema_id: str = "cs2_v2"
    patch_ticks: int = 8            # 125 ms a 64 tick/s (Parte II §12.2: R²_id(8)=0.974)
    tokens_per_window: int = 48     # 384 tick = 6 s
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    ffn_mult: int = 4               # SwiGLU con d_ff ridotto a 2/3·4·d
    cat_embed_dims: tuple = (4, 4, 2)  # map_id, weapon_class, side
    proj_hidden: int = 256
    proj_out: int = 64
    predictor_layers: int = 2
    horizons: tuple = (1, 4, 16)    # token → 0,125 / 0,5 / 2 s
    w_next: float = 1.0
    w_multi: float = 0.5
    lambda_sigreg_temporal: float = 2.5   # LeNEPA (CauKer): 2.5; PTB-XL: 20 — da sweep {1, 2.5, 5, 20}
    lambda_sigreg_batch: float = 0.1      # LeWM
    sigreg_taps: tuple = (0, -1)          # layer 0 (uscita tokenizer) e ultimo (LeNEPA Tab. 5)
    sigreg_num_proj: int = 1024
    sigreg_knots: int = 17
    sigreg_t_max: float = 3.0
    batch_size: int = 128
    steps: int = 20000
    lr_max: float = 1e-4
    lr_min: float = 1e-6
    warmup_steps: int = 1000
    weight_decay: float = 0.05
    betas: tuple = (0.9, 0.99)
    grad_clip: float = 1.0
    dtype: str = "bf16"
    seed: int = 0
    probe_every: int = 500
    abort_rankme_below: float = 8.0
    abort_std_min_below: float = 1e-3
```

### 4.2 `sigreg.py` (identico a le-wm `module.py`; test di parità con Parte I App. A.1)

```python
class SIGReg(nn.Module):
    def __init__(self, knots=17, num_proj=1024, t_max=3.0):
        super().__init__()
        t = torch.linspace(0, t_max, knots); dt = t_max / (knots - 1)
        weights = torch.full((knots,), 2 * dt); weights[[0, -1]] = dt
        window = torch.exp(-t.square() / 2.0)
        self.register_buffer("t", t); self.register_buffer("phi", window)
        self.register_buffer("weights", weights * window); self.num_proj = num_proj

    def forward(self, proj: torch.Tensor, generator=None) -> torch.Tensor:
        # proj: (..., N, D) — l'asse -2 è il CAMPIONE del test
        A = torch.randn(proj.size(-1), self.num_proj, device=proj.device, dtype=proj.dtype, generator=generator)
        A = A / A.norm(p=2, dim=0, keepdim=True)
        x_t = (proj @ A).unsqueeze(-1) * self.t                      # (..., N, M, K)
        err = (x_t.cos().mean(-3) - self.phi).square() + x_t.sin().mean(-3).square()
        return ((err @ self.weights) * proj.size(-2)).mean()

def sigreg_batch(u: torch.Tensor, reg: SIGReg, g=None) -> torch.Tensor:
    """u: (B, T, d) → per ogni t il batch è il campione. LeWM Alg. 3."""
    return reg(u.transpose(0, 1), g)          # (T, B, d): asse -2 = B

def sigreg_temporal(u: torch.Tensor, reg: SIGReg, g=None) -> torch.Tensor:
    """u: (B, T, d) → per ogni campione i T token sono il campione. LeNEPA eq. 2."""
    return reg(u, g)                          # asse -2 = T
```
Il generatore va seminato con `global_step` (LeJEPA Alg. 1) così che le direzioni cambino a ogni passo e siano riproducibili. `proj` deve essere l'uscita del **projector**, mai di una LayerNorm (Parte II §2.3.3).

### 4.3 `blocks.py` (formule in Parte II §10)

- `RMSNorm(d, eps=1e-6)`: `x * rsqrt(mean(x²)+eps) * g`.
- `SwiGLU(d, d_ff)`: `W2(silu(xW) * (xV))`, senza bias, `d_ff = int(2/3 * ffn_mult * d)` arrotondato a multiplo di 8.
- `rope(q, k, positions)`: rotazione per coppie con $\theta_i = 10000^{-2(i-1)/d_{head}}$; posizioni = indice del token nella finestra (relativo).
- `CausalSelfAttention(d, n_heads, qk_norm=True)`: `q,k,v = Linear(d, 3d, bias=False)`; `q = LN(q); k = LN(k)` (QK-norm); RoPE; `scaled_dot_product_attention(..., is_causal=True)`; out-proj senza bias.
- `TransformerBlock`: pre-norma `x = x + Attn(RMSNorm(x)); x = x + SwiGLU(RMSNorm(x))`.
- `FiLM(cond_dim, d)`: `γ, β = Linear(cond_dim, 2d)(c)`; `y = (1+γ) ⊙ x + β`, con i pesi finali inizializzati a zero (parte come identità, come adaLN-Zero).

### 4.4 `tokenizer.py`

Input `x_num: (B, L, 21)`, `x_cat: (B, L, 3)` con `L = T·P` tick. `Conv1d(21, d_num, kernel=P, stride=P)` su `x_num.transpose(1,2)` → `(B, T, d_num)`; per le categoriali, embedding per tick (`Embedding(V_i, e_i)`) poi **media sui P tick del patch** (le categoriali sono costanti nel round: media = valore); concatenazione `(B, T, d_num + 10)` → `Linear(·, d_model)`. Nessuna posizione assoluta (RoPE nell'attenzione).

### 4.5 `encoder.py`, `projector.py`, `predictor.py`

```python
class EncoderV2(nn.Module):
    def forward(self, x_num, x_cat, return_taps=False):
        h0 = self.tokenizer(x_num, x_cat)                 # (B, T, d)
        taps = [h0]; h = h0
        for blk in self.blocks: h = blk(h); taps.append(h)
        h = self.final_norm(h)                           # RMSNorm finale: SOLO per le teste, non per SIGReg
        return (h, taps) if return_taps else h

class Projector(nn.Module):   # d → 256 → 64, GELU, senza norma finale
class PredictorV2(nn.Module):
    """ẑ_{t+h} = FiLM_h(Blocks(z_{≤t})): 2 blocchi causali, FiLM sull'embedding dell'orizzonte."""
    def forward(self, z, horizon_idx): ...
```
La rappresentazione servita al coach è `taps[k]` con `k` scelto dalla curva delle sonde per layer (LeNEPA §5: i layer intermedi battono l'ultimo); di default `k = n_layers // 2`.

### 4.6 `losses.py`

Con `z = encoder(x)` `(B,T,d)`, `taps`, `p = projector`:
```python
def jepa_v2_loss(z, taps, pred_fn, proj, cfg, sigreg, step):
    g = torch.Generator(device=z.device).manual_seed(cfg.seed * 1_000_003 + step)
    u = proj(z)                                                  # (B, T, 64)
    # L_next (LeNEPA eq. 1): predizione del token successivo, senza stop-gradient
    zhat1 = pred_fn(z, horizon_idx=0)                            # (B, T, d)
    L_next = F.mse_loss(proj(zhat1[:, :-1]), u[:, 1:])
    # L_multi: orizzonti 4 e 16 token (CF-JEPA/HEPA multi-horizon)
    L_multi = 0.0
    for hi, h in enumerate(cfg.horizons[1:], start=1):
        zh = pred_fn(z, horizon_idx=hi)
        L_multi = L_multi + F.mse_loss(proj(zh[:, :-h]), u[:, h:])
    L_multi = L_multi / max(1, len(cfg.horizons) - 1)
    # SIGReg temporale sui taps scelti (LeNEPA eq. 2), batch su u (LeWM)
    L_sig_T = sum(sigreg_temporal(proj(taps[k]), sigreg, g) for k in cfg.sigreg_taps) / len(cfg.sigreg_taps)
    L_sig_B = sigreg_batch(u, sigreg, g)
    loss = cfg.w_next * L_next + cfg.w_multi * L_multi + cfg.lambda_sigreg_temporal * L_sig_T + cfg.lambda_sigreg_batch * L_sig_B
    return loss, {"L_next": L_next, "L_multi": L_multi, "sig_T": L_sig_T, "sig_B": L_sig_B}
```
Nessuna EMA, nessuno stop-gradient, nessun negativo, nessuna coda (Parte II §2). Il `proj` è condiviso fra predizione e bersaglio (LeNEPA Fig. 1).

### 4.7 `sampler.py`

Dagli shard `safetensors`: per epoca, per ogni episodio di lunghezza $\ge 384$ tick, campionare offset uniformi (seme per epoca) e produrre finestre `(x_num[384,21], x_cat[384,3])`; batch `B=128`; il set di validazione usa offset fissi (seme 0). Mai padding (J-5). Se un episodio è più corto di 384 tick, si salta (statistica loggata): con il campione della Parte II l'80% dei round dura > 30 s, quindi > 1.900 tick.

### 4.8 `trainer.py`

- `optimizer = AdamW(params, lr=cfg.lr_max, betas=cfg.betas, weight_decay=cfg.weight_decay)`; **scheduler per passo**: `lr(step) = lr_min + 0.5(lr_max−lr_min)(1+cos(π·(step−warmup)/(steps−warmup)))` dopo warmup lineare; `scheduler.step()` **dentro** il passo dell'ottimizzatore (oggi `training_orchestrator._run_epoch_loop` lo chiama per epoca, righe 388–400: con 1 epoca il coseno non parte mai).
- `torch.autocast(device_type="cuda", dtype=torch.bfloat16)` (già la politica di `nn/config.py:165-176`); niente `GradScaler` (serve solo a fp16; `jepa_trainer.py:130-132` lo usa con fp16 — J13).
- `clip_grad_norm_(1.0)`; seme globale; `torch.backends.cudnn` disabilitato su HIP come oggi (`nn/config.py:132`).
- Checkpoint ogni `probe_every` passi: `state_dict` dell'encoder **senza** predictor/projector nel file `jepa_v2_encoder.pt` (+ `jepa_v2_full.pt` per il resume), sidecar v2 (§2.3) con `extra = {step, best_probe_auroc, rankme, sigreg, lr, seed, git_sha}`.
- Nessuna `EmbeddingCollapseDetector` sulla varianza: le regole di abort sono in `telemetry.py`.

### 4.9 `telemetry.py`

Ogni `probe_every` passi, su un **probe-batch fisso** di 4.096 finestre di validazione: `compute_collapse_metrics` (riuso di `collapse_metrics.py`) su `taps[k].mean(1)` e su `u`; valore SIGReg batch/temporale; `S_straight` (Parte II §6.3); AUROC delle sonde (§5.2). Log in `metrics.csv` + TensorBoard via `TensorBoardCallback` esistente. **Abort** (exit ≠ 0, checkpoint marcato `aborted`) se `effective_rank < abort_rankme_below` o `std_min < abort_std_min_below` per due letture consecutive.

---

## 5. Passo 4 · Telemetria, sonde, benchmark contro il legacy

### 5.1 `probes.py`

```python
def fit_linear_probe(Z_train, y_train, Z_val, y_val, groups_train) -> ProbeResult:
    """LogisticRegression (C=1, class_weight='balanced', max_iter=3000) su StandardScaler;
    AUROC su val; temperature T fittata per NLL su val (Guo 2017); ECE con 15 bin su val."""
```
Etichette **esterne** per finestra (dal manifest/labels dell'export, mai dall'input): `round_won` (round dell'ultimo token), `death_within_2s` (salute → 0 nei 128 tick successivi all'ultimo token), `enemy_visible_within_2s`, `opening_death` (episodio), `side`. `GroupKFold(5)` con gruppo = demo. Le stesse funzioni servono in `verify_math_claims.py` (già implementate lì con la stessa firma logica) e nel benchmark.

### 5.2 `tools/benchmark_jepa_v2_vs_legacy.py`

Contendenti sullo **stesso** set di finestre (manifest con seme 0; 40 k train / 8 k val / 8 k test):
- **A** = ricetta di produzione riprodotta con `B = 128` (encoder `JEPAEncoder` per tick + media, `JEPAPredictor`, EMA coseno con copia iniziale, InfoNCE con τ appreso e coda, VICReg 0,01) — richiede `ALLOW_LEGACY_NEURAL_TRAINING=True` (§1.1);
- **B** = `jepa_v2` con `JepaV2Config()`;
- **R** = feature grezze (media di finestra) — il baseline che **oggi** batte l'encoder addestrato (Parte II §12.5).

Metriche su encoder congelato (test): RankMe (8 k finestre), AUROC/ECE delle sonde di 5.1, kNN-20, $R^2$ di $\Delta$pos a 0,5 s e 2 s dai latenti. **Superamento** (Parte I §7.7): B ≥ A **e B ≥ R** su tutte le AUROC; RankMe(B) ≥ 2·RankMe(A); media ± dev. su 3 semi. Rapporto in `docs/benchmarks/jepa_v2_vs_legacy.md` con i numeri di `verify_math_claims_2026-09-05.json` come riga "legacy archiviato".

### 5.3 Criterio di uscita del passo 4

`round_won` AUROC(B) > 0,760 e `death_within_2s` AUROC(B) > 0,838 (i valori delle feature grezze misurati in Parte II §12.5) con intervallo di confidenza che non include il baseline grezzo; RankMe(B) ≥ 64 (contro 66 del legacy su 256 dimensioni, ma qui su $d=128$: il criterio equivalente è RankMe/d ≥ 0,5).

---

## 6. Passo 5 · Un solo trainer, un solo entry point

### 6.1 `factory.py`

Aggiungere `TYPE_JEPA_V2 = "jepa_v2"` e `TYPE_COACH_V2 = "coach_v2"` (righe 36–41); in `get_model` (44–110) il ramo `jepa_v2` costruisce `EncoderV2(CS2_V2, JepaV2Config())` e legge `numeric_dim`/vocabolari dallo schema; `get_checkpoint_name("jepa_v2") == "jepa_v2_encoder"`. I tipi `jepa`, `vl-jepa`, `rap`, `rap-lite` restano istanziabili (baseline A e checkpoint archiviati) ma emettono `DeprecationWarning`.

### 6.2 `training_orchestrator.py`

- `_fetch_batches` (625–660) e `_prepare_tensor_batch` (820–935): il ramo `("jepa","vl-jepa")` costruisce **una** finestra per batch (`context = features[:10]`, `target = features[10:11]`, negativi 5 + coda). Per `jepa_v2` l'orchestratore **non** prepara tensori: delega a `jepa_v2.sampler` (shard `safetensors`) e a `jepa_v2.trainer.train_step`, e usa `_run_epoch_loop` solo per callback/early-stopping su AUROC delle sonde (non sulla loss).
- Rimuovere la chiamata per-epoca `trainer.scheduler.step()` (388–400) quando il trainer espone `steps_per_epoch`: lo schedule è per passo (§4.8).
- `_checkpoint_extra_meta` (456–476): per `jepa_v2` scrive `head_trained=False` (non esiste testa) e `probes_calibrated` (§9.1).
- Il gate di collasso D-13 (340–377) resta solo per i tipi legacy.

### 6.3 Codice morto da ritirare (in `backend/nn/legacy/` al primo passaggio, cancellazione al passo 9)

| file | simboli | motivo |
|---|---|---|
| `jepa_train.py` | `train_jepa_pretrain`, `train_jepa_finetune`, `_jepa_pretrain_*`, `JEPAPretrainDataset` | secondo path di training (J7); `train_jepa_finetune` alza per design (Parte I J8) |
| `jepa_trainer.py` | `train_epoch`, `check_val_drift`, `retrain_if_needed`, `encode_raw_negatives`, `_augment_with_moco_queue` | mai chiamati in produzione / no-op (J12, J14) |
| `training_config.py` | `JEPATrainingConfig` | mai importata (J12) |
| `jepa_model.py` | `forward_selective`, `ConceptLabeler`, `VLJEPACoachingModel.forward_vl`, `_sparse_moe`, LSTM/esperti/gate | testa mai allenata (J8), leakage (J9) |
| `train.py` | `_train_jepa_self_supervised` (ramo `config_name == TYPE_JEPA`) | terzo path di training |

`load_jepa_model`/`save_jepa_model` (jepa_train.py:727-830) restano per leggere i checkpoint archiviati nel benchmark.

### 6.4 `train.sh` e documentazione

`train.sh` invoca `run_full_training_cycle.py --model-type jepa_v2` e poi `--model-type coach_v2`; la sezione "gate" del suo help deve descrivere i gate che **esistono** (abort su RankMe/std, criterio AUROC), non quelli del path legacy (D7). `jepa.md` riceve un'intestazione che rimanda alle tre Parti e marca le sezioni 9–10 come storiche.

---

## 7. Passo 6 · Coach v2 sopra i latenti

**Nuovo pacchetto** `backend/nn/coach_v2/` che **consuma** `EncoderV2` congelato (checkpoint `jepa_v2_encoder`). Il RAP attuale (`experimental/rap_coach/`) resta come legacy finché ogni sua funzione non ha il sostituto verde; le correzioni minime al RAP, se lo si vuole tenere allenabile per confronto, sono in 7.7.

### 7.1 `world_model.py`

`PredictorAC(d=128, n_layers=2, action_dim=5)`: blocchi causali con **adaLN-Zero** (Parte II §6.1) condizionati su `a_t` (embedding `Linear(5, d)` dell'azione del token = media delle azioni dei suoi 8 tick da `actions` dell'export); loss `‖ẑ_{t+1} − z_{t+1}‖²` in spazio projector + `0.1·SIGReg_batch` (LeWM); encoder **congelato** (si allena solo il predittore: 2–3 M parametri, ore su RX 9070 XT). Rollout `rollout(z0, a_{1:H})` autoregressivo; `plan_cem(z0, z_goal, H=5, N=300, iters=10, K=30, bounds)` (LeWM App. B) con azioni limitate a $[-1,1]^5$ e ripianificazione MPC.

### 7.2 `surprise.py`

```python
class SurpriseTracker:
    """s_h(t) = ||proj(ẑ_{t+h}) − proj(z_{t+h})||²; z-score per orizzonte con Welford (Parte II §7.2)."""
    def update(self, s: float, h: int) -> float: ...   # restituisce ζ_h
    def state_dict(self) -> dict: ...                  # μ_h, M2_h, n_h per persistenza nel sidecar
```
Le statistiche di riferimento si stimano sul set di validazione a fine training e si salvano accanto al checkpoint del world model (`surprise_stats.json`); a inferenza si usa anche una finestra scorrevole per partita (adattamento al giocatore).

### 7.3 `chronovisor_v2.py` (modifica di `rap/chronovisor_scanner.py`)

- `ScaleConfig` (righe 60–90) esprime `window_ticks`, `lag` come **secondi** (`window_s`, `lag_s`) e li converte con il `tick_rate` risolto (`training_orchestrator._resolve_tick_rate` esiste già, riga 1313; a default 64 dopo la misura T1 se il metadato manca, con log).
- Ingresso: `ζ_h(t)` per token (o il valore di una sonda), non `advice_probs`.
- Lisciamento Savitzky–Golay (`scipy.signal.savgol_filter`, scipy 1.17 nel venv; finestra 5 token = 0,6 s, grado 2) prima delle differenze a lag.
- Soglie in unità di `ζ` (2,0 / 2,5 / 3,0 per micro/standard/macro) calibrate sul train; dedup fra scale con gap minimo 1 s.
- Mantenere `CriticalMoment`, `ScanResult` e i test `tests/verify_chronovisor_logic.py` adattando le unità.

### 7.4 `episodic_memory.py`

kNN (FAISS `IndexFlatIP` su latenti L2-normalizzati, come `knowledge/vector_index.py`) di token con `ζ > τ_w` (τ_w = 2,0), voce `{latente, demo, tick, episodio, ζ, esito back-fill}`; capacità 200 k; eviction "meno sorprendente"; persistenza su disco. Sostituisce Hopfield/LTC (R6) per il recupero di "situazioni simili di un pro".

### 7.5 `value_heads.py`

Testa HEPA (Parte II §8): predittore congelato → `λ_Δt = σ(wᵀĥ_Δt + b)`, `p(t,Δt) = 1 − Π(1−λ_j)`, BCE pesata `w₊ = N_neg/N_pos`, orizzonti densi 1..16 token (2 s); eventi: morte, perdita del round, primo contatto. Metrica h-AUROC per orizzonte; calibrazione per orizzonte con temperature scaling (§9). Sostituisce `DeathProbabilityEstimator` e `WinProbabilityNN` nel coaching (Parte II §11.4–11.5).

### 7.6 `attribution.py` e `communication_v2.py`

- Attribuzione: gradiente della sonda rispetto alle 21 feature numeriche attraverso il tokenizer (saliency integrata su 16 passi) + controfattuale per campo (azzerare `enemies_visible`, ridurre `equipment_value`, spostare la posizione di 1 s lungo l'azione pianificata) → Δ probabilità della sonda. Rango pieno per costruzione (una colonna per campo). Sostituisce `RAPPedagogy.diagnose` (pedagogy.py:60-95: tre colonne proporzionali a `‖Δpos‖`).
- Comunicazione: registri per `ζ` calibrato (assertivo < 0,35, con riserva 0,35–0,65, astensione > 0,65 — soglie iniziali da Mouchon, da ricalibrare); `confidence` = probabilità calibrata della sonda (mai costante: `run_ingestion.py:225` passa `confidence=0.85` letterale — da rimuovere); topic dal campo con attribuzione massima (non `argmax % 3`, communication.py:109-112). Template esistenti per tier riusati.

### 7.7 Correzioni minime al RAP legacy (solo se resta allenabile per confronto)

| file:righe | oggi | cambiamento |
|---|---|---|
| `rap/model.py:201-205` `compute_sparsity_loss` | `w·H(gate)` minimizzata (premia il collasso) | `α·N·Σ_i f_i P_i` con `f_i` = frazione argmax, `P_i` = media softmax, `α = 1e-2` (Switch eq. 4); test: gate uniforme → loss = α, gate one-hot → loss ≈ α·N |
| `rap/trainer.py:33,67` | `MSELoss(advice_probs, target_strat)` | `CrossEntropyLoss(logits, target_idx)`; `RAPStrategy.forward` restituisce anche i logit; rimuovere `ROLE_ROTATION` dal vocabolario o dargli una regola raggiungibile in `training_orchestrator._classify_tactical_role` (1711–1773) |
| `coach_manager._fetch_rap_windows` (909) `window_size=96`, `seq_len=32` → 3 finestre | BatchNorm su 3 campioni (Parte II Prop. 5) | `n_windows ≥ 32` o sostituire BatchNorm con GroupNorm/RMSNorm in `rap/perception.py` |
| `rap/communication.py:86,109-123` | `confidence < 0.7` su una costante 0,85; `topic = argmax % 3` | confidenza dalla sonda calibrata; topic dall'attribuzione |
| `nn/maturity_observatory.py:155,211` | `_last_belief_batch`, `strategy.superposition` inesistenti | il modello espone `telemetry() -> dict` con chiavi dichiarate; l'Observatory alza `KeyError` su chiave assente |
| `run_full_training_cycle.py:242-247` | JEPA distrutta prima del RAP | il RAP/coach v2 riceve `encoder` come argomento |

---

## 8. Passo 7 · Le altre reti e i motori di analisi (Parte II §11)

| componente | file:righe | cambiamento | test |
|---|---|---|---|
| `AdvancedCoachNN` / `train_nn` | `nn/model.py:28-172`, `nn/train.py:15-64`, `coach_manager._train_phase:1064`, `_calculate_deltas:1109`, `nn/evaluate.py`, `coaching/nn_refinement.py` | Ritirare dalla catena: `run_full_cycle` non chiama più `_train_phase`; `apply_nn_refinement` riceve `{}` (nessun aggiustamento) finché non esiste una sonda calibrata; il "delta rispetto al pro" resta `pro_baseline.calculate_deviations` | `test_coach_manager_flows.py`: nessun checkpoint `latest.pt` legacy prodotto; `test_nn_refinement_noop` |
| `NeuralRoleHead` | `nn/role_head.py:307-327` | Test di coerenza semantica fra le 5 feature di inferenza e le colonne di `Ext_PlayerPlaystyle` (stesse definizioni: `tapd`, `oap`, `podt`); esporre `probs` calibrate (temperature su val) | `test_feature_kast_roles.py::test_role_features_match_training_columns` |
| `WinProbabilityTrainerNN` | `nn/win_probability_trainer.py` | Rimuovere (nessun chiamante produce il DataFrame; 9-dim incompatibile con il predittore) | rimozione del test associato |
| `WinProbabilityNN` + euristiche | `analysis/win_probability.py:178-338` | `WinProbabilityPredictor.predict` restituisce `None` quando `_checkpoint_loaded is False` (oggi: sigmoide casuale + clamp); rimuovere i clamp `max(p,0.85)`/`min(p,0.15)`/`±0.10`/`0.65/0.35` (281–312) — i vincoli deterministici (0 vivi → 0, 0 nemici → 1) restano; la probabilità di round viene da `coach_v2.value_heads` (7.5) con Platt/temperature su VAL (`PlattScaler` esistente, 118–168) | `test_win_probability_refuses_untrained` |
| `ExpectiminimaxSearch` / `BlindSpotDetector` | `analysis/game_tree.py`, `analysis/blind_spots.py` | Non chiamati dal `CoachingService` finché `_evaluate_leaf` non ha un predittore addestrato; `_apply_action` marcato "regole a mano" nel docstring; `BlindSpotDetector.detect` richiede `action_taken` reale (non inferito) o esce con `ScanResult` vuoto-successo | `test_game_tree.py`: `suggest_strategy` alza `RuntimeError("predictor untrained")` |
| `DeathProbabilityEstimator` | `analysis/belief_model.py:76-137` | Nuovo `tools/fit_belief_logit.py`: regressione logistica su (threat, weapon, armor, exposure) → morte entro 2 s dalle etichette dell'export; coefficienti salvati in `CalibrationSnapshot`; `estimate()` li legge; `estimate_with_uncertainty` rinominata `estimate_with_input_perturbation` (non è MC-dropout) | `test_belief_model_extended.py::test_coefficients_from_snapshot` |
| `EntropyAnalyzer` | `analysis/entropy_analysis.py:79-145` | Griglia **fissa** per mappa in coordinate mondo (bounding box da `core/spatial_data.py`, cella 128 u); `_MAX_DELTA` sostituito da $\log_2(\text{celle occupate}_{max})$ misurato; entropia della credenza (posizioni possibili da `PlayerKnowledge`), non dei punti osservati | `test_entropy_extended.py::test_fixed_grid_translation_invariance` |
| `MomentumTracker` | `analysis/momentum.py` | `tools/fit_momentum.py`: regressione logistica `round_won ~ streak + economia` su `roundstats`; se il coefficiente dello streak non è significativo (p > 0,05), `predict_performance_adjustment` restituisce `base_rating` e la UI etichetta "narrativo" | test sui coefficienti |
| `DeceptionAnalyzer` | `analysis/deception_index.py:26-40` | Etichettare come punteggio; test AUROC pro vs amateur come da commento P8-04 | — |
| `HybridCoachingEngine` | `coaching/hybrid_engine.py:512-533` | Rinominare `confidence` → `priority_score` nell'API e nella UI; `knowledge_effectiveness` da `usage_count/100` a tasso di successo Beta-binomiale (8.1) | `test_hybrid_priority_not_probability` |
| `ExperienceBank` | `knowledge/experience_bank.py:360-420, 1027-1100, 1116-1200` | Rinominare `mu_skill/sigma_skill` → `eff_alpha/eff_beta` (contatori Beta-binomiali), media `α/(α+β)`, intervallo di credibilità al 90% da `scipy.stats.beta`; `REPLAY_GATE` sul quantile inferiore; rimuovere la dicitura "TrueSkill" | `test_experience_bank_beta` |
| `KnowledgeEmbedder` | `knowledge/rag_knowledge.py:151-185` | Fallback hash 100-d → `RuntimeError` in produzione (`get_setting("ALLOW_HASH_EMBEDDINGS")` per i test) | `test_rag_refuses_hash_fallback` |
| `LLMService` | `services/llm_service.py:27-49, 173, 227, 299` | Modello pinnato `gemma4:e2b@sha256:<digest>` (da `ollama show`), `temperature 0.2` per il renderer; il prompt riceve solo strutture calcolate (sorpresa, sonde, z-score, tick) con istruzione "non introdurre numeri" | `test_llm_prompt_has_no_free_numbers` |
| `TickFeatureDriftMonitor` | `processing/validation/drift.py:153-232` | Estendere allo schema v2 (21 numerici + frequenze categoriali) | esteso |
| `eval_harness.py` | `tools/eval_harness.py` | Sezioni nuove: RankMe/SIGReg dell'encoder v2, AUROC/ECE per orizzonte, Precision@K del Chronovisor | — |

### 8.1 Beta-binomiale per l'efficacia di un consiglio (sostituisce l'EMA chiamata TrueSkill)

Per ogni esperienza: `α = 1 + successi`, `β = 1 + fallimenti` (prior uniforme); media $\alpha/(\alpha+\beta)$; quantile inferiore al 5% `scipy.stats.beta.ppf(0.05, α, β)`; il gate di replay usa il quantile (l'incertezza si riduce **con l'evidenza**, non con un fattore 0,95 fisso). Migrazione: colonne nuove nella tabella `coachingexperience` (`eff_alpha`, `eff_beta`, default 1,1) via Alembic; le vecchie `mu_skill/sigma_skill` restano finché la UI non migra.

---

## 9. Passo 8 · Collegamento al `CoachingService` e all'interfaccia

### 9.1 `coaching/jepa_insight_adapter.py` (v2)

Oggi (righe 1–280): mappa le 10 uscite sigmoidi della testa mai allenata a messaggi per feature, con gate F-0029 su `extra.head_trained`. Sostituzione:
- `load_encoder_v2()`: carica `jepa_v2_encoder` + `surprise_stats.json` + sonde calibrate; gate **`extra.probes_calibrated == True`** (scritto dal passo 4 quando ECE < 0,05 su VAL e AUROC > baseline grezzo).
- `generate_insights_v2(x_num, x_cat, side)`: encoder → `taps[k]` → sonde (probabilità calibrate per orizzonte) → sorpresa `ζ` per token → Chronovisor v2 (momenti) → attribuzione per momento → `InsightCandidate{axis, message, probability, tick_range, register, source="neural_v2"}`.
- La scala di maturità (`_MATURITY_LADDER`) resta come **moltiplicatore del numero di candidati**, non della "confidenza": la confidenza è la probabilità calibrata e non si scala.

### 9.2 `services/coaching_service.py`

`_generate_jepa_insights` (801–851): estrae con `extract_batch_v2` sull'intero round del giocatore (non `rows[-256:]`: il Chronovisor ha bisogno dell'episodio), passa `side` da `roundstats`; persiste `CoachingInsight` con `tick_range` e `focus_area` dall'attribuzione. `_jepa_maturity_state` (774–799) invariato.

### 9.3 `run_ingestion.py:215-227` (RAP inline)

Rimuovere la chiamata a `comm.generate_advice(out["advice_probs"], confidence=0.85, ...)`; il coaching neurale passa **solo** da `CoachingService`.

### 9.4 Interfaccia (viewmodel Qt, non letto in questa sessione)

Contratto minimo che la UI deve rispettare: mostrare `probability` come percentuale **solo** se `calibrated=True`; mostrare `register` (assertivo/riserva/astensione); link al `tick_range`; distinguere `source in {statistical, neural_v2, llm_rendered}`.

---

## 10. Test: aggiungere, modificare, ritirare

**Aggiungere**
- `tests/test_schema_v2.py`: fingerprint stabile; `extract_v2` in range; rimappatura v1→v2 senza perdita su 100 k tick; vocabolari con fallback loggato.
- `tests/test_naming.py`: normalizzazione idempotente; join `roundstats`↔`playertickstate` copre ≥ 95% dei giocatori sul DB di test (D8).
- `tests/test_export_episodes.py`: §3.
- `tests/test_sigreg.py`: parità con la fixture PyTorch di Parte I App. A.1 (rel 1e-5); `SIGReg(N(0,I)) ≈ 1`; `SIGReg(costante) ≫ 1`; gradiente finito e limitato (Thm 4: $|\partial/\partial z_i| \le 4/(Ns^2)$ verificato numericamente); temporale vs batch su tensori costruiti (collasso temporale rilevato solo dal temporale).
- `tests/test_jepa_v2_blocks.py`: causalità (perturbare il token $t$ non cambia le uscite $<t$); RoPE dipende solo da posizioni relative; RMSNorm = LayerNorm a media nulla; SwiGLU forma.
- `tests/test_jepa_v2_training_smoke.py`: 200 passi su `sample_2k` (< 60 s CPU): loss decresce, RankMe cresce rispetto al passo 0, nessun NaN, checkpoint + sidecar v2 validi, due run con lo stesso seme → pesi identici.
- `tests/test_probes.py`: `LeakageGuard` (colonne sorgente ∩ schema = ∅; permutazione → AUROC ≈ 0,5); ECE su un classificatore perfettamente calibrato ≈ 0; temperature scaling non cambia l'argmax.
- `tests/test_coach_v2.py`: sorpresa reagisce al teletrasporto e non alla permutazione di `map_id` (Parte II §7.3 protocollo 1); Chronovisor v2 Precision@10 ≥ 3× caso su `sample_2k`; planner CEM riduce la distanza al goal; attribuzione a rango pieno; nessuna confidenza letterale (grep in CI su `confidence=0\.` nei moduli di coaching).
- `tests/test_legacy_frozen.py`: §1.1.

**Modificare**
- `test_jepa_window_fetcher.py`, `test_rap_window_fetcher.py`: usare nomi normalizzati.
- `test_persistence_stale_checkpoint.py`: caso `schema_fingerprint` (§2.3).
- `test_training_orchestrator_logic.py`: rimuovere le attese su `scheduler.step()` per epoca per `jepa_v2`.
- `test_collapse_metrics.py`: invariato; aggiungere il caso "gaussiana isotropa → RankMe ≈ D".

**Ritirare** (spostare in `tests/legacy/` insieme ai moduli, Parte I App. E): `test_jepa_collapse_feed.py::test_single_window_batch_is_unmeasurable_not_collapsed`, `::test_within_batch_variance_still_takes_precedence`; `test_jepa_model.py::{test_positioning_exposed, test_economy_wasteful_pistol_round, test_trade_isolated_low_kast, test_label_batch_2d, test_label_batch_3d, test_jepa_coaching_forward, test_jepa_coaching_with_role, test_forward_vl_output_shape, test_concept_probs_sum_to_one}`; `test_jepa_training_pipeline.py::{test_finetune_*, test_target_is_last_tick, test_context_target_no_overlap}`; `test_rap_coach.py::{test_advantage_gap, test_with_skill_vec, test_diagnose_shape}`.

---

## 11. Ordine di esecuzione e criteri di accettazione

| passo | prerequisito | comando di verifica | accettazione |
|---|---|---|---|
| 0 | — | `pytest tests/test_legacy_frozen.py -q` | training legacy rifiutato senza deroga |
| 1 | ingestione ferma per la migrazione D8 (opzionale; l'export può normalizzare al join) | `pytest tests/test_schema_v2.py tests/test_naming.py -q` | rimappatura senza perdita; join ≥ 95% |
| 1b | export `medium` | `PYTHONPATH=. .venv/bin/python tools/export_episodes.py --profile medium --out "$DATA/cs2_v2"` poi `pytest tests/test_export_episodes.py -q` | manifest valido, etichette ≥ 95% |
| 2–3 | 1b | `pytest tests/test_sigreg.py tests/test_jepa_v2_blocks.py tests/test_jepa_v2_training_smoke.py -q` | parità SIGReg; smoke verde; determinismo |
| 4 | 2–3, GPU | `PYTHONPATH=. .venv/bin/python run_full_training_cycle.py --model-type jepa_v2` (20 k passi, ≈ 1–2 h su RX 9070 XT) poi `tools/benchmark_jepa_v2_vs_legacy.py` | §5.3 |
| 5 | 4 | `pytest -q` (intera suite meno `legacy/`) | un solo trainer; `train.sh` coerente |
| 6 | 4 | `pytest tests/test_coach_v2.py -q` | sorpresa validata; Precision@10 ≥ 3× caso |
| 7 | 6 | test della tabella §8 | nessun output non calibrato |
| 8 | 7 | test end-to-end `insight.source == "neural_v2"` su `sample_2k` | insight neurali persistiti con `tick_range` |
| 9 | 8 | ciclo mensile: ri-export, ri-training, benchmark, versione | RankMe/AUROC non peggiorano; ECE < 0,05 |

Stima di calendario (Parte I §8, confermata): 18–22 giorni di lavoro per i passi 0–8.

---

## 12. Scoperte nuove di questa Parte (registro)

| id | scoperta | evidenza | effetto sul piano |
|---|---|---|---|
| D8 | Nomi giocatore normalizzati in `roundstats` (`lower/strip`) ma non in `playertickstate`/`playermatchstats`: 47/105 nomi senza corrispondenza esatta; 18/48 coppie senza tick nel campione | `run_ingestion.py:797` vs bulk insert 1701; misura Parte II §12.1 | §2.4: normalizzazione + migrazione approvata |
| D9 | Tutte le 1.031 righe di `playermatchstats` sono `UNASSIGNED`: nessun training può leggere `TRAIN` | query ro 2026-09-05 | §1.3 |
| V1 | La loss MoE della **JEPA** (`_sparse_moe`) è il termine di Switch con nomi $f_i/P_i$ scambiati ma valore corretto; solo il RAP ha il segno sbagliato | `jepa_model.py:220-243` vs `rap/model.py:201-205` | R4 resta; nessun fix alla JEPA su questo punto (la testa è comunque ritirata) |
| V2 | τ appreso nel checkpoint archiviato = 0,0481 (da 0,07) | Parte II §12.3 | conferma la dinamica di §2.1.3 |
| V3 | Target encoder convergiuto all'online ($\|\Delta\theta\| = 0{,}135$ vs 22,8 casuale) | Parte II §12.3 | J6 riguarda la fase iniziale, non lo stato finale |
| V4 | L'encoder addestrato è **peggiore delle feature grezze** e uguale a una rete casuale sulle sonde `round_won` (0,68 vs 0,76) e morte (0,74 vs 0,84) | Parte II §12.5 | il baseline **R** entra nel benchmark come soglia minima (§5.2) |
| V5 | Il predittore addestrato è peggiore dell'identità su MSE/coseno/InfoNCE fino a 32 tick; una rete casuale con identità ottiene top-1 97% | Parte II §12.4 | conferma J2/J4; la loss di produzione non misura apprendimento |
| V6 | RankMe 66/256 (rete casuale 61); SIGReg 660 vs 1 gaussiana | Parte II §12.3, §12.6 | soglie iniziali per l'abort v2 e per il benchmark |
| V7 | 19/25 feature costanti in > 93% delle finestre di 11 tick; salute/armatura/equip cambiano in < 0,2% dei tick | Parte II §12.2 | giustifica token 125 ms e orizzonti 0,5–2 s; motiva le etichette evento (HEPA) |

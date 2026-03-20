from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlmodel import select, update

from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

try:
    import joblib
except ImportError:
    joblib = None

logger = get_logger("cs2analyzer.data_pipeline")

# Hard upper bound for how many PlayerMatchStats rows to load into memory.
# Prevents OOM on large deployments. Bump if needed; pipeline is deterministic.
_MAX_PIPELINE_ROWS = 50_000


class ProDataPipeline:
    """
    Enhanced Data Engine: Cleaning, Preprocessing, Scaling, and Splitting.
    Prepares data for the MLP Neural Network.
    """

    def __init__(self):
        self.scaler = StandardScaler()
        self._pipeline_executed = False  # P-DP-04: idempotency guard
        self.feature_cols = [
            "avg_kills",
            "avg_deaths",
            "avg_adr",
            "avg_hs",
            "avg_kast",
            "kill_std",
            "adr_std",
            "kd_ratio",
            "impact_rounds",
            "accuracy",
            "econ_rating",
            "rating",
        ]

    SCALER_PATH = Path(__file__).parent.parent / "storage" / "fitted_scaler.joblib"

    def run_pipeline(self):
        # P-DP-04: Prevent double-application of scaler if called twice.
        if self._pipeline_executed:
            logger.warning("P-DP-04: run_pipeline() already executed on this instance. Skipping.")
            return
        db = get_db_manager()
        with db.get_session() as session:
            statement = (
                select(PlayerMatchStats)
                .where(PlayerMatchStats.data_quality != "none")  # C-04: exclude failed parses
                .order_by(PlayerMatchStats.id)  # H-09: deterministic ordering
                .limit(_MAX_PIPELINE_ROWS)
            )
            results = session.exec(statement).all()
            if not results:
                return
            if len(results) == _MAX_PIPELINE_ROWS:
                logger.warning(
                    "run_pipeline: query hit the %d-row limit. "
                    "Older records beyond this limit are excluded from the split.",
                    _MAX_PIPELINE_ROWS,
                )
            df = pd.DataFrame([r.model_dump() for r in results])

        # 1. Temporal split FIRST — outlier thresholds must be computed from
        # training data only to prevent data leakage (P-DP-01).
        df["stratify_col"] = df["is_pro"].astype(str) + "_" + df["user_id"].astype(str)
        train_df, val_df, test_df = self._split_data(df, temporal_split=True)

        if train_df.empty:
            logger.warning("Training split is empty after splitting. Cannot fit scaler.")
            return

        # 2. Outlier removal — thresholds derived from TRAINING set only (P-DP-01).
        # Applied to all splits so val/test stay distribution-consistent with train.
        train_df = train_df[train_df["avg_adr"] < 400]
        q1, q3 = train_df["avg_kills"].quantile([0.25, 0.75])
        iqr = q3 - q1
        # P-DP-03: Named constant for outlier IQR multiplier.
        # 3.0× IQR ≈ Tukey's outer fence, retaining ~99.7% of normal data.
        _IQR_EXTREME_OUTLIER_MULTIPLIER = 3.0
        upper_bound = q3 + _IQR_EXTREME_OUTLIER_MULTIPLIER * iqr
        train_df = train_df[train_df["avg_kills"] < upper_bound]
        val_df = val_df[(val_df["avg_adr"] < 400) & (val_df["avg_kills"] < upper_bound)]
        test_df = test_df[(test_df["avg_adr"] < 400) & (test_df["avg_kills"] < upper_bound)]

        if train_df.empty:
            logger.warning("Training split is empty after outlier removal. Cannot fit scaler.")
            return

        # 3. Fit scaler on TRAINING data ONLY, then transform all splits.
        # Work on explicit copies to prevent SettingWithCopyWarning and to ensure
        # that double-calling run_pipeline() doesn't silently double-scale existing
        # DataFrames (F2-23).
        train_df = train_df.copy()
        val_df = val_df.copy()
        test_df = test_df.copy()
        self.scaler.fit(train_df[self.feature_cols])
        train_df[self.feature_cols] = self.scaler.transform(train_df[self.feature_cols])
        val_df[self.feature_cols] = self.scaler.transform(val_df[self.feature_cols])
        test_df[self.feature_cols] = self.scaler.transform(test_df[self.feature_cols])

        logger.info(
            "Scaler fitted on %d training samples. Mean range: [%.3f, %.3f]",
            len(train_df),
            self.scaler.mean_.min(),
            self.scaler.mean_.max(),
        )

        # Persist scaler for inference consistency
        self._save_scaler()

        # 4. Save splits
        self._update_splits_in_db(train_df, "train")
        self._update_splits_in_db(val_df, "val")
        self._update_splits_in_db(test_df, "test")

        self._pipeline_executed = True

    def _save_scaler(self):
        """Persist fitted scaler with sklearn version for compatibility checks."""
        if joblib is not None:
            import sklearn

            payload = {"scaler": self.scaler, "sklearn_version": sklearn.__version__}
            joblib.dump(payload, self.SCALER_PATH)
            logger.info("Scaler saved to %s (sklearn %s)", self.SCALER_PATH, sklearn.__version__)

    def load_scaler(self) -> bool:
        """Load previously fitted scaler. Returns False if not found or incompatible."""
        if joblib is not None and self.SCALER_PATH.exists():
            import sklearn

            data = joblib.load(self.SCALER_PATH)
            if isinstance(data, dict) and "scaler" in data:
                saved_ver = data.get("sklearn_version", "unknown")
                # P-DP-05: Compare major.minor (not just major) — minor releases
                # can change scaler internals (e.g. StandardScaler dtype handling).
                current_mm = tuple(sklearn.__version__.split(".")[:2])
                saved_mm = tuple(saved_ver.split(".")[:2]) if saved_ver != "unknown" else current_mm
                if saved_mm != current_mm:
                    logger.warning(
                        "Scaler sklearn version mismatch: saved=%s, current=%s — refit recommended",
                        saved_ver,
                        sklearn.__version__,
                    )
                self.scaler = data["scaler"]
            else:
                # Legacy format (bare scaler without version metadata)
                self.scaler = data
                logger.warning("Loaded legacy scaler without version metadata — refit recommended")
            logger.info("Scaler loaded from %s", self.SCALER_PATH)
            return True
        return False

    def _split_data(self, df, temporal_split=True):
        """
        Splits data into Train (70%), Validation (15%), and Test (15%).

        Args:
            df: Input DataFrame
            temporal_split: If True, splits chronologically to prevent leakage.
                           If False, uses random stratified split (legacy).
        """
        if temporal_split:
            # Chronological Split with Stratification
            # Split Pros and Users separately to maintain class balance
            # Task 2.17.2: Preventing temporal leakage

            # Determine sort column
            if "match_date" in df.columns:
                sort_col = "match_date"
            else:
                sort_col = "processed_at"

            pros = df[df["is_pro"] == True].sort_values(by=sort_col)
            users = df[df["is_pro"] == False].sort_values(by=sort_col)

            def time_slice(sub_df):
                n = len(sub_df)
                if n == 0:
                    return sub_df, sub_df, sub_df

                train_idx = int(n * 0.70)
                val_idx = int(n * 0.85)

                return (
                    sub_df.iloc[:train_idx],
                    sub_df.iloc[train_idx:val_idx],
                    sub_df.iloc[val_idx:],
                )

            p_train, p_val, p_test = time_slice(pros)
            u_train, u_val, u_test = time_slice(users)

            train = pd.concat([p_train, u_train])
            val = pd.concat([p_val, u_val])
            test = pd.concat([p_test, u_test])

            # C-06: Player-level decontamination — ensure no player spans splits
            train, val, test = self._decontaminate_player_splits(train, val, test)

            # Log temporal boundaries for reproducibility
            for label, split_df in [("train", train), ("val", val), ("test", test)]:
                if not split_df.empty and sort_col in split_df.columns:
                    min_date = split_df[sort_col].min()
                    max_date = split_df[sort_col].max()
                    logger.info(
                        "Temporal split [%s]: %d records, date range %s → %s",
                        label,
                        len(split_df),
                        min_date,
                        max_date,
                    )

            return train, val, test

        else:
            # Legacy Random Stratified Split
            stratify = df["stratify_col"]
            if df["stratify_col"].value_counts().min() < 2:
                stratify = None

            train, temp = train_test_split(df, test_size=0.30, stratify=stratify, random_state=42)

            # Secondary split
            strat_temp = (
                temp["stratify_col"]
                if stratify is not None and temp["stratify_col"].value_counts().min() >= 2
                else None
            )
            val, test = train_test_split(temp, test_size=0.50, stratify=strat_temp, random_state=42)

            return train, val, test

    @staticmethod
    def _decontaminate_player_splits(train, val, test):
        """C-06: Ensure each player appears in exactly one split.

        P-DP-02: To respect temporal ordering, multi-split players are
        assigned to their **earliest** split (not the majority). This
        prevents future data from leaking into training when a temporal
        split is used. Dropping later-split rows is preferred over moving
        them backward in time, which would violate the temporal guarantee.
        """
        if "player_name" not in train.columns:
            return train, val, test

        all_data = pd.concat(
            [
                train.assign(_split="train"),
                val.assign(_split="val"),
                test.assign(_split="test"),
            ]
        )

        # P-DP-02: Assign each player to their earliest split to preserve
        # temporal ordering. Priority: train=0 < val=1 < test=2, so the
        # min-priority split is the earliest in time.
        split_priority = {"train": 0, "val": 1, "test": 2}
        player_split_counts = (
            all_data.groupby(["player_name", "_split"]).size().reset_index(name="count")
        )
        player_split_counts["priority"] = player_split_counts["_split"].map(split_priority)
        # Sort by player, then by priority (earliest split first)
        player_split_counts = player_split_counts.sort_values(
            ["player_name", "priority"], ascending=[True, True]
        )
        player_earliest = player_split_counts.groupby("player_name").first()["_split"]

        # Drop rows from later splits (not move them backward)
        all_data["_assigned"] = all_data["player_name"].map(player_earliest)
        decontaminated = all_data[all_data["_split"] == all_data["_assigned"]].drop(
            columns=["_split", "_assigned"]
        )

        new_train = decontaminated[decontaminated["player_name"].map(player_earliest) == "train"]
        new_val = decontaminated[decontaminated["player_name"].map(player_earliest) == "val"]
        new_test = decontaminated[decontaminated["player_name"].map(player_earliest) == "test"]

        # Count how many players had cross-split data dropped
        multi_split_players = player_split_counts.groupby("player_name").size()
        moved = (multi_split_players > 1).sum()
        if moved > 0:
            dropped = len(all_data) - len(decontaminated)
            logger.info(
                "P-DP-02 player decontamination: %d multi-split players resolved, "
                "%d rows dropped from later splits "
                "(train=%d, val=%d, test=%d)",
                moved,
                dropped,
                len(new_train),
                len(new_val),
                len(new_test),
            )

        return new_train, new_val, new_test

    def _update_splits_in_db(self, df, split_name):
        """Bulk-update dataset_split for all rows in the given split DataFrame.

        Uses a single UPDATE ... WHERE id IN (...) per chunk instead of N individual
        GET+SET+ADD queries, avoiding SQLite session timeouts on large datasets (F2-22).
        """
        if df.empty:
            return
        ids = df["id"].dropna().astype(int).tolist()
        _CHUNK = 500  # Stay under SQLite SQLITE_MAX_VARIABLE_NUMBER (999)
        db = get_db_manager()
        with db.get_session() as session:
            for i in range(0, len(ids), _CHUNK):
                chunk = ids[i : i + _CHUNK]
                session.exec(
                    update(PlayerMatchStats)
                    .where(PlayerMatchStats.id.in_(chunk))
                    .values(dataset_split=split_name)
                )
            session.commit()
        logger.debug("Split '%s': updated %d records in DB.", split_name, len(ids))

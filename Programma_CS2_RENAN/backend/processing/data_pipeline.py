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
        db = get_db_manager()
        with db.get_session() as session:
            statement = select(PlayerMatchStats).limit(_MAX_PIPELINE_ROWS)
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

        # 1. Cleaning
        df = df[df["avg_adr"] < 400]
        df = df[df["avg_kills"] < 3.0]

        # 2. Split FIRST to prevent data leakage (temporal split before scaling)
        df["stratify_col"] = df["is_pro"].astype(str) + "_" + df["user_id"].astype(str)
        train_df, val_df, test_df = self._split_data(df, temporal_split=True)

        if train_df.empty:
            logger.warning("Training split is empty after cleaning. Cannot fit scaler.")
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
                current_major = sklearn.__version__.split(".")[0]
                saved_major = saved_ver.split(".")[0] if saved_ver != "unknown" else current_major
                if saved_major != current_major:
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

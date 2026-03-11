import pandas as pd

from Programma_CS2_RENAN.observability.logger_setup import get_logger

LOGGER_NAME = "cs2analyzer.schema"
logger = get_logger(LOGGER_NAME)

# --- Schema Versioning (Task 2.19.1) ---
# Increment SCHEMA_VERSION when demo_parser.py adds new required columns.
# This ensures the validator's checklist stays in sync with the parser's output.
SCHEMA_VERSION = 2

EXPECTED_SCHEMA = {
    # Version 1 (Core Stats)
    "round": int,
    "kills": int,
    "deaths": int,
    "assists": int,
    "adr": float,
    "headshot_pct": float,
    "kast": float,
}

# Version 2 additions (HLTV 2.0 integration)
SCHEMA_V2_EXTENSIONS = {
    "accuracy": float,
}

# Registry: maps schema version to the cumulative set of required columns
_SCHEMA_REGISTRY = {
    1: EXPECTED_SCHEMA,
    2: {**EXPECTED_SCHEMA, **SCHEMA_V2_EXTENSIONS},
}


def get_active_schema(version: int = None) -> dict:
    """
    Returns the expected schema for a given version.
    Defaults to the latest SCHEMA_VERSION.
    """
    v = version or SCHEMA_VERSION
    if v not in _SCHEMA_REGISTRY:
        logger.warning("Unknown schema version %s, falling back to latest (%s)", v, SCHEMA_VERSION)
        v = SCHEMA_VERSION
    return _SCHEMA_REGISTRY[v]


def validate_demo_schema(df: pd.DataFrame, version: int = None) -> None:
    """
    Validates structural integrity of demo parser output.

    Task 2.19.1: Supports versioned schemas. When the parser is updated
    to include new columns, increment SCHEMA_VERSION and add entries
    to the registry. The validator auto-adapts.
    """
    active_schema = get_active_schema(version)
    logger.info("Schema validation started (v%s)", version or SCHEMA_VERSION)

    # Column existence
    missing = set(active_schema.keys()) - set(df.columns)
    if missing:
        logger.error("Missing columns: %s", missing)
        raise ValueError(f"Schema missing columns: {missing}")

    # Type validation
    for column, expected_type in active_schema.items():
        _validate_column_type(df, column, expected_type)

    logger.info("Schema validation passed")


def _validate_column_type(df, column, expected_type):
    if not pd.api.types.is_numeric_dtype(df[column]):
        logger.error("Column '%s' is not numeric", column)
        raise TypeError(f"Column '{column}' must be numeric")

    # For int columns, verify no fractional values exist. A bare astype(int) silently
    # truncates floats (e.g. 1.5 -> 1), masking upstream parser bugs. (F2-48)
    if expected_type is int:
        non_integer_mask = df[column].dropna().mod(1) != 0
        if non_integer_mask.any():
            logger.error(
                "Column '%s' has non-integer float values where int is expected", column
            )
            raise TypeError(
                f"Column '{column}' must contain integer values, but fractional values found"
            )
        return

    try:
        df[column].astype(expected_type)
    except (ValueError, TypeError):
        logger.error("Column '%s' invalid type cast to %s", column, expected_type)
        raise TypeError(f"Column '{column}' invalid type")

"""Typed feature schema for the CS2 v2 neural core (CORREZIONE_NUCLEO_NEURALE §2.1).

Defines the ``CS2_V2`` constant — the single source of truth for the 21 numeric
and 3 categorical features consumed by the JEPA v2 encoder, the v2 export
pipeline, and the downstream coaching heads.

v2 drops four v1 slots that were empirically uninformative or unsuitable for
embedding (Parte I D1-D3):

* **kast_estimate** (v1 slot 16): always 0.0 in the database — PlayerTickState
  has no KAST column, and the retired ``estimate_kast_from_stats`` heuristic
  diverged from real round-level KAST (0.91 vs 0.71 measured).
* **round_phase** (v1 slot 18): bucket-quantised from equipment_value, which is
  already a numeric feature — the ordinal encoding lost the continuous signal.
* **map_id hash** (v1 slot 17): MD5-derived float in [0, 1) carries no learnable
  structure; replaced by a categorical embedding with a fixed 10-map vocabulary.
* **weapon_class ordinal** (v1 slot 19): arbitrary 0-1 float ordinal lost class
  boundaries and conflated distance; replaced by a 9-class categorical embedding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.schema_v2")

_vocab_fallback_seen: set[str] = set()


class Kind(str, Enum):
    """Feature kind discriminator (Parte III §2.1, narrowed by D-04)."""

    numeric = "numeric"
    categorical = "categorical"


@dataclass(frozen=True)
class SchemaField:
    """Single feature slot in a v2 schema (D-04).

    Attributes:
        name: Unique feature name.
        kind: ``Kind.numeric`` or ``Kind.categorical``.
        source_column: Column name on ``PlayerTickState`` (or metadata source).
        unit: Physical unit or semantic tag (``hp``, ``bool``, ``count``, …).
        scale: Divisor for normalisation (``val / scale``); 1.0 for derived/binary.
        clip: Optional ``(lo, hi)`` bounds applied after scaling.  ``None`` in
              either position means unbounded on that side.
        vocab: Ordered vocabulary for categoricals; empty for numerics.
        derived_from_future: True if the feature uses information after the tick.
        description: Human-readable note (empty by default).
    """

    name: str
    kind: Kind
    source_column: str
    unit: str
    scale: float = 1.0
    clip: Optional[tuple[Optional[float], Optional[float]]] = None
    vocab: tuple[str, ...] = ()
    derived_from_future: bool = False
    description: str = ""


def _field_to_dict(f: SchemaField) -> dict:
    """Deterministic dict representation for JSON serialisation."""
    return {
        "clip": list(f.clip) if f.clip is not None else None,
        "derived_from_future": f.derived_from_future,
        "description": f.description,
        "kind": f.kind.value,
        "name": f.name,
        "scale": f.scale,
        "source_column": f.source_column,
        "unit": f.unit,
        "vocab": list(f.vocab),
    }


@dataclass(frozen=True)
class FeatureSchema:
    """Immutable v2 feature schema (Parte III §2.1, contract D-04/D-05).

    Attributes:
        schema_id: Short identifier (e.g. ``"cs2_v2"``).
        version: Schema revision number.
        fields: Ordered tuple of ``SchemaField`` instances.
    """

    schema_id: str
    version: int
    fields: tuple[SchemaField, ...]

    @property
    def numeric_fields(self) -> tuple[SchemaField, ...]:
        return tuple(f for f in self.fields if f.kind == Kind.numeric)

    @property
    def categorical_fields(self) -> tuple[SchemaField, ...]:
        return tuple(f for f in self.fields if f.kind == Kind.categorical)

    @property
    def numeric_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.numeric_fields)

    @property
    def categorical_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.categorical_fields)

    @property
    def numeric_dim(self) -> int:
        return len(self.numeric_fields)

    @property
    def categorical_vocab_sizes(self) -> list[int]:
        return [len(f.vocab) for f in self.categorical_fields]

    def fingerprint(self) -> str:
        """Stable content hash of the field definitions (D-04).

        Covers ``fields`` only — ``schema_id`` and ``version`` are excluded so
        that metadata bumps do not invalidate trained weights.
        """
        field_dicts = [_field_to_dict(f) for f in self.fields]
        payload = json.dumps(field_dicts, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_json(self) -> str:
        """Pretty-printed JSON for documentation and sidecar files."""
        field_dicts = [_field_to_dict(f) for f in self.fields]
        obj = {
            "schema_id": self.schema_id,
            "version": self.version,
            "fields": field_dicts,
        }
        return json.dumps(obj, indent=2, sort_keys=True)

    def vocab_index(self, field_name: str, value: str) -> int:
        """Look up ``value`` in the vocabulary of ``field_name``.

        Falls back to the last vocab entry (``other`` / ``unknown``) when
        ``value`` is not found, with a throttled WARNING log (D-05).
        """
        for f in self.fields:
            if f.name == field_name:
                if not f.vocab:
                    raise ValueError(f"Field {field_name!r} has no vocabulary")
                try:
                    return f.vocab.index(value)
                except ValueError:
                    fallback_idx = len(f.vocab) - 1
                    _log_vocab_fallback(field_name, value, f.vocab[fallback_idx])
                    return fallback_idx
        raise KeyError(f"No field named {field_name!r} in schema")


def _log_vocab_fallback(field_name: str, value: str, fallback: str) -> None:
    """Throttled WARNING for vocab fallback (one per unique field+value pair)."""
    key = f"{field_name}:{value}"
    if key not in _vocab_fallback_seen:
        _vocab_fallback_seen.add(key)
        _logger.warning(
            "Vocab fallback: field %r value %r not in vocabulary, using %r",
            field_name,
            value,
            fallback,
        )


def _reset_vocab_fallback_state_for_tests() -> None:
    """Test-only: reset throttle state so repeated tests can capture warnings."""
    _vocab_fallback_seen.clear()


# ---------------------------------------------------------------------------
# CS2_V2 constant — the single source of truth for v2 features (D-05).
# ---------------------------------------------------------------------------

CS2_V2 = FeatureSchema(
    schema_id="cs2_v2",
    version=1,
    fields=(
        # ---- Numeric (21 fields, v1 indices [0..15, 20..24]) ----
        SchemaField("health", Kind.numeric, "health", "hp", scale=100.0),
        SchemaField("armor", Kind.numeric, "armor", "ap", scale=100.0),
        SchemaField("has_helmet", Kind.numeric, "has_helmet", "bool"),
        SchemaField("has_defuser", Kind.numeric, "has_defuser", "bool"),
        SchemaField("equipment_value", Kind.numeric, "equipment_value", "usd", scale=10000.0),
        SchemaField("is_crouching", Kind.numeric, "is_crouching", "bool"),
        SchemaField("is_scoped", Kind.numeric, "is_scoped", "bool"),
        SchemaField("is_blinded", Kind.numeric, "flash_duration", "bool"),
        SchemaField(
            "enemies_visible",
            Kind.numeric,
            "enemies_visible",
            "count",
            scale=5.0,
            clip=(None, 1.0),
        ),
        SchemaField("pos_x", Kind.numeric, "pos_x", "units", scale=4096.0, clip=(-1.0, 1.0)),
        SchemaField("pos_y", Kind.numeric, "pos_y", "units", scale=4096.0, clip=(-1.0, 1.0)),
        SchemaField("pos_z", Kind.numeric, "pos_z", "units", scale=1024.0, clip=(-1.0, 1.0)),
        SchemaField("view_yaw_sin", Kind.numeric, "view_x", "rad"),
        SchemaField("view_yaw_cos", Kind.numeric, "view_x", "rad"),
        SchemaField("view_pitch", Kind.numeric, "view_y", "deg", scale=90.0),
        SchemaField("z_penalty", Kind.numeric, "pos_z", "norm"),
        SchemaField(
            "time_in_round",
            Kind.numeric,
            "time_in_round",
            "sec",
            scale=115.0,
            clip=(None, 1.0),
        ),
        SchemaField("bomb_planted", Kind.numeric, "bomb_planted", "bool"),
        SchemaField(
            "teammates_alive",
            Kind.numeric,
            "teammates_alive",
            "count",
            scale=4.0,
            clip=(None, 1.0),
        ),
        SchemaField(
            "enemies_alive",
            Kind.numeric,
            "enemies_alive",
            "count",
            scale=5.0,
            clip=(None, 1.0),
        ),
        SchemaField(
            "team_economy",
            Kind.numeric,
            "team_economy",
            "usd",
            scale=16000.0,
            clip=(None, 1.0),
        ),
        # ---- Categorical (3 fields, D-05 vocabs) ----
        SchemaField(
            "map_id",
            Kind.categorical,
            "map_name",
            "id",
            vocab=(
                "de_ancient",
                "de_anubis",
                "de_dust2",
                "de_inferno",
                "de_mirage",
                "de_nuke",
                "de_overpass",
                "de_train",
                "de_vertigo",
                "other",
            ),
        ),
        SchemaField(
            "weapon_class",
            Kind.categorical,
            "active_weapon",
            "class",
            vocab=(
                "none",
                "knife",
                "pistol",
                "smg",
                "rifle",
                "sniper",
                "heavy",
                "grenade",
                "other",
            ),
        ),
        SchemaField(
            "side",
            Kind.categorical,
            "side",
            "enum",
            vocab=("CT", "T", "unknown"),
        ),
    ),
)

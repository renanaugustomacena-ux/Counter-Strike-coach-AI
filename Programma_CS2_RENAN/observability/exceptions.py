"""
Centralized exception hierarchy for the CS2 Analyzer.

All domain-specific exceptions should inherit from ``CS2AnalyzerError``.
This enables:

1. Typed catch blocks instead of bare ``except Exception``
2. Error code attachment to exceptions for structured logging
3. Consistent Sentry fingerprinting via exception class name
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Programma_CS2_RENAN.observability.error_codes import ErrorCode


class CS2AnalyzerError(Exception):
    """Base exception for all CS2 Analyzer errors."""

    def __init__(self, message: str, error_code: "ErrorCode | None" = None):
        self.error_code = error_code
        super().__init__(message)


class ConfigurationError(CS2AnalyzerError):
    """Invalid or missing configuration."""


class DatabaseError(CS2AnalyzerError):
    """Database operation failure (connection, migration, query)."""


class IngestionError(CS2AnalyzerError):
    """Demo file ingestion failure (parsing, validation, storage)."""


class TrainingError(CS2AnalyzerError):
    """ML training pipeline failure (data prep, training, checkpoint)."""


class IntegrationError(CS2AnalyzerError):
    """External service integration failure (Steam, FACEIT, HLTV)."""


class UIError(CS2AnalyzerError):
    """UI rendering or interaction failure."""

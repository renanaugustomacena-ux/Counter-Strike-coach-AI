# DEPRECATED: Use ``from Programma_CS2_RENAN.observability.logger_setup import get_logger`` instead.
# This shim re-exports the canonical logger to avoid import breakage.
import warnings as _warnings

_warnings.warn(
    "Programma_CS2_RENAN.core.logger is deprecated — use observability.logger_setup",
    DeprecationWarning,
    stacklevel=2,
)

from Programma_CS2_RENAN.observability.logger_setup import (  # noqa: F401, E402
    app_logger,
    get_logger,
)

setup_logger = get_logger  # legacy alias

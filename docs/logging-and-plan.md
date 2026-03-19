Logging & Error Handling Audit Report
Project: Counter-Strike Coach AI (Programma_CS2_RENAN) Date: 2026-03-18 Scope: All 
.py
 files — core app, backend, tools, tests

Executive Summary
Dimension	Rating	Verdict
Centralized Logging	⭐⭐⭐⭐	Solid foundation via 
logger_setup.py
Structured Logging	⭐⭐⭐	JSON in 
console.py
, plain text elsewhere
Error Code System	⭐⭐	Exists as inline comments, no formal registry
Custom Exceptions	⭐⭐⭐	Domain-specific classes exist, underused
Error Reporting (Sentry)	⭐⭐⭐⭐⭐	PII scrubbing, double opt-in, pytest gate
Catch-all proliferation	⭐⭐	50+ bare except Exception blocks
Consistency	⭐⭐	Mixed print() / traceback.print_exc() / logger
Runtime Integrity (RASP)	⭐⭐⭐⭐	HMAC-signed manifests, SHA-256 file integrity
Log Rotation & Retention	⭐⭐⭐⭐	5 MB rotation, 3 backups, fallback handler
Debug Level Control	⭐⭐⭐⭐	
configure_log_level()
 for runtime switching
Overall professionalism: Intermediate-to-Advanced. The infrastructure components (logger_setup, sentry_setup, 
rasp.py
) are production-caliber. Enforcement across the codebase is incomplete — tools, tests, and standalone scripts bypass the centralized system.

1. Centralized Logging Infrastructure
1.1 Core: 
logger_setup.py
Strengths:

RotatingFileHandler — 5 MB cap, 3 backups. Prevents unbounded disk growth.
Fallback to FileHandler on Windows PermissionError with explicit warning code LS-01.
Consistent format: %(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s
Thread name in log format — essential for this multi-threaded daemon architecture.
configure_log_level()
 enables runtime log level switching for all cs2analyzer.* loggers.
Circular-dependency-safe: 
configure_log_dir()
 breaks the config↔logger import cycle.
Gaps:

Console handler set to WARNING — INFO/DEBUG messages are invisible on stdout. Acceptable for end-user apps, but complicates developer debugging without file log inspection.
No structlog or JSON output from the centralized logger. 
console.py
 has its own JSON handler, creating format divergence.
1.2 Console Module: 
console.py
 (Lines 99–112)
python
# JSON structured logging — GOOD
'{"ts":"%(asctime)s","lvl":"%(levelname)s","mod":"%(name)s","msg":"%(message)s"}'
Date-rotated log files (console_20260318.json) — sensible for an interactive CLI.
Conflict: Uses its own logging.FileHandler instead of the centralized 
get_logger()
. This means 
console.py
 logs go to logs/console_*.json while the rest of the app logs to 
logs/cs2_analyzer.log
 with a different format.
1.3 Session Engine: 
session_engine.py
 (Lines 32–48)
Adds a second FileHandler (to session_engine.log) on top of the one 
get_logger()
 already attaches. Produces duplicate writes to 
cs2_analyzer.log
 AND session_engine.log.
Different format string from the centralized one: %(asctime)s - %(name)s - %(levelname)s - %(message)s vs %(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s.
2. Logger Naming Convention
File	Logger Name	Follows cs2analyzer.*?
main.py
cs2analyzer.main	✅
console.py
cs2analyzer.console	✅
session_engine.py
cs2analyzer.session_engine	✅
jepa_model.py
cs2analyzer.nn.jepa_model	✅
sentry_setup.py
cs2analyzer.sentry	✅
batch_ingest.py
batch_ingest	❌
goliath.py
cs2analyzer.goliath	✅
Tools: 
Sanitize_Project.py
Sanitizer	❌
Tools: 
audit_binaries.py
BinaryAuditor	❌
Tools: 
Feature_Audit.py
FeatureAuditor	❌
Tools: 
build_pipeline.py
MacenaBuild	❌
Tools: 
migrate_db.py
DBMigrator	❌
Tools: 
observe_training_cycle.py
observe_cycle	❌
Tests: 
verify_chronovisor_real.py
RealDataTest	❌
logger_setup.py
 singleton	CS2_Coach_App	❌
Verdict: Core app follows the cs2analyzer.* hierarchy. All tools and tests use ad-hoc names, making 
configure_log_level()
 (which filters on cs2analyzer prefix) ineffective for them.

3. Error Code System
The project uses inline comment-style error codes. These are not machine-parseable and have no centralized registry.

Discovered Codes
Code	Location	Meaning
LS-01	logger_setup.py:38	RotatingFileHandler fallback
RP-01	rasp.py:14	HMAC key not set
DA-01-03	main.py:411	Malformed JSON from DB
P0-07	main.py:619	Uninitialized attribute guard
P3-01	main.py:426	Canonical enum mapping
P4-B	session_engine.py:189	Configurable zombie threshold
P7-01	console.py:662	Secure API key input
P7-02	console.py:149	Secret sanitization in errors
F6-06	session_engine.py:7	sys.path bootstrap
F6-SE	session_engine.py:58	Backup failure training gate
F6-03	session_engine.py:543	Explicit commit
F7-12	console.py:47	sys.path bootstrap
F7-19	main.py:534	Training status card props
F7-30	console.py:735	API key masking
SE-02	session_engine.py:162	Daemon thread join
SE-04	session_engine.py:209	Config validation
SE-05	session_engine.py:113	UI notification
SE-06	session_engine.py:405	Shutdown responsiveness
SE-07	session_engine.py:280	Settings reload
IM-03	session_engine.py:360	Event race condition fix
NN-02	session_engine.py:397	Training lock
G-07	session_engine.py:423	Belief calibration
H-02	session_engine.py:121	Knowledge base init
R1-12	rasp.py:9, 88, 137	HMAC manifest signing
WARNING

These codes live only as inline comments. No ERROR_CODES.md, no enum, no mapping to HTTP status codes or exit codes. If a user reports "LS-01", there is no lookup mechanism other than grep.

4. Custom Exception Classes
Exception	Module	Purpose
IntegrityError
observability/rasp.py
Runtime integrity violation
DataQualityError	
backend/processing/feature_engineering/vectorizer.py
Feature engineering validation
DEMValidationError	
backend/processing/validation/dem_validator.py
Demo file parsing failures
FACEITAPIError	
backend/data_sources/faceit_integration.py
FACEIT API errors
SteamNotFoundError	
backend/data_sources/steam_demo_finder.py
Steam installation missing
Assessment: Domain-scoped exception classes exist for critical subsystems. However, the project overwhelmingly catches Exception rather than these specific types, negating their diagnostic value.

5. Error Handling Anti-Patterns
5.1 Bare except Exception Proliferation
50+ occurrences across the codebase. Examples:

python
# session_engine.py:108 — good: uses logger.exception()
except Exception as e:
    logger.exception("Backup Routine Failed")
# console.py:148 — good: sanitizes secrets before logging
except Exception as e:
    sanitized = str(e)
    # redacts API keys...
# main.py:400 — BAD: error logged at DEBUG (invisible to operators)
except Exception as e:
    app_logger.debug("Profile Load Fail: %s", e)
# session_engine.py:256-258 — BAD: silent suppression
except Exception:
    pass  # Don't crash the scanner over a notification
5.2 print() Instead of Logger
40+ instances of print("ERROR: ...", file=sys.stderr) scattered across tools and tests. These bypass the logging pipeline entirely — no timestamp, no rotation, no Sentry capture.

5.3 traceback.print_exc() Instead of logger.exception()
Files using traceback.print_exc() directly:

tools/observe_training_cycle.py
 (3 locations)
tests/verify_map_integration.py
tests/verify_superposition.py
These print to stderr with no structured context.

5.4 logging.basicConfig() in Standalone Scripts
Three files call logging.basicConfig():

batch_ingest.py
tests/verify_chronovisor_real.py
tools/observe_training_cycle.py
This conflicts with the centralized 
get_logger()
 setup if both are active in the same process, because basicConfig modifies the root logger.

6. Sentry Integration (Remote Error Reporting)
sentry_setup.py
 — Production-grade.

Feature	Status
Double opt-in (enabled=True + DSN)	✅
PII scrubbing (home paths, server names)	✅
Breadcrumb data scrubbing	✅
send_default_pii=False	✅
Pytest detection gate	✅
Logging integration (WARNING → breadcrumb, ERROR → event)	✅
Release version tagging	✅
Graceful fallback if sentry_sdk not installed	✅
traces_sample_rate=0.1 (10% sampling)	✅
Idempotent initialization	✅
TIP

Sentry integration is the most professional component of the entire observability stack. No issues found.

7. Runtime Integrity (RASP)
rasp.py
 — Well-architected.

HMAC-signed manifest with hmac.compare_digest() (timing-safe comparison).
SHA-256 per-file hash verification.
Environment-aware: Production (frozen PyInstaller) vs. development mode with different strictness.
Build-time 
sign_manifest()
 workflow.
Frozen binary environment validation.
NOTE

The HMAC key falls back to a static string (macena-cs2-integrity-v1) with a warnings.warn() at module import. This is correctly documented as RP-01 and is acceptable for development, not production.

8. Application Startup Error Handling
main.py
 demonstrates a layered defense strategy:

Venv guard (line 13) — exits with code 2
RASP integrity check (line 24–37) — exits with code 1 in production, warns in dev
Sentry init (line 60–71) — graceful skip on failure
KV layout load (line 658–690) — fallback error screen on crash with exc_info=True
Top-level catch (line 2061–2062) — traceback.format_exc() to CRITICAL log
Good: Graceful degradation at every layer. The app doesn't crash silently. Gap: Exit codes are inconsistent — sys.exit(2) for venv, sys.exit(1) for integrity, sys.exit(0) for duplicate instance.

9. Console Secret Sanitization
console.py:149–158 — Sanitizes API keys from error messages before logging. Handles STEAM_API_KEY, FACEIT_API_KEY, STORAGE_API_KEY.

console.py:735 — Masks API keys in config display (**** + last 4 chars).

console.py:665–677 — Secure key input via getpass, explicit warning against CLI arguments.

Assessment: Security-conscious for a local desktop app. The comment P7-01 acknowledges the remaining gap (plaintext 
settings.json
).

10. Findings Summary
Critical (Must Fix)
#	Issue	Impact
C1	Profile Load Fail logged at DEBUG — invisible	User sees blank profile with no error indication
C2	Profile Save Fail logged at DEBUG — data loss invisible	User thinks save succeeded
C3	Silent except Exception: pass in disk check + notification	Operational blind spots
High (Should Fix)
#	Issue	Impact
H1	No formal error code registry	Error codes are undiscoverable without grep
H2	Logger naming inconsistency across tools	
configure_log_level()
 doesn't reach tools
H3	logging.basicConfig() in 3 scripts	Root logger pollution when imported
H4	
session_engine.py
 adds duplicate FileHandler	Double-writes to log files
Medium (Improve)
#	Issue	Impact
M1	40+ print(stderr) in tools/tests	Bypasses logging pipeline
M2	traceback.print_exc() in 5+ files	Unstructured error output
M3	No log correlation IDs	Cross-component tracing impossible
M4	Inconsistent log format strings	Parsing requires per-file regex
M5	No error metrics / counter	No dashboards possible
Low (Polish)
#	Issue	Impact
L1	app_logger singleton in 
logger_setup.py
 named CS2_Coach_App	Doesn't match cs2analyzer.* convention
L2	Exit codes not documented	CI/CD scripts can't distinguish failure modes
L3	No log level env var override	Requires code change for DEBUG in production
11. Recommendations (Prioritized)
Create ERROR_CODES.md — formalize the 24+ inline codes into a searchable registry with severity, module, and remediation.
Standardize logger names — rename all tools from Sanitizer/MacenaBuild/etc. to cs2analyzer.tools.*.
Promote DEBUG catches to WARNING/ERROR — Profile Load Fail and Profile Save Fail must be visible.
Remove duplicate handlers in 
session_engine.py
 — use 
get_logger()
 exclusively.
Replace print(stderr) in tools/tests with 
get_logger()
 or at minimum logging.getLogger(__name__).
Add a LOG_LEVEL env var to override log level without code changes.
Consider structured logging — adopt structlog or at least JSON format universally for machine-parseable logs.


Logging & Error Handling Infrastructure: 5-Star Overhaul Plan
This plan addresses every dimension from the audit report's rating table, detailing the exact file changes needed to bring each from its current rating to ⭐⭐⭐⭐⭐.

Current State → Target State
Dimension	Current	Target	Key Gaps
Centralized Logging	⭐⭐⭐⭐	⭐⭐⭐⭐⭐	Console & session engine bypass central logger
Structured Logging	⭐⭐⭐	⭐⭐⭐⭐⭐	Only 
console.py
 has JSON; rest is plaintext
Error Code System	⭐⭐	⭐⭐⭐⭐⭐	Inline-only, no registry, no machine-parseable enum
Custom Exceptions	⭐⭐⭐	⭐⭐⭐⭐⭐	Exist but underused; catch-all Exception everywhere
Error Reporting (Sentry)	⭐⭐⭐⭐⭐	⭐⭐⭐⭐⭐	Already production-grade — maintain
Catch-all Proliferation	⭐⭐	⭐⭐⭐⭐⭐	50+ bare except Exception blocks
Consistency	⭐⭐	⭐⭐⭐⭐⭐	Mixed print()/traceback.print_exc()/logger
Runtime Integrity (RASP)	⭐⭐⭐⭐	⭐⭐⭐⭐⭐	Missing logger integration, silent print(stderr)
Log Rotation & Retention	⭐⭐⭐⭐	⭐⭐⭐⭐⭐	Duplicate handlers, no retention policy
Debug Level Control	⭐⭐⭐⭐	⭐⭐⭐⭐⭐	No env var override, tools not wired
Proposed Changes
Component 1: Centralized Logger Factory — The Foundation
Everything flows from this component. The current 
logger_setup.py
 is good but needs to become the single source of truth for every module in the project, including tools and tests.

[MODIFY] 
logger_setup.py
Goal: Upgrade 
get_logger()
 to produce structured JSON logs, support env var overrides, add correlation ID threading, and expose a tool-specific factory.

Changes:

JSON Structured Formatter — Replace the plaintext Formatter with a JSON-emitting formatter that outputs machine-parseable log lines. This is the single most impactful change for structured logging.
python
class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for machine-parseable output."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "lvl": record.levelname,
            "mod": record.name,
            "thread": record.threadName,
            "msg": record.getMessage(),
        }
        # Attach correlation ID if present
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["cid"] = correlation_id
        # Attach error code if present
        error_code = getattr(record, "error_code", None)
        if error_code:
            log_entry["code"] = error_code
        # Attach exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exc_type"] = record.exc_info[0].__name__
            log_entry["exc_msg"] = str(record.exc_info[1])
            log_entry["traceback"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)
Environment Variable Override — Read CS2_LOG_LEVEL env var at startup for zero-code debug sessions.
python
def _resolve_log_level() -> int:
    env_level = os.environ.get("CS2_LOG_LEVEL", "").upper()
    return getattr(logging, env_level, logging.INFO)
Correlation ID Filter — A logging.Filter that injects a thread-local correlation ID into every log record, enabling cross-component tracing.
python
import threading
import uuid
_correlation_id: threading.local = threading.local()
def set_correlation_id(cid: str | None = None) -> str:
    """Set a correlation ID for the current thread. Returns the ID."""
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_id.value = cid
    return cid
def get_correlation_id() -> str | None:
    return getattr(_correlation_id, "value", None)
class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = getattr(_correlation_id, "value", None)
        return True
get_tool_logger() Factory — Dedicated function for standalone tool scripts, ensuring they get properly named loggers (cs2analyzer.tools.*) with their own JSON file handler but still share the namespace.
python
def get_tool_logger(tool_name: str) -> logging.Logger:
    """Logger factory for standalone tool scripts.
    
    Produces a logger named cs2analyzer.tools.<tool_name> with:
    - JSON file handler in logs/tools/<tool_name>_<timestamp>.json
    - Console handler at WARNING (for Rich-based tools that own stdout)
    """
    canonical_name = f"cs2analyzer.tools.{tool_name}"
    logger = logging.getLogger(canonical_name)
    if logger.handlers:
        return logger
    
    logger.setLevel(_resolve_log_level())
    
    tool_log_dir = os.path.join(_log_dir or "logs", "tools")
    os.makedirs(tool_log_dir, exist_ok=True)
    
    from datetime import datetime
    log_file = os.path.join(
        tool_log_dir,
        f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(JSONFormatter())
    logger.addHandler(fh)
    logger.addFilter(CorrelationFilter())
    logger.propagate = False
    return logger
Fix the singleton — Rename app_logger = get_logger("CS2_Coach_App") to app_logger = get_logger("cs2analyzer.app") for namespace consistency.

Add the JSON and uuid imports at the top of the file.

Integrate CorrelationFilter into the main 
get_logger()
 function — add logger.addFilter(CorrelationFilter()) after handler setup.

Switch 
_create_file_handler
 to use JSONFormatter instead of the plaintext formatter.

[NEW] 
error_codes.py
Goal: Machine-parseable error code registry. Every known inline code gets a formal definition with severity, module, description, and remediation.

python
"""
Centralized Error Code Registry for the CS2 Analyzer project.
Usage:
    from Programma_CS2_RENAN.observability.error_codes import ErrorCode, log_with_code
    
    logger.warning(
        log_with_code(ErrorCode.LS_01, "RotatingFileHandler unavailable for %s"),
        log_path,
    )
"""
from enum import Enum
from typing import NamedTuple
class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
class ErrorCodeDef(NamedTuple):
    code: str
    severity: Severity
    module: str
    description: str
    remediation: str
class ErrorCode(Enum):
    """Every error code used across the project.
    
    Naming convention: <MODULE_PREFIX>_<NUMBER>
    - LS: Logger Setup
    - RP: RASP
    - DA: Data Access
    - P0-P9: Pipeline/Processing
    - F6-F9: Feature/Fix
    - SE: Session Engine
    - IM: Ingestion Manager
    - NN: Neural Network
    - G: Game Analysis
    - H: Knowledge/HLTV
    """
    
    # --- Logger Setup ---
    LS_01 = ErrorCodeDef(
        "LS-01", Severity.MEDIUM, "observability.logger_setup",
        "RotatingFileHandler unavailable — using plain FileHandler",
        "Check file permissions. On Windows, close other processes holding the log file.",
    )
    
    # --- RASP ---
    RP_01 = ErrorCodeDef(
        "RP-01", Severity.HIGH, "observability.rasp",
        "CS2_MANIFEST_KEY not set — using static fallback HMAC key",
        "Set CS2_MANIFEST_KEY environment variable for production builds.",
    )
    
    # --- Data Access ---
    DA_01_03 = ErrorCodeDef(
        "DA-01-03", Severity.LOW, "main",
        "Malformed JSON from database (pc_specs_json)",
        "Re-run hardware detection or manually edit player profile.",
    )
    
    # --- Pipeline ---
    P0_07 = ErrorCodeDef(
        "P0-07", Severity.LOW, "main",
        "Attribute initialized to prevent AttributeError",
        "No user action needed. Internal guard.",
    )
    P3_01 = ErrorCodeDef(
        "P3-01", Severity.LOW, "main",
        "Role enum canonical mapping",
        "No user action needed. Role key normalization.",
    )
    P4_B = ErrorCodeDef(
        "P4-B", Severity.MEDIUM, "core.session_engine",
        "Configurable zombie task threshold",
        "Adjust ZOMBIE_TASK_THRESHOLD_SECONDS setting if large demos are being reset.",
    )
    P7_01 = ErrorCodeDef(
        "P7-01", Severity.HIGH, "console",
        "API keys stored in plaintext settings.json",
        "Migrate to OS credential store via the keyring library.",
    )
    P7_02 = ErrorCodeDef(
        "P7-02", Severity.HIGH, "console",
        "Secret sanitization in error messages",
        "Ensure all secret keys are listed in the sanitization loop.",
    )
    
    # --- Feature/Fix codes ---
    F6_03 = ErrorCodeDef(
        "F6-03", Severity.LOW, "core.session_engine",
        "Explicit commit for trained sample count",
        "No user action needed.",
    )
    F6_06 = ErrorCodeDef(
        "F6-06", Severity.LOW, "core.session_engine",
        "sys.path bootstrap for direct script execution",
        "Remove when entrypoints are configured in pyproject.toml.",
    )
    F6_SE = ErrorCodeDef(
        "F6-SE", Severity.HIGH, "core.session_engine",
        "Backup failure — training gate engaged",
        "Resolve backup issue and restart session engine.",
    )
    F7_12 = ErrorCodeDef(
        "F7-12", Severity.LOW, "console",
        "sys.path bootstrap for root-level CLI entry points",
        "Remove when pip install -e . and python -m invocation are standard.",
    )
    F7_19 = ErrorCodeDef(
        "F7-19", Severity.LOW, "main",
        "Training status card KivyMD properties",
        "No user action needed.",
    )
    F7_30 = ErrorCodeDef(
        "F7-30", Severity.MEDIUM, "console",
        "API key masking shows last 4 characters",
        "Acceptable until keyring is integrated.",
    )
    
    # --- Session Engine ---
    SE_02 = ErrorCodeDef(
        "SE-02", Severity.MEDIUM, "core.session_engine",
        "Daemon thread join for graceful shutdown",
        "No user action needed.",
    )
    SE_04 = ErrorCodeDef(
        "SE-04", Severity.MEDIUM, "core.session_engine",
        "Config validation for zombie threshold",
        "Ensure ZOMBIE_TASK_THRESHOLD_SECONDS is a positive integer.",
    )
    SE_05 = ErrorCodeDef(
        "SE-05", Severity.HIGH, "core.session_engine",
        "Backup failure surfaced to UI",
        "Check backup manager configuration and disk space.",
    )
    SE_06 = ErrorCodeDef(
        "SE-06", Severity.LOW, "core.session_engine",
        "Short wait for faster shutdown response",
        "No user action needed.",
    )
    SE_07 = ErrorCodeDef(
        "SE-07", Severity.MEDIUM, "core.session_engine",
        "Settings reload once per scan cycle (TOCTOU window)",
        "Acceptable for MEDIUM severity. Next cycle picks up new values.",
    )
    
    # --- Ingestion Manager ---
    IM_03 = ErrorCodeDef(
        "IM-03", Severity.MEDIUM, "core.session_engine",
        "Event wait/clear ordering to prevent lost wakeup signals",
        "No user action needed.",
    )
    
    # --- Neural Network ---
    NN_02 = ErrorCodeDef(
        "NN-02", Severity.MEDIUM, "core.session_engine",
        "Module-level training lock prevents concurrent training",
        "No user action needed.",
    )
    
    # --- Game Analysis ---
    G_07 = ErrorCodeDef(
        "G-07", Severity.LOW, "core.session_engine",
        "Belief calibration wired to Teacher daemon",
        "No user action needed.",
    )
    
    # --- Knowledge/HLTV ---
    H_02 = ErrorCodeDef(
        "H-02", Severity.LOW, "core.session_engine",
        "One-time knowledge base population from pro demos",
        "No user action needed.",
    )
    
    # --- Manifest ---
    R1_12 = ErrorCodeDef(
        "R1-12", Severity.HIGH, "observability.rasp",
        "HMAC manifest signing for integrity verification",
        "Ensure CS2_MANIFEST_KEY is set at build time.",
    )
def log_with_code(error_code: ErrorCode, message: str) -> str:
    """Prefix a log message with its formal error code.
    
    Usage:
        logger.warning(log_with_code(ErrorCode.LS_01, "Handler unavailable for %s"), path)
    """
    defn = error_code.value
    return f"[{defn.code}] {message}"
def get_all_codes() -> list[dict]:
    """Return all error codes as a list of dicts for programmatic access."""
    return [
        {
            "code": e.value.code,
            "severity": e.value.severity.value,
            "module": e.value.module,
            "description": e.value.description,
            "remediation": e.value.remediation,
        }
        for e in ErrorCode
    ]
[NEW] 
ERROR_CODES.md
Goal: Human-readable reference generated from the enum above. Auto-generated via a script or maintained manually initially.

This file will contain a markdown table with all error codes, their severity, module, description, and remediation steps. Organized by module prefix.

Component 2: Eliminate Dual/Conflicting Logging
[MODIFY] 
console.py
Lines 99–112: Replace the standalone FileHandler + custom JSON formatter with a call to get_tool_logger("console").

Before (current):

python
_log_dir = PROJECT_ROOT / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
_log_file = _log_dir / f"console_{datetime.now().strftime('%Y%m%d')}.json"
_fh = logging.FileHandler(_log_file, encoding="utf-8")
_fh.setLevel(logging.INFO)
_fh.setFormatter(
    logging.Formatter(
        '{"ts":"%(asctime)s","lvl":"%(levelname)s","mod":"%(name)s","msg":"%(message)s"}'
    )
)
logger = logging.getLogger("cs2analyzer.console")
logger.setLevel(logging.INFO)
logger.addHandler(_fh)
After:

python
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger
logger = get_tool_logger("console")
This removes the format inconsistency and ensures 
console.py
 logs go through the centralized JSON formatter with correlation ID support.

[MODIFY] 
session_engine.py
Lines 32–48: Remove the duplicate FileHandler addition. The 
get_logger("cs2analyzer.session_engine")
 call on line 30 already provides 
cs2_analyzer.log
 via the centralized setup — that is sufficient. The session engine should not add its own second handler.

Before (current):

python
logger = get_logger("cs2analyzer.session_engine")
# File logging for session engine subprocess
_session_fh = None
try:
    from Programma_CS2_RENAN.core.config import LOG_DIR
    log_file = os.path.join(LOG_DIR, "session_engine.log")
    _session_fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    _session_fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    _session_fh.setFormatter(formatter)
    logger.addHandler(_session_fh)
    logger.info("Session Engine File Logging Initialized")
except Exception as e:
    if _session_fh is not None:
        _session_fh.close()
        _session_fh = None
    logger.warning("Failed to setup file logging: %s", e)
After:

python
logger = get_logger("cs2analyzer.session_engine")
That's it. All 18 lines of duplicate handler setup removed. The centralized logger already handles file output.

[MODIFY] 
batch_ingest.py
Lines 27–35: Replace logging.basicConfig() with get_tool_logger().

Before:

python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | [%(processName)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("batch_ingest")
After:

python
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger
logger = get_tool_logger("batch_ingest")
NOTE

batch_ingest.py
 uses multiprocessing. Each worker subprocess will need its own logger setup inside 
ingest_one_demo()
. The get_tool_logger() call is safe to use in workers because it creates per-logger handlers, not root-level basicConfig.

Component 3: Tools Migration — Standardize All 8 Tool Loggers
Every tool in the tools/ directory follows the same boilerplate pattern: custom 
setup_logging()
 function, ad-hoc logger name, own JSON format. All 8 must be migrated to get_tool_logger().

[MODIFY] 
Sanitize_Project.py
Remove: The entire 
setup_logging()
 function (lines 55–69) and the logger setup in 
init
 (line 76).

Replace with:

python
from Programma_CS2_RENAN.observability.logger_setup import get_tool_logger
# In IndustrialSanitizer.__init__:
self.logger = get_tool_logger("sanitizer")
[MODIFY] 
build_pipeline.py
Same pattern: Remove 
setup_logging()
 (lines 60–77), replace with get_tool_logger("build_pipeline").

[MODIFY] 
audit_binaries.py
Replace logger name BinaryAuditor → get_tool_logger("audit_binaries").

[MODIFY] 
Feature_Audit.py
Replace logger name FeatureAuditor → get_tool_logger("feature_audit").

[MODIFY] 
migrate_db.py
Replace logger name DBMigrator → get_tool_logger("migrate_db").

[MODIFY] 
observe_training_cycle.py
Replace logging.basicConfig() + observe_cycle logger → get_tool_logger("observe_training").

Also replace all 3 instances of traceback.print_exc() with logger.exception("...").

[MODIFY] 
test_tactical_pipeline.py
Replace traceback.format_exc() usage with logger.exception().

Component 4: Exception Hierarchy — Typed Error Handling
[NEW] 
exceptions.py
Goal: Centralized exception hierarchy. All existing domain exceptions stay where they are but inherit from a common CS2AnalyzerError base. New code catches specific types instead of bare Exception.

python
"""
Centralized exception hierarchy for the CS2 Analyzer.
All domain-specific exceptions should inherit from CS2AnalyzerError.
This enables:
  1. Typed catch blocks instead of bare `except Exception`
  2. Error code attachment to exceptions
  3. Consistent Sentry fingerprinting
"""
from Programma_CS2_RENAN.observability.error_codes import ErrorCode
class CS2AnalyzerError(Exception):
    """Base exception for all CS2 Analyzer errors."""
    
    def __init__(self, message: str, error_code: ErrorCode | None = None):
        self.error_code = error_code
        super().__init__(message)
class ConfigurationError(CS2AnalyzerError):
    """Invalid or missing configuration."""
    pass
class DatabaseError(CS2AnalyzerError):
    """Database operation failure."""
    pass
class IngestionError(CS2AnalyzerError):
    """Demo file ingestion failure."""
    pass
class TrainingError(CS2AnalyzerError):
    """ML training pipeline failure."""
    pass
class IntegrationError(CS2AnalyzerError):
    """External service integration failure (Steam, FACEIT, HLTV)."""
    pass
class UIError(CS2AnalyzerError):
    """UI rendering or interaction failure."""
    pass
Component 5: Catch-All Cleanup — The Largest Changeset
This is the most labor-intensive component. The strategy is:

Critical path except Exception blocks (in 
main.py
, 
session_engine.py
, 
console.py
) get upgraded to catch specific types with a final except Exception fallback that logs at ERROR/CRITICAL with exc_info=True.
Profile load/save DEBUG logs get promoted to WARNING/ERROR.
Silent pass blocks get a logger.debug() minimum.
print(stderr) patterns — replace with logger.error() where feasible.
[MODIFY] 
main.py
Critical Fix 1 — Line 401: Profile load logged at DEBUG is invisible.

diff
-            app_logger.debug("Profile Load Fail: %s", e)
+            app_logger.warning("Profile load failed — displaying defaults: %s", e)
Critical Fix 2 — Line 485: Profile save logged at DEBUG means data loss is invisible.

diff
-            app_logger.debug("Profile Save Fail: %s", e)
+            app_logger.error("Profile save failed — user data may be lost: %s", e, exc_info=True)
Line 253: Catch-all in analytics is already correct (app_logger.error) — no change needed.

Line 333: Catch-all in insights is already correct — no change needed.

Line 56: print("WARNING: Database migration failed...") → replace with app_logger.warning(...).

Line 14: print("ERROR: Not in venv...") — this is pre-logger, must stay as print(stderr). No change.

Lines 29, 32, 36: RASP pre-logger prints — must stay as print(stderr). No change. These fire before any import can succeed; using print here is the correct choice.

[MODIFY] 
session_engine.py
Line 256–258: Silent pass in disk check notification.

diff
-            except Exception:
-                pass  # Don't crash the scanner over a notification
+            except Exception as notify_err:
+                logger.debug("Disk space notification failed: %s", notify_err)
Line 258–259: Silent pass in disk check itself.

diff
-    except Exception:
-        pass  # Don't crash the scanner over a disk check
+    except Exception as disk_err:
+        logger.debug("Disk space check failed: %s", disk_err)
[MODIFY] 
sentry_setup.py
Line 152: Silent exception suppression in 
add_breadcrumb
.

diff
-    except Exception as e:
-        _ = e  # Intentionally suppressed
+    except Exception as e:
+        logger.debug("Breadcrumb recording failed (non-fatal): %s", e)
Component 6: RASP Logger Integration
[MODIFY] 
rasp.py
Goal: Replace print(stderr) calls in 
run_rasp_audit()
 with proper logger usage, while keeping print(stderr) as a fallback for frozen builds where the logger might not be available.

Lines 180, 185–187: The 
run_rasp_audit()
 function uses print(file=sys.stderr).

diff
def run_rasp_audit(project_root: Path) -> bool:
+    from Programma_CS2_RENAN.observability.logger_setup import get_logger
+    rasp_logger = get_logger("cs2analyzer.rasp")
+    
     guard = RASPGuard(project_root)
     if not guard.check_frozen_binary():
-        print("CRITICAL: Suspicious execution environment detected!", file=sys.stderr)
+        rasp_logger.critical("Suspicious execution environment detected!")
         return False
 
     success, violations = guard.verify_runtime_integrity()
     if not success:
-        print("--- INTEGRITY VIOLATION DETECTED ---", file=sys.stderr)
+        rasp_logger.critical("INTEGRITY VIOLATION DETECTED")
         for v in violations:
-            print(f" ! {v}", file=sys.stderr)
+            rasp_logger.critical("  Violation: %s", v)
         return False
     return True
Line 17: Replace warnings.warn() for RP-01 with a proper logger call using the error code system.

diff
-    warnings.warn(
-        "RP-01: CS2_MANIFEST_KEY not set — using static fallback HMAC key. "
-        "Set the environment variable for production builds.",
-        stacklevel=1,
-    )
+    # RP-01: Module-level warning via logging (warnings.warn is not captured by Sentry)
+    import logging as _log
+    _log.getLogger("cs2analyzer.rasp").warning(
+        "[RP-01] CS2_MANIFEST_KEY not set — using static fallback HMAC key. "
+        "Set the environment variable for production builds."
+    )
Component 7: Test Verification Script — print(stderr) to Logger Migration
The test scripts under tests/ and tools/ use print("ERROR:", file=sys.stderr) extensively. These are standalone verification scripts that print directly. The strategy differs from the main app:

Venv guard print(stderr) at top of file: Keep as-is. These fire before any import is possible. Correct behavior.
Error reporting in the body of verification scripts: Replace print("CRITICAL FAILURE: ...") with logger.error(...) using get_tool_logger().
traceback.print_exc() calls: Replace with logger.exception().
Files to modify:

verify_chronovisor_real.py
 — Replace logging.basicConfig() + ad-hoc logger with get_tool_logger("verify_chronovisor").
verify_map_integration.py
 — Replace traceback.print_exc() with logger.exception().
verify_superposition.py
 — Replace traceback.print_exc() with logger.exception().
Component 8: Log Retention Policy & Exit Codes
[MODIFY] 
logger_setup.py
Log retention: The RotatingFileHandler with 5 MB × 3 backups is good. Add a TimedRotatingFileHandler as an alternative for daily rotation with configurable retention.

Add a configure_retention() function:

python
def configure_retention(max_days: int = 30) -> None:
    """Purge log files older than max_days from the log directory.
    
    Called at application startup to enforce retention policy.
    Safe to call multiple times.
    """
    log_dir = _log_dir or "logs"
    if not os.path.isdir(log_dir):
        return
    
    import time
    cutoff = time.time() - (max_days * 86400)
    
    for f in os.listdir(log_dir):
        fp = os.path.join(log_dir, f)
        if os.path.isfile(fp) and f.endswith((".log", ".json")):
            if os.path.getmtime(fp) < cutoff:
                try:
                    os.remove(fp)
                except OSError:
                    pass  # Best-effort cleanup
[NEW] 
EXIT_CODES.md
Goal: Document all exit codes for CI/CD and operator reference.

Code	Meaning	Used By
0	Success / Duplicate instance	
main.py
, all tools
1	Runtime failure / integrity failure / build failure	
main.py
, 
rasp.py
, 
console.py
, tools
2	Not in virtualenv	
main.py
, 
console.py
, all tools
Component 9: Observability Test Suite
There are currently zero tests for the observability module. We need a test file that verifies the logging infrastructure behaves correctly.

[NEW] 
test_observability.py
Test cases:

test_get_logger_returns_same_instance — 
get_logger("cs2analyzer.test")
 called twice returns the same logger with no duplicate handlers.
test_json_formatter_output — Capture log output and json.loads() it; verify fields 
ts
, lvl, 
mod
, 
thread
, msg are present.
test_json_formatter_includes_exception — Log with exc_info=True; verify exc_type, exc_msg, traceback fields exist in JSON.
test_correlation_id_filter — Set a correlation ID, log a message, verify cid field appears in JSON output.
test_configure_log_level_changes_all_cs2analyzer_loggers — Create loggers, call 
configure_log_level(logging.DEBUG)
, verify all changed.
test_log_level_env_var_override — Set CS2_LOG_LEVEL=DEBUG env var, create a new logger, verify it's at DEBUG.
test_error_code_registry_completeness — Verify all ErrorCode enum members have non-empty fields.
test_log_with_code_format — Verify log_with_code(ErrorCode.LS_01, "msg") produces "[LS-01] msg".
test_get_tool_logger_creates_tools_subdir — Verify get_tool_logger("test_tool") creates logs/tools/ directory and a JSON file.
test_configure_retention_removes_old_files — Create dummy log files with old timestamps, call configure_retention(max_days=1), verify deletions.
User Review Required
IMPORTANT

Scope decision: The print("ERROR: Not in venv", file=sys.stderr) pattern appears at the top of ~15 files as a pre-import venv guard. These must stay as print() because the logging module may not be available outside the venv. The plan explicitly does NOT change these.

WARNING

Breaking change potential: Changing the log format from plaintext to JSON affects any scripts or tools that parse 
cs2_analyzer.log
 with regex. If there are any external log parsers or monitoring tools that consume the current plaintext format, they will need updating.

IMPORTANT

batch_ingest.py
 multiprocessing: Each worker subprocess currently calls logging.basicConfig() which modifies the root logger. Replacing with get_tool_logger() in the main process is safe, but the 
ingest_one_demo()
 worker function runs in a separate process and needs its own logger setup. The plan accounts for this by keeping a simple logging.getLogger() call inside the worker with a local handler, since get_tool_logger() relies on imports that may have import-lock issues under fork().

File Change Summary
Action	File	Component
MODIFY	
Programma_CS2_RENAN/observability/logger_setup.py
1 (Foundation)
NEW	Programma_CS2_RENAN/observability/error_codes.py	1 (Error Registry)
NEW	Programma_CS2_RENAN/observability/exceptions.py	4 (Exception Hierarchy)
NEW	docs/ERROR_CODES.md	1 (Documentation)
NEW	docs/EXIT_CODES.md	8 (Documentation)
NEW	Programma_CS2_RENAN/tests/test_observability.py	9 (Tests)
MODIFY	
console.py
2 (Eliminate Dual Logging)
MODIFY	
Programma_CS2_RENAN/core/session_engine.py
2, 5 (Eliminate Dual, Catch-all)
MODIFY	
batch_ingest.py
2 (Eliminate basicConfig)
MODIFY	
Programma_CS2_RENAN/main.py
5 (Critical Log Level Promotions)
MODIFY	
Programma_CS2_RENAN/observability/sentry_setup.py
5 (Silent Suppression)
MODIFY	
Programma_CS2_RENAN/observability/rasp.py
6 (Logger Integration)
MODIFY	
tools/Sanitize_Project.py
3 (Tool Migration)
MODIFY	
tools/build_pipeline.py
3
MODIFY	
tools/audit_binaries.py
3
MODIFY	
tools/Feature_Audit.py
3
MODIFY	
tools/migrate_db.py
3
MODIFY	
tools/observe_training_cycle.py
3, 5
MODIFY	
tools/test_tactical_pipeline.py
3, 5
MODIFY	
tests/verify_chronovisor_real.py
7
MODIFY	
tests/verify_map_integration.py
7
MODIFY	
tests/verify_superposition.py
7
Total: 6 new files, 16 modified files.

Verification Plan
Automated Tests
Command to run the new observability test suite:

bash
cd "/media/renan/SSD Portable/Counter-Strike-coach-AI/Counter-Strike-coach-AI-main"
python -m pytest Programma_CS2_RENAN/tests/test_observability.py -v
This validates:

JSON formatter output structure
Correlation ID propagation
Log level env var override
Error code registry completeness
Tool logger file creation
Log retention cleanup
Command to run the full existing test suite (regression check):

bash
cd "/media/renan/SSD Portable/Counter-Strike-coach-AI/Counter-Strike-coach-AI-main"
python -m pytest Programma_CS2_RENAN/tests/ -x -q
This ensures none of the logging changes break existing functionality.

Manual Verification
JSON log output: After changes, run python console.py help and inspect logs/tools/console_*.json — verify each line is valid JSON with 
ts
, lvl, 
mod
, 
thread
, msg fields.

Correlation ID: Run python console.py sys status and inspect the log file — verify cid field appears in log entries.

Environment variable override: Run CS2_LOG_LEVEL=DEBUG python console.py sys status and check that DEBUG-level messages appear in the log file.

Error code in logs: After wiring log_with_code() into 
rasp.py
, set CS2_MANIFEST_KEY="" and import the module — verify log contains [RP-01] prefix.

Log retention: Create a dummy 
.log
 file in 
logs/
 with an old modification time (touch -t 202501011200 logs/old_test.log), call configure_retention(max_days=1), verify it is deleted.

Grep audit for remaining anti-patterns:

bash
# Should return 0 results outside of venv guards and pre-import contexts:
grep -rn "traceback.print_exc" Programma_CS2_RENAN/ --include="*.py" | grep -v __pycache__
# Should return 0 results:
grep -rn "logging.basicConfig" Programma_CS2_RENAN/ tools/ tests/ --include="*.py" | grep -v __pycache__
# All logger names should start with cs2analyzer:
grep -rn "getLogger(" Programma_CS2_RENAN/ tools/ --include="*.py" | grep -v __pycache__ | grep -v "cs2analyzer"
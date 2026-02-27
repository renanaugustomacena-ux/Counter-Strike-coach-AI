# Demo File Registry & Lifecycle Management

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

Demo file registry tracking and lifecycle state management. Prevents duplicate ingestion, tracks processing status, and provides audit trail for all demo file operations.

## Key Components

### `registry.py`
- **Demo file registration** — Records all discovered demo files in `DemoFileRecord` table
- **Duplicate detection** — File hash verification prevents redundant processing
- **Metadata tracking** — File size, discovery timestamp, source type (user/pro/tournament)
- **Query interface** — Retrieve files by status, source, date range

### `lifecycle.py`
- **State machine implementation** — Manages demo processing lifecycle
- **States**: `discovered` → `queued` → `processing` → `completed` | `failed`
- **Atomic state transitions** — Database transactions ensure consistency
- **Error state handling** — Failed files marked with error code and retry count

## Lifecycle States

1. **Discovered** — File found during directory scan, not yet validated
2. **Queued** — Validated and ready for ingestion, waiting for processing slot
3. **Processing** — Currently being parsed and ingested
4. **Completed** — Successfully ingested, all derived data persisted
5. **Failed** — Ingestion failed, error logged, marked for manual review

## Integration

Used by all ingestion pipelines (`user_ingest.py`, `pro_ingest.py`, `json_tournament_ingestor.py`) to:
- Check if file already processed before starting ingestion
- Update processing status in real-time
- Mark completion or failure with detailed error context

## Registry Queries

- `get_pending_files()` — Returns all files in `discovered` or `queued` state
- `get_failed_files()` — Returns files that failed ingestion with error details
- `get_completed_files(source_type, date_range)` — Retrieves successfully processed files by filter criteria

## Error Handling

Failed ingestions increment retry counter. After 3 failures, file is marked as permanently failed and requires manual intervention. All errors logged with correlation IDs for traceability.

## Database Schema

`DemoFileRecord` table includes:
- `file_path`, `file_hash`, `file_size`, `source_type`
- `lifecycle_state`, `error_code`, `retry_count`
- `discovered_at`, `queued_at`, `processing_started_at`, `completed_at`

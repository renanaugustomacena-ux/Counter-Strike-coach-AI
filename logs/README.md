> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Centralized System Logs

This directory serves as the centralized hub for system-wide observability and diagnostic data. It aggregates logs from the backend engine, match ingestion services, and AI inference modules to provide a comprehensive view of the system's operational health.

## Technical Overview

The logging architecture is designed for high-granularity monitoring of the Counter-Strike coach backend. Logs are generated using a structured format to facilitate automated analysis and alerting. The primary goal is to ensure that performance bottlenecks, ingestion failures, and model drifts are identified and resolved in real-time.

## Key Components

- **`cs2_analyzer.log`**: The primary log file for the backend analysis engine. It tracks:
    - **Error Monitoring**: Detailed stack traces for API failures, database connection issues, and demo parsing errors.
    - **Ingestion Throughput**: Metrics on how many demo files are being processed per minute, including file size and parsing duration.
    - **Inference Latency**: Precise timing for LLM and VLM requests, allowing for the optimization of model response times.
    - **System Health**: Periodic heartbeats from background worker processes and the HLTV sync service.

## Directory Structure

```text
logs/
├── cs2_analyzer.log        # Main backend and analysis log
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

### Real-time Monitoring
To monitor the system logs in real-time during a large-scale ingestion or training session:
```bash
tail -f logs/cs2_analyzer.log
```

### Log Rotation
The system is configured to automatically rotate logs when they reach 100MB, keeping up to 5 historical versions (e.g., `cs2_analyzer.log.1`) to prevent disk space exhaustion.

### Filtering for Errors
To quickly identify critical issues within the logs:
```bash
grep "ERROR" logs/cs2_analyzer.log
```

### Performance Analysis
Log entries include `latency_ms` fields for inference calls, which can be extracted to generate performance histograms and identify slow model responses.

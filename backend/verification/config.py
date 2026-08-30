"""M5 configuration.  Environment-driven, with safe defaults."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Durable store for VerificationRecords.  M4's submission store is process
#: memory; M5 keeps its own records so an analysis survives a restart and
#: re-links to a resubmitted file by SHA-256.
STORE_PATH = Path(os.environ.get(
    "M5_STORE_PATH", str(PROJECT_ROOT / ".m5-data" / "records.db")))

#: Retention window for verification records.
RETENTION_DAYS = int(os.environ.get("M5_RETENTION_DAYS", "90"))

#: Origins permitted to read M5 responses, which carry extracted document
#: information.  Defaults match frontend/vite.config.ts (port 5173).
ALLOWED_ORIGINS = tuple(
    origin.strip() for origin in os.environ.get(
        "M5_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
)

#: Path prefix the M5 CORS override applies to.  Nothing outside it is touched.
API_PREFIX = "/api/verification"
